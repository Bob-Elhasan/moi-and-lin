"""Build output/index.html: a grid of every generated photo for quick review."""
import html
import json
from pathlib import Path


def build(out_dir: Path) -> None:
    items = json.loads((out_dir / "manifest.json").read_text())
    cards = []
    for it in items:
        if it.get("status") != "ok":
            cards.append(f'<div class="c bad"><b>{html.escape(str(it))}</b></div>')
            continue
        cap = f"Row {it['row']} · {it['top']} / {it['bottom']} · {it['top_color']}"
        if it.get("footwear"):
            cap += f" · {it['footwear']}"
        cards.append(f'<div class="c"><img src="{it["file"]}" loading="lazy"><p>{html.escape(cap)}</p></div>')
    (out_dir / "index.html").write_text(
        "<!doctype html><meta charset=utf-8><title>Contact sheet</title>"
        "<style>body{font:13px system-ui;margin:16px;background:#fafafa}"
        ".g{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}"
        ".c{background:#fff;border:1px solid #ddd;padding:6px}.c img{width:100%}.bad{color:#b00}</style>"
        f"<div class=g>{''.join(cards)}</div>"
    )
