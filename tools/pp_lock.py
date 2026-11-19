"""Keeps Ditto's PP (energy bar) full in Pokopia while the emulator runs.

Run:  py pp_lock.py        (start it after loading your save; Ctrl+C or close the window to stop)

PP is stored as one 32-bit field: low 16 bits = current PP, high 16 bits = max PP. The field is
preceded by a pointer (top byte 0x83) and a zero, followed by a zero; there are four such player
slots 0x3E0 apart and slot 0 is ours.
"""
import sys, time
import numpy as np
sys.argv = sys.argv[:1]
import trainer as t

def find():
    hits = set()
    for base, size in t.regions(1 << 20):
        if not (0x24C00000000 <= base < 0x25000000000):
            continue
        for off in range(0, size, 1 << 26):
            u = np.frombuffer(t.read(base + off, min(1 << 26, size - off)), np.uint32)
            if len(u) < 8: continue
            hi, lo = u >> 16, u & 0xFFFF
            m = (hi >= 100) & (hi <= 9999) & (lo <= hi) & (hi % 50 == 0)
            m[:2] = m[-2:] = False
            i = np.nonzero(m)[0]
            i = i[(u[i - 1] == 0) & (u[i + 1] == 0) & ((u[i - 2] >> 24) == 0x83)]
            hits.update(base + off + 4 * int(j) for j in i)
    slots = sorted(a for a in hits if a + 0x3E0 in hits and a + 0x7C0 in hits and a - 0x3E0 not in hits)
    return slots[0] if slots else None

def field(addr):
    return int(np.frombuffer(t.read(addr, 4).ljust(4, b"\0"), np.uint32)[0])

def main():
    print("Searching for PP...")
    addr = None
    while True:
        if addr is None:
            addr = find()
            if addr is None:
                print("Not found yet (load your save). Retrying in 10 s."); time.sleep(10); continue
            print(f"PP found ({field(addr) & 0xFFFF}/{field(addr) >> 16}). Keeping it full. Close this window to stop.")
        v = field(addr); hi = v >> 16
        if not (100 <= hi <= 9999 and hi % 50 == 0):
            print("PP moved (save reloaded?). Searching again."); addr = None; continue
        if v & 0xFFFF != hi:
            t.k32.WriteProcessMemory(t.H, addr, np.array([hi], np.uint16).tobytes(), 2, None)
        time.sleep(0.2)

if __name__ == "__main__":
    main()
