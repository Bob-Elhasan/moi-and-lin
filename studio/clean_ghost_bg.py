"""Neutralize grey-ish backgrounds on ghost mannequin shots: set the white point to the measured
background color (corner median), so the backdrop becomes #FFFFFF while garment shading is kept."""
import sys
from pathlib import Path
from PIL import Image
import statistics as st

def clean(p: Path):
    im = Image.open(p).convert("RGB"); w, h = im.size
    pts = [im.getpixel((x, y)) for x in (5, w // 4, w // 2, 3 * w // 4, w - 6) for y in (5, h // 6)]
    bg = [st.median(c[i] for c in pts) for i in range(3)]
    if min(bg) >= 250 or min(bg) < 200:
        return False
    lut = sum(([min(255, round(v * 255 / b)) for v in range(256)] for b in bg), [])
    im.point(lut).save(p, quality=93)
    return True

if __name__ == "__main__":
    fs = [f for a in sys.argv[1:] for f in Path(a).rglob("*.jpg")]
    n = sum(clean(f) for f in fs)
    print(f"adjusted {n} of {len(fs)}")
