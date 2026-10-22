#!/usr/bin/env python3
"""
retime.py — fit every long-text block to the copy it actually carries, then re-flow the reel.

    python3 retime.py spec.json --write
    python3 retime.py spec.json --out spec.retimed.json [--target 45] [--min-block 5.0]

A long-text block (paragraph · definition · steps · timeline · compare · qa) is not a fixed slot: a
timeline with three short events needs ~9 s, the same block with four dated events and a line of
commentary needs ~16 s. Scaffolds and hand-edited specs carry placeholder lengths, and a block that
outlives its words fails `verify.py` with «longest static stretch»; a block that is too short fails
`build_reel.py` with «last reveal … less than 0.9 s before the scene ends».

This tool measures each long-text scene with the **same cue model** `build_reel.py` uses (it imports
that module — there is no second formula to drift), sets the scene to `last cue + 1.0 s`, and shifts
everything that follows. Short-form scenes keep their authored length. `--target` is only a check:
if the fitted reel is shorter than the target the copy is short — add a sentence or a scene, because
padding the slot only buys a still frame. Nothing else in the spec changes: copy, cues and sources
are untouched.

`--write` edits the file in place and updates `duration`; `--out` writes a copy.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_reel as B                                    # noqa: E402  (the cue model lives there)

TAIL = 1.0          # seconds kept after the last reveal (`_check_room` needs 0.9, plus rounding)
MIN_BLOCK = 5.0     # a long block shorter than this cannot show a full sentence and a source line
MAX_BLOCK = 24.0    # beyond this one screen is doing two screens' work — split the scene


def _probe(scene: dict):
    """Render one scene into a throw-away context and return (last cue, warnings)."""
    ctx = B.Ctx()
    try:
        B.BLOCKS[scene["type"]](scene, ctx)
    except SystemExit as e:                                # missing copy — a real spec error
        raise SystemExit(str(e))
    cues = [v for v in (ctx.cues.get(scene["id"]) or {}).values() if isinstance(v, (int, float))]
    return (max(cues) if cues else float(scene["start"])), list(ctx.warn)


def _needs(scene: dict) -> tuple[float, str]:
    """Measured length of one block, using build_reel's own renderer and cue model."""
    play = json.loads(json.dumps(scene, ensure_ascii=False))
    last, warn = _probe(play)
    need = round(last - float(scene["start"]) + TAIL, 1)
    # The cta clamps its own final line so the brand card stays inside the scene, which hides a
    # shortfall from the cue times. Re-probe with a longer scene until the clamp stops firing.
    extra = 0.0
    while scene.get("type") == "cta" and extra < 6.0 and any(
            ("tight" in w) or ("brand card" in w) for w in warn):
        extra += 0.5
        play["end"] = round(float(scene["end"]) + extra, 1)
        _, warn = _probe(play)
        need = max(need, round(play["end"] - float(scene["start"]), 1))
    return need, (warn[0] if warn else "")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--out")
    ap.add_argument("--write", action="store_true", help="rewrite the spec in place")
    ap.add_argument("--target", type=float, default=None,
                    help="check the fitted total against this; the tool never pads — a gap means the copy is short")
    ap.add_argument("--min-block", type=float, default=MIN_BLOCK)
    ap.add_argument("--max-block", type=float, default=MAX_BLOCK)
    a = ap.parse_args()

    path = Path(a.spec)
    spec = json.loads(path.read_text(encoding="utf-8"))
    scenes = spec.get("scenes") or []
    if not scenes:
        raise SystemExit(f"{path}: no scenes")

    old_total = round(float(scenes[-1]["end"]), 1)
    lens: list[float] = []
    rows: list[tuple[str, str, float, float, str]] = []
    for sc in scenes:
        cur = round(float(sc["end"]) - float(sc["start"]), 1)
        if sc.get("type") in B.LONG_TEXT_BLOCKS:
            need, note = _needs(sc)
            if need <= 0:
                raise SystemExit(f"[{sc.get('id')}] cannot measure this scene: {note}")
            if need < a.min_block:
                note = f"under {a.min_block:.1f}s — the copy is too thin for this block"
                need = a.min_block
            if need > a.max_block:
                note = f"over {a.max_block:.1f}s — split the scene or cut a sentence"
                need = a.max_block
            new = round(need, 1)
            rows.append((str(sc.get("id")), sc["type"], cur, new, note))
        else:
            new, note = cur, ""
            if sc.get("type") == "cta":          # never shrunk, but grown if its copy needs room
                need, _ = _needs(sc)
                if need > cur + 0.05:
                    new, note = round(need, 1), "the closing copy needs the room"
            rows.append((str(sc.get("id")), str(sc.get("type")), cur, new, note))
        lens.append(new)

    total = round(sum(lens), 1)

    t = 0.0
    t = 0.0
    for sc, dur in zip(scenes, lens):
        sc["start"] = round(t, 1)
        t = round(t + dur, 1)
        sc["end"] = t
    spec["duration"] = round(t, 1)

    print(f"{path.name}: {old_total}s → {spec['duration']}s")
    for sid, typ, old, new, note in rows:
        flag = "" if abs(new - old) < 0.05 else ("  ▲" if new > old else "  ▼")
        print(f"  {sid:<4} {typ:<11} {old:5.1f}s → {new:5.1f}s{flag}" + (f"   · {note}" if note else ""))
    if a.target and abs(spec["duration"] - a.target) > 1.0:
        print(f"  ⚠ fitted {spec['duration']}s vs target {a.target}s — "
              + ("add a sentence or a scene; do not pad the slot" if spec["duration"] < a.target
                 else "cut copy; do not squeeze the timing"))
    if spec["duration"] < 30:
        print(f"  ⚠ {spec['duration']}s is under the 30s floor — add a block, not padding")
    if spec["duration"] > 60:
        print(f"  ⚠ {spec['duration']}s is over the 60s ceiling — cut a block")

    out = path if a.write else (Path(a.out) if a.out else None)
    if out:
        out.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {out}")
    else:
        print("dry run — pass --write or --out to save")


if __name__ == "__main__":
    main()
