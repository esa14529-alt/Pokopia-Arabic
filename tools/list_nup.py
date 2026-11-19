import sys
from nup_extract import read_layout
L = read_layout(__import__("pathlib").Path(sys.argv[1]))
dc = L["dir_count"]
def walk(d, prefix):
    D = L["dirs"][d]
    for s in range(D["first"], D["first"] + D["count"]):
        n = L["children"][s]
        if n < dc:
            yield from walk(n, prefix + L["dirs"][n]["name"] + "/")
        else:
            f = L["files"][n - dc]
            yield prefix + f["name"], f["size"], f["codec"]
for p in L["packages"]:
    for path, size, codec in walk(p["romfs_dir"], ""):
        print(size, codec, path)
