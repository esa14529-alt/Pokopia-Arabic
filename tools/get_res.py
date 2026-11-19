"""Extract (and decompress) all resources of one type id from the .nup fdata files."""
import struct, sys, zlib
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
def inflate(blob, usize):
    parts, pos = [], 0
    while sum(map(len, parts)) < usize:
        k = min([i for i in (blob.find(b"\x78\x9c", pos), blob.find(b"\x78\xda", pos), blob.find(b"\x78\x01", pos)) if i >= 0])
        d = zlib.decompressobj(); parts.append(d.decompress(blob[k:])); pos = len(blob) - len(d.unused_data)
    return b"".join(parts)
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
                f.seek(base + pos); blob = f.read(esize)
                data = inflate(blob[0x40:], usize)
                name = f"{fid:08x}.bin"; (out / name).write_bytes(data)
                (out / (name + ".hdr")).write_bytes(blob[:0x60])
                print(name, path.split('/')[-1], pos, "esize", esize, "usize", usize, "got", len(data))
            pos = (pos + esize + 15) // 16 * 16
