"""Pack resources into IDRK fdata entries and repoint them in root.rdb."""
import struct
import zlib

CHUNK = 0x4000


def pack_entry(original_entry: bytes, data: bytes) -> bytes:
    """Rebuild an IDRK entry (header-only params, as fonts use) around new data.

    Chunk tags are written as zeros; the original header is kept otherwise.
    """
    if struct.unpack_from("<I", original_entry, 0x20)[0] != 0:
        raise ValueError("entry has a parameter block; not supported")
    body = bytearray()
    for pos in range(0, len(data), CHUNK):
        comp = zlib.compress(data[pos:pos + CHUNK], 9)
        body += struct.pack("<H", len(comp)) + b"\0" * 8 + comp
    header = bytearray(original_entry[:0x38])
    esize = 0x38 + len(body)
    struct.pack_into("<QQQ", header, 8, esize, len(body), len(data))
    return bytes(header + body)


COMPRESSED_FLAG = 0x00400000


def pack_entry_raw(original_entry: bytes, data: bytes) -> bytes:
    """Rebuild an IDRK entry storing data uncompressed (no chunk tags needed)."""
    if struct.unpack_from("<I", original_entry, 0x20)[0] != 0:
        raise ValueError("entry has a parameter block; not supported")
    header = bytearray(original_entry[:0x38])
    struct.pack_into("<QQQ", header, 8, 0x38 + len(data), len(data), len(data))
    flags = struct.unpack_from("<I", header, 0x2c)[0]
    struct.pack_into("<I", header, 0x2c, flags & ~COMPRESSED_FLAG)
    return bytes(header) + data


def find_rdb_entry(rdb: bytes, fid: int) -> int:
    pos = 0x20
    while pos < len(rdb):
        if rdb[pos:pos + 4] != b"IDRK":
            raise ValueError(f"bad rdb entry at {pos:#x}")
        esize = struct.unpack_from("<Q", rdb, pos + 8)[0]
        if struct.unpack_from("<I", rdb, pos + 0x24)[0] == fid:
            return pos
        pos = (pos + esize + 3) // 4 * 4
    raise KeyError(f"{fid:08x} not in rdb")


def repoint(rdb: bytearray, fid: int, file_index: int, offset: int, entry_size: int, usize: int,
            uncompressed: bool = False):
    pos = find_rdb_entry(rdb, fid)
    psize = struct.unpack_from("<Q", rdb, pos + 0x10)[0]
    param = pos + 0x38
    if psize != 13 or rdb[param] != 1 or rdb[param + 1] != 4:
        raise ValueError(f"unexpected location record for {fid:08x}")
    struct.pack_into("<Q", rdb, pos + 0x18, usize)
    struct.pack_into("<IIH", rdb, param + 2, offset, entry_size, file_index)
    if uncompressed:
        flags = struct.unpack_from("<I", rdb, pos + 0x2c)[0]
        struct.pack_into("<I", rdb, pos + 0x2c, flags & ~COMPRESSED_FLAG)
