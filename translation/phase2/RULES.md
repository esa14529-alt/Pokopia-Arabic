# Phase 2 translation rules (item names + descriptions)

Read `D:\Games\Pokopia-Arabic\translation\glossary.md` first; its terms are binding.

Input `batch_NN.en.json` is a list of `{"id", "en"}`. Output `batch_NN.ar.json` is a list of
`{"id", "ar"}` with every id, in UTF-8 and with `ensure_ascii=False`. Write the Arabic in normal
logical order. The build tool shapes and reorders it.

## Tags
Anything in `<...>` is a game code: copy it exactly, the same number of times. Examples are
`<br>`, `<$cdef(27)>`, `</color>`, `<fcap>`, `<iart;0()>`, `<fqty(1)>`, `<class>`,
`<$ifull;0(lnum1)>`, `<ininameicon>`, `<oneline>` and `<$cname;1(184)>`. Keep the same
number of `<br>` (line breaks). Keep each Arabic line about as long as the English line,
because boxes are narrow. A colour span `<$cdef(27)>...</color>` should still wrap the Arabic
word that corresponds to the English one. Tags that insert names
(`$pkname`, `$ifull`, `$iname`, `$cname`, `$etpname`, …) insert a noun, so build the Arabic
sentence around it.

## Item names
- Items usually come in pairs or quads: singular, plural, sometimes a "piece of
  <ininameicon>X" form. Give the Arabic plural for plurals (خشب / أخشاب, كرسي / كراسي).
  The forms of one item must stay consistent with each other.
- Use the indefinite form without ال (`كرسي خشبي`, not `الكرسي الخشبي`), because the game
  inserts names into sentences.
- Keep in Latin script: Pokémon species names, Poké Ball types (Poké Ball,
  Great Ball, …), and brand or product names (Nintendo, Joy-Con).
  Pikachu doll → دمية Pikachu. Pewter City → مدينة Pewter: translate the generic word, keep
  the proper name in Latin.
- Translate everything else: furniture, materials, food, plants, fossils (Armor Fossil →
  حفرية الدرع), badges, and titles in “quotes” (keep the Arabic quotes « » or “ ”).
- (upper)/(middle)/(lower)/(corner) → (علوي)/(أوسط)/(سفلي)/(زاوية).
- Keep names short. Prefer common everyday Arabic words.

## Descriptions and Pokémon chatter
Use friendly, simple Modern Standard Arabic for all ages. Sound effects like *munch munch*
become Arabic onomatopoeia (*قضم قضم*, *شم شم*, *تثاؤب*). Keep "..." and "♪" as they are.

## Process
1. Write the translation as one or more Python scripts in the scratchpad folder you are
   given. Each script writes or extends the `.ar.json` file. Do not paste the whole output
   into chat.
2. Run `cd D:\Games\Pokopia-Arabic\tools && py validate_batch.py ../translation/phase2/batch_NN`
   (no `-I`, with `PYTHONIOENCODING=utf-8`) until it reports 0 problems and 0 unknown ids.
3. Reply in at most 150 words: the counts, and the ids you are unsure about with a short
   reason. Do not quote long game text.
