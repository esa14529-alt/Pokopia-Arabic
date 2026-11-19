"""Merge translated batches into translation/ar.json ({"slot:row:col": arabic}).

Every English-bank row whose text matches a translated English string gets
that translation, so repeated strings are translated once.
"""
import glob
import json
from pathlib import Path

from c0text import C0
from english import english_banks

ROOT = Path(__file__).resolve().parent.parent
TR = ROOT / "translation"

en_to_ar = {}
for en_file in sorted(glob.glob(str(TR / "phase*" / "batch_*.en.json"))):
    ar_file = Path(en_file.replace(".en.json", ".ar.json"))
    if not ar_file.exists():
        print("skipped (not translated yet):", Path(en_file).name)
        continue
    src = {e["id"]: e["en"] for e in json.loads(Path(en_file).read_text(encoding="utf-8"))}
    try:
        dst = json.loads(ar_file.read_text(encoding="utf-8"))
    except ValueError:
        dst = []
    if {e["id"] for e in dst} != set(src):
        print("skipped (unfinished):", ar_file.parent.name, ar_file.name)
        continue
    for e in dst:
        if e["id"] in src and e["ar"].strip():
            en_to_ar[src[e["id"]]] = e["ar"]

for auto in sorted(glob.glob(str(TR / "phase*" / "auto.json"))) + sorted(glob.glob(str(TR / "phase*" / "fixes.json"))):
    en_to_ar.update(json.loads(Path(auto).read_text(encoding="utf-8")))

manual = json.loads((TR / "manual.json").read_text(encoding="utf-8")) if (TR / "manual.json").exists() else {}
c0 = C0(ROOT / "original/LD_C0_R.BIN", ROOT / "original/LI_C0_R.IDX")
out = {}
for slot, table in english_banks(c0).items():
    for r in table["rows"]:
        ar = en_to_ar.get(r["text"])
        if ar is not None and ar != r["text"]:
            out[f"{slot}:{r['row']}:{r['col']}"] = ar
out.update(manual)
(TR / "ar.json").write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
print(f"{len(en_to_ar)} translated strings -> {len(out)} game positions")
