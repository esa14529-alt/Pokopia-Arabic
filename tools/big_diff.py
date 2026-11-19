"""Unknown-value search across the game's heap mirrors (regions at 0x24c..0x250 0000 0000).

  py big_diff.py init            dump every region chunk to disk (all fields are candidates)
  py big_diff.py dec|inc|same    keep fields that went down / up / stayed since the last step
  py big_diff.py show [n]
"""
import sys, pickle, shutil
import numpy as np
sys.argv, args = sys.argv[:1], sys.argv[1:]
import trainer as t

D = t.STATE / "big"; LO, HI = 0x24c00000000, 0x25000000000
TYPES = ["<u1", "<u2", "<u4", "<f4"]
CH = 1 << 26

def chunk_list():
    for base, size in t.regions(1 << 20):
        if LO <= base < HI:
            for off in range(0, size, CH):
                yield base + off, min(CH, size - off)

def view(buf, ty):
    n = np.dtype(ty).itemsize
    return buf[: len(buf) // n * n].view(ty)

def cmp(cmd, n, o):
    with np.errstate(invalid="ignore"):
        if cmd == "show": return np.ones(len(n), bool)
        return {"dec": n < o, "inc": n > o, "same": n == o}[cmd]

def main(cmd):
    if cmd == "init":
        shutil.rmtree(D, ignore_errors=True); D.mkdir(parents=True)
        idx = {}
        for base, size in chunk_list():
            buf = np.frombuffer(t.read(base, size), np.uint8)
            np.save(D / f"{base:x}.npy", buf); idx[base] = None
        (D / "index.pkl").write_bytes(pickle.dumps(idx)); print("chunks:", len(idx)); return
    idx = pickle.loads((D / "index.pkl").read_bytes()); total = 0; shown = 0
    for base in list(idx):
        cf = D / f"{base:x}.cand"
        cand = pickle.loads(cf.read_bytes()) if cf.exists() else None
        buf = np.frombuffer(t.read(base, CH), np.uint8)
        if cand is None:  # first comparison: full chunk vs dump
            f = D / f"{base:x}.npy"; old = np.load(f); L = min(len(old), len(buf)); cand = {}
            for ty in TYPES:
                n, o = view(buf[:L], ty), view(old[:L], ty)
                k = np.nonzero(cmp(cmd, n, o))[0].astype(np.uint32)
                cand[ty] = (k, n[k].copy())
            f.unlink()
        else:
            for ty in TYPES:
                k, ov = cand[ty]; n = view(buf, ty)
                k = k[k < len(n)]; ov = ov[: len(k)]
                keep = cmp(cmd, n[k], ov)
                cand[ty] = (k[keep], n[k][keep].copy())
        if cmd != "show":
            f4 = cand["<f4"]; ok = np.isfinite(f4[1]) & (np.abs(f4[1]) < 1e6)
            cand["<f4"] = (f4[0][ok], f4[1][ok])
        cf.write_bytes(pickle.dumps(cand))
        for ty in TYPES:
            k, v = cand[ty]; total += len(k)
            if cmd == "show" and shown < int(args[1] if len(args) > 1 else 80):
                for i, x in zip(k[:20], v[:20]):
                    print(ty, hex(base + int(i) * np.dtype(ty).itemsize), x.item()); shown += 1
    (D / "index.pkl").write_bytes(pickle.dumps(idx)); print("candidates:", total)

main(args[0] if args else "show")
