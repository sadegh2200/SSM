#!/usr/bin/env python3
"""Inserts — short, self-contained brand cards an editor can cut into a take.

A footage edit needs b-roll that is not a screenshot of a page: a title, the one word the
speaker is about to say, the dates he is counting. These are 2–4 s cards on the brand's
paper, animated with the studio's own motion (deblur-in, hairline wipe, grain, one light
sweep, a slow push), encoded silent so they drop onto any timeline.

    python3 inserts.py build inserts.json --out deliver/inserts
    python3 inserts.py list

Each asset writes three files:

| file | for |
|---|---|
| `<id>.mp4` | 1080×1920 · 30 fps · silent · h264 — cut it in, no audio to fight |
| `<id>.png` | the hold frame at full size — a thumbnail, a freeze, a cover |
| `<id>-type.png` | the same type on **transparent** — layer it over the speaker |
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import brandkit as bk  # noqa: E402
import stage  # noqa: E402
import typo  # noqa: E402
from brandkit import CX, H, W  # noqa: E402

FPS = 30
CODEC = ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
         "-profile:v", "high", "-level", "4.2", "-movflags", "+faststart", "-an"]


# --------------------------------------------------------------------------- primitives
def _ink(text: str, key: str, px: int, color, max_w: int | None = 860):
    """A line of type, cropped to its ink — `.img` is what a stage pastes."""
    if max_w:
        px = typo.fit(text, key, max_w, px, max(16, px // 2))
    return typo.layout(text, key, px, color).img


def _stack(lines, key, px, color, leading=1.5, col_w=bk.COL_W):
    return typo.stack(lines, key, px, leading, "center", color, col_w=col_w).img


def _add(st: stage.Stage, img, cy: float, t_in: float, *, enter=None, exit_at=None,
         alpha=1.0, wipe=None, push=0.0, breathe=None, z=5):
    return st.add(stage.El(img, CX, cy, t_in, exit_at if exit_at else 1e9, enter,
                           stage.Exit(dur=0.30, dy=-12, blur=5) if exit_at else None,
                           wipe, alpha, z, push, (0.0, 0.0), breathe))


def _foot(st: stage.Stage, tk: dict, a: dict, dur: float, cy: float = 1556):
    """A watermark you have to look for: the still should name the page, quietly."""
    if not a.get("mark", True):
        return
    lm = stage.logo_mark(tk, 92, 0.34)
    if lm is not None:
        _add(st, lm, cy, 0.9, enter=stage.Enter(dy=8, dur=0.8, blur=6), exit_at=dur - 0.05,
             alpha=0.9, z=2)


# --------------------------------------------------------------------------- designs
def design_title(tk: dict, a: dict, dur: float) -> stage.Stage:
    st = stage.Stage(tk)
    st.camera = 0.012
    gold2, ink, ink2 = bk.rgb(tk["gold2"]), bk.rgb(tk["ink"]), bk.rgb(tk["ink2"])
    out_at = dur - 0.05
    _add(st, _ink(a.get("kicker", "مَعَ الصَّادِقِينَ"), "kufi", 30, gold2), 636, 0.02,
         enter=stage.Enter(dy=12, dur=0.55, blur=6), exit_at=out_at)
    _add(st, stage.arc_divider(tk, 640, 104), 728, 0.08,
         enter=stage.Enter(dy=8, dur=0.70, scale=0.97, blur=5), exit_at=out_at, z=4)
    st.add(stage.El(_stack(a["title"], "naskh_b", 108, ink, 1.38), CX, 900, 0.14, out_at,
                    stage.Enter(dy=26, dur=0.78, scale=0.975, blur=16),
                    stage.Exit(dur=0.35, dy=-14, blur=6), None, 1.0, 6))
    _add(st, stage.rule(560, 2, bk.rgb(tk["gold"]), alpha=225, taper=True), 1054, 0.44,
         wipe=(0.44, 0.5), exit_at=out_at, z=4)
    _add(st, stage.diamond(14, bk.rgb(tk["gold2"]), 235), 1104, 0.64,
         enter=stage.Enter(dy=6, dur=0.5, blur=3), exit_at=out_at, z=4)
    _add(st, _ink(a.get("sub", "الحَلْقَةُ الأُولَى"), "amiri", 44, ink2, 700), 1174, 0.68,
         enter=stage.Enter(dy=16, dur=0.65, blur=8), exit_at=out_at)
    _foot(st, tk, a, dur)
    return st


def design_word(tk: dict, a: dict, dur: float) -> stage.Stage:
    st = stage.Stage(tk)
    st.camera = 0.016
    gold2, ink, ink2 = bk.rgb(tk["gold2"]), bk.rgb(tk["ink"]), bk.rgb(tk["ink2"])
    out_at = dur - 0.05
    _add(st, _ink(a.get("kicker", "مِثَالٌ وَاحِدٌ"), "kufi", 32, gold2), 610, 0.02,
         enter=stage.Enter(dy=12, dur=0.5, blur=6), exit_at=out_at)
    _add(st, stage.arc_divider(tk, 660, 104), 700, 0.09,
         enter=stage.Enter(dy=6, dur=0.6, scale=0.97, blur=4), exit_at=out_at, z=4)
    word = a["word"]
    st.add(stage.El(_ink(word, "amiri_b", 190, ink, 880), CX, 880, 0.16, out_at,
                    stage.Enter(dy=30, dur=0.82, scale=0.94, blur=20),
                    stage.Exit(dur=0.32, dy=-16, blur=8), None, 1.0, 6))
    _add(st, stage.rule(300, 2, bk.rgb(tk["gold"]), alpha=225, taper=True), 1026, 0.52,
         wipe=(0.52, 0.45), exit_at=out_at, z=4)
    _add(st, stage.diamond(13, bk.rgb(tk["gold2"]), 235), 1072, 0.70,
         enter=stage.Enter(dy=5, dur=0.45, blur=3), exit_at=out_at, z=4)
    for i, line in enumerate(a.get("sub") or []):
        _add(st, _ink(line, "amiri", 44, ink2, 760), 1128 + i * 58, 0.74 + i * 0.14,
             enter=stage.Enter(dy=14, dur=0.6, blur=7), exit_at=out_at)
    _foot(st, tk, a, dur)
    return st


def design_dates(tk: dict, a: dict, dur: float) -> stage.Stage:
    """The count itself: two dates, ten beads between them, twenty days."""
    st = stage.Stage(tk)
    st.camera = 0.012
    gold, gold2, ink, ink2 = (bk.rgb(tk[k]) for k in ("gold", "gold2", "ink", "ink2"))
    out_at = dur - 0.05
    _add(st, _ink(a.get("kicker", "التَّارِيخ"), "kufi", 30, gold2), 512, 0.02,
         enter=stage.Enter(dy=12, dur=0.5, blur=6), exit_at=out_at)
    _add(st, _ink(a["from"], "naskh_b", 62, ink, 840), 620, 0.12,
         enter=stage.Enter(dy=20, dur=0.75, blur=10), exit_at=out_at)
    # ten beads, one every 0.05 s: the waiting between the two dates
    for i in range(10):
        d = stage.diamond(14 if i % 2 else 20, gold2 if i % 2 else gold, 225)
        _add(st, d, 726 + i * 30, 0.30 + i * 0.045,
             enter=stage.Enter(dy=0, dur=0.32, scale=0.4, blur=2), exit_at=out_at,
             alpha=0.95, z=3)
    _add(st, _ink(a["to"], "naskh_b", 62, ink, 840), 1042, 0.55,
         enter=stage.Enter(dy=20, dur=0.75, blur=10), exit_at=out_at)
    _add(st, stage.rule(420, 2, gold, alpha=210, taper=True), 1134, 0.78,
         wipe=(0.78, 0.45), exit_at=out_at, z=4)
    _add(st, _ink(a.get("count", "عِشْرُونَ يَوْمًا"), "kufi", 42, gold2, 800), 1206, 0.90,
         enter=stage.Enter(dy=14, dur=0.65, blur=8), exit_at=out_at)
    if a.get("sub"):
        _add(st, _ink(a["sub"], "amiri", 36, ink2, 820), 1276, 1.04,
             enter=stage.Enter(dy=12, dur=0.6, blur=6), exit_at=out_at)
    _foot(st, tk, a, dur)
    return st


DESIGNS = {"title": design_title, "word": design_word, "dates": design_dates}


# --------------------------------------------------------------------------- build
def render_one(asset: dict, tokens: dict, out_dir: Path, fps: int = FPS,
               progress=print) -> dict:
    aid = asset["id"]
    design = asset.get("design", "title")
    if design not in DESIGNS:
        raise SystemExit(f"unknown design «{design}» — pick one of {list(DESIGNS)}")
    dur = float(asset.get("dur", 3.2))
    st = DESIGNS[design](tokens, asset, dur)
    n = int(round(dur * fps))

    mp4 = out_dir / f"{aid}.mp4"
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
           "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", *CODEC, str(mp4)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    t0 = time.time()
    hold = int(n * 0.66)
    try:
        for i in range(n):
            t = i / fps
            f = st.finish(st.frame(t), t, dur)
            if i == hold:
                f.save(out_dir / f"{aid}.png")
            proc.stdin.write(f.tobytes())
    except BrokenPipeError:
        pass
    proc.stdin.close()
    err = proc.stderr.read().decode("utf-8", "replace")
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg failed for {aid}:\n{err[-1200:]}")

    # the same type, no paper: for layering over the speaker
    st2 = DESIGNS[design](tokens, asset, dur)
    st2.base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    st2.frame(hold / fps).save(out_dir / f"{aid}-type.png")

    progress(f'  {aid:6s} {design:6s} {dur:4.1f}s · {n} frames · '
             f'{time.time() - t0:5.1f}s · {mp4.stat().st_size / 1e6:.1f} MB')
    return {"id": aid, "design": design, "dur": dur, "mp4": str(mp4),
            "png": str(out_dir / f"{aid}.png"), "type_png": str(out_dir / f"{aid}-type.png")}


def _luma(c) -> float:
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _rel_lum(c: tuple[float, float, float]) -> float:
    def f(v: float) -> float:
        v = v / 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (f(x) for x in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_of(png: str, tokens: dict) -> float:
    """The brand's own number: the ink token against the paper the frame actually shows."""
    import numpy as np
    arr = np.asarray(Image.open(png).convert("RGB")).reshape(-1, 3)
    paper = tuple(float(x) for x in np.median(arr, axis=0))      # most of a card is paper
    ink = bk.rgb(tokens["ink"])
    a, b = _rel_lum(ink), _rel_lum(paper)
    return round((max(a, b) + 0.05) / (min(a, b) + 0.05), 2)


def build(spec_path: str, out_dir: str = "inserts", progress=print) -> dict:
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    tokens = bk.tokens(spec.get("theme"))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    assets = spec.get("assets") or []
    if not assets:
        raise SystemExit("no assets in the spec")

    import footage
    strings = []
    for a in assets:
        strings += [a.get("kicker", ""), a.get("sub") if isinstance(a.get("sub"), str) else ""]
        strings += a.get("title") or []
        strings += (a.get("sub") if isinstance(a.get("sub"), list) else [])
        strings += [a.get("word", ""), a.get("from", ""), a.get("to", ""),
                    a.get("count", "")]
    lint = [r for r in footage.copy_lint([s for s in strings if s]) if r["level"] == "fail"]
    for r in lint:
        progress(f'  copy gate: {r["what"]} — {r["in"]}')
    if lint:
        raise SystemExit("on-screen copy failed the brand gate")

    made = []
    for a in assets:
        made.append(render_one(a, tokens, out, int(spec.get("fps", FPS)), progress))

    rows = []
    for m in made:
        rows.append({"id": m["id"], "dur": m["dur"],
                     "contrast": contrast_of(m["png"], tokens)})
    lines = ["# inserts — three cards from the take", "",
             f'theme `{tokens.get("_theme")}` · 1080×1920 · {spec.get("fps", FPS)} fps · silent', "",
             "| id | design | duration | ink/paper contrast | files |", "|---|---|---|---|---|"]
    for m, r in zip(made, rows):
        lines.append(f'| {m["id"]} | {m["design"]} | {r["dur"]:.1f}s | {r["contrast"]:.1f}:1 | '
                     f'`{Path(m["mp4"]).name}` · `{Path(m["png"]).name}` · '
                     f'`{Path(m["type_png"]).name}` |')
    lines += ["", "Cut the `.mp4` in as it is (no audio, hard cuts on both ends). "
                  "Use the `-type.png` over the speaker when the paper is already on screen."]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"assets": made, "rows": rows, "out": str(out)}


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="short brand inserts for a take")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("build")
    p.add_argument("spec")
    p.add_argument("--out", default="inserts")
    p = sub.add_parser("list")
    a = ap.parse_args()
    if a.cmd == "list":
        print("\n".join(DESIGNS))
    elif a.cmd == "build":
        r = build(a.spec, a.out)
        print(f'{len(r["assets"])} inserts → {r["out"]}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
