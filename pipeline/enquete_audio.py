"""Vidéo « Enquête » montée sur UNE voix off externe (ElevenLabs, voix Tomas).

Le contenu JSON garde la structure de enquete.py, avec en plus :
  "audio": "chemin/vers/voix.mp3"            (relatif au JSON)
  "mots":  "chemin/vers/mots.json"           (transcription mot à mot : [{"text", "start", "end"}, ...])
  "intro" de chaque suspect : la phrase du narrateur avant sa réplique (« Le majordome, d'abord : »)
  "carnet" : la phrase lue pendant l'écran des indices ; "panne" : [i_debut, i_fin] des phrases du récit
  où la lumière est coupée.
La voix est découpée phrase par phrase grâce aux horodatages, puis chaque morceau est calé sur sa scène.
"""
import json, math, os, re, subprocess, unicodedata
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


E.perso = perso
_icon_base = E.icon


def icon(kind, size=110):
    if kind not in ("courant", "cadre"): return _icon_base(kind, size)
    k = size / 100 * E.S; im = Image.new("RGBA", (int(100 * k), int(100 * k)), (0, 0, 0, 0)); d = ImageDraw.Draw(im); s = lambda *v: [x * k for x in v]
    if kind == "courant":                                   # ampoule éteinte barrée
        d.ellipse(s(26, 8, 74, 58), fill=(120, 124, 150)); d.rectangle(s(38, 52, 62, 72), fill=(120, 124, 150))
        d.rectangle(s(36, 72, 64, 86), fill=(80, 84, 104)); d.rectangle(s(40, 86, 60, 92), fill=(80, 84, 104))
        d.line(s(14, 90, 88, 10), fill=(240, 60, 60), width=int(9 * k))
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


class EnqueteAudio(Enquete):
    GAP_RECIT = 0.12

    def __init__(self, c, work, base):
        super().__init__(c, work); self.base = base
        if not c.get("pluie"): self.rnd = []                # pas de pluie animée (effet grésillant)
        if not c.get("fenetre_cassee"):                    # fenêtre intacte (sinon faux indice)
            wx, wy, ww, wh = WIN; self.bars = Image.new("RGBA", (SCN_W, SCN_H), (0, 0, 0, 0)); bd = ImageDraw.Draw(self.bars)
            bd.rectangle([wx + ww / 2 - 6, wy, wx + ww / 2 + 6, wy + wh], fill=(120, 84, 60))
            bd.rectangle([wx, wy + wh / 2 - 6, wx + ww, wy + wh / 2 + 6], fill=(120, 84, 60))

    def units(self):
        c = self.c; u = [("hook", c["accroche"])] + [(f"r{i}", t) for i, t in enumerate(c["recit"])]
        for i, s in enumerate(self.sus): u += [(f"n{i}", s["intro"]), (f"s{i}", s["dit"])]
        return u + [("carnet", c["carnet"]), ("fin", c["fin"])]

    def voices(self):
        c, w = self.c, self.work
        src = os.path.join(self.base, c["audio"]); mots = json.load(open(os.path.join(self.base, c["mots"])))
        units = self.units(); st = aligner(units, mots); total = mots[-1]["end"] + 0.25
        full = load(src); D = {}
        fr = int(0.02 * SR)
        def calme(t):
            """Instant le plus silencieux dans [t-0.5 s, t+0.05 s] : la coupe ne tombe jamais au milieu d'un mot."""
            if t <= 0.1: return 0.0
            a0 = max(0, int((t - 0.5) * SR)); seg = full[a0: int((t + 0.05) * SR)]
            n = len(seg) // fr; e = [np.sqrt(np.mean(seg[i * fr:(i + 1) * fr] ** 2)) for i in range(n)]
            i = int(np.argmin(e)); return (a0 + i * fr + fr // 2) / SR
        cut = {key: calme(st[key]) for key, _ in units}
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

    def scene(self, t, cam=(0.5, 0.5, 1.0), steps=0.0, ring=None, insp=None, flash_off=0.6, storm=True, dark=0.0, lamp=True):
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
        dk = self.dark_at(t)
        self.put_scene(im, self.scene(t + 2.0, cam, 0, ring, ins, dark=dk))
        if dk > 0.5 and i < self.c["panne"][1]:
            lab = Image.new("RGBA", (W, 120), (0, 0, 0, 0))
            ImageDraw.Draw(lab).text((CX, 60), "PANNE DE COURANT  22 h → minuit", font=fit_font("PANNE DE COURANT  22 h → minuit", CW, 50), fill=ACC, anchor="mm", stroke_width=5, stroke_fill=(8, 8, 18))
            paste(im, lab, 0, 950, alpha=min(1, (t - st[self.c["panne"][0]] - self.DUR[f"r{self.c['panne'][0]}"] * 0.45) * 3))
        self.subtitle(im, self.c["recit"][i], (t - st[i]) / 0.3)
        return im

    def draw_hook(self, t):
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
            if name in ("hook", "recit"):
                off, shift = (0.25, 0.0) if name == "hook" else (0.6, 2.0)
                for ft in flash_times(dur + shift, off):
                    if ft - shift >= 0: tr.add(tr.sfx, THUNDER, t0 + ft - shift + 0.15, 0.4)
            t0 += dur
        if self.c.get("pluie"): tr.sfx += colored(tr.N, 800, 9000) * 0.035   # bruit de pluie de fond
        tr.sfx *= self.c.get("volume_bruitages", 0.45)      # bruitages discrets sous la voix
        mixdown(tr, wav, music_gain=0.35, soft=True, chords=E.CHORDS, bpm=78)
