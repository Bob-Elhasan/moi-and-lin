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
# match each found colourway to the nearest PDF colour of that product
cover = collections.defaultdict(list)    # SKU ID -> [(code,col)]
rows_found = []
for (code, col), f in sorted(found.items()):
    pc = pdf_code_for(code); match = ""
    if pc:
        hx, _ = name_hex(col)
        cands = [s for s in skus if s["Product code"] == pc]
        if hx and cands:
            best = min(cands, key=lambda s: dist(hx, PALETTE.get(s["Colour"], "#808080")))
            if dist(hx, PALETTE.get(best["Colour"], "#808080")) < 60 ** 2 * 3:
                match = best["Colour"]; cover[best["SKU ID"]].append((code, col))
    links = " | ".join(f"https://drive.google.com/file/d/{p['id']}/view" for p in f["photos"][:8])
    rows_found.append({"Folder code": code, "PDF product": pc or "NOT IN PDF", "Colour seen in photos": col,
                       "Matched PDF colour": match or ("" if not pc else "no close PDF colour"),
                       "Photos": len(f["photos"]), **{v: f["views"].get(v, 0) for v in VIEWS},
                       "Print": "; ".join(sorted({p.get("print", "") for p in f["photos"]}))[:80],
                       "Notes (sample)": "; ".join(sorted({p.get("notes", "")[:60] for p in f["photos"] if p.get("notes")}))[:200],
                       "Photo links (first 8)": links})
PRINTED = {"126/451A", "126/451B", "126/474", "126/433", "126/461"}
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
    rows_sku.append({"SKU ID": sid, "Product": pc, "Type": s["Type"], "Colour (PDF)": s["Colour"], "Status": st, "Real photos": det})

import openpyxl
from openpyxl.styles import Font, PatternFill
wb = openpyxl.Workbook(); wb.remove(wb.active)
summary = collections.Counter(r["Status"].split(":")[0].split(",")[0] for r in rows_sku)
tabs = [("SKU coverage", rows_sku), ("Colourways in client photos", rows_found),
        ("Summary", [{"Status": k, "SKUs": v} for k, v in summary.most_common()])]
for t, rows in tabs:
    ws = wb.create_sheet(t); ws.append(list(rows[0]))
    for r in rows: ws.append(list(r.values()))
    for c in ws[1]: c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="333333")
    ws.freeze_panes = "A2"; ws.auto_filter.ref = ws.dimensions
    for col in ws.columns: ws.column_dimensions[col[0].column_letter].width = min(60, max(10, max(len(str(c.value or "")) for c in col) + 2))
wb.save(out)
print(len(recs), "photos;", len(found), "colourways;", dict(summary))
