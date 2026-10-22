# Arabic hook formulas for scholarly hadith Reels

Upgraded from ig-reel's 26 formulas for a dignified, formal-Arabic audience. A hook is read in ≤ 1.5 s
(3–8 words), is **answered by the hadith on screen**, and never promises more than the card contains.
Score with `scripts/hook_score_ar.py` (target ≥ 80; publish nothing below 65).

The v3 scorer has seven dimensions — brevity 22 · curiosity 16 · stakes 12 · second person 12 ·
specificity 12 · structure 8 · **dignity 18**. Dignity is lost for fear-framing, second-person threats,
clickbait, vagueness and shouting; a fear hook can still score, but it is punished because it is
off-brand even when it works. `--profile classic` reproduces the old weights for comparison.

| # | Formula | Pattern | Example (≥ 80) |
|---|---|---|---|
| 1 | Sufficiency challenge | هل يكفي X لِـ Y؟ | هل يكفي الحُبُّ لتكونَ من شيعتِهم؟ |
| 2 | Counted conditions | N صفات/شروط… إن فقدتَ واحدةً… | ثلاثُ صفاتٍ إن فقدتَ واحدةً فلستَ منهم |
| 3 | Exclusion stakes | مَن لم يكن X فليسَ من Y | مَن لم يُسلِّم لأمرِهم فليسَ منهم |
| 4 | Imam answers | X؟ الإمامُ Y يُجيب | من هُم شيعتُهم؟ الإمامُ الرضا يُجيب |
| 5 | Silent assumption | تحسبُ أنَّ X يكفي؟ | أتحسبُ أنَّ المحبّةَ وحدَها تكفي؟ |
| 6 | Verified-chain promise | روايةٌ صحيحةُ السَّند تقول… | روايةٌ صحيحةُ السَّند تُحدِّدُ مَن هُم شيعتُهم |
| 7 | Mortal stakes | ميتةٌ/عاقبةٌ… مَن…؟ | ميتةٌ جاهليّة… مَن يموتُها اليوم؟ |
| 8 | Definition flip | ليس X مَن… بل مَن… | ليسَ الشيعيُّ مَن أحبَّ، بل مَن أطاع |
| 9 | Test yourself | اختبِر نفسَك: هل أنتَ…؟ | اختبِر نفسَك: هل أنتَ من شيعتِهم؟ |
| 10 | One word that decides | كلمةٌ واحدةٌ تفصلُ بين X و Y | كلمةٌ واحدةٌ تفصلُ بين المحبِّ والشيعيّ |
| 11 | Imam's own criterion | هكذا عرَّفَ الإمامُ X | هكذا عرَّفَ الإمامُ الرضا شيعتَه |
| 12 | Why-question | لماذا قالَ الإمامُ…؟ | لماذا قالَ الإمامُ: «فليسَ منّا»؟ |

## Writing rules

- Formal Arabic with tashkeel on the decisive word only (the `highlight`); full tashkeel makes the hook slow.
- Second person (تكون / أنت / -ك) raises self-relevance; «هل» and «لماذا» open the loop.
- Put the Imam's name in the hook scene's `sub` line, not in the hook itself, unless the formula needs it (4, 11, 12).
- Numbers in words when ≤ 10 (ثلاثُ صفات), digits for pages/volumes only.
- Forbidden: «لن تصدق», «صادم», «عاجل», emoji, «!!», Latin, dialect (ليش / شلون / شنو), any threat the hadith does not make.
- The cover frame shows the hook (or the hero line): keep it inside the centre 4:5 crop (both engines handle this).

## Three-hook routine

1. Write one *question*, one *number/condition*, one *stakes* hook.
2. `python3 scripts/hook_score_ar.py "…" "…" "…" --out hooks.json`
3. Best → the hook scene's `line1/line2` (spec) or `hook.line1/line2` (content.json); split at the natural pause so each line ≤ 4 words when possible.
4. Keep the other two (`post_kit.py --hooks hooks.json` lists them in post.md) for the cover text A/B or a re-cut after 48 h.
