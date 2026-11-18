"""Rebuild data/drive/index.csv + open_defects.csv from the Drive id maps and sync logs."""
import csv, glob, json, re
from pathlib import Path

url = {}   # filename -> viewUrl
byid = {}  # drive id -> filename
for f in sorted(glob.glob("data/drive/*_ids.json")):
    for name, v in json.load(open(f))["files"].items():
        url[name] = v["viewUrl"]; byid[v["id"]] = name
for i in (1, 2, 3):
    ops = json.load(open(f"data/drive/sync_ops_{i}.json"))
    done = json.load(open(f"data/drive/sync_done_{i}.json"))
    for op, d in zip(ops, done):
        if d.get("status") != "ok": continue
        if op["op"] == "trash":
            n = byid.pop(op["id"], None)
            if n and url.get(n, "").find(op["id"]) >= 0: url.pop(n)
        elif op["op"] == "upload":
            url[op["title"]] = d.get("viewUrl") or f"https://drive.google.com/file/d/{d['id']}/view"
            byid[d["id"]] = op["title"]
        elif op["op"] == "rename":
            old = byid.get(op["id"])
            if old and old in url: url[op["title"]] = url.pop(old)
            byid[op["id"]] = op["title"]

local = {p.name for p in Path("output").rglob("*.jpg") if "_up" not in p.parts and "_fix" not in p.parts}
missing = sorted(local - set(url)); extra = sorted(set(url) - local)
print(len(local), "local,", len(url), "on drive,", len(missing), "not on drive,", len(extra), "drive-only")
for m in missing[:15]: print("  missing", m)
for m in extra[:15]: print("  extra", m)

slug = lambda s: re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
jobs = json.load(open("data/catalog_jobs.json"))
ghost = json.load(open("data/ghost_jobs.json"))
gfile = {(g["kind"], g["code"], g["color"].lower(), g["side"]): g["file"] for g in ghost}
def gurl(kind, code, color, side):
    n = gfile.get((kind, code, (color or "Original").lower(), side))
    return url.get(n, "NOT ON DRIVE" if n else "") if n else ""
rows = []
for j in jobs:
    pre = f"_r{int(j['row']):03d}_"
    mine = sorted(n for n in local if pre in n and not n.startswith("ghost_"))
    def pick(*keys):
        return " | ".join(url.get(n, "NOT ON DRIVE") for n in mine if any(k in n for k in keys))
    r = {"Excel row": j["row"], "Barcode": f'="{j["code"]}"', "Top": j["top"], "Bottom": j["bottom"],
         "Top color": j["top_color"], "Bottom color": j["bottom_color"], "Footwear": j["footwear"],
         "Front": pick("_01-"), "Three-quarter / detail": pick("_02-"), "Back / side": pick("_03-"),
         "Editorial front": pick("_04-"), "Editorial back": pick("_05-") or "not generated yet"}
    for kind, code, color in (("top", j["top"], j["top_color"]), ("bottom", j["bottom"], j["bottom_color"])):
        for side in ("front", "back"):
            r[f"Ghost {kind} {side}"] = gurl(kind, code, color, side)
    rows.append(r)
json.dump({"rows": rows, "url": url}, open("data/drive/index_data.json", "w"), indent=1)
with open("data/drive/index.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(len(rows), "rows")
