#!/usr/bin/env python3
"""
plan.py — read the measurements and decide the edit.

    python3 plan.py analysis.json --out plan.json \
        --platform reels --pace tight --zoom punch --captions subtitles.srt

The plan is plain JSON so it can be argued with, diffed and re-run:

  segments   every keep range: source in/out, output in/out, focus, zoom
  look       exposure/white-balance/look numbers derived from real measurements
  audio      denoise, EQ, loudness targets, measured loudness values
  captions   where the subtitles come from and how they were remapped
  decisions  one line per choice, in plain language — this is the report
  warnings   things a human must know (clipping, no face, silent file, ...)

Rules the planner will not break:
  * never cut inside a speech range — only dead air and pad;
  * never invent a caption — absent text is reported, not generated;
  * never claim a correction it did not measure — an unmeasured value is left at neutral.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    ToolError, clamp, eprint, human_time, percentile, read_json, smooth_series,
    write_json,
)
import filters  # noqa: E402

PLATFORMS = {
    # name: (width, height, max_seconds, bottom_safe_fraction, loudness)
    "reels":     (1080, 1920, 90, 0.16, -14.0),
    "tiktok":    (1080, 1920, 600, 0.18, -14.0),
    "shorts":    (1080, 1920, 180, 0.16, -14.0),
    "youtube":   (1920, 1080, None, 0.10, -14.0),
    "yt-vertical": (1080, 1920, 180, 0.16, -14.0),
    "square":    (1080, 1080, 600, 0.12, -14.0),
    "podcast":   (1920, 1080, None, 0.10, -16.0),
    "broadcast": (1920, 1080, None, 0.10, -23.0),
    "original":  (None, None, None, 0.12, -14.0),
}

PACE = {
    # name: (interior gap longer than this is shortened, kept gap)
    "tight":   (0.30, 0.16),
    "natural": (0.60, 0.30),
    "loose":   (1.10, 0.55),
}

HEAD_LEAD = 0.18      # seconds kept before the first word
TAIL_HOLD = 0.45      # seconds kept after the last word
EDGE_PAD = 0.06       # widen each speech range so a word onset is never clipped


def _speech_ranges(analysis: dict, dur: float) -> list[dict]:
    au = analysis.get("audio") or {}
    ranges = au.get("speech_ranges")
    if ranges:
        out = []
        for r in ranges:
            out.append({"start": max(0.0, r["start"] - EDGE_PAD),
                        "end": min(dur, r["end"] + EDGE_PAD)})
        return out
    return []


def _merge(ranges: list[dict], gap: float) -> list[dict]:
    if not ranges:
        return []
    out = [dict(ranges[0])]
    for r in ranges[1:]:
        if r["start"] - out[-1]["end"] <= gap:
            out[-1]["end"] = max(out[-1]["end"], r["end"])
        else:
            out.append(dict(r))
    return out


def build_segments(analysis: dict, opts: dict, decisions: list[str], warnings: list[str]) -> list[dict]:
    dur = analysis["probe"]["duration"] or 0.0
    pace_open, pace_keep = PACE[opts["pace"]]
    src_ranges = _speech_ranges(analysis, dur)

    if opts.get("no_cut") or not src_ranges:
        if not src_ranges and not opts.get("no_cut"):
            warnings.append("no speech detected — nothing was cut; check the audio track")
        start = opts.get("trim_start") or 0.0
        end = opts.get("trim_end") or dur
        keep = [{"start": max(0.0, start), "end": min(dur, end)}]
        decisions.append(f"kept the whole range {human_time(keep[0]['start'])}–{human_time(keep[0]['end'])}")
    else:
        first = max(0.0, src_ranges[0]["start"] - HEAD_LEAD)
        last = min(dur, src_ranges[-1]["end"] + TAIL_HOLD)
        keep = [{"start": first, "end": min(dur, src_ranges[-1]["end"] + TAIL_HOLD)}]
        keep = [{"start": first, "end": last}]
        decisions.append(
            f"head trimmed {human_time(src_ranges[0]['start'])} of silence, "
            f"tail trimmed {human_time(max(0.0, dur - src_ranges[-1]['end']))}"
        )

        # interior gaps
        gaps = []
        for a, b in zip(src_ranges, src_ranges[1:]):
            gap = b["start"] - a["end"]
            if gap > pace_open:
                gaps.append((a["end"], b["start"], gap))
        if gaps:
            removed = sum(g - pace_keep for _, _, g in gaps)
            decisions.append(
                f"{len(gaps)} pause(s) longer than {pace_open:.2f}s shortened to {pace_keep:.2f}s "
                f"(-{removed:.1f}s of dead air)")
        else:
            decisions.append(f"no pause longer than {pace_open:.2f}s — nothing cut inside the take")

    # build the keep list from speech ranges with the chosen gap policy
    if src_ranges and not opts.get("no_cut"):
        segs = []
        cur = {"start": max(0.0, src_ranges[0]["start"] - HEAD_LEAD),
               "end": src_ranges[0]["end"]}
        for r in src_ranges[1:]:
            gap = r["start"] - cur["end"]
            if gap <= pace_open:
                cur["end"] = r["end"]
            else:
                segs.append(cur)
                cur = {"start": r["start"] - min(pace_keep, max(0.0, gap)), "end": r["end"]}
        segs.append(cur)
        segs[-1]["end"] = min(dur, segs[-1]["end"] + TAIL_HOLD)
        keep = [{"start": round(max(0.0, s["start"]), 3), "end": round(min(dur, s["end"]), 3)}
                for s in segs if s["end"] - s["start"] > 0.12]
    elif opts.get("no_cut"):
        keep = [{"start": opts.get("trim_start") or 0.0,
                 "end": opts.get("trim_end") or dur}]

    # max duration: only ever remove air, never words
    max_dur = opts.get("max_duration")
    if max_dur:
        total = sum(k.get("end", k.get("src_end", 0)) - k.get("start", k.get("src_start", 0))
                    for k in keep)
        if total > max_dur:
            warnings.append(
                f"the cut is {human_time(total)} but you asked for {human_time(max_dur)}; "
                f"words were not removed to fit — raise --pace tight or cut manually")
        decisions.append(f"target length {human_time(max_dur)}; cut length {human_time(total)}")

    # normalise keys (src_start/src_end) and lay out the output timeline
    out_t = 0.0
    for k in keep:
        k["src_start"] = round(float(k.pop("start", k.get("src_start"))), 3)
        k["src_end"] = round(float(k.pop("end", k.get("src_end"))), 3)
        k["out_start"] = round(out_t, 3)
        out_t += k["src_end"] - k["src_start"]
        k["out_end"] = round(out_t, 3)
    return keep


def segment_focus(analysis: dict, seg: dict) -> tuple[float, float, int]:
    """Median face centre inside this keep range, mapped through the cover crop later."""
    samples = analysis["video"].get("samples") or []
    boxes = [s["face"] for s in samples
             if s.get("face") and seg["src_start"] - 0.4 <= s["t"] <= seg["src_end"] + 0.4]
    if not boxes:
        return 0.5, 0.42, 0
    cx = [b[0] + b[2] / 2 for b in boxes]
    cy = [b[1] + b[3] / 2 for b in boxes]
    from _common import median
    mx, my = median(cx), median(cy)
    return (mx if mx is not None else 0.5), (my if my is not None else 0.42), len(boxes)


def plan_look(analysis: dict, opts: dict, decisions: list[str], warnings: list[str]) -> dict:
    video = analysis["video"]
    look = {"contrast": 1.0, "saturation": 1.0, "gamma": 1.0, "sharpen": 0.0,
            "vignette": False, "denoise_video": bool(opts.get("denoise_video"))}
    mode = opts.get("light", "auto")
    if mode == "off":
        decisions.append("colour/exposure left untouched (--light off)")
        return look

    # ---- exposure from the subject's own brightness when a face is known
    face_luma = (video.get("face_luma") or {}).get("median")
    frame_luma = (video.get("luma") or {}).get("median")
    target = 132.0
    ref = face_luma if face_luma is not None else frame_luma
    if ref is not None:
        delta = (target - ref) / 255.0
        delta = clamp(delta, -0.14, 0.14)
        if abs(delta) >= 0.004:
            look["brightness"] = round(delta, 4)
            src = "subject" if face_luma is not None else "frame"
            decisions.append(f"exposure: {src} luma {ref:.0f} → +{delta * 100:.1f}% brightness "
                             f"(target {target:.0f})")
        else:
            decisions.append(f"exposure: already on target ({ref:.0f} luma) — left alone")
    else:
        warnings.append("exposure not measured (no usable brightness samples) — left neutral")

    # ---- temporal exposure drift → smooth correction curve
    swing = (video.get("luma") or {}).get("swing")
    samples = video.get("samples") or []
    if opts.get("flicker", True) and samples and swing and swing > 18:
        vals = [s["y"] for s in samples]
        vals = smooth_series(vals, window=5, passes=2)
        med = sorted(vals)[len(vals) // 2]
        curve = [(s["t"], clamp((med - v) / 255.0, -0.10, 0.10))
                 for s, v in zip(samples, vals)]
        curve = [(t, v) for t, v in curve if abs(v) >= 0.002]
        if len(curve) >= 4:
            look["flicker_curve"] = [(round(t, 2), round(v, 4)) for t, v in curve]
            decisions.append(f"exposure swing {swing:.0f} luma → temporal correction curve applied")

    # ---- white balance (grey-world, gentle and clamped)
    ctx = video.get("color") or {}
    if ctx.get("gains"):
        g = ctx["gains"]
        look["white_balance"] = {k: round(clamp(v, -0.09, 0.09), 4)
                                 for k, v in g.items() if abs(v) > 0.004}
        if look["white_balance"]:
            decisions.append("white balance: neutralised a colour cast "
                             f"({', '.join(f'{k}{v:+.3f}' for k, v in look['white_balance'].items())})")

    # ---- the actual look
    grade = opts.get("grade", "clean")
    if grade == "warm":
        look.update(contrast=1.04, saturation=1.06,
                    white_balance={**(look.get("white_balance") or {}), "rm": 0.03, "bm": -0.02})
        decisions.append("grade: warm (slightly lifted midtones, small saturation lift)")
    elif grade == "cinematic":
        look.update(contrast=1.08, saturation=0.96, vignette=True, sharpen=0.6)
        decisions.append("grade: cinematic (contrast, mild desaturation, vignette, sharpening)")
    elif grade == "crisp":
        look.update(contrast=1.05, saturation=1.02, sharpen=0.9)
        decisions.append("grade: crisp (contrast + unsharp for social feeds)")
    else:
        look.update(contrast=1.02, sharpen=0.4)
        decisions.append("grade: clean (near-neutral, light sharpening for re-encode loss)")

    sharpen_median = (video.get("sharpness") or {}).get("median")
    if sharpen_median is not None and sharpen_median < 60:
        warnings.append(f"source looks soft (Laplacian {sharpen_median:.0f}) — sharpening is "
                        f"limited; a sharper capture would help more")
    if video.get("motion", {}).get("handheld"):
        warnings.append("handheld shake detected — pass --stabilize for a two-pass vidstab fix")
    return look


def plan_geometry(analysis: dict, keeps: list[dict], opts: dict, out_w: int, out_h: int,
                  decisions: list[str], warnings: list[str]) -> dict:
    src = analysis["probe"]
    crop_mode = opts.get("crop", "face")
    face_boxes = analysis["video"].get("face") or {}
    have_face = (face_boxes.get("detected") or 0) >= 2

    segments = []
    for seg in keeps:
        fx, fy, n = segment_focus(analysis, seg)
        if crop_mode == "face" and not have_face:
            crop_mode_effective = "center"
        else:
            crop_mode_effective = crop_mode
        if crop_mode_effective == "center":
            fx, fy = 0.5, 0.42
        elif crop_mode_effective == "top":
            fx, fy = 0.5, 0.25
        elif crop_mode_effective == "left":
            fx, fy = 0.3, 0.45
        elif crop_mode_effective == "right":
            fx, fy = 0.7, 0.45
        mx, my = filters.cover_map(src["width"], src["height"], out_w, out_h, fx, fy)
        segments.append({**seg, "focus": (round(mx, 4), round(my, 4)), "faces_in_segment": n})

    if opts.get("_fit_reason"):
        decisions.append("layout: " + opts["_fit_reason"])
    if crop_mode == "face" and have_face:
        rate = face_boxes.get("detection_rate") or 0
        drift = face_boxes.get("drift")
        decisions.append(
            f"reframe: speaker centred per take (face in {rate * 100:.0f}% of samples, "
            f"drift {drift}) — {out_w}×{out_h}")
        if rate < 0.4:
            warnings.append("face found in fewer than 40% of samples — reframe falls back to centre "
                            "between detections; check the result")
    elif crop_mode == "face":
        decisions.append(f"reframe: centre crop to {out_w}×{out_h} — no face to follow")
        warnings.append("no face detected: the crop is centred, not subject-aware. If this is a "
                        "talking head, check that the subject is not in profile or in shadow.")
    elif crop_mode != "none":
        decisions.append(f"reframe: {crop_mode} crop to {out_w}×{out_h}")

    total = segments[-1]["out_end"] if segments else 0.0
    zoom_mode = opts.get("zoom", "punch")
    if crop_mode == "none":
        zoom_mode = "none"
    geo = {
        "crop": crop_mode,
        "zoom_mode": zoom_mode,
        "zoom_amplitude": opts.get("zoom_amp", 0.06),
        "zoom_curve": filters.build_zoom_curve(segments, zoom_mode, opts.get("zoom_amp", 0.06), total),
        "pan": True,
    }
    fx_curve, fy_curve = filters.build_focus_curve(segments, total)
    geo["focus_x"], geo["focus_y"] = fx_curve, fy_curve
    if zoom_mode != "none":
        decisions.append(f"zoom: {zoom_mode} (max +{opts.get('zoom_amp', 0.06) * 100:.0f}%), "
                         f"one move per take")
    else:
        decisions.append("zoom: none (static framing)")
    return {"geometry": geo, "segments": segments}


def plan_audio(analysis: dict, opts: dict, decisions: list[str], warnings: list[str]) -> dict:
    au = analysis.get("audio") or {}
    loud = au.get("loudness") or {}
    floor = au.get("noise_floor_db")
    audio = {"highpass": True, "voice_eq": True, "deess": False,
             "loudnorm": {"target": opts.get("loudness")}, "denoise": False}

    if au.get("clipped"):
        warnings.append(f"source peaks at {au.get('peak_db')} dB — clipping cannot be undone; "
                        f"record lower next time")

    if opts.get("denoise_audio", True):
        if floor is None:
            warnings.append("noise floor not measured — noise reduction left off")
        elif floor > -30:
            audio.update(denoise=True, nr=18, nf=round(floor))
            warnings.append(f"noisy source (floor {floor:.0f} dB) — aggressive noise reduction applied")
        elif floor > -45:
            audio.update(denoise=True, nr=12, nf=round(floor))
            decisions.append(f"noise: floor {floor:.0f} dB → afftdn 12 dB")
        else:
            decisions.append(f"noise: floor {floor:.0f} dB is already clean — no denoise")
    else:
        decisions.append("noise: denoise disabled by request")

    if loud.get("input_i") is not None:
        audio["loudnorm"]["measured_i"] = loud["input_i"]
        audio["loudnorm"]["measured_tp"] = loud.get("input_tp")
        audio["loudnorm"]["measured_lra"] = loud.get("input_lra") or 11
        audio["loudnorm"]["measured_thresh"] = loud.get("input_thresh") or -30
        audio["loudnorm"]["offset"] = 0
        gain = opts["loudness"] - loud["input_i"]
        decisions.append(f"loudness: {loud['input_i']:.1f} LUFS → {opts['loudness']:.1f} LUFS "
                         f"({gain:+.1f} dB), true peak capped at -1.5 dBTP")
    else:
        warnings.append("loudness could not be measured — single-pass normalisation only")
    return audio


def plan_captions(analysis: dict, keeps: list[dict], opts: dict, decisions: list[str],
                  warnings: list[str], out_w: int, out_h: int) -> dict:
    path = opts.get("captions")
    margin = int(round(out_h * opts["safe_fraction"]))
    cap = {"status": "absent", "source": None, "margin": margin,
           "note": "no subtitles supplied — the video is delivered without captions"}
    if not path:
        decisions.append("captions: none supplied")
        return cap
    p = Path(path)
    if not p.is_file():
        warnings.append(f"captions file not found: {path}")
        return cap
    cues = _count_srt(p)
    if cues == 0:
        warnings.append(f"{p.name} has no readable cues — captions skipped")
        return cap
    dur = analysis["probe"]["duration"] or 0
    cap.update(status="supplied", source=str(p), cues_in=cues,
               shift=opts.get("caption_shift", 0.0))
    if opts.get("captions_in_output_time"):
        cap["shift"] = 0.0
        cap["note"] = "cue times taken as output times (no remap)"
        decisions.append("captions: supplied in output time — used as-is")
    else:
        decisions.append(f"captions: {cues} cues remapped through {len(keeps)} cut(s)")
    return cap


def _count_srt(p: Path) -> int:
    try:
        txt = p.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return 0
    return sum(1 for line in txt.splitlines() if "-->" in line)


# --------------------------------------------------------------------------- main

def make_plan(analysis: dict, opts: dict) -> dict:
    decisions: list[str] = []
    warnings: list[str] = []
    probe = analysis["probe"]
    if not probe.get("has_audio"):
        warnings.append("source has no audio track — the output will be silent")
    if probe.get("duration") is None:
        raise ToolError("could not read the source duration", kind="input")

    plat = opts.get("platform", "reels")
    pw, ph, pmax, safe, plufs = PLATFORMS.get(plat, PLATFORMS["reels"])
    out_w = opts.get("width") or pw or probe["width"]
    out_h = opts.get("height") or ph or probe["height"]
    out_w -= out_w % 2
    out_h -= out_h % 2

    # how much magnification a cover crop needs; beyond ~1.6x the face gets uncomfortably
    # large on vertical platforms, so "auto" switches to a blurred pad instead.
    src_ar = (probe["width"] or 1) / (probe["height"] or 1)
    out_ar = out_w / out_h
    mag = 1.0
    if out_ar < src_ar and (probe["width"] or 0):
        mag = (out_h / (probe["height"] or 1))
        mag = max(1.0, ((probe["height"] or 1) * 0 + out_w) / max(1.0, (probe["height"] or 1) * out_ar))
    fit = opts.get("fit", "auto")
    if fit == "auto":
        # crop keeps out_ar/src_ar of the source width → magnification = src_ar/out_ar
        magnification = src_ar / out_ar if out_ar and src_ar else 1.0
        face_w = (analysis["video"].get("face") or {}).get("median_width") or 0.0
        projected = face_w * magnification if face_w else 0.0
        fit = "pad" if (magnification > 1.55 and projected > 0.5) else "cover"
        opts["_fit_reason"] = (f"auto: magnification {magnification:.2f}x, projected face "
                               f"{projected * 100:.0f}% of frame width → {fit}")
    opts["fit"] = fit
    fps = opts.get("fps") or min(60.0, probe.get("fps") or 30.0)
    opts["safe_fraction"] = opts.get("safe_fraction", safe)
    if opts.get("loudness") is None:
        opts["loudness"] = plufs

    keeps = build_segments(analysis, opts, decisions, warnings)
    geo = plan_geometry(analysis, keeps, opts, out_w, out_h, decisions, warnings)
    look = plan_look(analysis, opts, decisions, warnings)
    audio = plan_audio(analysis, opts, decisions, warnings)
    caps = plan_captions(analysis, keeps, opts, decisions, warnings, out_w, out_h)

    duration_out = keeps[-1]["out_end"] if keeps else 0.0
    duration_in = probe["duration"] or 0.0
    if pmax and duration_out > pmax:
        warnings.append(f"{duration_out:.0f}s exceeds the {plat} limit of {pmax}s")

    plan = {
        "version": 1,
        "source": analysis["source"],
        "source_probe": probe,
        "output": {"path": opts.get("out"), "platform": plat, "width": out_w, "height": out_h,
                   "fps": round(fps, 3), "duration": round(duration_out, 3),
                   "crop": opts.get("crop", "face"), "fit": opts["fit"],
                   "anchor": opts.get("anchor", 0.34),
                   "band": opts.get("band", 0.62)},
        "summary": {
            "duration_in": round(duration_in, 3),
            "duration_out": round(duration_out, 3),
            "removed": round(max(0.0, duration_in - duration_out), 3),
            "cuts": len(keeps),
            "pace": opts.get("pace"),
        },
        "segments": geo["segments"],
        "geometry": geo["geometry"],
        "look": look,
        "audio": audio,
        "captions": caps,
        "options": {k: v for k, v in opts.items()
                    if k not in ("safe_fraction",) and not k.startswith("_")},
        "decisions": decisions,
        "warnings": warnings,
    }
    return plan


def summary_lines(plan: dict) -> list[str]:
    o, s = plan["output"], plan["summary"]
    lines = [
        f"output    {o['width']}×{o['height']} · {o['fps']} fps · {o['platform']} · "
        f"{human_time(s['duration_out'])} (from {human_time(s['duration_in'])}, "
        f"-{human_time(s['removed'])})",
        f"cuts      {s['cuts']} keep range(s), pace «{s['pace']}»",
    ]
    lines.append("decisions")
    lines += [f"  · {d}" for d in plan["decisions"]]
    if plan["warnings"]:
        lines.append("warnings")
        lines += [f"  ! {w}" for w in plan["warnings"]]
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description="Turn measurements into an edit plan.")
    ap.add_argument("analysis")
    ap.add_argument("--out", default=None, help="plan.json (default: <analysis>.plan.json)")
    ap.add_argument("--out-video", default=None, help="where the final MP4 should go")
    ap.add_argument("--platform", default="reels", choices=sorted(PLATFORMS))
    ap.add_argument("--width", type=int, default=None)
    ap.add_argument("--height", type=int, default=None)
    ap.add_argument("--fps", type=float, default=None)
    ap.add_argument("--pace", default="tight", choices=sorted(PACE))
    ap.add_argument("--max-duration", type=float, default=None)
    ap.add_argument("--trim-start", type=float, default=None)
    ap.add_argument("--trim-end", type=float, default=None)
    ap.add_argument("--no-cut", action="store_true", help="keep everything; only reframe/grade")
    ap.add_argument("--crop", default="face", choices=["face", "center", "top", "left", "right", "none"])
    ap.add_argument("--fit", default="auto", choices=["auto", "cover", "pad"],
                    help="cover = tight crop, pad = whole subject on a blurred fill")
    ap.add_argument("--anchor", type=float, default=0.34, help="pad: vertical position of the subject")
    ap.add_argument("--band", type=float, default=0.62, help="pad: share of the height the video band takes")
    ap.add_argument("--zoom", default="punch", choices=["none", "in", "out", "punch", "pulse"])
    ap.add_argument("--zoom-amp", type=float, default=0.06)
    ap.add_argument("--grade", default="clean", choices=["clean", "warm", "cinematic", "crisp"])
    ap.add_argument("--light", default="auto", choices=["auto", "manual", "off"])
    ap.add_argument("--denoise-audio", dest="denoise_audio", action="store_true", default=True)
    ap.add_argument("--no-denoise-audio", dest="denoise_audio", action="store_false")
    ap.add_argument("--denoise-video", action="store_true")
    ap.add_argument("--flicker", action="store_true", default=True)
    ap.add_argument("--no-flicker", dest="flicker", action="store_false")
    ap.add_argument("--loudness", type=float, default=None, help="target LUFS (default by platform)")
    ap.add_argument("--captions", default=None, help="SRT/VTT file")
    ap.add_argument("--caption-style", default="bold", choices=["minimal", "bold", "boxed", "karaoke"])
    ap.add_argument("--caption-size", type=int, default=None, help="font size in px (default 4 percent of height)")
    ap.add_argument("--caption-font", default=None, help="font file or family name")
    ap.add_argument("--caption-shift", type=float, default=0.0)
    ap.add_argument("--captions-in-output-time", action="store_true")
    ap.add_argument("--stabilize", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    analysis = read_json(args.analysis)
    opts = {k: v for k, v in vars(args).items()
            if k not in ("analysis", "out", "json")}
    opts["out"] = args.out_video
    plan = make_plan(analysis, opts)
    out = args.out or str(Path(args.analysis).with_suffix("")) + ".plan.json"
    write_json(out, plan)
    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2)[:6000])
    else:
        for line in summary_lines(plan):
            print(line)
        print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
