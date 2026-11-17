# Visual QA brief

You are reviewing fashion e-commerce photos for defects. Review ONLY; do not edit, regenerate, or spend any credits.

Your list file (given in your prompt) is a JSON array of contact-sheet image paths. Read EVERY sheet with the Read tool, one at a time, and look carefully.

## On-model sheets (onmodel_NN.jpg)
Each sheet has up to 3 looks stacked. Per look: top strip = 5 photos, second strip = face/upper crops of the same 5 photos, then a black caption bar BELOW them with: ROW number | top / bottom codes | top color | bottom color | shoes.
Columns, left to right: 01-front, 02-three-quarter, 03-back, 04-editorial-front, 05-editorial-back. "(not generated)" means that shot does not exist yet: do not report it.

Check each photo and report any of these:
- WRONG_ANGLE: the shot is not what its column says (e.g. 03-back shows the front or a side view; 02 is a plain front).
- COLOR_MISMATCH: top or bottom color differs between the 5 shots of the look, or clearly contradicts the caption (top color / bottom color).
- GARMENT_MISMATCH: garment design differs between shots (buttons, length, collar, print, sleeves, extra/missing layer).
- SHOES: sandals, heels or open toes; or shoes differ between shots; or clearly contradict the caption (flats vs sneakers, color).
- IDENTITY: a different-looking woman vs 01-front (face, hair color/length), incl. hair color drift.
- MAKEUP: dark/smoky eye makeup, heavy liner, glossy or plastic skin.
- ANATOMY: extra/missing fingers, distorted hands, limbs, feet, face; duplicate person; mirror/reflection.
- FRAMING: head or feet cut off in 01/02/03 (they must be full body); subject far off-center; 04/05 that are full-body instead of a closer crop is only MINOR.
- BACKGROUND: not white, grey cast, objects, hard edges, floor line, artifacts.
- OTHER: text, watermark, anything that looks wrong or AI-broken.

## Ghost sheets (ghost_NN.jpg)
20 ghost-mannequin product shots per sheet, each with its file name below (the "ghost_" prefix and ".jpg" are stripped; name = top|bottom _ code _ color _ front|back).
Report: a visible person/body part/mannequin/hanger; wrong side (front labeled back or vice versa); color clearly not matching the color in the name; front and back of the same product+color looking like different garments; broken/deformed shape; non-white background; text or artifacts; a "top" that shows trousers or vice versa.

## Output
Write a JSON file at the path given in your prompt: a list of objects
{"sheet": "<sheet file name>", "row": <row number or null>, "item": "<column name like 03-back, or the ghost file label>", "issue": "<CATEGORY>", "severity": "high|medium|low", "note": "<one short plain sentence>"}
- high = cannot be published (wrong color/garment, wrong angle, broken anatomy, duplicate person, sandals/heels).
- medium = noticeable (makeup, identity drift, background cast).
- low = cosmetic.
Be precise and honest: report only what you actually see, do not invent defects, and do not skip sheets. If a sheet is clean, add nothing for it.
Save the file after every few sheets. Finish with a short report: sheets reviewed, counts by severity.
