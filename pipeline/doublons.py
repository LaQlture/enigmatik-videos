"""Anti-doublons : refuse toute énigme déjà publiée ou trop proche d'une énigme publiée.

  python3 pipeline/doublons.py contenu/AAAA-MM-JJ_enigmes.json            → vérifie (code 1 si problème)
  python3 pipeline/doublons.py contenu/AAAA-MM-JJ_enigmes.json --ajouter  → vérifie puis enregistre dans historique.json
"""
import difflib, json, os, re, sys, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIST = os.path.join(REPO, "historique.json")

def norm(s):
    s = unicodedata.normalize("NFD", str(s).lower())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = re.sub(r"\b(le|la|les|l|un|une|des|du|de|d)\b", " ", re.sub(r"[^a-z0-9]+", " ", s))
    return " ".join(s.split())

def fiche(e, date):
    f = e["format"]; r = {"date": date, "format": f, "reponse": norm(e["reponse"])}
    if f == "suite": r["cle"] = [norm(x) for x in e["items"] if x != "?"]
    elif f == "intrus": r["cle"] = sorted(norm(x) for x in e["items"])
    elif f == "symboles":
        r["cle"] = sorted(f"{k}={v}" for k, v in e["valeurs"].items())
        r["lignes"] = [" ".join(l) for l in e["lignes"]]
    else: r["cle"] = norm(e["texte"])
    r["resume"] = e.get("texte") or " ".join(e.get("items", [])) or " | ".join(r.get("lignes", []))
    return r

def conflit(a, b):
    """Retourne la raison si a et b sont identiques ou trop proches, sinon None."""
    if a["format"] in ("devinette", "logique") and b["format"] in ("devinette", "logique"):
        ratio = difflib.SequenceMatcher(None, a["cle"], b["cle"]).ratio()
        if a["reponse"] == b["reponse"] and (a["format"] == b["format"] == "devinette" or ratio >= 0.4):
            return "même réponse qu'une énigme déjà faite"
        if ratio >= 0.6: return "énoncé trop proche"
        return None
    if a["format"] != b["format"]: return None
    if a["cle"] == b["cle"]: return "énigme identique"
    f = a["format"]
    if f == "suite":
        if a["cle"][:3] == b["cle"][:3]: return "même début de suite"
        if difflib.SequenceMatcher(None, " ".join(a["cle"]), " ".join(b["cle"])).ratio() >= 0.8: return "suite trop proche"
    elif f == "intrus":
        commun = len(set(a["cle"]) & set(b["cle"]))
        if commun >= 3 or (a["reponse"] == b["reponse"] and commun >= 2): return "mêmes propositions d'intrus"
    elif f == "symboles":
        if a.get("lignes") == b.get("lignes"): return "mêmes équations"
        if set(a["cle"]) == set(b["cle"]): return "mêmes valeurs de symboles"
    return None

def main(path, ajouter=False):
    c = json.load(open(path))
    hist = json.load(open(HIST)) if os.path.exists(HIST) else []
    hist_autres = [h for h in hist if h["date"] != c["date"]]   # relancer le même jour ne compte pas comme doublon
    new = [fiche(e, c["date"]) for e in c["enigmes"]]
    pb = []
    for i, a in enumerate(new, 1):
        for h in hist_autres:
            r = conflit(a, h)
            if r: pb.append(f"énigme {i} ({a['format']}) : {r} — déjà publiée le {h['date']} : {h['resume'][:70]}")
        for j, b in enumerate(new[i:], i + 1):
            r = conflit(a, b)
            if r: pb.append(f"énigmes {i} et {j} : {r}")
    if pb:
        print("DOUBLONS — remplacer ces énigmes puis relancer :\n- " + "\n- ".join(pb)); sys.exit(1)
    print(f"OK : aucune énigme en double ({len(hist_autres)} énigmes déjà publiées vérifiées)")
    if ajouter:
        hist = hist_autres + new
        json.dump(hist, open(HIST, "w"), ensure_ascii=False, indent=1)
        print(f"historique.json : {len(hist)} énigmes enregistrées")

if __name__ == "__main__":
    main(sys.argv[1], "--ajouter" in sys.argv)
