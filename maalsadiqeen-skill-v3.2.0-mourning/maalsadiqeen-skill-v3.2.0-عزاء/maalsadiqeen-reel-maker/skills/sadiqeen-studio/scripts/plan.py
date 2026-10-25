#!/usr/bin/env python3
"""Spec resolution: contiguity, cues, reading speed, word budget.

A spec is the brand's own format (see the `maalsadiqeen-reel` skill):
`{id, title, duration, theme, audio, scenes:[{id, type, start, end, …fields}]}`.

`resolve()` never changes what the reel *says*; it only adds the clock: when each reveal
lands, when the last one has to be on screen, and whether the copy fits the word budget.
That is what makes the build reproducible and the verification numeric.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

READ_WORD, READ_MIN, READ_PROSE, PROSE_MIN, GAP = 0.26, 1.15, 0.30, 1.80, 0.18

_EM = re.compile(r"<em>(.*?)</em>", re.S)

# which fields are revealed, and in what order, per block
REVEALS = {
    "hook": ["lead", "line1", "line2", "sub"],
    "verse": [],
    "contrast": ["wrong_label", "wrong", "right_label", "right", "line3", "line4"],
    "answer": ["q1", "q2", "hero", "after", "source"],
    "proof": ["cards", "line1", "line2", "attribution"],
    "cta": ["line1", "line2", "share", "final", "brand"],
    "quote": ["label", "text", "attribution"],
    "list": ["title", "items", "attribution"],
    "title": ["kicker", "title", "sub"],
    "paragraph": ["text"],
    "definition": ["term", "text", "note"],
    "steps": ["title", "steps"],
    "timeline": ["title", "events"],
    "compare": ["left", "right", "verdict"],
    "qa": ["question", "answer"],
}

PROSE_BLOCKS = {"paragraph", "definition", "qa", "compare", "steps", "timeline"}


def _words(s) -> int:
    if isinstance(s, list):
        return sum(_words(x) for x in s)
    if isinstance(s, dict):
        return sum(_words(v) for v in s.values())
    return len(_EM.sub(r"\1", str(s or "")).split())


def _dur(words: int, prose: bool) -> float:
    if prose:
        return max(PROSE_MIN, READ_PROSE * words + 0.55) + GAP
    return max(READ_MIN, READ_WORD * words) + GAP


def _default_cues(sc: dict) -> dict:
    t0, t1 = float(sc["start"]), float(sc["end"])
    typ = sc["type"]
    c: dict = {}
    pad = 0.05
    if typ == "hook":
        base = {"lead": 0.0, "line1": 0.16, "line2": 0.34, "rule": 0.85, "sub": 1.00}
        for k, v in base.items():
            c[k] = round(t0 + v, 2)
        c["emphasis"] = round(min(t1 - 1.2, t0 + 1.9), 2)
    elif typ == "verse":
        lines = sc.get("lines") or []
        words = [w for ln in lines for w in ln]
        span = max(0.4, (t1 - t0) - 1.9)
        step = span / max(1, len(words))
        c["words"] = [round(t0 + 0.3 + i * step, 2) for i in range(len(words))]
        hl = sc.get("highlight") or {}
        at = hl.get("at")
        c["highlight"] = round(float(at), 2) if at else round(t0 + (t1 - t0) * 0.72, 2)
    elif typ == "contrast":
        c = {"wrong_label": round(t0 + 0.05, 2), "wrong": round(t0 + 0.30, 2),
             "strike": round(t0 + _dur(_words(sc.get("wrong")), False) * 0.8, 2),
             "right_label": round(t0 + 1.70, 2), "right": round(t0 + 1.95, 2),
             "line3": round(t0 + 3.4, 2), "line4": round(t0 + 4.6, 2),
             "line4_gold": round(t0 + 5.8, 2)}
    elif typ == "answer":
        c = {"q1": round(t0 + 0.30, 2), "q2": round(t0 + 1.50, 2),
             "hero": round(t0 + 3.00, 2), "after": round(t0 + 4.90, 2),
             "source": round(t0 + 5.80, 2)}
    elif typ == "proof":
        cards = sc.get("cards") or []
        c = {"seal": round(t0 + 0.80, 2),
             "cards": [round(t0 + 2.0 + i * 1.1, 2) for i in range(len(cards))],
             "line1": round(t0 + 2.0 + len(cards) * 1.1 + 0.6, 2),
             "line2": round(t0 + 2.0 + len(cards) * 1.1 + 1.7, 2),
             "attribution": round(t0 + 2.0 + len(cards) * 1.1 + 2.4, 2)}
    elif typ == "cta":
        c = {"line1": round(t0 + 0.30, 2), "line2": round(t0 + 1.40, 2),
             "share": round(t0 + 2.70, 2), "final": round(t0 + 3.60, 2),
             "brand": round(t1 - 1.55, 2)}
    elif typ == "quote":
        c = {"label": round(t0 + 0.20, 2), "text": round(t0 + 0.55, 2),
             "attribution": round(t1 - 1.30, 2)}
    elif typ == "list":
        items = sc.get("items") or []
        c = {"title": round(t0 + 0.20, 2),
             "items": [round(t0 + 0.9 + i * 0.95, 2) for i in range(len(items))],
             "attribution": round(t1 - 1.10, 2)}
    elif typ == "title":
        c = {"kicker": round(t0 + 0.20, 2), "title": round(t0 + 0.55, 2),
             "sub": round(t0 + 1.40, 2)}
    elif typ == "paragraph":
        sents = _sentences(sc.get("text", ""))
        t = t0 + 0.35
        out = []
        for s in sents:
            out.append(round(t, 2))
            t += _dur(_words(s), True)
        c = {"text": out}
    elif typ == "definition":
        sents = _sentences(sc.get("text", ""))
        out = []
        t = t0 + 1.15
        for s in sents:
            out.append(round(t, 2))
            t += _dur(_words(s), True)
        c = {"term": round(t0 + 0.25, 2), "text": out,
             "note": round(min(t, t1 - 1.4), 2)}
    elif typ == "qa":
        sents = _sentences(sc.get("answer", ""))
        out = []
        t = t0 + 1.9
        for s in sents:
            out.append(round(t, 2))
            t += _dur(_words(s), True)
        c = {"question": round(t0 + 0.30, 2), "answer": out}
    elif typ == "steps":
        steps = sc.get("steps") or []
        c = {"title": round(t0 + 0.20, 2),
             "steps": [round(t0 + 0.9 + i * 1.5, 2) for i in range(len(steps))]}
    elif typ == "timeline":
        evs = sc.get("events") or []
        c = {"title": round(t0 + 0.20, 2),
             "events": [round(t0 + 0.9 + i * 1.6, 2) for i in range(len(evs))]}
    elif typ == "compare":
        c = {"left": round(t0 + 0.30, 2), "right": round(t0 + 1.40, 2),
             "verdict": round(t1 - 2.30, 2)}
    return c


def _sentences(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"(?<=[.؟!])\s+", _EM.sub(r"\1", text or "")) if p.strip()]
    return parts or ([text] if text else [])


def resolve(spec: dict, duration: float | None = None) -> dict:
    """Return a copy of the spec with `t0/t1/cues` filled in on every scene."""
    out = json.loads(json.dumps(spec, ensure_ascii=False))
    scenes = out["scenes"]
    for i, sc in enumerate(scenes):
        sc.setdefault("start", 0.0 if i == 0 else scenes[i - 1].get("end"))
        sc["start"] = float(sc["start"])
        if "end" not in sc or sc["end"] is None:
            sc["end"] = float(duration or out.get("duration") or 40.0)
        sc["end"] = float(sc["end"])
        given = sc.get("cues") or {}
        cues = _default_cues(sc)
        # a spec may override any cue; lists merge positionally
        for k, v in given.items():
            cues[k] = v
        sc["cues"] = cues
    out["duration"] = float(duration or out.get("duration") or scenes[-1]["end"])
    out["scenes"][-1]["end"] = out["duration"]
    return out


def audit(res: dict) -> dict:
    """Numbers the verification stage turns into pass / warn / fail."""
    dur = res["duration"]
    words = 0
    issues: list[dict] = []
    for sc in res["scenes"]:
        for key, val in sc.items():
            if key in ("id", "type", "start", "end", "cues", "theme"):
                continue
            words += _words(val)
        # every reveal must land at least 0.9 s before the cut
        last = 0.0
        for k, v in sc["cues"].items():
            for t in (v if isinstance(v, list) else [v]):
                if isinstance(t, (int, float)):
                    last = max(last, float(t))
        slack = round(sc["end"] - last, 2)
        if slack < 0.9:
            issues.append({"level": "warn", "scene": sc["id"],
                           "what": "last reveal is %.2fs before the cut" % slack,
                           "fix": "extend the scene, or move the reveal earlier — do not cut the "
                                  "sentence in half"})
        if sc["type"] == "hook" and sc["end"] - sc["start"] > 4.5:
            issues.append({"level": "warn", "scene": sc["id"],
                           "what": "hook runs %.1fs" % (sc["end"] - sc["start"]),
                           "fix": "the first cut must land inside the 3-second cliff"})
    hero = sum(1 for s in res["scenes"] if s["type"] == "answer" or s.get("hero"))
    if hero != 1:
        issues.append({"level": "warn" if hero == 0 else "fail", "scene": "-",
                       "what": f"{hero} hero moments",
                       "fix": "one hero line per reel (answer.hero or quote.hero) at 50–65 % "
                              "of the runtime; the cta.final is the closing line, not a hero"})
    soft, hard = max(95, 2.3 * dur), max(110, 2.9 * dur)
    if words > hard:
        issues.append({"level": "fail", "scene": "-",
                       "what": f"{words} on-screen words for {dur:.0f}s (hard {hard:.0f})",
                       "fix": "move a paragraph into the caption, or split into a series"})
    elif words > soft:
        issues.append({"level": "warn", "scene": "-",
                       "what": f"{words} on-screen words (soft {soft:.0f})",
                       "fix": "one dense block is enough; the rest stay short"})
    return {"words": words, "soft": round(soft), "hard": round(hard),
            "duration": dur, "scenes": len(res["scenes"]), "issues": issues}


def load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
