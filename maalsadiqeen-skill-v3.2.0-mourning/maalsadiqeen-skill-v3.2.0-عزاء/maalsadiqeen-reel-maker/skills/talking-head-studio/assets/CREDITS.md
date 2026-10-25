# Credits and licences — talking-head-studio

| Asset | Source | Licence | Notes |
|---|---|---|---|
| `fonts/Vazirmatn.ttf` | rastikerdar/vazirmatn | SIL OFL 1.1 | Copied from `maalsadiqeen-reel/assets/remotion-template/public/fonts/` (same repo) |
| `fonts/Amiri-Bold.ttf` | alif-type/amiri | SIL OFL 1.1 | Copied from `maalsadiqeen-reel/assets/fonts/` (same repo) |
| `cascades/haarcascade_frontalface_default.xml` | opencv/opencv `data/haarcascades` (4.x) | Apache-2.0 | Face detector for reframing; fetched once and vendored so no download is needed at runtime |

Everything else in this skill (scripts, references, evals) is original work for this repository.
The pipeline uses only ffmpeg, numpy, opencv and Pillow — all local, no model downloads, no API keys.
