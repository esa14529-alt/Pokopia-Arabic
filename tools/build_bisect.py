"""Two diagnostic mods: A = original font entries moved verbatim; B = original fonts re-packed with zero chunk tags."""
from pathlib import Path
from kt_pack import pack_entry, repoint
from kt_inflate import inflate_entry
ROOT = Path(__file__).resolve().parent.parent
KT = "motor_asset_re/KIDS_PLATFORM_OUNCE"
LOAD = Path("D:/Games/Pokemon Pokopia/user/load/0400A3A01EE4C000")
FONTS = (0x4b9d5e80, 0x8207d16b, 0xcd2c353f, 0x881d39a5, 0x7abb6ce2)
for name, repack in (("ArabicTestA", False), ("ArabicTestB", True)):
    host = bytearray((ROOT / "original" / KT / "0x4b13d561.fdata").read_bytes())
    rdb = bytearray((ROOT / "original" / KT / "root.rdb").read_bytes())
    for fid in FONTS:
        raw = (ROOT / "fonts_raw" / f"{fid:08x}.raw").read_bytes()
        data = inflate_entry(raw)
        entry = pack_entry(raw, data) if repack else raw
        off = (len(host) + 15) // 16 * 16
        host += b"\0" * (off - len(host)) + entry
        repoint(rdb, fid, 0x10, off, len(entry), len(data))
    host += b"\0" * ((-len(host)) % 16)
    out = LOAD / name / "romfs" / KT
    out.mkdir(parents=True, exist_ok=True)
    (out / "0x4b13d561.fdata").write_bytes(host)
    (out / "root.rdb").write_bytes(rdb)
    print(name, len(host))
