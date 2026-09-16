#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
batch.py – Skapa många avsnitt i ett svep (= hel säsong), uppladdning valfritt.

Exempel:
    python batch.py --count 5
    python batch.py --count 8 --lang en
    python batch.py --count 6 --llm                 # Qwen hittar på varje saga
    python batch.py --count 5 --upload --privacy unlisted
"""
import argparse
import random
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser(description="Massproducera pixelavsnitt.")
    ap.add_argument("--count", type=int, default=3)
    ap.add_argument("--start-seed", type=int, default=None)
    ap.add_argument("--lang", choices=["sv", "en"], default="en")
    ap.add_argument("--scale", type=int, default=4)
    ap.add_argument("--story", type=int, default=None, help="Lås säsongsmall (0-9, eskalerande)")
    ap.add_argument("--cast", default=None, help="Fast rollista, t.ex. 'doris,apan'")
    ap.add_argument("--llm", action="store_true", help="Låt Qwen skriva varje avsnitt")
    ap.add_argument("--backend", default="auto")
    ap.add_argument("--upload", action="store_true")
    ap.add_argument("--privacy", choices=["private", "unlisted", "public"], default="unlisted")
    args = ap.parse_args()

    start = args.start_seed if args.start_seed is not None else random.randint(1, 9000)
    done = []
    for i in range(args.count):
        seed = start + i
        print("\n" + "=" * 64)
        print(f"🎬 AVSNITT {i + 1}/{args.count}  (seed {seed})")
        print("=" * 64)
        cmd = [sys.executable, str(HERE / "make_video.py"),
               "--seed", str(seed), "--lang", args.lang,
               "--scale", str(args.scale), "--backend", args.backend]
        if args.llm:
            cmd += ["--llm"]
        else:
            story_idx = args.story if args.story is not None else seed % 10
            cmd += ["--story", str(story_idx)]
        if args.cast:
            cmd += ["--cast", args.cast]

        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(HERE))
        sys.stdout.write(res.stdout)
        if res.returncode != 0:
            print("❌ Fel vid skapande:\n", (res.stderr or res.stdout)[-2000:])
            continue
        m = re.search(r"^OUTPUT:\s*(.+)$", res.stdout, re.M)
        if not m:
            print("❌ Kunde inte tolka utdata.")
            continue
        mp4 = m.group(1).strip()
        done.append(mp4)

        if args.upload:
            up = subprocess.run([sys.executable, str(HERE / "upload_youtube.py"),
                                 mp4, "--privacy", args.privacy],
                                capture_output=True, text=True, cwd=str(HERE))
            sys.stdout.write(up.stdout)
            if up.returncode != 0:
                print("⚠️  Uppladdning misslyckades:\n", (up.stderr or "")[-1500:])

    print("\n" + "=" * 64)
    print(f"🏁 KLART! {len(done)}/{args.count} avsnitt skapade:")
    for p in done:
        print("  •", p)


if __name__ == "__main__":
    main()
