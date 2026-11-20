"""Read G1T resources out of Pokopia.nup (read-only) by fdata file + IDRK offset."""
import json, struct, sys, zlib
from pathlib import Path
sys.path.insert(0, r"D:\Games\Pokopia-Arabic\tools")
from nup_extract import read_layout

NUP = Path(r"D:\Games\Pokemon Pokopia\games\Pokopia.nup")
WORK = Path(r"D:\Games\Pokopia-Arabic\tex_work")
_L = None


def fdata_offsets():
    global _L
    if _L is None:
        L = read_layout(NUP); dc = L["dir_count"]; res = {}

        def walk(d):
            D = L["dirs"][d]
            for s in range(D["first"], D["first"] + D["count"]):
                n = L["children"][s]
                if n < dc: walk(n)
                else:
                    e = L["files"][n - dc]
                    if e["name"].endswith(".fdata"): res[e["name"]] = e["ext_off"]
        walk(L["packages"][0]["romfs_dir"])
        _L = res
    return _L


def inflate(blob, usize):
    # IDRK: 0x38 header + 8-byte param block + 0x18 sub-header, then
    # chunks [u16 size][8-byte tag][zlib or stored data]
    pos, out = 0x58, bytearray()
    while len(out) < usize and pos < len(blob):
        size = struct.unpack_from("<H", blob, pos)[0]
        data = blob[pos + 10:pos + 10 + size]
        try:
            out += zlib.decompress(data) if data[:1] == b"\x78" else data
        except zlib.error:
            out += data
        pos += 10 + size
    return bytes(out)


def read_entry(fdata, pos):
    with NUP.open("rb") as f:
        f.seek(fdata_offsets()[fdata] + pos)
        h = f.read(0x40)
        esize, _, usize = struct.unpack_from("<QQQ", h, 8)
        f.seek(fdata_offsets()[fdata] + pos)
        blob = f.read(esize)
    return blob, inflate(blob, usize)


def index():
    return json.loads((WORK / "g1t_all.json").read_text())
