#!/usr/bin/env python3
"""
captions.py — three native captions (Instagram · Facebook · X), composed and then validated.

    python3 captions.py spec.json --out captions/ [--texts captions.json] [--brief brief.json]
                                  [--brand config/brand.json] [--json] [--strict]

The default composer writes a *valid* caption from the spec (hook, sacred text, source, meaning,
life-impact, CTA, hashtags). For better prose, write `--texts captions.json`:

    {"instagram": "…", "facebook": "…", "x": "…",
     "x_thread": ["…", "…", "…"], "alt_text": "…"}

Every caption is validated against config/brand.json (§ platform limits): length, hashtag count,
links in the body, emoji, forbidden wording/CTA, reference present, fold line complete.
Exit 1 on a violation unless --sloppy.
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
from _common import EMOJI, strip_tashkeel, words  # noqa: E402

BRAND_PATH = SKILL / "config" / "brand.json"
TAG_RE = re.compile(r"<[^>]+>")
HASHTAG_RE = re.compile(r"#[\w\u0600-\u06FF_]+")
LINK_RE = re.compile(r"https?://|www\.|\bt\.me\b|instagram\.com|facebook\.com|x\.com", re.I)
REF_RE = re.compile(r"(ج\s*[٠-٩0-9]+|ص\s*[٠-٩0-9]+|الجزء|الصفحة|مادة|باب|الخطبة|الحكمة"
                      r"|حديث\s*(رقم\s*)?[٠-٩0-9]+"
                      r"|الكافي|نهج البلاغة|بحار|وسائل|التهذيب|من لا يحضره|تفسير|مجمع البيان"
                      r"|الميزان|ميزان الحكمة|غرر الحكم|لسان العرب|المفردات|مفردات|الصحاح"
                      r"|الخصال|التوحيد|معاني الأخبار|عيون أخبار|كمال الدين|الإرشاد|الاحتجاج"
                      r"|سورة|الآية|آية\s*[٠-٩]+)")
ALLOWED_LATIN = re.compile(r"@?maalsadiqeen|URL|IG|FB", re.I)


def load_json(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub("", s or "")).strip()


def scene(spec: dict, kind: str, **match) -> dict | None:
    for s in spec.get("scenes") or []:
        if s.get("type") != kind:
            continue
        if all(s.get(k) == v for k, v in match.items()):
            return s
    return None


def pick_hashtags(text: str, brand: dict, platform: str) -> list[str]:
    cfg = brand.get("hashtags") or {}
    tags = list(cfg.get("core") or ["#مع_الصادقين", "#معارف_أهل_البيت"])
    plain = strip_tashkeel(text)
    def hit(key: str) -> bool:
        stem = strip_tashkeel(key)
        return re.search(rf"(?<![\u0600-\u06FF]){re.escape(stem)}(?![\u0600-\u06FF])", plain) is not None

    for key, tag in (cfg.get("topic") or {}).items():
        if hit(key) and tag not in tags:
            tags.append(tag)
    for key, tag in (cfg.get("imam") or {}).items():
        if hit(key) and tag not in tags:
            tags.append(tag)
    if platform == "instagram":
        # a verse implies تفسير, a card implies سند — both are true of the content, not filler
        if "#تفسير_القرآن" in (cfg.get("topic") or {}).values() and not any(
                x in tags for x in (cfg.get("topic") or {}).values()):
            tags.append(cfg["topic"].get("تفسير", "#تفسير_القرآن"))
        if len(tags) < 3 and "#رجال_الحديث" in (cfg.get("topic") or {}).values():
            tags.append(cfg["topic"]["سند"])
    lim = (cfg.get("limits") or {}).get(platform) or [0, 2]
    lo, hi = lim
    if len(tags) > hi:
        tags = tags[:hi]
    return tags


def spec_facts(spec: dict, brief: dict) -> dict:
    scenes = spec.get("scenes") or []
    hook = next((s for s in scenes if s.get("type") == "hook"), {})
    hook_line = " ".join(clean(hook.get(k, "")) for k in ("lead", "line1", "line2") if hook.get(k))
    verse = next((s for s in scenes if s.get("type") == "verse"), None)
    quote = next((s for s in scenes if s.get("type") == "quote"), None)
    answer = next((s for s in scenes if s.get("type") == "answer"), None)
    contrast = next((s for s in scenes if s.get("type") == "contrast"), None)
    proof = next((s for s in scenes if s.get("type") == "proof"), None)
    cta = next((s for s in scenes if s.get("type") == "cta"), {})

    sacred, sacred_label, source = "", "", ""
    if verse:
        sacred = " ".join(w for line in verse.get("lines") or [] for w in line)
        sacred_label = clean(verse.get("label", ""))
        # a verse carries its own reference in the label («سورة البقرة — ١٥٦»): never leave it unreferenced
        source = clean(verse.get("source") or sacred_label)
    elif quote:
        text = quote.get("text")
        sacred = " ".join(text) if isinstance(text, list) else clean(text)
        sacred_label = clean(quote.get("label", ""))
        source = clean(quote.get("attribution", ""))
    if proof:
        cards = proof.get("cards") or []
        bits = []
        for c in cards[:2]:
            ref = " ".join(x for x in (clean(c.get("book", "")), clean(c.get("loc", ""))) if x)
            if c.get("grade"):
                ref += f" ({clean(c['grade'])})"
            bits.append(ref)
        source = "؛ ".join(b for b in bits if b) or source
        if proof.get("attribution") and not source:
            source = clean(proof["attribution"])
    if answer and answer.get("source") and not source:
        source = clean(answer["source"]).lstrip("— ").strip()

    qa = next((s for s in scenes if s.get("type") == "qa"), None)
    para = next((s for s in scenes if s.get("type") == "paragraph"), None)
    definition = next((s for s in scenes if s.get("type") == "definition"), None)
    if not source:
        for s in (qa, para, definition):
            if s and s.get("source"):
                source = clean(s["source"]).lstrip("— ").strip()
                break

    meaning = ""
    if answer:
        meaning = " ".join(clean(answer.get(k, "")) for k in ("hero", "after") if answer.get(k))
    if not meaning and contrast:
        meaning = clean(contrast.get("right", "")) + ((" — " + clean(contrast.get("line3", ""))) if contrast.get("line3") else "")
    if not meaning and quote and quote.get("hero"):
        text = quote.get("text")
        meaning = " ".join(text) if isinstance(text, list) else clean(text)
    if not meaning and qa:
        ans = qa.get("answer")
        meaning = " ".join(clean(x) for x in (ans if isinstance(ans, list) else [ans or ""]) if x)
    if not meaning and definition:
        body = definition.get("body")
        body = " ".join(str(x) for x in body) if isinstance(body, list) else str(body or "")
        meaning = (clean(definition.get("term", "")) + " — " + clean(body)).strip(" —")
    if not meaning and para:
        txt = para.get("text")
        meaning = " ".join(clean(x) for x in (txt if isinstance(txt, list) else [txt or ""]) if x)
    if not meaning:
        meaning = brief.get("one_idea") or ""

    life = spec.get("life_impact") or brief.get("life_impact") or ""
    if not life:
        for s in scenes:
            if s.get("type") == "list" and "الأثر" in clean(s.get("title", "")):
                life = " · ".join(clean(x) for x in s.get("items") or [])
                break

    share = clean(cta.get("share", ""))          # empty = this reel ends without an invitation
    wrong = clean(contrast.get("wrong", "")) if contrast else ""
    right = clean(contrast.get("right", "")) if contrast else ""
    attribution = clean(proof.get("attribution", "")) if proof else ""
    return {"wrong": wrong, "right": right, "attribution": attribution,
            "hook": hook_line, "verse": sacred, "verse_label": sacred_label, "source": source,
            "meaning": meaning, "life": life, "share": share,
            "final": clean(cta.get("final", "")), "handle": (cta.get("brand") or {}).get("handle") or "@maalsadiqeen"}


def brand_cta(brief: dict) -> list[str]:
    return ["أَرْسِلْهَا لِمَنْ تُحِبّ"]



def meaning_paragraph(f: dict, long_form: bool = False) -> str:
    """The «شرح» layer as prose: what the words say, then what they do not say."""
    body = f.get("meaning") or ""
    wrong = f.get("wrong") or ""
    if wrong and not long_form:
        body = f"{body}. وليس الأمر {wrong}" if body and not body.endswith(".") else (body or f"وليس الأمر {wrong}")
    return body.strip()


def pick_x_lead(f: dict) -> str:
    """X opens with one complete claim, short enough to survive the timeline."""
    cands = [f.get("x_lead") or "", f.get("right") or "", f.get("meaning") or "", f.get("hook") or ""]
    for c in cands:
        c = clean(c)
        if c and len(c) <= 58:
            return c
    return clean(cands[-1])


def pick_question(brand: dict, platform: str, spec: dict) -> str:
    qs = (brand.get("questions") or {}).get(platform) or []
    if not qs:
        return ""
    idx = int((spec.get("scenario") or {}).get("id") or 1)
    return qs[(idx - 1) % len(qs)]


def lengthen(text: str, f: dict, brand: dict, platform: str, tags: list[str]) -> str:
    """If the prose is under the platform's floor, add the block that carries the most meaning:
    the contrast (what it is / what it is not), then the second half of the source card."""
    limits = ((brand.get("limits") or {}).get(platform) or {}).get("target") or [0, 10**9]
    lo = limits[0]
    if len(text) >= lo:
        return text
    add = []
    if f.get("wrong"):
        add.append(f"ليس {f['wrong']}، بل {f.get('right') or f['meaning']}.")
    if f.get("attribution"):
        add.append(f["attribution"])
    if not add:
        return text
    lines = text.split("\n")
    # insert after the meaning paragraph (index 2–4) so the caption still opens with the hook
    at = min(6, len(lines))
    out = lines[:at] + [""] + add + lines[at:]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def compose(spec: dict, brand: dict, brief: dict | None = None) -> dict:
    brief = brief or {}
    f = spec_facts(spec, brief)
    hashtags_src = " ".join([f["hook"], f["verse"], f["meaning"], f["source"]])
    ig_tags = pick_hashtags(hashtags_src, brand, "instagram")
    fb_tags = pick_hashtags(hashtags_src, brand, "facebook")
    x_tags = pick_hashtags(hashtags_src, brand, "x")
    texts_cfg = brief.get("texts") or {}

    # ---- Instagram: hook → sacred + reference → meaning → life → question → CTA → tags
    ig = [f["hook"], ""]
    if f["verse"]:
        ig += ["﴿" + f["verse"] + "﴾", (f["verse_label"] or ""), ""]
    if f["source"]:
        ig += ["المصدر: " + f["source"], ""]
    if f["meaning"]:
        ig += [meaning_paragraph(f), ""]
    if f["life"]:
        ig += ["الأثر في الحياة:", f["life"], ""]
    q_ig = pick_question(brand, "instagram", spec)
    if q_ig and not ig[-1].endswith("؟"):
        ig += [q_ig, ""]
    # one closing line only: the reel's own invitation, or the quiet save if it ends without one
    ig += [(f["share"] or "احْفَظْهَا لِلْعَوْدَةِ"), "", " ".join(ig_tags)]
    instagram = "\n".join(ig).strip()
    instagram = lengthen(instagram, f, brand, "instagram", ig_tags)

    # ---- Facebook: hook → context → sacred + source → life → question → tags
    fb = [f["hook"], ""]
    if f["meaning"]:
        fb += [meaning_paragraph(f, long_form=True), ""]
    if f["verse"]:
        fb += ["﴿" + f["verse"] + "﴾" + (f" — {f['source']}" if f["source"] else ""), ""]
    elif f["source"]:
        fb += ["المصدر: " + f["source"], ""]
    if f["life"]:
        fb += ["الأثر في الحياة:", f["life"], ""]
    q_fb = pick_question(brand, "facebook", spec)
    if q_fb:
        fb += [q_fb]
    if fb_tags:
        fb += ["", " ".join(fb_tags)]
    facebook = re.sub(r"\n{3,}", "\n\n", "\n".join(fb)).strip()
    facebook = lengthen(facebook, f, brand, "facebook", fb_tags)

    # ---- X: a ≤60-char claim → the text → the meaning → the reference (hard 250)
    lead = shorten(pick_x_lead(f), 58)
    verse_bit = ("﴿" + shorten(f["verse"], 110) + "﴾") if f["verse"] else shorten(f["hook"], 100)
    meaning_bit = shorten(f["meaning"], 70)
    source_bit = shorten(f["source"], 55)
    x_lines = [x for x in [lead, "", verse_bit, ("— " + meaning_bit) if meaning_bit else "", source_bit] if x is not None]
    text_x = "\n".join(x_lines).strip()
    if len(text_x) > 250:  # drop the gloss first, then trim the verse
        x_lines = [x for x in [lead, verse_bit, source_bit] if x]
        text_x = "\n".join(x_lines).strip()
    if len(text_x) > 250:
        text_x = shorten(text_x, 247)

    alt = f"ريل عمودي من «مع الصادقين»: {shorten(f['hook'], 80)}" + (f" — {shorten(f['source'], 40)}" if f["source"] else "")

    return {
        "instagram": texts_cfg.get("instagram") or instagram,
        "facebook": texts_cfg.get("facebook") or facebook,
        "x": texts_cfg.get("x") or text_x,
        "x_thread": texts_cfg.get("x_thread") or [],
        "alt_text": texts_cfg.get("alt_text") or alt,
        "hashtags": {"instagram": ig_tags, "facebook": fb_tags, "x": x_tags},
        "facts": f,
    }


def shorten(s: str, n: int) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip())
    if len(s) <= n:
        return s
    cut = s[:n].rsplit(" ", 1)[0]
    return cut.rstrip("،,;·—- ")


# ----------------------------------------------------------------------------- validation
def check(platform: str, text: str, brand: dict) -> tuple[list[str], list[str]]:
    fails: list[str] = []
    warns: list[str] = []
    lim = (brand.get("limits") or {}).get(platform) or {}
    n = len(text)
    hard = int(lim.get("hard_max", 10**6))
    lo, hi = lim.get("target") or [0, hard]
    if n > hard:
        fails.append(f"{n} chars > hard limit {hard}")
    elif not (lo <= n <= hi):
        warns.append(f"{n} chars outside the target {lo}–{hi}")
    tags = HASHTAG_RE.findall(text)
    tlo, thi = lim.get("hashtags") or [0, 99]
    if not (tlo <= len(tags) <= thi):
        fails.append(f"{len(tags)} hashtags, platform wants {tlo}–{thi}")
    if not lim.get("links_in_body", True) and LINK_RE.search(text):
        fails.append("link in the body — move it to the bio / first comment / reply")
    if lim.get("emoji", False) is False and EMOJI.search(text):
        fails.append("emoji")
    body = strip_tashkeel(text)
    for bad in brand.get("forbidden_on_screen", []):
        if bad and bad in body:
            fails.append(f"forbidden wording «{bad}»")
    for bad in (brand.get("cta") or {}).get("forbidden", []):
        if bad in body:
            fails.append(f"follow-bait CTA «{bad}»")
    if re.search(r"[!]{1,}", text):
        fails.append("exclamation mark — the brand never raises its voice")
    latin = ALLOWED_LATIN.sub("", text)
    if re.search(r"[A-Za-z]{2,}", latin):
        fails.append("Latin letters besides the handle")
    if not REF_RE.search(strip_tashkeel(body)):
        fails.append("no reference (book or ج/ص) in the caption")
    if lim.get("question") and "؟" not in text and "?" not in text:
        warns.append("Facebook wants a real question")
    first = text.split("\n")[0]
    fold = int(lim.get("fold", 0) or 0)
    if fold and len(first) > fold:
        warns.append(f"first line {len(first)} chars > visible {fold}")
    if platform == "x" and len(first) > int(lim.get("hook_chars", 60)):
        warns.append(f"first line > {lim.get('hook_chars', 60)} chars — the hook is cut on mobile")
    if platform == "instagram":
        variants = (brand.get("cta") or {}).get("share") or ["أَرْسِلْهَا"]
        if not any(strip_tashkeel(v)[:12] in strip_tashkeel(text) for v in variants):
            warns.append("no approved share CTA")
    if n and re.search(r"\n{3,}", text):
        warns.append("extra blank lines")
    return fails, warns


def write_kit(spec: dict, brand: dict, brief: dict, outdir: Path, texts: dict | None) -> dict:
    merged = dict(brief or {})
    if texts:
        merged["texts"] = {**(merged.get("texts") or {}), **texts}
    comp = compose(spec, brand, merged)
    report = {"files": {}, "checks": {}, "ok": True}
    pre = {}
    for platform in ("instagram", "facebook", "x"):
        fails, warns = check(platform, comp[platform], brand)
        pre[platform] = (fails, warns)
        if fails:
            report["ok"] = False
    # a caption that breaks a limit never sits in the delivery folder
    target = outdir if report["ok"] else outdir / "_FAILED"
    target.mkdir(parents=True, exist_ok=True)
    for platform in ("instagram", "facebook", "x"):
        text = comp[platform]
        fails, warns = pre[platform]
        (target / f"{platform}.txt").write_text(text + "\n", encoding="utf-8")
        report["files"][platform] = {"chars": len(text), "hashtags": len(HASHTAG_RE.findall(text)),
                                     "words": words(text), "path": str(target / f"{platform}.txt")}
        report["checks"][platform] = {"fails": fails, "warns": warns}
        if fails:
            report["ok"] = False
    if comp["x_thread"]:
        fails, warns = [], []
        for i, post in enumerate(comp["x_thread"], 1):
            f2, w2 = check("x", post, brand)
            fails += [f"post {i}: {x}" for x in f2]
            warns += [f"post {i}: {x}" for x in w2]
        (target / "x-thread.txt").write_text("\n\n---\n\n".join(comp["x_thread"]) + "\n", encoding="utf-8")
        report["checks"]["x_thread"] = {"fails": fails, "warns": warns}
        if fails:
            report["ok"] = False
    (target / "alt-text.txt").write_text(comp["alt_text"] + "\n", encoding="utf-8")
    (outdir.parent / "captions.json").write_text(
        json.dumps({k: comp[k] for k in ("instagram", "facebook", "x", "x_thread", "alt_text", "hashtags")},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (outdir.parent / "caption-validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                                          encoding="utf-8")
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--out", default="captions")
    ap.add_argument("--texts", default=None)
    ap.add_argument("--brief", default=None)
    ap.add_argument("--brand", default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    spec = load_json(Path(a.spec))
    if not spec:
        sys.exit(f"cannot read {a.spec}")
    brand = load_json(Path(a.brand) if a.brand else BRAND_PATH, {}) or {}
    brief = load_json(Path(a.brief), {}) if a.brief else {}
    texts = load_json(Path(a.texts), {}) if a.texts else None
    outdir = Path(a.out)
    if not outdir.is_absolute():
        outdir = Path(a.spec).parent / outdir
    report = write_kit(spec, brand, brief or {}, outdir, texts)
    if a.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for platform, info in report["files"].items():
            chk = report["checks"][platform]
            print(f"{platform:9s} {info['chars']:4d} chars · {info['hashtags']} tags · "
                  f"{len(chk['fails'])} fail · {len(chk['warns'])} warn → {info['path']}")
            for x in chk["fails"]:
                print("   ✗", x)
            for x in chk["warns"]:
                print("   ⚠", x)
        print("captions →", outdir)
    if not report["ok"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
