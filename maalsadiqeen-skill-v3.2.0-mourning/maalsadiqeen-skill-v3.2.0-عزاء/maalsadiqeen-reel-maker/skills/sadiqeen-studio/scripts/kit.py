#!/usr/bin/env python3
"""The publishing half: three captions, seven comments, one schedule.

A reel is not finished when the MP4 exists. It is finished when the caption carries what
the screen could not say, the first comment is a reference and not a question, and the
posting time is the brand's own window rather than a guess.

    python3 kit.py spec.json --out kit/
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import brandkit as bk
import plan

EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")


def _cfg() -> dict:
    return bk.brand_config()


def _hashtags(spec: dict, n: int = 4) -> list[str]:
    h = _cfg().get("hashtags", {})
    core = list(h.get("core", ["#مع_الصادقين"]))
    tags = list(core)
    blob = json.dumps(spec, ensure_ascii=False)
    for key, tag in (h.get("imam") or {}).items():
        if key in blob and tag not in tags:
            tags.append(tag)
    for key, tag in (h.get("topic") or {}).items():
        if key in blob and tag not in tags:
            tags.append(tag)
    return tags[:n]


def _refs(spec: dict) -> list[str]:
    out = []
    for sc in spec["scenes"]:
        for key in ("source", "attribution"):
            if sc.get(key):
                out.append(str(sc[key]).lstrip("— ").strip())
        for card in sc.get("cards") or []:
            out.append(f'{card.get("book", "")} {card.get("loc", "")}'.strip())
        if sc.get("label"):
            out.append(str(sc["label"]).strip("﴿ ﴾"))
    seen, uniq = set(), []
    for r in out:
        if r and r not in seen:
            seen.add(r)
            uniq.append(r)
    return uniq


def _idea(spec: dict) -> str:
    for sc in spec["scenes"]:
        if sc["type"] in ("paragraph", "qa", "definition"):
            t = sc.get("text") or sc.get("answer") or ""
            first = re.split(r"(?<=[.؟!])\s+", t.strip())[0]
            return first
    for sc in spec["scenes"]:
        if sc.get("hero"):
            return sc["hero"]
    return spec.get("title", "")


def captions(spec: dict) -> dict:
    lim = _cfg().get("limits", {})
    tags = _hashtags(spec)
    idea = _idea(spec)
    refs = _refs(spec)
    title = spec.get("title", "")
    hook = next((sc.get("line2") or sc.get("line1") for sc in spec["scenes"]
                 if sc["type"] == "hook" and (sc.get("line2") or sc.get("line1"))), title)

    ig = [hook, "", idea]
    if refs:
        ig += ["", "📖 " + " · ".join(refs[:2]) if False else "المصدر: " + " · ".join(refs[:2])]
    ig += ["", " ".join(tags[:4])]
    fb = [hook, "", idea, ""]
    if refs:
        fb.append("المصدر: " + " · ".join(refs[:3]))
    fb += ["", " ".join(tags[:2]), "", "سؤال: أيّهما أقرب إلى ما تفهمه من النص؟"]
    x = [hook]
    if idea and len(hook) + len(idea) < 200:
        x.append(idea[: 190 - len(hook)])
    x.append(" ".join(tags[:1]))
    texts = {"instagram": "\n".join(ig).strip(), "facebook": "\n".join(fb).strip(),
             "x": "\n".join(x).strip()[:250]}

    verdicts = {}
    for platform, text in texts.items():
        L = lim.get(platform, {})
        hard = L.get("hard_max", 2200)
        target = L.get("target", [0, hard])
        hmin, hmax = L.get("hashtags", [0, 5])
        n_tags = len(re.findall(r"#\w+", text))
        notes = []
        if len(text) > hard:
            notes.append(f"{len(text)} chars > hard {hard}")
        elif not (target[0] <= len(text) <= target[1]):
            notes.append(f"{len(text)} chars, target {target[0]}–{target[1]}")
        if not (hmin <= n_tags <= hmax):
            notes.append(f"{n_tags} hashtags, want {hmin}–{hmax}")
        if EMOJI.search(text):
            notes.append("emoji")
        verdicts[platform] = {"chars": len(text), "hashtags": n_tags,
                              "ok": not notes, "notes": notes}
    return {"texts": texts, "verdicts": verdicts, "hashtags": tags, "refs": refs}


def comments(spec: dict, kit: dict) -> list[dict]:
    refs = kit["refs"]
    slots = [
        ("المصدر", refs[0] if refs else "المصادر مذكورة في الفيديو."),
        ("السياق", spec.get("life_impact") or "النصّ يُقرأ كاملًا قبل الاقتباس."),
        ("السؤال", "ما الفرق بين «الصادقين» و«صادقين» في الآية عندك؟"),
        ("الإحالة", "من أين قرأت هذا النص؟ اذكره لي حتى نتحقق منه معًا."),
        ("التصحيح", "إن ظهر خطأ في التشكيل أو الإحالة، سيُصحَّح في التعليق الأول."),
        ("التوسيع", "يمكن أن نُفرد لهذا المعنى ريلًا ثانيًا إن احتاجه المتابعون."),
        ("الأدب", "لا نقاش في الأشخاص والأسماء؛ النقاش في النصّ وسنده."),
    ]
    now = datetime.now(timezone.utc)
    out = []
    for i, (title, body) in enumerate(slots):
        out.append({"slot": title, "text": body,
                    "at": (now + timedelta(minutes=[2, 12, 40, 90, 240, 720, 1440][i]))
                    .strftime("%Y-%m-%d %H:%M UTC")})
    return out


def publish_md(spec: dict, kit: dict) -> str:
    cfg = _cfg()
    tz = cfg.get("timezone", "Asia/Baghdad")
    windows = cfg.get("posting_windows") or {}
    order = cfg.get("cross_post_order") or ["instagram", "facebook", "x"]
    lines = [f"# {spec.get('title', '')}", "", f"**المنطقة الزمنية:** {tz}", ""]
    if windows:
        lines += ["## نوافذ النشر", "", "| اليوم | الساعة |", "|---|---|"]
        for day, hours in list(windows.items())[:4]:
            lines.append(f"| {day} | {' · '.join(str(h) for h in hours) if isinstance(hours, list) else hours} |")
        lines.append("")
    lines += ["## ترتيب النشر", "", " → ".join(order), ""]
    lines += ["## الساعة الأولى", "",
              "1. ثبّت التعليق الأول (المصدر) قبل أي رد.",
              "2. أجب على أول خمسة تعليقات بسؤال واحد، لا بجدال.",
              "3. لا تعدّل الوصف قبل مرور ساعة — التعديل يقطع التوزيع.",
              "4. راقب sends-per-reach لا اللايكات.", ""]
    lines += ["## بعد ٤٨ ساعة", "",
              "- احفظ أفضل ثلاث لحظات (watch time) وأعد استخدامها كافتتاحيات.",
              "- إن كان الحفظ أقل من ٢٪، المشكلة في الوعد لا في الوصف.", ""]
    return "\n".join(lines)


def build(spec_path: str, out: str) -> dict:
    spec = plan.resolve(plan.load(spec_path))
    kit = captions(spec)
    d = Path(out)
    d.mkdir(parents=True, exist_ok=True)
    (d / "captions").mkdir(exist_ok=True)
    for platform, text in kit["texts"].items():
        (d / "captions" / f"{platform}.txt").write_text(text + "\n", encoding="utf-8")
    (d / "captions.json").write_text(json.dumps(kit, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
    cs = comments(spec, kit)
    md = ["# التعليقات (٧ خانات)", "", "| متى | الخانة | النصّ |", "|---|---|---|"]
    for c in cs:
        md.append(f'| {c["at"]} | {c["slot"]} | {c["text"]} |')
    (d / "comments.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (d / "publish.md").write_text(publish_md(spec, kit), encoding="utf-8")
    alt = f'{spec.get("title", "")} — {kit["texts"]["x"][:120]}'
    (d / "alt-text.txt").write_text(alt + "\n", encoding="utf-8")
    return kit


def main() -> int:
    ap = argparse.ArgumentParser(description="spec → captions · comments · schedule")
    ap.add_argument("spec")
    ap.add_argument("--out", default="kit")
    a = ap.parse_args()
    kit = build(a.spec, a.out)
    bad = {k: v for k, v in kit["verdicts"].items() if not v["ok"]}
    print(f"kit → {a.out}  ·  " + " · ".join(f'{k} {v["chars"]}c' for k, v in kit["verdicts"].items()))
    for k, v in bad.items():
        print(f"  ! {k}: {', '.join(v['notes'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
