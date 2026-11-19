"""Walk IDRK entries in every .fdata inside the .nup; report resource types and magics."""
import struct, sys, zlib, collections, json
from pathlib import Path
from nup_extract import read_layout
NUP = Path(sys.argv[1]); L = read_layout(NUP); dc = L["dir_count"]
def walk(d, prefix):
    D = L["dirs"][d]
    for s in range(D["first"], D["first"] + D["count"]):
        n = L["children"][s]
        if n < dc: yield from walk(n, prefix + L["dirs"][n]["name"] + "/")
        else: yield prefix + L["files"][n - dc]["name"], L["files"][n - dc]
types = collections.defaultdict(lambda: {"count": 0, "bytes": 0, "magic": collections.Counter(), "where": []})
with NUP.open("rb") as f:
    for path, e in walk(L["packages"][0]["romfs_dir"], ""):
        if not path.endswith(".fdata"): continue
        base, end, pos = e["ext_off"], e["ext_off"] + e["size"], 16
        while base + pos + 0x40 <= end:
            f.seek(base + pos); h = f.read(0x60)
            if h[:4] != b"IDRK": break
            esize, dsize, usize = struct.unpack_from("<QQQ", h, 8)
            fid, tid = struct.unpack_from("<II", h, 0x24)
            t = types[tid]; t["count"] += 1; t["bytes"] += usize
            if sum(t["magic"].values()) < 3:
                f.seek(base + pos); blob = f.read(min(esize, 0x400))
                k = blob.find(b"\x78\x9c"); k = k if k >= 0 else blob.find(b"\x78\xda")
                try: m = zlib.decompressobj().decompress(blob[k:], 16) if k >= 0 else blob[0x45:0x55]
                except zlib.error: m = b"?err"
                t["magic"][m[:8]] += 1
                if len(t["where"]) < 2: t["where"].append([path, pos, usize])
            pos = (pos + esize + 15) // 16 * 16
for tid, t in sorted(types.items(), key=lambda kv: -kv[1]["count"]):
    print(f"{tid:08x} n={t['count']:6d} {t['bytes']/1e6:9.1f}MB", dict(t["magic"]), t["where"][:1])
