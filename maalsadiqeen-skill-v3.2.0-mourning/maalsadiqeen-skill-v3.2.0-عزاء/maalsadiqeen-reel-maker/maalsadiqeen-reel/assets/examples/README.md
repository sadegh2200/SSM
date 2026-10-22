# Examples

## HyperFrames engine (default) — spec files

| file | archetype | length | notes |
|---|---|---|---|
| `sadiqeen-9-119.silent.json` | A (verse + ḥadīth + grading) | 45 s | exact rebuild of the delivered reel «كونوا مع الصادقين»; recitation 9:119 (`ar.mahermuaiqly`) with word cues — the gold standard |
| `hadith-only.json` | B/C (ḥadīth without a verse) | 41 s | «النَّاسُ أَعْدَاءُ مَا جَهِلُوا»; quote with word reveal, contrast, list, proof without seal |
| `ashura-mourning.silent.json` | **E** (مناسبت) | 36.5 s | the **mourning** palette end to end: charcoal paper, ivory text, inverted logo, and an ending with **no invitation** (verse + card). `verify` 16 ok · 0 warnings |
| `long-text-sadiq.silent.json` | **G** (شرحٌ متدرّج) | 53.5 s | a long-text reel: `paragraph` + `definition` + `qa` carry 3 sentences each; the prose is budgeted at 0.30 s/word, `copy_lint` 0 failures, `verify --light` 14 ok · 0 warnings |
| `*.sheet.jpg`, `hadith-only.beat-sheet.md` | — | — | contact sheet / beat sheet produced from these specs |

```bash
source scripts/env.sh
python3 scripts/build_reel.py assets/examples/sadiqeen-9-119.silent.json --out "$REEL_WORK/demo"
python3 scripts/copy_lint.py assets/examples/long-text-sadiq.silent.json       # 0 failures
python3 scripts/build_reel.py assets/examples/long-text-sadiq.silent.json --out "$REEL_WORK/demo-long"
python3 scripts/build_reel.py assets/examples/ashura-mourning.silent.json --out "$REEL_WORK/demo-mourning"  # theme: mourning
python3 scripts/mix.py "$REEL_WORK/demo" && python3 scripts/verify.py "$REEL_WORK/demo"
```

## Remotion studio engine (alternate) — `content.json` + generated `plan.json`

| folder | cards | scenes | length | notes |
|---|---|---|---|---|
| `shiatuna/` | 4 (ḥadīth · traits · sanad · sources) | hook · hadith · points(3) · sanad(7) · cta | 46 s | reproduces the delivered reel «شيعتنا المسلمون لأمرنا»; `preview-contact-sheet.jpg` is its render |
| `variant-bayan/` | 3 (ḥadīth · explanation · sanad) | hook · hadith · bayan · sanad(4) · cta | 42 s | **layout fixture** — verify the narration text, chain and pages against the sources before publishing |

```bash
python3 scripts/plan.py assets/examples/shiatuna/content.json          # regenerate the plan
python3 scripts/render.py --studio ~/reel-studio --content assets/examples/shiatuna/content.json
```
