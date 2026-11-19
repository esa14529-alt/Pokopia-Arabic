"""Render Arabic letters (base + presentation forms) to 4bpp cells with HarfBuzz/FreeType."""
import math
import unicodedata

import freetype
import uharfbuzz as hb

ZWJ = "‍"
FORM_CONTEXT = {"isolated": ("", ""), "initial": ("", ZWJ), "medial": (ZWJ, ZWJ), "final": (ZWJ, "")}


def target_codepoints():
    """codepoint -> (text to shape, prefix, suffix)."""
    out = {}
    for cp in range(0x0621, 0x064B):
        out[cp] = (chr(cp), "", "")
    for cp in (0x060C, 0x061B, 0x061F, 0x0640):
        out[cp] = (chr(cp), "", "")
    for cp in range(0xFE70, 0xFEFD):
        decomp = unicodedata.decomposition(chr(cp)).split()
        if not decomp or decomp[0].strip("<>") not in FORM_CONTEXT:
            continue
        form = decomp[0].strip("<>")
        text = "".join(chr(int(x, 16)) for x in decomp[1:])
        pre, post = FORM_CONTEXT[form]
        out[cp] = (text, pre, post)
    return out


class Renderer:
    def __init__(self, path: str, weight: int = 600):
        self.path = path
        blob = hb.Blob.from_file_path(path)
        self.hb_face = hb.Face(blob)
        self.hb_font = hb.Font(self.hb_face)
        self.hb_font.set_variations({"wght": weight})
        self.ft = freetype.Face(path)
        try:
            self.ft.set_var_design_coords((weight,))
        except Exception:
            pass
        self.upem = self.hb_face.upem

    def shape(self, text, pre, post):
        buf = hb.Buffer()
        buf.add_str(pre + text + post)
        buf.guess_segment_properties()
        hb.shape(self.hb_font, buf, {})
        start, end = len(pre), len(pre) + len(text)
        keep = [(i, p) for i, p in zip(buf.glyph_infos, buf.glyph_positions)
                if start <= i.cluster < end]
        return keep

    def render(self, text, pre, post, ppem):
        """Return (canvas rows 0..255, baseline_row, advance_px) or None."""
        glyphs = self.shape(text, pre, post)
        if not glyphs:
            return None
        scale = ppem / self.upem
        adv_units = sum(p.x_advance for _, p in glyphs)
        advance = max(1, round(adv_units * scale))
        H = ppem * 3
        base = ppem * 2
        W = advance
        canvas = [[0] * W for _ in range(H)]
        self.ft.set_pixel_sizes(0, ppem)
        # RTL run: HarfBuzz gives visual order left-to-right already.
        pen = 0.0
        for info, pos in glyphs:
            self.ft.load_glyph(info.codepoint, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_NO_HINTING)
            g = self.ft.glyph
            bm = g.bitmap
            x0 = int(math.floor(pen + pos.x_offset * scale)) + g.bitmap_left
            y0 = base - g.bitmap_top - round(pos.y_offset * scale)
            for r in range(bm.rows):
                y = y0 + r
                if not 0 <= y < H:
                    continue
                row = bm.buffer[r * bm.pitch:r * bm.pitch + bm.width]
                for c, v in enumerate(row):
                    x = x0 + c
                    if 0 <= x < W and v > canvas[y][x]:
                        canvas[y][x] = v
            pen += pos.x_advance * scale
        return canvas, base, advance


def to_cell(canvas, base, cell_h, baseline_y_field):
    """Bottom-align ink in a cell_h-row cell (ink bottom on row cell_h-2) and compute y field."""
    rows = [i for i, r in enumerate(canvas) if any(r)]
    w = len(canvas[0])
    if not rows:
        return [[0] * w for _ in range(cell_h)], baseline_y_field
    top, bottom = rows[0], rows[-1]
    first = bottom - (cell_h - 2)
    cell = []
    for y in range(first, first + cell_h):
        src = canvas[y] if 0 <= y < len(canvas) and y >= top - 0 else [0] * w
        cell.append([v >> 4 for v in src])
    # glyph bottom sits (base - bottom) px above the baseline
    y_field = baseline_y_field + (base - 1 - bottom)
    return cell, y_field
