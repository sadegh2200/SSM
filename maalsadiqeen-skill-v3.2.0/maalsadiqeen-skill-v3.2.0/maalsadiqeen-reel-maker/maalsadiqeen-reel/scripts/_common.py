"""Shared helpers for the maalsadiqeen-reel scripts (Arabic text metrics, IO)."""
from __future__ import annotations

import json
import re
import subprocess
import shutil
import sys
from pathlib import Path

TASHKEEL = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED\u0640]")
ARABIC = re.compile(r"[\u0600-\u06FF]")
LATIN = re.compile(r"[A-Za-z]")
EMOJI = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")


def strip_tashkeel(s: str) -> str:
    return TASHKEEL.sub("", s)


def letters(s: str) -> int:
    """Number of base characters (tashkeel removed, spaces kept) - a proxy for rendered width."""
    return len(strip_tashkeel(s))


def words(s: str) -> int:
    return len([w for w in strip_tashkeel(s).split() if w])


def has_arabic(s: str) -> bool:
    return bool(ARABIC.search(s))


def to_arabic_digits(s: str) -> str:
    return s.translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))


def load_json(path: str | Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(obj, path: str | Path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def die(msg: str, code: int = 1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent

# ----------------------------------------------------------------------------- media probes
def have(bin_name: str) -> bool:
    return shutil.which(bin_name) is not None


def media_duration(path: str) -> float | None:
    """ffprobe when it exists, otherwise parse `ffmpeg -i` — the same number, one fewer dependency."""
    if have("ffprobe"):
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "csv=p=0", str(path)], capture_output=True, text=True)
        try:
            return float(r.stdout.strip())
        except ValueError:
            pass
    if have("ffmpeg"):
        r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path)], capture_output=True, text=True)
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", r.stderr)
        if m:
            h, mi, s = m.groups()
            return int(h) * 3600 + int(mi) * 60 + float(s)
    return None

