"""Locate English text banks (2nd bank of each 9-language group)."""
from c0text import C0

def english_banks(c0: C0):
    slots = {s: t for s, o, r, t in c0.text_banks()}
    order = sorted(slots)
    en, i = [], 0
    while i < len(order):
        grp = order[i:i + 9]
        n = slots[grp[0]]["count"]
        if len(grp) == 9 and grp[-1] - grp[0] == 8 and all(slots[x]["count"] == n for x in grp):
            en.append(grp[1]); i += 9
        else:
            i += 1
    return {s: slots[s] for s in en}
