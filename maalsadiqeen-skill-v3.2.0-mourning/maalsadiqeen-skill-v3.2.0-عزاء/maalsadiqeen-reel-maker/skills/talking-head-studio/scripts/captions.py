#!/usr/bin/env python3
"""
captions.py — subtitle intake, time remapping and styling.

    python3 captions.py input.srt --out captions.ass \
        --size 72 --margin 280 --width 1080 --height 1920 \
        --font assets/fonts/Vazirmatn.ttf --style bold [--shift 0]

Why this is not just "burn the SRT":

  * Time remapping. The moment the pipeline cuts dead air, every cue in the
    user's SRT points at the wrong second. Each cue is therefore pushed through
    the same keep-range map used to cut the picture, split at cut boundaries,
    and dropped when it has nothing left. `--shift` additionally handles a
    hand-made SRT that starts from a different zero.

  * Reading speed. Cues are checked against a hard characters-per-second budget
    (default 17 for Latin, 14 for Arabic/Persian where letters are wider). Over
    budget is a warning with the exact cue number, not a silent rewrite — the
    words are the author's.

  * Script awareness. Arabic/Persian/Urdu text flips the style to an RTL-safe
    one (Vazirmatn/Amiri, bottom-centre, no italics) because libass' bidi
    handling differs from the Latin path.

    HARD-WON RULE: leave ASS `Spacing` at 0. A non-zero letter-spacing makes
    this libass draw Arabic/Persian glyphs in logical order without joining
    them — the text comes out mirrored and disconnected, and no bidi setting
    fixes it afterwards. Verified by bisection: Spacing 0 renders «سلام دنیا»
    correctly, Spacing 0.4 produces disjoint, reversed letters. Do not
    "improve" tracking in this file.

  * Safe areas. --margin is the distance from the bottom edge that platform UI
    covers; the caller computes it from the output height (see plan.py).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import FONTS, clamp, eprint, write_json  # noqa: E402

RTL_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")

STYLES = {
    # name      outline  shadow  boxed  bold  max_lines  cps_budget
    "minimal":  {"outline": 2.4, "shadow": 0.0, "boxed": False, "bold": 0, "max_lines": 2, "cps": 17},
    "bold":     {"outline": 3.4, "shadow": 0.8, "boxed": False, "bold": -1, "max_lines": 2, "cps": 17},
    "boxed":    {"outline": 1.4, "shadow": 0.0, "boxed": True,  "bold": -1, "max_lines": 2, "cps": 17},
    "karaoke":  {"outline": 3.0, "shadow": 0.6, "boxed": False, "bold": -1, "max_lines": 1, "cps": 20},
}


# --------------------------------------------------------------------------- srt parsing

def _ts(text: str) -> float | None:
    m = re.match(r"\s*(\d+):(\d{1,2}):(\d{1,2})[.,](\d{1,3})\s*$", text)
    if not m:
        return None
    h, mi, s, ms = m.groups()
    return int(h) * 3600 + int(mi) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000.0


def parse_srt(path: str | Path) -> list[dict]:
    raw = Path(path).read_text(encoding="utf-8-sig", errors="replace").replace("\r\n", "\n")
    cues = []
    for block in re.split(r"\n{2,}", raw.strip()):
        lines = [ln for ln in block.split("\n") if ln.strip() != ""]
        if not lines:
            continue
        idx = 0
        if re.fullmatch(r"\d+", lines[0].strip()) and len(lines) > 1:
            idx = 1
        if idx >= len(lines) or "-->" not in lines[idx]:
            continue
        left, _, right = lines[idx].partition("-->")
        start, end = _ts(left), _ts(right.strip().split()[0] if right.strip() else "")
        if start is None or end is None or end <= start:
            continue
        text = "\n".join(lines[idx + 1:]).strip()
        if not text:
            continue
        cues.append({"start": round(start, 3), "end": round(end, 3), "text": text})
    return cues


def parse_words(path: str | Path) -> list[dict]:
    """Optional word-level file: [{"t":1.23,"d":0.31,"w":"word"}, ...] or Whisper-style JSON."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    words = []
    if isinstance(data, dict) and "words" in data:
        data = data["words"]
    for w in data:
        if not isinstance(w, dict):
            continue
        start = w.get("t", w.get("start"))
        dur = w.get("d", w.get("duration"))
        end = w.get("end", (start + dur) if (start is not None and dur is not None) else None)
        text = w.get("w", w.get("word", w.get("text")))
        if start is None or end is None or not text:
            continue
        words.append({"start": float(start), "end": float(end), "text": str(text)})
    return sorted(words, key=lambda w: w["start"])


# --------------------------------------------------------------------------- time remap

def remap(cues: list[dict], keeps: list[dict], shift: float = 0.0) -> list[dict]:
    """
    Push cues through the cut map.

    keeps: [{"src_start":a,"src_end":b,"out_start":c}, ...] — output time for a
    source instant is c + (t - a). A cue that straddles a cut is split, and the
    parts are joined with a space so the sentence survives the jump cut.
    """
    out: list[dict] = []
    for cue in cues:
        s = cue["start"] - shift
        e = cue["end"] - shift
        if e <= s:
            continue
        parts = []
        for k in keeps:
            a, b = k["src_start"], k["src_end"]
            lo, hi = max(s, a), min(e, b)
            if hi - lo <= 0.04:
                continue
            parts.append({
                "start": round(k["out_start"] + (lo - a), 3),
                "end": round(k["out_start"] + (hi - a), 3),
                "text": cue["text"],
            })
        if not parts:
            continue
        if len(parts) == 1:
            out.append(parts[0])
        else:
            # merge consecutive parts of the same cue that stay adjacent
            merged = [parts[0]]
            for p in parts[1:]:
                if p["start"] - merged[-1]["end"] <= 0.12:
                    merged[-1]["end"] = p["end"]
                else:
                    merged.append(p)
            out.extend(merged)
    return _dedupe(out)


def _dedupe(cues: list[dict]) -> list[dict]:
    out: list[dict] = []
    for c in sorted(cues, key=lambda x: x["start"]):
        if out and abs(c["start"] - out[-1]["start"]) < 0.02 and c["text"] == out[-1]["text"]:
            out[-1]["end"] = max(out[-1]["end"], c["end"])
        else:
            out.append(dict(c))
    return out


def reading_speed(cues: list[dict], rtl: bool) -> dict:
    budget = 14.0 if rtl else 17.0
    worst, offenders = 0.0, []
    total_chars = 0
    for i, c in enumerate(cues, 1):
        dur = max(0.2, c["end"] - c["start"])
        chars = len(re.sub(r"\s+", " ", c["text"]).strip())
        total_chars += chars
        cps = chars / dur
        worst = max(worst, cps)
        if cps > budget:
            offenders.append({"cue": i, "cps": round(cps, 1), "text": c["text"][:48]})
    return {"budget": budget, "worst_cps": round(worst, 1),
            "offenders": offenders[:8], "total_chars": total_chars}


# --------------------------------------------------------------------------- ass writer

def _ass_time(t: float) -> str:
    t = max(0.0, t)
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _ass_color(hex_rgb: str, alpha: int = 0) -> str:
    h = hex_rgb.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def build_ass(cues: list[dict], *, width: int, height: int, size: int, margin: int,
              font_name: str = "Vazirmatn", style: str = "bold", rtl: bool = False,
              primary: str = "#FFFFFF", outline_color: str = "#000000",
              back: str = "#000000", back_alpha: int = 0x66,
              words: list[dict] | None = None, position: str = "bottom") -> str:
    """Return the ASS text. Cue text is never rewritten — only wrapped and styled."""
    spec = STYLES.get(style, STYLES["bold"])
    outline = spec["outline"] * (1.0 if height >= 1080 else 0.8)
    shadow = spec["shadow"]
    border_style = 3 if spec["boxed"] else 1
    align = 2 if position == "bottom" else (8 if position == "top" else 5)

    header = f"""[Script Info]
; generated by talking-head-studio
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: THS,{font_name},{size},{_ass_color(primary)},{_ass_color('#FFD24A')},{_ass_color(outline_color)},{_ass_color(back, back_alpha)},{spec['bold']},0,0,0,100,100,0,0,{border_style},{outline:.1f},{shadow:.1f},{align},{int(width * 0.07):d},{int(width * 0.07):d},{margin},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for cue in cues:
        text = cue["text"].replace("\r", "")
        text = "\\N".join(ln.strip() for ln in text.split("\n") if ln.strip())
        text = text.replace("{", "(").replace("}", ")")   # never let user text become override tags
        events.append(f"Dialogue: 0,{_ass_time(cue['start'])},{_ass_time(cue['end'])},THS,,0,0,0,,{text}")

    if words:
        # karaoke: one event per word-group, highlight by \\k timing inside the group
        for grp in _word_groups(words, words_per_line=3 if not rtl else 2):
            start, end = grp[0]["start"], grp[-1]["end"]
            parts = []
            for w in grp:
                cs = max(1, int(round((w["end"] - w["start"]) * 100)))
                parts.append(f"{{\\k{cs}}}{w['text']}")
            events.append(f"Dialogue: 1,{_ass_time(start)},{_ass_time(end)},THS,,0,0,0,,{' '.join(parts)}")

    return header + "\n".join(events) + "\n"


def _word_groups(words: list[dict], words_per_line: int = 3) -> list[list[dict]]:
    groups, cur = [], []
    for w in words:
        if cur and (len(cur) >= words_per_line or w["start"] - cur[-1]["end"] > 0.55):
            groups.append(cur)
            cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    return groups


def resolve_font(font: str | None, rtl: bool) -> tuple[str, Path | None]:
    """Font *name* for ASS plus the file to embed, if the skill ships one."""
    if font:
        p = Path(font)
        if p.is_file():
            return p.stem, p
        return font, None
    preferred = ["Vazirmatn.ttf", "Amiri-Bold.ttf"] if rtl else ["Vazirmatn.ttf", "Amiri-Bold.ttf"]
    for name in preferred:
        cand = FONTS / name
        if cand.is_file():
            return cand.stem, cand
    return ("Vazirmatn" if rtl else "DejaVu Sans"), None


def main() -> int:
    ap = argparse.ArgumentParser(description="SRT/word-JSON → styled ASS, with time remapping through cuts.")
    ap.add_argument("input")
    ap.add_argument("--out", required=True)
    ap.add_argument("--words", default=None, help="word-level JSON for karaoke")
    ap.add_argument("--keeps", default=None, help="JSON list of keep ranges (src_start/src_end/out_start)")
    ap.add_argument("--shift", type=float, default=0.0, help="seconds to subtract from cue times")
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    ap.add_argument("--size", type=int, default=None)
    ap.add_argument("--margin", type=int, default=None)
    ap.add_argument("--font", default=None)
    ap.add_argument("--style", default="bold", choices=sorted(STYLES))
    ap.add_argument("--position", default="bottom", choices=["bottom", "center", "top"])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    cues = parse_srt(args.input) if args.input.lower().endswith((".srt", ".vtt")) else []
    if not cues:
        eprint(f"✗ no cues parsed from {args.input}")
        return 2
    words = parse_words(args.words) if args.words else None
    keeps = None
    if args.keeps:
        keeps = json.loads(Path(args.keeps).read_text(encoding="utf-8"))
    if keeps:
        cues = remap(cues, keeps, args.shift)
    elif args.shift:
        cues = [{"start": round(c["start"] - args.shift, 3), "end": round(c["end"] - args.shift, 3),
                 "text": c["text"]} for c in cues]
    rtl = any(RTL_RE.search(c["text"]) for c in cues)
    if words and keeps:
        words = remap([{"start": w["start"], "end": w["end"], "text": w["text"]} for w in words], keeps, args.shift)

    size = args.size or max(28, int(round(args.height * 0.040)))
    margin = args.margin if args.margin is not None else int(round(args.height * 0.15))
    font_name, font_file = resolve_font(args.font, rtl)

    ass = build_ass(cues, width=args.width, height=args.height, size=size, margin=margin,
                    font_name=font_name, style=args.style, rtl=rtl, words=words,
                    position=args.position)
    Path(args.out).write_text(ass, encoding="utf-8")
    speed = reading_speed(cues, rtl)
    report = {"cues_in": len(parse_srt(args.input)) if args.input.lower().endswith((".srt", ".vtt")) else 0,
              "cues_out": len(cues), "rtl": rtl, "font": font_name,
              "font_file": str(font_file) if font_file else None,
              "size": size, "margin": margin, "style": args.style,
              "reading_speed": speed, "ass": args.out}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"captions → {args.out}: {len(cues)} cues · {'RTL' if rtl else 'LTR'} · "
              f"{font_name} {size}px · margin {margin}px")
        if speed["offenders"]:
            print(f"  ⚠ {len(speed['offenders'])} cue(s) above {speed['budget']} chars/s "
                  f"(worst {speed['worst_cps']})")
    write_json(Path(args.out).with_suffix(".captions.json"), report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
