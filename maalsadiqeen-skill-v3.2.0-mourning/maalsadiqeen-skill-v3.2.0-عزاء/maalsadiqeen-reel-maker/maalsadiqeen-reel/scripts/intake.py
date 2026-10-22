#!/usr/bin/env python3
"""
intake.py — turn any text (or sheets) into a brief seed, without touching the wording.

    python3 intake.py <file|dir|-> ... --slug <slug> [--sheets img ...] [--out DIR] [--json]

Writes into $REEL_WORK/<slug>/ (or --out):
    input.txt        normalised copy of everything that was given
    brief.seed.json  counts, quotes, references, layers, shape advice, flags
    brief.seed.md    the same in Persian, for the user

What it does NOT do: rewrite sacred text, invent a reference, translate a quotation, or decide
the scenario. Those are the agent's job (`references/text-intake.md`).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import strip_tashkeel, to_arabic_digits, words  # noqa: E402

# ----------------------------------------------------------------------------- vocabularies
BOOKS = [
    "الكافي", "نهج البلاغة", "بحار الأنوار", "وسائل الشيعة", "من لا يحضره الفقيه", "التهذيب",
    "الاستبصار", "المحاسن", "مرآة العقول", "تفسير القمي", "تفسير العياشي", "الغيبة", "كمال الدين",
    "الأمالي", "الخصال", "علل الشرائع", "عيون أخبار الرضا", "الاحتجاج", "الغارات", "الأصول الستة عشر",
    "مصباح المتهجد", "الهداية", "المقنع", "الفقيه", "الكافي ج", "تفسير الميزان", "الميزان",
]
GRADES = ["صحيح السند", "صحيح", "معتبر", "موثق", "حسن", "مرسل", "ضعيف", "قوي", "متواتر"]
SCHOLARS = ["المجلسي", "المفيد", "الصدوق", "الطوسي", "الطبرسي", "الحر العاملي", "الكليني",
            "العلامة الحلي", "الشهيد", "السيد", "المحقق", "الفيض", "المازندراني"]
HADITH_MARKERS = ["قال الإمام", "قال الامام", "عن الإمام", "عن الامام", "عن أبي عبد الله",
                  "عن أبي جعفر", "قال رسول الله", "عن النبي", "روى", "رُوي", "روي", "حدثنا",
                  "عن الصادق", "عن الباقر", "عن الرضا", "عن الكاظم", "قال الصادق", "قال الباقر",
                  "سُئل", "سئل", "فقال", "قال عليه السلام", "عن أمير المؤمنين"]
QURAN_MARKERS = ["قال الله", "يقول الله", "الآية", "الايه", "سورة", "سوره", "﴿"]
OCCASION_WORDS = ["ولادة", "شهادة", "عيد", "غدير", "عاشوراء", "رجب", "شعبان", "رمضان", "محرم",
                  "ذو القعدة", "ذو الحجة", "صفر", "مبعث", "ميلاد", "ذكرى", "مناسبة"]
OBJECTION_WORDS = ["شبهة", "اعتراض", "يقولون", "لماذا", "أشكل", "اشكال", "إشكال", "زعم", "يدّعي",
                   "يقول بعض", "أليس", "تناقض", "الجواب", "نقول", "الردّ", "الرد", "إشكال وارد"]

QURAN_BRACKET = re.compile(r"﴿(.+?)﴾", re.S)
GUILLEMET = re.compile(r"«(.+?)»", re.S)
REF_TAIL = re.compile(
    r"(?:ج|الجزء)\s*(?P<vol>[٠-٩0-9]+)\s*[/\s،,]*\s*(?:ص|الصفحة)\s*(?P<page>[٠-٩0-9]+)"
)
REF_PAGE_ONLY = re.compile(r"(?<![\u0600-\u06FF])ص\s*(?P<page>[٠-٩0-9]{1,4})(?![\u0600-\u06FF])")
AYAH_REF = re.compile(r"(?P<surah>[\u0600-\u06FF\s]{3,30}?)\s*(?:[:：/]|الآية|الايه)\s*(?P<ayah>[٠-٩0-9]{1,3})")
UNREADABLE = re.compile(r"\[\?\]|\[؟\]|\(\?\)|…\?")
INVISIBLE = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060\ufeff]")

TEXT_EXT = {".txt", ".md", ".markdown", ".json", ".srt"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}


# ----------------------------------------------------------------------------- io helpers
def read_one(path: Path) -> str:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return "\n\n".join(str(v) for v in data.values() if isinstance(v, str))
        return json.dumps(data, ensure_ascii=False, indent=1)
    return path.read_text(encoding="utf-8", errors="replace")


def collect(paths: list[str]) -> tuple[list[dict], list[str]]:
    """Return (documents, sheets) — sheets are images and are reported, not parsed."""
    docs, sheets = [], []
    for raw in paths:
        if raw == "-":
            docs.append({"name": "stdin", "text": sys.stdin.read()})
            continue
        p = Path(raw)
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and f.suffix.lower() in TEXT_EXT:
                    docs.append({"name": str(f), "text": read_one(f)})
                elif f.is_file() and f.suffix.lower() in IMAGE_EXT:
                    sheets.append(str(f))
            continue
        if p.suffix.lower() in IMAGE_EXT:
            sheets.append(str(p))
            continue
        docs.append({"name": str(p), "text": read_one(p)})
    return docs, sheets


def normalize(text: str) -> str:
    """Make the text readable for detection; never change a letter of the content."""
    t = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    t = INVISIBLE.sub("", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return "\n".join(line.rstrip() for line in t.split("\n")).strip() + "\n"


# ----------------------------------------------------------------------------- detection
def plain(s: str) -> str:
    return strip_tashkeel(s)


QURAN_REF = re.compile(r"[\\(（]?\s*([\u0600-\u06FF]{3,14})\s*[:：]\s*([٠-٩0-9]{1,3})\s*[\\)）]?")
SURAHS = {"الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال",
          "التوبة", "يونس", "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء",
          "الكهف", "مريم", "طه", "الأنبياء", "الحج", "المؤمنون", "النور", "الفرقان", "الشعراء",
          "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب", "سبأ", "فاطر",
          "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية",
          "الأحقاف", "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر",
          "الرحمن", "الواقعة", "الحديد", "المجادلة", "الحشر", "الممتحنة", "الصف", "الجمعة",
          "المنافقون", "التغابن", "الطلاق", "التحريم", "الملك", "القلم", "الحاقة", "المعارج",
          "نوح", "الجن", "المزمل", "المدثر", "القيامة", "الإنسان", "المرسلات", "النبأ", "النازعات",
          "عبس", "التكوير", "الانفطار", "المطففين", "الانشقاق", "البروج", "الطارق", "الأعلى",
          "الغاشية", "الفجر", "البلد", "الشمس", "الليل", "الضحى", "الشرح", "التين", "العلق",
          "القدر", "البينة", "الزلزلة", "العاديات", "القارعة", "التكاثر", "العصر", "الهمزة",
          "الفيل", "قريش", "الماعون", "الكوثر", "الكافرون", "النصر", "المسد", "الإخلاص",
          "الفلق", "الناس"}


def find_reference(segment: str, qpos: int = 0, kind: str = "") -> dict:
    """The reference nearest to the quotation inside this segment (never a later paragraph's)."""
    p = plain(segment)
    cands: list[tuple[int, str, str, str]] = []

    def grade_after(idx: int) -> str:
        tail = p[idx: idx + 80]
        for g in GRADES:
            if plain(g) in tail:
                return g
        return ""

    for book in BOOKS:
        b = plain(book)
        start = 0
        while True:
            idx = p.find(b, start)
            if idx < 0:
                break
            tail = p[idx: idx + 90]
            m = REF_TAIL.search(tail)
            loc = f"ج{m.group('vol')} ص{m.group('page')}" if m else ""
            if not loc:
                m2 = REF_PAGE_ONLY.search(tail)
                loc = f"ص{m2.group('page')}" if m2 else ""
            if loc:
                cands.append((idx, book, loc, grade_after(idx)))
            start = idx + len(b)

    if kind in ("quran", "other", ""):
        for m in QURAN_REF.finditer(p):
            if m.group(1) in SURAHS:
                cands.append((m.start(), "سورة " + m.group(1), f"الآية {m.group(2)}", ""))

    if not cands:
        return {}
    # prefer references at or just after the quotation; otherwise the closest before it
    after = [c for c in cands if c[0] >= qpos - 20]
    best = min(after or cands, key=lambda c: abs(c[0] - qpos))
    return {"book": best[1], "loc": best[2], "grade": best[3]}


def near(text: str, pos: int, markers: list[str], window: int = 140) -> bool:
    lo = max(0, pos - window)
    chunk = plain(text[lo: pos + 20])
    return any(plain(m) in chunk for m in markers)


def detect_quotes(text: str) -> list[dict]:
    quotes: list[dict] = []
    seen: set[str] = set()

    def add(kind: str, body: str, start: int) -> None:
        key = plain(body)[:60]
        if not key or key in seen:
            return
        seen.add(key)
        seg_start = text.rfind("\n\n", 0, max(0, start - 40))
        seg_start = seg_start if seg_start >= 0 else 0
        seg_end = text.find("\n\n", start + len(body))
        seg_end = seg_end if seg_end >= 0 else len(text)
        segment = text[seg_start:seg_end]
        qpos = start - seg_start
        ref = find_reference(segment, qpos, kind)
        status = "from_input" if ref.get("book") else "needs_user"
        quotes.append({
            "id": f"q{len(quotes) + 1}", "kind": kind, "text": body.strip(),
            "source": {"book": ref.get("book", ""), "loc": ref.get("loc", ""), "grade": ref.get("grade", "")},
            "status": status, "span": [start, start + len(body)], "words": words(body),
            "layer": "شرح" if kind == "scholar" else "نصّ",
        })

    for m in QURAN_BRACKET.finditer(text):
        add("quran", m.group(1), m.start())
    for m in GUILLEMET.finditer(text):
        body = m.group(1)
        if not body.strip() or words(body) < 2:
            continue
        if near(text, m.start(), SCHOLARS, window=60):
            kind = "scholar"
        elif near(text, m.start(), HADITH_MARKERS):
            kind = "hadith"
        elif near(text, m.start(), ["قال الله", "يقول الله"]):
            kind = "quran"
        elif words(body) >= 8:
            kind = "hadith"
        else:
            kind = "other"
        add(kind, body, m.start())

    # a scholar's sentence without guillemets: «قال العلّامة … : إنّ … .»
    for m in re.finditer(r"قال\s+(?:العلّامة|العلامة|الشيخ|السيّد|السيد|المحقّق|المجلسي|المفيد|الصدوق)[^:：\n]{0,50}[:：]\s*([^\n]{15,300})", text):
        add("scholar", m.group(1).strip(), m.start(1))
    return quotes


def layer_of(q: dict) -> str:
    return "نصّ" if q["kind"] in ("quran", "hadith") else "شرح"


def classify(text: str, quotes: list[dict]) -> tuple[str, str, str]:
    p = plain(text)
    kinds = {q["kind"] for q in quotes}
    has_quran, has_hadith, has_scholar = "quran" in kinds, "hadith" in kinds, "scholar" in kinds
    occasion = sum(1 for w in OCCASION_WORDS if plain(w) in p)
    objection = sum(1 for w in OBJECTION_WORDS if plain(w) in p)
    if objection >= 2:
        return "F", "ردّ شبهة", "نشانه‌های اشکال و پاسخ در متن"
    if has_quran and has_hadith:
        return "A", "سؤال → جواب المعصوم", "آیه و حدیث هر دو در متن هست"
    if occasion >= 2:
        return "E", "مناسبت", "نام مناسبت یا تاریخ در متن"
    if has_hadith:
        return "B", "کلمة واحدة تغيّر المعنى", "حدیث بدون آیه"
    if has_scholar:
        return "C", "تصحيح مفهوم", "نقل قول عالم یا تحقیق"
    if "?" in text or "؟" in text:
        return "D", "سؤال → جواب", "پرسش صریح در متن"
    return "C", "تصحيح مفهوم", "متن توضیحی بدون نقل صریح"


def shape_for(n_words: int, n_units: int = 1, n_sections: int = 0) -> dict:
    # several independent ideas inside a short text still make a series
    ideas = max(n_units, n_sections - 1 if n_sections >= 3 else 0)
    if ideas >= 3 and n_words > 180:
        parts = min(3, ideas)
        return {"mode": "split", "parts": parts,
                "reason": f"متن کوتاه است اما {ideas} ایدهٔ مستقل دارد؛ {parts} قسمت پیشنهاد می‌شود."}
    if n_words <= 250:
        return {"mode": "single", "parts": 1, "reason": "متن کوتاه است؛ یک ریل ۳۰–۴۵ ثانیه‌ای کافی است."}
    if n_words <= 700:
        return {"mode": "single_with_overflow", "parts": 1,
                "reason": "یک ریل + سرریز به کپشن و کامنت (حداکثر ۷۰ کلمه روی صفحه)."}
    if n_words <= 1800:
        return {"mode": "split", "parts": 2 if n_words <= 1100 else 3,
                "reason": "متن بیش از یک ریل است؛ هر قسمت باید ایده و منبع مستقل داشته باشد."}
    parts = max(4, min(8, round(n_words / 450)))
    return {"mode": "series", "parts": parts,
            "reason": f"متن بلند است؛ سری {parts} قسمتی پیشنهاد می‌شود (series.md)."}


def build_units(text: str, quotes: list[dict]) -> list[dict]:
    text = re.sub(r"\n(?=#{1,3}\s)", "\n\n", text)   # a heading starts a new unit
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    units, buf = [], ""
    for p in paragraphs:
        candidate = (buf + "\n\n" + p).strip() if buf else p
        if words(candidate) > 260 and buf:
            units.append(buf)
            buf = p
        else:
            buf = candidate
    if buf:
        units.append(buf)
    out = []
    for i, u in enumerate(units, 1):
        qids = [q["id"] for q in quotes if u.find(q["text"][:40]) >= 0]
        out.append({"id": f"u{i}", "words": words(u), "quotes": qids,
                    "preview": re.sub(r"\s+", " ", u)[:180]})
    return out


def build_flags(text: str, quotes: list[dict], sheets: list[str]) -> list[str]:
    flags = []
    for q in quotes:
        if q["kind"] in ("quran", "hadith") and not q["source"]["book"]:
            flags.append(f"{q['id']}: نقل قول بدون منبع («{q['text'][:40]}…») — بلوک سند حذف می‌شود یا منبع را بپرسید")
        if q["kind"] == "hadith" and not q["source"]["grade"]:
            flags.append(f"{q['id']}: حدیث بدون درجهٔ سند — مُهر «صحیح السند» نسازید")
    if UNREADABLE.search(text):
        flags.append("کلمهٔ ناخوانا یا علامت‌گذاری‌شده در متن هست؛ آن را به کاربر گزارش کنید و حدس نزنید")
    if re.search(r"[A-Za-z]{3,}", text):
        flags.append("حروف لاتین در متن هست؛ روی صفحه فقط handle مجاز است")
    if len(text) and len(re.findall(r"[٠-٩0-9]", text)) == 0 and quotes:
        flags.append("هیچ ارجاع عددی (ج/ص) در متن نیست؛ بررسی کنید منبع کامل است یا نه")
    if sheets:
        flags.append(f"{len(sheets)} تصویر ورق پیوست است؛ ورق‌ها را بخوانید و با متن تطبیق دهید")
    return flags


# ----------------------------------------------------------------------------- report
def seed_markdown(seed: dict) -> str:
    q = seed["quotes"]
    s = seed["shape"]
    lines = [
        f"# بریف خام — {seed['slug']}", "",
        f"**ورودی:** {seed['counts']['words']} کلمه · {seed['counts']['chars']} نویسه · "
        f"{seed['counts']['documents']} سند · {seed['counts']['sheets']} ورق",
        f"**شکل پیشنهادی:** {s['reason']}",
        f"**کلاس پیشنهادی:** {seed['classification']['class']} → {seed['classification']['archetype']}",
        f"**منبع‌یابی:** {seed['source_policy']}", "",
        "## نقل‌قول‌ها", "",
    ]
    if q:
        lines += ["| # | نوع | متن | منبع | وضعیت |", "|---|---|---|---|---|"]
        for x in q:
            src = (x["source"]["book"] + (f" {x['source']['loc']}" if x["source"]["loc"] else "")).strip() or "—"
            lines.append(f"| {x['id']} | {x['kind']} | {x['text'][:48]}… | {src} | {x['status']} |")
    else:
        lines.append("نقل‌قول صریحی پیدا نشد؛ اگر متن شامل آیه/حدیث است، آن را داخل «…» یا ﴿…﴾ بگذارید.")
    lines += ["", "## واحدهای فکری", ""]
    for u in seed["units"]:
        lines.append(f"- **{u['id']}** ({u['words']} کلمه): {u['preview']}…")
    lines += ["", "## هشدارها", ""]
    lines += [f"- {f}" for f in seed["flags"]] or ["- موردی نیست."]
    lines += [
        "", "## قدم بعد", "",
        "```bash", f"python3 scripts/scenarios.py init {seed['slug']} --brief brief.json", "# چهار سناریو را پر کنید، سپس:",
        f"python3 scripts/scenarios.py render {seed['slug']} --brief brief.json", "```", "",
        "> این فایل خام است. `brief.md` را خودتان با قالب `references/text-intake.md` §7 بنویسید.", "",
    ]
    return "\n".join(lines)


# ----------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="*", help="text file(s), a directory, or - for stdin")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--sheets", nargs="*", default=[])
    ap.add_argument("--out", default=None, help="output directory (default $REEL_WORK/<slug>)")
    ap.add_argument("--source-policy", default="hybrid", choices=["input", "research", "hybrid"])
    ap.add_argument("--json", action="store_true", help="print the seed JSON only")
    a = ap.parse_args()

    docs, sheets = collect(a.inputs)
    for s in a.sheets:
        if Path(s).suffix.lower() in IMAGE_EXT and s not in sheets:
            sheets.append(s)
        else:
            print(f"  ⚠ --sheets ignored «{s}»: not an image (pass text files as positional inputs)")
    if not docs and not sheets:
        sys.exit("no text and no sheets given")
    raw = "\n\n".join(d["text"] for d in docs)
    text = normalize(raw)
    quotes = detect_quotes(text)
    cls, archetype, why = classify(text, quotes)
    n_words = words(text)
    out = Path(a.out) if a.out else Path(os.environ.get("REEL_WORK", "reel-work")) / a.slug
    out.mkdir(parents=True, exist_ok=True)
    (out / "input.txt").write_text(text, encoding="utf-8")

    seed = {
        "schema": 3,
        "slug": a.slug,
        "source_policy": a.source_policy,
        "input": {"documents": [d["name"] for d in docs], "sheets": sheets},
        "counts": {"words": n_words, "chars": len(text), "documents": len(docs), "sheets": len(sheets),
                   "on_screen_budget": 70, "overflow_words": max(0, n_words - 70)},
        "classification": {"class": cls, "archetype": archetype, "why_fa": why},
        "shape": shape_for(n_words, len(build_units(text, quotes)),
                           len(re.findall(r"(?m)^#{1,3}\s", text))),
        "quotes": quotes,
        "units": build_units(text, quotes),
        "flags": build_flags(text, quotes, sheets),
        "suggested_commands": {
            "plan": f"python3 scripts/scenarios.py init {a.slug} --brief brief.json",
            "render": f"python3 scripts/scenarios.py render {a.slug} --brief brief.json",
        },
    }
    (out / "brief.seed.json").write_text(json.dumps(seed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "brief.seed.md").write_text(seed_markdown(seed), encoding="utf-8")

    if a.json:
        print(json.dumps(seed, ensure_ascii=False, indent=2))
        return
    print(f"intake → {out}")
    print(f"  words {n_words} · quotes {len(quotes)} · class {cls} ({archetype}) · shape {seed['shape']['mode']}")
    for f in seed["flags"]:
        print("  ⚠", f)
    print(f"  wrote input.txt, brief.seed.json, brief.seed.md")


if __name__ == "__main__":
    main()
