"""Generate one on-model photo per SKU with the Gemini API (OpenAI-compatible endpoint, key injected by the proxy).
  python -m studio.sku_photos --dry-run --limit 3       # show prompts only
  python -m studio.sku_photos --limit 5                 # test run
  python -m studio.sku_photos                           # everything that is ready (resumable)
Options: --model gemini-2.5-flash-image | gemini-3-pro-image-preview, --only <SKU ID>, --workers 3"""
import argparse, base64, io, json, os, re, subprocess, sys, time, concurrent.futures as cf
from pathlib import Path
import requests
from PIL import Image

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
OUT = Path("output/SKU Photos 2026")
COST = {"gemini-2.5-flash-image": 0.039, "gemini-3-pro-image-preview": 0.134, "gemini-3.1-flash-image-preview": 0.067}

def footwear(v):
    v = (v or "White Balerina").lower().replace("sheakers", "sneakers").replace(" or shoes", "")
    color = next((c for c in ("black", "white", "brown", "beige", "cream", "navy") if c in v), "white")
    if "sneaker" in v or "shoes" in v or "clean" in v:
        shoe = f"clean minimal {color} leather low-top sneakers with flat soles"
    else:
        shoe = f"closed-toe {color} leather ballet flats: round toe, completely flat sole, no heel, no straps, toes fully covered"
    return f"Footwear: {shoe}. Both feet fully visible and correctly proportioned. Never sandals, heels or open toes."

def prompt(j):
    L = ["Image 1 is our model, photographed in our studio. Dress HER, the same woman, in the outfit below and change nothing else.",
         "Keep her face, eye colour, eyebrows, hair, skin tone, body, pose, camera angle, framing, the seamless white studio and the soft lighting EXACTLY as in image 1. "
         "Do not beautify, slim or age her. No added makeup, natural and minimal."]
    n = 2
    if j["type"] == "Bottom":
        L.append(f"Bottom (image {n}): {j['code']} in {j['colour']} ({j['hex']}). Use exactly the garment in image {n}: cut, length, fabric, pockets, seams and details, in exactly that colour."); n += 1
        if j.get("top_ref"):
            L.append(f"Top (image {n}): {j['top']} in {j['top_colour']}. Use exactly the garment in image {n}."); n += 1
    else:
        kind = "Dress" if j["type"] == "Dress" else "Top"
        extra = "" if j["garment_ref_kind"] == "colour-exact cut-out" else f" The garment in image {n} is shown in a different colour: recolour it to exactly {j['colour']} ({j['hex']}) and keep everything else about it."
        L.append(f"{kind} (image {n}): {j['code']} in {j['colour']} ({j['hex']}). Use exactly the garment in image {n}: cut, length, fabric, buttons, seams and details, in exactly that colour.{extra}"); n += 1
        if j["type"] == "Top" and j.get("bottom"):
            if j.get("bottom_ref"):
                col = "keep its original colour" if j.get("bottom_original") else f"in {j['bottom_colour']}"
                L.append(f"Bottom (image {n}): {j['bottom']}, {col}. Use exactly the garment in image {n}."); n += 1
            else:
                L.append(f"Bottom: plain wide-leg trousers in {j['bottom_colour']}.")
    if j.get("undershirt"): L.append(f"Add a plain {j['undershirt'].lower()} undershirt under the top.")
    L.append(footwear(j.get("footwear")))
    L.append("Photorealistic, sharp, true-to-life colours, real fabric texture, no text, no watermark, no extra people.")
    return "\n".join(L)

def refs(j):
    r = [j["model"]]
    if j["type"] == "Bottom": r += [j["garment_ref"], j.get("top_ref")]
    else: r += [j["garment_ref"], j.get("bottom_ref") if j["type"] == "Top" and j.get("bottom") else None]
    return [x for x in r if x]

def b64(path, maxside=1280):
    im = Image.open(path).convert("RGB"); im.thumbnail((maxside, maxside))
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

def extract_image(resp):
    m = resp["choices"][0]["message"]
    for im in m.get("images") or []:
        u = (im.get("image_url") or {}).get("url") or im.get("url", "")
        if u.startswith("data:"): return base64.b64decode(u.split(",", 1)[1])
    c = m.get("content")
    if isinstance(c, list):
        for p in c:
            u = (p.get("image_url") or {}).get("url", "") if isinstance(p, dict) else ""
            if u.startswith("data:"): return base64.b64decode(u.split(",", 1)[1])
    if isinstance(c, str):
        mm = re.search(r"data:image/[a-z]+;base64,([A-Za-z0-9+/=]+)", c)
        if mm: return base64.b64decode(mm.group(1))
    return None

def out_path(j):
    return OUT / f"{j['type'].upper()} {j['code'].replace('/', '-')}" / j["colour"] / f"{j['sku']}_model-front.jpg"

def run_one(j, model, tries=3):
    p = out_path(j)
    if p.exists(): return j["sku"], "exists", 0.0
    content = [{"type": "text", "text": prompt(j)}] + [{"type": "image_url", "image_url": {"url": b64(x)}} for x in refs(j)]
    body = {"model": model, "messages": [{"role": "user", "content": content}]}
    for t in range(tries):
        try:
            r = requests.post(ENDPOINT, json=body, timeout=240)
            if r.status_code == 402: return j["sku"], "STOP: credits depleted (402)", 0.0
            if r.status_code == 429: time.sleep(20 * (t + 1)); continue
            r.raise_for_status()
            img = extract_image(r.json())
            if img is None: return j["sku"], "no image in response: " + json.dumps(r.json())[:200], 0.0
            p.parent.mkdir(parents=True, exist_ok=True); Image.open(io.BytesIO(img)).convert("RGB").save(p, quality=93)
            return j["sku"], "ok", COST.get(model, 0.05)
        except Exception as e:
            err = str(e)[:200]; time.sleep(5 * (t + 1))
    return j["sku"], "failed: " + err, 0.0

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--model", default="gemini-2.5-flash-image"); ap.add_argument("--limit", type=int)
    ap.add_argument("--only"); ap.add_argument("--workers", type=int, default=3); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--budget", type=float, default=10.0)
    a = ap.parse_args()
    jobs = [j for j in json.load(open("data/sku_photo_jobs.json")) if not j["blocked_by"] and (not a.only or j["sku"] == a.only)]
    jobs = [j for j in jobs if not out_path(j).exists()][: a.limit]
    if a.dry_run:
        for j in jobs: print("=" * 70, j["sku"], "|", j["style_source"], "\nrefs:", refs(j), "\n" + prompt(j))
        print(len(jobs), "photos, est. cost $%.2f" % (len(jobs) * COST.get(a.model, 0.05))); sys.exit()
    spent, log, stop = 0.0, [], False
    with cf.ThreadPoolExecutor(a.workers) as ex:
        for sku, status, cost in ex.map(lambda j: run_one(j, a.model), jobs):
            spent += cost; log.append({"sku": sku, "status": status, "cost": cost}); print(sku, status, "spent $%.2f" % spent, flush=True)
            if status.startswith("STOP") or spent >= a.budget: print("stopping"); break
    json.dump(log, open("data/results/sku_photos_log.json", "w"), indent=1)
    done = [str(out_path(j)) for j in jobs if out_path(j).exists()]
    if done: subprocess.run([sys.executable, "-m", "studio.tag_metadata", *done], check=True)
