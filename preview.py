# -*- coding: utf-8 -*-
"""preview.py – Snabbtest av motorn.

   python preview.py              kontaktskiss av alla 7 världar
   python preview.py props        alla objekt i biblioteket
   python preview.py cast         rollistan + alla action per karaktär
   python preview.py candy 2      en värld i större format
"""
import sys

from PIL import Image, ImageDraw

import engine

CAST_DEMO = ["doris", "boris", "apan", "kanin", "bosse", "kurre", "leo", "nova", "stina"]


def _label(img, text):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 8 * len(text) + 8, 15], fill=(0, 0, 0))
    d.text((4, 2), text, fill=(255, 255, 255))


def scenes_sheet(settings, scale=2):
    tiles = []
    for i, st in enumerate(settings):
        ch = engine.Character(CAST_DEMO[i % len(CAST_DEMO)])
        sc = engine.Scene(st, seed=100 + i, actors=[(ch, None)])
        img = sc.frame(1.3).resize((engine.W * scale, engine.H * scale), engine.NEAREST)
        _label(img, f"{st} ({ch.display})")
        tiles.append(img)
    cols = 3
    rows = (len(tiles) + cols - 1) // cols
    tw, th = tiles[0].size
    sheet = Image.new("RGB", (cols * tw, rows * th), (20, 20, 24))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * tw, (i // cols) * th))
    return sheet


def props_sheet():
    items = []
    for name, spec in engine.PROPS.items():
        rng = __import__("random").Random(name)
        if name == "fisk":
            col = (255, 140, 40)
            img = engine._sprite_image(engine.FISH_A,
                                       {"o": col, "t": tuple(int(v * .75) for v in col),
                                        "w": (255, 255, 255)})
        else:
            img = spec["img"](rng)
            if not isinstance(img, Image.Image):
                img = engine._sprite_image(engine.BALLOON,
                                           {"r": img, "w": (255, 255, 255), "s": (120, 120, 130)})
        items.append((name, img))
    cell = 84
    cols = 6
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * cell), (34, 28, 46))
    d = ImageDraw.Draw(sheet)
    for i, (name, img) in enumerate(items):
        x0, y0 = (i % cols) * cell, (i // cols) * cell
        s = max(1, min(6, 40 // max(img.size)))
        big = img.resize((img.width * s, img.height * s), engine.NEAREST)
        sheet.paste(big, (x0 + (cell - big.width) // 2, y0 + 26 + (44 - big.height) // 2), big)
        d.text((x0 + 4, y0 + 6), name, fill=(255, 240, 170))
    return sheet


# bästa t att fånga varje action på stillbild
ACTION_PEAK = {"walk": 0.35, "run": 0.12, "jump": 0.57, "dance": 0.35, "spin": 0.14,
               "hit": 0.20, "duck": 0.28, "wave": 0.20, "sleep": 1.4}


def cast_sheet():
    tiles = []
    # rad 1: rollistan
    for name in CAST_DEMO:
        ch = engine.Character(name)
        sc = engine.Scene("forest", seed=7, actors=[(ch, None)])
        img = sc.frame(0.35).crop((30, 60, 230, 175))
        img = img.resize((img.width * 2, img.height * 2), engine.NEAREST)
        _label(img, f"{ch.display} · {ch.species} · {ch.tint}")
        tiles.append(img)
    # rad 2-3: Doris gör alla action
    for act in ["walk", "run", "jump", "dance", "spin", "hit", "duck", "wave", "sleep"]:
        ch = engine.Character("doris")
        sc = engine.Scene("forest", seed=7, actors=[(ch, act)])
        img = sc.frame(ACTION_PEAK[act]).crop((30, 60, 230, 175))
        img = img.resize((img.width * 2, img.height * 2), engine.NEAREST)
        _label(img, f"Doris: {act}")
        tiles.append(img)
    # rad 3 slut: grupp-action
    for txt, ns, a in [("tillsammans-run", ["doris", "apan"], "run"),
                       ("tillsammans-dans", ["doris", "kanin"], "dance")]:
        sc = engine.Scene("forest", seed=7,
                          actors=[(engine.Character(n), a) for n in ns])
        img = sc.frame(0.22).crop((30, 60, 230, 175))
        img = img.resize((img.width * 2, img.height * 2), engine.NEAREST)
        _label(img, txt)
        tiles.append(img)

    cols = 3
    rows = (len(tiles) + cols - 1) // cols
    tw, th = tiles[0].size
    sheet = Image.new("RGB", (cols * tw, rows * th), (20, 20, 24))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * tw, (i // cols) * th))
    return sheet


def main():
    args = sys.argv[1:]
    if args and args[0] == "props":
        props_sheet().save("preview_props.png")
        print("sparade preview_props.png")
        return
    if args and args[0] == "cast":
        cast_sheet().save("preview_cast.png")
        print("sparade preview_cast.png")
        return
    scale = 2
    if args and args[-1].isdigit():
        scale, args = int(args[-1]), args[:-1]
    settings = args or ["forest", "night", "beach", "space", "snow", "underwater", "candy"]
    scenes_sheet(settings, scale).save("preview.png")
    print("sparade preview.png")


if __name__ == "__main__":
    main()
