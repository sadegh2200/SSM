#!/usr/bin/env python3
"""The stage: paper, light, ink and the motion they obey.

A reel is a list of `El` (elements) on a 1080×1920 `Stage`. Each element knows *when* it
arrives, *how* it arrives and *when* it leaves; the Stage owns everything that never moves
(paper, grain, vignette) and everything that breathes (arc, sprig, light sweep).

The motion vocabulary is deliberately small — three eases, one entrance, one exit, one
wipe — because the brand asks for "ink settling on paper", not for animation. Anything
that is not in this file does not belong in a «مع الصادقين» frame.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import brandkit as bk
from brandkit import H, W, rgb, rgba

# ----------------------------------------------------------------------------- easing
def out3(p: float) -> float:
    p = min(1.0, max(0.0, p))
    return 1 - (1 - p) ** 3


def out2(p: float) -> float:
    p = min(1.0, max(0.0, p))
    return 1 - (1 - p) ** 2


def in2(p: float) -> float:
    p = min(1.0, max(0.0, p))
    return p * p


def smooth(p: float) -> float:
    p = min(1.0, max(0.0, p))
    return p * p * (3 - 2 * p)


EASE = {"out3": out3, "out2": out2, "in2": in2, "smooth": smooth}


# --------------------------------------------------------------------------- elements
@dataclass
class Enter:
    dy: float = 26.0
    dur: float = 0.72
    scale: float = 0.985
    blur: float = 9.0
    ease: str = "out3"


@dataclass
class Exit:
    dy: float = -20.0
    dur: float = 0.42
    blur: float = 4.0
    ease: str = "in2"


@dataclass
class El:
    img: Image.Image
    cx: float
    cy: float
    t_in: float = 0.0
    t_out: float = 1e9
    enter: Enter | None = None
    exit: Exit | None = None
    wipe: tuple[float, float] | None = None      # (start, dur) reveal from the right
    alpha: float = 1.0
    z: int = 0
    push: float = 0.0                            # extra scale per second after settling
    drift: tuple[float, float] = (0.0, 0.0)
    breathe: tuple[float, float, float] | None = None   # (amp px, period s, phase)
    _cache: dict = field(default_factory=dict, repr=False)

    # -- derived ---------------------------------------------------------------
    def _scaled(self, scale: float) -> Image.Image:
        if abs(scale - 1.0) < 0.004:
            return self.img
        key = ("s", round(scale, 3))
        if key not in self._cache:
            nw, nh = max(1, int(self.img.width * scale)), max(1, int(self.img.height * scale))
            self._cache[key] = self.img.resize((nw, nh), Image.LANCZOS)
        return self._cache[key]

    def _blurred(self, radius: float) -> Image.Image:
        r = round(radius * 2) / 2
        if r <= 0.2:
            return self.img
        key = ("b", r)
        if key not in self._cache:
            self._cache[key] = self.img.filter(ImageFilter.GaussianBlur(r))
        return self._cache[key]

    def state(self, t: float):
        """(image, centre-x, centre-y, opacity) at time t, or None if invisible."""
        if t < self.t_in or t > self.t_out:
            return None
        p = 1.0
        if self.enter and self.enter.dur > 0:
            p = EASE[self.enter.ease]((t - self.t_in) / self.enter.dur)
        dy = (self.enter.dy if self.enter else 0.0) * (1 - p)
        scale = 1.0 + (self.enter.scale - 1.0) * (1 - p) if self.enter else 1.0
        op = self.alpha * (0.0 + p if self.enter else 1.0)

        img = self.img
        if self.enter and p < 0.999 and self.enter.blur > 0:
            img = Image.blend(self._blurred(self.enter.blur), img, p)

        age = t - self.t_in
        if self.push:
            scale *= 1.0 + self.push * age

        if self.exit:
            q = (t - (self.t_out - self.exit.dur)) / max(1e-6, self.exit.dur)
            if q > 0:
                e = EASE[self.exit.ease](q)
                op *= 1.0 - e
                dy += self.exit.dy * e
                if self.exit.blur > 0:
                    img = Image.blend(img, img.filter(ImageFilter.GaussianBlur(self.exit.blur)), e)

        if self.breathe:
            amp, period, phase = self.breathe
            dy += amp * math.sin(2 * math.pi * (age / period + phase))

        img = self._scaled(scale)
        x = self.cx + self.drift[0] * age - img.width / 2
        y = self.cy + self.drift[1] * age + dy - img.height / 2

        if self.wipe:
            start, dur = self.wipe
            r = EASE["out3"]((t - start) / dur) if dur > 0 else 1.0
            if r < 0.999:
                full_w = img.width
                keep = max(1, int(full_w * max(0.0, r)))
                # RTL: the line is revealed from its right edge leftwards, right edge pinned
                img = img.crop((full_w - keep, 0, full_w, img.height))
                x = x + full_w - keep
        return img, x, y, max(0.0, min(1.0, op))


# --------------------------------------------------------------------- decorations
def _noise(size: tuple[int, int], seed: int, scale: float = 1.0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    h, w = size[1], size[0]
    small = rng.normal(0.5, 0.16, (max(2, int(h / 3 * scale)), max(2, int(w / 3 * scale))))
    img = Image.fromarray(np.clip(small * 255, 0, 255).astype(np.uint8), "L")
    img = img.resize((w, h), Image.BICUBIC)
    return np.asarray(img).astype(np.float32) / 255.0


def paper(tokens: dict) -> Image.Image:
    """Radial paper: bright at the optical centre, cooler at the edges, plus fibres."""
    hi, mid, lo = rgb(tokens["paper_hi"]), rgb(tokens["paper_mid"]), rgb(tokens["paper_lo"])
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = W * 0.5, H * 0.42
    d = np.sqrt(((xx - cx) / (W * 0.78)) ** 2 + ((yy - cy) / (H * 0.62)) ** 2)
    d = np.clip(d, 0, 1.25)
    base = np.zeros((H, W, 3), np.float32)
    for i in range(3):
        near = np.where(d < 0.55, hi[i] + (mid[i] - hi[i]) * (d / 0.55),
                        mid[i] + (lo[i] - mid[i]) * np.clip((d - 0.55) / 0.7, 0, 1))
        base[..., i] = near
    fibres = _noise((W, H), 11, 0.55)
    emboss = _noise((W, H), 12, 0.22)
    shade = (fibres - 0.5) * 10 + (emboss - 0.5) * 5
    base += shade[..., None]
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


def vignette(tokens: dict) -> Image.Image:
    col = rgba(tokens["vignette"])
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.66)) ** 2)
    a = np.clip((d - 0.42) / 0.72, 0, 1) ** 1.6 * col[3]
    out = np.zeros((H, W, 4), np.uint8)
    out[..., 0], out[..., 1], out[..., 2] = col[0], col[1], col[2]
    out[..., 3] = a.astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def grain_overlays(tokens: dict, frames: int = 8) -> list[Image.Image]:
    """Pre-blurred vignette+grain plates, cycled — cheaper and calmer than per-frame noise."""
    vig = vignette(tokens)
    op = float(tokens.get("grain_opacity", 0.06))
    out = []
    for i in range(frames):
        n = _noise((W, H), 100 + i, 1.0)
        col = 255 if tokens.get("grain_blend") == "screen" else 0
        plate = np.zeros((H, W, 4), np.uint8)
        plate[..., 0] = plate[..., 1] = plate[..., 2] = col
        plate[..., 3] = (n * op * 255).astype(np.uint8)
        out.append(Image.alpha_composite(vig, Image.fromarray(plate, "RGBA")))
    return out


def light_sweep(tokens: dict) -> Image.Image:
    """One soft diagonal band; the Stage slides it across the frame over the whole reel.

    The alpha is windowed to zero at both x edges *before* the rotation: a band that is cut
    off by its own bounding box shows a hard vertical seam on a dark paper.
    """
    w, h = 620, H + 240
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    core = np.exp(-((xx - w / 2) / (w * 0.20)) ** 2)
    window = np.sin(np.pi * np.clip(xx / w, 0, 1)) ** 1.5
    # the cream palette needs a fainter sweep than the charcoal one
    k = 0.28 if tokens.get("_theme") == "main" else 0.55
    a = core * window * float(tokens.get("light_opacity", 0.1)) * k
    col = rgba(tokens["gold2"])
    img = np.zeros((h, w, 4), np.uint8)
    img[..., 0], img[..., 1], img[..., 2] = col[0], col[1], col[2]
    img[..., 3] = np.clip(a * 255, 0, 255).astype(np.uint8)
    plate = Image.fromarray(img, "RGBA").rotate(11, expand=True, resample=Image.BICUBIC)
    return plate.crop((0, 0, plate.width, min(plate.height, H + 240)))


def arc_divider(tokens: dict, width: int = 800, height: int = 130) -> Image.Image:
    """The brand's thin green arc with gold diamonds — the page's signature line."""
    ss = 2
    img = Image.new("RGBA", (width * ss, height * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    line = rgba(tokens["line"])[:3] + (205,)
    gold = rgba(tokens["gold"])[:3] + (215,)
    pts = []
    for i in range(129):
        p = i / 128
        x = p * width * ss
        y = (height * ss) * (0.5 - 0.30 * math.sin(math.pi * p) ** 0.7)
        pts.append((x, y))
    d.line(pts, fill=line, width=int(1.5 * ss), joint="curve")
    for frac, r in ((0.0, 3.2), (0.5, 4.4), (1.0, 3.2)):
        x, y = pts[int(frac * 128)]
        d.polygon([(x, y - r * ss), (x + r * ss, y), (x, y + r * ss), (x - r * ss, y)], fill=gold)
    return img.resize((width, height), Image.LANCZOS)


def sprig(tokens: dict, width: int = 104, height: int = 88) -> Image.Image:
    """An olive sprig, top-right: one stem, five pointed leaves, drawn not stamped."""
    ss = 4
    img = Image.new("RGBA", (width * ss, height * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    stem = rgba(tokens["sprig_line"])[:3] + (215,)
    leaf = rgba(tokens["sprig_leaf"])[:3] + (225,)
    d.line([(8 * ss, 78 * ss), (26 * ss, 56 * ss), (44 * ss, 34 * ss), (60 * ss, 14 * ss)],
           fill=stem, width=int(1.6 * ss), joint="curve")

    def add_leaf(ax, ay, length, ang):
        # a pointed leaf: two quadratic-ish halves meeting at a tip
        pts = []
        for k in range(13):
            u = k / 12
            pts.append((u * length, (math.sin(math.pi * u) ** 0.85) * length * 0.30))
        for k in range(12, -1, -1):
            u = k / 12
            pts.append((u * length, -(math.sin(math.pi * u) ** 0.85) * length * 0.30))
        c, sn = math.cos(ang), math.sin(ang)
        poly = [(ax + px * c - py * sn, ay + px * sn + py * c) for px, py in pts]
        d.polygon([(x * ss, y * ss) for x, y in poly], fill=leaf)

    add_leaf(24, 60, 40, math.radians(-118))
    add_leaf(40, 40, 38, math.radians(-128))
    add_leaf(54, 20, 32, math.radians(-135))
    add_leaf(30, 56, 34, math.radians(-28))
    add_leaf(46, 36, 30, math.radians(-20))
    return img.resize((width, height), Image.LANCZOS)


def logo_mark(tokens: dict, height: int = 96, opacity: float = 0.30) -> Image.Image | None:
    path = bk.asset("logo.png")
    if not path:
        return None
    logo = Image.open(path).convert("RGBA")
    scale = height / logo.height
    logo = logo.resize((max(1, int(logo.width * scale)), height), Image.LANCZOS)
    if tokens.get("_theme") == "mourning":
        # duotone ivory instead of a flat silhouette: same hue family, keeps the tree readable
        lum = np.asarray(logo.convert("L")).astype(np.float32) / 255.0
        ink = np.array(rgb(tokens["ink"]), np.float32)
        arr = np.zeros((logo.height, logo.width, 4), np.uint8)
        arr[..., :3] = np.clip(ink * (0.55 + 0.45 * lum[..., None]), 0, 255).astype(np.uint8)
        arr[..., 3] = (np.asarray(logo)[..., 3] * (0.45 + 0.55 * lum) * opacity).astype(np.uint8)
        return Image.fromarray(arr, "RGBA")
    a = np.asarray(logo).copy()
    a[..., 3] = (a[..., 3].astype(np.float32) * opacity).astype(np.uint8)
    return Image.fromarray(a, "RGBA")


# ------------------------------------------------------------------------------- stage
class Stage:
    def __init__(self, tokens: dict, grain_frames: int = 8):
        self.tk = tokens
        self.base = paper(tokens)
        self.plates = grain_overlays(tokens, grain_frames)
        self.sweep = light_sweep(tokens)
        self.els: list[El] = []
        self.persist: list[El] = []          # decorations that live for the whole reel
        self.camera = 1.0                    # total push over the reel
        self._frame_i = 0

    # -- adding ---------------------------------------------------------------
    def add(self, el: El) -> El:
        self.els.append(el)
        return el

    def add_persistent(self, el: El) -> El:
        self.persist.append(el)
        return el

    def text(self, ink, cx: float = bk.CX, cy: float = bk.OPTICAL_Y, t_in: float = 0.0,
             t_out: float = 1e9, enter: Enter | None = None, exit: Exit | None = None,
             wipe: tuple[float, float] | None = None, alpha: float = 1.0, z: int = 10,
             push: float = 0.0, breathe=None) -> El:
        return self.add(El(ink.img, cx, cy, t_in, t_out, enter, exit, wipe, alpha, z,
                           push, breathe=breathe))

    # -- rendering ------------------------------------------------------------
    def frame(self, t: float) -> Image.Image:
        base = self.base.copy()
        for el in self.persist + self.els:
            st = el.state(t)
            if not st:
                continue
            img, x, y, op = st
            if op <= 0.004 or img.width < 1 or img.height < 1:
                continue
            if op < 0.996:
                img = img.copy()
                img.putalpha(img.getchannel("A").point(lambda v, o=op: int(v * o)))
            base.paste(img, (int(round(x)), int(round(y))), img)
        return base

    def finish(self, frame: Image.Image, t: float, dur: float) -> Image.Image:
        """Vignette + grain + light sweep + camera push, in that order."""
        if self.camera and dur > 0:
            z = 1.0 + self.camera * (t / dur)
            if z > 1.001:
                fw, fh = int(W * z), int(H * z)
                big = frame.resize((fw, fh), Image.BICUBIC)
                left, top = (fw - W) // 2, (fh - H) // 2
                frame = big.crop((left, top, left + W, top + H))
        plate = self.plates[self._frame_i % len(self.plates)]
        self._frame_i += 1
        frame.alpha_composite(plate)
        # light sweep: one pass every ~11 s, moving right to left
        period = 11.0
        phase = (t % period) / period
        if phase < 0.55:
            p = phase / 0.55
            x = int(W * 1.10 - (W * 1.45) * smooth(p))
            y = (H - self.sweep.height) // 2
            frame.paste(self.sweep, (x, y), self.sweep)
        return frame.convert("RGB")


# --------------------------------------------------------------------------- shapes
def rule(width: int, thickness: int, color: tuple[int, int, int], alpha: int = 255,
         taper: bool = False) -> Image.Image:
    ss = 2
    img = Image.new("RGBA", (width * ss, thickness * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if taper:  # a hairline that thins at both ends, like a pen lift
        steps = width
        for i in range(steps):
            p = i / max(1, steps - 1)
            w = max(1, int(thickness * ss * (0.35 + 0.65 * math.sin(math.pi * p) ** 0.5)))
            d.line([(i * ss, (thickness * ss - w) // 2), (i * ss, (thickness * ss + w) // 2)],
                   fill=color + (alpha,), width=ss)
    else:
        d.rectangle([0, 0, width * ss, thickness * ss], fill=color + (alpha,))
    return img.resize((width, thickness), Image.LANCZOS)


def panel(width: int, height: int, tokens: dict, radius: int = 26, fill: str | None = None,
          line: str | None = None, line_w: int = 2) -> Image.Image:
    ss = 2
    img = Image.new("RGBA", (width * ss, height * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, width * ss - 1, height * ss - 1], radius=radius * ss,
                        fill=rgba(fill or tokens["card_bg"]),
                        outline=rgba(line or tokens["card_line"]), width=line_w * ss)
    return img.resize((width, height), Image.LANCZOS)


def flourish(height: int, color: tuple[int, int, int], mirror: bool = False,
             alpha: int = 235) -> Image.Image:
    """A drawn verse bracket — the ornate «﴿ ﴾» pair the brand prints around an āyah.

    No font on this machine carries U+FD3E/FD3F, and a tofu box is worse than no ornament,
    so the bracket is drawn: two nested arcs and a dot, in the accent colour.
    """
    ss = 4
    w = int(height * 0.62)
    img = Image.new("RGBA", (w * ss, height * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    col = color + (alpha,)
    W, Hh = w * ss, height * ss
    d.arc([int(W * 0.02), int(Hh * 0.06), int(W * 1.9), int(Hh * 0.94)], 120, 240,
          fill=col, width=int(2.4 * ss))
    d.arc([int(W * 0.30), int(Hh * 0.20), int(W * 1.55), int(Hh * 0.80)], 120, 240,
          fill=col, width=int(1.3 * ss))
    d.ellipse([int(W * 0.60), int(Hh * 0.46), int(W * 0.60 + 3.2 * ss),
               int(Hh * 0.46 + 3.2 * ss)], fill=col)
    if not mirror:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    return img.resize((w, height), Image.LANCZOS)


def diamond(size: int, color: tuple[int, int, int], alpha: int = 220) -> Image.Image:
    ss = 3
    img = Image.new("RGBA", (size * ss, size * ss), (0, 0, 0, 0))
    ImageDraw.Draw(img).polygon([(size * ss / 2, 0), (size * ss, size * ss / 2),
                                 (size * ss / 2, size * ss), (0, size * ss / 2)],
                                fill=color + (alpha,))
    return img.resize((size, size), Image.LANCZOS)


def seal(tokens: dict, line1: str, line2: str, size: int = 196) -> Image.Image:
    """The grading seal: two rings, two lines of kufi, one gold flash."""
    import typo
    ss = 3
    img = Image.new("RGBA", (size * ss, size * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    gold = rgba(tokens["gold"])
    d.ellipse([1 * ss, 1 * ss, size * ss - 2, size * ss - 2], outline=gold[:3] + (240,),
              width=int(2.2 * ss))
    d.ellipse([9 * ss, 9 * ss, size * ss - 10 * ss, size * ss - 10 * ss],
              outline=gold[:3] + (110,), width=int(1.1 * ss))
    for ang in (0, 90, 180, 270):
        r = math.radians(ang)
        cx, cy = size * ss / 2, size * ss / 2
        px, py = cx + math.cos(r) * (size * ss / 2 - 1), cy + math.sin(r) * (size * ss / 2 - 1)
        d.ellipse([px - 2.4 * ss, py - 2.4 * ss, px + 2.4 * ss, py + 2.4 * ss], fill=gold[:3] + (240,))
    img = img.resize((size, size), Image.LANCZOS)
    ink1 = typo.layout(line1, "kufi", max(20, size // 8), rgb(tokens["gold"]))
    ink2 = typo.layout(line2, "kufi", max(18, size // 9), rgb(tokens["ink"]))
    total = ink1.img.height + ink2.img.height + 10
    y = (size - total) // 2
    img.alpha_composite(ink1.img, ((size - ink1.img.width) // 2, y))
    img.alpha_composite(ink2.img, ((size - ink2.img.width) // 2,
                                   y + ink1.img.height + 10))
    return img
