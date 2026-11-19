"""Count untranslated unique strings in the phase-2 banks (remaining labels + descriptions)."""
import glob, json
from pathlib import Path
from c0text import C0
from english import english_banks
ROOT = Path(__file__).resolve().parent.parent
TR = ROOT / "translation"
tiers = json.loads((TR / "ui_tiers.json").read_text(encoding="utf-8"))
done1 = set(json.loads((TR / "phase1/meta.json").read_text(encoding="utf-8"))["banks"])
done = set()
for f in glob.glob(str(TR / "phase*/batch_*.en.json")):
    done |= {e["en"] for e in json.loads(Path(f).read_text(encoding="utf-8"))}
banks = english_banks(C0(ROOT / "original/LD_C0_R.BIN", ROOT / "original/LI_C0_R.IDX"))
for tier in ("labels", "descriptions"):
    for s in tiers[tier]:
        if s in done1: continue
        rows = [r["text"] for r in banks[s]["rows"] if r["text"].strip()]
        new = {t for t in rows if t not in done}
        print(tier, s, len(rows), len(new), sum(map(len, new)), repr(sorted(new)[:3])[:150])
