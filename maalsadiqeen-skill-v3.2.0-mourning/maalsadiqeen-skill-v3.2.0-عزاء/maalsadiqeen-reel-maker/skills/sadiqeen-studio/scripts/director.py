#!/usr/bin/env python3
"""Recognition and treatment — the two stages before a single pixel is drawn.

`recognize()` reads whatever arrived (a page of text, a transcript, a spec, a folder) and
answers four questions with evidence: *what kind of text is this, what is the one idea,
what proves it, and what is missing?* `treat()` turns that into three scored ways to tell
it. Neither writes Arabic copy: the agent writes; these two make sure it writes about the
right thing, and refuse to hide a missing reference.

    python3 director.py input.txt --out .
    python3 director.py recognition.json --treat
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import brandkit as bk

VERSES = re.compile(r"﴿([^﴾]+)﴾|«?\s*(?:سُورَة|سورة|سُورَةُ)\s+([^\s—\-0-9]+)\s*[—\-–:]?\s*"
                    r"([٠-٩0-9]+)?[^»\n]{0,6}")
REFS = re.compile(r"(الكافي|بصائر\s*الدرجات|مرآة\s*العقول|وسائل\s*الشيعة|التهذيب|الاستبصار|"
                  r"من\s*لا\s*يحضره\s*الفقيه|بحار\s*الأنوار|عيون\s*أخبار\s*الرضا|"
                  r"كمال\s*الدين|الخصال|الاحتجاج|الغيبة|تفسير\s*\S+|أمالي\s*\S+)[^،.\n]{0,26}")
LOC = re.compile(r"(?:ج|جزء)\s*([٠-٩0-9]+)\s*(?:/|ص|—|-)\s*(?:ص\s*)?([٠-٩0-9]+)?")
GRADE = re.compile(r"(صحيح\s*السند|صحيح|معتبر|موثّق|موثق|حسن|مرسل|ضعيف|مقبول)")
HADITH = re.compile(r"(قال\s+(?:الإمام|رسول|النبي|أمير)|عن\s+(?:أبي|الإمام|جعفر|الصادق|الباقر)|"
                    r"رُوي|روي|عَلَيْهِ\s*السَّ?لَام|عليه\s*السلام|صلى\s*الله)")
SCHOLARS = re.compile(r"(العلّامة\s*المجلسي|المجلسي|الشيخ\s*المفيد|المفيد|الصدوق|الطوسي|"
                      r"الكليني|الحر\s*العاملي|السيد\s*\S+|الشهيد\s*\S+)")
OCCASION = re.compile(r"(عاشوراء|عاشورا|محرم|مُحَرَّم|صفر|رمضان|غدير|شعبان|فاطمية|أربعين|"
                      r"شهادة|ولادة|ذكرى|مناسبة)")
OBJECTION = re.compile(r"(شبهة|شبهات|يقولون|يُقال|يقال|لماذا|لمَ|اعتراض|يتهمون)")
QUESTION = re.compile(r"[؟?]")
OCCASION_DEFAULTS = ("عاشوراء", "محرم", "صفر", "فاطمية", "أربعين")


def _text_from(path: Path) -> tuple[str, str]:
    if path.is_dir():
        chunks = []
        for p in sorted(path.rglob("*")):
            if p.suffix.lower() in (".txt", ".md", ".srt", ".vtt"):
                chunks.append(p.read_text(encoding="utf-8", errors="replace"))
        return "\n\n".join(chunks), "folder"
    suf = path.suffix.lower()
    if suf in (".txt", ".md"):
        return path.read_text(encoding="utf-8", errors="replace"), "text"
    if suf in (".srt", ".vtt"):
        raw = path.read_text(encoding="utf-8", errors="replace")
        lines = [ln for ln in raw.splitlines()
                 if ln.strip() and not re.match(r"^\d+$", ln.strip()) and "-->" not in ln
                 and not ln.strip().upper().startswith(("WEBVTT", "NOTE"))]
        return " ".join(lines), "transcript"
    if suf == ".json":
        return path.read_text(encoding="utf-8", errors="replace"), "spec"
    if suf in (".mp4", ".mov", ".mkv", ".m4a", ".mp3", ".wav"):
        side = path.with_suffix(".srt")
        if side.exists():
            return _text_from(side)[0], "media+transcript"
        return "", "media-no-transcript"
    if suf in (".png", ".jpg", ".jpeg", ".webp"):
        return "", "image-no-ocr"
    return path.read_text(encoding="utf-8", errors="replace"), "text"


def recognize(path: str) -> dict:
    p = Path(path)
    text, kind = _text_from(p)
    words = len(text.split())
    verses = []
    for m in VERSES.finditer(text):
        snippet = (m.group(1) or f"{m.group(2)} {m.group(3) or ''}").strip()
        if snippet:
            verses.append(snippet[:160])
    refs = []
    for m in REFS.finditer(text):
        loc = LOC.search(text[m.end(): m.end() + 40])
        r = m.group(1)
        if loc:
            r += f" ج{loc.group(1)}" + (f" ص{loc.group(2)}" if loc.group(2) else "")
        refs.append(r)
    grades = sorted({g.group(1) for g in GRADE.finditer(text)})
    hadith = bool(HADITH.search(text))
    scholars = sorted({s.group(1) for s in SCHOLARS.finditer(text)})
    occasion = sorted({o.group(1) for o in OCCASION.finditer(text)})
    objection = bool(OBJECTION.search(text))
    question = bool(QUESTION.search(text))

    if objection:
        cls = "F"
    elif question and not verses and not hadith:
        cls = "D"
    elif verses and hadith:
        cls = "A"
    elif verses:
        cls = "A"
    elif hadith and refs:
        cls = "B"
    elif scholars or (refs and not hadith):
        cls = "C"
    elif occasion:
        cls = "E"
    else:
        cls = "C" if text.strip() else "?"

    long_form = None
    if words > 1800:
        long_form = "series — one reel per idea"
    elif words > 700:
        long_form = "G–L: one dense block (paragraph · definition · qa · steps · timeline · compare)"

    # a title line is not the idea: take the first clause of at least six words
    clauses = [c.strip() for c in re.split(r"(?<=[.؟!])|\n+", text.strip()) if c.strip()]
    sentences = [c for c in clauses if len(c.split()) >= 6]
    idea = (sentences or clauses or [""])[0]
    hedge = [w for w in ("ربما", "قد يكون", "يقول البعض", "غير مؤكد") if w in text]
    evidence = sum(bool(x) for x in (verses, refs, grades, hadith, scholars))
    confidence = round(min(1.0, 0.18 + 0.16 * evidence), 2)
    missing = []
    if not refs:
        missing.append("لا إحالة في النصّ — لا كتلة «proof»، وقل ذلك في الملخّص")
    if hadith and not grades:
        missing.append("الحديث بلا درجة سند — لا خاتم (seal) على الشاشة")
    if verses and not any(c.isalpha() for c in "".join(verses[:1])):
        missing.append("تحقّق من لفظ الآية قبل وضعها على الشاشة")
    if kind in ("image-no-ocr", "media-no-transcript"):
        missing.append("لا يمكن قراءة الصورة أو الصوت هنا: اطلب النصّ أو ملف الترجمة (.srt)")

    return {
        "input": str(p), "kind": kind, "words": words, "class": cls,
        "long_form": long_form, "idea": idea, "verses": verses[:4], "hadith": hadith,
        "references": refs[:6], "grades": grades, "scholars": scholars[:4],
        "occasion": occasion[:4], "objection": objection, "question": question,
        "hedging": hedge, "confidence": confidence, "missing": missing,
        "questions": _questions(refs, grades, hadith, verses, kind),
    }


def _questions(refs, grades, hadith, verses, kind) -> list[str]:
    q = []
    if hadith and not grades:
        q.append("درجة السند كما وردت في المصدر؟ (بلا درجة لا نضع خاتمًا)")
    if not refs:
        q.append("المصدر (كتاب، جزء، صفحة)؟ سطر واحد يكفي.")
    if not verses and not hadith:
        q.append("النصّ المنقول حرفيًا أم شرحك له؟ (الطبقات لا تُخلط)")
    if kind == "media-no-transcript":
        q.append("ملف الترجمة (.srt) أو النصّ المكتوب؟")
    return q[:3]


def treat(rec: dict) -> dict:
    """Three ways to tell it — not four, and never a fourth that is the same as the first."""
    cls = rec.get("class", "?")
    evidence = rec.get("references") or []
    have_proof = bool(evidence)
    base = {
        "A": ["سؤال → جواب المعصوم", "الكلمة التي تغيّر المعنى", "المعنى في الحياة"],
        "B": ["كلمة واحدة تغيّر المعنى", "موقف/قصة", "تصحيح مفهوم"],
        "C": ["تصحيح مفهوم", "المسألة ثم الحدّ", "خطأ شائع ثم النصّ"],
        "D": ["سؤال → جواب", "الجواب في ثلاث نقاط", "السؤال كما يُسأل، ثم النصّ"],
        "E": ["مناسبة: عنوان ثم نصّ", "المناسبة كسؤال", "سطر واحد وبطاقة"],
        "F": ["الاعتراض كما يُقال، ثم الجواب", "تصحيح بمقارنة", "النصّ وحده"],
    }.get(cls, ["تصحيح مفهوم", "سؤال → جواب", "كلمة واحدة تغيّر المعنى"])

    hooks = {
        "A": ["فَمَنْ هُمُ الصَّادِقُون؟", "«مَعَ» لَيست «مِثل»", "ماذا يعني أن تكون معهم؟"],
        "B": ["كَلِمَةٌ وَاحِدَة", "النَّصُّ يَقُولُ غَيْرَ ذَلِك", "لَوْ قَرَأْتَهَا صَحِيحَة"],
        "C": ["مَا كُنَّا نَفْهَمُهَا كَذَا", "التَّعْرِيفُ أَوَّلًا", "الفَرْقُ فِي حَرْف"],
        "D": ["سُئِلْتُ عَنْ هَذَا كَثِيراً", "الجَوَابُ أَقْرَبُ مِمَّا تَظُنّ", "ثَلَاثُ نَقَاط"],
        "E": ["فِي هَذَا اليَوْم", "لَيْسَ يَوْمَ بُكَاءٍ فَقَط", "مَوْعِدٌ لِلْمُرَاجَعَة"],
        "F": ["يُقَالُ إِنَّ…", "قَبْلَ الجَوَاب، النَّصّ", "لَا نُنَاقِشُ الأَشْخَاص"],
    }.get(cls, ["سُؤَالٌ وَنِصّ", "الكَلِمَةُ المِفْصَل", "النَّصُّ يَقُول"])

    shapes = {
        "A": ["hook", "verse", "contrast", "answer", "proof", "cta"],
        "B": ["hook", "quote", "answer", "proof", "cta"],
        "C": ["hook", "contrast", "quote", "proof", "cta"],
        "D": ["hook", "qa", "proof", "cta"],
        "E": ["title", "quote", "paragraph", "cta"],
        "F": ["hook", "contrast", "quote", "cta"],
    }.get(cls, ["hook", "quote", "paragraph", "cta"])

    out = []
    for i, angle in enumerate(base, 1):
        shape = shapes[:]
        if i == 2 and "verse" in shape:  # the second option leads with the text, not the question
            shape = [s for s in shape if s != "hook"]
        if i == 3 and len(shape) > 3:
            shape = shape[:2] + ["paragraph", "cta"]
        dur = 36 if len(shape) <= 4 else 44 if len(shape) == 5 else 50
        score = {
            "clarity": 5 if i == 1 else 4,
            "evidence": 5 if (have_proof and i != 3) else (3 if have_proof else 2),
            "tension": {"A": 5, "B": 4, "C": 4, "D": 3, "E": 3, "F": 5}.get(cls, 3),
            "brand_fit": 5 if "hook" in shape else 4,
            "risk": 2 if (not have_proof and "proof" in shape) else 1,
        }
        total = round(sum(v for k, v in score.items() if k != "risk") - score["risk"], 1)
        out.append({
            "id": i, "angle": angle, "hook": hooks[i - 1], "shape": shape,
            "duration": dur, "score": score, "total": total,
            "why_fa": f'«{angle}» با صنف {cls} می‌خواند؛ ' +
                      ("شاهد دارد" if have_proof else "شاهد ندارد، پس کتلهٔ اثبات حذف می‌شود"),
            "copy_todo": ["hook.line1 / line2", "هر نقل با تثبیت لفظ", "منبع برای کتلهٔ proof"]
                          if have_proof else ["hook.line1 / line2", "بدون کتلهٔ proof"],
        })
    out.sort(key=lambda t: -t["total"])
    return {"class": cls, "treatments": out,
            "pick": out[0]["id"], "questions": rec.get("questions", []),
            "rule": "یک ریل یک ایده؛ اگر نمی‌توانی ایده را در ۱۴ کلمه بنویسی، دو ریل است"}


def treat_table(t: dict) -> str:
    rows = ["| # | زاویه | هوک | بلوک‌ها | مدت | امتیاز |", "|---|---|---|---|---|---|"]
    for tr in t["treatments"]:
        rows.append(f'| {tr["id"]} | {tr["angle"]} | {tr["hook"]} | '
                    f'{" → ".join(tr["shape"])} | {tr["duration"]}s | {tr["total"]} |')
    rows.append("")
    rows.append(f'پیشنهاد: **{t["pick"]}** — {t["rule"]}')
    for q in t["questions"]:
        rows.append(f"- ؟ {q}")
    return "\n".join(rows)


def write(rec: dict, out: str) -> None:
    d = Path(out)
    d.mkdir(parents=True, exist_ok=True)
    (d / "recognition.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    brief = [
        f'# {rec["idea"][:80] or "brief"}', "",
        f'- **الصنف:** {rec["class"]}' + (f' · {rec["long_form"]}' if rec.get("long_form") else ""),
        f'- **الكلمات:** {rec["words"]} · **الثقة:** {rec["confidence"]}',
        f'- **الآيات:** {" · ".join(rec["verses"]) or "—"}',
        f'- **الحديث:** {"نعم" if rec["hadith"] else "لا"} · **الدرجة:** '
        f'{" · ".join(rec["grades"]) or "غير مذكورة"}',
        f'- **الإحالات:** {" · ".join(rec["references"]) or "—"}',
        f'- **العلماء:** {" · ".join(rec["scholars"]) or "—"}',
        f'- **المناسبة:** {" · ".join(rec["occasion"]) or "—"}', "",
        "## ما ينقص", "",
    ]
    brief += [f"- {m}" for m in (rec["missing"] or ["لا شيء — النصّ مكتمل"])]
    brief += ["", "## أسئلة (٣ كحد أقصى، في رسالة واحدة)", ""]
    brief += [f"{i}. {q}" for i, q in enumerate(rec["questions"], 1)] or ["—"]
    (d / "brief.md").write_text("\n".join(brief) + "\n", encoding="utf-8")


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="recognize a text, then three treatments")
    ap.add_argument("input")
    ap.add_argument("--out", default=".")
    ap.add_argument("--treat", action="store_true", help="input is a recognition.json")
    a = ap.parse_args()
    if a.treat:
        rec = json.loads(Path(a.input).read_text(encoding="utf-8"))
        t = treat(rec)
        Path(a.out, "treatments.json").write_text(json.dumps(t, ensure_ascii=False, indent=1),
                                                  encoding="utf-8")
        print(treat_table(t))
        return 0
    rec = recognize(a.input)
    write(rec, a.out)
    print(json.dumps(rec, ensure_ascii=False, indent=1)[:1800])
    return 0


if __name__ == "__main__":
    sys.exit(main())
