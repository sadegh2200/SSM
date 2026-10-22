#!/usr/bin/env python3
"""
sanad_check.py — validate a ḥadīth card, or every quote and proof block of a reel spec.

    python3 sanad_check.py card.json                 # one card
    python3 sanad_check.py spec.json --spec          # a reel spec (quotes, answers, proof cards)
    python3 sanad_check.py notes.md                  # a text: quotes with no citation are flagged
    python3 sanad_check.py card.json --json
    python3 sanad_check.py card.json --warn-only

Errors (exit 1):
  an invented seal (a seal with no stated grade, or a card marked needs_verification),
  a grade outside the vocabulary, a grade with no grader, ASCII digits in a citation,
  a quote with no attribution, an answer attributed to an Imam with no source,
  a proof card with no book.

Warns: a location that is not in the house shape (ج / ص · ح · الخطبة/الكتاب/الحكمة),
  a seal on a proof block whose cards carry no grade, a source that names no work.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

GRADES = ["صحيح", "صحيحة", "حسن", "حسنة", "موثق", "موثقة", "قوي", "معتبر", "معتبرة",
          "مقبول", "مقبولة", "ضعيف", "ضعيفة", "مرسل", "مرسلة", "منقطع", "معضل", "مضمر", "موضوع"]
STRONG = {"صحيح", "صحيحة", "حسن", "حسنة", "موثق", "موثقة", "قوي", "معتبر", "معتبرة", "مقبول", "مقبولة"}
GRADE_ALLOWED = {"بسند", "سند", "السند", "الإسناد", "الاسناد", "اسناده", "إسناده",
                 "كالصحيح", "كالحسن", "كذلك", "عن", "في", "من", "على"}
LOC_OK = re.compile(r"(ج\s*[٠-٩]+\s*/\s*ص\s*[٠-٩]+)|(ص\s*[٠-٩]+)|(الخطبة|الكتاب|الحكمة|ح)\s*[٠-٩]+")
ASCII = re.compile(r"[0-9]")
WORK_RE = re.compile(r"(الكافي|نهج البلاغة|بحار|وسائل|التهذيب|من لا يحضره|تفسير|مجمع البيان|الميزان"
                     r"|ميزان الحكمة|غرر الحكم|لسان العرب|المفردات|الصحاح|الخصال|التوحيد|الإرشاد|الاحتجاج)")


def grade_word(grade: str) -> str:
    g = re.sub(r"[\u064B-\u0652]", "", grade or "")
    for w in GRADES:
        if w in g:
            return w
    return ""


def check_card(card: dict, where: str) -> list[dict]:
    out: list[dict] = []

    def err(code, msg):
        out.append({"level": "error", "code": code, "where": where, "msg": msg})

    def warn(code, msg):
        out.append({"level": "warn", "code": code, "where": where, "msg": msg})

    book = str(card.get("book") or "").strip()
    loc = str(card.get("loc") or "").strip()
    grade = str(card.get("grade") or "").strip()
    by = str(card.get("graded_by") or "").strip()
    status = str(card.get("status") or "from_input")
    seal = bool(card.get("seal"))

    if not book:
        err("no-book", "a card without a book is not a reference")
    if not loc:
        warn("no-loc", "no volume / page — allowed only when the work has no divisions")
    elif ASCII.search(loc):
        err("ascii-digits", f"«{loc}» — use Arabic-Indic digits")
    elif not LOC_OK.search(loc):
        warn("loc-shape", f"«{loc}» is not in the house shape (ج١ / ص٢٠٨ · ح٧١ · الحكمة ٣١)")

    word = grade_word(grade)
    if grade:
        if not word:
            err("grade-unknown", f"«{grade}» is not in the grading vocabulary (grading.md §1)")
        else:
            for tok in re.sub(r"[\u064B-\u0652]", "", grade).split():
                if not grade_word(tok) and tok not in GRADE_ALLOWED:
                    err("grade-extra", f"«{tok}» is not part of a grading — keep the grader's own words")
                    break
        if not by:
            err("no-grader", "a grade needs the scholar who gave it (graded_by)")
        if by and ASCII.search(by):
            warn("ascii-digits", f"grader line has ASCII digits: «{by}»")

    if seal and not grade:
        err("invented-seal", "a seal with no stated grade — invented authority")
    if seal and grade and word and word not in STRONG:
        err("weak-seal", f"«{word}» cannot carry a seal — the page does not seal a weak report")
    if seal and status == "needs_verification":
        err("unverified-seal", "a card marked needs_verification can never be sealed")

    return out


def check_spec(doc: dict) -> tuple[list[dict], list[dict]]:
    issues: list[dict] = []
    cards: list[dict] = []
    scenes = doc.get("scenes") or []
    for i, sc in enumerate(scenes, 1):
        sid = sc.get("id") or f"s{i}"
        t = sc.get("type")
        if t == "quote" and not str(sc.get("attribution") or "").strip():
            issues.append({"level": "error", "code": "quote-no-source", "where": sid,
                           "msg": "a quoted ḥadīth with no attribution — نصّ without its source"})
        if t == "answer" and sc.get("hero") and not str(sc.get("source") or "").strip():
            issues.append({"level": "error", "code": "answer-no-source", "where": sid,
                           "msg": "a saying attributed to an Imam with no source line"})
        if t == "proof":
            seal_cards = 0
            for j, c in enumerate(sc.get("cards") or [], 1):
                card = dict(c)
                card["seal"] = bool(sc.get("seal")) and j == 1
                got = check_card(card, f"{sid}.card{j}")
                issues += got
                cards.append(card)
                if str(c.get("grade") or "").strip():
                    seal_cards += 1
            if sc.get("seal") and not (sc.get("cards") or []):
                issues.append({"level": "error", "code": "seal-no-card", "where": sid,
                               "msg": "a seal with no card under it"})
            if sc.get("seal") and (sc.get("cards") or []) and not seal_cards:
                issues.append({"level": "error", "code": "seal-no-grade", "where": sid,
                               "msg": "a seal over cards that state no grade"})
        for k in ("source", "attribution"):
            v = str(sc.get(k) or "")
            if v and ASCII.search(v):
                issues.append({"level": "warn", "code": "ascii-digits", "where": f"{sid}.{k}",
                               "msg": f"ASCII digits in a reference: «{v}»"})
    return issues, cards


def check_text(text: str, name: str) -> list[dict]:
    """Text mode: a draft, not a card. Mechanically finds what a card would have caught.

    It cannot grade a ḥadīth — nobody can, from prose — so it flags the three things that make a
    text unbuildable: a quotation with no citation beside it, a seal asserted in prose, and ASCII
    digits inside a citation."""
    out: list[dict] = []
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    for i, para in enumerate(paras, 1):
        where = f"{name}:¶{i}"
        cited = bool(re.search(r"(ج\s*[٠-٩]|ص\s*[٠-٩]|الخطبة|الحكمة|الكتاب|حديث\s*[٠-٩]|رقم\s*[٠-٩])", para)) \
            or bool(re.search(r"—\s*\S", para)) or bool(WORK_RE.search(para))
        # a *transmitted* saying is the one that needs a citation: «…» beside قال/روي/عن الإمام.
        # A definition in «…» (a dictionary entry, a term of ours) is not a ḥadīth and is not flagged.
        transmitted = re.search(r"(قال|روي|روى|روت|عن الإمام|عن النبي|عن رسول|حديث|يَقول|قوله)", para)
        for m in re.finditer(r"«([^»]{20,})»", para):
            if transmitted and not cited:
                out.append({"level": "warn", "code": "quote-no-source", "where": where,
                            "msg": f"«{m.group(1)[:34].replace(chr(10), ' ')}…» — no citation in the paragraph"})
                break
        if re.search(r"(صحيح|حسن|موثق|معتبر)\s*(ال)?(سند|إسناد|اسناد)", para):
            out.append({"level": "warn", "code": "seal-in-prose", "where": where,
                        "msg": "a seal asserted in prose — it belongs on a card with a grader"})
        if re.search(r"ج\s*[0-9]|ص\s*[0-9]", para):
            out.append({"level": "warn", "code": "ascii-digits", "where": where,
                        "msg": "ASCII digits in a citation — use ٠١٢٣٤٥٦٧٨٩"})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path")
    ap.add_argument("--spec", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--warn-only", action="store_true")
    a = ap.parse_args()

    path = Path(a.path)
    raw = path.read_text(encoding="utf-8")
    doc = None
    if not a.spec:
        try:
            doc = json.loads(raw)
        except json.JSONDecodeError:
            doc = None
    if doc is None and not a.spec:
        issues = check_text(raw, path.name)
        errors = [i for i in issues if i["level"] == "error"]
        warns = [i for i in issues if i["level"] == "warn"]
        if a.json:
            print(json.dumps({"header": f"{path.name} · text", "errors": errors, "warnings": warns},
                             ensure_ascii=False, indent=2))
        else:
            print(f"{path.name} · text · {len(raw.splitlines())} lines")
            for i in errors:
                print(f"  ✗ [{i['code']}] {i['where']}: {i['msg']}")
            for i in warns:
                print(f"  ⚠ [{i['code']}] {i['where']}: {i['msg']}")
            print(f"{len(errors)} errors · {len(warns)} warnings")
        if errors and not a.warn_only:
            sys.exit(1)
        return
    if doc is None:
        sys.exit(f"{path.name}: --spec expects a JSON spec")
    if not a.spec and "scenes" in doc and "book" not in doc:
        a.spec = True                                   # a spec handed over without the flag
    if a.spec:
        issues, cards = check_spec(doc)
        header = f"{Path(a.path).name} · spec · {len(doc.get('scenes') or [])} scenes · {len(cards)} cards"
    else:
        issues = check_card(doc, Path(a.path).name)
        cards = [doc]
        header = f"{Path(a.path).name} · {doc.get('book', '?')} {doc.get('loc', '')}".strip()

    errors = [i for i in issues if i["level"] == "error"]
    warns = [i for i in issues if i["level"] == "warn"]

    if a.json:
        print(json.dumps({"header": header, "cards": cards, "errors": errors, "warnings": warns},
                         ensure_ascii=False, indent=2))
    else:
        print(header)
        for c in cards:
            word = grade_word(str(c.get("grade") or ""))
            grade = str(c.get("grade") or "—").strip() or "—"
            allowed = bool(c.get("seal")) and word in STRONG and bool(str(c.get("graded_by") or "").strip()) \
                and str(c.get("status") or "from_input") != "needs_verification"
            print(f"  card: {c.get('book', '?')} {c.get('loc', '')} · {grade}"
                  + (f" · seal {'✓' if allowed else '✗'}" if c.get("seal") else ""))
        for i in errors:
            print(f"  ✗ [{i['code']}] {i['where']}: {i['msg']}")
        for i in warns:
            print(f"  ⚠ [{i['code']}] {i['where']}: {i['msg']}")
        print(f"{len(errors)} errors · {len(warns)} warnings")

    if errors and not a.warn_only:
        sys.exit(1)


if __name__ == "__main__":
    main()
