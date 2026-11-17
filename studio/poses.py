"""Lively pose library: 10 front + 10 side/back poses, matched to garment type and rotated
so no two colors of the same product share a pose."""

# Garment type per TOP code (from the ghost mannequin review)
TOP_TYPE = {
    "125-7071": "open", "126-427": "open", "126-451A": "open", "2410": "open",
    "126-474": "blouse", "BXX-7039": "blouse", "7080 GREY": "blouse",
    "21008": "knit", "2400A": "knit", "2403": "knit", "2408": "knit", "5003": "knit",
    "5004": "knit", "5005": "knit", "5006": "knit", "2505": "knit", "5008": "knit",
    "1418": "sporty", "5010": "sporty", "5014": "sporty", "603": "sporty", "604": "sporty", "7096": "sporty",
    "1431": "coat", "7088": "coat", "7089": "coat", "7094": "coat", "7095": "coat", "7097": "coat",
}
ALL = {"open", "blouse", "knit", "sporty", "coat"}

FRONT = [
    ("F01", "mid-step walk toward the camera at a slight angle, one hand lightly brushing her hair back, soft genuine smile", ALL),
    ("F02", "standing with weight on one leg, both hands relaxed in her trouser pockets, slight lean, calm confident look", ALL),
    ("F03", "both hands lightly holding the edges of the open front of the top near the collar, chin slightly lifted, subtle smile", {"open", "coat", "blouse"}),
    ("F04", "a light natural laugh while looking down to the side, one knee softly bent, arms loose", ALL),
    ("F05", "arms loosely crossed at the waist, head slightly tilted, warm relaxed smile", {"knit", "sporty", "blouse"}),
    ("F06", "tucking a strand of hair behind one ear, playful look straight into the camera", ALL),
    ("F07", "one hand resting on the waistband, the other hanging relaxed, strong confident stance, feet hip-width apart", ALL),
    ("F08", "caught mid-motion walking across the frame, body turned slightly, looking toward the camera", ALL),
    ("F09", "one hand pulling the sleeve cuff slightly down over the wrist, shoulders relaxed, soft smile", {"knit", "sporty", "blouse"}),
    ("F10", "one hand tightening or holding the belt or front closure, other hand in pocket, editorial posture", {"coat", "open", "sporty"}),
]
BACK = [
    ("B01", "walking away from the camera and glancing back over her shoulder with a soft smile", ALL),
    ("B02", "three-quarter turn away from the camera, one hand on her hip, looking back toward the camera", ALL),
    ("B03", "clean side profile facing left, chin up, arms relaxed, one foot slightly forward", ALL),
    ("B04", "back fully to the camera, head turned in profile, one hand lightly touching the back of her hair", ALL),
    ("B05", "mid-turn with the hem and fabric swinging, looking over her shoulder", {"open", "coat", "blouse"}),
    ("B06", "side step to the right, glancing back with a playful smile, arms loose", ALL),
    ("B07", "back three-quarter view, both hands in the back pockets, head turned to the side", {"knit", "sporty", "blouse"}),
    ("B08", "side profile facing right, looking down at her sleeve cuff, relaxed shoulders", ALL),
    ("B09", "back view standing tall, both arms relaxed, head slightly turned, showing the full back of the garment", ALL),
    ("B10", "leaning weight onto one hip in a three-quarter back view, one hand lifting the collar", {"coat", "open", "sporty"}),
]

def assign(rows):
    """rows: list of dicts with 'row' and 'top'. Returns {row: (front_pose, back_pose)}."""
    out, used = {}, {}
    for i, r in enumerate(sorted(rows, key=lambda x: x["row"])):
        t = TOP_TYPE.get(r["top"], "knit")
        fr = [p for p in FRONT if t in p[2]]; bk = [p for p in BACK if t in p[2]]
        seen = used.setdefault(r["top"], set())
        f = next((p for k in range(len(fr)) if (p := fr[(i + k) % len(fr)])[0] not in seen), fr[i % len(fr)])
        b = next((p for k in range(len(bk)) if (p := bk[(i * 3 + k) % len(bk)])[0] not in seen), bk[i % len(bk)])
        seen |= {f[0], b[0]}
        if len(seen) >= len(fr) + len(bk) - 2: seen.clear()
        out[r["row"]] = (f, b)
    return out

COMMON = ("Image 1 is the approved photo of this exact woman in this exact outfit. Keep her identity IDENTICAL to image 1: "
          "same face shape, eyes, eye color, brows, nose, lips, jawline, skin tone and complexion, same natural minimal makeup "
          "(no added eyeliner, eyeshadow, contour, highlighter or lipstick), same hair color, length and texture. Do not "
          "beautify, slim, age or change her in any way. Keep every garment exactly as in the reference images (same colors, "
          "fabric, texture, seams, buttons, length and fit). Do not add or remove any garment or accessory. ")
TAIL = (" Natural, effortless body language, a candid moment rather than a stiff pose. Pure white seamless studio "
        "background (#FFFFFF), soft natural window-like light, subtle gentle shadows, true-to-life colors, 85mm lens. "
        "Real skin texture with pores, natural minimal makeup, no retouched or glossy look. Looks like an authentic "
        "candid photo from a premium brand lookbook, not AI.")

def prompt(pose, side):
    frame = ("Close editorial framing from just above the head to the hips, the top filling most of the frame, camera at "
             "chest height, natural slightly off-center composition. Front-facing pose: " if side == "front" else
             "Close editorial framing from just above the head to the hips, the back and side of the top filling most of "
             "the frame, camera at shoulder height, showing back details (yoke, seams, hood, belt) clearly. Image 2 shows the real "
             "back of the outfit: match its back details exactly. Pose: ")
    return COMMON + frame + pose[1] + "." + TAIL
