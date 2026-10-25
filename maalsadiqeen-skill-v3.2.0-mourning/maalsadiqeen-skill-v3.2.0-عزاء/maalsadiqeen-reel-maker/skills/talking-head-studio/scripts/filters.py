#!/usr/bin/env python3
"""
filters.py — turn a plan into one ffmpeg filter_complex.

The whole edit is a single filtergraph plus a single encode:

    source ──trim each keep range──► concat ──► reframe/zoom ──► look ──► subtitles ──► out
                                  └► concat ──► denoise/EQ ──► loudnorm ──► out

Why one graph: every extra encode costs quality and time, and every intermediate
file is a place for audio to drift out of sync. Segments are cut with trim (not
seek-based concat), so audio and video land on the same frame boundary.

Geometry: the source is scaled to *cover* the output frame, then a single
`zoompan` samples a moving, scaling window. Focus points measured on the source
(face centre) are pre-mapped through the cover-crop, so "keep the speaker
centred" stays true after the aspect change — the part most reframe tools get
wrong.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import clamp, piecewise_expr, resample_curve  # noqa: E402

MAX_CURVE_KEYS = 40
ZOOM_MIN, ZOOM_MAX = 1.0, 2.2


# --------------------------------------------------------------------------- geometry

def cover_map(src_w: int, src_h: int, out_w: int, out_h: int, fx: float, fy: float) -> tuple[float, float]:
    """
    Map a focus point measured on the source frame into the cover-cropped frame.

    cover: scale until both sides are >= output, then crop the excess equally.
    Returns fractions in the *cropped* frame, clamped to [0.05, 0.95].
    """
    if not (src_w and src_h):
        return 0.5, 0.42
    src_ar, out_ar = src_w / src_h, out_w / out_h
    if src_ar > out_ar:                     # source wider → crop left/right
        crop_w = src_h * out_ar
        off_x = (src_w - crop_w) / 2.0
        x = (fx * src_w - off_x) / crop_w
        y = fy
    else:                                   # source taller → crop top/bottom
        crop_h = src_w / out_ar
        off_y = (src_h - crop_h) / 2.0
        x = fx
        y = (fy * src_h - off_y) / crop_h
    return clamp(x, 0.05, 0.95), clamp(y, 0.05, 0.95)


def _clamp_focus_expr(expr: str, zoom_expr: str) -> tuple[str, str]:
    """Keep the sampled window inside the frame (zoompan will black-fill otherwise)."""
    x = f"max(0,min(iw-iw/({zoom_expr}),{expr}))"
    y = f"max(0,min(ih-ih/({zoom_expr}),{expr}))"
    return x, y


# --------------------------------------------------------------------------- zoom curves

def build_zoom_curve(segments: list[dict], mode: str, amplitude: float,
                     total: float) -> list[tuple[float, float]]:
    """
    A zoom (t, value) curve over *output* time.

    none   → flat 1.0
    in     → one slow push across the whole video (documentary feel)
    punch  → per-segment push-in that holds: the "edit punch" on every take
    out    → slow pull-back (reveal)
    pulse  → punch-in/out pairs, for high-energy pieces
    """
    amplitude = clamp(amplitude, 0.0, 0.45)
    if mode == "none" or amplitude == 0:
        return [(0.0, 1.0)]
    if mode == "in":
        return [(0.0, 1.0), (max(0.1, total), 1.0 + amplitude)]
    if mode == "out":
        return [(0.0, 1.0 + amplitude), (max(0.1, total), 1.0)]

    keys: list[tuple[float, float]] = []
    for seg in segments:
        a, b = seg["out_start"], seg["out_end"]
        length = b - a
        if length < 1.2:
            keys += [(a, 1.0), (b, 1.0)]
            continue
        ramp = clamp(length * 0.35, 0.45, 1.4)
        peak = 1.0 + amplitude
        if mode == "punch":
            keys += [(a, 1.0), (a + ramp, peak), (b, peak)]
        elif mode == "pulse":
            back = clamp(length * 0.30, 0.4, 1.0)
            keys += [(a, 1.0), (a + ramp, peak), (max(a + ramp, b - back), peak), (b, 1.0)]
        else:                                    # unknown → behave like punch
            keys += [(a, 1.0), (a + ramp, peak), (b, peak)]
    if not keys:
        return [(0.0, 1.0)]
    keys.append((total, keys[-1][1]))
    return resample_curve(keys, MAX_CURVE_KEYS)


def build_focus_curve(segments: list[dict], total: float) -> tuple[list[tuple[float, float]],
                                                                  list[tuple[float, float]]]:
    """Per-segment focus (median face position in that take), ramped between takes."""
    xs, ys = [], []
    for seg in segments:
        fx, fy = seg.get("focus") or (0.5, 0.42)
        # a short ease at the start of each take avoids a visible snap after a cut
        ease = min(0.35, max(0.12, (seg["out_end"] - seg["out_start"]) * 0.2))
        prev_x = xs[-1][1] if xs else fx
        prev_y = ys[-1][1] if ys else fy
        xs += [(seg["out_start"], prev_x), (seg["out_start"] + ease, fx), (seg["out_end"], fx)]
        ys += [(seg["out_start"], prev_y), (seg["out_start"] + ease, fy), (seg["out_end"], fy)]
    if not xs:
        return [(0.0, 0.5)], [(0.0, 0.42)]
    xs.append((total, xs[-1][1]))
    ys.append((total, ys[-1][1]))
    return resample_curve(xs, MAX_CURVE_KEYS), resample_curve(ys, MAX_CURVE_KEYS)


# --------------------------------------------------------------------------- graphs

def build_video_graph(plan: dict, *, subs_path: str | None,
                      font_dir: str | None) -> str:
    """The [vout] half of the filter_complex."""
    src = plan["source_probe"]
    out_w, out_h, fps = plan["output"]["width"], plan["output"]["height"], plan["output"]["fps"]
    segs = plan["segments"]
    look = plan.get("look", {})
    geo = plan.get("geometry", {})

    parts: list[str] = []

    # 1) cut every keep range out of the source timeline
    for i, seg in enumerate(segs):
        parts.append(
            f"[0:v]trim=start={seg['src_start']:.3f}:end={seg['src_end']:.3f},"
            f"setpts=PTS-STARTPTS,fps={fps}[v{i}]"
        )
    concat_in = "".join(f"[v{i}]" for i in range(len(segs)))
    parts.append(f"{concat_in}concat=n={len(segs)}:v=1:a=0[vc]")

    # 2) fit the frame: cover (tight crop) or pad (whole subject on a blurred fill)
    fit = plan.get("output", {}).get("fit", "cover")
    if fit == "pad":
        anchor = clamp(float(plan.get("output", {}).get("anchor", 0.34)), 0.15, 0.75)
        band = clamp(float(plan.get("output", {}).get("band", 0.62)), 0.35, 1.0)
        band_h = int(round(out_h * band / 2.0) * 2)
        # the hero band is cropped to the band's aspect first, so the subject fills it
        # instead of sitting small inside a full-width letterbox
        parts.append(
            f"[vc]split=2[bg_in][fg_in];"
            f"[bg_in]scale={out_w}:{out_h}:force_original_aspect_ratio=increase:flags=bilinear,"
            f"crop={out_w}:{out_h},boxblur=32:2,eq=brightness=-0.08:saturation=0.85[bg];"
            f"[fg_in]crop=w='min(iw\,ih*{out_w}/{band_h})':h='min(ih\,iw*{band_h}/{out_w})'"
            f":x='(iw-ow)/2':y='(ih-oh)/2',scale={out_w}:{band_h}:flags=lanczos[fg];"
            f"[bg][fg]overlay=x=0:y='({out_h}-{band_h})*{anchor:.3f}':format=auto[vfit]"
        )
    else:
        parts.append(
            f"[vc]scale={out_w}:{out_h}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={out_w}:{out_h}[vfit]"
        )

    # 3) reframe: static crop or animated zoompan
    zoom_curve = geo.get("zoom_curve") or [(0.0, 1.0)]
    focus_x = geo.get("focus_x") or [(0.0, 0.5)]
    focus_y = geo.get("focus_y") or [(0.0, 0.42)]
    animated = (geo.get("zoom_mode", "none") != "none"
                or geo.get("pan", False))
    if animated:
        z_expr = piecewise_expr(zoom_curve, var="in_time", decimals=4)
        fx_expr = piecewise_expr(focus_x, var="in_time", decimals=4)
        fy_expr = piecewise_expr(focus_y, var="in_time", decimals=4)
        x_expr = f"max(0,min(iw-iw/({z_expr}),{fx_expr}*iw-(iw/({z_expr}))/2))"
        y_expr = f"max(0,min(ih-ih/({z_expr}),{fy_expr}*ih-(ih/({z_expr}))/2))"
        parts.append(
            f"[vfit]zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}'"
            f":d=1:s={out_w}x{out_h}:fps={fps},setsar=1[vframe]"
        )
    else:
        parts.append("[vfit]setsar=1[vframe]")

    # 4) the look: exposure → flicker → white balance → contrast → denoise → sharpen → vignette
    chain: list[str] = []
    if look.get("denoise_video"):
        chain.append("hqdn3d=2:1.5:3:3")
    brightness = look.get("brightness", 0.0)
    flicker = look.get("flicker_curve") or []
    eq_bits = []
    if brightness:
        eq_bits.append(f"brightness={brightness:.4f}")
    eq_bits.append(f"contrast={look.get('contrast', 1.0):.3f}")
    eq_bits.append(f"saturation={look.get('saturation', 1.0):.3f}")
    eq_bits.append(f"gamma={look.get('gamma', 1.0):.3f}")
    if flicker:
        # a per-sample correction curve measured in analyze.py — smooths exposure drift
        eq_bits.append("eval=frame")
        eq_bits = [b for b in eq_bits if not b.startswith("eval=")]
        chain.append("eq=" + ":".join(eq_bits) + ":eval=frame")
        chain.append(f"eq=brightness='{piecewise_expr(flicker, var='t', decimals=4)}':eval=frame")
    else:
        chain.append("eq=" + ":".join(eq_bits))

    wb = look.get("white_balance") or {}
    if wb and any(abs(v) > 0.004 for v in wb.values()):
        chain.append("colorbalance=" + ":".join(f"{k}={v:.3f}" for k, v in wb.items()
                                                if k in ("rs", "gs", "bs", "rm", "gm", "bm")))
    if look.get("sharpen", 0) > 0:
        chain.append(f"unsharp=5:5:{look['sharpen']:.2f}:5:5:0.0")
    if look.get("vignette"):
        chain.append("vignette=PI/5")

    prev = "vframe"
    for i, filt in enumerate(chain):
        label = f"vlook{i}"
        parts.append(f"[{prev}]{filt}[{label}]")
        prev = label
    parts.append(f"[{prev}]format=yuv420p[vpre]")

    # 5) subtitles last, at delivery resolution, so text is never resampled
    if subs_path:
        fonts = f":fontsdir={font_dir}" if font_dir else ""
        parts.append(f"[vpre]ass='{_esc(subs_path)}'{fonts}[vout]")
    else:
        parts.append("[vpre]null[vout]")
    return ";\n".join(parts)


def build_audio_graph(plan: dict) -> str:
    """The [aout] half of the filter_complex."""
    segs = plan["segments"]
    audio = plan.get("audio", {})
    parts: list[str] = []
    for i, seg in enumerate(segs):
        parts.append(
            f"[0:a]atrim=start={seg['src_start']:.3f}:end={seg['src_end']:.3f},"
            f"asetpts=PTS-STARTPTS[a{i}]"
        )
    concat_in = "".join(f"[a{i}]" for i in range(len(segs)))
    parts.append(f"{concat_in}concat=n={len(segs)}:v=0:a=1[ac]")
    parts.append("[ac]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[abase]")

    chain: list[str] = []
    if audio.get("highpass"):
        chain.append("highpass=f=75")
    if audio.get("denoise"):
        nr = float(audio.get("nr", 12))
        nf = audio.get("nf")
        chain.append(f"afftdn=nr={nr:.0f}" + (f":nf={nf:.0f}" if nf is not None else ""))
    if audio.get("voice_eq"):
        chain.append("equalizer=f=250:t=q:w=1.0:g=-1.5")     # tame mud
        chain.append("equalizer=f=3200:t=q:w=1.2:g=1.5")    # presence
    if audio.get("deess"):
        chain.append("equalizer=f=6800:t=q:w=2.0:g=-2.5")
    ln = audio.get("loudnorm") or {}
    if ln.get("measured_i") is not None:
        chain.append(
            f"loudnorm=I={ln['target']}:TP={ln.get('tp', -1.5)}:LRA={ln.get('lra', 11)}"
            f":measured_I={ln['measured_i']}:measured_TP={ln.get('measured_tp', -1.5)}"
            f":measured_LRA={ln.get('measured_lra', 11)}"
            f":measured_thresh={ln.get('measured_thresh', -30)}"
            f":offset={ln.get('offset', 0)}:linear=true:print_format=summary"
        )
    elif ln.get("target") is not None:
        chain.append(f"loudnorm=I={ln['target']}:TP={ln.get('tp', -1.5)}:LRA={ln.get('lra', 11)}")

    prev = "abase"
    for i, filt in enumerate(chain):
        label = f"alook{i}"
        parts.append(f"[{prev}]{filt}[{label}]")
        prev = label
    parts.append(f"[{prev}]aformat=sample_fmts=fltp:sample_rates=48000[aout]")
    return ";\n".join(parts)


def build(plan: dict, *, subs_path: str | None = None,
          font_dir: str | None = None) -> tuple[str, dict]:
    """Video graph always; audio graph only when the source actually has audio."""
    graph = build_video_graph(plan, subs_path=subs_path, font_dir=font_dir)
    maps: dict = {"video": "[vout]", "audio": None}
    if plan.get("source_probe", {}).get("has_audio"):
        graph += ";\n" + build_audio_graph(plan)
        maps["audio"] = "[aout]"
    return graph, maps


def _esc(path: str) -> str:
    p = str(Path(path).resolve())
    return p.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace(",", "\\,")
