"""Recolor the white studio backdrop to light grey, keeping natural floor shadows.

The backdrop is found as the bright, neutral (low-saturation) region connected to the image
border. It is multiplied toward the target grey, so shadows keep their shape, and the mask is
feathered for soft hair edges. Garment pixels are left untouched.
Usage: python3 -m studio.grey_bg <in.jpg> <out.jpg> [hex=EEEEEE]
"""
import sys
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

def mask_for(im: Image.Image, lum_min=200, sat_max=14, scale=4, strict=False):
    small = im.resize((im.width // scale, im.height // scale), Image.BILINEAR)
    a = np.asarray(small).astype(np.int16)
    mx, mn = a.max(2), a.min(2)
    cand = (mn >= lum_min) & ((mx - mn) <= sat_max)
    if strict:   # white-on-white: only pixels very close to the measured border color count as backdrop
        edge = np.concatenate([a[:3].reshape(-1, 3), a[-3:].reshape(-1, 3), a[:, :3].reshape(-1, 3), a[:, -3:].reshape(-1, 3)])
        ref = np.median(edge, axis=0)
        cand &= (np.abs(a - ref).max(2) <= 5)
    # edges act as barriers so the fill does not cross garment outlines
    g = np.asarray(small.convert("L").filter(ImageFilter.FIND_EDGES)).astype(np.int16)
    g[:2, :] = g[-2:, :] = 0; g[:, :2] = g[:, -2:] = 0   # FIND_EDGES flags the frame border itself
    cand &= g < (6 if strict else 18)
    lab, _ = ndimage.label(cand)
    border = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    region = np.isin(lab, border[border > 0])
    region = ndimage.binary_closing(np.pad(region, 4, constant_values=True), iterations=2)[4:-4, 4:-4]
    # anything outside the subject's bounding box (plus margin) is backdrop, incl. floor gradients
    subj = ~region
    lab2, n2 = ndimage.label(subj)
    if n2:
        sizes = ndimage.sum(subj, lab2, range(1, n2 + 1))
        big = np.isin(lab2, 1 + np.where(sizes >= 0.01 * subj.size)[0])
        if big.any():
            ys, xs = np.where(big)
            pad = 4
            box = np.zeros_like(region)
            box[max(ys.min() - pad, 0):ys.max() + pad + 1, max(xs.min() - pad, 0):xs.max() + pad + 1] = True
            region |= ~box
            region &= ~big | ~box
    region = ndimage.binary_fill_holes(region) & region | region
    m = Image.fromarray((region * 255).astype(np.uint8)).resize(im.size, Image.BILINEAR)
    bg = np.median(np.asarray(small)[region], axis=0) if region.any() else np.array([255, 255, 255])
    return m.filter(ImageFilter.GaussianBlur(3)), float(region.mean()), bg

def recolor(src, dst, hexcol="EEEEEE", strict_hint=False):
    im = Image.open(src).convert("RGB")
    m, frac, bg = mask_for(im)
    mode = "loose"
    if frac > 0.85 or (strict_hint and frac > 0.8):   # fill leaked into a white garment: redo strictly
        m, frac, bg = mask_for(im, strict=True)
        mode = "strict"
    t = np.array([int(hexcol[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)
    a = np.asarray(im).astype(np.float32)
    k = np.asarray(m).astype(np.float32)[..., None] / 255.0
    # scale so the measured backdrop color lands exactly on the target; shadows keep their ratio
    out = a * (1 - k) + (a * (t / np.maximum(bg.astype(np.float32), 1))) * k
    res = np.clip(out, 0, 255).astype(np.uint8)
    Image.fromarray(res).save(dst, quality=93)
    # QA: leftover un-recolored backdrop = bright neutral pixels in the outer frame band
    r = res.astype(np.int16); h, w = r.shape[:2]; band = np.zeros((h, w), bool)
    bw = max(h, w) // 25; band[:bw] = band[-bw:] = True; band[:, :bw] = band[:, -bw:] = True
    bright = (r.min(2) >= 247) & ((r.max(2) - r.min(2)) <= 6) & band
    leftover = float(bright.sum() / band.sum())
    return {"frac": round(frac, 3), "mode": mode, "leftover": round(leftover, 4),
            "ok": leftover < 0.01 and 0.2 < frac < 0.9}

if __name__ == "__main__":
    print(recolor(sys.argv[1], sys.argv[2], *(sys.argv[3:4] or ["EEEEEE"])))
