"""Koei Tecmo G1N bitmap font: read, add glyphs, write.

Layout: header (magic, size, header size, version, bitmap base, font count x2,
per-font table offsets, one 16-colour palette per font). Each font table is a
65536-entry u16 codepoint -> glyph map followed by 12-byte glyph records
[w, h, x, y | advance, -h/2, 0, h | u32 bitmap offset]. Bitmaps are 4bpp, low
nibble first, rows padded to an even width, relative to the bitmap base.
"""
import struct

MAP_BYTES = 0x20000
REC = 12


class G1N:
    def __init__(self, data: bytes):
        self.magic = data[:8]
        _size, self.hdr_size, self.version, bmp, n, n2 = struct.unpack_from("<IIIIII", data, 8)
        offs = list(struct.unpack_from(f"<{n}I", data, 0x20))
        self.palettes = data[0x20 + 4 * n:self.hdr_size]
        self.n2 = n2
        ends = offs[1:] + [bmp]
        self.fonts = []
        for o, e in zip(offs, ends):
            cmap = list(struct.unpack_from("<65536H", data, o))
            recs = [bytearray(data[r:r + REC]) for r in range(o + MAP_BYTES, e, REC)]
            self.fonts.append({"map": cmap, "recs": recs})
        self.bitmaps = bytearray(data[bmp:])

    def cell_height(self, font: int) -> int:
        return self.fonts[font]["recs"][0][1]

    def baseline_y(self, font: int) -> int:
        """y field of a glyph that sits on the baseline (taken from 'A')."""
        f = self.fonts[font]
        return f["recs"][f["map"][0x41]][3]

    def template(self, font: int) -> bytearray:
        f = self.fonts[font]
        return bytearray(f["recs"][f["map"][0x41]])

    def add_glyph(self, font: int, codepoint: int, pixels: list[list[int]], advance: int, y: int):
        """pixels: rows of 0..15 values, all rows the same width."""
        h = len(pixels)
        w = len(pixels[0])
        stride = w + (w & 1)
        packed = bytearray()
        for row in pixels:
            row = row + [0] * (stride - w)
            for i in range(0, stride, 2):
                packed.append((row[i] & 15) | ((row[i + 1] & 15) << 4))
        offset = (len(self.bitmaps) + 0xFF) // 0x100 * 0x100
        self.bitmaps += b"\0" * (offset - len(self.bitmaps)) + packed
        rec = self.template(font)
        rec[0], rec[1], rec[2], rec[3] = w, h, 0, max(0, min(255, y))
        rec[4] = advance
        struct.pack_into("<I", rec, 8, offset)
        f = self.fonts[font]
        index = f["map"][codepoint] or len(f["recs"])
        if index == len(f["recs"]):
            f["recs"].append(rec)
        else:
            f["recs"][index] = rec
        f["map"][codepoint] = index

    def build(self) -> bytes:
        n = len(self.fonts)
        offs, pos = [], self.hdr_size
        for f in self.fonts:
            offs.append(pos)
            pos += MAP_BYTES + REC * len(f["recs"])
        bmp = pos
        out = bytearray(self.magic)
        out += struct.pack("<IIIIII", bmp + len(self.bitmaps), self.hdr_size, self.version, bmp, n, self.n2)
        out += struct.pack(f"<{n}I", *offs) + self.palettes
        assert len(out) == self.hdr_size
        for f in self.fonts:
            out += struct.pack("<65536H", *f["map"])
            for r in f["recs"]:
                out += r
        out += self.bitmaps
        return bytes(out)
