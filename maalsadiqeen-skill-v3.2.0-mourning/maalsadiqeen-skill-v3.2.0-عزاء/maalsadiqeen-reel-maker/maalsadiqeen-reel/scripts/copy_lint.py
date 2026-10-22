#!/usr/bin/env python3
"""
copy_lint.py — the verbal gate: everything that appears on screen, checked before a build.

    python3 copy_lint.py spec.json [--brand config/brand.json] [--json] [--warn-only]

Checks (fail = exit 1):
  placeholders left («…»), forbidden wording, dialect, emoji, Latin, «!!», >1 <em> per line,
  sacred text without tashkeel, seal without a stated grading, no CTA/brand card, >1 hero,
  on-screen words over the duration's budget (~2.9 words/s), scenes not contiguous, duration > 60 s,
  verse without recitation,
  no «الأثر في الحياة» block, a layer spoken without its label (verse without a reference, a
  hadith without an attribution), a Ma‛ṣūm named without the honourific.
Warns: line longer than the block budget, ASCII digits in a reference, «؟» with a leading space,
  words over the soft budget (~2.3 words/s), an unvocalised quote inside prose, more dense blocks
  than the reel can carry, a scene shorter than 2.5 s or longer than 17 s, hook > 4.5 s.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(HERE))
from _common import EMOJI, LATIN, strip_tashkeel, words  # noqa: E402

BRAND_PATH = SKILL / "config" / "brand.json"
TAG_RE = re.compile(r"<[^>]+>")

BUDGET = {
    "hook": {"lead": 4, "line1": 3, "line2": 2, "sub": 6},
    "verse": {"_line": 6},
    "contrast": {"wrong": 4, "right": 5, "line3": 3, "line4": 7},
    "answer": {"q1": 6, "q2": 5, "hero": 4, "after": 4, "source": 9},
    "proof": {"line1": 4, "line2": 4, "attribution": 9},
    "quote": {"_line": 7, "attribution": 9},
    "list": {"title": 4, "_item": 7},
    "title": {"kicker": 4, "title": 4, "sub": 7},
    "cta": {"line1": 3, "line2": 5, "share": 8, "final": 5},
    # v3 long-text blocks: one sentence per reveal, read at ~0.30 s/word
    "paragraph": {"_line": 20, "kicker": 4, "source": 12},
    "definition": {"_line": 22, "term": 4, "note": 14, "source": 12},
    "qa": {"_line": 20, "question": 9, "note": 14, "source": 12},
    "steps": {"title": 4, "_item": 12, "_head": 2, "source": 12},
    "timeline": {"_item": 12, "_when": 5, "source": 12},
    "compare": {"title": 4, "_cell": 10, "_head": 3, "verdict": 12, "source": 12},
}
LONG_TEXT = {"paragraph", "definition", "steps", "timeline", "compare", "qa"}
SACRED_BLOCKS = {"verse", "quote", "answer"}
# the fourteen, as they are actually written on screen
HOLY_NAMES = ["النبي", "رسول الله", "أمير المؤمنين", "علي", "فاطمة", "الحسن", "الحسين",
              "السجاد", "الباقر", "الصادق", "الكاظم", "الرضا", "الجواد", "الهادي", "العسكري", "المهدي"]
HONORIFIC = re.compile(r"(\(ع\)|عليه السلام|عليها السلام|عليهما السلام|صلوات الله عليه|صلى الله عليه|ﷺ)")
# an effect in life, not a slogan
LIFE_CLICHES = ["غيّر حياتك", "غير حياتك", "ستتغير حياتك", "حياة أفضل", "كن إيجابي", "طاقة إيجابية"]
INVISIBLE = {"lead", "label", "kicker", "source", "attribution", "sub"}
# keys that configure a block rather than say something on screen
NON_COPY = {"id", "type", "icon", "font", "lead_font", "final_font", "reveal", "theme",
            "track", "align", "mode", "layout"}
# an act the copy asks the reader to do — used to keep the ending to *one* invitation
REQUEST_RE = re.compile(r"(أرسل|ارسل|ابعث|احفظ|احتفظ|شارك|شارک|انشر|اشترك|تابع|ضَعْ|ضع |سجّل|سجل)")


def plain(s: str) -> str:
    return TAG_RE.sub("", s or "")


def clean_text(s) -> str:
    return re.sub(r"\s+", " ", plain(str(s or ""))).strip()


def load_json(p: Path, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


class Lint:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def fail(self, code: str, where: str, msg: str) -> None:
        self.items.append({"level": "fail", "code": code, "where": where, "msg": msg})

    def warn(self, code: str, where: str, msg: str) -> None:
        self.items.append({"level": "warn", "code": code, "where": where, "msg": msg})

    @property
    def fails(self) -> list[dict]:
        return [i for i in self.items if i["level"] == "fail"]

    @property
    def warns(self) -> list[dict]:
        return [i for i in self.items if i["level"] == "warn"]


def sentences_of(v) -> list[str]:
    """One entry per reveal for prose fields (the builder also splits long sentences at «،»)."""
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [x.strip() for x in re.split(r"(?<=[.؟!])\s+", str(v or "").strip()) if x.strip()]


def fields_of(sc: dict) -> list[tuple[str, str]]:
    """(field, text) pairs that are visible on screen."""
    t = sc.get("type")
    out: list[tuple[str, str]] = []
    if t == "verse":
        for line in sc.get("lines") or []:
            out.append(("_line", " ".join(line) if isinstance(line, list) else str(line)))
        if sc.get("label"):
            out.append(("label", str(sc["label"])))
    elif t == "quote":
        text = sc.get("text")
        if isinstance(text, list):
            for line in text:
                out.append(("_line", str(line)))
        elif text:
            out.append(("_line", str(text)))
        for k in ("label", "attribution"):
            if sc.get(k):
                out.append((k, str(sc[k])))
    elif t == "list":
        if sc.get("title"):
            out.append(("title", str(sc["title"])))
        for item in sc.get("items") or []:
            out.append(("_item", str(item)))
        if sc.get("attribution"):
            out.append(("attribution", str(sc["attribution"])))
    elif t == "proof":
        for k in ("line1", "line2", "attribution"):
            if sc.get(k):
                out.append((k, str(sc[k])))
        for c in sc.get("cards") or []:
            out.append(("card", " ".join(str(c.get(x, "")) for x in ("book", "loc", "grade")).strip()))
        if sc.get("seal"):
            out.append(("seal", " ".join(sc["seal"])))
    elif t == "paragraph":
        if sc.get("kicker"):
            out.append(("kicker", str(sc["kicker"])))
        out.extend(("_line", x) for x in sentences_of(sc.get("text")))
        if sc.get("source"):
            out.append(("source", str(sc["source"])))
    elif t == "definition":
        for k in ("label", "term", "note", "source"):
            if sc.get(k):
                out.append((k, str(sc[k])))
        out.extend(("_line", x) for x in sentences_of(sc.get("body")))
    elif t == "qa":
        for k in ("label_q", "question", "label_a", "note", "source"):
            if sc.get(k):
                out.append((k, str(sc[k])))
        out.extend(("_line", x) for x in sentences_of(sc.get("answer")))
    elif t == "steps":
        if sc.get("title"):
            out.append(("title", str(sc["title"])))
        for x in sc.get("items") or []:
            if isinstance(x, dict):
                if x.get("head"):
                    out.append(("_head", str(x["head"])))
                if x.get("text"):
                    out.append(("_item", str(x["text"])))
            elif str(x).strip():
                out.append(("_item", str(x)))
        if sc.get("source"):
            out.append(("source", str(sc["source"])))
    elif t == "timeline":
        if sc.get("title"):
            out.append(("title", str(sc["title"])))
        for x in sc.get("events") or []:
            if isinstance(x, dict):
                if x.get("when"):
                    out.append(("_when", str(x["when"])))
                if x.get("text"):
                    out.append(("_item", str(x["text"])))
            elif str(x).strip():
                out.append(("_item", str(x)))
        if sc.get("source"):
            out.append(("source", str(sc["source"])))
    elif t == "compare":
        if sc.get("title"):
            out.append(("title", str(sc["title"])))
        for key in ("col_a", "col_b"):
            c = sc.get(key) or {}
            if c.get("head"):
                out.append(("_head", str(c["head"])))
            for p in c.get("points") or []:
                if str(p).strip():
                    out.append(("_cell", str(p)))
        for k in ("verdict", "source"):
            if sc.get(k):
                out.append((k, str(sc[k])))
    else:
        for k, v in sc.items():
            if isinstance(v, str) and k not in NON_COPY:
                out.append((k, v))
    return out


def lint_spec(spec: dict, brand: dict) -> Lint:
    L = Lint()
    scenes = spec.get("scenes") or []
    if not scenes:
        L.fail("no-scenes", "spec", "spec has no scenes")
        return L

    # ---- structure and timing
    total = float(spec.get("duration") or (scenes[-1].get("end") or 0))
    if total > 60:
        L.fail("duration", "spec", f"{total}s > 60s — cut a scene")
    if total < 30:
        L.warn("duration-short", "spec", f"{total}s < 30s — thin for this audience")
    if scenes[0].get("type") != "hook":
        L.fail("first-hook", scenes[0].get("type", "?"), "the first scene must be a hook")
    if scenes[-1].get("type") != "cta":
        L.fail("last-cta", scenes[-1].get("type", "?"), "the last scene must be a cta with the brand card")
    for i in range(1, len(scenes)):
        prev, cur = scenes[i - 1], scenes[i]
        if prev.get("end") is not None and cur.get("start") is not None:
            if abs(float(prev["end"]) - float(cur["start"])) > 1e-6:
                L.fail("contiguous", f"s{i + 1}", f"starts at {cur['start']} but previous ends at {prev['end']}")
    hook = scenes[0]
    if float(hook.get("end", 0)) - float(hook.get("start", 0)) > 4.5:
        L.warn("hook-long", "s1", "hook scene > 4.5 s — the first cut should land earlier")
    for sc in scenes:
        d = float(sc.get("end", 0)) - float(sc.get("start", 0))
        if d and d < 2.5:
            L.warn("scene-short", sc.get("id", "?"), f"{d:.1f}s — too short to read")
        if d > 12 and sc.get("type") not in LONG_TEXT:
            L.warn("scene-long", sc.get("id", "?"), f"{d:.1f}s — no reveal for {d:.1f}s")
        elif d > 17:
            L.warn("scene-long", sc.get("id", "?"), f"{d:.1f}s — even prose needs a cut before 17 s")
    if any(s.get("type") == "verse" for s in scenes) and not (spec.get("audio") or {}).get("recitation"):
        L.fail("verse-no-recitation", "audio", "verse on screen but audio.recitation is missing")

    # ---- heroes and seals
    heroes = [s.get("id") for s in scenes if s.get("hero")]
    if len(heroes) > 1:
        L.warn("heroes", ", ".join(heroes), "more than one hero moment — keep one")
    for sc in scenes:
        if sc.get("type") == "proof" and sc.get("seal"):
            grades = [c.get("grade") for c in sc.get("cards") or []]
            if not any(grades):
                L.fail("invented-seal", sc.get("id", "?"), "seal shown but no card states a grading")
        if sc.get("type") == "proof" and not (sc.get("cards") or sc.get("attribution")):
            L.fail("empty-proof", sc.get("id", "?"), "proof block with no card and no attribution")

    # ---- the three layers must be legible on screen
    verse = next((s for s in scenes if s.get("type") == "verse"), None)
    if verse and not clean_text(verse.get("label")):
        L.fail("layer-unmarked", verse.get("id", "?"), "a verse on screen with no reference label — the viewer cannot tell the layer")
    quote = next((s for s in scenes if s.get("type") == "quote"), None)
    if quote and not clean_text(quote.get("attribution")):
        L.fail("layer-unmarked", quote.get("id", "?"), "a quoted hadith with no attribution — نصّ without its source")
    answer = next((s for s in scenes if s.get("type") == "answer"), None)
    if answer and answer.get("hero") and not clean_text(answer.get("source")):
        L.fail("layer-unmarked", answer.get("id", "?"), "a saying attributed to an Imam with no source line")
    if answer and answer.get("hero") and clean_text(answer.get("q2")) and not re.search(r"[:：]", clean_text(answer.get("q2"))):
        L.warn("layer-doubt", answer.get("id", "?"), "the question intro does not end with a colon — the answer may read as ours")

    # ---- «الأثر في الحياة» is mandatory: one concrete change, not a slogan
    life = clean_text(spec.get("life_impact"))
    if not life:
        life = next((" · ".join(clean_text(x) for x in s.get("items") or [])
                     for s in scenes if s.get("type") == "list" and "الأثر" in clean_text(s.get("title"))), "")
    if not life:
        L.fail("life-impact", "spec", "no «الأثر في الحياة» — say what changes in the viewer's week")
    else:
        lw = words(life)
        if lw < 4:
            L.fail("life-impact", "spec", f"{lw} words is a label, not an effect — make it a deed")
        elif lw > 32:
            L.warn("life-impact", "spec", f"{lw} words — keep the effect to one sentence")
        for c in LIFE_CLICHES:
            if c in strip_tashkeel(life):
                L.fail("life-cliche", "spec", f"«{c}» is a slogan, not an effect")

    # ---- honourifics on every Ma‛ṣūm named on screen
    # a term («الصَّادِق» as a word being defined), a date and a book reference are not persons
    NOT_A_PERSON = {"term", "_head", "_when", "source"}
    for sc in scenes:
        for field, raw in fields_of(sc):
            if field in NOT_A_PERSON:
                continue
            text = clean_text(raw)
            for name in HOLY_NAMES:
                if not re.search(rf"(^|[\s«(]){re.escape(name)}([\s»)،:.]|$)", strip_tashkeel(text)):
                    continue
                if "الإمام" not in text and name not in ("النبي", "رسول الله", "أمير المؤمنين") and len(name) < 5:
                    continue  # «علي» as a common word / part of another name
                # the honourific may sit up to 60 characters after the name
                flat = strip_tashkeel(text)
                m = re.search(rf"{re.escape(strip_tashkeel(name))}", flat)
                tail = flat[m.start(): m.start() + 60] if m else ""
                if not HONORIFIC.search(tail):
                    L.warn("honorific", f"{sc.get('id', '?')}.{field}", f"«{name}» without an honourific")

    # ---- words, lines, per-field rules
    total_words = 0
    for sc in scenes:
        sid = sc.get("id", "?")
        for field, raw in fields_of(sc):
            text = plain(raw)
            if not text.strip():
                continue
            w = words(text)
            if field not in INVISIBLE and sc.get("type") not in ("proof",):
                total_words += w
            budget = BUDGET.get(sc.get("type", ""), {}).get(field)
            if budget and w > budget + 3:
                L.warn("line-long", f"{sid}.{field}", f"{w} words (budget {budget}) — cut, do not shrink the font")

            body = strip_tashkeel(text)
            if re.fullmatch(r"[«»\s…\-—ـ]+", body):
                L.fail("placeholder", f"{sid}.{field}", f"placeholder copy «{text}» — replace it before building")
            if body.count("…") >= 2 and field != "_line":
                L.warn("ellipsis", f"{sid}.{field}", "two ellipses — is the quote complete?")
            for bad in brand.get("forbidden_on_screen", []):
                if bad and bad in body:
                    L.fail("forbidden", f"{sid}.{field}", f"«{bad}» is off-brand")
            for bad in brand.get("forbidden_dialect", []):
                if re.search(rf"(^|\s){re.escape(bad)}(\s|$)", body):
                    L.fail("dialect", f"{sid}.{field}", f"«{bad}» is dialect; use فصحى")
            if EMOJI.search(text):
                L.fail("emoji", f"{sid}.{field}", "emoji")
            latin = LATIN.findall(TAG_RE.sub("", text))
            if latin:
                L.fail("latin", f"{sid}.{field}", f"Latin letters «{''.join(latin)[:12]}» — only the handle is allowed")
            if "!" in text:
                L.fail("exclamation", f"{sid}.{field}", "exclamation mark")
            if raw.count("<em>") > 1:
                L.fail("emphasis", f"{sid}.{field}", f"{raw.count('<em>')} <em> in one line — one hinge word only")
            if re.search(r"\s[؟?]", text):
                L.warn("question-space", f"{sid}.{field}", "space before «؟»")
            if re.search(r"[0-9]", text) and field in ("source", "attribution", "card", "loc"):
                L.warn("digits", f"{sid}.{field}", "ASCII digits in a reference — use ٠١٢٣٤٥٦٧٨٩")
            if "(ع)" not in text and field == "attribution" and "الإمام" in text:
                L.warn("honorific", f"{sid}.{field}", "Imam named in an attribution without «(ع)»")

            # a quoted sentence inside prose must be vocalised too — otherwise it is not a quote
            if sc.get("type") in LONG_TEXT and field in ("_line", "_item", "_cell"):
                for m in re.finditer(r"«([^»]{25,})»", text):
                    if not re.search(r"[\u064B-\u0652]", m.group(1)):
                        L.warn("quote-plain", f"{sid}.{field}", "«…» without tashkeel inside prose — quote it as a quote block, or stop quoting")

            # sacred text must be vocalised
            if (sc.get("type") in SACRED_BLOCKS and field in ("_line", "hero", "text")) or (sc.get("type") == "hook" and field == "lead"):
                if w >= 4:
                    ratio = len(re.findall(r"[\u064B-\u0652]", text)) / max(1, len(body))
                    if ratio < 0.10:
                        L.fail("tashkeel", f"{sid}.{field}", "sacred text without tashkeel")
                    elif ratio < 0.18:
                        L.warn("tashkeel-light", f"{sid}.{field}", "light tashkeel — check the endings")

    warn_at = max(95, round(2.3 * total))
    fail_at = max(110, round(2.9 * total))
    if total_words > fail_at:
        L.fail("word-count", "spec", f"{total_words} on-screen words in {total:.0f}s — the reading budget is ~{fail_at}")
    elif total_words > warn_at:
        L.warn("word-count", "spec", f"{total_words} on-screen words in {total:.0f}s — trim toward {warn_at}, or move it to the caption")

    # density is budgeted per reel, not per block: a dense block costs ~9–16 s of screen time
    dense = [str(s.get("id")) for s in scenes if s.get("type") in LONG_TEXT]
    limit = 3 if total >= 46 else 2
    if len(dense) > limit:
        L.warn("dense-blocks", ", ".join(dense),
               f"{len(dense)} long-text blocks in {total:.0f}s — at most {limit}; past that it is a lecture, not a reel")


    # ---- the ending: at most one invitation, and never the sentimental one
    cta = scenes[-1]
    brand_cfg = brand.get("cta") or {}
    approved = brand_cfg.get("share") or []
    share = clean_text(cta.get("share") or "")
    forbidden = brand_cfg.get("forbidden") or []
    if share and any(x and x in share for x in forbidden):
        L.fail("cta-forbidden", "cta.share",
               "«أرسلها لمن تحب» وأخواتها خرجت من لغة الصفحة — اختر دعوة من `cta.endings` أو لا دعوة")
    if share and REQUEST_RE.search(strip_tashkeel(share)) and share not in approved:
        L.warn("cta-variant", "cta.share", "invitation not in the approved endings — add it to config/brand.json or use one")
    # one invitation per ending: the CTA may ask for one act, not three
    asks = [k for k in ("line1", "line2", "share", "final")
            if cta.get(k) and REQUEST_RE.search(strip_tashkeel(clean_text(cta[k])))]
    if len(asks) > 1:
        L.fail("cta-double", "cta." + "/".join(asks),
               f"{len(asks)} invitations in one ending ({', '.join(asks)}) — keep one")
    # a heavy or sensitive text is allowed to end with the verse and the card alone
    arch = str(spec.get("archetype") or (spec.get("scenario") or {}).get("archetype") or "")
    if arch in ("E", "F") and share and REQUEST_RE.search(strip_tashkeel(share)) and "احفظ" not in strip_tashkeel(share):
        L.warn("cta-heavy", "cta.share", f"archetype {arch} is heavy/sensitive — consider ending with no invitation")
    if not (cta.get("brand") or {}).get("handle"):
        L.warn("brand-card", "cta.brand", "no handle in the brand card")
    if cta.get("line1") and any(x in str(cta.get("line1")) for x in forbidden):
        L.fail("cta-bait", "cta.line1", "follow-bait CTA")

    return L


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--brand", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--warn-only", action="store_true", help="never exit non-zero")
    a = ap.parse_args()
    spec = load_json(Path(a.spec))
    if not spec:
        sys.exit(f"cannot read {a.spec}")
    brand = load_json(Path(a.brand) if a.brand else BRAND_PATH, {}) or {}
    L = lint_spec(spec, brand)
    if a.json:
        print(json.dumps({"fails": L.fails, "warns": L.warns}, ensure_ascii=False, indent=2))
    else:
        for i in L.fails:
            print(f"  ✗ [{i['code']}] {i['where']}: {i['msg']}")
        for i in L.warns:
            print(f"  ⚠ [{i['code']}] {i['where']}: {i['msg']}")
        print(f"{len(L.fails)} failures · {len(L.warns)} warnings")
    if L.fails and not a.warn_only:
        sys.exit(1)


if __name__ == "__main__":
    main()
