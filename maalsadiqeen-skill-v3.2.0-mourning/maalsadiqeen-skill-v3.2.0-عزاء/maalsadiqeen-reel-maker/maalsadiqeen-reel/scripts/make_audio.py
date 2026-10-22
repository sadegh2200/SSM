#!/usr/bin/env python3
"""
make_audio.py — synthesize the royalty-free sound layer (no downloads, no copyright risk).

    python3 make_audio.py --out ~/reel-studio/public/audio [--plan plan.json] [--seconds 62]
                          [--maqam bayati|hijaz|nahawand|rast] [--root 146.83] [--force]

Writes (44.1 kHz, 16-bit):
  pad.wav        slow maqam drone bed (−20 dB RMS, fades in/out; length = plan total + 2 s)
  tick.wav       soft wooden tick (text reveals)
  stamp.wav      low felt stamp (ثقة chips / warning line)
  boom.wav       cinematic sub hit (hook, seal)
  whoosh.wav, page-turn.wav, ding.wav   only if missing (synth fallbacks for the bundled ones)
The bed is instrumental, melodic-but-static (a drone, not music with rhythm) — appropriate for
religious content pages whose audience avoids rhythmic music. Replace pad.wav with a licensed
nasheed/ambient track if the page prefers; keep it ≈ −20 dB RMS so SFX and the final loudness stay balanced.
"""
from __future__ import annotations

import argparse
import json
import math
import wave
from pathlib import Path

import numpy as np

SR = 44100

# scale degrees in cents relative to the root (quarter-tones for Bayati/Rast)
MAQAMS = {
    "bayati": [0, 150, 300, 500, 700, 800, 1000, 1200],
    "hijaz": [0, 100, 400, 500, 700, 800, 1000, 1200],
    "nahawand": [0, 200, 300, 500, 700, 800, 1000, 1200],
    "rast": [0, 200, 350, 500, 700, 900, 1050, 1200],
}


def write_wav(path: Path, data: np.ndarray):
    """data: float array (n,) or (n, 2) in [-1, 1]."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if data.ndim == 1:
        data = data[:, None]
    pcm = (np.clip(data, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(data.shape[1])
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def lowpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    """One-pole low-pass (per channel)."""
    a = math.exp(-2 * math.pi * cutoff / SR)
    y = np.empty_like(x)
    if x.ndim == 1:
        acc = 0.0
        for i in range(len(x)):  # pragma: no cover (slow path for short SFX only)
            acc = a * acc + (1 - a) * x[i]
            y[i] = acc
        return y
    return np.stack([lowpass(x[:, c], cutoff) for c in range(x.shape[1])], axis=1)


def fast_lowpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    """FFT brick-wall-ish low-pass with a soft knee (fast for long signals)."""
    n = len(x)
    X = np.fft.rfft(x, axis=0)
    freqs = np.fft.rfftfreq(n, 1 / SR)
    gain = 1 / (1 + (freqs / cutoff) ** 4)
    return np.fft.irfft(X * gain[:, None] if x.ndim == 2 else X * gain, n=n, axis=0)


def env(n: int, a: float, d: float, s: float = 0.0, r: float = 0.0) -> np.ndarray:
    t = np.arange(n) / SR
    e = np.ones(n) * s
    a_n, d_n, r_n = int(a * SR), int(d * SR), int(r * SR)
    if a_n:
        e[:a_n] = np.linspace(0, 1, a_n)
    if d_n:
        e[a_n:a_n + d_n] = np.linspace(1, s, d_n)[: max(0, n - a_n)]
    if r_n and r_n < n:
        e[-r_n:] *= np.linspace(1, 0, r_n)
    return e * (t >= 0)


def rms_norm(x: np.ndarray, db: float) -> np.ndarray:
    cur = np.sqrt(np.mean(x ** 2)) + 1e-9
    return x * (10 ** (db / 20) / cur)


def peak_norm(x: np.ndarray, peak: float = 0.9) -> np.ndarray:
    return x / (np.max(np.abs(x)) + 1e-9) * peak


# ----------------------------------------------------------------------------- generators

def pad(seconds: float, maqam: str, root: float, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    cents = MAQAMS[maqam]
    # drone: root + fifth + octave, plus a slowly wandering upper voice on scale degrees
    voices = [(0, 0.5), (700, 0.22), (1200, 0.16), (-1200, 0.35)]
    out = np.zeros((n, 2))
    for c, amp in voices:
        f = root * 2 ** (c / 1200)
        for k, pa in enumerate([1.0, 0.35, 0.18, 0.08]):  # soft partials
            fk = f * (k + 1)
            det = 1 + rng.normal(0, 0.0008)
            vib = 1 + 0.002 * np.sin(2 * np.pi * (0.11 + 0.05 * k) * t + rng.uniform(0, 6))
            ph = rng.uniform(0, 2 * np.pi)
            sig = np.sin(2 * np.pi * fk * det * vib * t + ph) * amp * pa
            panL, panR = (0.5 + 0.3 * math.cos(k + c / 500)), (0.5 + 0.3 * math.sin(k + c / 500))
            out[:, 0] += sig * panL
            out[:, 1] += sig * panR
    # wandering melodic voice: holds each degree 4–7 s, cross-faded (static, non-rhythmic)
    pos, mel = 0, np.zeros((n, 2))
    degree = 2
    while pos < n:
        hold = int(rng.uniform(4, 7) * SR)
        seg = slice(pos, min(n, pos + hold))
        m = len(range(*seg.indices(n)))
        f = root * 2 * 2 ** (cents[degree % len(cents)] / 1200)
        e = np.ones(m)
        fade = min(int(1.2 * SR), m // 2)
        if fade:
            e[:fade] = np.linspace(0, 1, fade)
            e[-fade:] *= np.linspace(1, 0, fade)
        tt = np.arange(m) / SR
        s = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt)) * e * 0.12
        mel[seg, 0] += s * 0.6
        mel[seg, 1] += s * 0.8
        degree += rng.choice([-1, 1, 1, 2])
        pos += hold
    out += mel
    # breath: filtered noise swell
    noise = rng.normal(0, 1, (n, 2))
    noise = fast_lowpass(noise, 900) * (0.012 + 0.008 * np.sin(2 * np.pi * 0.05 * t))[:, None]
    out += noise
    out = fast_lowpass(out, 2600)
    # slow amplitude breathing + fades
    out *= (0.92 + 0.08 * np.sin(2 * np.pi * 0.07 * t))[:, None]
    fi, fo = int(1.5 * SR), int(2.5 * SR)
    out[:fi] *= np.linspace(0, 1, fi)[:, None]
    out[-fo:] *= np.linspace(1, 0, fo)[:, None]
    return rms_norm(out, -20)


def tick() -> np.ndarray:
    n = int(0.08 * SR)
    rng = np.random.default_rng(1)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * 1900 * t) * np.exp(-t * 90) + 0.4 * np.sin(2 * np.pi * 3200 * t) * np.exp(-t * 140)
    click = rng.normal(0, 1, n) * np.exp(-t * 400) * 0.5
    return peak_norm(body + click, 0.6)


def stamp() -> np.ndarray:
    n = int(0.35 * SR)
    rng = np.random.default_rng(2)
    t = np.arange(n) / SR
    thud = np.sin(2 * np.pi * (120 * np.exp(-t * 6)) * t) * np.exp(-t * 14)
    felt = fast_lowpass(rng.normal(0, 1, n), 1500) * np.exp(-t * 60) * 0.7
    return peak_norm(thud + felt, 0.8)


def boom() -> np.ndarray:
    n = int(1.2 * SR)
    rng = np.random.default_rng(3)
    t = np.arange(n) / SR
    f = 55 * np.exp(-t * 2.2) + 32
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.8)
    air = fast_lowpass(rng.normal(0, 1, n), 400) * np.exp(-t * 7) * 0.5
    return peak_norm(sub + air, 0.85)


def whoosh() -> np.ndarray:
    n = int(0.15 * SR)
    rng = np.random.default_rng(4)
    t = np.arange(n) / SR
    noise = rng.normal(0, 1, n)
    swept = fast_lowpass(noise, 3500) * np.sin(np.pi * t / t[-1]) ** 2
    return peak_norm(swept, 0.5)


def page_turn() -> np.ndarray:
    n = int(0.4 * SR)
    rng = np.random.default_rng(5)
    t = np.arange(n) / SR
    noise = fast_lowpass(rng.normal(0, 1, n), 5000)
    e = np.exp(-((t - 0.12) ** 2) / 0.004) + 0.5 * np.exp(-((t - 0.26) ** 2) / 0.006)
    return peak_norm(noise * e, 0.5)


def ding() -> np.ndarray:
    n = int(1.4 * SR)
    t = np.arange(n) / SR
    partials = [(1.0, 1.0), (2.76, 0.5), (5.4, 0.25), (8.9, 0.12)]
    f0 = 1046.5
    s = sum(a * np.sin(2 * np.pi * f0 * r * t) * np.exp(-t * (2 + r * 1.5)) for r, a in partials)
    st = np.stack([s * 0.9, s], axis=1)
    return peak_norm(st, 0.6)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="public/audio directory")
    ap.add_argument("--plan", help="plan.json (pad length = total/fps + 2 s)")
    ap.add_argument("--seconds", type=float, default=62.0)
    ap.add_argument("--maqam", default="bayati", choices=MAQAMS)
    ap.add_argument("--root", type=float, default=146.83, help="root frequency in Hz (D3 = 146.83)")
    ap.add_argument("--force", action="store_true", help="overwrite bundled whoosh/page-turn/ding too")
    a = ap.parse_args()
    out = Path(a.out)
    seconds = a.seconds
    if a.plan:
        p = json.load(open(a.plan, encoding="utf-8"))
        seconds = p["total"] / p["fps"] + 2
    write_wav(out / "pad.wav", pad(seconds, a.maqam, a.root))
    write_wav(out / "tick.wav", tick())
    write_wav(out / "stamp.wav", stamp())
    write_wav(out / "boom.wav", boom())
    for name, gen in (("whoosh", whoosh), ("page-turn", page_turn), ("ding", ding)):
        if a.force or not (out / f"{name}.wav").exists():
            write_wav(out / f"{name}.wav", gen())
    print(f"audio written to {out} (pad {seconds:.1f}s, maqam {a.maqam}, root {a.root} Hz)")


if __name__ == "__main__":
    main()
