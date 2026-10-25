#!/usr/bin/env python3
"""Front door for «استودیوی مع الصادقین».

    python3 studio.py doctor                       # what is installed, what is missing
    python3 studio.py recognize input.txt          # text/sheet/transcript → recognition.json
    python3 studio.py treat recognition.json       # three treatments, scored
    python3 studio.py build spec.json --out out/   # video + sound + report + kit
    python3 studio.py verify out/reel.mp4 --spec spec.json
    python3 studio.py kit spec.json --out out/kit
    python3 studio.py still spec.json 12.4 --out frame.png
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import brandkit as bk  # noqa: E402
import plan  # noqa: E402

PY_DEPS = [("numpy", "numpy"), ("PIL", "pillow"), ("uharfbuzz", "uharfbuzz"),
           ("freetype", "freetype-py")]


def doctor(verbose: bool = True) -> dict:
    out = {"python": sys.version.split()[0], "deps": {}, "tools": {}, "brand": {},
           "ok": True}
    for mod, pkg in PY_DEPS:
        try:
            __import__(mod)
            out["deps"][pkg] = "ok"
        except Exception as e:  # noqa: BLE001
            out["deps"][pkg] = f"MISSING ({e.__class__.__name__})"
            out["ok"] = False
    for tool in ("ffmpeg", "ffprobe"):
        p = shutil.which(tool)
        out["tools"][tool] = p or "MISSING"
        if not p:
            out["ok"] = False
    for key in ("quran", "amiri", "amiri_b", "kufi", "kufi_r", "naskh"):
        try:
            out.setdefault("fonts", {})[key] = Path(bk.font_path(key)).name
        except Exception:  # noqa: BLE001
            out.setdefault("fonts", {})[key] = "MISSING"
            out["ok"] = False
    root = bk.brand_root()
    out["brand"]["skill"] = str(root) if root else "not installed (tokens from the snapshot)"
    out["brand"]["theme"] = bk.tokens()["_theme"]
    out["brand"]["logo"] = str(bk.asset("logo.png") or "MISSING")
    out["brand"]["sfx"] = len([n for n in ("click-soft", "whoosh-short", "chime", "impact-bass-1",
                                           "sparkle", "pen-scratch", "riser")
                               if bk.asset(f"{n}.mp3") or bk.asset(f"{n}.wav")])
    if verbose:
        print(f'python {out["python"]}')
        for k, v in out["deps"].items():
            print(f'  dep  {k:14s} {v}')
        for k, v in out["tools"].items():
            print(f'  tool {k:14s} {v}')
        for k, v in out.get("fonts", {}).items():
            print(f'  font {k:14s} {v}')
        print(f'  brand skill   {out["brand"]["skill"]}')
        print(f'  theme         {out["brand"]["theme"]} · {out["brand"]["sfx"]} sound cues')
        print("OK" if out["ok"] else "MISSING DEPENDENCIES — run bootstrap.sh")
    return out


# ------------------------------------------------------------------------------- build
def mux(video: str, audio: str, out: str) -> str:
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", video, "-i", audio,
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest",
           "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    return out


def build(spec_path: str, out_dir: str = "out", theme: str | None = None,
          no_audio: bool = False, sheet: bool = True, kit: bool = True,
          force: bool = False, progress=print) -> dict:
    import brandgate
    import render
    import sound
    import verify

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    res = plan.resolve(plan.load(spec_path))
    if theme:
        res["theme"] = theme
    aud = plan.audit(res)
    progress(f'  spec  {res.get("title", spec_path)} · {res["duration"]:.1f}s · '
             f'{aud["scenes"]} scenes · {aud["words"]} words · theme {res.get("theme", "—")}')
    for issue in aud["issues"]:
        progress(f'  ! {issue["level"]}: {issue["what"]} — {issue["fix"]}')

    # the words are gated before a single frame is drawn
    gate = brandgate.run(spec_path)
    progress(f'  copy gate: {gate["verdict"]} — {len(gate["rows"])} findings')
    for row in gate["rows"]:
        if row["level"] != "pass":
            progress(f'    {row["level"]:4s} {row["gate"]}: {row["value"]}')
    if gate["fails"] and not force:
        progress("  stopped: the copy gate failed. Fix the spec, or pass --force to render anyway.")
        return {"video": None, "stopped": "copy-gate", "gate": gate, "verdict": {"verdict": "FAIL",
                "pass": 0, "warn": gate["warns"], "fail": gate["fails"]}}
    Path(out / "copy-gate.md").write_text(f'# copy gate — {gate["verdict"]}\n\n' +
                                          brandgate.table(gate) + "\n", encoding="utf-8")

    silent = str(out / "video-silent.mp4")
    progress("  picture …")
    render.render(res, silent, None, progress=lambda m: progress(m))
    cues_path = silent + ".cues.json"
    cues = json.loads(Path(cues_path).read_text(encoding="utf-8"))

    final = str(out / f'{(res.get("id") or "reel")}.mp4')
    if no_audio:
        shutil.move(silent, final)
        Path(cues_path).unlink(missing_ok=True)
    else:
        progress(f"  sound … {len(cues)} cues")
        mix = str(out / "mix.wav")
        sound.build(cues, res["duration"], mix, lufs=float(
            (res.get("audio") or {}).get("target_lufs", -15.5)), workdir=out)
        mux(silent, mix, final)
        Path(silent).unlink(missing_ok=True)
        Path(cues_path).unlink(missing_ok=True)

    progress("  gate …")
    rep = str(out / "report.md")
    sheet_path = str(out / "contact-sheet.png") if sheet else None
    data = verify.run(final, spec_path, rep, sheet_path, res.get("theme"))
    if kit:
        import kit as kitmod
        kitmod.build(spec_path, str(out / "kit"))
        export_variants(final, str(out / "kit"), res.get("id") or "reel", spec_path, progress)
    v = data["verdict"]
    progress(f'  {v["verdict"]} — {v["pass"]} pass · {v["warn"]} warn · {v["fail"]} fail')
    return {"video": final, "report": rep, "sheet": sheet_path, "kit": str(out / "kit")
            if kit else None, "verdict": v, "meta": data["meta"]}


def export_variants(video: str, kitdir: str, slug: str, spec_path: str, progress=print):
    """An SRT + alt text from the brand's own exporter, when that skill is installed."""
    import brandgate
    root = brandgate._skill("maalsadiqeen-reel")
    path = (root / "scripts" / "export_variants.py") if root else None
    if not path or not path.exists():
        return
    cmd = [sys.executable, str(path), video, "--out", kitdir, "--name", slug,
           "--spec", spec_path, "--srt", "--alt-text"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        progress(f'    ! export_variants: {(r.stderr or r.stdout).strip()[:120]}')


# -------------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description="استودیوی مع الصادقین — from text to a verified reel")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor")

    p = sub.add_parser("recognize")
    p.add_argument("input")
    p.add_argument("--out", default=".")

    p = sub.add_parser("treat")
    p.add_argument("recognition")
    p.add_argument("--out", default=".")

    p = sub.add_parser("build")
    p.add_argument("spec")
    p.add_argument("--out", default="out")
    p.add_argument("--theme")
    p.add_argument("--no-audio", action="store_true")
    p.add_argument("--no-kit", action="store_true")
    p.add_argument("--no-sheet", action="store_true")
    p.add_argument("--force", action="store_true", help="render even if the copy gate fails")

    p = sub.add_parser("verify")
    p.add_argument("video")
    p.add_argument("--spec")
    p.add_argument("--out", default="report.md")
    p.add_argument("--sheet")

    p = sub.add_parser("kit")
    p.add_argument("spec")
    p.add_argument("--out", default="kit")

    p = sub.add_parser("still")
    p.add_argument("spec")
    p.add_argument("at", type=float)
    p.add_argument("--out", default="frame.png")
    p.add_argument("--theme")

    a = ap.parse_args()
    if a.cmd == "doctor":
        return 0 if doctor()["ok"] else 1
    if a.cmd == "recognize":
        import director
        rec = director.recognize(a.input)
        director.write(rec, a.out)
        print(json.dumps({k: rec[k] for k in ("kind", "class", "confidence", "idea")},
                         ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "treat":
        import director
        rec = json.loads(Path(a.recognition).read_text(encoding="utf-8"))
        t = director.treat(rec)
        Path(a.out, "treatments.json").write_text(json.dumps(t, ensure_ascii=False, indent=1),
                                                  encoding="utf-8")
        print(director.treat_table(t))
        return 0
    if a.cmd == "build":
        d = build(a.spec, a.out, a.theme, a.no_audio, not a.no_sheet, not a.no_kit, a.force)
        print(d["video"])
        return 0 if d["verdict"]["fail"] == 0 else 1
    if a.cmd == "verify":
        import verify
        d = verify.run(a.video, a.spec, a.out, a.sheet)
        print(f'{d["verdict"]["verdict"]} — {d["verdict"]["pass"]} pass · '
              f'{d["verdict"]["warn"]} warn · {d["verdict"]["fail"]} fail')
        return 0 if d["verdict"]["fail"] == 0 else 1
    if a.cmd == "kit":
        import kit
        kit.build(a.spec, a.out)
        print(f"kit → {a.out}")
        return 0
    if a.cmd == "still":
        import render
        res = plan.resolve(plan.load(a.spec))
        st = render.build_stage(res)
        import blocks
        blocks.build_all(st, res)
        dur = res["duration"]
        f = st.finish(st.frame(a.at), a.at, dur)
        f.save(a.out)
        print(a.out)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
