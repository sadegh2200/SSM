#!/usr/bin/env python3
"""
build_reel.py — compile a reel spec (JSON) into a HyperFrames project.

    python3 build_reel.py spec.json --out /path/to/project [--skill-root <dir>]

Writes:  <out>/index.html, <out>/hyperframes.json, <out>/assets/{gsap.min.js,fonts,img}
         <out>/spec.resolved.json  (all cues resolved to absolute seconds — used by mix.py)

The spec is a list of SCENES built from a small library of proven BLOCKS. Two
families: the v2 short-form blocks (hook, verse, contrast, answer, proof, cta,
quote, list, title) for one-line-per-scene reels, and the v3 long-text blocks
(paragraph, definition, steps, timeline, compare, qa) that carry a passage of
prose on screen without turning into a wall of text. Every cue that is not given
explicitly is derived from reading-speed rules, so a "silent" (narration-free)
reel needs almost no manual timing. For narrated reels, pass the cues measured
with cues.py.

Spec reference: ../references/blocks.md
"""
import argparse, json, os, re, shutil, sys, unicodedata, html

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)

# ----------------------------------------------------------------------------- text metrics
_COMBINING = re.compile(r"[\u064B-\u065F\u0670\u06D6-\u06ED\u0640]")  # tashkeel + tatweel
# fallback: average advance per base character (em) when exact shaping is unavailable (p75 of measured samples)
_EM = {"kufi": 0.56, "kufi-r": 0.50, "amiri": 0.40, "amiri-b": 0.40, "quran": 0.40, "naskh": 0.41}
_FONT_FILES = {"quran": "AmiriQuran.ttf", "amiri": "Amiri-Regular.ttf", "amiri-b": "Amiri-Bold.ttf",
               "kufi": "NotoKufiArabic-Bold.ttf", "kufi-r": "NotoKufiArabic-Regular.ttf", "naskh": "NotoNaskhArabic-Regular.ttf"}
_font_cache = {}


def _pil_font(font):
    """Exact Arabic shaping via Pillow+libraqm (matches Chrome within ~1%). Returns None if unavailable."""
    if font in _font_cache:
        return _font_cache[font]
    f = None
    if os.environ.get("MSR_NO_RAQM"):          # testing hook: force the estimate fallback
        _font_cache[font] = None
        return None
    try:
        from PIL import ImageFont, features
        if features.check("raqm"):
            f = ImageFont.truetype(os.path.join(SKILL_ROOT, "assets", "fonts", _FONT_FILES[font]), 100)
    except Exception:
        f = None
    _font_cache[font] = f
    return f


def plain(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s or "")
    return html.unescape(s)


def nchars(s: str) -> int:
    return max(1, len(_COMBINING.sub("", plain(s))))


def width_em(text, font):
    """advance width of `text` in em for the given font class (handles <em> at 1.18em)."""
    text = text or ""
    f = _pil_font(font)
    parts = re.split(r"(<em>.*?</em>)", text)
    total = 0.0
    for part in parts:
        if not part:
            continue
        scale = 1.0
        if part.startswith("<em>"):
            scale = 1.18
            part = part[4:-5]
        t = plain(part)
        if f is not None:
            try:
                total += scale * f.getlength(t, direction="rtl", language="ar") / 100.0
                continue
            except Exception:
                pass
        total += scale * len(_COMBINING.sub("", t)) * _EM.get(font, 0.45)
    return total


def fit(text, font, max_px, min_px, width=800):
    """largest font size (px) <= max_px at which `text` fits on one line of `width` px."""
    w = width_em(text, font)
    size = width / w if w > 0 else max_px
    return int(max(min_px, min(max_px, size)))


def fit_wrapped(lines, font, max_px, min_px, width=800, max_lines=4, gap_em=0.32, max_height=980, line_height=1.95):
    """lines = list of word lists (forced breaks between lists). Words flow with gap_em between them.
    Returns (size, n_lines): the largest size with <= max_lines rendered lines and total height <= max_height."""
    ww = [[width_em(w, font) for w in ln] for ln in lines]
    for size in range(int(max_px), int(min_px) - 1, -2):
        n = 0
        for ln in ww:
            cur = 0.0
            n += 1
            for w in ln:
                adv = (w + gap_em) * size
                if cur + adv > width and cur > 0:
                    n += 1
                    cur = 0.0
                cur += adv
        if n <= max_lines and n * size * line_height <= max_height:
            return size, n
    return int(min_px), None


def em(s: str) -> str:
    """author markup: <em>…</em> → gold emphasis span; keep everything else escaped-safe."""
    s = s or ""
    s = s.replace("<em>", "\x00").replace("</em>", "\x01")
    s = html.escape(s, quote=False)
    return s.replace("\x00", '<span class="em">').replace("\x01", "</span>")


def ar_digits(n) -> str:
    return str(n).translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))


# ----------------------------------------------------------------------------- reading-speed defaults
READ_WORD = 0.26   # s per word (educated reader, فصيح with tashkeel)
READ_MIN = 1.15    # minimum dwell per line
GAP = 0.18         # gap between consecutive reveals
READ_PROSE = 0.30  # s per word for running prose (paragraph · qa · definition) — slower than a slogan
PROSE_MIN = 1.80   # minimum dwell per prose sentence


def words(s):
    return [w for w in plain(s).split() if w]


def dwell(s):
    return max(READ_MIN, READ_WORD * len(words(s)) + 0.55)


# ----------------------------------------------------------------------------- theme
BRAND_PATH = os.path.join(SKILL_ROOT, "config", "brand.json")


def load_brand(skill_root: str | None = None) -> dict:
    path = os.path.join(skill_root or SKILL_ROOT, "config", "brand.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return {}


def theme_of(spec: dict, brand: dict, override: str | None = None) -> tuple[str, dict]:
    """(name, tokens). `--theme` beats `spec.theme`, which beats the brand default."""
    themes = brand.get("themes") or {}
    name = override or spec.get("theme") or (brand.get("defaults") or {}).get("theme") or "main"
    if not themes:
        return "main", {}
    if name not in themes:
        raise SystemExit(f"unknown theme «{name}» — available: {', '.join(themes)}")
    return name, dict((themes[name] or {}).get("tokens") or {})


# The renderer is one CSS file with a light palette. A theme is a token set laid over it: the cascade
# does the rest, so a block never has to know which theme is running.
_THEME_RULES = """
      :root {{ {vars} }}
      html, body {{ background: var(--body-bg); }}
      #paper {{ background: radial-gradient(120% 85% at 50% 38%, var(--paper-hi) 0%, var(--paper-mid) 52%, var(--paper-lo) 100%); }}
      #light {{ opacity: var(--light-opacity); }}
      #grain {{ opacity: var(--grain-opacity); mix-blend-mode: var(--grain-blend); }}
      #vignette {{ background: radial-gradient(95% 75% at 50% 50%, rgba(0,0,0,0) 58%, var(--vignette) 100%); }}
      .glow {{ background: radial-gradient(closest-side, var(--glow), rgba(0,0,0,0) 70%); }}
      .card {{ background: var(--card-bg); border-color: var(--card-line); }}
      .blk-proof .seal {{ background: var(--seal-bg); }}
      .blk-proof .seal-flash {{ background: radial-gradient(closest-side, var(--seal-flash), rgba(0,0,0,0) 70%); }}
      .blk-cta .plane path, .blk-cta .mark path {{ stroke: var(--green); }}
      .brand img {{ filter: {logo}; }}
      #sprig path[stroke] {{ stroke: var(--sprig-line); }}
      #sprig path[fill]:not([fill="none"]) {{ fill: var(--sprig-leaf); }}
      .blk-steps .num {{ background: var(--chip-bg); }}
      .blk-cta .share {{ color: var(--ink); }}
      .blk-cta .invite.none {{ justify-content: center; }}
"""

_THEME_VARS = ["paper", "paper2", "green", "green2", "gold", "gold2", "ink", "ink2", "line", "body_bg",
               "paper_hi", "paper_mid", "paper_lo", "light_opacity", "grain_opacity", "grain_blend",
               "vignette", "glow", "card_bg", "card_line", "seal_bg", "seal_flash", "chip_bg",
               "sprig_line", "sprig_leaf"]


def theme_css(tokens: dict) -> str:
    if not tokens:
        return ""
    vars_ = " ".join(f"--{k.replace('_', '-')}: {tokens[k]};" for k in _THEME_VARS if k in tokens)
    return _THEME_RULES.format(vars=vars_, logo=tokens.get("logo_filter", "none"))


# ----------------------------------------------------------------------------- CSS
BASE_CSS = r"""
      @font-face { font-family: "Amiri Quran"; src: url("assets/fonts/AmiriQuran.ttf") format("truetype"); font-weight: 400; }
      @font-face { font-family: "Amiri"; src: url("assets/fonts/Amiri-Regular.ttf") format("truetype"); font-weight: 400; }
      @font-face { font-family: "Amiri"; src: url("assets/fonts/Amiri-Bold.ttf") format("truetype"); font-weight: 700; }
      @font-face { font-family: "Noto Kufi Arabic"; src: url("assets/fonts/NotoKufiArabic-Regular.ttf") format("truetype"); font-weight: 400; }
      @font-face { font-family: "Noto Kufi Arabic"; src: url("assets/fonts/NotoKufiArabic-Bold.ttf") format("truetype"); font-weight: 700; }
      @font-face { font-family: "Noto Naskh Arabic"; src: url("assets/fonts/NotoNaskhArabic-Regular.ttf") format("truetype"); font-weight: 400; }
      @font-face { font-family: "Noto Naskh Arabic"; src: url("assets/fonts/NotoNaskhArabic-Bold.ttf") format("truetype"); font-weight: 700; }

      * { margin: 0; padding: 0; box-sizing: border-box; }
      html, body { width: 1080px; height: 1920px; overflow: hidden; background: #ece6da; }
      :root { --paper: #ece6da; --paper-2: #e2dacb; --green: #1f4a35; --green-2: #2f6a4b; --gold: #957238; --gold-2: #cdb078;
              --ink: #2d2b27; --ink-2: #5a5650; --line: #8aa58f; }
      /* NOTE: direction is scoped to elements — never put dir="rtl" on <html> (renders a blank video). */
      #root { position: relative; width: 100%; height: 100%; overflow: hidden; direction: rtl; color: var(--ink); }

      #bg { position: absolute; inset: 0; z-index: 0; overflow: hidden; }
      #paper { position: absolute; inset: 0; background: radial-gradient(120% 85% at 50% 38%, #f4efe6 0%, #ebe4d7 52%, #ddd4c3 100%); }
      #light { position: absolute; top: -20%; left: -40%; width: 180%; height: 140%; opacity: 0.55;
        background: linear-gradient(112deg, rgba(255,255,255,0) 42%, rgba(255,255,255,0.42) 50%, rgba(255,255,255,0) 58%); }
      #grain { position: absolute; inset: -8%; opacity: 0.085; mix-blend-mode: multiply;
        background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='320' height='320'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch' seed='7'/><feColorMatrix type='saturate' values='0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>"); }
      #vignette { position: absolute; inset: 0; background: radial-gradient(95% 75% at 50% 50%, rgba(0,0,0,0) 58%, rgba(70,52,28,0.17) 100%); }
      #arc { position: absolute; left: 140px; top: 285px; width: 800px; height: 130px; }
      #arc path { fill: none; stroke: var(--line); stroke-width: 2.2; }
      #arc .dia { fill: var(--paper); stroke: var(--line); stroke-width: 2; }
      #sprig { position: absolute; right: 86px; top: 236px; width: 92px; height: 76px; opacity: 0.9; }

      .clip { position: absolute; inset: 0; z-index: 1; }
      .stage { position: absolute; inset: 0; direction: rtl; display: flex; flex-direction: column; align-items: center; justify-content: center;
        padding: 0 130px 150px 150px; text-align: center; }
      .block { display: block; width: 100%; }
      .w { display: inline-block; }
      .quran { font-family: "Amiri Quran", "Amiri", serif; color: var(--green); }
      .amiri { font-family: "Amiri", serif; color: var(--green); }
      .kufi  { font-family: "Noto Kufi Arabic", sans-serif; font-weight: 700; color: var(--green); }
      .kufi-r{ font-family: "Noto Kufi Arabic", sans-serif; font-weight: 400; }
      .naskh { font-family: "Noto Naskh Arabic", serif; color: var(--ink); }
      .gold { color: var(--gold); } .ink { color: var(--ink); } .ink2 { color: var(--ink-2); }
      .em { color: var(--gold); display: inline-block; font-size: 1.18em; padding: 0 0.06em; }
      .em.later { color: inherit; font-size: 1em; }
      .uline { position: relative; display: inline-block; isolation: isolate; }
      .uline .bar { position: absolute; right: 0; bottom: 0.06em; height: 0.16em; width: 100%; background: linear-gradient(90deg, var(--gold-2), var(--gold)); opacity: 0.55; border-radius: 4px; z-index: 0; }
      .uline .txt { position: relative; z-index: 1; }
      .rule { width: 140px; height: 2px; background: var(--gold); opacity: 0.8; margin: 26px auto 0; }

      /* hook */
      .blk-hook .lead { line-height: 1.8; opacity: 0.92; }
      .blk-hook .l1 { line-height: 1.5; margin-top: 50px; color: var(--ink); }
      .blk-hook .l2 { line-height: 1.4; }
      .blk-hook .sub { line-height: 1.8; margin-top: 60px; color: var(--ink-2); }
      /* verse / quote */
      .blk-verse .label, .blk-quote .label { letter-spacing: 0.02em; color: var(--gold); margin-bottom: 60px; }
      .blk-verse .verse { line-height: 1.95; } .blk-verse .line { display: block; } .blk-verse .nowrap { white-space: nowrap; } .blk-verse .w { margin: 0 0.16em; }
      .blk-quote .qline { display: block; line-height: 1.75; } .blk-quote .w { margin: 0 0.14em; }
      .blk-quote .attr, .blk-list .attr { line-height: 1.8; margin-top: 30px; color: var(--ink-2); }
      .hero-line { height: 6px; width: 72%; margin: 4px auto 0; background: linear-gradient(90deg, var(--gold-2), var(--gold), var(--gold-2)); border-radius: 4px; transform-origin: right center; }
      .glow { position: absolute; left: 50%; top: 50%; width: 1100px; height: 700px; margin: -350px 0 0 -550px; border-radius: 50%;
        background: radial-gradient(closest-side, rgba(210,180,122,0.55), rgba(210,180,122,0) 70%); pointer-events: none; }
      /* contrast */
      .blk-contrast .lbl { color: var(--ink-2); line-height: 1.6; }
      .blk-contrast .wrong { position: relative; display: inline-block; line-height: 1.6; color: var(--ink-2); }
      .blk-contrast .strike { position: absolute; right: 0; top: 54%; height: 5px; width: 100%; background: var(--gold); border-radius: 3px; transform-origin: right center; }
      .blk-contrast .r2 { margin-top: 44px; }
      .blk-contrast .right { line-height: 1.5; font-weight: 700; }
      .blk-contrast .l3 { line-height: 1.6; margin-top: 54px; }
      .blk-contrast .l4 { line-height: 1.8; margin-top: 10px; color: var(--ink); }
      /* answer */
      .blk-answer .q1 { line-height: 1.6; } .blk-answer .q2 { line-height: 1.7; color: var(--ink-2); margin-top: 6px; }
      .blk-answer .hero-wrap { position: relative; margin-top: 56px; display: block; width: 100%; }
      .blk-answer .hero { line-height: 1.45; font-weight: 700; display: inline-block; padding: 0 10px; position: relative; }
      .blk-answer .after { line-height: 1.55; margin-top: 40px; color: var(--ink); }
      .blk-answer .src { line-height: 1.7; margin-top: 26px; color: var(--ink-2); }
      /* proof */
      .blk-proof .seal-wrap { position: relative; width: 230px; height: 230px; margin-bottom: 40px; }
      .blk-proof .seal { position: absolute; inset: 0; border-radius: 50%; border: 3px double var(--green); display: flex; flex-direction: column; align-items: center; justify-content: center; background: rgba(255,255,255,0.22); color: var(--green); }
      .blk-proof .seal::before { content: ""; position: absolute; inset: 10px; border-radius: 50%; border: 1.5px solid var(--gold); opacity: 0.8; }
      .blk-proof .seal .t { font-size: 36px; line-height: 1.3; }
      .blk-proof .seal svg { width: 38px; height: 38px; margin-top: 4px; }
      .blk-proof .seal-flash { position: absolute; left: 50%; top: 50%; width: 520px; height: 520px; margin: -260px 0 0 -260px; border-radius: 50%; background: radial-gradient(closest-side, rgba(180,140,74,0.45), rgba(180,140,74,0) 70%); }
      .card { display: block; width: 760px; margin: 12px auto 0; padding: 12px 38px; border-radius: 999px; background: rgba(255,255,255,0.35); border: 1.5px solid rgba(31,74,53,0.35); line-height: 1.6; color: var(--ink); }
      .card b { color: var(--green); font-weight: 700; } .card .ok { color: var(--gold); }
      .blk-proof .p1 { line-height: 1.45; margin-top: 46px; font-weight: 700; }
      .blk-proof .p2 { line-height: 1.45; font-weight: 700; color: var(--gold); }
      .blk-proof .attr { line-height: 1.8; margin-top: 16px; color: var(--ink-2); }
      /* cta */
      .blk-cta .c1 { line-height: 1.55; }
      .blk-cta .path { width: 420px; height: 24px; margin: 6px auto 0; } .blk-cta .path path { fill: none; stroke: var(--gold); stroke-width: 3; stroke-linecap: round; }
      .blk-cta .c2 { line-height: 1.6; margin-top: 26px; color: var(--ink); }
      .blk-cta .share { display: flex; align-items: center; justify-content: center; gap: 26px; margin-top: 54px; }
      .blk-cta .share .txt { line-height: 1.5; color: var(--ink); } .blk-cta .plane { width: 80px; height: 80px; flex: none; }
      .blk-cta .share .bookmark { width: 64px; height: 64px; flex: none; }
      .blk-cta .share.none { gap: 0; }
      .blk-cta .no-invite .final { margin-top: 96px; }
      .blk-cta .no-invite .c2 { margin-top: 34px; }
      .blk-cta .final { line-height: 1.65; margin-top: 46px; }
      .blk-cta .final-line { height: 4px; width: 300px; margin: 0 auto; background: var(--gold); border-radius: 3px; transform-origin: center; }
      .brand { display: flex; flex-direction: column; align-items: center; gap: 6px; margin-top: 60px; }
      .brand img { width: 150px; height: auto; }
      .brand .h { font-family: "Noto Kufi Arabic", sans-serif; font-weight: 400; font-size: 38px; color: var(--green); letter-spacing: 0.02em; direction: ltr; }
      /* list / title */
      .blk-list .title, .blk-title .title { line-height: 1.5; }
      .blk-list .item { display: flex; align-items: baseline; justify-content: center; gap: 22px; line-height: 1.6; margin-top: 22px; color: var(--ink); }
      .blk-list .num { font-family: "Noto Kufi Arabic", sans-serif; font-weight: 700; color: var(--gold); font-size: 0.75em; }
      .blk-title .kicker { color: var(--gold); line-height: 1.7; margin-bottom: 18px; }
      .blk-title .sub { color: var(--ink-2); line-height: 1.7; margin-top: 26px; }

      /* ---- long-text blocks (v3 phase 2): paragraph · definition · steps · timeline · compare · qa
         Reading rules: body copy is right-aligned like a book page, never narrower than 34 px,
         one gold hairline on the right edge of running prose, no boxes around sacred text. */
      .kick { color: var(--gold); line-height: 1.7; letter-spacing: 0.02em; }
      .src { color: var(--ink-2); line-height: 1.8; }
      .pline { display: block; }
      .prose { text-align: right; }
      .prose .pline, .blk-qa .a .pline { border: 0; }
      /* paragraph */
      .blk-paragraph .kicker { margin-bottom: 30px; }
      .blk-paragraph .prose { border-right: 2px solid rgba(149,114,56,0.38); padding-right: 32px; }
      .blk-paragraph .src { margin-top: 34px; }
      /* definition */
      .blk-definition .kicker { margin-bottom: 26px; }
      .blk-definition .term { color: var(--green); line-height: 1.4; padding: 0 12px; display: inline-block; }
      .blk-definition .term-line { height: 5px; width: 58%; margin: 14px auto 0; border-radius: 3px; transform-origin: right center;
        background: linear-gradient(90deg, var(--gold-2), var(--gold), var(--gold-2)); }
      .blk-definition .body { margin-top: 48px; border-right: 2px solid rgba(149,114,56,0.38); padding-right: 32px; line-height: 1.85; }
      .blk-definition .note { margin-top: 22px; color: var(--ink-2); line-height: 1.7; }
      .blk-definition .src { margin-top: 18px; }
      /* steps */
      .blk-steps .steps { position: relative; width: 100%; margin-top: 40px; text-align: right; }
      .blk-steps .steps::before { content: ""; position: absolute; right: 33px; top: 40px; bottom: 40px; width: 1.5px; background: rgba(149,114,56,0.42); }
      .blk-steps .step { position: relative; display: flex; align-items: flex-start; gap: 24px; margin-top: 30px; }
      .blk-steps .step:first-child { margin-top: 0; }
      .blk-steps .num { position: relative; z-index: 1; flex: none; width: 68px; height: 68px; border-radius: 50%;
        border: 1.8px solid var(--gold); background: #f1ece1; color: var(--gold);
        font-family: "Noto Kufi Arabic", sans-serif; font-weight: 700; font-size: 32px;
        display: flex; align-items: center; justify-content: center; }
      .blk-steps .sbody { flex: 1; padding-top: 6px; }
      .blk-steps .shead { color: var(--green); line-height: 1.5; }
      .blk-steps .stext { color: var(--ink); line-height: 1.75; margin-top: 4px; }
      .blk-steps .src { margin-top: 34px; }
      /* timeline */
      .blk-timeline .items { position: relative; width: 100%; margin-top: 40px; text-align: right; }
      .blk-timeline .items::before { content: ""; position: absolute; right: 6px; top: 24px; bottom: 24px; width: 1.5px; background: rgba(149,114,56,0.42); }
      .blk-timeline .ev { position: relative; display: flex; align-items: baseline; gap: 22px; padding-right: 46px; margin-top: 34px; }
      .blk-timeline .ev:first-child { margin-top: 0; }
      .blk-timeline .ev::before { content: ""; position: absolute; right: 0; top: 0.55em; width: 13px; height: 13px; background: var(--gold); transform: rotate(45deg); }
      .blk-timeline .when { flex: none; color: var(--gold); line-height: 1.6; }
      .blk-timeline .etext { flex: 1; color: var(--ink); line-height: 1.75; }
      .blk-timeline .src { margin-top: 34px; }
      /* compare */
      .blk-compare .grid { display: flex; align-items: stretch; width: 100%; margin-top: 40px; }
      .blk-compare .col { flex: 1; padding: 0 26px; text-align: right; }
      .blk-compare .col + .col { border-right: 1.5px solid rgba(149,114,56,0.36); }
      .blk-compare .chead { color: var(--green); line-height: 1.5; }
      .blk-compare .pt { position: relative; margin-top: 20px; padding-right: 28px; color: var(--ink); line-height: 1.7; }
      .blk-compare .pt::before { content: ""; position: absolute; right: 0; top: 0.62em; width: 9px; height: 9px; background: var(--gold); transform: rotate(45deg); }
      .blk-compare .verdict { width: 100%; margin-top: 44px; color: var(--ink); line-height: 1.7; }
      .blk-compare .src { margin-top: 20px; }
      /* qa */
      .blk-qa .qlabel, .blk-qa .alabel { color: var(--gold); line-height: 1.7; }
      .blk-qa .q { margin-top: 14px; color: var(--green); line-height: 1.55; text-align: right; }
      .blk-qa .rule { margin-top: 34px; margin-bottom: 34px; }
      .blk-qa .a { margin-top: 16px; color: var(--ink); line-height: 1.85; text-align: right; }
      .blk-qa .note { margin-top: 22px; color: var(--ink-2); line-height: 1.7; text-align: right; }
      .blk-qa .src { margin-top: 20px; }

      #wm { position: absolute; left: 0; right: 0; top: 1372px; z-index: 2; display: flex; align-items: center; justify-content: center; gap: 12px; opacity: 0; }
      #wm img { width: 54px; height: auto; }
      #wm span { font-family: "Noto Kufi Arabic", sans-serif; font-size: 28px; color: var(--green); direction: ltr; opacity: 0.85; }
"""

BG_HTML = """      <div id="bg">
        <div id="paper"></div>
        <div id="light" data-layout-allow-overflow></div>
        <div id="grain"></div>
        <div id="vignette"></div>
        <svg id="arc" viewBox="0 0 800 130" aria-hidden="true">
          <path id="arc-path" d="M14 112 Q400 -70 786 112" />
          <path id="arc-dia-l" class="dia" d="M14 112 l10 -10 l10 10 l-10 10 z" />
          <path id="arc-dia-r" class="dia" d="M766 112 l10 -10 l10 10 l-10 10 z" />
          <path id="arc-dia-t" class="dia" d="M390 22 l10 -10 l10 10 l-10 10 z" />
        </svg>
        <svg id="sprig" viewBox="0 0 92 76" aria-hidden="true">
          <path d="M12 66 Q40 54 74 26" fill="none" stroke="#9a8650" stroke-width="2.2" stroke-linecap="round"/>
          <path d="M36 52 Q22 36 30 18 Q46 30 36 52 Z" fill="#4f7a55"/>
          <path d="M50 42 Q46 22 62 10 Q70 30 50 42 Z" fill="#3f6b48"/>
          <path d="M60 36 Q78 30 86 14 Q90 36 60 36 Z" fill="#5a8a5e"/>
        </svg>
      </div>
"""

JS_HELPERS = r"""
      const EASE_IN = "power3.out", EASE_OUT = "power2.in";
      const GOLD = "#957238";
      const tl = gsap.timeline({ paused: true, defaults: { ease: EASE_IN } });
      function enter(sel, t, o = {}) {
        const { dur = 0.75, y = 30, blur = 10, scale = null, ease = EASE_IN } = o;
        const from = { opacity: 0, y, filter: `blur(${blur}px)` };
        const to = { opacity: 1, y: 0, filter: "blur(0px)", duration: dur, ease };
        if (scale !== null) { from.scale = scale; to.scale = 1; }
        tl.fromTo(sel, from, to, t);
      }
      function exit(sel, t, o = {}) {
        const { dur = 0.42, y = -22, blur = 6, ease = EASE_OUT } = o;
        tl.to(sel, { opacity: 0, y, filter: `blur(${blur}px)`, duration: dur, ease }, t);
      }
      function sceneIn(sel, t, dur = 0.35) { tl.fromTo(sel, { opacity: 0 }, { opacity: 1, duration: dur, ease: "power1.out" }, t); }
      function drawPath(id, t, dur) { const el = document.getElementById(id); const L = el.getTotalLength();
        tl.fromTo(el, { strokeDasharray: L, strokeDashoffset: L }, { strokeDashoffset: 0, duration: dur, ease: "power2.inOut" }, t); }
      function heroIn(sel, lineSel, glowSel, t) {
        tl.fromTo(sel, { opacity: 1, clipPath: "inset(-10% 0% -10% 100%)", scale: 0.965, filter: "blur(3px)" },
                       { clipPath: "inset(-10% 0% -10% 0%)", scale: 1, filter: "blur(0px)", duration: 0.95, ease: "power3.out" }, t);
        if (lineSel) tl.fromTo(lineSel, { opacity: 1, scaleX: 0 }, { scaleX: 1, duration: 0.6, ease: "power2.out" }, t + 0.3);
        if (glowSel) { tl.fromTo(glowSel, { opacity: 0, scale: 0.7 }, { opacity: 0.85, scale: 1, duration: 0.5, ease: "power2.out" }, t);
                       tl.to(glowSel, { opacity: 0.35, scale: 1.08, duration: 2.2, ease: "power1.out" }, t + 0.5); }
        tl.fromTo(sel, { scale: 1 }, { scale: 1.012, duration: 1.8, ease: "sine.inOut", yoyo: true, repeat: 1 }, t + 1.0);
      }
"""

PLANE_SVG = """<svg class="plane" viewBox="0 0 64 64" aria-hidden="true"><path d="M58 6 L6 28 L26 36 L34 58 L58 6 Z" fill="none" stroke="#1f4a35" stroke-width="3.2" stroke-linejoin="round"/><path d="M26 36 L58 6" fill="none" stroke="#1f4a35" stroke-width="3.2" stroke-linecap="round"/></svg>"""
BOOKMARK_SVG = """<svg class="bookmark" viewBox="0 0 64 64" aria-hidden="true"><path d="M18 8 h28 v48 l-14 -11 l-14 11 Z" fill="none" stroke="#1f4a35" stroke-width="3.2" stroke-linejoin="round"/><path d="M26 24 h12" stroke="#1f4a35" stroke-width="3" stroke-linecap="round"/></svg>"""
NO_ICON = "none"


def invite_icon(sc: dict, brand_cta: dict, text: str) -> str:
    """send · save · none — explicit, then the brand's map, then the verb itself."""
    want = (sc.get("icon") or "").strip()
    if want in ("send", "save", "none"):
        return want
    mapped = (brand_cta.get("icons") or {}).get(text)
    if mapped in ("send", "save", "none"):
        return mapped
    if text.startswith("احفظ") or text.startswith("احْفَظ"):
        return "save"
    if text.startswith("أرسل") or text.startswith("أَرْسِل") or text.startswith("ابعث"):
        return "send"
    return NO_ICON
CHECK_SVG = """<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M8 25 L19 36 L40 13" fill="none" stroke="#b48c4a" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/></svg>"""


# ----------------------------------------------------------------------------- blocks
class Ctx:
    def __init__(self):
        self.html, self.js, self.warn = [], [], []
        self.cues = {}            # scene id -> {name: abs seconds}
        self.brand = {}           # config/brand.json, for tables a block needs (CTA icons)
        self.cuts = []            # scene start times (for SFX)


def _seq(scene, keys, start_pad=0.3):
    """default cue times for a list of text keys: sequential, reading-speed based."""
    t = scene["start"] + start_pad
    out = {}
    for k in keys:
        txt = scene.get(k)
        if not txt:
            continue
        out[k] = round(t, 2)
        t += dwell(txt if isinstance(txt, str) else " ".join(map(str, txt))) + GAP
    return out


def _cues(scene, defaults):
    c = dict(defaults)
    for k, v in (scene.get("cues") or {}).items():
        c[k] = v
    # relative cues ("+1.2") are allowed
    for k, v in list(c.items()):
        if isinstance(v, str) and v.startswith("+"):
            c[k] = round(scene["start"] + float(v[1:]), 2)
    return c


def _check_room(scene, cues, ctx):
    last = max([v for v in cues.values() if isinstance(v, (int, float))] or [scene["start"]])
    if last > scene["end"] - 0.9:
        ctx.warn.append(f"[{scene['id']}] last reveal at {last:.2f}s is less than 0.9s before the scene ends ({scene['end']}s) — extend the scene or drop a line")


def blk_hook(sc, ctx):
    sid = sc["id"]
    lead_font = sc.get("lead_font", "quran")
    f_lead = fit(sc.get("lead", ""), lead_font, 66, 44)
    f1 = fit(sc.get("line1", ""), "kufi", 84, 56)
    f2 = fit(sc.get("line2", ""), "kufi", 138, 84)
    cues = _cues(sc, {"emphasis": round(min(sc["end"] - 1.2, sc["start"] + 1.9), 2)})
    ctx.cues[sid] = cues
    h = [f'<section id="{sid}" class="clip blk-hook" data-track-index="{sc.get("track",1)}" data-start="{sc["start"]}" data-duration="{round(sc["end"]-sc["start"],3)}"><div class="stage">']
    if sc.get("lead"):
        h.append(f'<div id="{sid}-lead" class="block lead {lead_font}" style="font-size:{f_lead}px">{em(sc["lead"])}</div>')
    if sc.get("line1"):
        h.append(f'<div id="{sid}-l1" class="block l1 kufi" style="font-size:{f1}px">{em(sc["line1"])}</div>')
    h.append(f'<div id="{sid}-l2" class="block l2 kufi" style="font-size:{f2}px"><span class="uline"><span class="bar" id="{sid}-bar"></span><span class="txt">{em(sc.get("line2",""))}</span></span></div>')
    h.append(f'<div class="rule" id="{sid}-rule"></div>')
    if sc.get("sub"):
        h.append(f'<div id="{sid}-sub" class="block sub naskh" style="font-size:{fit(sc["sub"], "naskh", 38, 28)}px">{em(sc["sub"])}</div>')
    h.append('</div></section>')
    ctx.html.append("\n".join(h))
    s = sc["start"]
    js = [f"// ---- {sid} hook",
          f'tl.fromTo("#{sid}-lead", {{ opacity: 0.6, y: 12, filter: "blur(3px)" }}, {{ opacity: 1, y: 0, filter: "blur(0px)", duration: 0.5 }}, {s});' if sc.get("lead") else "",
          f'enter("#{sid}-l1", {s+0.16:.2f}, {{ dur: 0.7, y: 34 }});' if sc.get("line1") else "",
          f'enter("#{sid}-l2", {s+0.34:.2f}, {{ dur: 0.8, y: 40, blur: 14, scale: 0.94 }});',
          f'tl.fromTo("#{sid}-rule", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.6, ease: "power2.out" }}, {s+0.85:.2f});',
          f'enter("#{sid}-sub", {s+1.0:.2f}, {{ dur: 0.6, y: 18, blur: 6 }});' if sc.get("sub") else "",
          f'tl.fromTo("#{sid}-bar", {{ scaleX: 0, transformOrigin: "right center" }}, {{ scaleX: 1, duration: 0.5, ease: "power2.out" }}, {cues["emphasis"]});',
          f'tl.fromTo("#{sid}-l2", {{ scale: 1 }}, {{ scale: 1.035, duration: 0.3, ease: "power2.out", yoyo: true, repeat: 1 }}, {cues["emphasis"]});',
          f'exit("#{sid} .stage > *", {sc["end"]-0.42:.2f}, {{ dur: 0.4 }});']
    ctx.js.append("\n".join(x for x in js if x))


def blk_verse(sc, ctx):
    """Quranic verse (or any sacred text) revealed word by word."""
    sid = sc["id"]
    lines = sc["lines"]                      # list of lists of words
    flat = [w for ln in lines for w in ln]
    n = len(flat)
    font = sc.get("font", "quran")
    size = sc.get("size") or fit_wrapped(lines, font, 94, 52, max_lines=sc.get("max_lines", 4))[0]
    # cues: explicit word times, or evenly paced reading
    if "words" in (sc.get("cues") or {}):
        wt = sc["cues"]["words"]
    else:
        t0 = sc["start"] + 0.55
        span = (sc["end"] - 1.6) - t0
        step = min(0.85, max(0.42, span / max(1, n)))
        wt = [round(t0 + i * step, 2) for i in range(n)]
    if len(wt) != n:
        ctx.warn.append(f"[{sid}] cues.words has {len(wt)} entries but the verse has {n} words")
    hl = sc.get("highlight") or {}
    hl_at = hl.get("at", round(min(sc["end"] - 1.3, (wt[-1] if wt else sc["start"]) + 0.6), 2))
    cues = {"words": wt, "highlight": hl_at, "label": round(sc["start"] + 0.15, 2)}
    ctx.cues[sid] = cues
    h = [f'<section id="{sid}" class="clip blk-verse" data-track-index="{sc.get("track",1)}" data-start="{sc["start"]}" data-duration="{round(sc["end"]-sc["start"],3)}"><div class="stage">']
    if sc.get("label"):
        h.append(f'<div id="{sid}-label" class="block label kufi-r" style="font-size:{fit(sc["label"], "kufi-r", 36, 26)}px">{em(sc["label"])}</div>')
    h.append(f'<div id="{sid}-verse" class="block verse {font}" style="font-size:{size}px">')
    k = 0
    for ln in lines:
        cls = "line" + (" nowrap" if sc.get("nowrap") else "")
        h.append(f'<span class="{cls}">' + "".join(f'<span class="w" id="{sid}-w{k+i+1}">{html.escape(w)}</span>' for i, w in enumerate(ln)) + "</span>")
        k += len(ln)
    h.append("</div></div></section>")
    ctx.html.append("\n".join(h))
    js = [f"// ---- {sid} verse", f'sceneIn("#{sid} .stage", {sc["start"]});']
    if sc.get("label"):
        js.append(f'enter("#{sid}-label", {cues["label"]}, {{ dur: 0.6, y: 16, blur: 6 }});')
    for i, t in enumerate(wt):
        js.append(f'enter("#{sid}-w{i+1}", {t-0.28:.2f}, {{ dur: 0.75, y: 22, blur: 12, scale: 0.98 }});')
    if hl.get("words"):
        sel = "[" + ",".join(f'"#{sid}-w{i}"' for i in hl["words"]) + "]"
        js.append(f'tl.to({sel}, {{ color: GOLD, duration: 0.9, ease: "power2.inOut" }}, {hl_at});')
        js.append(f'tl.fromTo({sel}, {{ scale: 1 }}, {{ scale: 1.05, duration: 0.9, ease: "power2.out", transformOrigin: "center" }}, {hl_at});')
    js.append(f'tl.to("#{sid}-verse", {{ scale: 1.015, duration: {max(2.0, sc["end"]-sc["start"]-1.5):.1f}, ease: "none", transformOrigin: "center" }}, {sc["start"]+0.4:.2f});')
    js.append(f'exit("#{sid} .stage > *", {sc["end"]-0.45:.2f});')
    ctx.js.append("\n".join(js))


def blk_contrast(sc, ctx):
    sid = sc["id"]
    d = _seq(sc, ["wrong", "right", "line3", "line4"], start_pad=0.3)
    strike = round(d.get("wrong", sc["start"]) + 1.0, 2)
    shift = max(0.0, (strike + 1.0) - d.get("right", strike + 1.0))   # the right phrase lands >= 1 s after the strike
    for k in ("right", "line3", "line4"):
        if k in d:
            d[k] = round(d[k] + shift, 2)
    defaults = {"wrong": d.get("wrong"), "strike": strike, "right": d.get("right"), "line3": d.get("line3"), "line4": d.get("line4")}
    if sc.get("line4"):
        defaults["line4_gold"] = round(d["line4"] + 1.1, 2)
    cues = _cues(sc, {k: v for k, v in defaults.items() if v is not None})
    ctx.cues[sid] = cues
    _check_room(sc, cues, ctx)
    fw = fit(sc.get("wrong", ""), "amiri", 72, 46); fr = fit(sc.get("right", ""), "amiri-b", 92, 56)
    h = [f'<section id="{sid}" class="clip blk-contrast" data-track-index="{sc.get("track",1)}" data-start="{sc["start"]}" data-duration="{round(sc["end"]-sc["start"],3)}"><div class="stage">',
         f'<div class="block row"><div class="lbl kufi-r" id="{sid}-l1" style="font-size:{fit(sc.get("wrong_label",""), "kufi-r", 42, 30)}px">{em(sc.get("wrong_label",""))}</div>'
         f'<div class="wrong amiri" id="{sid}-wrong" style="font-size:{fw}px">{em(sc.get("wrong",""))}<div class="strike" id="{sid}-strike"></div></div></div>',
         f'<div class="block row r2"><div class="lbl kufi-r" id="{sid}-l2" style="font-size:{fit(sc.get("right_label",""), "kufi-r", 42, 30)}px">{em(sc.get("right_label",""))}</div>'
         f'<div class="right amiri" id="{sid}-right" style="font-size:{fr}px">{em(sc.get("right",""))}</div></div>']
    if sc.get("line3"):
        h.append(f'<div class="block l3 kufi" id="{sid}-l3" style="font-size:{fit(sc["line3"], "kufi", 64, 40)}px">{em(sc["line3"])}</div>')
    if sc.get("line4"):
        # the gold word of line4 lights up later (cue line4_gold) → mark it "later"
        line4_html = em(sc["line4"]).replace('class="em"', 'class="em later"')
        h.append(f'<div class="block l4 naskh" id="{sid}-l4" style="font-size:{fit(sc["line4"], "naskh", 52, 34)}px">{line4_html}</div>')
    h.append("</div></section>")
    ctx.html.append("\n".join(h))
    js = [f"// ---- {sid} contrast", f'sceneIn("#{sid} .stage", {sc["start"]});',
          f'enter("#{sid}-l1", {cues["wrong"]-0.05:.2f}, {{ dur: 0.55, y: 16 }});',
          f'enter("#{sid}-wrong", {cues["wrong"]+0.25:.2f}, {{ dur: 0.7, y: 26 }});',
          f'tl.fromTo("#{sid}-strike", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.45, ease: "power2.inOut" }}, {cues["strike"]});',
          f'tl.to("#{sid}-wrong", {{ opacity: 0.42, duration: 0.5 }}, {cues["strike"]+0.15:.2f});',
          f'enter("#{sid}-l2", {cues["right"]-0.1:.2f}, {{ dur: 0.55, y: 16 }});',
          f'enter("#{sid}-right", {cues["right"]+0.15:.2f}, {{ dur: 0.8, y: 30, blur: 12, scale: 0.97 }});',
          f'tl.fromTo("#{sid}-right .em", {{ scale: 1, transformOrigin: "center" }}, {{ scale: 1.18, duration: 0.35, ease: "power2.out", yoyo: true, repeat: 1 }}, {cues["right"]+0.95:.2f});']
    if sc.get("line3"):
        js.append(f'enter("#{sid}-l3", {cues["line3"]}, {{ dur: 0.7, y: 28 }});')
    if sc.get("line4"):
        js.append(f'enter("#{sid}-l4", {cues["line4"]}, {{ dur: 0.7, y: 24 }});')
        js.append(f'tl.to("#{sid}-l4 .em", {{ color: GOLD, duration: 0.5 }}, {cues["line4_gold"]});')
    js.append(f'exit("#{sid} .stage > *", {sc["end"]-0.45:.2f});')
    ctx.js.append("\n".join(js))


def blk_answer(sc, ctx):
    sid = sc["id"]
    d = _seq(sc, ["q1", "q2", "hero", "after", "source"], start_pad=0.3)
    cues = _cues(sc, d)
    ctx.cues[sid] = cues
    _check_room(sc, cues, ctx)
    fh = fit(sc.get("hero", ""), "amiri-b", 118, 70, width=780)
    h = [f'<section id="{sid}" class="clip blk-answer" data-track-index="{sc.get("track",1)}" data-start="{sc["start"]}" data-duration="{round(sc["end"]-sc["start"],3)}"><div class="stage" id="{sid}-stage"><div class="glow" id="{sid}-glow"></div>']
    if sc.get("q1"): h.append(f'<div id="{sid}-q1" class="block q1 amiri" style="font-size:{fit(sc["q1"], "amiri", 64, 44)}px">{em(sc["q1"])}</div>')
    if sc.get("q2"): h.append(f'<div id="{sid}-q2" class="block q2 naskh" style="font-size:{fit(sc["q2"], "naskh", 48, 32)}px">{em(sc["q2"])}</div>')
    h.append(f'<div class="hero-wrap"><div id="{sid}-hero" class="hero amiri" style="font-size:{fh}px">{em(sc.get("hero",""))}</div><div class="hero-line" id="{sid}-hline"></div></div>')
    if sc.get("after"): h.append(f'<div id="{sid}-after" class="block after amiri" style="font-size:{fit(sc["after"], "amiri", 74, 46)}px">{em(sc["after"])}</div>')
    if sc.get("source"): h.append(f'<div id="{sid}-src" class="block src naskh" style="font-size:{fit(sc["source"], "naskh", 34, 26)}px">{em(sc["source"])}</div>')
    h.append("</div></section>")
    ctx.html.append("\n".join(h))
    js = [f"// ---- {sid} answer", f'sceneIn("#{sid} .stage", {sc["start"]});',
          f'tl.set(["#{sid}-glow", "#{sid}-hero", "#{sid}-hline", "#{sid}-after", "#{sid}-src"], {{ opacity: 0 }}, 0);']
    if sc.get("q1"): js.append(f'enter("#{sid}-q1", {cues["q1"]}, {{ dur: 0.8, y: 28 }});')
    if sc.get("q2"): js.append(f'enter("#{sid}-q2", {cues["q2"]}, {{ dur: 0.6, y: 18, blur: 6 }});')
    js += [f'heroIn("#{sid}-hero", "#{sid}-hline", "#{sid}-glow", {cues["hero"]});',
           f'tl.to(["#{sid}-q1", "#{sid}-q2"], {{ y: -16, opacity: 0.78, duration: 0.8, ease: "power2.out" }}, {cues["hero"]});',
           f'tl.fromTo("#{sid}-stage", {{ scale: 1 }}, {{ scale: 1.028, duration: 3.6, ease: "power1.out", transformOrigin: "50% 45%" }}, {cues["hero"]});']
    if sc.get("after"): js.append(f'enter("#{sid}-after", {cues["after"]}, {{ dur: 0.75, y: 26 }});')
    if sc.get("source"): js.append(f'enter("#{sid}-src", {cues["source"]}, {{ dur: 0.6, y: 14, blur: 5 }});')
    js.append(f'exit("#{sid} .stage > *:not(.glow)", {sc["end"]-0.45:.2f}); tl.to("#{sid}-glow", {{ opacity: 0, duration: 0.4 }}, {sc["end"]-0.45:.2f});')
    ctx.js.append("\n".join(js))


def blk_proof(sc, ctx):
    sid = sc["id"]
    cards = sc.get("cards") or []
    t = sc["start"] + 0.8
    d = {}
    if sc.get("seal"): d["seal"] = round(t, 2); t += 1.2
    cd = []
    for c in cards:
        cd.append(round(t, 2)); t += 1.1
    if cards: d["cards"] = cd; t += 0.6
    for k in ["line1", "line2", "attribution"]:
        if sc.get(k): d[k] = round(t, 2); t += dwell(sc[k]) + GAP
    cues = _cues(sc, d)
    ctx.cues[sid] = cues
    _check_room(sc, {k: v for k, v in cues.items() if k != "cards"}, ctx)
    h = [f'<section id="{sid}" class="clip blk-proof" data-track-index="{sc.get("track",1)}" data-start="{sc["start"]}" data-duration="{round(sc["end"]-sc["start"],3)}"><div class="stage" id="{sid}-stage">']
    if sc.get("seal"):
        t1, t2 = (sc["seal"] + [""])[:2]
        h.append(f'<div class="seal-wrap"><div class="seal-flash" id="{sid}-flash"></div><div class="seal" id="{sid}-seal"><div class="t kufi">{em(t1)}</div><div class="t kufi">{em(t2)}</div>{CHECK_SVG}</div></div>')
    for i, c in enumerate(cards):
        txt = f'<b>{em(c.get("book",""))}</b>' + (f' · {em(c["loc"])}' if c.get("loc") else "") + (f' · <span class="ok">{em(c["grade"])}</span>' if c.get("grade") else "")
        h.append(f'<div class="card naskh" id="{sid}-card{i+1}" style="font-size:{fit(plain(txt), "naskh", 42, 28, width=680)}px">{txt}</div>')
    if sc.get("line1"): h.append(f'<div id="{sid}-p1" class="block p1 amiri" style="font-size:{fit(sc["line1"], "amiri-b", 76, 48)}px">{em(sc["line1"])}</div>')
    if sc.get("line2"): h.append(f'<div id="{sid}-p2" class="block p2 amiri" style="font-size:{fit(sc["line2"], "amiri-b", 76, 48)}px">{em(sc["line2"])}</div>')
    if sc.get("attribution"): h.append(f'<div id="{sid}-attr" class="block attr naskh" style="font-size:{fit(sc["attribution"], "naskh", 34, 26)}px">{em(sc["attribution"])}</div>')
    h.append("</div></section>")
    ctx.html.append("\n".join(h))
    js = [f"// ---- {sid} proof", f'sceneIn("#{sid} .stage", {sc["start"]});',
          'tl.set([' + ",".join(f'"#{sid}-{x}"' for x in (["seal", "flash"] if sc.get("seal") else []) + [f"card{i+1}" for i in range(len(cards))] + [x for x, k in (("p1", "line1"), ("p2", "line2"), ("attr", "attribution")) if sc.get(k)]) + '], { opacity: 0 }, 0);']
    if sc.get("seal"):
        js += [f'tl.fromTo("#{sid}-seal", {{ opacity: 0, scale: 1.55, rotation: -9, transformOrigin: "center" }}, {{ opacity: 1, scale: 1, rotation: -5, duration: 0.42, ease: "power3.out" }}, {cues["seal"]});',
               f'tl.fromTo("#{sid}-flash", {{ opacity: 0, scale: 0.6 }}, {{ opacity: 1, scale: 1, duration: 0.25, ease: "power2.out" }}, {cues["seal"]+0.05:.2f});',
               f'tl.to("#{sid}-flash", {{ opacity: 0, scale: 1.25, duration: 1.1, ease: "power2.out" }}, {cues["seal"]+0.3:.2f});']
    for i, ct in enumerate(cues.get("cards", [])):
        js.append(f'tl.fromTo("#{sid}-card{i+1}", {{ opacity: 0, x: 70, filter: "blur(6px)" }}, {{ opacity: 1, x: 0, filter: "blur(0px)", duration: 0.6 }}, {ct});')
    if sc.get("line1"): js.append(f'enter("#{sid}-p1", {cues["line1"]}, {{ dur: 0.75, y: 28, blur: 12 }});')
    if sc.get("line2"): js.append(f'enter("#{sid}-p2", {cues["line2"]}, {{ dur: 0.75, y: 28, blur: 12 }});')
    if sc.get("attribution"): js.append(f'enter("#{sid}-attr", {cues["attribution"]}, {{ dur: 0.6, y: 14, blur: 5 }});')
    js.append(f'tl.fromTo("#{sid}-stage", {{ scale: 1 }}, {{ scale: 1.02, duration: {sc["end"]-sc["start"]:.1f}, ease: "none", transformOrigin: "50% 40%" }}, {sc["start"]});')
    js.append(f'exit("#{sid} .stage > *", {sc["end"]-0.45:.2f});')
    ctx.js.append("\n".join(js))


def blk_cta(sc, ctx):
    sid = sc["id"]
    d = _seq(sc, ["line1", "line2", "share", "final"], start_pad=0.3)
    user = sc.get("cues") or {}
    latest = round(sc["end"] - 2.6, 2)                  # final line + brand card need >= 2.6 s together
    if "final" in d and "final" not in user and d["final"] > latest:
        ctx.warn.append(f"[{sid}] cta is tight: final line moved from {d['final']}s to {latest}s — extend the scene or cut a line")
        d["final"] = latest
    d["brand"] = round(d["final"] + 0.7, 2) if "final" in d else round(sc["end"] - 1.9, 2)
    cues = _cues(sc, d)
    if "final" in cues and "brand" not in user:
        cues["brand"] = round(cues["final"] + 0.7, 2)
    if sc["end"] - cues["brand"] < 1.5:
        ctx.warn.append(f"[{sid}] brand card shows only {sc['end'] - cues['brand']:.1f}s (needs >= 1.5s)")
    ctx.cues[sid] = cues
    _check_room(sc, cues, ctx)
    brand = sc.get("brand") or {}
    handle = brand.get("handle", "@maalsadiqeen")
    invite = str(sc.get("share") or "").strip()
    icon = invite_icon(sc, ctx.brand.get("cta") or {}, invite) if invite else NO_ICON
    stage_cls = "stage" + ("" if invite else " no-invite")
    h = [f'<section id="{sid}" class="clip blk-cta" data-track-index="{sc.get("track",1)}" data-start="{sc["start"]}" data-duration="{round(sc["end"]-sc["start"],3)}"><div class="{stage_cls}">']
    if sc.get("line1"):
        h.append(f'<div id="{sid}-c1" class="block c1 kufi" style="font-size:{fit(sc["line1"], "kufi", 76, 48)}px">{em(sc["line1"])}</div>')
        h.append(f'<svg class="path" id="{sid}-path" viewBox="0 0 420 24" aria-hidden="true"><path id="{sid}-pathline" d="M414 12 C 330 2, 250 22, 170 12 S 40 2, 6 12" /></svg>')
    if sc.get("line2"): h.append(f'<div id="{sid}-c2" class="block c2 amiri" style="font-size:{fit(sc["line2"], "amiri", 68, 44)}px">{em(sc["line2"])}</div>')
    if invite:
        mark = PLANE_SVG if icon == "send" else (BOOKMARK_SVG if icon == "save" else "")
        h.append(f'<div class="share {icon}" id="{sid}-share">{mark}<div class="txt kufi-r" style="font-size:{fit(invite, "kufi-r", 60, 40, width=660)}px">{em(invite)}</div></div>')
    if sc.get("final"):
        h.append(f'<div id="{sid}-final" class="block final {sc.get("final_font","quran")}" style="font-size:{fit(sc["final"], sc.get("final_font","quran"), 104, 64)}px">{em(sc["final"])}</div><div class="final-line" id="{sid}-fline"></div>')
    h.append(f'<div class="brand" id="{sid}-brand"><img src="assets/img/logo.png" alt="" /><div class="h">{html.escape(handle)}</div></div>')
    h.append("</div></section>")
    ctx.html.append("\n".join(h))
    js = [f"// ---- {sid} cta", f'sceneIn("#{sid} .stage", {sc["start"]});', f'tl.set("#{sid} .stage > *", {{ opacity: 0 }}, 0);']
    if sc.get("line1"):
        js.append(f'enter("#{sid}-c1", {cues["line1"]}, {{ dur: 0.7, y: 26 }}); tl.set("#{sid}-path", {{ opacity: 1 }}, {cues["line1"]}); drawPath("{sid}-pathline", {cues["line1"]+0.2:.2f}, 1.1);')
    if sc.get("line2"): js.append(f'enter("#{sid}-c2", {cues["line2"]}, {{ dur: 0.75, y: 26 }});')
    if invite:
        js.append(f'tl.fromTo("#{sid}-share", {{ opacity: 0, y: 30 }}, {{ opacity: 1, y: 0, duration: 0.6 }}, {cues["share"]});')
        if icon == "send":
            js += [f'tl.fromTo("#{sid}-share .plane", {{ x: -140, y: 90, rotation: -18, opacity: 0 }}, {{ x: 0, y: 0, rotation: 0, opacity: 1, duration: 0.8, ease: "power3.out" }}, {cues["share"]});',
                   f'tl.to("#{sid}-share .plane", {{ y: -6, duration: 1.4, ease: "sine.inOut", yoyo: true, repeat: 2 }}, {cues["share"]+0.8:.2f});']
        elif icon == "save":
            js += [f'tl.fromTo("#{sid}-share .bookmark", {{ y: -26, opacity: 0, scale: 0.8 }}, {{ y: 0, opacity: 1, scale: 1, duration: 0.7, ease: "back.out(1.6)" }}, {cues["share"]});',
                   f'tl.to("#{sid}-share .bookmark", {{ y: 4, duration: 1.6, ease: "sine.inOut", yoyo: true, repeat: 2 }}, {cues["share"]+0.7:.2f});']
        js.append(f'tl.to(["#{sid}-c1", "#{sid}-path", "#{sid}-c2"], {{ y: -26, opacity: 0.55, duration: 0.7, ease: "power2.out" }}, {cues["share"]});')
    if sc.get("final"):
        js += [f'enter("#{sid}-final", {cues["final"]}, {{ dur: 0.9, y: 34, blur: 14, scale: 0.96 }});',
               f'tl.fromTo("#{sid}-fline", {{ opacity: 1, scaleX: 0 }}, {{ scaleX: 1, duration: 0.6, ease: "power2.out" }}, {cues["final"]+0.35:.2f});']
    js += [f'tl.fromTo("#{sid}-brand", {{ opacity: 0, y: 18 }}, {{ opacity: 1, y: 0, duration: 0.7 }}, {cues.get("brand", sc["end"]-1.6)});',
           f'tl.fromTo("#{sid}-brand img", {{ scale: 0.86, transformOrigin: "center" }}, {{ scale: 1, duration: 0.9, ease: "power2.out" }}, {cues.get("brand", sc["end"]-1.6)});',
           f'tl.to("#arc", {{ opacity: 0, duration: 0.8, ease: "power1.inOut" }}, {sc["start"]+0.2:.2f});']
    ctx.js.append("\n".join(js))


def blk_quote(sc, ctx):
    """Generic hadith / scholar quote: label, text lines (word- or line-reveal), attribution. hero:true adds underline+glow."""
    sid = sc["id"]
    font = sc.get("font", "amiri")
    lines = sc["text"] if isinstance(sc["text"], list) else [sc["text"]]
    reveal = sc.get("reveal", "lines")
    size = sc.get("size") or fit_wrapped([words(ln) for ln in lines], font, 96 if len(lines) <= 2 else 76, 44,
                                           max_lines=sc.get("max_lines", 5), gap_em=0.28, line_height=1.75)[0]
    # cues
    if reveal == "words":
        flat = [w for ln in lines for w in words(ln)]
        if "words" in (sc.get("cues") or {}):
            wt = sc["cues"]["words"]
        else:
            t0 = sc["start"] + 0.6; span = (sc["end"] - 1.8) - t0
            step = min(0.8, max(0.4, span / max(1, len(flat))))
            wt = [round(t0 + i * step, 2) for i in range(len(flat))]
        cues = {"words": wt}
        last = wt[-1] if wt else sc["start"]
    else:
        t = sc["start"] + 0.5; lt = []
        for ln in lines:
            lt.append(round(t, 2)); t += dwell(ln) + GAP
        cues = {"lines": (sc.get("cues") or {}).get("lines", lt)}
        last = cues["lines"][-1]
    cues["label"] = round(sc["start"] + 0.15, 2)
    cues["attribution"] = (sc.get("cues") or {}).get("attribution", round(last + 1.0, 2))
    cues["hero"] = (sc.get("cues") or {}).get("hero", cues["lines"][0] if reveal != "words" else sc["start"] + 0.6)
    ctx.cues[sid] = cues
    _check_room(sc, {k: v for k, v in cues.items() if k not in ("words", "lines")}, ctx)
    h = [f'<section id="{sid}" class="clip blk-quote" data-track-index="{sc.get("track",1)}" data-start="{sc["start"]}" data-duration="{round(sc["end"]-sc["start"],3)}"><div class="stage" id="{sid}-stage">']
    if sc.get("hero"): h.append(f'<div class="glow" id="{sid}-glow"></div>')
    if sc.get("label"): h.append(f'<div id="{sid}-label" class="block label kufi-r" style="font-size:{fit(sc["label"], "kufi-r", 36, 26)}px">{em(sc["label"])}</div>')
    h.append(f'<div id="{sid}-text" class="block {font}" style="font-size:{size}px">')
    k = 0
    for i, ln in enumerate(lines):
        if reveal == "words":
            ws = words(ln)
            h.append(f'<span class="qline" id="{sid}-ln{i+1}">' + "".join(f'<span class="w" id="{sid}-w{k+j+1}">{html.escape(w)}</span>' for j, w in enumerate(ws)) + "</span>")
            k += len(ws)
        else:
            h.append(f'<span class="qline" id="{sid}-ln{i+1}">{em(ln)}</span>')
    h.append("</div>")
    if sc.get("hero"): h.append(f'<div class="hero-line" id="{sid}-hline" style="width:60%"></div>')
    if sc.get("attribution"): h.append(f'<div id="{sid}-attr" class="block attr naskh" style="font-size:{fit(sc["attribution"], "naskh", 34, 26)}px">{em(sc["attribution"])}</div>')
    h.append("</div></section>")
    ctx.html.append("\n".join(h))
    js = [f"// ---- {sid} quote", f'sceneIn("#{sid} .stage", {sc["start"]});']
    if sc.get("label"): js.append(f'enter("#{sid}-label", {cues["label"]}, {{ dur: 0.6, y: 16, blur: 6 }});')
    if reveal == "words":
        for i, t in enumerate(cues["words"]):
            js.append(f'enter("#{sid}-w{i+1}", {t-0.28:.2f}, {{ dur: 0.75, y: 22, blur: 12, scale: 0.98 }});')
    else:
        for i, t in enumerate(cues["lines"]):
            js.append(f'enter("#{sid}-ln{i+1}", {t}, {{ dur: 0.8, y: 28, blur: 12, scale: 0.98 }});')
    if sc.get("hero"):
        js += [f'tl.set(["#{sid}-glow", "#{sid}-hline"], {{ opacity: 0 }}, 0);',
               f'tl.fromTo("#{sid}-hline", {{ opacity: 1, scaleX: 0 }}, {{ scaleX: 1, duration: 0.6, ease: "power2.out" }}, {cues["hero"]+0.4:.2f});',
               f'tl.fromTo("#{sid}-glow", {{ opacity: 0, scale: 0.7 }}, {{ opacity: 0.75, scale: 1, duration: 0.5, ease: "power2.out" }}, {cues["hero"]});',
               f'tl.to("#{sid}-glow", {{ opacity: 0.3, scale: 1.08, duration: 2.2, ease: "power1.out" }}, {cues["hero"]+0.5:.2f});',
               f'tl.fromTo("#{sid}-stage", {{ scale: 1 }}, {{ scale: 1.028, duration: 3.6, ease: "power1.out", transformOrigin: "50% 45%" }}, {cues["hero"]});']
    else:
        js.append(f'tl.fromTo("#{sid}-stage", {{ scale: 1 }}, {{ scale: 1.02, duration: {sc["end"]-sc["start"]:.1f}, ease: "none", transformOrigin: "50% 45%" }}, {sc["start"]});')
    if sc.get("attribution"): js.append(f'enter("#{sid}-attr", {cues["attribution"]}, {{ dur: 0.6, y: 14, blur: 5 }});')
    js.append(f'exit("#{sid} .stage > *:not(.glow)", {sc["end"]-0.45:.2f});' + (f' tl.to("#{sid}-glow", {{ opacity: 0, duration: 0.4 }}, {sc["end"]-0.45:.2f});' if sc.get("hero") else ""))
    ctx.js.append("\n".join(js))


def blk_list(sc, ctx):
    sid = sc["id"]
    items = sc.get("items") or []
    t = sc["start"] + 0.3; d = {}
    if sc.get("title"): d["title"] = round(t, 2); t += dwell(sc["title"]) + GAP
    it = []
    for x in items:
        it.append(round(t, 2)); t += dwell(x) + GAP
    d["items"] = it
    if sc.get("attribution"): d["attribution"] = round(t, 2)
    cues = _cues(sc, d)
    ctx.cues[sid] = cues
    _check_room(sc, {k: v for k, v in cues.items() if k != "items"}, ctx)
    fs = fit(max(items, key=nchars) if items else "", "naskh", 60, 38, width=700)
    h = [f'<section id="{sid}" class="clip blk-list" data-track-index="{sc.get("track",1)}" data-start="{sc["start"]}" data-duration="{round(sc["end"]-sc["start"],3)}"><div class="stage" id="{sid}-stage">']
    if sc.get("title"): h.append(f'<div id="{sid}-title" class="block title kufi" style="font-size:{fit(sc["title"], "kufi", 76, 48)}px">{em(sc["title"])}</div>')
    for i, x in enumerate(items):
        num = f'<span class="num">{ar_digits(i+1)}</span>' if sc.get("numbered", True) else ""
        h.append(f'<div class="item naskh" id="{sid}-it{i+1}" style="font-size:{fs}px;{"margin-top:40px" if i==0 else ""}">{num}<span>{em(x)}</span></div>')
    if sc.get("attribution"): h.append(f'<div id="{sid}-attr" class="block attr naskh" style="font-size:{fit(sc["attribution"], "naskh", 34, 26)}px">{em(sc["attribution"])}</div>')
    h.append("</div></section>")
    ctx.html.append("\n".join(h))
    js = [f"// ---- {sid} list", f'sceneIn("#{sid} .stage", {sc["start"]});']
    if sc.get("title"): js.append(f'enter("#{sid}-title", {cues["title"]}, {{ dur: 0.7, y: 26 }});')
    for i, ct in enumerate(cues["items"]):
        js.append(f'tl.fromTo("#{sid}-it{i+1}", {{ opacity: 0, x: 60, filter: "blur(6px)" }}, {{ opacity: 1, x: 0, filter: "blur(0px)", duration: 0.65 }}, {ct});')
    if sc.get("attribution"): js.append(f'enter("#{sid}-attr", {cues["attribution"]}, {{ dur: 0.6, y: 14, blur: 5 }});')
    js.append(f'tl.fromTo("#{sid}-stage", {{ scale: 1 }}, {{ scale: 1.02, duration: {sc["end"]-sc["start"]:.1f}, ease: "none", transformOrigin: "50% 45%" }}, {sc["start"]});')
    js.append(f'exit("#{sid} .stage > *", {sc["end"]-0.45:.2f});')
    ctx.js.append("\n".join(js))


def blk_title(sc, ctx):
    sid = sc["id"]
    d = _seq(sc, ["kicker", "title", "sub"], start_pad=0.25)
    cues = _cues(sc, d)
    ctx.cues[sid] = cues
    h = [f'<section id="{sid}" class="clip blk-title" data-track-index="{sc.get("track",1)}" data-start="{sc["start"]}" data-duration="{round(sc["end"]-sc["start"],3)}"><div class="stage">']
    if sc.get("kicker"): h.append(f'<div id="{sid}-k" class="block kicker kufi-r" style="font-size:{fit(sc["kicker"], "kufi-r", 40, 28)}px">{em(sc["kicker"])}</div>')
    h.append(f'<div id="{sid}-t" class="block title kufi" style="font-size:{fit(sc.get("title",""), "kufi", 110, 60)}px">{em(sc.get("title",""))}</div><div class="rule" id="{sid}-rule"></div>')
    if sc.get("sub"): h.append(f'<div id="{sid}-s" class="block sub naskh" style="font-size:{fit(sc["sub"], "naskh", 46, 30)}px">{em(sc["sub"])}</div>')
    h.append("</div></section>")
    ctx.html.append("\n".join(h))
    js = [f"// ---- {sid} title", f'sceneIn("#{sid} .stage", {sc["start"]});']
    if sc.get("kicker"): js.append(f'enter("#{sid}-k", {cues["kicker"]}, {{ dur: 0.6, y: 16, blur: 6 }});')
    js.append(f'enter("#{sid}-t", {cues["title"]}, {{ dur: 0.85, y: 36, blur: 14, scale: 0.95 }}); tl.fromTo("#{sid}-rule", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.6, ease: "power2.out" }}, {cues["title"]+0.5:.2f});')
    if sc.get("sub"): js.append(f'enter("#{sid}-s", {cues["sub"]}, {{ dur: 0.6, y: 18, blur: 6 }});')
    js.append(f'exit("#{sid} .stage > *", {sc["end"]-0.45:.2f});')
    ctx.js.append("\n".join(js))


def _seq_texts(scene, pairs, start_pad=0.3, pace=READ_PROSE, floor=PROSE_MIN):
    """Like _seq, but for text that is not a scene field (split sentences, list items, events).
    pairs = [(cue_name, text_or_list), …] — the pace is slower because running prose is read, not glanced."""
    t = scene["start"] + start_pad
    out = {}
    for k, txt in pairs:
        if not txt:
            continue
        out[k] = round(t, 2)
        lines = txt if isinstance(txt, list) else [txt]
        t += max(floor, pace * sum(len(words(x)) for x in lines) + 0.55) + GAP
    return out


def split_prose(text, max_words=18):
    """Authored prose → readable chunks, one chunk per reveal.

    A list is taken as authored (one entry per screen line). A string is split at sentence ends
    (. ؟ !), and a sentence longer than `max_words` is split at its last «،» / «؛» before the limit.
    A chunk carrying <em> is never cut (the hinge word stays whole)."""
    if isinstance(text, list):
        return [str(x).strip() for x in text if str(x).strip()]
    t = str(text or "").strip()
    if not t:
        return []
    out = []
    for p in re.split(r"(?<=[.؟!])\s+", t):
        p = p.strip()
        if not p:
            continue
        w = words(p)
        if len(w) <= max_words or "<em>" in p:
            out.append(p)
            continue
        cut = None
        for i in range(max_words, 5, -1):
            if i < len(w) and w[i - 1].endswith(("،", "؛", ":")):
                cut = i
                break
        cut = cut or max_words
        out.append(" ".join(w[:cut]))
        rest = " ".join(w[cut:])
        if rest:
            out.extend(split_prose(rest, max_words))
    return out


def _item(x):
    """steps / timeline items: a string, or {head|when, text}."""
    if isinstance(x, dict):
        return {"head": str(x.get("head") or x.get("when") or "").strip(),
                "text": str(x.get("text") or "").strip()}
    return {"head": "", "text": str(x or "").strip()}


def _src_line(sid, sc, size=(30, 24)):
    if not sc.get("source"):
        return "", ""
    return (f'<div id="{sid}-src" class="block src naskh" style="font-size:{fit(sc["source"], "naskh", size[0], size[1])}px">'
            f'{em(sc["source"])}</div>', "source")


def _prose_html(sid, chunks, size, cls="prose naskh"):
    return (f'<div class="block {cls}" style="font-size:{size}px">'
            + "".join(f'<span class="pline" id="{sid}-p{i+1}">{em(c)}</span>' for i, c in enumerate(chunks))
            + "</div>")


def _enter_prose(sid, cues, n, dur=0.7, y=24):
    return [f'enter("#{sid}-p{i+1}", {cues[f"p{i+1}"]}, {{ dur: {dur}, y: {y}, blur: 8 }});' for i in range(n)]


def blk_paragraph(sc, ctx):
    """A prose passage (up to ~60 words) revealed sentence by sentence — the شرح layer on screen.

    `kicker` (optional label) · `text` (string or list) · `source` (optional). `font` (naskh default),
    `size`, `max_lines` (8), `max_words` (18 words per chunk)."""
    sid = sc["id"]
    chunks = split_prose(sc.get("text"), int(sc.get("max_words") or 18))
    if not chunks:
        raise SystemExit(f"[{sid}] paragraph needs text")
    if len(chunks) > 7:
        ctx.warn.append(f"[{sid}] {len(chunks)} sentences in one paragraph — split the scene or cut to five")
    pairs = ([("kicker", sc.get("kicker"))] if sc.get("kicker") else []) \
        + [(f"p{i+1}", c) for i, c in enumerate(chunks)] \
        + ([("source", sc.get("source"))] if sc.get("source") else [])
    cues = _cues(sc, _seq_texts(sc, pairs))
    ctx.cues[sid] = cues
    _check_room(sc, cues, ctx)
    font = sc.get("font", "naskh")
    size = sc.get("size") or fit_wrapped([words(c) for c in chunks], font, 56, 36, width=760,
                                         max_lines=int(sc.get("max_lines") or 8), max_height=1020, line_height=1.85)[0]
    h = [f'<section id="{sid}" class="clip blk-paragraph" data-track-index="{sc.get("track",1)}" data-start="{sc["start"]}" data-duration="{round(sc["end"]-sc["start"],3)}"><div class="stage" id="{sid}-stage">']
    if sc.get("kicker"):
        h.append(f'<div id="{sid}-k" class="block kick kicker kufi-r" style="font-size:{fit(sc["kicker"], "kufi-r", 38, 26)}px">{em(sc["kicker"])}</div>')
    h.append(_prose_html(sid, chunks, size, f"prose {font}"))
    src, _ = _src_line(sid, sc, (32, 26))
    if src:
        h.append(src)
    h.append("</div></section>")
    ctx.html.append("\n".join(h))
    js = [f"// ---- {sid} paragraph", f'sceneIn("#{sid} .stage", {sc["start"]});']
    if sc.get("kicker"):
        js.append(f'enter("#{sid}-k", {cues["kicker"]}, {{ dur: 0.6, y: 16, blur: 6 }});')
    js += _enter_prose(sid, cues, len(chunks), dur=0.75, y=26)
    if sc.get("source"):
        js.append(f'enter("#{sid}-src", {cues["source"]}, {{ dur: 0.55, y: 12, blur: 4 }});')
    js.append(f'tl.fromTo("#{sid}-stage", {{ scale: 1 }}, {{ scale: 1.015, duration: {sc["end"]-sc["start"]:.1f}, ease: "none", transformOrigin: "50% 45%" }}, {sc["start"]});')
    js.append(f'exit("#{sid} .stage > *", {sc["end"]-0.45:.2f});')
    ctx.js.append("\n".join(js))


def blk_definition(sc, ctx):
    """حدّ المصطلح: label · term · body (prose) · note · source.

    Use it when the whole reel turns on what a word means. The term is the only Kufi display line;
    the body is Naskh prose, right-aligned, so it reads like a margin note, not an ad."""
    sid = sc["id"]
    term = sc.get("term") or ""
    if not term:
        raise SystemExit(f"[{sid}] definition needs term")
    body = split_prose(sc.get("body"), int(sc.get("max_words") or 20))
    if not body:
        raise SystemExit(f"[{sid}] definition needs body")
    label = sc.get("label", "التَّعْرِيف")
    pairs = ([("label", label)] if label else []) + [("term", term)] \
        + [(f"p{i+1}", c) for i, c in enumerate(body)] \
        + ([("note", sc.get("note"))] if sc.get("note") else []) \
        + ([("source", sc.get("source"))] if sc.get("source") else [])
    cues = _cues(sc, _seq_texts(sc, pairs))
    ctx.cues[sid] = cues
    _check_room(sc, cues, ctx)
    f_term = fit(term, "kufi", 104, 56)
    f_body = fit_wrapped([words(c) for c in body], "naskh", 48, 32, width=760, max_lines=6, max_height=700, line_height=1.85)[0]
    h = [f'<section id="{sid}" class="clip blk-definition" data-track-index="{sc.get("track",1)}" data-start="{sc["start"]}" data-duration="{round(sc["end"]-sc["start"],3)}"><div class="stage" id="{sid}-stage">']
    if label:
        h.append(f'<div id="{sid}-l" class="block kick kicker kufi-r" style="font-size:{fit(label, "kufi-r", 38, 26)}px">{em(label)}</div>')
    h.append(f'<div class="block term-wrap"><div id="{sid}-t" class="term kufi" style="font-size:{f_term}px">{em(term)}</div><div id="{sid}-tl" class="term-line"></div></div>')
    h.append(_prose_html(sid, body, f_body, "body prose naskh"))
    if sc.get("note"):
        h.append(f'<div id="{sid}-n" class="block note naskh" style="font-size:{fit(sc["note"], "naskh", 36, 28)}px">{em(sc["note"])}</div>')
    src, _ = _src_line(sid, sc, (30, 24))
    if src:
        h.append(src)
    h.append("</div></section>")
    ctx.html.append("\n".join(h))
    js = [f"// ---- {sid} definition", f'sceneIn("#{sid} .stage", {sc["start"]});']
    if label:
        js.append(f'enter("#{sid}-l", {cues["label"]}, {{ dur: 0.6, y: 14, blur: 5 }});')
    js.append(f'enter("#{sid}-t", {cues["term"]}, {{ dur: 0.85, y: 34, blur: 14, scale: 0.95 }});')
    js.append(f'tl.fromTo("#{sid}-tl", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.6, ease: "power2.out" }}, {cues["term"]+0.45:.2f});')
    js += _enter_prose(sid, cues, len(body), dur=0.75, y=24)
    if sc.get("note"):
        js.append(f'enter("#{sid}-n", {cues["note"]}, {{ dur: 0.55, y: 12, blur: 4 }});')
    if sc.get("source"):
        js.append(f'enter("#{sid}-src", {cues["source"]}, {{ dur: 0.55, y: 12, blur: 4 }});')
    js.append(f'exit("#{sid} .stage > *", {sc["end"]-0.45:.2f});')
    ctx.js.append("\n".join(js))


def blk_steps(sc, ctx):
    """خطوات مرقّمة: title · items (≤ 4, string or {head, text}) · source.

    For a text that gives a procedure or an ordered set of conditions. The rail and the Arabic-Indic
    numbers carry the order; the words stay short (a step is an action, not a paragraph)."""
    sid = sc["id"]
    items = [_item(x) for x in (sc.get("items") or [])]
    items = [x for x in items if x["text"] or x["head"]]
    if not items:
        raise SystemExit(f"[{sid}] steps needs items")
    if len(items) > 4:
        ctx.warn.append(f"[{sid}] {len(items)} steps — four is the ceiling for one screen")
    pairs = ([("title", sc.get("title"))] if sc.get("title") else []) \
        + [(f"i{i+1}", x["head"] + " " + x["text"]) for i, x in enumerate(items)] \
        + ([("source", sc.get("source"))] if sc.get("source") else [])
    cues = _cues(sc, _seq_texts(sc, pairs, pace=0.32, floor=2.0))
    ctx.cues[sid] = cues
    _check_room(sc, cues, ctx)
    h = [f'<section id="{sid}" class="clip blk-steps" data-track-index="{sc.get("track",1)}" data-start="{sc["start"]}" data-duration="{round(sc["end"]-sc["start"],3)}"><div class="stage" id="{sid}-stage">']
    if sc.get("title"):
        h.append(f'<div id="{sid}-t" class="block title kufi" style="font-size:{fit(sc["title"], "kufi", 78, 48)}px">{em(sc["title"])}</div>')
    h.append(f'<div class="steps" id="{sid}-steps">')
    for i, x in enumerate(items):
        fh = fit(x["head"], "kufi", 46, 30, width=640) if x["head"] else 0
        ft = fit_wrapped([words(x["text"])], "naskh", 40, 28, width=640, max_lines=3, max_height=300, line_height=1.75)[0] if x["text"] else 0
        body = (f'<div class="shead kufi" style="font-size:{fh}px">{em(x["head"])}</div>' if x["head"] else "") \
            + (f'<div class="stext naskh" style="font-size:{ft}px">{em(x["text"])}</div>' if x["text"] else "")
        h.append(f'<div class="step" id="{sid}-i{i+1}"><div class="num">{ar_digits(i+1)}</div><div class="sbody">{body}</div></div>')
    h.append("</div>")
    src, _ = _src_line(sid, sc, (30, 24))
    if src:
        h.append(src)
    h.append("</div></section>")
    ctx.html.append("\n".join(h))
    js = [f"// ---- {sid} steps", f'sceneIn("#{sid} .stage", {sc["start"]});']
    if sc.get("title"):
        js.append(f'enter("#{sid}-t", {cues["title"]}, {{ dur: 0.7, y: 26 }});')
    for i in range(len(items)):
        js.append(f'enter("#{sid}-i{i+1}", {cues[f"i{i+1}"]}, {{ dur: 0.7, y: 26, blur: 8 }});')
        js.append(f'tl.fromTo("#{sid}-i{i+1} .num", {{ scale: 0.6, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.45, ease: "back.out(1.7)" }}, {cues[f"i{i+1}"]+0.05:.2f});')
    if sc.get("source"):
        js.append(f'enter("#{sid}-src", {cues["source"]}, {{ dur: 0.55, y: 12, blur: 4 }});')
    js.append(f'exit("#{sid} .stage > *", {sc["end"]-0.45:.2f});')
    ctx.js.append("\n".join(js))


def blk_timeline(sc, ctx):
    """خطّ زمني: title · events (≤ 4 × {when, text}) · source.

    For a biography, a chain of transmissions, or the history of a ruling. `when` is a date or an
    era written for the ear («سَنَة ١٤٨ هـ», «بَعْدَ وَفَاةِ النَّبِيّ»), never an ISO string."""
    sid = sc["id"]
    events = [_item(x) for x in (sc.get("events") or [])]
    events = [x for x in events if x["head"] or x["text"]]
    if not events:
        raise SystemExit(f"[{sid}] timeline needs events")
    if len(events) > 4:
        ctx.warn.append(f"[{sid}] {len(events)} events — four is the ceiling for one screen")
    pairs = ([("title", sc.get("title"))] if sc.get("title") else []) \
        + [(f"e{i+1}", x["head"] + " " + x["text"]) for i, x in enumerate(events)] \
        + ([("source", sc.get("source"))] if sc.get("source") else [])
    cues = _cues(sc, _seq_texts(sc, pairs, pace=0.32, floor=2.1))
    ctx.cues[sid] = cues
    _check_room(sc, cues, ctx)
    h = [f'<section id="{sid}" class="clip blk-timeline" data-track-index="{sc.get("track",1)}" data-start="{sc["start"]}" data-duration="{round(sc["end"]-sc["start"],3)}"><div class="stage" id="{sid}-stage">']
    if sc.get("title"):
        h.append(f'<div id="{sid}-t" class="block title kufi" style="font-size:{fit(sc["title"], "kufi", 74, 46)}px">{em(sc["title"])}</div>')
    h.append(f'<div class="items" id="{sid}-items">')
    for i, x in enumerate(events):
        fw = fit(x["head"], "kufi", 38, 26, width=210) if x["head"] else 0
        ft = fit_wrapped([words(x["text"])], "naskh", 40, 28, width=520, max_lines=3, max_height=280, line_height=1.75)[0] if x["text"] else 0
        h.append(f'<div class="ev" id="{sid}-e{i+1}">'
                 + (f'<div class="when kufi" style="font-size:{fw}px">{em(x["head"])}</div>' if x["head"] else "")
                 + (f'<div class="etext naskh" style="font-size:{ft}px">{em(x["text"])}</div>' if x["text"] else "")
                 + "</div>")
    h.append("</div>")
    src, _ = _src_line(sid, sc, (30, 24))
    if src:
        h.append(src)
    h.append("</div></section>")
    ctx.html.append("\n".join(h))
    js = [f"// ---- {sid} timeline", f'sceneIn("#{sid} .stage", {sc["start"]});']
    if sc.get("title"):
        js.append(f'enter("#{sid}-t", {cues["title"]}, {{ dur: 0.7, y: 24 }});')
    for i in range(len(events)):
        js.append(f'tl.fromTo("#{sid}-e{i+1}", {{ opacity: 0, x: 46, filter: "blur(6px)" }}, {{ opacity: 1, x: 0, filter: "blur(0px)", duration: 0.7, ease: "power3.out" }}, {cues[f"e{i+1}"]});')
    if sc.get("source"):
        js.append(f'enter("#{sid}-src", {cues["source"]}, {{ dur: 0.55, y: 12, blur: 4 }});')
    js.append(f'exit("#{sid} .stage > *", {sc["end"]-0.45:.2f});')
    ctx.js.append("\n".join(js))


def blk_compare(sc, ctx):
    """مقارنة هادئة: title · col_a {head, points[]} · col_b {head, points[]} · verdict · source.

    Two readings side by side without polemics: each column states what its holders say, the verdict
    says what the text settles. Never used to caricature a group — `col_a` is usually the common
    assumption, `col_b` the text."""
    sid = sc["id"]
    a, b = sc.get("col_a") or {}, sc.get("col_b") or {}
    if not a.get("head") or not b.get("head"):
        raise SystemExit(f"[{sid}] compare needs col_a.head and col_b.head")
    pa = [str(x).strip() for x in (a.get("points") or []) if str(x).strip()][:3]
    pb = [str(x).strip() for x in (b.get("points") or []) if str(x).strip()][:3]
    if not pa and not pb:
        raise SystemExit(f"[{sid}] compare needs at least one point")
    # a comparison is read in pairs: both heads, then a1 with b1, a2 with b2 … then the verdict
    d, t = {}, sc["start"] + 0.3
    if sc.get("title"):
        d["title"] = round(t, 2); t += max(1.9, 0.32 * len(words(sc["title"])) + 0.55) + GAP
    d["head_a"] = d["head_b"] = round(t, 2)
    t += 2.1
    for i in range(max(len(pa), len(pb))):
        if i < len(pa):
            d[f"a{i+1}"] = round(t, 2)
        if i < len(pb):
            d[f"b{i+1}"] = round(t, 2)
        pair = max([x for x in (pa[i] if i < len(pa) else "", pb[i] if i < len(pb) else "") if x] or [""], key=len)
        t += max(2.0, 0.32 * len(words(pair)) + 1.35) + GAP
    if sc.get("verdict"):
        d["verdict"] = round(t, 2); t += max(2.2, 0.30 * len(words(sc["verdict"])) + 0.55) + GAP
    if sc.get("source"):
        d["source"] = round(t, 2)
    cues = _cues(sc, d)
    ctx.cues[sid] = cues
    _check_room(sc, cues, ctx)
    f_pt = min(fit_wrapped([words(p)], "naskh", 36, 26, width=310, max_lines=3,
                           max_height=210, line_height=1.7)[0] for p in (pa + pb))
    h = [f'<section id="{sid}" class="clip blk-compare" data-track-index="{sc.get("track",1)}" data-start="{sc["start"]}" data-duration="{round(sc["end"]-sc["start"],3)}"><div class="stage" id="{sid}-stage">']
    if sc.get("title"):
        h.append(f'<div id="{sid}-t" class="block title kufi" style="font-size:{fit(sc["title"], "kufi", 70, 44)}px">{em(sc["title"])}</div>')
    h.append(f'<div class="grid" id="{sid}-grid">')
    for key, col, pts in (("a", a, pa), ("b", b, pb)):
        h.append(f'<div class="col" id="{sid}-col{key}">')
        h.append(f'<div class="chead kufi" id="{sid}-h{key}" style="font-size:{fit(col["head"], "kufi", 46, 30, width=310)}px">{em(col["head"])}</div>')
        for i, p in enumerate(pts):
            h.append(f'<div class="pt naskh" id="{sid}-{key}{i+1}" style="font-size:{f_pt}px">{em(p)}</div>')
        h.append("</div>")
    h.append("</div>")
    if sc.get("verdict"):
        h.append(f'<div id="{sid}-v" class="verdict naskh" style="font-size:{fit_wrapped([words(sc["verdict"])], "naskh", 44, 30, max_lines=3, max_height=300, line_height=1.75)[0]}px">{em(sc["verdict"])}</div>')
    src, _ = _src_line(sid, sc, (30, 24))
    if src:
        h.append(src)
    h.append("</div></section>")
    ctx.html.append("\n".join(h))
    js = [f"// ---- {sid} compare", f'sceneIn("#{sid} .stage", {sc["start"]});']
    if sc.get("title"):
        js.append(f'enter("#{sid}-t", {cues["title"]}, {{ dur: 0.7, y: 22 }});')
    js.append(f'tl.fromTo("#{sid}-ha", {{ opacity: 0, x: 40, filter: "blur(8px)" }}, {{ opacity: 1, x: 0, filter: "blur(0px)", duration: 0.7, ease: "power3.out" }}, {cues["head_a"]});')
    js.append(f'tl.fromTo("#{sid}-hb", {{ opacity: 0, x: -40, filter: "blur(8px)" }}, {{ opacity: 1, x: 0, filter: "blur(0px)", duration: 0.7, ease: "power3.out" }}, {cues["head_b"]});')
    for i in range(len(pa)):
        js.append(f'enter("#{sid}-a{i+1}", {cues[f"a{i+1}"]}, {{ dur: 0.6, y: 16, blur: 6 }});')
    for i in range(len(pb)):
        js.append(f'enter("#{sid}-b{i+1}", {cues[f"b{i+1}"]}, {{ dur: 0.6, y: 16, blur: 6 }});')
    if sc.get("verdict"):
        js.append(f'enter("#{sid}-v", {cues["verdict"]}, {{ dur: 0.8, y: 26, blur: 10 }});')
    if sc.get("source"):
        js.append(f'enter("#{sid}-src", {cues["source"]}, {{ dur: 0.55, y: 12, blur: 4 }});')
    js.append(f'exit("#{sid} .stage > *", {sc["end"]-0.45:.2f});')
    ctx.js.append("\n".join(js))


def blk_qa(sc, ctx):
    """سؤال طويل ← جواب مركّب: question · answer (prose, 2–5 sentences) · note · source.

    The `answer` block is one hero line; `qa` is the long form — a follower's question answered in
    full sentences, still without a narrator. Cue `hero` marks the first answer sentence for mix.py."""
    sid = sc["id"]
    q = sc.get("question") or ""
    if not q:
        raise SystemExit(f"[{sid}] qa needs question")
    ans = split_prose(sc.get("answer"), int(sc.get("max_words") or 18))
    if not ans:
        raise SystemExit(f"[{sid}] qa needs answer")
    lq = sc.get("label_q", "السُّؤَال")
    la = sc.get("label_a", "الجَوَاب")
    pairs = [("label_q", lq), ("q", q), ("label_a", la)] + [(f"p{i+1}", c) for i, c in enumerate(ans)] \
        + ([("note", sc.get("note"))] if sc.get("note") else []) \
        + ([("source", sc.get("source"))] if sc.get("source") else [])
    cues = _cues(sc, _seq_texts(sc, pairs))
    cues["hero"] = cues.get("p1", cues.get("label_a"))
    ctx.cues[sid] = cues
    _check_room(sc, {k: v for k, v in cues.items() if k != "hero"}, ctx)
    f_q = fit_wrapped([words(q)], "kufi", 64, 38, max_lines=3, max_height=360, line_height=1.55)[0]
    f_a = fit_wrapped([words(c) for c in ans], "naskh", 46, 30, width=780, max_lines=8, max_height=760, line_height=1.85)[0]
    h = [f'<section id="{sid}" class="clip blk-qa" data-track-index="{sc.get("track",1)}" data-start="{sc["start"]}" data-duration="{round(sc["end"]-sc["start"],3)}"><div class="stage" id="{sid}-stage">']
    if lq:
        h.append(f'<div id="{sid}-lq" class="block qlabel kufi-r" style="font-size:{fit(lq, "kufi-r", 34, 26)}px">{em(lq)}</div>')
    h.append(f'<div id="{sid}-q" class="block q kufi" style="font-size:{f_q}px">{em(q)}</div>')
    h.append(f'<div class="rule" id="{sid}-rule"></div>')
    if la:
        h.append(f'<div id="{sid}-la" class="block alabel kufi-r" style="font-size:{fit(la, "kufi-r", 34, 26)}px">{em(la)}</div>')
    h.append(_prose_html(sid, ans, f_a, "a prose naskh"))
    if sc.get("note"):
        h.append(f'<div id="{sid}-n" class="block note naskh" style="font-size:{fit(sc["note"], "naskh", 36, 26)}px">{em(sc["note"])}</div>')
    src, _ = _src_line(sid, sc, (30, 24))
    if src:
        h.append(src)
    h.append("</div></section>")
    ctx.html.append("\n".join(h))
    js = [f"// ---- {sid} qa", f'sceneIn("#{sid} .stage", {sc["start"]});']
    if lq:
        js.append(f'enter("#{sid}-lq", {cues["label_q"]}, {{ dur: 0.55, y: 12, blur: 4 }});')
    js.append(f'enter("#{sid}-q", {cues["q"]}, {{ dur: 0.8, y: 30, blur: 10 }});')
    js.append(f'tl.fromTo("#{sid}-rule", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.55, ease: "power2.out" }}, {cues["q"]+0.8:.2f});')
    if la:
        js.append(f'enter("#{sid}-la", {cues["label_a"]}, {{ dur: 0.55, y: 12, blur: 4 }});')
    js += _enter_prose(sid, cues, len(ans), dur=0.75, y=24)
    if sc.get("note"):
        js.append(f'enter("#{sid}-n", {cues["note"]}, {{ dur: 0.55, y: 12, blur: 4 }});')
    if sc.get("source"):
        js.append(f'enter("#{sid}-src", {cues["source"]}, {{ dur: 0.55, y: 12, blur: 4 }});')
    js.append(f'exit("#{sid} .stage > *", {sc["end"]-0.45:.2f});')
    ctx.js.append("\n".join(js))


BLOCKS = {"hook": blk_hook, "verse": blk_verse, "contrast": blk_contrast, "answer": blk_answer,
          "proof": blk_proof, "cta": blk_cta, "quote": blk_quote, "list": blk_list, "title": blk_title,
          "paragraph": blk_paragraph, "definition": blk_definition, "steps": blk_steps,
          "timeline": blk_timeline, "compare": blk_compare, "qa": blk_qa}
LONG_TEXT_BLOCKS = {"paragraph", "definition", "steps", "timeline", "compare", "qa"}



# ----------------------------------------------------------------------------- assemble
def build(spec, out, skill_root, theme: str | None = None):
    scenes = spec["scenes"]
    brand_cfg = load_brand(skill_root)
    theme_name, tokens = theme_of(spec, brand_cfg, theme)
    spec["theme"] = theme_name                     # so the summary and spec.resolved agree
    # ids, continuity
    for i, sc in enumerate(scenes):
        sc.setdefault("id", f"s{i+1}")
        if "end" not in sc and i + 1 < len(scenes):
            sc["end"] = scenes[i + 1]["start"]
    duration = float(spec.get("duration") or scenes[-1]["end"])
    scenes[-1].setdefault("end", duration)
    ctx = Ctx()
    ctx.brand = brand_cfg
    for i, sc in enumerate(scenes):
        sc.setdefault("track", 1 + (i % 2))
        if i and abs(sc["start"] - scenes[i - 1]["end"]) > 1e-6:
            ctx.warn.append(f"[{sc['id']}] starts at {sc['start']} but previous scene ends at {scenes[i-1]['end']}")
        if sc["type"] not in BLOCKS:
            raise SystemExit(f"unknown block type: {sc['type']}")
        BLOCKS[sc["type"]](sc, ctx)
        if i:
            ctx.cuts.append(sc["start"])
    wm = spec.get("watermark", {"show": True})
    wm_js = ""
    if wm.get("show", True) and len(scenes) >= 3:
        wm_from = wm.get("from", scenes[1]["start"] + 0.6)
        wm_until = wm.get("until", scenes[-1]["start"] - 0.5)
        wm_js = f'tl.fromTo("#wm", {{ opacity: 0 }}, {{ opacity: 0.9, duration: 0.6 }}, {wm_from}); tl.to("#wm", {{ opacity: 0, duration: 0.4 }}, {wm_until});'
    handle = (spec.get("brand") or {}).get("handle", "maalsadiqeen").lstrip("@")
    audio = spec.get("audio", {}).get("file", "mix.wav")
    title = html.escape(spec.get("title", spec.get("id", "reel")))
    page = f"""<!doctype html>
<html lang="ar" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <title>{title}</title>
    <script src="assets/gsap.min.js"></script>
    <style>{BASE_CSS}{theme_css(tokens)}    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{duration}" data-width="1080" data-height="1920">
{BG_HTML}
{chr(10).join(ctx.html)}
      <div id="wm"><img src="assets/img/logo-wm.png" alt="" /><span>{html.escape(handle)}</span></div>
      <audio id="mix" src="assets/audio/{audio}" data-start="0" data-duration="{duration}" data-volume="1"></audio>
    </div>
    <script>
      // generated by maalsadiqeen-reel/scripts/build_reel.py — edit the spec, not this file
{JS_HELPERS}
      function build() {{
        tl.fromTo("#light", {{ xPercent: -22 }}, {{ xPercent: 22, duration: {duration}, ease: "none" }}, 0);
        tl.fromTo("#arc", {{ y: 0 }}, {{ y: 8, duration: 7, ease: "sine.inOut", repeat: {int(duration//7)+1}, yoyo: true }}, 0);
        tl.fromTo("#sprig", {{ rotation: -2, transformOrigin: "20% 90%" }}, {{ rotation: 2, duration: 5.5, ease: "sine.inOut", repeat: {int(duration//5.5)+1}, yoyo: true }}, 0);
        drawPath("arc-path", 0.1, 1.6);
        tl.fromTo(["#arc-dia-l", "#arc-dia-r", "#arc-dia-t"], {{ opacity: 0, scale: 0.4, transformOrigin: "center" }}, {{ opacity: 1, scale: 1, duration: 0.5, stagger: 0.12 }}, 1.2);
{chr(10).join("        " + line for blk in ctx.js for line in blk.splitlines())}
        {wm_js}
        tl.set({{}}, {{}}, {duration});
      }}
      document.fonts.ready.then(() => {{
        build();
        window.__timelines["main"] = tl;
        tl.seek(0);
        if (window.__hfForceTimelineRebind) window.__hfForceTimelineRebind();
      }});
    </script>
  </body>
</html>
"""
    os.makedirs(os.path.join(out, "assets", "audio"), exist_ok=True)
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    # project scaffolding (copied once)
    a = os.path.join(skill_root, "assets")
    for src, dst in [(os.path.join(a, "hyperframes.json"), os.path.join(out, "hyperframes.json")),
                     (os.path.join(a, "gsap.min.js"), os.path.join(out, "assets", "gsap.min.js"))]:
        if not os.path.exists(dst):
            shutil.copy(src, dst)
    for sub, dst in [("fonts", "fonts"), ("brand", "img")]:
        d = os.path.join(out, "assets", dst)
        if not os.path.isdir(d):
            shutil.copytree(os.path.join(a, sub), d)
    resolved = {"id": spec.get("id"), "duration": duration, "cuts": ctx.cuts, "theme": theme_name,
                "scenes": [{"id": sc["id"], "type": sc["type"], "start": sc["start"], "end": sc["end"], "hero": bool(sc.get("hero")),
                            "cues": ctx.cues.get(sc["id"], {})} for sc in scenes],
                "audio": spec.get("audio", {})}
    with open(os.path.join(out, "spec.resolved.json"), "w", encoding="utf-8") as f:
        json.dump(resolved, f, ensure_ascii=False, indent=1)
    return ctx, duration


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec"); ap.add_argument("--out", required=True); ap.add_argument("--skill-root", default=SKILL_ROOT)
    ap.add_argument("--theme", help="theme name from config/brand.json (main · mourning); beats spec.theme")
    a = ap.parse_args()
    with open(a.spec, encoding="utf-8") as f:
        spec = json.load(f)
    if a.theme:
        spec["theme"] = a.theme
    ctx, duration = build(spec, a.out, a.skill_root)
    print(f"built {a.out}/index.html — {len(spec['scenes'])} scenes, {duration}s · theme {spec.get('theme') or 'main'}")
    for w in ctx.warn:
        print("WARN", w)
    print("cues ->", os.path.join(a.out, "spec.resolved.json"))


if __name__ == "__main__":
    main()
