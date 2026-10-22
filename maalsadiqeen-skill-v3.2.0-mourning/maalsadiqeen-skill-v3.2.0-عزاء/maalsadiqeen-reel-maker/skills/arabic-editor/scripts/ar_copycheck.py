#!/usr/bin/env python3
"""
ar_copycheck.py — the mechanical pass of the Arabic editor (arabic-editor skill).

    python3 ar_copycheck.py copy.md                  # a text / markdown file ("-" for stdin)
    python3 ar_copycheck.py spec.json --spec         # every on-screen field of a reel spec
    python3 ar_copycheck.py copy.md --json           # machine-readable
    python3 ar_copycheck.py copy.md --warn-only      # never exit non-zero

Checks: hamza and the common misspellings, the ta-marbuta nouns that are always wrong with a ha,
Arabic-Indic digits, Latin letters, «!», « ؟», the three-dot ellipsis, dialect words, the fourteen
names without an honourific, over-long sentences, tatweel, and tashkeel density by line and by quote.

Exit 1 when an error is found (unless --warn-only). Warnings never change the exit code.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HARAKAT = re.compile(r"[\u064B-\u0652]")          # fathatan … sukun
TATWEEL = "\u0640"
TAG = re.compile(r"<[^>]+>")
LATIN = re.compile(r"[A-Za-z]")
HANDLE = re.compile(r"@[A-Za-z0-9_.]+")


def plain(s: str) -> str:
    return TAG.sub("", str(s or ""))


def base_letters(s: str) -> int:
    return len([c for c in plain(s) if c.strip() and not HARAKAT.match(c) and c != TATWEEL])


def density(s: str) -> float:
    n = base_letters(s)
    return len(HARAKAT.findall(plain(s))) / n if n else 0.0


def words(s: str) -> int:
    return len([w for w in re.split(r"\s+", plain(s).strip()) if w])


# ----------------------------------------------------------------------------- the rule tables
HAMZA = [
    ("إنشاء الله", "إن شاء الله"), ("انشاء الله", "إن شاء الله"), ("انشالله", "إن شاء الله"),
    ("إنشالله", "إن شاء الله"), ("إنشاءالله", "إن شاء الله"), ("انشاءالله", "إن شاء الله"),
    ("الله اعلم", "اللهُ أَعْلَم"), ("والله اعلم", "وَاللهُ أَعْلَم"),
    ("اللة", "الله"), ("مسئلة", "مسألة"), ("مسأله", "مسألة"),
    ("إبتداء", "ابتداء"), ("إبتدأ", "ابتدأ"), ("إستغفار", "استغفار"), ("إستغفر", "استغفر"),
    ("إجتماع", "اجتماع"), ("إجتمع", "اجتمع"), ("إنتظار", "انتظار"), ("إنتظر", "انتظر"),
    ("إبتلاء", "ابتلاء"), ("إستقامة", "استقامة"), ("إجتهاد", "اجتهاد"),
    ("هاذا", "هذا"), ("هاذه", "هذه"), ("الذى", "الذي"), ("التى", "التي"),
    ("عبدالله", "عبد الله"), ("عبدالرحمن", "عبد الرحمن"), ("علية", "عليه"),
    ("شئ", "شيء"), ("شىء", "شيء"),
]
# a definite feminine noun written with ه — always wrong (the ه of a pronoun has no ال)
TA_MARBUTA = ["السنه", "الجنه", "النعمه", "الرحمه", "الكلمه", "الحكمه", "الآيه", "الايه",
              "العبره", "الامه", "الأمه", "الشيعه", "الحريه", "المعرفه", "الاسره", "الأسره"]
DIALECT = ["كتير", "كتيرة", "شو", "ليش", "هيك", "هلق", "هلأ", "منيح", "بدي", "بدك",
           "مو", "كمان", "هيدا", "هاد", "تعا", "منشان", "هلقيت"]
NAMES = ["النبي", "رسول الله", "أمير المؤمنين", "الإمام علي", "فاطمة", "الزهراء",
         "الحسن", "الحسين", "السجاد", "زين العابدين", "الباقر", "الصادق", "الكاظم",
         "الرضا", "الجواد", "الهادي", "العسكري", "المهدي"]
HONORIFIC = re.compile(r"(\(ع\)|\(عج\)|عليه السلام|عليها السلام|عليهما السلام|صلى الله عليه|ﷺ|رضي الله عنه|رحمه الله)")
QUOTE = re.compile(r"«([^»]{25,})»|﴿([^﴾]{25,})﴾")
SENT_END = re.compile(r"[.؟!]")
# patterns that need a warning rather than a substitution (the right form depends on the grammar)
SOFT = [
    (re.compile(r"(قال|يقول|قالت)\s+ان\s"), "«ان» after «قال» — write «إنّ» (or «أنّ» if it is not emphasis)"),
    (re.compile(r"صلى\s+الله\s+عليه\s+وسلم"), "the page's full form is «صَلَّى اللهُ عَلَيْهِ وَآلِهِ وَسَلَّم»"),
]


def check_line(line: str, where: str) -> list[dict]:
    out: list[dict] = []
    text = line.strip()
    if not text:
        return out

    def err(code: str, msg: str):
        out.append({"level": "error", "code": code, "where": where, "msg": msg})

    def warn(code: str, msg: str):
        out.append({"level": "warn", "code": code, "where": where, "msg": msg})

    bare = plain(text)

    for wrong, right in HAMZA:
        if re.search(rf"(^|[\s«(]){re.escape(wrong)}([\s»)،:.]|$)", bare):
            err("hamza", f"«{wrong}» → «{right}»")
    for wrong in TA_MARBUTA:
        if re.search(rf"(^|[\s«(]){re.escape(wrong)}([\s»)،:.]|$)", bare):
            err("ta-marbuta", f"«{wrong}» → «{wrong[:-1]}ة»")
    if re.search(r"[0-9]", bare) and re.search(r"[\u0621-\u064A]", bare):
        err("digits", "ASCII digits in Arabic copy — use ٠١٢٣٤٥٦٧٨٩")
    latin = [m for m in LATIN.findall(HANDLE.sub("", bare))]
    if latin:
        err("latin", f"Latin letters «{''.join(latin)[:12]}» — only the handle may be Latin")
    if "!" in bare:
        err("bang", "exclamation mark")
    if re.search(r"\s[؟?]", bare):
        err("q-space", "space before «؟»")
    if "..." in bare:
        warn("ellipsis", "three dots — use «…»")
    if TATWEEL in bare:
        warn("tatweel", "tatweel (ـ) inside a word — remove it")
    if re.search(r"[^\s]  +[^\s]", bare):
        warn("double-space", "double space")

    for rx, msg in SOFT:
        if rx.search(bare):
            warn("grammar", msg)

    for bad in DIALECT:
        if re.search(rf"(^|[\s«(]){re.escape(bad)}([\s»)،:.]|$)", bare):
            err("dialect", f"«{bad}» is dialect — use fusha")

    flat = re.sub(HARAKAT, "", bare)
    if not where.endswith(".term"):          # a word being defined is not a person
        for name in NAMES:
            m = re.search(rf"(?<![^\s«(]){re.escape(name)}(?=[\s»)،:.]|$)", flat)
            if not m:
                continue
            tail = flat[m.start(): m.start() + 60]
            if not HONORIFIC.search(tail):
                warn("honorific", f"«{name}» without an honourific")

    for sentence in re.split(r"(?<=[.؟!])\s+", bare):
        n = words(sentence)
        if n > 22:
            warn("sentence-long", f"{n} words in one sentence — split it")

    for m in QUOTE.finditer(bare):
        q = m.group(1) or m.group(2)
        if words(q) >= 6 and density(q) < 0.10:
            warn("quote-plain", f"a quoted span at tashkeel {density(q):.2f} — a quotation needs ≥ 0.10")
    return out


def check_text(text: str, label: str) -> tuple[list[dict], dict]:
    issues: list[dict] = []
    lines = [ln for ln in text.splitlines()]
    for i, ln in enumerate(lines, 1):
        issues += check_line(ln, f"{label}:{i}" if label else f"line {i}")
    stats = {"lines": len([x for x in lines if x.strip()]),
             "words": words(text), "tashkeel": round(density(text), 3)}
    return issues, stats


def walk_scene(sc: dict, sid: str) -> list[tuple[str, str]]:
    """(where, text) for every on-screen string of a scene — mirrors copy_lint.fields_of."""
    out: list[tuple[str, str]] = []
    skip = {"id", "type", "start", "end", "track", "seconds", "cues", "brand", "highlight",
            "reveal", "font", "size", "max_lines", "max_words", "numbered", "nowrap", "lead_font",
            "final_font", "icon", "theme", "align", "mode"}

    def walk(v, path):
        if isinstance(v, str):
            if v.strip():
                out.append((f"{sid}.{path}", v))
        elif isinstance(v, list):
            for i, x in enumerate(v):
                walk(x, f"{path}[{i}]" if isinstance(x, (dict, list)) else path)
        elif isinstance(v, dict):
            for k, x in v.items():
                if k in ("handle",):
                    continue
                walk(x, f"{path}.{k}" if path else k)

    for k, v in sc.items():
        if k in skip:
            continue
        walk(v, k)
    return out


def check_spec(doc: dict) -> tuple[list[dict], dict]:
    issues: list[dict] = []
    scenes = doc.get("scenes") or []
    all_text = []
    for sc in scenes:
        sid = sc.get("id") or f"s{scenes.index(sc) + 1}"
        for where, txt in walk_scene(sc, sid):
            all_text.append(txt)
            issues += check_line(txt, where)
    joined = "\n".join(all_text)
    stats = {"scenes": len(scenes), "words": words(joined), "tashkeel": round(density(joined), 3)}
    return issues, stats


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help="text file, or spec.json with --spec ('-' = stdin)")
    ap.add_argument("--spec", action="store_true", help="the file is a reel spec: check every on-screen field")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--warn-only", action="store_true")
    a = ap.parse_args()

    raw = sys.stdin.read() if a.path == "-" else Path(a.path).read_text(encoding="utf-8")
    if a.spec:
        doc = json.loads(raw)
        issues, stats = check_spec(doc)
        label = Path(a.path).name if a.path != "-" else "spec"
    else:
        issues, stats = check_text(raw, "")
        label = Path(a.path).name if a.path != "-" else "stdin"

    errors = [i for i in issues if i["level"] == "error"]
    warns = [i for i in issues if i["level"] == "warn"]

    if a.json:
        print(json.dumps({"file": label, "stats": stats, "errors": errors, "warnings": warns},
                         ensure_ascii=False, indent=2))
    else:
        print(f"{label} · {stats.get('lines', stats.get('scenes', 0))} "
              f"{'lines' if 'lines' in stats else 'scenes'} · {stats['words']} words · "
              f"tashkeel {stats['tashkeel']:.3f}")
        for i in errors:
            print(f"  ✗ [{i['code']}] {i['where']}: {i['msg']}")
        for i in warns:
            print(f"  ⚠ [{i['code']}] {i['where']}: {i['msg']}")
        print(f"{len(errors)} errors · {len(warns)} warnings")

    if errors and not a.warn_only:
        sys.exit(1)


if __name__ == "__main__":
    main()
