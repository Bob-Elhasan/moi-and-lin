"""Rebuild data/drive/index.csv + open_defects.csv from the Drive id maps and sync logs."""
import csv, glob, json, re
from pathlib import Path

files = {}  # drive id -> [filename, viewUrl]
for f in sorted(glob.glob("data/drive/*_ids.json")):
    for name, v in json.load(open(f))["files"].items():
        files[v["id"]] = [name, v["viewUrl"]]
for i in (1, 2, 3):
    ops = json.load(open(f"data/drive/sync_ops_{i}.json"))
    done = json.load(open(f"data/drive/sync_done_{i}.json"))
    ok_up = {d["title"]: d for d in done if d["op"] == "upload" and d.get("status") == "ok"}
    ok_id = {(d["op"], d["id"]) for d in done if d["op"] != "upload" and d.get("status") == "ok"}
    for op in ops:
        d = ok_up.get(op["title"]) if op["op"] == "upload" else ((op["op"], op["id"]) in ok_id or None)
        if not d: print("NOT DONE", op["op"], op["title"]); continue
        if op["op"] == "trash": files.pop(op["id"], None)
        elif op["op"] == "upload":
            files[d["id"]] = [op["title"], d.get("viewUrl") or f"https://drive.google.com/file/d/{d['id']}/view"]
        else: files[op["id"]][0] = op["title"]
for f in sorted(glob.glob("data/drive/crop_done_*.json")) + sorted(glob.glob("data/drive/pose_done_*.json")):
    for d in json.load(open(f)):
        if d.get("status") == "ok": files[d["id"]] = [d["title"], d["viewUrl"]]
names = [n for n, _ in files.values()]
dup = {n for n in names if names.count(n) > 1}
if dup: print("DUPLICATE NAMES ON DRIVE", sorted(dup))
url = {n: u for n, u in files.values()}

local = {p.name for p in Path("output").rglob("*.jpg") if "_up" not in p.parts and "_up2" not in p.parts and "_fix" not in p.parts and "SKU Colors 2026" not in p.parts}
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
FOLD = {}
for _f in glob.glob("data/drive/*_ids.json"): FOLD.update(json.load(open(_f))["folders"])
_clean = lambda seg: re.sub(r"\s*/\s*", "-", seg).strip()
furl = lambda i: f"https://drive.google.com/drive/folders/{i}" if i else ""
def onmodel_folder(j):
    parts = j["folder"].split("/")                   # On-Model/<look>/<colour, may contain '/'>
    return FOLD.get(f"{_clean(parts[1])}/{_clean('/'.join(parts[2:]))}")
def ghost_folder(kind, code, color):
    c = (color or "Original")
    for g in ghost:
        if g["kind"] == kind and g["code"] == code and g["color"].lower() == c.lower():
            parts = g["folder"].split("/")           # Ghost Mannequin/TOP x/colour
            return FOLD.get(f"{_clean(parts[1])}/{_clean('/'.join(parts[2:]))}")
    return None
misses = []
rows = []
for j in jobs:
    pre = f"_r{int(j['row']):03d}_"
    mine = sorted(n for n in local if pre in n and not n.startswith("ghost_"))
    def pick(*keys):
        return " | ".join(url.get(n, "NOT ON DRIVE") for n in mine if any(k in n for k in keys))
    fo, gt, gb = onmodel_folder(j), ghost_folder("top", j["top"], j["top_color"]), ghost_folder("bottom", j["bottom"], j["bottom_color"])
    if not (fo and gt and gb): misses.append((j["row"], bool(fo), bool(gt), bool(gb)))
    mk = lambda i, label: f'=HYPERLINK("{furl(i)}","{label}")' if i else "NO FOLDER FOUND"
    r = {"Excel row": j["row"], "Barcode": f'="{j["code"]}"', "Top": j["top"], "Bottom": j["bottom"],
         "Top color": j["top_color"], "Bottom color": j["bottom_color"], "Footwear": j["footwear"],
         "All photos of this look (folder)": mk(fo, "Open folder"),
         "Ghost mannequin top (folder)": mk(gt, "Open folder"), "Ghost mannequin bottom (folder)": mk(gb, "Open folder"),
         "Front": pick("_01-"), "Three-quarter / detail": pick("_02-"), "Back / side": pick("_03-"),
         "Editorial front": pick("_04-"), "Editorial back": pick("_05-") or "not generated yet",
         "Detail crop top (real photo)": pick("_06-"), "Detail crop bottom (real photo)": pick("_07-"),
         "Detail pose (AI-generated)": pick("_08-")}
    for kind, code, color in (("top", j["top"], j["top_color"]), ("bottom", j["bottom"], j["bottom_color"])):
        for side in ("front", "back"):
            r[f"Ghost {kind} {side}"] = gurl(kind, code, color, side)
    rows.append(r)
json.dump({"rows": rows, "url": url}, open("data/drive/index_data.json", "w"), indent=1)
with open("data/drive/index.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(len(rows), "rows;", "rows with a missing folder:", misses[:10], len(misses))
