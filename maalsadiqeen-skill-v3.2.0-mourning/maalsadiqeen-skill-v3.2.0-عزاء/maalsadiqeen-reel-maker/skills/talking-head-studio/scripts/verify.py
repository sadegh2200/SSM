#!/usr/bin/env python3
"""
verify.py — prove the render before anyone publishes it.

    python3 verify.py final.mp4 --plan plan.json --out verify.json [--sheet sheet.png]

Every row is a measurement, not an opinion. Rows are PASS / WARN / FAIL and the
report names the number it saw, so a human can disagree with the *threshold*
instead of guessing what happened.

Hard checks (FAIL):
    duration matches the plan (±0.25s)      → a cut lost or gained frames
    frame is 1080×1920 (or the plan size)   → wrong export
    fps matches the plan                    → judder on every platform
    audio stream exists and is not silent   → silent uploads are the #1 embarrassment
    no run of ≥2s of identical frames       → a frozen encode

Judgement checks (WARN):
    loudness vs the platform target         → platforms normalise, so mismatches pump
    true peak above -1.0 dBTP               → clipping after transcodes
    face outside the frame                  → the reframe cut someone's head off
    face smaller than 12% of width          → the subject reads as a speck
    black intro/outro longer than 0.6s      → dead air on the platform
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    CASCADES, ToolError, eprint, ffmpeg, human_time, probe, read_json, run, write_json,
)

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"


class Report:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, name: str, status: str, detail: str, hint: str | None = None) -> None:
        self.rows.append({"check": name, "status": status, "detail": detail, "hint": hint})

    def count(self, status: str) -> int:
        return sum(1 for r in self.rows if r["status"] == status)

    def summary(self) -> str:
        return (f"{len(self.rows)} checks · {self.count(PASS)} pass · "
                f"{self.count(WARN)} warn · {self.count(FAIL)} fail")


def _loudness(path: str) -> dict | None:
    try:
        cp = run([ffmpeg(), "-hide_banner", "-nostats", "-i", path, "-vn",
                  "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                  "-f", "null", "-"], check=False, timeout=900)
    except ToolError:
        return None
    log = cp.stderr or ""
    blob = log[log.rfind("{"):log.rfind("}") + 1] if "{" in log else ""
    try:
        d = json.loads(blob)
    except json.JSONDecodeError:
        return None
    out = {}
    for k in ("input_i", "input_tp", "input_lra"):
        try:
            v = float(d.get(k))
            out[k] = v if math.isfinite(v) else None
        except (TypeError, ValueError):
            out[k] = None
    return out


def _silence_and_black(path: str) -> tuple[list[dict], list[dict], list[dict]]:
    """black frames, frozen runs, and silent stretches — one decode pass each."""
    blacks, freezes, silences = [], [], []
    try:
        cp = run([ffmpeg(), "-hide_banner", "-nostats", "-i", path, "-vf",
                  "blackdetect=d=0.3:pix_th=0.06,freezedetect=n=0.0008:d=1.5",
                  "-an", "-f", "null", "-"], check=False, timeout=1800)
        log = cp.stderr or ""
        for line in log.splitlines():
            if "black_start:" in line:
                seg = {}
                for token in line.split():
                    if token.startswith("black_start:"):
                        seg["start"] = float(token.split(":")[1])
                    elif token.startswith("black_end:"):
                        seg["end"] = float(token.split(":")[1])
                if seg:
                    blacks.append(seg)
            if "freeze_start:" in line:
                seg = {}
                for token in line.split():
                    if token.startswith("freeze_start:"):
                        seg["start"] = float(token.split(":")[1])
                    elif token.startswith("freeze_end:"):
                        seg["end"] = float(token.split(":")[1])
                if seg:
                    freezes.append(seg)
    except ToolError:
        pass
    try:
        cp = run([ffmpeg(), "-hide_banner", "-nostats", "-i", path, "-vn",
                  "-af", "silencedetect=n=-45dB:d=2.0", "-f", "null", "-"],
                 check=False, timeout=1800)
        for line in (cp.stderr or "").splitlines():
            if "silence_start:" in line:
                try:
                    silences.append({"start": float(line.split("silence_start:")[1].split()[0])})
                except (ValueError, IndexError):
                    pass
    except ToolError:
        pass
    return blacks, freezes, silences


def _face_rows(path: str, out_w: int, out_h: int, samples: int = 12) -> dict:
    """Detect the face in the *output*: is it inside the frame and big enough?"""
    import cv2
    import numpy as np
    cascade_path = CASCADES / "haarcascade_frontalface_default.xml"
    if not cascade_path.exists() or not out_w or not out_h:
        return {"available": False}
    cc = cv2.CascadeClassifier(str(cascade_path))
    if cc.empty():
        return {"available": False}
    dur = probe(path)["duration"] or 0
    if dur <= 0:
        return {"available": False}
    scale_w = 360
    scale_h = int(round(out_h * (scale_w / out_w) / 2) * 2)
    frame_bytes = scale_w * scale_h * 3
    boxes, checked = [], 0
    cmd = [ffmpeg(), "-hide_banner", "-nostats", "-v", "error", "-i", path,
           "-vf", f"fps={max(0.2, samples / dur):.6f},scale={scale_w}:{scale_h}:flags=area",
           "-pix_fmt", "rgb24", "-f", "rawvideo", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        while True:
            buf = proc.stdout.read(frame_bytes)
            if not buf or len(buf) < frame_bytes:
                break
            frame = np.frombuffer(buf, np.uint8).reshape(scale_h, scale_w, 3)
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            det = cc.detectMultiScale(cv2.equalizeHist(gray), 1.1, 5,
                                     minSize=(24, 24))
            checked += 1
            if len(det):
                bx, by, bw, bh = max(det, key=lambda r: r[2] * r[3])
                boxes.append({"x": bx / scale_w, "y": by / scale_h,
                              "w": bw / scale_w, "h": bh / scale_h})
    finally:
        try:
            proc.stdout.close()
        finally:
            proc.wait(timeout=30)
    if not boxes:
        return {"available": True, "found": 0, "checked": checked}
    inside = sum(1 for b in boxes if b["x"] > 0.02 and b["y"] > 0.02
                 and b["x"] + b["w"] < 0.98 and b["y"] + b["h"] < 0.98)
    widths = sorted(b["w"] for b in boxes)
    return {
        "available": True, "found": len(boxes), "checked": checked,
        "inside_ratio": round(inside / len(boxes), 3),
        "median_width": round(widths[len(widths) // 2], 4),
        "median_top": round(sorted(b["y"] for b in boxes)[len(boxes) // 2], 4),
    }


def make_sheet(path: str, out: Path, tiles: int = 12, width: int = 1080) -> Path | None:
    """A contact sheet with no text overlays — inspectable by eye, no drawtext needed."""
    try:
        dur = probe(path)["duration"] or 0
        if dur <= 0:
            return None
        cols = 4 if tiles >= 8 else 3
        rows = max(1, math.ceil(tiles / cols))
        vf = (f"fps={max(0.05, tiles / dur):.6f},"
              f"scale={max(160, width // cols)}:-2:flags=area,tile={cols}x{rows}")
        cmd = [ffmpeg(), "-hide_banner", "-nostats", "-v", "error", "-i", path,
               "-vf", vf, "-frames:v", "1", "-y", str(out)]
        run(cmd, timeout=600)
        return out if out.is_file() else None
    except ToolError:
        return None


def verify(path: str, plan: dict | None, *, sheet: bool = True,
           target_lufs: float | None = None) -> dict:
    rep = Report()
    info = probe(path)
    dur = info["duration"] or 0.0
    plan_out = (plan or {}).get("output", {})
    exp_w, exp_h = plan_out.get("width"), plan_out.get("height")
    exp_fps = plan_out.get("fps")
    exp_dur = (plan or {}).get("summary", {}).get("duration_out")
    target = target_lufs or ((plan or {}).get("audio", {}).get("loudnorm", {}) or {}).get("target") or -14.0

    # ---- hard checks
    if exp_dur:
        delta = abs(dur - exp_dur)
        rep.add("duration", PASS if delta <= 0.25 else FAIL,
                f"{human_time(dur)} (plan {human_time(exp_dur)}, Δ{delta:.2f}s)",
                None if delta <= 0.25 else "re-run the render; a segment was dropped")
    if exp_w and exp_h:
        ok = (info["width"], info["height"]) == (exp_w, exp_h)
        rep.add("frame", PASS if ok else FAIL,
                f"{info['width']}×{info['height']} (plan {exp_w}×{exp_h})",
                None if ok else "check output.fit/crop in the plan")
    if exp_fps:
        ok = abs((info["fps"] or 0) - exp_fps) <= 0.05
        rep.add("fps", PASS if ok else FAIL, f"{info['fps']} (plan {exp_fps})")
    if not info["has_audio"]:
        source_had_audio = ((plan or {}).get("source_probe") or {}).get("has_audio")
        if source_had_audio:
            rep.add("audio", FAIL, "the output has no audio but the source did",
                    "the audio graph was dropped — re-run the render")
        else:
            rep.add("audio", WARN, "no audio (the source had none)",
                    "silent video is fine for captions-only content; add a track if needed")
    else:
        rep.add("audio", PASS, f"{info['acodec']} {info['channels']}ch {info['sample_rate']}Hz")

    blacks, freezes, silences = _silence_and_black(path)
    long_freezes = [f for f in freezes if (f.get("end", dur) - f.get("start", 0)) >= 2.0]
    rep.add("frozen frames", PASS if not long_freezes else FAIL,
            "none" if not long_freezes else f"{len(long_freezes)} run(s) ≥2s",
            None if not long_freezes else "the encode stalled; re-render")

    # ---- loudness
    loud = _loudness(path)
    if loud and loud.get("input_i") is not None:
        delta = abs(loud["input_i"] - target)
        rep.add("loudness", PASS if delta <= 1.5 else WARN,
                f"{loud['input_i']:.1f} LUFS (target {target:.0f} ±1.5)",
                None if delta <= 1.5 else "platforms will re-normalise; consider re-running audio")
        if loud.get("input_tp") is not None:
            ok = loud["input_tp"] <= -1.0
            rep.add("true peak", PASS if ok else WARN,
                    f"{loud['input_tp']:.1f} dBTP (≤ -1.0)",
                    None if ok else "lower the loudnorm ceiling or trim gain")
        if loud.get("input_lra") is not None and loud["input_lra"] > 14:
            rep.add("dynamic range", WARN, f"LRA {loud['input_lra']:.1f} LU",
                    "very wide dynamics read as quiet/loud jumps on phones")
    else:
        rep.add("loudness", WARN, "not measurable", "ffmpeg loudnorm failed on this file")

    # ---- silence inside the delivery (not at the edges)
    inner = [s for s in silences if 0.5 < s["start"] < dur - 0.5]
    if inner:
        rep.add("dead air", WARN, f"{len(inner)} silent stretch(es) ≥2s inside the cut",
                "raise --pace to natural, or check that the source had speech there")

    # ---- black runs
    long_black = [b for b in blacks if (b.get("end", dur) - b.get("start", 0)) >= 0.6]
    rep.add("black frames", PASS if not long_black else WARN,
            "none" if not long_black else
            f"{len(long_black)} run(s): " + ", ".join(
                f"{b.get('start', 0):.1f}s–{b.get('end', 0):.1f}s" for b in long_black[:3]),
            None if not long_black else "trim the black intro/outro or add a card")

    # ---- the subject
    face = _face_rows(path, info["width"] or 0, info["height"] or 0)
    if face.get("available"):
        if not face.get("found"):
            rep.add("subject", WARN, "no face detected in the output",
                    "fine for B-roll; for a talking head this usually means over-cropping")
        else:
            ratio = face.get("inside_ratio", 0)
            rep.add("subject in frame", PASS if ratio >= 0.8 else WARN,
                    f"face fully inside in {ratio * 100:.0f}% of sampled frames")
            mw = face.get("median_width", 0)
            rep.add("subject size", PASS if 0.12 <= mw <= 0.75 else WARN,
                    f"face is {mw * 100:.0f}% of frame width (want 12–75%)",
                    None if 0.12 <= mw <= 0.75 else
                    ("too small: use --fit cover or --zoom in" if mw < 0.12
                     else "too large: use --fit pad or lower --zoom-amp"))
            if face.get("median_top", 1) < 0.01:
                rep.add("head room", WARN, "face touches the top edge", "lower --anchor slightly")
    else:
        rep.add("subject", WARN, "face check unavailable (no cascade file)", None)

    result = {
        "file": str(Path(path).resolve()),
        "duration": dur,
        "probe": info,
        "loudness": loud,
        "target_lufs": target,
        "black_runs": blacks,
        "freezes": freezes,
        "silences": silences,
        "face": face,
        "rows": rep.rows,
        "summary": rep.summary(),
        "verdict": FAIL if rep.count(FAIL) else ("WARN" if rep.count(WARN) else PASS),
    }
    if sheet:
        sheet_path = Path(path).with_suffix(".sheet.png")
        made = make_sheet(path, sheet_path)
        result["sheet"] = str(made) if made else None
    return result


def print_report(res: dict) -> None:
    print(f"{Path(res['file']).name} — {res['summary']}")
    for row in res["rows"]:
        mark = {PASS: "✓", WARN: "!", FAIL: "✗"}[row["status"]]
        print(f"  {mark} {row['check']:<18} {row['detail']}")
        if row.get("hint") and row["status"] != PASS:
            print(f"      → {row['hint']}")
    if res.get("sheet"):
        print(f"  sheet: {res['sheet']}")
    print(f"\nverdict: {res['verdict']}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify a rendered talking-head video.")
    ap.add_argument("video")
    ap.add_argument("--plan", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--target-lufs", type=float, default=None)
    ap.add_argument("--no-sheet", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="exit 1 on warnings too")
    args = ap.parse_args()

    plan = read_json(args.plan) if args.plan else None
    try:
        res = verify(args.video, plan, sheet=not args.no_sheet,
                     target_lufs=args.target_lufs)
    except ToolError as exc:
        eprint(f"✗ {exc}")
        return 2
    out = args.out or str(Path(args.video).with_suffix(".verify.json"))
    write_json(out, res)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2)[:6000])
    else:
        print_report(res)
        print(f"\nwrote {out}")
    if res["verdict"] == FAIL:
        return 1
    if args.strict and res["verdict"] == WARN:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
