"""SKU database from 'Final Selection Colors 2026' (PDF, 12 pages).
One SKU = one product code in one color, regardless of pairing.
Writes data/skus.csv, data/sku_products.csv and an .xlsx for upload."""
import csv, json, re, sys
from collections import OrderedDict

# (type, code, description EN, description AR, colors as written, page)
P = [
 ("Top","5004","Sleeveless turtle-neck knit pullover","هاي كول كت ساده","Caffe - BURGUNDY - NAVY - WHITE - BROWN - GRAY - BLACK",1),
 ("Bottom","2500B","Plain knit trousers","بنطلون تريكو ساده","Of White - BLACK - BURGUNDY - ROSE - CAFEE - BEIGE",1),
 ("Top","5006","Knit pullover with button hem detail","بلوفر ساده 3 زراير اسفل","Black - NAVY - BROWN - BURGUNDY - GRAY - CAFEE - WHITE",1),
 ("Bottom","2400B","Plain knit trousers","بنطلون تريكو ساده","Gray - OF WHITE - BEIGE",1),
 ("Top","5005","Plain oversized mock-neck knit pullover","هاف كول اوفر سايز ساده","Gray - BROWN - CAFEE - NAVY - WHITE",1),
 ("Bottom","N022","","","Of White - BLACK - BURGUNDY - BEIGE - OLIVE",1),
 ("Top","2505","Plain knit vest","فيست تريكو ساده","White - BURGUNDY - BROWN",2),
 ("Top","5003","Plain v-neck pullover","بلوفر تريكو ساده","Caffe - BLACK - BROWN - GRAY - NAVY - WHITE",2),
 ("Top","2500A","Hooded pullover with pockets","بلوفر كابيشو وجيوب","Of White - BLACK - BURGUNDY",2),
 ("Bottom","N025","","","Navy - BLACK - BLUE - D.BLUE",2),
 ("Top","25003","Plain crew-neck pullover","بلوفر روند كتف ساقط ساده","Burgundy - BLACK - GRAY - ROSE",2),
 ("Bottom","N023","","","Blue - BLACK - D.BLUE - D.NAVY - GRAY",2),
 ("Top","2408","High-neck oversized pullover with diagonal cable knit","بلوفر واسع ضفاير مايله","Black - AQUA - BEIGE - GRAY",3),
 ("Bottom","N024","","","Beige - OF WHITE",3),
 ("Top","2403","U-neck pullover","بلوفر اجور ياقه محفوره V","White - BLACK - BURGUNDY - CAFEE - D GRAY - NAVY",3),
 ("Top","5010","Zip-up knit hoodie","سويت شيرت تريكو سوسته","White - CAFEE - NAVY - BURGUNDY - BROWN - GRAY - BLACK",3),
 ("Top","7097","Oversized suede bomber jacket with hidden placket","جاكت سويد بانده مسحوره","Black - BEIGE - BROWN - BURGUNDY",3),
 ("Top","1438","","","Caffe - OLIVE - MOVE - D GRAY",4),
 ("Top","1431","Wool bomber jacket with contrasting trim","سويت شيرت صوف","Gray - D GRAY",4),
 ("Bottom","NC024","","","D.Gray - GRAY - D.NAVY",4),
 ("Top","7095","Belted wool trench coat","بالطو ساده برباط","Of White - MOVE - LEMON - GRAY - CAFEE - BLACK - BEIGE",4),
 ("Top","7096","Oversized mid-length boucle jacket","جاكيت اوفر سايز بكابشو","Of White - ROSE - BLACK - BEIGE",4),
 ("Bottom","N022022","","","Black - BLUE - GRAY",4),
 ("Top","2410","Knit cardigan with pockets","كارديجان تريكو بجيوب","Beige - BURGUNDY - OF WHITE",5),
 ("Top","603","Zip-up milton hoodie with pockets","سويت شيرت سوسته كابشو","Beige - BLACK - BROWN - BURGUNDY - WHITE",5),
 ("Bottom","601/1","Plain milton trousers","بنطلون ميلتون ساده","Black - WHITE - BEIGE",5),
 ("Top","604","Zip-up milton hoodie with pockets","سويت شيرت 2 جيب شق","Beige - OF WHITE - CAFEE - BURGUNDY - BROWN - BLACK",5),
 ("Top","7098","Wool jacket with fur cuffs","جاكت جوخ بفرو على الكم","Beige - BLACK - CAMEL - OLIVE",5),
 ("Top","21008","Basic knit mock-neck pullover","هاف كول ساده طويل","Black - ROSE - PINK - L MOVE - GRAY - D MOVE - CAFEE - BEIGE - AQUA",6),
 ("Top","5014","Hooded knit sweatshirt","سويت شيرت تريكو كابشو","Beige - OLIVE - INDIGO - D ROSE - CAMEL - BURGUNDY - BROWN - BLACK",6),
 ("Top","2400A","Plain knit pullover","بلوفر تريكو ساده","Beige - GRAY",6),
 ("Top","1418","Milton half-zip sweatshirt","سويت شيرت ساده","Black - BEIGE - WHITE",7),
 ("Top","5008","Oversized V-neck knit vest","فيست تريكو بياقة V","Black - BEIGE - BURGUNDY - CAFEE - GRAY - NAVY - ROSE",7),
 ("Top","7080","Wool shirt with two pockets","قميص صوف 2 جيب بانده عادي","Gray - CAFEE - BROWN",7),
 ("Top","7088","Belted waterproof trench coat","جاكيت وتر بروف بزراير","Black",7),
 ("Top","7089","Belted leather trench coat","بالطو ترنش كوت جلد","Black - WHITE - L.OLIVE - HAVAN - D.OLIVE - BROWN - BEIGE",8),
 ("Top","7094","Belted wool trench coat","بالطو جوخ ساده 6 زراير","Beige - CAFEE - GRAY",8),
 ("Top","125/7071","Blouse with statement collar","بلوزه بانده وكالونه ياقه","TURQUOIS - BLUE",8),
 ("Bottom","126/439","Plain pants with drawstring","بنطلون ساده برباط","CAFEE",8),
 ("Top","126/427","Plain linen-blend cardigan","كاردجن ساده","BLACK - BEIGE - B.ROSE - BROWN - LAVANDER - L.GREEN - MUSTARD - OLIVE - PURPLE - SKY BLUE - WHITE",8),
 ("Top","126/451A","Mini polka-dot print cardigan","كاردجن نقشه كور صغيره","BLACK - CAFEE - NAVY - WHITE",9),
 ("Bottom","126/451B","Mini polka-dot print trousers","بنطلون نقشات كور صغيره","BLACK - CAFEE - NAVY - WHITE",9),
 ("Top","126/474","Long-sleeve blouse and elastic waist","بلوزه بكم مع خصر مطاط","BLACK - BEIGE - BROWN - OLIVE",9),
 ("Bottom","BXX/SMB115","Wide-leg leggings","ليجن رجل واسعه","BLACK",9),
 ("Top","BXX/7039","Collared blouse with concealed button placket","قميص ساده بانده","L BEIGE - TURQUOIS - KIWI - BROWN - BEIGE",9),
 ("Bottom","BXX/1384","Wide-leg trousers with button-front closure","بنطلون قماش بزرار","NAVY - BLACK - WHITE - L.BEIGE - CAFEE - D NAVY - B.ROSE - D.BEIGE",9),
 ("Top","125/7082","Plain blouse with bow","بلوزه ساده فيونكه","BLACK - BEIGE - CANARY - FUCHSIA - MOVE",9),
 ("Top","125/7064","Plain chiffon shirt","قميص ساده شيفون","BLACK - BROWN - FUSCHIA - GREEN - LAVANDER - LEMON - ROSE - SKY BLUE",10),
 ("Top","126/1336","Plain half-sleeve blouse","بلوزه نصف كم ساده","WHITE - BLACK - FUCHSIA - NAVY - PETROLY - TURQUOIS",10),
 ("Bottom","126/SMO101/1","Tiered maxi-skirt","جيبة ماكسي أدوار","BLUE - FUCHSIA - KIWI - PURPLE",10),
 ("Top","126/1372","Open-neck half-sleeve blouse","بلوزه نصف كم ساده فتحه ام","BLACK - BEIGE - WHITE",10),
 ("Top","126/425","Sleeveless blouse","بلوزه كت كشكشه","BLACK - BEIGE - CANARY - FUCHSIA - MOVE - WHITE",10),
 ("Top","126/433","Printed sleeveless blouse","بلوزه كت مشجر","NAVY - BLUE - RED",11),
 ("Top","125/1380","Plain blouse with shoulder buttons","بلوزه ساده زراير / الكتف","BLACK - HAVAN - MINT - ROSE",11),
 ("Top","5015","","","TBC",0),
 ("Dress","126/461","Contrast maxi dress with patterned hem","فستان ماكسي بدون اكمام","OLVIE - BURGUNDY",11),
 ("Dress","125/415","Short ruffled-sleeve maxi dress","فستان ساده","BEIGE - BROWN - NAVY - PURPLE - WHITE",11),
 ("Dress","126/486","Tiered dress with smocked waist and button detail","فستان طويل باكمام قصيره","CREAMY - BROWN - CAMEL - MOVE",12),
]
# (top/dress code, bottom code) as shown in the PDF
PAIRS = [("5015","2500B"),("5004","2500B"),("5006","2400B"),("5005","N022"),("2505","N022"),("5003","2500B"),("2500A","N025"),("25003","N023"),
 ("2408","N024"),("2403","N022"),("5010","2500B"),("7097","N023"),("1438","N025"),("1431","NC024"),("7095","N022"),("7096","N022022"),
 ("2410","N022"),("603","601/1"),("604","N022"),("7098","N023"),("21008","N022"),("5014","N023"),("5010","N022"),("2400A","N022"),
 ("1418","601/1"),("5008","N022"),("7080","N022"),("7088","N022"),("7089","N023"),("7094","N022"),("125/7071","126/439"),
 ("126/427","126/439"),("126/451A","126/451B"),("126/474","BXX/SMB115"),("BXX/7039","BXX/1384"),("125/7082","BXX/1384"),
 ("125/7064","126/439"),("126/1336","126/SMO101/1"),("126/1372","BXX/1384"),("126/425","BXX/1384"),("126/433","BXX/1384"),("125/1380","126/439")]

NORM = {"CAFFE":"Café","CAFEE":"Café","OF WHITE":"Off White","MOVE":"Mauve","L MOVE":"Light Mauve","D MOVE":"Dark Mauve",
 "D GRAY":"Dark Gray","D.GRAY":"Dark Gray","D.BLUE":"Dark Blue","D.NAVY":"Dark Navy","D NAVY":"Dark Navy","D ROSE":"Dark Rose",
 "L.OLIVE":"Light Olive","D.OLIVE":"Dark Olive","HAVAN":"Havana","L.GREEN":"Light Green","LAVANDER":"Lavender","TURQUOIS":"Turquoise",
 "L BEIGE":"Light Beige","L.BEIGE":"Light Beige","D.BEIGE":"Dark Beige","FUSCHIA":"Fuchsia","PETROLY":"Petrol","OLVIE":"Olive",
 "CREAMY":"Cream","TBC":"TBC (colour list needed)","B.ROSE":"B.Rose"}
NOTE = {"B.ROSE":"'B.' prefix unclear in source (Baby / Blush / Bright Rose?)"}
# product code as used in the existing photo catalog (Excel / Drive folders), where it exists
CATALOG = {"125/7071":"125-7071","126/427":"126-427","126/439":"126-439","126/451A":"126-451A","126/451B":"126-451B","126/474":"126-474",
 "BXX/SMB115":"BXX-SMB115","BXX/7039":"BXX-7039","BXX/1384":"BXX-1384","601/1":"601 / 601 BLACK","7080":"7080 GREY",
 "N022":"N022 / N022 OFF WHITE","N022022":"N022022","N023":"N023 / NO23","N024":"N024","N025":"N025","NC024":"NC024",
 **{c:c for c in "1418 1431 1438 21008 2400A 2403 2408 2410 2505 5003 5004 5005 5006 5008 5010 5014 603 604 7088 7089 7094 7095 7096 7097 2400B 2500B".split()}}
PNOTE = {"5015":"Not in the PDF; added on request (18 Nov). Studio photos exist (shot with 2500B). Description and colour list still needed.","7098":"NO studio photos in Drive: only the hanger photo in the PDF.","125/7064":"Only 1 studio photo in Drive (other products have 3 or more).","7088":"Colour list in the PDF is incomplete: 'Black -' then nothing.","1438":"No description in the PDF.",
 "N022":"Bottom 'not in catalogue' in the PDF: no description given.","N023":"Bottom 'not in catalogue': no description.",
 "N024":"Bottom 'not in catalogue': no description.","N025":"Bottom 'not in catalogue': no description.",
 "NC024":"Bottom 'not in catalogue': no description.","N022022":"Bottom 'not in catalogue': no description.",
 "126/461":"PDF cell reads 'no photo supplied' although a photo is shown.",
 "5010":"Appears twice in the PDF (with 2500B and with N022); first entry has no description."}

CHECK = {r[0]: r for r in json.load(open("data/drive/pdf_photo_check.json"))}  # code -> (code, type, originals, files, folders)
import os
_plan = {}
for j in json.load(open("data/color_plan.json")): _plan.setdefault(j["sku"], {})[j["side"]] = os.path.basename(j["out"])
_url = {}
for _f in sorted(__import__("glob").glob("data/drive/sku_done_*.json")):
    for d in json.load(open(_f))["files"]:
        if d["status"] == "ok": _url[d["title"]] = d["viewUrl"]
_fold = {}
for _f in sorted(__import__("glob").glob("data/drive/sku_done_*.json")): _fold.update(json.load(open(_f))["folders"])
_ai = {t["SKU ID"]: t["why"] for t in json.load(open("data/color_needs_ai.json"))}
STATUS_AI = {"printed / patterned fabric": "Waiting: printed fabric needs an AI recolour (Canva quota)",
             "no usable product cut-out yet": "Waiting: product cut-out not made yet (Canva quota)",
             "cut-out needs a redo": "Waiting: first cut-out flawed, redo needed",
             "colour list missing": "Waiting: colour list for this product needed from client"}
slug = lambda s: re.sub(r"[^A-Z0-9]+", "-", s.upper()).strip("-")
prod, skus = [], []
for typ, code, en, ar, cols, page in P:
    colors = [c.strip() for c in cols.split(" - ") if c.strip()]
    paired = sorted({b for t, b in PAIRS if t == code} | {t for t, b in PAIRS if b == code})
    cat = CATALOG.get(code, "")
    prod.append(OrderedDict([("Product code", code), ("Type", typ), ("Description (EN)", en), ("Description (AR)", ar),
        ("Number of colours", len(colors)), ("Colours", ", ".join(NORM.get(c.upper(), c.title()) for c in colors)),
        ("Shown paired with (PDF)", ", ".join(paired)), ("Code in existing photo catalog", cat),
        ("Studio photos in Drive", CHECK[code][2]), ("Drive shoot folders", "; ".join(CHECK[code][4])),
        ("Already in AI catalog (Nov run)", "Yes" if cat else "No"), ("PDF page", page), ("Notes", PNOTE.get(code, ""))]))
    for c in colors:
        n = NORM.get(c.upper(), c.title())
        skus.append(OrderedDict([("SKU ID", f"{slug(code)}-{slug(n)}"), ("Product code", code), ("Type", typ),
            ("Description (EN)", en), ("Description (AR)", ar), ("Colour", n), ("Colour as written in PDF", c),
            ("Barcode (EAN)", ""), ("Studio photos in Drive for product", CHECK[code][2]),
            ("Product already in AI catalog (Nov run)", "Yes" if cat else "No"),
            ("Recolour status", ""), ("Folder with this product's images (Drive)", ""), ("Front image (Drive)", ""), ("Back image (Drive)", ""), ("On-model status", ""), ("PDF page", page), ("Notes", NOTE.get(c.upper(), ""))]))
assert len({s["SKU ID"] for s in skus}) == len(skus), "duplicate SKU ids"
for r in skus:
    sid = r["SKU ID"]
    if sid in _plan:
        r["Recolour status"] = "Done (local recolour, front + back)"
        _fid = _fold.get(f'{r["Type"].upper()} {r["Product code"].replace("/", "-")}')
        r["Folder with this product's images (Drive)"] = f'=HYPERLINK("https://drive.google.com/drive/folders/{_fid}","Open folder")' if _fid else ""
        r["Front image (Drive)"] = _url.get(_plan[sid]["front"], ""); r["Back image (Drive)"] = _url.get(_plan[sid]["back"], "")
    elif r["Product code"] == "7098": r["Recolour status"] = "Skipped (client request)"
    else: r["Recolour status"] = STATUS_AI.get(_ai.get(sid, ""), "Waiting")
for name, rows in (("data/skus.csv", skus), ("data/sku_products.csv", prod)):
    w = csv.DictWriter(open(name, "w", newline="", encoding="utf-8"), fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
import collections
print(len(prod), "products", collections.Counter(p["Type"] for p in prod), "|", len(skus), "SKUs", collections.Counter(s["Type"] for s in skus))
print("no studio photos:", [p["Product code"] for p in prod if not p["Studio photos in Drive"]])

if len(sys.argv) > 1:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = openpyxl.Workbook(); wb.remove(wb.active)
    pairs = [OrderedDict([("Top / dress", t), ("Bottom", b)]) for t, b in PAIRS]
    q = [OrderedDict([("Product code", p["Product code"]), ("Question", p["Notes"])]) for p in prod if p["Notes"]]
    q += [OrderedDict([("Product code", "126/427, BXX/1384"), ("Question", "What does 'B.ROSE' stand for (Baby / Blush / Bright Rose)?")]),
          OrderedDict([("Product code", "all"), ("Question", "Barcodes (EAN) are not in the PDF: the column is empty until supplied.")])]
    for title, rows in (("SKUs", skus), ("Products", prod), ("Pairings shown in PDF", pairs), ("Open questions", q)):
        ws = wb.create_sheet(title); ws.append(list(rows[0]))
        for r in rows: ws.append(list(r.values()))
        for c in ws[1]: c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="333333")
        ws.freeze_panes = "A2"; ws.auto_filter.ref = ws.dimensions
        for i, col in enumerate(ws.columns):
            ws.column_dimensions[col[0].column_letter].width = min(60, max(12, max(len(str(c.value or "")) for c in col) + 2))
        for row in ws.iter_rows(min_row=2):
            for c in row:
                if c.column_letter in ("A", "B"): c.number_format = "@"
    wb.save(sys.argv[1]); print("wrote", sys.argv[1])
