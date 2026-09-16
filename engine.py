# -*- coding: utf-8 -*-
"""
engine.py – Pixelmotorn. Hela sagovärlden ritas proceduellt på CPU.

v3:
  • KARAKTÄRSREGISTER: samma namn = alltid samma karaktär (art + färg),
    i varje scen, varje avsnitt. "Doris är alltid samma Doris."
  • Arter: dino, apa, kanin. Flera karaktärer kan vara i samma scen.
  • Action per karaktär: walk, run, jump, dance, spin, hit, duck, wave, sleep.
"""
import hashlib
import math
import random

from PIL import Image, ImageDraw

W, H = 320, 180
GROUND_Y = 150
CHAR_X = 82
CHAR_SCALE = 2
ACTOR_GAP = 52

NEAREST = getattr(getattr(Image, "Resampling", Image), "NEAREST")
ACTIONS = ("walk", "run", "jump", "dance", "spin", "hit", "duck", "wave", "sleep")
LAND = frozenset(["forest", "night", "beach", "space", "snow", "candy"])


def _rows(s):
    lines = [ln.rstrip() for ln in s.strip("\n").splitlines()]
    w = max(len(ln) for ln in lines)
    return [ln.ljust(w, ".") for ln in lines]


def _sprite_image(rows, colors, blink=False):
    h, w = len(rows), max(len(r) for r in rows)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch not in colors:
                continue
            c = colors[ch]
            if blink and ch == "W":
                c = colors.get("O", c)
            px[x, y] = c
    return img


def _lighter(c, f=1.28):
    return tuple(min(255, int(v * f + 14)) for v in c[:3])


# ---------------------------------------------------------------------------
# SPRITES
# O=kropp  D=mörk fläck  B=mage/nos  E=öra  W=öga  K=pupill
# ---------------------------------------------------------------------------
DINO_A = _rows("""
............OOOO......
..........OOOOOOOO....
..........OOOOWWOO....
..........OOOOWKOO....
..........OOOOOOO.....
........OOOOOOOO......
.....OODOODOOOO.......
...OODOODOOOOBBB......
.OOOOOOOOOOBBBB.......
OOOOOOOOOOBBBBB.......
OOOOOOOBBBBBBB........
.OOOOBBBBBBB..........
....OOOOBBBB..........
.....OOOOOBB..........
.....OO...OO..........
.....OO...OO..........
.....OO...OO..........
....OOO...OOO.........
""")

DINO_B = _rows("""
............OOOO......
..........OOOOOOOO....
..........OOOOWWOO....
..........OOOOWKOO....
..........OOOOOOO.....
........OOOOOOOO......
.....OODOODOOOO.......
...OODOODOOOOBBB......
.OOOOOOOOOOBBBB.......
OOOOOOOOOOBBBBB.......
OOOOOOOBBBBBBB........
.OOOOBBBBBBB..........
....OOOOBBBB..........
.....OOOOOBB..........
.....OO...OO..........
....OOO...OO..........
....OO....OOO.........
""")

APE_A = _rows("""
............MMMM......
.........MMMMMMMM.....
........EMMMWWMMME....
........EMMMWKMMME....
.........MMMBBBM......
.........MMMBBM.......
..M.....MMMMMMMM......
..MM..MMMMMMMMDMMM....
..MM.MMMMMMMMMBBMMM...
..MMM.MMMMMMMBBB......
...MMMMMMMMBBBBB......
....MMMMMMBBBBB.......
.....MMMMMBBB.........
......MMMMM...........
......MM...MM.........
......MM...MM.........
......MM...MM.........
.....MMM...MMM........
""")

APE_B = _rows("""
............MMMM......
.........MMMMMMMM.....
........EMMMWWMMME....
........EMMMWKMMME....
.........MMMBBBM......
.........MMMBBM.......
..M.....MMMMMMMM......
..MM..MMMMMMMMDMMM....
..MM.MMMMMMMMMBBMMM...
..MMM.MMMMMMMBBB......
...MMMMMMMMBBBBB......
....MMMMMMBBBBB.......
.....MMMMMBBB.........
......MMMMM...........
......MM...MM.........
.....MM.....MM........
.....MM....MMM........
""")

BUNNY_A = _rows("""
..........OO.OO.......
..........OEOEO.......
..........OEOEO.......
..........OOOOO.......
..........OOOOOO......
..........OOOWWOO.....
..........OOOWKOO.....
..........OOOOB.......
.....OOOOOOOO.........
..WWOOOOOOOBB.........
..WWOOOOOOOBBB........
...OOOOOOBBBBB........
....OOOOBBBBB.........
.....OOOOBB...........
.....O....O...........
....O......O..........
....OO....OOO.........
..OOOO..OOOOO.........
""")

BUNNY_B = _rows("""
..........OO.OO.......
..........OEOEO.......
..........OEOEO.......
..........OOOOO.......
..........OOOOOO......
..........OOOWWOO.....
..........OOOWKOO.....
..........OOOOB.......
.....OOOOOOOO.........
..WWOOOOOOOBB.........
..WWOOOOOOOBBB........
...OOOOOOBBBBB........
....OOOOBBBBB.........
.....OOOOBB...........
.....O....O...........
....O......O..........
....OO......OO........
..OOOO....OOOO........
""")

FAGEL_A = _rows("""
.k...k.
.kk.kk.
..kkk..
""")
FAGEL_B = _rows("""
..kkk..
.kk.kk.
.k...k.
""")

# ---------------------------------------------------------------------------
# KARAKTÄRSREGISTER – samma namn, samma karaktär. För evigt.
# ---------------------------------------------------------------------------
DINO_TINTS = {
    "orange": {"O": (244, 132, 42),  "D": (210, 96, 28),  "B": (255, 213, 148)},
    "grön":   {"O": (104, 190, 78),  "D": (66, 145, 46),  "B": (215, 245, 178)},
    "teal":   {"O": (62, 186, 174),  "D": (34, 138, 128), "B": (192, 244, 236)},
    "lila":   {"O": (158, 110, 230), "D": (116, 74, 180), "B": (226, 206, 255)},
    "rosa":   {"O": (240, 120, 160), "D": (196, 78, 122), "B": (255, 205, 224)},
}
APE_TINTS = {
    # "M" = kroppen (BUGGFIX: utan denna nyckel ritades apan osynlig!),
    # "D" = mörka fläckar, "B" = mage/ansikte, "E" = öron
    "brun":    {"O": (150, 100, 58), "M": (150, 100, 58), "D": (112, 72, 40),  "B": (230, 196, 152), "E": (230, 196, 152)},
    "gyllene": {"O": (205, 150, 60), "M": (205, 150, 60), "D": (160, 112, 40), "B": (250, 224, 168), "E": (250, 224, 168)},
    "grå":     {"O": (140, 145, 155), "M": (140, 145, 155), "D": (105, 110, 120), "B": (215, 220, 228), "E": (215, 220, 228)},
}
BUNNY_TINTS = {
    "vit":  {"O": (236, 236, 242), "D": (204, 204, 216), "B": (255, 255, 255), "E": (255, 165, 195)},
    "grå":  {"O": (165, 168, 178), "D": (130, 133, 145), "B": (228, 230, 236), "E": (255, 165, 195)},
    "rosa": {"O": (248, 175, 195), "D": (220, 138, 162), "B": (255, 222, 232), "E": (255, 255, 255)},
    "brun": {"O": (190, 145, 95),  "D": (150, 110, 66),  "B": (235, 205, 165), "E": (255, 190, 205)},
}

SPECIES_MAPS = {"dino": (DINO_A, DINO_B), "apa": (APE_A, APE_B), "kanin": (BUNNY_A, BUNNY_B)}
SPECIES_TINTS = {"dino": DINO_TINTS, "apa": APE_TINTS, "kanin": BUNNY_TINTS}

# Fast rollista (key -> (art, färg, visningsnamn, alias som hör till samma karaktär))
REGISTRY = {
    "doris": ("dino", "rosa",   "Doris"),
    "boris": ("dino", "teal",   "Boris"),
    "leo":   ("dino", "orange", "Leo"),
    "nova":  ("dino", "lila",   "Nova"),
    "trix":  ("dino", "grön",   "Trix"),
    "puff":  ("dino", "lila",   "Puff"),
    "milo":  ("dino", "orange", "Milo"),
    "zia":   ("dino", "teal",   "Zia"),
    "apa":   ("apa",  "brun",   "Rico"),
    "apan":  ("apa",  "brun",   "Rico"),
    "bosse": ("apa",  "gyllene", "Bosco"),
    "kanin": ("kanin", "vit",   "Hops"),
    "kaninen": ("kanin", "vit", "Hops"),
    "kurre": ("kanin", "grå",   "Ash"),
    "stina": ("kanin", "rosa",  "Pix"),
}


def _canon(name):
    return REGISTRY.get(str(name).strip().lower())


def resolve_character(name):
    """namn -> (art, tint, visningsnamn). Okända namn får stabil hash-identitet."""
    key = str(name).strip().lower()
    hit = _canon(key)
    if hit:
        sp, tint, disp = hit
        return key, sp, tint, disp
    digest = hashlib.md5(key.encode("utf-8")).digest()
    sp = ("dino", "dino", "apa", "kanin")[digest[0] % 4]
    tints = sorted(SPECIES_TINTS[sp])
    tint = tints[digest[1] % len(tints)]
    disp = str(name).strip().capitalize()
    return key, sp, tint, disp


def alias_group(name):
    """Alla namn/alias som pekar på samma karaktär (för verb-parsern)."""
    key, sp, tint, disp = resolve_character(name)
    group = {key, disp.lower()}
    for k, v in REGISTRY.items():
        if v[0] == sp and v[1] == tint:
            group.add(k)
            group.add(v[2].lower())
    return {g for g in group if g}


_FRAME_CACHE = {}


class Character:
    """En persistent karaktär. Character('doris') ser ALLTID likadan ut."""

    def __init__(self, name="leo"):
        self.key, self.species, self.tint, self.display = resolve_character(name)
        cache_key = (self.species, self.tint)
        if cache_key not in _FRAME_CACHE:
            cols = dict(SPECIES_TINTS[self.species][self.tint])
            cols.setdefault("W", (255, 255, 255))
            cols.setdefault("K", (28, 28, 32))
            cols.setdefault("E", cols["B"])
            a, b = SPECIES_MAPS[self.species]
            frames = {}
            for tag, rows_ in (("A", a), ("B", b)):
                for blink, suf in ((False, ""), (True, "_b")):
                    img = _sprite_image(rows_, cols, blink=blink)
                    frames[tag + suf] = img.resize(
                        (img.width * CHAR_SCALE, img.height * CHAR_SCALE), NEAREST)
            _FRAME_CACHE[cache_key] = frames
        self.frames = _FRAME_CACHE[cache_key]
        self.w = self.frames["A"].width
        self.h = self.frames["A"].height
        self.hopping = self.species == "kanin"


# ---------------------------------------------------------------------------
# Reaktionssymboler + POW-stjärna
# ---------------------------------------------------------------------------
_BANG = _rows(".##.\n.##.\n.##.\n.##.\n....\n.##.")
_QUES = _rows(".###.\n#...#\n....#\n..##.\n..#..\n.....\n..#..")
_HEART = _rows(".##.##.\n#######\n#######\n.#####.\n..###..\n...#...")
_STAR = _rows("...#...\n..###..\n#######\n.#####.\n..#.#..")
_ZED = _rows("####\n...#\n..#.\n.#..\n####")
_POW = _rows("..y...y..\n.yyy.yyy.\n..yyyyy..\nyyyyyyyyy\n..yyyyy..\n.yyy.yyy.\n..y...y..")

REACTIONS = {"!": (_BANG, (232, 60, 60)), "?": (_QUES, (70, 140, 235)),
             "♥": (_HEART, (240, 90, 130)), "★": (_STAR, (245, 200, 60))}


def _bubble(sym_rows, color, scale=2):
    sw, sh = len(sym_rows[0]), len(sym_rows)
    bw, bh = sw * scale + 8, sh * scale + 8
    img = Image.new("RGBA", (bw, bh + 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, bw - 1, bh - 1], radius=4,
                        fill=(255, 255, 255, 245), outline=(58, 58, 68, 255), width=1)
    d.polygon([(3, bh - 1), (9, bh - 1), (3, bh + 3)], fill=(255, 255, 255, 245))
    sym = _sprite_image(sym_rows, {"#": color})
    sym = sym.resize((sw * scale, sh * scale), NEAREST)
    img.paste(sym, (4, 4), sym)
    return img


# ---------------------------------------------------------------------------
# OBJEKTBIBLIOTEKET
# ---------------------------------------------------------------------------
MUSHROOM = _rows("""
...rrrr...
..rwwrrwr..
.rrrrrrrr.
rrrrrrrrrr
...wwww...
...wwww...
...wwww...
""")
HOUSE = _rows("""
......r......
.....rrr.....
....rrrrr....
...rrrrrrr...
..rrrrrrrrr..
.bbbbbbbbbbb.
.bbyybbbyybb.
.bbyybbbyybb.
.bbbbbddbbbb.
.bbbbbddbbbb.
.bbbbbddbbbb.
""")
ROCKET = _rows("""
.....rrr.....
....rrrrr....
....sssss....
....swwws....
....swwws....
....sssss....
....sssss....
....sssss....
...fsssssf...
..ffsssssff..
..fsssssssf..
..gsssssssg..
""")
SNOWMAN = _rows("""
...wwww...
..wwwwww..
..wkwkww..
..wwowww..
..wwwwww..
...rrrr...
..wwwwww..
.wwwwwwww.
.wwkwwkww.
wwwwwwwwww
""")
FISH_A = _rows("""
....oooo..
t..oooooo.
ttoooooowo
t..oooooo.
....oooo..
""")
FISH_B = _rows("""
....oooo..
tt.oooooo.
.toooooowo
tt.oooooo.
....oooo..
""")
CRAB = _rows("""
.k.....k.
.kk...kk.
..rrrrr..
rrrrrrrrr
r.rrrrr.r
..r.r.r..
.r..r..r.
""")
SHELL = _rows("""
...pp...
..pppp..
.pwpwpp.
pppppppp
pwwppwwp
""")
CAKE = _rows("""
......y.....
......c.....
...ffffff...
..ffffffff..
..pppppppp..
..pwppppwp..
..pppppppp..
.pppppppppp.
.pwwpwwpwwp.
.pppppppppp.
""")
ICECREAM = _rows("""
...pppp...
..pppppp..
.pppppppp.
.pwwppwwp.
.pppppppp.
..pppppp..
...oooo...
...oooo...
....oo....
....oo....
.....o....
""")
BALLOON = _rows("""
...rrrr...
..rrrrrr..
.rrrrrrrr.
.rrwrrrrr.
.rrrrrrrr.
..rrrrrr..
...rrrr...
....rr....
....s.....
....s.....
...s......
""")
GSTAR = _rows("""
...y...
..yyy..
yyyyyyy
.yyyyy.
..y.y..
.y...y.
""")
GEM = _rows("""
...cccc...
..cwwccc..
.cccccccc.
cccccccccc
.cccccccc.
..cccccc..
...cccc...
....cc....
""")
CHEST = _rows("""
..KKKKKKKKK..
.KKKKKKKKKKK.
.KGKKKKKGKKK.
KKKKKYYYKKKKK
.KGKKKKKGKKK.
.KGKKKKKGKKK.
.KKKKKKKKKKK.
""")
BUSH = _rows("""
...gggg...
..grgggg..
.gggggrgg.
gggggggggg
.grgggggg.
..gggrgg..
""")
FROG = _rows("""
wkw...wkw
.ww...ww.
.ggggggg.
ggggggggg
ggggggggg
.gg...gg.
.g.....g.
""")
BIGFLOWER = _rows("""
..ppp..
.ppppp.
.ppypp.
.ppppp.
..ppp..
...g...
..gg...
...g...
..g.g..
...g...
""")

_FISH_COLORS = [(255, 140, 40), (90, 190, 255), (255, 210, 60), (255, 90, 120)]
_BALLOON_COLORS = [(240, 80, 90), (90, 170, 255), (255, 205, 70), (150, 230, 120)]


def _rainbow_img():
    img = Image.new("RGBA", (74, 42), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cols = [(255, 90, 90), (255, 175, 60), (255, 230, 90), (120, 220, 110), (95, 165, 255)]
    for i, c in enumerate(cols):
        r = 33 - i * 3
        d.arc([37 - r, 42 - r, 37 + r, 42 + r], 180, 360, fill=c + (215,), width=3)
    return img


def _prop_entry(img_fn, zone, settings, kw):
    return {"img": img_fn, "zone": zone, "settings": settings, "kw": kw}


PROPS = {
    "svamp": _prop_entry(lambda r: _sprite_image(MUSHROOM, {"r": (225, 60, 60), "w": (245, 238, 220)}),
                         "ground", LAND, ["svamp", "mushroom"]),
    "hus": _prop_entry(lambda r: _sprite_image(HOUSE, {"r": (205, 80, 60), "b": (250, 235, 205),
                                                       "y": (150, 200, 230), "d": (120, 70, 35)}),
                       "ground", LAND, ["hus ", "house", "hemma"]),
    "raket": _prop_entry(lambda r: _sprite_image(ROCKET, {"r": (230, 70, 60), "s": (210, 215, 225),
                                                          "w": (110, 210, 235), "f": (200, 60, 60),
                                                          "g": (120, 125, 135)}),
                         "ground", LAND, ["raket", "rocket"]),
    "snögubbe": _prop_entry(lambda r: _sprite_image(SNOWMAN, {"w": (245, 250, 255), "k": (40, 40, 45),
                                                              "o": (240, 140, 40), "r": (220, 60, 70)}),
                            "ground", {"snow"}, ["snögubbe", "snowman"]),
    "fisk": _prop_entry(lambda r: r.choice(_FISH_COLORS), "water-swim", {"underwater"},
                        ["fisk", "fiskar", "fish"]),
    "krabba": _prop_entry(lambda r: _sprite_image(CRAB, {"k": (40, 40, 45), "r": (225, 70, 60)}),
                          "ground", {"beach", "underwater"}, ["krabba", "crab"]),
    "snäcka": _prop_entry(lambda r: _sprite_image(SHELL, {"p": (255, 175, 195), "w": (255, 235, 240)}),
                          "ground", {"beach", "underwater"}, ["snäcka", "sjösnäcka", "seashell", "shell"]),
    "tårta": _prop_entry(lambda r: _sprite_image(CAKE, {"y": (255, 220, 90), "c": (255, 120, 120),
                                                        "f": (255, 245, 225), "p": (240, 140, 175),
                                                        "w": (255, 255, 255)}),
                         "ground", LAND, ["tårta", "tårtor", "cake", "födelsedag"]),
    "glass": _prop_entry(lambda r: _sprite_image(ICECREAM, {"p": r.choice([(255, 170, 200), (170, 230, 180), (255, 220, 160)]),
                                                            "w": (255, 255, 255), "o": (224, 184, 130)}),
                         "ground", LAND, ["glass", "glassar", "ice cream"]),
    "ballong": _prop_entry(lambda r: r.choice(_BALLOON_COLORS), "sky-float",
                           LAND, ["ballong", "ballonger", "balloon"]),
    "stjärna": _prop_entry(lambda r: _sprite_image(GSTAR, {"y": (255, 225, 90)}),
                           "ground", LAND, ["stjärna", "star"]),
    "ädelsten": _prop_entry(lambda r: _sprite_image(GEM, {"c": (60, 220, 235), "w": (255, 255, 255)}),
                            "ground", LAND, ["ädelsten", "diamant", "kristall", "gem", "diamond", "crystal"]),
    "kista": _prop_entry(lambda r: _sprite_image(CHEST, {"K": (130, 80, 35), "G": (255, 205, 80),
                                                         "Y": (255, 225, 120)}),
                         "ground", LAND, ["skattkista", "kista", "treasure chest"]),
    "bär": _prop_entry(lambda r: _sprite_image(BUSH, {"g": (50, 130, 60), "r": (230, 60, 70)}),
                       "ground", LAND, ["bär", "berries", "berry"]),
    "groda": _prop_entry(lambda r: _sprite_image(FROG, {"w": (255, 255, 255), "k": (40, 40, 45),
                                                        "g": (90, 190, 80)}),
                         "hop", LAND, ["groda", "padda", "frog"]),
    "blomma": _prop_entry(lambda r: _sprite_image(BIGFLOWER, {"p": r.choice([(255, 130, 170), (255, 200, 90), (190, 150, 255)]),
                                                              "y": (255, 230, 110), "g": (70, 150, 70)}),
                          "ground", LAND, ["blomma", "blommor", "flower"]),
    "regnbåge": _prop_entry(lambda r: _rainbow_img(), "sky-static",
                            {"forest", "beach", "snow", "candy"}, ["regnbåge", "rainbow"]),
}

NAME_ALIASES = {"mushroom": "svamp", "house": "hus", "rocket": "raket", "snowman": "snögubbe",
                "fish": "fisk", "crab": "krabba", "shell": "snäcka", "cake": "tårta",
                "icecream": "glass", "ice cream": "glass", "balloon": "ballong", "star": "stjärna",
                "gem": "ädelsten", "diamond": "ädelsten", "crystal": "ädelsten",
                "chest": "kista", "treasure": "kista", "berries": "bär", "frog": "groda",
                "flower": "blomma", "rainbow": "regnbåge"}


def normalize_prop_names(props):
    if not props:
        return []
    if isinstance(props, str):
        props = [p.strip() for p in props.split(",")]
    out = []
    for p in props:
        p = NAME_ALIASES.get(str(p).strip().lower(), str(p).strip().lower())
        if p in PROPS and p not in out:
            out.append(p)
    return out


def props_for_text(text, setting):
    low = " " + (text or "").lower() + " "
    ground, other = [], []
    for name, spec in PROPS.items():
        if setting not in spec["settings"]:
            continue
        if any(k in low for k in spec["kw"]):
            (ground if spec["zone"] == "ground" else other).append(name)
    return ground[:3] + other[:3]


# ---------------------------------------------------------------------------
# Världar
# ---------------------------------------------------------------------------
SCHEMES = {
    "forest": {
        "sky": ((122, 196, 232), (214, 240, 214)), "celest": ("sun", (262, 30, 13)),
        "hills": (((150, 205, 130), 128, 16, 120), ((104, 168, 92), 142, 10, 84)),
        "tree": "pine", "tree_cols": ((30, 92, 54), (56, 140, 84)),
        "ground": ((150, 110, 66), (96, 158, 80)),
        "dots": [(90, 150, 74), (120, 180, 92), (200, 150, 90)],
        "flowers": True, "particles": "leaf", "clouds": 3, "bird": True,
    },
    "night": {
        "sky": ((18, 26, 58), (52, 60, 104)), "celest": ("moon", (250, 30, 12)),
        "hills": (((24, 50, 44), 128, 15, 120), ((16, 36, 34), 142, 10, 84)),
        "tree": "pine", "tree_cols": ((10, 28, 26), (18, 40, 34)),
        "ground": ((40, 62, 54), (30, 48, 44)), "dots": [(34, 54, 48), (48, 74, 62)],
        "particles": "firefly", "clouds": 1, "stars": 46,
    },
    "beach": {
        "sky": ((110, 196, 240), (255, 244, 205)), "celest": ("sun", (262, 30, 13)),
        "hills": None, "sea": True, "tree": "palm", "tree_cols": ((36, 130, 70), (52, 160, 86)),
        "ground": ((236, 214, 160), (226, 204, 146)), "dots": [(206, 178, 118), (244, 226, 178)],
        "particles": None, "clouds": 3, "bird": True,
    },
    "space": {
        "sky": ((8, 8, 30), (40, 22, 64)), "celest": ("planet", (60, 36, 22)),
        "hills": None, "tree": "crystal", "tree_cols": ((96, 54, 160), (150, 96, 220)),
        "ground": ((96, 90, 112), (76, 70, 92)), "dots": [(70, 64, 86), (110, 104, 128)],
        "particles": "mote", "clouds": 0, "stars": 78,
    },
    "snow": {
        "sky": ((176, 210, 236), (244, 248, 252)), "celest": ("sun", (262, 30, 12)),
        "hills": (((206, 224, 240), 130, 12, 110), ((170, 198, 222), 144, 9, 80)),
        "tree": "pine", "tree_cols": ((52, 102, 72), (88, 150, 104)), "snowy": True,
        "ground": ((246, 250, 254), (224, 236, 246)), "dots": [(198, 216, 234), (214, 228, 242)],
        "particles": "snow", "clouds": 2,
    },
    "underwater": {
        "sky": ((14, 78, 148), (66, 158, 212)), "celest": None,
        "hills": None, "rays": True, "weeds": True,
        "tree": "coral", "coral_cols": [(255, 120, 110), (255, 170, 80), (200, 110, 200)],
        "tree_cols": ((255, 120, 110), (255, 170, 80)),
        "ground": ((228, 206, 158), (214, 190, 140)), "dots": [(240, 225, 190), (198, 178, 138)],
        "particles": "bubbla", "clouds": 0,
    },
    "candy": {
        "sky": ((255, 186, 214), (255, 240, 247)), "celest": ("sun", (262, 30, 13)),
        "hills": (((255, 196, 224), 130, 14, 110), ((255, 164, 206), 144, 10, 80)),
        "tree": "lollipop",
        "loli_cols": [(255, 130, 170), (255, 160, 90), (170, 230, 140), (150, 200, 255)],
        "ground": ((255, 240, 226), (255, 214, 168)),
        "dots": [(255, 120, 170), (140, 220, 250), (255, 220, 90), (170, 240, 140)],
        "particles": "glitter", "clouds": 3,
    },
}


# ---------------------------------------------------------------------------
# Miljöritare
# ---------------------------------------------------------------------------
def _gradient(top, bottom, w, h):
    img = Image.new("RGB", (1, h))
    px = img.load()
    for y in range(h):
        f = y / max(1, h - 1)
        px[0, y] = tuple(int(top[i] + (bottom[i] - top[i]) * f) for i in range(3))
    return img.resize((w, h))


def _cloud_img(rng):
    w = rng.randint(36, 66)
    h = max(12, w * 2 // 5)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for _ in range(rng.randint(4, 6)):
        bw = rng.randint(w // 4, w // 2)
        bh = max(4, bw * 2 // 5)
        bx = rng.randint(2, max(3, w - bw - 2))
        by = rng.randint(h // 4, max(h // 4 + 1, h - bh - 2))
        d.ellipse([bx, by, bx + bw, by + bh], fill=(255, 255, 255, 210))
    d.rectangle([4, h - 6, w - 4, h - 1], fill=(255, 255, 255, 185))
    return img


def _pine(d, x, base, s, dark, light, snowy=False):
    x, base = int(x), int(base)
    d.rectangle([x - s, base - 5 * s, x + max(1, s) - 1, base], fill=(104, 70, 42))
    yy = base - 4 * s
    for i, (hw, hh) in enumerate(((13, 10), (10, 9), (7, 8))):
        hw, hh = int(hw * s), int(hh * s)
        top = snowy and i == 2
        c = (240, 246, 252) if top else light
        cd = (196, 210, 228) if top else dark
        d.polygon([(x - hw, yy), (x, yy - hh), (x + hw, yy)], fill=c)
        d.polygon([(x - hw, yy), (x, yy - hh), (x, yy)], fill=cd)
        yy -= int(6 * s)


def _palm(d, x, base, s, dark, light):
    x, base = int(x), int(base)
    seg = 8
    xx = x
    for i in range(seg):
        yy = base - 6 * i * s
        xx = x + int(i * i * 0.30 * s)
        d.rectangle([xx - 2 * s, yy - 6 * s, xx + s, yy - 1], fill=(150, 105, 60))
    tx, ty = xx, base - 6 * seg * s
    d.ellipse([tx - 3 * s, ty, tx, ty + 3 * s], fill=(110, 72, 40))
    d.ellipse([tx + s, ty, tx + 4 * s, ty + 3 * s], fill=(110, 72, 40))
    for ang in (200, 245, 295, 340, 160, 20):
        r = math.radians(ang)
        mx = tx + int(math.cos(r) * 16 * s)
        my = ty + int(math.sin(r) * 7 * s)
        ex = tx + int(math.cos(r) * 27 * s)
        ey = ty + int(math.sin(r) * 12 * s) + 6 * s
        d.line([(tx, ty), (mx, my), (ex, ey)], fill=light, width=int(max(2, 3 * s)))
        d.line([(tx, ty + s), (mx, my + s), (ex, ey + s)], fill=dark, width=int(max(1, int(s))))


def _crystal(d, x, base, s, dark, light):
    hgt = int(20 * s) + 6
    w2 = max(2, int(hgt * 0.32))
    d.polygon([(x - w2, base), (x, base - hgt), (x + w2, base)], fill=light)
    d.polygon([(x, base), (x, base - hgt), (x + w2, base)], fill=dark)
    d.point((x, base - hgt), fill=(255, 255, 255))
    d.point((x - w2 - 2, base - 3), fill=dark)
    d.point((x + w2 + 2, base - 5), fill=light)


def _lollipop(d, x, base, s, crown):
    x, base = int(x), int(base)
    hgt = int(20 * s)
    for i, yy in enumerate(range(base - hgt, base, 3)):
        col = (255, 255, 255) if i % 2 == 0 else (255, 150, 190)
        d.rectangle([x - 1, yy, x + 1, min(yy + 2, base)], fill=col)
    r = int(9 * s)
    cy = base - hgt - r + 3
    d.ellipse([x - r, cy - r, x + r, cy + r], fill=crown)
    d.ellipse([x - r + 3, cy - r + 3, x + r - 3, cy + r - 3], outline=_lighter(crown), width=2)
    d.ellipse([x - 2, cy - 2, x + 2, cy + 2], fill=(255, 255, 255))


def _coral(d, x, base, col, hgt=14):
    x, base = int(x), int(base)
    d.line([(x, base), (x, base - hgt)], fill=col, width=2)
    for ang, le in ((-38, 8), (32, 9), (-14, 6), (58, 6)):
        r = math.radians(ang - 90)
        x2 = x + int(math.cos(r) * le)
        y2 = base - hgt + int(math.sin(r) * le)
        d.line([(x, base - hgt), (x2, y2)], fill=col, width=2)
        d.point((x2, y2), fill=_lighter(col))
    d.ellipse([x - 2, base - hgt - 2, x + 2, base - hgt + 1], fill=_lighter(col))


# ---------------------------------------------------------------------------
# Scenen
# ---------------------------------------------------------------------------
class Scene:
    """En levande pixelscen. actors = [(Character, action|None), ...] (max 3)."""

    def __init__(self, setting="forest", seed=0, actors=None, text=None,
                 props=None, reaction=None):
        self.setting = setting if setting in SCHEMES else "forest"
        self.rng = random.Random(seed)
        self.pal = SCHEMES[self.setting]
        if not actors:
            actors = [(Character("leo"), None)]
        self.actors = []
        for a in actors[:3]:
            ch, act = (a if isinstance(a, tuple) else (a, None))
            self.actors.append((ch, act if act in ACTIONS else None))
        self.reaction = reaction if reaction in REACTIONS else None

        names = normalize_prop_names(props)
        if not names and text:
            names = props_for_text(text, self.setting)
        names = [n for n in names if self.setting in PROPS[n]["settings"]]

        self._build_sky()
        self._build_hills()
        self._build_trees()
        self._build_ground()
        self._bake_props(names)
        self._build_clouds()
        self._build_particles()
        self._setup_animals(names)
        self._build_reaction()

        self.bird = bool(self.pal.get("bird")) and self.rng.random() < 0.85
        self.bird_y = self.rng.randint(30, 62)
        self.bird_speed = self.rng.uniform(20, 30)
        self.bird_off = self.rng.uniform(0, 200)
        self.bird_imgs = (_sprite_image(FAGEL_A, {"k": (70, 66, 84)}),
                          _sprite_image(FAGEL_B, {"k": (70, 66, 84)}))
        self.pow = _sprite_image(_POW, {"y": (255, 222, 80)})
        self.pow = self.pow.resize((self.pow.width * 2, self.pow.height * 2), NEAREST)

    # -- uppbyggnad ------------------------------------------------------
    def _build_sky(self):
        top, bot = self.pal["sky"]
        self.sky = _gradient(top, bot, W, H)
        n = self.pal.get("stars", 0)
        self.stars = [(self.rng.randrange(W), self.rng.randrange(GROUND_Y - 46),
                       self.rng.uniform(0, 6.28), self.rng.uniform(1.5, 4.0))
                      for _ in range(n)]
        self.rays = None
        if self.pal.get("rays"):
            r = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(r)
            for x0 in (26, 128, 226):
                d.polygon([(x0, 0), (x0 + 24, 0), (x0 + 66, GROUND_Y), (x0 + 32, GROUND_Y)],
                          fill=(255, 255, 255, 15))
            self.rays = r

    def _build_hills(self):
        spec = self.pal.get("hills")
        if not spec:
            self.hills = None
            return
        img = Image.new("RGBA", (2 * W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        for color, base, amp, wl in spec:
            ph = self.rng.uniform(0, 6.28)
            pts = [(x, base + amp * math.sin(ph + x / wl)) for x in range(0, 2 * W + 8, 8)]
            d.polygon(pts + [(2 * W, H), (0, H)], fill=color + (255,))
        for _ in range(26):
            x = self.rng.randrange(2 * W)
            c, b, a, wl = spec[-1]
            y = b + a * math.sin(x / wl) + 2
            dark = self.pal.get("tree_cols", ((30, 60, 40),))[0]
            td = tuple(int(v * 0.8) for v in dark)
            d.polygon([(x - 4, y), (x, y - 9), (x + 4, y)], fill=td + (255,))
        self.hills = img

    def _build_trees(self):
        img = Image.new("RGBA", (2 * W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        kind = self.pal.get("tree")
        if not kind:
            self.trees = None
            return
        dark, light = self.pal.get("tree_cols", ((40, 80, 50), (60, 120, 70)))
        snowy = bool(self.pal.get("snowy"))
        spacing = {"palm": self.rng.randint(120, 200), "coral": self.rng.randint(70, 110),
                   "lollipop": self.rng.randint(56, 84)}.get(kind, self.rng.randint(44, 70))
        x = self.rng.randint(0, 30)
        while x < W + 40:
            for xx in (x, x + W):
                if kind == "pine":
                    _pine(d, xx, GROUND_Y + 2, self.rng.uniform(0.9, 1.4), dark, light, snowy)
                elif kind == "palm":
                    _palm(d, xx, GROUND_Y + 3, self.rng.uniform(0.9, 1.2), dark, light)
                elif kind == "crystal":
                    _crystal(d, xx, GROUND_Y + 2, self.rng.uniform(0.7, 1.2), dark, light)
                elif kind == "coral":
                    _coral(d, xx, GROUND_Y + 4, self.rng.choice(self.pal.get(
                        "coral_cols", [(255, 120, 110)])), hgt=self.rng.randint(10, 20))
                elif kind == "lollipop":
                    _lollipop(d, xx, GROUND_Y + 2, self.rng.uniform(0.9, 1.3),
                              self.rng.choice(self.pal.get("loli_cols", [(255, 130, 170)])))
            x += spacing + self.rng.randint(-14, 22)
        self.trees = img

    def _build_ground(self):
        ground, top = self.pal["ground"]
        img = Image.new("RGBA", (2 * W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rectangle([0, GROUND_Y, 2 * W, H], fill=ground + (255,))
        d.rectangle([0, GROUND_Y, 2 * W, GROUND_Y + 3], fill=top + (255,))
        for _ in range(110):
            x = self.rng.randrange(2 * W)
            y = self.rng.randrange(GROUND_Y + 6, H)
            d.point((x, y), fill=self.rng.choice(self.pal["dots"]) + (255,))
        if self.pal.get("flowers"):
            for _ in range(14):
                x = self.rng.randrange(2 * W)
                y = self.rng.randrange(GROUND_Y + 8, H - 4)
                d.line([(x, y), (x, y - 4)], fill=(60, 130, 60, 255))
                d.point((x, y - 5), fill=self.rng.choice(
                    [(255, 130, 150, 255), (255, 230, 120, 255), (255, 255, 255, 255),
                     (200, 150, 255, 255)]))
        if self.setting == "space":
            for _ in range(7):
                x = self.rng.randrange(2 * W)
                y = self.rng.randrange(GROUND_Y + 8, H - 4)
                r = self.rng.randint(3, 8)
                d.ellipse([x - r, y - r // 2, x + r, y + r // 2], fill=self.pal["dots"][0] + (255,))
        self.ground = img

    def _bake_props(self, names):
        for name in names:
            spec = PROPS[name]
            if spec["zone"] == "ground":
                img = spec["img"](self.rng)
                for _ in range(2 if name in ("svamp", "blomma", "snäcka") else 1):
                    x = self.rng.randint(6, 2 * W - img.width - 6)
                    self.ground.paste(img, (x, GROUND_Y - img.height + 2), img)
            elif spec["zone"] == "sky-static" and self.hills is not None:
                img = spec["img"](self.rng)
                x = self.rng.randint(W // 2, W - img.width // 2)
                self.hills.paste(img, (x, 16), img)

    def _setup_animals(self, names):
        self.swimmers, self.hoppers, self.floaters = [], [], []
        n_fish = (3 if self.setting == "underwater" else 0) + names.count("fisk") * 2
        for _ in range(min(5, n_fish)):
            col = self.rng.choice(_FISH_COLORS)
            cols = {"o": col, "t": tuple(int(v * 0.75) for v in col), "w": (255, 255, 255)}
            self.swimmers.append({"imgs": (_sprite_image(FISH_A, cols), _sprite_image(FISH_B, cols)),
                                  "y": self.rng.uniform(46, GROUND_Y - 26),
                                  "speed": self.rng.uniform(18, 34),
                                  "off": self.rng.uniform(0, 400),
                                  "ph": self.rng.uniform(0, 6.28)})
        for _ in range(names.count("groda")):
            self.hoppers.append({"img": PROPS["groda"]["img"](self.rng),
                                 "off": self.rng.uniform(0, 300),
                                 "ph": self.rng.uniform(0, 6.28)})
        for _ in range(min(2, names.count("ballong"))):
            col = PROPS["ballong"]["img"](self.rng)
            self.floaters.append({"img": _sprite_image(
                BALLOON, {"r": col, "w": (255, 255, 255), "s": (120, 120, 130)}),
                "y": self.rng.uniform(26, 62), "speed": self.rng.uniform(4, 8),
                "off": self.rng.uniform(0, 300), "ph": self.rng.uniform(0, 6.28)})
        self.weeds = []
        if self.pal.get("weeds"):
            for _ in range(7):
                self.weeds.append({"x": self.rng.randint(4, W - 4),
                                   "h": self.rng.randint(14, 34),
                                   "ph": self.rng.uniform(0, 6.28),
                                   "col": self.rng.choice([(28, 140, 90), (40, 172, 110), (22, 110, 76)])})

    def _build_clouds(self):
        self.clouds = []
        for _ in range(self.pal.get("clouds", 0)):
            ci = _cloud_img(self.rng)
            self.clouds.append([ci, self.rng.uniform(0, W + 160),
                                self.rng.randint(8, 62), self.rng.uniform(2.0, 5.0)])

    def _build_particles(self):
        kind = self.pal.get("particles")
        count = {"leaf": 12, "snow": 32, "firefly": 9, "mote": 16,
                 "bubbla": 18, "glitter": 22}.get(kind or "", 0)
        self.parts = []
        for _ in range(count):
            self.parts.append({"x": self.rng.uniform(0, W), "y": self.rng.uniform(0, GROUND_Y),
                               "v": self.rng.uniform(6, 18), "sway": self.rng.uniform(3, 10),
                               "ph": self.rng.uniform(0, 6.28), "sp": self.rng.uniform(1.5, 4),
                               "r": self.rng.choice([1, 1, 2])})
        self.part_kind = kind

    def _build_reaction(self):
        self.bubble_img = None
        if self.reaction:
            rows, col = REACTIONS[self.reaction]
            self.bubble_img = _bubble(rows, col)
        self.zz = _sprite_image(_ZED, {"#": (205, 225, 255)})
        self.zz = self.zz.resize((self.zz.width * 2, self.zz.height * 2), NEAREST)

    # -- per frame ---------------------------------------------------------
    def _paste_wrapped(self, base, layer, dx):
        ox = int(dx) % W
        crop = layer.crop((ox, 0, ox + W, H))
        base.paste(crop, (0, 0), crop)

    def _draw_stars(self, img, t):
        px = img.load()
        for x, y, ph, sp in self.stars:
            b = 0.5 + 0.5 * math.sin(t * sp + ph)
            if b < 0.12:
                continue
            v = int(90 + 165 * b)
            px[x, y] = (v, v, min(255, v + 25))

    def _draw_celestial(self, img, t):
        spec = self.pal.get("celest")
        if not spec:
            return
        kind, (x, y, r) = spec
        bob = int(math.sin(t * 0.5) * 1.5)
        d = ImageDraw.Draw(img)
        if kind == "sun":
            d.ellipse([x - r - 5, y - r - 5 + bob, x + r + 5, y + r + 5 + bob], fill=(255, 240, 150))
            d.ellipse([x - r, y - r + bob, x + r, y + r + bob], fill=(255, 206, 80))
        elif kind == "moon":
            d.ellipse([x - r, y - r + bob, x + r, y + r + bob], fill=(238, 234, 214))
            for cx, cy, cr in ((x - 4, y - 3, 3), (x + 3, y + 2, 2), (x - 1, y + 5, 2)):
                d.ellipse([cx - cr, cy - cr + bob, cx + cr, cy + cr + bob], fill=(206, 200, 178))
        elif kind == "planet":
            d.ellipse([x - r, y - r + bob, x + r, y + r + bob], fill=(146, 88, 200))
            d.rectangle([x - r, y - 4 + bob, x + r, y + 2 + bob], fill=(120, 66, 170))
            d.ellipse([x - r - 14, y - r // 2 + bob, x + r + 14, y + r // 2 + bob],
                      outline=(210, 160, 240))

    def _draw_clouds(self, img, t):
        for ci, x0, y, spd in self.clouds:
            w = ci.width
            x = int((x0 - t * spd) % (W + w + 80)) - w - 40
            img.paste(ci, (x, y), ci)

    def _draw_sea(self, img, t):
        d = ImageDraw.Draw(img)
        d.rectangle([0, 100, W, GROUND_Y - 2], fill=(62, 150, 205))
        d.line([0, 100, W, 100], fill=(222, 246, 255))
        for yb, ph in ((116, 0.0), (130, 2.1)):
            pts = [(x, yb + 2 * math.sin(x / 14.0 + t * 2.2 + ph)) for x in range(0, W + 1, 4)]
            d.line(pts, fill=(168, 218, 244))

    def _draw_weeds(self, img, t):
        d = ImageDraw.Draw(img)
        for wd in self.weeds:
            pts = []
            for yy in range(0, wd["h"], 4):
                xo = 2.2 * math.sin(t * 1.3 + wd["ph"] + yy / 7.0)
                pts.append((wd["x"] + xo, GROUND_Y + 2 - yy))
            if len(pts) > 1:
                d.line(pts, fill=wd["col"], width=2)

    def _draw_bird(self, img, t):
        im = self.bird_imgs[int(t * 6) % 2]
        span = W + 60
        x = int(span - ((t * self.bird_speed + self.bird_off) % span)) - 30
        y = int(self.bird_y + 4 * math.sin(t * 1.3))
        img.paste(im, (x, y), im)

    def _draw_swimmers(self, img, t):
        for f in self.swimmers:
            im = f["imgs"][int(t * 6) % 2]
            span = W + im.width + 40
            x = int(((t * f["speed"] + f["off"]) % span)) - im.width - 20
            y = int(f["y"] + 4 * math.sin(t * 1.6 + f["ph"]))
            img.paste(im, (x, y), im)

    def _draw_hoppers(self, img, t):
        for hp in self.hoppers:
            im = hp["img"]
            span = W + im.width + 60
            x = int((hp["off"] - t * 14.0) % span) - 30
            y = GROUND_Y - im.height + 2 - abs(int(6 * math.sin(t * 5.2 + hp["ph"])))
            img.paste(im, (x, y), im)

    def _draw_floaters(self, img, t):
        for fl in self.floaters:
            im = fl["img"]
            span = W + im.width + 80
            x = int((fl["off"] + t * fl["speed"]) % span) - 40
            y = int(fl["y"] + 4 * math.sin(t * 0.9 + fl["ph"]))
            img.paste(im, (x, y), im)

    def _draw_actors(self, img, t):
        d = ImageDraw.Draw(img, "RGBA")
        for i, (ch, act) in enumerate(self.actors):
            tt = t + i * 0.31
            x = CHAR_X + i * ACTOR_GAP
            d.ellipse([x - 6, GROUND_Y - 2, x + ch.w + 6, GROUND_Y + 5], fill=(0, 0, 0, 70))
            speed = 12 if act == "run" else 7
            fr = "A" if int(tt * speed) % 2 == 0 else "B"
            if act == "sleep":
                fr = "A"
            blink = act != "sleep" and (tt % 3.7) < 0.12
            spr = ch.frames[fr + ("_b" if blink else "")]
            feet = GROUND_Y + 2 + i
            xoff = 0
            tilt = 0.0
            squash = 1.0
            lunge = 0

            if act == "run":
                tilt = -7.0
                feet -= abs(int(2 * math.sin(tt * 12)))
            elif act == "jump":
                ph = (tt % 1.15) / 1.15
                feet -= int(64 * ph * (1 - ph))
            elif act == "dance":
                feet -= abs(int(3 * math.sin(tt * 9)))
                xoff = int(3 * math.sin(tt * 4.5))
                tilt = -10 * math.sin(tt * 4.5)
            elif act == "spin":
                tilt = -(tt % 1.0) * 360.0
            elif act == "wave":
                tilt = 12 * math.sin(tt * 8)
                feet -= abs(int(2 * math.sin(tt * 8)))
            elif act == "hit":
                c = (tt % 0.9) / 0.9
                lunge = int(9 * max(0.0, 1.0 - abs(c - 0.2) / 0.14))
                xoff += lunge
            elif act == "duck":
                c = (tt % 1.6) / 1.6
                if c < 0.55:
                    squash = 1.0 - 0.42 * math.sin(math.pi * c / 0.55)
            elif act == "sleep":
                tilt = 6.0
                for k in range(3):
                    rise = (tt * 16 + k * 14) % 42
                    zy = int(feet - ch.h - 6 - rise)
                    if zy > 4:
                        img.paste(self.zz, (int(x + ch.w - 2 + k * 7 +
                                                3 * math.sin(tt + k)), zy), self.zz)
            else:  # walk / None
                if ch.hopping:
                    feet -= abs(int(2 * math.sin(tt * 7)))
                elif fr == "B":
                    feet -= CHAR_SCALE

            if squash != 1.0:
                spr = spr.resize((spr.width, max(6, int(spr.height * squash))), NEAREST)
            if tilt != 0.0:
                spr = spr.rotate(tilt, resample=NEAREST, expand=True, fillcolor=(0, 0, 0, 0))

            px = x + xoff + (ch.w - spr.width) // 2
            py = feet - spr.height
            img.paste(spr, (px, py), spr)
            if lunge > 6:
                img.paste(self.pow, (x + ch.w + 2, int(feet - ch.h * 0.75)), self.pow)

        if self.bubble_img and self.actors and 0.55 <= t <= 3.0:
            ch, _ = self.actors[0]
            by = max(2, GROUND_Y + 2 - ch.h - self.bubble_img.height - 4 +
                     int(2 * math.sin(t * 2.2)))
            img.paste(self.bubble_img, (CHAR_X + ch.w - 6, by), self.bubble_img)

    def _draw_particles(self, img, t):
        d = ImageDraw.Draw(img)
        kind = self.part_kind
        for p in self.parts:
            if kind == "leaf":
                x = int((p["x"] - t * 9 + p["sway"] * math.sin(t * 2 + p["ph"])) % (W + 16)) - 8
                y = int((p["y"] + t * (4 + p["v"] * 0.4)) % (GROUND_Y - 6)) + 2
                col = ((255, 196, 66), (255, 150, 60), (140, 200, 90))[int(p["ph"]) % 3]
                d.rectangle([x, y, x + 1, y + 1], fill=col)
            elif kind == "snow":
                x = int((p["x"] + p["sway"] * math.sin(t + p["ph"]) - t * 2) % W)
                y = int((p["y"] + t * (3 + p["v"] * 0.3)) % (GROUND_Y - 4)) + 1
                d.point((x, y), fill=(255, 255, 255))
                d.point((x + 1, y), fill=(235, 242, 250))
            elif kind == "firefly":
                x = int(p["x"] + 18 * math.sin(t * 0.7 + p["ph"]))
                y = int(60 + p["y"] * 0.5 + 8 * math.sin(t * 1.1 + p["ph"] * 2))
                if 0.5 + 0.5 * math.sin(t * p["sp"] + p["ph"]) > 0.35:
                    d.point((x, y), fill=(190, 255, 120))
                    d.point((x + 1, y), fill=(140, 200, 90))
            elif kind == "mote":
                x = int((p["x"] - t * 6) % W)
                y = int((p["y"] + t * 2) % GROUND_Y)
                b = 0.5 + 0.5 * math.sin(t * p["sp"] + p["ph"])
                v = int(120 + 100 * b)
                d.point((x, y), fill=(v, v // 2, min(255, v + 60)))
            elif kind == "bubbla":
                y = GROUND_Y - ((p["y"] + t * p["v"]) % (GROUND_Y - 14)) - 2
                x = int(p["x"] + 2.5 * math.sin(t * 1.7 + p["ph"]))
                r = p["r"]
                d.ellipse([x - r, y - r, x + r, y + r], outline=(185, 225, 250))
            elif kind == "glitter":
                x = int((p["x"] + p["sway"] * math.sin(t + p["ph"])) % W)
                y = int((p["y"] + t * (3 + p["v"] * 0.2)) % (GROUND_Y - 4)) + 1
                col = [(255, 255, 255), (255, 230, 120), (255, 170, 210),
                       (170, 235, 255)][int(t * 2 + p["ph"]) % 4]
                d.point((x, y), fill=col)

    def frame(self, t):
        img = self.sky.copy()
        self._draw_stars(img, t)
        if self.rays is not None:
            img.paste(self.rays, (0, 0), self.rays)
        self._draw_celestial(img, t)
        self._draw_clouds(img, t)
        self._draw_floaters(img, t)
        if self.bird:
            self._draw_bird(img, t)
        if self.hills is not None:
            self._paste_wrapped(img, self.hills, t * 3.0)
        if self.pal.get("sea"):
            self._draw_sea(img, t)
        if self.trees is not None:
            self._paste_wrapped(img, self.trees, t * 9.0)
        if self.weeds:
            self._draw_weeds(img, t)
        self._paste_wrapped(img, self.ground, t * 16.0)
        self._draw_swimmers(img, t)
        self._draw_actors(img, t)
        self._draw_hoppers(img, t)
        self._draw_particles(img, t)
        return img
