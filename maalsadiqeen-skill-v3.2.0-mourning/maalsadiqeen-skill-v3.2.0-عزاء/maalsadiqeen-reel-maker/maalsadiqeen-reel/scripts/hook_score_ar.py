#!/usr/bin/env python3
"""
hook_score_ar.py — score formal-Arabic Reel hooks (0–100) and rank them.

    python3 hook_score_ar.py "هل يكفي الحُبُّ لتكونَ من شيعتِهم؟" "…" …
    python3 hook_score_ar.py --file hooks.txt
    python3 hook_score_ar.py --json content.json
    python3 hook_score_ar.py --profile classic "…"      # v2 weights (compatibility)

v3 profile («dignified», default) rewards what this brand actually wants: brevity, a real curiosity
gap, a stake the text can support, self-relevance, specific religious content, a conditional
structure — and **dignity**: no fear-selling, no clickbait, no slang, no shouting. A fear-based hook
can still score, but it is punished, because it is off-brand even when it works.

Dimensions (max): brevity 22 · curiosity 16 · stakes 12 · second person 12 · specificity 12 ·
structure 8 · dignity 18. Penalties: emoji, Latin, dialect, vague wording, clickbait.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import EMOJI, LATIN, strip_tashkeel, words  # noqa: E402

CURIOSITY = ["هل", "لماذا", "كيف", "ما الذي", "ماذا", "أتعلم", "أتدري", "اختبر", "أيُّ", "أيّ",
             "من هو", "من هم", "ما معنى", "ما الفرق", "أين"]
STAKES = ["فليس منا", "ليس منا", "لست من", "فلست من", "لن", "خسر", "هلك", "يكفي", "شرط", "لا ينفع",
          "باطل", "حرام", "لا يقبل", "يوم القيامة", "برزخ", "فقدت", "منهم", "مصير", "عاقبة"]
SECOND_PERSON = ["أنت", "أنتم", "تكون", "تظن", "تعرف", "تحسب", "تحب", "تدعي", "فقدت", "تركت",
                 "تريد", "تعلم", "تدري", "تقرأ", "تصلي", "تسأل", "تقول", "تفعل"]
SECOND_PERSON_RE = re.compile(r"(^|\s)(ل|ف|و)?(ت\w{2,}|لست)(\s|$)|\w+ك(\s|$|[؟?،.])")
SPECIFIC = ["الإمام", "الامام", "النبي", "رسول الله", "الصادق", "الباقر", "الرضا", "الكاظم",
            "أمير المؤمنين", "علي", "فاطمة", "الحسين", "الحديث", "رواية", "سند", "صحيح",
            "الشيعة", "شيعت", "القرآن", "الآية", "الصادقين", "أهل البيت"]
STRUCTURE = ["إنّ", "إن ", "إذا", "إلا", "الا ", "فلست", "فليس", "من لم", "من لا", "لكن", "بل ",
             "…", "...", "بعد", "قبل", "حتى"]
FEAR = ["الموت", "ميتة", "هلاك", "هلكت", "خسرت", "خاسر", "جهنم", "النار", "عذاب", "البرزخ",
        "عاقبة", "مصيرك", "ستموت", "ستخسر", "مصير"]
CLICKBAIT = ["لن تصدق", "لن تصدّق", "صادم", "مذهل", "خطير جدا", "كارثة", "فضيحة", "عاجل", "!!!",
             "السر", "الحقيقة التي", "لا أحد يخبرك"]
VAGUE = ["شيء", "أمر مهم", "معلومة", "نصيحة", "تأمل", "كلام جميل", "موضوع"]
COLLOQUIAL = ["ليش", "شلون", "وين", "هاي", "هسه", "شنو", "كلش", "خوش", "شو"]
THREAT_RE = re.compile(r"(ستموت|ستخسر|ستندم|مصيرك|عاقبتك)")


def _brevity(n: int) -> tuple[int, list[str]]:
    if 4 <= n <= 8:
        return 22, []
    if n in (3, 9):
        return 16, ["length ok-ish (aim 4–8 words)"]
    if n <= 2:
        return 7, ["too short to carry a question"]
    return max(0, 18 - (n - 9) * 4), [f"{n} words: too long for 1.5 s reading"]


def score_classic(raw: str) -> dict:
    """v2 weights — kept for compatibility with older hooks.json files."""
    s = strip_tashkeel(raw)
    n = words(s)
    pts, notes = 0, []
    if 4 <= n <= 8:
        pts += 25
    elif n in (3, 9):
        pts += 18
    elif n <= 2:
        pts += 8
    else:
        pts += max(0, 20 - (n - 9) * 4)
    cur = any(k in s for k in CURIOSITY)
    if cur:
        pts += 14
    if re.search(r"[؟?]\s*$", s):
        pts += 6
    if any(k in s for k in STAKES):
        pts += 15
    if any(k in s for k in SECOND_PERSON) or SECOND_PERSON_RE.search(s):
        pts += 15
    if any(k in s for k in SPECIFIC):
        pts += 9
    if re.search(r"[٠-٩0-9]|ثلاث|أربع|خمس|سبع|عشر|واحد|اثن", s):
        pts += 6
    if re.search(r"\.\.\.|…|لكن|إلا|ولكن|أم ", s):
        pts += 6
    if re.search(r"(يكفي|وحده|فقط)", s):
        pts += 4
    for k in CLICKBAIT:
        if k in s:
            pts -= 25
    for k in COLLOQUIAL:
        if re.search(rf"(^|\s){k}(\s|$)", s):
            pts -= 30
    if EMOJI.search(raw):
        pts -= 20
    if LATIN.search(raw):
        pts -= 15
    if any(k in s for k in VAGUE):
        pts -= 10
    pts = max(0, min(100, pts))
    return {"hook": raw.strip(), "words": n, "score": pts, "grade": grade(pts), "profile": "classic",
            "notes": notes, "dimensions": {}}


def grade(pts: int) -> str:
    return "A" if pts >= 80 else "B" if pts >= 65 else "C" if pts >= 50 else "D"


def score(raw: str) -> dict:
    s = strip_tashkeel(raw).strip()
    n = words(s)
    dims: dict[str, int] = {}
    notes: list[str] = []

    dims["brevity"], bnotes = _brevity(n)
    notes += bnotes

    cur = any(k in s for k in CURIOSITY)
    dims["curiosity"] = 12 if cur else 0
    if re.search(r"[؟?]\s*$", s):
        dims["curiosity"] += 4
        notes.append("question form")
    elif cur:
        dims["curiosity"] += 2
    if cur:
        notes.append("curiosity opener")

    st = [k for k in STAKES if k in s]
    dims["stakes"] = 12 if st else 0
    if st:
        notes.append(f"stakes present ({st[0]})")

    if any(k in s for k in SECOND_PERSON) or SECOND_PERSON_RE.search(s):
        dims["second"] = 12
        notes.append("addresses the viewer")
    else:
        dims["second"] = 0

    dims["specific"] = 0
    if any(k in s for k in SPECIFIC):
        dims["specific"] += 9
        notes.append("religious specificity")
    if re.search(r"[٠-٩0-9]|ثلاث|أربع|خمس|سبع|عشر|واحد|اثن", s):
        dims["specific"] += 3
        notes.append("concrete number")

    dims["structure"] = 0
    if any(k in s for k in STRUCTURE):
        dims["structure"] += 5
        notes.append("conditional / contrast structure")
    if re.search(r"(يكفي|وحده|فقط|مجرد|مجرد)", s):
        dims["structure"] += 3
        notes.append("challenges an assumption")

    # dignity: start full, lose points for anything that cheapens the brand
    d = 18
    fear = [k for k in FEAR if k in s]
    if fear:
        d -= min(18, 6 * len(fear))
        notes.append(f"fear framing «{fear[0]}» — off-brand (-{min(18, 6*len(fear))})")
    if THREAT_RE.search(s):
        d -= 8
        notes.append("second-person threat — off-brand")
    if any(k in s for k in CLICKBAIT):
        d -= 18
        notes.append("clickbait wording")
    if any(k in s for k in VAGUE):
        d -= 8
        notes.append("vague wording")
    if n > 12:
        d -= 6
        notes.append("too long to sound calm")
    if raw.count("!") >= 1:
        d -= 4 * min(3, raw.count("!"))
        notes.append("exclamation mark")
    dims["dignity"] = max(0, d)

    pts = sum(dims.values())

    # hard penalties outside the dignity frame
    if EMOJI.search(raw):
        pts -= 20
        notes.append("emoji")
    if LATIN.search(raw):
        pts -= 15
        notes.append("Latin letters")
    for k in COLLOQUIAL:
        if re.search(rf"(^|\s){k}(\s|$)", s):
            pts -= 30
            notes.append(f"colloquial «{k}»")
            break
    if n >= 6 and not re.search(r"[\u064B-\u0652]", raw):
        notes.append("tip: add tashkeel on the key word for elegance")

    pts = max(0, min(100, pts))
    return {"hook": raw.strip(), "words": n, "score": pts, "grade": grade(pts), "profile": "dignified",
            "dimensions": dims, "notes": notes}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("hooks", nargs="*")
    ap.add_argument("--file")
    ap.add_argument("--json", help="content.json or spec.json: score its hook scene")
    ap.add_argument("--profile", choices=["dignified", "classic"], default="dignified")
    ap.add_argument("--out", help="write the ranked JSON here")
    ap.add_argument("--details", action="store_true", help="print the dimension breakdown")
    a = ap.parse_args()

    hooks = list(a.hooks)
    if a.file:
        hooks += [line.strip() for line in open(a.file, encoding="utf-8") if line.strip()]
    if a.json:
        data = json.load(open(a.json, encoding="utf-8"))
        if isinstance(data, str):
            hooks.append(data)
        elif isinstance(data, list):
            # ig-reel hooks.json, or an already-scored results file
            for it in data:
                if isinstance(it, str):
                    hooks.append(it)
                elif isinstance(it, dict):
                    hooks.append(str(it.get("hook") or it.get("text") or it.get("example") or ""))
            hooks = [h for h in hooks if h.strip()]
        elif "hooks" in data and isinstance(data["hooks"], list):
            for it in data["hooks"]:
                if isinstance(it, dict):
                    hooks.append(str(it.get("example") or it.get("template") or ""))
            hooks = [h for h in hooks if h.strip()]
        elif "scenes" in data:
            for sc in data["scenes"]:
                if sc.get("type") == "hook":
                    hooks.append(" ".join(str(sc.get(k, "")) for k in ("lead", "line1", "line2")).strip())
                    break
        elif "hook" in data:
            h = data["hook"]
            if isinstance(h, dict):
                hooks.append((h.get("line1", "") + " " + (h.get("line2") or "")).strip())
            else:
                hooks.append(str(h))
    if not hooks:
        ap.error("no hooks given")

    fn = score_classic if a.profile == "classic" else score
    results = sorted((fn(h) for h in hooks), key=lambda r: -r["score"])
    for i, r in enumerate(results, 1):
        print(f"{i}. [{r['score']:3d} {r['grade']}] {r['hook']}  ({r['words']} w)")
        if a.details and r["dimensions"]:
            print("      " + " · ".join(f"{k} {v}" for k, v in r["dimensions"].items()))
        for n in r["notes"]:
            if n.startswith(("fear", "second-person threat", "clickbait", "vague", "colloquial")):
                print(f"      ⚠ {n}")
    if results[0]["score"] < 65:
        print("\nBest hook is below 65 — rewrite using references/hooks-ar.md formulas before planning.",
              file=sys.stderr)
    if a.out:
        Path(a.out).write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {a.out}")
    print("\nBest hook: aim ≥ 80. Below 65, rewrite — do not build on it.")


if __name__ == "__main__":
    main()
