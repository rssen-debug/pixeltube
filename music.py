# -*- coding: utf-8 -*-
"""
music.py – Generativ chiptune/8-bit-musik med numpy.
Varje seed ger en egen melodi i A-dur pentatonisk -> alltid glad stämning,
och musiken är 100 % din egen (inget upphovsrättstrassel på YouTube).
"""
import random
import wave

import numpy as np

SR = 44100


def _midi(m):
    return 440.0 * 2.0 ** ((m - 69) / 12.0)


def _env(n, atk=0.006, rel=0.05):
    e = np.ones(n, dtype=np.float32)
    a = max(1, int(atk * SR))
    r = max(1, int(rel * SR))
    if a < n:
        e[:a] = np.linspace(0, 1, a)
    if r < n:
        e[-r:] = np.linspace(1, 0, r)
    return e


def square(freq, dur):
    n = max(1, int(SR * dur))
    t = np.arange(n) / SR
    return (np.sign(np.sin(2 * np.pi * freq * t)) * _env(n)).astype(np.float32)


def tri(freq, dur):
    n = max(1, int(SR * dur))
    t = np.arange(n) / SR
    ph = (t * freq) % 1.0
    return ((2 * np.abs(2 * ph - 1) - 1) * _env(n, 0.01, 0.08)).astype(np.float32)


def chip(seed, seconds, bpm=116):
    """Returnerar float32-array (mono, 44100 Hz) med en glad chiptune-låt."""
    rng = random.Random(seed)
    npr = np.random.default_rng(seed)
    scale = [57, 61, 64, 66, 71, 73, 76, 78, 81]   # A-dur pentatonisk
    roots = [45, 40, 42, 38]                        # A – E – F# – D
    eighth = 60.0 / bpm / 2.0
    total = int(seconds * SR) + SR

    lead = np.zeros(total, dtype=np.float32)
    bass = np.zeros(total, dtype=np.float32)
    hats = np.zeros(total, dtype=np.float32)

    idx = max(0, min(len(scale) - 1, len(scale) // 2 + rng.randint(-2, 2)))
    pos = 0
    i = 0
    while pos < total:
        chord = roots[(i // 8) % 4]
        bn = tri(_midi(chord + (12 if i % 2 else 0)),
                 min(eighth * 0.9, (total - pos) / SR))
        bass[pos:pos + len(bn)] += bn * 0.9

        if rng.random() > 0.10:                     # melodi
            if rng.random() < 0.55:
                idx = max(0, min(len(scale) - 1, idx + rng.choice([-2, -1, 1, 2])))
            ln = eighth * (1.9 if rng.random() < 0.15 else 0.95)
            mn = square(_midi(scale[idx] + 12), min(ln, (total - pos) / SR))
            lead[pos:pos + len(mn)] += mn

        if i % 2 == 1:                              # enkel "hihat"
            n = int(SR * 0.04)
            if pos + n < total:
                hats[pos:pos + n] += (npr.uniform(-1, 1, n)
                                      * np.exp(-np.linspace(0, 7, n))).astype(np.float32)
        pos += int(round(eighth * SR))
        i += 1

    mix = lead * 0.30 + bass * 0.30 + hats * 0.05
    mix = (np.tanh(mix * 1.25) * 0.85).astype(np.float32)
    return mix[:int(seconds * SR)]


def save_wav16(path, data):
    data = np.clip(data, -1.0, 1.0)
    pcm = (data * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
