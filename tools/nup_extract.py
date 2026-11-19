"""Read a Pokopia .nup container (unencrypted) and extract RomFS files from it."""
import hashlib
import struct
import sys
from pathlib import Path

HEADER = struct.Struct("<4sHHQQ32sQQII16s32s")
TOC_HEADER = struct.Struct("<4sIQQQQQ")
PACKAGE = struct.Struct("<QIIIIBBHIQI20x")
DIRECTORY = struct.Struct("<IIIIQ")
FILE = struct.Struct("<IIQQQ32sBBH12x")
NO_DIR = 0xFFFFFFFF


def read_layout(path: Path) -> dict:
    with path.open("rb") as f:
        (magic, header_size, _ver, toc_offset, toc_size, toc_sha, blob_offset,
         _size, package_count, _flags, _uuid, _res) = HEADER.unpack(f.read(HEADER.size))
        if magic != b"NUP\x01":
            raise ValueError("not a NUP v1 file")
        f.seek(toc_offset)
        toc = f.read(toc_size)
    if hashlib.sha256(toc).digest() != toc_sha:
        raise ValueError("TOC checksum mismatch")
    _m, _pc, dir_count, file_count, pool_offset, pool_size, _r = TOC_HEADER.unpack_from(toc)
    pkg_off = TOC_HEADER.size
    dir_off = pkg_off + package_count * PACKAGE.size
    file_off = dir_off + dir_count * DIRECTORY.size
    child_off = file_off + file_count * FILE.size
    pool = toc[pool_offset:pool_offset + pool_size]

    packages = []
    for i in range(package_count):
        (title_id, root_dir, exefs_dir, romfs_dir, version, kind, flags,
         _r1, _r2, _mo, _ms) = PACKAGE.unpack_from(toc, pkg_off + i * PACKAGE.size)
        packages.append({"index": i, "title_id": title_id, "romfs_dir": romfs_dir,
                         "version": version, "kind": kind, "flags": flags})
    dirs = []
    for i in range(dir_count):
        no, nl, first, count, _r = DIRECTORY.unpack_from(toc, dir_off + i * DIRECTORY.size)
        dirs.append({"name": pool[no:no + nl].decode("utf-8", "replace"),
                     "first": first, "count": count})
    files = []
    for i in range(file_count):
        no, nl, size, ext_off, ext_size, digest, codec, _cf, _r = \
            FILE.unpack_from(toc, file_off + i * FILE.size)
        files.append({"name": pool[no:no + nl].decode("utf-8", "replace"), "size": size,
                      "ext_off": ext_off, "ext_size": ext_size, "sha256": digest,
                      "codec": codec})
    children = struct.unpack_from(f"<{(pool_offset - child_off) // 4}I", toc, child_off)
    return {"packages": packages, "dirs": dirs, "files": files,
            "children": children, "dir_count": dir_count}


def find_file(layout: dict, package: dict, relative: str) -> int | None:
    current = package["romfs_dir"]
    if current == NO_DIR:
        return None
    parts = [p for p in relative.replace("\\", "/").split("/") if p]
    for n, part in enumerate(parts):
        d = layout["dirs"][current]
        hit = None
        for slot in range(d["first"], d["first"] + d["count"]):
            node = layout["children"][slot]
            if node < layout["dir_count"]:
                name, is_dir, idx = layout["dirs"][node]["name"], True, node
            else:
                idx = node - layout["dir_count"]
                name, is_dir = layout["files"][idx]["name"], False
            if name.casefold() == part.casefold():
                hit = (is_dir, idx)
        if hit is None:
            return None
        if n < len(parts) - 1:
            if not hit[0]:
                return None
            current = hit[1]
        elif not hit[0]:
            return hit[1]
    return None


def extract(path: Path, entry: dict, out: Path) -> None:
    if entry["codec"] != 0:
        raise ValueError(f"codec {entry['codec']} not supported yet")
    out.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with path.open("rb") as src, out.open("wb") as dst:
        src.seek(entry["ext_off"])
        left = entry["size"]
        while left:
            chunk = src.read(min(left, 1 << 22))
            digest.update(chunk)
            dst.write(chunk)
            left -= len(chunk)
    if digest.digest() != entry["sha256"]:
        raise ValueError(f"checksum mismatch for {out.name}")


def main() -> None:
    nup = Path(sys.argv[1])
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    layout = read_layout(nup)
    for p in layout["packages"]:
        print(f"package {p['index']}: title {p['title_id']:016X} kind {p['kind']} "
              f"version {p['version']} romfs_dir {p['romfs_dir']}")
        for rel in ("LD_C0_R.BIN", "LI_C0_R.IDX"):
            idx = find_file(layout, p, rel)
            if idx is None:
                continue
            e = layout["files"][idx]
            print(f"  {rel}: size {e['size']} stored {e['ext_size']} codec {e['codec']}")
            if out_dir:
                extract(nup, e, out_dir / f"pkg{p['index']}_v{p['version']}" / rel)
                print("    extracted")


if __name__ == "__main__":
    main()
