"""Make recurring phase-2 terms consistent across batches; writes translation/phase2/fixes.json
({english: arabic}), which merge_translations.py applies over the batches."""
import glob, json, re
from pathlib import Path

TR = Path(__file__).resolve().parent.parent / "translation"
REGION = {"Wasteland": "البرية", "Ridge": "التلال", "Beach": "الشاطئ",
          "Skyland": "السماء", "Basin": "الحوض"}
# Area names are copied into a ~40-byte buffer (visual UTF-8), so they stay short.
AREAS = {"Withered Wasteland": "البرية الجافة", "Bleak Beach": "الشاطئ الكئيب",
         "Rocky Ridges": "التلال الصخرية", "Sparkling Skylands": "السماء اللامعة",
         "Bubbly Basin": "الحوض الفوّار"}
pairs = {}
for f in sorted(glob.glob(str(TR / "phase2/batch_*.en.json"))):
    if not Path(f.replace(".en.", ".ar.")).exists():
        continue
    en = {e["id"]: e["en"] for e in json.loads(Path(f).read_text(encoding="utf-8"))}
    ar = {e["id"]: e["ar"] for e in json.loads(Path(f.replace(".en.", ".ar.")).read_text(encoding="utf-8"))}
    pairs.update({en[i]: ar[i] for i in en})

fixes = {}
center = re.compile(r"^(?:(an?|the) )?(Wasteland|Ridge|Beach|Skyland|Basin) Pokémon (Center|Centers|Center kit|Center kits)$", re.I)
for en, ar in pairs.items():
    m = center.match(en)
    if m:
        region = REGION[m.group(2).capitalize()]
        kind = m.group(3).lower()
        fixes[en] = {"center": f"مركز Pokémon {region}", "centers": f"مراكز Pokémon {region}",
                     "center kit": f"طقم مركز Pokémon {region}",
                     "center kits": f"أطقم مركز Pokémon {region}"}[kind]
    elif "Pokémetal" in en:
        fixes[en] = re.sub(r"معدن Poké", "Pokémetal", ar)
    elif re.search(r"\bkits?$", en):
        fixes[en] = re.sub(r"^(عُدد|عدد) ", "أطقم ", re.sub(r"^عدة ", "طقم ", ar))
fixes.update(AREAS)
fixes = {k: v for k, v in fixes.items() if v != pairs.get(k)}
(TR / "phase2/fixes.json").write_text(json.dumps(fixes, ensure_ascii=False, indent=0), encoding="utf-8")
print(len(fixes), "fixes")
for k in list(fixes)[:12]:
    print(" ", k, "=>", fixes[k])
