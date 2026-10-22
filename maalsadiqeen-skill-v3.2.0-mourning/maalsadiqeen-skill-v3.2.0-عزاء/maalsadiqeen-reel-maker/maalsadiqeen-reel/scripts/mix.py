#!/usr/bin/env python3
"""
mix.py — build the soundtrack of a reel from spec.resolved.json (written by build_reel.py).

    python3 mix.py <project_dir> [--recitation path.wav] [--stems name=path:at:gain ...] [--no-bed] [--dry-run]

Reads  <project>/spec.resolved.json  →  "audio" section + resolved cues
Writes <project>/assets/audio/{bed.wav, mix-raw.wav, <audio.file>}  (default mix.wav), prints LUFS before/after.

audio section of the spec (all optional):
  "mode":        "silent" (default: recitation + sound design + bed, NO voice) | "narrated"
  "file":        output file name inside assets/audio (default mix.wav; must match the <audio> src in index.html)
  "recitation":  {"ref": "9:119", "edition": "ar.mahermuaiqly", "at": 3.9, "file": "assets/audio/recite.wav", "gain_db": 0}
                 → if "file" is missing, recite.py downloads+trims it. "at" defaults to the first verse scene's first word cue.
  "stems":       [{"file": "...wav", "at": 12.3, "gain_db": -2, "fade_in": 0.05, "fade_out": 0.3}]   (narration or other voice stems)
  "bed":         {"gain_db": -7, "duck_db": -9, "fade_out": 2.2, "seed": 7}   or  false to disable
  "auto_sfx":    true (default) → sound design derived from the cues (see references/audio.md for the design rules)
  "sfx":         [{"name": "chime", "at": 30.4, "gain_db": -16}]  extra/explicit events (names = files in assets/sfx)
  "target_lufs": -15.5 (default; -14 for louder platforms), "true_peak_db": -1.5
"""
import argparse, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from _common import media_duration  # noqa: E402
SFX_DIR = os.path.join(SKILL, "assets", "sfx")


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        sys.stderr.write(r.stderr[-4000:])
        raise SystemExit(f"command failed: {' '.join(cmd[:3])} …")
    return r


def dur(path):
    d = media_duration(path)
    if d is None:
        raise SystemExit(f"cannot read the duration of {path} — install ffmpeg/ffprobe")
    return float(d)


def lufs(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=framelog=verbose", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.findall(r"^\s+I:\s+(-?[\d.]+) LUFS", r.stderr, re.M)
    return float(m[-1]) if m else None


def sfx_path(name):
    for ext in (".wav", ".mp3", ".ogg"):
        p = os.path.join(SFX_DIR, name + ext)
        if os.path.exists(p):
            return p
    raise SystemExit(f"unknown sfx '{name}' (looked in {SFX_DIR})")


# ----------------------------------------------------------------------------- sound design from cues
def auto_events(res):
    """Derive SFX events from resolved cues. Returns [(name, at, gain_db, extra_filter)]."""
    ev = []
    cuts = res.get("cuts", [])
    dur_total = res["duration"]
    first = res["scenes"][0]
    for t in cuts:                                    # every cut: short whoosh
        ev.append(("whoosh-short", t, -19, ""))
    ev.append(("whoosh-short", first["start"] + 0.34, -24, ""))
    hero_t = None
    for sc in res["scenes"]:
        c = sc["cues"]; ty = sc["type"]
        if ty == "hook" and "emphasis" in c:
            ev.append(("sparkle", c["emphasis"], -19, ""))
        elif ty == "verse":
            if c.get("words"):
                ev.append(("sparkle", c["words"][0] + 0.05, -16, ""))
            if "highlight" in c:
                ev.append(("ping", c["highlight"], -24, ""))
        elif ty == "contrast":
            for k in ("wrong", "right", "line3", "line4"):
                if k in c: ev.append(("click-soft", c[k], -23, ""))
            if "strike" in c: ev.append(("pen-scratch", c["strike"], -14, ""))
            if "right" in c: ev.append(("pop", c["right"] + 0.95, -21, ""))
            if "line3" in c: ev.append(("pop", c["line3"], -19, ""))
        elif ty == "answer":
            for k in ("q1", "q2", "after", "source"):
                if k in c: ev.append(("click-soft", c[k], -23, ""))
            if "hero" in c:
                hero_t = c["hero"]
                ev.append(("riser", hero_t - 6.0, -23, "atrim=start=4.03,asetpts=PTS-STARTPTS,afade=t=in:d=2.5"))
                ev.append(("impact-bass-1", hero_t, -14, ""))
        elif ty == "proof":
            if "seal" in c: ev.append(("chime", c["seal"], -16, ""))
            for t in c.get("cards", []): ev.append(("pop", t, -19, ""))
            for k in ("line1", "line2", "attribution"):
                if k in c: ev.append(("click-soft", c[k], -23, ""))
        elif ty == "quote":
            for t in c.get("lines", []): ev.append(("click-soft", t, -23, ""))
            if c.get("words"): ev.append(("sparkle", c["words"][0] + 0.05, -18, ""))
            if "hero" in c and sc.get("hero"): ev.append(("impact-bass-2", c["hero"], -16, ""))
            if "attribution" in c: ev.append(("click-soft", c["attribution"], -23, ""))
        elif ty == "list":
            if "title" in c: ev.append(("click-soft", c["title"], -23, ""))
            for t in c.get("items", []): ev.append(("pop", t, -20, ""))
        elif ty == "title":
            if "title" in c: ev.append(("sparkle", c["title"], -18, ""))
        elif ty in ("paragraph", "definition"):
            for k in ("kicker", "label", "term"):
                if k in c: ev.append(("click-soft", c[k], -22, ""))
            for i in range(1, 9):
                if f"p{i}" in c: ev.append(("click-soft", c[f"p{i}"], -25, ""))
            if "note" in c: ev.append(("click-soft", c["note"], -26, ""))
            if "source" in c: ev.append(("click-soft", c["source"], -27, ""))
        elif ty == "steps":
            if "title" in c: ev.append(("click-soft", c["title"], -23, ""))
            for i in range(1, 5):
                if f"i{i}" in c: ev.append(("pop", c[f"i{i}"], -21, ""))
        elif ty == "timeline":
            if "title" in c: ev.append(("click-soft", c["title"], -24, ""))
            for i in range(1, 5):
                if f"e{i}" in c: ev.append(("click-soft", c[f"e{i}"], -24, ""))
        elif ty == "compare":
            if "title" in c: ev.append(("click-soft", c["title"], -24, ""))
            if "head_a" in c: ev.append(("click-soft", c["head_a"], -23, ""))
            for i in range(1, 4):
                if f"a{i}" in c: ev.append(("click-soft", c[f"a{i}"], -25, ""))
            if "verdict" in c: ev.append(("pop", c["verdict"], -19, ""))
        elif ty == "qa":
            if "q" in c: ev.append(("sparkle", c["q"], -20, ""))
            if "hero" in c: ev.append(("impact-bass-2", c["hero"], -18, ""))
            for i in range(1, 9):
                if f"p{i}" in c: ev.append(("click-soft", c[f"p{i}"], -25, ""))
            if "note" in c: ev.append(("click-soft", c["note"], -26, ""))
        elif ty == "cta":
            for k in ("line1", "line2"):
                if k in c: ev.append(("click-soft", c[k], -23, ""))
            if "share" in c: ev.append(("whoosh", c["share"] + 0.1, -18, ""))
            if "final" in c: ev.append(("sparkle", c["final"] - 0.05, -14, ""))
    return [e for e in ev if 0 <= e[1] < dur_total - 0.2]


def ms(x):
    return int(round(x * 1000))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--recitation", help="override recitation file (wav/mp3)")
    ap.add_argument("--allow-missing-recitation", action="store_true",
                    help="keep mixing (bed + sfx) when the recitation cannot be fetched; the result is not publishable")
    ap.add_argument("--stem", action="append", default=[], help="extra stem: path:at[:gain_db]")
    ap.add_argument("--no-bed", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="print the event list only")
    a = ap.parse_args()
    proj = os.path.abspath(a.project)
    with open(os.path.join(proj, "spec.resolved.json"), encoding="utf-8") as f:
        res = json.load(f)
    au = res.get("audio") or {}
    D = float(res["duration"])
    adir = os.path.join(proj, "assets", "audio")
    os.makedirs(adir, exist_ok=True)
    out_name = au.get("file", "mix.wav")
    target = float(au.get("target_lufs", -15.5))
    tp = float(au.get("true_peak_db", -1.5))
    limit = 10 ** (tp / 20)

    inputs, chains, mixes = [], [], []   # ffmpeg -i list, filter chains, labels to mix

    def add_input(path):
        inputs.append(path); return len(inputs) - 1

    # --- recitation
    rec = au.get("recitation")
    rec_label = None
    if rec or a.recitation:
        rec = rec or {}
        rpath = a.recitation or rec.get("file")
        if rpath and not os.path.isabs(rpath):
            rpath = os.path.join(proj, rpath)
        if not rpath or not os.path.exists(rpath):
            if not rec.get("ref"):
                raise SystemExit("recitation needs 'file' or 'ref' (surah:ayah)")
            rpath = os.path.join(adir, "recite.wav")
            try:
                run([sys.executable, os.path.join(HERE, "recite.py"), rec["ref"],
                     "--edition", rec.get("edition", "ar.mahermuaiqly"), "--out", rpath])
            except SystemExit:
                if a.allow_missing_recitation:
                    print("⚠ recitation unavailable — mixing without it (the reel is NOT publishable yet)")
                    rec, rpath = None, None
                else:
                    raise
        if rpath and rec:
            at = rec.get("at")
            if at is None:  # default: first word cue of the first verse scene
                for sc in res["scenes"]:
                    if sc["type"] == "verse" and sc["cues"].get("words"):
                        at = sc["cues"]["words"][0]; break
                at = 0.5 if at is None else at
            rd = dur(rpath)
            i = add_input(rpath)
            chains.append(f"[{i}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={rec.get('gain_db',0)}dB,"
                          f"afade=t=in:d=0.08,afade=t=out:st={max(0, rd-0.35):.3f}:d=0.35,adelay={ms(at)}|{ms(at)}[rec]")
            rec_label = "rec"
            print(f"recitation: {os.path.basename(rpath)} ({rd:.2f}s) at {at}s")

    # --- voice stems (narration) — only when explicitly requested
    stem_labels = []
    stems = list(au.get("stems") or [])
    for s in a.stem:
        parts = s.split(":"); stems.append({"file": parts[0], "at": float(parts[1]), "gain_db": float(parts[2]) if len(parts) > 2 else 0})
    for k, st in enumerate(stems):
        p = st["file"] if os.path.isabs(st["file"]) else os.path.join(proj, st["file"])
        sd = dur(p); i = add_input(p)
        fo = st.get("fade_out", 0.25)
        chains.append(f"[{i}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={st.get('gain_db',0)}dB,"
                      f"afade=t=in:d={st.get('fade_in',0.05)},afade=t=out:st={max(0, sd-fo):.3f}:d={fo},adelay={ms(st['at'])}|{ms(st['at'])}[st{k}]")
        stem_labels.append(f"st{k}")

    # voice bus (recitation + stems) = sidechain source for the bed
    voice_labels = ([rec_label] if rec_label else []) + stem_labels
    if voice_labels:
        if len(voice_labels) == 1:
            chains.append(f"[{voice_labels[0]}]asplit=2[voice_out][voice_sc0]")
        else:
            chains.append("".join(f"[{l}]" for l in voice_labels) + f"amix=inputs={len(voice_labels)}:normalize=0:duration=longest,asplit=2[voice_out][voice_sc0]")
        chains.append(f"[voice_sc0]apad=whole_dur={D+1}[voice_sc]")   # finite pad: an infinite apad makes ffmpeg spin forever
        mixes.append("voice_out")

    # --- bed
    bed = au.get("bed", {})
    if bed is not False and not a.no_bed:
        bed = bed or {}
        bpath = os.path.join(adir, "bed.wav")
        hero = None; final = None
        for sc in res["scenes"]:
            if sc["type"] == "answer" and "hero" in sc["cues"]: hero = sc["cues"]["hero"]
            if sc["type"] == "quote" and sc["cues"].get("hero") and hero is None: hero = sc["cues"]["hero"]
            if sc["type"] == "cta" and "final" in sc["cues"]: final = sc["cues"]["final"]
        cmd = [sys.executable, os.path.join(HERE, "gen_bed.py"), bpath, "--duration", str(D), "--cuts", ",".join(str(c) for c in res.get("cuts", [])), "--seed", str(bed.get("seed", 7))]
        if hero is not None: cmd += ["--hero", str(hero)]
        if final is not None: cmd += ["--final", str(final)]
        if not os.path.exists(bpath) or bed.get("regen", True):
            run(cmd)
        i = add_input(bpath)
        fo = float(bed.get("fade_out", 2.2))
        chains.append(f"[{i}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={bed.get('gain_db',-7)}dB,afade=t=out:st={D-fo:.2f}:d={fo}[bed0]")
        if voice_labels:
            duck = float(bed.get("duck_db", -9))
            ratio = {-6: 2.2, -9: 3, -12: 4}.get(int(duck), 3)
            chains.append(f"[bed0][voice_sc]sidechaincompress=threshold=0.02:ratio={ratio}:attack=40:release=800:makeup=1:level_sc=1[bed]")
        else:
            chains.append("[bed0]acopy[bed]")
        mixes.append("bed")

    # --- sound design
    events = auto_events(res) if au.get("auto_sfx", True) else []
    for e in au.get("sfx") or []:
        events.append((e["name"], float(e["at"]), float(e.get("gain_db", -18)), e.get("filter", "")))
    if a.dry_run:
        for n, t, g, _ in sorted(events, key=lambda x: x[1]):
            print(f"{t:7.2f}  {n:14s} {g:+.0f} dB")
        return
    by_name = {}
    for n, t, g, f in events:
        by_name.setdefault(n, []).append((t, g, f))
    sfx_labels = []
    for n, evs in by_name.items():
        i = add_input(sfx_path(n))
        k = len(evs)
        chains.append(f"[{i}:a]aformat=sample_rates=48000:channel_layouts=stereo,asplit={k}" + "".join(f"[{n}_{j}]" for j in range(k)) if k > 1
                      else f"[{i}:a]aformat=sample_rates=48000:channel_layouts=stereo[{n}_0]")
        for j, (t, g, f) in enumerate(evs):
            pre = (f + ",") if f else ""
            lab = re.sub(r"[^a-z0-9]", "", n) + f"{j}"
            chains.append(f"[{n}_{j}]{pre}volume={g}dB,adelay={ms(t)}|{ms(t)}[x{lab}]")
            sfx_labels.append(f"x{lab}")
    if sfx_labels:
        chains.append("".join(f"[{l}]" for l in sfx_labels) + f"amix=inputs={len(sfx_labels)}:normalize=0:duration=longest[sfx]")
        mixes.append("sfx")

    if not mixes:
        raise SystemExit("nothing to mix (no recitation, stems, bed or sfx)")
    chains.append("".join(f"[{l}]" for l in mixes) + f"amix=inputs={len(mixes)}:normalize=0:duration=longest,apad=whole_dur={D},atrim=0:{D}[out]")

    raw = os.path.join(adir, "mix-raw.wav")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for p in inputs: cmd += ["-i", p]
    cmd += ["-filter_complex", ";\n".join(chains), "-map", "[out]", "-t", str(D), "-ar", "48000", "-c:a", "pcm_s16le", raw]
    run(cmd)
    li = lufs(raw)
    gain = round(target - li, 2)
    final_path = os.path.join(adir, out_name)
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", raw, "-af",
         f"volume={gain}dB,alimiter=limit={limit:.3f}:attack=4:release=90:level=false", "-ar", "48000", "-c:a", "pcm_s16le", final_path])
    print(f"events: {len(events)} sfx · inputs: {len(inputs)} · raw {li} LUFS → gain {gain:+} dB → {lufs(final_path)} LUFS")
    print(f"wrote {final_path} ({dur(final_path):.3f}s)")


if __name__ == "__main__":
    main()
