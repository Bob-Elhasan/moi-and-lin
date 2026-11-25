"""Colourway sheet from the classified client catalogue photos (scratchpad cw/out*.json) against the PDF SKUs.
  python studio/build_colourway_sheet.py <cw dir> <out.xlsx>"""
import csv, glob, json, re, sys, collections
sys.path.insert(0, ".")
from studio.build_sku_photo_jobs import name_hex, dist, PALETTE

cw, out = sys.argv[1], sys.argv[2]
recs = [r for f in sorted(glob.glob(f"{cw}/out*.json")) for r in json.load(open(f))]
skus = list(csv.DictReader(open("data/skus.csv", encoding="utf-8")))
prods = {p["Product code"]: p for p in csv.DictReader(open("data/sku_products.csv", encoding="utf-8"))}
key = lambda c: re.sub(r"^12[56]/", "", c).upper()
folder_codes = {}
for r in recs:
    for c in re.split(r"\s*-\s*", r["folder"]): folder_codes.setdefault(c.strip().upper(), set()).add(r["folder"])
def pdf_code_for(folder_code):
    return next((p for p in prods if key(p) == folder_code or p.upper() == folder_code), None)

def colour_for(rec, code, folder):
    c = rec.get("product_colour", "")
    if " / " in c and "top:" in c.lower():
        top, bottom = (x.split(":", 1)[-1].strip() for x in c.split(" / ", 1))
        codes = [x.strip().upper() for x in re.split(r"\s*-\s*", folder)]
        typ = prods.get(pdf_code_for(code) or "", {}).get("Type", "")
        return bottom if (typ == "Bottom" or (codes and code == codes[-1] and len(codes) > 1 and typ != "Top")) else top
    return c

VIEWS = ["front", "three-quarter", "side", "back", "detail-close-up", "other"]
found = collections.defaultdict(lambda: {"photos": [], "views": collections.Counter()})
for r in recs:
    if not r.get("usable", True): continue
    for code in [x.strip().upper() for x in re.split(r"\s*-\s*", r["folder"])]:
        col = colour_for(r, code, r["folder"]).strip().lower()
        f = found[(code, col)]; f["photos"].append(r); f["views"][r.get("view", "other")] += 1
# match each found colourway to the PDF colour list of that product, by colour words (not by guessed hex)
RULES = [(r"off.?white|ivory", ["Off White", "White", "Cream"]), (r"cream", ["Cream", "Off White", "White", "Beige"]),
 (r"white", ["White", "Off White"]), (r"black", ["Black"]), (r"navy", ["Navy", "Dark Navy"]), (r"burgundy", ["Burgundy"]),
 (r"chocolate|mocha|chestnut", ["Brown", "Café", "Havana"]), (r"taupe", ["Café", "Mauve", "Gray"]),
 (r"camel", ["Camel", "Café", "Brown", "Beige"]), (r"oatmeal|beige|sand", ["Beige", "Light Beige", "Cream"]),
 (r"charcoal", ["Dark Gray", "Gray", "Black"]), (r"gr[ae]y|marl|heather", ["Gray", "Dark Gray"]),
 (r"mauve", ["Mauve", "Light Mauve", "Dark Mauve", "Rose"]), (r"purple", ["Purple", "Mauve", "Dark Mauve"]),
 (r"blush|pink", ["Rose", "Pink", "Dark Rose", "B.Rose", "Mauve"]), (r"turquoise|aqua", ["Aqua", "Turquoise"]),
 (r"denim|blue", ["Indigo", "Blue", "Dark Blue"]), (r"sage|olive", ["Olive", "Light Olive", "Dark Olive"]),
 (r"mustard|yellow", ["Mustard", "Lemon", "Canary"]), (r"brown", ["Brown", "Café", "Havana"])]
def candidates(seen):
    main = re.split(r"\s+with\s+|\s*/\s*", seen)[0]          # 'purple with black rib trim' -> 'purple'
    for rx, cands in RULES:
        if re.search(rx, main): return cands
    return []
cover = collections.defaultdict(list)
rows_found = []
taken = collections.defaultdict(set)
for (code, col), f in sorted(found.items(), key=lambda kv: -len(kv[1]["photos"])):
    pc = pdf_code_for(code); match, conf = "", ""
    if pc:
        pdfcols = [s["Colour"] for s in skus if s["Product code"] == pc]
        cands = [c for c in candidates(col) if c in pdfcols and c not in taken[pc]]
        if cands:
            match = cands[0]; conf = "same colour name" if candidates(col)[0] == match else "closest name in the PDF list: check by eye"
            taken[pc].add(match)
            cover[next(s["SKU ID"] for s in skus if s["Product code"] == pc and s["Colour"] == match)].append((code, col))
    links = " | ".join(f"https://drive.google.com/file/d/{p['id']}/view" for p in f["photos"][:8])
    rows_found.append({"Folder code": code, "PDF product": pc or "NOT IN PDF", "Colour seen in photos": col,
                       "Matched PDF colour": match or ("" if not pc else "not in the PDF colour list"), "Match": conf,
                       "Photos": len(f["photos"]), **{v: f["views"].get(v, 0) for v in VIEWS},
                       "Print": "; ".join(sorted({p.get("print", "") for p in f["photos"]}))[:80],
                       "Notes (sample)": "; ".join(sorted({p.get("notes", "")[:60] for p in f["photos"] if p.get("notes")}))[:200],
                       "Photo links (first 8)": links})
rows_found.sort(key=lambda r: (r["Folder code"], r["Colour seen in photos"]))
PRINTED = {"126/451A", "126/451B", "126/474", "126/433", "126/461", "5008"}   # 5008 is colour-blocked in the real photos
UNCERTAIN = {"126/427": "client folder '427-410-406' shows a kimono + trouser set; PDF 126/427 is a plain linen-blend cardigan. Confirm it is the same product."}
rows_sku = []
for s in skus:
    sid, pc = s["SKU ID"], s["Product code"]
    if sid in cover:
        st = "REAL PHOTOS (client catalogue folder)"
        det = "; ".join(f"{c} '{col}' ({len(found[(c, col)]['photos'])} photos)" for c, col in cover[sid])
    elif pc in PRINTED:
        st, det = "PRINT, no photo of this colourway: colour swatch only, no generated image", ""
    elif any(k[0] == key(pc) or k[0] == pc.upper() for k in found):
        st, det = "Product photographed, this colour not: recolour the real photo (solid)", ""
    else:
        st, det = "Product not in client folder: use Nov studio shoot if it has this colour, else recolour", ""
    rows_sku.append({"SKU ID": sid, "Product": pc, "Type": s["Type"], "Colour (PDF)": s["Colour"], "Status": st, "Real photos": det,
                     "Check": UNCERTAIN.get(pc, "colour-blocked in the real photos, not a solid colour" if pc == "5008" else "")})

# matched looks from the PDF (top + bottom pairs), with what the real photos cover and what the Excel says
src = open("studio/build_sku_db.py").read()
PAIRS = eval(src[src.index("PAIRS = [") + 8: src.index("NORM = {")].strip())
from studio.sheet import load_outfits
def xbase(c):
    c = re.sub(r"\(.*?\)", "", c).strip().upper(); c = re.sub(r"[ -](GREY|OFF[ -]WHITE|BLACK|BLUE)$", "", c)
    return c.replace("NO23", "N023").replace("/", "-").replace(" ", "-").replace("601-1", "601")
ex = collections.defaultdict(set)
for o in load_outfits("data/combinations.xlsx"): ex[xbase(o.top)].add(xbase(o.bottom))
def cols(pc): return [s["Colour"] for s in skus if s["Product code"] == pc]
def real(pc): return [s["Colour"] for s in skus if s["Product code"] == pc and s["SKU ID"] in cover]
rows_looks = []
for i, (t, b) in enumerate(PAIRS, 1):
    e = ex.get(xbase(t))
    agree = "not in the Excel" if e is None else ("same pairing as the Excel" if xbase(b) in e else "Excel pairs it with " + ", ".join(sorted(e)))
    rows_looks.append({"Look": i, "Top": t, "Bottom": b,
        "Top colours (PDF)": ", ".join(cols(t)), "Top colours with real photos": ", ".join(real(t)) or "none",
        "Bottom colours (PDF)": ", ".join(cols(b)), "Bottom colours with real photos": ", ".join(real(b)) or "none",
        "Excel": agree,
        "Styling rule": "Excel row for colour pairing and footwear" if e is not None and xbase(b) in e else "PDF pairing; neutral contrast bottom colour; white ballet flats"})

import openpyxl
from openpyxl.styles import Font, PatternFill
wb = openpyxl.Workbook(); wb.remove(wb.active)
summary = collections.Counter(r["Status"].split(":")[0].split(",")[0] for r in rows_sku)
tabs = [("Matched looks (PDF)", rows_looks), ("SKU coverage", rows_sku), ("Colourways in client photos", rows_found),
        ("Summary", [{"Status": k, "SKUs": v} for k, v in summary.most_common()])]
for t, rows in tabs:
    ws = wb.create_sheet(t); ws.append(list(rows[0]))
    for r in rows: ws.append(list(r.values()))
    for c in ws[1]: c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="333333")
    ws.freeze_panes = "A2"; ws.auto_filter.ref = ws.dimensions
    for col in ws.columns: ws.column_dimensions[col[0].column_letter].width = min(60, max(10, max(len(str(c.value or "")) for c in col) + 2))
wb.save(out)
print(len(recs), "photos;", len(found), "colourways;", dict(summary))
