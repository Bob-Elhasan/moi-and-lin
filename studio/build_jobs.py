"""Build data/jobs.json: one entry per sheet row x photoshoot pose."""
import csv, json, re, collections, openpyxl
from studio.generate import footwear_prompt

inv = collections.defaultdict(dict)  # barcode -> pose -> drive_id
for r in csv.DictReader(open("data/photoshoot_inventory.csv")):
    m = re.match(r"(\d{12})-Fullbody-JPG-(\d)", r["file"])
    if m and m.group(2) not in inv[m.group(1)]:
        inv[m.group(1)][m.group(2)] = r["drive_id"]

def clean(v):
    s = re.sub(r"\s+", " ", str(v or "")).strip()
    return "" if s.lower() == "none" else s

POSE = {"1": "front view", "2": "three-quarter view", "3": "back view"}
ws = openpyxl.load_workbook("data/combinations.xlsx").active
jobs, missing = [], []
for n, row in enumerate(ws.iter_rows(min_row=3, values_only=True), start=3):
    _, code, top, bottom, under, foot, bcol, tcol = (list(row) + [None] * 8)[:8]
    code, top, bottom = clean(code), clean(top), clean(bottom)
    if not top or not bottom:
        continue
    poses = inv.get(code, {})
    if not poses:
        missing.append({"row": n, "code": code, "top": top, "bottom": bottom})
        continue
    tcol, bcol, under = clean(tcol), clean(bcol), clean(under)
    for p in sorted(poses)[:3]:
        parts = [f"Edit this real e-commerce studio photo ({POSE.get(p, 'view')})."]
        if tcol:
            parts.append(f"Change the color of the top garment (product {top}) to {tcol}, keeping its exact cut, fabric texture, seams, buttons and details.")
        if bcol:
            parts.append(f"Change the bottom garment (product {bottom}) to {bcol}, keeping its exact cut and fabric.")
        if under:
            parts.append(f"Any undershirt is {under}.")
        parts.append(footwear_prompt(foot) + (" If feet are hidden, leave them." if p == "3" else ""))
        parts.append("Keep the woman, face, hair, body, pose, every other garment, the white studio background, lighting and framing exactly the same. Photorealistic.")
        jobs.append({"row": n, "code": code, "pose": p, "drive_id": poses[p], "top": top, "bottom": bottom,
                     "top_color": tcol, "bottom_color": bcol, "footwear": clean(foot), "prompt": " ".join(parts)})
json.dump(jobs, open("data/jobs.json", "w"), indent=1)
json.dump(missing, open("data/missing_shoots.json", "w"), indent=1)
print(len(jobs), "jobs,", len({j["code"] for j in jobs}), "barcodes,", len({j["drive_id"] for j in jobs}), "source photos;", len(missing), "rows missing")
