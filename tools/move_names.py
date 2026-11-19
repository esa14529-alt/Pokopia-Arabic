"""Give Pokémon move names Arabic names everywhere.

1. Every game position whose English text is exactly a move name gets the Arabic name
   (written to translation/manual.json, keyed "slot:row:col").
2. Latin move names inside already translated Arabic text are replaced (outside tags).
Run merge_translations.py afterwards.
"""
import json, glob, re
from pathlib import Path
from c0text import C0
from english import english_banks

ROOT = Path(__file__).resolve().parent.parent
TR = ROOT / "translation"
# Longest names first so "Rock Smash" wins over shorter overlaps.
MOVES = {
    "Thunder Punch": "لكمة رعدية",
    "Draco Meteor": "نيزك التنين",
    "Magnet Rise": "رفع مغناطيسي",
    "Rock Smash": "تحطيم الصخور",
    "Rototiller": "الحراثة",
    "Camouflage": "التمويه",
    "Water Gun": "مسدس الماء",
    "Fire Spin": "دوامة النار",
    "Rain Dance": "رقصة المطر",
    "Headbutt": "نطحة",
    "Strength": "القوة",
    "Teleport": "الانتقال الآني",
    "Leafage": "ورق متطاير",
    "Rollout": "التدحرج",
    "Glide": "انزلاق",
    "Surf": "ركوب الأمواج",
    "Dive": "الغوص",
    "Sing": "الغناء",
    "Cut": "القطع",
    "Fly": "الطيران",
}
TAG = re.compile(r"(<[^>]*>)")
WORD = re.compile(r"(?<![A-Za-z])(" + "|".join(map(re.escape, MOVES)) + r")(?![A-Za-z])")


def main():
    banks = english_banks(C0(ROOT / "original/LD_C0_R.BIN", ROOT / "original/LI_C0_R.IDX"))
    manual_f = TR / "manual.json"
    manual = json.loads(manual_f.read_text(encoding="utf-8"))
    added = 0
    for slot, bank in banks.items():
        for r in bank["rows"]:
            if r["text"].strip() in MOVES:
                manual[f"{slot}:{r['row']}:{r['col']}"] = MOVES[r["text"].strip()]
                added += 1
    manual_f.write_text(json.dumps(manual, ensure_ascii=False, indent=1), encoding="utf-8")

    changed = 0
    for f in glob.glob(str(TR / "phase*" / "batch_*.ar.json")):
        data = json.loads(Path(f).read_text(encoding="utf-8"))
        dirty = False
        for e in data:
            parts = TAG.split(e["ar"])
            new = "".join(p if p.startswith("<") else WORD.sub(lambda m: MOVES[m.group(1)], p) for p in parts)
            if new != e["ar"]:
                e["ar"] = new; dirty = True; changed += 1
        if dirty:
            Path(f).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"move-name positions: {added}, translated strings updated: {changed}")


if __name__ == "__main__":
    main()
