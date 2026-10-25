#!/usr/bin/env python3
"""Arabic/Persian typesetting: real shaping, real metrics, real fitting.

Why not `PIL.ImageDraw.text`? Because Pillow in this environment has no libraqm, so it
draws unjoined, left-to-right letters. This module shapes with HarfBuzz (the same engine
libass and Chrome use) and rasterises the resulting glyph ids with FreeType, so the output
is the text the font designer drew — ligatures, mark positioning and all.

Positions are accumulated in **supersampled** space and rounded once per glyph, not per
advance: rounding the advance instead would open a one-pixel gap at every letter join and
break the cursive line.

    layout(text, font, px, color, em_color=…) -> Ink      # one line, <em> = accent
    measure(text, font, px) -> int
    wrap(text, font, px, max_w) -> list[str]
    fit(text, font, max_w, hi, lo) -> int                 # largest px that fits
    stack(lines, …) -> Ink                                # several lines, RTL rhythm
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache

import freetype
import uharfbuzz as hb
from PIL import Image

from brandkit import font_path, rgb

SS = 2  # supersampling factor for text rasterisation

_AR = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")
_EM = re.compile(r"<em>(.*?)</em>", re.S)


# ------------------------------------------------------------------------ shaping core
@dataclass
class Glyph:
    gid: int
    xadv: float        # advance, supersampled px
    xoff: float        # offset, supersampled px
    yoff: float
    key: str = ""      # which face drew it (punctuation falls back to Amiri)


@dataclass
class Run:
    direction: str
    glyphs: list[Glyph] = field(default_factory=list)
    width: int = 0     # supersampled px


@dataclass
class Ink:
    """A rendered text block: RGBA image plus the metrics needed to place it."""
    img: Image.Image
    width: int
    height: int
    baseline: int
    px: int

    def tinted(self, color: tuple[int, int, int]) -> "Ink":
        return Ink(_tint(self.img, color), self.width, self.height, self.baseline, self.px)


def _tint(img: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    """Recolour an alpha mask to `color`, keeping its coverage in the alpha channel."""
    r, g, b = color
    alpha = img if img.mode == "L" else img.getchannel("A")
    solid = Image.new("RGBA", img.size, (r, g, b, 255))
    solid.putalpha(alpha)
    return solid


@lru_cache(maxsize=256)
def _hb_font(key: str, px: int):
    data = open(font_path(key), "rb").read()
    face = hb.Face(data)
    font = hb.Font(face)
    font.scale = (int(px * SS) * 64, int(px * SS) * 64)
    return face, font


@lru_cache(maxsize=256)
def _ft_face(key: str, px: int):
    face = freetype.Face(font_path(key))
    # set_pixel_sizes, not set_char_size: FreeType must render *pixels* so its bitmap and
    # HarfBuzz's advances share a unit (set_char_size assumes 64 dpi and shrinks by 72/64).
    face.set_pixel_sizes(0, int(px * SS))
    return face


def _class(ch: str) -> str:
    if _AR.match(ch):
        return "rtl"
    if "\u06F0" <= ch <= "\u06F9" or "\u0660" <= ch <= "\u0669":
        return "rtl"
    if unicodedata.category(ch).startswith("L"):
        return "ltr"
    return "neutral"


def split_runs(text: str) -> list[tuple[str, str]]:
    """Logical-order script runs. Neutral characters join the run they follow."""
    runs: list[list[str]] = []
    for ch in text:
        cls = _class(ch)
        if not runs:
            runs.append([cls, ch])
        elif cls == "neutral" or cls == runs[-1][0]:
            runs[-1][1] += ch
        else:
            runs.append([cls, ch])
    return [("rtl" if cls == "rtl" else "ltr", s) for cls, s in runs]


@lru_cache(maxsize=8192)
def _shape_run(text: str, key: str, px: int, direction: str) -> tuple[tuple[int, ...], ...]:
    _, font = _hb_font(key, px)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.direction = direction
    buf.script = "Arab" if direction == "rtl" else "Latn"
    buf.language = "ar" if direction == "rtl" else "en"
    hb.shape(font, buf, {"kern": True, "liga": True, "clig": True, "calt": True,
                         "mark": True, "mkmk": True, "ccmp": True})
    return tuple((i.codepoint, p.x_advance, p.x_offset, p.y_offset)
                 for i, p in zip(buf.glyph_infos, buf.glyph_positions))


@lru_cache(maxsize=64)
def _coverage(key: str) -> frozenset[int]:
    _, font = _hb_font(key, 24)
    return frozenset(c for c in range(0x20, 0x2100) if font.get_nominal_glyph(c) is not None)


def _fallback_key(key: str) -> str:
    return "amiri_b" if key in ("kufi", "naskh_b", "amiri_b") else "amiri"


def _pieces(chunk: str, key: str) -> list[tuple[str, str]]:
    """Split a run into (text, font) pieces: the Noto Arabic builds carry no Latin
    punctuation (/ · « » :), and a missing glyph draws as an empty box, so those
    characters fall back to Amiri instead of breaking the line."""
    cov = _coverage(key)
    fb = _fallback_key(key)
    if fb == key:
        return [(chunk, key)]
    fb_cov = _coverage(fb)
    out: list[list[str]] = []
    for ch in chunk:
        use = key if ord(ch) in cov else (fb if ord(ch) in fb_cov else key)
        if out and out[-1][1] == use:
            out[-1][0] += ch
        else:
            out.append([ch, use])
    return [(t, k) for t, k in out]


def shape(text: str, key: str, px: int) -> list[Run]:
    """Shape one logical string into visual-order runs (RTL base direction)."""
    runs = []
    for direction, chunk in split_runs(text):
        for piece, pk in _pieces(chunk, key):
            if not piece:
                continue
            # 26.6 fixed point at the supersampled size → supersampled px (keep the fraction)
            gl = [Glyph(gid, xa / 64, xo / 64, yo / 64, pk)
                  for gid, xa, xo, yo in _shape_run(piece, pk, px, direction)]
            runs.append(Run(direction, gl, sum(g.xadv for g in gl)))
    # NOTE: run order stays logical. `layout()` paints the first run at the *right* edge,
    # which is what an RTL base direction wants, so a leading «—» correctly sits rightmost.
    return runs


def measure_runs(runs: list[Run]) -> int:
    return int(round(sum(r.width for r in runs) / SS))


@lru_cache(maxsize=2048)
def measure(text: str, key: str, px: int) -> int:
    return measure_runs(shape(text, _safe_key(text, key), px))


def _metrics(key: str, px: int) -> tuple[float, float]:
    """Ascender / descender in *device* pixels (the face is set at px·SS)."""
    face = _ft_face(key, px)
    return face.size.ascender / 64 / SS, -face.size.descender / 64 / SS


def _rasterise(runs: list[Run], key: str, px: int, color: tuple[int, int, int],
               padx_ss: int) -> Ink:
    """Rasterise shaped runs. Horizontal padding is *small and fixed* so that a word's
    width is its ink width: word spacing in a verse is a design decision, not a side effect
    of the rasteriser's margins. Vertical padding stays generous — the harakat need it."""
    face = _ft_face(key, px)
    asc, desc = (v * SS for v in _metrics(key, px))
    pady = int(px * SS * 0.42) + 8
    width_ss = int(round(sum(r.width for r in runs))) + 2 * padx_ss
    height_ss = int(asc + desc) + 2 * pady + int(px * SS * 0.18)
    baseline_ss = pady + int(asc)
    canvas = Image.new("L", (max(1, width_ss), max(1, height_ss)), 0)

    # an RTL base line is laid out right-to-left, so the logical run sequence is mirrored
    # before it is painted left-to-right (a trailing «—» must not appear above the first word)
    runs = list(reversed(runs))
    cursor = float(padx_ss)
    for run in runs:
        for g in run.glyphs:
            gf = _ft_face(g.key or key, px)
            gf.load_glyph(g.gid, freetype.FT_LOAD_RENDER)
            bm = gf.glyph.bitmap
            if bm.width and bm.rows:
                glyph_img = Image.frombytes("L", (bm.width, bm.rows), bytes(bm.buffer))
                canvas.paste(glyph_img,
                             (int(round(cursor + g.xoff)) + gf.glyph.bitmap_left,
                              baseline_ss - gf.glyph.bitmap_top - int(round(g.yoff))))
            cursor += g.xadv
    canvas = canvas.resize((max(1, width_ss // SS), max(1, height_ss // SS)), Image.LANCZOS)
    edge = padx_ss // SS
    return Ink(_tint(canvas, color), max(1, width_ss // SS - 2 * edge),
               max(1, height_ss // SS), baseline_ss // SS, px)


# ------------------------------------------------------------------------- rich lines
def _segments(text: str) -> list[tuple[str, bool]]:
    """Split on <em>…</em> into (chunk, is_emphasis) in logical order."""
    segs, pos = [], 0
    for m in _EM.finditer(text):
        if m.start() > pos:
            segs.append((text[pos:m.start()], False))
        segs.append((m.group(1), True))
        pos = m.end()
    if pos < len(text):
        segs.append((text[pos:], False))
    return segs or [(text, False)]


_LATIN = re.compile(r"[A-Za-z@#_]")


def _safe_key(text: str, key: str) -> str:
    """Noto Kufi/Naskh ship no Latin glyphs: a handle like @maalsadiqeen would be boxes."""
    if _LATIN.search(text or "") and key in ("kufi", "kufi_r", "naskh", "naskh_b", "quran"):
        return "amiri_b" if key in ("kufi", "naskh_b") else "amiri"
    return key


def layout(text: str, key: str = "naskh", px: int = 44,
           color: tuple[int, int, int] | None = None,
           em_color: tuple[int, int, int] | None = None,
           em_scale: float = 1.18) -> Ink:
    """One line, `<em>` in the accent colour at `em_scale`. Reading order right-to-left.

    The returned image is cropped to its ink, so `img.height` is what the eye sees and
    `baseline` is measured from the top of the crop: that is what lets a block be centred
    on its ink instead of on the font's (very generous) ascender box.
    """
    color = color or rgb("#efe8d8")
    em_color = em_color or color
    key = _safe_key(text, key)
    padx_ss = int(px * SS * 0.035) + 2
    pieces: list[tuple[Ink, int]] = []
    for chunk, is_em in _segments(text):
        if not chunk:
            continue
        size = int(round(px * em_scale)) if is_em else px
        runs = shape(chunk, key, size)
        w = int(round(sum(r.width for r in runs) / SS))
        pieces.append((_rasterise(runs, key, size, em_color if is_em else color, padx_ss), w))
    total = sum(w for _, w in pieces)

    asc, desc = _metrics(key, px)
    padx = padx_ss // SS
    pady = int(px * 0.42) + 6
    height = int(asc + desc) + 2 * pady + int(px * 0.22)
    baseline = pady + int(asc)
    canvas = Image.new("RGBA", (max(1, total + 2 * padx), height), (0, 0, 0, 0))
    x = padx + total  # RTL: fill from the right edge leftwards
    for ink, w in pieces:
        canvas.alpha_composite(ink.img, (max(0, x - w - padx), baseline - ink.baseline))
        x -= w

    box = canvas.getbbox()
    if box:
        m = 2
        y0, y1 = max(0, box[1] - m), min(canvas.height, box[3] + m)
        canvas = canvas.crop((0, y0, canvas.width, y1))
        baseline -= y0
    return Ink(canvas, total, canvas.height, baseline, px)


def stack(lines: list[str], key: str = "naskh", px: int = 44, leading: float = 1.62,
          align: str = "center", color: tuple[int, int, int] | None = None,
          em_color: tuple[int, int, int] | None = None, em_scale: float = 1.18,
          col_w: int = 800) -> Ink:
    """Several lines on one baseline grid, aligned inside `col_w`."""
    inks = [layout(t, key, px, color, em_color, em_scale) for t in lines]
    lh = int(px * leading)
    height = lh * len(inks)
    canvas = Image.new("RGBA", (col_w, max(1, height)), (0, 0, 0, 0))
    for i, ink in enumerate(inks):
        x = {"center": (col_w - ink.img.width) // 2,
             "right": col_w - ink.img.width, "left": 0}[align]
        y = i * lh + (lh - ink.img.height) // 2
        canvas.alpha_composite(ink.img, (max(0, x), max(0, y)))
    return Ink(canvas, col_w, max(1, height), int(inks[0].baseline) if inks else 0, px)


def paragraph(text: str, key: str = "naskh", px: int = 44, max_w: int = 800,
              leading: float = 1.72, align: str = "right",
              color: tuple[int, int, int] | None = None,
              em_color: tuple[int, int, int] | None = None, em_scale: float = 1.14,
              max_lines: int = 8) -> Ink:
    """A wrapped block of prose. RTL paragraphs are right-aligned, not centred.

    Centring every line of a paragraph is the commonest tell of an amateur reel: the right
    edge — where an Arabic eye enters the line — drifts with the word count.
    """
    lines = wrap(text, key, px, max_w, max_lines, strip_em=False)
    inks = [layout(ln, key, px, color, em_color, em_scale) for ln in lines]
    lh = int(px * leading)
    canvas = Image.new("RGBA", (max_w, max(1, lh * len(inks))), (0, 0, 0, 0))
    for i, ink in enumerate(inks):
        x = {"right": max_w - ink.img.width, "center": (max_w - ink.img.width) // 2,
             "left": 0}[align]
        y = i * lh + (lh - ink.img.height) // 2
        canvas.alpha_composite(ink.img, (max(0, x), max(0, y)))
    return Ink(canvas, max_w, max(1, lh * len(inks)), int(inks[0].baseline) if inks else 0, px)


# ------------------------------------------------------------------------ fitting/wrap
def wrap(text: str, key: str = "naskh", px: int = 44, max_w: int = 800,
         max_lines: int = 6, strip_em: bool = False) -> list[str]:
    """Greedy word wrap with real shaped widths."""
    plain = _EM.sub(r"\1", text) if strip_em else text
    key = _safe_key(plain, key)
    words = plain.split()
    lines, cur = [], []
    for w in words:
        trial = " ".join(cur + [w])
        if cur and measure(trial, key, px) > max_w:
            lines.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(" ".join(cur))
    while len(lines) > max_lines:
        i = max(range(len(lines)), key=lambda k: len(lines[k]))
        ws = lines.pop(i).split()
        mid = max(1, len(ws) // 2)
        lines[i:i] = [" ".join(ws[:mid]), " ".join(ws[mid:])]
    return lines


def fit(text: str, key: str = "kufi", max_w: int = 800, hi: int = 110, lo: int = 36,
        step: int = 2) -> int:
    """Largest size ≤ hi that keeps the line on one row inside max_w (never below lo)."""
    px = hi
    while px > lo:
        if measure(text, key, px) <= max_w:
            return px
        px -= step
    return lo


def fit_wrapped(text: str, key: str = "naskh", max_w: int = 800, max_h: int = 980,
                hi: int = 72, lo: int = 30, max_lines: int = 6) -> tuple[int, list[str]]:
    """Largest size whose wrap fits both the column and the height budget."""
    px = hi
    while px > lo:
        lines = wrap(text, key, px, max_w, max_lines, strip_em=True)
        if len(lines) * int(px * 1.62) <= max_h and \
                all(measure(l, key, px) <= max_w for l in lines):
            return px, lines
        px -= 2
    return lo, wrap(text, key, lo, max_w, max_lines, strip_em=True)


# ---------------------------------------------------------------------------- utilities
def to_arabic_digits(s: str) -> str:
    """0-9 → ٠-٩ (Arabic-Indic, what the brand prints)."""
    return s.translate({ord(c): ord(c) + 0x630 for c in "0123456789"})


def words(s: str) -> int:
    return len(_EM.sub(r"\1", s).split())
