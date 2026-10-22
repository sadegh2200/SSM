#!/usr/bin/env python3
"""
plan.py — turn content.json into plan.json (timing, pagination, type sizes, SFX cues).

    python3 plan.py content.json [-o plan.json] [--target 46] [--fps 30] [--print]

Rules (all tunable below):
  * On-screen Arabic reading speed ≈ 2.3 words/s  → dwell = 0.45 s + words/2.3 s, clamped.
  * Every scene gets a short in/out breath; scenes overlap by 5 frames for crossfades.
  * Total is nudged toward --target seconds (default 46) and hard-clamped to 30–60 s
    by scaling the *holds* (never the reveal animations).
  * Hadith is paginated when its block would not fit the safe area.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

from _common import letters, load_json, save_json, words, die

FPS_DEFAULT = 30
SAFE_W = 940            # px available for a text line
HADITH_BLOCK_MAX = 790  # px: y 632 → ~1420


def f(sec: float, fps: int) -> int:
    return int(round(sec * fps))


_PACE = 1.0  # set by build_plan(); <1 = faster holds, >1 = slower holds (animations never change)


def dwell(text: str, fps: int, base: float = 0.45, wps: float = 2.3, lo: float = 1.3, hi: float = 5.0) -> int:
    """Frames a line should stay before the next reveal (scaled by the global pace)."""
    return f(min(hi, max(lo, base + words(text) / wps)) * _PACE, fps)


def hold(sec: float, fps: int) -> int:
    """A pure hold (no text) scaled by pace."""
    return f(sec * _PACE, fps)


def fit_size(text: str, max_size: int, min_size: int, em_per_letter: float = 0.6, width: int = SAFE_W) -> int:
    n = max(letters(text), 1)
    return int(max(min_size, min(max_size, math.floor(width / (em_per_letter * n)))))


# ----------------------------------------------------------------------------- scenes

def plan_hook(c, fps):
    h = c["hook"]
    longest = max(letters(h.get("line1", "")), letters(h.get("line2", "") or ""))
    size = int(max(72, min(112, math.floor(1700 / max(longest, 10)))))
    sub_at = 38
    dur = hold(3.1, fps) + (dwell(h.get("sub", ""), fps) // 2 if h.get("sub") else 0)
    dur = int(max(f(2.8, fps), min(f(4.2, fps), dur)))  # a hook never exceeds 4.2 s
    return {"dur": dur, "size": size, "sub_at": sub_at}


def plan_hadith(c, fps):
    h = c["hadith"]
    lines = h["lines"]
    if not lines:
        die("hadith.lines is empty")
    body_lines = [l for l in lines if l.get("style", "body") == "body"]
    max_letters = max([letters(l["t"]) for l in body_lines] or [10])
    body = fit_size(" " * max_letters, 78, 56)
    # vertical budget: shrink before paginating
    intro = 44 if h.get("intro") else 0

    def rows(text, size, em=0.6):
        return max(1, math.ceil(letters(text) * em * size / SAFE_W))

    def block_height(ls, body_size):
        hgt = (intro * 1.8 + 6) if intro else 0
        for l in ls:
            st = l.get("style", "body")
            if st == "lead":
                sz = min(128, body_size * 1.65); hgt += sz * 1.5 * rows(l["t"], sz)
            elif st == "warning":
                sz = min(66, body_size * 0.9); hgt += sz * 1.8 * rows(l["t"], sz)
            else:
                hgt += body_size * 1.75 * rows(l["t"], body_size)
        return hgt

    while block_height(lines, body) > HADITH_BLOCK_MAX and body > 56:
        body -= 2
    # paginate if still too tall
    def greedy():
        out, cur = [], []
        for i, l in enumerate(lines):
            if cur and block_height([lines[j] for j in cur] + [l], body) > HADITH_BLOCK_MAX:
                out.append(cur); cur = []
            cur.append(i)
        if cur:
            out.append(cur)
        return out

    def balanced(n_pages):
        per = math.ceil(len(lines) / n_pages)
        out = [list(range(k, min(k + per, len(lines)))) for k in range(0, len(lines), per)]
        ok = all(block_height([lines[j] for j in pg], body) <= HADITH_BLOCK_MAX for pg in out)
        return out if ok else None

    if block_height(lines, body) > HADITH_BLOCK_MAX:
        g = greedy()
        pages_idx = balanced(len(g)) or g  # prefer evenly filled pages over a lonely last line
    else:
        pages_idx = [list(range(len(lines)))]

    lead = int(min(128, body * 1.65))
    warning = int(min(66, body * 0.9))
    pages = []
    cursor = 0
    for pi, idxs in enumerate(pages_idx):
        t = 0
        intro_at = 22 if (pi == 0 and intro) else 0
        t = intro_at + (dwell(h.get("intro", ""), fps, lo=1.0, hi=1.8) if intro and pi == 0 else 14)
        rel = []
        for i in idxs:
            rel.append({"i": i, "at": t})
            l = lines[i]
            st = l.get("style", "body")
            t += dwell(l["t"], fps) + (12 if st == "lead" else 0) + (18 if st == "warning" else 0)
        bridge_at = None
        if pi == len(pages_idx) - 1 and h.get("bridge"):
            bridge_at = t + 10
            t = bridge_at + dwell(h["bridge"], fps) + 14
        else:
            t += hold(0.7, fps)
        h_page = block_height([lines[i] for i in idxs], body)
        top = int(632 + max(0, min(260, (HADITH_BLOCK_MAX - h_page) / 2.4)))  # short pages sit lower (optical centre)
        page = {"from": cursor, "dur": t, "intro_at": intro_at, "top": top, "lines": rel}
        if bridge_at is not None:
            page["bridge_at"] = bridge_at
        pages.append(page)
        cursor += t - (10 if pi < len(pages_idx) - 1 else 0)
    dur = cursor if len(pages) == 1 else pages[-1]["from"] + pages[-1]["dur"]
    return {"dur": dur, "body": body, "lead": lead, "warning": warning, "intro": intro, "pages": pages}


def plan_points(c, fps):
    pts = c.get("points") or []
    if not pts:
        return None
    longest_title = max(letters(p["title"]) for p in pts)
    title = fit_size(" " * longest_title, 104, 72, em_per_letter=0.55)
    longest_desc = max([letters(d) for p in pts for d in (p.get("desc") or [])] or [10])
    desc = fit_size(" " * longest_desc, 44, 34, em_per_letter=0.5)
    cards = []
    cursor = 0
    for i, p in enumerate(pts):
        hold_ = 40 + dwell(p["title"], fps)
        for d in p.get("desc") or []:
            hold_ += dwell(d, fps, lo=1.0)
        q = p.get("quote") or {}
        qlines = q.get("lines") or [x for x in [q.get("a"), q.get("b")] if x]
        for ql in qlines:
            hold_ += dwell(ql, fps, lo=1.1)
        if q.get("src"):
            hold_ += 12
        hold_ = int(max(hold(3.6, fps), min(hold(7.5, fps), hold_)))
        overlap = 0 if i == 0 else 8
        cards.append({"from": cursor - overlap, "dur": hold_ + overlap})
        cursor += hold_
    return {"dur": cursor, "cards": cards, "title": title, "desc": desc}


def plan_bayan(c, fps):
    b = c.get("bayan")
    if not b or not b.get("lines"):
        return None
    longest = max(letters(l) for l in b["lines"])
    size = fit_size(" " * longest, 56, 40, em_per_letter=0.55, width=840)
    est = (64 * 1.45 + 60 if b.get("title") else 0) + 68 + (60 if b.get("src") else 0)
    for l in b["lines"]:
        est += size * 1.8 * max(1, math.ceil(letters(l) * 0.55 * size / 840))
    top = int(max(460, min(700, 940 - est / 2)))  # vertically centred block
    t = 24 if b.get("title") else 8
    lines_at = []
    for l in b["lines"]:
        lines_at.append(t)
        t += dwell(l, fps)
    t += (14 if b.get("src") else 0) + hold(1.2, fps)
    return {"dur": int(max(hold(4, fps), min(hold(10, fps), t))), "size": size, "top": top, "lines_at": lines_at}


def plan_sanad(c, fps):
    s = c.get("sanad")
    if not s:
        return None
    chain = s.get("chain") or []
    n = len(chain)
    row = int(min(112, math.floor(800 / n))) if n else 112
    name = 40 if row >= 100 else 34 if row >= 80 else 30
    chip = 28 if row >= 100 else 24
    start = 30
    step = int(max(16, min(30, 26 - 2 * max(0, n - 7)))) if n else 0
    after_chain = start + step * max(n - 1, 0) + 24 if n else 24
    seal_at = after_chain if s.get("verdict") else after_chain
    tail = hold(3.4, fps) + (hold(0.8, fps) if s.get("note") else 0)
    dur = seal_at + tail if s.get("verdict") else after_chain + hold(1.0, fps)
    return {"dur": int(dur), "start": start, "step": step, "seal_at": int(seal_at), "row": row, "name": name, "chip": chip}


def plan_cta(c, fps):
    cta = c.get("cta") or {}
    dur = hold(5.6, fps) + (hold(0.8, fps) if cta.get("footer") else 0) + (hold(0.6, fps) if c.get("sources") else 0)
    return {"dur": int(dur)}


# ----------------------------------------------------------------------------- sfx

def sfx_for(order, scenes, c):
    cues = []
    add = lambda at, src, vol: cues.append({"at": int(at), "src": src, "vol": vol})
    for sid in order:
        sc = scenes[sid]
        a = sc["from"]
        if sid == "hook":
            add(0, "boom", 0.7)
            add(3, "whoosh", 0.35)
        elif sid == "hadith":
            add(a, "page-turn", 0.4)
            for p in sc["pages"]:
                for l in p["lines"]:
                    st = c["hadith"]["lines"][l["i"]].get("style", "body")
                    add(a + p["from"] + l["at"], "whoosh" if st == "lead" else "stamp" if st == "warning" else "tick", 0.3 if st == "lead" else 0.55 if st == "warning" else 0.7)
                if "bridge_at" in p:
                    add(a + p["from"] + p["bridge_at"], "tick", 0.5)
        elif sid == "points":
            add(a, "page-turn", 0.4)
            for card in sc["cards"]:
                add(a + card["from"] + 14, "whoosh", 0.3)
                add(a + card["from"] + 34, "tick", 0.6)
        elif sid == "bayan":
            add(a, "page-turn", 0.4)
            for t in sc["lines_at"]:
                add(a + t, "tick", 0.6)
        elif sid == "sanad":
            add(a, "page-turn", 0.4)
            chain = (c.get("sanad") or {}).get("chain") or []
            for i, node in enumerate(chain):
                at = a + sc["start"] + sc["step"] * i
                add(at, "tick", 0.55)
                if node.get("grade"):
                    add(at + 10, "stamp", 0.5)
            if (c.get("sanad") or {}).get("verdict"):
                add(a + sc["seal_at"], "ding", 0.4)
                add(a + sc["seal_at"], "boom", 0.4)
        elif sid == "cta":
            add(a, "page-turn", 0.4)
            add(a + 30, "whoosh", 0.35)
            add(a + 78, "tick", 0.6)
            add(a + 88, "tick", 0.6)
    return cues


# ----------------------------------------------------------------------------- main

def build_scenes(c, fps):
    order, scenes = [], {}
    scenes["hook"] = plan_hook(c, fps); order.append("hook")
    scenes["hadith"] = plan_hadith(c, fps); order.append("hadith")
    pts = plan_points(c, fps)
    if pts: scenes["points"] = pts; order.append("points")
    bay = plan_bayan(c, fps)
    if bay: scenes["bayan"] = bay; order.append("bayan")
    san = plan_sanad(c, fps)
    if san: scenes["sanad"] = san; order.append("sanad")
    scenes["cta"] = plan_cta(c, fps); order.append("cta")
    cursor = 0
    for sid in order:
        scenes[sid]["from"] = cursor
        cursor += scenes[sid]["dur"] - 5  # 5-frame crossfade overlap
    return order, scenes, cursor + 5


def build_plan(c, fps=FPS_DEFAULT, target=46.0):
    """Plan at pace 1.0, then re-plan with pace = target/total (bounded) until within ±2 s."""
    global _PACE
    _PACE = 1.0
    order, scenes, total = build_scenes(c, fps)
    tgt = f(target, fps)
    for _ in range(4):
        if abs(total - tgt) <= f(2.0, fps):
            break
        _PACE = max(0.55, min(1.12, _PACE * tgt / total))  # never stretch holds by more than 12 %
        if _PACE >= 1.12 and total < tgt:
            order, scenes, total = build_scenes(c, fps)
            break
        order, scenes, total = build_scenes(c, fps)
    lo, hi = f(30, fps), f(60, fps)
    if total > hi:
        _PACE = max(0.5, _PACE * (hi - 15) / total)
        order, scenes, total = build_scenes(c, fps)
    if total > hi:
        print(f"WARNING: total {total/fps:.1f}s exceeds 60s even at pace {_PACE:.2f} — shorten content (hadith lines / points / chain).")
    if total < lo:
        _PACE = min(1.6, _PACE * (lo + 15) / total)
        order, scenes, total = build_scenes(c, fps)
        print(f"NOTE: content is short — stretched pace to {_PACE:.2f} to reach 30 s; consider adding a bayan scene or a second supporting narration.")
    if _PACE <= 0.6:
        print(f"WARNING: reading pace is at the floor ({_PACE:.2f}) — the content is heavy for one Reel; consider splitting it (e.g. hadith+sanad now, points later).")
    plan = {"fps": fps, "total": int(total), "pace": round(_PACE, 3), "order": order, "scenes": scenes}
    plan["sfx"] = sfx_for(order, scenes, c)
    return plan


def describe(plan):
    fps = plan["fps"]
    print(f"total {plan['total']/fps:.1f}s  ({plan['total']} frames @ {fps}fps, pace {plan.get('pace', 1)})")
    for sid in plan["order"]:
        sc = plan["scenes"][sid]
        extra = ""
        if sid == "hadith":
            extra = f" body={sc['body']}px lead={sc['lead']}px pages={len(sc['pages'])}"
        if sid == "points":
            extra = f" cards={len(sc['cards'])} title={sc['title']}px"
        if sid == "sanad":
            extra = f" row={sc['row']}px step={sc['step']}f seal@{sc['seal_at']}f"
        print(f"  {sid:7s} {sc['from']/fps:5.1f}s → {(sc['from']+sc['dur'])/fps:5.1f}s  ({sc['dur']/fps:4.1f}s){extra}")
    print(f"  sfx cues: {len(plan['sfx'])}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("content")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--target", type=float, default=46.0, help="target seconds (30–60)")
    ap.add_argument("--fps", type=int, default=FPS_DEFAULT)
    ap.add_argument("--print", action="store_true")
    a = ap.parse_args()
    c = load_json(a.content)
    plan = build_plan(c, a.fps, a.target)
    out = a.out or str(Path(a.content).with_name("plan.json"))
    save_json(plan, out)
    describe(plan)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
