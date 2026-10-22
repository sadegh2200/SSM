#!/usr/bin/env python3
"""
validate_content.py — schema + Arabic quality gate for content.json.

    python3 validate_content.py content.json [--public assets/remotion-template/public] [--strict]

Exit code 1 on errors; warnings are printed but do not fail (unless --strict).
Checks: required keys, line-length limits (readability at 1080×1920), formal-Arabic hygiene
(no Latin, no emoji, no Persian-only letters), sanad verdict present when a chain exists,
referenced brand/audio files exist.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from _common import EMOJI, LATIN, has_arabic, letters, load_json, words

PERSIAN_ONLY = re.compile(r"[پچژگک]")  # ک = Persian kaf (Arabic is ك)
COLLOQUIAL = ["ليش", "شلون", "وين", "هاي", "هسه", "ماكو", "اكو", "شنو", "يعني هاي"]

MAX = {
    "hook_words": 7, "hook_lines": 2,
    "hadith_line_letters": 42, "hadith_lines": 10,
    "points": 5, "point_title_letters": 30, "point_desc_lines": 3, "point_desc_letters": 48,
    "bayan_lines": 6, "bayan_line_letters": 50,
    "chain": 12, "chain_name_letters": 40,
    "sources": 6, "cta_letters": 34,
}


class Report:
    def __init__(self):
        self.errors, self.warnings = [], []

    def err(self, m): self.errors.append(m)
    def warn(self, m): self.warnings.append(m)


def check_text(r: Report, where: str, s: str):
    if not isinstance(s, str) or not s.strip():
        r.err(f"{where}: empty text")
        return
    if LATIN.search(s):
        r.warn(f"{where}: contains Latin letters — on-screen text must be Arabic: «{s[:40]}»")
    if EMOJI.search(s):
        r.err(f"{where}: emoji are not allowed (dignity rule): «{s[:40]}»")
    if PERSIAN_ONLY.search(s):
        r.err(f"{where}: Persian-only letter (پ چ ژ گ ک) — use Arabic ك/ي: «{s[:40]}»")
    for w in COLLOQUIAL:
        if re.search(rf"(^|\s){w}(\s|$)", s):
            r.err(f"{where}: colloquial word «{w}» — formal Arabic only")
    if not has_arabic(s):
        r.err(f"{where}: no Arabic characters: «{s[:40]}»")


def validate(c: dict, public: Path | None) -> Report:
    r = Report()
    # ---- hook
    h = c.get("hook")
    if not isinstance(h, dict) or not h.get("line1"):
        r.err("hook.line1 is required")
    else:
        for k in ("line1", "line2", "sub"):
            if h.get(k):
                check_text(r, f"hook.{k}", h[k])
        for k in ("line1", "line2"):
            if h.get(k) and words(h[k]) > MAX["hook_words"]:
                r.warn(f"hook.{k}: {words(h[k])} words > {MAX['hook_words']} — hooks must be read in <1.5 s")
        if h.get("highlight") and h["highlight"] not in (h.get("line1", "") + " " + h.get("line2", "")):
            r.warn("hook.highlight is not a substring of line1/line2 (will be ignored)")
        full = (h.get("line1", "") + " " + (h.get("line2") or "")).strip()
        if not re.search(r"[؟?]", full) and not re.search(r"[٠-٩0-9]", full):
            r.warn("hook: neither a question nor a number — consider a stronger curiosity hook (see references/hooks-ar.md)")
    # ---- hadith
    hd = c.get("hadith")
    if not isinstance(hd, dict) or not isinstance(hd.get("lines"), list) or not hd["lines"]:
        r.err("hadith.lines[] is required (each {t, style?})")
    else:
        if len(hd["lines"]) > MAX["hadith_lines"]:
            r.err(f"hadith: {len(hd['lines'])} lines > {MAX['hadith_lines']} — split into a second Reel")
        styles = set()
        for i, l in enumerate(hd["lines"]):
            if not isinstance(l, dict) or "t" not in l:
                r.err(f"hadith.lines[{i}]: must be an object with 't'")
                continue
            check_text(r, f"hadith.lines[{i}]", l["t"])
            st = l.get("style", "body")
            styles.add(st)
            if st not in ("body", "lead", "warning"):
                r.err(f"hadith.lines[{i}].style '{st}' not in body|lead|warning")
            if letters(l["t"]) > MAX["hadith_line_letters"]:
                r.warn(f"hadith.lines[{i}]: {letters(l['t'])} letters > {MAX['hadith_line_letters']} — split the line at a natural pause")
        if "lead" not in styles:
            r.warn("hadith: no 'lead' line — the first clause usually deserves emphasis")
        for k in ("intro", "bridge"):
            if hd.get(k):
                check_text(r, f"hadith.{k}", hd[k])
        joined = " ".join(l.get("t", "") for l in hd["lines"] if isinstance(l, dict))
        if not re.search(r"[\u064B-\u0652]", joined):
            r.warn("hadith: no tashkeel found — the hadith text should be fully vocalized (copy exactly from the card)")
    # ---- points
    pts = c.get("points")
    if pts is not None:
        if not isinstance(pts, list):
            r.err("points must be a list")
        else:
            if len(pts) > MAX["points"]:
                r.err(f"points: {len(pts)} > {MAX['points']}")
            if len(pts) == 1:
                r.warn("points: a single point reads better as 'bayan'")
            for i, p in enumerate(pts):
                if not p.get("title"):
                    r.err(f"points[{i}].title required")
                    continue
                check_text(r, f"points[{i}].title", p["title"])
                if letters(p["title"]) > MAX["point_title_letters"]:
                    r.warn(f"points[{i}].title too long ({letters(p['title'])} letters)")
                for j, d in enumerate(p.get("desc") or []):
                    check_text(r, f"points[{i}].desc[{j}]", d)
                    if letters(d) > MAX["point_desc_letters"]:
                        r.warn(f"points[{i}].desc[{j}] too long ({letters(d)} letters)")
                if len(p.get("desc") or []) > MAX["point_desc_lines"]:
                    r.warn(f"points[{i}].desc has {len(p['desc'])} lines > {MAX['point_desc_lines']}")
                if p.get("chip") and words(p["chip"]) > 2:
                    r.warn(f"points[{i}].chip should be 1–2 words")
                q = p.get("quote")
                if q:
                    for j, ql in enumerate(q.get("lines") or [x for x in (q.get("a"), q.get("b")) if x]):
                        check_text(r, f"points[{i}].quote[{j}]", ql)
    # ---- bayan
    b = c.get("bayan")
    if b:
        if not b.get("lines"):
            r.err("bayan.lines[] required when bayan present")
        else:
            if len(b["lines"]) > MAX["bayan_lines"]:
                r.warn(f"bayan: {len(b['lines'])} lines > {MAX['bayan_lines']}")
            for i, l in enumerate(b["lines"]):
                check_text(r, f"bayan.lines[{i}]", l)
                if letters(l) > MAX["bayan_line_letters"]:
                    r.warn(f"bayan.lines[{i}] too long ({letters(l)} letters)")
    # ---- sanad
    s = c.get("sanad")
    if s:
        chain = s.get("chain") or []
        if len(chain) > MAX["chain"]:
            r.err(f"sanad.chain: {len(chain)} nodes > {MAX['chain']}")
        for i, n in enumerate(chain):
            if not n.get("name"):
                r.err(f"sanad.chain[{i}].name required")
                continue
            check_text(r, f"sanad.chain[{i}].name", n["name"])
            if letters(n["name"]) > MAX["chain_name_letters"]:
                r.warn(f"sanad.chain[{i}].name long ({letters(n['name'])} letters) — abbreviate the nisba")
            if n.get("grade"):
                check_text(r, f"sanad.chain[{i}].grade", n["grade"])
        if chain and not s.get("verdict"):
            r.err("sanad.verdict is required when a chain is shown (e.g. السَّنَدُ صحيحٌ معتبَرٌ)")
        imams = [n for n in chain if n.get("imam")]
        if chain and not imams:
            r.warn("sanad.chain: no node marked imam:true — the last node is usually the Imam")
        for k in ("question", "sub", "verdict", "verdict_sub", "note"):
            if s.get(k):
                check_text(r, f"sanad.{k}", s[k])
    # ---- sources / cta
    src = c.get("sources") or []
    if not src:
        r.warn("sources[] empty — a scholarly page should always cite sources")
    if len(src) > MAX["sources"]:
        r.warn(f"sources: {len(src)} > {MAX['sources']} — keep the 4 most authoritative")
    for i, x in enumerate(src):
        check_text(r, f"sources[{i}]", x)
    cta = c.get("cta") or {}
    for k in ("line1", "line2", "footer"):
        if cta.get(k):
            check_text(r, f"cta.{k}", cta[k])
            if letters(cta[k]) > MAX["cta_letters"]:
                r.warn(f"cta.{k} long ({letters(cta[k])} letters)")
    if not cta.get("line1"):
        r.warn("cta.line1 missing — a share-oriented CTA drives 'sends', the strongest reach signal")
    # ---- files
    if public:
        br = c.get("brand") or {}
        for k in ("logo", "branch"):
            if br.get(k) and not (public / br[k]).exists():
                r.warn(f"brand.{k} '{br[k]}' not found under {public} — template will fall back")
        au = c.get("audio") or {}
        if au.get("bed", True) and not (public / "audio" / "pad.wav").exists():
            r.warn("audio/pad.wav missing — run scripts/make_audio.py or set audio.bed=false")
        for n in ("tick", "stamp", "boom", "whoosh", "page-turn", "ding"):
            if au.get("sfx", True) and not (public / "audio" / f"{n}.wav").exists():
                r.warn(f"audio/{n}.wav missing — run scripts/make_audio.py")
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("content")
    ap.add_argument("--public", default=None, help="template public/ dir to check referenced files")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    a = ap.parse_args()
    c = load_json(a.content)
    r = validate(c, Path(a.public) if a.public else None)
    for w in r.warnings:
        print(f"WARN  {w}")
    for e in r.errors:
        print(f"ERROR {e}")
    n_scenes = 2 + bool(c.get("points")) + bool(c.get("bayan")) + bool(c.get("sanad")) + 1
    print(f"— {len(r.errors)} errors, {len(r.warnings)} warnings; scenes: hook, hadith"
          f"{', points' if c.get('points') else ''}{', bayan' if c.get('bayan') else ''}{', sanad' if c.get('sanad') else ''}, cta ({n_scenes})")
    sys.exit(1 if r.errors or (a.strict and r.warnings) else 0)


if __name__ == "__main__":
    main()
