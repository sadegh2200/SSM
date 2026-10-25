#!/usr/bin/env python3
"""Frames → MP4. No browser, no node, no network: PIL composes, ffmpeg encodes.

    python3 render.py spec.json --out reel.mp4 [--audio mix.wav] [--still 6.5 out.png]
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

import blocks
import brandkit as bk
import plan
import stage
import typo
from brandkit import CX, H, W

FPS = 30
CODEC = ["-c:v", "libx264", "-preset", "medium", "-crf", "24", "-pix_fmt", "yuv420p",
         "-profile:v", "high", "-level", "4.2", "-movflags", "+faststart"]


def build_stage(res: dict, camera: float = 0.008) -> stage.Stage:
    tk = bk.tokens(res.get("theme"))
    st = stage.Stage(tk)
    st.camera = camera
    dur = res["duration"]

    # the page furniture: arc, sprig, watermark — the same on every scene
    arc = stage.arc_divider(tk, 800, 130)
    st.add_persistent(stage.El(arc, CX, 352, 0, dur, None, None, None, 0.95, 2,
                               breathe=(3.0, 7.0, 0.0)))
    sprig = stage.sprig(tk, 104, 88)
    st.add_persistent(stage.El(sprig, 952, 330, 0, dur, None, None, None, 0.9, 2,
                               breathe=(2.5, 5.5, 0.25)))
    wm = stage.logo_mark(tk, 172, 0.20)
    if wm is not None and (res.get("watermark") or {}).get("show", True):
        show = float((res.get("watermark") or {}).get("from", res["scenes"][0]["end"] if len(res["scenes"]) > 1 else 0))
        # the brand card replaces the watermark on the closing scene
        last_start = float(res["scenes"][-1]["start"]) if len(res["scenes"]) > 1 else dur
        until = float((res.get("watermark") or {}).get("until", last_start))
        st.add_persistent(stage.El(wm, CX, 1436, show, until,
                                   stage.Enter(dy=0, dur=0.8, scale=1.0, blur=6),
                                   stage.Exit(dur=0.5), None, 1.0, 1))

    # hairline between the arc and the text, like the sheet's ruled margin
    hr = stage.rule(72, 1, bk.rgb(tk["gold"]), 120)
    st.add_persistent(stage.El(hr, CX, 452, 0.6, dur, None, None, None, 0.8, 2))
    return st


def render(res: dict, out: str, audio: str | None = None, fps: int = FPS,
           still: float | None = None, still_path: str | None = None,
           ffmpeg: str = "ffmpeg", progress=print) -> str:
    st = build_stage(res)
    cues = blocks.build_all(st, res)
    dur = res["duration"]
    n = int(round(dur * fps))

    if still is not None:
        f = st.finish(st.frame(still), still, dur)
        f.save(still_path or "still.png")
        return still_path or "still.png"

    has_audio = bool(audio) and Path(audio).exists()
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-"]
    if has_audio:
        cmd += ["-i", audio]
    cmd += CODEC
    if has_audio:
        cmd += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest"]
    cmd += [out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    t_start = time.time()
    try:
        for i in range(n):
            t = i / fps
            frame = st.finish(st.frame(t), t, dur)
            proc.stdin.write(frame.tobytes())
            if i % 60 == 0:
                el = time.time() - t_start
                progress(f"  frame {i:5d}/{n}  {i / max(1e-6, el):5.1f} fps")
        proc.stdin.close()
    except BrokenPipeError:
        pass
    err = proc.stderr.read().decode("utf-8", "replace")
    rc = proc.wait()
    if rc != 0:
        raise RuntimeError(f"ffmpeg failed ({rc}):\n{err[-2000:]}")
    progress(f"  rendered {n} frames in {time.time() - t_start:.1f}s → {out}")
    # the cue list is the sound stage's input
    Path(out + ".cues.json").write_text(
        __import__("json").dumps([{"t": round(t, 3), "sfx": s, "gain_db": g} for t, s, g in cues],
                                 ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="spec → MP4 (PIL + ffmpeg)")
    ap.add_argument("spec")
    ap.add_argument("--out", default="reel.mp4")
    ap.add_argument("--audio")
    ap.add_argument("--fps", type=int, default=FPS)
    ap.add_argument("--still", type=float, help="render one frame at this second instead")
    ap.add_argument("--still-out", default="still.png")
    a = ap.parse_args()
    res = plan.resolve(plan.load(a.spec))
    out = render(res, a.out, a.audio, a.fps, a.still, a.still_out)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
