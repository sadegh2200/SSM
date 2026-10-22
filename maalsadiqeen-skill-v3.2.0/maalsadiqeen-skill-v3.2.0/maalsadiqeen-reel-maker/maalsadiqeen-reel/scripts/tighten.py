#!/usr/bin/env python3
"""Tighten long pauses in a speech clip (deterministic).
usage: tighten.py in.wav out.wav [--max-pause 0.26] [--thresh-db -36] [--tempo 1.0]
"""
import argparse, subprocess, sys, struct
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("inp"); ap.add_argument("out")
ap.add_argument("--max-pause", type=float, default=0.26)
ap.add_argument("--thresh-db", type=float, default=-36.0)
ap.add_argument("--tempo", type=float, default=1.0)
ap.add_argument("--sr", type=int, default=44100)
a = ap.parse_args()

sr = a.sr
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", a.inp, "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"],
                     capture_output=True, check=True).stdout
x = np.frombuffer(raw, dtype=np.float32).copy()
win = int(sr * 0.01)  # 10 ms
n = len(x) // win
rms = np.sqrt(np.mean(x[: n * win].reshape(n, win) ** 2, axis=1) + 1e-12)
db = 20 * np.log10(rms + 1e-9)
quiet = db < a.thresh_db

# find quiet runs
segments = []  # (start_win, end_win)
i = 0
while i < n:
    if quiet[i]:
        j = i
        while j < n and quiet[j]:
            j += 1
        segments.append((i, j))
        i = j
    else:
        i += 1

max_w = int(round(a.max_pause / 0.01))
keep_mask = np.ones(n, dtype=bool)
removed = 0.0
for s, e in segments:
    L = e - s
    if s == 0 or e == n:
        # leading/trailing: keep at most 60 ms lead / 150 ms tail
        lim = 6 if s == 0 else 15
        if L > lim:
            if s == 0:
                keep_mask[s : e - lim] = False
            else:
                keep_mask[s + lim : e] = False
            removed += (L - lim) * 0.01
    elif L > max_w:
        half = max_w // 2
        keep_mask[s + half : e - (max_w - half)] = False
        removed += (L - max_w) * 0.01

# assemble with 5 ms crossfades at cut points
out = []
fade = int(sr * 0.005)
i = 0
chunks = []
while i < n:
    if keep_mask[i]:
        j = i
        while j < n and keep_mask[j]:
            j += 1
        chunks.append(x[i * win : j * win])
        i = j
    else:
        i += 1
tail = x[n * win :]
if len(tail) and keep_mask[-1]:
    chunks[-1] = np.concatenate([chunks[-1], tail])

y = chunks[0]
for c in chunks[1:]:
    if len(y) > fade and len(c) > fade:
        ramp = np.linspace(0, 1, fade, dtype=np.float32)
        y[-fade:] = y[-fade:] * (1 - ramp) + c[:fade] * ramp
        y = np.concatenate([y, c[fade:]])
    else:
        y = np.concatenate([y, c])

tmp = a.out + ".raw.f32"
with open(tmp, "wb") as f:
    f.write(y.astype(np.float32).tobytes())
af = f"atempo={a.tempo}" if abs(a.tempo - 1.0) > 1e-3 else "anull"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", tmp,
                "-af", af, "-c:a", "pcm_s16le", a.out], check=True)
import os; os.remove(tmp)
dur = len(y) / sr / a.tempo
print(f"{a.inp}: removed {removed:.2f}s of pauses -> {dur:.2f}s (tempo {a.tempo})")
