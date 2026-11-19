import struct, sys
from pathlib import Path
from nup_extract import read_layout
NUP = Path(sys.argv[1]); want = int(sys.argv[2], 16); out = Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
L = read_layout(NUP); dc = L["dir_count"]
def walk(d, prefix):
    D = L["dirs"][d]
    for s in range(D["first"], D["first"] + D["count"]):
        n = L["children"][s]
        if n < dc: yield from walk(n, prefix + L["dirs"][n]["name"] + "/")
        else: yield prefix + L["files"][n - dc]["name"], L["files"][n - dc]
with NUP.open("rb") as f:
    for path, e in walk(L["packages"][0]["romfs_dir"], ""):
        if not path.endswith(".fdata"): continue
        base, end, pos = e["ext_off"], e["ext_off"] + e["size"], 16
        while base + pos + 0x40 <= end:
            f.seek(base + pos); h = f.read(0x60)
            if h[:4] != b"IDRK": break
            esize, dsize, usize = struct.unpack_from("<QQQ", h, 8)
            fid, tid = struct.unpack_from("<II", h, 0x24)
            if tid == want:
                f.seek(base + pos); (out / f"{fid:08x}.raw").write_bytes(f.read(esize))
                print(f"{fid:08x}", path.split('/')[-1], base + pos - e["ext_off"], esize, dsize, usize)
            pos = (pos + esize + 15) // 16 * 16
