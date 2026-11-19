"""Check a translated batch: every id present, tags preserved, <br> count kept.

usage: py validate_batch.py ../translation/phase1/batch_00
"""
import json
import re
import sys
from pathlib import Path

TAG = re.compile(r"<[^<>]*>")

base = Path(sys.argv[1])
src = {e["id"]: e["en"] for e in json.loads(base.with_suffix(".en.json").read_text(encoding="utf-8"))}
dst_path = base.with_suffix(".ar.json")
dst = {e["id"]: e["ar"] for e in json.loads(dst_path.read_text(encoding="utf-8"))}
problems = []
for i, en in src.items():
    ar = dst.get(i)
    if ar is None:
        problems.append((i, "missing"))
        continue
    if sorted(TAG.findall(en)) != sorted(TAG.findall(ar)):
        problems.append((i, "tags differ"))
    elif "\0" in ar or not ar.strip():
        problems.append((i, "empty"))
extra = set(dst) - set(src)
print(f"{len(src)} source, {len(dst)} translated, {len(problems)} problems, {len(extra)} unknown ids")
for p in problems[:30]:
    print(p)
sys.exit(1 if problems or extra else 0)
