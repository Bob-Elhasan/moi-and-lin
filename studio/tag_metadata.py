"""Write IPTC / XMP AI-disclosure metadata into generated images (requires exiftool).

On-model retouches of a real photo  -> compositeWithTrainedAlgorithmicMedia
Ghost mannequins (fully synthesized) -> trainedAlgorithmicMedia
Usage: python -m studio.tag_metadata output/
"""
import subprocess, sys
from pathlib import Path

BASE = "http://cv.iptc.org/newscodes/digitalsourcetype/"
import os
BRAND = os.environ.get("BRAND_NAME", "Focus Beratung GmbH")
RIGHTS = f"(c) 2026 {BRAND}, HRB 21811, Amtsgericht Moenchengladbach. All rights reserved."

def tag(path: Path):
    ghost = path.name.startswith("ghost_")
    editorial = "_editorial-" in path.name
    src = "trainedAlgorithmicMedia" if (ghost or editorial) else "compositeWithTrainedAlgorithmicMedia"
    desc = ("AI-generated ghost mannequin product image derived from a real studio photograph."
            if ghost else "AI-generated editorial pose of a real model, derived from a licensed studio photograph."
            if editorial else "Real studio photograph, retouched and recolored with generative AI (Nano Banana Pro).")
    subprocess.run(["exiftool", "-q", "-overwrite_original",
        f"-XMP-iptcExt:DigitalSourceType={BASE}{src}",
        f"-XMP-dc:Description={desc}", f"-IPTC:Caption-Abstract={desc}", f"-EXIF:ImageDescription={desc}",
        f"-XMP-photoshop:Credit={BRAND}", f"-IPTC:Credit={BRAND}",
        f"-XMP-dc:Rights={RIGHTS}", f"-IPTC:CopyrightNotice={RIGHTS}", f"-EXIF:Copyright={RIGHTS}",
        f"-XMP-photoshop:Source={BRAND} studio photoshoot", f"-XMP-xmpRights:Marked=True",
        "-XMP-xmp:CreatorTool=Higgsfield Nano Banana Pro", "-IPTC:OriginatingProgram=Higgsfield Nano Banana Pro",
        str(path)], check=True)

if __name__ == "__main__":
    files = [p for a in sys.argv[1:] for p in (Path(a).rglob("*.jpg") if Path(a).is_dir() else [Path(a)])]
    for f in files: tag(f)
    print(f"tagged {len(files)} files")
