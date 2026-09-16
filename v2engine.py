#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v2 PIXEL ANIME — engine. Fristående från v1 (engine.py).
Mänskliga pixelkaraktärer: hår per stil, ögon-reaktioner, mun-läppsynk
(hämtad från röstens envelope), poser: idle/walk/run/punch/hurt/point.
Scener: dock (regn + fyr + signalmast), dojo-interiör (shoji-dörr som ÖPPNAS),
tittskort / eyecatch / next-episode. Kamera: zoom, pan, shake, letterbox.
"""
import math
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

NEAREST = Image.Resampling.NEAREST
W, H = 320, 180           # logisk duk (skalas x4 -> 1280x720)
GROUND = 150              # fötternas baslinje

# ===========================================================================
# PIXELTEXT – litet typsnitt uppskalat NEAREST = äkta pixeltypografi
# ===========================================================================
def ptext(line, scale=3, col=(255, 255, 255)):
    f = ImageFont.load_default()
    im = Image.new("RGBA", (len(line) * 7 + 4, 12), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.fontmode = "1"
    d.text((2, 1), line, font=f, fill=tuple(col) + (255,))
    return im.resize((im.width * scale, im.height * scale), NEAREST)


def ptext_fit(line, col=(255, 255, 255), scales=(5, 4, 3, 2, 1), maxw=W - 20):
    for s in scales:
        im = ptext(line, s, col)
        if im.width <= maxw:
            return im
    return ptext(line, 1, col)


def ptext_center(big, line, y, scale=3, col=(255, 255, 255)):
    t = ptext(line, scale, col)
    big.alpha_composite(t, ((W * 4 - t.width) // 2 // 4, y)) if False else None
    return t


# ===========================================================================
# KROPP – 24 bred x 26 hög. Bokstäver: H=hår S=hud T=top P=byxor B=boots A=bälte
# ===========================================================================
def _rows(s):
    out = [r for r in s.strip("\n").splitlines()]
    w = max(len(r) for r in out)
    return [r.ljust(w, ".") for r in out]


ART = {}

ART["idle"] = _rows("""
........................
......HHHHHHHHH.........
......HHSSSSSSH.........
......HSSWWSSWWSH.......
......HSSWKSSWKSH.......
......HSSSSSSSSH........
......HSSSMMSSH.........
.......SSSSSSS..........
......TTTTTTTTT.........
...TTTTTTTTTTTTTTT......
...TTTTTTTTTTTTTTT......
...TTTTTTTTTTTTTTT......
...TTTTTTTTTTTTTTT......
...SSSTTTTTTTTTSSS......
...SSSTTTTTTTTTSSS......
......TTTTTTTTT.........
......TTTTTTTTT.........
......AAAAAAAAA.........
......PPP...PPPP........
......PPP...PPPP........
......PPP...PPPP........
......PPP...PPPP........
......PPP...PPPP........
......PPP...PPPP........
.....BBBB...BBBBB.......
.....BBBB...BBBBB.......
""")

ART["walk1"] = _rows("""
........................
......HHHHHHHHH.........
......HHSSSSSSH.........
......HSSWWSSWWSH.......
......HSSWKSSWKSH.......
......HSSSSSSSSH........
......HSSSMMSSH.........
.......SSSSSSS..........
......TTTTTTTTT.........
...TTTTTTTTTTTTTTT......
...TTTTTTTTTTTTTTT......
...TTTTTTTTTTTTTTT......
...TTTTTTTTTTTTTTT......
...SSSTTTTTTTTTSSS......
...SSSTTTTTTTTTSSS......
......TTTTTTTTT.........
......TTTTTTTTT.........
......AAAAAAAAA.........
......PPPPPPPPP.........
.....PPPP...PPPPP.......
....PPPP.....PPPPP......
....PPP.......PPPP......
....PPP........PPP......
....PPP........PPP......
...BBBB........BBBB.....
...BBBB........BBBB.....
""")

ART["punch"] = _rows("""
........................
......HHHHHHHHH.........
......HHSSSSSSH.........
......HSSWWSSWWSH.......
......HSSWKSSWKSH.......
......HSSSSSSSSH........
......HSSSMMSSH.........
.......SSSSSSS..........
......TTTTTTTTT.........
...TTTTTTTTTTT..........
...SSTTTTTTTTTTTTTTTTTSS
...SSTTTTTTTTTTTTTTTTTSS
...TTTTTTTTTTT..........
...SSSTTTTTTTT..........
...SSSTTTTTTTT..........
......TTTTTTTTT.........
......TTTTTTTTT.........
......AAAAAAAAA.........
......PPPPPPPPP.........
.....PPPP....PPPP.......
....PPPP......PPPP......
....PPP.......PPPP......
....PPP........PPP......
....PPP........PPP......
...BBBB........BBBB.....
...BBBB........BBBB.....
""")

ART["hurt"] = _rows("""
........................
......HHHHHHHHH.........
......HHSSSSSSH.........
......HSSWWSSWWSH.......
......HSSWKSSWKSH.......
......HSSSSSSSSH........
......HSSSMMSSH.........
.......SSSSSSS..........
......TTTTTTTTT.........
.S...TTTTTTTTTTT...S....
.SS..TTTTTTTTTTT..SS....
.SS.TTTTTTTTTTTT..SS....
.S..TTTTTTTTTTT...S.....
....TTTTTTTTTTT.........
....TTTTTTTTTTT.........
......TTTTTTTTT.........
......TTTTTTTTT.........
......AAAAAAAAA.........
......PPPPPPPPP.........
.....PPPP..PPPP.........
....PPPP..PPPP..........
....PPP...PPPP..........
....PPP....PPP..........
....PPP.....PPP.........
...BBBB.....BBBB........
...BBBB.....BBBB........
""")

ART["point"] = _rows("""
........................
......HHHHHHHHH.........
......HHSSSSSSH.........
......HSSWWSSWWSH.......
......HSSWKSSWKSH.......
......HSSSSSSSSH........
......HSSSMMSSH.........
.......SSSSSSS..........
......TTTTTTTTT..S......
...TTTTTTTTTTT..SS......
...TTTTTTTTTTTSSS.......
...TTTTTTTTTTSSSS.......
...TTTTTTTTTTT..........
...SSSTTTTTTTTT.........
...SSSTTTTTTTTT.........
......TTTTTTTTT.........
......TTTTTTTTT.........
......AAAAAAAAA.........
......PPP...PPPP........
......PPP...PPPP........
......PPP...PPPP........
......PPP...PPPP........
......PPP...PPPP........
......PPP...PPPP........
.....BBBB...BBBBB.......
.....BBBB...BBBBB.......
""")

ART["guard"] = _rows("""
........................
......HHHHHHHHH.........
......HHSSSSSSH.........
......HSSWWSSWWSH.......
......HSSWKSSWKSH.......
......HSSSSSSSSH........
......HSSSMMSSH.........
.......SSSSSSS..........
....SSTTTTTTTTTTSS......
....SSTTTTTTTTTTSS......
....TTT.STT.STTT........
....TTTTTTTTTTTT........
....TTTTTTTTTTTT........
......TTTTTTTTT.........
......TTTTTTTTT.........
......TTTTTTTTT.........
......TTTTTTTTT.........
......AAAAAAAAA.........
......PPP...PPPP........
......PPP...PPPP........
......PPP...PPPP........
......PPP...PPPP........
......PPP...PPPP........
......PPP...PPPP........
.....BBBB...BBBBB.......
.....BBBB...BBBBB.......
""")

# ---------------------------------------------------------------------------
# HÅRSTILAR (ersätter topp-raderna i huvudet; sidlock tillåtna via extra_px)
# ---------------------------------------------------------------------------
HAIR = {}
HAIR["spiky"] = _rows("""
..............H.........
....H..HH..HH.HH..H.....
....HHHHHHHHHHHHHHH.....
....HHHHHHHHHHHHHHH.....
""")
HAIR["long"] = _rows("""
.......HHHHHHH..........
.....HHHHHHHHHHH........
....HHHHHHHHHHHHH.......
....HHHHHHHHHHHHH.......
""")
HAIR["pony"] = _rows("""
...........HHHH.........
......HHHHHHHHHHH.......
......HHHHHHHHHHHH......
......HHHHHHHHHHH.......
""")
HAIR["hawk"] = _rows("""
........HHHHH...........
........HHHHH...........
........HHHHH...........
........HHHHH...........
""")

FACE_X, FACE_Y = 9, 3   # vänster ögats övre hörn i 24x26-biten (W startar här)


def _mk(rows, cols):
    img = Image.new("RGBA", (24, 26), (0, 0, 0, 0))
    px = img.load()
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in cols:
                px[x, y] = cols[ch] + (255,)
    return img


# ---------------------------------------------------------------------------
# ANSIKTET: dynamiska overlays för ögon/mun/blåmärke – ritas ovanpå basbilden
# ---------------------------------------------------------------------------
def _face_patch(img, cols, eyes="normal", mouth="closed", bruise=False):
    """eyes: normal/blink/wide/angry/x/spark/sad  mouth: closed/open/grin/shout"""
    out = img.copy()
    d = ImageDraw.Draw(out)
    skin = cols["S"] + (255,)
    dark = cols["K"] + (255,)
    white = (255, 255, 255, 255)
    # Ansiktsregion (ögon + mun) täcks först med hud om något ska ändras
    cover = [(8, 2), (16, 6)]
    if eyes != "normal" or mouth != "closed":
        d.rectangle(cover, fill=skin)
    # ---- ögon ----
    if eyes == "blink":
        d.line([(8, 4), (10, 4)], fill=dark)
        d.line([(12, 4), (14, 4)], fill=dark)
    elif eyes == "wide":                       # chock: stora vita
        for ex in (8, 12):
            d.rectangle([ex, 2, ex + 2, 5], fill=white)
            d.point((ex + 1, 4), fill=dark)
    elif eyes == "angry":                      # arga bryn + smala ögon
        for ex in (8, 12):
            d.rectangle([ex, 3, ex + 2, 4], fill=white)
            d.point((ex + 1, 4), fill=dark)
        d.line([(8, 3), (10, 2)], fill=dark)   # vänster bryn lutar ner-in
        d.line([(14, 3), (12, 2)], fill=dark)
    elif eyes == "x":                          # X-X (oomtoold)
        for ex in (8, 12):
            d.line([(ex, 3), (ex + 2, 5)], fill=dark)
            d.line([(ex + 2, 3), (ex, 5)], fill=dark)
    elif eyes == "spark":                      # stjärn-glans
        for ex in (8, 12):
            d.point((ex + 1, 3), fill=white); d.point((ex, 4), fill=white)
            d.point((ex + 2, 4), fill=white); d.point((ex + 1, 4), fill=white)
            d.point((ex + 1, 5), fill=white)
    elif eyes == "sad":
        for ex in (8, 12):
            d.point((ex + 1, 4), fill=dark)
            d.rectangle([ex, 4, ex + 2, 4], fill=dark)
    else:                                      # normal
        for ex in (8, 12):
            d.rectangle([ex, 3, ex + 2, 4], fill=white)
            d.point((ex + 1, 4), fill=dark)
    # ---- mun ----
    if mouth == "open":
        d.rectangle([10, 6, 11, 7], fill=dark)
    elif mouth == "grin":
        d.rectangle([9, 6, 12, 6], fill=white)
        d.point((10, 7), fill=dark); d.point((11, 7), fill=dark)
    elif mouth == "shout":
        d.rectangle([9, 6, 12, 7], fill=dark)
        d.point((10, 6), fill=white)
    elif mouth == "frown":
        d.point((9, 7), fill=dark); d.line([(10, 6), (11, 6)], fill=dark)
        d.point((12, 7), fill=dark)
    else:
        d.point((10, 6), fill=dark); d.point((11, 6), fill=dark)
    if bruise:
        red = (235, 90, 90, 255)
        d.point((7, 6), fill=red); d.point((7, 7), fill=red)
        d.point((8, 7), fill=red)
    return out


class PXChar:
    """En mänsklig pixelkaraktär. Samma namn -> samma utseende, för evigt."""

    def __init__(self, name, palette, hair="spiky", scale=1.0, voice_pitch="ren"):
        self.name = name
        self.scale = scale
        self.voice_pitch = voice_pitch
        cols = dict(palette)
        cols.setdefault("W", (250, 250, 250))
        cols.setdefault("K", (24, 22, 28))
        cols.setdefault("M", (90, 30, 40))
        # håret: ersätt topprader rader 0-3
        hair_rows = HAIR[hair]
        hair_col = cols["H"]
        self.cols = cols
        self.hair_col = hair_col
        self.hair_rows = hair_rows
        self._pose_base = {}
        for pose, rows in ART.items():
            base = _mk(self._merge_hair(rows), cols)
            if scale != 1.0:
                nw, nh = int(24 * scale + 0.5), int(26 * scale + 0.5)
                base = base.resize((nw, nh), NEAREST)
            self._pose_base[pose] = base
        # walk2 = spegling av walk1 (annat ben framåt) – gratis gångfas!
        self._pose_base["walk2"] = ImageOps.mirror(self._pose_base["walk1"])

    def _merge_hair(self, rows):
        rows = list(rows)
        for hy, hrow in enumerate(self.hair_rows):
            line = list(rows[hy])
            for x, ch in enumerate(hrow):
                if ch == "H":
                    line[x] = "H"
            rows[hy] = "".join(line)
        return rows

    def get(self, pose, face_eyes="normal", face_mouth="closed", bruise=False, flip=False):
        base = self._pose_base[pose]
        im = _face_patch(base, self.cols, eyes=face_eyes, mouth=face_mouth, bruise=bruise)
        if flip:
            im = ImageOps.mirror(im)
        return im

    @property
    def w(self):
        return self._pose_base["idle"].width

    @property
    def hgt(self):
        return self._pose_base["idle"].height


# ===========================================================================
# SCEN-GRUNDER
# ===========================================================================
def _lerp(a, b, p):
    return a + (b - a) * p


def ease(p):
    return 1 - (1 - p) * (1 - p)


class Track:
    """Nyckelbilder för x-position (+ flaggor)."""
    def __init__(self, pts):
        self.pts = sorted(pts, key=lambda p: p[0])   # [(t, x, flip, pose?)]

    def at(self, t):
        if t <= self.pts[0][0]:
            return self.pts[0][1], self.pts[0][2]
        if t >= self.pts[-1][0]:
            return self.pts[-1][1], self.pts[-1][2]
        for i in range(len(self.pts) - 1):
            t0, x0 = self.pts[i][0], self.pts[i][1]
            t1, x1 = self.pts[i + 1][0], self.pts[i + 1][1]
            if t0 <= t <= t1:
                p = 0 if t1 == t0 else (t - t0) / (t1 - t0)
                e = ease(p)
                return int(_lerp(x0, x1, e)), self.pts[i][2]
        return self.pts[-1][1], self.pts[-1][2]


class Actor:
    """Karaktär + pos-block + ansikts-block + rörelse-track inom en scen."""
    def __init__(self, char, blocks, track, faces=None, y_off=0):
        self.char = char
        self.blocks = sorted(blocks, key=lambda b: b[0])  # [(t0,t1,pose)]
        self.track = track
        self.faces = sorted(faces or [], key=lambda f: f[0])  # [(t,eyes,bruise)]
        self.y_off = y_off
        self.mouth = np.zeros(0)   # per-frame bool array sätts av v2make (lipsynk)

    def pose_at(self, t):
        for t0, t1, pose in self.blocks:
            if t0 <= t < t1:
                return pose
        return self.blocks[-1][2] if self.blocks else "idle"

    def face_at(self, t):
        eyes, bruise = "normal", False
        for ft, fe, fb in self.faces:
            if t >= ft * -1 and ft < 0:   # negativ = tills nästa positiva
                pass
            if t >= abs(ft):
                eyes, bruise = fe, fb
        return eyes, bruise


# ===========================================================================
# SCEN 1 – HAMNEN (regn, fyr, signalmast, lyktstolpar)
# ===========================================================================
class DockNight:
    def __init__(self, seed=0, rain=True, lights_on=False, light_event=None):
        self.rng = random.Random(seed)
        self.rain = rain
        self.light_event = light_event          # tid då hamnens ljus tänds
        self.lights_on = lights_on
        self._build()

    def _build(self):
        self.bg = Image.new("RGB", (W, H), (10, 14, 34))
        d = ImageDraw.Draw(self.bg)
        # himmel: indigo -> teal horisont
        for y in range(96):
            p = y / 95
            col = (int(_lerp(12, 26, p)), int(_lerp(16, 70, p)), int(_lerp(44, 92, p)))
            d.line([(0, y), (W, y)], fill=col)
        for _ in range(60):                     # stjärnor
            d.point((self.rng.randrange(W), self.rng.randrange(78)),
                    fill=(220, 225, 255) if self.rng.random() < .5 else (150, 160, 200))
        # måne
        d.ellipse([250, 12, 278, 40], fill=(238, 236, 210))
        d.ellipse([258, 16, 282, 38], fill=(10, 14, 34, 0))  # halvmåne-känsla
        # hav
        d.rectangle([0, 96, W, 128], fill=(16, 42, 66))
        for _ in range(160):
            x = self.rng.randrange(W); y = self.rng.randrange(98, 126)
            d.point((x, y), fill=self.rng.choice([(40, 90, 120), (30, 70, 100), (70, 130, 150)]))
        # fartyg-silhuett
        d.rectangle([36, 84, 86, 96], fill=(8, 10, 22))
        d.rectangle([48, 76, 60, 84], fill=(8, 10, 22))
        d.rectangle([70, 72, 74, 84], fill=(8, 10, 22))
        # kaj
        d.rectangle([0, 128, W, H], fill=(58, 46, 40))
        for x in range(0, W, 14):
            d.line([(x, 128), (x, H)], fill=(44, 34, 30))
        d.line([(0, 128), (W, 128)], fill=(90, 76, 62))
        for x in range(6, W, 48):               # pålar
            d.rectangle([x, 142, x + 5, H], fill=(38, 30, 26))
        self.tower_x = 236                      # signalmast
        tw = self.tower_x
        d.line([(tw, 128), (tw + 10, 60)], fill=(30, 30, 44))
        d.line([(tw + 16, 128), (tw + 10, 60)], fill=(30, 30, 44))
        for yy in range(66, 122, 10):
            p = (yy - 60) / 68
            d.line([(tw + int(2 * p), yy), (tw + int(16 - 2 * p), yy)], fill=(30, 30, 44))
            d.line([(tw + int(2 * p), yy), (tw + int(16 - 2 * p), yy + 7)], fill=(30, 30, 44))
        d.rectangle([tw + 6, 56, tw + 14, 62], fill=(40, 40, 56))
        self._tower_lamp = None
        # fyr (fyrtorn längst till vänster på molo)
        d.rectangle([6, 76, 20, 128], fill=(36, 34, 48))
        d.rectangle([2, 70, 24, 76], fill=(44, 42, 58))
        d.rectangle([10, 62, 16, 70], fill=(250, 240, 190))
        self.beam_origin = (13, 66)
        # lyktstolpar (släckta tills light_event)
        self.lamp_xs = [70, 150]

    def frame(self, t, lights_on):
        img = self.bg.copy().convert("RGBA")
        d = ImageDraw.Draw(img, "RGBA")
        # fyr-rotorstråle
        ang = t * 0.55
        ox, oy = self.beam_origin
        for da in (-3, 3):
            a2 = ang + math.radians(da)
            d.polygon([(ox, oy), (ox + int(math.cos(a2) * 190), oy + int(math.sin(a2) * 190)),
                       (ox + int(math.cos(ang) * 150), oy + int(math.sin(ang) * 150))],
                      fill=(250, 240, 190, 26))
        # signalmastens lampa: röd blink, ELLER stadiljus-läget tänt varmt
        lamp = (255, 70, 80, 255) if int(t * 2) % 2 == 0 else (80, 30, 36, 255)
        if lights_on:
            lamp = (255, 214, 130, 255)
        tw = self.tower_x
        d.ellipse([tw + 8, 57, tw + 12, 61], fill=lamp)
        if lights_on:
            d.ellipse([tw - 2, 48, tw + 22, 72], fill=(255, 214, 130, 36))
        for lx in self.lamp_xs:
            d.rectangle([lx, 96, lx + 2, 128], fill=(26, 24, 30))
            if lights_on:
                d.ellipse([lx - 3, 91, lx + 5, 99], fill=(255, 224, 150, 255))
                d.ellipse([lx - 9, 85, lx + 11, 105], fill=(255, 224, 150, 40))
                d.rectangle([lx - 2, 128, lx + 4, 132], fill=(255, 224, 150, 70))
            else:
                d.ellipse([lx - 3, 91, lx + 5, 99], fill=(40, 38, 46))
        # stads-ljus i bakgrunden täcks upp
        if lights_on:
            for _ in range(26):
                x = self.rng_lights() if False else None
            self.rng2 = random.Random(7)
            for _ in range(30):
                d.point((self.rng2.randrange(W), self.rng2.randrange(88, 96)),
                        fill=(255, 200, 120, see := 255))
        if self.rain:
            for i in range(80):
                rng = random.Random(i)
                xx = rng.randrange(W + 40)
                sp = 180 + (i % 5) * 30
                yy = (rng.randrange(H) + t * sp) % H
                xx2 = xx - int((H - yy) * 0.18)
                d.line([(xx2, yy), (xx2 - 2, yy + 6)], fill=(160, 190, 220, 110))
        return img


# ===========================================================================
# SCEN 2 – DOJO-INTERIÖR (shoji-dörr som glider upp, boxningssäck som svarar)
# ===========================================================================
class DojoInterior:
    def __init__(self, seed=0, door_t=None, bag_hits=()):
        self.rng = random.Random(seed)
        self.door_t = door_t          # tidpunkt dörren börjar glida
        self.bag_hits = list(bag_hits)
        self._build()

    def _build(self):
        self.bg = Image.new("RGB", (W, H), (96, 70, 48))
        d = ImageDraw.Draw(self.bg)
        for y in range(0, 128, 8):    # träpanel
            d.line([(0, y), (W, y)], fill=(82, 60, 40))
        d.rectangle([0, 128, W, H], fill=(150, 118, 78))     # golv
        for x in range(0, W, 22):
            d.line([(x, 128), (x - 10, H)], fill=(126, 98, 64))
        d.rectangle([0, 126, W, 128], fill=(64, 46, 32))
        # matta
        d.rectangle([60, 132, 190, 162], fill=(64, 92, 120))
        d.rectangle([64, 136, 186, 158], fill=(74, 106, 138))
        # fönster: natt
        d.rectangle([148, 26, 216, 70], fill=(70, 52, 36))
        d.rectangle([152, 30, 212, 66], fill=(12, 18, 40))
        for _ in range(10):
            d.point((self.rng.randrange(153, 212), self.rng.randrange(31, 65)),
                    fill=(200, 205, 235))
        d.line([(182, 30), (182, 66)], fill=(70, 52, 36))
        # boxningssäck
        self.bag_x = 46
        # shoji-dörr (x4 bredd, glider åt vänster in i väggen)
        self.door = Image.new("RGBA", (64, 96), (0, 0, 0, 0))
        dd = ImageDraw.Draw(self.door)
        dd.rectangle([0, 0, 63, 95], fill=(222, 206, 180, 255))
        for gx in range(0, 64, 16):
            dd.line([(gx, 0), (gx, 95)], fill=(140, 110, 84, 255))
        for gy in range(0, 96, 24):
            dd.line([(0, gy), (63, gy)], fill=(140, 110, 84, 255))
        dd.rectangle([0, 0, 63, 95], outline=(110, 86, 60, 255), width=2)
        dd.ellipse([56, 44, 60, 52], fill=(70, 52, 36, 255))
        self.door_rect = (236, 32, 300, 128)
        # dörröppningens mörker + yttre ljuskil
        d.rectangle(list(self.door_rect), fill=(16, 20, 38))
        # väggposter / kalligrafi-rulle
        d.rectangle([108, 30, 128, 78], fill=(228, 220, 204))
        dd2 = ImageDraw.Draw(self.bg)
        dd2.line([(118, 38), (118, 70)], fill=(30, 26, 30), width=2)
        dd2.line([(114, 46), (122, 46)], fill=(30, 26, 30))

    def frame(self, t):
        img = self.bg.copy().convert("RGBA")
        d = ImageDraw.Draw(img, "RGBA")
        # boxningssäck: pendel efter träffar
        sw = 0.0
        for ht in self.bag_hits:
            if t > ht:
                sw += 14.0 * math.exp(-(t - ht) * 2.2) * math.sin((t - ht) * 7.0)
        bx = self.bag_x + int(sw)
        d.line([(bx + 7, 10), (bx + 7, 30)], fill=(30, 26, 26, 255))
        d.ellipse([bx, 30, bx + 14, 64], fill=(150, 60, 46, 255))
        d.ellipse([bx + 2, 34, bx + 6, 40], fill=(180, 84, 66, 255))
        # dörr: glider upp under 0.9s; ljuskil strömmar in
        x0, y0, x1, y1 = self.door_rect
        p = 0.0
        if self.door_t is not None and t > self.door_t:
            p = min(1.0, (t - self.door_t) / 0.9)
            p = ease(p)
        if p > 0:
            d.polygon([(x0, y1), (x1, y1), (x1 - 20 - int(20 * p), y0)],
                      fill=(255, 232, 170, int(20 + 60 * p)))
        off = int(64 * p)
        img.alpha_composite(self.door, (x0 + off, y0))
        return img


# ===========================================================================
# KORT – titel / eyecatch / preview (helskärmar, ingen kamera)
# ===========================================================================
class Card:
    def __init__(self, bg_col=(8, 8, 16), seed=0):
        self.rng = random.Random(seed)
        self.bg_col = bg_col

    def _base(self, t):
        img = Image.new("RGBA", (W, H), self.bg_col + (255,))
        d = ImageDraw.Draw(img, "RGBA")
        for i in range(26):          # pulsande stjärnstoft
            rng = random.Random(i)
            if int(t * 8 + i) % 3 == 0:
                d.point((rng.randrange(W), rng.randrange(H)),
                        fill=(255, 240, 200, 120))
        return img, d


class TitleCard(Card):
    def __init__(self, series, episode, seed=0):
        super().__init__((6, 6, 14), seed)
        self.series = series
        self.episode = episode

    def frame(self, t):
        img, d = self._base(t)
        flick = (int(t * 11) % 7) != 3
        if flick:
            big = ptext_fit(self.series, col=(120, 230, 255), maxw=W - 16)
            img.alpha_composite(big, ((W - big.width) // 2, 42))
            glow = ptext_fit(self.series, col=(255, 255, 255), maxw=W - 20)
            img.alpha_composite(glow, ((W - glow.width) // 2 - 2, 40))
        if t > 0.9:
            sub = ptext_fit(self.episode, col=(255, 220, 150), maxw=W - 24)
            img.alpha_composite(sub, ((W - sub.width) // 2, 106))
            ln = ptext_fit("PIXEL ANIME - frame by frame, by your CPU",
                           col=(150, 150, 170), maxw=W - 6)
            img.alpha_composite(ln, ((W - ln.width) // 2, 132))
        return img


class EyecatchCard(Card):
    """Halvtidskortet! Karaktär i pose + serienamn (KonoSuba-stil)."""
    def __init__(self, pxchar, series, catchword, seed=0, dark=False):
        super().__init__((30, 8, 20) if dark else (10, 22, 50), seed)
        self.px = pxchar
        self.series = series
        self.catchword = catchword
        self.dark = dark

    def frame(self, t):
        img, d = self._base(t)
        for i in range(-4, 22):      # diagonala strålar
            col = (60, 120, 200, 70) if not self.dark else (200, 60, 80, 70)
            if i % 2 == 0:
                d.polygon([(i * 18 - int(t * 60) % 36, H), (i * 18 + 40 - int(t * 60) % 36, 0),
                           (i * 18 + 64 - int(t * 60) % 36, 0), (i * 18 + 24 - int(t * 60) % 36, H)],
                          fill=col)
        big = self.px.get_bust_scaled("angry", "grin", 5)
        if self.dark:
            from PIL import ImageOps as _IO
            big = _IO.mirror(big)
        bob = int(math.sin(t * 6) * 3)
        img.alpha_composite(big, (10, H - big.height - 6 + bob))
        nm = ptext_fit(self.series, col=(255, 255, 255), scales=(3, 2, 1), maxw=150)
        img.alpha_composite(nm, (W - nm.width - 12, 16))
        cw = ptext_fit(self.catchword, col=(150, 230, 255) if not self.dark else (255, 150, 150),
                       scales=(2, 1), maxw=150)
        img.alpha_composite(cw, (W - cw.width - 12, 16 + nm.height + 6))
        return img


class PreviewCard(Card):
    def __init__(self, episode_no, title, lines, seed=0):
        super().__init__((4, 6, 14), seed)
        self.no = episode_no
        self.title = title
        self.lines = lines

    def frame(self, t):
        img, d = self._base(t)
        h1 = ptext_fit("NEXT EPISODE", col=(255, 210, 110), scales=(4, 3, 2), maxw=W - 20)
        img.alpha_composite(h1, ((W - h1.width) // 2, 26))
        h2 = ptext_fit(f"EPISODE {self.no:03d} - '{self.title}'", col=(140, 220, 255),
                       scales=(2, 1), maxw=W - 24)
        img.alpha_composite(h2, ((W - h2.width) // 2, 26 + h1.height + 10))
        y = 26 + h1.height + 30
        for ln in self.lines:
            tt = ptext_fit(ln, col=(210, 210, 220), scales=(1,), maxw=W - 30)
            img.alpha_composite(tt, ((W - tt.width) // 2, y))
            y += tt.height + 6
        fade = ptext_fit("The static is listening.", col=(120, 120, 140), maxw=W - 40)
        img.alpha_composite(fade, ((W - fade.width) // 2, y + 6))
        return img


# ===========================================================================
# FX & KAMERA
# ===========================================================================
def apply_camera(img, t, ops):
    """ops: zoom/pan/shake/letterbox. Returnerar (320x180)-bild."""
    d = ImageDraw.Draw(img, "RGBA")
    for op in ops:
        k = op["kind"]
        if k == "zoom":
            z = op["z"](t) if callable(op["z"]) else op["z"]
            if z > 1.001:
                fx, fy = op.get("focus", (W // 2, H // 2))
                cw, ch = W / z, H / z
                x0 = min(max(fx - cw / 2, 0), W - cw)
                y0 = min(max(fy - ch / 2, 0), H - ch)
                img = img.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), NEAREST)
                d = ImageDraw.Draw(img, "RGBA")
        elif k == "shake":
            t0, t1, amp = op["t0"], op["t1"], op.get("amp", 3)
            if t0 <= t <= t1:
                dx = int(math.sin(t * 47.0) * amp)
                dy = int(math.cos(t * 39.0) * amp * 0.6)
                img = ImageOps.expand(img, border=amp, fill=(0, 0, 0, 255)).crop(
                    (amp - dx, amp - dy, amp - dx + W, amp - dy + H))
                d = ImageDraw.Draw(img, "RGBA")
    for op in ops:                       # letterbox SIST
        if op["kind"] == "letterbox":
            hgt = op.get("h", 14)
            d.rectangle([0, 0, W, hgt], fill=(0, 0, 0, 255))
            d.rectangle([0, H - hgt, W, H], fill=(0, 0, 0, 255))
    return img


def speedlines(img, cx, cy, n=26, col=(255, 255, 255, 120)):
    d = ImageDraw.Draw(img, "RGBA")
    for i in range(n):
        a = i * (2 * math.pi / n) + 0.13
        r0 = 26 + (i % 4) * 7
        r1 = r0 + 40 + (i % 5) * 12
        d.line([(cx + int(math.cos(a) * r0), cy + int(math.sin(a) * r0)),
                (cx + int(math.cos(a) * r1), cy + int(math.sin(a) * r1))], fill=col, width=1)


def kiai(img, cx, cy, n=12):
    d = ImageDraw.Draw(img, "RGBA")
    for i in range(n):
        a = i * (2 * math.pi / n)
        r0, r1 = 30, 90 + (i % 3) * 20
        col = [(255, 120, 60, 160), (255, 200, 90, 150), (255, 255, 255, 140)][i % 3]
        d.line([(cx + int(math.cos(a) * r0), cy + int(math.sin(a) * r0)),
                (cx + int(math.cos(a) * r1), cy + int(math.sin(a) * r1))], fill=col, width=3)


def aura(img, x, y_base, hgt, t, hue="violet"):
    """Eld-flamma runt karaktären: rader med flicker, genomskinlig = hjälten syns."""
    d = ImageDraw.Draw(img, "RGBA")
    pal = {"violet": [(150, 90, 235, 120), (190, 140, 255, 100), (245, 230, 255, 165)],
           "gold":   [(255, 170, 60, 120), (255, 215, 110, 100), (255, 248, 210, 165)]}[hue]
    rows = int(hgt)
    for i, c in enumerate(pal):
        wscale = (9 - i * 3) * 1.15
        step = 2
        for r in range(0, rows, step):
            p = r / rows
            base_w = wscale * (1.0 - p ** 1.5) + 1.5
            fl = math.sin(t * 11.0 + r * 0.35 + i * 2.4) * (1.5 + p * 3.0)
            xx = x + int(math.sin(t * 7 + r * 0.2) * p * 2.0)
            wdt = max(1, int(base_w + fl))
            y0 = y_base - r - step
            d.rectangle([xx - wdt, y0, xx + wdt, y0 + step - 1], fill=c)
        for k in range(3):
            rng = random.Random(k * 7 + int(t * 6))
            tip = y_base - int(hgt * (0.5 + 0.45 * rng.random()))
            xo = x + rng.randrange(-6, 7)
            d.line([(xo, tip + 8), (xo + rng.randrange(-3, 4), tip)], fill=c, width=2)
    for i in range(6):
        rng = random.Random(i)
        yy = y_base - ((t * 34 + rng.randrange(int(hgt))) % (hgt + 10))
        d.point((x + rng.randrange(-9, 9), yy), fill=(255, 255, 255, 210))


def dust(img, x, y, n=7):
    d = ImageDraw.Draw(img, "RGBA")
    for i in range(n):
        rng = random.Random(i * 7)
        x0 = x + rng.randrange(-16, 14)
        y0 = y + rng.randrange(-9, 3)
        d.ellipse([x0, y0, x0 + 5, y0 + 4], fill=(120, 110, 100, 90))


def slash(img, x, y, t0, t):
    if not (t0 <= t <= t0 + 0.35):
        return
    d = ImageDraw.Draw(img, "RGBA")
    p = (t - t0) / 0.35
    ln = int(60 * math.sin(math.pi * min(1.0, p * 1.35)))
    d.line([(x - ln, y + ln // 2), (x + ln, y - ln // 2)], fill=(255, 255, 255, 230), width=2)
    d.line([(x - ln, y + ln // 2 + 2), (x + ln, y - ln // 2 + 2)], fill=(150, 230, 255, 150), width=1)


def word_burst(img, word, x, y, t0, t, col=(255, 235, 120)):
    if not (t0 <= t <= t0 + 0.9):
        return
    p = (t - t0) / 0.9
    scl = max(1, int(_lerp(2, 5, min(1.0, p * 4)) + math.sin(p * 26)))
    tt = ptext(word, scale=scl, col=col)
    img.alpha_composite(tt, (x - tt.width // 2 + int(math.sin(p * 33) * 2),
                             y - tt.height // 2 + int(p * 6)))


def impact_flash(img, t0, t, invert=False):
    p = (t - t0) / 0.22
    if 0 <= p <= 1:
        if invert and p < 0.5:
            rgb = np.asarray(img.convert("RGB"), dtype=np.uint8)
            Image.fromarray(255 - rgb, "RGB").convert("RGBA")
            arr = Image.fromarray(255 - rgb, "RGB").convert("RGBA")
            return Image.blend(img.convert("RGB"), arr.convert("RGB"), min(1.0, p * 2)).convert("RGBA")
        white = Image.new("RGBA", img.size, (255, 255, 255, 255))
        return Image.blend(img, white, (1 - p) * 0.92)
    return img


# ===========================================================================
# v3 REAL ANIME RIG – skelett-kapsel-kropp (animeproportioner, INTE chibi)
# + detaljerat animehuvud (iris, glans, ögonfrans, bryn, näsa)
# ===========================================================================
from PIL import ImageChops

BODY_CV_W, BODY_CV_H = 56, 92
GROUND_CV = 88            # lokala y=0 (golv) mappar hit
JW, JW2 = 5, 4            # kapseltjocklekar


def _cap(d, p0, p1, col, wdt, outl):
    if outl:
        d.line([(p0[0], p0[1]), (p1[0], p1[1])], fill=outl, width=wdt + 2)
    d.line([(p0[0], p0[1]), (p1[0], p1[1])], fill=col, width=wdt)
    r = wdt / 2
    for p in (p0, p1):
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=col)


def _stand():
    """Lokala leder, +x = framåt (höger), +y = UPPÅT från golvyta 0."""
    return {
        "footL": (-5, 0), "footR": (5, 0),
        "kneeL": (-5, 15), "kneeR": (5, 15),
        "hipL": (-3, 29), "hipR": (3, 29),
        "pelvis": (0, 30),
        "shoulderL": (-8, 54), "shoulderR": (8, 54),
        "elbowL": (-10, 42), "elbowR": (10, 42),
        "handL": (-10, 31), "handR": (10, 31),
        "neck": (0, 56),
    }


def _mid(a, b, f=0.5):
    return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)


def joints_for(pose, t):
    j = _stand()
    if pose in ("walk", "run"):
        run = pose == "run"
        ph = 2 * math.pi * (t * (2.0 if run else 1.25))
        sw = 11.0 if run else 7.0
        j["footL"] = (-5 + sw * math.sin(ph), max(0.0, 2.6 * math.cos(ph - 0.5)))
        j["footR"] = (5 - sw * math.sin(ph), max(0.0, 2.6 * math.cos(ph + math.pi - 0.5)))
        for side in ("L", "R"):
            hip = j["hip" + side]; foot = j["foot" + side]
            kneed = _mid(hip, foot)
            j["knee" + side] = (kneed[0] - (3.0 if not run else 4.5),
                                kneed[1] + 1.5 + foot[1] * 0.4)
        j["handL"] = (-10 - sw * 0.8 * math.sin(ph), 31 + 2 * math.sin(ph))
        j["handR"] = (10 + sw * 0.8 * math.sin(ph), 31 + 2 * math.sin(ph + math.pi))
        j["elbowL"] = _mid(j["shoulderL"], j["handL"], 0.55)
        j["elbowR"] = _mid(j["shoulderR"], j["handR"], 0.55)
        bob = (2.6 if run else 1.4) * abs(math.sin(ph))
        for k in ("pelvis", "shoulderL", "shoulderR", "hipL", "hipR", "neck",
                  "elbowL", "elbowR", "handL", "handR"):
            j[k] = (j[k][0], j[k][1] - bob)
        if run:
            for k in ("shoulderL", "shoulderR", "neck"):
                j[k] = (j[k][0] + 4, j[k][1] - 1)
    elif pose == "punch":
        j["elbowR"] = (11, 56)
        j["handR"] = (23, 57)
        j["handL"] = (2, 43)
        j["elbowL"] = (-6, 46)
        for k in ("shoulderL", "shoulderR", "neck", "pelvis"):
            j[k] = (j[k][0] + 3, j[k][1])
        j["footR"] = (10, 0)
        j["kneeR"] = (6, 14)
    elif pose == "hurt":
        j["handL"] = (-15, 60)
        j["handR"] = (3, 66)
        j["elbowL"] = (-12, 52)
        j["elbowR"] = (6, 58)
        for k in ("shoulderL", "shoulderR", "neck"):
            j[k] = (j[k][0] - 4, j[k][1] + (2 if k == "neck" else 0))
        j["footR"] = (11, 0)
        j["kneeR"] = (8, 13)
    elif pose == "point":
        j["handR"] = (15, 64)
        j["elbowR"] = (11, 59)
    elif pose == "guard":
        j["handL"] = (4, 50)
        j["handR"] = (0, 52)
        j["elbowL"] = (-11, 45)
        j["elbowR"] = (11, 46)
    else:  # idle: andning
        b = math.sin(t * 2.0) * 0.8
        for k in ("shoulderL", "shoulderR", "neck"):
            j[k] = (j[k][0], j[k][1] - b)
    return j


class Suit:
    """Outfit-färger per person."""
    def __init__(self, jacket, pants, boots, skin, outl=(18, 16, 24)):
        self.jacket, self.pants, self.boots, self.skin, self.outl = \
            jacket, pants, boots, skin, outl


def _dk(c, f=0.62):
    return tuple(int(v * f) for v in c[:3])


def draw_body(img, suit, j, scale=1.0):
    """Ritar kapsel-kroppen i en 56x92-canvas. Bakre->främre."""
    d = ImageDraw.Draw(img)
    ox, oy = BODY_CV_W // 2, GROUND_CV

    def P(name):
        x, y = j[name]
        return (ox + int(x * scale), oy - int(y * scale))

    out = suit.outl
    shL, shR = P("shoulderL"), P("shoulderR")
    hipL, hipR = P("hipL"), P("hipR")
    knL, knR = P("kneeL"), P("kneeR")
    ftL, ftR = P("footL"), P("footR")
    # ben: bakre (vänster) mörkare
    for (hip, kn, ft, colp) in ((hipL, knL, ftL, _dk(suit.pants)),
                                (hipR, knR, ftR, suit.pants)):
        _cap(d, hip, kn, colp, int(JW * scale), out)
        _cap(d, kn, ft, colp, int(JW2 * scale), out)
        # boot: box + tå
        bx, by = ft
        d.rectangle([bx - 3, by - 5, bx + 4, by], fill=out)
        d.rectangle([bx - 2, by - 4, bx + 3, by - 1], fill=suit.boots)
        d.rectangle([bx + 3, by - 4, bx + 6 + (1 if ft is ftR else 0), by - 2], fill=suit.boots)
        d.line([(bx + 3, by - 3), (bx + 6, by - 2)], fill=out)
    # bälte/bäcken
    d.ellipse([P("pelvis")[0] - 8, P("pelvis")[1] - 4, P("pelvis")[0] + 8, P("pelvis")[1] + 4],
              fill=suit.pants)
    # torso (kapsel-axlar + kapsel-kropp)
    _cap(d, hipL, hipR, suit.jacket, int(9 * scale), out)
    _cap(d, shL, shR, suit.jacket, int(8 * scale), out)
    _cap(d, P("pelvis"), P("neck"), suit.jacket, int(11 * scale), out)
    # tvåtons-skuggning: höger sida mörkare (ljus från vänster)
    _cap(d, (P("pelvis")[0] + 7, P("pelvis")[1]), (shR[0] + 2, shR[1]),
         _dk(suit.jacket, 0.8), int(6 * scale), _dk(suit.jacket, 0.8))
    # krage + dragkedja
    nx, ny = P("neck")
    d.polygon([(nx - 5, ny + 2), (nx, ny - 3), (nx + 5, ny + 2)], fill=_dk(suit.jacket, 0.8))
    d.line([(nx, ny + 2), (nx, P("pelvis")[1] + 2)], fill=_dk(suit.jacket, 0.7))
    # armar: bakre (vänster) före torso-arm-konflikt: rita bakre arm FÖRE torso? enkelt: båda efter
    for (sh, el, hd, cols_) in ((shL, P("elbowL"), P("handL"), _dk(suit.jacket)),
                                (shR, P("elbowR"), P("handR"), suit.jacket)):
        _cap(d, sh, el, cols_, int(5 * scale), out)
        _cap(d, el, hd, cols_, int(4 * scale), out)
        hx, hy = hd
        d.rectangle([hx - 2, hy - 2, hx + 2, hy + 2], fill=suit.skin)
        d.rectangle([hx - 2, hy - 2, hx + 2, hy + 2], outline=out)


# ---------------------------------------------------------------------------
# ANIMEHUVUD 26x24 – ansiktsupplägg ritas dynamiskt per frame
# ---------------------------------------------------------------------------
def _lt(c, f=1.25):
    return tuple(min(255, int(v * f)) for v in c[:3])


def _base_head(skin, out):
    # canvas 34x34 (+5 pixlar ovanför gamla 30-ramen: hårtopparna får plats)
    h = Image.new("RGBA", (34, 34), (0, 0, 0, 0))
    d = ImageDraw.Draw(h)
    dk = _dk(skin, 0.82)
    d.polygon([(17, 33), (8, 30), (5, 23), (5, 13), (29, 13), (29, 23), (26, 30)], fill=skin)
    # skugg-sida (höger kant, ljuset kommer vänsterifrån) + käkskugga
    d.polygon([(27, 14), (29, 14), (28, 21), (28, 26), (27, 26)], fill=dk)
    d.polygon([(23, 28), (26, 30), (17, 33)], fill=dk)
    d.line([(9, 30), (16, 32)], fill=dk)
    # öra
    d.rectangle([4, 17, 5, 21], fill=skin)
    d.point((4, 18), fill=dk)
    return h


def _hair(d, style, col, out):
    dk = _dk(col, 0.78)
    lt = _lt(col)
    if style == "spiky":
        d.polygon([(2, 16), (4, 7), (8, 11), (11, 4), (15, 10), (18, 3), (21, 9),
                   (25, 4), (28, 10), (31, 6), (33, 15), (30, 11), (17, 8), (4, 11)], fill=col)
        d.polygon([(4, 11), (17, 8), (30, 11), (32, 14), (30, 13), (17, 10), (5, 13), (2, 16)],
                  fill=dk)
        d.line([(6, 14), (10, 12)], fill=dk)
        d.line([(24, 12), (28, 14)], fill=dk)
        d.point((12, 7), fill=lt); d.point((19, 6), fill=lt)
    elif style == "long":
        d.polygon([(1, 17), (4, 6), (17, 3), (30, 6), (33, 17), (29, 12), (17, 9), (5, 12)],
                  fill=col)
        d.polygon([(1, 17), (5, 12), (5, 32), (2, 29)], fill=dk)
        d.polygon([(33, 17), (29, 12), (29, 32), (32, 29)], fill=dk)
        d.polygon([(5, 12), (17, 9), (29, 12), (28, 13), (17, 11), (6, 13)], fill=dk)
        d.line([(12, 8), (12, 12)], fill=dk)
        d.line([(22, 8), (22, 12)], fill=dk)
    elif style == "pony":
        d.polygon([(2, 16), (4, 6), (17, 3), (30, 6), (32, 16), (28, 11), (17, 8), (6, 11)],
                  fill=col)
        d.polygon([(3, 8), (-1, 15), (0, 29), (4, 25), (4, 15)], fill=dk)
        d.polygon([(29, 9), (33, 14), (32, 17)], fill=col)
        d.polygon([(6, 11), (17, 8), (28, 11), (27, 12), (17, 10), (7, 12)], fill=dk)
        d.line([(8, 12), (12, 10)], fill=dk)
        d.point((14, 7), fill=lt)
    elif style == "hawk":
        d.polygon([(11, 13), (12, 2), (17, 0), (22, 2), (23, 13), (20, 8), (14, 8)], fill=col)
        d.line([(13, 5), (21, 5)], fill=dk)
        d.point((18, 3), fill=lt)


def make_head_images(cols, hair_style, iris):
    skin, out = cols["S"], cols["K"]
    white = (255, 255, 255, 255)

    heads = {}
    for state in ("normal", "blink", "wide", "angry", "x", "spark", "sad", "whiteout"):
        im = _base_head(skin, out)
        d = ImageDraw.Draw(im)
        _hair(d, hair_style, cols["H"], out)

        def eye(cx, cy, side):
            if state == "blink":
                d.line([(cx - 3, cy), (cx + 2, cy)], fill=out, width=1)
                return
            if state == "x":
                d.line([(cx - 3, cy - 3), (cx + 2, cy + 3)], fill=out)
                d.line([(cx + 2, cy - 3), (cx - 3, cy + 3)], fill=out)
                return
            if state == "spark":
                for dx, dy in ((0, -4), (-3, -1), (2, -1), (-2, 2), (1, 2), (0, 4)):
                    d.point((cx + dx, cy + dy), fill=white)
                return
            tall = 1 if state == "wide" else 0
            # öga: vitor + iris + glans + frans (stora anime-ögon)
            if state == "whiteout":            # One Piece: tomma vita ögon m. pupillprick
                d.rectangle([cx - 3, cy - 5, cx + 3, cy + 3], fill=white)
                d.point((cx - 1, cy + 1), fill=out)
                d.line([(cx - 3, cy - 5), (cx + 3, cy - 5)], fill=out)
            else:
                d.rectangle([cx - 3, cy - 4 - tall, cx + 3, cy + 3], fill=white)
                d.rectangle([cx - 2, cy - 3 - tall, cx, cy + 3], fill=iris + (255,))
                d.rectangle([cx - 1, cy - 1, cx - 1, cy + 3], fill=_dk(iris, 0.55) + (255,))
                d.point((cx - 2, cy - 3 - tall), fill=white)                   # GLANSEN
                if state == "angry":
                    d.rectangle([cx - 3, cy - 4, cx + 3, cy - 1], fill=out)
                d.line([(cx - 3, cy - 4 - tall), (cx + 3, cy - 4 - tall)], fill=out)  # frans
                d.point((cx - 2, cy + 4), fill=_dk(skin, 0.65))                # nedre frans
        eye(10, 19, 1)
        eye(23, 19, -1)
        # bryn
        if state == "angry":
            d.line([(6, 15), (12, 17)], fill=out, width=1)
            d.line([(27, 15), (21, 17)], fill=out, width=1)
            d.line([(6, 14), (12, 15)], fill=_dk(out, 0.7))
        elif state == "sad":
            d.line([(6, 17), (12, 15)], fill=out)
            d.line([(27, 17), (21, 15)], fill=out)
        elif state in ("normal", "wide", "spark"):
            d.line([(7, 15), (12, 15)], fill=_dk(cols["H"], 0.5))
            d.line([(22, 15), (27, 15)], fill=_dk(cols["H"], 0.5))
        # näsa
        d.line([(16, 22), (17, 24)], fill=_dk(skin, 0.7))
        if state == "angry":
            d.point((14, 24), fill=_dk(skin, 0.6))
        heads[state] = im

    def with_mouth(im, mouth, addons=()):
        out_im = im.copy()
        d = ImageDraw.Draw(out_im)
        mc = (28, 16, 22, 255)
        teeth = (250, 250, 246, 255)
        tongue = (200, 80, 90, 255)
        if mouth == "open":
            d.rectangle([13, 26, 21, 29], fill=mc)
            d.rectangle([14, 28, 20, 29], fill=tongue)
            d.line([(13, 26), (21, 26)], fill=teeth)
        elif mouth == "grin":
            d.rectangle([12, 26, 22, 28], fill=teeth)
            d.line([(12, 28), (22, 28)], fill=out)
            d.line([(17, 26), (17, 28)], fill=_dk((250, 250, 246), 0.7))
            d.point((11, 26), fill=out); d.point((23, 26), fill=out)
        elif mouth == "shout":
            d.rectangle([12, 25, 22, 30], fill=mc)
            d.rectangle([12, 25, 22, 26], fill=teeth)
            d.rectangle([14, 29, 20, 30], fill=tongue)
        elif mouth == "grit":                    # One Piece-argbest: knäppt tänder
            d.rectangle([11, 25, 23, 29], fill=teeth)
            for gx in (14, 17, 20):
                d.line([(gx, 25), (gx, 29)], fill=_dk((250, 250, 246), 0.55))
            d.line([(11, 27), (23, 27)], fill=_dk((250, 250, 246), 0.5))
            d.rectangle([11, 25, 11, 29], outline=out)
        elif mouth == "frown":
            d.line([(13, 28), (21, 27)], fill=out)
            d.point((12, 29), fill=out); d.point((22, 27), fill=out)
        else:
            d.line([(14, 27), (20, 27)], fill=_dk(skin, 0.6))
        # anime-ikoner: svett / vredesåder / rodnad
        if "sweat" in addons:
            for i, (sx, sy) in enumerate(((29, 14), (31, 19), (4, 15))):
                d.rectangle([sx, sy, sx + 1, sy + 2], fill=(170, 220, 250, 255))
                d.point((sx, sy), fill=white)
        if "vein" in addons:
            vx, vy = 27, 9
            d.line([(vx - 2, vy), (vx + 2, vy)], fill=out)
            d.line([(vx, vy - 2), (vx, vy + 2)], fill=out)
            d.line([(vx - 3, vy + 2), (vx + 3, vy - 2)], fill=_dk(out, 0.6))
        if "blush" in addons:
            for bx in (7, 26):
                d.point((bx, 23), fill=(245, 140, 150, 200))
                d.point((bx + 1, 23), fill=(245, 140, 150, 200))
        if "bruise" in addons:
            d.point((27, 25), fill=(230, 90, 90, 255)); d.point((27, 26), fill=(230, 90, 90, 255))
            d.point((28, 26), fill=(230, 90, 90, 255))
        return out_im

    return heads, with_mouth


class AnimeChar:
    """Skelett-animehjälte. draw() renderar kropp+huvud som EN bild (cachad)."""

    def __init__(self, name, palette, hair="spiky", iris=(200, 120, 40),
                 suit=None, scale=1.0, voice_pitch="ren"):
        self.name = name
        self.scale = scale
        self.voice_pitch = voice_pitch
        self.suit = suit or Suit(jacket=palette.get("T", (50, 60, 120)),
                                 pants=palette.get("P", (50, 50, 60)),
                                 boots=palette.get("B", (60, 45, 35)),
                                 skin=palette["S"])
        self.heads, self._with_mouth = make_head_images(palette, hair, iris)
        self._cache = {}
        self.hair_style = hair
        self.dark = palette.get("__dark__", False)

    def full(self, pose, t, eyes="normal", mouth="closed", bruise=False, addons=()):
        key = (pose, round(t * (6.0 if pose in ("walk", "run") else 2.0), 2),
               eyes, mouth, bruise, addons)
        if key in self._cache:
            return self._cache[key]
        img = Image.new("RGBA", (BODY_CV_W, BODY_CV_H), (0, 0, 0, 0))
        j = joints_for("walk" if pose == "mov" else pose,
                       t if pose in ("walk", "run", "idle", "mov") else 0.0)
        draw_body(img, self.suit, j, scale=1.0)
        # huvud: neck-led (0,56) -> huvudets nederdel ditsätts
        head = self.heads.get(eyes, self.heads["normal"])
        head = self._with_mouth(head, mouth, addons)
        if bruise:
            hd = ImageDraw.Draw(head)
            hd.point((20, 16), fill=(235, 90, 90, 255))
            hd.point((20, 17), fill=(235, 90, 90, 255))
        hscale = 1.38
        head = head.resize((int(head.width * hscale), int(head.height * hscale)), NEAREST)
        nx = BODY_CV_W // 2 + int(j["neck"][0])
        ny = GROUND_CV - int(j["neck"][1])
        img.alpha_composite(head, (nx - head.width // 2, ny - head.height + 8))
        if self.scale != 1.0:
            img = img.resize((int(BODY_CV_W * self.scale), int(BODY_CV_H * self.scale)), NEAREST)
        self._cache[key] = img
        return img

    def bust(self, eyes="angry", mouth="grin", addons=()):
        """Bröstbild: huvud + axelparti (anime-byst). addons: sweat/vein/blush/bruise."""
        head = self._with_mouth(self.heads.get(eyes, self.heads["normal"]), mouth, addons)
        b = Image.new("RGBA", (44, 40), (0, 0, 0, 0))
        d = ImageDraw.Draw(b)
        out = self.suit.outl
        d.polygon([(0, 39), (3, 31), (12, 29), (22, 27), (32, 29), (41, 31), (44, 39)],
                  fill=self.suit.jacket)
        d.polygon([(0, 39), (3, 31), (12, 29), (22, 27), (32, 29), (41, 31), (44, 39)],
                  outline=out)
        d.rectangle([21, 28, 22, 39], fill=_dk(self.suit.jacket, 0.7))
        d.rectangle([20, 26, 23, 28], fill=self.suit.skin)
        b.alpha_composite(head, (5, 3))
        return b

    def get_bust_scaled(self, eyes, mouth, n, addons=()):
        return self.bust(eyes, mouth, addons).resize((44 * n, 40 * n), NEAREST)


def cutin(img, char, t_since, side, name, chip_col, mood="normal", addons=()):
    """Närbilds-insättning vid replik: dämpad scen + strålvifte + stor byst."""
    ov = Image.new("RGBA", img.size, (6, 8, 18, 150))
    img.alpha_composite(ov)
    d = ImageDraw.Draw(img, "RGBA")
    cw, ch2 = img.size
    cx = cw - 240 if side else 240
    for i in range(14):
        a = i * math.pi / 14 + math.pi / 24
        col = tuple(min(255, c + 46) for c in chip_col[:3]) + (58,)
        d.polygon([(cx, ch2), (cx + int(math.cos(a - 0.02) * 900), 0),
                   (cx + int(math.cos(a + 0.02) * 900), 0)], fill=col)
    slide = int(max(0.0, (0.14 - t_since)) * 900)
    faces = {"normal": ("angry", "grin"), "grit": ("angry", "grit"),
             "rage": ("whiteout", "shout"), "hurt": ("x", "open")}
    fv, fm = faces.get(mood, ("angry", "grin"))
    bust = char.get_bust_scaled(fv, fm, 9, addons)
    if not side:
        from PIL import ImageOps as _IO
        bust = _IO.mirror(bust)
    bx = img.width - bust.width - 80 + slide if side else 80 - slide
    img.alpha_composite(bust, (bx, img.height - bust.height - 46))
    nm = ptext(name.upper(), scale=4, col=(255, 255, 255))
    bar = Image.new("RGBA", (nm.width + 26, nm.height + 14), tuple(chip_col[:3]) + (255,))
    bar.alpha_composite(nm, (13, 7))
    tx = img.width - bar.width - 80 if side else 80
    img.alpha_composite(bar, (tx, img.height - bar.height - 46))
    return img


def faceoff(img, charA, charB, active, chip_a, chip_b, name_a, name_b, t_since):
    """DUELL-SPLIT: två stora byster från varsin kant, diagonalblixt mellan dem."""
    ov = Image.new("RGBA", img.size, (6, 8, 18, 165))
    img.alpha_composite(ov)
    d = ImageDraw.Draw(img, "RGBA")
    cw, ch2 = img.size
    # diagonal skiljelinje (blixt)
    zx = cw // 2
    pts = [(zx + 10, 0), (zx - 16, ch2 // 2), (zx - 2, ch2 // 2), (zx - 18, ch2),
           (zx + 4, ch2 // 2), (zx + 10, ch2 // 2), (zx + 22, 0)]
    # fartlinjer bakom varje byst (chip-färg), som strålviften i cutin
    import math as _m
    _cen = ((-40 + 44 * 9 // 2, -1, chip_a), (img.width - 44 * 9 // 2 + 40, 1, chip_b))
    for cx, back, cc in _cen:
        col = tuple(min(255, c + 80) for c in cc[:3]) + (95,)
        cy = ch2 - 40 * 9 - 40 + 110
        for k in range(12):
            a = _m.pi + back * (k - 5.5) * 0.20
            x2 = cx + int(_m.cos(a) * 560); y2 = cy + int(_m.sin(a) * 420)
            d.line((cx, cy, x2, y2), fill=col, width=5)
    # glid-in från respektive kant (0.14 s ease)
    prog = min(1.0, max(0.0, t_since / 0.14))
    off = int((1.0 - (1 - prog) ** 2) * -460 + 460) if prog < 1.0 else 0
    bA = charA.get_bust_scaled("angry", "grit", 9)
    bB = charB.get_bust_scaled("angry" if active != "B" else "whiteout",
                               "grit" if active != "B" else "shout", 9)
    xA = -40 - off; xB = img.width - bB.width + 40 + off
    img.alpha_composite(bA, (xA, img.height - bA.height - 40))
    from PIL import ImageOps as _IO
    bB = _IO.mirror(bB)
    img.alpha_composite(bB, (xB, img.height - bB.height - 40))
    # blixt-skiljelinjen OVANPÅ bysterna (One Piece-stil)
    d = ImageDraw.Draw(img, "RGBA")
    d.polygon(pts, fill=(255, 255, 255, 235))
    d.polygon([(p[0] - 7, p[1]) for p in pts], fill=(255, 205, 90, 200))
    for nm, cc, xx in ((name_a, chip_a, 30), (name_b, chip_b, None)):
        lit = ptext(nm.upper(), scale=4, col=(255, 255, 255))
        bar = Image.new("RGBA", (lit.width + 24, lit.height + 12), tuple(cc[:3]) + (255,))
        bar.alpha_composite(lit, (12, 6))
        img.alpha_composite(bar, (xx if xx is not None else img.width - bar.width - 30, 26))
    return img
