#!/usr/bin/env python3
"""
verify.py — QC gate for a reel project (run BEFORE rendering, and again on the render).

    python3 verify.py <project_dir> [--render out.mp4] [--snaps 1.2,11.5,...] [--no-check] [--target-lufs -15.5]

Pre-render:  spec/pacing rules · index.html sanity (no dir=rtl on <html>, duration ≤ 60, audio present)
             · `hyperframes check` (lint+runtime+layout+contrast) · snapshots at the decisive beats → qc/sheet.jpg
Post-render: ffprobe (1080×1920, 30 fps, duration, audio) · integrated LUFS vs target · true peak.
Exit code 1 on any FAIL. Open qc/sheet.jpg and look at every frame — the eye is the last gate.
"""
import argparse, json, os, re, subprocess, sys, glob, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _common import media_duration  # noqa: E402
FAILS, WARNS, OKS = [], [], []


def ok(m): OKS.append(m); print("  ✓", m)
def warn(m): WARNS.append(m); print("  ⚠", m)
def fail(m): FAILS.append(m); print("  ✗", m)


def sh(cmd, cwd=None, timeout=600):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def ffprobe(path, sel, entries):
    r = sh(["ffprobe", "-v", "error", "-select_streams", sel, "-show_entries", entries, "-of", "json", path])
    try:
        return json.loads(r.stdout)["streams"][0]
    except Exception:
        return {}


def lufs(path):
    r = sh(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true:framelog=verbose", "-f", "null", "-"])
    I = re.findall(r"^\s+I:\s+(-?[\d.]+) LUFS", r.stderr, re.M)
    P = re.findall(r"^\s+Peak:\s+(-?[\d.]+) dBFS", r.stderr, re.M)
    return (float(I[-1]) if I else None, float(P[-1]) if P else None)


# ----------------------------------------------------------------------------- theme contrast
def _rgb(hex_or_rgb: str):
    h = (hex_or_rgb or "").strip()
    if h.startswith("#") and len(h) in (4, 7):
        h = h[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    m = re.findall(r"[\d.]+", h)
    return tuple(float(x) for x in m[:3]) if len(m) >= 3 else None


def _lum(rgb) -> float:
    def ch(v):
        v = float(v) / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg: str, bg: str) -> float | None:
    a, b = _rgb(fg), _rgb(bg)
    if not a or not b:
        return None
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def key_times(res):
    """decisive beats: hook emphasis, verse highlight, strike, hero, seal/cards, final/brand."""
    ts = []
    for sc in res["scenes"]:
        c = sc["cues"]
        for k in ("emphasis", "highlight", "strike", "hero", "seal", "final"):
            if isinstance(c.get(k), (int, float)):
                ts.append(round(c[k] + 0.9, 2))
        if sc["type"] in ("quote", "list", "title", "contrast", "proof",
                          "paragraph", "definition", "steps", "timeline", "compare", "qa"):
            ts.append(round(sc["end"] - 0.8, 2))
    ts = sorted(set(t for t in ts if 0 < t < res["duration"]))
    # thin to <= 8
    while len(ts) > 8:
        ts = ts[::2] if len(ts) > 12 else ts[:-1]
    return ts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project"); ap.add_argument("--render"); ap.add_argument("--snaps")
    ap.add_argument("--no-check", action="store_true"); ap.add_argument("--target-lufs", type=float, default=None)
    ap.add_argument("--light", action="store_true", help="skip hyperframes check + snapshots (fast, no browser)")
    ap.add_argument("--no-audio", action="store_true", help="skip audio presence/duration checks (no ffprobe)")
    ap.add_argument("--source-spec", default=None, help="spec.json to run the copy gate on")
    ap.add_argument("--kit", default=None, help="kit directory to validate (captions + comments)")
    a = ap.parse_args()
    proj = os.path.abspath(a.project)
    qc = os.path.join(proj, "qc"); os.makedirs(qc, exist_ok=True)
    res = json.load(open(os.path.join(proj, "spec.resolved.json"), encoding="utf-8"))
    html = open(os.path.join(proj, "index.html"), encoding="utf-8").read()
    D = float(res["duration"])
    print(f"QC · {os.path.basename(proj)} · {D}s · {len(res['scenes'])} scenes")

    # ---- 1. spec / pacing
    print("[1] spec & pacing")
    (ok if D <= 60 else fail)(f"duration {D}s ≤ 60s" if D <= 60 else f"duration {D}s > 60s — cut a scene")
    (ok if 30 <= D else warn)(f"duration {D}s ≥ 30s" if D >= 30 else f"duration {D}s < 30s — short for a narrative reel")
    types = [s["type"] for s in res["scenes"]]
    (ok if types and types[0] == "hook" else fail)("first scene is a hook" if types and types[0] == "hook" else "first scene is not a hook")
    (ok if types and types[-1] == "cta" else warn)("last scene is a cta" if types and types[-1] == "cta" else "last scene is not a cta (no brand card?)")
    if res["scenes"][0]["end"] > 4.5:
        warn(f"hook scene is {res['scenes'][0]['end']}s — keep the first cut ≤ 4.5s (3-second cliff)")
    LONG_TEXT = {"paragraph", "definition", "steps", "timeline", "compare", "qa"}
    static_max, stretch = 0, 0
    for sc in res["scenes"]:
        c = sc["cues"]
        pts = sorted(v for k, v in c.items() if isinstance(v, (int, float)) and k not in ("highlight", "strike", "line4_gold", "label", "brand"))
        for arr in ("words", "cards", "lines", "items"):
            pts += list(c.get(arr, []))
        pts = sorted(set(pts))
        prev = sc["start"]
        limit = 5.0 if sc["type"] in LONG_TEXT else 3.4     # a prose sentence is read, not stared at
        for t in pts + [sc["end"]]:
            gap = t - prev
            static_max = max(static_max, gap)
            if gap > limit:
                stretch = max(stretch, gap)
            prev = t
        for p, q in zip(pts, pts[1:]):
            if q - p < 0.35 and sc["type"] not in ("verse", "quote"):
                warn(f"[{sc['id']}] two reveals only {q-p:.2f}s apart ({p}s, {q}s)")
        if sc["type"] == "hook" and sc["end"] - sc["start"] < 2.6:
            warn(f"[{sc['id']}] hook shorter than 2.6s")
    if stretch:
        warn(f"longest static stretch {stretch:.2f}s — > 3.4s (5.0s in prose), add a reveal or shorten")
    else:
        ok(f"longest static stretch {static_max:.2f}s")

    # ---- 2. html sanity
    print("[2] index.html")
    (fail if re.search(r"<html[^>]*\bdir=", html) else ok)("no dir attribute on <html> (render-breaker)" if not re.search(r"<html[^>]*\bdir=", html) else "<html dir=…> present — remove it (blank render)")
    m = None if a.no_audio else re.search(r'<audio[^>]*src="([^"]+)"', html)
    if a.no_audio:
        warn("audio checks skipped (--no-audio): no ffprobe here, the soundtrack is a placeholder")
    elif m:
        ap_ = os.path.join(proj, m.group(1))
        (ok if os.path.exists(ap_) else fail)(f"audio {m.group(1)} present" if os.path.exists(ap_) else f"audio {m.group(1)} missing — run mix.py")
        if os.path.exists(ap_):
            ad = media_duration(ap_)
            if ad is None:
                warn("audio duration unknown (no ffprobe/ffmpeg) — listen to it once")
            else:
                (ok if abs(ad - D) < 0.25 else fail)(f"audio duration {ad:.2f}s matches" if abs(ad - D) < 0.25 else f"audio duration {ad:.2f}s ≠ {D}s")
    else:
        warn("no <audio> element")
    for f in ("assets/fonts/AmiriQuran.ttf", "assets/fonts/NotoKufiArabic-Bold.ttf", "assets/img/logo.png", "assets/gsap.min.js", "hyperframes.json"):
        (ok if os.path.exists(os.path.join(proj, f)) else fail)(f"{f}" if os.path.exists(os.path.join(proj, f)) else f"{f} missing")
    if "z-index: -1" in html or "z-index:-1" in html:
        warn("negative z-index found — use DOM order for layering")

    # ---- 3. hyperframes check + snapshots
    workdir = os.environ.get("HF_WORKDIR", os.path.expanduser("~/reel-sadiqeen"))
    env = dict(os.environ, TMPDIR=os.environ.get("TMPDIR", os.path.expanduser("~/.cache/tmp")), HYPERFRAMES_SKIP_SKILLS="1",
               HYPERFRAMES_EXTRACT_CACHE_DIR=os.environ.get("HYPERFRAMES_EXTRACT_CACHE_DIR", os.path.expanduser("~/.cache/hfx")))
    if os.path.isdir("/opt/node22/bin"):
        env["PATH"] = "/opt/node22/bin:" + env.get("PATH", "")
    os.makedirs(env["TMPDIR"], exist_ok=True); os.makedirs(env["HYPERFRAMES_EXTRACT_CACHE_DIR"], exist_ok=True)
    if not a.no_check and not a.light:
        print("[3] hyperframes check")
        if not os.path.isdir(os.path.join(workdir, "node_modules", "hyperframes")):
            fail(f"hyperframes not installed in {workdir} (source scripts/env.sh)")
        else:
            r = subprocess.run(["npx", "hyperframes", "check", proj], cwd=workdir, env=env, capture_output=True, text=True, timeout=900)
            out = r.stdout + r.stderr
            open(os.path.join(qc, "check.log"), "w").write(out)
            passed = "Check passed" in out
            browser = "Browser session never ran" not in out
            (ok if passed else fail)("hyperframes check passed" if passed else "hyperframes check FAILED — see qc/check.log")
            (ok if browser else fail)("browser session ran" if browser else "browser never ran (missing Chrome libs?)")
            mc = re.search(r"(\d+)/(\d+) text checks pass", out)
            if mc:
                (ok if mc.group(1) == mc.group(2) else warn)(f"contrast {mc.group(1)}/{mc.group(2)} pass WCAG AA")
            ml = re.search(r"(\d+) issues across (\d+) sample", out)
            if ml:
                (ok if ml.group(1) == "0" else warn)(f"layout {ml.group(1)} issues across {ml.group(2)} samples")
            times = [float(x) for x in a.snaps.split(",")] if a.snaps else key_times(res)
            sd = os.path.join(qc, "snaps"); shutil.rmtree(sd, ignore_errors=True)
            r = subprocess.run(["npx", "hyperframes", "snapshot", proj, "--at", ",".join(str(t) for t in times), "-o", sd, "--no-end"],
                               cwd=workdir, env=env, capture_output=True, text=True, timeout=900)
            frames = sorted(glob.glob(os.path.join(sd, "frame-*.png")))
            if frames:
                cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
                for f in frames: cmd += ["-i", f]
                cmd += ["-filter_complex", "".join(f"[{i}]" for i in range(len(frames))) + f"hstack={len(frames)},scale={min(1920, 320*len(frames))}:-1" if len(frames) > 1 else "scale=540:-1",
                        os.path.join(qc, "sheet.jpg")]
                sh(cmd)
                ok(f"{len(frames)} snapshots at {times} → qc/sheet.jpg (LOOK AT IT: clipping, overlap, wrong line breaks, missing seal/logo)")
            else:
                fail("snapshots failed — see qc/snapshot.log"); open(os.path.join(qc, "snapshot.log"), "w").write(r.stdout + r.stderr)

    # ---- 4. render
    if a.render:
        print("[4] render")
        v = ffprobe(a.render, "v:0", "stream=width,height,r_frame_rate,duration,codec_name")
        au = ffprobe(a.render, "a:0", "stream=codec_name,sample_rate,channels")
        (ok if (v.get("width"), v.get("height")) == (1080, 1920) else fail)(f"{v.get('width')}×{v.get('height')}")
        fps = v.get("r_frame_rate", "0/1"); n, d = fps.split("/"); fpsv = float(n) / float(d)
        (ok if abs(fpsv - 30) < 0.1 else warn)(f"{fpsv:.2f} fps")
        vd = float(v.get("duration", 0))
        (ok if abs(vd - D) < 0.15 else fail)(f"video duration {vd:.3f}s (spec {D}s)")
        (ok if au else fail)(f"audio {au.get('codec_name')} {au.get('sample_rate')} Hz" if au else "NO AUDIO STREAM")
        target = a.target_lufs if a.target_lufs is not None else float((res.get("audio") or {}).get("target_lufs", -15.5))
        I, P = lufs(a.render)
        if I is not None:
            (ok if abs(I - target) <= 1.2 else warn)(f"integrated {I} LUFS (target {target})")
            (ok if P is not None and P <= -0.8 else warn)(f"true peak {P} dBTP")
        size = os.path.getsize(a.render) / 1e6
        (ok if size < 100 else warn)(f"{size:.1f} MB")

    # ---- 4b. theme: which palette this reel was built in, and whether it is readable
    print("[4] theme & contrast")
    theme_name, tokens = "main", {}
    try:
        brand_cfg = json.load(open(os.path.join(os.path.dirname(HERE), "config", "brand.json"), encoding="utf-8"))
        rp = os.path.join(proj, "spec.resolved.json")
        theme_name = (json.load(open(rp, encoding="utf-8")).get("theme") if os.path.exists(rp) else None) or "main"
        themes = brand_cfg.get("themes") or {}
        if themes:
            if theme_name not in themes:
                fail(f"unknown theme «{theme_name}» — available: {', '.join(themes)}")
            entry = themes.get(theme_name) or {}
            tokens = entry.get("tokens") or {}
            tokens = dict(tokens, label_ar=entry.get("label_ar") or theme_name)
    except (OSError, ValueError):
        warn("theme tokens unreadable — contrast not checked")
    if tokens:
        ci = contrast(tokens.get("ink", ""), tokens.get("paper", ""))
        cg = contrast(tokens.get("gold", ""), tokens.get("paper", ""))
        ck = contrast(tokens.get("green", ""), tokens.get("paper", ""))
        label = tokens.get("label_ar") or theme_name
        if ci is None:
            warn("theme contrast: tokens are not plain colours")
        else:
            (fail if ci < 6 else ok)(f"theme {theme_name} ({label}) · body contrast {ci:.1f}:1 (≥ 6)")
            if 6 <= ci < 7:
                warn(f"theme {theme_name} · body contrast {ci:.1f}:1 is AA-large only")
            if cg is not None:
                (warn if cg < 3 else ok)(f"theme {theme_name} · gold {cg:.1f}:1 against paper (≥ 3 for large type)")
            if ck is not None:
                (warn if ck < 4.5 else ok)(f"theme {theme_name} · sacred-text colour {ck:.1f}:1 (≥ 4.5)")
        if theme_name == "main" and (tokens.get("logo_filter") or "none") != "none":
            warn("main theme should not filter the logo")
        if theme_name == "mourning" and tokens.get("logo_filter") in (None, "", "none"):
            warn("mourning theme renders a dark logo on black — set logo_filter")

    # ---- 5. optional gates: copy + kit
    if a.source_spec:
        print("[5] copy gate")
        try:
            sys.path.insert(0, HERE)
            import copy_lint  # noqa: PLC0415
            spec = json.load(open(a.source_spec, encoding="utf-8"))
            brand = {}
            bp = os.path.join(os.path.dirname(HERE), "config", "brand.json")
            if os.path.exists(bp):
                brand = json.load(open(bp, encoding="utf-8"))
            L = copy_lint.lint_spec(spec, brand)
            (ok if not L.fails else fail)(f"copy: {len(L.fails)} failures, {len(L.warns)} warnings")
            for x in L.fails:
                fail(f"copy [{x['where']}] {x['msg']}")
        except Exception as e:  # never let the optional gate crash QC
            warn(f"copy gate skipped: {e}")
    if a.kit:
        print("[5] kit gate")
        vpath = os.path.join(a.kit, "validation.md")
        if os.path.exists(vpath):
            txt = open(vpath, encoding="utf-8").read()
            bad = txt.startswith("# اعتبارسنجی کیت — قرمز")
            (fail if bad else ok)("kit validation " + ("FAILED — see " + vpath if bad else "green"))
        else:
            warn(f"no validation.md in {a.kit} — run social_kit.py")

    print(f"\n{len(OKS)} ok · {len(WARNS)} warnings · {len(FAILS)} failures")
    for w in WARNS: print("  ⚠", w)
    for f in FAILS: print("  ✗", f)
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
