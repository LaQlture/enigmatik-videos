"""Vidéo « Énigmes » avec la voix ElevenLabs (Tomas).

Ce que la voix lit, dans l'ordre (une seule prise ElevenLabs par vidéo) :
  accroche (« Seulement 1 % des gens… »), puis pour chaque énigme « Énigme N. <question> » et « Réponse : … ! »,
  entre l'énigme 3 et l'énigme 4 la phrase « milieu » (« N'hésite pas à t'abonner pour plus de quiz ! »),
  et à la fin la phrase « fin » (score en commentaire pour le classement).
  Jamais les propositions, les cases, les symboles ni l'explication.

Champs en plus du format de enigme.py :
  "accroche": {"texte": "..."}   "milieu": {"texte": "..."}   "fin": {"texte": "..."}   (+ "tts" si lu autrement)
  "audio": "voix/<date>_enigmes.mp3"      "mots": "voix/<date>_enigmes_mots.json" (transcription words.json)
Sans "audio", la vidéo est fabriquée SANS voix (aperçu pour valider les énigmes avant de payer la voix).
Texte à faire lire : python3 pipeline/enigme_audio.py contenu/<date>_enigmes.json --texte
Bruitages : « volume_bruitages » (0.3 par défaut), transitions encore plus discrètes.
"""
import json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from enigme import Enigmes, CHORDS, wrap2, CX, CW
from enquete_audio import _tokens, point_calme, charger_mots

MUET = {"intro": 2.6, "mid": 2.6, "outro": 2.6}      # durée des écrans sans voix (s)


def question(e, i):
    f = e["format"]
    if e.get("tts"): q = e["tts"]
    elif f == "suite": q = e.get("consigne", "Quel nombre complète la suite ?")
    elif f == "intrus": q = "Trouve l'intrus !"
    elif f == "symboles": q = "Chaque symbole cache un nombre. Combien vaut la dernière ligne ?"
    else: q = e["texte"]
    return f"Énigme {i}. {q}"


def lignes(c):
    """Toutes les phrases lues, dans l'ordre : (clé, texte)."""
    out = [("intro", c["accroche"].get("tts", c["accroche"]["texte"]))] if c.get("accroche") else []
    for i, e in enumerate(c["enigmes"], 1):
        out += [(f"q{i}", question(e, i)), (f"a{i}", f"Réponse : {e.get('tts_reponse', e['reponse'])} !")]
        if i == 3 and c.get("milieu"): out.append(("mid", c["milieu"].get("tts", c["milieu"]["texte"])))
    if c.get("fin"): out.append(("outro", c["fin"].get("tts", c["fin"]["texte"])))
    return out


def texte_a_lire(c):
    return "\n\n".join(t for _, t in lignes(c))


class EnigmesAudio(Enigmes):
    def __init__(self, c, work, base):
        super().__init__(c, work); self.base = base; self.apercu = not c.get("audio")

    def voices(self):
        c, w = self.c, self.work
        self.DUR = dict(MUET)
        if self.apercu:                                   # aperçu sans voix : durées estimées
            for k, t in lignes(c):
                if k[0] in "qa": self.DUR[k] = round(0.9 + len(t) / 15, 2) if k[0] == "q" else 1.7
            return
        src = os.path.join(self.base, c["audio"]); mots = charger_mots(os.path.join(self.base, c["mots"]))
        full = load(src); total = len(full) / SR
        seq = [(tk, m["start"]) for m in mots for tk in _tokens(m["text"])[:1]]
        keys = [k for k, _ in lignes(c)]; st = {}
        rep = {"enigme": [t for tk, t in seq if tk == "enigme"], "reponse": [t for tk, t in seq if tk == "reponse"]}
        if len(rep["enigme"]) != 5 or len(rep["reponse"]) != 5:
            raise SystemExit(f"transcription inattendue : {len(rep['enigme'])} « énigme » et {len(rep['reponse'])} « réponse » (5 attendus)")
        for i in range(5): st[f"q{i+1}"] = rep["enigme"][i]; st[f"a{i+1}"] = rep["reponse"][i]
        if "intro" in keys: st["intro"] = 0.0
        if "mid" in keys:                                  # 1er mot de la phrase du milieu, après la réponse 3
            mot1 = _tokens(dict(lignes(c))["mid"])[0]
            st["mid"] = next(t for tk, t in seq if tk == mot1 and st["a3"] < t < st["q4"])
        if "outro" in keys:                                # 1er mot de la phrase de fin, après la réponse 5
            mot1 = _tokens(dict(lignes(c))["outro"])[0]
            st["outro"] = next(t for tk, t in seq if tk == mot1 and t > st["a5"] + 0.3)
        for a, b in zip(keys, keys[1:]): assert st[a] < st[b], f"ordre inattendu entre {a} et {b}"
        cut = {k: point_calme(full, st[k]) for k in keys}
        for j, k in enumerate(keys):
            a = cut[k]; b = cut[keys[j + 1]] if j + 1 < len(keys) else total
            seg = full[int(a * SR): int(b * SR)]
            env = np.convolve(np.abs(seg), np.ones(441) / 441, mode="same")          # silences de début/fin retirés
            nz = np.nonzero(env > 0.03 * env.max())[0]
            if len(nz): seg = seg[max(0, nz[0] - int(0.04 * SR)): min(len(seg), nz[-1] + int(0.15 * SR))]
            p = f"{w}/{k}.wav"
            open(p + ".f32", "wb").write(seg.astype(np.float32).tobytes())
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", p + ".f32", p], check=True)
            os.remove(p + ".f32"); d = round(len(seg) / SR, 3)
            self.DUR[k] = max(MUET[k], d + 0.3) if k in MUET else d

    def draw_intro(self, t):
        acc = self.c.get("accroche")
        if not acc: return super().draw_intro(t)
        h = self.hook; self.hook = (h[0], "", h[2])
        im = super().draw_intro(t); self.hook = h
        for sz in (58, 52, 46, 40):                         # tient toujours sur 2 lignes
            lines = wrap2(acc["texte"].upper(), font(sz, "Black"), CW)
            if len(lines) <= 2: break
        lay = Image.new("RGBA", (W, 200), (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
        for k, ln in enumerate(lines):
            dl.text((CX, 50 + k * int(sz * 1.24)), ln, font=font(sz, "Black"), fill=WHITE, anchor="mm", stroke_width=6, stroke_fill=(8, 8, 18))
        paste(im, lay, 0, 830, alpha=min(1, t * 4), scale=1.06 - 0.06 * ease_out(t / 0.3))
        return im

    def audio(self, tl, wav):
        total = sum(d for _, d in tl); tr = Track(total); t0 = 0.0; w = self.work
        voix = lambda k: (not self.apercu) and os.path.exists(f"{w}/{k}.wav")
        WH = 0.1                                           # transitions (whoosh) très discrètes
        for name, dur in tl:
            if name in ("intro", "mid", "outro"):
                tr.add(tr.sfx, WHOOSH, t0, WH)
                if voix(name): tr.add(tr.voice, load(f"{w}/{name}.wav"), t0 + 0.2)
                if name == "outro": tr.add(tr.sfx, DING, t0 + 1.2, 0.25)
            else:
                i = int(name[1:]); T = self.timing(i)
                tr.add(tr.sfx, WHOOSH, t0, WH)
                if voix(f"q{i}"): tr.add(tr.voice, load(f"{w}/q{i}.wav"), t0 + T["t_voice"])
                for k in range(T["n"]):
                    tr.add(tr.sfx, TICK if k % 2 == 0 else TOCK, t0 + T["t_cd"] + k, 0.45 if T["n"] - k > 2 else 0.7)
                tr.add(tr.sfx, DING, t0 + T["t_rev"], 0.45)
                if voix(f"a{i}"): tr.add(tr.voice, load(f"{w}/a{i}.wav"), t0 + T["t_ans"])
            t0 += dur
        tr.sfx *= self.c.get("volume_bruitages", 0.3)
        if self.apercu: tr.voice[:100] = 1e-4               # piste voix vide (évite une division par zéro)
        mixdown(tr, wav, chords=CHORDS, bpm=92)


if __name__ == "__main__" and "--texte" in sys.argv:
    print(texte_a_lire(json.load(open(sys.argv[1]))))
