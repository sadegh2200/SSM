#!/usr/bin/env python3
"""
export_variants.py — derive the publishing set from a rendered 9:16 master.

    python3 export_variants.py master.mp4 --out deliver/ --name sadiqeen-9-119
        [--cover] [--cover-at 24.9] [--feed] [--square] [--audio] [--srt] [--alt-text] [--caption]
        [--spec spec.json] [--resolved project/spec.resolved.json] [--brand config/brand.json]

Cover is **opt-in** in v3: if the user does not ask for an image, none is made — the first frame is
Instagram's cover anyway, and `verify` already checks that it is readable. Everything that needs
ffmpeg (cover, feed, square, audio) is skipped with a clear message when ffmpeg is missing.
The text artefacts (SRT, alt text, caption) need no ffmpeg at all.
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

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(HERE))
TAG_RE = re.compile(r"<[^>]+>")


def load(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return None


def have(b: str) -> bool:
    return shutil.which(b) is not None


def run(cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode:
        sys.stderr.write(r.stderr[-2000:])
        raise SystemExit(f"failed: {' '.join(str(c) for c in cmd[:4])} …")


def scene_text(sc: dict) -> str:
    t = sc.get("type")
    if t == "hook":
        return " ".join(str(sc.get(k, "")) for k in ("lead", "line1", "line2")).strip()
    if t == "verse":
        return " ".join(w for line in sc.get("lines") or [] for w in line)
    if t == "quote":
        text = sc.get("text")
        return " ".join(text) if isinstance(text, list) else str(text or "")
    if t == "contrast":
        return str(sc.get("right") or sc.get("wrong") or "")
    if t == "answer":
        return " ".join(str(sc.get(k, "")) for k in ("hero", "after") if sc.get(k))
    if t == "proof":
        cards = sc.get("cards") or []
        bits = [" ".join(x for x in (c.get("book", ""), c.get("loc", ""), c.get("grade", "")) if x) for c in cards[:1]]
        bits += [str(sc.get(k)) for k in ("line1", "line2") if sc.get(k)]
        if sc.get("attribution"):
            bits.append(re.sub(r"^[—–-]\s*", "", str(sc["attribution"])))
        return " — ".join(b for b in bits if b)
    if t == "cta":
        return " ".join(str(sc.get(k, "")) for k in ("line1", "line2") if sc.get(k))
    if t == "list":
        return " · ".join(sc.get("items") or [])
    if t == "title":
        return str(sc.get("title") or "")
    if t == "paragraph":
        return " ".join(str(x) for x in (sc.get("text") if isinstance(sc.get("text"), list) else [sc.get("text") or ""]) if x)
    if t == "definition":
        body = sc.get("body")
        body = " ".join(body) if isinstance(body, list) else str(body or "")
        return f"{sc.get('term', '')} — {body}".strip(" —")
    if t == "qa":
        ans = sc.get("answer")
        ans = " ".join(ans) if isinstance(ans, list) else str(ans or "")
        return f"{sc.get('question', '')} {ans}".strip()
    if t in ("steps", "timeline"):
        key = "items" if t == "steps" else "events"
        bits = []
        for x in sc.get(key) or []:
            if isinstance(x, dict):
                bits.append(" ".join(str(x.get(k, "")) for k in ("head", "when", "text") if x.get(k)))
            else:
                bits.append(str(x))
        return " · ".join(bits)
    if t == "compare":
        bits = []
        for key in ("col_a", "col_b"):
            c = sc.get(key) or {}
            bits.append(str(c.get("head", "")))
            bits += [str(x) for x in c.get("points") or []]
        return " · ".join(x for x in bits if x) + (f" — {sc['verdict']}" if sc.get("verdict") else "")
    return ""


def srt_from(spec: dict) -> str:
    def ts(sec: float) -> str:
        ms = int(round(float(sec) * 1000))
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    out, n = [], 0
    for sc in spec.get("scenes") or []:
        text = re.sub(r"\s+", " ", TAG_RE.sub("", scene_text(sc))).strip()
        if not text:
            continue
        n += 1
        out.append(f"{n}\n{ts(sc['start'])} --> {ts(sc['end'])}\n{text}\n")
    return "\n".join(out)


def alt_text(spec: dict) -> str:
    hook = next((s for s in spec.get("scenes") or [] if s.get("type") == "hook"), {})
    line = " ".join(str(hook.get(k, "")) for k in ("lead", "line1", "line2")).strip()
    src = ""
    proof = next((s for s in spec.get("scenes") or [] if s.get("type") == "proof"), None)
    if proof and (proof.get("cards") or []):
        c = proof["cards"][0]
        src = " ".join(x for x in (c.get("book", ""), c.get("loc", "")) if x)
    text = "ريل عمودي من «مع الصادقين»" + (f": {line}" if line else "")
    if src:
        text += f" — {src}"
    return text[:240]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("master", nargs="?", default=None, help="the rendered 9:16 master (omit for text-only exports)")
    ap.add_argument("--out", default="deliver")
    ap.add_argument("--name", default=None)
    ap.add_argument("--spec", help="spec.json (for srt / alt text / cover timing / caption)")
    ap.add_argument("--resolved", help="spec.resolved.json (preferred for timing)")
    ap.add_argument("--brand", default=str(SKILL / "config" / "brand.json"))
    ap.add_argument("--cover", action="store_true", help="export <name>-cover.jpg (off by default)")
    ap.add_argument("--cover-at", type=float, default=None)
    ap.add_argument("--feed", action="store_true")
    ap.add_argument("--square", action="store_true")
    ap.add_argument("--audio", action="store_true")
    ap.add_argument("--srt", action="store_true")
    ap.add_argument("--alt-text", action="store_true")
    ap.add_argument("--caption", action="store_true")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    if not a.master and (a.cover or a.feed or a.square or a.audio):
        sys.exit("cover/feed/square/audio need a master MP4 (pass it as the first argument)")
    name = a.name or (os.path.splitext(os.path.basename(a.master))[0] if a.master else "reel")
    spec = load(a.spec) if a.spec else None
    resolved = load(a.resolved) if a.resolved else None
    made: list[str] = []

    if a.srt:
        if not spec:
            print("  ⚠ --srt needs --spec")
        else:
            try:
                import social_kit  # noqa: PLC0415
                text = social_kit.srt_from_spec(spec)
            except Exception:
                text = srt_from(spec)
            p = os.path.join(a.out, f"{name}.srt")
            Path(p).write_text(text, encoding="utf-8")
            made.append(p)
            print("srt", p)

    if a.alt_text:
        if not spec:
            print("  ⚠ --alt-text needs --spec")
        else:
            p = os.path.join(a.out, f"{name}.alt.txt")
            Path(p).write_text(alt_text(spec) + "\n", encoding="utf-8")
            made.append(p)
            print("alt", p)

    if a.caption:
        if not spec:
            print("  ⚠ --caption needs --spec")
        else:
            try:
                import captions  # noqa: PLC0415
                brand = load(a.brand) or {}
                comp = captions.compose(spec, brand, {})
                p = os.path.join(a.out, f"{name}-caption.txt")
                Path(p).write_text(comp["instagram"] + "\n", encoding="utf-8")
                made.append(p)
                print("caption", p)
            except Exception as e:
                print("  ⚠ caption failed:", e)

    video_ops = a.cover or a.feed or a.square or a.audio
    if video_ops and not (have("ffmpeg") and have("ffprobe")):
        print("  ⚠ ffmpeg/ffprobe missing — cover/feed/square/audio skipped")
        return

    if a.cover:
        t = a.cover_at
        timing = resolved or spec
        if t is None and timing:
            for sc in timing.get("scenes") or []:
                cues = sc.get("cues") or {}
                hero = cues.get("hero")
                if sc.get("type") in ("answer", "quote") and isinstance(hero, (int, float)):
                    t = hero + 0.9
                    break
        if t is None:
            t = 1.6
        p = os.path.join(a.out, f"{name}-cover.jpg")
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(t), "-i", a.master,
             "-frames:v", "1", "-q:v", "2", p])
        made.append(p)
        print("cover", p, f"@{t}s")

    enc = ["-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", "-c:a", "aac", "-b:a", "192k"]
    if a.feed:
        p = os.path.join(a.out, f"{name}-feed-4x5.mp4")
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", a.master,
             "-vf", "crop=1080:1350:0:220"] + enc + [p])
        made.append(p)
        print("feed 4:5", p)
    if a.square:
        p = os.path.join(a.out, f"{name}-1x1.mp4")
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", a.master,
             "-vf", "crop=1080:1080:0:420"] + enc + [p])
        made.append(p)
        print("square", p)
    if a.audio:
        p = os.path.join(a.out, f"{name}.m4a")
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", a.master,
             "-vn", "-c:a", "aac", "-b:a", "192k", p])
        made.append(p)
        print("audio", p)
    if not made:
        print("nothing requested — v3 does not export a cover unless you pass --cover")


if __name__ == "__main__":
    main()
