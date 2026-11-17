"""Read the combinations spreadsheet and group rows into outfit jobs.

Each sheet row = one output photo. Rows that share the same top, bottom,
footwear and bottom color form one "outfit": the model is dressed once,
then each top color is applied as a follow-up turn in the same chat.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import openpyxl


def _clean(v) -> str:
    if v is None:
        return ""
    s = re.sub(r"\s+", " ", str(v)).strip()
    return "" if s.lower() == "none" else s


def code_key(code: str) -> str:
    """Normalize a product code for folder matching: '126-451A' -> '126-451A',
    'NO23 (as in folder name)' -> 'NO23', '7080 GREY' -> '7080-GREY'."""
    code = re.sub(r"\(.*?\)", "", code).strip()
    return re.sub(r"[^A-Za-z0-9]+", "-", code).strip("-").upper()


@dataclass
class Outfit:
    top: str
    bottom: str
    undershirt: str
    footwear: str
    bottom_color: str
    colors: list[tuple[int, str, str]] = field(default_factory=list)  # (row, barcode, top color)

    @property
    def slug(self) -> str:
        parts = [code_key(self.top), code_key(self.bottom)]
        if self.bottom_color:
            parts.append(code_key(self.bottom_color))
        if self.footwear:
            parts.append(code_key(self.footwear))
        return "_".join(p for p in parts if p)


def load_outfits(path: str | Path) -> list[Outfit]:
    ws = openpyxl.load_workbook(path, data_only=True).active
    header = [_clean(c) for c in next(ws.iter_rows(min_row=2, max_row=2, values_only=True))]
    col = {name.lower(): i for i, name in enumerate(header) if name}

    def get(row, name):
        i = col.get(name)
        return _clean(row[i]) if i is not None else ""

    outfits: dict[tuple, Outfit] = {}
    for rnum, row in enumerate(ws.iter_rows(min_row=3, values_only=True), start=3):
        top, bottom = get(row, "top"), get(row, "bottom")
        if not top or not bottom:
            continue  # notes / free-text rows at the bottom of the sheet
        key = (top, bottom, get(row, "undershirt"), get(row, "foot wear"), get(row, "bottom color"))
        o = outfits.setdefault(key, Outfit(*key))
        o.colors.append((rnum, get(row, "code"), get(row, "top color")))
    return list(outfits.values())


if __name__ == "__main__":
    import sys

    outs = load_outfits(sys.argv[1] if len(sys.argv) > 1 else "data/combinations.xlsx")
    print(f"{len(outs)} outfits, {sum(len(o.colors) for o in outs)} photos")
    for o in outs:
        print(f"  {o.slug:45s} {len(o.colors)} colors: {', '.join(c for _, _, c in o.colors)}")
