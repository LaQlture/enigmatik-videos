"""Vidéo « Énigmes » avec la voix ElevenLabs (Tomas).

Règle de la chaîne : la voix lit SEULEMENT « Énigme N. <question> » puis « Réponse : … ! ».
Pas d'intro, de milieu ni de conclusion parlés (ces écrans restent, en texte + musique).

Le contenu JSON garde le format de enigme.py, avec en plus :
  "audio": "voix/<date>_enigmes.mp3"       une seule prise ElevenLabs : les 10 phrases dans l'ordre
  "mots":  "voix/<date>_enigmes_mots.json" transcription mot à mot ([{"text", "start", "end"}, ...])
Texte à faire lire : python3 pipeline/enigme_audio.py contenu/<date>_enigmes.json --texte
"""
import json, os, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from enigme import Enigmes, CHORDS
from enquete_audio import _tokens, point_calme, charger_mots

MUET = {"intro": 1.8, "mid": 2.6, "outro": 2.6}      # durée des écrans sans voix (s)


def lignes(c):
    """Les 10 phrases lues, dans l'ordre : (clé, texte)."""
    out = []
    for i, e in enumerate(c["enigmes"], 1):
        f = e["format"]
        if e.get("tts"): q = e["tts"]
        elif f == "suite": q = e.get("consigne", "Quel nombre complète la suite ?")
        elif f == "intrus": q = "Trouve l'intrus !"
        elif f == "symboles": q = "Chaque symbole cache un nombre. Combien vaut la dernière ligne ?"
        else: q = e["texte"]
        out += [(f"q{i}", f"Énigme {i}. {q}"), (f"a{i}", f"Réponse : {e.get('tts_reponse', e['reponse'])} !")]
    return out


def texte_a_lire(c):
    return "\n\n".join(t for _, t in lignes(c))


class EnigmesAudio(Enigmes):
    def __init__(self, c, work, base):
        super().__init__(c, work); self.base = base

    def voices(self):
        c, w = self.c, self.work
        src = os.path.join(self.base, c["audio"]); mots = charger_mots(os.path.join(self.base, c["mots"]))
        full = load(src); total = len(full) / SR
        # repères : le i-ème « énigme » ouvre la question i, le i-ème « réponse » ouvre la réponse i
        rep = {"enigme": [], "reponse": []}
        for m in mots:
            tk = _tokens(m["text"])
            if tk and tk[0] in rep: rep[tk[0]].append(m["start"])
        if len(rep["enigme"]) != 5 or len(rep["reponse"]) != 5:
            raise SystemExit(f"transcription inattendue : {len(rep['enigme'])} « énigme » et {len(rep['reponse'])} « réponse » (5 attendus)")
        st = {}
        for i in range(5): st[f"q{i+1}"] = rep["enigme"][i]; st[f"a{i+1}"] = rep["reponse"][i]
        keys = [k for k, _ in lignes(c)]
        for a, b in zip(keys, keys[1:]): assert st[a] < st[b], f"ordre inattendu entre {a} et {b}"
        cut = {k: point_calme(full, st[k]) for k in keys}
        self.DUR = dict(MUET)
        for j, k in enumerate(keys):
            a = cut[k]; b = cut[keys[j + 1]] if j + 1 < len(keys) else total
            seg = full[int(a * SR): int(b * SR)]
            env = np.convolve(np.abs(seg), np.ones(441) / 441, mode="same")          # silence de fin retiré
            nz = np.nonzero(env > 0.03 * env.max())[0]
            if len(nz): seg = seg[: min(len(seg), nz[-1] + int(0.15 * SR))]
            p = f"{w}/{k}.wav"
            open(p + ".f32", "wb").write(seg.astype(np.float32).tobytes())
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", p + ".f32", p], check=True)
            os.remove(p + ".f32"); self.DUR[k] = round(len(seg) / SR, 3)

    def audio(self, tl, wav):
        total = sum(d for _, d in tl); tr = Track(total); t0 = 0.0
        for name, dur in tl:
            if name == "intro": tr.add(tr.sfx, WHOOSH, t0 + 0.1, 0.2)
            elif name in ("mid", "outro"):
                tr.add(tr.sfx, WHOOSH, t0, 0.25)
                if name == "outro": tr.add(tr.sfx, DING, t0 + 1.2, 0.25)
            else:
                i = int(name[1:]); T = self.timing(i)
                tr.add(tr.sfx, WHOOSH, t0, 0.25); tr.add(tr.voice, load(f"{self.work}/q{i}.wav"), t0 + T["t_voice"])
                for k in range(T["n"]):
                    tr.add(tr.sfx, TICK if k % 2 == 0 else TOCK, t0 + T["t_cd"] + k, 0.45 if T["n"] - k > 2 else 0.7)
                tr.add(tr.sfx, DING, t0 + T["t_rev"], 0.45); tr.add(tr.voice, load(f"{self.work}/a{i}.wav"), t0 + T["t_ans"])
            t0 += dur
        mixdown(tr, wav, chords=CHORDS, bpm=92)


if __name__ == "__main__" and "--texte" in sys.argv:
    print(texte_a_lire(json.load(open(sys.argv[1]))))
