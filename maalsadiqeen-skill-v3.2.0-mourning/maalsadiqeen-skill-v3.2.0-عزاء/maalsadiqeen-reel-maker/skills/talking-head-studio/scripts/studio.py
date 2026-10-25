#!/usr/bin/env python3
"""
studio.py — one command from a talking-head recording to a finished, verified video.

    python3 studio.py TALK.mp4 --out final.mp4
    python3 studio.py TALK.mp4 --out final.mp4 --captions talk.srt --preset social
    python3 studio.py TALK.mp4 --plan-only            # measure + decide, no render

Presets are option bundles, not pipelines — the same five stages always run:

    social     reels/tiktok/shorts: tight pace, punch zoom, crisp grade, bold captions
    clean      a calm, faithful cut: natural pace, slow push-in, clean grade
    cinematic  contrast, vignette, slow zoom, looser pauses
    podcast    landscape, no reframe, gentle grade, no zoom
    raw        no cut, no grade, no zoom — only subtitles and loudness if asked

Stages, each reported with what it measured:
    0 bootstrap   check (never install without --install)
    1 analyze     silence map, loudness, noise floor, face, exposure, shake
    2 plan        keep ranges, reframe, look, captions, loudness → plan.json
    3 render      one ffmpeg graph: trim → concat → reframe → look → subtitles → AAC
    4 verify      duration, frame, fps, audio, loudness, freeze, face, contact sheet

Exit codes: 0 delivered, 1 verification failed, 2 could not run, 3 needs a decision.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(HERE))

from _common import (  # noqa: E402
    ToolError, eprint, ffmpeg, ffprobe, human_time, read_json, write_json, write_text,
)

PRESETS = {
    # platform   pace      zoom      grade       captions  fit      loudness
    "social":    dict(platform="reels", pace="tight", zoom="punch", grade="crisp",
                      caption_style="bold", fit="auto"),
    "clean":     dict(platform="reels", pace="natural", zoom="in", grade="clean",
                      caption_style="bold", fit="auto"),
    "cinematic": dict(platform="reels", pace="loose", zoom="in", grade="cinematic",
                      caption_style="minimal", fit="auto"),
    "podcast":   dict(platform="podcast", pace="natural", zoom="none", grade="clean",
                      caption_style="bold", fit="cover"),
    "raw":       dict(platform="original", pace="loose", zoom="none", grade="clean",
                      caption_style="minimal", fit="cover"),
}


def _run(script: str, args: list[str], *, quiet: bool = True) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(HERE / script)] + args
    cp = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if cp.returncode != 0:
        raise ToolError(f"{script} failed", cmd, (cp.stderr or cp.stdout)[-1500:], "stage")
    return cp


def bootstrap_check() -> dict:
    """Never installs anything: reports what is ready so the caller can decide."""
    out = {"python": sys.version.split()[0], "ffmpeg": None, "ffprobe": None,
           "numpy": False, "cv2": False, "pil": False, "filters": {}, "ready": False}
    try:
        out["ffmpeg"] = ffmpeg()
    except ToolError:
        pass
    out["ffprobe"] = ffprobe()
    for mod in ("numpy", "cv2", "PIL"):
        try:
            __import__(mod)
            out[mod] = True
        except ImportError:
            pass
    if out["ffmpeg"]:
        from _common import has_filter
        for f in ("trim", "concat", "scale", "crop", "zoompan", "eq", "ass", "loudnorm"):
            out["filters"][f] = has_filter(f)
    out["ready"] = bool(out["ffmpeg"] and out["numpy"] and all(out["filters"].values())
                        and (SKILL / "assets/cascades/haarcascade_frontalface_default.xml").exists())
    return out


def cmd_wrap(text: str, width: int = 96) -> str:
    import textwrap
    return "\n".join(textwrap.wrap(text, width))


def write_report(path: Path, *, source: Path, out: Path, analysis: dict, plan: dict,
                 result: dict | None, verification: dict | None, elapsed: float) -> Path:
    """A Markdown hand-off: what was measured, what was decided, what was checked."""
    L: list[str] = []
    p = analysis["probe"]
    L.append(f"# تدوین‌شده: {out.name}")
    L.append("")
    L.append(f"**منبع:** `{source.name}` — {p['width']}×{p['height']}، {p['fps']} fps، "
             f"{human_time(p['duration'])}، {p['vcodec']}/{p['acodec']}")
    s = plan["summary"]
    L.append(f"**خروجی:** {plan['output']['width']}×{plan['output']['height']}، "
             f"{plan['output']['fps']} fps، {human_time(s['duration_out'])} "
             f"(از {human_time(s['duration_in'])}، حذف {human_time(s['removed'])})")
    L.append("")
    if verification:
        L.append(f"**داوری:** {verification['verdict']} — {verification['summary']}")
        L.append("")
    L.append("## تصمیم‌ها")
    L.append("")
    for d in plan["decisions"]:
        L.append(f"- {d}")
    L.append("")
    if plan["warnings"]:
        L.append("## هشدارها")
        L.append("")
        for w in plan["warnings"]:
            L.append(f"- ⚠ {w}")
        L.append("")
    if verification:
        L.append("## بررسی فنی")
        L.append("")
        L.append("| بررسی | نتیجه | جزئیات |")
        L.append("|---|---|---|")
        mark = {"PASS": "✓", "WARN": "!", "FAIL": "✗"}
        for row in verification["rows"]:
            L.append(f"| {row['check']} | {mark[row['status']]} | {row['detail']} |")
        L.append("")
        if verification.get("sheet"):
            L.append(f"شیت بازبینی: `{Path(verification['sheet']).name}`")
            L.append("")
    if result:
        L.append("## مراحل رندر")
        L.append("")
        for st in result["stages"]:
            detail = ", ".join(f"{k}={v}" for k, v in st.items() if k not in ("stage", "status"))
            L.append(f"- `{st['stage']}` {st['status']} {detail}")
        L.append("")
    L.append(f"<sub>talking-head-studio · {elapsed:.1f}s · v1.0</sub>")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="studio.py",
        description="A talking-head recording in, a finished verified video out.")
    ap.add_argument("source")
    ap.add_argument("--out", "-o", default=None, help="output MP4 (default: <source>.studio.mp4)")
    ap.add_argument("--preset", default="social", choices=sorted(PRESETS))
    ap.add_argument("--platform", default=None,
                    help="reels|tiktok|shorts|youtube|square|podcast|broadcast|original")
    ap.add_argument("--captions", default=None, help="SRT/VTT file for the source audio")
    ap.add_argument("--caption-style", default=None,
                    choices=["minimal", "bold", "boxed", "karaoke"])
    ap.add_argument("--caption-size", type=int, default=None)
    ap.add_argument("--caption-shift", type=float, default=0.0,
                    help="seconds to subtract from cue times")
    ap.add_argument("--captions-in-output-time", action="store_true")
    ap.add_argument("--words", default=None, help="word-level JSON (enables karaoke)")
    ap.add_argument("--pace", default=None, choices=["tight", "natural", "loose"])
    ap.add_argument("--zoom", default=None, choices=["none", "in", "out", "punch", "pulse"])
    ap.add_argument("--zoom-amp", type=float, default=0.06)
    ap.add_argument("--grade", default=None, choices=["clean", "warm", "cinematic", "crisp"])
    ap.add_argument("--crop", default=None, choices=["face", "center", "top", "left", "right", "none"])
    ap.add_argument("--fit", default=None, choices=["auto", "cover", "pad"])
    ap.add_argument("--light", default=None, choices=["auto", "off"])
    ap.add_argument("--no-denoise", action="store_true", help="skip audio noise reduction")
    ap.add_argument("--denoise-video", action="store_true")
    ap.add_argument("--no-flicker", action="store_true")
    ap.add_argument("--stabilize", action="store_true", help="two-pass vidstab")
    ap.add_argument("--loudness", type=float, default=None)
    ap.add_argument("--max-duration", type=float, default=None)
    ap.add_argument("--trim-start", type=float, default=None)
    ap.add_argument("--trim-end", type=float, default=None)
    ap.add_argument("--no-cut", action="store_true")
    ap.add_argument("--width", type=int, default=None)
    ap.add_argument("--height", type=int, default=None)
    ap.add_argument("--fps", type=float, default=None)
    ap.add_argument("--workdir", default=None, help="folder for analysis/plan/report (default: next to --out)")
    ap.add_argument("--plan-only", action="store_true", help="measure and decide, do not render")
    ap.add_argument("--preview", action="store_true", help="fast low-quality draft")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--install", action="store_true", help="run bootstrap.sh if tools are missing")
    args = ap.parse_args()

    t0 = time.time()
    src = Path(args.source)
    if not src.is_file():
        eprint(f"✗ no such file: {src}")
        return 2
    out = Path(args.out) if args.out else src.with_suffix("").with_name(src.stem + ".studio.mp4")
    work = Path(args.workdir) if args.workdir else out.parent
    work.mkdir(parents=True, exist_ok=True)

    # ---- stage 0: environment
    env = bootstrap_check()
    if not env["ready"]:
        missing = [k for k, v in (("ffmpeg", env["ffmpeg"]), ("numpy", env["numpy"]),
                                  ("opencv", env["cv2"]), ("pillow", env["pil"])) if not v]
        missing += [f"filter:{k}" for k, v in env["filters"].items() if not v]
        if args.install:
            eprint("• installing the toolchain (bash scripts/bootstrap.sh)…")
            cp = subprocess.run(["bash", str(HERE / "bootstrap.sh")])
            env = bootstrap_check()
            if not env["ready"]:
                eprint("✗ toolchain still incomplete after bootstrap — run "
                       "`bash scripts/bootstrap.sh` and read the ✗ lines")
                return 2
        else:
            eprint("✗ environment not ready: " + ", ".join(missing))
            eprint("  fix with:  bash scripts/bootstrap.sh      (or re-run with --install)")
            return 2

    preset = PRESETS[args.preset]
    plat = args.platform or preset["platform"]

    # ---- stage 1: measure
    analysis_path = work / f"{out.stem}.analysis.json"
    eprint("• measuring the source…")
    _run("analyze.py", [str(src), "--out", str(analysis_path)])
    analysis = read_json(analysis_path)

    # ---- stage 2: decide
    plan_args = [str(analysis_path), "--out", str(work / f"{out.stem}.plan.json"),
                 "--out-video", str(out), "--platform", plat,
                 "--pace", args.pace or preset["pace"],
                 "--zoom", args.zoom or preset["zoom"],
                 "--grade", args.grade or preset["grade"],
                 "--zoom-amp", str(args.zoom_amp),
                 "--crop", args.crop or "face",
                 "--fit", args.fit or preset["fit"],
                 "--caption-style", args.caption_style or preset["caption_style"]]
    if args.captions:
        plan_args += ["--captions", str(Path(args.captions).resolve())]
    if args.caption_size:
        plan_args += ["--caption-size", str(args.caption_size)]
    if args.caption_shift:
        plan_args += ["--caption-shift", str(args.caption_shift)]
    if args.captions_in_output_time:
        plan_args += ["--captions-in-output-time"]
    if args.light:
        plan_args += ["--light", args.light]
    if args.no_denoise:
        plan_args += ["--no-denoise-audio"]
    if args.denoise_video:
        plan_args += ["--denoise-video"]
    if args.no_flicker:
        plan_args += ["--no-flicker"]
    if args.loudness is not None:
        plan_args += ["--loudness", str(args.loudness)]
    if args.max_duration:
        plan_args += ["--max-duration", str(args.max_duration)]
    if args.trim_start is not None:
        plan_args += ["--trim-start", str(args.trim_start)]
    if args.trim_end is not None:
        plan_args += ["--trim-end", str(args.trim_end)]
    if args.no_cut:
        plan_args += ["--no-cut"]
    if args.width:
        plan_args += ["--width", str(args.width)]
    if args.height:
        plan_args += ["--height", str(args.height)]
    if args.fps:
        plan_args += ["--fps", str(args.fps)]
    _run("plan.py", plan_args)
    plan = read_json(work / f"{out.stem}.plan.json")

    if args.plan_only:
        payload = {"stage": "plan-only", "analysis": str(analysis_path),
                   "plan": str(work / f"{out.stem}.plan.json"),
                   "summary": plan["summary"], "decisions": plan["decisions"],
                   "warnings": plan["warnings"], "output": plan["output"]}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            for d in plan["decisions"]:
                print(f"  · {d}")
            for w in plan["warnings"]:
                print(f"  ! {w}")
            print(f"\nno render (--plan-only). plan: {payload['plan']}")
        return 0

    # ---- stage 3: render
    eprint("• rendering…")
    render_args = [str(work / f"{out.stem}.plan.json"), "--out", str(out), "--json"]
    if args.preview:
        render_args.append("--preview")
    if args.stabilize:
        render_args.append("--stabilize")
    cp = _run("render.py", render_args)
    result = json.loads(cp.stdout[cp.stdout.find("{"):])

    # ---- stage 4: verify
    eprint("• verifying…")
    verify_path = work / f"{out.stem}.verify.json"
    cp = subprocess.run([sys.executable, str(HERE / "verify.py"), str(out),
                         "--plan", str(work / f"{out.stem}.plan.json"),
                         "--out", str(verify_path), "--json"],
                        capture_output=True, text=True, errors="replace")
    verification = None
    if verify_path.is_file():
        verification = read_json(verify_path)
    elif cp.returncode != 0:
        eprint("! verification could not run: " + (cp.stderr or "")[-400:])

    # ---- stage 5: hand-off
    report = write_report(work / f"{out.stem}.report.md", source=src, out=out,
                          analysis=analysis, plan=plan, result=result,
                          verification=verification, elapsed=time.time() - t0)
    manifest = {
        "source": str(src.resolve()),
        "output": str(out.resolve()),
        "analysis": str(analysis_path),
        "plan": str(work / f"{out.stem}.plan.json"),
        "verify": str(verify_path) if verification else None,
        "report": str(report),
        "captions_ass": (result.get("manifest") or {}).get("ass"),
        "captions_srt": (result.get("manifest") or {}).get("srt"),
        "sheet": (verification or {}).get("sheet"),
        "verdict": (verification or {}).get("verdict"),
        "seconds": round(time.time() - t0, 1),
    }
    write_json(work / f"{out.stem}.manifest.json", manifest)

    if args.json:
        print(json.dumps({"manifest": manifest, "summary": plan["summary"],
                          "decisions": plan["decisions"], "warnings": plan["warnings"],
                          "verification": (verification or {}).get("rows")},
                         ensure_ascii=False, indent=2))
    else:
        s = plan["summary"]
        print(f"\n✓ {out}  ({human_time(s['duration_out'])}, "
              f"-{human_time(s['removed'])} dead air, {s['cuts']} cut(s))")
        print(f"  verdict: {(verification or {}).get('verdict', 'not verified')}"
              f" — {(verification or {}).get('summary', '')}")
        for f in (manifest["report"], manifest["sheet"], manifest["captions_srt"]):
            if f:
                print(f"  · {Path(f).name}")
        print(f"  total {manifest['seconds']}s")

    verdict = (verification or {}).get("verdict")
    if verdict == "FAIL":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
