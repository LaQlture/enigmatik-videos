"""Vidéo « Enquête » (enigmatik) : une scène animée, des suspects qui parlent, un menteur à trouver."""
import math, os, random, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from common import *
from common import _dummy
from enigme import wrap2, fit_font, CX0, CW, CX, SOFT2, DARK

ACC = (255, 214, 10)              # jaune « ruban de police »
RED = (240, 60, 60)
NIGHT_TOP, NIGHT_BOT = (8, 10, 24), (26, 18, 44)
SCN_W, SCN_H = 1300, 866          # toile de la scène (recadrée par la « caméra »)
VIEW_Y, VIEW_W, VIEW_H = 290, 1080, 720
CHORDS = [[57, 60, 64], [53, 57, 60], [52, 55, 59], [52, 56, 59]]
WIN = (70, 90, 330, 400)          # fenêtre : x, y, l, h
FRAME = (540, 100, 360, 280)      # tableau volé
STEPS = [(1040, 790), (940, 740), (840, 800), (735, 750), (635, 805), (530, 755), (430, 810), (330, 760)]
FLASH_EVERY, FLASH_LEN = 4.6, 0.32
S = 2                             # sur-échantillonnage des dessins


def flash_amount(t, offset=0.6):
    """Intensité d'un éclair à l'instant t (0 = rien)."""
    if t < offset: return 0.0
    p = (t - offset) % FLASH_EVERY
    if p > FLASH_LEN: return 0.0
    return (1 - p / FLASH_LEN) * (0.6 + 0.4 * (p < 0.08 or 0.14 < p < 0.2))


def flash_times(dur, offset=0.6):
    out, t = [], offset
    while t < dur - 0.5: out.append(t); t += FLASH_EVERY
    return out


def pitch(src, dst, f):
    """Change la hauteur de la voix (f < 1 : plus grave) sans changer sa vitesse."""
    if abs(f - 1) < 1e-3: os.replace(src, dst); return
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-af", f"asetrate={SR}*{f},aresample={SR},atempo={1/f:.4f}", dst], check=True)
    os.remove(src)


def envelope(path, n_frames):
    """Volume de la voix image par image (pour animer la bouche)."""
    x = load(path); per = SR / FPS; out = []
    for k in range(n_frames):
        seg = x[int(k * per): int((k + 1) * per)]
        out.append(float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0)
    m = max(out) or 1
    return [v / m for v in out]


# ---------------- personnages ----------------
SKIN = {"gardien": (240, 196, 160), "cuisiniere": (200, 140, 100), "jardinier": (150, 100, 70)}
BODY = {"gardien": (40, 60, 120), "cuisiniere": (245, 245, 245), "jardinier": (60, 130, 70)}


def perso(kind, w, mouth=0.0, blink=False):
    """Personnage plat ; mouth = ouverture de la bouche (0..1), blink = yeux fermés."""
    k = w / 270 * S; h = int(330 * w / 270)
    im = Image.new("RGBA", (int(270 * k), int(330 * k)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    s = lambda *v: [x * k for x in v]; cx = 135
    d.rounded_rectangle(s(cx - 80, 170, cx + 80, 330), int(50 * k), fill=BODY[kind])
    if kind == "jardinier":                      # bretelles de salopette
        d.rectangle(s(cx - 50, 175, cx - 36, 330), fill=(40, 90, 50)); d.rectangle(s(cx + 36, 175, cx + 50, 330), fill=(40, 90, 50))
    if kind == "gardien":                        # badge
        d.polygon(s(cx + 30, 210, cx + 46, 214, cx + 46, 232, cx + 38, 240, cx + 30, 232), fill=ACC)
    if kind == "cuisiniere":
        d.polygon(s(cx - 30, 190, cx + 30, 190, cx, 230), fill=(220, 60, 60))
    d.ellipse(s(cx - 52, 60, cx + 52, 172), fill=SKIN[kind])
    if blink:
        d.line(s(cx - 26, 112, cx - 10, 112), fill=(30, 30, 30), width=int(4 * k)); d.line(s(cx + 10, 112, cx + 26, 112), fill=(30, 30, 30), width=int(4 * k))
    else:
        d.ellipse(s(cx - 24, 105, cx - 12, 117), fill=(30, 30, 30)); d.ellipse(s(cx + 12, 105, cx + 24, 117), fill=(30, 30, 30))
    if mouth > 0.15:
        mh = 6 + 16 * min(mouth, 1)
        d.ellipse(s(cx - 13, 134 - mh / 2, cx + 13, 134 + mh / 2), fill=(70, 20, 30))
    else:
        d.arc(s(cx - 20, 120, cx + 20, 148), 20, 160, fill=(30, 30, 30), width=int(4 * k))
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


def inspecteur(w=230):
    k = w / 230 * S; im = Image.new("RGBA", (int(230 * k), int(420 * k)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    s = lambda *v: [x * k for x in v]; px, py = 120, 40
    d.polygon(s(px - 70, py + 340, px - 55, py + 90, px + 55, py + 90, px + 70, py + 340), fill=(196, 160, 100))
    d.polygon(s(px - 8, py + 90, px + 8, py + 90, px + 4, py + 340, px - 4, py + 340), fill=(160, 126, 74))
    d.polygon(s(px - 55, py + 90, px - 20, py + 90, px - 40, py + 170), fill=(176, 140, 84))
    d.polygon(s(px + 55, py + 90, px + 20, py + 90, px + 40, py + 170), fill=(176, 140, 84))
    d.rectangle(s(px - 60, py + 205, px + 60, py + 220), fill=(120, 90, 50))
    d.rectangle(s(px - 40, py + 340, px - 12, py + 375), fill=(50, 44, 40)); d.rectangle(s(px + 12, py + 340, px + 40, py + 375), fill=(50, 44, 40))
    d.ellipse(s(px - 38, py + 18, px + 38, py + 96), fill=(240, 196, 160))
    d.ellipse(s(px - 72, py + 20, px + 72, py + 44), fill=(60, 50, 44))
    d.rounded_rectangle(s(px - 44, py - 22, px + 44, py + 32), int(14 * k), fill=(70, 58, 50))
    d.rectangle(s(px - 44, py + 14, px + 44, py + 24), fill=(30, 26, 24))
    d.ellipse(s(px - 18, py + 52, px - 8, py + 62), fill=(30, 30, 30)); d.ellipse(s(px + 8, py + 52, px + 18, py + 62), fill=(30, 30, 30))
    d.line(s(px - 14, py + 78, px + 14, py + 78), fill=(120, 70, 60), width=int(3 * k))
    # bras + loupe
    d.line(s(px - 50, py + 120, px - 80, py + 210), fill=(176, 140, 84), width=int(26 * k))
    d.line(s(px - 80, py + 210, px - 100, py + 250), fill=(80, 60, 40), width=int(12 * k))
    d.ellipse(s(px - 150, py + 225, px - 76, py + 299), outline=(225, 225, 235), width=int(9 * k), fill=(180, 220, 255, 90))
    return im.resize((w, int(420 * w / 230)), Image.LANCZOS)


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
    d.rectangle(s(wx - 26, wy + wh + 10, wx + ww + 26, wy + wh + 28), fill=(140, 100, 72))      # rebord
    fx, fy2, fw, fh = FRAME
    d.rectangle(s(fx - 24, fy2 - 24, fx + fw + 24, fy2 + fh + 24), fill=(212, 170, 60))
    d.rectangle(s(fx - 11, fy2 - 11, fx + fw + 11, fy2 + fh + 11), fill=(168, 128, 40))
    d.rectangle(s(fx, fy2, fx + fw, fy2 + fh), fill=(36, 40, 60))
    # cordon de sécurité sur poteaux
    for x in (500, 940):
        d.rectangle(s(x - 8, 470, x + 8, 660), fill=(200, 170, 70)); d.ellipse(s(x - 18, 450, x + 18, 486), fill=(220, 190, 80))
        d.ellipse(s(x - 30, 650, x + 30, 672), fill=(160, 130, 50))
    d.line(s(500, 480, 940, 480), fill=ACC, width=12 * S)
    for x in range(500, 940, 64): d.line(s(x, 480, x + 32, 480), fill=(20, 20, 20), width=12 * S)
    # petite table renversée + lampe
    d.rectangle(s(1080, 560, 1240, 580), fill=(110, 74, 50)); d.rectangle(s(1100, 580, 1116, 650), fill=(90, 60, 40)); d.rectangle(s(1204, 580, 1220, 650), fill=(90, 60, 40))
    d.polygon(s(1130, 470, 1190, 470, 1210, 530, 1110, 530), fill=(230, 200, 120)); d.rectangle(s(1154, 530, 1166, 560), fill=(60, 50, 40))
    st = im.resize((SCN_W, SCN_H), Image.LANCZOS)
    bars = Image.new("RGBA", (SCN_W, SCN_H), (0, 0, 0, 0)); bd = ImageDraw.Draw(bars)
    bd.rectangle([wx + ww / 2 - 6, wy, wx + ww / 2 + 6, wy + wh], fill=(120, 84, 60))
    bd.rectangle([wx, wy + wh / 2 - 6, wx + ww, wy + wh / 2 + 6], fill=(120, 84, 60))
    return st, bars


class Enquete:
    def __init__(self, c, work):
        self.c, self.work = c, work
        self.sus = c["suspects"]; assert len(self.sus) == 3 and 0 <= c["menteur"] <= 2
        self.static, self.bars = decor_static()
        self.insp = inspecteur(250)
        top, bot = np.array(NIGHT_TOP), np.array(NIGHT_BOT)
        y = np.linspace(0, 1, H)[:, None, None]
        self.BG = Image.fromarray(np.repeat(top * (1 - y) + bot * y, W, axis=1).astype(np.uint8), "RGB").convert("RGBA")
        fade = np.zeros((VIEW_H, 1), np.float32); fade[-160:, 0] = np.linspace(0, 1, 160) ** 1.5; fade[:40, 0] = np.linspace(1, 0, 40) * 0.8
        col = np.array(NIGHT_TOP if True else NIGHT_BOT)
        self.FADE = Image.fromarray(np.dstack([np.full((VIEW_H, W, 3), (12, 12, 28), np.uint8),
                                               np.repeat((fade * 255).astype(np.uint8), W, axis=1)]), "RGBA")
        self.rnd = [(random.Random(i).uniform(0, 1), random.Random(i * 7 + 1).uniform(0, 1), random.Random(i * 13 + 2).uniform(0.8, 1.3)) for i in range(70)]

    # ---------- voix ----------
    def voices(self):
        c = self.c; W_ = self.work; D = {}
        D["intro"] = say(f"Nouvelle enquête : {c['titre']}. Sauras-tu trouver qui ment ?", f"{W_}/intro.wav")
        for i, txt in enumerate(c["recit"]): D[f"r{i}"] = say(txt, f"{W_}/r{i}.wav")
        for i, s in enumerate(self.sus):
            raw = say(s["dit"], f"{W_}/s{i}.tmp.wav", speed=1.05); pitch(f"{W_}/s{i}.tmp.wav", f"{W_}/s{i}.wav", s.get("voix", 1.0))
            D[f"s{i}"] = round(duration(f"{W_}/s{i}.wav"), 3)
            D[f"n{i}"] = say(s["nom"] + ".", f"{W_}/n{i}.wav")
        D["question"] = say(c.get("question", "Alors, qui ment ? Écris ta réponse en commentaire avant la fin du chrono !"), f"{W_}/question.wav")
        D["reveal"] = say(c["explication_tts"], f"{W_}/reveal.wav")
        D["outro"] = say("Tu avais trouvé le coupable ? Dis-le en commentaire, et abonne-toi pour la prochaine enquête !", f"{W_}/outro.wav")
        self.DUR = D
        self.ENV = {f"s{i}": envelope(f"{W_}/s{i}.wav", int(D[f's{i}'] * FPS) + 2) for i in range(3)}

    def recit_plan(self):
        t, out = 0.4, []
        for i in range(len(self.c["recit"])): out.append(t); t += self.DUR[f"r{i}"] + 0.35
        return out, t + 0.5

    def timeline(self):
        r = lambda x: round(x * FPS) / FPS; D = self.DUR
        tl = [("intro", r(0.3 + D["intro"] + 0.7)), ("recit", r(self.recit_plan()[1]))]
        for i in range(3): tl.append((f"sus{i}", r(0.3 + D[f"n{i}"] + 0.25 + D[f"s{i}"] + 0.8)))
        self.CD = 8
        tl.append(("question", r(0.25 + D["question"] + 0.3 + self.CD + 0.2)))
        tl.append(("reveal", r(0.9 + D["reveal"] + 1.2)))
        tl.append(("outro", r(0.3 + D["outro"] + 1.6)))
        return tl

    # ---------- la scène animée ----------
    def scene(self, t, cam=(0.5, 0.5, 1.0), steps=0.0, ring=None, insp=None, flash_off=0.6, storm=True):
        im = self.static.copy(); d = ImageDraw.Draw(im)
        fl = flash_amount(t, flash_off) if storm else 0
        wx, wy, ww, wh = WIN
        if fl > 0:
            d.rectangle([wx, wy, wx + ww, wy + wh], fill=(120, 140, 200, int(150 * fl)))
            bx = wx + ww * 0.6
            d.polygon([(bx, wy + 10), (bx - 50, wy + 170), (bx - 6, wy + 170), (bx - 62, wy + 340), (bx + 48, wy + 130), (bx, wy + 130), (bx + 42, wy + 10)], fill=(255, 245, 180, int(255 * min(1, fl * 1.5))))
        for (a, b, sp) in self.rnd:                                      # pluie
            x = wx + a * ww; y = wy + ((b * wh + t * 900 * sp) % wh)
            y2 = min(wy + wh, y + 30)
            d.line([(x, y), (x - 9, y2)], fill=(150, 180, 230, 200), width=3)
        im.alpha_composite(self.bars)
        fx, fy, fw, fh = FRAME                                            # « ? » du tableau disparu
        q = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
        ImageDraw.Draw(q).text((fw / 2, fh / 2), "?", font=font(190, "Black"), fill=(255, 255, 255, int(55 + 35 * math.sin(t * 3))), anchor="mm")
        im.alpha_composite(q, (fx, fy))
        n = len(STEPS)
        for k, (x, y) in enumerate(STEPS):                                # traces de boue
            p = steps * n - k
            if p <= 0: continue
            a = int(255 * min(1, p)); dd = ImageDraw.Draw(im)
            dd.ellipse([x, y, x + 62, y + 32], fill=(48, 30, 18, a)); dd.ellipse([x + 56, y + 4, x + 78, y + 28], fill=(48, 30, 18, a))
        if ring:                                                          # cercle de mise en évidence
            (rx, ry, rr), p = ring
            if p > 0:
                rr2 = rr * (1.4 - 0.4 * ease_out(min(p * 2.5, 1))) * (1 + 0.04 * math.sin(t * 8))
                d.ellipse([rx - rr2, ry - rr2 * 0.75, rx + rr2, ry + rr2 * 0.75], outline=ACC + (int(255 * min(1, p * 3)),), width=9)
        if insp is not None:                                              # inspecteur qui entre en marchant
            x, walk = insp
            bob = abs(math.sin(t * 7)) * 10 * walk
            im.alpha_composite(self.insp, (int(x), int(866 - self.insp.height + 10 - bob)))
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
        f = fit_font("x", 1, 54); lines = wrap2(text, font(54, "Black"), CW)
        lay = Image.new("RGBA", (W, 90 * len(lines) + 40), (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
        for k, ln in enumerate(lines):
            dl.text((CX, 45 + k * 70), ln, font=font(54, "Black"), fill=WHITE, anchor="mm", stroke_width=6, stroke_fill=(8, 8, 18))
        paste(im, lay, 0, y + (1 - ease_out(p)) * 25, alpha=min(1, p * 1.6))

    # ---------- scènes ----------
    def draw_intro(self, t):
        im = self.BG.copy(); self.put_scene(im, self.scene(t, flash_off=0.35), dim=0.35)
        # rubans de police qui traversent l'écran
        for k, (y, ang, sp) in enumerate([(700, -9, 1), (860, 7, -1)]):
            tape = Image.new("RGBA", (2600, 96), ACC + (255,)); td = ImageDraw.Draw(tape)
            lab = "ENQUÊTE  •  NE PAS FRANCHIR  •  "; step = int(_dummy.textlength(lab, font=font(44, "Black")))
            off = (t * 260 * sp) % step
            for x in range(-step, 2600 + step, step): td.text((x + off, 48), lab, font=font(44, "Black"), fill=(20, 20, 20), anchor="lm")
            tape = tape.rotate(ang, expand=True, resample=Image.BICUBIC)
            p = ease_out((t - 0.15 * k) / 0.5)
            im.alpha_composite(tape, (int(W / 2 - tape.width / 2 + (1 - p) * 1400 * (1 if k else -1)), int(y - tape.height / 2)))
        big = Image.new("RGBA", (1000, 300), (0, 0, 0, 0)); bd = ImageDraw.Draw(big)
        bd.text((500, 100), self.c["titre"].upper(), font=fit_font(self.c["titre"].upper(), 940, 96), fill=WHITE, anchor="mm", stroke_width=8, stroke_fill=(8, 8, 18))
        bd.text((500, 215), "Qui ment ?", font=font(76, "Black"), fill=ACC, anchor="mm", stroke_width=7, stroke_fill=(8, 8, 18))
        paste(im, big, CX - 500, 1100, scale=max(0.05, 0.6 + 0.4 * ease_back((t - 0.5) / 0.45)), alpha=min(1, max(0, (t - 0.5) * 3)))
        ImageDraw.Draw(im).text((CX, 215), "NOUVELLE ENQUÊTE", font=font(50, "Black"), fill=ACC, anchor="mm")
        return im

    def recit_state(self, t):
        st, _ = self.recit_plan(); ev = self.c.get("evenements", {})
        def since(name):
            i = ev.get(name); return -1 if i is None else t - st[i]
        cams = [(0, (0.5, 0.5, 1.0))]
        if since("tableau") >= 0: cams.append((st[ev["tableau"]], (0.55, 0.3, 1.45)))
        if since("traces") >= 0: cams.append((st[ev["traces"]], (0.55, 0.84, 1.35)))
        if since("fenetre") >= 0: cams.append((st[ev["fenetre"]], (0.18, 0.35, 1.5)))
        if since("inspecteur") >= 0: cams.append((st[ev["inspecteur"]], (0.5, 0.5, 1.0)))
        (t0, prev), (t1, cur) = (cams[-2] if len(cams) > 1 else cams[0]), cams[-1]
        p = ease_out((t - t1) / 0.9) if len(cams) > 1 else 1
        cam = tuple(a + (b - a) * p for a, b in zip(prev, cur))
        cam = (cam[0], cam[1], cam[2] * (1 + 0.015 * t))           # léger zoom continu
        steps = min(1, max(0, since("traces")) / 1.6) if since("traces") >= 0 else 0
        ring = None
        if since("tableau") >= 0 and since("traces") < 0: ring = ((FRAME[0] + FRAME[2] / 2, FRAME[1] + FRAME[3] / 2, 250), since("tableau") - 0.5)
        if since("traces") >= 0 and since("fenetre") < 0 and since("inspecteur") < 0: ring = ((720, 790, 230), since("traces") - 1.4)
        if since("fenetre") >= 0 and since("inspecteur") < 0: ring = ((WIN[0] + WIN[2] / 2, WIN[1] + WIN[3] / 2, 240), since("fenetre") - 0.4)
        insp = None
        if since("inspecteur") >= 0:
            p = ease_out(since("inspecteur") / 2.2); insp = (1350 - 430 * p, 1 - p)
        cur_i = max([i for i, s in enumerate(st) if t >= s - 0.05] or [0])
        return cam, steps, ring, insp, cur_i, t - st[cur_i]

    def draw_recit(self, t):
        im = self.BG.copy(); self.header(im)
        cam, steps, ring, insp, i, ts = self.recit_state(t)
        self.put_scene(im, self.scene(t + 2.0, cam, steps, ring, insp))
        self.subtitle(im, self.c["recit"][i], ts / 0.3)
        return im

    def draw_sus(self, i, t):
        s = self.sus[i]; D = self.DUR
        im = self.BG.copy(); self.header(im, f"SUSPECT {i + 1}/3")
        self.put_scene(im, self.scene(t + 7 * i, (0.5, 0.5, 1.0), 1, None, (920, 0), storm=False), dim=0.55)
        t_say = 0.3 + D[f"n{i}"] + 0.25; env = self.ENV[f"s{i}"]
        fi = int((t - t_say) * FPS); mouth = env[fi] if 0 <= fi < len(env) else 0
        blink = (t % 2.9) < 0.12
        p = ease_back(t / 0.5); bob = math.sin(t * 2.2) * 6
        spr = perso(s["perso"], 470, mouth=mouth * 1.3, blink=blink)
        paste(im, spr, CX - spr.width / 2 + (1 - min(p, 1)) * (-700 if i % 2 == 0 else 700), 560 + bob)
        d = ImageDraw.Draw(im)
        tag, tp = rr_image(int(_dummy.textlength(s["nom"], font=font(50, "Black")) + 80), 90, 45, ACC, shadow=True)
        ImageDraw.Draw(tag).text((tp + tag.width / 2 - tp, tp + 47), s["nom"], font=font(50, "Black"), fill=DARK, anchor="mm")
        paste(im, tag, CX - tag.width / 2, 1135 - tp, alpha=min(1, t * 3))
        # bulle avec le texte qui s'écrit au rythme de la voix
        if t > t_say - 0.1:
            prog = min(1, (t - t_say) / max(0.5, D[f"s{i}"] * 0.92))
            txt = "« " + s["dit"] + " »"; nshow = int(len(txt) * prog)
            fo = font(46, "Bold"); lines = wrap2(txt, fo, CW - 90); bh = int(58 * len(lines) + 70)
            bub, bp = rr_image(CW, bh, 34, WHITE, shadow=True); bdraw = ImageDraw.Draw(bub)
            bdraw.polygon([(bp + CW / 2 - 30, bp), (bp + CW / 2 + 30, bp), (bp + CW / 2, bp - 34)], fill=WHITE)
            shown = 0
            for k, ln in enumerate(lines):
                part = ln[: max(0, nshow - shown)]; shown += len(ln) + 1
                bdraw.text((bp + 45, bp + 35 + k * 58), part, font=fo, fill=DARK, anchor="lt")
            paste(im, bub, CX0 - bp, 1250 - bp, alpha=min(1, (t - t_say + 0.1) * 4))
        return im

    def cards(self, im, t, rev=None):
        """Les trois suspects côte à côte ; rev = progression de la révélation."""
        cw = CW // 3 - 12; m = self.c["menteur"]
        for k, s in enumerate(self.sus):
            x0 = CX0 + k * (cw + 18); y0 = 470
            liar = rev is not None and k == m
            dim = rev is not None and k != m and rev > 0
            border = RED if liar and rev > 0 else (70, 74, 110)
            c, cp = rr_image(cw, 470, 30, (30, 32, 56), border=border, bw=6 if liar and rev > 0 else 3, shadow=True)
            dc = ImageDraw.Draw(c)
            blink = ((t + k * 0.9) % 3.1) < 0.12
            spr = perso(s["perso"], 220, blink=blink); c.alpha_composite(spr, (cp + cw // 2 - 110, cp + 18))
            dc.text((cp + cw / 2, cp + 315), s["nom"], font=fit_font(s["nom"], cw - 20, 34), fill=ACC, anchor="mm")
            for j, ln in enumerate(wrap2(s["court"], font(28, "SemiBold"), cw - 30)):
                dc.text((cp + cw / 2, cp + 365 + j * 36), ln, font=font(28, "SemiBold"), fill=SOFT2, anchor="mm")
            ent = ease_out((t - 0.12 * k) / 0.4)
            sc = 1.0
            if liar and rev > 0: sc = 1 + 0.08 * ease_back(min(rev / 0.4, 1))
            paste(im, c, x0 - cp, y0 - cp + (1 - ent) * 120, alpha=(0.35 if dim else 1) * min(1, ent * 1.5), scale=sc)
            if liar and rev > 0.35:                                  # tampon « MENTEUR ! »
                p = (rev - 0.35) / 0.3
                st = Image.new("RGBA", (420, 130), (0, 0, 0, 0)); sd = ImageDraw.Draw(st)
                sd.rounded_rectangle([6, 6, 414, 124], 18, outline=RED, width=10)
                sd.text((210, 68), "MENTEUR !", font=font(70, "Black"), fill=RED, anchor="mm")
                st = st.rotate(-14, expand=True, resample=Image.BICUBIC)
                paste(im, st, x0 + cw / 2 - st.width / 2, y0 + 150, alpha=min(1, p * 3), scale=max(0.05, 2.2 - 1.2 * ease_out(p)))

    def draw_question(self, t):
        im = self.BG.copy(); self.header(im); d = ImageDraw.Draw(im)
        big = Image.new("RGBA", (1000, 140), (0, 0, 0, 0)); ImageDraw.Draw(big).text((500, 70), "QUI MENT ?", font=font(110, "Black"), fill=ACC, anchor="mm")
        paste(im, big, CX - 500, 300, scale=max(0.05, 0.6 + 0.4 * ease_back(t / 0.4)) * (1 + 0.03 * math.sin(t * 5)))
        self.cards(im, t)
        t_cd = 0.25 + self.DUR["question"] + 0.3
        if t >= t_cd:
            ti = t - t_cd; n = max(1, int(math.ceil(self.CD - ti - 1e-6))); frac = max(0, 1 - ti / self.CD)
            s2 = 2; R = 80; size = (R + 14) * 2
            tm = Image.new("RGBA", (size * s2, size * s2), (0, 0, 0, 0)); td = ImageDraw.Draw(tm); c = size * s2 / 2
            td.ellipse([c - R * s2, c - R * s2, c + R * s2, c + R * s2], fill=(12, 18, 26, 235), outline=(255, 255, 255, 45), width=10 * s2)
            col = GREEN if n > 3 else YELLOW if n > 1 else RED
            td.arc([c - R * s2, c - R * s2, c + R * s2, c + R * s2], -90, -90 + 360 * frac, fill=col, width=12 * s2)
            tm = tm.resize((size, size), Image.LANCZOS)
            sc = 1 + 0.25 * max(0, 1 - (ti % 1.0) / 0.25)
            ImageDraw.Draw(tm).text((size / 2, size / 2 + 3), str(n), font=font(int(74 * sc), "Black"), fill=WHITE, anchor="mm")
            im.alpha_composite(tm, (CX - size // 2, 1080 - size // 2))
            d.text((CX, 1215), "Écris ta réponse en commentaire !", font=font(44, "Bold"), fill=WHITE, anchor="mm")
        return im

    def draw_reveal(self, t):
        im = self.BG.copy(); self.header(im, "SOLUTION")
        d = ImageDraw.Draw(im)
        d.text((CX, 365), self.c["reponse"].upper(), font=fit_font(self.c["reponse"].upper(), CW, 86), fill=RED, anchor="mm")
        self.cards(im, 5, rev=t)
        if t > 0.9:                                                   # l'indice : la fenêtre sous l'orage
            p = ease_out((t - 0.9) / 0.4)
            view = self.scene(t, (0.19, 0.33, 2.1), storm=False).resize((540, 360), Image.BILINEAR)
            card, cp = rr_image(560, 380, 26, ACC, shadow=True); card.alpha_composite(view, (cp + 10, cp + 10))
            paste(im, card, CX - 280 - cp, 990 - cp + (1 - p) * 80, alpha=min(1, p * 1.5))
            if t > 1.4:
                lab, lp = rr_image(430, 70, 35, RED)
                ImageDraw.Draw(lab).text((lp + 215, lp + 37), self.c.get("indice", "Il pleuvait à verse !"), font=fit_font(self.c.get("indice", "Il pleuvait à verse !"), 400, 38), fill=WHITE, anchor="mm")
                paste(im, lab, CX - 215 - lp, 1335 - lp, scale=0.85 + 0.15 * ease_back((t - 1.4) / 0.35))
            if t > 2.2:
                fe = font(40, "SemiBold")
                for k, ln in enumerate(wrap2(self.c["explication"], fe, CW)):
                    d.text((CX, 1440 + k * 50), ln, font=fe, fill=WHITE, anchor="mm")
        return im

    def draw_outro(self, t):
        im = self.BG.copy(); self.put_scene(im, self.scene(t, (0.5, 0.5, 1.0), 1, None, (920, 0), storm=False), dim=0.6)
        d = ImageDraw.Draw(im); p = ease_back(t / 0.4)
        st = Image.new("RGBA", (900, 200), (0, 0, 0, 0)); sd = ImageDraw.Draw(st)
        sd.rounded_rectangle([8, 8, 892, 192], 24, outline=GREEN, width=12)
        sd.text((450, 100), "AFFAIRE RÉSOLUE", font=font(86, "Black"), fill=GREEN, anchor="mm")
        st = st.rotate(-6, expand=True, resample=Image.BICUBIC)
        paste(im, st, CX - st.width / 2, 470, scale=max(0.05, 2 - ease_out(t / 0.35)), alpha=min(1, t * 4))
        if t > 0.8:
            lp = (t - 0.8) / 0.35
            d.text((CX, 1110), "Tu avais trouvé ?", font=font(72, "Black"), fill=WHITE, anchor="mm", stroke_width=6, stroke_fill=(8, 8, 18))
            d.text((CX, 1200), "Dis-le en commentaire !", font=font(52, "Bold"), fill=SOFT2, anchor="mm", stroke_width=5, stroke_fill=(8, 8, 18))
            btn, bp = cta_button("+ ABONNE-TOI", 700, 130, 60)
            paste(im, btn, CX - 350 - bp, 1290 - bp, alpha=min(1, lp * 2), scale=(0.8 + 0.2 * ease_back(lp)) * (1 + 0.04 * math.sin(t * 6)))
        return im

    def frame_fn(self, name):
        if name.startswith("sus"):
            i = int(name[3:]); return lambda t: self.draw_sus(i, t)
        return getattr(self, f"draw_{name}")

    def check_frames(self):
        st, end = self.recit_plan()
        out = [("intro", 2.0)] + [("recit", s + 1.2) for s in st] + [(f"sus{i}", 0.3 + self.DUR[f"n{i}"] + 0.25 + self.DUR[f"s{i}"] * 0.7) for i in range(3)]
        out += [("question", 0.25 + self.DUR["question"] + 1.5), ("reveal", 3.0), ("outro", 2.5)]
        return out

    # ---------- audio ----------
    def audio(self, tl, wav):
        total = sum(d for _, d in tl); tr = Track(total); t0 = 0.0; W_ = self.work
        rng = np.random.default_rng(1)
        def colored(n, lo, hi):
            x = np.fft.rfft(rng.standard_normal(n)); f = np.fft.rfftfreq(n, 1 / SR)
            x *= ((f > lo) & (f < hi)) / np.maximum(f, 20) ** 0.5
            y = np.fft.irfft(x, n); return y / np.abs(y).max()
        thunder_n = int(2.2 * SR); tt = np.arange(thunder_n) / SR
        THUNDER = colored(thunder_n, 20, 260) * np.minimum(tt / 0.06, 1) * np.exp(-tt / 0.7)
        THUNDER[: int(0.25 * SR)] += colored(int(0.25 * SR), 400, 5000) * np.exp(-tt[: int(0.25 * SR)] / 0.05) * 0.5
        THUD = np.sin(2 * np.pi * (60 + 90 * np.exp(-tt[: int(0.4 * SR)] / 0.03)) * tt[: int(0.4 * SR)]) * np.exp(-tt[: int(0.4 * SR)] / 0.1)
        storm_scenes = {"intro": 0.35, "recit": 0.6 + 2.0}
        for name, dur in tl:
            if name != "intro": tr.add(tr.sfx, WHOOSH, t0, 0.2)
            if name == "intro": tr.add(tr.voice, load(f"{W_}/intro.wav"), t0 + 0.3)
            elif name == "recit":
                st, _ = self.recit_plan()
                for i, s in enumerate(st): tr.add(tr.voice, load(f"{W_}/r{i}.wav"), t0 + s)
            elif name.startswith("sus"):
                i = int(name[3:]); tr.add(tr.voice, load(f"{W_}/n{i}.wav"), t0 + 0.3)
                tr.add(tr.voice, load(f"{W_}/s{i}.wav"), t0 + 0.3 + self.DUR[f"n{i}"] + 0.25)
            elif name == "question":
                tr.add(tr.voice, load(f"{W_}/question.wav"), t0 + 0.25); t_cd = 0.25 + self.DUR["question"] + 0.3
                for k in range(self.CD): tr.add(tr.sfx, TICK if k % 2 == 0 else TOCK, t0 + t_cd + k, 0.45 if self.CD - k > 2 else 0.7)
            elif name == "reveal":
                tr.add(tr.sfx, DING, t0, 0.4); tr.add(tr.sfx, THUD, t0 + 0.4, 0.9); tr.add(tr.voice, load(f"{W_}/reveal.wav"), t0 + 0.9)
            elif name == "outro":
                tr.add(tr.sfx, THUD, t0 + 0.1, 0.7); tr.add(tr.voice, load(f"{W_}/outro.wav"), t0 + 0.3)
            if name in ("intro", "recit"):                    # tonnerre synchronisé avec les éclairs
                off = 0.35 if name == "intro" else 0.6
                shift = 0 if name == "intro" else 2.0
                for ft in flash_times(dur + shift, off):
                    if ft - shift >= 0: tr.add(tr.sfx, THUNDER, t0 + ft - shift + 0.15, 0.5)
            t0 += dur
        rain = colored(tr.N, 800, 9000); tr.sfx += rain * 0.035          # pluie en fond tout du long
        mixdown(tr, wav, music_gain=0.4, soft=True, chords=CHORDS, bpm=78)
