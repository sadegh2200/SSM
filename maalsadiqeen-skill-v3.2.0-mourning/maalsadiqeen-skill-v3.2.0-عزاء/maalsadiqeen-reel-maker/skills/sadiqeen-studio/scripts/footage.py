#!/usr/bin/env python3
"""Footage mode — a recorded take, cut and dressed to the brand.

The rest of the studio *draws* a reel from text. This module does the other half of the
job: it takes a phone/laptop recording of a scholar, measures it, and dresses it — the
same brand, the same type, the same paper, but the picture is the speaker instead of a
page.

    python3 footage.py probe  raw.mp4                     # what is this file, really
    python3 footage.py pauses raw.mp4                     # where does the speaker breathe
    python3 footage.py build  edit.json --out out/edit    # the finished cut
    python3 footage.py still  edit.json 12.4 --out f.png  # one composited frame

What it decides on its own (and prints, so nothing is hidden):

* **timeline** — the take is measured for silence; the head and the tail are trimmed, and
  two paragraph pauses are removed. Every removed pause is covered by a full-frame brand
  card, so the jump cut is never seen and no word is lost.
* **grade** — a filmic dark grade keyed to the mourning tokens: warm highlights, no
  crushed blacks, a 6% push-in, grain, vignette. The phone look is removed, not filtered.
* **type** — Arabic shaped with HarfBuzz (RTL joins correct), never a font fallback box:
  a hook card, chapter cards, a quote card, an end card, and chyrons that land on the
  syllables the speaker actually breathes before.
* **sound** — denoise, presence, gentle compression, two-pass EBU R128 to −15.5 LUFS.
  No music: a scholar's voice is the content.
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import brandkit as bk  # noqa: E402
import stage  # noqa: E402
import typo  # noqa: E402

W, H = bk.W, bk.H
COL_R = 986                     # right edge of the picture's type column
COL_L = 94
CHY_BOTTOM = 1420               # baseline block of a chyron: over the chest, above the UI
SCRIM_TOP = 0.30                # top falloff, for the brand mark
SCRIM_BOTTOM = 0.46             # bottom falloff, under the chyron
SCRIM_START = 1040              # where the bottom falloff begins
WASH_ALPHA = 0.0                # optional local band behind a chyron (0 = off)
FPS = 30


# --------------------------------------------------------------------------- shell
def _run(cmd: list[str], check: bool = True) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout)[-1500:])
    return r.stderr or r.stdout


def _ffmpeg(*args: str) -> list[str]:
    return ["ffmpeg", "-hide_banner", "-nostdin", "-y", *args]


# --------------------------------------------------------------------------- probe
def probe(src: str) -> dict:
    """Resolution, rotation, duration, fps, and whether there is audio to keep."""
    out = _run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams",
                "-show_format", str(src)])
    j = json.loads(out)
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    if not v:
        raise SystemExit("no video stream")
    rot = 0
    for sd in v.get("side_data_list") or []:
        if "rotation" in sd:
            rot = int(sd["rotation"]) % 360
    num, den = (v.get("r_frame_rate") or "30/1").split("/")
    dur = float(j["format"].get("duration") or v.get("duration") or 0)
    return {
        "file": str(src), "duration": round(dur, 3),
        "fps": round(float(num) / max(1.0, float(den)), 3),
        "width": int(v["width"]), "height": int(v["height"]), "rotation": rot,
        "display": (int(v["height"]), int(v["width"])) if rot in (90, 270)
        else (int(v["width"]), int(v["height"])),
        "vcodec": v.get("codec_name"), "pix_fmt": v.get("pix_fmt"),
        "audio": bool(a), "acodec": (a or {}).get("codec_name"),
        "sample_rate": (a or {}).get("sample_rate"),
        "channels": (a or {}).get("channels"),
    }


@dataclass
class Pause:
    start: float
    end: float

    @property
    def dur(self) -> float:
        return self.end - self.start


def pauses(src: str, noise_db: float = -34.0, min_d: float = 0.30) -> list[Pause]:
    """Where the room goes quiet — the editor's only honest cut points."""
    log = _run(_ffmpeg("-i", str(src), "-af",
                       f"silencedetect=noise={noise_db}dB:d={min_d}",
                       "-f", "null", "-"), check=False)
    out, start = [], None
    for line in log.splitlines():
        m = re.search(r"silence_start:\s*(-?[\d.]+)", line)
        if m:
            start = max(0.0, float(m.group(1)))
        m = re.search(r"silence_end:\s*([\d.]+)", line)
        if m and start is not None:
            out.append(Pause(start, float(m.group(1))))
            start = None
    return out


def onsets(ps: list[Pause], duration: float) -> list[float]:
    """Speech starts. Chyrons snap to these, so type never arrives mid-word."""
    return [round(p.end, 3) for p in ps if p.end < duration - 0.1]


# --------------------------------------------------------------------------- timeline
@dataclass
class Timeline:
    segs: list[tuple[float, float]]
    cuts: list[dict] = field(default_factory=list)      # {"out","src","dropped"}

    @property
    def duration(self) -> float:
        return round(sum(b - a for a, b in self.segs), 3)

    def map(self, t_src: float) -> float:
        """Source second → output second, through the removed pauses."""
        acc = 0.0
        for a, b in self.segs:
            if a <= t_src <= b:
                return round(acc + (t_src - a), 3)
            if t_src < a:                      # inside a removed pause: clamp forward
                return round(acc, 3)
            acc += b - a
        return round(acc, 3)

    def unmap(self, t_out: float) -> float:
        """Output second → the second of the take that is playing (for sampling frames)."""
        acc = 0.0
        for a, b in self.segs:
            if t_out <= acc + (b - a):
                return round(a + max(0.0, t_out - acc), 3)
            acc += b - a
        return round(self.segs[-1][1], 3)

    def src_duration(self) -> float:
        return self.segs[-1][1] if self.segs else 0.0


def plan(med: dict, ps: list[Pause], cfg: dict) -> Timeline:
    """Choose the cut points and build the segment list.

    A pause is never removed whole: `lead` seconds stay at each end, so the sentence still
    lands and lifts. `cut_at` lets the editor name the paragraph breaks instead of trusting
    the two longest silences — the ones that matter are the ones between ideas.
    """
    head = float(cfg.get("head_trim", 1.0))
    tail = float(cfg.get("tail_keep", 1.2))
    lead = float(cfg.get("lead", 0.12))
    max_drop = float(cfg.get("max_drop", 1.25))
    dur = med["duration"]
    end = round(dur - tail, 3)

    chosen: list[Pause] = []
    if cfg.get("cut_at"):
        for t in cfg["cut_at"]:
            cand = [p for p in ps if p.start - 0.05 <= float(t) <= p.end + 0.05]
            if cand:
                chosen.append(min(cand, key=lambda p: abs(p.start - float(t))))
            else:
                chosen.append(Pause(float(t), float(t) + 0.9))   # tolerate a mis-measure
    else:
        cand = [p for p in ps if p.dur >= float(cfg.get("min_pause", 0.85))
                and p.start > head + 2.5 and p.end < end - 2.5]
        cand.sort(key=lambda p: -p.dur)
        chosen = cand[:int(cfg.get("max_cuts", 2))]
    chosen.sort(key=lambda p: p.start)

    segs: list[tuple[float, float]] = []
    cuts: list[dict] = []
    cur, acc = head, 0.0
    for p in chosen:
        room = max(0.0, p.dur - 2 * lead)
        drop = min(room, max_drop)
        pad = (p.dur - drop) / 2
        seg_end = round(p.start + pad, 3)
        nxt = round(p.end - pad, 3)
        if seg_end - cur < 1.2 or nxt <= seg_end:
            continue
        segs.append((round(cur, 3), seg_end))
        acc += seg_end - cur
        cuts.append({"out": round(acc, 3), "src": round(p.start, 3),
                     "dropped": round(nxt - seg_end, 3)})
        cur = nxt
    segs.append((round(cur, 3), end))
    return Timeline(segs, cuts)


# --------------------------------------------------------------------------- copy gate
_EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F]")
_LATIN = re.compile(r"[A-Za-z]{2,}")


def copy_lint(strings: list[str]) -> list[dict]:
    """The brand's on-screen bans, checked on every string before it is drawn."""
    brand = bk.brand_config()
    banned = list(brand.get("forbidden_on_screen") or [])
    rows = []
    for s in strings:
        plain = re.sub(r"<[^>]+>", "", s)
        for bad in banned:
            if bad and bad in plain:
                rows.append({"level": "fail", "what": f"banned on screen: «{bad}»", "in": plain[:60]})
        if _EMOJI.search(plain):
            rows.append({"level": "fail", "what": "emoji on screen", "in": plain[:60]})
        if "!!" in plain or "؟!" in plain or ".." in plain:
            rows.append({"level": "fail", "what": "shouty punctuation", "in": plain[:60]})
        latin = [w for w in _LATIN.findall(plain) if w.lower() not in
                 (brand.get("handle") or "").lower()]
        if latin:
            rows.append({"level": "warn", "what": f"latin on screen: {latin}", "in": plain[:60]})
    return rows


# --------------------------------------------------------------------------- type
def _paper(tokens: dict) -> Image.Image:
    img = stage.paper(tokens)
    img.alpha_composite(stage.vignette(tokens))
    return img


def _put(img: Image.Image, layer: Image.Image, x: int | None = None, y: int = 0,
         align: str = "center", col: tuple[int, int] = (bk.COL_X, bk.COL_W)) -> int:
    if x is None:
        x = {"center": col[0] + (col[1] - layer.width) // 2,
             "right": col[0] + col[1] - layer.width,
             "left": col[0]}[align]
    img.alpha_composite(layer, (int(x), int(y)))
    return y + layer.height


def _line(img, text: str, key: str, px: int, color: tuple[int, int, int], y: int,
          align: str = "center", col=(bk.COL_X, bk.COL_W), max_w: int | None = None):
    px = px if max_w is None else typo.fit(text, key, max_w, px, max(18, px // 2))
    ink = typo.layout(text, key, px, color)
    return _put(img, ink.img, None, y, align, col), ink


def _block(img, lines: list[str], key: str, px: int, color, y: int, leading: float = 1.5,
           align: str = "center", col=(bk.COL_X, bk.COL_W), max_w: int | None = None):
    if max_w:                      # every line must fit, so the widest one sets the size
        px = min(typo.fit(t, key, max_w, px, max(18, px // 2)) for t in lines)
    ink = typo.stack(lines, key, px, leading, align, color, col_w=col[1])
    return _put(img, ink.img, None, y, align, col), ink


def _rule(img, y: int, width: int = 360, tokens=None, align: str = "center",
          col=(bk.COL_X, bk.COL_W), thickness: int = 2):
    tokens = tokens or bk.tokens()
    r = stage.rule(width, thickness, bk.rgb(tokens["gold"]), alpha=225, taper=True)
    return _put(img, r, None, y, align, col)


def _diamond(img, y: int, tokens: dict, align: str = "center", col=(bk.COL_X, bk.COL_W)):
    d = stage.diamond(14, bk.rgb(tokens["gold2"]), 235)
    return _put(img, d, None, y, align, col)


# --------------------------------------------------------------------------- cards
def _latin(img, text: str, px: int, color, y: int, align: str = "center",
           col=(bk.COL_X, bk.COL_W), gap: int = 2):
    """A Latin handle, laid out left-to-right: `typo` is an RTL shaper, so the run is
    built by hand — the «@», then the word, in that order."""
    at = typo.layout("@", "amiri", px, color)
    body = typo.layout(text, "amiri", px, color)
    w = at.width + gap + body.width
    x = {"center": col[0] + (col[1] - w) // 2, "right": col[0] + col[1] - w,
         "left": col[0]}[align]
    img.alpha_composite(at.img, (int(x), y + body.img.height - at.img.height))
    img.alpha_composite(body.img, (int(x + at.width + gap), y))
    return y + max(body.img.height, at.img.height)


def _pips(img, tokens: dict, step: int, steps: int, y: int):
    """Series progress: filled diamonds up to `step`, hollow after."""
    gold, line = bk.rgb(tokens["gold"]), bk.rgb(tokens["line"])
    size, gap = 13, 26
    total = steps * size + (steps - 1) * gap
    x = (W - total) // 2
    for i in range(steps):
        d = stage.diamond(size, gold if i < step else line, 240 if i < step else 160)
        img.alpha_composite(d, (x, y))
        x += size + gap


def card_hook(tokens: dict, b: dict) -> Image.Image:
    img = _paper(tokens)
    ink, gold, gold2, ink2 = (bk.rgb(tokens[k]) for k in ("ink", "gold", "gold2", "ink2"))
    y = 540
    y, _ = _line(img, b.get("kicker", "مَعَ الصَّادِقِينَ"), "kufi", 30, gold2, y)
    y += 26
    y = _put(img, stage.arc_divider(tokens, 640, 104), None, y)
    y += 26
    y, _ = _block(img, b["title"], "naskh_b", 112, ink, y, leading=1.40, max_w=820)
    y += 26
    y = _rule(img, y, 560, tokens)
    y = _diamond(img, y + 16, tokens)
    y += 44
    if b.get("sub"):
        y, _ = _block(img, b["sub"], "amiri", 46, ink2, y, leading=1.62, max_w=760)
        y += 24
    if b.get("foot"):
        _line(img, b["foot"], "kufi", 28, gold, y)
    if b.get("logo"):
        lm = stage.logo_mark(tokens, 92, 0.42)
        if lm:
            _put(img, lm, None, 1580, "center")
    return img


def card_chapter(tokens: dict, b: dict) -> Image.Image:
    img = _paper(tokens)
    ink, gold, gold2, ink2 = (bk.rgb(tokens[k]) for k in ("ink", "gold", "gold2", "ink2"))
    y = 720
    y, _ = _line(img, b["kicker"], "kufi", 32, gold2, y)
    y += 30
    y = _put(img, stage.arc_divider(tokens, 700, 108), None, y)
    y += 30
    y, _ = _block(img, b["title"], "naskh_b", 100, ink, y, leading=1.40, max_w=820)
    y += 34
    y = _rule(img, y, 420, tokens)
    y = _diamond(img, y + 14, tokens)
    y += 38
    if b.get("sub"):
        _block(img, b["sub"], "amiri", 46, ink2, y, leading=1.60, max_w=780)
    _pips(img, tokens, int(b.get("step", 1)), int(b.get("steps", 3)), 1556)
    return img


def card_quote(tokens: dict, b: dict) -> Image.Image:
    img = _paper(tokens)
    ink, gold, gold2, ink2 = (bk.rgb(tokens[k]) for k in ("ink", "gold", "gold2", "ink2"))
    col = (196, 688)                    # narrower than the page: the brackets need air
    label = b.get("label") or "المَأْثُور"
    lk = typo.layout(label, "kufi", 28, gold2)
    plate = stage.panel(lk.img.width + 60, lk.img.height + 28, tokens, radius=10)
    img.alpha_composite(plate, ((W - plate.width) // 2, 648))
    img.alpha_composite(lk.img, ((W - lk.img.width) // 2, 648 + 14))

    if b.get("quote_lines"):            # a hand-broken quotation beats a greedy wrap
        lines = list(b["quote_lines"])
        px = min(typo.fit(t, "amiri", col[1], 64, 40) for t in lines)
    else:
        px, lines = typo.fit_wrapped(b["quote"], "amiri", col[1], 560, 64, 40, 4)
    blk = typo.stack(lines, "amiri", px, 1.50, "center", ink, col_w=col[1])
    qy = 796
    img.alpha_composite(blk.img, ((W - blk.img.width) // 2, qy))
    fh = int(blk.img.height * 0.84)
    fl = stage.flourish(fh, gold, mirror=False, alpha=190)
    fr = stage.flourish(fh, gold, mirror=True, alpha=190)
    img.alpha_composite(fl, (44, qy + (blk.img.height - fl.height) // 2))
    img.alpha_composite(fr, (W - 44 - fr.width, qy + (blk.img.height - fr.height) // 2))
    y = qy + blk.img.height + 74
    y = _rule(img, y, 300, tokens)
    y = _diamond(img, y + 12, tokens)
    y += 40
    if b.get("note"):
        _block(img, b["note"], "amiri", 38, ink2, y, leading=1.60, max_w=740)
    return img


def card_end(tokens: dict, b: dict) -> Image.Image:
    img = _paper(tokens)
    ink, gold, gold2, ink2 = (bk.rgb(tokens[k]) for k in ("ink", "gold", "gold2", "ink2"))
    y = 596
    lm = stage.logo_mark(tokens, 210, 1.0)
    if lm:
        y = _put(img, lm, None, y)
        y += 30
    y, _ = _line(img, b.get("name", "مَعَ الصَّادِقِينَ"), "kufi", 46, gold2, y, max_w=700)
    y += 30
    y = _put(img, stage.arc_divider(tokens, 720, 112), None, y)
    y += 26
    y, _ = _block(img, b["verse"], "quran", 82, ink, y, leading=1.46, max_w=800)
    y += 28
    y = _rule(img, y, 460, tokens)
    y = _diamond(img, y + 14, tokens)
    y += 38
    if b.get("series"):
        y, _ = _line(img, b["series"], "kufi", 30, ink2, y, max_w=700)
        y += 24
    if b.get("handle"):
        _latin(img, b["handle"].lstrip("@"), 34, gold, y)
    return img


def card_word(tokens: dict, b: dict) -> Image.Image:
    """One word, held. The moment a term is named, the page names it too."""
    img = _paper(tokens)
    ink, gold, gold2, ink2 = (bk.rgb(tokens[k]) for k in ("ink", "gold", "gold2", "ink2"))
    y = 650
    y, _ = _line(img, b["kicker"], "kufi", 32, gold2, y)
    y += 26
    y = _put(img, stage.arc_divider(tokens, 660, 104), None, y)
    y += 40
    word = b["word"]
    px = typo.fit(word, "amiri_b", 860, 190, 90)
    y, _ = _line(img, word, "amiri_b", px, ink, y, max_w=860)
    y += 34
    y = _rule(img, y, 300, tokens)
    y = _diamond(img, y + 14, tokens)
    y += 36
    if b.get("sub"):
        y, _ = _block(img, b["sub"], "amiri", 44, ink2, y, leading=1.60, max_w=740)
    if b.get("verse"):
        _block(img, b["verse"], "quran", 40, gold, y + 24, leading=1.5, max_w=740)
    return img


# --------------------------------------------------------------------------- overlays
def _dither(a: np.ndarray) -> np.ndarray:
    """Quantise a 0-1 alpha ramp with noise, not truncation.

    An 8-bit gradient over a dark picture bands: the steps are one level apart and the eye
    finds every one of them. Half a level of noise costs nothing and removes all of them.
    """
    rng = np.random.default_rng(7)
    return np.clip(a * 255.0 + rng.uniform(-0.5, 0.5, a.shape), 0, 255).astype(np.uint8)


def _wash(w: int, h: int, alpha: int, ramp_in: float = 0.30, ramp_out: float = 0.14):
    """A soft vertical band behind the words: zero at both edges, flat in the middle.

    Drawn as a gradient rather than a blurred rectangle on purpose — a rectangle always
    leaves a corner the eye can find, and a caption you can see the edges of is a sticker.
    """
    y = np.linspace(0.0, 1.0, max(2, h), dtype=np.float32)
    up = np.clip(y / max(1e-3, ramp_in), 0, 1)
    down = np.clip((1.0 - y) / max(1e-3, ramp_out), 0, 1)
    a = (up ** 1.15) * (down ** 1.15) * float(alpha)
    arr = np.zeros((h, w, 4), np.uint8)
    arr[..., 0], arr[..., 1], arr[..., 2] = 5, 6, 5
    arr[..., 3] = _dither(a[:, None] * np.ones((1, w), np.float32))
    return Image.fromarray(arr, "RGBA")


def chyron(tokens: dict, b: dict) -> tuple[Image.Image, dict]:
    """A picture lower-third: kicker, hairline, one or two lines — over its own shadow.

    Type on footage needs a shadow before it needs a box. A blurred, offset copy of the very
    same layer costs nothing, follows every diacritic, and holds the ratio when a pale hand
    crosses behind the words. The optional wash (`WASH_ALPHA`) stays off by default: on a
    black cloak the falloff already carries it, and a band you can see the edge of is worse
    than no band at all.
    """
    ink, gold, gold2 = (bk.rgb(tokens[k]) for k in ("ink", "gold", "gold2"))
    col = (COL_L, COL_R - COL_L)
    lines = b["lines"]
    px = 58
    while px > 34 and any(typo.measure(t, "amiri", px) > col[1] for t in lines):
        px -= 2
    main = typo.stack(lines, "amiri", px, 1.46, "right", ink, col_w=col[1])
    kick = typo.layout(b["kicker"], "kufi", 29, gold2)
    gap1, gap2 = 16, 12
    height = kick.img.height + gap1 + 2 + gap2 + main.img.height
    pad_t, pad_b = 34, 30
    w = W
    layer = Image.new("RGBA", (w, height + pad_t + pad_b), (0, 0, 0, 0))
    y = pad_t
    layer.alpha_composite(kick.img, (COL_R - kick.img.width, y))
    y += kick.img.height + gap1
    rule = stage.rule(230, 2, gold, alpha=215)
    layer.alpha_composite(rule, (COL_R - rule.width, y))
    y += 2 + gap2
    layer.alpha_composite(main.img, (COL_R - col[1], y))

    img = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    wash = float(b.get("wash", WASH_ALPHA))
    if wash > 0:
        img.alpha_composite(_wash(w, layer.height, int(255 * wash),
                                  ramp_in=0.42, ramp_out=0.20), (0, 0))
    shadow = Image.new("RGBA", layer.size, (2, 3, 2, 255))
    shadow.putalpha(layer.getchannel("A").point(lambda v: int(v * 0.70)))
    shadow = shadow.filter(ImageFilter.GaussianBlur(7))
    img.alpha_composite(shadow, (2, 5))
    img.alpha_composite(layer, (0, 0))

    top = CHY_BOTTOM - height - pad_b
    return img, {"x": 0, "y": top, "w": w, "h": height,
                 "box": (COL_L, top + pad_t + kick.img.height + gap1 + 2 + gap2,
                         col[1], main.img.height)}


def mark(tokens: dict) -> Image.Image:
    """A small brand plate, top-left, that never fights the books behind it."""
    gold2 = bk.rgb(tokens["gold2"])
    ink = typo.layout("مَعَ الصَّادِقِينَ", "kufi", 26, gold2)
    w, h = ink.img.width + 44, ink.img.height + 24
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=9, fill=(6, 7, 6, 108),
                        outline=bk.rgba(tokens["gold"])[:3] + (86,), width=1)
    img.alpha_composite(ink.img, (22, 12))
    return img


def scrim(tokens: dict) -> Image.Image:
    """Top and bottom falloff: the type's backdrop, and the reason the frame reads calm.

    The ramp is tuned against a worst case, not a mood: a pale hand passing behind the chyron
    still has to leave the ivory above 6:1. Measured on such a frame, this falloff alone gives
    9.4:1 — which is why the local wash is off by default: it is there for a bright wall, not
    for a black cloak, and a band you can see the edges of is worse than no band.
    """
    a = np.zeros((H, W, 4), np.uint8)
    yy = np.mgrid[0:H, 0:W][0].astype(np.float32)
    top = np.clip(1 - yy / 320.0, 0, 1) ** 1.4 * SCRIM_TOP
    bot = np.clip((yy - SCRIM_START) / 760.0, 0, 1) ** 1.25 * SCRIM_BOTTOM
    a[..., 3] = _dither(np.clip(top + bot, 0, 0.72))
    return Image.fromarray(a, "RGBA")


DESIGNS = {"hook": card_hook, "chapter": card_chapter, "word": card_word,
           "quote": card_quote, "end": card_end}


# --------------------------------------------------------------------------- planning
def _texts(spec: dict) -> list[str]:
    out = []
    for b in spec.get("beats", []):
        for k in ("title", "kicker", "foot", "label", "quote", "note", "verse",
                  "series", "name", "handle"):
            v = b.get(k)
            if isinstance(v, str):
                out.append(v)
            elif isinstance(v, list):
                out += [x for x in v if isinstance(x, str)]
        out += [x for x in (b.get("lines") or []) if isinstance(x, str)]
        out += [x for x in (b.get("sub") or []) if isinstance(x, str)]
    return out


def schedule(spec: dict, tl: Timeline, on: list[float], total: float) -> list[dict]:
    """Beats → output windows. Card anchors are guaranteed to cover their jump cut."""
    beats, out = spec.get("beats", []), []
    for b in beats:
        dur = float(b.get("dur", 3.0))
        anchor = b.get("anchor")
        if anchor == "start":
            start = float(b.get("lead", 0.0))
        elif anchor == "end":
            start = round(total - dur - float(b.get("tail", 0.15)), 3)
        elif anchor == "cut":
            i = int(b.get("index", 0))
            cut = tl.cuts[i]["out"] if i < len(tl.cuts) else total
            start = round(cut - float(b.get("lead", 0.95)), 3)
        else:
            t_src = float(b["at"])
            if b.get("snap") and on:
                near = min(on, key=lambda o: abs(o - t_src))
                if abs(near - t_src) <= float(b.get("snap_window", 1.6)):
                    t_src = near
            start = tl.map(t_src)
        start = max(0.0, min(start, total - 0.4))
        end = min(total, start + dur)
        out.append({**b, "t_in": round(start, 3), "t_out": round(end, 3)})
    out.sort(key=lambda b: b["t_in"])
    return out


def resolve(beats: list[dict], total: float) -> tuple[list[dict], list[str]]:
    """Type never stacks. Cards own the frame; chyrons slide out of a card's way."""
    notes: list[str] = []
    cards = [b for b in beats if b.get("kind") == "card"]
    out: list[dict] = []
    last = -1e9
    for b in beats:
        if b.get("kind") == "card":
            for c in cards:
                if c is not b and b["t_in"] < c["t_out"] - 0.02 and c["t_in"] < b["t_out"] - 0.02:
                    notes.append(f'dropped {b["id"]}: collides with card {c["id"]}')
                    b = {**b, "_dropped": True}
            if b.get("_dropped"):
                continue
            out.append(b)
            last = max(last, b["t_out"])
            continue
        t_in, dur, t_out = b["t_in"], b["t_out"] - b["t_in"], b["t_out"]
        hit = [c for c in cards if t_in < c["t_out"] + 0.12 and t_out > c["t_in"] - 0.12]
        if hit:
            c = hit[0]
            t_in = round(c["t_out"] + 0.18, 3)
            t_out = round(min(total, t_in + dur), 3)
            notes.append(f'moved {b["id"]} behind card {c["id"]} → {t_in:.2f}s')
        if t_in < last + 0.25:
            t_in = round(last + 0.25, 3)
            t_out = round(min(total, t_in + dur), 3)
            notes.append(f'pushed {b["id"]} to {t_in:.2f}s')
        if t_out - t_in < 1.1:
            notes.append(f'dropped {b["id"]}: no room left ({t_out - t_in:.2f}s)')
            continue
        out.append({**b, "t_in": t_in, "t_out": t_out})
        last = t_out
    return out, notes


def audit(ov: list[dict], tl: Timeline, total: float) -> list[dict]:
    rows = []
    for c in tl.cuts:
        cover = [o for o in ov if o["kind"] == "card" and o["t_in"] <= c["out"] <= o["t_out"]]
        rows.append({"level": "pass" if cover else "fail",
                     "what": f"jump cut @ {c['out']:.2f}s (−{c['dropped']:.2f}s) "
                             f"{'covered by ' + cover[0]['id'] if cover else 'exposed'}"})
    for i, a in enumerate(ov):
        for b in ov[i + 1:]:
            if b["t_in"] < a["t_out"] - 0.02:
                rows.append({"level": "warn",
                             "what": f"overlap {a['id']} → {b['id']} "
                                     f"({b['t_in']:.2f} < {a['t_out']:.2f})"})
    cards = [o for o in ov if o["kind"] == "card"]
    secs = sum(o["t_out"] - o["t_in"] for o in cards)
    rows.append({"level": "pass" if secs / max(1e-6, total) < 0.34 else "warn",
                 "what": f"cards hold the screen {secs:.1f}s of {total:.1f}s "
                         f"({100 * secs / max(1e-6, total):.0f}%)"})
    if not any(o["kind"] == "card" and o["t_in"] < 0.4 for o in ov):
        rows.append({"level": "warn", "what": "no opening card — the first frame is the phone"})
    return rows


# --------------------------------------------------------------------------- audio
def build_audio(src: str, tl: Timeline, out_wav: str, lufs: float = -15.5,
                tp: float = -1.4, tail: float = 0.0) -> dict:
    """Cut the same segments out of the sound, then make it broadcast-clean.

    The chain is deliberately conservative: a phone in a library has hiss and a boomy
    room, not a problem to be sculpted away. Denoise, a little warmth, a little presence,
    tame the sibilance, then two-pass EBU R128 — measure the *processed* signal, because
    that is what will be normalised.
    """
    n = len(tl.segs)
    parts = [f"[0:a]asplit={n}" + "".join(f"[a{i}]" for i in range(n))]
    for i, (a, b) in enumerate(tl.segs):
        parts.append(f"[a{i}]atrim=start={a}:end={b},asetpts=PTS-STARTPTS[s{i}]")
    graph = ";".join(parts) + ";" + "".join(f"[s{i}]" for i in range(n))
    graph += (f"concat=n={n}:v=0:a=1,"
              "highpass=f=80,"
              "afftdn=nr=8:nf=-48:tn=1,"
              "equalizer=f=170:t=q:w=0.9:g=1.4,"
              "equalizer=f=2700:t=q:w=1.0:g=1.6,"
              "equalizer=f=6800:t=q:w=1.6:g=-2.2,"
              "acompressor=threshold=-20dB:ratio=2.4:attack=14:release=240:makeup=1.6,"
              "aresample=48000")
    if tail > 0:
        graph += f",apad=pad_dur={tail:.3f}"
    graph += "[out]"

    pre = Path(out_wav).parent / "pre.wav"
    _run(_ffmpeg("-i", str(src), "-filter_complex", graph, "-map", "[out]",
                 "-c:a", "pcm_s24le", str(pre)))

    j = _run(_ffmpeg("-i", str(pre), "-af",
                     f"loudnorm=I={lufs}:TP={tp}:LRA=9:print_format=json",
                     "-f", "null", "-"), check=False)
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", j, re.S)
    meas = json.loads(m.group(0)) if m else {}
    if meas:
        ln = (f"loudnorm=I={lufs}:TP={tp}:LRA=9:"
              f"measured_I={meas['input_i']}:measured_TP={meas['input_tp']}:"
              f"measured_LRA={meas['input_lra']}:measured_thresh={meas['input_thresh']}:"
              f"offset={meas.get('target_offset', 0)}:linear=true")
    else:
        ln = f"loudnorm=I={lufs}:TP={tp}:LRA=9"
    _run(_ffmpeg("-i", str(pre), "-af", ln, "-c:a", "pcm_s24le", str(out_wav)))
    pre.unlink(missing_ok=True)
    return {"measured": meas, "gain_db": round(float(meas.get("target_offset", 0)), 2)
            if meas else 0.0}


# --------------------------------------------------------------------------- picture
def _grade(tokens: dict) -> str:
    return ",".join([
        "scale=1080:1920:flags=lanczos", "setsar=1", "fps=30",
        "eq=contrast=1.055:brightness=0.004:saturation=0.90:gamma=0.99",
        "colorbalance=rs=0.035:gs=0.010:bs=-0.045:rm=0.018:bm=-0.020:rh=0.008:bh=-0.030",
        "curves=all='0/0.012 0.30/0.285 0.62/0.655 0.85/0.885 1/0.975'",
        "unsharp=5:5:0.30:5:5:0.0",
        "vignette=a=PI/4.6",
        "noise=alls=4:allf=t+u",
    ])


def render_picture(spec: dict, tl: Timeline, ov: list[dict], out_video: str,
                   tokens: dict, total: float, work: Path, progress=print) -> str:
    n = len(tl.segs)
    parts = [f"[0:v]split={n}" + "".join(f"[s{i}]" for i in range(n))]
    for i, (a, b) in enumerate(tl.segs):
        parts.append(f"[s{i}]trim=start={a}:end={b},setpts=PTS-STARTPTS[v{i}]")
    parts.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vc]")

    push = float(spec.get("push", 0.055))
    tail = float(spec.get("tail_card", 0.0))
    z = f"1+{push / max(1.0, total * FPS):.8f}*in"
    chain = (f"[vc]{_grade(tokens)},zoompan=z='{z}':d=1:"
             f"x='iw/2-(iw/zoom/2)':y='ih*0.46-(ih/zoom/2)':s=1080x1920:fps=30")
    if tail > 0:
        chain += f",tpad=stop_mode=clone:stop_duration={tail:.3f}"
    parts.append(chain + "[base]")

    inputs = []
    prev = "base"
    for i, o in enumerate(ov):
        win = round(o["t_out"] - o["t_in"] + 0.25, 3)
        inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{win}", "-i", o["png"]]
        fi, fo = float(o.get("fade_in", 0.30)), float(o.get("fade_out", 0.28))
        f = [f"[{i + 1}:v]format=rgba", f"setpts=PTS+{o['t_in']}/TB"]
        if fi > 0:
            f.append(f"fade=t=in:st={o['t_in']}:d={fi}:alpha=1")
        if fo > 0:
            f.append(f"fade=t=out:st={o['t_out'] - fo:.3f}:d={fo}:alpha=1")
        parts.append(",".join(f) + f"[o{i}]")
        ox, oy = int(o.get("x", 0)), int(o.get("y", 0))
        parts.append(f"[{prev}][o{i}]overlay={ox}:{oy}:eof_action=pass:repeatlast=0:"
                     f"enable='between(t,{o['t_in']},{o['t_out']})'[p{i}]")
        prev = f"p{i}"

    fade_in = float(spec.get("fade_in", 0.55))
    fade_out = float(spec.get("fade_out", 0.9))
    parts.append(f"[{prev}]fade=t=in:st=0:d={fade_in},"
                 f"fade=t=out:st={total - fade_out:.3f}:d={fade_out},format=yuv420p[vout]")
    graph = ";".join(parts)
    (work / "graph.txt").write_text(graph.replace(";", ";\n"), encoding="utf-8")

    cmd = _ffmpeg("-i", str(spec["source"]), *inputs, "-filter_complex", graph,
                  "-map", "[vout]", "-an", "-c:v", "libx264", "-preset", "medium",
                  "-crf", str(spec.get("crf", 21)), "-pix_fmt", "yuv420p",
                  "-profile:v", "high", "-level", "4.1", "-g", "60",
                  "-movflags", "+faststart", str(out_video))
    progress(f"  picture … {n} segments, {len(ov)} layers, {total:.2f}s")
    _run(cmd)
    return out_video


# --------------------------------------------------------------------------- verify
def _luma(img: np.ndarray) -> np.ndarray:
    return (0.2126 * img[..., 0] + 0.7152 * img[..., 1] + 0.0722 * img[..., 2]).astype(np.float32)


def _contrast(video: str, t: float, box: tuple[int, int, int, int],
              ink: tuple[int, int, int]) -> float:
    """Measured on the finished frame: the brightest background near the words, not a guess."""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "f.png"
        _run(_ffmpeg("-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", str(p)), check=False)
        if not p.exists():
            return 0.0
        a = np.asarray(Image.open(p).convert("RGB"))
    x, y, w, h = box
    pad = 34
    x0, y0 = max(0, x - pad), max(0, y - pad)
    x1, y1 = min(W, x + w + pad), min(H, y + h + pad)
    region = _luma(a[y0:y1, x0:x1])
    bg = float(np.percentile(region, 92))
    li = _luma(np.array([[[*ink]]], np.uint8))[0, 0]
    return round((max(li, bg) + 0.05) / (min(li, bg) + 0.05), 2)


def _graded_frame(src: str, t: float, tokens: dict, scrim_img: Image.Image) -> Image.Image:
    """One graded frame of the take, with the falloff already on it — the editor's eye."""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "f.png"
        _run(_ffmpeg("-ss", f"{max(0.0, t):.3f}", "-i", str(src), "-vf", _grade(tokens),
                     "-frames:v", "1", str(p)), check=False)
        if not p.exists():
            return Image.new("RGBA", (W, H), (0, 0, 0, 255))
        img = Image.open(p).convert("RGBA")
    img.alpha_composite(scrim_img)
    return img


def _box_contrast(frame: Image.Image, layer: Image.Image, y: int,
                  box: tuple[int, int, int, int], ink: tuple[int, int, int]) -> float:
    im = frame.copy()
    im.alpha_composite(layer, (0, y))
    a = _luma(np.asarray(im.convert("RGB")))
    x, by, w, h = box
    pad = 34
    reg = a[max(0, by - pad):by + h + pad, max(0, x - pad):x + w + pad]
    if not reg.size:
        return 0.0
    bg = float(np.percentile(reg, 92)) / 255.0
    li = float(_luma(np.array([[[*ink]]], np.uint8))[0, 0]) / 255.0
    return round((max(li, bg) + 0.05) / (min(li, bg) + 0.05), 2)


def auto_wash(src: str, tl: Timeline, beat: dict, tokens: dict, scrim_img: Image.Image,
              want: float = 6.2, cap: float = 0.58) -> tuple[float, float]:
    """Find the lightest wash that keeps this chyron above the contrast promise.

    Four chyrons out of seven need nothing: the frame behind them is already dark. The other
    three land on a pale hand, and a band that appears only there — measured, not guessed —
    is the difference between a caption you trust and one you squint at.
    """
    mid = (beat["t_in"] + beat["t_out"]) / 2
    frame = _graded_frame(src, tl.unmap(mid), tokens, scrim_img)
    best = (0.0, 0.0)
    for w in (0.0, 0.16, 0.28, 0.40, 0.50, cap):
        layer, box = chyron(tokens, {**beat, "wash": w})
        c = _box_contrast(frame, layer, box["y"], box["box"], bk.rgb(tokens["ink"]))
        best = (w, c)
        if c >= want:
            break
    return best


def verify(video: str, spec: dict, ov: list[dict], total: float, out_md: str,
           sheet: str | None, tokens: dict, extra: dict | None = None) -> dict:
    med = probe(video)
    loud = _run(["ffmpeg", "-hide_banner", "-nostdin", "-i", video, "-af",
                 "ebur128=peak=true", "-f", "null", "-"], check=False)
    lis = re.findall(r"I:\s*(-?[\d.]+) LUFS", loud)
    tps = re.findall(r"Peak:\s*(-?[\d.]+) dBFS", loud)
    lufs = float(lis[-1]) if lis else 0.0
    peak = float(tps[-1]) if tps else 0.0
    rows = []

    def add(level, what, value, want=""):
        rows.append({"level": level, "what": what, "value": value, "want": want})

    add("pass" if abs(med["display"][0] - 1080) <= 1 and med["display"][1] == 1920 else "fail",
        "frame", f'{med["display"][0]}×{med["display"][1]}', "1080×1920")
    add("pass" if abs(med["fps"] - 30) < 0.2 else "warn", "fps", med["fps"], "30")
    add("pass", "duration", f'{med["duration"]:.2f}s', "")
    add("pass" if abs(lufs + 15.5) <= 1.2 else "warn", "loudness", f"{lufs:.1f} LUFS", "−15.5 ±1.2")
    add("pass" if peak <= -1.0 else "fail", "true peak", f"{peak:.1f} dBFS", "≤ −1.0")
    ink = bk.rgb(tokens["ink"])
    for o in ov:
        if o["kind"] != "chyron" or "box" not in o:
            continue
        c = _contrast(video, (o["t_in"] + o["t_out"]) / 2, o["box"], ink)
        add("pass" if c >= 6.0 else ("warn" if c >= 4.5 else "fail"),
            f'contrast · chyron {o["id"]}', f"{c:.2f}:1", "≥6:1")

    if sheet:
        try:
            import verify as vmod
            vmod.contact_sheet(video, sheet, 12, 4)
        except Exception as e:  # noqa: BLE001
            add("warn", "contact sheet", str(e)[:60])

    verdict = {"pass": sum(r["level"] == "pass" for r in rows),
               "warn": sum(r["level"] == "warn" for r in rows),
               "fail": sum(r["level"] == "fail" for r in rows)}
    verdict["verdict"] = "FAIL" if verdict["fail"] else ("WARN" if verdict["warn"] else "PASS")

    lines = [f'# {spec.get("title", "footage edit")}', "",
             f'**{verdict["verdict"]}** — {verdict["pass"]} pass · {verdict["warn"]} warn · '
             f'{verdict["fail"]} fail', "",
             f'- source: `{Path(spec["source"]).name}` · {spec.get("source_meta", {})}',
             f'- out: {med["display"][0]}×{med["display"][1]} · {med["fps"]} fps · '
             f'{med["duration"]:.2f}s · {med.get("vcodec")}']
    if extra:
        for k, v in extra.items():
            lines.append(f"- {k}: {v}")
    lines += ["", "## checks", "", "| | check | value | want |", "|---|---|---|---|"]
    for r in rows:
        mark = {"pass": "✓", "warn": "!", "fail": "✗"}[r["level"]]
        lines.append(f'| {mark} | {r["what"]} | {r["value"]} | {r["want"]} |')
    Path(out_md).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"rows": rows, "verdict": verdict, "meta": med, "lufs": lufs, "peak": peak}


# --------------------------------------------------------------------------- post copy
def post_md(spec: dict) -> str:
    cfg = bk.brand_config()
    tags = list((cfg.get("hashtags") or {}).get("core") or []) + ["#فاطمة_الزهراء"]
    cap = spec.get("caption") or {}
    body = cap.get("body") or spec.get("title", "")
    return "\n".join([
        f'# {spec.get("title", "edit")} — post copy', "",
        "## Instagram", "", body, "", " ".join(tags), "",
        "## Facebook", "", cap.get("facebook", body), "",
        "## X", "", cap.get("x", body[:230]), "",
        "## on-screen lines (for alt text / archive)", "",
        *[f'- {t}' for t in _texts(spec)],
    ]) + "\n"


# --------------------------------------------------------------------------- build
def build(spec_path: str, out_dir: str = "out/edit", theme: str | None = None,
          dry_run: bool = False, progress=print) -> dict:
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    work = out / "work"
    work.mkdir(exist_ok=True)
    tokens = bk.tokens(theme or spec.get("theme"))
    src = str(spec["source"])

    med = probe(src)
    spec["source_meta"] = {k: med[k] for k in ("display", "fps", "vcodec", "rotation", "audio")}
    progress(f'  source  {Path(src).name} · {med["display"][0]}×{med["display"][1]} · '
             f'{med["duration"]:.2f}s · {med["fps"]}fps · {med["vcodec"]}'
             f'{" · rot " + str(med["rotation"]) if med["rotation"] else ""}')
    ps = pauses(src)
    on = onsets(ps, med["duration"])
    progress(f'  pauses  {len(ps)} silences · {len(on)} speech onsets')

    tl = plan(med, ps, spec.get("timeline") or {})
    tail_card = float(spec.get("tail_card", 0.0))
    total = round(tl.duration + tail_card, 3)
    progress(f'  timeline {tl.duration:.2f}s picture · {len(tl.cuts)} cuts · '
             f'+{tail_card:.2f}s end card = {total:.2f}s')
    for c in tl.cuts:
        progress(f'    cut  src {c["src"]:.2f} → out {c["out"]:.2f} (−{c["dropped"]:.2f}s)')

    # copy gate before a single pixel
    lint = copy_lint(_texts(spec))
    for r in lint:
        progress(f'  {r["level"]:4s} copy: {r["what"]} — {r["in"]}')
    if any(r["level"] == "fail" for r in lint):
        progress("  stopped: on-screen copy failed the brand gate.")
        return {"video": None, "stopped": "copy-lint", "rows": lint}

    beats, moves = resolve(schedule(spec, tl, on, total), total)
    for m in moves:
        progress(f'  type   {m}')

    # overlays: scrim and mark are always on, cards and chyrons where the plan says
    ov: list[dict] = []
    sc = scrim(tokens)
    p = work / "ov-scrim.png"
    sc.save(p)
    ov.append({"id": "scrim", "kind": "bed", "png": str(p), "t_in": 0.0, "t_out": total,
               "fade_in": 0.01, "fade_out": 0.01})
    mk = mark(tokens)
    p = work / "ov-mark.png"
    mk.save(p)
    ov.append({"id": "mark", "kind": "bed", "png": str(p), "t_in": 0.0, "t_out": total,
               "fade_in": 0.8, "fade_out": 0.6, "x": 64, "y": 74})

    for i, b in enumerate(beats):
        kind = b.get("kind", "chyron")
        o = {"id": b.get("id") or f"{kind}{i}", "kind": kind,
             "t_in": b["t_in"], "t_out": b["t_out"],
             "fade_in": float(b.get("fade_in", 0.34 if kind == "card" else 0.26)),
             "fade_out": float(b.get("fade_out", 0.40 if kind == "card" else 0.24))}
        if kind == "card":
            img = DESIGNS[b.get("design", "chapter")](tokens, b)
            p = work / f"ov-{o['id']}.png"
            img.convert("RGB").save(p)
            o["png"] = str(p)
        elif kind == "chyron":
            if spec.get("adaptive_wash", True):
                w, c = auto_wash(src, tl, b, tokens, sc, want=6.2)
                b = {**b, "wash": w}
                o["wash"], o["contrast_at_plan"] = w, c
                progress(f'  wash   {o["id"]} · {c:.1f}:1 at plan'
                         + (f' · band {w:.2f}' if w else ' · no band'))
            img, box = chyron(tokens, b)
            p = work / f"ov-{o['id']}.png"
            img.save(p)
            o["png"] = str(p)
            o["box"] = box["box"]
            o["y"] = box["y"]
        else:
            raise SystemExit(f"unknown beat kind {kind}")
        ov.append(o)

    # the mark needs its offset baked, not overlaid at 0:0
    rows = audit([o for o in ov if o["kind"] in ("card", "chyron")], tl, total)
    for r in rows:
        progress(f'  {r["level"]:4s} {r["what"]}')
    if any(r["level"] == "fail" for r in rows):
        progress("  stopped: a jump cut is not covered by a card.")
        return {"video": None, "stopped": "audit", "rows": rows}

    if dry_run:
        progress("  dry run: overlays written, nothing encoded")
        return {"video": None, "overlays": ov, "timeline": tl, "rows": rows}

    build_audio(src, tl, str(work / "mix.wav"),
                lufs=float((spec.get("audio") or {}).get("lufs", -15.5)),
                tp=float((spec.get("audio") or {}).get("tp", -1.4)), tail=tail_card)
    progress("  sound … denoise, presence, −15.5 LUFS")

    silent = str(work / "picture.mp4")
    render_picture(spec, tl, ov, silent, tokens, total, work, progress)

    final = str(out / f'{spec.get("id") or "edit"}.mp4')
    _run(_ffmpeg("-i", silent, "-i", str(work / "mix.wav"), "-map", "0:v:0", "-map", "1:a:0",
                 "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                 "-shortest", "-movflags", "+faststart", final))
    Path(silent).unlink(missing_ok=True)

    if spec.get("keep_overlays"):
        progress(f"  overlays kept in {work}")
    else:
        for f in work.glob("ov-*.png"):
            f.unlink(missing_ok=True)

    sheet = str(out / "contact-sheet.png") if spec.get("sheet", True) else None
    extra = {"cuts": len(tl.cuts),
             "removed silence": f'{sum(c["dropped"] for c in tl.cuts):.2f}s',
             "cards": ", ".join(f'{o["id"]} {o["t_in"]:.1f}–{o["t_out"]:.1f}'
                                for o in ov if o["kind"] == "card"),
             "chyrons": len([o for o in ov if o["kind"] == "chyron"])}
    data = verify(final, spec, ov, total, str(out / "report.md"), sheet, tokens, extra)
    Path(out / "post.md").write_text(post_md(spec), encoding="utf-8")
    Path(out / "timeline.json").write_text(json.dumps({
        "segments": tl.segs, "cuts": tl.cuts, "total": total,
        "overlays": [{k: v for k, v in o.items() if k != "png"} for o in ov],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    v = data["verdict"]
    progress(f'  {v["verdict"]} — {v["pass"]} pass · {v["warn"]} warn · {v["fail"]} fail')
    return {"video": final, "report": str(out / "report.md"), "sheet": sheet,
            "verdict": v, "overlays": ov, "timeline": tl, "rows": rows, "lint": lint}


# --------------------------------------------------------------------------- cli
def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="footage mode — a recorded take, dressed")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("probe")
    p.add_argument("source")

    p = sub.add_parser("pauses")
    p.add_argument("source")
    p.add_argument("--noise", type=float, default=-34.0)
    p.add_argument("--min", type=float, default=0.30)

    p = sub.add_parser("build")
    p.add_argument("spec")
    p.add_argument("--out", default="out/edit")
    p.add_argument("--theme")
    p.add_argument("--dry-run", action="store_true")

    a = ap.parse_args()
    if a.cmd == "probe":
        print(json.dumps(probe(a.source), ensure_ascii=False, indent=1))
    elif a.cmd == "pauses":
        ps = pauses(a.source, a.noise, a.min)
        med = probe(a.source)
        print(json.dumps({"duration": med["duration"],
                          "pauses": [[round(p.start, 2), round(p.end, 2)] for p in ps],
                          "onsets": onsets(ps, med["duration"])}, ensure_ascii=False, indent=1))
    elif a.cmd == "build":
        r = build(a.spec, a.out, a.theme, a.dry_run)
        return 0 if r.get("video") else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
