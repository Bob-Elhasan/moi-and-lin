"""Local, deterministic garment recolour for ghost-mannequin images on white.
Keeps the photographed shading and texture (CIELAB lightness detail), swaps the colour.
  python -m studio.recolor <src.jpg> <out.jpg> <#RRGGBB>"""
import sys
import numpy as np
from PIL import Image, ImageFilter
from skimage import color

def garment_mask(rgb):
    """Soft mask of the garment. Tightens the white threshold until the mask no longer runs into
    the left/right image border (a grey floor gradient would otherwise be recoloured too)."""
    from scipy import ndimage
    full = rgb.shape[:2]
    rgb = np.asarray(Image.fromarray(rgb).resize((full[1] // 3, full[0] // 3), Image.BILINEAR))   # mask at 1/3 size: fast
    a = rgb.astype(int); sat = (a.max(2) - a.min(2)) > 12
    garment_mask.floor = False
    for thr in (240, 232, 224, 216, 208, 200):
        m = (a.min(2) < thr) | sat
        m = ndimage.binary_fill_holes(ndimage.binary_closing(m, iterations=2))
        m = ndimage.binary_opening(m, iterations=1)
        lab, n = ndimage.label(m)
        if n > 1:
            sizes = ndimage.sum(m, lab, range(1, n + 1)); keep = [i + 1 for i, v in enumerate(sizes) if v > 0.08 * sizes.max()]
            m = np.isin(lab, keep)
        if m[:, :3].mean() < 0.01 and m[:, -3:].mean() < 0.01: break
        if thr == 240:
            # a grey floor gradient is present: compare each row with its own background (edge columns) instead
            g = a.min(2).astype(float); w = g.shape[1]
            bg = np.median(np.concatenate([g[:, : w // 12], g[:, -w // 12:]], 1), 1)[:, None]
            m2 = (np.abs(g - bg) > 5) | sat
            m2 = ndimage.binary_fill_holes(ndimage.binary_closing(m2, iterations=4))
            m2 = ndimage.binary_opening(m2, iterations=5)
            lab2, n2 = ndimage.label(m2)
            if n2:
                sizes = ndimage.sum(m2, lab2, range(1, n2 + 1)); m2 = lab2 == (int(np.argmax(sizes)) + 1)
                core2 = ndimage.binary_erosion(m2, iterations=9)          # cut thin bridges to stray blobs
                l3, n3 = ndimage.label(core2)
                if n3:
                    sz = ndimage.sum(core2, l3, range(1, n3 + 1))
                    m2 = ndimage.binary_dilation(l3 == (int(np.argmax(sz)) + 1), iterations=10) & m2
                m2 = ndimage.binary_fill_holes(m2)
                if m2[:, :3].mean() < 0.01 and m2[:, -3:].mean() < 0.01 and m2.mean() > 0.08:
                    m = m2; garment_mask.floor = True; break
    garment_mask.clean = bool(m[:, :3].mean() < 0.01 and m[:, -3:].mean() < 0.01)
    m = Image.fromarray((m * 255).astype("uint8")).resize((full[1], full[0]), Image.BILINEAR)
    return np.asarray(m.filter(ImageFilter.GaussianBlur(1.5))).astype(float) / 255

def recolor(im, hexcol):
    rgb = np.asarray(im.convert("RGB")); m = garment_mask(rgb)
    lab = color.rgb2lab(rgb / 255.0)
    t = color.rgb2lab(np.array([[[int(hexcol[i:i + 2], 16) / 255 for i in (1, 3, 5)]]]))[0, 0]
    core = m > 0.9
    L = lab[..., 0]; Lmed = np.median(L[core]); spread = np.percentile(L[core], 95) - np.percentile(L[core], 5) + 1e-6
    # keep texture: re-centre lightness on the target, with contrast that suits the target's lightness
    want = 22 if t[0] > 80 else 26 if t[0] > 45 else 20      # typical 5-95% lightness spread of real fabric
    k = np.clip(want / spread, 0.45, 2.2)
    out = lab.copy()
    out[..., 0] = np.clip(t[0] + (L - Lmed) * k, 2, 98)
    shade = np.clip(out[..., 0] / max(t[0], 1), 0.35, 1.15)  # chroma falls off in shadows
    out[..., 1] = t[1] * shade; out[..., 2] = t[2] * shade
    res = color.lab2rgb(out) * 255
    # keep dark neutral trims, buttons and zips of a coloured garment as photographed
    chroma = np.hypot(lab[..., 1], lab[..., 2]); cmed = np.median(chroma[core])
    if cmed > 14:
        trim = ((chroma < 0.35 * cmed) & (L < Lmed - 18)).astype(float)
        trim = np.asarray(Image.fromarray((trim * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(1))) / 255.0
        res = res * (1 - trim[..., None]) + rgb * trim[..., None]
    base = np.full_like(res, 255.0) if garment_mask.floor else rgb   # drop a grey floor behind a white garment
    res = base * (1 - m[..., None]) + res * m[..., None]
    return Image.fromarray(np.clip(res, 0, 255).astype("uint8"))

if __name__ == "__main__":
    recolor(Image.open(sys.argv[1]), sys.argv[3]).save(sys.argv[2], quality=93)
