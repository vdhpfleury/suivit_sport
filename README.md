# Dashboard nutrition & performance

Suivi quotidien/hebdomadaire des apports alimentaires (par categorie) vs objectifs,
et suivi du poids/mensurations. Les donnees sont stockees dans un Google Sheet,
ce qui permet d'utiliser l'app depuis ton telephone ou ton ordinateur, de
n'importe ou, une fois deployee sur Streamlit Community Cloud (gratuit).

## Vue d'ensemble

```
Telephone / PC  --->  App Streamlit (hebergee sur Streamlit Cloud)  --->  Google Sheet (stockage)
```

Il y a 3 etapes : (1) creer le Google Sheet + les acces, (2) mettre le code sur
GitHub, (3) deployer sur Streamlit Community Cloud. Compte environ 20-30 min la
premiere fois, c'est ensuite instantane a chaque utilisation.

---

## Etape 1 - Creer le Google Sheet et les acces

### 1.1 Creer le classeur

Cree un nouveau Google Sheet (sheets.new), nomme-le par exemple
`suivi-nutrition-sportif`, puis cree **3 onglets** avec ces noms et lignes
d'en-tete exactes (copier-coller la premiere ligne dans chaque onglet) :

**Onglet `daily_log`**
```
date	type_journee	repas	viande_poisson	oeufs	fromage_blanc	lait	feculents	legumes	fruits	huile_olive	oleagineux	sucres
```

**Onglet `measurements`**
```
date	poids	tour_taille	tour_bras	tour_cuisse	tour_poitrine	tour_hanches	masse_grasse
```

**Onglet `profile`**
```
taille_cm	age	poids_defaut_kg
```
(ajoute une deuxieme ligne avec par exemple `195	24	88` pour initialiser)

### 1.2 Creer un compte de service Google Cloud

1. Va sur [console.cloud.google.com](https://console.cloud.google.com), cree un
   nouveau projet (ou reutilise un projet existant).
2. Dans "APIs & Services > Library", active **Google Sheets API** et
   **Google Drive API**.
3. Dans "APIs & Services > Credentials", clique "Create credentials >
   Service account". Donne-lui un nom (ex. `nutrition-app`), pas besoin de
   roles particuliers au niveau projet.
4. Ouvre le compte de service cree, onglet "Keys" > "Add key" > "Create new
   key" > format **JSON**. Un fichier `.json` se telecharge : garde-le, il
   contient les identifiants dont l'app a besoin.

### 1.3 Partager le Google Sheet avec le compte de service

Dans le fichier JSON telecharge, recupere la valeur de `client_email`
(quelque chose comme `nutrition-app@ton-projet.iam.gserviceaccount.com`).
Dans ton Google Sheet, clique "Partager" et ajoute cet email en tant
qu'**Editeur**.

---

## Etape 2 - Mettre le code sur GitHub

1. Cree un repo GitHub (peut etre prive) et pousse tous les fichiers de ce
   dossier (`app.py`, `requirements.txt`, `.gitignore`) **sauf**
   `secrets.toml.example` qui n'est qu'un modele, et surtout jamais de vrai
   fichier `secrets.toml`.
2. Verifie que `.gitignore` est bien pris en compte (le vrai fichier de
   secrets ne doit jamais apparaitre sur GitHub).

## Etape 3 - Deployer sur Streamlit Community Cloud

1. Va sur [share.streamlit.io](https://share.streamlit.io), connecte-toi avec
   GitHub, clique "New app", selectionne ton repo et `app.py` comme fichier
   principal.
2. Avant de lancer, va dans les parametres avances ("Advanced settings") >
   "Secrets", et colle le contenu de `secrets.toml.example` en remplacant
   chaque champ vide par les valeurs correspondantes du fichier JSON telecharge
   a l'etape 1.2 :

   - `spreadsheet` = le nom exact de ton Google Sheet (ou son URL complete)
   - `project_id`, `private_key_id`, `private_key`, `client_email`,
     `client_id`, `client_x509_cert_url` = copies directement depuis le JSON

   Attention pour `private_key` : garde les `\n` tels quels et entoure toute
   la valeur de guillemets, exactement comme dans le fichier JSON.

3. Clique "Deploy". Au bout de quelques minutes, l'app est disponible a une
   URL du type `https://ton-app.streamlit.app`, accessible depuis ton
   telephone comme depuis ton PC, sans que rien ne tourne chez toi.
4. Sur ton telephone, ouvre cette URL dans le navigateur puis "Ajouter a
   l'ecran d'accueil" pour t'en servir comme une app.

---

## Utilisation locale (optionnel, pour tester avant de deployer)

```bash
pip install -r requirements.txt
mkdir -p .streamlit
cp secrets.toml.example .streamlit/secrets.toml   # puis remplir avec tes vraies valeurs
streamlit run app.py
```

## Mettre a jour l'app plus tard

Toute modification poussee sur la branche GitHub connectee redeploie
automatiquement l'app sur Streamlit Cloud (redemarrage en quelques secondes).

## Structure des 3 onglets de l'app

- **Suivi quotidien** : choix de la date + type de journee (Repos /
  Musculation / Basket / Musculation + Basket), puis saisie des quantites
  consommees **repas par repas** (un volet depliable par repas, avec un
  bouton d'enregistrement propre a chaque repas). L'objectif specifique a
  chaque repas est affiche directement a cote de la case de saisie
  correspondante (la cible quotidienne de chaque categorie est repartie
  automatiquement entre les repas ou elle intervient). En dessous, un
  recapitulatif du total de la journee compare aux cibles quotidiennes
  (tableau + graphique), et un bilan calories/proteines/lipides/glucides vs
  objectif du jour.
- **Suivi hebdomadaire** : choix d'une periode, courbes d'evolution jour par
  jour (consomme vs objectif) pour chaque macro, moyennes sur la periode, et
  comparaison moyenne par categorie.
- **Poids & mensurations** : formulaire de saisie (poids, tour de taille,
  bras, cuisse, poitrine, hanches, % masse grasse estime), historique et
  courbes d'evolution. Le poids le plus recent est automatiquement repris
  pour calculer les objectifs caloriques dans les deux autres onglets.

Les cibles par categorie et les valeurs nutritionnelles utilisees sont les
memes que celles du classeur Excel `Plan_alimentaire_sportif.xlsx` ; modifie
les dictionnaires `TARGETS` et `NUTRI` en haut de `app.py` si tu veux les
ajuster.

## Notes techniques

- Les lectures Google Sheets se font avec `ttl=0` (pas de cache) pour que les
  donnees soient toujours a jour, meme apres une ecriture depuis un autre
  appareil.
- Chaque enregistrement (repas, mensuration) reecrit l'integralite de
  l'onglet correspondant apres avoir remplace la ligne concernee - logique
  d'"upsert" simple, adaptee au volume de donnees d'un suivi personnel.
- Le suivi quotidien stocke desormais **une ligne par repas** (colonne
  `repas`) plutot qu'une ligne par jour, pour permettre la saisie repas par
  repas avec un objectif dedie a chaque repas. Si tu avais deja utilise une
  version precedente de l'app, ajoute simplement la colonne `repas` en 3e
  position dans l'en-tete de l'onglet `daily_log` de ton Google Sheet ; les
  anciennes lignes (sans repas precise) restent lisibles mais n'apparaitront
  pas dans un volet de repas specifique tant qu'elles n'auront pas ete
  resaisies.# Dashboard nutrition & performance

Suivi quotidien/hebdomadaire des apports alimentaires (par categorie) vs objectifs,
et suivi du poids/mensurations. Les donnees sont stockees dans un Google Sheet,
ce qui permet d'utiliser l'app depuis ton telephone ou ton ordinateur, de
n'importe ou, une fois deployee sur Streamlit Community Cloud (gratuit).

## Vue d'ensemble

```
Telephone / PC  --->  App Streamlit (hebergee sur Streamlit Cloud)  --->  Google Sheet (stockage)
```

Il y a 3 etapes : (1) creer le Google Sheet + les acces, (2) mettre le code sur
GitHub, (3) deployer sur Streamlit Community Cloud. Compte environ 20-30 min la
premiere fois, c'est ensuite instantane a chaque utilisation.

---

## Etape 1 - Creer le Google Sheet et les acces

### 1.1 Creer le classeur

Cree un nouveau Google Sheet (sheets.new), nomme-le par exemple
`suivi-nutrition-sportif`, puis cree **3 onglets** avec ces noms et lignes
d'en-tete exactes (copier-coller la premiere ligne dans chaque onglet) :

**Onglet `daily_log`**
```
date	type_journee	viande_poisson	oeufs	fromage_blanc	lait	feculents	legumes	fruits	huile_olive	oleagineux	sucres
```

**Onglet `measurements`**
```
date	poids	tour_taille	tour_bras	tour_cuisse	tour_poitrine	tour_hanches	masse_grasse
```

**Onglet `profile`**
```
taille_cm	age	poids_defaut_kg
```
(ajoute une deuxieme ligne avec par exemple `195	24	88` pour initialiser)

### 1.2 Creer un compte de service Google Cloud

1. Va sur [console.cloud.google.com](https://console.cloud.google.com), cree un
   nouveau projet (ou reutilise un projet existant).
2. Dans "APIs & Services > Library", active **Google Sheets API** et
   **Google Drive API**.
3. Dans "APIs & Services > Credentials", clique "Create credentials >
   Service account". Donne-lui un nom (ex. `nutrition-app`), pas besoin de
   roles particuliers au niveau projet.
4. Ouvre le compte de service cree, onglet "Keys" > "Add key" > "Create new
   key" > format **JSON**. Un fichier `.json` se telecharge : garde-le, il
   contient les identifiants dont l'app a besoin.

### 1.3 Partager le Google Sheet avec le compte de service

Dans le fichier JSON telecharge, recupere la valeur de `client_email`
(quelque chose comme `nutrition-app@ton-projet.iam.gserviceaccount.com`).
Dans ton Google Sheet, clique "Partager" et ajoute cet email en tant
qu'**Editeur**.

---

## Etape 2 - Mettre le code sur GitHub

1. Cree un repo GitHub (peut etre prive) et pousse tous les fichiers de ce
   dossier (`app.py`, `requirements.txt`, `.gitignore`) **sauf**
   `secrets.toml.example` qui n'est qu'un modele, et surtout jamais de vrai
   fichier `secrets.toml`.
2. Verifie que `.gitignore` est bien pris en compte (le vrai fichier de
   secrets ne doit jamais apparaitre sur GitHub).

## Etape 3 - Deployer sur Streamlit Community Cloud

1. Va sur [share.streamlit.io](https://share.streamlit.io), connecte-toi avec
   GitHub, clique "New app", selectionne ton repo et `app.py` comme fichier
   principal.
2. Avant de lancer, va dans les parametres avances ("Advanced settings") >
   "Secrets", et colle le contenu de `secrets.toml.example` en remplacant
   chaque champ vide par les valeurs correspondantes du fichier JSON telecharge
   a l'etape 1.2 :

   - `spreadsheet` = le nom exact de ton Google Sheet (ou son URL complete)
   - `project_id`, `private_key_id`, `private_key`, `client_email`,
     `client_id`, `client_x509_cert_url` = copies directement depuis le JSON

   Attention pour `private_key` : garde les `\n` tels quels et entoure toute
   la valeur de guillemets, exactement comme dans le fichier JSON.

3. Clique "Deploy". Au bout de quelques minutes, l'app est disponible a une
   URL du type `https://ton-app.streamlit.app`, accessible depuis ton
   telephone comme depuis ton PC, sans que rien ne tourne chez toi.
4. Sur ton telephone, ouvre cette URL dans le navigateur puis "Ajouter a
   l'ecran d'accueil" pour t'en servir comme une app.

---

## Utilisation locale (optionnel, pour tester avant de deployer)

```bash
pip install -r requirements.txt
mkdir -p .streamlit
cp secrets.toml.example .streamlit/secrets.toml   # puis remplir avec tes vraies valeurs
streamlit run app.py
```

## Mettre a jour l'app plus tard

Toute modification poussee sur la branche GitHub connectee redeploie
automatiquement l'app sur Streamlit Cloud (redemarrage en quelques secondes).

## Structure des 3 onglets de l'app

- **Suivi quotidien** : choix de la date + type de journee (Repos /
  Musculation / Basket / Musculation + Basket), saisie des quantites
  consommees par categorie, comparaison immediate avec les cibles (tableau +
  graphique), et bilan calories/proteines/lipides/glucides vs objectif du
  jour.
- **Suivi hebdomadaire** : choix d'une periode, courbes d'evolution jour par
  jour (consomme vs objectif) pour chaque macro, moyennes sur la periode, et
  comparaison moyenne par categorie.
- **Poids & mensurations** : formulaire de saisie (poids, tour de taille,
  bras, cuisse, poitrine, hanches, % masse grasse estime), historique et
  courbes d'evolution. Le poids le plus recent est automatiquement repris
  pour calculer les objectifs caloriques dans les deux autres onglets.

Les cibles par categorie et les valeurs nutritionnelles utilisees sont les
memes que celles du classeur Excel `Plan_alimentaire_sportif.xlsx` ; modifie
les dictionnaires `TARGETS` et `NUTRI` en haut de `app.py` si tu veux les
ajuster.

## Notes techniques

- Les lectures Google Sheets se font avec `ttl=0` (pas de cache) pour que les
  donnees soient toujours a jour, meme apres une ecriture depuis un autre
  appareil.
- Chaque enregistrement (journee alimentaire ou mensuration) reecrit
  l'integralite de l'onglet correspondant apres avoir remplace la ligne du
  jour concerne - logique d'"upsert" simple, adaptee au volume de donnees
  d'un suivi personnel.
