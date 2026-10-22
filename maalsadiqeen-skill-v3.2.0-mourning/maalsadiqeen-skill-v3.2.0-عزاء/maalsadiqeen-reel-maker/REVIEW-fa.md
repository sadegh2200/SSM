# بازبینی دو اسکیل «مع الصادقین» و تحویل اسکیل نهایی

**تاریخ:** ۱۴ اکتبر ۲۰۲۶ · **ورودی:** `maalsadiqeen-1/` (موتور Remotion) و `maalsadiqeen-reel/` (موتور HyperFrames) ·
**مرجع بازبینی:** ۷ اسکیل برتر دانلودشده در همین مخزن (`skill-creator`، `writing-skills`، `writing-for-agents`،
`motion-graphics`، `remotion-best-practices`، `ig-reel`، `viral-instagram-reels`) · **خروجی:** یک اسکیل نهایی با عنوان
«ریل‌ساز مع الصادقین» (Maalsadiqeen Reel Maker) در پوشهٔ اصلی `maalsadiqeen-reel-maker/` — خودِ اسکیل:
`maalsadiqeen-reel-maker/maalsadiqeen-reel/` (نام فنی `maalsadiqeen-reel`، نسخهٔ ۲.۰).

---

## ۱) وضعیت اولیه — دو اسکیل برای یک کار

| | `maalsadiqeen-1` | `maalsadiqeen-reel` |
|---|---|---|
| موتور | Remotion 4 (قالب React داده‌محور) | HyperFrames 0.8 (HTML + GSAP از روی spec) |
| ورودی داده | `content.json` → `plan.py` → `plan.json` | `spec.json` → `build_reel.py` |
| فایل‌ها | ۶ مرجع، ۹ اسکریپت، قالب Remotion (۲٫۵ MB) | **همهٔ فایل‌های `maalsadiqeen-1` بایت‌به‌بایت + ** ۱۰ مرجع، ۱۲ اسکریپت، فونت/افکت/لوگو، evals |
| `name` در frontmatter | `maalsadiqeen-reel` | `maalsadiqeen-reel` |
| تفاوت واقعی | فقط `SKILL.md` (دو «درِ ورودی» متفاوت روی یک مجموعه فایل) | |

یعنی عملاً دو اسکیل با **یک نام**، دو دستورالعمل متناقض، و مجموعه‌ای از فایل‌های تکراری و حتی متناقض (پالت رنگ،
هدف بلندی صدا، ناحیهٔ امن) وجود داشت. هر ایجنتی که هر دو را بارگذاری می‌کرد، با تداخل trigger و دو گردش‌کار
ناسازگار روبه‌رو می‌شد.

## ۲) آنچه هر اسکیل مرجع می‌گوید و وضعیت دو اسکیل در برابر آن

| مرجع | قاعدهٔ کلیدی | وضعیت قبلی | اقدام در اسکیل نهایی |
|---|---|---|---|
| **skill-creator** (Anthropic) | description = مکانیزم trigger؛ «کمی pushy» باشد؛ بدنهٔ SKILL.md < ۵۰۰ خط؛ progressive disclosure؛ مراجع یک‌سطحی؛ evals با فایل‌های واقعی؛ اسکریپت‌ها تست‌شده و با خطای واضح | description اسکیل ۱ «چه می‌کند» بود نه «کی فعال شو»؛ evals به `evals/files/sheet-1..3.jpg` اشاره می‌کرد که **در مخزن وجود ندارند**؛ دو اسکریپت اصلاً اجرا نمی‌شدند (پایین‌تر) | description واحدِ trigger-first با کلیدواژه‌های فارسی/عربی/انگلیسی (۶۸۹ کاراکتر)؛ SKILL.md = ۱۷۲ خط؛ ۱۳ مرجع همگی مستقیم از SKILL.md؛ `evals/files/README.md` + eval شمارهٔ ۵ که بدون فایل خصوصی قابل اجراست |
| **writing-skills** (Superpowers) | description با «Use when…» و فقط شرایط فعال‌شدن (نه خلاصهٔ گردش‌کار)؛ سوم‌شخص؛ یک مثال عالی به‌جای چند نسخهٔ متوسط؛ «deploy untested skill = deploy untested code» | اسکیل ۲ درست بود؛ اسکیل ۱ خلاصهٔ گردش‌کار را در description گذاشته بود؛ دو نسخهٔ موازی = «multi-dilution» | یک description؛ یک گردش‌کار پیش‌فرض؛ موتور دوم فقط به‌عنوان escape hatch در یک مرجع جدا؛ همهٔ اسکریپت‌ها اجرا و تست شدند |
| **writing-for-agents** (Pocock) | description = «context pointer» همیشه‌بارگذاری‌شده؛ اطلاعات را سلسله‌مراتبی و نزدیک به محل استفاده بگذار؛ هر چیزِ تکراری یک خانه داشته باشد | دو description همیشه‌بارگذاری‌شده برای یک کار؛ قواعد برند در دو فایل متناقض (`brand.md` و `design-system.md`) | یک description؛ `brand.md` تنها منبع حقیقت برند برای هر دو موتور (پالت Remotion هم با آن هم‌تراز شد) |
| **motion-graphics** (HyperFrames) | کار بلندتر از ۱۰ ثانیه/چندصحنه‌ای مسیر `/hyperframes` است نه motion-graphics؛ فاز verify = lint + check + snapshots؛ رندر با تأیید کاربر («render now, or what changes?»)؛ PROJECT_DIR قراردادی | گیت `verify.py` وجود داشت ✔؛ تأیید پیش از رندر صریح نبود؛ مسیرها به سندباکس خاصی قفل بودند (`/home/user/skills/...`, `/home/user/work`, `/home/user/deliver`) | مرحلهٔ ۵ شامل پرسش «رندر کنم یا تغییر؟» وقتی کاربر حاضر است؛ همهٔ مسیرها از `env.sh` می‌آیند (`SKILL_DIR`, `REEL_WORK`, `REEL_DELIVER`, `HF_WORKDIR`)؛ `hyperframes lint/info/timeline` روی خروجی builder واقعاً اجرا شد (۰ خطا بعد از mix؛ فقط هشدار ساختاری sub-composition) |
| **remotion-best-practices** | `calculateMetadata`، `staticFile`، `<Audio>` از `@remotion/media`، فونت محلی با `loadFont`، `interpolate` با clamp، `Sequence` | قالب Remotion همهٔ این‌ها را رعایت می‌کرد ✔ (تأیید با خواندن کد + `tsc --noEmit` + `remotion bundle` موفق) | بدون تغییر ساختاری؛ فقط پالت پیش‌فرض با برند هم‌تراز شد و آستانهٔ بلندی صدا در `render.py` با موتور اصلی یکی شد |
| **ig-reel** | سه هوک بنویس، امتیاز بده، بهترین را بردار؛ ۲۶ فرمول؛ قانون ۳ ثانیه؛ ناحیهٔ امن | اسکیل ۱: `hook_score_ar.py` + ۱۲ فرمول عربی ✔ ولی اسکیل ۲ (HyperFrames) اصلاً از آن استفاده نمی‌کرد | امتیازدهی هوک مرحلهٔ ۲ گردش‌کار اصلی شد؛ `hooks-ar.md` از هر دو موتور ارجاع می‌شود |
| **viral-instagram-reels** | sends-per-reach، Trial Reels، اصالت محتوا، کاور، کپشن کلیدواژه‌دار، عیب‌یابی افت | در `publish.md` و `virality.md` به‌صورت تکراری و با واژگان متفاوت | ادغام در یک `publish.md` (الگوهای ممنوع، چک‌لیست ۶۰ دقیقهٔ اول، تشخیص افت)؛ `post_kit.py` حالا از spec هم پست‌کیت می‌سازد |

## ۳) ایرادهای مشخصی که پیدا و رفع شد

| # | ایراد | شدت | رفع |
|---|---|---|---|
| ۱ | `build_reel.py` و `post_kit.py` روی Python < 3.12 با `SyntaxError: f-string expression part cannot include a backslash` اصلاً اجرا نمی‌شدند (اسکریپت‌ها روی ۳٫۱۲ نوشته شده بودند؛ سندباکس/دبیان ۱۲ = ۳٫۱۱) | **بحرانی** — کل موتور پیش‌فرض از کار می‌افتاد | هر دو اصلاح شد؛ همهٔ ۱۹ اسکریپت پایتون با `py_compile` روی ۳٫۱۱ سبز هستند |
| ۲ | دو اسکیل با `name` یکسان و دو description رقیب | بالا | یک اسکیل، یک نام، یک description |
| ۳ | مسیرهای سخت‌کد سندباکس (`/home/user/skills/…`, `/home/user/work`, `/home/user/deliver`) و یادداشت «حافظه ≈ ۱ GB» | بالا (غیرقابل‌حمل) | متغیرهای محیطی با پیش‌فرض نسبی در `env.sh`؛ متن‌ها عمومی شدند |
| ۴ | `evals/evals.json` به ۳ تصویر ارجاع می‌داد که در مخزن نیستند | متوسط | `evals/files/README.md` توضیح می‌دهد؛ eval ۵ با فایل موجود اضافه شد |
| ۵ | `assets/sfx/CREDITS.md` فهرست فایل‌هایی را می‌آورد که بسته‌بندی نشده‌اند (click، error، glitch، typing…) | متوسط (گمراه‌کننده از نظر لایسنس) | بازنویسی با فهرست واقعی و منشأ هر فایل |
| ۶ | تناقض برند: `design-system.md` سبز `rgb(10,79,6)` + **قرمزِ تیره (maroon)** برای هشدار، در حالی که `brand.md` می‌گوید «هرگز قرمز»؛ تناقض هدف صدا (−۱۶±۴ و −۲۲…−۱۲ در برابر −۱۵٫۵ LUFS)؛ دو تعریف ناحیهٔ امن | متوسط | `brand.md` منبع واحد؛ پالت پیش‌فرض قالب Remotion به توکن‌های برند تغییر کرد (`maroon` → طلایی تیرهٔ `#7a5a24`)؛ هدف واحد −۱۵٫۵ LUFS / TP ≤ −۱٫۵ dBTP در هر دو موتور |
| ۷ | فایل‌های تکراری/بی‌استفاده: قالب Remotion ۲٫۵ مگابایتی داخل اسکیل HyperFrames بدون هیچ ارجاعی در SKILL.md؛ `logo.png` = `logo-wm.png`؛ `whoosh.mp3` = `whoosh-short.mp3` | پایین | قالب به `assets/remotion-template/` منتقل و از `remotion-studio.md` ارجاع داده شد؛ تکراری‌های کوچک چون کد به هر دو نام نیاز دارد نگه داشته و مستند شدند |
| ۸ | نمونهٔ `hadith-only.json` خودش هشدار «cta is tight» می‌داد (در حالی که eval می‌گوید نباید WARN بماند) | پایین | صحنهٔ CTA ۱ ثانیه بلندتر شد (۴۱ s)؛ بیت‌شیت نمونه بازتولید شد |
| ۹ | `recite.py` در نبود شبکه traceback خام می‌داد | پایین | پیام خطای راهنما + گزینهٔ `--from-files` برای فایل‌های از قبل دانلودشده |
| ۱۰ | `env.sh` فقط برای یک سندباکس خاص نوشته شده بود | پایین | بررسی numpy/ffprobe اضافه شد؛ fallback به ffmpeg ایستای `imageio-ffmpeg`؛ چاپ مسیرها |

## ۴) تصمیم معماری: یک اسکیل، یک موتور پیش‌فرض، یک راه فرار

- **پیش‌فرض = HyperFrames.** دلیل: کامل‌تر است (شش الگوی روایی A–F، تلاوت هم‌زمان با کلمات، گیت‌های `verify.py`،
  evals، بیت‌شیت فارسی، خروجی‌های ۴:۵/کاور)، و خودِ شما هم آن را به‌عنوان نسخهٔ نهایی ساخته بودید (پوشهٔ
  `maalsadiqeen-reel` ابرمجموعهٔ `maalsadiqeen-1` بود و `README-fa.md` آن (اکنون `README.md` پوشهٔ اصلی) آن را «جمع‌بندی پنج اسکیل عمومی» می‌نامید).
- **Remotion حذف نشد؛ تبدیل به موتور جایگزین شد** (`references/remotion-studio.md` + `remotion-schema.md` +
  `assets/remotion-template/`). دلیل: قالب Remotion صحنه‌های اختصاصی دارد که موتور اصلی ندارد (زنجیرهٔ سند متحرک با
  مهر «ثقة»، مُهر نتیجه، چیپ‌های پیشرفت) و ریل «شیعتنا المسلّمون» با آن ساخته شده است. این دقیقاً الگوی توصیه‌شدهٔ
  Anthropic است: «یک پیش‌فرض بده، با یک راه فرار» و «وقتی اسکیل چند framework را پوشش می‌دهد، SKILL.md انتخاب را
  انجام دهد و هر variant در یک مرجع جدا باشد».
- **ابزارهای مشترک** (`hook_score_ar.py`، `post_kit.py`، `extract_brand.py`) موتور-مستقل شدند و در گردش‌کار اصلی
  جای گرفتند (`post_kit.py` حالا هم `spec.json` و هم `content.json` را می‌فهمد).
- `maalsadiqeen-1/` حذف شد (در تاریخچهٔ گیت — commit `2c02d3b` — باقی است).

## ۵) ساختار نهایی

```
maalsadiqeen-reel-maker/             ← پوشهٔ اصلی: «ریل‌ساز مع الصادقین»
├── README.md                        ← عنوان، نصب، راهنمای فارسی صاحب صفحه
├── REVIEW-fa.md                     ← همین گزارش
└── maalsadiqeen-reel/               ← خودِ اسکیل (نام فنی maalsadiqeen-reel)
    ├── SKILL.md                     ← یک درِ ورودی: قواعد، انتخاب موتور، گردش‌کار ۰–۷، جدول تصمیم، فایل‌ها، «done means»
    ├── LICENSE · agents/openai.yaml
    ├── references/  brand · content-analysis · hooks-ar · narrative · arabic-copy · blocks · audio · motion ·
    │                qc · publish · troubleshooting · remotion-studio · remotion-schema      (۱۳ فایل، یک‌سطحی)
    ├── scripts/     env.sh · hook_score_ar · post_kit · extract_brand            (مشترک)
    │                new_spec · build_reel · recite · cues · mix · gen_bed · tighten · verify · render.sh ·
    │                export_variants · beat_sheet                                 (HyperFrames)
    │                setup_studio · validate_content · plan · make_audio · render (Remotion)
    ├── assets/      fonts · brand · sfx (+CREDITS) · gsap.min.js · hyperframes.json · examples · remotion-template
    └── evals/       evals.json (۵ سناریو) · rubric.md · files/README.md
```

## ۶) چه چیزی واقعاً آزمایش شد

| آزمایش | نتیجه |
|---|---|
| `skill-creator/scripts/quick_validate.py maalsadiqeen-reel` | ✅ Skill is valid |
| `py_compile` روی هر ۱۹ اسکریپت پایتون (Python 3.11) | ✅ |
| `build_reel.py` روی هر دو نمونه | ✅ ۶ صحنه / ۴۵ s و ۶ صحنه / ۴۱ s، بدون WARN |
| `mix.py` (بستر تولیدی + ۲۷ افکت خودکار + مسترینگ) | ✅ خروجی −۱۵٫۵ LUFS |
| `verify.py` پیش از رندر (`--no-check`) و روی یک MP4 آزمایشی (`--render`) | ✅ ۱۹ ok / ۰ failure |
| `beat_sheet.py --lang fa`، `export_variants.py --feed --audio`، `post_kit.py` (spec و content.json)، `hook_score_ar.py`، `cues.py`، `recite.py --from-files` | ✅ |
| Remotion: `validate_content.py`، `plan.py`، `make_audio.py`، `setup_studio.py` (کپی قالب)، `npm install` + `tsc --noEmit` + `remotion bundle` | ✅ |
| HyperFrames واقعی: نصب `hyperframes@0.8.157`، `hyperframes lint / info / timeline` روی خروجی builder | ✅ ۰ خطا (پس از mix)، ۶ هشدار ساختاری «nested_structure_needs_subcomposition» (مستند شد) |
| **اجرا نشد (در این محیط ممکن نبود):** `hyperframes check/snapshot/render` و `remotion render` (نیاز به دانلود Chrome Headless Shell — در سندباکس مسدود)، دانلود تلاوت از `cdn.islamic.network` | ⚠ باید یک‌بار در محیط خودتان اجرا شود؛ `env.sh` دقیقاً می‌گوید چه چیزی کم است |

## ۷) پیشنهادهای بعدی (خارج از این تحویل)

1. **Sub-composition در builder:** هر صحنه را به‌صورت فایل جدا با `data-composition-src` تولید کند تا هشدار lint
   برطرف شود و تایم‌لاین استودیوی HyperFrames یک ردیف برای هر صحنه نشان دهد.
2. **سه ورق اصلی** را در `evals/files/` بگذارید تا eval های ۱ و ۳ قابل اجرا شوند؛ سپس چرخهٔ eval اسکیل‌ساز
   (با/بدون اسکیل، سه تکرار) را یک بار اجرا کنید.
3. اگر Remotion را عملاً به کار نمی‌برید، در نسخهٔ بعد می‌توان آن را به یک اسکیل جدا با نام متفاوت
   (`maalsadiqeen-remotion`) برد و این اسکیل را سبک‌تر کرد — فعلاً به دلیل صحنه‌های اختصاصی سند نگه داشته شد.
