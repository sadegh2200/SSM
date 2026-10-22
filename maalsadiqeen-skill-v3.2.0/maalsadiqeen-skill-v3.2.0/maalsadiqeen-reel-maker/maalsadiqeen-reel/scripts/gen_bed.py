#!/usr/bin/env python3
"""Deterministic ambient music bed (no external samples) — D-minor pad, sub drone, soft bells, paper-room air, synthetic reverb.
Writes a 48 kHz stereo WAV.

    gen_bed.py OUT.wav --duration 45 [--cuts 3.4,13.2,21.6,29.6,38.6] [--hero 24.6] [--final 42.7] [--seed 7]

Chords change on the scene cuts (crossfade 2.2 s); the brightest chord lands on --hero; the resolve chord on the last cut;
bells land on 0.25 s, --hero and --final. Fully reproducible for a given spec.
"""
import sys, math, argparse, subprocess
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("--duration", type=float, default=45.0)
ap.add_argument("--cuts", default="")
ap.add_argument("--hero", type=float, default=None)
ap.add_argument("--final", type=float, default=None)
ap.add_argument("--seed", type=int, default=7)
A = ap.parse_args()

SR = 48000
DUR = A.duration
OUT = A.out
rng = np.random.default_rng(A.seed)
N = int(SR * DUR)
t = np.arange(N) / SR

def note(name):
    names = {"C":0,"C#":1,"D":2,"D#":3,"E":4,"F":5,"F#":6,"G":7,"G#":8,"A":9,"A#":10,"B":11}
    n, o = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((names[n] - 9) / 12 + (o - 4))

# chord palette (D minor): cycled over the scene cuts; the hero moment gets Dm(add9), the last cut resolves to Dm
PALETTE = [["D3", "A3", "D4", "F4"], ["D3", "A3", "D4", "F4", "A4"], ["A#2", "F3", "A#3", "D4", "F4"],
           ["G2", "D3", "G3", "A#3", "D4"], ["A#2", "F3", "A#3", "D4", "F4"], ["F3", "A3", "C4", "F4"]]
cuts = [float(x) for x in A.cuts.split(",") if x.strip()]
chords = {0.0: PALETTE[0]}
for i, tm in enumerate(cuts):
    chords[round(tm, 3)] = PALETTE[(i + 1) % len(PALETTE)]
if cuts:
    chords[round(cuts[-1], 3)] = ["D3", "A3", "D4", "F4", "A4"]      # last scene resolves to Dm
if A.hero is not None:
    chords[round(A.hero, 3)] = ["D3", "A3", "D4", "F4", "E5"]        # the answer: Dm(add9), brighter
CHORDS = sorted(chords.items())
XF = 2.2  # crossfade seconds between chords

def voice(freq, seed):
    """Soft pad voice: detuned pair of gently harmonic tones with slow amplitude drift."""
    r = np.random.default_rng(seed)
    det = 1 + r.uniform(-0.0012, 0.0012)
    ph = r.uniform(0, 2 * math.pi, 4)
    f1, f2 = freq * det, freq / det
    sig = (np.sin(2 * math.pi * f1 * t + ph[0]) + np.sin(2 * math.pi * f2 * t + ph[1])) * 0.5
    sig += 0.22 * np.sin(2 * math.pi * 2 * freq * t + ph[2])
    sig += 0.07 * np.sin(2 * math.pi * 3 * freq * t + ph[3])
    # slow drift (period 6-13 s) so the pad breathes
    p = r.uniform(6, 13); p2 = r.uniform(9, 17)
    drift = 0.72 + 0.18 * np.sin(2 * math.pi * t / p + r.uniform(0, 6)) + 0.10 * np.sin(2 * math.pi * t / p2 + r.uniform(0, 6))
    return sig * drift

def chord_env(start, end):
    """Envelope that fades in over XF at start and out over XF at end (end may be None)."""
    env = np.zeros(N)
    a = start - XF / 2 if start > 0 else 0.0
    b = start + XF / 2 if start > 0 else 0.0
    if end is None:
        c, d = DUR + 1, DUR + 2
    else:
        c, d = end - XF / 2, end + XF / 2
    # attack
    env += np.clip((t - a) / max(b - a, 1e-6), 0, 1)
    # release
    env *= 1 - np.clip((t - c) / max(d - c, 1e-6), 0, 1)
    # smooth (raised cosine)
    env = 0.5 - 0.5 * np.cos(np.pi * np.clip(env, 0, 1))
    return env

pad = np.zeros(N)
for i, (start, notes) in enumerate(CHORDS):
    end = CHORDS[i + 1][0] if i + 1 < len(CHORDS) else None
    env = chord_env(start, end)
    for j, nm in enumerate(notes):
        f = note(nm)
        w = 1.0 / (1 + 0.35 * j)  # upper voices quieter
        if f > 500: w *= 0.45
        pad += w * voice(f, seed=100 * i + j) * env

# sub drone D2, very soft, slow swell
sub = np.sin(2 * math.pi * note("D2") * t) * (0.5 + 0.5 * np.sin(2 * math.pi * t / 11.0))
pad += 0.35 * sub

# soft bells on cues: (time, note, gain)
BELLS = [(0.25, "D5", 0.5)]
if A.hero is not None:
    BELLS += [(A.hero, "D5", 0.75), (A.hero + 0.1, "A5", 0.45)]
if A.final is not None:
    BELLS += [(A.final, "D5", 0.6), (A.final + 0.35, "A5", 0.45), (A.final + 0.7, "D6", 0.35)]
bell = np.zeros(N)
for (bt, nm, g) in BELLS:
    i0 = int(bt * SR); L = int(3.2 * SR)
    if i0 >= N: continue
    L = min(L, N - i0)
    tt = np.arange(L) / SR
    f = note(nm)
    env = np.exp(-tt * 1.6) * (1 - np.exp(-tt * 400))
    s = np.sin(2 * math.pi * f * tt) + 0.35 * np.sin(2 * math.pi * f * 2.0 * tt) * np.exp(-tt * 3.0) \
        + 0.12 * np.sin(2 * math.pi * f * 2.99 * tt) * np.exp(-tt * 5.0)
    bell[i0:i0 + L] += g * 0.3 * s * env

# air: very quiet filtered noise bed (paper/room tone), fixed seed
noise = rng.standard_normal(N) * 0.012
dry = pad * 0.16 + bell + noise

# --- FFT filtering (whole signal): gentle lowpass on the pad, highpass at 60 Hz
def fft_filter(x, lo=60.0, hi=2600.0):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    hp = 1 / (1 + (lo / np.maximum(f, 1e-3)) ** 4)
    lp = 1 / (1 + (f / hi) ** 3)
    return np.fft.irfft(X * hp * lp, n=len(x))

dry = fft_filter(dry)

# --- reverb: synthetic IR (2.8 s decaying noise, lowpassed), overlap-add convolution
ir_len = int(2.8 * SR)
ir_t = np.arange(ir_len) / SR
ir = np.random.default_rng(11).standard_normal(ir_len) * np.exp(-ir_t * 2.2)
ir = fft_filter(ir, lo=80, hi=3500)
ir /= np.sqrt(np.sum(ir ** 2))
ir *= 0.9

def ola_convolve(x, h, block=1 << 17):
    nfft = 1
    while nfft < block + len(h) - 1: nfft <<= 1
    H = np.fft.rfft(h, nfft)
    y = np.zeros(len(x) + len(h) - 1)
    for s in range(0, len(x), block):
        seg = x[s:s + block]
        Y = np.fft.irfft(np.fft.rfft(seg, nfft) * H, nfft)
        y[s:s + nfft] += Y[: min(nfft, len(y) - s)]
    return y[: len(x)]

wet = ola_convolve(dry, ir)
mix = 0.55 * dry + 0.45 * wet

# stereo: slight decorrelation via small delays/panning of the wet part
wetL = np.roll(wet, 0); wetR = np.roll(wet, int(0.011 * SR)); wetR[: int(0.011 * SR)] = 0
L = 0.55 * dry + 0.45 * wetL
R = 0.55 * dry + 0.45 * wetR

# global fade in/out
fade_in = np.clip(t / 1.8, 0, 1); fade_out = np.clip((DUR - t) / 2.5, 0, 1)
g = (0.5 - 0.5 * np.cos(np.pi * fade_in)) * (0.5 - 0.5 * np.cos(np.pi * fade_out))
L *= g; R *= g

peak = max(np.max(np.abs(L)), np.max(np.abs(R)), 1e-9)
L = L / peak * 0.5; R = R / peak * 0.5  # -6 dBFS peak; mixed down later
st = np.stack([L, R], axis=1).astype(np.float32)
raw = OUT + ".f32"
st.tofile(raw)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", raw, "-c:a", "pcm_s16le", OUT], check=True)
import os; os.remove(raw)
print("wrote", OUT, f"{DUR}s")
