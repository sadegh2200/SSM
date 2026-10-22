#!/usr/bin/env python3
"""
comments.py — the seven-comment bank, scheduled, validated, copy-paste ready.

    python3 comments.py spec.json --out comments.md [--brief brief.json] [--series series.json]
                             [--at 19:30] [--brand config/brand.json] [--json]

Slots (config/brand.json → comments.slots): sources · opening question · term · life impact ·
series/next · calm objection · share. Times are offsets from publish, printed in the audience zone
and UTC. Every comment is ≤ config.comments.max_chars, emoji-free, and the first one carries the
reference (it is the one that gets pinned).

Nothing here is invented: the content is derived from the spec the agent authored. When a slot has no
material (e.g. no series planned), it becomes a real question to the audience instead of a fake
promise.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(HERE))
from _common import EMOJI, strip_tashkeel, words  # noqa: E402
import captions  # noqa: E402

BRAND_PATH = SKILL / "config" / "brand.json"


def load_json(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", captions.clean(s))


def shorten(s: str, n: int) -> str:
    s = clean(s)
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0].rstrip("،,; ") + "…"


def build(spec: dict, brand: dict, brief: dict | None, series: dict | None) -> list[dict]:
    brief = brief or {}
    f = captions.spec_facts(spec, brief)
    scenes = spec.get("scenes") or []
    contrast = next((s for s in scenes if s.get("type") == "contrast"), {})
    proof = next((s for s in scenes if s.get("type") == "proof"), {})
    cta = next((s for s in scenes if s.get("type") == "cta"), {})
    title = brief.get("title") or (spec.get("scenario") or {}).get("title_fa") or ""
    topic = clean(f.get("verse_label") or f.get("hook") or "")

    out: list[dict] = []

    # 1 · sources (pinned)
    seal = " ".join(proof.get("seal") or [])
    body = "المصادر: " + (f["source"] or "تُذكر في التعليق المثبّت") + "."
    if seal:
        body += f" الدرجة: {seal}."
    if f["verse"]:
        body += f" النصّ: «{shorten(f['verse'], 110)}»."
    out.append({"slot": "sources", "kind": "المصادر والدرجة", "pinned": True,
                "text": body, "goal": "اعتماد وذخیره؛ مرجع کامل روی صفحه جا نمی‌شود"})

    # 2 · opening question
    qs = (brand.get("questions") or {}).get("instagram") or ["ما الذي يفتحه هذا النصّ في فهمك؟"]
    question = qs[0]
    hero = clean((next((s for s in scenes if s.get("type") == "answer"), {}) or {}).get("hero", ""))
    text = f"{question}" + (f" الجواب في النصّ: «{shorten(hero, 60)}»." if hero else "")
    out.append({"slot": "opening_question", "kind": "سؤال الافتتاح", "pinned": False,
                "text": text, "goal": "شروع گفتگو با پرسشی که با یک خط پاسخ‌پذیر است"})

    # 3 · term
    if contrast:
        hinge = clean(contrast.get("right", ""))
        line3 = clean(contrast.get("line3", ""))
        text = f"«{shorten(hinge, 70)}»" + (f" — {line3}." if line3 else ".") + " الفرقُ في كلمةٍ واحدة."
        out.append({"slot": "term", "kind": "توضيح المصطلح", "pinned": False, "text": text,
                    "goal": "ورود مخاطب غیرمتخصص به معنای واژه"})
    else:
        out.append({"slot": "term", "kind": "توضيح المصطلح", "pinned": False,
                    "text": f"المصطلح المفتاحي في هذا النصّ: «{shorten(topic, 60)}». ما معناه عندك؟",
                    "goal": "ورود مخاطب غیرمتخصص به معنای واژه (نیازمند ویرایش انسانی)"})

    # 4 · life impact
    life = clean(spec.get("life_impact") or brief.get("life_impact") or "")
    if life:
        out.append({"slot": "life_impact", "kind": "الأثر في الحياة", "pinned": False,
                    "text": life, "goal": "پیوند معرفت با زندگی روزمره"})
    else:
        out.append({"slot": "life_impact", "kind": "الأثر في الحياة", "pinned": False,
                    "text": f"في حياتك اليوم: أين يظهر «{shorten(topic, 50)}» في قرارٍ واحد تتخذه؟",
                    "goal": "پیوند معرفت با زندگی روزمره (نیازمند ویرایش انسانی)"})

    # 5 · series or next question
    if series and series.get("title_ar"):
        part = (spec.get("scenario") or {}).get("id")
        nxt = ""
        for p in series.get("parts") or []:
            if p.get("n") and part and int(p["n"]) == int(part) + 1:
                nxt = p.get("question") or ""
        text = f"سلسلة «{series['title_ar']}»" + (f" — الحلقة القادمة: {shorten(nxt, 90)}" if nxt else "")
        out.append({"slot": "series_or_next", "kind": "الإشارة إلى السلسلة", "pinned": False,
                    "text": text + ".", "goal": "بازگشت به قسمت بعد"})
    else:
        out.append({"slot": "series_or_next", "kind": "سؤال الحلقة القادمة", "pinned": False,
                    "text": f"ما السؤال الذي تودّ أن نجيب عنه في الحلقة القادمة عن «{shorten(topic, 50)}»؟ اكتبه هنا.",
                    "goal": "سوخت محتوای قسمت بعد از کامنت‌ها"})

    # 6 · calm objection
    if contrast.get("wrong"):
        wrong = clean(contrast.get("wrong"))
        right = clean(contrast.get("right"))
        text = f"يُقال: «{shorten(wrong, 70)}». والجواب: {shorten(right, 100)}"
        if f["source"]:
            text += f" — {shorten(f['source'], 50)}."
        else:
            text += "."
        out.append({"slot": "objection", "kind": "ردّ استباقي هادئ", "pinned": False,
                    "text": text, "goal": "پیش‌گیری از جدل با پاسخ مستند"})
    else:
        out.append({"slot": "objection", "kind": "ردّ استباقي هادئ", "pinned": False,
                    "text": "إن ورد إشكالٌ على النصّ، نجيبه هنا بالمصدر لا بالجدل. اطرحه بهدوء.",
                    "goal": "پیش‌گیری از جدل"})

    # 7 · the closing invitation — only if the reel earned one; otherwise a question that opens thought
    share = clean(cta.get("share") or "")
    if share:
        sending = "أرسل" in strip_tashkeel(share) or "أَرْسِل" in share
        text = (f"{share} — {shorten(topic, 60)} يخصّ من يسأل عن هذا المعنى." if sending
                else f"{share} — {shorten(topic, 60)}.")
        out.append({"slot": "share", "kind": "دعوة للمشاركة" if sending else "دعوة للحفظ", "pinned": False,
                    "text": text, "goal": "افزایش sends" if sending else "افزایش save"})
    else:
        out.append({"slot": "open_question", "kind": "سؤال مفتوح", "pinned": False,
                    "text": f"ما الذي بقي معك من {shorten(topic, 50)} بعد سماعه؟",
                    "goal": "دعوة إلى تأمّل، لا إلى مشاركة — النصّ الثقيل لا يُسوَّق"})
    return out


def validate(items: list[dict], brand: dict) -> list[dict]:
    max_chars = int((brand.get("comments") or {}).get("max_chars", 300))
    seen: dict[str, int] = {}
    for i, it in enumerate(items, 1):
        fails, warns = [], []
        text = it["text"]
        if len(text) > max_chars:
            fails.append(f"{len(text)} chars > {max_chars}")
        if EMOJI.search(text):
            fails.append("emoji")
        if "!" in text:
            fails.append("exclamation mark")
        if not re.search(r"[\u0600-\u06FF]", text):
            fails.append("not Arabic")
        plain = strip_tashkeel(text)
        for bad in brand.get("forbidden_on_screen", []):
            if bad and bad in plain:
                fails.append(f"«{bad}»")
        for bad in brand.get("forbidden_dialect", []):
            if re.search(rf"(^|\s){re.escape(bad)}(\s|$)", plain):
                fails.append(f"dialect «{bad}»")
        key = plain[:40]
        if key in seen:
            fails.append(f"duplicate of comment {seen[key]}")
        seen[key] = i
        if i == 1 and not captions.REF_RE.search(strip_tashkeel(plain)):
            fails.append("the pinned sources comment has no reference")
        if words(text) < 4:
            warns.append("very short")
        it["chars"] = len(text)
        it["fails"] = fails
        it["warns"] = warns
    return items


def schedule(items: list[dict], brand: dict, at: str | None) -> list[dict]:
    cfg = brand.get("comments") or {}
    offsets = cfg.get("offsets_minutes") or [0, 20, 150, 150, 300, 1440, 1440]
    window = ((brand.get("posting_windows") or {}).get("instagram") or {}).get("local", "19:00–22:30")
    start = at or window.split("–")[0].strip()
    try:
        hh, mm = [int(x) for x in start.split(":")[:2]]
    except Exception:
        hh, mm = 19, 0
    off = int(brand.get("utc_offset_hours", 3))
    local_tz = timezone(timedelta(hours=off))
    base = datetime.now(local_tz).replace(hour=hh, minute=mm, second=0, microsecond=0)
    for it, delta in zip(items, offsets):
        when = base + timedelta(minutes=int(delta))
        it["at_local"] = when.strftime("%H:%M")
        it["at_utc"] = when.astimezone(timezone.utc).strftime("%H:%M")
        it["day"] = "يوم النشر" if delta < 1440 else "اليوم التالي"
    return items


def write_md(items: list[dict], spec: dict, brand: dict, path: Path) -> None:
    title = (spec.get("scenario") or {}).get("title_fa") or spec.get("title") or spec.get("id", "")
    zone = brand.get("timezone", "Asia/Baghdad")
    lines = [f"# بنك کامنت — {title}", "",
             f"**منطقهٔ زمانی مخاطب:** {zone} · **زمان انتشار:** {items[0]['at_local']} (UTC {items[0]['at_utc']})", "",
             "| # | اسلات | زمان | منطقه | هدف | طول |", "|---|---|---|---|---|---|"]
    for i, it in enumerate(items, 1):
        pin = " 📌" if it.get("pinned") else ""
        lines.append(f"| {i} | {it['kind']}{pin} | {it['at_local']} | {it['day']} | {it['goal']} | {it['chars']} |")
    lines += ["", "> کامنت اول را در لحظهٔ انتشار بگذارید و **پین** کنید.", ""]
    for i, it in enumerate(items, 1):
        lines += [f"## {i} · {it['kind']}" + (" — پین شود" if it.get("pinned") else ""), "",
                  f"`{it['at_local']} {zone} · {it['at_utc']} UTC · {it['chars']} کاراکتر`", "",
                  "```", it["text"], "```", ""]
        for f in it.get("fails") or []:
            lines.append(f"- ✗ {f}")
        for w in it.get("warns") or []:
            lines.append(f"- ⚠ {w}")
        if it.get("fails") or it.get("warns"):
            lines.append("")
    lines += ["## قواعد", "",
              "- هر اسلات یک کامنت؛ تکرار نکنید.",
              "- پاسخ به ده کامنت اول با یک منبع یا یک تعریف، نه با قلب.",
              "- بحث را با لحن پاسخ‌گو ادامه دهید، نه خطابه؛ هیچ‌کس را نام نبرید.",
              "- اگر کامنت توهین‌آمیز بود: پنهان/حذف؛ اگر نقد بود: یک پاسخ مستند و بس.",
              ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--out", default=None)
    ap.add_argument("--brief", default=None)
    ap.add_argument("--series", default=None)
    ap.add_argument("--brand", default=None)
    ap.add_argument("--at", default=None, help="publish time in the audience zone, e.g. 19:30")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    spec = load_json(Path(a.spec))
    if not spec:
        sys.exit(f"cannot read {a.spec}")
    brand = load_json(Path(a.brand) if a.brand else BRAND_PATH, {}) or {}
    brief = load_json(Path(a.brief), {}) if a.brief else {}
    series = load_json(Path(a.series), {}) if a.series else None
    items = schedule(validate(build(spec, brand, brief, series), brand), brand, a.at)
    out = Path(a.out) if a.out else Path(a.spec).parent / "comments.md"
    write_md(items, spec, brand, out)
    (out.parent / "comments.json").write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fails = sum(len(i["fails"]) for i in items)
    warns = sum(len(i["warns"]) for i in items)
    if a.json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
    else:
        print(f"wrote {out} — {len(items)} comments · {fails} fails · {warns} warns")
        for i, it in enumerate(items, 1):
            flag = "📌" if it.get("pinned") else "  "
            print(f"  {flag} {i} {it['at_local']} ({it['day']}) {it['kind']:<22} {it['chars']:3d} chars")
            for f in it["fails"]:
                print("      ✗", f)
    if fails:
        sys.exit(1)


if __name__ == "__main__":
    main()
