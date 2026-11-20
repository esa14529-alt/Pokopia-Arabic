"""Koei Tecmo G1T (GT1G0600, Switch 2 / Pokopia) texture decode/encode.

decode(g1t_bytes)            -> list of PIL RGBA images (mip 0 of each texture)
encode(orig, index, image)   -> new g1t bytes; same format, size and mip count
info(g1t_bytes)              -> list of dicts describing each texture

Layout:
  0x00 'GT1G0600', u32 file_size, u32 table_off, u32 count, u32 platform(0x18), u32 extra
  table_off: count x u32 offsets (relative to table_off) of texture records
  record: u8 (mips<<4 | type), u8 format, u8 (log2h<<4 | log2w), u8 unk,
          4 flag bytes; if flags[3] & 0x10:  # extended header (size-prefixed) u32 ext_size (0x0c) + ext bytes; then data.
  Data: all mips, each mip Tegra block-linear swizzled (BCn: 4x4 blocks are
  the elements). Mip block height starts from the mip-0 GOB block height and
  halves while the mip is short enough (tegra_swizzle rules). Mip sizes are
  padded to whole GOB blocks (64 bytes x 8*bh rows).
"""
import struct
import numpy as np
from PIL import Image
import texture2ddecoder as t2d

# format code -> (name, bytes per 4x4 block or per pixel, is_block_compressed)
FORMATS = {
    0x60: ("BC1", 8, True), 0x61: ("BC2", 16, True), 0x62: ("BC3", 16, True),
    0x63: ("BC4", 8, True), 0x64: ("BC5", 16, True), 0x65: ("BC6H", 16, True),
    0x66: ("BC7", 16, True),
    0x0a: ("RGBA8?", 4, False), 0x0b: ("RGBA8?", 4, False),
    0x0c: ("RGBA8?", 4, False), 0x0d: ("RGBA8?", 4, False), 0x01: ("RGBA8", 4, False),
}


def _div(a, b):
    return (a + b - 1) // b


def _bh0(height_blocks):
    hh = height_blocks + height_blocks // 2
    for lim, v in ((128, 16), (64, 8), (32, 4), (16, 2)):
        if hh >= lim:
            return v
    return 1


def _mip_bh(h_blocks, bh):
    while bh > 1 and h_blocks <= (bh // 2) * 8:
        bh //= 2
    return bh


def _swizzle_offsets(w, h, bpe, bh):
    """Byte offset in the block-linear surface of each element (row-major w x h)."""
    gobs_x = _div(w * bpe, 64)
    y = np.arange(h, dtype=np.int64)[:, None]
    xb = (np.arange(w, dtype=np.int64) * bpe)[None, :]
    gob = ((y // (8 * bh)) * 512 * bh * gobs_x + (xb // 64) * 512 * bh
           + ((y % (8 * bh)) // 8) * 512)
    # In-GOB byte order differs from Tegra X1 (Switch 1): bits 5 and 6 are
    # swapped -> [xb0-3][y0][y1][xb4][y2][xb5]  (found empirically, Switch 2).
    return (gob + (xb % 16) + (y % 2) * 16 + ((y // 2) % 2) * 32
            + ((xb // 16) % 2) * 64 + ((y // 4) % 2) * 128 + ((xb // 32) % 2) * 256)


def _surface_size(w, h, bpe, bh):
    return _div(w * bpe, 64) * 64 * _div(h, 8 * bh) * 8 * bh


def _levels(t):
    """Yield (mip, width_px, height_px, w_el, h_el, bh, offset_in_data, size)."""
    name, bpe, bc = FORMATS[t["fmt"]]
    blk = 4 if bc else 1
    w, h = t["width"], t["height"]
    bh = _bh0(_div(h, blk))
    off = 0
    for m in range(t["mips"]):
        mw, mh = max(1, w >> m), max(1, h >> m)
        we, he = _div(mw, blk), _div(mh, blk)
        mbh = _mip_bh(he, bh)
        size = _surface_size(we, he, bpe, mbh)
        yield m, mw, mh, we, he, mbh, off, size
        off += size


def info(g):
    if g[:4] != b"GT1G":
        raise ValueError(f"not G1T: {g[:8]!r}")
    table, count = struct.unpack_from("<II", g, 0x0c)
    offs = [table + o for o in struct.unpack_from(f"<{count}I", g, table)]
    ends = offs[1:] + [len(g)]
    res = []
    for i, off in enumerate(offs):
        b0, fmt, dxy, b3 = g[off:off + 4]
        flags = g[off + 4:off + 8]
        data_off = off + 8
        ext = b""
        if flags[3] & 0x10:  # extended header (size-prefixed)
            esz = struct.unpack_from("<I", g, data_off)[0]
            ext = g[data_off:data_off + esz]
            data_off += esz
        t = dict(index=i, record=off, fmt=fmt, format=FORMATS.get(fmt, ("?",))[0],
                 width=1 << (dxy & 15), height=1 << (dxy >> 4), mips=max(1, b0 >> 4),
                 type=b0 & 15, flags=flags.hex(), ext=ext.hex(),
                 data_off=data_off, data_size=ends[i] - data_off)
        if fmt in FORMATS:
            lv = list(_levels(t))
            t["computed_size"] = lv[-1][6] + lv[-1][7]
            t["mip0_block_height"] = lv[0][5]
        res.append(t)
    return res


def _deswizzle(raw, we, he, bpe, bh):
    offs = _swizzle_offsets(we, he, bpe, bh)
    src = np.frombuffer(raw, np.uint8)
    idx = offs[..., None] + np.arange(bpe)
    return src[idx].tobytes()  # row-major elements


def _swizzle(linear, we, he, bpe, bh, size):
    offs = _swizzle_offsets(we, he, bpe, bh)
    out = np.zeros(size, np.uint8)
    out[(offs[..., None] + np.arange(bpe)).ravel()] = np.frombuffer(linear, np.uint8)
    return out.tobytes()


def _decode_level(fmt, lin, w, h):
    name, bpe, bc = FORMATS[fmt]
    pw, ph = (_div(w, 4) * 4, _div(h, 4) * 4) if bc else (w, h)
    if not bc:
        img = Image.frombytes("RGBA", (pw, ph), lin)
        return img
    fn = {"BC1": t2d.decode_bc1, "BC3": t2d.decode_bc3, "BC4": t2d.decode_bc4,
          "BC5": t2d.decode_bc5, "BC7": t2d.decode_bc7, "BC6H": t2d.decode_bc6}[name]
    bgra = fn(lin, pw, ph)
    img = Image.frombytes("RGBA", (pw, ph), bgra, "raw", "BGRA")
    return img.crop((0, 0, w, h)) if (pw, ph) != (w, h) else img


def decode(g, all_mips=False):
    out = []
    for t in info(g):
        if t["fmt"] not in FORMATS:
            out.append(None)
            continue
        name, bpe, bc = FORMATS[t["fmt"]]
        mips = []
        for m, mw, mh, we, he, bh, off, size in _levels(t):
            raw = g[t["data_off"] + off:t["data_off"] + off + size]
            mips.append(_decode_level(t["fmt"], _deswizzle(raw, we, he, bpe, bh), mw, mh))
            if not all_mips:
                break
        out.append(mips if all_mips else mips[0])
    return out


def _encode_level(fmt, img):
    import etcpak
    name, bpe, bc = FORMATS[fmt]
    w, h = img.size
    if not bc:
        return img.convert("RGBA").tobytes()
    pw, ph = _div(w, 4) * 4, _div(h, 4) * 4
    if (pw, ph) != (w, h):
        pad = Image.new("RGBA", (pw, ph)); pad.paste(img, (0, 0)); img = pad
    bgra = img.convert("RGBA").tobytes()  # etcpak takes RGBA order
    if name == "BC1": return etcpak.compress_bc1(bgra, pw, ph)
    if name == "BC3": return etcpak.compress_bc3(bgra, pw, ph)
    if name == "BC4": return etcpak.compress_bc4(bgra, pw, ph)
    if name == "BC5": return etcpak.compress_bc5(bgra, pw, ph)
    if name == "BC7":
        p = etcpak.BC7CompressBlockParams()
        return etcpak.compress_bc7(bgra, pw, ph, p)
    raise NotImplementedError(f"encode {name}")


def encode(orig, index, image):
    """Replace texture `index` with `image` (resized to the texture size if needed);
    all mips are regenerated. Returns new G1T bytes of identical length/layout."""
    t = info(orig)[index]
    name, bpe, bc = FORMATS[t["fmt"]]
    img = image.convert("RGBA")
    if img.size != (t["width"], t["height"]):
        img = img.resize((t["width"], t["height"]), Image.LANCZOS)
    g = bytearray(orig)
    for m, mw, mh, we, he, bh, off, size in _levels(t):
        level = img if m == 0 else img.resize((mw, mh), Image.LANCZOS)
        lin = _encode_level(t["fmt"], level)
        g[t["data_off"] + off:t["data_off"] + off + size] = _swizzle(lin, we, he, bpe, bh, size)
    return bytes(g)
