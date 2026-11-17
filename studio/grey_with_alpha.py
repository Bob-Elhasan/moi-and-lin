"""Grey backdrop using an AI cut-out (alpha) to protect the subject; the backdrop is recolored
the same way as studio.grey_bg (multiply to target, shadows kept).
Usage: python3 -m studio.grey_with_alpha <src.jpg> <cutout.png> <dst.jpg> [hex=EEEEEE]"""
import sys, subprocess
import numpy as np
from PIL import Image, ImageFilter

def run(src, cut, dst, hexcol="EEEEEE"):
    im = Image.open(src).convert("RGB")
    c = Image.open(cut)
    alpha = (c.getchannel("A") if "A" in c.getbands() else c.convert("L")).resize(im.size, Image.LANCZOS)
    alpha = alpha.filter(ImageFilter.GaussianBlur(1.5))
    a = np.asarray(im).astype(np.float32)
    k = 1.0 - np.asarray(alpha).astype(np.float32)[..., None] / 255.0       # 1 = backdrop
    bgpx = a[k[..., 0] > 0.98]
    bg = np.median(bgpx[bgpx.min(1) >= 200], axis=0) if len(bgpx) else np.array([255, 255, 255], np.float32)
    t = np.array([int(hexcol[i:i + 2], 16) for i in (0, 2, 4)], np.float32)
    out = a * (1 - k) + np.clip(a * (t / np.maximum(bg, 1)), 0, 255) * k
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(dst, quality=93)
    subprocess.run([sys.executable, "-m", "studio.tag_metadata", dst], check=True, capture_output=True)

if __name__ == "__main__":
    run(*sys.argv[1:4], *(sys.argv[4:5] or ["EEEEEE"]))
