"""Finish a re-rolled image.
 on-model: python3 -m studio.finish_fix onmodel <png> <out.jpg>
 ghost pair (front|back side by side): python3 -m studio.finish_fix ghost <png> <out_front.jpg> <out_back.jpg>
Writes to a staging copy under fix_staging/ (same relative path) so originals stay until approved."""
import sys, os, subprocess
from PIL import Image, ImageChops

def stage(p):
    q = p.replace("output/", "fix_staging/", 1); os.makedirs(os.path.dirname(q), exist_ok=True); return q

def tag(p): subprocess.run([sys.executable, "-m", "studio.tag_metadata", p], check=True, capture_output=True)

def fit(im, size=(1856, 2304)):
    bg = Image.new("RGB", im.size, (255, 255, 255))
    box = ImageChops.difference(im, bg).convert("L").point(lambda v: 255 if v > 12 else 0).getbbox() or (0, 0, *im.size)
    c = im.crop(box); s = min(size[0] * 0.86 / c.width, size[1] * 0.86 / c.height)
    c = c.resize((int(c.width * s), int(c.height * s)), Image.LANCZOS)
    out = Image.new("RGB", size, (255, 255, 255)); out.paste(c, ((size[0] - c.width) // 2, (size[1] - c.height) // 2)); return out

mode, src = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("RGB")
if mode == "onmodel":
    o = stage(sys.argv[3]); im.resize((1696, 2528), Image.LANCZOS).save(o, quality=93); tag(o); print(o)
else:
    w, h = im.size
    for half, dst in ((im.crop((0, 0, w // 2, h)), sys.argv[3]), (im.crop((w // 2, 0, w, h)), sys.argv[4])):
        o = stage(dst); fit(half).save(o, quality=93); tag(o); print(o)
