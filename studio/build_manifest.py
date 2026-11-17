"""Build data/drive_manifest.json: every output image with its clean Drive path + sha256."""
import json, glob, hashlib, re
from pathlib import Path

def clean(seg):  # no slashes inside a folder name
    return re.sub(r"\s*/\s*", "-", seg).strip()

items = []
def add(results_glob, root):
    for f in sorted(glob.glob(results_glob)):
        for r in json.load(open(f)):
            if r.get("status") != "completed": continue
            local = Path("output") / r["folder"] / r["file"]
            top, rest = r["folder"].split("/", 1)
            group, color = rest.split("/", 1)
            parts = [root, clean(group), clean(color)]
            items.append({"path": parts, "file": r["file"], "local": str(local.resolve()),
                          "sha256": hashlib.sha256(local.read_bytes()).hexdigest(), "row": r.get("row"),
                          "code": r.get("code"), "kind": "on-model" if root == "On-Model" else "ghost"})
add("data/results/catalog_part*.json", "On-Model")
add("data/results/ghost_part*.json", "Ghost Mannequin")
json.dump(items, open("data/drive_manifest.json", "w"), indent=1)
folders = {tuple(i["path"]) for i in items}
print(len(items), "files,", len(folders), "leaf folders,", len({tuple(p[:2]) for p in folders}), "group folders")
