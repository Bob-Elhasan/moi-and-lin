"""Close-up detail crops cut from the real (retouched) front studio photo. No generation.
  <base>_06-detail-top.jpg     chin to hips
  <base>_07-detail-bottom.jpg  waist to feet
They inherit the 'composite' IPTC tag of the photo they are cut from."""
import json, re, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image

OUT = (1200, 1800)

def bbox(im):
    """Figure box + horizontal center (median of the torso mass, robust to stray edge pixels)."""
    a = np.asarray(im.convert("RGB").resize((im.width // 4, im.height // 4))).astype(int)
    m = (a.min(2) < 228) | ((a.max(2) - a.min(2)) > 22)
    rows = np.where(m.sum(1) > m.shape[1] * 0.03)[0]
    y0, y1 = rows[0], rows[-1]; H = y1 - y0
    band = m[int(y0 + 0.2 * H): int(y0 + 0.6 * H)].sum(0).astype(float)
    cs = np.cumsum(band); cx = int(np.searchsorted(cs, cs[-1] / 2))
    return cx * 4, y0 * 4, y1 * 4

def crop(im, cx, y0, y1):
    h = y1 - y0; w = h * 2 / 3
    x0 = min(max(cx - w / 2, 0), im.width - w)
    return im.crop((int(x0), int(y0), int(x0 + w), int(y1))).resize(OUT, Image.LANCZOS)

def run(front: Path):
    im = Image.open(front).convert("RGB")
    cx, y0, y1 = bbox(im); H = y1 - y0
    base = re.sub(r"_0[12]-[a-z-]+\.jpg$", "", front.name)
    made = []
    for name, a, b in (("06-detail-top", 0.11, 0.62), ("07-detail-bottom", 0.44, 0.985)):
        o = front.parent / f"{base}_{name}.jpg"
        crop(im, cx, y0 + a * H, min(y0 + b * H, im.height)).save(o, quality=93)
        made.append(o)
    return made

if __name__ == "__main__":
    # Rows whose 01 file is not a usable full-body front: crop from the 02 shot, or skip.
    USE_02, SKIP = {68, 70, 71, 72}, {148}
    row = lambda f: int(re.search(r"_r(\d+)_", f.name).group(1))
    for old in Path("output/On-Model").rglob("*_0[67]-detail-*.jpg"): old.unlink()
    fronts = sorted(f for f in Path("output/On-Model").rglob("*_0[12]-*.jpg")
                    if row(f) not in SKIP and (f.name.split(f"_r{row(f):03d}_")[1][:2] == ("02" if row(f) in USE_02 else "01")))
    made = [m for f in fronts for m in run(f)]
    subprocess.run([sys.executable, "-m", "studio.tag_metadata", *map(str, made)], check=True)
    json.dump([str(m) for m in made], open("data/results/detail_crops.json", "w"), indent=1)
    print(len(fronts), "fronts ->", len(made), "crops")
