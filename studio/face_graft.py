"""Keep her real face. Take the head (face + hair) from the real studio photo, soften the heavy eye make-up and shine
locally, and blend it onto the retouched/recoloured image, so identity never drifts.
  python -m studio.face_graft <real.jpg> <ai.jpg> <out.jpg>"""
import sys
import cv2
import numpy as np

CASC = cv2.data.haarcascades
def find_face(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY); H, W = g.shape
    c = cv2.CascadeClassifier(CASC + "haarcascade_frontalface_default.xml")
    f = c.detectMultiScale(g[: int(H * 0.3)], 1.1, 5, minSize=(int(W * 0.07), int(W * 0.07)))
    return tuple(sorted(f, key=lambda r: -r[2])[0]) if len(f) else None

def soften_face(img, face, eyes=0.7, shine=0.4, lips=0.35, warm=1.0):
    """Pro-retouch look on the real face: calm the smoky shadow and dark circles, warm the grey skin cast, soften shine
    and lipstick. Eye colour, lashes, brows and all facial structure stay exactly as photographed."""
    fx, fy, fw, fh = face
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    L, A, B = lab[..., 0].copy(), lab[..., 1].copy(), lab[..., 2].copy()
    H, W = L.shape; yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    ch = lab[int(fy + 0.55 * fh): int(fy + 0.78 * fh), int(fx + 0.15 * fw): int(fx + 0.85 * fw)].reshape(-1, 3)
    skin = np.median(ch, 0)
    face_m = np.zeros((H, W), np.float32)
    cv2.ellipse(face_m, (int(fx + fw / 2), int(fy + 0.58 * fh)), (int(0.50 * fw), int(0.66 * fh)), 0, 0, 360, 1, -1)
    face_m = cv2.GaussianBlur(face_m, (0, 0), 0.05 * fw)
    area = np.zeros((H, W), np.float32); protect = np.zeros((H, W), np.float32)
    for ex in (0.30, 0.70):
        cx, cy = fx + ex * fw, fy + 0.40 * fh
        area += np.exp(-(((xx - cx) / (0.20 * fw)) ** 2 + ((yy - (cy + 0.02 * fw)) / (0.15 * fw)) ** 2) ** 1.4)
        protect += np.exp(-(((xx - cx) / (0.075 * fw)) ** 2 + ((yy - cy) / (0.032 * fw)) ** 2) ** 1.6)   # iris + lash line
    brow = np.exp(-((yy - (fy + 0.265 * fh)) / (0.04 * fh)) ** 2) * (np.abs(xx - (fx + 0.5 * fw)) < 0.46 * fw)
    area = np.clip(area, 0, 1) * (1 - np.clip(protect, 0, 1) * 0.92) * (1 - 0.85 * brow)
    dark = np.clip((skin[0] - L) / 40.0, 0, 1)
    w = np.clip(eyes * area * np.clip(dark * 1.8, 0, 1), 0, 0.92)
    L = L + w * (skin[0] - 6 - L); A = A + w * (skin[1] + 3 - A); B = B + w * (skin[2] + 2 - B)
    # warm, healthy skin: the raw photo has a grey-green cast
    L = L + warm * 5 * face_m
    A = A + warm * 5 * face_m * (1 - np.clip(protect, 0, 1)); B = B + warm * 8 * face_m * (1 - np.clip(protect, 0, 1))
    blur = cv2.GaussianBlur(L, (0, 0), 0.06 * fw)
    hi = np.clip((L - blur) / 16.0, 0, 1)
    L = L - shine * face_m * hi * (L - blur)
    lm = np.exp(-(((xx - (fx + 0.5 * fw)) / (0.17 * fw)) ** 2 + ((yy - (fy + 0.82 * fh)) / (0.06 * fh)) ** 2) ** 1.5)
    A = A - lips * lm * (A - 128) * 0.6
    out = cv2.cvtColor(np.clip(np.dstack([L, A, B]), 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)
    sm = cv2.bilateralFilter(out, 0, 22, 0.012 * fw)
    m3 = (0.5 * face_m * (1 - np.clip(protect, 0, 1)) * (1 - 0.8 * brow))[..., None]
    return (out * (1 - m3) + sm * m3).astype(np.uint8)

def graft(real, ai, scale_fallback=None):
    fr, fo = find_face(real), find_face(ai)
    if fr and fo:
        s = fo[2] / fr[2]; cxr, cyr = fr[0] + fr[2] / 2, fr[1] + fr[3] / 2; cxo, cyo = fo[0] + fo[2] / 2, fo[1] + fo[3] / 2
        M = np.array([[s, 0, cxo - s * cxr], [0, s, cyo - s * cyr]], np.float32)
    else:
        s = ai.shape[1] / real.shape[1]; M = np.array([[s, 0, 0], [0, s, 0]], np.float32); fo = None
    warp = cv2.warpAffine(real, M, (ai.shape[1], ai.shape[0]), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REPLICATE)
    if fo is None:
        return None
    face_w = soften_face(warp, fo)
    fx, fy, fw, fh = fo; cx, cy = fx + fw / 2, fy + fh / 2
    mask = np.zeros(ai.shape[:2], np.float32)
    cv2.ellipse(mask, (int(cx), int(cy - 0.15 * fw)), (int(1.2 * fw), int(1.6 * fw)), 0, 0, 360, 1, -1)
    mask[int(cy + 1.0 * fw):] = 0
    mask = cv2.GaussianBlur(mask, (0, 0), 0.10 * fw)[..., None]
    return (face_w * mask + ai * (1 - mask)).astype(np.uint8)

if __name__ == "__main__":
    real, ai = cv2.imread(sys.argv[1]), cv2.imread(sys.argv[2])
    r = graft(real, ai)
    if r is None: sys.exit("no face found in one of the images")
    cv2.imwrite(sys.argv[3], r, [cv2.IMWRITE_JPEG_QUALITY, 94])
