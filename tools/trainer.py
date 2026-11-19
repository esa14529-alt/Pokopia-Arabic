"""Memory scanner / editor for the running emulator (fritchii.exe).

  py trainer.py scan  <type> <value>   first search; type = u16 | u32 | f32
  py trainer.py next  <value>          keep candidates that now hold <value>
  py trainer.py dec | inc | same       keep candidates that went down / up / stayed (needs 'snap')
  py trainer.py snap  <type> <lo> <hi> remember every value in [lo, hi] (unknown-value search)
  py trainer.py show                   list candidates
  py trainer.py set   <value> [name]   write <value> to all candidates (name saves them)
  py trainer.py freeze <name>=<value> ...  keep writing saved addresses until Ctrl+C
State lives in trainer_state/ next to this file.
"""
import ctypes as C, ctypes.wintypes as W, json, sys, time, subprocess
from pathlib import Path
import numpy as np

STATE = Path(__file__).with_name("trainer_state"); STATE.mkdir(exist_ok=True)
DT = {"u16": np.uint16, "u32": np.uint32, "f32": np.float32}
k32 = C.WinDLL("kernel32", use_last_error=True)

class MBI(C.Structure):
    _fields_ = [("BaseAddress", C.c_void_p), ("AllocationBase", C.c_void_p), ("AllocationProtect", W.DWORD),
                ("PartitionId", W.WORD), ("RegionSize", C.c_size_t), ("State", W.DWORD),
                ("Protect", W.DWORD), ("Type", W.DWORD)]
k32.VirtualQueryEx.argtypes = [W.HANDLE, C.c_void_p, C.POINTER(MBI), C.c_size_t]
k32.ReadProcessMemory.argtypes = [W.HANDLE, C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(C.c_size_t)]
k32.WriteProcessMemory.argtypes = [W.HANDLE, C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(C.c_size_t)]
k32.OpenProcess.restype = W.HANDLE

def pid():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq fritchii.exe", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout
    if "fritchii" not in out.lower(): sys.exit("The emulator is not running.")
    return int(out.split('","')[1])

H = k32.OpenProcess(0x0010 | 0x0020 | 0x0008 | 0x0400, False, pid())

def regions(min_size=1 << 16):
    a, m = 0, MBI()
    while k32.VirtualQueryEx(H, a, C.byref(m), C.sizeof(m)):
        if m.State == 0x1000 and m.Protect in (0x04, 0x40) and m.RegionSize >= min_size:
            yield m.BaseAddress, m.RegionSize
        a = (m.BaseAddress or 0) + m.RegionSize

def read(addr, n):
    buf = C.create_string_buffer(n); got = C.c_size_t()
    k32.ReadProcessMemory(H, addr, buf, n, C.byref(got))
    return buf.raw[:got.value]

def values(addrs, dt):
    sz = np.dtype(dt).itemsize
    if len(addrs) > 5000:  # bulk: re-read whole regions and pick the addresses out
        out = np.full(len(addrs), np.nan if dt == np.float32 else 0, dt)
        for base, data in chunks():
            i, j = np.searchsorted(addrs, [base, base + len(data) - sz + 1])
            if i == j: continue
            arr = np.frombuffer(data, np.uint8)
            off = (addrs[i:j] - np.uint64(base)).astype(np.int64)
            out[i:j] = np.stack([arr[off + k] for k in range(sz)], 1).copy().view(dt).ravel()
        return out
    return np.array([np.frombuffer(read(int(a), sz).ljust(sz, b"\0"), dt)[0] for a in addrs], dt)

def chunks():
    for base, size in regions():
        for off in range(0, size, 1 << 26):
            n = min(1 << 26, size - off)
            data = read(base + off, n)
            if data: yield base + off, data

def save(dt, addrs, vals=None):
    np.save(STATE / "addrs.npy", np.asarray(addrs, np.uint64))
    if vals is not None: np.save(STATE / "vals.npy", vals)
    (STATE / "type.txt").write_text(dt)
    print(f"{len(addrs)} candidates")

def load():
    dt = (STATE / "type.txt").read_text()
    return dt, np.load(STATE / "addrs.npy")

def scan(dt, value, lo=None, hi=None):
    d = DT[dt]; sz = np.dtype(d).itemsize; out, vals = [], []
    for base, data in chunks():
        arr = np.frombuffer(data[: len(data) // sz * sz], d)
        if lo is None:
            idx = np.nonzero(np.isclose(arr, value, atol=0.01) if dt == "f32" else arr == d(value))[0]
        else:
            with np.errstate(invalid="ignore"):
                idx = np.nonzero((arr >= lo) & (arr <= hi) & (arr != 0))[0]
            vals.append(arr[idx].copy())
        out.append(base + idx.astype(np.uint64) * sz)
    addrs = np.concatenate(out) if out else np.array([], np.uint64)
    save(dt, addrs, np.concatenate(vals) if vals else None)

def main(a):
    cmd = a[0]
    if cmd == "scan": scan(a[1], float(a[2]))
    elif cmd == "snap": scan(a[1], None, float(a[2]), float(a[3]))
    elif cmd in ("next", "dec", "inc", "same"):
        dt, addrs = load(); now = values(addrs, DT[dt])
        if cmd == "next":
            keep = np.isclose(now, float(a[1]), atol=0.01) if dt == "f32" else now == DT[dt](float(a[1]))
        else:
            old = np.load(STATE / "vals.npy")
            keep = {"dec": now < old, "inc": now > old, "same": now == old}[cmd]
        save(dt, addrs[keep], now[keep])
    elif cmd == "show":
        dt, addrs = load()
        for x, v in zip(addrs[:40], values(addrs[:40], DT[dt])): print(hex(int(x)), v)
    elif cmd == "set":
        dt, addrs = load(); raw = np.array([float(a[1])], DT[dt]).tobytes()
        for x in addrs: k32.WriteProcessMemory(H, int(x), raw, len(raw), None)
        print(f"wrote {a[1]} to {len(addrs)} addresses")
        if len(a) > 2:
            (STATE / f"{a[2]}.json").write_text(json.dumps({"type": dt, "addrs": [int(x) for x in addrs]}))
    elif cmd == "freeze":
        targets = []
        for spec in a[1:]:
            name, v = spec.split("=")
            s = json.loads((STATE / f"{name}.json").read_text())
            targets.append((np.array([float(v)], DT[s["type"]]).tobytes(), s["addrs"]))
        print("Freezing. Press Ctrl+C to stop.")
        while True:
            for raw, addrs in targets:
                for x in addrs: k32.WriteProcessMemory(H, x, raw, len(raw), None)
            time.sleep(0.1)

if __name__ == "__main__":
    main(sys.argv[1:] or ["show"])
