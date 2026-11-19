"""Copy the game files the build needs out of your own Pokopia .nup into ../original/.

Usage:  py setup_originals.py "D:\\path\\to\\Pokopia.nup"
The .nup is only read, never modified.
"""
import sys
from pathlib import Path
from nup_extract import read_layout, find_file, extract

NEEDED = [
    "LD_C0_R.BIN",
    "LI_C0_R.IDX",
    "motor_asset_re/KIDS_PLATFORM_OUNCE/0x4b13d561.fdata",
    "motor_asset_re/KIDS_PLATFORM_OUNCE/MountPoint_1/0xaced3bfa.fdata",
    "motor_asset_re/KIDS_PLATFORM_OUNCE/root.rdb",
    "motor_asset_re/KIDS_PLATFORM_OUNCE/root.rdx",
    "motor_asset_re/KIDS_PLATFORM_OUNCE/system.rdb",
    "motor_asset_re/KIDS_PLATFORM_OUNCE/system.rdx",
]

def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    nup = Path(sys.argv[1])
    layout = read_layout(nup)
    pkg = layout["packages"][0]
    out = Path(__file__).resolve().parent.parent / "original"
    for rel in NEEDED:
        i = find_file(layout, pkg, rel)
        extract(nup, layout["files"][i], out / rel)
        print("ok", rel)

if __name__ == "__main__":
    main()
