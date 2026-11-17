"""Build data/catalog_jobs.json: 3 catalog shots per sheet row, from that row's real shoot.

Naming convention (file):  <barcode>_<TOP>_<BOTTOM>_<top-color>[_<bottom-color>]_r<row>_<NN-shot>.jpg
Folder:                    TOP <top> + BOTTOM <bottom>/<Top color>[ - <Bottom color>]/
"""
import json, re
from studio.generate import footwear_prompt

def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

QUALITY = (
    "This must look like a real photograph from a professional fashion e-commerce studio shoot, not AI: "
    "natural skin texture with visible pores, no plastic smoothing, real hair strands, true-to-life fabric texture, "
    "weave, seams, stitching and buttons exactly as in the reference, accurate garment length and fit, natural fabric folds. "
    "Same woman as the reference (same face, hair and body), relaxed confident expression with a soft natural closed-mouth smile, "
    "natural minimal makeup: fresh even skin, light blush, nude lips, soft brows, no heavy eyeliner. "
    "Pure white seamless background (#FFFFFF), soft diffused studio lighting with a gentle natural floor shadow, "
    "85mm lens, full body head to toe, centered, 2:3 vertical. Premium website catalog quality."
)
SHOTS = [
    ("01-front", "1", "Pose: front view, standing relaxed with weight on one leg, one hand casually in the trouser pocket or lightly at the waist, the other arm relaxed, slight head tilt, looking at the camera."),
    ("02-three-quarter", "2", "Pose: three-quarter view, standing naturally and at ease, shoulders relaxed, arms soft, gaze slightly off camera."),
    ("03-walking", "1", "Pose: natural mid-step walk toward the camera at a slight angle, arms swinging gently, garments moving naturally, glancing at the camera."),
]

media = json.load(open("data/media_map.json"))
inv = {}
for j in json.load(open("data/jobs.json")):
    inv.setdefault((j["row"]), {"meta": j, "poses": {}})["poses"][j["pose"]] = j["drive_id"]

out = []
for row, d in sorted(inv.items()):
    m = d["meta"]
    outfit = []
    outfit.append(f"the top (product {m['top']})" + (f" recolored to {m['top_color']}" if m["top_color"] else ""))
    outfit.append(f"the bottom (product {m['bottom']})" + (f" in {m['bottom_color']}" if m["bottom_color"] else ""))
    color_part = slug(m["top_color"] or "original") + (f"_{slug(m['bottom_color'])}" if m["bottom_color"] else "")
    folder = f"TOP {m['top']} + BOTTOM {m['bottom']}/{m['top_color'] or 'Original'}" + (f" - {m['bottom_color']}" if m["bottom_color"] else "")
    for shot, pose, pose_txt in SHOTS:
        src = d["poses"].get(pose) or next(iter(d["poses"].values()))
        prompt = (f"Use the reference photo for the exact garments and the model's identity. Show her wearing the same outfit: "
                  f"{' and '.join(outfit)}, plus every other garment exactly as in the reference. "
                  f"{footwear_prompt(m['footwear'])} {pose_txt} {QUALITY}")
        out.append({"row": row, "code": m["code"], "top": m["top"], "bottom": m["bottom"], "top_color": m["top_color"],
                    "bottom_color": m["bottom_color"], "footwear": m["footwear"], "shot": shot, "media_id": media[src],
                    "folder": folder,
                    "file": f"{m['code']}_{slug(m['top'])}_{slug(m['bottom'])}_{color_part}_r{row:03d}_{shot}.jpg",
                    "prompt": prompt})
json.dump(out, open("data/catalog_jobs.json", "w"), indent=1)
for i in range(3):
    json.dump(out[i::3] if False else out[i * len(out) // 3:(i + 1) * len(out) // 3], open(f"data/catalog_part{i+1}.json", "w"), indent=1)
print(len(out), "shots,", len({o['file'] for o in out}), "unique names")
print(out[0]["folder"], "/", out[0]["file"])
