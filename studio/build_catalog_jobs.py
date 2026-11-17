"""Build catalog jobs (v3): light retouch of the REAL shoot, 3 original poses per row.

Per row, shot 01-front is generated first; 02-three-quarter and 03-back then use the
front RESULT as a second reference so face, eyes, makeup, hair and garment color match.

Folder: On-Model/TOP <top> + BOTTOM <bottom>/<Top color>[ - <Bottom color>]/
File:   <barcode>_<top>_<bottom>_<top-color>[_<bottom-color>]_r<row>_<NN-shot>.jpg
"""
import json, re
from studio.generate import footwear_prompt

def slug(s): return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

BEAUTY = ("MAKEUP: remove any dark or smoky eye makeup completely: no dark eyeshadow, no black eyeliner, no smudged liner under "
          "the eyes, no dark circles. Clean 'no-makeup' fashion-model look: bare-looking soft eyelids in a light neutral tone, a touch "
          "of soft brown mascara, natural groomed brows, fresh nude-pink lips, light natural blush. No shine, no highlighter, no contouring. "
          "SKIN: smoother, even, luminous but matte, softened under-eye area, fine natural skin texture kept (no plastic, no blur). "
          "Hair neat and glossy. ")
NATURAL = (BEAUTY + "Pure white background, same soft studio light. Looks like a real photo from a premium brand catalog "
           "(COS, Massimo Dutti), indistinguishable from an untouched real photograph.")

def front_prompt(m, outfit):
    return ("Light professional retouch of this real fashion e-commerce photo, like a high-end retoucher would do. "
            "Keep the SAME real woman and her identity. Refine subtly: balance eye symmetry (both eyes equally open, same size "
            "and level, irises centered, gaze direct), even and harmonious facial features, without changing her face shape or "
            "who she is. Calm, confident, relaxed fashion-model expression, lips softly closed. Relax the shoulders and hands very "
            f"slightly; same pose, framing and camera angle. {outfit} {footwear_prompt(m['footwear'])} "
            "Keep every garment's exact cut, fabric weave, seams, stitching and buttons. " + NATURAL)

def follow_prompt(view):
    if view == "back view":
        return ("Image 1 is a real fashion e-commerce photo (back view) to retouch. Image 2 is the approved retouched front shot of "
                "the same woman in the same outfit. Keep image 1's pose, framing and camera angle exactly. Match the hair color and "
                "texture and every garment's color, fabric and details exactly to image 2; if feet are visible they wear the same "
                "shoes as image 2. " + NATURAL)
    return (f"Image 1 is a real fashion e-commerce photo ({view}) to retouch. Image 2 is the approved retouched front shot of the "
            "same woman in the same outfit. Retouch image 1 so her face, eyes (balanced symmetry, same eye shape and color), brows, "
            "lips, skin tone, makeup and hair match image 2 exactly, as the same person photographed from this angle. Match every "
            "garment's color, fabric, details and the shoes exactly to image 2. Keep image 1's pose, framing and camera angle; relax "
            "shoulders and hands very slightly. Calm, confident fashion-model expression. " + NATURAL)

media = json.load(open("data/media_map.json"))
rows = {}
for j in json.load(open("data/jobs.json")):
    rows.setdefault(j["row"], {"m": j, "p": {}})["p"][j["pose"]] = media[j["drive_id"]]

out = []
for row, d in sorted(rows.items()):
    m, p = d["m"], d["p"]
    outfit = ""
    if m["top_color"]: outfit += f"Change the top garment (product {m['top']}) to {m['top_color']}. "
    if m["bottom_color"]: outfit += f"Change the bottom garment (product {m['bottom']}) to {m['bottom_color']}. "
    color_part = slug(m["top_color"] or "original") + (f"_{slug(m['bottom_color'])}" if m["bottom_color"] else "")
    base = f"{m['code']}_{slug(m['top'])}_{slug(m['bottom'])}_{color_part}_r{row:03d}"
    shots = [{"shot": "01-front", "source": p.get("1") or next(iter(p.values())), "prompt": front_prompt(m, outfit)}]
    if "2" in p: shots.append({"shot": "02-three-quarter", "source": p["2"], "prompt": follow_prompt("three-quarter view")})
    if "3" in p: shots.append({"shot": "03-back", "source": p["3"], "prompt": follow_prompt("back view")})
    out.append({"row": row, "code": m["code"], "top": m["top"], "bottom": m["bottom"], "top_color": m["top_color"],
                "bottom_color": m["bottom_color"], "footwear": m["footwear"],
                "folder": f"On-Model/TOP {m['top']} + BOTTOM {m['bottom']}/{m['top_color'] or 'Original'}"
                          + (f" - {m['bottom_color']}" if m["bottom_color"] else ""),
                "shots": [dict(s, file=f"{base}_{s['shot']}.jpg") for s in shots]})
json.dump(out, open("data/catalog_jobs.json", "w"), indent=1)
n = len(out)
for i in range(3):
    json.dump(out[i * n // 3:(i + 1) * n // 3], open(f"data/catalog_part{i+1}.json", "w"), indent=1)
print(n, "rows,", sum(len(r["shots"]) for r in out), "shots")
