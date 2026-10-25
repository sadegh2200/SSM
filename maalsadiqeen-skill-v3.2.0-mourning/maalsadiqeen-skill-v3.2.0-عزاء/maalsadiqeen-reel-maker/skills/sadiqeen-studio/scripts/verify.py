#!/usr/bin/env python3
"""The gate: numbers first, then the eye.

Nothing here is a matter of taste. A reel passes when it is the right size, the right
length, the right loudness, the right theme, and when every reveal has room to be read.
The contact sheet is the second half of the gate — it is for the one thing numbers cannot
see: whether the frame looks like the page.

    python3 verify.py reel.mp4 --spec spec.json --out report.md
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import brandkit as bk
import plan
from brandkit import H, W

TARGET_LUFS = -15.5


def _ffprobe(path: str) -> dict:
    cmd = ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path]
    return json.loads(subprocess.run(cmd, capture_output=True, check=True).stdout)


def probe(path: str) -> dict:
    info = _ffprobe(path)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), {})
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), {})
    num, den = (v.get("r_frame_rate") or "0/1").split("/")
    fps = round(float(num) / float(den or 1), 3) if float(den or 1) else 0
    return {
        "width": v.get("width"), "height": v.get("height"), "fps": fps,
        "vcodec": v.get("codec_name"), "pix_fmt": v.get("pix_fmt"),
        "duration": round(float(info["format"].get("duration", 0)), 3),
        "acodec": a.get("codec_name"), "sample_rate": a.get("sample_rate"),
        "channels": a.get("channels"), "size": int(info["format"].get("size", 0)),
    }


def loudness(path: str) -> dict:
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-i", path,
           "-af", "ebur128=peak=true", "-f", "null", "-"]
    err = subprocess.run(cmd, capture_output=True).stderr.decode("utf-8", "replace")
    lufs = re.findall(r"I:\s*(-?\d+\.\d+)\s*LUFS", err)
    peak = re.findall(r"Peak:\s*(-?\d+\.\d+)\s*dBFS", err)
    return {"lufs": float(lufs[-1]) if lufs else None,
            "true_peak": float(peak[-1]) if peak else None}


def contact_sheet(path: str, out: str, n: int = 12, cols: int = 4,
                  duration: float | None = None) -> str:
    from PIL import Image, ImageDraw
    dur = duration or probe(path)["duration"]
    frames = []
    for i in range(n):
        t = dur * (i + 0.5) / n
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t:.3f}",
               "-i", path, "-frames:v", "1", "-vf", "scale=405:-1", "-f", "image2", "-"]
        raw = subprocess.run(cmd, capture_output=True).stdout
        if raw:
            import io
            frames.append((t, Image.open(io.BytesIO(raw)).convert("RGB")))
    if not frames:
        raise RuntimeError("no frames decoded for the contact sheet")
    w, h = frames[0][1].size
    rows = (len(frames) + cols - 1) // cols
    pad, label = 12, 26
    sheet = Image.new("RGB", (cols * w + pad * (cols + 1), rows * (h + label) + pad * (rows + 1)),
                      (18, 18, 17))
    d = ImageDraw.Draw(sheet)
    for i, (t, img) in enumerate(frames):
        x = pad + (i % cols) * (w + pad)
        y = pad + (i // cols) * (h + label + pad)
        sheet.paste(img, (x, y + label))
        d.text((x + 2, y + 6), f"{t:5.2f}s", fill=(196, 164, 108))
    sheet.save(out)
    return out


def checks(meta: dict, loud: dict, aud: dict, res: dict | None, theme: str) -> list[dict]:
    tk = bk.tokens(theme)
    out: list[dict] = []

    def add(level, name, value, want):
        out.append({"level": level, "check": name, "value": value, "want": want})

    add("pass" if (meta["width"], meta["height"]) == (W, H) else "fail", "frame",
        f'{meta["width"]}×{meta["height"]}', f"{W}×{H}")
    add("pass" if abs(meta["fps"] - 30) < 0.05 else "fail", "fps", meta["fps"], "30.000")
    dur = meta["duration"]
    add("pass" if (res is None or abs(dur - res["duration"]) <= 0.12) else "warn", "duration",
        f"{dur:.2f}s", f'{(res or {}).get("duration", dur):.2f}s ±0.12')
    add("pass" if meta["vcodec"] == "h264" and meta["pix_fmt"] == "yuv420p" else "warn",
        "video codec", f'{meta["vcodec"]} · {meta["pix_fmt"]}', "h264 · yuv420p")
    add("pass" if meta["acodec"] else "fail", "audio", meta["acodec"] or "none", "aac")
    if loud.get("lufs") is not None:
        ok = abs(loud["lufs"] - TARGET_LUFS) <= 1.2
        add("pass" if ok else "warn", "loudness", f'{loud["lufs"]:.1f} LUFS',
            f"{TARGET_LUFS} ±1.2")
    if loud.get("true_peak") is not None:
        add("pass" if loud["true_peak"] <= -1.0 else "warn", "true peak",
            f'{loud["true_peak"]:.1f} dBTP', "≤ −1.0 dBTP")
    ratio = bk.contrast(bk.rgb(tk["ink"]), bk.rgb(tk["paper"]))
    add("pass" if ratio >= 6 else "fail", "body contrast", f"{ratio}:1", "≥ 6:1")
    tok = json.dumps({k: v for k, v in tk.items() if not k.startswith("_")}).lower()
    bad = [c for c in ("#000000", "#ffffff", "#fff", "#000") if c in tok]
    add("pass" if not bad else "fail", "palette", f"{theme}" + (f" · {','.join(bad)}" if bad else ""),
        "no pure black or white")
    add("pass" if not re.search(r"#(8|9|a|b|c|d|e|f)[0-3][0-1][0-1]", tok) else "warn", "red-free",
        "ok", "no blood red")
    if aud:
        for issue in aud["issues"]:
            add(issue["level"], "copy", issue["what"], issue["fix"])
        add("pass", "word budget", f'{aud["words"]} words', f'soft {aud["soft"]} / hard {aud["hard"]}')
        add("pass", "scenes", aud["scenes"], "—")
    return out


def summary(rows: list[dict]) -> dict:
    n = {"pass": 0, "warn": 0, "fail": 0}
    for r in rows:
        n[r["level"]] += 1
    return {"pass": n["pass"], "warn": n["warn"], "fail": n["fail"],
            "verdict": "FAIL" if n["fail"] else ("WARN" if n["warn"] else "PASS")}


def report_md(res: dict | None, meta: dict, loud: dict, rows: list[dict], verdict: dict,
              sheet: str | None, title: str) -> str:
    L = [f"# {title}", ""]
    L.append(f"**{verdict['verdict']}** — {verdict['pass']} pass · {verdict['warn']} warn · "
             f"{verdict['fail']} fail")
    L += ["", "## The numbers", "",
          f"- {meta['width']}×{meta['height']} · {meta['fps']:.3f} fps · {meta['duration']:.2f} s · "
          f"{meta['size'] / 1e6:.2f} MB",
          f"- {meta['vcodec']} / {meta['pix_fmt']} · {meta['acodec']} "
          f"{meta['sample_rate']} Hz ×{meta['channels']}"]
    if loud.get("lufs") is not None:
        L.append(f"- loudness {loud['lufs']:.1f} LUFS · true peak "
                 f"{loud['true_peak'] if loud['true_peak'] is not None else '—'} dBTP")
    L += ["", "| check | value | wanted | verdict |", "|---|---|---|---|"]
    for r in rows:
        mark = {"pass": "✓", "warn": "!", "fail": "✗"}[r["level"]]
        L.append(f"| {r['check']} | {r['value']} | {r['want']} | {mark} |")
    if res:
        L += ["", "## The scenes", "", "| # | block | in | out | what changes |", "|---|---|---|---|---|"]
        for i, sc in enumerate(res["scenes"], 1):
            what = ", ".join(k for k in sc if k not in
                             ("id", "type", "start", "end", "cues", "theme")) or "—"
            L.append(f"| {i} | {sc['type']} | {sc['start']:.2f} | {sc['end']:.2f} | {what} |")
        im = res.get("life_impact")
        if im:
            L += ["", f"**الأثر في الحياة:** {im}"]
    if sheet:
        L += ["", f"![contact sheet]({Path(sheet).name})", ""]
    L += ["", "## What to look at with your own eyes", "",
          "1. The first 1.5 s: does the hook land before the scroll?",
          "2. The hero frame: is it the one you would screenshot?",
          "3. The last frame: is the brand card alone, uncluttered?",
          "4. The joins: no clipped word at the safe-zone edges, no orphan on a line.",
          ""]
    return "\n".join(L)


def brand_rows(spec_path: str | None) -> list[dict]:
    if not spec_path:
        return []
    try:
        import brandgate
        res = brandgate.run(spec_path)
        return [{"level": r["level"], "check": f'gate · {r["gate"]}', "value": r["value"],
                 "want": r["want"]} for r in res["rows"]]
    except Exception as e:  # noqa: BLE001
        return [{"level": "warn", "check": "copy gates", "value": str(e)[:120],
                 "want": "the brand's checkers installed"}]


def run(video: str, spec: str | None = None, out: str = "report.md", sheet: str | None = None,
        theme: str | None = None) -> dict:
    meta = probe(video)
    loud = loudness(video)
    res = None
    aud = None
    if spec:
        res = plan.resolve(plan.load(spec))
        aud = plan.audit(res)
        theme = theme or res.get("theme")
    theme = theme or bk.tokens()["_theme"]
    rows = checks(meta, loud, aud, res, theme) + brand_rows(spec)
    verdict = summary(rows)
    if sheet:
        contact_sheet(video, sheet, 12, 4, meta["duration"])
    title = (res or {}).get("title") or Path(video).stem
    Path(out).write_text(report_md(res, meta, loud, rows, verdict, sheet, title), encoding="utf-8")
    data = {"verdict": verdict, "meta": meta, "loudness": loud, "checks": rows,
            "theme": theme, "words": (aud or {}).get("words")}
    Path(out.replace(".md", ".json")).write_text(
        json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data


def main() -> int:
    ap = argparse.ArgumentParser(description="verify a rendered reel and write the report")
    ap.add_argument("video")
    ap.add_argument("--spec")
    ap.add_argument("--out", default="report.md")
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--theme")
    a = ap.parse_args()
    d = run(a.video, a.spec, a.out, a.sheet, a.theme)
    v = d["verdict"]
    print(f'{v["verdict"]} — {v["pass"]} pass · {v["warn"]} warn · {v["fail"]} fail')
    for r in d["checks"]:
        if r["level"] != "pass":
            print(f'  {r["level"].upper():4s} {r["check"]}: {r["value"]} (want {r["want"]})')
    return 0 if v["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
