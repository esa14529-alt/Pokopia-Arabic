# Pokopia Arabic — تعريب Pokémon Pokopia

تعريب من المعجبين للعبة **Pokémon Pokopia** (Nintendo Switch 2)، يعمل كمود LayeredFS على محاكي Eden / Fritchii.
A fan Arabic translation of Pokémon Pokopia, delivered as a LayeredFS mod.

> هذا المستودع **لا يحتوي على أي ملف من ملفات اللعبة**. تحتاج نسختك الخاصة من اللعبة، وأدوات البناء تستخرج منها الملفات اللازمة وتبني المود محلياً.
> This repo contains no game files. You need your own copy; the build reads it and produces the mod locally.

## ما المترجم / Status
| الجزء | الحالة |
|---|---|
| القوائم والواجهة | ✅ |
| أسماء الأدوات وأوصافها | ✅ |
| المهام والنصائح | ✅ |
| الحوارات والقصة | 🔄 قيد العمل |

خط عربي مضاف إلى خطوط اللعبة: [Baloo Bhaijaan 2](arfont/OFL.txt) (رخصة SIL OFL).

## البناء / Build
المتطلبات: Python 3.11+ مع `numpy`, `Pillow`, `fonttools`, `arabic-reshaper`, `python-bidi`.

```powershell
cd tools
py setup_originals.py "D:\path\to\Pokopia.nup"      # يقرأ فقط ولا يعدّل اللعبة
$env:POKOPIA_MOD_DIR = "<emulator>\user\load\0400A3A01EE4C000\Arabic\romfs"
py build_mod.py                                    # الخطوط + النصوص
py build_mod.py --text-only                        # النصوص فقط (أسرع)
```
ثم فعّل مود **Arabic** من إعدادات اللعبة في المحاكي.

## الترجمة / Translating
- `translation/glossary.md` — القاموس الموحد للمصطلحات.
- `translation/phase*/RULES.md` — قواعد الوسوم (`<br>`, `<$cname..>` …) والأسلوب.
- `translation/phase*/batch_NN.ar.json` — الترجمات العربية لكل دفعة.
- `tools/merge_translations.py` يجمعها في `translation/ar.json` الذي يقرؤه البناء.
- `tools/validate_batch.py` يتحقق من الوسوم وعدد الأسطر.

## أدوات إضافية / Extras
- `PP_Lock.bat` — يبقي شريط الطاقة (PP) ممتلئاً أثناء اللعب (يعمل على ذاكرة المحاكي، لا يعدّل ملفات اللعبة).
- `tools/trainer.py` — باحث ذاكرة بسيط لتعديل القيم (مثل عدد القطع المعدنية).

## إخلاء مسؤولية / Disclaimer
مشروع معجبين غير رسمي وغير مرتبط بـ Nintendo أو The Pokémon Company أو Game Freak.
Pokémon and Pokopia are trademarks of their respective owners.
