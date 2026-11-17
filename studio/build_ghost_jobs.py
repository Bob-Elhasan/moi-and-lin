"""Ghost mannequin (invisible mannequin) front + back for every top color and bottom color in the sheet.
Folder: Ghost Mannequin/TOP <code>/<color>/   File: ghost_top_<code>_<color>_front.jpg
"""
import json, re
def slug(s): return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
media = json.load(open("data/media_map.json"))
rows = {}
for j in json.load(open("data/jobs.json")):
    rows.setdefault(j["row"], {"m": j, "p": {}})["p"][j["pose"]] = media[j["drive_id"]]

GHOST = ("Professional ghost mannequin (invisible mannequin) e-commerce product photo. Remove the model completely: "
         "only the garment, shown as if worn by an invisible body, with natural 3D volume and shape. {view} "
         "Keep the garment exactly as in the reference: cut, length, proportions, fabric weave and texture, seams, stitching, "
         "buttons, pockets, trims and drape. No mannequin, no hanger, no body parts, no other garments. "
         "Pure white seamless background (#FFFFFF), soft even studio lighting, subtle natural shadow, centered, sharp, "
         "true-to-life color. Must look like a real product photograph, not AI.")
FRONT = "Front view, symmetrical. Where the neck/waist opening is, show the inside back of the garment (the hollow interior), as in real ghost mannequin photos."
BACK = "Back view, symmetrical, showing the back of the garment exactly; infer only what the reference back photo shows."

seen, out = set(), []
for row, d in sorted(rows.items()):
    m = d["m"]
    for kind, code, color in (("top", m["top"], m["top_color"]), ("bottom", m["bottom"], m["bottom_color"])):
        key = (kind, code, color.lower())
        if key in seen: continue
        seen.add(key)
        label = "top garment (upper body piece)" if kind == "top" else "bottom garment (trousers / skirt / jeans)"
        col = f" in the color {color}" if color else " in its original color"
        for side, pose, view in (("front", "1", FRONT), ("back", "3", BACK)):
            src = d["p"].get(pose) or d["p"].get("1")
            out.append({"kind": kind, "code": code, "color": color or "Original", "side": side, "row": row,
                        "media_id": src,
                        "folder": f"Ghost Mannequin/{kind.upper()} {code}/{color or 'Original'}",
                        "file": f"ghost_{kind}_{slug(code)}_{slug(color or 'original')}_{side}.jpg",
                        "prompt": f"Isolate ONLY the {label} (product {code}) from the reference photo{col}. " + GHOST.format(view=view)})
json.dump(out, open("data/ghost_jobs.json", "w"), indent=1)
h = len(out) // 2
json.dump(out[:h], open("data/ghost_part1.json", "w"), indent=1); json.dump(out[h:], open("data/ghost_part2.json", "w"), indent=1)
print(len(out), "ghost shots;", len({o['file'] for o in out}), "unique")
