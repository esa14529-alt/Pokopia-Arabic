"""Build the Arabic LayeredFS mod: Arabic glyphs added to every game font,
fonts appended to a copy of 0x4b13d561.fdata and repointed in root.rdb,
plus translated text banks."""
import json
import struct
import sys
from pathlib import Path

from ar_visual import to_visual
from arabic_glyphs import Renderer, target_codepoints, to_cell
from c0text import C0
from g1n import G1N
from kt_pack import pack_entry_raw, repoint

ROOT = Path(__file__).resolve().parent.parent
ORIG = ROOT / "original"
KT = "motor_asset_re/KIDS_PLATFORM_OUNCE"
import os
MOD = Path(os.environ.get("POKOPIA_MOD_DIR", "D:/Games/Pokemon Pokopia/user/load/0400A3A01EE4C000/Arabic/romfs"))
FONTS = (0x4b9d5e80, 0x8207d16b, 0xcd2c353f, 0x881d39a5, 0x7abb6ce2)
HOST_FDATA = "0x4b13d561.fdata"
HOST_INDEX = 0x10          # root.rdx slot of 0x4b13d561
PPEM = {64: 58, 32: 29}    # Arabic alef ~ Latin cap height


def visual(text: str) -> str:
    return to_visual(text)


def build_fonts():
    renderer = Renderer(str(ROOT / "arfont/BalooBhaijaan2.ttf"))
    targets = target_codepoints()
    cache = {}
    host = bytearray((ORIG / KT / HOST_FDATA).read_bytes())
    rdb = bytearray((ORIG / KT / "root.rdb").read_bytes())
    for fid in FONTS:
        raw_entry = (ROOT / "fonts_raw" / f"{fid:08x}.raw").read_bytes()
        g = G1N((ROOT / "fonts_raw" / f"{fid:08x}.g1n").read_bytes())
        for i in range(len(g.fonts)):
            h = g.cell_height(i)
            base_y = g.baseline_y(i)
            for cp, (text, pre, post) in targets.items():
                key = (h, cp)
                if key not in cache:
                    res = renderer.render(text, pre, post, PPEM[h])
                    cache[key] = res and (to_cell(res[0], res[1], h, 0), res[2])
                if not cache[key]:
                    continue
                (cell, y_rel), advance = cache[key]
                g.add_glyph(i, cp, cell, advance, base_y + y_rel)
        data = g.build()
        # Stored uncompressed: compressed chunks carry tags the game verifies.
        entry = pack_entry_raw(raw_entry, data)
        offset = (len(host) + 15) // 16 * 16
        host += b"\0" * (offset - len(host)) + entry
        repoint(rdb, fid, HOST_INDEX, offset, len(entry), len(data), uncompressed=True)
        print(f"font {fid:08x}: {len(data)} bytes, entry {len(entry)} at {offset}")
    host += b"\0" * ((-len(host)) % 16)
    out = MOD / KT
    out.mkdir(parents=True, exist_ok=True)
    (out / HOST_FDATA).write_bytes(host)
    (out / "root.rdb").write_bytes(rdb)


def build_text(translations: dict):
    """translations: {"slot:row:col": "Arabic text"} (logical order)."""
    c0 = C0(ORIG / "LD_C0_R.BIN", ORIG / "LI_C0_R.IDX")
    edits = {}
    for key, text in translations.items():
        slot, row, col = (int(x) for x in key.split(":"))
        edits.setdefault(slot, {})[(row, col)] = visual(text)
    new_bin, new_idx = c0.build(edits)
    MOD.mkdir(parents=True, exist_ok=True)
    (MOD / "LD_C0_R.BIN").write_bytes(new_bin)
    (MOD / "LI_C0_R.IDX").write_bytes(new_idx)
    print(f"text: {sum(len(v) for v in edits.values())} strings")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    tr_file = Path(args[0]) if args else ROOT / "translation" / "ar.json"
    build_text(json.loads(tr_file.read_text(encoding="utf-8")))
    if "--text-only" not in sys.argv:
        build_fonts()
