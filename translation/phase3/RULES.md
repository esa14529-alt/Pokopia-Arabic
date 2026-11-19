# Phase 3 translation rules (dialogue and story)

Read these first. Their terms and tag rules are binding:
- `D:\Games\Pokopia-Arabic\translation\glossary.md`
- `D:\Games\Pokopia-Arabic\translation\phase2\RULES.md`

Input `batch_NN.en.json` is a list of `{"id", "en"}`. Output `batch_NN.ar.json` is a list of
`{"id", "ar"}` with every id, in UTF-8, written with `ensure_ascii=False`. Write the Arabic in
normal logical order. The build tool shapes the letters and reorders them.

## Tags
- Copy every `<...>` tag exactly, the same number of times. That includes the performance tags
  (`<$voicel(..)>`, `<$motion(..)>`, `<$emotion(..)>`, `<$facial(..)>`, `<$comeff(..)>`,
  `<wait(..)>`, `<$voicev(..)>`), the layout tags (`<br>`, `<clear>`, `<slide>`, `<oneline>`)
  and the name and colour tags.
- Keep performance tags in roughly the same sentence as in the English.
- `<br>` is a hard line break and the game does not wrap text. Keep the same number of `<br>`,
  and keep each Arabic line no longer than its English line, measured in characters without
  tags. Shorten the wording if needed.
- `<clear>` starts a new text box.
- Name tags insert text:
  - `<pname;..>` is the player's name.
  - `$cname`, `$pkname`, `nowner` and `acqpname` insert names of Pokémon or people.
  - `$iname` and `$ifull` insert item names, which are already Arabic and have no ال.
  - `$hatname` inserts a habitat name and `$bname` a building name.
  - `$spwname` and `$spwfull` insert a specialty word. Write it as a label, for example
    «تخصص X» or «مهارة X», never as the sentence's own verb.
- Leftover English suffixes glued to a tag (`'s`, `s`, `ing`) can be dropped and the sentence
  rephrased.

## Style
- Friendly, simple Modern Standard Arabic suitable for all ages.
- Keep each character's voice: casual Pokémon talk, a polite professor, sleepy drawn-out
  speech and so on. Turn English slang and contractions ("meetcha", "gonna", "bud") into
  natural, light Arabic (يا صديقي، سأفعل).
- Interjections become Arabic interjections: أوه، واو، همم، آه. Keep "..." and "♪".
- Keep Pokémon species names and Poké Ball types in Latin script. Move names are Arabic (see tools/move_names.py).

## Process
1. Write the translation as Python scripts in the scratchpad folder you are given. Split the
   work into parts of about 100 entries each. Each script writes or extends the `.ar.json`.
   Do not paste the whole output into chat.
2. Run `cd D:\Games\Pokopia-Arabic\tools && py validate_batch.py ../translation/phase3/batch_NN`.
   Use `PYTHONIOENCODING=utf-8` and do not use `-I`. Repeat until it reports 0 problems and
   0 unknown ids.
3. Reply in at most 120 words: the counts, and the ids you are unsure about. Do not quote long
   game text.
