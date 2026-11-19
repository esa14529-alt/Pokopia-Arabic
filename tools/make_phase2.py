"""Split phase 2 (item names + descriptions) into translation batches.

"<Species>’s gift(s)" items are translated by pattern into translation/phase2/auto.json;
Pokémon cry words (2090-2117), language names (4664) and the Japanese debug bank (4691)
are left as they are.
"""
import glob, json, re
from pathlib import Path
from c0text import C0
from english import english_banks

ROOT = Path(__file__).resolve().parent.parent
TR = ROOT / "translation"
OUT = TR / "phase2"
BANKS = [4646, 2261] + json.loads((TR / "ui_tiers.json").read_text(encoding="utf-8"))["descriptions"]
GIFT = re.compile(r"^([A-Z][^’<>]*)’s (gift|gifts)$")
BATCH_CHARS = 18000

done = set()
for f in glob.glob(str(TR / "phase1/batch_*.en.json")):
    done |= {e["en"] for e in json.loads(Path(f).read_text(encoding="utf-8"))}
banks = english_banks(C0(ROOT / "original/LD_C0_R.BIN", ROOT / "original/LI_C0_R.IDX"))

auto, todo, seen = {}, [], set()
for slot in BANKS:
    for r in sorted(banks[slot]["rows"], key=lambda r: (r["row"], r["col"])):
        t = r["text"]
        if not t.strip() or t in done or t in seen:
            continue
        seen.add(t)
        m = GIFT.match(t)
        if m:
            auto[t] = ("هدية " if m.group(2) == "gift" else "هدايا ") + m.group(1)
        else:
            todo.append(t)

OUT.mkdir(exist_ok=True)
(OUT / "auto.json").write_text(json.dumps(auto, ensure_ascii=False, indent=0), encoding="utf-8")
batches, cur, size = [], [], 0
for t in todo:
    cur.append(t); size += len(t)
    if size >= BATCH_CHARS:
        batches.append(cur); cur, size = [], 0
if cur:
    batches.append(cur)
for i, b in enumerate(batches):
    (OUT / f"batch_{i:02d}.en.json").write_text(
        json.dumps([{"id": j, "en": t} for j, t in enumerate(b)], ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"batch_{i:02d}: {len(b)} strings, {sum(map(len, b))} chars")
print(f"auto: {len(auto)}; manual: {len(todo)}")
