"""Unknown-value search over windows of memory, for integer and float fields.

  py region_diff.py init            snapshot the windows, every field is a candidate
  py region_diff.py dec|inc|same    keep fields that went down / up / stayed since last snapshot
  py region_diff.py show
"""
import sys, pickle
import numpy as np
sys.argv, args = sys.argv[:1], sys.argv[1:]
import trainer as t

CENTERS = [0x24d52f2f49c, 0x24d8e93c244, 0x24d37711744]  # metal, player, misc heap
HALF = 48 << 20
TYPES = ["<u1", "<u2", "<u4", "<f4"]
ST = t.STATE / "region.pkl"

def grab():
    out = []
    for c in CENTERS:
        base = (c - HALF) & ~0xFFF
        out.append((base, np.frombuffer(t.read(base, 2 * HALF), np.uint8).copy()))
    return out

def view(buf, ty):
    n = np.dtype(ty).itemsize
    return buf[: len(buf) // n * n].view(ty)

def main(cmd):
    snap = grab()
    if cmd == "init":
        masks = [{ty: np.ones(len(view(b, ty)), bool) for ty in TYPES} for _, b in snap]
    else:
        old, masks = pickle.loads(ST.read_bytes())
        for (base, b), (_, ob), m in zip(snap, old, masks):
            for ty in TYPES:
                n, o = view(b, ty), view(ob, ty)
                L = min(len(n), len(o), len(m[ty]))
                with np.errstate(invalid="ignore"):
                    keep = {"dec": n[:L] < o[:L], "inc": n[:L] > o[:L], "same": n[:L] == o[:L], "show": np.ones(L, bool)}[cmd]
                m[ty] = m[ty][:L] & keep
    if cmd != "init":
        for (base, b), m in zip(snap, masks):  # drop junk floats
            f = view(b, "<f4")[: len(m["<f4"])]
            with np.errstate(invalid="ignore"):
                m["<f4"] &= np.isfinite(f) & (np.abs(f) < 1e6)
    ST.write_bytes(pickle.dumps((snap, masks)))
    total = 0
    for (base, b), m in zip(snap, masks):
        for ty in TYPES:
            idx = np.nonzero(m[ty])[0]; total += len(idx)
            if cmd == "show" or 0 < len(idx) <= 30:
                v = view(b, ty)
                print(ty, [(hex(base + i * np.dtype(ty).itemsize), v[i].item()) for i in idx[:30]])
    print("candidates:", total)

main(args[0] if args else "show")
