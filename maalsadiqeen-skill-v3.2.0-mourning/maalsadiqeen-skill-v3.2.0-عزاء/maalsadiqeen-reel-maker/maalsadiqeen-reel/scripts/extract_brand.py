#!/usr/bin/env python3
"""
extract_brand.py — pull palette + logo/branch assets out of the user's carousel card image.

    python3 extract_brand.py "cards/1.jpg" --out ~/reel-studio/public [--logo-box bl] [--branch-box tr] [--no-logo] [--no-branch]

Writes:
  <out>/img/logo.png      keyed (transparent) crop of the logo corner (default bottom-left of card)
  <out>/img/branch.png    keyed crop of the ornament corner (default top-right)
  <out>/brand.json        sampled palette → paste into content.json "brand.palette"
The crops are background-keyed by sampling the paper colour and removing near-paper pixels.
Fallbacks: if a crop is nearly empty (no ink), the file is NOT written and the template shows
the @handle text instead. Verify the PNGs visually before rendering.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

BOXES = {  # fractions of (w, h): x0, y0, x1, y1
    "bl": (0.00, 0.86, 0.50, 1.00),
    "br": (0.50, 0.86, 1.00, 1.00),
    "tl": (0.00, 0.00, 0.28, 0.12),
    "tr": (0.72, 0.00, 1.00, 0.12),
}


def rgb(bgr):
    return f"rgb({int(bgr[2])},{int(bgr[1])},{int(bgr[0])})"


def sample_palette(img):
    h, w = img.shape[:2]
    center = img[int(h * 0.45):int(h * 0.55), int(w * 0.4):int(w * 0.6)].reshape(-1, 3)
    bg_center = np.median(center, axis=0)
    edge = np.concatenate([img[:20].reshape(-1, 3), img[-20:].reshape(-1, 3), img[:, :20].reshape(-1, 3), img[:, -20:].reshape(-1, 3)])
    bg_edge = np.median(edge, axis=0)
    # dominant saturated colour (the brand green/maroon) = pixels far from paper
    flat = img.reshape(-1, 3).astype(np.int32)
    dist = np.abs(flat - bg_center.astype(np.int32)).sum(axis=1)
    ink = flat[dist > 120]
    accent = None
    if len(ink) > 200:
        hsv = cv2.cvtColor(ink.reshape(-1, 1, 3).astype(np.uint8), cv2.COLOR_BGR2HSV).reshape(-1, 3)
        sat = hsv[:, 1] > 60
        if sat.sum() > 100:
            # k-means (k=3) on saturated ink, pick the largest cluster
            data = ink[sat].astype(np.float32)
            crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
            _, labels, centers = cv2.kmeans(data, 3, None, crit, 3, cv2.KMEANS_PP_CENTERS)
            accent = centers[np.bincount(labels.ravel()).argmax()]
        dark = ink[(hsv[:, 1] <= 60) & (hsv[:, 2] < 120)]
    else:
        dark = np.array([])
    text = np.median(dark, axis=0) if len(dark) else np.array([25, 34, 41])
    return {"bgCenter": rgb(bg_center), "bgEdge": rgb(bg_edge), "green": rgb(accent) if accent is not None else "rgb(10,79,6)", "ink": rgb(text)}


def key_crop(img, box, bg):
    h, w = img.shape[:2]
    x0, y0, x1, y1 = (int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h))
    crop = img[y0:y1, x0:x1]
    # local paper estimate (large median kernel) so the vignette/gradient does not leak into alpha
    local_bg = cv2.medianBlur(crop, 61)
    dist = np.abs(crop.astype(np.int32) - local_bg.astype(np.int32)).sum(axis=2)
    alpha = np.clip((dist - 20) * 8, 0, 255).astype(np.uint8)
    alpha = cv2.morphologyEx(alpha, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    alpha = cv2.GaussianBlur(alpha, (3, 3), 0)
    ys, xs = np.where(alpha > 40)
    if len(xs) < 150:
        return None
    pad = 12
    ya, yb = max(0, ys.min() - pad), min(crop.shape[0], ys.max() + pad)
    xa, xb = max(0, xs.min() - pad), min(crop.shape[1], xs.max() + pad)
    rgba = np.dstack([crop[ya:yb, xa:xb], alpha[ya:yb, xa:xb]])
    return rgba


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("card")
    ap.add_argument("--out", required=True, help="template public/ dir")
    ap.add_argument("--logo-box", default="bl", choices=BOXES)
    ap.add_argument("--branch-box", default="tr", choices=BOXES)
    ap.add_argument("--no-logo", action="store_true")
    ap.add_argument("--no-branch", action="store_true")
    a = ap.parse_args()
    img = cv2.imread(a.card)
    if img is None:
        raise SystemExit(f"cannot read {a.card}")
    out = Path(a.out)
    (out / "img").mkdir(parents=True, exist_ok=True)
    pal = sample_palette(img)
    bg = np.array([int(v) for v in pal["bgCenter"][4:-1].split(",")][::-1])
    result = {"palette": pal, "logo": None, "branch": None}
    if not a.no_logo:
        crop = key_crop(img, BOXES[a.logo_box], bg)
        if crop is not None and crop.shape[0] > 20:
            cv2.imwrite(str(out / "img" / "logo.png"), crop)
            result["logo"] = "img/logo.png"
        else:
            print("logo corner looks empty — no logo.png written (template falls back to the @handle)")
    if not a.no_branch:
        crop = key_crop(img, BOXES[a.branch_box], bg)
        if crop is not None and crop.shape[0] > 20:
            cv2.imwrite(str(out / "img" / "branch.png"), crop)
            result["branch"] = "img/branch.png"
        else:
            print("branch corner looks empty — no branch.png written")
    with open(out / "brand.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"wrote {out/'brand.json'} — paste 'palette' into content.json → brand.palette and set brand.logo/branch")


if __name__ == "__main__":
    main()
