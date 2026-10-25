#!/usr/bin/env python3
"""Brand tokens, geometry and asset resolution for «مع الصادقين» reels.

This module holds **no copy and no design opinion of its own**: every colour, size and
font comes from the brand skill's `config/brand.json` when it is installed, and from a
baked-in snapshot of the same tokens when it is not. That keeps one source of truth: if
the brand changes a token, every reel built by this studio changes with it.

    from brandkit import THEME, tokens, font_path, logo
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

# ---------------------------------------------------------------- geometry (1080x1920)
W, H = 1080, 1920
COL_X, COL_W = 150, 800          # brand stage padding 0 130 150 150 → 800 px text column
CX = COL_X + COL_W // 2          # 550 — optical centre, 10 px right of the geometric one
SAFE_TOP, SAFE_BOT = 300, 1440   # platform UI never eats this band
OPTICAL_Y = 885

DEFAULT_THEME = "mourning"

# Snapshot of config/brand.json → themes. Used only when the brand skill is absent.
_FALLBACK = {
    "main": {
        "paper": "#ece6da", "paper2": "#e2dacb", "green": "#1f4a35", "green2": "#2f6a4b",
        "gold": "#957238", "gold2": "#cdb078", "ink": "#2d2b27", "ink2": "#5a5650",
        "line": "#8aa58f", "body_bg": "#ece6da", "paper_hi": "#f4efe6", "paper_mid": "#ebe4d7",
        "paper_lo": "#ddd4c3", "light_opacity": "0.55", "grain_opacity": "0.085",
        "grain_blend": "multiply", "vignette": "rgba(70,52,28,0.17)",
        "glow": "rgba(210,180,122,0.55)", "card_bg": "rgba(255,255,255,0.35)",
        "card_line": "rgba(31,74,53,0.35)", "seal_bg": "rgba(255,255,255,0.22)",
        "seal_flash": "rgba(180,140,74,0.45)", "chip_bg": "#f1ece1", "logo_filter": "none",
        "sprig_line": "#9a8650", "sprig_leaf": "#4f7a55", "panel_bg": "#f7f3ea",
        "panel_line": "#c9c0b0",
    },
    "mourning": {
        "paper": "#0e0f0e", "paper2": "#151614", "green": "#e8dfcb", "green2": "#f4eddd",
        "gold": "#c2a267", "gold2": "#ddc79a", "ink": "#efe8d8", "ink2": "#a89f8c",
        "line": "#565244", "body_bg": "#0a0b0a", "paper_hi": "#171814", "paper_mid": "#101110",
        "paper_lo": "#060706", "light_opacity": "0.10", "grain_opacity": "0.06",
        "grain_blend": "screen", "vignette": "rgba(0,0,0,0.62)",
        "glow": "rgba(194,162,103,0.18)", "card_bg": "rgba(255,255,255,0.05)",
        "card_line": "rgba(194,162,103,0.34)", "seal_bg": "rgba(255,255,255,0.04)",
        "seal_flash": "rgba(194,162,103,0.28)", "chip_bg": "rgba(255,255,255,0.06)",
        "logo_filter": "brightness(0) invert(1) opacity(.86)", "sprig_line": "#6d5f42",
        "sprig_leaf": "#3a3f35", "panel_bg": "#121311", "panel_line": "#2c2a24",
    },
}

# font key → (file, weight). Mirrors references/brand.md § Typography.
FONTS = {
    "quran":     ("AmiriQuran.ttf", "regular"),
    "amiri":     ("Amiri-Regular.ttf", "regular"),
    "amiri_b":   ("Amiri-Bold.ttf", "bold"),
    "kufi":      ("NotoKufiArabic-Bold.ttf", "bold"),
    "kufi_r":    ("NotoKufiArabic-Regular.ttf", "regular"),
    "naskh":     ("NotoNaskhArabic-Regular.ttf", "regular"),
    "naskh_b":   ("NotoNaskhArabic-Bold.ttf", "bold"),
}


# --------------------------------------------------------------------- path resolution
def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _first(cands: list[Path], probe: str) -> Path | None:
    for c in cands:
        if c and (c / probe).exists():
            return c
    return None


@lru_cache(maxsize=1)
def brand_root() -> Path | None:
    """The installed «maalsadiqeen-reel» skill (fonts, logo, sfx, brand.json live there)."""
    env = os.environ.get("SADIQEEN_BRAND_ROOT")
    root = skill_root()
    cands = [
        Path(env) if env else None,
        root.parent / "maalsadiqeen-reel",
        root.parent.parent / "maalsadiqeen-reel",
        Path.home() / ".agents" / "skills" / "maalsadiqeen-reel",
        Path.home() / ".claude" / "skills" / "maalsadiqeen-reel",
    ]
    return _first([c for c in cands if c], "config/brand.json")


@lru_cache(maxsize=1)
def brand_config() -> dict:
    root = brand_root()
    if root:
        try:
            return json.loads((root / "config" / "brand.json").read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"handle": "maalsadiqeen", "handle_display": "@maalsadiqeen",
            "brand_name_ar": "مع الصادقين", "brand_name_fa": "مع الصادقین",
            "defaults": {"duration": 40, "theme": DEFAULT_THEME, "lufs": -15.5},
            "themes": {k: {"tokens": v} for k, v in _FALLBACK.items()},
            "cta": {"endings": []}, "hashtags": {"core": []}, "limits": {}}


@lru_cache(maxsize=4)
def tokens(theme: str | None = None) -> dict:
    """Resolved token dict for a palette: `main` (النهار) or `mourning` (ليلُ العزاء)."""
    theme = theme or os.environ.get("SADIQEEN_THEME") or \
        brand_config().get("defaults", {}).get("theme") or DEFAULT_THEME
    themes = brand_config().get("themes", {})
    if theme not in themes:
        theme = "mourning" if theme not in ("main", "mourning") else theme
    snap = dict(_FALLBACK.get(theme, _FALLBACK[DEFAULT_THEME]))
    snap.update(themes.get(theme, {}).get("tokens", {}))
    snap["_theme"] = theme
    snap["_label_ar"] = themes.get(theme, {}).get("label_ar", "")
    return snap


def theme_name(spec: dict | None = None) -> str:
    spec = spec or {}
    return spec.get("theme") or tokens()["_theme"]


def font_path(key: str) -> str:
    fname, _ = FONTS.get(key, FONTS["naskh"])
    root = brand_root()
    if root and (root / "assets" / "fonts" / fname).exists():
        return str(root / "assets" / "fonts" / fname)
    env = os.environ.get("SADIQEEN_FONTS")
    if env and (Path(env) / fname).exists():
        return str(Path(env) / fname)
    raise FileNotFoundError(
        f"font {fname} not found — install the maalsadiqeen-reel skill or set SADIQEEN_FONTS")


def asset(name: str) -> Path | None:
    root = brand_root()
    for sub in ("assets/brand", "assets/sfx", "assets"):
        if root and (root / sub / name).exists():
            return root / sub / name
    return None


# ------------------------------------------------------------------------------- colour
def rgb(value: str) -> tuple[int, int, int]:
    v = value.strip()
    if v.startswith("rgba") or v.startswith("rgb"):
        parts = v[v.index("(") + 1:v.rindex(")")].split(",")
        return tuple(int(float(p)) for p in parts[:3])  # type: ignore[return-value]
    v = v.lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def rgba(value: str, default_alpha: float = 1.0) -> tuple[int, int, int, int]:
    v = value.strip()
    if v.startswith("rgba"):
        parts = v[v.index("(") + 1:v.rindex(")")].split(",")
        a = float(parts[3]) if len(parts) > 3 else default_alpha
        return (*[int(float(p)) for p in parts[:3]], int(round(a * 255)))
    if v.startswith("rgb"):
        return (*rgb(v), int(round(default_alpha * 255)))
    return (*rgb(v), int(round(default_alpha * 255)))


def _lum(c: tuple[int, int, int]) -> float:
    def f(x: float) -> float:
        x /= 255.0
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    r, g, b = (f(float(v)) for v in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return round((hi + 0.05) / (lo + 0.05), 2)


def mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))  # type: ignore


__all__ = ["W", "H", "COL_X", "COL_W", "CX", "SAFE_TOP", "SAFE_BOT", "OPTICAL_Y", "DEFAULT_THEME",
           "FONTS", "skill_root", "brand_root", "brand_config", "tokens", "theme_name",
           "font_path", "asset", "rgb", "rgba", "contrast", "mix"]
