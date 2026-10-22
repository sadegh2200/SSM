# Reading the sheets («الورق») and choosing the story

> **Two doors, one room.** Since v3 the input can also be plain text — a book page, a lecture
> transcript, a forwarded message, a question. That path has its own contract in
> `references/text-intake.md`; run `scripts/intake.py` first and come back here at §3
> (classification) with the extracted quotes. Everything below also applies to a transcribed sheet.

## 1. Transcribe faithfully

For each sheet, write down (in a scratch file, never from memory):

1. **Sacred text** — Qurʾanic verse(s) with sūrah:āyah; ḥadīth text with the speaker (معصوم) named.
2. **Chain / grading** — book, volume, page, grading words («صحيح السند», «معتبر», «موثّق», «مرسل»).
3. **Scholarly comment** — who (العلّامة المجلسي، الشيخ المفيد …), which book, what exactly he says.
4. **The page's own framing** — headline, the question it poses, its concluding line.
5. **Visible brand cues** — handle, logo, series name, any date/occasion.

Keep the exact wording with tashkeel when present. If a word is unreadable, mark it `[?]` and say so
to the user — never "repair" a sacred text by guessing. Verify a verse against a Muṣḥaf text source if
you have web access (quran.com / tanzil.net wording) and the ḥadīth reference format against the
sheet; if the sheet gives no reference, say that the reel will omit the «proof» block unless the user
supplies one.

## 2. Classify the content

| class | what the sheets contain | default archetype (see narrative.md) |
|---|---|---|
| A — آية + حديث + توثيق | verse, an Imam's explanation, chain grading | **سؤال → جواب المعصوم** (the proven 6-scene structure) |
| B — حديث فقط | a ḥadīth with reference, no verse | **كلمة واحدة تغيّر المعنى** or **موقف/قصة** |
| C — قول عالم / تحقيق | a scholar's analysis, lexical point, chain discussion | **تصحيح مفهوم** |
| D — مسألة / سؤال شائع | a question people ask, with a short answer | **سؤال → جواب** (answer may be a list) |
| E — مناسبة | a date (ولادة/شهادة/عيد/غدير/عاشوراء), a name, a short text | **مناسبة** (title + quote + cta) |
| F — ردّ شبهة | an objection and its refutation | **تصحيح مفهوم** with a contrast block, tone extra calm |

Mixed sheets: pick the class of the *strongest single piece of evidence* (a graded ḥadīth beats a
scholar's paraphrase; a verse beats both as an opener but cannot carry the reel alone).

## 3. Find the one idea

Write one sentence: «المشاهد سيخرج وقد عرف أنّ ______». If you cannot write it in ≤ 14 words, the
reel is about two things — split it into two reels. Then find:

- **the hinge word** — the single word on which the meaning turns (مَعَ in 9:119, «الصادقين» vs
  «صادقين»; in a ḥadīth it is often a particle, a restriction «إنّما», or a number);
- **the surprise** — what the educated viewer assumes vs what the text says;
- **the authority** — who settles it (المعصوم > الكتاب المعتمد > العالم);
- **the take-away line** — ≤ 6 words, usually the sacred text itself or a 2-word slogan.

## 4. Decide what is NOT in the reel

A 45 s reel holds ~55–70 words of on-screen text. Typical cuts: secondary references (keep max 2
cards), lexical digressions, the second half of a long ḥadīth (quote the decisive sentence and cite the
rest), parallel verses. Put the overflow into the caption (publish.md), not on screen.

## 5. Hand-off to the scenario

Fill this brief before writing scenes (keep it in `brief.md` next to the spec):

```
فكرة واحدة:        …
الصنف:             A/B/C/D/E/F  →  النموذج: …
كلمة المفصل:       …
المفاجأة:          الظنّ: …  /  النصّ: …
الحجّة:            من؟ أين؟ (كتاب ج ص، درجة السند)
سطر الختام:        …
ما يُحذف:          …
الصوت:             تلاوة؟ (سورة:آية، القارئ)  /  بلا تلاوة → تصميم صوتي فقط
```

Then go to `narrative.md` for the beat sheet and `arabic-copy.md` for the wording.
