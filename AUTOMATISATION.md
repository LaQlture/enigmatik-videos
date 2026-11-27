# Production quotidienne — enigmatik (TikTok @enigmatik.1)

Mode d'emploi suivi chaque jour par la tâche programmée.
Objectif : fabriquer la vidéo d'énigmes **du jour** et la programmer sur TikTok via Buffer pour **19 h 00 (heure de Paris)**.

Si `contenu/<date>_enigmes.json` **et** `videos/<date>_enigmes.mp4` existent déjà, vérifier dans Buffer
(`list_posts` sur la chaîne **enigmatik.1**) qu'un post est déjà programmé pour aujourd'hui : si oui, ne rien refaire.

## 1. Écrire les 5 énigmes → `contenu/<date>_enigmes.json`

**Règle n° 1 : jamais de doublon.** Ouvrir `historique.json` (toutes les énigmes déjà publiées) et écrire des énigmes
**nouvelles** : pas la même énigme, ni la même idée sous un autre habillage, ni la même réponse de devinette.
Le script de l'étape 2 bloque les doublons, mais il faut viser des idées vraiment neuves dès l'écriture.

```json
{
 "type": "enigmes", "date": "AAAA-MM-JJ",
 "enigmes": [
  {"format": "suite", "consigne": "Quel nombre complète la suite ?", "items": ["3","6","12","24","?"],
   "reponse": "48", "explication": "Chaque nombre est multiplié par 2."},
  {"format": "intrus", "items": ["Baleine","Requin","Dauphin","Orque"], "ans": 1, "reponse": "Requin",
   "explication": "C'est le seul poisson : les trois autres sont des mammifères."},
  {"format": "symboles",
   "lignes": [["triangle","+","triangle","+","triangle","=","15"], ["triangle","+","cercle","+","cercle","=","11"],
              ["cercle","+","carre","=","7"], ["carre","+","triangle","×","cercle","=","?"]],
   "valeurs": {"triangle": 5, "cercle": 3, "carre": 4}, "reponse": "19",
   "explication": "Triangle 5, cercle 3, carré 4. On multiplie d'abord : 4 + 15 = 19."},
  {"format": "devinette", "texte": "Plus j'ai de gardiens, moins je suis gardé. Qui suis-je ?", "reponse": "Un secret",
   "explication": "Plus il y a de gens qui le connaissent, moins il est bien gardé."},
  {"format": "logique", "texte": "Si 5 machines fabriquent 5 objets en 5 minutes, combien de minutes faut-il à 100 machines pour fabriquer 100 objets ?",
   "reponse": "5 minutes", "explication": "Chaque machine fait 1 objet en 5 minutes. Donc 100 machines font 100 objets en 5 minutes."}
 ],
 "legende": "Tu en trouves combien sur 5 ? 🧠 Dis ton score en commentaire 👇 #enigme #enigmes #cassetete #logique #devinette #testdelogique #fyp"
}
```

Formats possibles :
- `suite` : 4 à 8 cases (≤ 4 caractères chacune), la dernière vaut `"?"`. Nombres ou lettres. `consigne` facultative
  (ex. « Quelle lettre complète la suite ? »).
- `intrus` : exactement 4 propositions (≤ 13 caractères), `ans` = position de l'intrus (0 à 3, à varier), `reponse` = ce mot.
- `symboles` : 3 ou 4 lignes ; symboles possibles `triangle`, `cercle`, `carre`, `etoile`, `losange`, `hexagone` ;
  opérateurs `+`, `-`, `×` ; la dernière ligne finit par `"?"`. `valeurs` = la valeur de chaque symbole.
  Le programme recalcule toutes les lignes et refuse toute erreur.
- `devinette` et `logique` : `texte` ≤ 210 caractères.

Règles :
- 5 énigmes de difficulté croissante (facile, facile, moyen, difficile, expert) ; **au moins 3 formats différents**,
  et ne pas reprendre exactement le même enchaînement de formats que la veille ;
- **une seule bonne réponse indiscutable** : refaire chaque calcul et chaque suite en code (python) avant de valider ;
  pour une devinette, vérifier que la réponse ne prête pas à débat ;
- `explication` ≤ 110 caractères, `reponse` ≤ 22 caractères ;
- la voix lit seulement la question (jamais les cases, propositions ni symboles) puis « Réponse : … ! » ;
  l'explication est affichée à l'écran mais pas lue. Pour les devinettes et la logique, la voix lit le `texte` ;
- facultatif : `tts` (question lue autrement qu'affichée), `tts_reponse` (réponse lue autrement : sigles, symboles) ;
- varier les thèmes, les nombres et le type d'astuce d'un jour à l'autre ; pas de sujet choquant ou politique.

## 2. Vérifier les doublons et fabriquer la vidéo
```bash
bash pipeline/setup.sh                                   # outils + voix (≈ 2 min la 1re fois)
python3 pipeline/doublons.py contenu/<date>_enigmes.json # DOUBLONS → remplacer les énigmes citées et relancer
python3 pipeline/make.py contenu/<date>_enigmes.json
```
- `make.py` refuse un contenu mal formé (erreur de calcul, format, longueur) : corriger et relancer.
- `TROP COURT` → choisir des énigmes un peu plus longues (devinette/logique plus développée, suite plus longue). Minimum 62 s (monétisation TikTok).
- Ouvrir la planche de contrôle (`verif.jpg`) avec l'outil Read : texte lisible, rien ne déborde, pas de faute.

## 3. Mettre en ligne
```bash
python3 pipeline/doublons.py contenu/<date>_enigmes.json --ajouter   # enregistre les énigmes dans historique.json
git add contenu videos historique.json
git commit -m "Énigmes du <date>"
git -c push.negotiate=true push origin main
```
Vérifier que `https://raw.githubusercontent.com/<compte>/<dépôt>/main/videos/<date>_enigmes.mp4` répond 200 (`curl -sIL`).

## 4. Programmer sur Buffer
- `get_account` → organisation « My organization » + heure actuelle (+01:00 l'hiver, +02:00 l'été).
- `list_channels` → chaîne TikTok **enigmatik.1** (ne jamais publier sur la.qlture).
- `create_post` : `channelId` d'enigmatik.1, `mode: customScheduled`, `dueAt: <date>T19:00:00+01:00` (ou +02:00),
  `schedulingType: automatic`, `text` = `legende`, `assets: [{video: {url: <lien raw>}}]`,
  `metadata: {tiktok: {isAiGenerated: true}}`.
- Si 19 h est déjà passé : programmer le lendemain 19 h et le signaler.

## 5. En cas de problème
Ne jamais programmer une vidéo défectueuse, une énigme douteuse ou un doublon. Si une étape échoue après une nouvelle
tentative, s'arrêter et envoyer un message clair à l'utilisateur. Terminer par un court résumé : formats, réponses, durée, heure.

## Règles validées par l'utilisateur (nov. 2026)
- **Voix : ElevenLabs uniquement**, voix Tomas (`eaGBbHXreemvYFjnRcMw`, modèle `eleven_v4`), une seule prise par vidéo.
  Télécharger le mp3 et la transcription mot à mot (`words.json`) dans `contenu/voix/`.
- **Quiz** (`pipeline/enigme_audio.py`) : la voix lit une phrase d'**accroche** au début (champ `accroche`, ex.
  « Impossible de trouver toutes les réponses ! »), puis seulement « Énigme N. question » et « Réponse : … ! ».
  Rien d'autre n'est lu (ni propositions, ni explication, ni milieu, ni fin). Texte à faire lire :
  `python3 pipeline/enigme_audio.py contenu/<date>_enigmes.json --texte`.
- **Enquêtes** (`pipeline/enquete_audio.py`) : accroche dès le début, pas de solution (réponse en commentaire),
  **un décor différent à chaque enquête** — ne pas réutiliser la même pièce avec fenêtre à gauche et objet au centre.
  Déjà utilisés : salon du manoir (orage), chalet en rondins (neige).
- **Pas de pluie animée ni de bruit de pluie** (effet grésillant) ; **bruitages discrets** (`volume_bruitages` 0.45).
