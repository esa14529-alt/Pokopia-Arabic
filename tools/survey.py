import re, sys, collections
from c0text import C0
c0 = C0("../original/LD_C0_R.BIN", "../original/LI_C0_R.IDX")
EN = set("the you and to of is your a for with this it can in on be will".split())
FR = set("le la les de vous et est pour un une des".split())
DE = set("der die das und ist sie du ein eine nicht".split())
ES = set("el la los de que y es para un una tu".split())
def lang(rows):
    words = collections.Counter(w for r in rows for w in re.findall(r"[a-zà-ÿ]+", r["text"].lower()))
    sc = {k: sum(words[w] for w in v) for k, v in dict(en=EN, fr=FR, de=DE, es=ES).items()}
    cjk = sum(1 for r in rows for c in r["text"] if '぀' <= c <= '鿿' or '가' <= c <= '힯')
    best = max(sc, key=sc.get)
    if cjk > sum(sc.values()): return "cjk"
    return best if sc[best] else "?"
tot = collections.Counter(); ent = collections.Counter(); seq = []
for slot, off, raw, t in c0.text_banks():
    l = lang(t["rows"]); tot[l] += 1; ent[l] += len(t["rows"]); seq.append((slot, l, len(t["rows"]), t["stride"]))
print(tot, ent)
print(seq[:60])
