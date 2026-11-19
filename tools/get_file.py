import sys
from pathlib import Path
from nup_extract import read_layout, find_file, extract
nup = Path(sys.argv[1]); L = read_layout(nup); p = L["packages"][0]
for rel in sys.argv[2:]:
    i = find_file(L, p, rel); extract(nup, L["files"][i], Path("../original") / rel); print("ok", rel)
