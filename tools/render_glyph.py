import struct, sys
from PIL import Image
fn, font, ch = sys.argv[1], int(sys.argv[2]), sys.argv[3]
b = open(fn, "rb").read()
hs, ver, bmp, nf, _ = struct.unpack_from("<IIIII", b, 12)
offs = struct.unpack_from(f"<{nf}I", b, 0x20)
pal = struct.unpack_from("<16I", b, 0x24 + nf * 4 + font * 0x40) if False else None
o = offs[font]; idx = struct.unpack_from("<H", b, o + ord(ch) * 2)[0]
rec = b[o + 0x20000 + idx * 12:o + 0x20000 + idx * 12 + 12]
w, h = rec[0], rec[1]; off = struct.unpack_from("<I", rec, 8)[0]
cell = h  # square cells
data = b[bmp + off: bmp + off + cell * cell // 2]
img = Image.new("L", (cell, cell))
px = []
for byte in data:
    px += [(byte & 15) * 17, (byte >> 4) * 17]
img.putdata(px[:cell * cell])
img = img.resize((cell * 4, cell * 4), Image.NEAREST)
img.save(sys.argv[4]); print(rec.hex(), "w", w, "h", h, "off", hex(off))
