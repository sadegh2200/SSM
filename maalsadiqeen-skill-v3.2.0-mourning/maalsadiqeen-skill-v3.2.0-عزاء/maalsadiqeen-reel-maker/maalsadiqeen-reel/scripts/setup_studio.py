#!/usr/bin/env python3
"""
setup_studio.py — create (or refresh) the Remotion studio folder from the skill template.

    python3 setup_studio.py [--dest ~/reel-studio] [--link-node-modules /path/to/existing/node_modules]
                            [--skip-install] [--skip-browser]

What it does
  1. copies assets/remotion-template → <dest> (src/, public/fonts, public/img/noise.png, bundled SFX, configs);
     existing public/content.json, plan.json, img/logo.png, img/branch.png, audio/pad.wav are preserved
  2. npm install (remotion 4.0.535 pinned) — or symlinks an existing node_modules to save time/disk
  3. npx remotion browser ensure (downloads Chrome Headless Shell if missing)
  4. installs Chrome's shared libraries + Arabic fonts with apt when running as root and they are missing
  5. synthesizes the audio layer if public/audio/pad.wav is missing
  6. runs tsc --noEmit as a smoke test
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "assets" / "remotion-template"
PRESERVE = ["public/content.json", "public/plan.json", "public/img/logo.png", "public/img/branch.png", "public/audio/pad.wav", "public/brand.json"]
APT_LIBS = ["libnss3", "libatk-bridge2.0-0", "libgtk-3-0", "libgbm1", "libasound2", "libxss1", "libxshmfence1", "fonts-noto-core", "fonts-kacst", "fonts-hosny-amiri"]


def run(cmd, cwd=None, check=True, timeout=1800):
    print("$", " ".join(cmd))
    r = subprocess.run(cmd, cwd=cwd, text=True, timeout=timeout)
    if check and r.returncode:
        sys.exit(f"command failed: {' '.join(cmd)}")
    return r.returncode


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dest", default=os.path.expanduser("~/reel-studio"))
    ap.add_argument("--link-node-modules", default=None)
    ap.add_argument("--skip-install", action="store_true")
    ap.add_argument("--skip-browser", action="store_true")
    a = ap.parse_args()
    dest = Path(a.dest)
    dest.mkdir(parents=True, exist_ok=True)

    # 1. copy template, preserving user files
    saved = {}
    for rel in PRESERVE:
        p = dest / rel
        if p.exists():
            saved[rel] = p.read_bytes()
    for item in TEMPLATE.iterdir():
        target = dest / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)
    for rel, data in saved.items():
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        (dest / rel).write_bytes(data)
    print(f"template copied to {dest} (preserved: {', '.join(saved) or 'nothing'})")

    # 2. deps
    nm = dest / "node_modules"
    if a.link_node_modules:
        src = Path(a.link_node_modules).resolve()
        if nm.is_symlink() or nm.exists():
            if nm.is_dir() and not nm.is_symlink():
                shutil.rmtree(nm)
            else:
                nm.unlink()
        nm.symlink_to(src)
        print(f"linked node_modules → {src}")
    elif not a.skip_install and not (nm / "remotion").exists():
        run(["npm", "install", "--no-audit", "--no-fund"], cwd=dest)

    # 4. system libs (root only)
    if os.geteuid() == 0 and shutil.which("apt-get"):
        missing = [lib for lib in APT_LIBS if subprocess.run(["dpkg", "-s", lib], capture_output=True).returncode]
        if missing:
            run(["apt-get", "install", "-y", "-q", *missing], check=False)

    # 3. browser
    if not a.skip_browser:
        run(["npx", "remotion", "browser", "ensure"], cwd=dest, check=False)

    # 5. audio
    if not (dest / "public" / "audio" / "pad.wav").exists():
        run([sys.executable, str(ROOT / "scripts" / "make_audio.py"), "--out", str(dest / "public" / "audio")])

    # 6. smoke test
    rc = run(["npx", "tsc", "--noEmit", "-p", "tsconfig.json"], cwd=dest, check=False)
    print("studio ready" if rc == 0 else "studio copied but tsc reported errors — inspect above")


if __name__ == "__main__":
    main()
