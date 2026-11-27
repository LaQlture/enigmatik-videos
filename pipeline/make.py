"""Fabrique la vidéo d'énigmes à partir d'un fichier de contenu JSON.

Usage : python3 pipeline/make.py contenu/AAAA-MM-JJ_enigmes.json
Sortie : videos/AAAA-MM-JJ_enigmes.mp4 + planche de vérification /tmp/enigmatik/<date>/verif.jpg
"""
import json, multiprocessing as mp, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import encode, assemble, duration

MIN_DUR = 62.0   # monétisation TikTok : plus d'1 minute
OBJ = None

def _render(args):
    name, dur, path = args
    encode(path, dur, OBJ.frame_fn(name))
    return name

def main(src):
    global OBJ
    c = json.load(open(src))
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    work = f"/tmp/enigmatik/{c['date']}"; os.makedirs(work, exist_ok=True)
    if c["type"] == "enquete" and c.get("audio"):       # voix off externe (ElevenLabs)
        from enquete_audio import EnqueteAudio
        OBJ = EnqueteAudio(c, work, os.path.dirname(os.path.abspath(src)))
    elif c["type"] == "enquete":
        from enquete import Enquete
        OBJ = Enquete(c, work)
    elif c.get("audio"):                                  # quiz avec voix ElevenLabs
        from enigme_audio import EnigmesAudio
        OBJ = EnigmesAudio(c, work, os.path.dirname(os.path.abspath(src)))
    else:
        from enigme import Enigmes
        OBJ = Enigmes(c, work)      # vérifie aussi le contenu (formats, calculs des symboles…)
    t = time.time()
    OBJ.voices()
    tl = OBJ.timeline(); total = sum(d for _, d in tl)
    print(f"voix OK ({time.time()-t:.0f}s) — durée prévue {total:.1f}s", flush=True)
    if total < MIN_DUR:
        raise SystemExit(f"TROP COURT : {total:.1f}s < {MIN_DUR}s — allonger les énoncés ou explications")

    from PIL import Image
    fr = [OBJ.frame_fn(n)(tt).convert("RGB").resize((360, 640)) for n, tt in OBJ.check_frames()]
    cols = 7; rows = (len(fr) + cols - 1) // cols
    sheet = Image.new("RGB", (360 * cols, 640 * rows))
    for k, f in enumerate(fr): sheet.paste(f, (360 * (k % cols), 640 * (k // cols)))
    sheet.save(f"{work}/verif.jpg", quality=88)

    jobs = [(n, d, f"{work}/{n}.mp4") for n, d in tl]
    with mp.get_context("fork").Pool(max(1, min(4, os.cpu_count() or 2))) as pool:
        for n in pool.imap_unordered(_render, jobs): print("scène", n, flush=True)
    wav = f"{work}/mix.wav"; OBJ.audio(tl, wav)
    os.makedirs(f"{repo}/videos", exist_ok=True)
    out = f"{repo}/videos/{c['date']}_{c['type']}.mp4"
    assemble([j[2] for j in jobs], wav, out)
    d = duration(out)
    print(json.dumps({"video": out, "duree": round(d, 1), "verif": f"{work}/verif.jpg", "temps_s": round(time.time() - t)}))
    if d < MIN_DUR: raise SystemExit("vidéo trop courte")

if __name__ == "__main__":
    main(sys.argv[1])
