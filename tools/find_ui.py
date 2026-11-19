import sys
from c0text import C0
c0 = C0("../original/LD_C0_R.BIN", "../original/LI_C0_R.IDX")
want = {w.lower() for w in sys.argv[1:]}
for slot, off, raw, t in c0.text_banks():
    for r in t["rows"]:
        if r["text"].strip().lower() in want:
            print(slot, r["row"], r["col"], t["stride"], repr(r["text"]))
