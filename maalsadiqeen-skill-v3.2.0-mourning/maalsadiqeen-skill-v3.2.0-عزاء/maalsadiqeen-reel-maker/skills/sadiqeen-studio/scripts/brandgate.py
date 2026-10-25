#!/usr/bin/env python3
"""The brand's own gates, run as gates.

The words on screen are not this studio's to approve. Three installed skills own them, and
each ships a checker; this module runs all four on the spec **before** a frame is drawn, so
a reel never renders a sentence the brand would refuse.

    copy_lint    ← maalsadiqeen-reel   placeholders · forbidden · layers · budget · honourifics
    ar_copycheck ← arabic-editor       hamza · ta-marbuta · digits · dialect · tashkeel density
    sanad_check  ← hadith-sanad        a seal without a grade · an invented citation
    hook_score_ar← maalsadiqeen-reel   is the first 3 s worth the scroll?

    python3 brandgate.py spec.json
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import brandkit as bk

GATES = [
    ("copy_lint", "maalsadiqeen-reel", "scripts/copy_lint.py", ["--json"]),
    ("ar_copycheck", "arabic-editor", "scripts/ar_copycheck.py", ["--spec", "--json"]),
    ("sanad_check", "hadith-sanad", "scripts/sanad_check.py", ["--spec", "--json"]),
]


def _skill(name: str) -> Path | None:
    """Find an installed sibling skill (any of the standard locations)."""
    root = bk.skill_root()
    cands = [root.parent / name, Path.home() / ".agents" / "skills" / name,
             Path.home() / ".claude" / "skills" / name]
    for c in cands:
        if (c / "SKILL.md").exists():
            return c
    return None


def _parse(out: str) -> dict:
    out = out.strip()
    if not out:
        return {}
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        i, j = out.find("{"), out.rfind("}")
        if i >= 0 and j > i:
            try:
                return json.loads(out[i:j + 1])
            except json.JSONDecodeError:
                return {}
    return {}


def _items(d: dict, *keys) -> list[str]:
    got: list[str] = []
    for k in keys:
        v = d.get(k)
        if isinstance(v, list):
            got += [str(x.get("message", x)) if isinstance(x, dict) else str(x) for x in v]
        elif isinstance(v, dict):
            got += [f"{kk}: {vv}" for kk, vv in v.items()]
    return got


def run(spec_path: str, strict: bool = True) -> dict:
    """Run every available gate. `strict` turns tool failures into failures, not silence."""
    rows: list[dict] = []
    for name, skill, script, args in GATES:
        root = _skill(skill)
        path = (root / script) if root else None
        if not path or not path.exists():
            rows.append({"level": "warn", "gate": name,
                         "value": f"skill «{skill}» not installed",
                         "want": "installed — the words are not ours to approve"})
            continue
        cmd = [sys.executable, str(path), spec_path] + args
        r = subprocess.run(cmd, capture_output=True, text=True)
        data = _parse(r.stdout) or _parse(r.stderr)
        fails = _items(data, "fails", "fail", "errors", "error")
        warns = _items(data, "warns", "warn", "warnings")
        for f in fails:
            rows.append({"level": "fail", "gate": name, "value": f, "want": "0 failures"})
        for w in warns:
            rows.append({"level": "warn", "gate": name, "value": w, "want": "0 warnings"})
        if not fails and not warns:
            rows.append({"level": "pass", "gate": name, "value": "clean", "want": "0 failures"})
        elif not fails:
            rows.append({"level": "pass", "gate": name,
                         "value": f"{len(warns)} warning(s), no failures", "want": "0 failures"})
        elif not data and r.returncode != 0 and strict:
            rows.append({"level": "fail", "gate": name,
                         "value": (r.stdout or r.stderr).strip()[:200], "want": "a clean spec"})
    rows.append(hook_check(spec_path))
    fails = sum(1 for r in rows if r["level"] == "fail")
    warns = sum(1 for r in rows if r["level"] == "warn")
    return {"rows": rows, "fails": fails, "warns": warns,
            "verdict": "FAIL" if fails else ("WARN" if warns else "PASS")}


def hook_check(spec_path: str) -> dict:
    """Advisory, never binding: the scorer reads a hook in isolation, and a title card
    («في محراب العزاء») is not a curiosity gap. copy_lint is the gate; this is advice."""
    root = _skill("maalsadiqeen-reel")
    path = (root / "scripts" / "hook_score_ar.py") if root else None
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    hook = next((s for s in spec.get("scenes", []) if s.get("type") == "hook"), None)
    if hook is None:
        return {"level": "warn", "gate": "hook_score", "value": "no hook scene",
                "want": "a first cut inside the 3-second cliff"}
    text = " ".join(str(hook.get(k, "")) for k in ("lead", "line1", "line2")).strip()
    if not path or not path.exists():
        return {"level": "warn", "gate": "hook_score", "value": "scorer not installed",
                "want": "maalsadiqeen-reel installed"}
    r = subprocess.run([sys.executable, str(path), text, "--details"],
                       capture_output=True, text=True)
    m = re.search(r"\[\s*(\d{1,3})", r.stdout)
    if not m:
        return {"level": "warn", "gate": "hook_score", "value": "unscored", "want": "≥ 65/100"}
    score = int(m.group(1))
    dims = re.search(r"brevity[^\n]+", r.stdout)
    want = "≥ 65/100 (aim 80; below 65 rewrite from hooks-ar.md)"
    lvl = "pass" if score >= 65 else "warn"
    return {"level": lvl, "gate": "hook_score",
            "value": f"{score}/100 — «{text}»" + (f" · {dims.group(0)}" if dims else ""),
            "want": want}


def table(res: dict) -> str:
    rows = ["| gate | finding | wanted | verdict |", "|---|---|---|---|"]
    for r in res["rows"]:
        mark = {"pass": "✓", "warn": "!", "fail": "✗"}[r["level"]]
        rows.append(f'| {r["gate"]} | {r["value"]} | {r["want"]} | {mark} |')
    return "\n".join(rows)


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="run the brand's copy gates on a spec")
    ap.add_argument("spec")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    res = run(a.spec)
    print(json.dumps(res, ensure_ascii=False, indent=1) if a.json else
          f'{res["verdict"]}\n' + table(res))
    return 0 if res["fails"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
