#!/usr/bin/env python3
"""
render.py — render the Reel + cover + QA artefacts from a studio folder.

    python3 render.py --studio ~/reel-studio --content content.json [--plan plan.json]
                      [--out ~/reel-output/<slug>] [--stills-only] [--concurrency 1] [--crf 18]

Steps
  1. copies content.json / plan.json into <studio>/public (the composition loads them at runtime)
  2. `npx remotion render src/index.ts Reel out/reel.mp4` (H.264, yuv420p, AAC, 1080×1920)
  3. cover.jpg (hook frame) + contact sheet (12 frames) with cv2 for visual QA
  4. duration / loudness check (EBU R128 via imageio-ffmpeg's bundled ffmpeg when available)
  5. writes qa.json next to the outputs; exits 1 on hard failures (duration outside 30–60 s, render error)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from _common import load_json


def sh(cmd, cwd=None, timeout=1800):
    print("$", " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=timeout)


def ffmpeg_bin():
    try:
        import imageio_ffmpeg  # type: ignore
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg")


def loudness(ff, path):
    r = subprocess.run([ff, "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"], text=True, capture_output=True)
    # ebur128 prints running values; the summary block at the end holds the integrated result → take the last match
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r.stderr)
    return (float(m[-1]) if m else None, float(tp[-1]) if tp else None)


def probe_duration(ff, path):
    r = subprocess.run([ff, "-i", str(path)], text=True, capture_output=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else None


def contact_sheet(video, plan, out_path, cols=4, rows=3):
    import cv2  # noqa
    import numpy as np  # noqa
    cap = cv2.VideoCapture(str(video))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or plan["total"]
    picks = [int(n * (i + 0.5) / (cols * rows)) for i in range(cols * rows)]
    tiles = []
    for f in picks:
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ok, fr = cap.read()
        if not ok:
            fr = np.zeros((1920, 1080, 3), np.uint8)
        fr = cv2.resize(fr, (270, 480))
        cv2.putText(fr, f"{f/plan['fps']:.1f}s", (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 3)
        cv2.putText(fr, f"{f/plan['fps']:.1f}s", (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
        tiles.append(fr)
    sheet = np.vstack([np.hstack(tiles[r * cols:(r + 1) * cols]) for r in range(rows)])
    cv2.imwrite(str(out_path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 85])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--studio", default=os.path.expanduser("~/reel-studio"))
    ap.add_argument("--content", required=True)
    ap.add_argument("--plan", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--stills-only", action="store_true", help="only render the cover + 6 key stills (fast layout check)")
    ap.add_argument("--concurrency", default="1")
    ap.add_argument("--crf", default="18")
    a = ap.parse_args()

    studio = Path(a.studio)
    content_p = Path(a.content)
    plan_p = Path(a.plan) if a.plan else content_p.with_name("plan.json")
    if not plan_p.exists():
        sys.exit(f"plan not found: {plan_p} — run scripts/plan.py first")
    content, plan = load_json(content_p), load_json(plan_p)
    slug = content.get("slug") or "reel"
    out = Path(a.out) if a.out else Path.home() / "reel-output" / slug
    out.mkdir(parents=True, exist_ok=True)

    pub = studio / "public"
    shutil.copy(content_p, pub / "content.json")
    shutil.copy(plan_p, pub / "plan.json")

    s = plan["scenes"]
    key_frames = {"hook": s["hook"]["from"] + 60}
    if "hadith" in s:
        pg = s["hadith"]["pages"][-1]
        key_frames["hadith"] = s["hadith"]["from"] + pg["from"] + pg["lines"][-1]["at"] + 30
    if "points" in s:
        key_frames["points"] = s["points"]["from"] + s["points"]["cards"][0]["from"] + 90
    if "bayan" in s:
        key_frames["bayan"] = s["bayan"]["from"] + s["bayan"]["lines_at"][-1] + 30
    if "sanad" in s:
        key_frames["sanad"] = s["sanad"]["from"] + s["sanad"]["seal_at"] - 8
        key_frames["seal"] = s["sanad"]["from"] + s["sanad"]["seal_at"] + 50
    key_frames["cta"] = s["cta"]["from"] + 110

    qa = {"slug": slug, "frames": plan["total"], "fps": plan["fps"], "planned_seconds": round(plan["total"] / plan["fps"], 2), "stills": {}}

    if a.stills_only:
        for name, fr in key_frames.items():
            r = sh(["npx", "remotion", "still", "src/index.ts", "Reel", str(out / f"still-{name}.jpg"), f"--frame={fr}", "--jpeg-quality=85", "--log=error"], cwd=studio)
            if r.returncode:
                print(r.stderr[-800:]); sys.exit(1)
            qa["stills"][name] = str(out / f"still-{name}.jpg")
        print(json.dumps(qa, ensure_ascii=False, indent=2))
        return

    video = out / f"{slug}.mp4"
    r = sh(["npx", "remotion", "render", "src/index.ts", "Reel", str(video), f"--concurrency={a.concurrency}", f"--crf={a.crf}", "--codec=h264", "--log=error"], cwd=studio)
    if r.returncode:
        print(r.stdout[-1500:]); print(r.stderr[-1500:]); sys.exit(1)
    # cover = hook frame
    r = sh(["npx", "remotion", "still", "src/index.ts", "Reel", str(out / "cover.jpg"), f"--frame={key_frames['hook']}", "--jpeg-quality=90", "--log=error"], cwd=studio)
    qa["cover"] = str(out / "cover.jpg")
    qa["video"] = str(video)
    qa["size_mb"] = round(video.stat().st_size / 1e6, 2)
    try:
        contact_sheet(video, plan, out / "contact-sheet.jpg")
        qa["contact_sheet"] = str(out / "contact-sheet.jpg")
    except Exception as e:  # cv2 missing etc.
        qa["contact_sheet_error"] = str(e)
    ff = ffmpeg_bin()
    if ff:
        qa["duration_s"] = probe_duration(ff, video)
        lufs, tp = loudness(ff, video)
        qa["integrated_lufs"], qa["true_peak_dbfs"] = lufs, tp
        # same mastering target as the HyperFrames engine (references/brand.md): −15.5 LUFS, true peak ≤ −1.5 dBTP
        if lufs is not None and not (-17.5 <= lufs <= -13.5):
            qa.setdefault("warnings", []).append(f"loudness {lufs} LUFS outside −15.5 ± 2 — adjust audio.bed_volume / SFX vols")
        if tp is not None and tp > -1.5:
            qa.setdefault("warnings", []).append(f"true peak {tp} dBFS > −1.5 — lower boom/stamp volumes in plan.sfx")
    else:
        qa["note"] = "ffmpeg not found (pip install imageio-ffmpeg) — loudness not measured"
    dur = qa.get("duration_s") or qa["planned_seconds"]
    if not (30 <= dur <= 60):
        qa.setdefault("errors", []).append(f"duration {dur:.1f}s outside 30–60 s")
    json.dump(qa, open(out / "qa.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    if qa.get("errors"):
        sys.exit(1)


if __name__ == "__main__":
    main()
