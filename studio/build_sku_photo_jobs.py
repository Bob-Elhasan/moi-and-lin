"""One on-model photo per SKU, with the ONE model (assets/model/front.png), styled by the combinations sheet.

Top / dress SKU  -> the model wears that SKU; bottom, undershirt and footwear come from the Excel row whose top has the
                    same product code and the closest colour (so 'Mustard top -> white pants + white ballet flats' carries over).
Bottom SKU       -> the model wears that bottom colour with the top (and footwear) of the Excel row for that bottom.
Writes data/sku_photo_jobs.json
"""
import csv, json, re, os, sys
from pathlib import Path
sys.path.insert(0, ".")
from studio.sheet import load_outfits, code_key
from studio.color_skus import PALETTE, BOTTOM_PALETTE, slug

KEYS = [("charcoal", "Dark Gray"), ("burgundy", "Burgundy"), ("navy", "Navy"), ("sky", "Sky Blue"), ("powder", "Sky Blue"), ("turquoise", "Turquoise"),
 ("aqua", "Aqua"), ("mint", "Mint"), ("sage", "Light Green"), ("olive", "Olive"), ("kiwi", "Kiwi"), ("green", "Green"), ("mustard", "Mustard"),
 ("yellow", "Lemon"), ("lemon", "Lemon"), ("camel", "Camel"), ("tan", "Camel"), ("chocolate", "Brown"), ("brown", "Brown"), ("khaki", "Beige"),
 ("taupe", "Café"), ("stone", "Beige"), ("beige", "Beige"), ("cream", "Cream"), ("ivory", "Cream"), ("off", "Off White"), ("white", "White"),
 ("black", "Black"), ("dark gr", "Dark Gray"), ("grey", "Gray"), ("gray", "Gray"), ("lavender", "Lavender"), ("lilac", "Lavender"), ("mauve", "Mauve"),
 ("plum", "Dark Mauve"), ("purple", "Purple"), ("dusty rose", "Rose"), ("blush", "Rose"), ("rose", "Rose"), ("pink", "Pink"), ("cobalt", "Blue"),
 ("blue", "Blue"), ("indigo", "Indigo"), ("red", "Red"), ("cafe", "Café"), ("café", "Café")]
def name_hex(name):
    n = (name or "").lower()
    for k, p in KEYS:
        if k in n: return PALETTE[p], p
    return None, None
def hex_rgb(h): return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
def dist(a, b): return sum((x - y) ** 2 for x, y in zip(hex_rgb(a), hex_rgb(b)))

def base(c):
    c = re.sub(r"\(.*?\)", "", c).strip().upper()
    c = re.sub(r"[ -](GREY|OFF[ -]WHITE|BLACK)$", "", c)
    c = c.replace("NO23", "N023").replace("/", "-").replace(" ", "-")
    return "601" if c == "601-1" else c

# ---- Excel
outs = load_outfits("data/combinations.xlsx")
rows = []   # one per Excel row
for o in outs:
    for r, bc, tc in o.colors:
        rows.append({"row": r, "barcode": bc, "top": o.top, "top_base": base(o.top), "bottom": o.bottom, "bottom_base": base(o.bottom),
                     "top_color": tc, "bottom_color": o.bottom_color, "undershirt": o.undershirt, "footwear": o.footwear})
# ---- cut-outs
plan = {}
for j in json.load(open("data/color_plan.json")): plan.setdefault(j["sku"], {})[j["side"]] = j["out"]
def ghost(kind, code, color):
    for g in json.load(open("data/ghost_jobs.json")):
        pass
G = {}
for g in json.load(open("data/ghost_jobs.json")):
    if g["side"] == "front": G[(g["kind"], base(g["code"]), g["color"].lower())] = "output/" + g["folder"].split("Ghost Mannequin/", 1)[0] + g["folder"] + "/" + g["file"] if False else "output/" + g["folder"] + "/" + g["file"]
def ghost_for(kind, code, color_name):
    """Ghost cut-out from the November run (Excel colours) closest to the wanted colour."""
    cands = [(k, v) for k, v in G.items() if k[0] == kind and k[1] == base(code) and os.path.exists(v)]
    if not cands: return None
    want, _ = name_hex(color_name)
    if not want: want = None
    best = min(cands, key=lambda kv: dist(want, (name_hex(kv[0][2])[0] or "#808080")) if want else 0)
    return best[1]

skus = list(csv.DictReader(open("data/skus.csv", encoding="utf-8")))
sku_by = {(s["Product code"], s["Colour"]): s for s in skus}
FOOT_DEFAULT = "White Balerina"
def style_for_top(code, colour):
    hx = PALETTE.get(colour)
    cands = [r for r in rows if r["top_base"] == base(code)]
    if not cands: return None
    best = min(cands, key=lambda r: dist(hx, name_hex(r["top_color"])[0] or "#808080"))
    return best

def bottom_ref(bcode, bcolour_name):
    """Cut-out for the bottom in the colour the Excel asks for ('' = its original colour)."""
    if bcolour_name:
        want, pal = name_hex(bcolour_name)
        cands = [s for s in skus if base(s["Product code"]) == base(bcode) and s["Type"] == "Bottom" and s["SKU ID"] in plan]
        if cands and want:
            s = min(cands, key=lambda s: dist(want, BOTTOM_PALETTE.get(s["Colour"]) or PALETTE[s["Colour"]]))
            return plan[s["SKU ID"]]["front"], s["Colour"], False
        sub = ghost_for("bottom", bcode, bcolour_name)
        return sub, bcolour_name, False
    return ghost_for("bottom", bcode, "Original") or None, "its original colour", True

jobs, blocked = [], []
for s in skus:
    code, typ, col, sid = s["Product code"], s["Type"], s["Colour"], s["SKU ID"]
    if code == "7098":
        continue
    job = {"sku": sid, "code": code, "type": typ, "colour": col, "hex": (BOTTOM_PALETTE.get(col) if typ == "Bottom" else None) or PALETTE.get(col),
           "model": "assets/model/front.png"}
    if typ in ("Top", "Dress"):
        job["garment_ref"] = plan.get(sid, {}).get("front")
        job["garment_ref_kind"] = "colour-exact cut-out" if job["garment_ref"] else None
        if not job["garment_ref"]:                       # no coloured cut-out yet: nearest same-product cut-out, recoloured by prompt
            job["garment_ref"] = ghost_for("top" if typ == "Top" else "dress", code, col)
            job["garment_ref_kind"] = "same product, other colour (recolour by prompt)" if job["garment_ref"] else None
        st = style_for_top(code, col)
        if typ == "Dress":
            job.update(bottom=None, undershirt="", footwear=FOOT_DEFAULT, style_source="dress default (no dresses in the sheet)")
        elif st:
            br, bcn, orig = bottom_ref(st["bottom"], st["bottom_color"])
            job.update(bottom=st["bottom"], bottom_colour=bcn, bottom_original=orig, bottom_ref=br, undershirt=st["undershirt"],
                       footwear=st["footwear"] or FOOT_DEFAULT, style_source=f"sheet row {st['row']} ({st['top']} {st['top_color']})")
        else:                                            # product not in the sheet: use the pairing printed in the PDF
            pair = next((p for p in csv.DictReader(open("data/sku_products.csv", encoding="utf-8")) if p["Product code"] == code), {})
            pb = (pair.get("Shown paired with (PDF)") or "").split(", ")[0]
            light = col in ("White", "Off White", "Cream", "Beige", "Light Beige", "Mint", "Canary", "Lemon", "Pink")
            bcol = "Black" if light else "Off White"
            br = None
            for b in skus:
                if b["Type"] == "Bottom" and b["Product code"] == pb and b["Colour"] == bcol and b["SKU ID"] in plan: br = plan[b["SKU ID"]]["front"]
            job.update(bottom=pb, bottom_colour=bcol, bottom_original=False, bottom_ref=br, undershirt="", footwear=FOOT_DEFAULT,
                       style_source="not in the sheet: PDF pairing, neutral contrast colour, white ballet flats")
    else:  # Bottom SKU
        job["garment_ref"] = plan.get(sid, {}).get("front"); job["garment_ref_kind"] = "colour-exact cut-out" if job["garment_ref"] else None
        cands = [r for r in rows if r["bottom_base"] == base(code)]
        if cands:
            hx = job["hex"]
            r = min(cands, key=lambda r: dist(hx, (name_hex(r["bottom_color"])[0] or hx)) if r["bottom_color"] else 10 ** 9) if any(c["bottom_color"] for c in cands) else cands[0]
            tg = ghost_for("top", r["top"], r["top_color"])
            job.update(top=r["top"], top_colour=r["top_color"], top_ref=tg, undershirt=r["undershirt"], footwear=r["footwear"] or FOOT_DEFAULT,
                       style_source=f"sheet row {r['row']} ({r['top']} {r['top_color']})")
        else:
            job.update(top=None, top_ref=None, undershirt="", footwear=FOOT_DEFAULT, style_source="bottom not in the sheet")
    miss = []
    if not job.get("garment_ref"): miss.append("garment reference")
    if typ == "Top" and job.get("bottom") and not job.get("bottom_ref"): miss.append("bottom reference")
    if typ == "Bottom" and not job.get("top_ref"): miss.append("top reference")
    job["blocked_by"] = miss
    (blocked if miss else jobs).append(job)
allj = jobs + blocked
json.dump(allj, open("data/sku_photo_jobs.json", "w"), indent=1, ensure_ascii=False)
import collections
print(len(allj), "SKU photos;", len(jobs), "ready;", len(blocked), "blocked", collections.Counter(tuple(b["blocked_by"]) for b in blocked))
print(collections.Counter(j["garment_ref_kind"] for j in allj))
print(collections.Counter(j["style_source"].split(" (")[0] for j in allj))
for b in blocked[:0]: print(b["sku"])
