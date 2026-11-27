"""Vidéo « Énigmes » (enigmatik) : 5 énigmes de plus en plus dures, compte à rebours, réponse expliquée."""
import datetime, math, os, re
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from common import *
from common import _dummy

CX0, CW = 60, 880            # colonne de contenu (la colonne d'icônes TikTok à droite reste libre)
CX = CX0 + CW // 2
DARK = (10, 14, 20)
SOFT2 = (190, 205, 215)
CARD2 = (22, 32, 42)
NIV = [(46, 204, 113), (160, 230, 40), (255, 214, 10), (255, 140, 30), (240, 60, 60)]
NIV_NOM = ["FACILE", "FACILE", "MOYEN", "DIFFICILE", "EXPERT"]
TEMPS = [5, 5, 6, 6, 6]       # secondes de réflexion
FORMATS = {"suite": "SUITE LOGIQUE", "intrus": "TROUVE L'INTRUS", "symboles": "CALCUL DE SYMBOLES",
           "devinette": "DEVINETTE", "logique": "LOGIQUE"}
SHAPES = {"triangle": (255, 140, 30), "cercle": (0, 200, 255), "carre": (255, 70, 160),
          "etoile": (255, 214, 10), "losange": (160, 110, 255), "hexagone": (46, 204, 113)}
SHAPE_TTS = {"triangle": "triangle", "cercle": "cercle", "carre": "carré", "etoile": "étoile", "losange": "losange", "hexagone": "hexagone"}
THEMES = [  # fond haut, fond bas, accent, accent 2 — change chaque jour pour varier
    ((6, 14, 22), (8, 42, 48), (198, 255, 0), (0, 229, 255)),
    ((14, 8, 26), (40, 14, 58), (0, 255, 170), (255, 90, 200)),
    ((6, 10, 30), (10, 30, 72), (255, 214, 10), (0, 200, 255)),
    ((22, 10, 12), (58, 20, 26), (0, 229, 255), (255, 170, 0)),
]
ACCROCHES = [  # (gros mot, sous-titre, voix) — tourne chaque jour
    ("ÉNIGMES", "de plus en plus dures", "Cinq énigmes, de plus en plus dures. Tu en trouves combien ?"),
    ("ÉNIGMES", "la dernière est un piège", "Cinq énigmes. Les premières sont faciles, la dernière beaucoup moins. Tu en trouves combien ?"),
    ("DÉFIS", "pour ton cerveau", "Cinq défis pour ton cerveau, du plus facile au plus dur. C'est parti !"),
    ("ÉNIGMES", "teste ta logique", "Cinq énigmes pour tester ta logique. Mets pause si tu as besoin de plus de temps !"),
]
MID_TTS = "Si tu aimes les énigmes, abonne-toi : il y en a des nouvelles chaque jour. Attention, les deux dernières sont les plus dures !"
OUTRO_TTS = "Alors, tu en as trouvé combien sur cinq ? Dis-le en commentaire, et abonne-toi pour les énigmes de demain !"
CHORDS = [[57, 60, 64], [53, 57, 60], [50, 53, 57], [52, 56, 59]]   # la mineur, fa, ré mineur, mi : ambiance mystère


def evaluer(tokens, valeurs):
    """Calcule une ligne de symboles (partie gauche du =)."""
    expr = ""
    for tk in tokens:
        if tk in SHAPES: expr += str(valeurs[tk])
        elif tk in ("+", "-"): expr += tk
        elif tk in ("×", "x", "*"): expr += "*"
        elif re.fullmatch(r"\d+", tk): expr += tk
        else: raise ValueError(f"symbole inconnu : {tk}")
    return eval(expr, {"__builtins__": {}})


def verifier(c):
    E = c["enigmes"]
    assert len(E) == 5, "il faut exactement 5 énigmes"
    assert len({e["format"] for e in E}) >= 3, "au moins 3 formats différents par vidéo"
    for i, e in enumerate(E, 1):
        f = e["format"]; assert f in FORMATS, f"énigme {i} : format inconnu {f}"
        assert e.get("reponse") and e.get("explication"), f"énigme {i} : réponse/explication manquante"
        assert len(e["explication"]) <= 110, f"énigme {i} : explication trop longue (≤ 110 caractères)"
        assert len(str(e["reponse"])) <= 22, f"énigme {i} : réponse trop longue (≤ 22 caractères)"
        if f == "suite":
            assert e["items"][-1] == "?" and 4 <= len(e["items"]) <= 8, f"énigme {i} : la suite doit finir par ? (4 à 8 cases)"
            assert all(len(x) <= 4 for x in e["items"]), f"énigme {i} : cases de 4 caractères max"
        elif f == "intrus":
            assert len(e["items"]) == 4 and 0 <= e["ans"] <= 3, f"énigme {i} : 4 propositions + ans 0-3"
            assert e["items"][e["ans"]] == e["reponse"], f"énigme {i} : reponse ≠ items[ans]"
            assert all(len(x) <= 13 for x in e["items"]), f"énigme {i} : propositions de 13 caractères max"
        elif f == "symboles":
            L = e["lignes"]; assert 3 <= len(L) <= 4, f"énigme {i} : 3 ou 4 lignes"
            for k, ln in enumerate(L):
                g, d = ln[: ln.index("=")], ln[ln.index("=") + 1:]
                assert len(d) == 1 and len(g) <= 7, f"énigme {i} ligne {k+1} : format"
                v = evaluer(g, e["valeurs"])
                if k < len(L) - 1: assert d[0] != "?" and v == int(d[0]), f"énigme {i} ligne {k+1} : {v} ≠ {d[0]} (erreur de calcul)"
                else: assert d[0] == "?" and v == int(e["reponse"]), f"énigme {i} : la dernière ligne vaut {v}, pas {e['reponse']}"
        else:
            assert len(e["texte"]) <= 210, f"énigme {i} : texte trop long (≤ 210 caractères)"


def tts_items(items):
    return ", ".join(x for x in items if x != "?")


def shape_img(name, size):
    s = 4; S = size * s; im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im); m = S * 0.07; col = SHAPES[name]
    c = S / 2; R = S / 2 - m
    if name == "cercle": d.ellipse([m, m, S - m, S - m], fill=col)
    elif name == "carre": d.rounded_rectangle([m * 1.5, m * 1.5, S - m * 1.5, S - m * 1.5], S * 0.12, fill=col)
    elif name == "triangle": d.polygon([(c, m), (S - m, S - m * 1.6), (m, S - m * 1.6)], fill=col)
    elif name == "losange": d.polygon([(c, m), (S - m * 1.6, c), (c, S - m), (m * 1.6, c)], fill=col)
    elif name == "etoile":
        d.polygon([(c + (R if k % 2 == 0 else R * 0.45) * math.sin(k * math.pi / 5), c - (R if k % 2 == 0 else R * 0.45) * math.cos(k * math.pi / 5) + S * 0.03) for k in range(10)], fill=col)
    elif name == "hexagone": d.polygon([(c + R * math.cos(k * math.pi / 3), c + R * math.sin(k * math.pi / 3)) for k in range(6)], fill=col)
    return im.resize((size, size), Image.LANCZOS)


def wrap2(text, f, maxw):
    """Comme wrap, mais « ? », « ! », « : » ne partent jamais seuls à la ligne."""
    toks = []
    for w in text.split():
        if toks and w in ("?", "!", ":", ";", "»"): toks[-1] += " " + w
        else: toks.append(w)
    lines, cur = [], ""
    for w in toks:
        t = (cur + " " + w).strip()
        if _dummy.textlength(t, font=f) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = w
    lines.append(cur)
    return lines


def fit_font(text, maxw, start, weight="Black", mini=28):
    sz = start
    while sz > mini and _dummy.textlength(text, font=font(sz, weight)) > maxw: sz -= 2
    return font(sz, weight)


class Enigmes:
    def __init__(self, c, work):
        verifier(c)
        self.c, self.E, self.work = c, c["enigmes"], work
        k = datetime.date.fromisoformat(c["date"]).toordinal()
        top, bot, self.A1, self.A2 = THEMES[k % len(THEMES)]
        self.hook = ACCROCHES[(k // len(THEMES)) % len(ACCROCHES)]
        self.BG = self.make_bg(top, bot)

    def make_bg(self, top, bot):
        y = np.linspace(0, 1, H)[:, None]; x = np.linspace(0, 1, W)[None, :]
        g = np.array(top)[None, None, :] * (1 - y[..., None]) + np.array(bot)[None, None, :] * y[..., None]
        for cx, cy, r, col, kk in [(0.1, 0.1, 0.5, self.A1, 0.10), (0.95, 0.82, 0.55, self.A2, 0.13)]:
            dist = np.sqrt(((x - cx) * W / H) ** 2 + (y - cy) ** 2)
            m = np.clip(1 - dist / r, 0, 1) ** 2 * kk
            g = g * (1 - m[..., None]) + np.array(col)[None, None, :] * m[..., None]
        im = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); rng = np.random.default_rng(7)
        for _ in range(34):
            d.text((rng.uniform(0, W), rng.uniform(0, H)), "?", font=font(int(rng.uniform(60, 170)), "Black"),
                   fill=(255, 255, 255, int(rng.uniform(7, 16))), anchor="mm")
        im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(1.2)))
        return im

    # ---------- voix ----------
    def voices(self):
        items = {"intro": self.hook[2], "mid": MID_TTS, "outro": OUTRO_TTS}
        for i, e in enumerate(self.E, 1):
            f = e["format"]
            if e.get("tts"): q = e["tts"]
            elif f == "suite": q = e.get("consigne", "Quel nombre complète la suite ?")
            elif f == "intrus": q = "Trouve l'intrus !"
            elif f == "symboles": q = "Chaque symbole cache un nombre. Combien vaut la dernière ligne ?"
            else: q = e["texte"]
            items[f"q{i}"] = f"Énigme {i}. {q}"
            items[f"a{i}"] = f"Réponse : {e.get('tts_reponse', e['reponse'])} !"   # la voix ne lit que le résultat
        self.DUR = {k: say(t, os.path.join(self.work, f"{k}.wav")) for k, t in items.items()}

    # ---------- timings ----------
    def timing(self, i):
        qd, ad = self.DUR[f"q{i}"], self.DUR[f"a{i}"]
        t_cd = max(0.25 + qd + 0.3, 1.6); t_rev = t_cd + TEMPS[i - 1]; t_ans = t_rev + 0.25
        return dict(t_voice=0.25, t_cd=t_cd, t_rev=t_rev, t_ans=t_ans, n=TEMPS[i - 1], end=round((t_ans + ad + 0.8) * FPS) / FPS)

    def timeline(self):
        r = lambda x: round(x * FPS) / FPS
        tl = [("intro", r(0.2 + self.DUR["intro"] + 0.6))]
        for i in range(1, 6):
            tl.append((f"q{i}", self.timing(i)["end"]))
            if i == 3: tl.append(("mid", r(0.3 + self.DUR["mid"] + 0.6)))
        tl.append(("outro", r(0.3 + self.DUR["outro"] + 1.6)))
        return tl

    # ---------- éléments ----------
    def header(self, im, i):
        d = ImageDraw.Draw(im)
        d.text((CX0, 215), "ÉNIGME", font=font(40, "Bold"), fill=SOFT2, anchor="lm")
        qw = d.textlength("ÉNIGME ", font=font(40, "Bold"))
        d.text((CX0 + qw, 213), str(i), font=font(62, "Black"), fill=WHITE, anchor="lm")
        nw = d.textlength(str(i), font=font(62, "Black"))
        d.text((CX0 + qw + nw + 6, 220), "/5", font=font(40, "Bold"), fill=SOFT2, anchor="lm")
        lv = NIV_NOM[i - 1]; fl = font(36, "Black"); tw = d.textlength(lv, font=fl)
        pill, _ = rr_image(int(tw + 60), 64, 32, NIV[i - 1]); im.alpha_composite(pill, (int(CX0 + CW - tw - 60), 183))
        d.text((CX0 + CW - (tw + 60) / 2, 216), lv, font=fl, fill=DARK, anchor="mm")
        seg = (CW - 4 * 12) / 5
        for k in range(5):
            x = CX0 + k * (seg + 12)
            d.rounded_rectangle([x, 285, x + seg, 299], 7, fill=NIV[k] if k < i else (255, 255, 255, 40))

    def label(self, im, f):
        txt = FORMATS[f]; fo = font(34, "Black"); tw = _dummy.textlength(txt, font=fo); w = int(tw + 70)
        pill, p = rr_image(w, 66, 33, CARD2, border=self.A2, bw=3)
        ImageDraw.Draw(pill).text((p + w / 2, p + 35), txt, font=fo, fill=self.A2, anchor="mm")
        im.alpha_composite(pill, (int(CX - w / 2 - p), 335 - p))

    def timer(self, im, t_in, total, cy):
        s = 2; R = 80; size = (R + 14) * 2
        t = Image.new("RGBA", (size * s, size * s), (0, 0, 0, 0)); d = ImageDraw.Draw(t); c = size * s / 2
        d.ellipse([c - R * s, c - R * s, c + R * s, c + R * s], fill=(12, 18, 26, 235), outline=(255, 255, 255, 45), width=10 * s)
        frac = max(0.0, 1 - t_in / total); n = max(1, int(math.ceil(total - t_in - 1e-6)))
        col = GREEN if n > 3 else YELLOW if n > 1 else (255, 80, 80)
        if frac > 0: d.arc([c - R * s, c - R * s, c + R * s, c + R * s], -90, -90 + 360 * frac, fill=col, width=12 * s)
        t = t.resize((size, size), Image.LANCZOS); dd = ImageDraw.Draw(t)
        sc = 1 + 0.25 * max(0, 1 - (t_in % 1.0) / 0.25)
        dd.text((size / 2, size / 2 + 3), str(n), font=font(int(74 * sc), "Black"), fill=WHITE, anchor="mm")
        im.alpha_composite(t, (CX - size // 2, int(cy) - size // 2))
        ImageDraw.Draw(im).text((CX, int(cy) + 125), "À toi de jouer !", font=font(40, "Bold"), fill=SOFT2, anchor="mm")

    def assets(self, i):
        e = self.E[i - 1]; f = e["format"]; a = {}
        rep = str(e["reponse"])
        # bandeau réponse + explication
        fo = fit_font(f"RÉPONSE : {rep}", 760, 60); tw = _dummy.textlength(f"RÉPONSE : {rep}", font=fo); w = int(min(CW, tw + 90))
        pill, p = rr_image(w, 112, 56, self.A1, shadow=True)
        ImageDraw.Draw(pill).text((p + w / 2, p + 58), f"RÉPONSE : {rep}", font=fo, fill=DARK, anchor="mm")
        a["rep"], a["rep_p"] = pill, p
        fe = font(46, "SemiBold"); lines = wrap2(e["explication"], fe, CW - 40)
        if len(lines) > 3: fe = font(40, "SemiBold"); lines = wrap2(e["explication"], fe, CW - 30)
        a["expl"] = (fe, lines)
        if f == "suite":
            it = e["items"]; per = len(it) if len(it) <= 5 else math.ceil(len(it) / 2); gap = 20
            s = int(min(160, (CW - gap * (per - 1)) / per)); a["tile"] = s; a["per"] = per
            for k, x in enumerate(it):
                if x == "?":
                    for st, fill, txt, col in (("q", self.A1, "?", DARK), ("ok", GREEN, rep, WHITE)):
                        im, pp = rr_image(s, s, 30, fill, shadow=True)
                        ImageDraw.Draw(im).text((pp + s / 2, pp + s / 2 + 3), txt, font=fit_font(txt, s * 0.8, int(s * 0.5)), fill=col, anchor="mm")
                        a[("t", k, st)] = (im, pp)
                else:
                    im, pp = rr_image(s, s, 30, CARD2, border=(70, 90, 105), bw=3, shadow=True)
                    ImageDraw.Draw(im).text((pp + s / 2, pp + s / 2 + 3), x, font=fit_font(x, s * 0.78, int(s * 0.45)), fill=WHITE, anchor="mm")
                    a[("t", k, "n")] = (im, pp)
        elif f == "intrus":
            cw, ch = 430, 190
            for k, x in enumerate(e["items"]):
                for st in ("n", "ok", "dim"):
                    if st == "ok": im, pp = rr_image(cw, ch, 34, self.A1, shadow=True); col = DARK
                    elif st == "dim": im, pp = rr_image(cw, ch, 34, (18, 24, 30), border=(45, 55, 65), bw=3); col = (110, 120, 130)
                    else: im, pp = rr_image(cw, ch, 34, CARD2, border=(70, 90, 105), bw=3, shadow=True); col = WHITE
                    ImageDraw.Draw(im).text((pp + cw / 2, pp + ch / 2 + 2), x, font=fit_font(x, cw - 50, 58), fill=col, anchor="mm")
                    a[("c", k, st)] = (im, pp)
        elif f == "symboles":
            a["shape"] = {n: shape_img(n, 118) for n in SHAPES}
            for st, fill, txt, col in (("q", self.A1, "?", DARK), ("ok", GREEN, rep, WHITE)):
                ww = max(120, int(_dummy.textlength(txt, font=font(76, "Black")) + 50))
                im, pp = rr_image(ww, 120, 30, fill, shadow=True)
                ImageDraw.Draw(im).text((pp + ww / 2, pp + 63), txt, font=font(76, "Black"), fill=col, anchor="mm")
                a[("s", st)] = (im, pp, ww)
        else:
            ft = font(56, "Bold"); lines = wrap2(e["texte"], ft, CW - 110)
            while len(lines) > 7 and ft.size > 40: ft = font(ft.size - 4, "Bold"); lines = wrap2(e["texte"], ft, CW - 100)
            lh = ft.size * 1.28; ch = int(max(360, lh * len(lines) + 120))
            im, pp = rr_image(CW, ch, 40, WHITE, shadow=True); d = ImageDraw.Draw(im)
            y0 = pp + ch / 2 - lh * (len(lines) - 1) / 2
            for k, ln in enumerate(lines): d.text((pp + CW / 2, y0 + k * lh), ln, font=ft, fill=DARK, anchor="mm")
            a["card"] = (im, pp, ch)
        if f == "suite": nr = math.ceil(len(e["items"]) / a["per"]); bas = 650 + nr * a["tile"] + (nr - 1) * 30
        elif f == "intrus": bas = 500 + 2 * 190 + 24
        elif f == "symboles": bas = 440 + (len(e["lignes"]) - 1) * 165 + 120
        else: bas = 440 + a["card"][2]
        a["zone"] = min(bas + 90, 1180)
        return a

    # ---------- dessin d'une énigme ----------
    def draw_q(self, i, t, A, T):
        e = self.E[i - 1]; f = e["format"]; im = self.BG.copy(); self.header(im, i); self.label(im, f)
        d = ImageDraw.Draw(im); rev = t >= T["t_rev"]; rp = t - T["t_rev"]
        pop = lambda: 1 + 0.1 * math.sin(min(rp / 0.35, 1) * math.pi)
        if f == "suite":
            y_c = 520; fc = font(48, "Bold")
            for k, ln in enumerate(wrap2(e.get("consigne", "Quel nombre complète la suite ?"), fc, CW)):
                d.text((CX, y_c + k * 62), ln, font=fc, fill=WHITE, anchor="mm")
            it = e["items"]; s, per = A["tile"], A["per"]; gap = 20
            for k, x in enumerate(it):
                row, col = divmod(k, per); nrow = min(per, len(it) - row * per)
                x0 = CX - (nrow * s + (nrow - 1) * gap) / 2 + col * (s + gap); y0 = 650 + row * (s + 30)
                ts = 0.2 + 0.12 * k
                if t < ts: continue
                lp = (t - ts) / 0.3
                if x == "?":
                    img, pp = A[("t", k, "ok" if rev else "q")]
                    sc = pop() if rev else 1 + 0.05 * math.sin(t * 2 * math.pi / 0.9)
                    paste(im, img, x0 - pp, y0 - pp, alpha=min(1, lp * 1.5), scale=sc * (0.7 + 0.3 * ease_back(lp)))
                else:
                    img, pp = A[("t", k, "n")]
                    paste(im, img, x0 - pp, y0 - pp + (1 - ease_out(lp)) * 40, alpha=min(1, lp * 1.5))
        elif f == "intrus":
            cw, ch = 430, 190
            for k in range(4):
                row, col = divmod(k, 2); x0 = CX0 + col * (cw + 20); y0 = 500 + row * (ch + 24)
                ts = 0.3 + 0.15 * k
                if t < ts: continue
                lp = (t - ts) / 0.3
                st = ("ok" if k == e["ans"] else "dim") if rev else "n"
                img, pp = A[("c", k, st)]
                paste(im, img, x0 - pp + (1 - ease_out(lp)) * (300 if col else -300), y0 - pp, alpha=min(1, lp * 1.5),
                      scale=pop() if (rev and k == e["ans"]) else 1.0)
        elif f == "symboles":
            sh = A["shape"]; L = e["lignes"]
            for r, ln in enumerate(L):
                ts = 0.2 + 0.5 * r
                if t < ts: continue
                lp = (t - ts) / 0.3; y = 440 + r * 165
                widths = []
                for tk in ln:
                    if tk in SHAPES: widths.append(118)
                    elif tk == "?": widths.append(A[("s", "ok" if rev else "q")][2])
                    else: widths.append(int(_dummy.textlength(tk, font=font(80, "Black")) + 34))
                x = CX - sum(widths) / 2
                for tk, w_ in zip(ln, widths):
                    a_ = min(1, lp * 1.5); dx = (1 - ease_out(lp)) * 60
                    if tk in SHAPES: paste(im, sh[tk], x + dx, y, alpha=a_)
                    elif tk == "?":
                        img, pp, _ = A[("s", "ok" if rev else "q")]
                        paste(im, img, x - pp + dx, y - pp, alpha=a_, scale=pop() if rev else 1 + 0.05 * math.sin(t * 2 * math.pi / 0.9))
                    else:
                        col = SOFT2 if tk in "+-×=" else WHITE
                        lay = Image.new("RGBA", (w_ + 20, 140), (0, 0, 0, 0))
                        ImageDraw.Draw(lay).text(((w_ + 20) / 2, 70), tk, font=font(80, "Black"), fill=col, anchor="mm")
                        paste(im, lay, x - 10 + dx, y - 11, alpha=a_)
                    x += w_
        else:
            img, pp, ch = A["card"]
            paste(im, img, CX0 - pp, 440 - pp + (1 - ease_out(t / 0.3)) * 60, alpha=min(1, t / 0.2), scale=0.92 + 0.08 * ease_back(t / 0.35))
        # compte à rebours puis réponse
        Z = A["zone"]
        if T["t_cd"] <= t < T["t_rev"]: self.timer(im, t - T["t_cd"], T["n"], Z + 105)
        elif rev:
            img, pp = A["rep"], A["rep_p"]; lp = (rp - 0.05) / 0.35
            if lp > 0: paste(im, img, CX - img.width / 2, Z + 10 - pp, alpha=min(1, lp * 2), scale=0.8 + 0.2 * ease_back(lp))
            fe, lines = A["expl"]; lp2 = (rp - 0.5) / 0.4
            if lp2 > 0:
                lay = Image.new("RGBA", (W, 240), (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
                for k, ln in enumerate(lines): dl.text((CX, 40 + k * fe.size * 1.24), ln, font=fe, fill=WHITE, anchor="mm")
                paste(im, lay, 0, Z + 128 + (1 - ease_out(lp2)) * 30, alpha=min(1, lp2 * 1.5))
            if rp < 0.15: im.alpha_composite(Image.new("RGBA", (W, H), self.A1 + (int(60 * (1 - rp / 0.15)),)))
        return im

    # ---------- intro / milieu / fin ----------
    def draw_intro(self, t):
        im = self.BG.copy(); d = ImageDraw.Draw(im)
        d.text((CX, 320), "ENIGMATIK", font=font(64, "Black"), fill=self.A1, anchor="mm")
        big = Image.new("RGBA", (1000, 420), (0, 0, 0, 0)); bd = ImageDraw.Draw(big)
        bd.text((500, 140), "5", font=font(260, "Black"), fill=self.A1, anchor="mm")
        bd.text((500, 330), self.hook[0], font=fit_font(self.hook[0], 860, 120), fill=WHITE, anchor="mm")
        paste(im, big, CX - 500, 420, scale=max(0.05, 0.7 + 0.3 * ease_back(t / 0.45)) * (1 + 0.025 * math.sin(t * 2 * math.pi / 1.3)))
        d.text((CX, 905), self.hook[1], font=font(54, "SemiBold"), fill=SOFT2, anchor="mm")
        bw, gap = 150, 18; x0 = CX - (5 * bw + 4 * gap) // 2
        for k in range(5):
            h = 70 + k * 55; p = ease_back((t - 0.3 - 0.12 * k) / 0.35); hh = int(h * max(0, min(p, 1.2)))
            if hh > 4:
                bar, _ = rr_image(bw, hh, 20, NIV[k]); im.alpha_composite(bar, (x0 + k * (bw + gap), 1300 - hh))
            d.text((x0 + k * (bw + gap) + bw // 2, 1345), str(k + 1), font=font(40, "Black"), fill=NIV[k], anchor="mm")
        d.text((CX, 1450), "TU EN TROUVES COMBIEN ?", font=font(56, "Black"), fill=WHITE, anchor="mm")
        return im

    def draw_mid(self, t):
        im = self.BG.copy(); d = ImageDraw.Draw(im); p = ease_back(t / 0.4)
        big = Image.new("RGBA", (1000, 230), (0, 0, 0, 0)); bd = ImageDraw.Draw(big)
        bd.text((500, 70), "PLUS QUE", font=font(72, "Black"), fill=WHITE, anchor="mm")
        bd.text((500, 170), "2 ÉNIGMES", font=font(116, "Black"), fill=self.A1, anchor="mm")
        paste(im, big, CX - 500, 330, scale=max(0.05, 0.6 + 0.4 * p))
        seg = (CW - 4 * 12) / 5
        for k in range(5):
            x = CX0 + k * (seg + 12); d.rounded_rectangle([x, 650, x + seg, 668], 9, fill=NIV[k] if k < 3 else (255, 255, 255, 40))
        if t > 0.9:
            lp = (t - 0.9) / 0.35
            d.text((CX, 880), "Tu aimes les énigmes ?", font=font(62, "Black"), fill=WHITE, anchor="mm")
            btn, bp = cta_button("+ ABONNE-TOI", 700, 130, 60)
            paste(im, btn, CX - 350 - bp, 970 - bp, alpha=min(1, lp * 2), scale=(0.8 + 0.2 * ease_back(lp)) * (1 + 0.05 * math.sin((t - 0.9) * 2 * math.pi / 0.9)))
            d.text((CX, 1170), "Une nouvelle énigme chaque jour", font=font(46, "SemiBold"), fill=SOFT2, anchor="mm")
        if t > 3.8:
            lp = (t - 3.8) / 0.35
            pill, pp = rr_image(820, 96, 48, NIV[4])
            ImageDraw.Draw(pill).text((pp + 410, pp + 50), "Les plus dures arrivent...", font=font(46, "Black"), fill=WHITE, anchor="mm")
            paste(im, pill, CX - 410 - pp, 1310 - pp, alpha=min(1, lp * 2), scale=0.85 + 0.15 * ease_back(lp))
        return im

    def draw_outro(self, t):
        im = self.BG.copy(); d = ImageDraw.Draw(im); p = ease_back(t / 0.4)
        big = Image.new("RGBA", (1000, 200), (0, 0, 0, 0))
        ImageDraw.Draw(big).text((500, 100), "C'EST FINI !", font=font(118, "Black"), fill=self.A1, anchor="mm")
        paste(im, big, CX - 500, 300, scale=max(0.05, 0.6 + 0.4 * p))
        d.text((CX, 560), "Ton score ?", font=font(76, "Black"), fill=WHITE, anchor="mm")
        rows = [("5/5", "Génie", NIV[4]), ("4/5", "Cerveau en feu", NIV[3]), ("2-3", "Pas mal", NIV[2]), ("0-1", "Revanche demain", NIV[0])]
        for k, (s, n, c) in enumerate(rows):
            ts = 0.35 + 0.15 * k
            if t < ts: continue
            lp = (t - ts) / 0.3; card, cp = rr_image(780, 112, 30, CARD2, border=c, bw=4); dr = ImageDraw.Draw(card)
            dr.text((cp + 50, cp + 58), s, font=font(52, "Black"), fill=c, anchor="lm")
            dr.text((cp + 730, cp + 58), n, font=font(48, "Bold"), fill=WHITE, anchor="rm")
            paste(im, card, CX - 390 - cp + (1 - ease_out(lp)) * 300, 680 + k * 140 - cp, alpha=min(1, lp * 1.5))
        if t > 1.2:
            lp = (t - 1.2) / 0.35
            d.text((CX, 1300), "Dis-le en commentaire !", font=font(60, "Black"), fill=WHITE, anchor="mm")
            btn, bp = cta_button("+ ABONNE-TOI", 640, 110, 52)
            paste(im, btn, CX - 320 - bp, 1380 - bp, alpha=min(1, lp * 2), scale=0.8 + 0.2 * ease_back(lp))
        return im

    def frame_fn(self, name):
        if name == "intro": return self.draw_intro
        if name == "mid": return self.draw_mid
        if name == "outro": return self.draw_outro
        i = int(name[1:]); A = self.assets(i); T = self.timing(i)
        return lambda t: self.draw_q(i, t, A, T)

    def check_frames(self):
        out = [("intro", 2.5), ("mid", 4.6), ("outro", 3.0)]
        for i in range(1, 6):
            T = self.timing(i); out += [(f"q{i}", T["t_cd"] + 1.3), (f"q{i}", T["t_rev"] + 1.5)]
        return out

    # ---------- audio ----------
    def audio(self, tl, wav):
        total = sum(d for _, d in tl); tr = Track(total); t0 = 0.0
        for name, dur in tl:
            if name == "intro": tr.add(tr.voice, load(f"{self.work}/intro.wav"), t0 + 0.2)
            elif name in ("mid", "outro"):
                tr.add(tr.sfx, WHOOSH, t0, 0.25); tr.add(tr.voice, load(f"{self.work}/{name}.wav"), t0 + 0.3)
                if name == "outro": tr.add(tr.sfx, DING, t0 + 1.2, 0.25)
            else:
                i = int(name[1:]); T = self.timing(i)
                tr.add(tr.sfx, WHOOSH, t0, 0.25); tr.add(tr.voice, load(f"{self.work}/q{i}.wav"), t0 + T["t_voice"])
                for k in range(T["n"]):
                    tr.add(tr.sfx, TICK if k % 2 == 0 else TOCK, t0 + T["t_cd"] + k, 0.45 if T["n"] - k > 2 else 0.7)
                tr.add(tr.sfx, DING, t0 + T["t_rev"], 0.45); tr.add(tr.voice, load(f"{self.work}/a{i}.wav"), t0 + T["t_ans"])
            t0 += dur
        mixdown(tr, wav, chords=CHORDS, bpm=92)
