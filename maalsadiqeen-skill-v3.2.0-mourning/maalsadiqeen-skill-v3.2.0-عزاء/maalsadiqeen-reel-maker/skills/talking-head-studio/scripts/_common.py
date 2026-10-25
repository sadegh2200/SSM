#!/usr/bin/env python3
"""
_common.py — shared plumbing for talking-head-studio.

Everything that touches the outside world lives here: finding ffmpeg/ffprobe, running
commands, probing media, reading/writing JSON, and the small amount of maths the pipeline
needs (smoothing, expression building, unit conversion).

Design rules this file enforces for the whole skill:
  * no silent success — every helper returns facts or raises ToolError with the real message;
  * no invented numbers — if a measurement fails, the field is None and the caller must say so;
  * ffmpeg is a hard dependency, ffprobe is a hard dependency for measurement but the build
    itself can still run without it (it degrades honestly).
"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
ASSETS = SKILL_DIR / "assets"
FONTS = ASSETS / "fonts"
CASCADES = ASSETS / "cascades"
STYLES = ASSETS / "styles"


class ToolError(RuntimeError):
    """A command the pipeline needs failed. Carries ffmpeg's own stderr tail."""

    def __init__(self, message: str, cmd: list[str] | None = None, stderr: str = "", kind: str = "tool"):
        super().__init__(message)
        self.cmd = cmd or []
        self.stderr = stderr
        self.kind = kind

    def as_dict(self) -> dict:
        return {"kind": self.kind, "message": str(self), "cmd": self.cmd,
                "stderr": self.stderr[-2000:]}


# --------------------------------------------------------------------------- tool discovery

def _env_paths() -> list[Path]:
    """Places a previous bootstrap may have left the static binaries."""
    home = Path.home()
    return [
        home / ".cache" / "sc" / "bin",
        home / ".cache" / "reel-bin",
        home / "bin",
        Path("/usr/local/bin"),
        Path("/usr/bin"),
    ]


def find_tool(name: str) -> str | None:
    hit = shutil.which(name)
    if hit:
        return hit
    for d in _env_paths():
        cand = d / name
        if cand.is_file() and os.access(cand, os.X_OK):
            return str(cand)
    return None


def ffmpeg() -> str:
    p = find_tool("ffmpeg")
    if not p:
        raise ToolError(
            "ffmpeg not found. Run: bash <skill>/scripts/bootstrap.sh   (or install ffmpeg)",
            kind="missing_tool")
    return p


def ffprobe() -> str | None:
    return find_tool("ffprobe")


# --------------------------------------------------------------------------- process running

def run(cmd: list[str], *, timeout: int = 1800, check: bool = True,
        stdin_text: str | None = None) -> subprocess.CompletedProcess:
    """Run a command, capture everything, and raise ToolError with the real stderr on failure."""
    try:
        cp = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            input=stdin_text, errors="replace",
        )
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f"timed out after {timeout}s: {cmd[0]}", cmd, str(exc), "timeout") from exc
    except FileNotFoundError as exc:
        raise ToolError(f"not found: {cmd[0]}", cmd, str(exc), "missing_tool") from exc
    if check and cp.returncode != 0:
        raise ToolError(f"{Path(cmd[0]).name} exited {cp.returncode}", cmd,
                        cp.stderr or cp.stdout, "tool")
    return cp


# --------------------------------------------------------------------------- media probing

def probe(path: str | Path) -> dict:
    """ffprobe → a flat, always-present shape. Missing values are None, never guessed."""
    path = str(path)
    exe = ffprobe()
    if not exe:
        raise ToolError("ffprobe not found — needed to measure the source", kind="missing_tool")
    cp = run([exe, "-v", "error", "-print_format", "json",
              "-show_format", "-show_streams", path], timeout=120)
    raw = json.loads(cp.stdout or "{}")
    fmt = raw.get("format", {}) or {}
    v = next((s for s in raw.get("streams", []) if s.get("codec_type") == "video"), None)
    a = next((s for s in raw.get("streams", []) if s.get("codec_type") == "audio"), None)

    def f(x, default=None):
        try:
            return float(x)
        except (TypeError, ValueError):
            return default

    def i(x, default=None):
        try:
            return int(float(x))
        except (TypeError, ValueError):
            return default

    rot = 0
    if v:
        for sd in (v.get("side_data_list") or []):
            if "rotation" in sd:
                rot = int(f(sd.get("rotation"), 0) or 0)
        rot = int(f((v.get("tags") or {}).get("rotate"), rot) or rot)
    dur = f(fmt.get("duration")) or f(v and v.get("duration")) or None

    width, height = (i(v.get("width")), i(v.get("height"))) if v else (None, None)
    # a 90/270 rotation means the displayed frame is swapped
    if v and abs(rot) % 180 == 90 and width and height:
        width, height = height, width

    return {
        "path": path,
        "duration": dur,
        "size_bytes": i(fmt.get("size")),
        "bitrate": i(fmt.get("bit_rate")),
        "has_video": v is not None,
        "has_audio": a is not None,
        "width": width,
        "height": height,
        "rotation": rot,
        "fps": parse_rate(v.get("r_frame_rate") if v else None),
        "avg_fps": parse_rate(v.get("avg_frame_rate") if v else None),
        "vcodec": v.get("codec_name") if v else None,
        "pix_fmt": v.get("pix_fmt") if v else None,
        "color_primaries": v.get("color_primaries") if v else None,
        "color_transfer": v.get("color_transfer") if v else None,
        "acodec": a.get("codec_name") if a else None,
        "sample_rate": i(a.get("sample_rate")) if a else None,
        "channels": i(a.get("channels")) if a else None,
        "ch_layout": (a.get("channel_layout") if a else None),
        "audio_start": f(a.get("start_time")) if a else None,
        "video_start": f(v.get("start_time")) if v else None,
    }


def parse_rate(text: str | None) -> float | None:
    if not text or text in ("0/0", "N/A"):
        return None
    if "/" in text:
        num, _, den = text.partition("/")
        try:
            n, d = float(num), float(den)
            return round(n / d, 4) if d else None
        except ValueError:
            return None
    try:
        return round(float(text), 4)
    except ValueError:
        return None


def has_filter(name: str) -> bool:
    """Is this ffmpeg filter present in the build we are using? Cached per process."""
    cache = has_filter.__dict__.setdefault("_cache", {})
    if name not in cache:
        try:
            cp = run([ffmpeg(), "-hide_banner", "-filters"], check=False, timeout=60)
            cache[name] = any(len(p := line.split()) >= 3 and p[1] == name
                              for line in cp.stdout.splitlines())
        except ToolError:
            cache[name] = False
    return cache[name]


# --------------------------------------------------------------------------- json io

def read_json(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: str | Path, data: dict) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    tmp.replace(path)
    return path


def write_text(path: str | Path, text: str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# --------------------------------------------------------------------------- maths helpers

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def median(values: list[float]) -> float | None:
    vals = sorted(v for v in values if v is not None and not math.isnan(v))
    if not vals:
        return None
    mid = len(vals) // 2
    return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2


def percentile(values: list[float], p: float) -> float | None:
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    k = clamp(p, 0.0, 1.0) * (len(vals) - 1)
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return vals[int(k)]
    return vals[lo] + (vals[hi] - vals[lo]) * (k - lo)


def smooth_series(values: list[float], window: int = 5, passes: int = 2) -> list[float]:
    """Moving average, repeated. Used so a face-tracking pan never jitters."""
    out = list(values)
    if window <= 1 or not out:
        return out
    for _ in range(max(1, passes)):
        half = window // 2
        src = list(out)
        n = len(src)
        for idx in range(n):
            lo, hi = max(0, idx - half), min(n, idx + half + 1)
            out[idx] = sum(src[lo:hi]) / (hi - lo)
    return out


def resample_curve(points: list[tuple[float, float]], count: int) -> list[tuple[float, float]]:
    """Linear-resample (t,v) keyframes down to at most `count` evenly spaced keys."""
    pts = [(t, v) for t, v in points if t is not None and v is not None]
    if not pts:
        return []
    if len(pts) <= count:
        return pts
    t0, t1 = pts[0][0], pts[-1][0]
    if t1 <= t0:
        return [pts[0]]
    out = []
    for k in range(count):
        t = t0 + (t1 - t0) * k / (count - 1)
        lo = max(p for p in pts if p[0] <= t)
        hi = min((p for p in pts if p[0] >= t), default=lo)
        if hi[0] == lo[0]:
            out.append((t, lo[1]))
        else:
            f = (t - lo[0]) / (hi[0] - lo[0])
            out.append((t, lo[1] + (hi[1] - lo[1]) * f))
    return out


def piecewise_expr(keys: list[tuple[float, float]], var: str = "t",
                   decimals: int = 2) -> str:
    """
    Build an ffmpeg expression that linearly interpolates keyframes over time.

    Used for crop x/y and zoom curves: ffmpeg evaluates these per frame, so a
    piecewise-linear chain is exactly a smooth pan — no external timeline needed.
    """
    keys = [(round(t, 4), round(v, decimals)) for t, v in keys]
    if not keys:
        return "0"
    if len(keys) == 1:
        return f"{keys[0][1]}"
    expr = f"{keys[-1][1]}"
    for (t0, v0), (t1, v1) in reversed(list(zip(keys, keys[1:]))):
        span = max(1e-6, t1 - t0)
        seg = f"({v0}+({v1}-{v0})*({var}-{t0})/{span:.4f})"
        expr = f"if(lt({var},{t1}),{seg},{expr})"
    return expr


# --------------------------------------------------------------------------- misc

def ensure_parent(path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def human_time(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    seconds = max(0.0, float(seconds))
    m, s = divmod(seconds, 60)
    h, m = divmod(int(m), 60)
    return f"{h}:{m:02d}:{s:05.2f}" if h else f"{m}:{s:05.2f}"


def eprint(*args, **kwargs) -> None:
    print(*args, file=sys.stderr, **kwargs)


def esc_filter_path(path: str | Path) -> str:
    """Escape a path for use inside an ffmpeg filter argument (subtitles=, fontfile=)."""
    p = str(Path(path).resolve())
    p = p.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    return p


def temp_dir(prefix: str = "ths-") -> Path:
    base = Path(os.environ.get("TMPDIR") or tempfile.gettempdir())
    base.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=str(base)))
