"""Convert logical Arabic game text (with <tags>) to the visual left-to-right
form the game draws, keeping every tag intact.

Each line (split on <br>, <clear>, <slide>) is shaped and reordered on its own.
Tags become bidi-neutral placeholders during reordering; paired colour tags
swap ends afterwards because reordering reverses them.
"""
import re

import arabic_reshaper
from bidi.algorithm import get_display

TAG = re.compile(r"<[^<>]*>")
LINE_BREAKS = re.compile(r"(<br>|<clear>|<slide>)")
# Zero-width performance tags: moved to the start of their line.
CONTROL = re.compile(r"<\$(voicel|facial|motion|emotion|comeff)\([^>]*\)>|<oneline>")
OPEN_COLOR = re.compile(r"<\$cdef\(\d+\)>")
CLOSE_COLOR = "</color>"
PH_BASE = 0x2500  # box-drawing block: bidi class ON, never in game text
# <qty;n(singular,plural)> carries its words inside the tag; give them Arabic forms.
QTY = re.compile(r"<qty;(\d+)\(([^,()]*),([^,()]*)\)>")
QTY_WORDS = {"CD": "أسطوانة", "CDs": "أسطوانات", "bunch of": "حزمة من", "bunches of": "حزم من",
             "dish": "طبق", "dishes": "أطباق", "it": "إياه", "them": "إياها",
             "patch": "رقعة", "patches": "رقع", "tree": "شجرة", "trees": "أشجار",
             "type": "نوع", "types": "أنواع",
             "Jump": "قفزة", "Jumps": "قفزات", "jump": "قفزة", "jumps": "قفزات",
             "Life Coin": "عملة حياة", "Life Coins": "عملات حياة",
             "Prism Scale": "حرشفة موشورية", "Prism Scales": "حراشف موشورية",
             "Syrupy Apple": "تفاحة معسّلة", "Syrupy Apples": "تفاحات معسّلة",
             "shining wish note": "ورقة أمنيات لامعة", "shining wish notes": "أوراق أمنيات لامعة",
             "cluster of": "مجموعة من", "clusters of": "مجموعات من",
             "piece of": "قطعة من", "pieces of": "قطع من", "piece": "قطعة", "pieces": "قطع",
             "day": "يوم", "days": "أيام", "time": "مرة", "times": "مرات",
             "feather": "ريشة", "feathers": "ريشات", "fragment": "قطعة", "fragments": "قطع",
             "gift": "هدية", "gifts": "هدايا", "level": "مستوى", "levels": "مستويات",
             "point": "نقطة", "points": "نقاط", "set": "طقم", "sets": "أطقم",
             "thing": "شيء", "things": "أشياء",
             "It": "هو", "They": "هي", "they": "هي", "’em": "إياها",
             "This": "هذا", "These": "هذه", "this": "هذا", "these": "هذه",
             "That": "ذلك", "Those": "تلك", "that": "ذلك", "those": "تلك",
             "THAT": "ذلك", "THOSE": "تلك", "Thith": "هذا", "Theeth": "هذه",
             "is": "هو", "are": "هي", "ith": "هو", "isn’t": "ليس", "aren’t": "ليست",
             "was": "كان", "were": "كانت", "It was": "كان", "They were": "كانت",
             "it was": "كان", "they were": "كانت", "That was": "كان ذلك",
             "It really was": "كان حقاً", "They really were": "كانت حقاً",
             "It’s": "إنه", "They’re": "إنها", "it’s": "إنه", "they’re": "إنها",
             "lasts": "يدوم", "last": "تدوم", "tastes": "طعمه", "taste": "طعمها"}

_reshaper = arabic_reshaper.ArabicReshaper({"delete_harakat": True})


def _line(text: str, carry: str | None) -> tuple[str, str | None]:
    """Convert one line; `carry` is the colour tag still open from the previous line.
    Returns the visual line and the colour left open for the next one."""
    controls = "".join(m.group(0) for m in CONTROL.finditer(text))
    text = CONTROL.sub("", text)
    tags = []

    def hold(m):
        tags.append(m.group(0))
        return chr(PH_BASE + len(tags) - 1)

    held = TAG.sub(hold, text)
    if not re.search(r"[؀-ۿ]", held):
        for t in tags:
            carry = t if OPEN_COLOR.fullmatch(t) else None if t == CLOSE_COLOR else carry
        return controls + text, carry
    tags = [_qty(t) for t in tags]
    # Pair colour tags within the line; unpaired ones belong to spans crossing a line break.
    pair, stack, loose_close = {}, [], []
    for i, t in enumerate(tags):
        if OPEN_COLOR.fullmatch(t):
            stack.append(i)
        elif t == CLOSE_COLOR:
            if stack:
                j = stack.pop(); pair[i] = j; pair[j] = i
            else:
                loose_close.append(i)
    loose_open = stack
    visual = get_display(_reshaper.reshape(held), base_dir="R")
    # Reordering reverses spans, so a colour span now reads close ... open.
    out = []
    for ch in visual:
        i = ord(ch) - PH_BASE
        if not 0 <= i < len(tags):
            out.append(ch)
            continue
        tag = tags[i]
        if i in pair:
            tag = tags[pair[i]] if tag == CLOSE_COLOR else CLOSE_COLOR
        elif i in loose_close:      # end of a span begun on the previous line
            tag = carry or "<$cdef(27)>"
        elif i in loose_open:       # span continues onto the next line
            tag = CLOSE_COLOR
        out.append(tag)
    line = "".join(out)
    if loose_close:
        line += CLOSE_COLOR
    elif carry:                     # the whole line sits inside a carried span
        line = carry + line + CLOSE_COLOR
    if loose_open:
        line = tags[loose_open[-1]] + line
        return controls + line, tags[loose_open[-1]]
    return controls + line, None if loose_close else carry


def _qty(tag: str) -> str:
    m = QTY.fullmatch(tag)
    if not m or m.group(2) not in QTY_WORDS:
        return tag
    one, many = (_line(QTY_WORDS[w], None)[0] for w in m.group(2, 3))
    return f"<qty;{m.group(1)}({one},{many})>"


def _matching_open(tags, close_index):
    depth = 0
    for j in range(close_index - 1, -1, -1):
        if tags[j] == CLOSE_COLOR:
            depth += 1
        elif OPEN_COLOR.fullmatch(tags[j]):
            if depth == 0:
                return tags[j]
            depth -= 1
    return "<$cdef(27)>"


def to_visual(text: str) -> str:
    out, carry = [], None
    for p in LINE_BREAKS.split(text):
        if LINE_BREAKS.fullmatch(p):
            out.append(p)
        else:
            line, carry = _line(p, carry)
            out.append(line)
    return "".join(out)


def tag_signature(text: str) -> list[str]:
    return sorted(TAG.findall(text))
