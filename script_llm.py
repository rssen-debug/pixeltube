# -*- coding: utf-8 -*-
"""
script_llm.py – Lokal LLM (Qwen via Ollama på CPU) skriver nya avsnitt
med FAST rollista och verb som motorn animerar direkt.

Setup:
    1. https://ollama.com/download
    2. ollama pull qwen2.5:3b
    3. python make_video.py --llm
       python make_video.py --idea "en rädd pizza" --cast "doris,apan"
"""
import json
import random
import urllib.request

import engine
from story import SETTINGS, normalize_scenes

OLLAMA_URL = "http://localhost:11434/api/generate"

CAST_PAIRS = [("doris", "apan"), ("boris", "kanin"), ("leo", "nova"),
              ("doris", "boris"), ("trix", "apan")]

FUN_IDEAS = [
    "a heist to steal back the world's largest diamond from laser-guarded vault",
    "a routine spy mission ruined by a very angry crab",
    "a space rescue where the escape rocket only has one seat",
    "a deep-sea dive to defuse a singing coral mine",
    "a snow mission where the snowball drones have formed a union",
    "a candy-vault break-in staged by two suspects in love with cake",
    "a beach fortress defense against an army of smug crabs",
    "a jungle chase where the getaway vehicle is a frog",
]

PROMPT_TMPL = """You write scenes for PixelTube: a 16+ pixel-animation mission series,
comedy-action with cool agents. Think heist movies, not bedtime stories.
Series cast (use EXACTLY these names in every scene): {cast_sv}.

Format - reply with VALID JSON only, no markdown:
{{"title_en": "...",
 "scenes": [
   {{"setting": "forest", "en": "...", "reaction": "!", "props": "mushroom"}}
 ]}}

Rules:
- Exactly {n} scenes. Max 22 English words per scene. snappy, funny, cinematic.
- setting MUST be one of: {settings}
- COLD OPEN: scene 1 starts MID-CHAOS (pursuit, explosion, consequence of
  something the cast already did). Never introduce anyone. No "meet the agents".
- FLAW ENGINE: the conflict must be CAUSED by a cast member's personality
  (overconfidence / greed / cowardice / snack obsession / perfectionism /
  recklessness / grumpiness), never by bad luck.
- MYSTERY: exactly one scene has "mystery": true and contains a cryptic
  untouched clue about "the spiral" or "the Watcher". Never explain it.
- CLIFFHANGER: the final scene must end on a question, absurd reveal, or
  glitch – never a cozy resolution. Built for next-episode swipes.
- HUMOR: exaggerate (faceplants, fire, freezes) instead of explaining jokes.
- ACTIONS are written as VERBS that the animation engine plays instantly.
  Allowed verbs: jump/leap, run/sprint/dash/bolt, dance/boogie, spin/twirl,
  hit/punch/smack/bonk, duck/dodge, wave/salute, sleep/snooze, walk/sneak/stroll,
  fire: blasts/roasts/ignites, shock: gasps/yelps/freezes, fall: trips/faceplants/topples,
  flex: flexes/poses/struts.
  Examples: "Doris leapt onto the vault." / "Rico ducked just in time." /
  "They sprinted back together."
  Use at least 3 explicit action verbs, each within 3 words of a cast name,
  plus at least one group action ("they ... together" / "both ...").
- reaction MUST be one of: "!", "?", "♥", "★" - or null.
- props: 0-3 from: mushroom, house, rocket, snowman, fish, crab, shell, cake,
  ice cream, balloon, star, gem, chest, berries, frog, flower, rainbow.
  snowman only in snow. fish only in underwater.
- Tone: deadpan spy-comedy. Confident agents, absurd obstacles, zero fear.
- No copyrighted characters. English only.
Mission brief: {idea}
"""


def _clean_json(txt):
    t = txt.strip()
    if "```" in t:
        for p in t.split("```"):
            p = p.strip().lstrip("json").strip()
            if p.startswith("{"):
                t = p
                break
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        raise ValueError("LLM:en svarade inte med JSON")
    return json.loads(t[i:j + 1])


def _coerce(data, seed, lang, idea, cast):
    scenes = []
    for s in data.get("scenes", []):
        if not isinstance(s, dict):
            continue
        setting = s.get("setting", "forest")
        if setting not in SETTINGS:
            setting = "forest"
        sv, en = str(s.get("sv", "")).strip(), str(s.get("en", "")).strip()
        text = sv if lang == "sv" else (en or sv)
        if len(text) < 4:
            continue
        scenes.append({"setting": setting, "text": text, "action": None,
                       "reaction": s.get("reaction"), "props": s.get("props")})
    if not 3 <= len(scenes) <= 14:
        raise ValueError(f"LLM gav {len(scenes)} scener (vill ha 3-14)")

    names = [engine.resolve_character(c)[3] for c in cast]
    title = (data.get(f"title_{lang}") or data.get("title_sv")
             or data.get("title_en") or idea or "Ett nytt äventyr")
    beats = "\n".join("• " + s["text"] for s in scenes)
    description = (f"{title} ⚡\n\nStarring {' & '.join(names)}.\n\n{beats}\n\n"
                   "Mission written by a local LLM (Qwen), animated 100% by code.\n\n"
                   "#pixelanimation #cartoon #animatedseries")
    return {"title": title, "name": names[0], "cast": cast, "scenes": scenes,
            "tags": ["pixel animation", "animated series", "AI story", "cartoon"],
            "description": description, "seed": seed, "lang": lang}


def llm_story(seed, lang="en", idea=None, model="qwen2.5:3b", n_scenes=6,
              cast=None, url=OLLAMA_URL, timeout=300):
    rng = random.Random(seed)
    cast = list(cast) if cast else list(rng.choice(CAST_PAIRS))
    if not idea:
        idea = rng.choice(FUN_IDEAS)
    cast_sv = ", ".join(engine.resolve_character(c)[3] for c in cast)
    prompt = PROMPT_TMPL.format(n=n_scenes, settings=", ".join(SETTINGS),
                                idea=idea, cast_sv=cast_sv)

    body = json.dumps({"model": model, "prompt": prompt, "stream": False,
                       "format": "json",
                       "options": {"temperature": 0.95, "num_predict": 1400}}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    print(f"  🤖 Frågar {model} om en saga med {cast_sv} (idé: ”{idea}”)…")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        payload = json.loads(r.read().decode())
    return _coerce(_clean_json(payload["response"]), seed, lang, idea, cast)
