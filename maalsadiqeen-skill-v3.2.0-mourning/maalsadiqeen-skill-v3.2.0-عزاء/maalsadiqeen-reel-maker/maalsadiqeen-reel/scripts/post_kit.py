#!/usr/bin/env python3
"""
post_kit.py — generate post.md (caption, hashtags, pinned source comment, alt hooks, publish checklist).

    python3 post_kit.py spec.json      [--hooks hooks.json] [-o post.md]     # HyperFrames spec (default engine)
    python3 post_kit.py content.json   [--hooks hooks.json] [-o post.md]     # Remotion studio content.json

The input kind is detected from the JSON ("scenes" → spec, "hadith" → content.json).

Caption strategy (ranking signals, see references/publish.md): keyword-rich first line (search),
the full sacred text (saves), the grading/references (trust → sends), a soft share prompt,
≤ 8 niche hashtags. Pinned comment = every reference and grading that is on screen, nothing more.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from _common import load_json, strip_tashkeel

TAG_RE = re.compile(r"<[^>]+>")
IMAM_TAGS = (("الرضا", "#الإمام_الرضا"), ("الصادق", "#الإمام_الصادق"), ("الباقر", "#الإمام_الباقر"),
             ("الكاظم", "#الإمام_الكاظم"), ("أمير المؤمنين", "#أمير_المؤمنين"), ("أَمِيرُ المُؤْمِنِين", "#أمير_المؤمنين"),
             ("الحسين", "#الإمام_الحسين"), ("فاطمة", "#فاطمة_الزهراء"))
KW_TAGS = (("شيعت", "#شيعة"), ("ولاي", "#الولاية"), ("سند", "#رجال_الحديث"), ("الصادقين", "#كونوا_مع_الصادقين"))


def clean(s: str) -> str:
    """Drop <em> markup and collapse spaces (spec copy may carry inline emphasis tags)."""
    return re.sub(r"\s+", " ", TAG_RE.sub("", s or "")).strip()


def pick_tags(text: str, *, base=("#أهل_البيت", "#حديث_شريف")) -> list[str]:
    plain = strip_tashkeel(text)
    tags = list(base)
    for needle, tag in IMAM_TAGS:  # whole-word match: «الصادق» must not fire on «الصادقين»
        if re.search(r"(?<!\w)" + re.escape(strip_tashkeel(needle)) + r"(?!\w)", plain) and tag not in tags:
            tags.append(tag)
    for kw, tag in KW_TAGS:
        if kw in plain and tag not in tags:
            tags.append(tag)
    tags += [t for t in ("#مع_الصادقين", "#معارف_أهل_البيت") if t not in tags]
    return tags[:8]


# ----------------------------------------------------------------------------- Remotion content.json
def from_content(c: dict) -> dict:
    hook = c["hook"]
    hadith = c["hadith"]
    sanad = c.get("sanad") or {}
    chain = sanad.get("chain") or []
    body = [((hadith.get("intro", "") + " ") if hadith.get("intro") else "") + " ".join(l["t"] for l in hadith["lines"])]
    for p in c.get("points") or []:
        body.append(f"• {p['title']}" + (f": {' '.join(p.get('desc') or [])}" if p.get("desc") else ""))
    if c.get("bayan"):
        body.append(" ".join(c["bayan"]["lines"]))
    pinned = []
    if chain:
        chain_md = " ← ".join(n["name"] + (f" ({n['grade']})" if n.get("grade") else "") for n in chain)
        pinned.append(f"سلسلة السند: {chain_md}.")
    if sanad.get("verdict"):
        pinned.append(f"النتيجة: {sanad['verdict']}" + (f" — {sanad['verdict_sub']}" if sanad.get("verdict_sub") else "") + ".")
    if sanad.get("note"):
        pinned.append(sanad["note"] + ".")
    cta = c.get("cta") or {}
    return {
        "title": c.get("title") or strip_tashkeel(hadith["lines"][0]["t"]),
        "hook": (hook.get("line1", "") + " " + (hook.get("line2") or "")).strip(),
        "body": body,
        "verdict": (sanad.get("verdict") or "") + (f" — {sanad['verdict_sub']}" if sanad.get("verdict_sub") else ""),
        "sources": list(c.get("sources") or []),
        "pinned": pinned,
        "cta": (cta.get("line1", "") + (" " + cta["line2"] if cta.get("line2") else "")).strip(),
        "pace_hint": "plan.py --target 40",
    }


# ----------------------------------------------------------------------------- HyperFrames spec.json
def from_spec(s: dict) -> dict:
    scenes = s.get("scenes") or []
    by = lambda t: [sc for sc in scenes if sc.get("type") == t]  # noqa: E731
    hook = (by("hook") or [{}])[0]
    hook_line = clean(" ".join(x for x in (hook.get("lead", ""), hook.get("line1", ""), hook.get("line2", "")) if x))
    body, sources, pinned = [], [], []
    verdict = ""
    for sc in scenes:
        t = sc.get("type")
        if t == "verse":
            words = [w for line in sc.get("lines") or [] for w in line]
            body.append(clean(sc.get("label", "")) + " " + " ".join(words))
        elif t == "quote":
            body.append(clean(sc.get("label", "")) + " «" + clean(sc.get("text", "")) + "»" + (" " + clean(sc["attribution"]) if sc.get("attribution") else ""))
            if sc.get("attribution"):
                sources.append(clean(sc["attribution"]).lstrip("— ").strip())
        elif t == "answer":
            body.append(" ".join(clean(sc.get(k, "")) for k in ("q1", "q2", "hero", "after") if sc.get(k)))
            if sc.get("source"):
                sources.append(clean(sc["source"]).lstrip("— ").strip())
        elif t == "contrast":
            body.append(" ".join(clean(sc.get(k, "")) for k in ("wrong_label", "wrong", "right_label", "right") if sc.get(k)))
        elif t == "list":
            body.append(clean(sc.get("title", "")) + ": " + " · ".join(clean(i) for i in sc.get("items") or []))
        elif t == "paragraph":
            txt = sc.get("text")
            body.append(clean(" ".join(txt) if isinstance(txt, list) else str(txt or "")))
            if sc.get("source"):
                sources.append(clean(sc["source"]).lstrip("— ").strip())
        elif t == "definition":
            txt = sc.get("body")
            body.append(clean(sc.get("term", "")) + ": " + clean(" ".join(txt) if isinstance(txt, list) else str(txt or "")))
            if sc.get("source"):
                sources.append(clean(sc["source"]).lstrip("— ").strip())
        elif t == "qa":
            txt = sc.get("answer")
            body.append(clean(sc.get("question", "")) + " " + clean(" ".join(txt) if isinstance(txt, list) else str(txt or "")))
            if sc.get("source"):
                sources.append(clean(sc["source"]).lstrip("— ").strip())
        elif t == "steps":
            items = []
            for x in sc.get("items") or []:
                items.append(clean(" ".join(str(x.get(k, "")) for k in ("head", "text") if x.get(k))) if isinstance(x, dict) else clean(x))
            body.append(clean(sc.get("title", "")) + ": " + " · ".join(i for i in items if i))
        elif t == "timeline":
            evs = []
            for x in sc.get("events") or []:
                evs.append(clean(" ".join(str(x.get(k, "")) for k in ("when", "text") if x.get(k))) if isinstance(x, dict) else clean(x))
            body.append(clean(sc.get("title", "")) + ": " + " · ".join(e for e in evs if e))
        elif t == "compare":
            bits = []
            for key in ("col_a", "col_b"):
                c = sc.get(key) or {}
                bits.append(clean(c.get("head", "")) + ": " + " · ".join(clean(x) for x in c.get("points") or []))
            body.append(" | ".join(b for b in bits if b.strip(" :")))
            if sc.get("verdict"):
                body.append(clean(sc["verdict"]))
        elif t == "proof":
            if sc.get("seal"):
                verdict = " ".join(sc["seal"])
            for card in sc.get("cards") or []:
                ref = " ".join(x for x in (card.get("book", ""), card.get("loc", "")) if x)
                sources.append(ref + (f" ({card['grade']})" if card.get("grade") else ""))
            if sc.get("attribution"):
                sources.append(clean(sc["attribution"]).lstrip("— ").strip())
    if verdict:
        pinned.append(f"النتيجة: {verdict}.")
    if sources:
        pinned.append("المصادر: " + "؛ ".join(dict.fromkeys(sources)) + ".")
    cta = (by("cta") or [{}])[0]
    return {
        "title": s.get("title") or strip_tashkeel(hook_line),
        "hook": hook_line,
        "body": [b for b in body if b.strip()],
        "verdict": verdict,
        "sources": list(dict.fromkeys(sources)),
        "pinned": pinned,
        "cta": clean(" ".join(x for x in (cta.get("line1", ""), cta.get("line2", "")) if x)),
        "pace_hint": "shorten the scene where the drop happens (spec: end − 1 s) and rebuild",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="spec.json (HyperFrames) or content.json (Remotion studio)")
    ap.add_argument("--hooks", help="ranked hooks JSON from hook_score_ar.py --out")
    ap.add_argument("-o", "--out", default=None)
    a = ap.parse_args()
    data = load_json(a.source)
    info = from_spec(data) if "scenes" in data else from_content(data)
    tags = pick_tags(" ".join([info["title"], info["hook"], *info["body"], " ".join(info["sources"])]))

    caption = [info["hook"], ""]
    for b in info["body"]:
        caption += [b, ""]
    if info["verdict"]:
        caption += [f"✦ {info['verdict']}", ""]
    if info["sources"]:
        caption += ["المصادر: " + "؛ ".join(info["sources"]), ""]
    if info["cta"]:
        caption += [info["cta"], ""]
    caption.append(" ".join(tags))

    alt_hooks = ""
    if a.hooks and Path(a.hooks).exists():
        ranked = load_json(a.hooks)
        alt_hooks = "\n".join(f"{i + 1}. [{r['score']}] {r['hook']}" for i, r in enumerate(ranked[:5]))
    if not alt_hooks:
        alt_hooks = 'run: python3 scripts/hook_score_ar.py "…" "…" "…" --out hooks.json'

    nl = "\n"
    md = f"""# {info['title']} — Post kit

## Caption (copy as-is)

```
{nl.join(caption)}
```

## Pinned comment (references & grading — pin it right after posting)

```
{nl.join(info['pinned']) if info['pinned'] else "—"}
```

## Alternative hooks (A/B for the cover text or a re-cut)

{alt_hooks}

## Publish checklist

- [ ] Cover = the hero/hook frame; the text sits inside the 4:5 centre crop
- [ ] Caption line 1 = the hook (Imam's name + topic keywords) — Instagram search indexes it
- [ ] Reel topics set in the composer: أهل البيت / حديث / سند
- [ ] Pin the references comment within the first minute; answer the first 10 comments with substance
- [ ] Share to Story with an «أرسِل لمن…» prompt; sends-per-reach is the strongest non-follower signal
- [ ] Original render only — no reposted footage, no watermarks of other pages
- [ ] Post when the Arabic-speaking audience is awake (19:00–22:00 Baghdad/Riyadh; Thursday–Friday nights peak)
- [ ] Read retention after 24 h: early drop → re-cut the hook only (A/B); drop in the middle → {info['pace_hint']}

## Hashtags

{" ".join(tags)}
"""
    out = a.out or str(Path(a.source).with_name("post.md"))
    Path(out).write_text(md, encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
