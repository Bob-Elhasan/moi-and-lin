"""data/drive/open_defects.csv: everything still wrong or missing after the fix rounds."""
import csv, json
Q = "data/qa/"
regen = {(r["row"], r["slot"]): r for r in json.load(open(Q + "regen_needed.json"))}
r2 = {j["fix"]: j for j in json.load(open("data/fix_round2_jobs.json"))}
v = json.load(open(Q + "fix_round2_verdicts.json"))
SLOT = {"01": "Front", "02": "Three-quarter", "03": "Back", "04": "Editorial front", "05": "Editorial back"}
out = []
def add(kind, row, item, sev, issue, status): out.append(dict(zip(
    ["Type", "Excel row", "Shot / item", "Severity", "Issue", "Status"], [kind, row, item, sev, issue, status])))
for state, label in (("rejected", "Re-roll failed again, needs another attempt"), ("not_run", "Not re-rolled yet (credits ran out)")):
    for f in v[state]:
        j = r2[f]; g = regen.get((j["row"], j["slot"]), {})
        add("On-model", j["row"], SLOT[j["slot"]], j["sev"], " ".join(g.get("notes", [])), label)
for f, row, slot, note in json.load(open(Q + "fix_unfixable.json")):
    add("On-model", row, SLOT[slot], "high", note, "Two re-rolls failed; source photo likely needs a manual retouch or reshoot")
acc = set(json.load(open(Q + "fix_ghost_verdicts.json"))["accepted"])
gj = {j["pair"] if "pair" in j else j.get("key"): j for j in json.load(open("data/fix_ghost_jobs.json"))}
for r in csv.DictReader(open(Q + "qa_report.csv")):
    if r["Type"].lower().startswith("ghost") and r["Severity"] in ("high", "medium"):
        key = r["Shot / item"]
        if any(a in key or key in a for a in acc): continue
        add("Ghost mannequin", r["Excel row"], key, r["Severity"], r["Note"],
            "Re-roll rejected" if r["Severity"] == "high" else "Not attempted yet")
for r in json.load(open("data/drive/index_data.json"))["rows"]:
    if r["Editorial back"] == "not generated yet":
        add("Editorial", r["Excel row"], "Editorial back", "missing", "Second lively shot (side/back) not generated", "Waiting on credits")
for m in json.load(open("data/missing_shoots.json")):
    add("No photoshoot", m["row"], f'{m["top"]} + {m["bottom"]}', "missing", f'No studio photos found for barcode {m["code"]}', "Needs a shoot or the photos added to Drive")
w = csv.DictWriter(open("data/drive/open_defects.csv", "w", newline=""), fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
import collections; print(len(out), collections.Counter((o["Type"], o["Severity"]) for o in out))
