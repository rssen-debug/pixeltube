#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_video.py – Skapar ett färdigt pixeläventyr (MP4).

Ljudlägen:
  --backend gtts|espeak  Berättarröst (TTS).
  --backend none         KARAKTÄRSRÖSTER: figurerna piper (ingen TTS!),
                         undertexterna säger vad de menar. (default-ljudet)
  --silent               Helt utan tal/voices, bara musik + effekter.

Allt rörelse-ljud loopas i takt med animationen: fotsteg (gå/spring),
hopp + landningsduns, dansstötsar, spin-whoosh, bonk, snarkningar.
"""
import argparse
import bisect
import json
import random
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

import engine
import music as musicmod
import sfx as sfxmod
import story as storymod
import tts as ttsmod
import voice as voicemod

FPS = 24
TITLE_T = 3.0
OUTRO_T = 2.6

FONT_BOLD = ["C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/segoeuib.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
             "/System/Library/Fonts/Supplemental/Arial Bold.ttf"]
FONT_REG = ["C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf"]

HERE = Path(__file__).resolve().parent

OUTROS = {"sv": ("TACK FÖR ATT DU TITTADE!", "Prenumerera för fler äventyr!"),
          "en": ("MISSION COMPLETE", "Subscribe – new episode every week!")}


def find_ffmpeg():
    p = shutil.which("ffmpeg")
    if p:
        return p
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        sys.exit("Hittar ingen ffmpeg! Kör: pip install imageio-ffmpeg")


def load_font(size, bold=True):
    for p in (FONT_BOLD if bold else FONT_REG) + (FONT_REG if bold else FONT_BOLD):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def wrap_lines(draw, text, font, maxw, max_lines=2):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
            if len(lines) == max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines and len(" ".join(lines)) < len(text):
        lines[-1] = lines[-1].rstrip(".…") + "…"
    return lines


def slugify(s, fallback="avsnitt"):
    s = s.lower().replace("å", "a").replace("ä", "a").replace("ö", "o")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:40] or fallback


def draw_subtitle(d, text, font, W2, H2, u):
    lines = wrap_lines(d, text, font, int(W2 * 0.88), 2)
    asc, desc = font.getmetrics()
    lh = asc + desc + int(3 * u)
    pad = int(7 * u)
    tw = max(d.textlength(ln, font=font) for ln in lines)
    box_h = lh * len(lines) + 2 * pad
    y1 = H2 - int(16 * u) - box_h
    x1 = (W2 - tw) / 2 - pad
    d.rounded_rectangle([x1, y1, x1 + tw + 2 * pad, y1 + box_h],
                        radius=int(8 * u), fill=(0, 0, 0, 95))
    for j, ln in enumerate(lines):
        lw = d.textlength(ln, font=font)
        d.text(((W2 - lw) / 2, y1 + pad + j * lh), ln, font=font,
               fill=(255, 255, 255), stroke_width=max(1, int(1.2 * u)),
               stroke_fill=(0, 0, 0, 200))


def draw_center_block(d, lines, W2, H2, u, y_frac=0.40, dim=110):
    d.rectangle([0, 0, W2, H2], fill=(0, 0, 0, dim))
    total_h = sum(f.getmetrics()[0] + f.getmetrics()[1] + int(4 * u) for f, _, _, _ in lines)
    y = H2 * y_frac - total_h / 2
    for f, text, fill, sw in lines:
        lw = d.textlength(text, font=f)
        d.text(((W2 - lw) / 2, y), text, font=f, fill=fill,
               stroke_width=sw, stroke_fill=(30, 20, 8, 230))
        y += f.getmetrics()[0] + f.getmetrics()[1] + int(4 * u)


def get_story(args, seed):
    cast = [c.strip() for c in args.cast.split(",")] if args.cast else None
    if args.idea or args.llm:
        try:
            import script_llm
            return script_llm.llm_story(seed, args.lang, idea=args.idea,
                                        model=args.model, n_scenes=args.llm_scenes,
                                        cast=cast)
        except Exception as e:  # noqa: BLE001
            print(f"  [llm] Funkade inte ({e}) – använder sagomall istället.")
    return storymod.make_story(seed, args.lang, args.story, cast=cast)


def pick_speaker(text, cast, chars):
    """Vilken karaktär 'säger' repliken? Första namnet som nämns, annars huvudpersonen."""
    low = (text or "").lower()
    best, best_pos = None, 10 ** 9
    for name in cast:
        for alias in engine.alias_group(name):
            p = low.find(alias)
            if 0 <= p < best_pos:
                best, best_pos = name, p
    return chars[best or cast[0]]


def _loop_sfx(act, dur, phase=0.0):
    """Bygger en loopad ljudbädd för en action under dur sekunder."""
    sr = musicmod.SR
    n = max(1, int(dur * sr))
    tr = np.zeros(n, dtype=np.float32)

    def put(t0, arr, vol):
        off = int(t0 * sr)
        if off < 0 or off >= n:
            return
        end = min(n, off + len(arr))
        tr[off:end] += arr[:end - off] * vol

    if act == "jump":
        k = phase
        while k < dur:
            put(k, sfxmod.boing(), 0.50)
            put(k + 0.95, sfxmod.thud(), 0.55)
            k += 1.15
    elif act == "run":
        k, alt = phase, 0
        while k < dur:
            put(k, sfxmod.step(alt % 2), 0.55)
            k += 0.24
            alt += 1
    elif act in (None, "walk"):
        k, alt = phase, 0
        while k < dur:
            put(k, sfxmod.step(alt % 2), 0.24)
            k += 0.48
            alt += 1
    elif act == "dance":
        k = phase
        while k < dur:
            put(k, sfxmod.boing(), 0.32)
            k += 0.70
    elif act == "spin":
        k = phase
        while k < dur:
            put(k, sfxmod.whoosh(), 0.45)
            k += 1.0
    elif act == "hit":
        k = phase
        while k < dur:
            put(k, sfxmod.bonk(), 0.55)
            k += 0.90
    elif act == "sleep":
        k = phase
        while k < dur:
            put(k, sfxmod.snore(), 0.35)
            k += 2.1
    elif act == "fire":
        k = phase
        while k < dur:
            put(k, sfxmod.flame(), 0.45)
            k += 1.3
    elif act == "shock":
        k = phase
        while k < dur:
            put(k, sfxmod.pop(), 0.38)
            put(k + 0.22, sfxmod.sparkle(), 0.30)
            k += 1.2
    elif act == "fall":
        k = phase
        while k < dur:
            put(k + 0.42, sfxmod.thud(), 0.62)
            k += 1.9
    elif act == "flex":
        k = phase
        while k < dur:
            put(k, sfxmod.sparkle(), 0.22)
            k += 2.6
    return tr


def main():
    ap = argparse.ArgumentParser(description="Skapa ett pixeläventyr som färdig MP4.")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--lang", choices=["sv", "en"], default="en")
    ap.add_argument("--story", type=int, default=None, help="Sagomall 0-6")
    ap.add_argument("--cast", default=None, help="Rollista, t.ex. 'doris,apan'")
    ap.add_argument("--scale", type=int, default=4, help="4=720p, 2=360p (snabbtest)")
    ap.add_argument("--backend", default="auto", choices=["auto", "gtts", "espeak", "none"],
                    help="none = karaktärerna piper istället för TTS")
    ap.add_argument("--silent", action="store_true", help="Barra musik + effekter, inga röster alls")
    ap.add_argument("--idea", default=None)
    ap.add_argument("--llm", action="store_true")
    ap.add_argument("--model", default="qwen2.5:3b")
    ap.add_argument("--llm-scenes", type=int, default=6)
    ap.add_argument("--no-outro", action="store_true")
    ap.add_argument("--out", default=str(HERE / "out"))
    args = ap.parse_args()

    seed = args.seed if args.seed is not None else random.randint(1, 99999)
    meta = get_story(args, seed)
    cast = list(meta.get("cast") or [meta["name"]])
    scenes = storymod.normalize_scenes(meta["scenes"])
    texts = [s["text"] for s in scenes]

    chars = {name: engine.Character(name) for name in cast}
    disp = {name: ch.display for name, ch in chars.items()}

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    workdir = outdir / f"ep{seed:03d}_work"
    workdir.mkdir(parents=True, exist_ok=True)

    print(f"🎬 Avsnitt {seed}: ”{meta['title']}”")
    print("   🎭 rollista: " + ", ".join(f"{disp[n]} ({chars[n].species}/{chars[n].tint})"
                                    for n in cast))

    ffmpeg = find_ffmpeg()

    # --- 1. Röster: TTS, eller pixel-pip, eller tyst ---
    t0 = time.time()
    auds, used = ttsmod.synth_lines(texts, args.lang, workdir, ffmpeg, args.backend)
    gibberish = None
    if used == "none" and not args.silent:
        gibberish = []
        for i, txt in enumerate(texts):
            spk = pick_speaker(txt, cast, chars)
            arr = voicemod.speak(txt, species=spk.species, seed=seed * 31 + i)
            gibberish.append((spk, arr))
        # Scenlängd = max(pip-längd, LÄSTID) – undertexten måste hinnas läsas!
        auds = [(None, max(len(arr) / musicmod.SR, ttsmod.estimate_dur(txt)))
                for (spk, arr), txt in zip(gibberish, texts)]
        print(f"   🗣️  pixelröster (pip!): " +
              ", ".join(f"{g[0].display}~{g[0].species}" for g in gibberish) +
              f"  ({time.time() - t0:.1f}s)")
    elif used == "none":
        print("   🔇 inga röster (silent)")
    else:
        print(f"   🎙️  röst: {used}  ({time.time() - t0:.1f}s)")

    # --- 2. Tidslinje ---
    starts, audio_starts = [], []
    cur = 0.0
    for i, (_, adur) in enumerate(auds):
        pre = TITLE_T + 0.4 if i == 0 else 0.55
        starts.append(cur)
        audio_starts.append(cur + pre)
        cur += pre + adur + 1.4
    total = cur
    print(f"   ⏱️  längd: {total:.1f}s")

    # --- 3. Scener + vem gör vad ---
    scene_objs, scene_actions = [], []
    for i, s in enumerate(scenes):
        acts = storymod.parse_actions(s["text"], cast)
        if s["action"] and not acts.get(cast[0]):
            acts[cast[0]] = s["action"]
        scene_actions.append(acts)
        scene_objs.append(engine.Scene(
            s["setting"], seed * 97 + i,
            actors=[(chars[n], acts[n]) for n in cast],
            text=s["text"], props=s["props"], reaction=s["reaction"],
            mystery=s.get("mystery")))
    bits = []
    for i, s in enumerate(scenes):
        who = "/".join(f"{disp[n]}:{scene_actions[i][n]}" for n in cast if scene_actions[i][n])
        bits.append(f"{s['setting']}{'<' + who + '>' if who else ''}")
    print("   🎬 scener: " + " | ".join(bits))

    # --- 4. Ljudmix: röster + loopade rörelseljud + effekter + musik ---
    SR = musicmod.SR
    mix = np.zeros(int((total + 0.5) * SR), dtype=np.float32)
    has_speech = False
    for i, (wpath, _) in enumerate(auds):
        data = None
        if wpath:
            data = ttsmod.read_wav_float(wpath)
        elif gibberish is not None:
            data = gibberish[i][1]
        if data is not None and len(data):
            has_speech = True
            off = int(audio_starts[i] * SR)
            mix[off:off + len(data)] += data

    for i, sc in enumerate(scenes):
        st = starts[i]
        dur_i = (starts[i + 1] - st) if i < len(scenes) - 1 else (total - st)
        for ai, name in enumerate(cast):
            tr = _loop_sfx(scene_actions[i][name], dur_i, phase=ai * 0.31)
            off = int(st * SR)
            if off + len(tr) <= len(mix):
                mix[off:off + len(tr)] += tr

    sfx_events = set()
    last = len(scenes) - 1
    for i, sc in enumerate(scenes):
        st = starts[i]
        dur_i = (starts[i + 1] - st) if i < last else (total - st)
        reac = sc["reaction"]
        if reac in ("!", "?"):
            sfx_events.add((round(st + 0.7, 2), "pop"))
        elif reac in ("♥", "★"):
            sfx_events.add((round(st + 0.7, 2), "sparkle"))
        if sc["setting"] == "underwater":
            sfx_events.add((round(st + 0.15, 2), "splash"))
        if i == last:
            sfx_events.add((round(st + max(0.2, dur_i - (OUTRO_T if not args.no_outro else 1.2)), 2),
                            "fanfare"))
    for st, name in sorted(sfx_events):
        arr = sfxmod.make(name) * 0.55
        off = int(st * SR)
        if off + len(arr) <= len(mix):
            mix[off:off + len(arr)] += arr

    mus = musicmod.chip(seed + 1234, total)
    mix[:len(mus)] += mus * (0.38 if has_speech else 0.9)
    mix = np.tanh(mix) * 0.95
    mix_path = workdir / "mix.wav"
    musicmod.save_wav16(mix_path, mix)
    print(f"   🎵 ljud klart ({'röster + ' if has_speech else ''}musik + loopade effekter)")

    # --- 5. Rendera ---
    scale = max(1, args.scale)
    W2, H2 = engine.W * scale, engine.H * scale
    silent_mp4 = workdir / "silent.mp4"
    cmd = [ffmpeg, "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W2}x{H2}",
           "-r", str(FPS), "-i", "pipe:0", "-an",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
           "-pix_fmt", "yuv420p", str(silent_mp4)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    u = scale / 4
    sub_font = load_font(max(10, int(30 * u)), bold=True)
    big_font = load_font(max(14, int(52 * u)), bold=True)
    small_font = load_font(max(9, int(22 * u)), bold=False)
    ep_label = f"AVSNITT {seed:03d}" if args.lang == "sv" else f"EPISODE {seed:03d}"
    o1, o2 = OUTROS[args.lang]

    n = int(total * FPS)
    t_start = time.time()
    for f in range(n):
        t = f / FPS
        idx = min(len(scene_objs) - 1, max(0, bisect.bisect_right(starts, t) - 1))
        img = scene_objs[idx].frame(t - starts[idx])

        b = 1.0
        if t < 0.8:
            b = t / 0.8
        if total - t < 1.0:
            b = min(b, max(0.0, (total - t) / 1.0))
        if b < 1.0:
            img = ImageEnhance.Brightness(img).enhance(b)

        up = img.resize((W2, H2), engine.NEAREST)
        d = ImageDraw.Draw(up, "RGBA")

        outro = (not args.no_outro and idx == len(scenes) - 1
                 and total - t <= OUTRO_T and t > TITLE_T)
        if t < TITLE_T:
            draw_center_block(d, [(big_font, meta["title"], (255, 232, 120), max(2, int(2.4 * u))),
                                  (small_font, ep_label, (235, 235, 245), max(1, int(u)))],
                              W2, H2, u)
        elif outro:
            draw_center_block(d, [(big_font, o1, (255, 232, 120), max(2, int(2.4 * u))),
                                  (small_font, o2, (235, 235, 245), max(1, int(u)))],
                              W2, H2, u, y_frac=0.38, dim=95)
        elif t >= audio_starts[idx]:
            draw_subtitle(d, scenes[idx]["text"], sub_font, W2, H2, u)

        proc.stdin.write(up.tobytes())
        if f % (FPS * 2) == 0:
            print(f"\r   🖼️  renderar… {100.0 * t / total:5.1f}%", end="", flush=True)

    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg misslyckades under videokodningen.")
    print(f"\r   🖼️  renderat ({time.time() - t_start:.0f}s)          ")

    # --- 6. Muxa ---
    slug = slugify(meta["title"])
    final = outdir / f"ep{seed:03d}-{slug}.mp4"
    subprocess.run([ffmpeg, "-y", "-loglevel", "error",
                    "-i", str(silent_mp4), "-i", str(mix_path),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                    "-movflags", "+faststart", "-shortest", str(final)], check=True)

    meta_out = {"title": meta["title"], "description": meta["description"],
                "tags": meta["tags"], "madeForKids": True, "categoryId": "1",
                "madeForKids": False,
                "language": args.lang, "seed": seed, "cast": cast,
                "voices": "gibberish" if gibberish else used}
    final.with_suffix(".json").write_text(
        json.dumps(meta_out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ KLART: {final}  ({final.stat().st_size / 1e6:.1f} MB, {total:.0f}s)")
    print(f"OUTPUT: {final}")


if __name__ == "__main__":
    main()
