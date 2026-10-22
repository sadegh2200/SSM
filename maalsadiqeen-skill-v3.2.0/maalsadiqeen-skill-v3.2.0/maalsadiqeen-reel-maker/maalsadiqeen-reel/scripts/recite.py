#!/usr/bin/env python3
"""
recite.py — fetch a Quran recitation for an ayah (or a short range) and trim it for the reel.

    python3 recite.py 9:119 [--edition ar.mahermuaiqly] [--out assets/audio/recite.wav] [--print-url]

Source: https://cdn.islamic.network/quran/audio/128/<edition>/<global_ayah>.mp3  (AlQuran Cloud CDN, no key)
Editions that work well: ar.mahermuaiqly (default, warm & measured), ar.alafasy (brighter). Avoid ar.husary
(too slow for a 60 s reel), ar.abdulsamad / ar.parhizgar (CDN returns stubs).
Output: 48 kHz mono WAV, leading/trailing silence trimmed (-40 dB), 60 ms fade in/out. Prints the duration —
copy it into the spec as the verse scene length budget (scene must be >= duration + 1.6 s).
"""
import argparse, os, subprocess, sys, urllib.request, urllib.error, tempfile

AYAHS = [7, 286, 200, 176, 120, 165, 206, 75, 129, 109, 123, 111, 43, 52, 99, 128, 111, 110, 98, 135, 112, 78, 118, 64, 77,
         227, 93, 88, 69, 60, 34, 30, 73, 54, 45, 83, 182, 88, 75, 85, 54, 53, 89, 59, 37, 35, 38, 29, 18, 45, 60, 49, 62,
         55, 78, 96, 29, 22, 24, 13, 14, 11, 11, 18, 12, 12, 30, 52, 52, 44, 28, 28, 20, 56, 40, 31, 50, 40, 46, 42, 29,
         19, 36, 25, 22, 17, 19, 26, 30, 20, 15, 21, 11, 8, 8, 19, 5, 8, 8, 11, 11, 8, 3, 9, 5, 4, 7, 3, 6, 3, 5, 4, 5, 6]
assert len(AYAHS) == 114 and sum(AYAHS) == 6236


def global_no(surah, ayah):
    if not (1 <= surah <= 114 and 1 <= ayah <= AYAHS[surah - 1]):
        raise SystemExit(f"invalid reference {surah}:{ayah}")
    return sum(AYAHS[:surah - 1]) + ayah


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref", help="surah:ayah or surah:ayah-ayah (max 5 ayat)")
    ap.add_argument("--edition", default="ar.mahermuaiqly")
    ap.add_argument("--out", default="recite.wav")
    ap.add_argument("--print-url", action="store_true")
    ap.add_argument("--from-files", nargs="*", help="already-downloaded mp3(s) for the ayat (offline / sandbox without CDN access)")
    a = ap.parse_args()
    s, rest = a.ref.split(":")
    s = int(s)
    if "-" in rest:
        a1, a2 = map(int, rest.split("-"))
    else:
        a1 = a2 = int(rest)
    if a2 - a1 > 4:
        raise SystemExit("keep recitation to <= 5 ayat for a reel")
    urls = [f"https://cdn.islamic.network/quran/audio/128/{a.edition}/{global_no(s, n)}.mp3" for n in range(a1, a2 + 1)]
    if a.print_url:
        print("\n".join(urls)); return
    tmp = tempfile.mkdtemp(prefix="recite-")
    parts = []
    for i, u in enumerate(urls):
        p = os.path.join(tmp, f"p{i}.mp3")
        if a.from_files:
            if i >= len(a.from_files):
                raise SystemExit(f"--from-files needs {len(urls)} file(s) for {a.ref}")
            p = a.from_files[i]
        else:
            try:
                urllib.request.urlretrieve(u, p)
            except (urllib.error.URLError, OSError) as e:
                raise SystemExit(f"could not download {u}\n  ({e})\n  → no network to cdn.islamic.network: download the mp3(s) elsewhere "
                                 f"and re-run with --from-files, or set audio.recitation.file to a local WAV in the spec")
        d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p], capture_output=True, text=True).stdout.strip() or 0)
        if d < 1.0:
            raise SystemExit(f"{u} looks like a stub ({os.path.getsize(p)} bytes, {d:.2f}s) — try --edition ar.alafasy")
        parts.append(p)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    trim = "silenceremove=start_periods=1:start_threshold=-40dB:start_silence=0.05,areverse,silenceremove=start_periods=1:start_threshold=-40dB:start_silence=0.05,areverse"
    if len(parts) == 1:
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", parts[0], "-af", f"{trim},afade=t=in:d=0.06,aformat=sample_rates=48000:channel_layouts=mono", a.out]
    else:
        lst = os.path.join(tmp, "list.txt")
        with open(lst, "w") as f:
            for p in parts: f.write(f"file '{p}'\n")
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-af", f"{trim},afade=t=in:d=0.06,aformat=sample_rates=48000:channel_layouts=mono", a.out]
    subprocess.run(cmd, check=True)
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.out], capture_output=True, text=True).stdout.strip())
    # soft fade-out on the trimmed tail
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", a.out, "-af", f"afade=t=out:st={max(0, d-0.08):.3f}:d=0.08", a.out + ".tmp.wav"], check=True)
    os.replace(a.out + ".tmp.wav", a.out)
    print(f"{a.ref} ({a.edition}) -> {a.out}  duration {d:.2f}s")


if __name__ == "__main__":
    main()
