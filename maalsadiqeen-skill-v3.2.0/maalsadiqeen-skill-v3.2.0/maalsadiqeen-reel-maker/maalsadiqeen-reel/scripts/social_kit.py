#!/usr/bin/env python3
"""
social_kit.py — one command for the whole publishing kit.

    python3 social_kit.py spec.json --out kit/ [--brief brief.json] [--texts captions.json]
                            [--series series.json] [--preset minimal|standard|full]
                            [--publish-at 19:30] [--brand config/brand.json] [--json]

Produces (preset → files):
  minimal   captions/{instagram,facebook,x}.txt · captions.json · alt-text.txt · comments.md
  standard  + publish.md (schedule, cross-post order, 48 h review) · validation.md
  full      + captions.srt (scene-level subtitles) · hooks.md (alt hooks if hooks.json is given)

Exit 0 only when every caption and comment passes its platform rules.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(HERE))
from _common import strip_tashkeel  # noqa: E402
import captions  # noqa: E402
import comments  # noqa: E402
import copy_lint  # noqa: E402

BRAND_PATH = SKILL / "config" / "brand.json"
TAG_RE = re.compile(r"<[^>]+>")


def load_json(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def scene_text(sc: dict) -> str:
    t = sc.get("type")
    if t == "hook":
        return " ".join(str(sc.get(k, "")) for k in ("lead", "line1", "line2")).strip()
    if t == "verse":
        return " ".join(w for line in sc.get("lines") or [] for w in line)
    if t == "quote":
        text = sc.get("text")
        return " ".join(text) if isinstance(text, list) else str(text or "")
    if t == "contrast":
        return str(sc.get("right") or sc.get("wrong") or "")
    if t == "answer":
        return " ".join(str(sc.get(k, "")) for k in ("hero", "after") if sc.get(k))
    if t == "proof":
        return sc.get("attribution") or ""
    if t == "cta":
        return " ".join(str(sc.get(k, "")) for k in ("line1", "line2") if sc.get(k))
    if t == "list":
        return " · ".join(sc.get("items") or [])
    if t == "title":
        return str(sc.get("title") or "")
    if t == "paragraph":
        return " ".join(str(x) for x in (sc.get("text") if isinstance(sc.get("text"), list) else [sc.get("text") or ""]) if x)
    if t == "definition":
        body = sc.get("body")
        body = " ".join(body) if isinstance(body, list) else str(body or "")
        return f"{sc.get('term', '')} — {body}".strip(" —")
    if t == "qa":
        ans = sc.get("answer")
        ans = " ".join(ans) if isinstance(ans, list) else str(ans or "")
        return f"{sc.get('question', '')} {ans}".strip()
    if t in ("steps", "timeline"):
        key = "items" if t == "steps" else "events"
        bits = []
        for x in sc.get(key) or []:
            if isinstance(x, dict):
                bits.append(" ".join(str(x.get(k, "")) for k in ("head", "when", "text") if x.get(k)))
            else:
                bits.append(str(x))
        return " · ".join(bits)
    if t == "compare":
        bits = []
        for key in ("col_a", "col_b"):
            c = sc.get(key) or {}
            bits.append(str(c.get("head", "")))
            bits += [str(x) for x in c.get("points") or []]
        return " · ".join(x for x in bits if x) + (f" — {sc['verdict']}" if sc.get("verdict") else "")
    return ""


def srt_from_spec(spec: dict) -> str:
    def ts(sec: float) -> str:
        ms = int(round(sec * 1000))
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    blocks, n = [], 0
    for sc in spec.get("scenes") or []:
        text = re.sub(r"\s+", " ", TAG_RE.sub("", scene_text(sc))).strip()
        if not text:
            continue
        n += 1
        blocks.append(f"{n}\n{ts(float(sc['start']))} --> {ts(float(sc['end']))}\n{text}\n")
    return "\n".join(blocks)


def publish_md(spec: dict, brand: dict, brief: dict, comp: dict, items: list[dict], hooks: list | None) -> str:
    windows = brand.get("posting_windows") or {}
    order = brand.get("cross_post_order") or ["instagram", "facebook", "x"]
    cadence = brand.get("cadence") or {}
    zone = brand.get("timezone", "Asia/Baghdad")
    title = (spec.get("scenario") or {}).get("title_fa") or spec.get("title") or spec.get("id", "")
    lines = [f"# برنامهٔ انتشار — {title}", "",
             f"**زمان انتشار (پیشنهادی):** {items[0]['at_local']} به وقت {zone} · {items[0]['at_utc']} UTC",
             f"**ترتیب کراس‌پست:** {' → '.join(order)}",
             f"**ریتم:** {cadence.get('reels_per_week', 3)} ریل در هفته · حداقل "
             f"{cadence.get('min_days_between_ab', 3)} روز فاصله برای A/B", "",
             "## پنجرهٔ هر پلتفرم", "", "| پلتفرم | پنجرهٔ محلی | روزها | متریک اصلی |", "|---|---|---|---|"]
    for p in order:
        w = windows.get(p) or {}
        lines.append(f"| {p} | {w.get('local', '—')} | {'، '.join(w.get('best_days') or [])} | "
                     f"{'، '.join(w.get('metrics') or [])} |")
    lines += ["", "## چک‌لیست ۶۰ دقیقهٔ اول", "",
              "- [ ] کامنت منابع را همان لحظه بگذارید و پین کنید (`comments.md`، اسلات ۱).",
              "- [ ] ریل را در استوری با دعوت «أرسِل لمن…» بازنشر کنید.",
              "- [ ] به ده کامنت اول با یک منبع یا تعریف پاسخ دهید.",
              "- [ ] کاور/فریم اول را در گرید چک کنید (متن داخل کراپ ۴:۵).",
              "- [ ] متن سه پلتفرم را از `captions/` کپی کنید — هیچ‌کدام را دوباره استفاده نکنید.",
              "- [ ] لینک (اگر هست) فقط در بایو / اولین کامنت / پاسخ X.",
              ""]
    lines += ["## بازبینی ۴۸ ساعته", "",
              "| نشانه | معنا | اقدام |", "|---|---|---|",
              "| تماشای میانگین < ۴۰٪ | مشکل هوک | فقط صحنهٔ اول را عوض کنید (هوک B) |",
              "| تماشا خوب، sends کم | جملهٔ پایانی قابل ارسال نیست | hero/CTA را بازنویسی کنید |",
              "| sends خوب، فالو کم | کارت برند کوتاه یا نامشخص | کارت برند ≥ ۱٫۵ ثانیه و کاور را چک کنید |",
              "| افت در میانه | یک صحنه طولانی است | همان صحنه را ۱ ثانیه کوتاه کنید |",
              "| کامنت‌ها روی سند | سند به‌اندازهٔ کافی دیده نشده | کارت سند را یک ثانیه زودتر بیاورید |",
              "", "متریک‌ها را از **Insights بومی** بخوانید، نه از حدس. «بازدید» به‌تنهایی تصمیمی نمی‌سازد.", ""]
    if hooks:
        lines += ["## هوک‌های جایگزین (A/B)", ""]
        for i, h in enumerate(hooks[:5], 1):
            if isinstance(h, dict):
                lines.append(f"{i}. [{h.get('score', '?')}] {h.get('hook', '')}")
            else:
                lines.append(f"{i}. {h}")
        lines.append("")
    if comp.get("hashtags"):
        lines += ["## هشتگ‌ها", "",
                  f"- اینستاگرام: {' '.join(comp['hashtags']['instagram'])}",
                  f"- فیس‌بوک: {' '.join(comp['hashtags']['facebook']) or '—'}",
                  f"- X: {' '.join(comp['hashtags']['x']) or '—'}", ""]
    lines += ["> قواعد کامل: `references/platforms.md` و `references/comments.md`.", ""]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--out", default="kit")
    ap.add_argument("--brief", default=None)
    ap.add_argument("--texts", default=None)
    ap.add_argument("--series", default=None)
    ap.add_argument("--hooks", default=None)
    ap.add_argument("--preset", choices=["minimal", "standard", "full"], default=None)
    ap.add_argument("--publish-at", default=None)
    ap.add_argument("--brand", default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    spec = load_json(Path(a.spec))
    if not spec:
        sys.exit(f"cannot read {a.spec}")
    brand = load_json(Path(a.brand) if a.brand else BRAND_PATH, {}) or {}
    preset = a.preset or (brand.get("defaults") or {}).get("preset", "standard")
    brief = load_json(Path(a.brief), {}) if a.brief else {}
    series = load_json(Path(a.series), {}) if a.series else None
    texts = load_json(Path(a.texts), {}) if a.texts else None
    hooks = load_json(Path(a.hooks), []) if a.hooks else None

    out = Path(a.out)
    if not out.is_absolute():
        out = Path(a.spec).parent / out
    out.mkdir(parents=True, exist_ok=True)

    report = captions.write_kit(spec, brand, brief or {}, out / "captions", texts)
    comp = captions.compose(spec, brand, brief or {})
    items = comments.schedule(comments.validate(comments.build(spec, brand, brief or {}, series), brand),
                              brand, a.publish_at)
    comments.write_md(items, spec, brand, out / "comments.md")
    (out / "comments.json").write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lint = copy_lint.lint_spec(spec, brand)
    report["copy_lint"] = {"fails": lint.fails, "warns": lint.warns}
    report["comments"] = {"items": len(items),
                          "fails": [f"#{i + 1} {e}" for i, it in enumerate(items) for e in it["fails"]],
                          "warns": [f"#{i + 1} {e}" for i, it in enumerate(items) for e in it["warns"]]}
    if preset in ("standard", "full"):
        (out / "publish.md").write_text(publish_md(spec, brand, brief or {}, comp, items, hooks), encoding="utf-8")
    if preset == "full":
        (out / "captions.srt").write_text(srt_from_spec(spec), encoding="utf-8")
        if hooks:
            md = ["# هوک‌های جایگزین", ""]
            for i, h in enumerate(hooks[:8], 1):
                md.append(f"{i}. [{h.get('score', '?')}] {h.get('hook', '')}" if isinstance(h, dict) else f"{i}. {h}")
            (out / "hooks.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    ok = report["ok"] and not report["copy_lint"]["fails"] and not report["comments"]["fails"]
    vmd = [f"# اعتبارسنجی کیت — {'سبز' if ok else 'قرمز'}", "",
           f"**preset:** {preset}", "",
           "| بخش | نتیجه |", "|---|---|",
           f"| کپشن‌ها | {'✓' if report['ok'] else '✗'} |",
           f"| کپی روی صفحه | {len(report['copy_lint']['fails'])} خطا · {len(report['copy_lint']['warns'])} هشدار |",
           f"| کامنت‌ها | {len(report['comments']['fails'])} خطا · {len(report['comments']['warns'])} هشدار |", ""]
    for name, chk in report["checks"].items():
        vmd.append(f"## {name}")
        rows = [f"- ✗ {x}" for x in chk["fails"]] + [f"- ⚠ {x}" for x in chk["warns"]]
        vmd += rows or [f"- ✓ {report['files'].get(name, {}).get('chars', '')} chars, "
                        f"{report['files'].get(name, {}).get('hashtags', '')} tags"]
        vmd.append("")
    (out / "validation.md").write_text("\n".join(vmd), encoding="utf-8")

    files = sorted(str(p.relative_to(out)) for p in out.rglob("*") if p.is_file())
    if a.json:
        print(json.dumps({"ok": ok, "preset": preset, "files": files, "report": report}, ensure_ascii=False, indent=2))
    else:
        for f in files:
            print("  •", out / f)
        print(f"kit {'OK' if ok else 'HAS ERRORS'} · preset {preset}")
        for x in report["copy_lint"]["fails"]:
            print("  ✗ copy:", x["where"], x["msg"])
        for x in report["comments"]["fails"]:
            print("  ✗ comment:", x)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
