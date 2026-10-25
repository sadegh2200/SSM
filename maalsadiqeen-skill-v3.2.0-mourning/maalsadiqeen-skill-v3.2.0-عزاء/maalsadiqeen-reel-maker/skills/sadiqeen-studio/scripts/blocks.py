#!/usr/bin/env python3
"""The block library — fifteen blocks, one page.

Each builder is a small, readable composition recipe: it takes the resolved scene, the
theme tokens and the stage, and returns the sound cues it wants. The look is the brand's:
paper, one hero, gold hairlines, sacred text in Amiri Quran, prose right-aligned in Naskh
with a gold margin rule, nothing centred just because it is easy.

Every builder obeys the same three rules:
  1. one idea per frame — if a block needs a second idea, it is two blocks;
  2. attribution lands last, always;
  3. no element leaves alone: exits are collective (the Stage handles the cut).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFilter

import brandkit as bk
import typo
from brandkit import CX, H, W, rgb
import stage
from stage import El, Enter, Exit, diamond, panel, rule, seal

SFX_CLICK, SFX_SCRATCH = "click-soft", "pen-scratch"
SFX_IMPACT, SFX_CHIME = "impact-bass-1", "chime"
SFX_SPARK, SFX_WHOOSH = "sparkle", "whoosh-short"


# --------------------------------------------------------------------------- helpers
@dataclass
class Part:
    ink: object
    gap: int = 22
    t: float = 0.0
    enter: Enter | None = None
    wipe: tuple | None = None
    alpha: float = 1.0
    cx: float | None = None
    cy: float | None = None
    push: float = 0.0
    breathe: tuple | None = None
    z: int = 10


def _flow(st, parts: list[Part], cy: float, t1: float, x: float = CX) -> list[El]:
    total = sum(p.ink.img.height for p in parts) + sum(p.gap for p in parts[:-1])
    y = cy - total / 2
    out = []
    for p in parts:
        h = p.ink.img.height
        el = st.text(p.ink, p.cx if p.cx is not None else x, y + h / 2, p.t, t1,
                     p.enter, Exit(), p.wipe, p.alpha, p.z, p.push, p.breathe)
        out.append(el)
        y += h + p.gap
    return out


def _label(text: str, tk: dict, px: int = 30, color: str = "gold"):
    """A label line. The verse brackets «﴿ ﴾» are drawn, not typed: no installed font has
    U+FD3E/FD3F, and the substitute would be a tofu box on the brand's most quoted line."""
    clean = text.replace("﴿", "").replace("﴾", "").strip()
    key = "amiri" if typo._LATIN.search(clean) else "kufi_r"
    return typo.layout(clean, key, px, rgb(tk[color]))


def _verse_label(st, text, tk, cx, cy, t_in, t_out, alpha=0.95) -> None:
    ink = _label(text, tk, 30)
    st.add(El(ink.img, cx, cy, t_in, t_out,
              Enter(dy=10, dur=0.55, scale=1.0, blur=5), Exit(), None, alpha, 10))
    if "﴿" in text or "﴾" in text:
        h = 34
        left = stage.flourish(h, rgb(tk["gold"]), mirror=True)
        right = stage.flourish(h, rgb(tk["gold"]))
        pad = 20
        st.add(El(right, cx + ink.img.width / 2 + pad + left.width / 2, cy, t_in, t_out,
                  Enter(dy=6, dur=0.5, scale=1.0, blur=3), Exit(), None, alpha, 10))
        st.add(El(left, cx - ink.img.width / 2 - pad - left.width / 2, cy, t_in, t_out,
                  Enter(dy=6, dur=0.5, scale=1.0, blur=3), Exit(), None, alpha, 10))


def _body(text: str, tk: dict, px: int = 46, color: str = "ink", key: str = "naskh"):
    return typo.layout(text, key, px, rgb(tk[color]), rgb(tk["gold"]))


def _rule_el(st, tk, width: int, y: float, t: float, t1: float, thick: int = 2,
             alpha: int = 235) -> El:
    return st.add(El(rule(width, thick, rgb(tk["gold"]), alpha), CX, y, t, t1,
                     None, Exit(), (t, 0.6)))


def _fade(st, img, cx, cy, t_in, t_out, alpha=1.0, z=9) -> El:
    return st.add(El(img, cx, cy, t_in, t_out, Enter(dy=0, dur=0.34, scale=1.0, blur=0.0),
                     Exit(), None, alpha, z))


def _sentences(text: str) -> list[str]:
    import re
    parts = [p.strip() for p in re.split(r"(?<=[.؟!])\s+", text or "") if p.strip()]
    return parts or [text]


# ------------------------------------------------------------------------- the blocks
def build_hook(st, sc, tk, c, t0, t1) -> list:
    cues = [(c["line1"], SFX_CLICK, -20), (c["line2"], SFX_IMPACT, -14)]
    parts = []
    if sc.get("lead"):
        px = typo.fit(sc["lead"], sc.get("lead_font", "amiri"), int(bk.COL_W * 0.9), 54, 30)
        parts.append(Part(typo.layout(sc["lead"], sc.get("lead_font", "amiri"), px,
                                      rgb(tk["ink2"])), gap=16, t=c.get("lead", t0),
                          enter=Enter(dy=18, dur=0.7), alpha=0.92))
    if sc.get("line1"):
        px = typo.fit(sc["line1"], "kufi", bk.COL_W, 104, 44)
        parts.append(Part(_body(sc["line1"], tk, px, "ink", "kufi"), gap=8,
                          t=c.get("line1", t0 + 0.16), enter=Enter(dy=24, dur=0.72)))
    line2 = sc.get("line2") or sc.get("title") or ""
    line2_ink = None
    if line2:
        px = typo.fit(line2, "kufi", int(bk.COL_W * 1.0), 138, 56)
        line2_ink = _body(line2, tk, px, "ink", "kufi")
        parts.append(Part(line2_ink, gap=34,
                          t=c.get("line2", t0 + 0.34), enter=Enter(dy=30, dur=0.8)))
    if sc.get("sub"):
        px = typo.fit(sc["sub"], "naskh", int(bk.COL_W * 0.8), 34, 22)
        parts.append(Part(_body(sc["sub"], tk, px, "ink2"), gap=0,
                          t=c.get("sub", t0 + 1.0), enter=Enter(dy=14, dur=0.6)))

    cy = 940 if sc.get("lead") else 905
    els = _flow(st, parts, cy, t1)
    # the gold underline under the hero word, drawn after it lands
    hero_el = next((e for e in els if line2_ink is not None and e.img is line2_ink.img), None)
    if hero_el is None and els:
        hero_el = els[-1]
    if hero_el is not None and line2_ink is not None:
        w = min(bk.COL_W, int(hero_el.img.width * 0.62))
        y = hero_el.cy + hero_el.img.height / 2 - 6
        st.add(El(rule(w, 3, rgb(tk["gold"]), 240), CX, y, c.get("emphasis", t0 + 1.9), t1,
                  None, Exit(), (c.get("emphasis", t0 + 1.9), 0.62)))
        glow = rule(w, 10, rgb(tk["gold2"]), 60)
        _fade(st, glow, CX, y, c.get("emphasis", t0 + 1.9) + 0.2,
              c.get("emphasis", t0 + 1.9) + 1.6, alpha=1.0, z=8)
    return cues


def build_title(st, sc, tk, c, t0, t1) -> list:
    parts = []
    if sc.get("kicker"):
        parts.append(Part(_label(sc["kicker"], tk, 30), gap=20, t=c.get("kicker", t0),
                          enter=Enter(dy=14, dur=0.6)))
    title = sc.get("title") or ""
    if title:
        px = typo.fit(title, "kufi", bk.COL_W, 110, 48)
        parts.append(Part(_body(title, tk, px, "ink", "kufi"), gap=28,
                          t=c.get("title", t0 + 0.35), enter=Enter(dy=26, dur=0.8)))
    if sc.get("sub"):
        parts.append(Part(_body(sc["sub"], tk, 34, "ink2"), gap=0, t=c.get("sub", t0 + 1.2),
                          enter=Enter(dy=14, dur=0.6)))
    els = _flow(st, parts, bk.OPTICAL_Y, t1)
    _rule_el(st, tk, 220, (els[1].cy + els[1].img.height / 2 - 4) if len(els) > 1 else 1000,
             c.get("title", t0 + 0.9), t1)
    return [(c.get("title", t0), SFX_CLICK, -20)]


def build_verse(st, sc, tk, c, t0, t1) -> list:
    """Word by word, right to left. The highlighted words turn gold and grow 4 %."""
    font = sc.get("font", "quran")
    key = "quran" if font == "quran" else "amiri_b"
    lines = sc.get("lines") or []
    hi = sc.get("size") or (122 if key == "quran" else 104)
    joined = [" ".join(ln) for ln in lines]
    px = min(typo.fit(j, key, int(bk.COL_W * 1.0), hi, 34) for j in joined) if joined else hi
    hl = set(int(i) for i in ((sc.get("highlight") or {}).get("words") or []))
    hl_at = float(c.get("highlight", t0 + (t1 - t0) * 0.72))
    word_cues = c.get("words") or []
    gold, ink = rgb(tk["gold"]), rgb(tk["green"])
    gap = int(px * 0.24)

    # measure first, so the block can be centred on its ink and share one baseline
    prepared = []
    for ln in lines:
        words = [typo.layout(w, key, px, ink) for w in ln]
        total = sum(w.img.width for w in words) + gap * max(0, len(words) - 1)
        base = max([w.baseline for w in words] or [px])
        hi_ink = max([w.baseline for w in words] or [px]) + \
            max([w.img.height - w.baseline for w in words] or [0])
        prepared.append((words, total, hi_ink, base))
    leading = int(px * 1.62)
    block_h = leading * len(prepared)
    label = _label(sc["label"], tk, 30) if sc.get("label") else None
    label_h = (label.img.height + 26) if label else 0
    top = bk.OPTICAL_Y - (block_h + label_h) / 2
    if label:
        _verse_label(st, sc["label"], tk, CX, top + label.img.height / 2, t0 + 0.15, t1)
    y = top + label_h

    idx = 0
    for words, total, hi_ink, base in prepared:
        x_right = CX + total / 2
        baseline_y = y + (leading - hi_ink) / 2 + base
        for w_ink in words:
            cx = x_right - w_ink.img.width / 2
            cy = baseline_y - w_ink.baseline + w_ink.img.height / 2
            t_in = float(word_cues[idx]) if idx < len(word_cues) else t0 + 0.3 + idx * 0.3
            hot = (idx + 1) in hl
            st.text(w_ink, cx, cy, t_in, hl_at if hot else t1, Enter(dy=14, dur=0.5))
            if hot:
                st.text(w_ink.tinted(gold), cx, cy, hl_at, t1,
                        Enter(dy=0, dur=0.42, scale=1.05, blur=5))
            x_right -= w_ink.img.width + gap
            idx += 1
        y += leading

    cues = [(float(t), SFX_CLICK, -30) for t in word_cues[:3]]
    if hl:
        cues.append((hl_at, SFX_SPARK, -16))
    return cues


def build_contrast(st, sc, tk, c, t0, t1) -> list:
    cues = [(c.get("strike", t0 + 1.0), SFX_SCRATCH, -18)]
    parts = []
    if sc.get("wrong_label"):
        parts.append(Part(_label(sc["wrong_label"], tk, 28, "ink2"), gap=10,
                          t=c.get("wrong_label", t0), enter=Enter(dy=12, dur=0.5)))
    wrong = sc.get("wrong") or ""
    wrong_el = None
    if wrong:
        px = typo.fit(wrong, "amiri", int(bk.COL_W * 0.92), 60, 34)
        wrong_ink = typo.layout(wrong, "amiri", px, rgb(tk["ink2"]))
        parts.append(Part(wrong_ink, gap=30, t=c.get("wrong", t0 + 0.3),
                          enter=Enter(dy=16, dur=0.6), alpha=0.9))
    if sc.get("right_label"):
        parts.append(Part(_label(sc["right_label"], tk, 30), gap=10,
                          t=c.get("right_label", t0 + 1.7), enter=Enter(dy=12, dur=0.5)))
    right = sc.get("right") or ""
    right_el = None
    if right:
        px = typo.fit(typo._EM.sub(r"\1", right), "amiri_b", int(bk.COL_W * 0.95), 76, 38)
        parts.append(Part(typo.layout(right, "amiri_b", px, rgb(tk["ink"]), rgb(tk["gold"])),
                          gap=32, t=c.get("right", t0 + 1.95),
                          enter=Enter(dy=22, dur=0.72)))
    if sc.get("line3"):
        px = typo.fit(sc["line3"], "kufi", int(bk.COL_W * 0.9), 52, 30)
        parts.append(Part(_body(sc["line3"], tk, px, "ink", "kufi"), gap=14,
                          t=c.get("line3", t0 + 3.4), enter=Enter(dy=18, dur=0.6)))
    if sc.get("line4"):
        px = typo.fit(typo._EM.sub(r"\1", sc["line4"]), "naskh", int(bk.COL_W * 0.95), 44, 28)
        parts.append(Part(typo.layout(sc["line4"], "naskh", px, rgb(tk["ink2"]), rgb(tk["gold"])),
                          gap=0, t=c.get("line4", t0 + 4.6), enter=Enter(dy=16, dur=0.6)))
    els = _flow(st, parts, bk.OPTICAL_Y, t1)

    # a gold bar through the wrong reading, drawn from the right
    if wrong:
        el = els[1] if len(els) > 1 else els[0]
        strike = float(c.get("strike", t0 + 1.0))
        st.add(El(rule(int(el.img.width * 0.96), 4, rgb(tk["gold"]), 235), el.cx, el.cy,
                  strike, t1, None, Exit(), (strike, 0.45)))
        st.add(El(rule(int(el.img.width * 0.96), 12, rgb(tk["gold2"]), 40), el.cx, el.cy,
                  strike + 0.1, strike + 0.8, Enter(dy=0, dur=0.3, scale=1.0, blur=0.0),
                  Exit(), None, 1.0, 8))
    if sc.get("line4") and els:
        last = els[-1]
        gold_px = typo.fit(typo._EM.sub(r"\1", sc["line4"]), "naskh",
                           int(bk.COL_W * 0.95), 44, 28)
        glow = typo.layout(sc["line4"], "naskh", gold_px, rgb(tk["gold"]), rgb(tk["gold2"]))
        el = st.text(glow, last.cx, last.cy, c.get("line4_gold", t0 + 5.8), t1,
                     Enter(dy=0, dur=0.5, blur=3))
        last.t_out = min(last.t_out, c.get("line4_gold", t0 + 5.8))
    return cues


def build_quote(st, sc, tk, c, t0, t1) -> list:
    parts = []
    if sc.get("label"):
        parts.append(Part(_label(sc["label"], tk, 30), gap=26, t=c.get("label", t0),
                          enter=Enter(dy=12, dur=0.5)))
    text = sc.get("text")
    key = "amiri_b" if sc.get("hero") else "amiri"
    lines = text if isinstance(text, list) else [text]
    px, wrapped = typo.fit_wrapped(" ".join(lines), key, int(bk.COL_W * 0.98), 760, 84, 34)
    shown = lines if isinstance(text, list) else wrapped
    for i, ln in enumerate(shown):
        parts.append(Part(typo.layout(ln, key, px, rgb(tk["ink"]), rgb(tk["gold"])),
                          gap=int(px * 0.34), t=c.get("text", t0 + 0.5) + i * 0.55,
                          enter=Enter(dy=22, dur=0.7),
                          wipe=(c.get("text", t0 + 0.5) + i * 0.55 - 0.1, 0.75) if sc.get("hero") else None))
    if sc.get("attribution"):
        parts.append(Part(_body(sc["attribution"], tk, 30, "ink2"), gap=0,
                          t=c.get("attribution", t1 - 1.3), enter=Enter(dy=12, dur=0.6)))
    els = _flow(st, parts, bk.OPTICAL_Y + 20, t1)
    if sc.get("hero") and els:
        hero = els[0] if not sc.get("label") else els[1]
        _rule_el(st, tk, 300, hero.cy + hero.img.height / 2 - 2,
                 c.get("text", t0 + 0.9) + 0.9, t1)
    return [(c.get("text", t0), SFX_CLICK, -22)]


def build_answer(st, sc, tk, c, t0, t1) -> list:
    cues = [(c.get("hero", t0 + 3.0), SFX_IMPACT, -12),
            (max(t0, c.get("hero", t0 + 3.0) - 0.6), "riser", -24)]
    parts = []
    if sc.get("q1"):
        px = typo.fit(sc["q1"], "amiri", int(bk.COL_W * 0.92), 50, 30)
        parts.append(Part(typo.layout(sc["q1"], "amiri", px, rgb(tk["ink2"])), gap=8,
                          t=c.get("q1", t0 + 0.3), enter=Enter(dy=14, dur=0.6)))
    if sc.get("q2"):
        px = typo.fit(sc["q2"], "naskh", int(bk.COL_W * 0.92), 42, 26)
        parts.append(Part(typo.layout(sc["q2"], "naskh", px, rgb(tk["ink2"])), gap=54,
                          t=c.get("q2", t0 + 1.5), enter=Enter(dy=14, dur=0.6)))
    hero_ink = None
    if sc.get("hero"):
        px = typo.fit(typo._EM.sub(r"\1", sc["hero"]), "amiri_b", int(bk.COL_W * 1.0), 118, 46)
        hero_ink = typo.layout(sc["hero"], "amiri_b", px, rgb(tk["ink"]), rgb(tk["gold"]))
        parts.append(Part(hero_ink, gap=30, t=c.get("hero", t0 + 3.0),
                          enter=Enter(dy=26, dur=0.9, blur=12), push=0.008,
                          wipe=(c.get("hero", t0 + 3.0) - 0.15, 0.95)))
    if sc.get("after"):
        px = typo.fit(typo._EM.sub(r"\1", sc["after"]), "amiri", int(bk.COL_W * 0.92), 46, 28)
        parts.append(Part(typo.layout(sc["after"], "amiri", px, rgb(tk["ink"]), rgb(tk["gold"])),
                          gap=22, t=c.get("after", t0 + 4.9), enter=Enter(dy=16, dur=0.6)))
    if sc.get("source"):
        px = typo.fit(sc["source"], "naskh", int(bk.COL_W * 0.86), 30, 20)
        parts.append(Part(typo.layout(sc["source"], "naskh", px, rgb(tk["ink2"])), gap=0,
                          t=c.get("source", t0 + 5.8), enter=Enter(dy=10, dur=0.6)))
    els = _flow(st, parts, bk.OPTICAL_Y, t1)
    if hero_ink is not None:
        hero_el = [e for e in els if e.img is hero_ink.img][0]
        y = hero_el.cy + hero_el.img.height / 2 - 8
        _rule_el(st, tk, int(min(bk.COL_W * 0.9, hero_el.img.width * 0.8)), y,
                 c.get("hero", t0 + 3.0) + 0.95, t1)
        glow = rule(int(min(bk.COL_W, hero_el.img.width)), 26, rgb(tk["gold2"]), 26)
        _fade(st, glow, CX, hero_el.cy, c.get("hero", t0 + 3.0) + 0.6,
              c.get("hero", t0 + 3.0) + 2.6, 1.0, z=8)
    return cues


def build_proof(st, sc, tk, c, t0, t1) -> list:
    """Authority on one card: book, volume/page, grade — then the two closing lines.

    Everything is packed from a computed top so the last line can never run under the
    watermark: a proof block that collides with the page furniture is worse than no proof.
    """
    cues = []
    cards = sc.get("cards") or []
    BOTTOM = 1322.0
    card_w, card_h, gap = 720, 104, 20
    line1_px = typo.fit(sc["line1"], "amiri_b", int(bk.COL_W * 0.94), 58, 32) if sc.get("line1") else 0
    line2_px = typo.fit(typo._EM.sub(r"\1", sc.get("line2", "")), "amiri_b",
                        int(bk.COL_W * 0.94), 58, 32) if sc.get("line2") else 0
    l1 = typo.layout(sc["line1"], "amiri_b", line1_px, rgb(tk["ink"])) if sc.get("line1") else None
    l2 = typo.layout(sc["line2"], "amiri_b", line2_px, rgb(tk["gold"])) if sc.get("line2") else None
    attr = _body(sc["attribution"], tk, 28, "ink2") if sc.get("attribution") else None
    seal_size = 196 if sc.get("seal") else 0
    total = (seal_size + 40 if seal_size else 0) + len(cards) * (card_h + gap) + 22
    total += ((l1.img.height + 10) if l1 else 0) + ((l2.img.height + 8) if l2 else 0)
    total += ((attr.img.height + 16) if attr else 0)
    top = max(496.0, BOTTOM - total)

    y = top
    if seal_size:
        lines = sc["seal"]
        img = seal(tk, lines[0], lines[1] if len(lines) > 1 else "", seal_size)
        st.add(El(img, CX, y + seal_size / 2, c.get("seal", t0 + 0.8), t1,
                  Enter(dy=0, dur=0.42, scale=1.5, blur=8), Exit()))
        flash = img.filter(ImageFilter.GaussianBlur(18))
        _fade(st, flash, CX, y + seal_size / 2, c.get("seal", t0 + 0.8),
              c.get("seal", t0 + 0.8) + 0.9, 0.5, z=8)
        cues.append((c.get("seal", t0 + 0.8), SFX_CHIME, -14))
        y += seal_size + 40

    for i, card in enumerate(cards):
        img = panel(card_w, card_h, tk, 20).copy()
        book = typo.layout(card.get("book", ""), "naskh_b", 38, rgb(tk["ink"]))
        loc = typo.layout(card.get("loc", ""), "naskh", 26, rgb(tk["ink2"]))
        grade = typo.layout(card.get("grade", ""), "kufi_r", 24, rgb(tk["gold"]))
        right = card_w - 28
        img.alpha_composite(book.img, (right - book.img.width, 20))
        img.alpha_composite(loc.img, (right - loc.img.width, 62))
        img.alpha_composite(grade.img, (28, (card_h - grade.img.height) // 2))
        divider_x = 28 + max(grade.img.width + 26, 150)
        if divider_x < right - max(book.img.width, loc.img.width) - 20:
            img.alpha_composite(rule(1, card_h - 44, rgb(tk["line"]), 120), (divider_x, 22))
        t = (c.get("cards") or [t0 + 2.0])[i] if i < len(c.get("cards") or []) else t0 + 2 + i
        st.add(El(img, CX, y + card_h / 2, t, t1, Enter(dy=18, dur=0.6), Exit()))
        cues.append((t, SFX_CLICK, -24))
        y += card_h + gap
    y += 22

    if l1 is not None:
        st.text(l1, CX, y + l1.img.height / 2, c.get("line1", t0 + 4.0), t1,
                Enter(dy=18, dur=0.65), Exit())
        y += l1.img.height + 10
    if l2 is not None:
        st.text(l2, CX, y + l2.img.height / 2, c.get("line2", t0 + 5.0), t1,
                Enter(dy=18, dur=0.65), Exit())
        y += l2.img.height + 8
    if attr is not None:
        st.text(attr, CX, y + attr.img.height / 2, c.get("attribution", t1 - 1.2), t1,
                Enter(dy=10, dur=0.6), Exit())
    return cues


def build_cta(st, sc, tk, c, t0, t1) -> list:
    """Take-away, at most one invitation, then the card. The card closes the reel in silence."""
    cues = [(c.get("final", t0 + 3.6), SFX_IMPACT, -17)]
    y = 700.0
    if sc.get("line1"):
        px = typo.fit(sc["line1"], "kufi", int(bk.COL_W * 0.9), 72, 34)
        ink = _body(sc["line1"], tk, px, "ink", "kufi")
        st.text(ink, CX, y, c.get("line1", t0 + 0.3), t1, Enter(dy=20, dur=0.7), Exit())
        y += ink.img.height + 30
    if sc.get("line2"):
        px = typo.fit(typo._EM.sub(r"\1", sc["line2"]), "amiri", int(bk.COL_W * 0.94), 66, 32)
        ink = typo.layout(sc["line2"], "amiri", px, rgb(tk["ink"]), rgb(tk["gold"]))
        st.text(ink, CX, y, c.get("line2", t0 + 1.4), t1, Enter(dy=20, dur=0.7), Exit())
        y += ink.img.height + 44
    if sc.get("share"):
        px = typo.fit(sc["share"], "kufi_r", int(bk.COL_W * 0.7), 36, 24)
        share = typo.layout(sc["share"], "kufi_r", px, rgb(tk["gold"]))
        icon = sc.get("icon", "none")
        off = 0 if icon == "none" else 26
        st.text(share, CX + off / 2, y, c.get("share", t0 + 2.7), t1, Enter(dy=12, dur=0.6))
        if icon != "none":
            iw = _icon(icon, tk)
            if iw:
                st.add(El(iw, CX - share.img.width / 2 - 26, y, c.get("share", t0 + 2.7), t1,
                          Enter(dy=0, dur=0.5, blur=4), Exit()))
        y += share.img.height + 40
    if sc.get("final"):
        key = sc.get("final_font", "kufi")
        px = typo.fit(sc["final"], key, int(bk.COL_W * 0.98), 118, 40)
        fin = _body(sc["final"], tk, px, "ink", key)
        fy = max(y + fin.img.height / 2, 1060)
        st.text(fin, CX, fy, c.get("final", t0 + 3.6), t1, Enter(dy=24, dur=0.85, blur=10), Exit())
        _rule_el(st, tk, 280, fy + fin.img.height / 2 + 34, c.get("final", t0 + 3.6) + 1.0, t1)

    # the card: tree, name, handle — nothing else, and nothing moving
    bt = c.get("brand", t1 - 1.55)
    brand_ar = typo.layout(bk.brand_config().get("brand_name_ar", "مع الصادقين"), "kufi", 46,
                           rgb(tk["ink"]))
    handle = (sc.get("brand") or {}).get("handle") or \
        bk.brand_config().get("handle_display", "@maalsadiqeen")
    handle_ink = typo.layout(handle, "kufi_r", 28, rgb(tk["gold"]))
    card_y = 1520.0
    mark = stage_mark(tk)
    if mark is not None:
        st.add(El(mark, CX, card_y - 120, bt, t1, Enter(dy=0, dur=0.8, scale=1.0, blur=6),
                  Exit(), None, 1.0, 9))
    st.text(brand_ar, CX, card_y, bt + 0.1, t1, Enter(dy=12, dur=0.7), Exit())
    st.text(handle_ink, CX, card_y + 46, bt + 0.26, t1, Enter(dy=10, dur=0.7), Exit())
    return cues


def stage_mark(tk: dict):
    """The tree, at card size, in the palette's ink — not the faint watermark."""
    import stage
    return stage.logo_mark(tk, 96, 0.85)


def build_quote_list(st, sc, tk, c, t0, t1) -> list:
    """list — up to four short items, numbered with Arabic-Indic digits."""
    parts = []
    if sc.get("title"):
        px = typo.fit(sc["title"], "kufi", int(bk.COL_W * 0.9), 58, 32)
        parts.append(Part(_body(sc["title"], tk, px, "ink", "kufi"), gap=40,
                          t=c.get("title", t0 + 0.2), enter=Enter(dy=18, dur=0.65)))
    y = bk.OPTICAL_Y - 120
    items = sc.get("items") or []
    px = min(typo.fit(i, "naskh", int(bk.COL_W * 0.88), 46, 28) for i in items) if items else 40
    cues = []
    for i, it in enumerate(items):
        num = typo.layout(typo.to_arabic_digits(str(i + 1)) + ".", "kufi_r", px - 6,
                          rgb(tk["gold"]))
        body = typo.layout(it, "naskh", px, rgb(tk["ink"]))
        t = (c.get("items") or [t0 + 0.9 + i * 0.95])[i] if i < len(c.get("items") or []) \
            else t0 + 0.9 + i * 0.95
        yy = y + i * (body.img.height + 26)
        st.text(num, CX + bk.COL_W / 2 - num.img.width / 2, yy + body.img.height / 2, t, t1,
                Enter(dy=12, dur=0.55))
        st.text(body, CX - 34, yy + body.img.height / 2, t + 0.06, t1, Enter(dy=14, dur=0.6))
        cues.append((t, SFX_CLICK, -26))
    if sc.get("attribution"):
        st.text(_body(sc["attribution"], tk, 28, "ink2"), CX,
                y + len(items) * 90 + 40, c.get("attribution", t1 - 1.1), t1,
                Enter(dy=10, dur=0.6))
    return cues


def _prose(st, sc, tk, c, t0, t1, text_key="text", kicker=None, right=True) -> list:
    """A passage, one sentence at a time, right-aligned Naskh with a gold margin rule."""
    text = sc.get(text_key, "")
    sents = _sentences(text)
    px, _ = typo.fit_wrapped(" ".join(sents), "naskh", int(bk.COL_W * 0.94), 860, 54, 30)
    inks = [typo.paragraph(s, "naskh", px, int(bk.COL_W * 0.94), 1.72,
                           "right" if right else "center", rgb(tk["ink"]), rgb(tk["gold"]))
            for s in sents]
    total = sum(i.img.height for i in inks) + 22 * (len(inks) - 1) + (56 if kicker else 0)
    top = bk.OPTICAL_Y - total / 2
    cues = []
    timings = c.get("text") or [t0 + 0.4]
    if kicker:
        _fade(st, _label(kicker, tk, 28).img, CX + 120, top + 14, c.get("kicker", t0 + 0.2),
              t1, 0.95)
        top += 56
    body_top = top
    for i, ink in enumerate(inks):
        t = timings[i] if i < len(timings) else t0 + 0.5 + i * 2
        st.add(El(ink.img, CX - 12, top + ink.img.height / 2, t, t1,
                  Enter(dy=20, dur=0.7, blur=8), Exit(), None, 1.0, 10))
        cues.append((t, SFX_CLICK, -30))
        top += ink.img.height + 22
    rule_h = int(top - body_top - 22)
    if rule_h > 40:
        bar = rule(3, rule_h, rgb(tk["gold"]), 170)
        st.add(El(bar, CX + bk.COL_W / 2 - 24, body_top + rule_h / 2,
                  timings[0], t1, None, Exit(), (timings[0], 0.8), 0.9, 8))
    return cues


def build_paragraph(st, sc, tk, c, t0, t1) -> list:
    return _prose(st, sc, tk, c, t0, t1, "text", sc.get("kicker"))


def build_definition(st, sc, tk, c, t0, t1) -> list:
    cues = [(c.get("term", t0 + 0.25), SFX_CLICK, -22)]
    term = sc.get("term", "")
    px = typo.fit(term, "amiri_b", int(bk.COL_W * 0.9), 84, 40)
    t_ink = typo.layout(term, "amiri_b", px, rgb(tk["ink"]), rgb(tk["gold"]))
    top = bk.OPTICAL_Y - 300
    st.text(t_ink, CX, top + t_ink.img.height / 2, c.get("term", t0 + 0.25), t1,
            Enter(dy=20, dur=0.7), Exit(), wipe=(c.get("term", t0 + 0.25), 0.8))
    _rule_el(st, tk, 240, top + t_ink.img.height + 16, c.get("term", t0 + 0.25) + 0.7, t1)
    sents = _sentences(sc.get("text", ""))
    px2, _ = typo.fit_wrapped(" ".join(sents), "naskh", int(bk.COL_W * 0.94), 700, 46, 28)
    y = top + t_ink.img.height + 60
    timings = c.get("text") or []
    for i, s in enumerate(sents):
        ink = typo.paragraph(s, "naskh", px2, int(bk.COL_W * 0.94), 1.72, "right",
                             rgb(tk["ink"]), rgb(tk["gold"]))
        t = timings[i] if i < len(timings) else t0 + 1.2 + i * 2.0
        st.add(El(ink.img, CX + 10, y + ink.img.height / 2, t, t1, Enter(dy=18, dur=0.65), Exit()))
        y += ink.img.height + 16
        cues.append((t, SFX_CLICK, -30))
    if sc.get("note"):
        note = typo.layout(sc["note"], "naskh", 28, rgb(tk["gold"]))
        st.text(note, CX, y + 30, c.get("note", t1 - 1.5), t1, Enter(dy=10, dur=0.6))
    return cues


def build_steps(st, sc, tk, c, t0, t1) -> list:
    parts = []
    if sc.get("title"):
        px = typo.fit(sc["title"], "kufi", int(bk.COL_W * 0.9), 54, 30)
        parts.append((_body(sc["title"], tk, px, "ink", "kufi"), c.get("title", t0 + 0.2)))
    steps = sc.get("steps") or []
    px = min(typo.fit(s, "naskh", int(bk.COL_W * 0.78), 44, 26) for s in steps) if steps else 36
    inks = [typo.layout(s, "naskh", px, rgb(tk["ink"])) for s in steps]
    head = parts[0][0].img.height + 54 if parts else 0
    total = head + sum(i.img.height for i in inks) + 34 * max(0, len(inks) - 1)
    top = bk.OPTICAL_Y - total / 2
    cues = []
    if parts:
        st.text(parts[0][0], CX, top + parts[0][0].img.height / 2, parts[0][1], t1,
                Enter(dy=18, dur=0.65))
        top += head
    for i, ink in enumerate(inks):
        t = (c.get("steps") or [t0 + 0.9 + i * 1.5])[i] if i < len(c.get("steps") or []) \
            else t0 + 0.9 + i * 1.5
        num = typo.layout(typo.to_arabic_digits(str(i + 1)), "kufi", 30, rgb(tk["gold"]))
        st.text(num, CX + bk.COL_W / 2 - 10, top + ink.img.height / 2, t, t1,
                Enter(dy=12, dur=0.5))
        st.text(ink, CX - 26, top + ink.img.height / 2, t + 0.05, t1, Enter(dy=14, dur=0.6))
        cues.append((t, SFX_CLICK, -26))
        top += ink.img.height + 34
    return cues


def build_timeline(st, sc, tk, c, t0, t1) -> list:
    events = sc.get("events") or []
    top = bk.OPTICAL_Y - (len(events) * 120 + 80) / 2
    cues = []
    if sc.get("title"):
        px = typo.fit(sc["title"], "kufi", int(bk.COL_W * 0.9), 50, 30)
        head = _body(sc["title"], tk, px, "ink", "kufi")
        st.text(head, CX, top + head.img.height / 2, c.get("title", t0 + 0.2), t1,
                Enter(dy=16, dur=0.6))
        top += head.img.height + 50
    if events:
        spine = rule(2, int(len(events) * 120), rgb(tk["line"]), 170)
        st.add(El(spine, CX + 250, top + len(events) * 60 - 30, c.get("title", t0 + 0.4), t1,
                  None, Exit(), (c.get("title", t0 + 0.4), 0.9), 0.8, 7))
    for i, ev in enumerate(events):
        when = ev.get("when", "")
        what = ev.get("what", "")
        t = (c.get("events") or [t0 + 0.9 + i * 1.6])[i] if i < len(c.get("events") or []) \
            else t0 + 0.9 + i * 1.6
        w_ink = typo.layout(when, "kufi_r", 26, rgb(tk["gold"]))
        b_ink = typo.layout(what, "naskh", 40, rgb(tk["ink"]))
        y = top + i * 120
        st.add(El(diamond(14, rgb(tk["gold"])), CX + 250, y + 30, t, t1,
                  Enter(dy=0, dur=0.4, scale=0.4, blur=0), Exit()))
        st.text(w_ink, CX + 210, y + 16, t + 0.05, t1, Enter(dy=8, dur=0.5))
        st.text(b_ink, CX - 40, y + 46, t + 0.1, t1, Enter(dy=12, dur=0.6))
        cues.append((t, SFX_CLICK, -26))
    return cues


def build_compare(st, sc, tk, c, t0, t1) -> list:
    left, right = sc.get("left") or {}, sc.get("right") or {}
    w, h = 380, 420
    cues = []
    for side, data, t in (("l", left, c.get("left", t0 + 0.3)), ("r", right, c.get("right", t0 + 1.4))):
        x = CX + (w / 2 + 12) if side == "l" else CX - (w / 2 + 12)
        img = panel(w, h, tk, 24).copy()
        title = typo.layout(data.get("title", ""), "kufi", 30, rgb(tk["gold"]))
        img.alpha_composite(title.img, ((w - title.img.width) // 2, 26))
        y = 84
        for pt in data.get("points", [])[:3]:
            ink = typo.layout(pt, "naskh", 30, rgb(tk["ink"]))
            img.alpha_composite(ink.img, (max(16, w - 20 - ink.img.width), y))
            y += ink.img.height + 14
        st.add(El(img, x, bk.OPTICAL_Y - 60, t, t1, Enter(dy=20, dur=0.65), Exit()))
        cues.append((t, SFX_CLICK, -26))
    if sc.get("verdict"):
        px = typo.fit(sc["verdict"], "kufi", int(bk.COL_W * 0.94), 52, 28)
        ink = _body(sc["verdict"], tk, px, "ink", "kufi")
        st.text(ink, CX, bk.OPTICAL_Y + 260, c.get("verdict", t1 - 2.3), t1,
                Enter(dy=18, dur=0.7), Exit())
        cues.append((c.get("verdict", t1 - 2.3), SFX_IMPACT, -20))
    return cues


def build_qa(st, sc, tk, c, t0, t1) -> list:
    q = sc.get("question", "")
    px = typo.fit(q, "kufi", int(bk.COL_W * 0.94), 62, 32)
    q_ink = _body(q, tk, px, "gold", "kufi")
    top = 620.0
    st.text(q_ink, CX, top + q_ink.img.height / 2, c.get("question", t0 + 0.3), t1,
            Enter(dy=18, dur=0.65))
    _rule_el(st, tk, 200, top + q_ink.img.height + 44, c.get("question", t0 + 0.3) + 0.6, t1)
    sents = _sentences(sc.get("answer", ""))
    px2, _ = typo.fit_wrapped(" ".join(sents), "naskh", int(bk.COL_W * 0.94), 760, 48, 28)
    y = top + q_ink.img.height + 70
    cues = [(c.get("question", t0 + 0.3), SFX_CLICK, -22)]
    timings = c.get("answer") or []
    for i, s in enumerate(sents):
        ink = typo.paragraph(s, "naskh", px2, int(bk.COL_W * 0.94), 1.72, "right",
                             rgb(tk["ink"]), rgb(tk["gold"]))
        t = timings[i] if i < len(timings) else t0 + 1.9 + i * 2.2
        st.add(El(ink.img, CX - 12, y + ink.img.height / 2, t, t1, Enter(dy=18, dur=0.65), Exit()))
        y += ink.img.height + 20
        cues.append((t, SFX_CLICK, -30))
    return cues


def _icon(kind: str, tk: dict):
    """A 26 px brand icon: a paper plane for «أرسل», a bookmark for «احفظ»."""
    s = 3
    gold = rgb(tk["gold"]) + (240,)
    if kind == "send":
        img = Image.new("RGBA", (26 * s, 26 * s), (0, 0, 0, 0))
        ImageDraw.Draw(img).polygon(
            [(1 * s, 13 * s), (25 * s, 3 * s), (15 * s, 23 * s), (12 * s, 15 * s)], fill=gold)
    elif kind == "save":
        img = Image.new("RGBA", (26 * s, 26 * s), (0, 0, 0, 0))
        ImageDraw.Draw(img).polygon(
            [(6 * s, 2 * s), (20 * s, 2 * s), (20 * s, 24 * s), (13 * s, 18 * s),
             (6 * s, 24 * s)], fill=gold)
    else:
        return None
    return img.resize((26, 26), Image.LANCZOS)


BUILDERS = {
    "hook": build_hook,
    "title": build_title,
    "verse": build_verse,
    "contrast": build_contrast,
    "answer": build_answer,
    "proof": build_proof,
    "cta": build_cta,
    "quote": build_quote,
    "list": build_quote_list,
    "paragraph": build_paragraph,
    "definition": build_definition,
    "steps": build_steps,
    "timeline": build_timeline,
    "compare": build_compare,
    "qa": build_qa,
}


def build_all(st, res: dict) -> list:
    tk = st.tk
    cues: list = []
    for sc in res["scenes"]:
        t0, t1 = float(sc["start"]), float(sc["end"])
        fn = BUILDERS.get(sc["type"])
        if not fn:
            continue
        got = fn(st, sc, tk, sc["cues"], t0, t1) or []
        cues.extend(got)
    # one whoosh on every cut, at a lower level than the content
    for sc in res["scenes"][1:]:
        cues.append((float(sc["start"]), SFX_WHOOSH, -26))
    return cues
