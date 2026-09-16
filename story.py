# -*- coding: utf-8 -*-
"""
story.py – Episode templates: 16+ mission-comedy, fully verb-driven.

COHERENCE RULES:
  • Every episode has a fixed cast. Characters are identical in every scene
    and every episode – engine.resolve_character() guarantees it.
  • VERBS IN THE TEXT DRIVE THE ANIMATION:
      "Doris jumps"               -> Doris plays jump
      "Rico ducked"               -> Rico plays duck
      "Rico punched the drone"    -> Rico plays hit (+ POW star)
      "They sprinted together"    -> EVERYONE plays run
  • Templates have structure: setup (meet/mission) -> middle (problems,
    chaos) -> end (victory dance / sleep).
"""
import random

NAMES = ["leo", "nova", "trix", "puff", "milo", "zia"]
SETTINGS = ["forest", "night", "beach", "space", "snow", "underwater", "candy"]

# verb -> action. Synonyms welcome; cooler writing = better episodes.
VERBS = {
    "jump":  ["jump", "jumps", "jumped", "leap", "leaps", "leaped", "leapt",
              "bounced", "hopped"],
    "run":   ["run", "runs", "ran", "rush", "rushes", "rushed", "sprint",
              "sprints", "sprinted", "dash", "dashes", "dashed", "bolt",
              "bolts", "bolted", "fled", "charge", "charged"],
    "dance": ["dance", "dances", "danced", "boogie", "boogied", "groove", "grooved"],
    "spin":  ["spin", "spins", "spun", "spinning", "twirl", "twirls", "twirled"],
    "hit":   ["hit", "hits", "punch", "punches", "punched", "smack", "smacked",
              "bonk", "bonks", "bonked", "whacked", "kicked", "slammed"],
    "duck":  ["duck", "ducks", "ducked", "dodged", "crouch", "crouched"],
    "wave":  ["wave", "waves", "waved", "saluted", "salute"],
    "sleep": ["sleep", "sleeps", "slept", "snooze", "snoozed", "napped",
              "snores", "snored", "snuck*never"],
    "walk":  ["walk", "walks", "walked", "sneak", "sneaks", "sneaked",
              "snuck", "stroll", "strolled", "slunk", "crept"],
}
GROUP_WORDS = [" they ", " both ", " everyone ", " the duo ", " the two ",
               " together", " duo "]


def parse_actions(text, cast_names):
    """Find who does what in a line. Returns {cast_name: action|None}.

    Matches WHOLE words ("wound" never counts as "run") and picks the verb
    standing CLOSEST to the character's name – so "'RUN,' yelled Doris...
    Rico ducked" assigns run->Doris, duck->Rico. Group words (they, both,
    together) apply the verb to every cast member without one.
    """
    import re

    import engine
    low = (text or "").lower()
    padded = " " + low + " "
    words = [re.sub(r"[^\wåäöüé'-]", "", w) for w in low.split()]
    verb_at = {}
    for i, w in enumerate(words):
        for action, verbs in VERBS.items():
            if w in verbs:
                verb_at.setdefault(i, action)

    found = {}
    for name in cast_names:
        found[name] = None
        aliases = engine.alias_group(name)
        best = None
        for iw, w in enumerate(words):
            if w not in aliases:
                continue
            for vi, action in verb_at.items():
                dist = abs(vi - iw)
                if dist <= 6 and (best is None or dist < best[0]):
                    best = (dist, action)
        if best:
            found[name] = best[1]

    if verb_at and any(g in padded for g in GROUP_WORDS):
        action = next(iter(verb_at.values()))
        for name in cast_names:
            if found[name] is None:
                found[name] = action
    return found


# ---------------------------------------------------------------------------
# MISSION TEMPLATES – every verb in the text animates a character.
# Settings: forest, night, beach, space, snow, underwater, candy
# Reactions: ! ? ♥ ★
# Props keywords: gem, chest, rocket, snowman, fish, crab, shell, cake,
#                 ice cream, balloon, star, berries, frog, flower, rainbow,
#                 mushroom, house
# ---------------------------------------------------------------------------
TEMPLATES = [
    {
        "title": "The Crystal Heist", "cast": ["doris", "apan"],
        "scenes": [
            {"setting": "beach",
             "text": "03:00 hours. Rico spotted the glowing gem first - someone hid it in a shell by the sea.",
             "reaction": "!", "props": "ädelsten, snäcka"},
            {"setting": "beach",
             "text": "'Back off, it's mine,' grunted Doris, but Rico dashed ahead, faster than the tide."},
            {"setting": "forest",
             "text": "They sprinted through the jungle together, past vines and one very offended frog.",
             "props": "groda, svamp"},
            {"setting": "forest",
             "text": "Doris leapt onto the crystal platform. Rico ducked as the alarm lasers woke up. Classic Tuesday."},
            {"setting": "forest",
             "text": "Rico punched the security drone right in its smug little face. POW."},
            {"setting": "night",
             "text": "Mission complete. They danced on the rooftop until the moon went to sleep.",
             "reaction": "★"},
        ],
    },
    {
        "title": "Deep Cover: Operation Splash", "cast": ["doris", "boris"],
        "scenes": [
            {"setting": "beach",
             "text": "Boris had one job: make the crab talk. The crab was not in the mood.",
             "reaction": "?", "props": "krabba"},
            {"setting": "beach",
             "text": "'We do it the fun way,' said Doris, and jumped straight off the dock. SPLASH."},
            {"setting": "underwater",
             "text": "Under the waves they sneaked past the fish patrol together. Total silence. Ish.",
             "props": "fisk"},
            {"setting": "underwater",
             "text": "A gold fish spun three times: the secret signal. Boris waved back like a true professional.",
             "props": "fisk"},
            {"setting": "underwater",
             "text": "Doris smacked the lava-eel lamp into darkness. Beautiful, professional darkness."},
            {"setting": "night",
             "text": "Report filed. They both slept like rocks. Classified rocks."},
        ],
    },
    {
        "title": "Neon Jungle Run", "cast": ["leo", "nova"],
        "scenes": [
            {"setting": "night",
             "text": "Midnight in the neon jungle. Nova stretched. Leo held the map upside down again."},
            {"setting": "forest",
             "text": "'RUN!' They sprinted through the pines together as the alarm howled behind them."},
            {"setting": "forest",
             "text": "Leo leapt the ravine. Nova spun through the laser web. Nobody even blinked."},
            {"setting": "forest",
             "text": "The mushroom guards formed a wall. Nova bonked the biggest one. End of discussion.",
             "props": "svamp"},
            {"setting": "night",
             "text": "They danced under the stars. Victory rhythm. Zero shame.", "reaction": "★"},
            {"setting": "night",
             "text": "Then they both slept. Even legends need eight hours."},
        ],
    },
    {
        "title": "Frost Protocol", "cast": ["kurre", "stina"],
        "scenes": [
            {"setting": "snow",
             "text": "Rule one of the Frost Protocol: look adorable, act unstoppable. Ash and Pix wrote it."},
            {"setting": "snow",
             "text": "The snowman was obviously bait. Pix waved at it politely. Ash was not fooled.",
             "props": "snögubbe"},
            {"setting": "snow",
             "text": "Snowball drones incoming! They dashed between the pines together, ears flat in the wind."},
            {"setting": "snow",
             "text": "Ash ducked. A snowball screaming overhead hit a pine instead. Splat."},
            {"setting": "snow",
             "text": "Pix leapt and smacked the last drone clean out of the sky. That is a ten."},
            {"setting": "snow",
             "text": "Protocol complete. They both snoozed in a frozen high-five position."},
        ],
    },
    {
        "title": "Space Riot", "cast": ["puff", "milo"],
        "scenes": [
            {"setting": "night",
             "text": "A rocket crashed the garden party. Milo saluted. Puff asked what the red button does.",
             "props": "raket", "reaction": "?"},
            {"setting": "space",
             "text": "Zero gravity. They spun together like two confused galaxies."},
            {"setting": "space",
             "text": "The moon-cats guarded the star gem. Puff danced at them. Nobody knows why. It worked.",
             "props": "ädelsten"},
            {"setting": "space",
             "text": "Milo sneaked in and grabbed the gem. Stealth level: professional."},
            {"setting": "space",
             "text": "They bolted back to the rocket as the moon-cats screamed in meow-minor. Together. Fast."},
            {"setting": "night",
             "text": "Home again. They both slept while the gem kept the night light on.",
             "reaction": "★"},
        ],
    },
    {
        "title": "Midnight Snack Heist", "cast": ["trix", "zia"],
        "scenes": [
            {"setting": "candy",
             "text": "The Cake Vault. Trix studied the blueprints. Zia studied a napkin. Perfect team.",
             "reaction": "?", "props": "tårta"},
            {"setting": "candy",
             "text": "Alarm! They rushed between the sugar hills together as the sirens went off."},
            {"setting": "candy",
             "text": "Trix ducked under the caramel laser. Zia did not. Zia is fine. Zia is sticky."},
            {"setting": "candy",
             "text": "One guard cake blocked the exit. Zia punched it into confetti. Delicious confetti.",
             "props": "tårta"},
            {"setting": "candy",
             "text": "They danced out with the cake held high. The rainbow applauded silently.",
             "props": "regnbåge"},
            {"setting": "night",
             "text": "Cake eaten. Crumbs everywhere. They both slept like tiny criminals. The good kind."},
        ],
    },
    {
        "title": "The Beach Break-In", "cast": ["doris", "apan"],
        "scenes": [
            {"setting": "beach",
             "text": "Rico's coconut fortress was under attack. The enemy: one extremely smug crab.",
             "props": "krabba, snäcka", "reaction": "!"},
            {"setting": "beach",
             "text": "'On three. One - THREE!' They charged down the beach together, faster than the waves."},
            {"setting": "beach",
             "text": "Rico leapt over the crab. Doris spun like a pink tornado. Strategy: pure chaos."},
            {"setting": "beach",
             "text": "The crab counterattacked. Doris ducked. Rico did not. Rico regrets everything."},
            {"setting": "beach",
             "text": "Victory. They danced on the ruins of the fortress until the sun gave up."},
            {"setting": "night",
             "text": "They both slept on the beach. The crab guards the ruins now. Long live the crab.",
             "reaction": "★"},
        ],
    },
]


def normalize_scenes(raw):
    out = []
    for s in raw:
        out.append({"setting": s.get("setting", "forest"),
                    "text": s.get("text") or s.get("en") or s.get("sv") or "",
                    "action": s.get("action") or None,
                    "reaction": s.get("reaction") or None,
                    "props": s.get("props")})
    return out


def make_story(seed, lang="en", story_index=None, cast=None):
    import engine
    rng = random.Random(seed)
    tpl = TEMPLATES[story_index % len(TEMPLATES)] if story_index is not None else rng.choice(TEMPLATES)

    cast = [c.strip() for c in cast] if cast else list(tpl.get("cast") or [rng.choice(NAMES)])
    names = [engine.resolve_character(c)[3] for c in cast]
    name0 = names[0]
    name1 = names[1] if len(names) > 1 else name0

    title_key = "title" if "title" in tpl else "title_en"
    title = tpl[title_key].format(namn=name0, kompis=name1)
    scenes = normalize_scenes(
        [dict(s, text=(s.get("text") or s.get("en") or s["sv"]).format(namn=name0, kompis=name1))
         for s in tpl["scenes"]])
    beats = "\n".join("• " + s["text"] for s in scenes)
    cast_str = " & ".join(names)
    description = (f"{title} ⚡\n\nStarring {cast_str}.\n\n{beats}\n\n"
                   "A PixelTube original – every frame drawn and every note composed by code.\n"
                   "Subscribe and you'll be on the next mission. 🦖\n\n"
                   "#pixelanimation #cartoon #animatedseries #mission")
    tags = ["pixel animation", "animated series", "cartoon", "pixel art",
            "comedy animation", "adventure cartoon", "agent dino", "original cartoon"]

    return {"title": title, "name": name0, "cast": cast, "scenes": scenes,
            "tags": tags, "description": description, "seed": seed, "lang": "en"}
