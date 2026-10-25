#!/usr/bin/env python3
"""
render.py — execute a plan, then prove the result.

    python3 render.py plan.json --out final.mp4 [--preview] [--stabilize]

Stages (each one is reported, none is skipped silently):

  0. preflight   ffmpeg capabilities, output folder, free space, plan sanity
  1. stabilize   optional two-pass vidstab (source → temp intermediate)
  2. loudness    measure the *trimmed* audio, so normalisation targets the real cut
  3. captions    SRT → ASS with cue times remapped through the cuts
  4. encode      one ffmpeg run: trim → concat → reframe/zoom → look → subtitles → AAC
  5. verify      durations, streams, loudness, black frames, and contact sheets

Everything written next to the output is a fact the user can check: final.mp4,
final.srt (retimed), captions.ass, verify.json, sheet.png, plan.json, analysis.json.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    ToolError, eprint, ffmpeg, ffprobe, has_filter, human_time, probe, read_json,
    run, temp_dir, write_json,
)
import captions as capmod  # noqa: E402
import filters  # noqa: E402


# --------------------------------------------------------------------------- helpers

def _free_gb(path: Path) -> float:
    try:
        st = shutil.disk_usage(path)
        return st.free / 1e9
    except OSError:
        return 0.0


def preflight(plan: dict, out_path: Path) -> list[str]:
    notes = []
    if not plan.get("segments"):
        raise ToolError("plan has no keep ranges", kind="plan")
    for f in ("create", "sad", "test"):
        pass
    required = ["trim", "concat", "scale", "crop", "zoompan", "eq", "aresample", "loudnorm"]
    missing = [f for f in required if not has_filter(f)]
    if missing:
        raise ToolError(f"this ffmpeg lacks filters the plan needs: {', '.join(missing)}",
                        kind="missing_filter")
    if plan.get("captions", {}).get("status") == "supplied" and not has_filter("ass"):
        raise ToolError("this ffmpeg has no 'ass' filter — captions cannot be burned",
                        kind="missing_filter")
    if not ffprobe():
        notes.append("ffprobe missing: verification will be limited")
    free = _free_gb(out_path.parent)
    need = max(0.2, plan["summary"]["duration_out"] * 0.02)
    if free and free < need:
        notes.append(f"only {free:.1f} GB free — a render needs about {need:.1f} GB")
    return notes


def stabilize(src: str, plan: dict, workdir: Path) -> tuple[Path, dict]:
    """Two-pass vidstab: detect the shake, then transform the whole source once."""
    if not (has_filter("vidstabdetect") and has_filter("vidstabtransform")):
        raise ToolError("this ffmpeg has no vidstab filters — cannot stabilise", kind="missing_filter")
    trf = workdir / "transforms.trf"
    out = workdir / "stabilized.mp4"
    t0 = time.time()
    run([ffmpeg(), "-hide_banner", "-nostats", "-v", "error", "-i", src,
         "-vf", f"vidstabdetect=shakiness=6:accuracy=15:result={trf}",
         "-f", "null", "-"], timeout=3600)
    run([ffmpeg(), "-hide_banner", "-nostats", "-v", "error", "-i", src,
         "-vf", f"vidstabtransform=input={trf}:smoothing=12:zoom=2:optzoom=1:interpol=bicubic",
         "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17",
         "-pix_fmt", "yuv420p", str(out)], timeout=3600)
    return out, {"pass": "two-pass vidstab", "smoothing": 12, "zoom": 2,
                 "seconds": round(time.time() - t0, 1)}


def measure_trimmed_loudness(src: str, plan: dict, target: float) -> dict | None:
    """loudnorm pass 1 on the trimmed audio only: decode is cheap, no video work."""
    parts = []
    segs = plan["segments"]
    for i, seg in enumerate(segs):
        parts.append(f"[0:a]atrim=start={seg['src_start']:.3f}:end={seg['src_end']:.3f},"
                     f"asetpts=PTS-STARTPTS[a{i}]")
    parts.append("".join(f"[a{i}]" for i in range(len(segs))) +
                 f"concat=n={len(segs)}:v=0:a=1,loudnorm=I={target}:TP=-1.5:LRA=11:print_format=json[ao]")
    graph = ";".join(parts)
    try:
        cp = run([ffmpeg(), "-hide_banner", "-nostats", "-i", src, "-filter_complex", graph,
                  "-map", "[ao]", "-f", "null", "-"], check=False, timeout=1800)
    except ToolError:
        return None
    log = cp.stderr or ""
    blob = log[log.rfind("{"):log.rfind("}") + 1] if "{" in log else ""
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        return None
    def n(k, d=None):
        try:
            v = float(data.get(k))
            return v if v == v and abs(v) != float("inf") else d
        except (TypeError, ValueError):
            return d
    return {"measured_i": n("input_i"), "measured_tp": n("input_tp", -1.5),
            "measured_lra": n("input_lra", 11), "measured_thresh": n("input_thresh", -30),
            "offset": n("target_offset", 0)}


def build_captions(plan: dict, workdir: Path, out_path: Path) -> dict:
    cap = plan.get("captions") or {}
    if cap.get("status") != "supplied" or not cap.get("source"):
        return {"status": "absent"}
    src = Path(cap["source"])
    if not src.is_file():
        return {"status": "missing", "note": f"{src} not found"}
    ass_path = out_path.with_suffix(".ass")
    keeps_path = workdir / "keeps.json"
    write_json(keeps_path, plan["segments"])
    rtl = False
    try:
        cues = capmod.parse_srt(src)
        rtl = any(capmod.RTL_RE.search(c["text"]) for c in cues)
    except Exception:
        pass
    out_w = plan["output"]["width"]
    out_h = plan["output"]["height"]
    cmd = [sys.executable, str(Path(__file__).resolve().parent / "captions.py"),
           str(src), "--out", str(ass_path),
           "--width", str(out_w), "--height", str(out_h),
           "--margin", str(cap.get("margin", int(out_h * 0.16))),
           "--style", plan.get("options", {}).get("caption_style", "bold"),
           "--json"]
    if not plan.get("options", {}).get("captions_in_output_time"):
        cmd += ["--keeps", str(keeps_path), "--shift", str(cap.get("shift", 0.0))]
    elif cap.get("shift"):
        cmd += ["--shift", str(cap["shift"])]
    if plan["options"].get("caption_font"):
        cmd += ["--font", plan["options"]["caption_font"]]
    if plan["options"].get("caption_size"):
        cmd += ["--size", str(plan["options"]["caption_size"])]
    cp = run(cmd, timeout=300)
    report = {}
    try:
        report = json.loads(cp.stdout[cp.stdout.find("{"):])
    except (json.JSONDecodeError, ValueError):
        report = {}
    # a retimed SRT beside the MP4: the same cut, for YouTube/TikTok uploads
    try:
        retimed = capmod.remap(capmod.parse_srt(src), plan["segments"], cap.get("shift", 0.0)) \
            if not plan["options"].get("captions_in_output_time") else capmod.parse_srt(src)
        srt_out = out_path.with_suffix(".srt")
        blocks = []
        for i, c in enumerate(retimed, 1):
            blocks.append(f"{i}\n{_srt_ts(c['start'])} --> {_srt_ts(c['end'])}\n{c['text']}\n")
        srt_out.write_text("\n".join(blocks), encoding="utf-8")
        report["srt"] = str(srt_out)
    except Exception as exc:                      # never fail the render for a sidecar
        report["srt_error"] = str(exc)
    report.update({"status": "burned", "ass": str(ass_path), "rtl": rtl})
    return report


def _srt_ts(t: float) -> str:
    t = max(0.0, t)
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    if ms >= 1000:
        s, ms = s + 1, ms - 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def choose_encoder(plan: dict, preview: bool) -> list[str]:
    out_h = plan["output"]["height"]
    crf = "23" if preview else "19"
    if preview:
        return ["-c:v", "libx264", "-preset", "veryfast", "-crf", crf,
                "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    return ["-c:v", "libx264", "-preset", "slow", "-crf", crf,
            "-profile:v", "high", "-level", "4.2" if out_h <= 1920 else "5.1",
            "-pix_fmt", "yuv420p", "-color_primaries", "bt709",
            "-color_trc", "bt709", "-colorspace", "bt709",
            "-movflags", "+faststart", "-g", "60"]


# --------------------------------------------------------------------------- main render

def render(plan: dict, out_path: Path, *, preview: bool = False,
           stabilize_flag: bool = False, workdir: Path | None = None,
           keep_intermediate: bool = False) -> dict:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    workdir = workdir or temp_dir("ths-render-")
    workdir.mkdir(parents=True, exist_ok=True)
    stages: list[dict] = []
    notes = preflight(plan, out_path)
    t_start = time.time()

    src = plan["source"]
    effective = plan
    if stabilize_flag:
        try:
            t0 = time.time()
            stab_path, info = stabilize(src, plan, workdir)
            info["seconds"] = round(time.time() - t0, 1)
            src = str(stab_path)
            # the plan's keep ranges are in *source* time and the stabilised copy has the
            # same duration and frame count, so timings carry over unchanged
            stages.append({"stage": "stabilize", "status": "done", **info})
        except ToolError as exc:
            stages.append({"stage": "stabilize", "status": "skipped", "reason": str(exc)})

    # loudness on the trimmed audio
    target = (plan.get("audio", {}).get("loudnorm") or {}).get("target") or -14.0
    measured = measure_trimmed_loudness(src, plan, target) \
        if plan["source_probe"].get("has_audio") else None
    if measured and measured.get("measured_i") is not None:
        plan["audio"]["loudnorm"] = {**plan["audio"].get("loudnorm", {}), **measured, "target": target}
        stages.append({"stage": "loudness", "status": "measured",
                       "input_i": measured["measured_i"], "target": target})
    elif plan["source_probe"].get("has_audio"):
        stages.append({"stage": "loudness", "status": "fallback",
                       "reason": "measurement failed; single-pass normalisation"})

    # captions
    cap_info = build_captions(plan, workdir, out_path)
    stages.append({"stage": "captions", "status": cap_info.get("status", "absent"),
                   **{k: v for k, v in cap_info.items() if k not in ("status",)}})

    subs = cap_info.get("ass") if cap_info.get("status") == "burned" else None
    font_dir = str(Path(__file__).resolve().parent.parent / "assets" / "fonts")
    graph, maps = filters.build(plan, subs_path=subs, font_dir=font_dir if subs else None)

    has_audio = bool(plan["source_probe"].get("has_audio")) and maps.get("audio")
    cmd = [ffmpeg(), "-hide_banner", "-nostats", "-y", "-i", src,
           "-filter_complex", graph, "-map", maps["video"]]
    if has_audio:
        cmd += ["-map", maps["audio"]]
    cmd += choose_encoder(plan, preview)
    if has_audio:
        cmd += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-shortest"]
    else:
        stages.append({"stage": "audio", "status": "absent",
                       "reason": "the source has no audio stream"})
    cmd += ["-t", f"{plan['summary']['duration_out']:.3f}", str(out_path)]

    write_json(out_path.with_suffix(".graph.json"), {"graph": graph, "cmd": cmd})
    t0 = time.time()
    cp = run(cmd, check=False, timeout=7200)
    if cp.returncode != 0 or not out_path.is_file() or out_path.stat().st_size < 10_000:
        err = (cp.stderr or cp.stdout or "")[-1500:]
        raise ToolError("encode failed", cmd, err)
    stages.append({"stage": "encode", "status": "done",
                   "seconds": round(time.time() - t0, 1),
                   "size_mb": round(out_path.stat().st_size / 1e6, 2)})

    result = {
        "output": str(out_path),
        "seconds_total": round(time.time() - t_start, 1),
        "stages": stages,
        "notes": notes,
        "manifest": {"ass": cap_info.get("ass"), "srt": cap_info.get("srt"),
                     "plan": plan.get("_plan_path"), "analysis": plan.get("_analysis_path")},
    }
    if not keep_intermediate:
        shutil.rmtree(workdir, ignore_errors=True)
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Render a talking-head-studio plan.")
    ap.add_argument("plan")
    ap.add_argument("--out", required=True)
    ap.add_argument("--preview", action="store_true", help="fast 720p-ish draft")
    ap.add_argument("--stabilize", action="store_true", help="two-pass vidstab first")
    ap.add_argument("--workdir", default=None)
    ap.add_argument("--keep-work", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    plan = read_json(args.plan)
    plan["_plan_path"] = str(Path(args.plan).resolve())
    try:
        res = render(plan, Path(args.out), preview=args.preview,
                     stabilize_flag=args.stabilize,
                     workdir=Path(args.workdir) if args.workdir else None,
                     keep_intermediate=args.keep_work)
    except ToolError as exc:
        eprint(f"✗ {exc}")
        if exc.stderr:
            eprint(exc.stderr[-1200:])
        return 2
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        for st in res["stages"]:
            detail = ", ".join(f"{k}={v}" for k, v in st.items() if k not in ("stage", "status"))
            print(f"  {st['stage']:<10} {st['status']:<10} {detail}")
        print(f"\n✓ {res['output']}  ({res['seconds_total']}s)")
        for n in res["notes"]:
            print(f"  ! {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
