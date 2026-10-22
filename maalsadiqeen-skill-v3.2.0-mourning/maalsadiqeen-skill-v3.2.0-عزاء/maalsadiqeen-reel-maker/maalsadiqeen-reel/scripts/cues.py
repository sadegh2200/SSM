#!/usr/bin/env python3
"""
cues.py — derive word/line onset cues from an audio clip (recitation or a voice stem).

    python3 cues.py recite.wav --words 8 [--offset 3.9] [--json]
    python3 cues.py vo.wav --lines 3 --offset 21.6            # one onset per spoken line (long pauses split lines)

Method: 10 ms RMS envelope → onsets where energy rises > 6 dB above the running floor after a dip.
With --words N the N most prominent onsets are kept (pauses between words are weighted), else all onsets are printed.
Times are absolute when --offset (the clip's start in the reel) is given — paste them into the spec's "cues".
Always sanity-check against the audio: the result is a strong first draft, not ground truth.
"""
import argparse, json, subprocess, sys
import numpy as np


def envelope(path, sr=16000, hop=0.01):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    n = int(sr * hop)
    m = len(x) // n
    frames = x[:m * n].reshape(m, n)
    rms = np.sqrt((frames ** 2).mean(axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-9)
    return db, hop


def onsets(db, hop, min_gap=0.18, rise_db=6.0, floor_db=-45.0):
    """candidate onsets: local energy rises after dips. Returns [(time, prominence)]."""
    # smooth a little
    k = 3
    sm = np.convolve(db, np.ones(k) / k, mode="same")
    out = []
    last = -1e9
    dip = sm[0]
    for i in range(1, len(sm)):
        dip = min(dip, sm[i - 1]) if sm[i - 1] < sm[i] or i == 1 else dip
        if sm[i] > floor_db and sm[i] - dip >= rise_db and (sm[i] - sm[i - 1]) > 0.5:
            t = i * hop
            if t - last >= min_gap:
                # prominence = depth of the preceding dip + length of silence before it
                j = i
                while j > 0 and sm[j - 1] <= sm[j]:
                    j -= 1
                depth = sm[i] - sm[j]
                out.append((round(t, 3), float(depth)))
                last = t
                dip = sm[i]
        if sm[i] < dip:
            dip = sm[i]
    return out


def pick_words(cands, n, dur):
    """choose n onsets (first fixed at 0) maximising prominence while keeping gaps close to the mean word spacing."""
    exp = dur / n
    lam = 6.0
    T = [c[0] for c in cands]; P = [min(c[1], 20.0) for c in cands]
    m = len(T)
    NEG = -1e18
    best = [[NEG] * m for _ in range(n)]
    back = [[-1] * m for _ in range(n)]
    best[0][0] = P[0]
    for k in range(1, n):
        for j in range(1, m):
            for i in range(j):
                if best[k - 1][i] == NEG:
                    continue
                gap = T[j] - T[i]
                if gap < 0.25:
                    continue
                sc = best[k - 1][i] + P[j] - lam * ((gap - exp) / exp) ** 2
                if sc > best[k][j]:
                    best[k][j] = sc; back[k][j] = i
    j = max(range(m), key=lambda j: best[n - 1][j])
    out = []
    for k in range(n - 1, -1, -1):
        out.append(T[j]); j = back[k][j]
    return sorted(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--words", type=int, help="number of words expected → keep the N most prominent onsets")
    ap.add_argument("--lines", type=int, help="number of lines → split on the N-1 longest pauses")
    ap.add_argument("--offset", type=float, default=0.0, help="clip start inside the reel (s)")
    ap.add_argument("--min-gap", type=float, default=0.18)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    db, hop = envelope(a.audio)
    cands = onsets(db, hop, min_gap=a.min_gap)
    if not cands:
        raise SystemExit("no onsets found — is the clip silent?")
    if cands[0][0] > 0.12:
        cands.insert(0, (0.0, 99.0))  # speech usually starts at the trimmed clip start
    else:
        cands[0] = (0.0, 99.0)
    times = None
    if a.words:
        n = a.words
        dur = len(db) * hop
        cands = [c for c in cands if c[0] <= dur - 0.45] or cands
        if len(cands) >= n:
            times = pick_words(cands, n, dur)
        else:
            times = list(np.round(np.linspace(0, dur * (1 - 1.0 / n), n), 2))
    elif a.lines:
        # split on the longest pauses: measure silence length before each onset
        pauses = []
        for i, (t, _) in enumerate(cands[1:], 1):
            prev = cands[i - 1][0]
            seg = db[int(prev / hop): int(t / hop)]
            sil = (seg < -40).sum() * hop if len(seg) else 0
            pauses.append((sil, t))
        top = sorted(sorted(pauses, key=lambda p: -p[0])[: a.lines - 1], key=lambda p: p[1])
        times = [0.0] + [t for _, t in top]
    else:
        times = [c[0] for c in cands]
    times = [round(t + a.offset, 2) for t in times]
    if a.json:
        print(json.dumps(times))
    else:
        for i, t in enumerate(times):
            print(f"{i+1:3d}  {t:7.2f}")


if __name__ == "__main__":
    main()
