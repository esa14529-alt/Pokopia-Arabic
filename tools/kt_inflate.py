"""Decompress an IDRK resource entry: 0x38-byte header, then chunks of
[u16 size][8-byte tag][zlib data of `size` bytes] each inflating to <=16 KiB."""
import struct, sys, zlib
from pathlib import Path

def inflate_entry(blob: bytes) -> bytes:
    usize = struct.unpack_from("<Q", blob, 0x18)[0]
    esize = struct.unpack_from("<Q", blob, 0x08)[0]
    out, pos = bytearray(), 0x38
    while len(out) < usize and pos < esize:
        size = struct.unpack_from("<H", blob, pos)[0]
        data = blob[pos + 10:pos + 10 + size]
        out += zlib.decompress(data) if data[:1] == b"\x78" else data
        pos += 10 + size
    if len(out) != usize:
        raise ValueError(f"inflated {len(out)} bytes, expected {usize}")
    return bytes(out)

if __name__ == "__main__":
    for p in sys.argv[1:]:
        data = inflate_entry(Path(p).read_bytes())
        Path(p).with_suffix(".g1n").write_bytes(data)
        print(p, len(data))
