#!/usr/bin/env python3
"""
preview_frames.py — three still frames per scenario, so the user can choose by eye before any render.

    python3 preview_frames.py scenarios.json --out preview/ [--brand config/brand.json] [--html preview.html]

Two backends, chosen automatically:
  • JPEGs (540×960) when Pillow + libraqm are available — shaped Arabic, brand fonts;
  • otherwise one self-contained `preview.html` (brand CSS, absolute font paths) that any browser opens.

The frames are: (a) the hook, (b) the hero line, (c) the proof or the take-away. They are a design
decision aid, not a render — no motion, no audio.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
BRAND_DEFAULT = SKILL / "config" / "brand.json"


def load_brand(path: str | None) -> dict:
    p = Path(path) if path else BRAND_DEFAULT
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def clean(s: str) -> str:
    import re
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def frames_for(sc: dict) -> list[dict]:
    """Return up to three frames for a scenario: hook, hero, proof/cta."""
    scenes = sc.get("scenes") or []
    out: list[dict] = []
    hook = next((s for s in scenes if s.get("type") == "hook"), None)
    if hook:
        lines = [clean(hook.get(k, "")) for k in ("lead", "line1", "line2")]
        lines = [x for x in lines if x]
        out.append({"kind": "hook", "label": "HOOK · 0–3 s", "lines": lines,
                    "sub": clean(hook.get("sub", "")), "hero": False})
    hero = None
    for s in scenes:
        if s.get("type") == "answer" and s.get("hero"):
            hero = {"kind": "hero", "label": "HERO · the answer", "lines": [clean(s["hero"])],
                    "sub": clean(s.get("source", "")), "hero": True}
            break
        if s.get("type") == "quote" and s.get("hero"):
            text = s.get("text")
            lines = [clean(x) for x in (text if isinstance(text, list) else [text or ""])]
            hero = {"kind": "hero", "label": "HERO · the text", "lines": lines,
                    "sub": clean(s.get("attribution", "")), "hero": True}
            break
        if s.get("type") == "qa" and not hero:
            ans = s.get("answer")
            ans = [clean(x) for x in (ans if isinstance(ans, list) else [ans or ""]) if x]
            hero = {"kind": "hero", "label": "ANSWER · the reply", "lines": [clean(s.get("question", ""))] + ans[:2],
                    "sub": clean(s.get("source", "")), "hero": True}
            break
        if s.get("type") == "definition" and not hero:
            body = s.get("body")
            body = [clean(x) for x in (body if isinstance(body, list) else [body or ""]) if x]
            hero = {"kind": "definition", "label": "DEFINITION · the term", "lines": [clean(s.get("term", ""))] + body[:2],
                    "sub": clean(s.get("note", "")), "hero": True}
            break
        if s.get("type") == "compare" and not hero:
            a, b = s.get("col_a") or {}, s.get("col_b") or {}
            hero = {"kind": "compare", "label": "COMPARE · two readings",
                    "lines": [clean(a.get("head", "")), clean(b.get("head", "")), clean(s.get("verdict", ""))],
                    "sub": clean(s.get("title", "")), "hero": False}
            break
        if s.get("type") in ("paragraph", "steps", "timeline") and not hero:
            key = {"paragraph": "text", "steps": "items", "timeline": "events"}[s["type"]]
            v = s.get(key)
            lines = [clean(x) for x in (v if isinstance(v, list) else [v or ""]) if x]
            hero = {"kind": "prose", "label": s["type"].upper(), "lines": lines[:2],
                    "sub": clean(s.get("kicker", "") or s.get("title", "")), "hero": False}
            break
        if s.get("type") == "contrast" and not hero:
            hero = {"kind": "contrast", "label": "TURN · not X, but Y",
                    "lines": [clean(s.get("wrong", "")), clean(s.get("right", ""))],
                    "sub": clean(s.get("line3", "")), "hero": False}
    if hero:
        out.append(hero)
    proof = next((s for s in scenes if s.get("type") == "proof"), None)
    cta = next((s for s in scenes if s.get("type") == "cta"), None)
    if proof:
        cards = proof.get("cards") or []
        lines = [clean(" · ".join(x for x in (c.get("book", ""), c.get("loc", "")) if x)) for c in cards[:2]]
        if proof.get("seal"):
            lines.insert(0, clean(" ".join(proof["seal"])))
        out.append({"kind": "proof", "label": "PROOF · the reference", "lines": lines or ["—"],
                    "sub": clean(proof.get("attribution", "")), "hero": False})
    elif cta:
        out.append({"kind": "cta", "label": "CLOSE · take-away", "lines": [clean(cta.get(k, "")) for k in ("line1", "line2") if cta.get(k)],
                    "sub": clean(cta.get("share", "")), "hero": False})
    return out[:3]


# ----------------------------------------------------------------------------- HTML backend
def _theme_tokens(brand: dict, theme: str | None = None) -> dict:
    """The palette the preview should be drawn in — the same tokens build_reel.py uses."""
    themes = (brand or {}).get("themes") or {}
    name = theme or ((brand or {}).get("defaults") or {}).get("theme") or "main"
    entry = themes.get(name) or {}
    return dict(entry.get("tokens") or {}, label=entry.get("label_fa") or name)


def write_html(scenarios: list[dict], path: Path, brand: dict | None = None, title: str = "Preview",
               theme: str | None = None) -> Path:
    brand = brand or {}
    tk = _theme_tokens(brand, theme)
    vars_ = " ".join(f"--{k.replace('_', '-')}:{tk[k]};" for k in (
        "paper", "paper2", "green", "green2", "gold", "gold2", "ink", "ink2", "line",
        "body_bg", "paper_hi", "paper_mid", "panel_bg", "panel_line") if k in tk)
    if "body_bg" not in tk:
        vars_ += "--body-bg:#d9d2c5;--panel-bg:#f7f3ea;--panel-line:#c9c0b0;"
    fonts = SKILL / "assets" / "fonts"
    faces = []
    for name, file in (("Amiri", "Amiri-Regular.ttf"), ("AmiriB", "Amiri-Bold.ttf"),
                       ("AmiriQuran", "AmiriQuran.ttf"), ("Kufi", "NotoKufiArabic-Bold.ttf"),
                       ("KufiR", "NotoKufiArabic-Regular.ttf"), ("Naskh", "NotoNaskhArabic-Regular.ttf")):
        faces.append(f"@font-face{{font-family:'{name}';src:url('file://{(fonts / file).as_posix()}');}}")
    cards = []
    for sc in scenarios:
        meta = f"<div class='meta'><span class='id'>#{sc.get('id')}</span>{html.escape(str(sc.get('angle', '')))} · {html.escape(str(sc.get('archetype', '')))}"
        if sc.get("total_score") is not None:
            meta += f" · <b>{sc['total_score']}/100</b>"
        meta += f"<br><span class='hook'>{html.escape(clean((sc.get('hook') or {}).get('text', '')))}</span></div>"
        frames = []
        for f in frames_for(sc):
            body = "".join(f"<p class='{'hero' if f['hero'] and i == len(f['lines']) - 1 else 'line'}'>{html.escape(x)}</p>"
                           for i, x in enumerate(f["lines"]))
            frames.append(f"<figure class='frame {f['kind']}'><figcaption>{html.escape(f['label'])}</figcaption>"
                          f"<div class='paper'><div class='arc'></div>{body}"
                          f"<p class='sub'>{html.escape(f['sub'])}</p>"
                          f"<div class='wm'>maalsadiqeen</div></div></figure>")
        life = clean(sc.get("life_impact", ""))
        cards.append(f"<section class='sc'>{meta}<div class='frames'>{''.join(frames)}</div>"
                     + (f"<p class='life'>الأثر في الحياة: {html.escape(life)}</p>" if life else "")
                     + f"<p class='why'>{html.escape(str(sc.get('why_fa', '')))}</p></section>")
    doc = f"""<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
<title>{html.escape(title)}</title><style>
{''.join(faces)}
:root{{--paper:#ece6da;--green:#1f4a35;--gold:#957238;--ink:#2d2b27;--ink2:#5a5650;--line:#8aa58f;{vars_}}}
*{{box-sizing:border-box}}body{{margin:24px;background:var(--body-bg);color:var(--ink);
font-family:'Naskh',serif;direction:rtl}}h1{{font-family:'Kufi',sans-serif;font-size:22px;margin:0 0 18px}}
.sc{{background:var(--panel-bg);border:1px solid var(--panel-line);border-radius:10px;padding:14px 16px;margin:0 0 20px}}
.meta{{font-size:13px;color:var(--ink2);margin-bottom:10px}}.meta .id{{background:var(--green);color:#fff;
border-radius:4px;padding:1px 8px;margin-inline-end:8px}}.meta .hook{{font-family:'Amiri',serif;font-size:16px;color:var(--green)}}
.frames{{display:flex;gap:14px;flex-wrap:wrap}}.frame{{margin:0;width:190px}}
.frame figcaption{{font-family:'KufiR',sans-serif;font-size:10px;color:var(--gold);letter-spacing:.06em;margin-bottom:4px}}
.paper{{position:relative;aspect-ratio:9/16;background:radial-gradient(circle at 50% 42%,var(--paper-hi,#f4efe6),var(--paper-mid,#ebe4d7) 60%,var(--paper-lo,#ddd4c3));
border:1px solid var(--panel-line,#cfc5b2);border-radius:6px;padding:26px 16px 34px;display:flex;flex-direction:column;
justify-content:center;align-items:center;text-align:center;overflow:hidden}}
.paper .arc{{position:absolute;top:14px;left:50%;transform:translateX(-50%);width:120px;height:12px;
border-top:1px solid var(--line);border-radius:50%;opacity:.7}}
.line{{font-family:'Amiri',serif;font-size:15px;line-height:1.7;color:var(--green);margin:2px 0}}
.hero{{font-family:'AmiriB',serif;font-size:17px;line-height:1.6;color:var(--green);margin:4px 0;
border-bottom:2px solid rgba(149,114,56,.55);padding-bottom:3px}}
.sub{{font-family:'Naskh',serif;font-size:9px;color:var(--ink2);margin-top:8px}}
.proof .line{{font-family:'Kufi',sans-serif;font-size:12px;color:var(--green)}}
.cta .hero{{color:var(--green)}}.wm{{position:absolute;bottom:10px;left:0;right:0;text-align:center;
font-family:'KufiR',sans-serif;font-size:8px;color:var(--ink2,#8b8377);letter-spacing:.08em}}
.why{{font-size:12px;color:var(--ink2);margin:10px 0 0;line-height:1.7}}
.life{{font-size:13px;color:var(--green);margin:10px 0 0;line-height:1.7;border-inline-start:2px solid var(--gold,#957238);padding-inline-start:8px}}
</style></head><body><h1>{html.escape(title)}</h1>{''.join(cards)}</body></html>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc, encoding="utf-8")
    return path


# ----------------------------------------------------------------------------- Pillow backend
def _pil_ready() -> bool:
    try:
        from PIL import ImageFont, features
        return bool(features.check("raqm"))
    except Exception:
        return False


def write_jpgs(scenarios: list[dict], outdir: Path, brand: dict | None = None) -> int:
    """Render 3 JPEGs per scenario. Returns the number of files written (0 when Pillow/raqm is absent)."""
    if not _pil_ready():
        return 0
    from PIL import Image, ImageDraw, ImageFont  # noqa: PLC0415

    W, H = 540, 960
    paper, green, gold, ink2 = (236, 230, 218), (31, 74, 53), (149, 114, 56), (90, 86, 80)
    f_hero = ImageFont.truetype(str(SKILL / "assets/fonts/Amiri-Bold.ttf"), 44)
    f_line = ImageFont.truetype(str(SKILL / "assets/fonts/Amiri-Regular.ttf"), 34)
    f_sub = ImageFont.truetype(str(SKILL / "assets/fonts/NotoNaskhArabic-Regular.ttf"), 20)
    f_lab = ImageFont.truetype(str(SKILL / "assets/fonts/NotoKufiArabic-Regular.ttf"), 16)
    outdir.mkdir(parents=True, exist_ok=True)
    n = 0
    for sc in scenarios:
        for i, f in enumerate(frames_for(sc), 1):
            img = Image.new("RGB", (W, H), paper)
            d = ImageDraw.Draw(img)
            d.rectangle([0, 0, W - 1, H - 1], outline=(207, 197, 178))
            d.line([W * 0.25, 60, W * 0.75, 60], fill=(138, 165, 143), width=1)
            d.text((W - 24, 34), f["label"], font=f_lab, fill=gold, anchor="ra")
            y = 240
            for j, line in enumerate(f["lines"]):
                font = f_hero if (f["hero"] and j == len(f["lines"]) - 1) else f_line
                d.multiline_text((W / 2, y), line, font=font, fill=green, anchor="ma", spacing=10,
                                 align="center", direction="rtl")
                y += (58 if font is f_hero else 48)
            if f["sub"]:
                d.text((W / 2, min(y + 30, H - 180)), f["sub"], font=f_sub, fill=ink2, anchor="ma", direction="rtl")
            d.text((W / 2, H - 44), "maalsadiqeen", font=f_lab, fill=(139, 131, 119), anchor="mm")
            img.save(outdir / f"sc{sc.get('id')}-{i}.jpg", quality=88)
            n += 1
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scenarios")
    ap.add_argument("--out", default="preview")
    ap.add_argument("--brand", default=None)
    ap.add_argument("--html", default=None, help="also write a self-contained HTML preview here")
    ap.add_argument("--theme", default=None, help="main · mourning (default: config/brand.json)")
    a = ap.parse_args()
    data = json.loads(Path(a.scenarios).read_text(encoding="utf-8"))
    scenarios = data.get("scenarios", data if isinstance(data, list) else [])
    brand = load_brand(a.brand)
    outdir = Path(a.out)
    n = write_jpgs(scenarios, outdir, brand)
    if n:
        print(f"wrote {n} JPEG frames → {outdir}")
    else:
        print("Pillow+raqm unavailable — JPEG preview skipped")
    path = Path(a.html) if a.html else outdir.parent / "preview.html"
    write_html(scenarios, path, brand, title="مع الصادقين — scenario preview", theme=a.theme)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
