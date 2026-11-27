"""Vidéo « Enquête » (enigmatik) : accroche immédiate, scène animée où l'inspecteur enquête,
interrogatoires, récapitulatif des indices — la solution n'est PAS donnée (réponse en commentaire)."""
import math, os, random, subprocess
import numpy as np
from PIL import Image, ImageDraw
from common import *
from common import _dummy
from enigme import wrap2, fit_font, CX0, CW, CX, SOFT2, DARK

ACC = (255, 214, 10)
RED = (240, 60, 60)
NIGHT_TOP, NIGHT_BOT = (8, 10, 24), (26, 18, 44)
SCN_W, SCN_H = 1300, 866
VIEW_Y, VIEW_W, VIEW_H = 290, 1080, 720
CHORDS = [[57, 60, 64], [53, 57, 60], [52, 55, 59], [52, 56, 59]]
WIN = (70, 90, 330, 400)
FRAME = (540, 100, 360, 280)
STEPS = [(1040, 790), (940, 740), (840, 800), (735, 750), (635, 805), (530, 755), (430, 810), (330, 760)]
FLASH_EVERY, FLASH_LEN = 4.6, 0.32
S = 2
WALK_V, STRIDE = 300.0, 95.0      # vitesse de marche (px/s sur la toile) et longueur d'un pas
CAMS = {"large": (0.5, 0.5, 1.0), "tableau": (0.55, 0.3, 1.45), "fenetre": (0.18, 0.35, 1.5)}
NARR = dict(speed=1.0, f=0.95)    # narrateur : un peu plus posé et plus grave
INSP = dict(speed=1.0, f=0.84)    # inspecteur : voix grave


def flash_amount(t, offset=0.6):
    if t < offset: return 0.0
    p = (t - offset) % FLASH_EVERY
    if p > FLASH_LEN: return 0.0
    return (1 - p / FLASH_LEN) * (0.6 + 0.4 * (p < 0.08 or 0.14 < p < 0.2))


def flash_times(dur, offset=0.6):
    out, t = [], offset
    while t < dur - 0.5: out.append(t); t += FLASH_EVERY
    return out


def voix(text, path, speed=1.0, f=1.0):
    """Voix IA + traitement : hauteur, chaleur (graves), léger effet de pièce. Retourne la durée."""
    tmp = path[:-4] + ".tmp.wav"; say(text, tmp, speed=speed)
    af = (f"asetrate={SR}*{f},aresample={SR},atempo={1/f:.4f},"
          "equalizer=f=170:t=q:w=1.1:g=3,equalizer=f=3200:t=q:w=1.5:g=1.5,equalizer=f=7500:t=q:w=1:g=-3,"
          "aecho=0.85:0.5:28|47:0.10|0.06")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-af", af, path], check=True)
    os.remove(tmp)
    return round(duration(path), 3)


def envelope(path, n_frames):
    x = load(path); per = SR / FPS; out = []
    for k in range(n_frames):
        seg = x[int(k * per): int((k + 1) * per)]
        out.append(float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0)
    m = max(out) or 1
    return [v / m for v in out]


# ---------------- personnages ----------------
SKIN = {"gardien": (240, 196, 160), "cuisiniere": (200, 140, 100), "jardinier": (150, 100, 70)}
BODY = {"gardien": (40, 60, 120), "cuisiniere": (245, 245, 245), "jardinier": (60, 130, 70)}


def eyes(d, s, cx, y, k, blink):
    if blink:
        d.line(s(cx - 26, y, cx - 10, y), fill=(30, 30, 30), width=int(4 * k)); d.line(s(cx + 10, y, cx + 26, y), fill=(30, 30, 30), width=int(4 * k))
    else:
        d.ellipse(s(cx - 24, y - 6, cx - 12, y + 6), fill=(30, 30, 30)); d.ellipse(s(cx + 12, y - 6, cx + 24, y + 6), fill=(30, 30, 30))


def mouth_draw(d, s, cx, y, k, mouth):
    if mouth > 0.15:
        mh = 6 + 16 * min(mouth, 1); d.ellipse(s(cx - 13, y - mh / 2, cx + 13, y + mh / 2), fill=(70, 20, 30))
    else:
        d.arc(s(cx - 20, y - 14, cx + 20, y + 14), 20, 160, fill=(30, 30, 30), width=int(4 * k))


def perso(kind, w, mouth=0.0, blink=False):
    k = w / 270 * S; h = int(330 * w / 270)
    im = Image.new("RGBA", (int(270 * k), int(330 * k)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    s = lambda *v: [x * k for x in v]; cx = 135
    d.rounded_rectangle(s(cx - 80, 170, cx + 80, 330), int(50 * k), fill=BODY[kind])
    if kind == "jardinier":
        d.rectangle(s(cx - 50, 175, cx - 36, 330), fill=(40, 90, 50)); d.rectangle(s(cx + 36, 175, cx + 50, 330), fill=(40, 90, 50))
    if kind == "gardien":
        d.polygon(s(cx + 30, 210, cx + 46, 214, cx + 46, 232, cx + 38, 240, cx + 30, 232), fill=ACC)
    if kind == "cuisiniere":
        d.polygon(s(cx - 30, 190, cx + 30, 190, cx, 230), fill=(220, 60, 60))
    d.ellipse(s(cx - 52, 60, cx + 52, 172), fill=SKIN[kind])
    eyes(d, s, cx, 111, k, blink)
    mouth_draw(d, s, cx, 134, k, mouth)
    if kind == "gardien":
        d.rounded_rectangle(s(cx - 56, 46, cx + 56, 92), int(14 * k), fill=(30, 40, 90)); d.rectangle(s(cx - 70, 84, cx + 70, 98), fill=(20, 28, 70))
        d.ellipse(s(cx - 12, 54, cx + 12, 78), fill=ACC)
    elif kind == "cuisiniere":
        for ox in (-34, 0, 34): d.ellipse(s(cx + ox - 34, 4, cx + ox + 34, 72), fill=(255, 255, 255))
        d.rectangle(s(cx - 52, 50, cx + 52, 90), fill=(255, 255, 255))
    else:
        d.ellipse(s(cx - 95, 66, cx + 95, 100), fill=(220, 190, 110)); d.rounded_rectangle(s(cx - 52, 20, cx + 52, 88), int(24 * k), fill=(230, 200, 120))
        d.rectangle(s(cx - 52, 66, cx + 52, 78), fill=(180, 60, 60))
    return im.resize((w, h), Image.LANCZOS)


def inspecteur(w=250, phase=0.0, walk=0.0, pose="debout", mouth=0.0, blink=False, flip=False):
    """Inspecteur articulé : jambes et bras qui balancent en marchant, loupe levée ou baissée."""
    k = w / 230 * S; im = Image.new("RGBA", (int(230 * k), int(430 * k)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    s = lambda *v: [x * k for x in v]; px = 115
    a = math.sin(phase) * 26 * walk
    coat, coat2, shoe = (196, 160, 100), (160, 126, 74), (50, 44, 40)
    for side, ang in ((-1, a), (1, -a)):
        hx, hy = px + side * 20, 300; L = 98
        fx_, fy_ = hx + L * math.sin(math.radians(ang)), hy + L * math.cos(math.radians(ang))
        d.line(s(hx, hy, fx_, fy_), fill=(60, 56, 70), width=int(26 * k))
        d.ellipse(s(fx_ - 22, fy_ - 10, fx_ + 26, fy_ + 12), fill=shoe)
    sway = math.sin(phase) * 5 * walk
    d.polygon(s(px - 68 + sway, 345, px - 54, 130, px + 54, 130, px + 68 + sway, 345), fill=coat)
    d.polygon(s(px - 6, 130, px + 6, 130, px + 3 + sway, 345, px - 3 + sway, 345), fill=coat2)
    d.polygon(s(px - 54, 130, px - 18, 130, px - 38, 205), fill=(176, 140, 84)); d.polygon(s(px + 54, 130, px + 18, 130, px + 38, 205), fill=(176, 140, 84))
    d.rectangle(s(px - 58, 238, px + 58, 252), fill=(120, 90, 50))
    ab = math.radians(-a * 0.9 + 4)
    sx, sy = px - 50, 145; hx2, hy2 = sx + 120 * math.sin(ab), sy + 120 * math.cos(ab)
    d.line(s(sx, sy, hx2, hy2), fill=coat, width=int(26 * k)); d.ellipse(s(hx2 - 13, hy2 - 13, hx2 + 13, hy2 + 13), fill=(240, 196, 160))
    sx, sy = px + 50, 145
    if pose == "loupe_haut": hand, lc = (px + 110, 120), (px + 140, 95)
    elif pose == "loupe_bas": hand, lc = (px + 100, 250), (px + 125, 285)
    else:
        ab2 = math.radians(a * 0.9 - 4); hand = (sx + 118 * math.sin(ab2), sy + 118 * math.cos(ab2)); lc = (hand[0] + 16, hand[1] + 36)
    d.line(s(sx, sy, *hand), fill=coat, width=int(26 * k))
    d.line(s(hand[0], hand[1], lc[0], lc[1]), fill=(80, 60, 40), width=int(10 * k))
    d.ellipse(s(lc[0] - 34, lc[1] - 34, lc[0] + 34, lc[1] + 34), outline=(225, 225, 235), width=int(8 * k), fill=(180, 220, 255, 90))
    d.ellipse(s(hand[0] - 13, hand[1] - 13, hand[0] + 13, hand[1] + 13), fill=(240, 196, 160))
    hy0 = 58
    d.ellipse(s(px - 38, hy0, px + 38, hy0 + 78), fill=(240, 196, 160))
    eyes(d, s, px, hy0 + 40, k * 0.9, blink)
    mouth_draw(d, s, px, hy0 + 60, k * 0.8, mouth)
    d.ellipse(s(px - 72, hy0, px + 72, hy0 + 24), fill=(60, 50, 44))
    d.rounded_rectangle(s(px - 44, hy0 - 42, px + 44, hy0 + 12), int(14 * k), fill=(70, 58, 50))
    d.rectangle(s(px - 44, hy0 - 6, px + 44, hy0 + 4), fill=(30, 26, 24))
    im = im.resize((w, int(430 * w / 230)), Image.LANCZOS)
    if pose == "loupe_bas": im = im.rotate(-6, resample=Image.BICUBIC, center=(w / 2, im.height))
    return im.transpose(Image.FLIP_LEFT_RIGHT) if flip else im


# ---------------- décor ----------------
def decor_static():
    im = Image.new("RGBA", (SCN_W * S, SCN_H * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im); s = lambda *v: [x * S for x in v]
    fy = 640
    d.rectangle(s(0, 0, SCN_W, fy), fill=(46, 52, 78))
    for x in range(0, SCN_W, 80): d.rectangle(s(x, 0, x + 40, fy), fill=(51, 58, 86))
    d.rectangle(s(0, fy, SCN_W, SCN_H), fill=(92, 60, 44))
    for x in range(-300, SCN_W + 300, 120): d.line(s(x, fy, x - 140, SCN_H), fill=(80, 52, 38), width=4 * S)
    d.rectangle(s(0, fy - 22, SCN_W, fy + 6), fill=(30, 33, 50))
    wx, wy, ww, wh = WIN
    d.rectangle(s(wx - 16, wy - 16, wx + ww + 16, wy + wh + 16), fill=(120, 84, 60))
    d.rectangle(s(wx, wy, wx + ww, wy + wh), fill=(18, 26, 52))
    d.rectangle(s(wx - 26, wy + wh + 10, wx + ww + 26, wy + wh + 28), fill=(140, 100, 72))
    fx, fy2, fw, fh = FRAME
    d.rectangle(s(fx - 24, fy2 - 24, fx + fw + 24, fy2 + fh + 24), fill=(212, 170, 60))
    d.rectangle(s(fx - 11, fy2 - 11, fx + fw + 11, fy2 + fh + 11), fill=(168, 128, 40))
    d.rectangle(s(fx, fy2, fx + fw, fy2 + fh), fill=(36, 40, 60))
    for x in (500, 940):
        d.rectangle(s(x - 8, 470, x + 8, 660), fill=(200, 170, 70)); d.ellipse(s(x - 18, 450, x + 18, 486), fill=(220, 190, 80))
        d.ellipse(s(x - 30, 650, x + 30, 672), fill=(160, 130, 50))
    d.line(s(500, 480, 940, 480), fill=ACC, width=12 * S)
    for x in range(500, 940, 64): d.line(s(x, 480, x + 32, 480), fill=(20, 20, 20), width=12 * S)
    d.rectangle(s(1080, 560, 1240, 580), fill=(110, 74, 50)); d.rectangle(s(1100, 580, 1116, 650), fill=(90, 60, 40)); d.rectangle(s(1204, 580, 1220, 650), fill=(90, 60, 40))
    d.polygon(s(1130, 470, 1190, 470, 1210, 530, 1110, 530), fill=(230, 200, 120)); d.rectangle(s(1154, 530, 1166, 560), fill=(60, 50, 40))
    st = im.resize((SCN_W, SCN_H), Image.LANCZOS)
    bars = Image.new("RGBA", (SCN_W, SCN_H), (0, 0, 0, 0)); bd = ImageDraw.Draw(bars)
    bd.rectangle([wx + ww / 2 - 6, wy, wx + ww / 2 + 6, wy + wh], fill=(120, 84, 60))
    bd.rectangle([wx, wy + wh / 2 - 6, wx + ww, wy + wh / 2 + 6], fill=(120, 84, 60))
    for (x1, y1, x2, y2) in [(wx + 250, wy + 300, wx + 300, wy + 260), (wx + 250, wy + 300, wx + 215, wy + 350), (wx + 250, wy + 300, wx + 300, wy + 345), (wx + 250, wy + 300, wx + 205, wy + 270)]:
        bd.line([x1, y1, x2, y2], fill=(210, 225, 255, 230), width=3)
    return st, bars


def icon(kind, size=110):
    k = size / 100 * S; im = Image.new("RGBA", (int(100 * k), int(100 * k)), (0, 0, 0, 0)); d = ImageDraw.Draw(im); s = lambda *v: [x * k for x in v]
    if kind == "orage":
        d.ellipse(s(10, 14, 60, 50), fill=(170, 180, 210)); d.ellipse(s(38, 6, 90, 50), fill=(190, 200, 225)); d.rectangle(s(24, 32, 80, 50), fill=(180, 190, 215))
        d.polygon(s(52, 48, 34, 76, 50, 76, 40, 98, 70, 66, 54, 66, 64, 48), fill=ACC)
    elif kind == "boue":
        for ox, oy in ((14, 52), (52, 14)):
            d.ellipse(s(ox, oy, ox + 30, oy + 40), fill=(140, 92, 60)); d.ellipse(s(ox + 4, oy + 40, ox + 26, oy + 54), fill=(140, 92, 60))
    elif kind == "fenetre":
        d.rectangle(s(10, 8, 90, 92), fill=(140, 100, 72)); d.rectangle(s(18, 16, 82, 84), fill=(40, 60, 110))
        for x1, y1, x2, y2 in [(60, 58, 80, 40), (60, 58, 44, 80), (60, 58, 82, 76), (60, 58, 36, 46)]: d.line(s(x1, y1, x2, y2), fill=(230, 240, 255), width=int(3 * k))
    return im.resize((size, size), Image.LANCZOS)


class Enquete:
    def __init__(self, c, work):
        self.c, self.work = c, work
        self.sus = c["suspects"]; assert len(self.sus) == 3
        self.static, self.bars = decor_static()
        top, bot = np.array(NIGHT_TOP), np.array(NIGHT_BOT)
        y = np.linspace(0, 1, H)[:, None, None]
        self.BG = Image.fromarray(np.repeat(top * (1 - y) + bot * y, W, axis=1).astype(np.uint8), "RGB").convert("RGBA")
        fade = np.zeros((VIEW_H, 1), np.float32); fade[-160:, 0] = np.linspace(0, 1, 160) ** 1.5; fade[:40, 0] = np.linspace(1, 0, 40) * 0.8
        self.FADE = Image.fromarray(np.dstack([np.full((VIEW_H, W, 3), (12, 12, 28), np.uint8), np.repeat((fade * 255).astype(np.uint8), W, axis=1)]), "RGBA")
        self.rnd = [(random.Random(i).uniform(0, 1), random.Random(i * 7 + 1).uniform(0, 1), random.Random(i * 13 + 2).uniform(0.8, 1.3)) for i in range(70)]

    # ---------- voix ----------
    def voices(self):
        c = self.c; w = self.work; D = {}
        D["hook"] = voix(c["accroche"], f"{w}/hook.wav", **NARR)
        for i, txt in enumerate(c["recit"]): D[f"r{i}"] = voix(txt, f"{w}/r{i}.wav", **NARR)
        for i, s in enumerate(self.sus):
            D[f"q{i}"] = voix(s["question"], f"{w}/q{i}.wav", **INSP)
            D[f"s{i}"] = voix(s["dit"], f"{w}/s{i}.wav", speed=1.03, f=s.get("voix", 1.0))
        D["recap0"] = voix("Récapitulons.", f"{w}/recap0.wav", **NARR)
        for i, r in enumerate(c["recap"]): D[f"recap{i+1}"] = voix(r["voix"], f"{w}/recap{i+1}.wav", **NARR)
        D["fin"] = voix(c["fin"], f"{w}/fin.wav", **NARR)
        self.DUR = D
        self.ENV = {k: envelope(f"{w}/{k}.wav", int(D[k] * FPS) + 2) for k in [f"q{i}" for i in range(3)] + [f"s{i}" for i in range(3)]}

    def recit_plan(self):
        t, out = 0.3, []
        for i in range(len(self.c["recit"])): out.append(t); t += self.DUR[f"r{i}"] + 0.45
        return out, t + 0.4

    def sus_plan(self, i):
        tq = 0.45; ts = tq + self.DUR[f"q{i}"] + 0.35
        return tq, ts, ts + self.DUR[f"s{i}"] + 0.8

    def recap_plan(self):
        t, out = 0.3, []
        for i in range(len(self.c["recap"]) + 1): out.append(t); t += self.DUR[f"recap{i}"] + 0.35
        return out, t + 0.6

    def timeline(self):
        r = lambda x: round(x * FPS) / FPS; D = self.DUR
        tl = [("hook", r(0.05 + D["hook"] + 0.45)), ("recit", r(self.recit_plan()[1]))]
        for i in range(3): tl.append((f"sus{i}", r(self.sus_plan(i)[2])))
        tl.append(("recap", r(self.recap_plan()[1])))
        tl.append(("fin", r(0.3 + D["fin"] + 2.2)))
        return tl

    # ---------- déplacements de l'inspecteur ----------
    def insp_moves(self):
        st, _ = self.recit_plan()
        return [(st[int(k)] + 0.2, float(x), pose) for k, (x, pose) in sorted(self.c["inspecteur"].items(), key=lambda kv: int(kv[0]))]

    def insp_state(self, t):
        """Position, phase de marche, pose et sens de l'inspecteur à l'instant t du récit (None = pas encore entré)."""
        mv = self.insp_moves()
        if not mv or t < mv[0][0]: return None
        x, pose, flip, dist = SCN_W + 160.0, "debout", True, 0.0
        for j, (ts, tx, p) in enumerate(mv):
            if t < ts: break
            t_end = mv[j + 1][0] if j + 1 < len(mv) else 1e9
            dur = abs(tx - x) / WALK_V; now = min(t, t_end)
            if now < ts + dur:                                   # en train de marcher
                fl = tx < x; nx = x + (tx - x) * (now - ts) / max(dur, 1e-6)
                if t < t_end: return dict(x=nx, walk=1.0, phase=(dist + (now - ts) * WALK_V) / STRIDE * math.pi, pose="debout", flip=fl)
                dist += abs(nx - x); x, flip, pose = nx, fl, "debout"
            else:
                if tx != x: flip = tx < x
                dist += abs(tx - x); x, pose = tx, p
        return dict(x=x, walk=0.0, phase=0.0, pose=pose, flip=flip)

    def footstep_times(self, dur):
        out, t, last = [], 0.0, None
        while t < dur:
            s = self.insp_state(t)
            if s and s["walk"] > 0:
                k = int(s["phase"] / math.pi)
                if last is not None and k != last: out.append(t)
                last = k
            else: last = None
            t += 1 / FPS
        return out

    # ---------- scène ----------
    def scene(self, t, cam=(0.5, 0.5, 1.0), steps=0.0, ring=None, insp=None, flash_off=0.6, storm=True):
        im = self.static.copy(); d = ImageDraw.Draw(im)
        fl = flash_amount(t, flash_off) if storm else 0
        wx, wy, ww, wh = WIN
        if fl > 0:
            d.rectangle([wx, wy, wx + ww, wy + wh], fill=(120, 140, 200, int(150 * fl)))
            bx = wx + ww * 0.6
            d.polygon([(bx, wy + 10), (bx - 50, wy + 170), (bx - 6, wy + 170), (bx - 62, wy + 340), (bx + 48, wy + 130), (bx, wy + 130), (bx + 42, wy + 10)], fill=(255, 245, 180, int(255 * min(1, fl * 1.5))))
        for (a, b, sp) in self.rnd:
            x = wx + a * ww; y = wy + ((b * wh + t * 900 * sp) % wh); y2 = min(wy + wh, y + 30)
            d.line([(x, y), (x - 9, y2)], fill=(150, 180, 230, 200), width=3)
        im.alpha_composite(self.bars)
        fx, fy, fw, fh = FRAME
        q = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
        ImageDraw.Draw(q).text((fw / 2, fh / 2), "?", font=font(190, "Black"), fill=(255, 255, 255, int(55 + 35 * math.sin(t * 3))), anchor="mm")
        im.alpha_composite(q, (fx, fy))
        n = len(STEPS); dd = ImageDraw.Draw(im)
        for k, (x, y) in enumerate(STEPS):
            p = steps * n - k
            if p <= 0: continue
            a = int(255 * min(1, p))
            dd.ellipse([x, y, x + 62, y + 32], fill=(48, 30, 18, a)); dd.ellipse([x + 56, y + 4, x + 78, y + 28], fill=(48, 30, 18, a))
        if ring:
            (rx, ry, rr), p = ring
            if p > 0:
                rr2 = rr * (1.4 - 0.4 * ease_out(min(p * 2.5, 1))) * (1 + 0.04 * math.sin(t * 8))
                d.ellipse([rx - rr2, ry - rr2 * 0.75, rx + rr2, ry + rr2 * 0.75], outline=ACC + (int(255 * min(1, p * 3)),), width=9)
        if insp:
            spr = inspecteur(260, insp["phase"], insp["walk"], insp["pose"], blink=(t % 3.3) < 0.12, flip=insp["flip"])
            bob = abs(math.sin(insp["phase"])) * 9 * insp["walk"]
            im.alpha_composite(spr, (int(insp["x"] - spr.width / 2), int(SCN_H - spr.height - 4 - bob)))
        if fl > 0: im.alpha_composite(Image.new("RGBA", im.size, (220, 230, 255, int(70 * fl))))
        cx, cy, z = cam; cw, ch = SCN_W / z, SCN_H / z
        x0 = min(max(cx * SCN_W - cw / 2, 0), SCN_W - cw); y0 = min(max(cy * SCN_H - ch / 2, 0), SCN_H - ch)
        return im.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((VIEW_W, VIEW_H), Image.BILINEAR)

    def put_scene(self, frame, view, dim=0.0):
        if dim: view = Image.blend(view, Image.new("RGBA", view.size, (10, 10, 24, 255)), dim)
        frame.alpha_composite(view, (0, VIEW_Y)); frame.alpha_composite(self.FADE, (0, VIEW_Y))

    def header(self, im, right=None):
        d = ImageDraw.Draw(im)
        d.text((CX0, 215), "ENQUÊTE", font=font(46, "Black"), fill=ACC, anchor="lm")
        txt = right or self.c["titre"]; fo = fit_font(txt, 520, 36, "Bold")
        d.text((CX0 + CW, 217), txt, font=fo, fill=SOFT2, anchor="rm")

    def subtitle(self, im, text, p, y=1110):
        if p <= 0: return
        lines = wrap2(text, font(54, "Black"), CW)
        lay = Image.new("RGBA", (W, 90 * len(lines) + 40), (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
        for k, ln in enumerate(lines):
            dl.text((CX, 45 + k * 70), ln, font=font(54, "Black"), fill=WHITE, anchor="mm", stroke_width=6, stroke_fill=(8, 8, 18))
        paste(im, lay, 0, y + (1 - ease_out(p)) * 25, alpha=min(1, p * 1.6))

    def tapes(self, im, t):
        for k, (y, ang, sp) in enumerate([(700, -9, 1), (860, 7, -1)]):
            tape = Image.new("RGBA", (2600, 96), ACC + (255,)); td = ImageDraw.Draw(tape)
            lab = "ENQUÊTE  •  NE PAS FRANCHIR  •  "; step = int(_dummy.textlength(lab, font=font(44, "Black")))
            off = (t * 260 * sp) % step
            for x in range(-step, 2600 + step, step): td.text((x + off, 48), lab, font=font(44, "Black"), fill=(20, 20, 20), anchor="lm")
            tape = tape.rotate(ang, expand=True, resample=Image.BICUBIC)
            im.alpha_composite(tape, (int(W / 2 - tape.width / 2), int(y - tape.height / 2)))

    # ---------- 1. accroche (dès la 1re image) ----------
    def draw_hook(self, t):
        im = self.BG.copy(); self.put_scene(im, self.scene(t, flash_off=0.25), dim=0.35); self.header(im)
        self.tapes(im, t)
        lines = wrap2(self.c["accroche"].upper(), font(78, "Black"), CW)
        lay = Image.new("RGBA", (W, 100 * len(lines) + 40), (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
        for k, ln in enumerate(lines):
            dl.text((CX, 60 + k * 96), ln, font=fit_font(ln, CW, 78), fill=ACC if k == len(lines) - 1 else WHITE, anchor="mm", stroke_width=8, stroke_fill=(8, 8, 18))
        paste(im, lay, 0, 1020, scale=1.12 - 0.12 * ease_out(t / 0.35) + 0.015 * math.sin(t * 6))
        return im

    # ---------- 2. récit animé ----------
    def recit_cam(self, t, st, ins):
        plans = self.c["plans"]
        def target(i):
            m = plans[i]
            if m == "suivre": return (min(max(ins["x"] / SCN_W, 0.3), 0.75), 1.0, 1.15) if ins else CAMS["large"]
            return CAMS[m]
        i = max([j for j, s in enumerate(st) if t >= s - 0.05] or [0])
        cur = target(i)
        if i == 0: cam = cur
        else:
            prev = target(i - 1); p = ease_out((t - st[i]) / 1.0)
            cam = tuple(a + (b - a) * p for a, b in zip(prev, cur))
        return (cam[0], cam[1], cam[2] * (1 + 0.01 * t)), i

    def draw_recit(self, t):
        im = self.BG.copy(); self.header(im)
        st, _ = self.recit_plan(); ev = self.c.get("evenements", {})
        since = lambda n: (t - st[ev[n]]) if n in ev else -1
        ins = self.insp_state(t)
        cam, i = self.recit_cam(t, st, ins)
        steps = min(1, since("traces") / 1.6) if since("traces") >= 0 else 0
        ring = None
        if i == ev.get("tableau"): ring = ((FRAME[0] + FRAME[2] / 2, FRAME[1] + FRAME[3] / 2, 250), since("tableau") - 0.5)
        if i == ev.get("traces"): ring = ((700, 790, 240), since("traces") - 1.8)
        if i == ev.get("fenetre"): ring = ((WIN[0] + WIN[2] / 2, WIN[1] + WIN[3] / 2, 240), since("fenetre") - 1.0)
        self.put_scene(im, self.scene(t + 2.0, cam, steps, ring, ins))
        self.subtitle(im, self.c["recit"][i], (t - st[i]) / 0.3)
        return im

    # ---------- 3. interrogatoires ----------
    def bubble(self, im, text, prog, y, tail_x):
        txt = "« " + text + " »"; nshow = int(len(txt) * prog)
        fo = font(46, "Bold"); lines = wrap2(txt, fo, CW - 90); bh = int(58 * len(lines) + 70)
        bub, bp = rr_image(CW, bh, 34, WHITE, shadow=True); bd = ImageDraw.Draw(bub)
        tx = bp + tail_x - CX0
        bd.polygon([(tx - 30, bp + 2), (tx + 30, bp + 2), (tx, bp - 34)], fill=WHITE)
        shown = 0
        for k, ln in enumerate(lines):
            part = ln[: max(0, nshow - shown)]; shown += len(ln) + 1
            bd.text((bp + 45, bp + 35 + k * 58), part, font=fo, fill=DARK, anchor="lt")
        im.alpha_composite(bub, (CX0 - bp, y - bp))

    def draw_sus(self, i, t):
        s = self.sus[i]; D = self.DUR; tq, ts, _ = self.sus_plan(i)
        im = self.BG.copy(); self.header(im, f"SUSPECT {i + 1}/3")
        self.put_scene(im, self.scene(t + 7 * i, (0.5, 0.5, 1.0), 1, None, None, storm=False), dim=0.6)
        def env_at(key, t0):
            fi = int((t - t0) * FPS); e = self.ENV[key]; return e[fi] if 0 <= fi < len(e) else 0
        p = ease_out(t / 0.45)
        ins = inspecteur(300, pose="debout", mouth=env_at(f"q{i}", tq) * 1.3, blink=(t % 3.4) < 0.12)
        paste(im, ins, 20 - (1 - p) * 400, 1160 - ins.height + math.sin(t * 2) * 4)
        p2 = ease_back((t - 0.15) / 0.5)
        spr = perso(s["perso"], 420, mouth=env_at(f"s{i}", ts) * 1.3, blink=((t + 1.1) % 2.9) < 0.12)
        paste(im, spr, 480 + (1 - min(max(p2, 0), 1)) * 600, 1160 - spr.height + math.sin(t * 2.3 + 1) * 5)
        tag, tp = rr_image(int(_dummy.textlength(s["nom"], font=font(46, "Black")) + 70), 82, 41, ACC, shadow=True)
        ImageDraw.Draw(tag).text((tag.width / 2, tp + 43), s["nom"], font=font(46, "Black"), fill=DARK, anchor="mm")
        paste(im, tag, 690 - tag.width / 2, 1145 - tp, alpha=min(1, t * 3))
        if tq - 0.05 <= t < ts - 0.1:
            self.bubble(im, s["question"], min(1, (t - tq) / max(0.4, D[f"q{i}"] * 0.9)), 1265, 190)
        elif t >= ts - 0.1:
            self.bubble(im, s["dit"], min(1, (t - ts) / max(0.5, D[f"s{i}"] * 0.92)), 1265, 690)
        return im

    # ---------- 4. récapitulatif des indices ----------
    def draw_recap(self, t):
        im = self.BG.copy(); self.header(im, "LES INDICES"); d = ImageDraw.Draw(im)
        st, _ = self.recap_plan()
        big = Image.new("RGBA", (1000, 140), (0, 0, 0, 0)); ImageDraw.Draw(big).text((500, 70), "RÉCAPITULONS", font=font(92, "Black"), fill=ACC, anchor="mm")
        paste(im, big, CX - 500, 300, scale=max(0.05, 0.7 + 0.3 * ease_back(t / 0.4)))
        for k, r in enumerate(self.c["recap"]):
            ts = st[k + 1]
            if t < ts - 0.1: continue
            p = ease_out((t - ts + 0.1) / 0.4)
            card, cp = rr_image(CW, 190, 34, (30, 32, 56), border=ACC, bw=4, shadow=True)
            card.alpha_composite(icon(r["icone"], 130), (cp + 30, cp + 30))
            fo = font(50, "Black"); lines = wrap2(r["texte"], fo, CW - 230)
            for j, ln in enumerate(lines): ImageDraw.Draw(card).text((cp + 195, cp + 95 + (j - (len(lines) - 1) / 2) * 60), ln, font=fo, fill=WHITE, anchor="lm")
            paste(im, card, CX0 - cp + (1 - p) * 500, 470 + k * 225 - cp, alpha=min(1, p * 1.5))
        if t > st[-1] + 1.0:
            d.text((CX, 1190), "Un seul suspect ment…", font=font(54, "Black"), fill=WHITE, anchor="mm")
        return im

    # ---------- 5. qui ment ? → réponse en commentaire ----------
    def cards(self, im, t):
        cw = CW // 3 - 12
        for k, s in enumerate(self.sus):
            x0 = CX0 + k * (cw + 18); y0 = 470
            c, cp = rr_image(cw, 470, 30, (30, 32, 56), border=(70, 74, 110), bw=3, shadow=True); dc = ImageDraw.Draw(c)
            spr = perso(s["perso"], 220, blink=((t + k * 0.9) % 3.1) < 0.12); c.alpha_composite(spr, (cp + cw // 2 - 110, cp + 18))
            dc.text((cp + cw / 2, cp + 315), s["nom"], font=fit_font(s["nom"], cw - 20, 34), fill=ACC, anchor="mm")
            for j, ln in enumerate(wrap2(s["court"], font(28, "SemiBold"), cw - 30)):
                dc.text((cp + cw / 2, cp + 365 + j * 36), ln, font=font(28, "SemiBold"), fill=SOFT2, anchor="mm")
            ent = ease_out((t - 0.12 * k) / 0.4)
            paste(im, c, x0 - cp, y0 - cp + (1 - ent) * 120, alpha=min(1, ent * 1.5), scale=1 + 0.03 * math.sin(t * 3 + k * 2))

    def draw_fin(self, t):
        im = self.BG.copy(); self.header(im); d = ImageDraw.Draw(im)
        big = Image.new("RGBA", (1000, 140), (0, 0, 0, 0)); ImageDraw.Draw(big).text((500, 70), "QUI MENT ?", font=font(110, "Black"), fill=ACC, anchor="mm")
        paste(im, big, CX - 500, 300, scale=max(0.05, 0.6 + 0.4 * ease_back(t / 0.4)) * (1 + 0.03 * math.sin(t * 5)))
        self.cards(im, t)
        if t > 0.8:
            lp = ease_back((t - 0.8) / 0.4)
            pill, pp = rr_image(860, 120, 60, WHITE, shadow=True); pd = ImageDraw.Draw(pill)
            pd.rounded_rectangle([pp + 34, pp + 30, pp + 104, pp + 82], 14, fill=(255, 44, 85)); pd.polygon([(pp + 50, pp + 80), (pp + 66, pp + 80), (pp + 48, pp + 98)], fill=(255, 44, 85))
            for j in range(3): pd.ellipse([pp + 50 + j * 18, pp + 51, pp + 60 + j * 18, pp + 61], fill=WHITE)
            pd.text((pp + 490, pp + 62), "Ta réponse en commentaire !", font=font(44, "Black"), fill=DARK, anchor="mm")
            paste(im, pill, CX - 430 - pp, 1010 - pp, scale=max(0.05, 0.8 + 0.2 * min(lp, 1.2)) * (1 + 0.03 * math.sin(t * 6)))
        if t > 1.6:
            lp = (t - 1.6) / 0.35
            btn, bp = cta_button("+ ABONNE-TOI", 640, 120, 56)
            paste(im, btn, CX - 320 - bp, 1170 - bp, alpha=min(1, lp * 2), scale=max(0.05, 0.8 + 0.2 * ease_back(lp)))
            d.text((CX, 1345), "Une nouvelle enquête bientôt", font=font(42, "SemiBold"), fill=SOFT2, anchor="mm")
        return im

    def frame_fn(self, name):
        if name.startswith("sus"):
            i = int(name[3:]); return lambda t: self.draw_sus(i, t)
        return getattr(self, f"draw_{name}")

    def check_frames(self):
        st, _ = self.recit_plan()
        out = [("hook", 0.0), ("hook", 1.5)] + [("recit", s + 1.6) for s in st]
        for i in range(3):
            tq, ts, _ = self.sus_plan(i); out += [(f"sus{i}", tq + 0.8), (f"sus{i}", ts + self.DUR[f"s{i}"] * 0.8)]
        rs, _ = self.recap_plan()
        out += [("recap", rs[-1] + 1.2), ("fin", 2.5)]
        return out

    # ---------- audio ----------
    def audio(self, tl, wav):
        total = sum(d for _, d in tl); tr = Track(total); t0 = 0.0; w = self.work
        rng = np.random.default_rng(1)
        def colored(n, lo, hi):
            x = np.fft.rfft(rng.standard_normal(n)); f = np.fft.rfftfreq(n, 1 / SR)
            x *= ((f > lo) & (f < hi)) / np.maximum(f, 20) ** 0.5
            y = np.fft.irfft(x, n); return y / np.abs(y).max()
        tt = np.arange(int(2.2 * SR)) / SR
        THUNDER = colored(len(tt), 20, 260) * np.minimum(tt / 0.06, 1) * np.exp(-tt / 0.7)
        THUNDER[: int(0.25 * SR)] += colored(int(0.25 * SR), 400, 5000) * np.exp(-tt[: int(0.25 * SR)] / 0.05) * 0.5
        n = int(0.09 * SR); STEP = colored(n, 60, 900) * np.exp(-np.arange(n) / SR / 0.025)
        for name, dur in tl:
            if name not in ("hook", "recit"): tr.add(tr.sfx, WHOOSH, t0, 0.2)
            if name == "hook": tr.add(tr.voice, load(f"{w}/hook.wav"), t0 + 0.05)
            elif name == "recit":
                st, _ = self.recit_plan()
                for i, s in enumerate(st): tr.add(tr.voice, load(f"{w}/r{i}.wav"), t0 + s)
                for k, ft in enumerate(self.footstep_times(dur)): tr.add(tr.sfx, STEP, t0 + ft, 0.32 if k % 2 else 0.26)
            elif name.startswith("sus"):
                i = int(name[3:]); tq, ts, _ = self.sus_plan(i)
                tr.add(tr.voice, load(f"{w}/q{i}.wav"), t0 + tq); tr.add(tr.voice, load(f"{w}/s{i}.wav"), t0 + ts)
            elif name == "recap":
                st, _ = self.recap_plan()
                for i, s in enumerate(st):
                    tr.add(tr.voice, load(f"{w}/recap{i}.wav"), t0 + s)
                    if i: tr.add(tr.sfx, POP, t0 + s - 0.05, 0.35)
            elif name == "fin":
                tr.add(tr.voice, load(f"{w}/fin.wav"), t0 + 0.3); tr.add(tr.sfx, POP, t0 + 0.8, 0.3)
            if name in ("hook", "recit"):
                off, shift = (0.25, 0.0) if name == "hook" else (0.6, 2.0)
                for ft in flash_times(dur + shift, off):
                    if ft - shift >= 0: tr.add(tr.sfx, THUNDER, t0 + ft - shift + 0.15, 0.5)
            t0 += dur
        tr.sfx += colored(tr.N, 800, 9000) * 0.035
        mixdown(tr, wav, music_gain=0.4, soft=True, chords=CHORDS, bpm=78)
