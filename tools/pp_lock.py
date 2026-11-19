"""Keeps Ditto's PP (energy bar) full in Pokopia while the emulator runs.

Run:  py pp_lock.py        (start it after loading your save; Ctrl+C or close the window to stop)

PP is stored as one 32-bit field: low 16 bits = current PP, high 16 bits = max PP. The field is
preceded by a pointer (top byte 0x83) and a zero, followed by a zero; there are four such player
slots 0x3E0 apart and slot 0 is ours. The emulator maps game memory at different host addresses
on every run, so all of its memory is searched, and every matching slot 0 (the game keeps mirrored
copies) is kept full.
"""
import sys, time
import numpy as np
sys.argv = sys.argv[:1]
import trainer as t

def find():
    hits = set()
    for base, size in t.regions(1 << 20):
        for off in range(0, size, 1 << 26):
            u = np.frombuffer(t.read(base + off, min(1 << 26, size - off)), np.uint32)
            if len(u) < 8: continue
            hi, lo = u >> 16, u & 0xFFFF
            m = (hi >= 100) & (hi <= 9999) & (lo <= hi) & (hi % 50 == 0)
            m[:2] = m[-2:] = False
            i = np.nonzero(m)[0]
            i = i[(u[i - 1] == 0) & (u[i + 1] == 0) & ((u[i - 2] >> 24) == 0x83)]
            hits.update(base + off + 4 * int(j) for j in i)
    return sorted(a for a in hits if a + 0x3E0 in hits and a + 0x7C0 in hits and a - 0x3E0 not in hits)

def field(addr):
    return int(np.frombuffer(t.read(addr, 4).ljust(4, b"\0"), np.uint32)[0])

def ok(v):
    hi = v >> 16
    return 100 <= hi <= 9999 and hi % 50 == 0 and (v & 0xFFFF) <= hi

def main():
    print("Searching for PP (this can take a minute)...")
    addrs = []
    while True:
        if not addrs:
            addrs = find()
            if not addrs:
                print("Not found yet (load your save). Retrying in 10 s."); time.sleep(10); continue
            v = min(field(a) & 0xFFFF for a in addrs)
            print(f"PP found ({v}/{field(addrs[0]) >> 16}). Keeping it full. Close this window to stop.")
        addrs = [a for a in addrs if ok(field(a))]
        if not addrs:
            print("PP moved (save reloaded?). Searching again."); continue
        for a in addrs:
            v = field(a); hi = v >> 16
            if v & 0xFFFF != hi:
                t.k32.WriteProcessMemory(t.H, a, np.array([hi], np.uint16).tobytes(), 2, None)
        time.sleep(0.2)

if __name__ == "__main__":
    main()
