"""Split phase 3 (all remaining dialogue) into translation batches: story banks first,
then misc messages, then Pokémon chatter (1910-2072)."""
import glob, json, re
from pathlib import Path
from c0text import C0
from english import english_banks

ROOT = Path(__file__).resolve().parent.parent
TR = ROOT / "translation"
OUT = TR / "phase3"
SKIP = {2090, 2099, 2108, 2117, 4664, 4691}   # cry words, language names, Japanese debug
CJK = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")
BATCH_CHARS = 45000

done = set()
for f in glob.glob(str(TR / "phase[12]/batch_*.en.json")):
    done |= {e["en"] for e in json.loads(Path(f).read_text(encoding="utf-8"))}
banks = english_banks(C0(ROOT / "original/LD_C0_R.BIN", ROOT / "original/LI_C0_R.IDX"))
order = sorted(s for s in banks if s not in SKIP)
order = [s for s in order if 2072 < s < 4000] + [s for s in order if s >= 4000] + [s for s in order if s <= 2072]

todo, seen = [], set()
for slot in order:
    for r in sorted(banks[slot]["rows"], key=lambda r: (r["row"], r["col"])):
        t = r["text"]
        if t.strip() and t not in done and t not in seen and not CJK.search(t):
            seen.add(t); todo.append(t)

OUT.mkdir(exist_ok=True)
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
print(len(batches), "batches,", len(todo), "strings")
