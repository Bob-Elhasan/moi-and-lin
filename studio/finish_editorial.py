"""Post-process one ElevenLabs result: upscale to 1696x2528, white-point fix, JPEG, IPTC tags.
Usage: python3 -m studio.finish_editorial <png_in> <jpg_out>"""
import sys, subprocess
from PIL import Image
from studio.clean_ghost_bg import clean
src, dst = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("RGB").resize((1696, 2528), Image.LANCZOS)
im.save(dst, quality=93)
from pathlib import Path
clean(Path(dst))
subprocess.run([sys.executable, "-m", "studio.tag_metadata", dst], check=True)
