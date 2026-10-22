# ریل‌ساز مع الصادقین — Maalsadiqeen Reel Maker

**پوشهٔ اصلی اسکیل نهایی.** یک اسکیل ایجنت (استاندارد `SKILL.md`) که **هر متن** (یا ورق‌های برند صفحهٔ
«مع الصادقين» @maalsadiqeen) را به ریل عمودی ۳۰–۶۰ ثانیه‌ای، باوقار و آمادهٔ انتشار تبدیل می‌کند — با
چهار سناریوی پیشنهادی و گیت انتخاب، تلاوت، طراحی صدا، گیت کیفیت، رندر و کیت انتشار سه‌پلتفرمی.

| | |
|---|---|
| **عنوان** | ریل‌ساز مع الصادقین · Maalsadiqeen Reel Maker |
| **نام فنی اسکیل** (`name` در frontmatter، نام پوشهٔ قابل نصب) | `maalsadiqeen-reel` |
| **نسخه** | 3.2.0 — نسخهٔ ۳ کامل + **پایانِ تازهٔ ریل** (حداکثر یک دعوت، هیچ دعوت برای متن سنگین) و **دو پالت: اصلی و ایام عزاداری** |
| **موتور پیش‌فرض / جایگزین** | HyperFrames 0.8 / Remotion 4 (داخل همین اسکیل) |
| **خروجی** | MP4 ۱۰۸۰×۱۹۲۰ (۳۰ fps، ≤ ۶۰ s) + کپشن IG/FB/X + بانک ۷ کامنت + برنامهٔ انتشار + `validation.md` (کاور فقط با `--cover`) |

## ساختار این پوشه

```
maalsadiqeen-reel-maker/            ← پوشهٔ اصلی (شما اینجا هستید)
├── README.md                        ← همین راهنما
├── REVIEW-fa.md                     ← گزارش بازبینی دو اسکیل قبلی بر اساس ۷ اسکیل مرجع و تصمیم‌های ادغام
├── UPGRADE-PLAN-fa.md               ← نقشهٔ ارتقا و گزارش فازها
├── skills/                          ← دو ابزار درون‌سازمانی (نصب می‌شوند، مثل اسکیل اصلی)
│   ├── arabic-editor/               ← ویرایش فصحی: ثبت، املاء، اعراب، نشانه‌گذاری + ar_copycheck.py
│   └── hadith-sanad/                ← متن/سند/تخریج/درجه + sanad_check.py
└── maalsadiqeen-reel/               ← خودِ اسکیل — این پوشه را نصب کنید
    ├── SKILL.md                     ← دستورالعمل ایجنت (ورودی متن، چهار سناریو، گیت، ساخت، کیت)
    ├── config/                      ← brand.json (تنظیمات زمان اجرا) + content-log.json (گارد تنوع)
    ├── references/                  ← هویت برند و مخاطب، ورودی متن، سناریوها، سری، پلتفرم‌ها، کامنت‌ها + بلوک‌ها/روایت/صدا (بازنویسی‌شده برای متن‌محوری)
    ├── scripts/                     ← ۲۸ اسکریپت پایتون + ۳ شل (Python ≥ 3.9)
    ├── assets/                      ← فونت‌ها، لوگو، افکت‌ها، GSAP، نمونه‌ها، قالب‌ها، قالب Remotion
    ├── evals/                       ← ۱۲ سناریوی آزمون + روبریک + فیکسچرهای متنی
    └── agents/openai.yaml · LICENSE
```

## نصب

```bash
# Claude Code (پروژه‌ای)            → .claude/skills/maalsadiqeen-reel/SKILL.md
mkdir -p .claude/skills && cp -r maalsadiqeen-reel-maker/maalsadiqeen-reel .claude/skills/

# Codex / Copilot / Gemini CLI و بقیه (مسیر مشترک)
mkdir -p ~/.agents/skills && cp -r maalsadiqeen-reel-maker/maalsadiqeen-reel ~/.agents/skills/

# یا مستقیم از گیت‌هاب
npx skills add sadegh2200/my --skill maalsadiqeen-reel
```

در همین مخزن، اسکریپت `install-skill.sh` (ریشهٔ مخزن) همین کار را برای هر سه مسیر انجام می‌دهد و کپی را
بایت‌به‌بایت با نسخهٔ مادر مقایسه می‌کند: `bash install-skill.sh` برای نصب/همگام‌سازی و
`bash install-skill.sh --check` برای بررسی. نسخهٔ مادر همان `maalsadiqeen-reel-maker/maalsadiqeen-reel/` است؛
فقط آن را ویرایش کنید و اسکریپت را دوباره اجرا کنید.

اسکریپت، دو ابزار درون‌سازمانی (`arabic-editor` و `hadith-sanad`) و چهار اسکیل مکمل را هم نصب می‌کند
(`skill-creator`، `ig-reel`، `virat-design`، `instagram-growth`)؛ جزئیات و قاعدهٔ تقدم در
[`vendor/skills/README.md`](../vendor/skills/README.md).

پیش‌نیازها را `scripts/env.sh` خودش بررسی می‌کند و دستور نصبِ هر چیزِ کم را چاپ می‌کند: Python ≥ 3.9 با
`numpy` و `pillow`، `ffmpeg/ffprobe`، Node ≥ 22 و `hyperframes@0.8.157` (+ Chrome Headless Shell با
`npx hyperframes browser ensure`). برای موتور جایگزین: `scripts/setup_studio.py` (Remotion 4).

## چطور صدا کنید

ورق‌ها را پیوست کنید و بنویسید: «از این ورق‌ها یک ریل برای مع الصادقین بساز». دستیار خودش اسکیل را فعال
می‌کند (کلیدواژه‌ها: ریل، reel، مع الصادقین، maalsadiqeen، ورق/پست، حدیث/آیه، اینستاگرام). اگر نوع خاصی
می‌خواهید بگویید: «نسخهٔ B هوک»، «برش ۴:۵»، «۳۵ ثانیه برای مناسبت»، «با گوینده» (فقط اگر واقعاً گوینده
بخواهید)، «با Remotion» (اگر موتور جایگزین را می‌خواهید).

## چه چیزی می‌گیرد، چه چیزی می‌دهد

- **ورودی:** هر متن (کوتاه یا بلند، حتی یک فصل کتاب یا متن سخنرانی) یا یک/چند ورقِ برند — با آیه یا
  بی‌آیه؛ حدیث، قول عالم، سؤال، مناسبت یا ردّ شبهه.
- **خروجی:** ریل عمودی ۱۰۸۰×۱۹۲۰ (۳۰ تا ۶۰ ثانیه، پیش‌فرض ۴۰)، سه کپشن بومی، بانک هفت کامنت با
  زمان‌بندی، برنامهٔ انتشار و `validation.md`؛ کاور و ۴:۵ فقط با درخواست.
- **پایان ریل:** حداکثر **یک** دعوت، و فقط اگر متن آن را سزاوار باشد: «احفظها للعودة» برای تعریف و
  سند، «أرسلها لمن سألك عنها» برای پاسخ، و **هیچ دعوتی** برای مناسبت، سیره، ردّ شبهه و حکم. جملهٔ
  «أرسلها لمن تحب» حالا در `copy_lint` **خطا** می‌دهد.
- **دو پالت:** `main` (کاغذ کرمی — پیش‌فرض) و `mourning` (مشکی گرم `#0e0f0e`، عاجی، طلایی کم‌رنگ؛
  برای محرم و صفر) — با `--theme mourning` یا `"theme": "mourning"` در spec.
- **متن بلند:** ۷۰۰ تا ۱۸۰۰ کلمه با یک ایده، در همان ۶۰ ثانیه — با شش بلوک بلند (`paragraph`،
  `definition`، `steps`، `timeline`، `compare`، `qa`) و شش الگوی روایی G–L؛ متن بلندتر از یک ایده
  می‌شود سری (`references/series.md`).
- **سیاست صدا:** بدون گویندهٔ انسانی/مصنوعی (مگر خودتان بخواهید)؛ تلاوت قرآن وقتی آیه هست؛ طراحی صدا +
  بستر ملایم؛ مسترینگ −۱۵٫۵ LUFS. ویدیو باید بی‌صدا هم کامل فهمیده شود.

## مسیر کار (موتور پیش‌فرض)

| مرحله | ابزار | نتیجه |
|---|---|---|
| ۰ | `bash scripts/bootstrap.sh --check` + `source scripts/env.sh` | مسیرها + بررسی ابزارها و دستور نصب |
| ۱ | `reel.py intake` + `references/text-intake.md` | بریف: یک ایده، سه لایه، أثر در زندگی، شکل (ریل/سری) + هشدارهای منبع |
| ۲ | `reel.py plan --finalize` + `references/scenarios.md` | چهار سناریو با هشت زاویه، امتیاز، پیش‌نمایش سه‌فریمی — **توقف تا انتخاب شما** |
| ۳ | `reel.py build --choose N` | `copy_lint` → `build_reel.py` → `mix.py` → `verify.py --light --source-spec` → کیت |
| ۴ | `social_kit.py` (خودکار در ساخت) | کپشن IG/FB/X + ۷ کامنت زمان‌بندی‌شده + `publish.md` + `validation.md` |
| ۵ | `render.sh` + `verify.py --render` | رندر ۱۰۸۰×۱۹۲۰ و بررسی فنی خروجی |
| ۶ | `export_variants.py` + `beat_sheet.py` | SRT/متن جایگزین/[کاور]، بیت‌شیت فارسی، خلاصهٔ فارسی |

## الگوهای روایی (پیش‌فرض بر اساس محتوای ورق)

- **A** سؤال → جواب معصوم (آیه + حدیث + سند) — همان ساختار ریل «کونوا مع الصادقین».
- **B** یک کلمه معنا را عوض می‌کند (فقط حدیث). **C** تصحیح یک تصور (قول عالم/مفهوم).
- **D** سؤال → جواب (پرسش رایج). **E** مناسبت (ولادت/شهادت/عید). **F** ردّ شبهه (آرام و مستند).

## موتور جایگزین: Remotion studio

برای کاروسل‌های «حدیث + صفات شماره‌دار + سلسلهٔ سند» (مثل ریل «شیعتنا المسلّمون لأمرنا») قالب Remotion
صحنه‌های اختصاصی دارد: زنجیرهٔ راویان با مهر «ثقة»، مُهر نتیجه، چیپ‌های پیشرفت. دستورالعمل کامل در
`maalsadiqeen-reel/references/remotion-studio.md` و اسکیمای `content.json` در `remotion-schema.md`؛ قالب در
`assets/remotion-template/` و نمونه‌ها در `assets/examples/shiatuna/` و `variant-bayan/`.

## خطوط قرمز

۱) بدون گوینده مگر به درخواست شما. ۲) هیچ منبع یا درجهٔ سندی ساخته نمی‌شود؛ اگر روی ورق نیست، بلوک «سند» حذف
می‌شود و به شما گفته می‌شود. ۳) متن آیه/حدیث عیناً از ورق، با اعراب؛ کلمهٔ ناخوانا علامت‌گذاری می‌شود.
۴) حداکثر ۶۰ ثانیه. ۵) قبل از رندر، همیشه `verify.py` و دیدن فریم‌ها. ۶) رنگ قرمز هرگز؛ فقط کاغذ، سبز، طلایی.

## اجرای سریع نمونه‌ها

```bash
cd maalsadiqeen-reel-maker/maalsadiqeen-reel
source scripts/env.sh
python3 scripts/build_reel.py assets/examples/sadiqeen-9-119.silent.json --out "$REEL_WORK/demo"   # بازسازی ریل ۴۵ ثانیه‌ای
python3 scripts/mix.py "$REEL_WORK/demo" && python3 scripts/verify.py "$REEL_WORK/demo"
bash scripts/render.sh "$REEL_WORK/demo" "$REEL_DELIVER/demo.mp4"
```

نمونهٔ دوم: `assets/examples/hadith-only.json` → ریل ۴۱ ثانیه‌ای بدون آیه («النَّاسُ أَعْدَاءُ مَا جَهِلُوا»).

## چه چیزی آزمایش شده و چه چیزی باید در محیط شما یک‌بار اجرا شود

کل مسیر پایتونی هر دو موتور (build → mix → verify → بیت‌شیت/کاور/پست‌کیت؛ plan/validate/make_audio؛ `tsc` و
`remotion bundle` قالب؛ `hyperframes lint`) آزمایش شده است — جزئیات در `REVIEW-fa.md`. آنچه نیاز به مرورگر
یا اینترنت دارد (`hyperframes check/snapshot/render`، `remotion render`، دانلود تلاوت) باید یک‌بار در محیط
خودتان اجرا شود؛ `env.sh` می‌گوید چه چیزی کم است.
