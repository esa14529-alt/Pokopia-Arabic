"""Read and write the Pokopia text banks stored in LD_C0_R.BIN / LI_C0_R.IDX.

BIN holds zlib-framed banks; IDX holds one 32-byte record per bank
(offset, raw size, stored size, flags). Text banks are "version 2" tables of
relative pointers to NUL-terminated UTF-8 strings.
"""
import struct
import zlib

INDEX_RECORD = 32


def align(value: int, boundary: int) -> int:
    return (value + boundary - 1) // boundary * boundary


def decode_bank(binary: bytes, offset: int, stored: int) -> bytes:
    limit, count, raw_size = struct.unpack_from("<III", binary, offset)
    if not limit or not count or count > 1024 or count != (raw_size + limit - 1) // limit:
        raise ValueError("bad bank header")
    cursor = offset + align(12 + 4 * count, 128)
    end = offset + stored
    parts = []
    for i in range(count):
        framed = struct.unpack_from("<I", binary, offset + 12 + i * 4)[0]
        expected = min(limit, raw_size - i * limit)
        if framed <= 0 or cursor + framed > end:
            raise ValueError("truncated frame")
        if framed == expected:
            part = binary[cursor:cursor + framed]
        else:
            size = struct.unpack_from("<I", binary, cursor)[0]
            if size + 4 != framed:
                raise ValueError("bad compressed frame")
            part = zlib.decompress(binary[cursor + 4:cursor + framed])
        if len(part) != expected:
            raise ValueError("bad frame size")
        parts.append(part)
        cursor = align(cursor + framed, 128)
    return b"".join(parts)


def encode_bank(raw: bytes, old_binary: bytes, old_offset: int) -> bytes:
    limit = struct.unpack_from("<I", old_binary, old_offset)[0]
    chunks = [raw[p:p + limit] for p in range(0, len(raw), limit)]
    header_size = align(12 + 4 * len(chunks), 128)
    header = bytearray(header_size)
    header[:min(header_size, 128)] = old_binary[old_offset:old_offset + min(header_size, 128)]
    struct.pack_into("<III", header, 0, limit, len(chunks), len(raw))
    out = bytearray()
    frames = []
    for i, chunk in enumerate(chunks):
        comp = zlib.compress(chunk, 9)
        frame = struct.pack("<I", len(comp)) + comp
        struct.pack_into("<I", header, 12 + i * 4, len(frame))
        frames.append(frame)
    out += header
    for frame in frames:
        out += frame
        out += b"\0" * (align(len(out), 128) - len(out))
    return bytes(out)


def parse_table(raw: bytes):
    if len(raw) < 72:
        return None
    count, version = struct.unpack_from("<II", raw, 0)
    if version != 2 or not 0 < count <= 20000 or 64 + count * 8 > len(raw):
        return None
    first = struct.unpack_from("<I", raw, 64)[0]
    stride = next((s for s in (12, 16, 20, 24, 28, 32, 40, 48, 64) if first == count * s), 8)
    if 64 + count * stride > len(raw):
        return None
    columns = min({12: 2, 32: 6}.get(stride, 1 if stride == 8 else stride // 4), stride // 4)
    floor = 64 + count * stride
    rows = []
    for row in range(count):
        for col in range(columns):
            field = 64 + row * stride + col * 4
            rel = struct.unpack_from("<I", raw, field)[0]
            target = field + rel
            if not rel or target < floor or target >= len(raw):
                continue
            end = raw.find(b"\0", target)
            if end < 0:
                continue
            try:
                value = raw[target:end].decode("utf-8")
            except UnicodeDecodeError:
                continue
            if not value or any(ord(c) < 32 and c not in "\r\n\t" for c in value):
                continue
            rows.append({"row": row, "col": col, "field": field, "text": value})
    return {"count": count, "stride": stride, "columns": columns, "rows": rows}


class C0:
    def __init__(self, bin_path, idx_path):
        self.bin = open(bin_path, "rb").read()
        self.idx = open(idx_path, "rb").read()

    def records(self):
        for slot in range(len(self.idx) // INDEX_RECORD):
            offset, size, stored, flags = struct.unpack_from("<4Q", self.idx, slot * INDEX_RECORD)
            yield slot, offset, size, stored, flags

    def text_banks(self):
        """Yield (slot, offset, raw, table) for every decodable text table."""
        for slot, offset, size, stored, _flags in self.records():
            if not size or not stored or offset + stored > len(self.bin):
                continue
            try:
                raw = decode_bank(self.bin, offset, stored)
            except (ValueError, zlib.error, struct.error):
                continue
            table = parse_table(raw)
            if table and table["rows"]:
                yield slot, offset, raw, table

    def build(self, edits: dict):
        """edits: {slot: {(row, col): new_text}} -> (new_bin, new_idx)."""
        new_bin = bytearray(self.bin)
        new_idx = bytearray(self.idx)
        banks = {slot: (offset, raw, table) for slot, offset, raw, table in self.text_banks()
                 if slot in edits}
        for slot in sorted(edits):
            offset, raw, table = banks[slot]
            raw = bytearray(raw)
            for (row, col), value in edits[slot].items():
                field = 64 + row * table["stride"] + col * 4
                raw_target = len(raw)
                raw += value.encode("utf-8") + b"\0"
                struct.pack_into("<I", raw, field, raw_target - field)
            raw += b"\0" * ((-len(raw)) % 8)
            packed = encode_bank(bytes(raw), self.bin, offset)
            new_offset = align(len(new_bin), 256)
            new_bin += b"\0" * (new_offset - len(new_bin))
            new_bin += packed
            struct.pack_into("<QQQ", new_idx, slot * INDEX_RECORD, new_offset, len(raw), len(packed))
            if decode_bank(bytes(new_bin), new_offset, len(packed)) != bytes(raw):
                raise ValueError(f"bank {slot} failed round-trip check")
        return bytes(new_bin), bytes(new_idx)
