"""276 editorial shots (2 per look) for ElevenLabs Nano Banana 2.1, 1K 2:3."""
import json, glob
from studio.poses import assign, prompt
rows = json.load(open("data/catalog_jobs.json"))
res = {}
for f in glob.glob("data/results/catalog_part*.json") + ["data/results/catalog_reroll.json"]:
    for r in json.load(open(f)):
        if r.get("status") == "completed": res[(r["row"], r["shot"])] = r["result_url"]
a = assign(rows)
jobs = []
for r in rows:
    f, b = a[r["row"]]
    front_ref = res[(r["row"], "01-front")]
    back_ref = res.get((r["row"], "03-back")) or res.get((r["row"], "02-three-quarter"))
    base = r["shots"][0]["file"].replace("_01-front.jpg", "")
    jobs.append({"row": r["row"], "code": r["code"], "folder": r["folder"], "shot": "04-editorial-front", "pose": f[0],
                 "refs": [front_ref], "prompt": prompt(f, "front"), "file": f"{base}_04-editorial-front.jpg"})
    jobs.append({"row": r["row"], "code": r["code"], "folder": r["folder"], "shot": "05-editorial-back", "pose": b[0],
                 "refs": [front_ref] + ([back_ref] if back_ref else []), "prompt": prompt(b, "back"),
                 "file": f"{base}_05-editorial-back.jpg"})
json.dump(jobs, open("data/editorial_jobs.json", "w"), indent=1)
n = len(jobs)
for i in range(4):
    json.dump(jobs[i * n // 4:(i + 1) * n // 4], open(f"data/editorial_part{i+1}.json", "w"), indent=1)
print(n, "shots;", sum(len(j["refs"]) == 2 for j in jobs if j["shot"].startswith("05")), "back shots with real back ref")
