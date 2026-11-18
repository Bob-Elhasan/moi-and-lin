"""Colour every SKU of the 2026 selection: one ghost-mannequin front + back per product colour.
Source = an existing ghost mannequin of the same product; the colour is changed locally (studio.recolor).
Output: output/SKU Colors 2026/<TYPE> <code>/<Colour>/ghost_<type>_<code>_<colour>_<side>.jpg
  python -m studio.color_skus plan      -> data/color_plan.json (+ what cannot be done locally)
  python -m studio.color_skus run [n]   -> render (resumable)"""
import csv, glob, json, os, re, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image

PALETTE = {
 "Black": "#1C1C1E", "White": "#F6F5F1", "Off White": "#EFEAE0", "Cream": "#F1E8D4", "Beige": "#D8C4A6", "Light Beige": "#E6D8C0",
 "Dark Beige": "#B89F7E", "Café": "#8A6B58", "Brown": "#5B3B2A", "Camel": "#B8894F", "Havana": "#9A6A3C", "Burgundy": "#6B1A2B",
 "Navy": "#1F2A44", "Dark Navy": "#141C30", "Blue": "#2F5FA8", "Dark Blue": "#1E3A6E", "Sky Blue": "#9CC3E6", "Indigo": "#2E3270",
 "Petrol": "#1F5C66", "Turquoise": "#2FB5B0", "Aqua": "#7FD4D0", "Mint": "#A8DCC4", "Gray": "#8F9093", "Dark Gray": "#4B4C50",
 "Olive": "#6B6A3A", "Light Olive": "#9A9A62", "Dark Olive": "#4A4A28", "Green": "#2F7D4F", "Light Green": "#A9CFA0", "Kiwi": "#9BC53D",
 "Rose": "#D99AA5", "Dark Rose": "#B56576", "Pink": "#F0B6C8", "B.Rose": "#E3A6B0", "Mauve": "#B48FA8", "Light Mauve": "#D3B8CC",
 "Dark Mauve": "#7E5A75", "Lavender": "#B9A7D6", "Purple": "#5E2D79", "Fuchsia": "#C2187A", "Red": "#C0202B", "Lemon": "#F2E273",
 "Canary": "#F7D842", "Mustard": "#C99A2E",
}
# PDF code -> ghost folder name(s) from the November run
FOLDER = {"125/7071": ["125-7071"], "126/427": ["126-427"], "126/439": ["126-439"], "126/451A": ["126-451A"], "126/451B": ["126-451B"],
 "126/474": ["126-474"], "BXX/SMB115": ["BXX-SMB115"], "BXX/7039": ["BXX-7039"], "BXX/1384": ["BXX-1384"], "601/1": ["601", "601 BLACK"],
 "7080": ["7080 GREY"], "N022": ["N022", "N022 OFF WHITE"], "N022022": ["N022022 (as in folder name)"],
 "N023": ["N023", "NO23 (as in folder name)"], "2500B": ["2500B", "2500B OFF WHITE"]}
PRINT = {"126/451A", "126/451B", "126/474", "126/433", "126/461"}   # prints / patterns: a flat recolour would destroy them
SKIP = {"7098"}
REDO = {"125/1380"}   # cut-out exists but is flawed (camisole shows through the sheer fabric)
BAD_SRC = re.compile(r"print|check|dots|floral|over white|vest over", re.I)
slug = lambda s: re.sub(r"[^a-z0-9]+", "-", s.lower().replace("é", "e")).strip("-")
ROOT = Path("output/Ghost Mannequin"); OUT = Path("output/SKU Colors 2026")

def sources(typ, code):
    kind = "BOTTOM" if typ == "Bottom" else "TOP"
    res = []
    for f in FOLDER.get(code, [code.replace('/', '-')]):
        base = ROOT / f"{kind} {f}"
        for fr in sorted(base.rglob("*_front.jpg")):
            bk = fr.with_name(fr.name.replace("_front.jpg", "_back.jpg"))
            name = "/".join(p.strip() for p in fr.parent.relative_to(base).parts)
            if bk.exists() and name.count("/") <= 1 and not re.search(r"white ?/|grey/beige", name, re.I): res.append((name, fr, bk))
    return res

def score(front):
    """Prefer a plain, mid-tone, evenly lit source: easiest to recolour without losing texture."""
    from skimage import color
    from studio.recolor import garment_mask
    im = Image.open(front).convert("RGB"); im.thumbnail((500, 500))
    rgb = np.asarray(im); m = garment_mask(rgb) > 0.9
    if not garment_mask.clean or m.mean() < 0.05: return -1
    L = color.rgb2lab(rgb / 255.0)[..., 0][m]
    return 100 - abs(np.median(L) - 55) - 0.5 * max(0, np.percentile(L, 95) - np.percentile(L, 5) - 35)

def plan():
    skus = list(csv.DictReader(open("data/skus.csv", encoding="utf-8")))
    known = json.load(open("data/qa/fix_ghost_verdicts.json")).get("rejected", [])
    jobs, todo_ai = [], []
    best = {}
    for s in skus:
        code, typ, col = s["Product code"], s["Type"], s["Colour"]
        if code in SKIP: continue
        if code in REDO:
            todo_ai.append({**{k: s[k] for k in ("SKU ID", "Product code", "Type", "Colour")}, "why": "cut-out needs a redo"}); continue
        if col not in PALETTE:
            todo_ai.append({**{k: s[k] for k in ("SKU ID", "Product code", "Type", "Colour")}, "why": "colour list missing"}); continue
        if code in PRINT: todo_ai.append({**{k: s[k] for k in ("SKU ID", "Product code", "Type", "Colour")}, "why": "printed / patterned fabric"}); continue
        if code not in best:
            cands = [(score(fr), name, fr, bk) for name, fr, bk in sources(typ, code) if not BAD_SRC.search(name)
                     and not any(r in fr.name for r in known)]
            cands = [c for c in cands if c[0] > 0]
            if typ == "Bottom":   # other variants were styling substitutes (jeans etc.) in the first run, not this product
                cands = [c for c in cands if c[1].lower() == ("white pants" if code == "BXX/1384" else "original")]
            best[code] = max(cands) if cands else None
        if not best[code]:
            todo_ai.append({**{k: s[k] for k in ("SKU ID", "Product code", "Type", "Colour")}, "why": "no usable product cut-out yet"}); continue
        _, name, fr, bk = best[code]
        kind = {"Top": "top", "Bottom": "bottom", "Dress": "dress"}[typ]
        d = OUT / f"{typ.upper()} {code.replace('/', '-')}" / col
        for side, src in (("front", fr), ("back", bk)):
            jobs.append({"sku": s["SKU ID"], "code": code, "type": typ, "colour": col, "hex": PALETTE[col], "side": side,
                         "src": str(src), "src_colour": name, "out": str(d / f"ghost_{kind}_{slug(code)}_{slug(col)}_{side}.jpg")})
    json.dump(jobs, open("data/color_plan.json", "w"), indent=1, ensure_ascii=False)
    json.dump(todo_ai, open("data/color_needs_ai.json", "w"), indent=1, ensure_ascii=False)
    import collections
    print(len(jobs) // 2, "SKUs colourable locally;", len(todo_ai), "SKUs need AI first:",
          dict(collections.Counter((t["Product code"], t["why"]) for t in todo_ai)))
    for c, b in best.items(): print(" ", c.ljust(13), "source:", b[1] if b else "-")

def run(limit=None):
    from studio.recolor import recolor
    jobs = [j for j in json.load(open("data/color_plan.json")) if not os.path.exists(j["out"])][: limit]
    for i, j in enumerate(jobs):
        os.makedirs(os.path.dirname(j["out"]), exist_ok=True)
        recolor(Image.open(j["src"]), j["hex"]).save(j["out"], quality=93)
        if i % 20 == 0: print(i, "/", len(jobs), flush=True)
    if jobs: subprocess.run([sys.executable, "-m", "studio.tag_metadata", *[j["out"] for j in jobs]], check=True)
    print("rendered", len(jobs))

if __name__ == "__main__":
    plan() if sys.argv[1] == "plan" else run(int(sys.argv[2]) if len(sys.argv) > 2 else None)
