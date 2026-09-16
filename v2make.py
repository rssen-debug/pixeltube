#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v2 PIXEL ANIME – v2make: regissören som monterar en riktig anime-episod på CPU.
Episod-anatomi (research): avant-title -> OP-kort -> A-part (mini-cliff) ->
EYECATCH (2 kort) -> B-part (fight!) -> C-part-tease -> NEXT EPISODE.
Munnar läppsynkas från röstens envelope; ögon visar reaktioner; dörrar öppnas;
slag gör ont (knockback + X-ögon + blåmärke).
"""
import argparse
import json
import math
import os
import random
import subprocess
import time

import numpy as np
import imageio_ffmpeg
from PIL import Image, ImageDraw

import voice as voicemod
import sfx as sfxmod
import music as musicmod
import tts as ttsmod
import v2engine as E

NEAREST = E.NEAREST

FPSS = 12
SCALE = 4                       # 320x180 -> 1280x720
OUTW, OUTH = E.W * SCALE, E.H * SCALE

SERIES = "VOLT BREAKER"

# -------------------------------------------------------------------------- #
# ROLLLISTA (v2 – människor!)                                               #
# -------------------------------------------------------------------------- #
def build_cast():
    suit = E.Suit
    return {
        "ren":  E.AnimeChar("ren",  {"H": (245, 130, 40), "S": (255, 215, 175), "T": (42, 64, 150),
                                     "P": (48, 48, 66), "B": (72, 52, 40), "K": (24, 22, 28)},
                              hair="spiky", iris=(200, 120, 40), voice_pitch="ren"),
        "yuki": E.AnimeChar("yuki", {"H": (234, 236, 248), "S": (252, 226, 200), "T": (52, 54, 64),
                                     "P": (30, 30, 44), "B": (40, 36, 40), "K": (24, 22, 28)},
                              hair="long", iris=(110, 190, 235), voice_pitch="yuki"),
        "mika": E.AnimeChar("mika", {"H": (245, 120, 170), "S": (255, 218, 185), "T": (186, 50, 78),
                                     "P": (60, 60, 90), "B": (90, 50, 66), "K": (24, 22, 28)},
                              hair="pony", iris=(210, 80, 150), voice_pitch="mika"),
        "kaba": E.AnimeChar("kaba", {"H": (44, 44, 54), "S": (192, 196, 206), "T": (110, 30, 42),
                                     "P": (40, 40, 48), "B": (30, 28, 30), "K": (20, 16, 22)},
                              hair="hawk", iris=(200, 60, 60), scale=1.12, voice_pitch="kaba"),
        "hood": E.AnimeChar("hood", {"H": (22, 22, 30), "S": (34, 34, 44), "T": (26, 26, 38),
                                     "P": (24, 24, 34), "B": (22, 22, 32), "K": (10, 10, 16)},
                              hair="long", iris=(90, 90, 120), scale=0.95, voice_pitch="narr"),
    }


# -------------------------------------------------------------------------- #
# LÄPPSYNK: röstens envelope -> per-frame öppen/stängd mun                   #
# -------------------------------------------------------------------------- #
def mouth_track(wave, fps=FPSS):
    a = np.abs(np.asarray(wave, dtype=np.float32))
    if a.size == 0:
        return np.zeros(0, bool)
    per = int(voicemod.SR / fps)
    n = (a.size + per - 1) // per
    pad = np.zeros(n * per, np.float32); pad[:a.size] = a
    amp = pad.reshape(n, per).max(axis=1)
    nz = amp[amp > 0.004]
    if nz.size < 2:
        return np.zeros(n, bool)
    thr = max(0.02, np.percentile(nz, 38))
    open_ = amp > thr
    # mjuka upp: undvik 1-frame blinkfladder
    for i in range(1, n - 1):
        if open_[i - 1] and open_[i + 1]:
            open_[i] = True
    return open_


# -------------------------------------------------------------------------- #
# SUBTITLES (namn-chip + piller)                                            #
# -------------------------------------------------------------------------- #
CHIP_COLS = {"ren": (245, 130, 40), "yuki": (200, 205, 225), "mika": (245, 130, 178),
             "kaba": (160, 70, 80), "narr": (140, 140, 160), "hood": (120, 120, 150)}
DISP = {"ren": "REN", "yuki": "YUKI", "mika": "MIKA", "kaba": "KABA",
        "narr": "", "hood": "???"}


def draw_sub(pil_img, text, who=None):
    d = ImageDraw.Draw(pil_img, "RGBA")
    t = E.ptext(text, scale=3, col=(255, 255, 255))
    pad_x, pad_y = 18, 12
    bw, bh = t.width + pad_x * 2 + 8, t.height + pad_y * 2
    x0 = (OUTW - bw) // 2
    y0 = OUTH - bh - 22
    d.rectangle([x0 + 4, y0 + 5, x0 + bw + 4, y0 + bh + 5], fill=(0, 0, 0, 110))
    d.rectangle([x0, y0, x0 + bw, y0 + bh], fill=(12, 12, 20, 200),
                outline=(90, 90, 120, 220), width=2)
    x_text = x0 + pad_x
    if who and DISP.get(who):
        chip = E.ptext(DISP[who], scale=2, col=(20, 20, 26))
        cw = chip.width + 16
        ch_col = CHIP_COLS.get(who, (150, 150, 150))
        d.rectangle([x0, y0 - chip.height - 10, x0 + cw + 10, y0 - 2], fill=ch_col + (255,))
        pil_img.alpha_composite(chip, (x0 + 8, y0 - chip.height - 6))
    pil_img.alpha_composite(t, (x_text + 4, y0 + pad_y))


# -------------------------------------------------------------------------- #
# EPISOD 1 – REGIBOKEN. Tider är scen-lokala (sekunder).                    #
# -------------------------------------------------------------------------- #
def episode_001(cast):
    """Returnerar scendirektiv-lista. Varje dict: env, dur, actors, lines,
    events (audio + fx), cam."""
    scenes = []
    # ============ 0) COLD OPEN – hamnen i regn, berättarröst ============== #
    scenes.append({
        "env": ("dock", {}), "dur": 11.6, "letterbox": 14, "fadein": 0.7,
        "cam": [{"kind": "zoom", "z": lambda t: 1.12 + t * 0.006, "focus": (160, 100)}],
        "actors": {
            "ren": {"track": [(0.0, -34, False), (2.4, 148, False), (11.6, 152, False)],
                    "blocks": [(0, 2.5, "mov"), (2.5, 99, "idle")],
                    "faces": [(3.1, "angry", False)]},
            "hood": {"track": [(6.4, 26, False), (11.6, 26, False)], "y_off": -78,
                     "blocks": [(6.4, 99, "idle")], "faces": []},
        },
        "lines": [(1.0, "narr", "Port Kaminari. Midnight. The sea stopped answering."),
                  (5.2, "ren", "Who turned off the ocean?"),
                  (8.3, "narr", "No boats. No gulls. Only the tower... counting.")],
        "audio": [(0.3, "boom", 0.45), (4.7, "riser", 0.35)],
    })
    # ============ 1) OP-TITELKORT ========================================= #
    scenes.append({"env": ("title", {"series": SERIES,
                                     "episode": "EPISODE 001 - The Night the Sea Went Silent"}),
                   "dur": 4.2, "audio": [(0.15, "boom", 0.9), (0.9, "riser", 0.7)]})
    # ============ 2) A-PART: DOJON – dörren ÖPPNAS ======================== #
    scenes.append({
        "env": ("dojo", {"door_t": 4.4, "bag_hits": (0.75, 1.6, 2.5)}), "dur": 13.4,
        "cam": [{"kind": "zoom", "z": lambda t: 1.0 if t < 5.2 else 1.18, "focus": (150, 96)}],
        "actors": {
            "ren": {"track": [(0, 84, False), (8.2, 120, False), (13.4, 122, False)],
                    "blocks": [(0.55, 0.82, "punch"), (0.82, 1.4, "idle"),
                               (1.4, 1.68, "punch"), (1.68, 2.3, "idle"),
                               (2.3, 2.58, "punch"), (2.58, 8.2, "idle"),
                               (8.2, 10.6, "point"), (10.6, 99, "idle")],
                    "faces": [(8.2, "angry", False)]},
            "mika": {"track": [(0, 288, False), (4.4, 244, True), (6.2, 172, True), (13.4, 174, True)],
                     "blocks": [(0, 4.4, "none"), (4.4, 6.3, "mov"), (6.3, 99, "point")],
                     "faces": []},
        },
        "lines": [(5.5, "mika", "Ren! Every lamp at the harbor just went out - at once!"),
                  (9.0, "ren", "Then we wake every single one back up.")],
        "audio": [(0.72, "thud", 0.8), (1.57, "thud", 0.8), (2.47, "thud", 0.9),
                  (4.4, "whoosh", 0.5), (8.9, "riser", 0.3)],
    })
    # ============ 3) A-PART: SKURKEN LANDAR (mini-cliffhanger) ============ #
    scenes.append({
        "env": ("dock", {}), "dur": 12.6,
        "cam": [{"kind": "zoom", "z": lambda t: 1.05 if t < 3.4 else 1.16, "focus": (190, 100)},
                {"kind": "shake", "t0": 3.2, "t1": 3.7, "amp": 4}],
        "actors": {
            "ren": {"track": [(0, -34, False), (1.6, 84, False), (12.6, 84, False)],
                    "blocks": [(0, 1.7, "mov"), (1.7, 7.6, "idle"), (7.6, 99, "point")],
                    "faces": [(3.6, "angry", False)]},
            "yuki": {"track": [(0, -70, False), (2.0, 40, False), (12.6, 40, False)],
                     "blocks": [(0, 2.1, "mov"), (2.1, 99, "idle")], "faces": []},
            "mika": {"track": [(0, -100, False), (2.4, 220, True), (12.6, 220, True)],
                     "blocks": [(0, 2.5, "mov"), (2.5, 99, "idle")], "faces": []},
            "kaba": {"track": [(0, 226, True), (12.6, 226, True)],
                     "blocks": [(0, 2.0, "none"), (2.0, 3.55, "hurt"), (3.55, 8.6, "guard"),
                                (8.6, 99, "point")],
                     "faces": [(4.2, "angry", False)],
                     "drop": (3.2, -180)},
        },
        "lines": [(4.6, "kaba", "The signal tower answers to ME now. Crawl home, kids."),
                  (8.6, "ren", "Kids?! KIDS?!"),
                  (10.6, "kaba", "Thunder belongs to the strong, little spark.")],
        "audio": [(3.2, "boom", 0.95), (4.5, "riser", 0.4), (10.5, "riser", 0.55)],
        "dust_at": (3.2, 226),
    })
    # ============ 4) EYECATCH (halvtidskorten!) =========================== #
    scenes.append({"env": ("eyecatch", {"who": "ren"}), "dur": 1.5,
                   "audio": [(0.05, "sparkle", 0.8)]})
    scenes.append({"env": ("eyecatch", {"who": "kaba"}), "dur": 1.5,
                   "audio": [(0.05, "boom", 0.5)]})
    # ============ 5) B-PART: FIGHT! ======================================= #
    scenes.append({
        "env": ("dock", {}), "dur": 21.4, "lights_on_at": 15.4,
        "cam": [{"kind": "zoom",
                 "z": lambda t: 1.1 if t < 5.0 else (1.25 if t < 12.9 else 1.08),
                 "focus": (170, 96)},
                {"kind": "shake", "t0": 0.75, "t1": 1.15, "amp": 4},
                {"kind": "shake", "t0": 12.3, "t1": 12.95, "amp": 6}],
        "actors": {
            "ren": {"track": [(0, 84, False), (1.0, 56, False), (2.2, 60, False),
                              (5.0, 96, False), (11.9, 96, False), (12.15, 208, False),
                              (13.0, 210, False), (21.4, 210, False)],
                    "blocks": [(0, 0.75, "idle"), (0.75, 2.1, "hurt"), (2.1, 4.9, "idle"),
                               (4.9, 6.1, "point"), (6.1, 11.9, "idle"),
                               (11.9, 12.15, "mov"), (12.15, 12.5, "punch"),
                               (12.5, 12.75, "idle"), (12.75, 13.05, "punch"),
                               (13.05, 99, "idle")],
                    "faces": [(0.75, "x", True), (2.1, "sad", True), (4.9, "angry", False),
                              (16.0, "spark", False)]},
            "yuki": {"track": [(0, 40, False), (2.3, 150, False), (3.4, 168, False),
                               (21.4, 168, False)],
                     "blocks": [(0, 2.2, "idle"), (2.2, 2.6, "punch"), (2.6, 99, "guard")],
                     "faces": [(2.2, "angry", False)]},
            "mika": {"track": [(0, 226, True), (10.0, 110, True), (21.4, 112, True)],
                     "blocks": [(0, 6.4, "guard"), (6.4, 8.6, "mov"), (8.6, 99, "idle")],
                     "faces": [(15.4, "spark", False)]},
            "kaba": {"track": [(0, 230, True), (4.4, 236, True), (13.1, 236, True),
                               (13.65, 340, True), (21.4, 360, True)],
                     "blocks": [(0, 0.75, "guard"), (0.75, 1.0, "punch"),
                                (1.0, 2.3, "guard"), (2.3, 3.4, "hurt"), (3.4, 12.9, "guard"),
                                (12.9, 13.5, "hurt"), (13.5, 99, "hurt")],
                     "faces": [(2.3, "x", True), (3.4, "angry", False), (12.3, "x", True)]},
        },
        "lines": [(1.2, "ren", "Rgh- cheap shot!"),
                  (4.0, "yuki", "My turn, spark-stealer."),
                  (5.2, "ren", "Mika said wake them up..."),
                  (8.3, "ren", "SO WE WAKE THEM UP."),
                  (15.8, "mika", "Look - the harbor is breathing again!"),
                  (18.9, "ren", "Whoever dimmed it owes me a sandwich.")],
        "audio": [(0.75, "boom", 0.85), (2.3, "whoosh", 0.9), (2.55, "thud", 0.7),
                  (4.9, "riser", 0.75), (8.3, "riser", 0.9), (11.9, "whoosh", 0.8),
                  (12.2, "thud", 0.9), (12.4, "boom", 1.0), (12.8, "boom", 0.9),
                  (15.4, "fanfare", 0.8), (15.6, "sparkle", 0.6)],
        "fx": [
            {"kind": "impact", "t": 0.75, "x": 74, "y": 92, "invert": True},
            {"kind": "kiai", "t": 0.75, "x": 74, "y": 92},
            {"kind": "slash", "t": 2.3, "x": 196, "y": 92},
            {"kind": "kiai", "t": 2.55, "x": 212, "y": 92},
            {"kind": "aura", "t0": 4.9, "t1": 11.9, "x_track": "ren", "hue": "gold"},
            {"kind": "impact", "t": 12.3, "x": 226, "y": 90, "invert": True, "word": "BAAM"},
            {"kind": "kiai", "t": 12.3, "x": 226, "y": 90},
            {"kind": "speedwin", "t0": 11.9, "t1": 12.6, "cx": 170, "cy": 92},
            {"kind": "speedwin", "t0": 12.75, "t1": 13.3, "cx": 226, "cy": 90},
        ],
        "dust_at": (13.5, 246),
    })
    # ============ 6) C-PART TEASE ========================================= #
    scenes.append({
        "env": ("dock", {"lights_on": True}), "dur": 7.2, "letterbox": 15,
        "cam": [{"kind": "zoom", "z": lambda t: 1.1 + min(1.0, t / 6.0) * 0.55,
                 "focus": (24, 70)}],
        "actors": {
            "hood": {"track": [(0, 26, False), (7.2, 26, False)], "y_off": -78,
                     "blocks": [(0, 2.2, "idle"), (2.2, 99, "point")], "faces": []},
            "ren": {"track": [(0, 150, True), (7.2, 150, True)],
                    "blocks": [(0, 99, "idle")], "faces": [(2.4, "wide", False)]},
        },
        "lines": [(1.2, "narr", "On the lighthouse, someone applauded. Slowly."),
                  (4.4, "ren", "...I heard that. Show yourself!")],
        "audio": [(2.2, "boom", 0.4)],
    })
    # ============ 7) NEXT EPISODE (jikai yokoku) ========================== #
    scenes.append({
        "env": ("preview", {"no": 2, "title": "The Girl in the Fog",
                            "lines": ["She dodged thunder once. Once was enough.",
                                      "Ren loses his sandwich. War is declared.",
                                      "Yuki draws his sword on the mist itself."]}),
        "dur": 6.4, "fadeout": 0.8,
        "lines": [(0.4, "narr", "Next time on Volt Breaker!")],
        "audio": [(0.2, "sparkle", 0.5)],
    })
    return scenes


# -------------------------------------------------------------------------- #
# RENDERER                                                                  #
# -------------------------------------------------------------------------- #
class Renderer:
    def __init__(self, cast):
        self.cast = cast

    # -- per scen byggda aktörer (Actor = poser + track + faces + mun) ------
    def _mk_actors(self, scene, mouths):
        actors = {}
        for name, a in scene.get("actors", {}).items():
            act = E.Actor(self.cast[name], a["blocks"], E.Track(a["track"]), a.get("faces"))
            act.y_off = a.get("y_off", 0)
            act.drop = a.get("drop")
            act.mouth = mouths.get(name, np.zeros(0))
            act.mouth_off = 0
            actors[name] = act
        return actors

    def scene_frame(self, scene, env, actors, local_t):
        # miljö
        if isinstance(env, E.DockNight):
            lights = scene.get("lights_on_at") is not None and local_t >= scene["lights_on_at"] \
                     or getattr(env, "lights_on", False)
            img = env.frame(local_t, lights)
        else:
            img = env.frame(local_t)
        d = ImageDraw.Draw(img, "RGBA")
        # damm vid landning
        if scene.get("dust_at"):
            dt, dx = scene["dust_at"]
            if dt <= local_t <= dt + 0.8:
                E.dust(img, dx, 140)
        # aktörer
        order = sorted(actors.items(), key=lambda kv: kv[1].track.at(local_t)[0])
        for name, act in order:
            pose = act.pose_at(local_t)
            if pose == "none":
                continue
            x, flip = act.track.at(local_t)
            if pose == "mov":
                pose = "walk1" if int(local_t * 6) % 2 == 0 else "walk2"
            # auto-blink (2.7-4.1s intervaller, seedat per namn)
            eyes, bruise = act.face_at(local_t)
            rng = random.Random(hash(name) & 0xffff)
            cyc = 2.4 + rng.random() * 1.9
            ph = rng.random() * cyc
            if eyes == "normal" and ((local_t + ph) % cyc) < 0.13:
                eyes = "blink"
            # mun: läppsynk har företräde, annars normal/stängd
            mouth = "closed"
            fi = int(local_t * FPSS)
            if fi < act.mouth.size and act.mouth[fi]:
                mouth = "open"
            # aura bakom karaktären hanteras av fx nedan (ordning: aura pre-actors)
            rig_pose = {"mov": "walk", "walk1": "walk", "walk2": "walk"}.get(pose, pose)
            ch_img = act.char.full(rig_pose, local_t, eyes, mouth, bruise)
            if flip:
                from PIL import ImageOps as _IO
                ch_img = _IO.mirror(ch_img)
            bx = x - ch_img.width // 2
            by = E.GROUND - (E.GROUND_CV if hasattr(E, "GROUND_CV") else ch_img.height) + act.y_off
            if act.drop and local_t < act.drop[0]:
                p = max(0.0, local_t / act.drop[0])
                by += int((1 - (p * p)) * act.drop[1])
            if eyes == "x" and pose == "hurt":      # knock-vibration
                bx += int(math.sin(local_t * 60) * 1.5)
            img.alpha_composite(ch_img, (bx, by))
            # idle-andning
        # fx-lager
        for fx in scene.get("fx", []):
            k = fx["kind"]
            if k == "impact" and fx["t"] <= local_t <= fx["t"] + 0.25:
                img = E.impact_flash(img, fx["t"], local_t, invert=fx.get("invert", False))
                d = ImageDraw.Draw(img, "RGBA")
                if fx.get("word"):
                    E.word_burst(img, fx["word"], fx["x"], fx["y"] - 30, fx["t"], local_t)
            elif k == "kiai" and fx["t"] <= local_t <= fx["t"] + 0.45:
                E.kiai(img, fx["x"], fx["y"])
            elif k == "slash":
                E.slash(img, fx["x"], fx["y"], fx["t"], local_t)
            elif k == "aura" and fx["t0"] <= local_t <= fx["t1"]:
                ax = actors[fx["x_track"]].track.at(local_t)[0] if fx.get("x_track") else fx["x"]
                E.aura(img, ax, E.GROUND, 96, local_t, fx.get("hue", "violet"))
                # rit energi OM igen efter aktörer -> vi kompositörer aura under/över
            elif k == "speedwin" and fx["t0"] <= local_t <= fx["t1"]:
                E.speedlines(img, fx["cx"], fx["cy"])
        return img   # logisk 320x180 UBEN undertext (ritas efter kamera)

    def card_frame(self, card, local_t):
        return card.frame(local_t).resize((OUTW, OUTH), NEAREST)


# -------------------------------------------------------------------------- #
# MAIN                                                                      #
# -------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ep", type=int, default=1)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cast = build_cast()
    scenes = episode_001(cast) if args.ep == 1 else episode_001(cast)

    # ---------------- LJUD: röster + envelope-läppar ----------------------
    np.random.seed(0)
    total = sum(s["dur"] for s in scenes)
    print(f"   ▶ {SERIES}  episod {args.ep}  ({total:.1f}s, {len(scenes)} segment)")
    mix = np.zeros(int((total + 0.6) * voicemod.SR), dtype=np.float32)

    def put(t0, arr, vol=1.0):
        off = int(t0 * voicemod.SR)
        seg = arr.astype(np.float32) * vol
        end = min(len(mix), off + len(seg))
        if end > off:
            mix[off:end] += seg[: end - off]

    # musik
    track = musicmod.chip(77, int(total + 1), bpm=120)
    put(0.0, track, 0.62)

    # per scen: röster+läppar+sfx
    scene_starts, cur = [], 0.0
    mouth_per = {}          # (scene_idx, name) -> bool array lokala frames
    lines_global = []       # (scene_idx, who, text, t0_local, t1_local)
    for i, s in enumerate(scenes):
        scene_starts.append(cur)
        local, tcur = [], 0.0
        for (lt, who, text) in sorted(s.get("lines", []), key=lambda l: l[0]):
            sp = cast.get(who, E.PXChar("n", {"H": (0, 0, 0), "S": (0, 0, 0), "T": (0, 0, 0),
                                              "P": (0, 0, 0), "B": (0, 0, 0), "A": (0, 0, 0)},
                                        "spiky")).voice_pitch
            if who == "narr" or who == "hood":
                sp = "narr"
            arr = voicemod.speak(text, species=sp, seed=301 * 57 + i * 13 + int(lt * 10))
            put(cur + lt, arr, 0.9)
            dur = len(arr) / voicemod.SR
            lines_global.append((i, who, text, lt, lt + max(dur, 0.5) + 1.1))
            if who in ("ren", "yuki", "mika", "kaba"):
                mo = mouth_track(arr)
                pre = np.zeros(int(lt * FPSS), bool)
                post = np.zeros(int((s["dur"]) * FPSS) - pre.size - mo.size, bool)
                if post.size < 0:
                    post = np.zeros(0, bool)
                full = np.concatenate([pre, mo, post])
                if (i, who) in mouth_per:
                    mouth_per[(i, who)] |= full[: len(mouth_per[(i, who)])]
                else:
                    mouth_per[(i, who)] = full
        for (lt, name, vol) in s.get("audio", []):
            fn = getattr(sfxmod, name, None)
            if fn:
                put(cur + lt, fn(), vol)
        cur += s["dur"]

    # normalisera
    peak = np.max(np.abs(mix)) or 1.0
    if peak > 0.98:
        mix *= 0.98 / peak

    # ---------------- VIDEO-RENDER -----------------------------------------
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    out = args.out or f"/home/user/pixeltube/out/volt-breaker-ep{args.ep:03d}.mp4"
    os.makedirs(os.path.dirname(out), exist_ok=True)

    renderer = Renderer(cast)
    t0 = time.time()
    tmp_silent = out.replace(".mp4", "_silent.mp4")

    # steg 1: bildrender till silent-mp4; ljudet muxas i steg 2
    pipe = subprocess.Popen(
        [ffmpeg, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OUTW}x{OUTH}",
         "-r", str(FPSS), "-i", "-", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-preset", "medium", "-crf", "18", tmp_silent],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    lwins_all = {}
    for (ii, who, text, t0, t1) in lines_global:
        lwins_all.setdefault(ii, []).append((who, text, t0, t1))
    for kk in range(len(scenes)):
        lwins_all.setdefault(kk, [])

    nframes = int(total * FPSS)
    for f in range(nframes):
        tg = f / FPSS
        idx = 0
        for j, st in enumerate(scene_starts):
            if tg >= st:
                idx = j
        s = scenes[idx]
        lt = tg - scene_starts[idx]
        env_kind, env_args = s["env"]
        if not hasattr(Renderer, "_envcache"):
            Renderer._envcache = {}
        ck = idx
        if ck not in Renderer._envcache:
            if env_kind == "dock":
                Renderer._envcache[ck] = E.DockNight(seed=301 + idx, **{k: v for k, v in env_args.items() if k != "rain"})
            elif env_kind == "dojo":
                Renderer._envcache[ck] = E.DojoInterior(seed=301 + idx, **env_args)
            elif env_kind == "title":
                Renderer._envcache[ck] = E.TitleCard(env_args["series"], env_args["episode"], seed=301)
            elif env_kind == "eyecatch":
                who = env_args["who"]
                Renderer._envcache[ck] = E.EyecatchCard(pxchar=cast[who], series=SERIES,
                                                        catchword=("THUNDER SEASON 1" if who == "ren"
                                                                   else "static grins back"),
                                                        seed=301, dark=(who != "ren"))
            elif env_kind == "preview":
                Renderer._envcache[ck] = E.PreviewCard(env_args["no"], env_args["title"], env_args["lines"], seed=301)
        env = Renderer._envcache[ck]
        if not hasattr(Renderer, "_lwins"):
            Renderer._lwins = {}
        mouths = {name: mouth_per.get((idx, name), np.zeros(0)) for name in s.get("actors", {})}
        if env_kind in ("dock", "dojo"):
            if not hasattr(Renderer, "_actcache"):
                Renderer._actcache = {}
            if ck not in Renderer._actcache:
                Renderer._actcache[ck] = renderer._mk_actors(s, mouths)
            actors = Renderer._actcache[ck]
            for nm, ac in actors.items():
                ac.mouth = mouths.get(nm, np.zeros(0))
            lwins = [(who, text, t0, t1) for (ii, who, text, t0, t1) in lines_global if ii == idx]
            small = renderer.scene_frame(s, env, actors, lt)
        else:
            small = env.frame(lt)          # kort lever redan på logisk nivå
        # ---- kamera & letterbox på logisk nivå (320x180) -------------------
        if s.get("cam") or s.get("letterbox"):
            ops = list(s.get("cam", []))
            if s.get("letterbox"):
                ops.append({"kind": "letterbox", "h": s["letterbox"]})
            small = E.apply_camera(small, lt, ops)
        img = small.resize((OUTW, OUTH), NEAREST)
        # ---- CUT-IN närbild under replik (anime-reaktionsklipp) -------------
        cutwho, cutwin = None, None
        if env_kind in ("dock", "dojo"):
            for who, text, t0, t1 in lwins_all[idx]:
                if t0 <= lt <= t1 and who in cast and who not in ("narr", "hood"):
                    cutwho, cutwin = who, (t0, t1)
                    break
        if cutwho:
            side = (lwins_all[idx][0][0] != cutwho)
            img = E.cutin(img, cast[cutwho], lt - cutwin[0], side, cutwho,
                          CHIP_COLS.get(cutwho, (150, 150, 150)))
        # ---- undertext EFTER kamera (aldrig croppad av zoom) ---------------
        if env_kind in ("dock", "dojo"):
            for who, text, t0, t1 in lwins_all[idx]:
                if t0 <= lt <= t1:
                    draw_sub(img, text, who)
                    break
        # fades
        if s.get("fadein") and lt < s["fadein"]:
            p = lt / s["fadein"]
            img = Image.blend(Image.new("RGBA", img.size, (0, 0, 0, 255)), img, p)
        if s.get("fadeout") and lt > s["dur"] - s["fadeout"]:
            p = max(0.0, (s["dur"] - lt) / s["fadeout"])
            img = Image.blend(Image.new("RGBA", img.size, (0, 0, 0, 255)), img, p)
        pipe.stdin.write(img.convert("RGB").tobytes())
        if f % 120 == 0:
            print(f"\r   renderar {100*f/nframes:5.1f}%", end="", flush=True)
    pipe.stdin.close(); pipe.wait()
    print(f"\r   renderar 100% ({time.time()-t0:.0f}s)")

    # steg 2: ljud-wav + mux
    wav = out.replace(".mp4", ".wav")
    musicmod.save_wav16(wav, mix)
    subprocess.run([ffmpeg, "-y", "-i", tmp_silent, "-i", wav, "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", out],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for junk in (tmp_silent, wav):
        try: os.remove(junk)
        except OSError: pass
    size = os.path.getsize(out) / 1e6
    print(f"   ✅ KLART: {out} ({size:.1f} MB)")
    meta = {"title": f"{SERIES} - Episode {args.ep:03d}", "seed": 301,
            "madeForKids": False, "language": "en"}
    json.dump(meta, open(out.replace(".mp4", ".json"), "w"), indent=2)


if __name__ == "__main__":
    main()
