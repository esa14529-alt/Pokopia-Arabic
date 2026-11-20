"""Draw the Arabic title texture (logo + "press A") over the English layout.

Output: tex_work/title_ar.png (1024x1024 RGBA) and title_ar_preview.png (on a dark background).
"""
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONT = str(HERE.parent / "arfont" / "BalooBhaijaan2.ttf")
EN = Image.open(HERE / "title_logo_en_79c6dd0e.png").convert("RGBA")
W = H = 1024


def font(size, weight=b"ExtraBold"):
    f = ImageFont.truetype(FONT, size)
    f.set_variation_by_name(weight)
    return f


import math, sys
import numpy as np
sys.path.insert(0, str(HERE.parent / "tools"))
from arabic_glyphs import Renderer
_R = {}


def shaped(text, ppem, origin, weight=800):
    """Per-glyph masks (full canvas) of `text` shaped with HarfBuzz; origin = top-left."""
    r = _R.setdefault(weight, Renderer(FONT, weight))
    glyphs = r.shape(text, "", "")
    scale = ppem / r.upem
    r.ft.set_pixel_sizes(0, ppem)
    import freetype
    pen = origin[0]; base = origin[1] + int(ppem * 1.15)
    out = []
    for info, pos in glyphs:
        r.ft.load_glyph(info.codepoint, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_NO_HINTING)
        g = r.ft.glyph; bm = g.bitmap
        m = Image.new("L", (W, H), 0)
        if bm.width and bm.rows:
            a = np.array(bm.buffer, np.uint8).reshape(bm.rows, bm.pitch)[:, :bm.width]
            m.paste(Image.fromarray(a), (int(math.floor(pen + pos.x_offset * scale)) + g.bitmap_left,
                                         base - g.bitmap_top - round(pos.y_offset * scale)))
        out.append(m)
        pen += pos.x_advance * scale
    return out, pen - origin[0]


def width_of(text, ppem, weight=800):
    return shaped(text, ppem, (0, 0), weight)[1]


def union(masks):
    u = Image.new("L", (W, H), 0)
    for m in masks:
        u = ImageChops.lighter(u, m)
    return u


def glyph_mask(text, f, size):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).text((0, 0), text, font=f, fill=255)
    return m


def dilate(mask, r):
    return mask.filter(ImageFilter.MaxFilter(r * 2 + 1)) if r > 0 else mask


def fill(mask, color):
    layer = Image.new("RGBA", mask.size, color)
    layer.putalpha(mask)
    return layer


# ---------- blob with green checkers ----------
def blob():
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    for box in [(150, 70, 560, 330), (100, 130, 420, 470), (330, 110, 700, 480),
                (90, 300, 680, 520), (520, 200, 690, 470), (230, 60, 520, 200)]:
        d.ellipse(box, fill=255)
    m = m.filter(ImageFilter.GaussianBlur(18)).point(lambda v: 255 if v > 128 else 0)
    m = m.filter(ImageFilter.GaussianBlur(1.2))
    chk = Image.new("RGBA", (W, H), (196, 232, 92, 255))
    d = ImageDraw.Draw(chk)
    s = 34
    import random
    rnd = random.Random(7)
    for y in range(0, H, s):
        for x in range(0, W, s):
            if (x // s + y // s) % 2 == 0 or rnd.random() < 0.15:
                d.rectangle((x, y, x + s - 1, y + s - 1), fill=(226, 242, 120, 255))
    chk.putalpha(m)
    return chk


# ---------- multicolour word ----------
COLORS = [(52, 196, 238), (255, 158, 42), (190, 120, 245), (255, 92, 70),
          (110, 205, 40), (190, 120, 245), (255, 120, 60)]


def lighter(c, k=0.35):
    return tuple(int(v + (255 - v) * k) for v in c) + (255,)


def colorful_word(text, ppem, origin, colors):
    size = (W, H)
    x0, y0 = origin
    glyphs, _ = shaped(text, ppem, origin)
    full = union(glyphs)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    # white outline + soft green edge like the original
    out.alpha_composite(fill(dilate(full, 13).filter(ImageFilter.GaussianBlur(1)), (60, 150, 40, 255)))
    out.alpha_composite(fill(dilate(full, 11).filter(ImageFilter.GaussianBlur(1)), (255, 255, 255, 255)))
    # colour each glyph: split by cumulative advance of the visual string
    ci = 0
    for g in glyphs:
        bb = g.getbbox()
        if not bb:
            continue
        col = colors[ci % len(colors)]
        ci += 1
        out.alpha_composite(fill(g, col + (255,)))
        # diagonal light stripe for the glossy look
        stripe = Image.new("L", size, 0)
        sd = ImageDraw.Draw(stripe)
        cx = bb[0]
        sd.polygon([(cx - 40, bb[3]), (cx + 10, bb[3]), (cx + 140, bb[1] - 20), (cx + 90, bb[1] - 20)], fill=110)
        out.alpha_composite(fill(ImageChops.multiply(stripe, g), lighter(col)[:3] + (255,)))
    return out, full


def pokemon_word(text, ppem, origin):
    m = union(shaped(text, ppem, origin)[0])
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.alpha_composite(fill(dilate(m, 12), (24, 52, 128, 255)))       # dark navy rim
    out.alpha_composite(fill(dilate(m, 8), (42, 117, 187, 255)))        # Pokémon blue
    out.alpha_composite(fill(m, (255, 203, 5, 255)))                    # Pokémon yellow
    hi = ImageChops.subtract(m, m.transform(m.size, Image.AFFINE, (1, 0, 0, 0, 1, 6)))
    out.alpha_composite(fill(hi.point(lambda v: v // 2), (200, 140, 0, 255)))
    return out


def main():
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    img.alpha_composite(blob())

    # "بوكيمون" (Pokémon) on top
    wpk = width_of("بوكيمون", 150)
    img.alpha_composite(pokemon_word("بوكيمون", 150, (int(382 - wpk / 2), 40)))
    # TM from the English texture
    img.alpha_composite(EN.crop((535, 262, 562, 280)), (int(382 + wpk / 2) - 6, 262))

    # "بوكوبيا" (Pokopia) big and colourful
    ww = width_of("بوكوبيا", 210)
    word, _ = colorful_word("بوكوبيا", 210, (int(382 - ww / 2), 205), COLORS)
    img.alpha_composite(word)
    # Ditto face from the English "i" dot, placed above the alef (leftmost glyph in visual order)
    cx, cy, rb, rw = 604, 304, 25, 33
    ball = EN.crop((cx - rb, cy - rb, cx + rb, cy + rb))
    cm = Image.new("L", ball.size, 0)
    ImageDraw.Draw(cm).ellipse((0, 0, rb * 2 - 1, rb * 2 - 1), fill=255)
    ball.putalpha(ImageChops.multiply(ball.getchannel("A"), cm.filter(ImageFilter.GaussianBlur(0.6))))
    ditto = Image.new("RGBA", (rw * 2 + 4, rw * 2 + 4), (0, 0, 0, 0))
    dd = ImageDraw.Draw(ditto)
    dd.ellipse((0, 0, rw * 2 + 3, rw * 2 + 3), fill=(60, 150, 40, 255))
    dd.ellipse((2, 2, rw * 2 + 1, rw * 2 + 1), fill=(255, 255, 255, 255))
    ditto.alpha_composite(ball, (rw + 2 - rb, rw + 2 - rb))
    alef = word.getchannel("A").crop((0, 0, int(382 - ww / 2) + 90, H)).getbbox()
    img.alpha_composite(ditto, (int((alef[0] + alef[2]) / 2) - rw - 2, alef[1] - rw - 6))

    # "اضغط Ⓐ" press-start line
    a_icon = EN.crop((258, 628, 316, 686))
    w1, w2 = width_of("اضغط", 84), width_of("للبدء", 84)
    gap = 18
    total = w2 + gap + a_icon.width + gap + w1   # visual order: للبدء  Ⓐ  اضغط (RTL reads اضغط first)
    x = int(326 - total / 2)
    y = 600
    line = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    line.alpha_composite(fill(union(shaped("للبدء", 84, (x, y))[0]), (255, 255, 255, 255)))
    line.alpha_composite(a_icon, (int(x + w2 + gap), y + 40))
    line.alpha_composite(fill(union(shaped("اضغط", 84, (int(x + w2 + gap * 2 + a_icon.width), y))[0]), (255, 255, 255, 255)))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow.putalpha(line.getchannel("A").filter(ImageFilter.GaussianBlur(6)).point(lambda v: v * 6 // 10))
    img.alpha_composite(shadow, (3, 4))
    img.alpha_composite(line)

    img.save(HERE / "title_ar.png")
    prev = Image.new("RGBA", (W, H), (70, 90, 80, 255))
    prev.alpha_composite(img)
    prev.convert("RGB").save(HERE / "title_ar_preview.png")


if __name__ == "__main__":
    main()
