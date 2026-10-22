#!/usr/bin/env python3
"""
beat_sheet.py — write the beat sheet (Markdown) for a built project: scenes, copy, cues, audio events.

    python3 beat_sheet.py <project_dir> --spec spec.json [--out deliver/beat-sheet.md] [--lang fa|ar|en]

The sheet is what the user keeps: it documents every on-screen line with its source and timing, so
captions, translations and A/B variants can be made without reopening the project.
"""
import argparse, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LABELS = {
    "fa": {"title": "بیت‌شیت ریل", "scene": "صحنه", "type": "بلوک", "time": "زمان", "copy": "متن روی تصویر", "cues": "کیوها (ثانیه)",
           "audio": "طرح صدا", "ev": "رویدادهای صوتی (auto_sfx)", "src": "منابع ذکرشده", "dur": "مدت", "mode": "حالت صدا"},
    "ar": {"title": "ورقة الإيقاع", "scene": "المشهد", "type": "الكتلة", "time": "الزمن", "copy": "النصّ على الشاشة", "cues": "النقاط (ثانية)",
           "audio": "خطّة الصوت", "ev": "أحداث الصوت", "src": "المصادر", "dur": "المدّة", "mode": "نمط الصوت"},
    "en": {"title": "Beat sheet", "scene": "Scene", "type": "Block", "time": "Time", "copy": "On-screen copy", "cues": "Cues (s)",
           "audio": "Audio plan", "ev": "Audio events (auto_sfx)", "src": "Sources cited", "dur": "Duration", "mode": "Audio mode"},
}
TEXT_KEYS = ["lead", "line1", "line2", "sub", "label", "lines", "wrong_label", "wrong", "right_label", "right", "line3", "line4",
             "q1", "q2", "hero", "after", "source", "seal", "cards", "attribution", "text", "items", "title", "kicker", "share", "final",
             # v3 long-text blocks
             "term", "body", "note", "question", "answer", "events", "col_a", "col_b", "verdict", "label_q", "label_a"]


def flat(v):
    if isinstance(v, list):
        return " / ".join(flat(x) for x in v)
    if isinstance(v, dict):
        return " · ".join(flat(x) for x in v.values() if x)
    return str(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project"); ap.add_argument("--spec", required=True); ap.add_argument("--out"); ap.add_argument("--lang", default="fa")
    a = ap.parse_args()
    L = LABELS[a.lang]
    spec = json.load(open(a.spec, encoding="utf-8"))
    res = json.load(open(os.path.join(a.project, "spec.resolved.json"), encoding="utf-8"))
    out = a.out or os.path.join(a.project, "beat-sheet.md")
    lines = [f"# {L['title']} — {spec.get('title', spec.get('id', ''))}", "",
             f"- {L['dur']}: **{res['duration']} s** · 1080×1920 · 30 fps", f"- {L['mode']}: `{(spec.get('audio') or {}).get('mode', 'silent')}`" +
             (f" · recitation {spec['audio']['recitation'].get('ref')} ({spec['audio']['recitation'].get('edition', 'ar.mahermuaiqly')})" if (spec.get('audio') or {}).get('recitation') else " · no recitation"), "",
             f"| # | {L['type']} | {L['time']} | {L['copy']} | {L['cues']} |", "|---|---|---|---|---|"]
    srcs = []
    for sc, rs in zip(spec["scenes"], res["scenes"]):
        copy = []
        for k in sc:
            if k in TEXT_KEYS and sc[k]:
                v = flat(sc[k]); copy.append(f"**{k}**: {re.sub(r'</?em>', '*', v)}")
                if k in ("source", "attribution", "cards", "sub"):
                    srcs.append(v)
        cues = "; ".join(f"{k} {v}" for k, v in rs["cues"].items())
        lines.append(f"| {sc['id']} | {sc['type']} | {sc['start']}–{sc['end']} | " + "<br>".join(copy).replace("|", "،") + f" | {cues} |")
    lines += ["", f"## {L['audio']}", ""]
    try:
        ev = subprocess.run([sys.executable, os.path.join(HERE, "mix.py"), a.project, "--dry-run"], capture_output=True, text=True).stdout.strip().splitlines()
        lines += [f"### {L['ev']}", "", "```", *ev, "```", ""]
    except Exception:
        pass
    if srcs:
        lines += [f"## {L['src']}", ""] + [f"- {s}" for s in dict.fromkeys(srcs)]
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
