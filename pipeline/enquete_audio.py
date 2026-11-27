"""Vidéo « Enquête » montée sur UNE voix off externe (ElevenLabs, voix Tomas).

Le contenu JSON garde la structure de enquete.py, avec en plus :
  "audio": "chemin/vers/voix.mp3"            (relatif au JSON)
  "mots":  "chemin/vers/mots.json"           (transcription mot à mot : [{"text", "start", "end"}, ...])
  "intro" de chaque suspect : la phrase du narrateur avant sa réplique (« Le majordome, d'abord : »)
  "carnet" : la phrase lue pendant l'écran des indices ; "panne" : [i_debut, i_fin] des phrases du récit
  où la lumière est coupée.
La voix est découpée phrase par phrase grâce aux horodatages, puis chaque morceau est calé sur sa scène.
"""
import json, math, os, random, re, subprocess, unicodedata
import numpy as np
from PIL import Image, ImageDraw
import enquete as E
from enquete import Enquete, envelope, flash_times, ACC, FRAME, WIN, SCN_W, SCN_H
from common import *
from common import _dummy
from enigme import wrap2, fit_font, CX0, CW, CX, SOFT2, DARK

# ---------------- personnages supplémentaires ----------------
E.SKIN.update({"majordome": (236, 200, 170), "neveu": (226, 178, 140)})
E.BODY.update({"majordome": (28, 28, 34), "neveu": (200, 70, 60)})
_perso_base = E.perso


def perso(kind, w, mouth=0.0, blink=False):
    if kind in ("moniteur", "photographe", "cousin"): return perso_chalet(kind, w, mouth, blink)
    if kind not in ("majordome", "neveu"): return _perso_base(kind, w, mouth, blink)
    k = w / 270 * E.S; h = int(330 * w / 270)
    im = Image.new("RGBA", (int(270 * k), int(330 * k)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    s = lambda *v: [x * k for x in v]; cx = 135
    if kind == "majordome":
        d.rounded_rectangle(s(cx - 80, 170, cx + 80, 330), int(50 * k), fill=(28, 28, 34))
        d.polygon(s(cx - 34, 172, cx + 34, 172, cx, 290), fill=(245, 245, 245))           # chemise
        d.polygon(s(cx - 34, 172, cx - 6, 172, cx - 28, 250), fill=(44, 44, 52)); d.polygon(s(cx + 34, 172, cx + 6, 172, cx + 28, 250), fill=(44, 44, 52))
        d.polygon(s(cx - 26, 180, cx - 26, 204, cx, 192), fill=(20, 20, 20)); d.polygon(s(cx + 26, 180, cx + 26, 204, cx, 192), fill=(20, 20, 20))
        d.ellipse(s(cx - 7, 185, cx + 7, 199), fill=(10, 10, 10))                          # nœud papillon
        for yb in (236, 266, 296): d.ellipse(s(cx - 5, yb - 5, cx + 5, yb + 5), fill=(190, 190, 190))
        d.ellipse(s(cx - 52, 60, cx + 52, 172), fill=E.SKIN[kind])
        d.ellipse(s(cx - 58, 92, cx - 40, 130), fill=(200, 200, 205)); d.ellipse(s(cx + 40, 92, cx + 58, 130), fill=(200, 200, 205))
        d.chord(s(cx - 52, 58, cx + 52, 150), 180, 360, fill=(205, 205, 210)); d.chord(s(cx - 46, 70, cx + 46, 140), 180, 360, fill=E.SKIN[kind])
        E.eyes(d, s, cx, 111, k, blink)
        d.line(s(cx - 22, 96, cx - 8, 92), fill=(150, 150, 150), width=int(4 * k)); d.line(s(cx + 8, 92, cx + 22, 96), fill=(150, 150, 150), width=int(4 * k))
        E.mouth_draw(d, s, cx, 136, k, mouth)
    else:
        d.rounded_rectangle(s(cx - 80, 170, cx + 80, 330), int(50 * k), fill=(200, 70, 60))      # sweat à capuche
        d.rounded_rectangle(s(cx - 62, 156, cx + 62, 200), int(22 * k), fill=(170, 52, 46))
        d.rounded_rectangle(s(cx - 44, 262, cx + 44, 302), int(12 * k), fill=(170, 52, 46))
        d.line(s(cx - 14, 190, cx - 18, 240), fill=WHITE, width=int(4 * k)); d.line(s(cx + 14, 190, cx + 18, 240), fill=WHITE, width=int(4 * k))
        d.ellipse(s(cx - 50, 62, cx + 50, 170), fill=E.SKIN[kind])
        hair = (90, 56, 32)
        d.chord(s(cx - 54, 48, cx + 54, 130), 180, 360, fill=hair)
        for ox, oy in ((-40, 52), (-14, 40), (12, 42), (36, 52)): d.polygon(s(cx + ox - 16, oy + 30, cx + ox, oy - 4, cx + ox + 18, oy + 30), fill=hair)
        E.eyes(d, s, cx, 113, k, blink)
        E.mouth_draw(d, s, cx, 138, k, mouth)
    return im.resize((w, h), Image.LANCZOS)


def perso_chalet(kind, w, mouth=0.0, blink=False):
    k = w / 270 * E.S; h = int(330 * w / 270)
    im = Image.new("RGBA", (int(270 * k), int(330 * k)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    s = lambda *v: [x * k for x in v]; cx = 135
    skin = {"moniteur": (238, 196, 160), "photographe": (232, 186, 150), "cousin": (168, 112, 80)}[kind]
    if kind == "photographe":                                                       # queue de cheval derrière la tête
        d.ellipse(s(cx + 30, 70, cx + 86, 190), fill=(70, 44, 30))
    body = {"moniteur": (214, 40, 46), "photographe": (64, 120, 92), "cousin": (58, 82, 156)}[kind]
    d.rounded_rectangle(s(cx - 80, 170, cx + 80, 330), int(50 * k), fill=body)
    if kind == "moniteur":
        d.rectangle(s(cx - 80, 236, cx + 80, 252), fill=WHITE); d.line(s(cx, 176, cx, 330), fill=(160, 26, 30), width=int(5 * k))
        d.rounded_rectangle(s(cx - 50, 166, cx + 50, 192), int(12 * k), fill=(180, 30, 36))
    elif kind == "photographe":
        d.rounded_rectangle(s(cx - 62, 162, cx + 62, 196), int(16 * k), fill=(236, 230, 214))   # col en fourrure
        d.line(s(cx - 44, 190, cx - 20, 250), fill=(30, 30, 30), width=int(5 * k)); d.line(s(cx + 44, 190, cx + 20, 250), fill=(30, 30, 30), width=int(5 * k))
        d.rounded_rectangle(s(cx - 40, 240, cx + 40, 292), int(8 * k), fill=(34, 34, 40)); d.rectangle(s(cx - 30, 232, cx - 12, 242), fill=(34, 34, 40))
        d.ellipse(s(cx - 18, 248, cx + 18, 284), fill=(70, 74, 90)); d.ellipse(s(cx - 9, 257, cx + 9, 275), fill=(140, 180, 230))
    else:
        for yy in (210, 260):
            pts = []
            for j in range(9): pts += [cx - 80 + j * 20, yy + (0 if j % 2 else 14)]
            d.line(s(*pts), fill=(236, 236, 240), width=int(5 * k))
    d.ellipse(s(cx - 52, 60, cx + 52, 172), fill=skin)
    E.eyes(d, s, cx, 111, k, blink)
    E.mouth_draw(d, s, cx, 136, k, mouth)
    if kind == "moniteur":                                                          # bonnet + pompon + masque
        d.chord(s(cx - 56, 34, cx + 56, 140), 180, 360, fill=(214, 40, 46)); d.rectangle(s(cx - 58, 78, cx + 58, 98), fill=WHITE)
        d.ellipse(s(cx - 18, 14, cx + 18, 50), fill=WHITE)
        d.rounded_rectangle(s(cx - 50, 56, cx + 50, 82), int(12 * k), fill=(255, 150, 40)); d.rectangle(s(cx - 56, 64, cx + 56, 72), fill=(30, 30, 30))
        d.rounded_rectangle(s(cx - 46, 59, cx + 46, 79), int(10 * k), fill=(255, 170, 60))
    elif kind == "photographe":
        d.chord(s(cx - 54, 54, cx + 54, 140), 180, 360, fill=(70, 44, 30)); d.ellipse(s(cx + 30, 74, cx + 58, 102), fill=(220, 60, 90))
    else:
        for ox in range(-46, 50, 16): d.ellipse(s(cx + ox - 12, 48, cx + ox + 12, 84), fill=(34, 26, 22))
        for ex in (-18, 18): d.ellipse(s(cx + ex - 17, 95, cx + ex + 17, 127), outline=(30, 30, 30), width=int(4 * k))
        d.line(s(cx - 1, 108, cx + 1, 108), fill=(30, 30, 30), width=int(4 * k))
    return im.resize((w, h), Image.LANCZOS)


E.perso = perso
_icon_base = E.icon


def icon(kind, size=110):
    if kind not in ("courant", "cadre", "neige", "pas", "coffre"): return _icon_base(kind, size)
    k = size / 100 * E.S; im = Image.new("RGBA", (int(100 * k), int(100 * k)), (0, 0, 0, 0)); d = ImageDraw.Draw(im); s = lambda *v: [x * k for x in v]
    if kind == "courant":                                   # ampoule éteinte barrée
        d.ellipse(s(26, 8, 74, 58), fill=(120, 124, 150)); d.rectangle(s(38, 52, 62, 72), fill=(120, 124, 150))
        d.rectangle(s(36, 72, 64, 86), fill=(80, 84, 104)); d.rectangle(s(40, 86, 60, 92), fill=(80, 84, 104))
        d.line(s(14, 90, 88, 10), fill=(240, 60, 60), width=int(9 * k))
    elif kind == "neige":                                   # flocon
        for a in range(0, 180, 60):
            r = math.radians(a); dx, dy = 40 * math.cos(r), 40 * math.sin(r)
            d.line(s(50 - dx, 50 - dy, 50 + dx, 50 + dy), fill=(220, 236, 255), width=int(7 * k))
            for sg in (-1, 1):
                bx, by = 50 + sg * dx * 0.6, 50 + sg * dy * 0.6
                for b in (-1, 1):
                    rb = r + b * math.radians(45) + (0 if sg > 0 else math.pi)
                    d.line(s(bx, by, bx + 14 * math.cos(rb), by + 14 * math.sin(rb)), fill=(220, 236, 255), width=int(5 * k))
    elif kind == "pas":                                     # traces de pas barrées
        d.rounded_rectangle(s(4, 20, 96, 80), int(14 * k), fill=(236, 242, 255))
        for ox, oy in ((22, 30), (54, 46)):
            d.ellipse(s(ox, oy, ox + 18, oy + 26), fill=(120, 130, 160)); d.ellipse(s(ox + 2, oy + 26, ox + 16, oy + 34), fill=(120, 130, 160))
        d.line(s(10, 88, 90, 12), fill=(240, 60, 60), width=int(9 * k))
    elif kind == "coffre":                                  # coffre-fort ouvert
        d.rounded_rectangle(s(8, 14, 76, 86), int(8 * k), fill=(110, 116, 132)); d.rectangle(s(18, 24, 66, 76), fill=(26, 28, 36))
        d.polygon(s(76, 16, 96, 24, 96, 76, 76, 84), fill=(150, 156, 170))
    else:                                                   # cadre vide
        d.rectangle(s(8, 14, 92, 86), fill=(212, 170, 60)); d.rectangle(s(18, 24, 82, 76), fill=(36, 40, 60))
        d.text(s(50, 50), "?", font=font(int(46 * k), "Black"), fill=(255, 255, 255, 170), anchor="mm")
    return im.resize((size, size), Image.LANCZOS)


E.icon = icon


# ---------------- alignement de la voix ----------------
def _norm(w):
    w = unicodedata.normalize("NFD", w.lower()); w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", w)


def _tokens(text):
    return [t for t in (_norm(x) for x in re.split(r"[\s'’\-]+", text)) if t]


def aligner(units, mots):
    """units : [(clé, texte)] dans l'ordre de lecture ; mots : transcription. Retourne {clé: début en s}."""
    seq = []
    for m in mots:
        for t in _tokens(m["text"]): seq.append((t, m["start"], m["end"]))
    out, j = {}, 0
    for key, text in units:
        toks = _tokens(text); assert toks, key
        best = None
        for jj in range(j, min(len(seq), j + 12)):                 # tolère quelques mots mal transcrits
            ok = sum(1 for a, b in zip(toks[:4], [x[0] for x in seq[jj:jj + 4]]) if a == b)
            if best is None or ok > best[0]: best = (ok, jj)
            if ok == min(4, len(toks)): break
        if best[0] < min(2, len(toks)): raise SystemExit(f"alignement impossible pour « {text[:40]} » (mots reçus : {[x[0] for x in seq[j:j+6]]})")
        jj = best[1]; out[key] = seq[jj][1]; j = jj + len(toks) - 2
    return out


# ---------------- décor « chalet » (neige) ----------------
def decor_chalet():
    S2 = E.S; im = Image.new("RGBA", (SCN_W * S2, SCN_H * S2), (0, 0, 0, 0)); d = ImageDraw.Draw(im); s = lambda *v: [x * S2 for x in v]
    fy = 640
    d.rectangle(s(0, 0, SCN_W, fy), fill=(112, 72, 46))                                  # murs en rondins
    for y in range(0, fy, 64):
        d.rectangle(s(0, y + 50, SCN_W, y + 64), fill=(92, 58, 36)); d.line(s(0, y + 2, SCN_W, y + 2), fill=(130, 88, 58), width=3 * S2)
    d.rectangle(s(0, fy, SCN_W, SCN_H), fill=(84, 56, 40))
    for x in range(-300, SCN_W + 300, 120): d.line(s(x, fy, x - 140, SCN_H), fill=(72, 46, 32), width=4 * S2)
    d.rectangle(s(0, fy - 22, SCN_W, fy + 6), fill=(60, 38, 26))
    wx, wy, ww, wh = WIN                                                                  # fenêtre : montagne enneigée
    d.rectangle(s(wx - 16, wy - 16, wx + ww + 16, wy + wh + 16), fill=(150, 104, 66))
    for k in range(wh):
        a = k / wh; col = tuple(int(c0 * (1 - a) + c1 * a) for c0, c1 in zip((22, 34, 78), (120, 120, 170)))
        d.line(s(wx, wy + k, wx + ww, wy + k), fill=col)
    d.polygon(s(wx, wy + 230, wx + 80, wy + 140, wx + 150, wy + 210, wx + 230, wy + 110, wx + ww, wy + 200, wx + ww, wy + wh, wx, wy + wh), fill=(70, 78, 120))
    d.polygon(s(wx + 52, wy + 166, wx + 80, wy + 140, wx + 108, wy + 168, wx + 92, wy + 160, wx + 80, wy + 172, wx + 66, wy + 160), fill=(235, 240, 255))
    d.polygon(s(wx + 196, wy + 146, wx + 230, wy + 110, wx + 266, wy + 150, wx + 246, wy + 142, wx + 230, wy + 156, wx + 212, wy + 142), fill=(235, 240, 255))
    d.rectangle(s(wx, wy + 300, wx + ww, wy + wh), fill=(236, 242, 255))                  # neige au sol, intacte
    d.ellipse(s(wx, wy + 276, wx + 170, wy + 326), fill=(236, 242, 255)); d.ellipse(s(wx + 120, wy + 282, wx + ww, wy + 330), fill=(236, 242, 255))
    for tx in (wx + 40, wx + 290):
        d.polygon(s(tx, wy + 300, tx + 22, wy + 236, tx + 44, wy + 300), fill=(40, 90, 70)); d.polygon(s(tx + 6, wy + 262, tx + 22, wy + 222, tx + 38, wy + 262), fill=(50, 104, 80))
        d.polygon(s(tx + 8, wy + 246, tx + 22, wy + 222, tx + 36, wy + 246), fill=(240, 244, 255))
    d.rectangle(s(wx - 26, wy + wh + 10, wx + ww + 26, wy + wh + 28), fill=(170, 120, 78))
    fx, fy2, fw, fh = FRAME                                                               # coffre-fort ouvert
    d.rounded_rectangle(s(fx - 6, fy2 - 6, fx + fw + 6, fy2 + fh + 6), 14 * S2, fill=(70, 76, 90))
    d.rectangle(s(fx + 20, fy2 + 20, fx + fw - 20, fy2 + fh - 20), fill=(26, 28, 36))
    d.rectangle(s(fx + 40, fy2 + fh / 2 - 4, fx + fw - 40, fy2 + fh / 2 + 4), fill=(50, 54, 66))
    d.polygon(s(fx + fw + 6, fy2 + 4, fx + fw + 96, fy2 + 30, fx + fw + 96, fy2 + fh - 30, fx + fw + 6, fy2 + fh - 4), fill=(96, 104, 122))
    d.ellipse(s(fx + fw + 34, fy2 + fh / 2 - 26, fx + fw + 78, fy2 + fh / 2 + 26), fill=(150, 156, 170)); d.ellipse(s(fx + fw + 48, fy2 + fh / 2 - 10, fx + fw + 64, fy2 + fh / 2 + 10), fill=(70, 76, 90))
    for x in (500, 940):                                                                  # poteaux + ruban
        d.rectangle(s(x - 8, 470, x + 8, 660), fill=(200, 170, 70)); d.ellipse(s(x - 18, 450, x + 18, 486), fill=(220, 190, 80))
        d.ellipse(s(x - 30, 650, x + 30, 672), fill=(160, 130, 50))
    d.line(s(500, 480, 940, 480), fill=ACC, width=12 * S2)
    for x in range(500, 940, 64): d.line(s(x, 480, x + 32, 480), fill=(20, 20, 20), width=12 * S2)
    d.rectangle(s(1080, 560, 1240, 580), fill=(110, 74, 50)); d.rectangle(s(1100, 580, 1116, 650), fill=(90, 60, 40)); d.rectangle(s(1204, 580, 1220, 650), fill=(90, 60, 40))
    d.polygon(s(1130, 470, 1190, 470, 1210, 530, 1110, 530), fill=(230, 200, 120)); d.rectangle(s(1154, 530, 1166, 560), fill=(60, 50, 40))
    return im.resize((SCN_W, SCN_H), Image.LANCZOS)


FLOCONS = [(random.Random(i * 3 + 5).uniform(0, 1), random.Random(i * 11 + 7).uniform(0, 1), random.Random(i * 17 + 3).uniform(0.6, 1.2)) for i in range(45)]


def charger_mots(path):
    """Transcription ElevenLabs : fichier words.json ({"words": [...]}) ou liste simple."""
    d = json.load(open(path)); d = d["words"] if isinstance(d, dict) else d
    return [w for w in d if w.get("type", "word") == "word"]


def point_calme(full, t):
    """Instant le plus silencieux dans [t-0.5 s, t+0.05 s] : une coupe ne tombe jamais au milieu d'un mot."""
    if t <= 0.1: return 0.0
    fr = int(0.02 * SR); a0 = max(0, int((t - 0.5) * SR)); seg = full[a0: int((t + 0.05) * SR)]
    n = len(seg) // fr; e = [np.sqrt(np.mean(seg[i * fr:(i + 1) * fr] ** 2)) for i in range(n)]
    i = int(np.argmin(e)); return (a0 + i * fr + fr // 2) / SR


class EnqueteAudio(Enquete):
    GAP_RECIT = 0.12

    def __init__(self, c, work, base):
        super().__init__(c, work); self.base = base
        self.orage = c.get("orage", True); self.decor = c.get("decor", "manoir")
        if self.decor == "chalet": self.static = self.static0 = decor_chalet()
        if not c.get("pluie"): self.rnd = []                # pas de pluie animée (effet grésillant)
        if self.decor == "chalet":
            wx, wy, ww, wh = WIN; self.bars = Image.new("RGBA", (SCN_W, SCN_H), (0, 0, 0, 0)); bd = ImageDraw.Draw(self.bars)
            bd.rectangle([wx + ww / 2 - 6, wy, wx + ww / 2 + 6, wy + wh], fill=(150, 104, 66))
            bd.rectangle([wx, wy + wh / 2 - 6, wx + ww, wy + wh / 2 + 6], fill=(150, 104, 66))
        elif not c.get("fenetre_cassee"):                  # fenêtre intacte (sinon faux indice)
            wx, wy, ww, wh = WIN; self.bars = Image.new("RGBA", (SCN_W, SCN_H), (0, 0, 0, 0)); bd = ImageDraw.Draw(self.bars)
            bd.rectangle([wx + ww / 2 - 6, wy, wx + ww / 2 + 6, wy + wh], fill=(120, 84, 60))
            bd.rectangle([wx, wy + wh / 2 - 6, wx + ww, wy + wh / 2 + 6], fill=(120, 84, 60))

    def units(self):
        c = self.c; u = [("hook", c["accroche"])] + [(f"r{i}", t) for i, t in enumerate(c["recit"])]
        for i, s in enumerate(self.sus): u += [(f"n{i}", s["intro"]), (f"s{i}", s["dit"])]
        return u + [("carnet", c["carnet"]), ("fin", c["fin"])]

    def voices(self):
        c, w = self.c, self.work
        src = os.path.join(self.base, c["audio"]); mots = charger_mots(os.path.join(self.base, c["mots"]))
        units = self.units(); st = aligner(units, mots); total = mots[-1]["end"] + 0.25
        full = load(src); D = {}
        cut = {key: point_calme(full, st[key]) for key, _ in units}
        self.CUT = cut
        for k, (key, _) in enumerate(units):
            a = cut[key]
            b = cut[units[k + 1][0]] if k + 1 < len(units) else total
            seg = full[int(a * SR): int(b * SR)]          # découpe calée sur les horodatages seulement
            path = f"{w}/{key}.wav"
            open(path + ".f32", "wb").write(seg.astype(np.float32).tobytes())
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", path + ".f32", path], check=True)
            os.remove(path + ".f32"); D[key] = round(len(seg) / SR, 3)
        self.DUR = D; self.START = st
        self.ENV = {f"s{i}": envelope(f"{w}/s{i}.wav", int(D[f"s{i}"] * FPS) + 2) for i in range(3)}
        for i in range(3): self.ENV[f"q{i}"] = [0.0] * (int(D[f"n{i}"] * FPS) + 2)

    # ---------- plans ----------
    def recit_plan(self):
        t, out = 0.25, []
        for i in range(len(self.c["recit"])): out.append(t); t += self.DUR[f"r{i}"] + self.GAP_RECIT
        return out, t + 0.3

    def sus_plan(self, i):
        tq = 0.35; ts = tq + self.DUR[f"n{i}"] + 0.12
        return tq, ts, ts + self.DUR[f"s{i}"] + 0.55

    def recap_plan(self):
        n = len(self.c["recap"]); out = [0.3 + 0.75 * k for k in range(n + 1)]
        return out, max(out[-1] + 1.5, 0.3 + self.DUR["carnet"] + 2.2)

    def timeline(self):
        r = lambda x: round(x * FPS) / FPS; D = self.DUR
        tl = [("hook", r(0.05 + D["hook"] + 0.35)), ("recit", r(self.recit_plan()[1]))]
        for i in range(3): tl.append((f"sus{i}", r(self.sus_plan(i)[2])))
        tl.append(("recap", r(self.recap_plan()[1])))
        tl.append(("fin", r(0.3 + D["fin"] + 2.6)))
        return tl

    # ---------- panne de courant ----------
    def dark_at(self, t):
        if "panne" not in self.c: return 0.0
        st, _ = self.recit_plan(); a, b = self.c["panne"]
        t_off = st[a] + self.DUR[f"r{a}"] * 0.45; t_on = st[b] + 0.25
        if t < t_off: return 0.0
        if t < t_off + 0.25: return 0.82 * (1 if int((t - t_off) * 20) % 2 else 0.3)   # grésillement
        if t < t_on: return 0.82
        return 0.82 * max(0.0, 1 - (t - t_on) / 0.3)

    def scene(self, t, cam=(0.5, 0.5, 1.0), steps=0.0, ring=None, insp=None, flash_off=0.6, storm=None, dark=0.0, lamp=True, snow=0.0):
        if storm is None: storm = self.orage
        if self.decor == "chalet":
            st = self.static0
            if snow > 0:                                    # gros flocons lents dans la fenêtre
                st = st.copy(); sd = ImageDraw.Draw(st); wx, wy, ww, wh = WIN
                for k, (a, b, sp) in enumerate(FLOCONS):
                    if k >= len(FLOCONS) * snow: break
                    y = wy + (b * wh + t * 45 * sp) % wh; x = wx + (a * ww + 12 * math.sin(t * 0.8 + k)) % ww; r = 3 + 3 * sp
                    sd.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 225))
            self.static = st
        view = super().scene(t, cam, steps, ring, insp, flash_off, storm)
        if lamp and dark < 0.5:                                         # halo de la lampe allumée
            cx, cy, z = cam; cw, ch = SCN_W / z, SCN_H / z
            x0 = min(max(cx * SCN_W - cw / 2, 0), SCN_W - cw); y0 = min(max(cy * SCN_H - ch / 2, 0), SCN_H - ch)
            lx, ly = (1160 - x0) * E.VIEW_W / cw, (500 - y0) * E.VIEW_H / ch; r = 150 * z
            glow = Image.new("RGBA", view.size, (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
            for k in range(6): gd.ellipse([lx - r * (1 - k / 7), ly - r * (1 - k / 7), lx + r * (1 - k / 7), ly + r * (1 - k / 7)], fill=(255, 220, 140, 10))
            view.alpha_composite(glow)
        if dark > 0:
            fl = E.flash_amount(t, flash_off) if storm else 0
            view = Image.blend(view, Image.new("RGBA", view.size, (4, 6, 16, 255)), dark * (1 - 0.75 * fl))
        return view

    def draw_recit(self, t):
        im = self.BG.copy(); self.header(im)
        st, _ = self.recit_plan(); ev = self.c.get("evenements", {})
        since = lambda n: (t - st[ev[n]]) if n in ev else -1
        ins = self.insp_state(t)
        cam, i = self.recit_cam(t, st, ins)
        ring = None
        if i == ev.get("tableau"): ring = ((FRAME[0] + FRAME[2] / 2, FRAME[1] + FRAME[3] / 2, 250), since("tableau") - 0.4)
        if i == ev.get("fenetre"): ring = ((WIN[0] + WIN[2] / 2, WIN[1] + WIN[3] * 0.8, 230), since("fenetre") - 0.6)
        dk = self.dark_at(t)
        self.put_scene(im, self.scene(t + 2.0, cam, 0, ring, ins, dark=dk, snow=self.snow_at(t)))
        for b in self.c.get("bandeaux", []):               # bandeau d'info pendant certaines phrases
            if b["de"] <= i <= b["a"]:
                lab = Image.new("RGBA", (W, 120), (0, 0, 0, 0))
                ImageDraw.Draw(lab).text((CX, 60), b["texte"], font=fit_font(b["texte"], CW, 50), fill=ACC, anchor="mm", stroke_width=5, stroke_fill=(8, 8, 18))
                paste(im, lab, 0, 950, alpha=min(1, (t - st[b["de"]]) * 3))
        if dk > 0.5 and i < self.c["panne"][1]:
            lab = Image.new("RGBA", (W, 120), (0, 0, 0, 0)); txt = self.c.get("panne_texte", "PANNE DE COURANT  22 h → minuit")
            ImageDraw.Draw(lab).text((CX, 60), txt, font=fit_font(txt, CW, 50), fill=ACC, anchor="mm", stroke_width=5, stroke_fill=(8, 8, 18))
            paste(im, lab, 0, 950, alpha=min(1, (t - st[self.c["panne"][0]] - self.DUR[f"r{self.c['panne'][0]}"] * 0.45) * 3))
        self.subtitle(im, self.c["recit"][i], (t - st[i]) / 0.3)
        return im

    def snow_at(self, t):
        """Neige qui tombe pendant le récit, jusqu'à la phrase c["neige"][1] (elle s'arrête en 1,5 s)."""
        if "neige" not in self.c: return 0.0
        st, _ = self.recit_plan(); stop = st[self.c["neige"][1]] + 0.8
        return 1.0 if t < stop else max(0.0, 1 - (t - stop) / 1.5)

    def draw_hook(self, t):
        if "neige" in self.c:
            im = self.BG.copy(); self.put_scene(im, self.scene(t, flash_off=0.25, snow=1.0), dim=0.35); self.header(im)
            self.tapes(im, t)
            lines = wrap2(self.c["accroche"].upper(), font(78, "Black"), CW)
            lay = Image.new("RGBA", (W, 100 * len(lines) + 40), (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
            for k, ln in enumerate(lines):
                dl.text((CX, 60 + k * 96), ln, font=fit_font(ln, CW, 78), fill=ACC if k == len(lines) - 1 else WHITE, anchor="mm", stroke_width=8, stroke_fill=(8, 8, 18))
            paste(im, lay, 0, 1020, scale=1.12 - 0.12 * ease_out(t / 0.35) + 0.015 * math.sin(t * 6))
            return im
        return super().draw_hook(t)

    # ---------- interrogatoires : le narrateur annonce, le suspect parle ----------
    def draw_sus(self, i, t):
        s = self.sus[i]; D = self.DUR; tq, ts, _ = self.sus_plan(i)
        im = self.BG.copy(); self.header(im, f"SUSPECT {i + 1}/3")
        self.put_scene(im, self.scene(t + 7 * i, (0.5, 0.5, 1.0), 0, None, None, storm=False), dim=0.6)
        def env_at(key, t0):
            fi = int((t - t0) * FPS); e = self.ENV[key]; return e[fi] if 0 <= fi < len(e) else 0
        p = ease_out(t / 0.45)
        ins = E.inspecteur(300, pose="loupe_haut" if t < ts else "debout", blink=(t % 3.4) < 0.12)
        paste(im, ins, 20 - (1 - p) * 400, 1160 - ins.height + math.sin(t * 2) * 4)
        p2 = ease_back((t - 0.15) / 0.5)
        spr = perso(s["perso"], 420, mouth=env_at(f"s{i}", ts) * 1.3, blink=((t + 1.1) % 2.9) < 0.12)
        paste(im, spr, 480 + (1 - min(max(p2, 0), 1)) * 600, 1160 - spr.height + math.sin(t * 2.3 + 1) * 5)
        tag, tp = rr_image(int(_dummy.textlength(s["nom"], font=font(46, "Black")) + 70), 82, 41, ACC, shadow=True)
        ImageDraw.Draw(tag).text((tag.width / 2, tp + 43), s["nom"], font=font(46, "Black"), fill=DARK, anchor="mm")
        paste(im, tag, 690 - tag.width / 2, 1145 - tp, alpha=min(1, t * 3))
        if t >= ts - 0.1:
            self.bubble(im, s["dit"], min(1, (t - ts) / max(0.5, D[f"s{i}"] * 0.92)), 1265, 690)
        return im

    # ---------- indices ----------
    def draw_recap(self, t):
        im = self.BG.copy(); self.header(im, "LES INDICES"); d = ImageDraw.Draw(im)
        st, _ = self.recap_plan()
        big = Image.new("RGBA", (1000, 140), (0, 0, 0, 0)); ImageDraw.Draw(big).text((500, 70), "LES INDICES", font=font(92, "Black"), fill=ACC, anchor="mm")
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
        if t > st[-1] + 0.4:
            self.subtitle(im, "Un seul suspect ment…", (t - st[-1] - 0.4) / 0.3, y=1170)
        return im

    def check_frames(self):
        st, _ = self.recit_plan()
        out = [("hook", 0.0), ("hook", 1.5)] + [("recit", s + 1.2) for s in st]
        for i in range(3):
            tq, ts, _ = self.sus_plan(i); out += [(f"sus{i}", tq + 0.5), (f"sus{i}", ts + self.DUR[f"s{i}"] * 0.8)]
        rs, end = self.recap_plan()
        out += [("recap", end - 0.3), ("fin", 2.5)]
        return out

    # ---------- son ----------
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
        n2 = int(0.35 * SR); ZAP = colored(n2, 200, 6000) * (np.sin(np.arange(n2) / SR * 2 * np.pi * 18) > 0) * np.exp(-np.arange(n2) / SR / 0.15)
        for name, dur in tl:
            if name not in ("hook", "recit"): tr.add(tr.sfx, WHOOSH, t0, 0.2)
            if name == "hook": tr.add(tr.voice, load(f"{w}/hook.wav"), t0 + 0.05)
            elif name == "recit":
                st, _ = self.recit_plan()
                for i, s in enumerate(st): tr.add(tr.voice, load(f"{w}/r{i}.wav"), t0 + s)
                for k, ft in enumerate(self.footstep_times(dur)): tr.add(tr.sfx, STEP, t0 + ft, 0.32 if k % 2 else 0.26)
                if "panne" in self.c:
                    a, b = self.c["panne"]
                    tr.add(tr.sfx, THUNDER, t0 + st[a] + self.DUR[f"r{a}"] * 0.45 - 0.1, 0.8)
            elif name.startswith("sus"):
                i = int(name[3:]); tq, ts, _ = self.sus_plan(i)
                tr.add(tr.voice, load(f"{w}/n{i}.wav"), t0 + tq); tr.add(tr.voice, load(f"{w}/s{i}.wav"), t0 + ts)
            elif name == "recap":
                st, _ = self.recap_plan(); tr.add(tr.voice, load(f"{w}/carnet.wav"), t0 + 0.3)
                for s in st[1:]: tr.add(tr.sfx, POP, t0 + s - 0.05, 0.35)
            elif name == "fin":
                tr.add(tr.voice, load(f"{w}/fin.wav"), t0 + 0.3); tr.add(tr.sfx, POP, t0 + 0.8, 0.3)
            if name in ("hook", "recit") and self.orage:
                off, shift = (0.25, 0.0) if name == "hook" else (0.6, 2.0)
                for ft in flash_times(dur + shift, off):
                    if ft - shift >= 0: tr.add(tr.sfx, THUNDER, t0 + ft - shift + 0.15, 0.4)
            t0 += dur
        if self.c.get("pluie"): tr.sfx += colored(tr.N, 800, 9000) * 0.035   # bruit de pluie de fond
        tr.sfx *= self.c.get("volume_bruitages", 0.45)      # bruitages discrets sous la voix
        mixdown(tr, wav, music_gain=0.35, soft=True, chords=E.CHORDS, bpm=78)
