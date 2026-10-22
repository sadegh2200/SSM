#!/usr/bin/env python3
"""
new_spec.py — scaffold a spec for one of the narrative archetypes (see references/narrative.md).

    python3 new_spec.py --archetype A --duration 45 --out spec.json [--id slug] [--recitation 9:119]

Archetypes A–F (short form): A سؤال→جواب المعصوم (verse+hadith+grading) · B كلمة واحدة (hadith only)
            C تصحيح مفهوم · D سؤال→جواب (FAQ) · E مناسبة (occasion) · F ردّ شبهة (objection)
Archetypes G–L (long text): G شرحٌ متدرّج · H تعريفٌ ثمّ مقارنة · I خطوات · J خطّ زمني · K مقارنة · L سؤالٌ طويل
Every text field is a placeholder «…» you must replace; delete optional fields you do not need.
`cta.share` is left empty on purpose: fill it with **one** approved ending (`cta.endings` in
config/brand.json) or leave it empty for a heavy text — an empty `share` renders no invitation.
Scene lengths are proportional to --duration; a verse scene is sized later from the recitation length.
"""
import argparse, json, sys
from pathlib import Path

PLANS = {
    "A": [("hook", 3.4, {"lead": "«…»", "line1": "فَمَنْ هُمُ", "line2": "…؟", "sub": "سُورَةُ … · الآيَة …"}),
          ("verse", 9.8, {"label": "﴿ سُورَةُ … — … ﴾", "lines": [["…", "…", "…"], ["…", "…"]], "highlight": {"words": [4, 5]}}),
          ("contrast", 8.4, {"wrong_label": "الأَمْرُ لَيْسَ:", "wrong": "«…»", "right_label": "بَلْ:", "right": "«… <em>…</em> …»", "line3": "…", "line4": "… <em>…</em>"}),
          ("answer", 8.0, {"q1": "سُئِلَ الإمَامُ … عَلَيْهِ السَّلام", "q2": "عَنْ هَذِهِ الآيَة… فَقَالَ:", "hero": "…", "after": "…", "source": "— الإمام … (ع) · … ج… ص…"}),
          ("proof", 9.0, {"seal": ["صَحِيحُ", "السَّنَد"], "cards": [{"book": "…", "loc": "ج… / ص…", "grade": "بِسَنَدٍ صَحِيح"}], "line1": "…", "line2": "…", "attribution": "— العلّامة … · … ج… ص…"}),
          ("cta", 6.4, {"line1": "…", "line2": "… <em>…</em>", "share": "", "final": "…", "brand": {"handle": "@maalsadiqeen"}})],
    "B": [("hook", 3.4, {"lead": "«…»", "lead_font": "amiri", "line1": "مَاذَا تَعْنِي", "line2": "…؟", "sub": "… · ج… ص…"}),
          ("quote", 8.0, {"label": "قَالَ الإمَامُ … عَلَيْهِ السَّلام", "text": "…", "reveal": "words", "attribution": "— … ج… ص…"}),
          ("contrast", 8.5, {"wrong_label": "لَيْسَ المَعْنَى:", "wrong": "…", "right_label": "بَلْ:", "right": "… <em>…</em>", "line3": "…", "line4": "… <em>…</em>"}),
          ("quote", 7.5, {"text": ["…"], "hero": True, "attribution": "— … ج… ص…"}),
          ("proof", 8.0, {"cards": [{"book": "…", "loc": "ج… / ص…", "grade": ""}], "line1": "…", "line2": "…"}),
          ("cta", 6.6, {"line1": "…", "line2": "… <em>…</em>", "share": "", "final": "…", "final_font": "amiri", "brand": {"handle": "@maalsadiqeen"}})],
    "C": [("hook", 3.4, {"line1": "يَظُنُّ كَثِيرُون", "line2": "…", "sub": "وَالنَّصُّ يَقُولُ غَيْرَ ذَلِك"}),
          ("contrast", 9.0, {"wrong_label": "الظَّنُّ:", "wrong": "…", "right_label": "النَّصُّ:", "right": "… <em>…</em>", "line3": "الفَرْقُ: …"}),
          ("quote", 8.0, {"label": "قَالَ … عَلَيْهِ السَّلام", "text": ["…"], "hero": True, "attribution": "— … ج… ص…"}),
          ("list", 7.0, {"title": "مَاذَا يَتَرَتَّبُ عَلَيْه؟", "items": ["…", "…", "…"]}),
          ("proof", 6.6, {"cards": [{"book": "…", "loc": "ج… / ص…", "grade": ""}], "line1": "…"}),
          ("cta", 6.4, {"line1": "…", "line2": "… <em>…</em>", "share": "", "final": "…", "final_font": "amiri", "brand": {"handle": "@maalsadiqeen"}})],
    "D": [("hook", 3.4, {"line1": "سُؤَالٌ يَتَكَرَّر:", "line2": "…؟", "sub": "…"}),
          ("title", 4.0, {"kicker": "الجَوَاب", "title": "…", "sub": "…"}),
          ("list", 10.0, {"title": "…", "items": ["…", "…", "…"], "attribution": "— … ج… ص…"}),
          ("quote", 8.0, {"label": "قَالَ … عَلَيْهِ السَّلام", "text": ["…"], "hero": True, "attribution": "— … ج… ص…"}),
          ("proof", 6.6, {"cards": [{"book": "…", "loc": "ج… / ص…", "grade": ""}], "line1": "…"}),
          ("cta", 6.4, {"line1": "…", "line2": "… <em>…</em>", "share": "", "final": "…", "final_font": "amiri", "brand": {"handle": "@maalsadiqeen"}})],
    "E": [("title", 4.6, {"kicker": "… (التاريخ)", "title": "…", "sub": "…"}),
          ("quote", 10.0, {"label": "قَالَ … عَلَيْهِ السَّلام", "text": "…", "reveal": "words", "attribution": "— … ج… ص…"}),
          ("quote", 8.0, {"text": ["…"], "hero": True}),
          ("cta", 7.4, {"line1": "…", "line2": "… <em>…</em>", "share": "", "final": "…", "final_font": "amiri", "brand": {"handle": "@maalsadiqeen"}})],
    "F": [("hook", 3.6, {"lead": "«…» — يُقَال", "lead_font": "amiri", "line1": "فَهَلْ", "line2": "…؟"}),
          ("contrast", 9.0, {"wrong_label": "الاعْتِرَاض:", "wrong": "…", "right_label": "وَالنَّصُّ:", "right": "… <em>…</em>", "line3": "…", "line4": "… <em>…</em>"}),
          ("quote", 8.5, {"label": "قَالَ … عَلَيْهِ السَّلام", "text": ["…"], "hero": True, "attribution": "— … ج… ص…"}),
          ("proof", 9.0, {"seal": ["صَحِيحُ", "السَّنَد"], "cards": [{"book": "…", "loc": "ج… / ص…", "grade": "…"}], "line1": "…", "line2": "…", "attribution": "— … ج… ص…"}),
          ("list", 7.0, {"title": "النَّتِيجَة", "items": ["…", "…"]}),
          ("cta", 6.9, {"line1": "…", "line2": "… <em>…</em>", "share": "", "final": "…", "brand": {"handle": "@maalsadiqeen"}})],
}


LONG_ARCHETYPES = "GHIJKL"


def long_plan(arch: str) -> list[tuple[str, float, dict]]:
    """G–L reuse the scenario scaffolds so there is one definition of the long-text shapes."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from scenarios import scaffold_scenes          # local import: scenarios imports the brand at runtime
    out = []
    for sc in scaffold_scenes(arch, {}, "maalsadiqeen"):
        d = {k: v for k, v in sc.items() if k not in ("type", "seconds")}
        out.append((sc["type"], float(sc.get("seconds") or 8.0), d))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archetype", required=True, choices=list(PLANS) + list(LONG_ARCHETYPES))
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--id", default="reel")
    ap.add_argument("--recitation", help="surah:ayah when the reel opens on a verse (archetype A/E)")
    a = ap.parse_args()
    plan = PLANS[a.archetype] if a.archetype in PLANS else long_plan(a.archetype)
    base = sum(d for _, d, _ in plan)
    D = a.duration or base
    k = D / base
    scenes, t = [], 0.0
    for i, (typ, d, fields) in enumerate(plan):
        end = round(min(D, t + d * k), 1) if i < len(plan) - 1 else D
        sc = {"id": f"s{i+1}", "type": typ, "start": round(t, 1), "end": end}
        sc.update(fields)
        scenes.append(sc); t = end
    audio = {"mode": "silent", "file": "mix.wav", "bed": {"gain_db": -7}, "auto_sfx": True, "target_lufs": -15.5}
    if a.recitation:
        audio["recitation"] = {"ref": a.recitation, "edition": "ar.mahermuaiqly"}
    spec = {"id": a.id, "title": "…", "duration": D, "brand": {"handle": "maalsadiqeen"}, "audio": audio, "scenes": scenes}
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
    print(f"wrote {a.out}: archetype {a.archetype}, {len(scenes)} scenes, {D}s — replace every «…», then build_reel.py")


if __name__ == "__main__":
    main()
