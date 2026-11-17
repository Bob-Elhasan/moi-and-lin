"""Generate website photos with Nano Banana (Gemini image model), multi-turn.

For every outfit in the sheet:
  turn 1  -> studio model photo + product reference photos + text: dress her.
  turn 2+ -> "same photo, change only the top to <color>", one turn per color.

Keeping the whole outfit in one chat is what keeps the face, pose, lighting
and background identical across the color variants.

Usage:
  export GEMINI_API_KEY=...
  python -m studio.generate --limit 1          # test one outfit
  python -m studio.generate --only 126-427     # one top code
  python -m studio.generate                    # everything (skips done files)
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image

from .sheet import Outfit, code_key, load_outfits

ROOT = Path(__file__).resolve().parent.parent
MODEL = os.environ.get("NANO_BANANA_MODEL", "gemini-2.5-flash-image")
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp"}

STUDIO_RULES = (
    "This is an e-commerce product photo. Keep EVERYTHING from the model photo identical: "
    "same woman, same face, hair, body, skin tone, same pose and framing, same camera angle, "
    "same seamless white studio background, same soft lighting and shadows. "
    "Only the clothing and shoes change. Garments must match the product references exactly: "
    "cut, length, fabric texture, buttons, seams, prints and details. Photorealistic, sharp, no text, no watermark."
)


def product_refs(code: str) -> list[Path]:
    """Images in assets/products/<CODE>/ (folder name normalized like the sheet code)."""
    folder = ROOT / "assets" / "products" / code_key(code)
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in IMG_EXT)


DEFAULT_FOOTWEAR = "White Balerina"
FLATS = ("closed-toe {c} leather ballet flats: round toe, completely flat sole, no heel, "
         "no straps, toes fully covered")
SNEAKERS = "clean minimal {c} leather low-top sneakers with flat soles"


def footwear_prompt(sheet_value: str) -> str:
    """Footwear comes from the Excel only, and is always flats or sneakers.
    Blank cells default to white ballet flats. Never sandals or heels."""
    v = (sheet_value or DEFAULT_FOOTWEAR).lower().replace("sheakers", "sneakers")
    v = v.replace(" or shoes", "")
    color = "white"
    for c in ("black", "white", "brown", "beige", "cream", "navy"):
        if c in v:
            color = c
            break
    shoe = SNEAKERS if ("sneaker" in v or "shoes" in v or "clean" in v) else FLATS
    return ("Replace any footwear with " + shoe.format(c=color) + ". Both feet fully visible and "
            "correctly proportioned. Never sandals, heels, or open toes.")


def first_prompt(o: Outfit, first_color: str) -> str:
    lines = [
        "Image 1 is the model in our studio. The other images are product references.",
        f"Dress the model in the top (product {o.top}) and the bottom (product {o.bottom}) from the references.",
    ]
    if first_color:
        lines.append(f"The top's color must be: {first_color}.")
    if o.bottom_color:
        lines.append(f"The bottom's color must be: {o.bottom_color}.")
    if o.undershirt:
        lines.append(f"Add a plain {o.undershirt} undershirt under the top.")
    lines.append(footwear_prompt(o.footwear))
    lines.append(STUDIO_RULES)
    return "\n".join(lines)


def recolor_prompt(color: str) -> str:
    return (
        f"Same photo, change ONLY the color of the top to {color}. "
        "Keep the garment's cut, fabric, texture and details, and keep the model, pose, bottom, "
        "shoes, background and lighting exactly the same."
    )


def save_image(resp, out: Path) -> bool:
    for part in resp.candidates[0].content.parts if resp.candidates else []:
        if part.inline_data and part.inline_data.data:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(part.inline_data.data)
            return True
    return False


def send(chat, contents, retries=3):
    for attempt in range(retries):
        try:
            return chat.send_message(contents)
        except Exception as e:  # rate limits / transient errors
            if attempt == retries - 1:
                raise
            wait = 10 * (attempt + 1)
            print(f"    retry in {wait}s: {e}")
            time.sleep(wait)


def run_outfit(client, o: Outfit, model_img: Image.Image, out_dir: Path, log: list) -> None:
    refs = product_refs(o.top) + product_refs(o.bottom)
    if not refs:
        print(f"  ! no product photos for {o.top} / {o.bottom} in assets/products, using text only")
    chat = client.chats.create(
        model=MODEL,
        config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
    )
    for i, (row, barcode, color) in enumerate(o.colors):
        name = f"{o.slug}_{code_key(color) or 'BASE'}_r{row}.png"
        out = out_dir / name
        entry = {"row": row, "barcode": barcode, "top": o.top, "bottom": o.bottom,
                 "footwear": o.footwear, "bottom_color": o.bottom_color, "top_color": color, "file": name}
        if out.exists():
            print(f"  = {name} (exists)")
            log.append(entry | {"status": "ok"})
            continue
        if i == 0 or not chat.get_history():
            contents = [model_img, *[Image.open(p) for p in refs], first_prompt(o, color)]
        else:
            contents = recolor_prompt(color)
        resp = send(chat, contents)
        ok = save_image(resp, out)
        print(f"  {'+' if ok else '!'} {name}")
        log.append(entry | {"status": "ok" if ok else "no image returned"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default=str(ROOT / "data" / "combinations.xlsx"))
    ap.add_argument("--model-photo", default=str(ROOT / "assets" / "model" / "front.png"))
    ap.add_argument("--out", default=str(ROOT / "output"))
    ap.add_argument("--only", help="only outfits whose top code matches")
    ap.add_argument("--limit", type=int, help="max outfits to run")
    ap.add_argument("--max-colors", type=int, help="max colors per outfit (for test runs)")
    args = ap.parse_args()

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(api_key=key)
    model_img = Image.open(args.model_photo)
    outfits = load_outfits(args.sheet)
    if args.only:
        outfits = [o for o in outfits if code_key(o.top) == code_key(args.only)]
    if args.limit:
        outfits = outfits[: args.limit]

    out_dir = Path(args.out)
    log: list[dict] = []
    for o in outfits:
        if args.max_colors:
            o.colors = o.colors[: args.max_colors]
        print(f"> {o.slug} ({len(o.colors)} photos)")
        try:
            run_outfit(client, o, model_img, out_dir, log)
        except Exception as e:
            print(f"  ! failed: {e}")
            log.append({"top": o.top, "bottom": o.bottom, "status": f"error: {e}"})

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "manifest.json").write_text(json.dumps(log, indent=2))
    from .contact_sheet import build
    build(out_dir)
    print(f"\nDone. Review: {out_dir / 'index.html'}")


if __name__ == "__main__":
    main()
