#!/usr/bin/env python3
"""
reel.py — the three-command front door (v3).

    python3 reel.py intake <file|dir|-> ... --slug <slug> [--sheets img ...]
        text or sheets → input.txt, brief.seed.json, brief.seed.md

    python3 reel.py plan <slug> [--count 4]                 # create scenarios.json to fill
    python3 reel.py plan <slug> --finalize                  # validate + score + preview  ⛔ gate
        then wait for the user: «۲» or «۲ و ۴»

    python3 reel.py build <slug> --choose 2,4 [--preset minimal|standard|full] [--render]
        → spec-<id>.json → project-<id>/ → mix → verify → [render] → kit

    python3 reel.py kit <slug> --id 2 [--preset …] [--texts captions.json] [--publish-at 19:30]
    python3 reel.py status <slug>
    python3 reel.py log <slug> --id 2 --status rendered|published [--metrics "…"]
    python3 reel.py series <slug>

Paths: REEL_WORK (default ./reel-work), REEL_DELIVER (default ./reel-deliver).
The build degrades honestly: with no ffmpeg it still compiles the spec, the project and the whole
publishing kit and prints the exact commands that remain; it never pretends a render happened.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
LONG_TEXT = {"paragraph", "definition", "steps", "timeline", "compare", "qa"}
SKILL = HERE.parent
sys.path.insert(0, str(HERE))

import scenarios as S  # noqa: E402
import copy_lint  # noqa: E402

BRAND_PATH = SKILL / "config" / "brand.json"
LOG_PATH = SKILL / "config" / "content-log.json"
WORK = Path(os.environ.get("REEL_WORK", "reel-work"))
DELIVER = Path(os.environ.get("REEL_DELIVER", "reel-deliver"))


def load_json(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(obj, p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def brand() -> dict:
    return load_json(BRAND_PATH, {}) or {}


def run(cmd: list[str], **kw) -> int:
    print("  $", " ".join(str(c) for c in cmd))
    r = subprocess.run([str(c) for c in cmd], **kw)
    return r.returncode


def have(binary: str) -> bool:
    return shutil.which(binary) is not None


def hf_installed() -> bool:
    wd = Path(os.environ.get("HF_WORKDIR", Path.home() / "reel-sadiqeen"))
    return (wd / "node_modules" / "hyperframes").is_dir()


def workdir(slug: str) -> Path:
    return WORK / slug


# ----------------------------------------------------------------------------- intake
def cmd_intake(a) -> None:
    cmd = [sys.executable, HERE / "intake.py", *a.inputs, "--slug", a.slug, "--out", str(workdir(a.slug))]
    if a.sheets:
        cmd += ["--sheets", *a.sheets]
    sys.exit(run(cmd))


# ----------------------------------------------------------------------------- plan
def cmd_plan(a) -> int:
    w = workdir(a.slug)
    scpath = w / "scenarios.json"
    if not scpath.exists():
        brief = w / "brief.seed.json"
        cmd = [sys.executable, HERE / "scenarios.py", "init", a.slug, "--count", str(a.count)]
        if brief.exists():
            cmd += ["--brief", str(brief)]
        rc = run(cmd)
        print("\nNext: fill every «…» in", scpath, "(references/scenarios.md), then:")
        print(f"  python3 scripts/reel.py plan {a.slug} --finalize")
        return rc
    doc = load_json(scpath, {}) or {}
    b = brand()
    if not a.finalize:
        errs, warns = S.validate(doc, b)
        for x in errs:
            print("  ✗", x)
        for x in warns:
            print("  ⚠", x)
        print(f"{len(doc.get('scenarios') or [])} scenarios · {len(errs)} errors · {len(warns)} warnings")
        print(f"  finalize: python3 scripts/reel.py plan {a.slug} --finalize")
        return 1 if errs else 0
    errs, warns = S.validate(doc, b)
    for x in errs:
        print("  ✗", x)
    for x in warns:
        print("  ⚠", x)
    if errs:
        print(f"\n{len(errs)} errors in {scpath} — nothing scored, nothing rendered.")
        print("  Fix them (references/scenarios.md), then re-run --finalize.")
        return 1
    cmd = [sys.executable, HERE / "scenarios.py", "render", str(scpath)]
    brief = w / "brief.json"
    if not brief.exists():
        brief = w / "brief.seed.json"
    if brief.exists():
        cmd += ["--brief", str(brief)]
    if getattr(a, "theme", None):
        cmd += ["--theme", a.theme]
    return run(cmd)


# ----------------------------------------------------------------------------- build
def compile_one(doc: dict, sid: int, b: dict, slug: str, theme: str | None = None) -> tuple[Path, dict]:
    sc = next((s for s in doc.get("scenarios") or [] if s.get("id") == sid), None)
    if not sc:
        sys.exit(f"scenario #{sid} not found in scenarios.json")
    spec = S.compile_spec(sc, b, spec_id=f"{slug}-{sid}")
    if theme:
        spec["theme"] = theme
    path = workdir(slug) / f"spec-{sid}.json"
    save_json(spec, path)
    return path, spec


def ensure_silence(path: Path, seconds: float) -> None:
    """Placeholder audio when ffmpeg is absent, so the project is still inspectable. Never delivered."""
    import wave
    path.parent.mkdir(parents=True, exist_ok=True)
    sr = 48000
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        block = b"\x00\x00" * sr
        for _ in range(int(seconds)):
            wf.writeframes(block)
        wf.writeframes(b"\x00\x00" * int((seconds - int(seconds)) * sr))


def cmd_build(a) -> int:
    w = workdir(a.slug)
    scpath = w / "scenarios.json"
    if not scpath.exists():
        sys.exit(f"no scenarios.json in {w} — run plan first")
    doc = load_json(scpath, {}) or {}
    chosen = [int(x) for x in a.choose.replace("و", ",").replace("،", ",").split(",") if x.strip().isdigit()]
    if not chosen:
        sys.exit("--choose needs at least one scenario id, e.g. --choose 2,4")
    errs, _ = S.validate(doc, brand())
    if errs:
        for e in errs:
            print("  ✗", e)
        sys.exit("scenarios are not valid yet — fix them before building")
    S.score_all(doc, load_json(w / "brief.seed.json", {}) or {}, brand(), load_json(LOG_PATH, {}) or {})
    save_json(doc, scpath)

    preset = a.preset or (brand().get("defaults") or {}).get("preset", "standard")
    DELIVER.mkdir(parents=True, exist_ok=True)
    results = []
    for sid in chosen:
        print(f"\n=== scenario #{sid} ===")
        spec_path, spec = compile_one(doc, sid, brand(), a.slug, getattr(a, "theme", None))

        # the verbal gate runs *before* anything is built: no scene is rendered with copy that fails
        lint = copy_lint.lint_spec(spec, brand())
        for x in lint.fails:
            print(f"  ✗ copy [{x['where']}] {x['msg']}")
        for x in lint.warns:
            print(f"  ⚠ copy [{x['where']}] {x['msg']}")
        if lint.fails and not getattr(a, "force_copy", False):
            print(f"  ⛔ #{sid} not built — fix the copy, or pass --force-copy to build anyway")
            results.append({"id": sid, "ok": False, "stage": "copy", "spec": str(spec_path)})
            continue
        print(f"  copy ✓ {len(lint.fails)} failures · {len(lint.warns)} warnings" if not lint.fails
              else f"  copy ⚠ forced past {len(lint.fails)} failures")

        # long-text blocks are sized from their copy, not from the scaffold: fit them before building
        # (short-form reels are untouched — the cta is only grown if its own copy does not fit)
        if any(s.get("type") in LONG_TEXT for s in spec.get("scenes") or []):
            if run([sys.executable, HERE / "retime.py", str(spec_path), "--write"]):
                print("  ⚠ retime failed — building with the scaffold's lengths")
            else:
                spec = load_json(spec_path, {}) or spec

        proj = w / f"project-{sid}"
        bcmd = [sys.executable, HERE / "build_reel.py", str(spec_path), "--out", str(proj)]
        if getattr(a, "theme", None):
            bcmd += ["--theme", a.theme]
        rc = run(bcmd)
        if rc:
            print(f"  ✗ build failed for #{sid}")
            results.append({"id": sid, "ok": False, "stage": "build"})
            continue

        audio_ok = have("ffmpeg")  # ffprobe is optional: _common.media_duration falls back to ffmpeg
        published_audio = False
        if audio_ok:
            mcmd = [sys.executable, HERE / "mix.py", str(proj)]
            if not getattr(a, "strict_recitation", False):
                mcmd.append("--allow-missing-recitation")
            rc = run(mcmd)
            if rc:
                print("  ⚠ mix failed — writing a silent placeholder so the project stays inspectable")
                ensure_silence(proj / "assets" / "audio" / "mix.wav", float(spec["duration"]))
            else:
                published_audio = True
        else:
            print("  ⚠ ffmpeg not installed — writing a silent placeholder track")
            ensure_silence(proj / "assets" / "audio" / "mix.wav", float(spec["duration"]))

        vcmd = [sys.executable, HERE / "verify.py", str(proj), "--light", "--source-spec", str(spec_path)]
        if not audio_ok:
            vcmd.append("--no-audio")

        mp4 = DELIVER / f"{a.slug}-{sid}.mp4"
        if a.render:
            if not (have("node") and hf_installed() and audio_ok):
                print("  ⚠ render skipped: needs node ≥22, hyperframes and ffmpeg (source scripts/env.sh)")
            else:
                rc = run(["bash", HERE / "render.sh", str(proj), str(mp4)])
                if rc == 0:
                    run(vcmd + ["--render", str(mp4), "--no-check"])
                else:
                    print("  ✗ render failed")
        run(vcmd)

        kit_dir = DELIVER / f"{a.slug}-{sid}"
        if not a.no_kit:
            kcmd = [sys.executable, HERE / "social_kit.py", str(spec_path), "--out", str(kit_dir / "kit"),
                    "--preset", preset]
            for opt, val in (("--brief", a.brief), ("--texts", a.texts), ("--publish-at", a.publish_at)):
                if val:
                    kcmd += [opt, val]
            run(kcmd)
        results.append({"id": sid, "ok": not lint.fails, "theme": spec.get("theme"), "spec": str(spec_path), "project": str(proj),
                        "mp4": str(mp4) if mp4.exists() else None, "kit": str(kit_dir / "kit")})

    log_entry(a.slug, doc, chosen, preset, results)
    print("\n=== summary ===")
    for r in results:
        print(f"  #{r['id']}: spec ✓ · project ✓ · mp4 {'✓' if r.get('mp4') else '—'} · kit {r.get('kit', '—')}")
    if not have("ffmpeg"):
        print("\nRemaining for a real render: install ffmpeg, then re-run with --render (see scripts/env.sh).")
    return 0 if all(r["ok"] for r in results) else 1


def log_entry(slug: str, doc: dict, chosen: list[int], preset: str, results: list[dict]) -> None:
    log = load_json(LOG_PATH, {}) or {"reels": []}
    reels = log.setdefault("reels", [])
    scs = {s.get("id"): s for s in doc.get("scenarios") or []}
    for sid in chosen:
        sc = scs.get(sid) or {}
        entry = {
            "slug": slug, "scenario": sid, "date": str(date.today()),
            "archetype": sc.get("archetype"), "angle": sc.get("angle"),
            "hook_formula": (sc.get("hook") or {}).get("formula"),
            "cta": ((next((x for x in sc.get("scenes") or [] if x.get("type") == "cta"), {}) or {}).get("share")),
            "topic": sc.get("title_fa"), "duration": sum(float(x.get("seconds", 0)) for x in sc.get("scenes") or []),
            "platforms": (brand().get("defaults") or {}).get("platform_priority"),
            "preset": preset, "status": "built", "metrics_48h": None,
        }
        prev = next((r for r in reels if r.get("slug") == slug and r.get("scenario") == sid), None)
        if prev:
            keep = {k: prev.get(k) for k in ("status", "metrics_48h") if prev.get(k) not in (None, "built")}
            prev.update(entry)
            prev.update(keep)
            continue
        reels.append(entry)
    save_json(log, LOG_PATH)


# ----------------------------------------------------------------------------- kit / status / log / series
def cmd_kit(a) -> int:
    w = workdir(a.slug)
    spec = w / f"spec-{a.id}.json"
    if not spec.exists():
        sys.exit(f"{spec} not found — build scenario #{a.id} first")
    out = DELIVER / f"{a.slug}-{a.id}" / "kit"
    cmd = [sys.executable, HERE / "social_kit.py", str(spec), "--out", str(out),
           "--preset", a.preset or "standard"]
    for opt, val in (("--brief", a.brief), ("--texts", a.texts), ("--publish-at", a.publish_at)):
        if val:
            cmd += [opt, val]
    return run(cmd)


def cmd_status(a) -> int:
    w = workdir(a.slug)
    if not w.exists():
        print(f"no work directory {w}")
        return 1
    print(f"{w}")
    for p in sorted(w.iterdir()):
        mark = "dir " if p.is_dir() else "file"
        print(f"  {mark} {p.name}")
    print(f"\n{DELIVER}")
    for p in sorted(DELIVER.glob(f"{a.slug}*")):
        print(f"  {p.name}")
    return 0


def cmd_log(a) -> int:
    log = load_json(LOG_PATH, {}) or {"reels": []}
    hit = None
    for r in log.get("reels", []):
        if r.get("slug") == a.slug and r.get("scenario") == a.id:
            hit = r
            break
    if not hit:
        sys.exit(f"no log entry for {a.slug} #{a.id}")
    hit["status"] = a.status
    if a.metrics:
        hit["metrics_48h"] = a.metrics
    save_json(log, LOG_PATH)
    print(f"logged {a.slug} #{a.id} → {a.status}")
    return 0


def cmd_series(a) -> int:
    w = workdir(a.slug)
    series = load_json(w / "series.json")
    if not series:
        seed = load_json(w / "brief.seed.json", {}) or {}
        shape = seed.get("shape") or {}
        print(f"no series.json in {w}")
        if shape.get("mode") == "series":
            print(f"the brief suggests a {shape.get('parts')}-part series: {shape.get('reason')}")
            print("create series.json (references/series.md §Planning a series) and re-run.")
        else:
            print("the brief does not call for a series.")
        return 0
    print(f"# {series.get('title_ar', '')} — {series.get('title_fa', '')}")
    for p in series.get("parts") or []:
        print(f"  {p.get('n')}. [{p.get('status', 'planned')}] {p.get('question', '')} — {p.get('source', '')}")
    print("\nBuild a part: python3 scripts/reel.py plan <slug> --finalize")
    return 0


# ----------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("intake")
    p.add_argument("inputs", nargs="*", help="text file(s), a directory, '-' for stdin, or nothing with --sheets")
    p.add_argument("--slug", required=True)
    p.add_argument("--sheets", nargs="*", default=[])

    p = sub.add_parser("plan")
    p.add_argument("slug")
    p.add_argument("--count", type=int, default=4)
    p.add_argument("--finalize", action="store_true")
    p.add_argument("--theme", default=None, help="main · mourning — palette of the preview")

    p = sub.add_parser("build")
    p.add_argument("slug")
    p.add_argument("--choose", required=True)
    p.add_argument("--preset", choices=["minimal", "standard", "full"], default=None)
    p.add_argument("--theme", default=None, help="main · mourning — the palette this reel is built in")
    p.add_argument("--render", action="store_true")
    p.add_argument("--no-kit", action="store_true")
    p.add_argument("--brief", default=None)
    p.add_argument("--texts", default=None)
    p.add_argument("--publish-at", default=None)

    p = sub.add_parser("kit")
    p.add_argument("slug")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--preset", choices=["minimal", "standard", "full"], default=None)
    p.add_argument("--brief", default=None)
    p.add_argument("--texts", default=None)
    p.add_argument("--publish-at", default=None)

    p = sub.add_parser("status")
    p.add_argument("slug")

    p = sub.add_parser("log")
    p.add_argument("slug")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--status", required=True, choices=["built", "rendered", "published", "dropped"])
    p.add_argument("--metrics", default=None)

    p = sub.add_parser("series")
    p.add_argument("slug")

    a = ap.parse_args()
    rc = {"intake": cmd_intake, "plan": cmd_plan, "build": cmd_build, "kit": cmd_kit,
          "status": cmd_status, "log": cmd_log, "series": cmd_series}[a.cmd](a)
    if rc is not None:
        sys.exit(rc)


if __name__ == "__main__":
    main()
