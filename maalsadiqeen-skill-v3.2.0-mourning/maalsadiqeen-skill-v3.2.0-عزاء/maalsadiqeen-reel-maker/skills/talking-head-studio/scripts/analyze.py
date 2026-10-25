#!/usr/bin/env python3
"""
analyze.py — measure the footage before touching it.

    python3 analyze.py SOURCE [--out analysis.json] [--sample 0.5] [--width 480]

What it measures, and why each number exists:

  audio
    speech / silence intervals   → which parts to cut (dead air, false starts at the edges)
    integrated loudness + true peak → how much gain the voice needs to reach -14 LUFS
    noise floor (5th percentile RMS) → how hard afftdn may work, and whether to warn
    clipped samples              → a warning: clipping cannot be undone
    A/V start offset             → a sync warning before any cut happens

  video
    per-sample luma / chroma means → exposure and white-balance correction amounts
    face box per sample            → the reframe pan, and whether the face stays inside it
    sharpness (variance of Laplacian) → warns on soft footage and over-smoothing
    global motion between samples  → flags handheld shake and counts cuts
    black frames                   → catches a dead intro/outro

Nothing here decides anything: it only reports. plan.py turns these facts into a plan a
human can read and argue with.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    CASCADES, ToolError, clamp, eprint, ffmpeg, human_time, median, percentile,
    probe, resample_curve, run, write_json,
)

import numpy as np  # noqa: E402

DEFAULT_SAMPLE = 0.5
DEFAULT_WIDTH = 480
SILENCE_DB = -32.0
SILENCE_MIN = 0.30
MAX_SERIES = 1500


# --------------------------------------------------------------------------- audio

def _parse_time_pairs(text: str, key: str) -> list[float]:
    out = []
    for line in text.splitlines():
        if key in line:
            try:
                out.append(float(line.rsplit(key, 1)[1].strip().rstrip("s").split()[0]))
            except (ValueError, IndexError):
                continue
    return out


def analyze_audio(path: str) -> dict:
    """Silence map, loudness, noise floor, clipping and start offset."""
    result: dict = {
        "speech_ranges": None, "silences": None, "loudness": None,
        "noise_floor_db": None, "peak_db": None, "clipped": None,
        "start_offset": None, "error": None,
    }
    exe = ffmpeg()

    # 1) silence map
    try:
        cp = run([exe, "-hide_banner", "-nostats", "-i", path, "-vn",
                  "-af", f"silencedetect=n={SILENCE_DB}dB:d={SILENCE_MIN}",
                  "-f", "null", "-"], check=False, timeout=900)
        log = cp.stderr or ""
        starts = _parse_time_pairs(log, "silence_start:")
        ends = _parse_time_pairs(log, "silence_end:")
        sil = []
        for idx, s in enumerate(starts):
            e = ends[idx] if idx < len(ends) else None
            sil.append({"start": round(s, 3), "end": round(e, 3) if e is not None else None})
        result["silences"] = sil
    except ToolError as exc:
        result["error"] = f"silencedetect failed: {exc}"

    # 2) loudness + peaks (one pass over the audio)
    try:
        cp = run([exe, "-hide_banner", "-nostats", "-i", path, "-vn",
                  "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                  "-f", "null", "-"], check=False, timeout=900)
        log = cp.stderr or ""
        blob = log[log.rfind("{"):log.rfind("}") + 1]
        if blob:
            data = json.loads(blob)
            def n(k):
                try:
                    v = float(data.get(k))
                    return v if math.isfinite(v) else None
                except (TypeError, ValueError):
                    return None
            result["loudness"] = {
                "input_i": n("input_i"), "input_tp": n("input_tp"),
                "input_lra": n("input_lra"), "input_thresh": n("input_thresh"),
            }
    except (ToolError, json.JSONDecodeError) as exc:
        result["error"] = (result["error"] or "") + f" loudnorm measure failed: {exc}"

    # 3) per-window RMS → noise floor; and peak
    try:
        cp = run([exe, "-hide_banner", "-nostats", "-i", path, "-vn",
                  "-af", "astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level",
                  "-f", "null", "-"], check=False, timeout=900)
        rms = []
        for line in (cp.stderr or "").splitlines():
            if "RMS_level=" in line:
                try:
                    v = float(line.split("RMS_level=")[1].strip())
                    if math.isfinite(v):
                        rms.append(v)
                except (ValueError, IndexError):
                    continue
        if rms:
            result["noise_floor_db"] = round(percentile(rms, 0.05), 2)
        cp2 = run([exe, "-hide_banner", "-nostats", "-i", path, "-vn",
                   "-af", "astats=metadata=1:reset=0", "-f", "null", "-"],
                  check=False, timeout=900)
        log2 = cp2.stderr or ""
        for line in log2.splitlines():
            if "Peak level dB" in line:
                try:
                    result["peak_db"] = round(float(line.split(":")[-1].strip()), 2)
                except ValueError:
                    pass
            if "Number of samples" in line and ":" in line:
                pass
        result["clipped"] = bool(result["peak_db"] is not None and result["peak_db"] >= -0.1)
    except ToolError as exc:
        result["error"] = (result["error"] or "") + f" rms measure failed: {exc}"

    # 4) speech ranges from the silence map
    sil = [s for s in result["silences"] or [] if s["end"] is not None]
    if sil:
        ranges, cursor = [], 0.0
        for s in sil:
            if s["start"] > cursor + 0.05:
                ranges.append({"start": round(cursor, 3), "end": round(s["start"], 3)})
            cursor = max(cursor, s["end"])
        dur = None
        try:
            dur = probe(path)["duration"]
        except ToolError:
            pass
        if dur and dur > cursor + 0.05:
            ranges.append({"start": round(cursor, 3), "end": round(dur, 3)})
        result["speech_ranges"] = ranges
    return result


# --------------------------------------------------------------------------- video

def _load_cascade():
    import cv2
    path = CASCADES / "haarcascade_frontalface_default.xml"
    if not path.exists():
        return None
    cc = cv2.CascadeClassifier(str(path))
    return None if cc.empty() else cc


def analyze_video(path: str, info: dict, sample: float, width: int) -> dict:
    """
    Stream small frames out of ffmpeg and measure them with numpy/cv2 in one pass.
    Keeps memory flat: frames are consumed as they arrive, never stored.
    """
    import cv2

    src_w, src_h = info["width"], info["height"]
    if not src_w or not src_h:
        return {"error": "no video stream", "samples": []}
    scale_w = min(width, src_w)
    scale_h = int(round(src_h * (scale_w / src_w) / 2) * 2)
    frame_bytes = scale_w * scale_h * 3

    cascade = _load_cascade()
    samples: list[dict] = []
    prev_gray = None
    faces_found = 0

    cmd = [
        ffmpeg(), "-hide_banner", "-nostats", "-v", "error", "-i", path,
        "-vf", f"fps={1.0 / sample:.6f},scale={scale_w}:{scale_h}:flags=area",
        "-pix_fmt", "rgb24", "-f", "rawvideo", "-",
    ]
    proc = None
    try:
        import subprocess
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        idx = 0
        while True:
            buf = proc.stdout.read(frame_bytes)
            if not buf or len(buf) < frame_bytes:
                break
            frame = np.frombuffer(buf, np.uint8).reshape(scale_h, scale_w, 3)
            t = round(idx * sample, 3)
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            y = float(gray.mean())
            # channel means for a grey-world white-balance estimate
            r_mean = float(frame[:, :, 0].mean())
            g_mean = float(frame[:, :, 1].mean())
            b_mean = float(frame[:, :, 2].mean())
            sharp = float(cv2.Laplacian(gray, cv2.CV_64F).var())

            face = None
            if cascade is not None and idx % 2 == 0:      # faces every other sample: cheap
                det = cascade.detectMultiScale(
                    cv2.equalizeHist(gray), 1.1, 5,
                    minSize=(max(28, int(scale_h * 0.10)), max(28, int(scale_h * 0.10))))
                if len(det):
                    # keep the largest box (the speaker), not a face on a bookshelf
                    bx, by, bw, bh = max(det, key=lambda r: r[2] * r[3])
                    face = [round(float(bx) / scale_w, 4), round(float(by) / scale_h, 4),
                            round(float(bw) / scale_w, 4), round(float(bh) / scale_h, 4)]
                    faces_found += 1
                    # the subject's own brightness is what "correct exposure" means here
                    patch = gray[by:by + bh, bx:bx + bw]
                    face_y = float(patch.mean()) if patch.size else None

            motion = None
            if prev_gray is not None and prev_gray.shape == gray.shape:
                try:
                    (dx, dy), _resp = cv2.phaseCorrelate(
                        np.float32(prev_gray), np.float32(gray))
                    motion = [round(float(dx) / scale_w, 4), round(float(dy) / scale_h, 4)]
                except Exception:
                    motion = None
            prev_gray = gray

            samples.append({"t": t, "y": round(y, 2),
                            "r": round(r_mean, 2), "g": round(g_mean, 2), "b": round(b_mean, 2),
                            "sharp": round(sharp, 1), "face": face,
                            "face_y": round(face_y, 2) if 'face_y' in dir() and face_y is not None else None,
                            "motion": motion,
                            "black": bool(y < 8.0 and sharp < 3.0)})
            face_y = None
            idx += 1
    except FileNotFoundError as exc:
        return {"error": f"ffmpeg could not start: {exc}", "samples": []}
    finally:
        if proc is not None:
            try:
                proc.stdout.close()
            except Exception:
                pass
            proc.wait(timeout=30)

    # faces are detected every other sample: carry the last box forward in a copy
    carried, last = [], None
    for s in samples:
        if s["face"]:
            last = s["face"]
            carried.append(s)
        else:
            carried.append({**s, "face_carried": last})
    samples = carried

    boxes = [s["face"] for s in samples if s.get("face")]
    ys = [s["y"] for s in samples]
    sharps = [s["sharp"] for s in samples]
    motions = [abs(m[0]) + abs(m[1]) for s in samples if (m := s.get("motion"))]
    cut_like = [1 for m in motions if m > 0.06]

    def smooth_face_box(box):
        cx = box[0] + box[2] / 2.0
        cy = box[1] + box[3] / 2.0
        return cx, cy, box[2], box[3]

    faces = [smooth_face_box(b) for b in boxes]
    face_ys = [s["face_y"] for s in samples if s.get("face_y") is not None]
    detection_rate = (len(boxes) / max(1, len(range(0, len(samples), 2)))) if samples else 0.0

    rs = [s["r"] for s in samples if s.get("r") is not None]
    gs = [s["g"] for s in samples if s.get("g") is not None]
    bs = [s["b"] for s in samples if s.get("b") is not None]
    colour = None
    if rs and gs and bs:
        mr, mg, mb = median(rs), median(gs), median(bs)
        grey = (mr + mg + mb) / 3.0
        if grey > 12:
            colour = {
                "median_rgb": [round(mr, 1), round(mg, 1), round(mb, 1)],
                "cast": [round(mr - grey, 1), round(mg - grey, 1), round(mb - grey, 1)],
                # colourbalance midtone offsets: reduce the channel that is too strong
                "gains": {"rm": round((grey - mr) / 255.0, 4),
                          "gm": round((grey - mg) / 255.0, 4),
                          "bm": round((grey - mb) / 255.0, 4)},
            }

    return {
        "samples": samples,
        "sample_interval": sample,
        "color": colour,
        "analysis_size": [scale_w, scale_h],
        "face": {
            "detected": faces_found,
            "detection_rate": round(detection_rate, 3),
            "boxes": boxes,
            "median_center": ([round(median([f[0] for f in faces]), 4),
                               round(median([f[1] for f in faces]), 4)]
                              if faces else None),
            "median_width": round(median([f[2] for f in faces]), 4) if faces else None,
            "drift": ([round(max(f[0] for f in faces) - min(f[0] for f in faces), 4),
                       round(max(f[1] for f in faces) - min(f[1] for f in faces), 4)]
                      if faces else None),
        },
        "face_luma": {"median": median(face_ys), "p10": percentile(face_ys, 0.10),
                      "p90": percentile(face_ys, 0.90)} if face_ys else None,
        "luma": {"median": median(ys), "p10": percentile(ys, 0.10),
                 "p90": percentile(ys, 0.90),
                 "swing": (percentile(ys, 0.90) - percentile(ys, 0.10)) if ys else None},
        "sharpness": {"median": median(sharps), "p10": percentile(sharps, 0.10)},
        "motion": {"median": median(motions), "p90": percentile(motions, 0.90),
                   "shake_samples": len(cut_like),
                   "handheld": bool((percentile(motions, 0.9) or 0) > 0.012)},
        "black_runs": _black_runs(samples, sample),
        "error": None,
    }


def _black_runs(samples: list[dict], sample: float) -> list[dict]:
    runs, cur = [], None
    for s in samples:
        if s.get("black"):
            if cur is None:
                cur = {"start": s["t"], "end": s["t"]}
            else:
                cur["end"] = s["t"]
        elif cur is not None:
            runs.append(cur)
            cur = None
    if cur is not None:
        runs.append(cur)
    return [r for r in runs if (r["end"] - r["start"]) + sample >= 0.4]


# --------------------------------------------------------------------------- main

def analyze(path: str, sample: float = DEFAULT_SAMPLE, width: int = DEFAULT_WIDTH) -> dict:
    info = probe(path)
    if not info["has_video"]:
        raise ToolError(f"no video stream in {path}", kind="input")
    audio = analyze_audio(path) if info["has_audio"] else {
        "speech_ranges": None, "silences": None, "loudness": None,
        "noise_floor_db": None, "peak_db": None, "clipped": None,
        "start_offset": None, "error": "no audio stream"}
    video = analyze_video(path, info, sample, width)

    if info["has_audio"] and info.get("audio_start") is not None and info.get("video_start") is not None:
        audio["start_offset"] = round((info["audio_start"] or 0) - (info["video_start"] or 0), 3)

    # keep the file small enough to read: cap the stored series
    series = video.get("samples") or []
    if len(series) > MAX_SERIES:
        step = len(series) / MAX_SERIES
        series = [series[int(i * step)] for i in range(MAX_SERIES)]
    video["samples"] = series

    return {
        "version": 1,
        "source": str(Path(path).resolve()),
        "probe": info,
        "audio": audio,
        "video": video,
        "settings": {"sample": sample, "analysis_width": width,
                     "silence_db": SILENCE_DB, "silence_min": SILENCE_MIN},
    }


def summary_lines(a: dict) -> list[str]:
    p, au, vi = a["probe"], a["audio"], a["video"]
    lines = [f"source      {Path(p['path']).name}  {p['width']}×{p['height']}  "
             f"{p['fps']} fps  {human_time(p['duration'])}  {p['vcodec']}/{p['acodec']}"]
    if au.get("silences") is not None:
        sil = au["silences"]
        speech = au.get("speech_ranges") or []
        total_sil = sum((s["end"] - s["start"]) for s in sil if s["end"])
        lines.append(f"audio       {len(speech)} speaking ranges · {len(sil)} silences · "
                     f"{total_sil:.1f}s dead air")
    if au.get("loudness"):
        L = au["loudness"]
        lines.append(f"loudness    {L['input_i']} LUFS · true peak {L['input_tp']} dBTP · "
                     f"LRA {L['input_lra']}")
    if au.get("noise_floor_db") is not None:
        lines.append(f"noise floor {au['noise_floor_db']} dB (5th pct) · peak {au.get('peak_db')} dB"
                     + ("  ⚠ CLIPPED" if au.get("clipped") else ""))
    if vi.get("face"):
        f = vi["face"]
        lines.append(f"face         detected in {f['detected']} samples ({f['detection_rate'] * 100:.0f}% of checked) · "
                     f"drift {f['drift']}")
    if vi.get("luma"):
        lines.append(f"exposure     median luma {vi['luma']['median']:.0f}/255 · "
                     f"swing {vi['luma']['swing']:.0f}")
    if vi.get("motion"):
        lines.append(f"motion       median {vi['motion']['median']:.4f} · p90 {vi['motion']['p90']}"
                     + ("  ⚠ handheld shake" if vi["motion"].get("handheld") else ""))
    if vi.get("black_runs"):
        lines.append(f"black        {len(vi['black_runs'])} black run(s)")
    if au.get("start_offset") not in (None, 0, 0.0):
        lines.append(f"sync        ⚠ audio starts {au['start_offset']:+.3f}s from video")
    if vi.get("error"):
        lines.append(f"video error  {vi['error']}")
    if au.get("error"):
        lines.append(f"audio error  {au['error']}")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description="Measure a talking-head recording.")
    ap.add_argument("source")
    ap.add_argument("--out", default=None, help="analysis.json path (default: <source>.analysis.json)")
    ap.add_argument("--sample", type=float, default=DEFAULT_SAMPLE, help="seconds between video samples")
    ap.add_argument("--width", type=int, default=DEFAULT_WIDTH, help="analysis frame width")
    ap.add_argument("--json", action="store_true", help="print the JSON to stdout")
    args = ap.parse_args()

    try:
        a = analyze(args.source, args.sample, args.width)
    except ToolError as exc:
        eprint(f"✗ {exc}")
        if exc.stderr:
            eprint(exc.stderr[-800:])
        return 2

    out = args.out or str(Path(args.source).with_suffix("")) + ".analysis.json"
    write_json(out, a)
    if args.json:
        print(json.dumps(a, ensure_ascii=False)[:4000])
    else:
        for line in summary_lines(a):
            print("  " + line)
        print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
