#!/usr/bin/env python3
"""The sound stage: one bed, the cues the picture asked for, one loudness target.

The bed is the brand's own deterministic D-minor pad (`gen_bed.py` in the
`maalsadiqeen-reel` skill), so two renders of the same spec sound identical. The cues come
from the picture — every reveal that mattered wrote (time, sfx, gain) while it was being
drawn. Nothing here guesses a mood: if the block did not ask for a sparkle, there is none.

    python3 sound.py cues.json --duration 36.5 --out mix.wav [--recitation quran.wav]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

import brandkit as bk

SR = 48000


# ------------------------------------------------------------------ reading and writing
def _read_wav(path: str | Path) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        n, ch, sw = w.getnframes(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(n)
    if sw != 2:
        raise ValueError("expected 16-bit audio")
    a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
    return a.reshape(-1, ch) if ch > 1 else a.reshape(-1, 1)


def _write_wav(path: str | Path, data: np.ndarray) -> None:
    if data.ndim == 1:
        data = data[:, None]
    pcm = (np.clip(data, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(pcm.shape[1])
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def _decode(path: Path, seconds: float | None = None) -> np.ndarray:
    """Any audio file → float32 stereo array at 48 kHz, via ffmpeg."""
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
           "-f", "s16le", "-acodec", "pcm_s16le", "-ac", "2", "-ar", str(SR), "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float32).reshape(-1, 2) / 32768.0
    if seconds:
        a = a[: int(seconds * SR)]
    return a


def _pad(a: np.ndarray, n: int) -> np.ndarray:
    if a.shape[0] >= n:
        return a[:n]
    return np.vstack([a, np.zeros((n - a.shape[0], a.shape[1]), np.float32)])


# ---------------------------------------------------------------------------------- bed
def bed(duration: float, cuts: list[float], hero: float | None, final: float | None,
        seed: int = 7, workdir: Path | None = None) -> np.ndarray:
    """The brand's pad when the brand skill is installed, otherwise a small local one."""
    root = bk.brand_root()
    script = (root / "scripts" / "gen_bed.py") if root else None
    out = Path(workdir or tempfile.gettempdir()) / "bed.wav"
    if script and script.exists():
        cmd = [sys.executable, str(script), str(out), "--duration", f"{duration:.3f}",
               "--cuts", ",".join(f"{c:.3f}" for c in cuts), "--seed", str(seed)]
        if hero:
            cmd += ["--hero", f"{hero:.3f}"]
        if final:
            cmd += ["--final", f"{final:.3f}"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0 and out.exists():
            a = _read_wav(out)
            return _pad(a, int(duration * SR))
        print(f"  ! gen_bed failed ({r.stderr.strip()[:120]}) — using the local pad", file=sys.stderr)
    return _local_pad(duration)


def _local_pad(duration: float) -> np.ndarray:
    """A quiet D-minor drone: root, fifth, minor third — enough to hold a calm frame."""
    n = int(duration * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2), np.float32)
    for f, amp, det in ((73.42, 0.5, 0.0), (110.0, 0.28, 0.15), (174.61, 0.16, -0.2)):
        for ch, d in ((0, -det), (1, det)):
            ph = 2 * np.pi * (f + d) * t
            out[:, ch] += amp * (np.sin(ph) + 0.22 * np.sin(2 * ph))
    lfo = 0.85 + 0.15 * np.sin(2 * np.pi * 0.07 * t)
    out *= lfo[:, None] * 0.12
    fade = np.minimum(1.0, t / 2.0) * np.minimum(1.0, (duration - t) / 2.5).clip(0, 1)
    return out * fade[:, None]


# ------------------------------------------------------------------------------- mixing
def cue_track(cues: list[dict], duration: float) -> np.ndarray:
    n = int(duration * SR)
    track = np.zeros((n, 2), np.float32)
    cache: dict[str, np.ndarray] = {}
    for c in cues:
        name = c.get("sfx")
        path = bk.asset(f"{name}.mp3") or bk.asset(f"{name}.wav")
        if not path:
            continue
        if name not in cache:
            cache[name] = _decode(Path(path))
        snd = cache[name]
        g = 10 ** (float(c.get("gain_db", -20)) / 20.0)
        i = int(float(c["t"]) * SR)
        if i >= n or i < 0:
            continue
        j = min(n, i + snd.shape[0])
        track[i:j] += snd[: j - i] * g
    return track


def _duck(bed_track: np.ndarray, voice: np.ndarray, depth_db: float = -9.0) -> np.ndarray:
    """Side-chain the bed under the voice: 20 ms attack, 320 ms release, smoothed."""
    env = np.abs(voice).mean(axis=1)
    win = int(0.05 * SR)
    if win > 1:
        k = np.ones(win, np.float32) / win
        env = np.convolve(env, k, mode="same")
    env = np.clip(env / (env.max() + 1e-9), 0, 1)
    gain = 10 ** ((depth_db * env) / 20.0)
    # one-pole smoothing so the bed breathes instead of pumping
    a = 0.0015
    out = np.empty_like(gain)
    acc = 1.0
    for i, g in enumerate(gain):
        acc += a * (g - acc)
        out[i] = acc
    return bed_track * out[:, None]


def build(cues: list[dict], duration: float, out: str, bed_gain_db: float = -7.0,
          recitation: str | None = None, lufs: float = -15.5, tp: float = -1.5,
          target_peak: bool = True, workdir: Path | None = None) -> str:
    cuts = sorted({round(float(c["t"]), 3) for c in cues if c.get("sfx") == "whoosh-short"})
    heroes = [float(c["t"]) for c in cues if c.get("sfx") == "impact-bass-1"]
    finals = [float(c["t"]) for c in cues if c.get("sfx") in ("impact-bass-2", "chime")]
    base = bed(duration, cuts, heroes[0] if heroes else None,
               finals[-1] if finals else None, workdir=workdir)
    base = base * (10 ** (bed_gain_db / 20.0))

    voice = None
    if recitation and Path(recitation).exists():
        voice = _pad(_decode(Path(recitation)), int(duration * SR))
        base = _duck(_pad(base, voice.shape[0]), voice)

    mix = _pad(base, int(duration * SR))
    if voice is not None:
        mix = mix + voice * 0.9
    mix = mix + cue_track(cues, duration)

    peak = float(np.abs(mix).max())
    if peak > 0.98:
        mix *= 0.98 / peak
    tmp = Path(workdir or tempfile.gettempdir()) / "mix-raw.wav"
    _write_wav(tmp, mix)

    filters = [f"loudnorm=I={lufs}:TP={tp}:LRA=11:linear=false"]
    if target_peak:
        filters.append("alimiter=limit=0.94:level=false")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(tmp),
           "-af", ",".join(filters), "-ar", str(SR), "-ac", "2", out]
    subprocess.run(cmd, check=True)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="cue list → a mastered mix")
    ap.add_argument("cues")
    ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--out", default="mix.wav")
    ap.add_argument("--bed-db", type=float, default=-7.0)
    ap.add_argument("--lufs", type=float, default=-15.5)
    ap.add_argument("--recitation")
    a = ap.parse_args()
    cues = json.loads(Path(a.cues).read_text(encoding="utf-8"))
    build(cues, a.duration, a.out, a.bed_db, a.recitation, a.lufs)
    print(a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
