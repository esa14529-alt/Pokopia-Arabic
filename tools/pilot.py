"""Pilot: put Arabic in a few Yes/No/Back labels to test the game font."""
from pathlib import Path
import arabic_reshaper
from bidi.algorithm import get_display
from c0text import C0

def visual(text):  # joined presentation forms, reversed for left-to-right drawing
    return get_display(arabic_reshaper.reshape(text))

LABELS = {"Yes": ("A1", "نعم"), "No": ("A2", "لا"), "Back": ("A3", "رجوع")}
c0 = C0("../original/LD_C0_R.BIN", "../original/LI_C0_R.IDX")
edits = {}
for slot, off, raw, t in c0.text_banks():
    if slot != 2270:
        continue
    for r in t["rows"]:
        if r["text"] in LABELS:
            tag, ar = LABELS[r["text"]]
            edits.setdefault(slot, {})[(r["row"], r["col"])] = f"{tag} {visual(ar)} / {ar}"
print("strings changed:", sum(len(v) for v in edits.values()))
new_bin, new_idx = c0.build(edits)
out = Path("D:/Games/Pokemon Pokopia/user/load/0400A3A01EE4C000/Arabic/romfs")
out.mkdir(parents=True, exist_ok=True)
(out / "LD_C0_R.BIN").write_bytes(new_bin)
(out / "LI_C0_R.IDX").write_bytes(new_idx)
# verify by reading back
check = C0(out / "LD_C0_R.BIN", out / "LI_C0_R.IDX")
for slot, off, raw, t in check.text_banks():
    if slot == 2270:
        sample = [r["text"] for r in t["rows"] if r["text"].startswith("A")][:3]
        print("read back:", sample)
