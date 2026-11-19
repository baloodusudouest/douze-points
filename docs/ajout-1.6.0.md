# Douze points — Ajout 1.6.0 : jumeaux de vote et photos de la soirée

Cadrage du 19/11/2026 (questions à choix, réponses de Julien). À relire avec `docs/dossier.md`.

## 1. Besoin

- Quand le classement est figé (soirée dévoilée), **chaque invité a son jumeau de vote** : l'invité dont les notes ressemblent le plus aux siennes. L'appli propose d'**immortaliser le duo** par une photo.
- Sur **tous les écrans de vote des invités**, une **icône photo** pour prendre des photos de la soirée, **de l'ouverture jusqu'à l'archivage**.
- Toutes les photos partent dans un **album Immich créé automatiquement** : `AAAA-MM-JJ <titre de la soirée>` (ex. « 2027-05-15 Eurovision 2027 – Finale (Vienne) »).
- Les invités **ne voient pas** les photos des autres dans Douze points (Immich seul) ; ils voient « photo envoyée » et le nombre de photos de la soirée.
- **Toujours actif** (pas de case par soirée) ; seule l'absence de clé Immich cache l'icône.

## 2. Technique

- **Jumeaux** : `points.jumeaux(notes)` (pur, testé seul). Pour chaque invité, l'autre invité de plus petit écart moyen sur les chansons notées par les deux (3 chansons communes au moins, comme les affinités) ; à égalité, le plus petit identifiant. Accord affiché = `100 × (1 − écart moyen / 20)`, arrondi. **Duos** = paires distinctes tirées de ces jumeaux (A↔B réciproque montré une fois, marqué « réciproques »). Calculé sur les participants retenus au dévoilement, rendu seulement quand la soirée est dévoilée (porte invité comprise, voir `tests/test_secret.py`).
- **Photos** : `PUT /invite/<jeton>/api/photo` (en-tête `X-Telephone`, corps brut, en-tête facultatif `X-Duo: <id de l'invité jumeau>`). JPEG, PNG ou HEIC (signature vérifiée), 25 Mo au plus. Rangées dans `/data/photos/<soirée>/` + table `photo` (soirée, participation, duo, fichier, type, reçue le, id Immich, essais, erreur). Refus 409 si la soirée est en brouillon ou archivée ; `X-Duo` refusé (422) si ce n'est pas le jumeau de l'invité ou son jumeau inverse, ou avant le dévoilement.
- **Envoi vers Immich** côté serveur (clé `DOUZE_POINTS_IMMICH_CLE`, adresse `DOUZE_POINTS_IMMICH_URL`, défaut `http://immich_server:2283`) : envoi juste après réception (tâche en fond), puis **nouvel essai toutes les 10 min** (`_boucle_immich`, déclarée à la santé des tâches). Étapes : envoi de l'image (`POST /api/assets`), album trouvé ou créé (identifiant gardé sur la soirée, `soiree.immich_album`), ajout à l'album, description, tags. Fichier local effacé une fois tout fait. L'invité voit « photo reçue » dès que le NAS l'a.
  - Description : « Douze points – <titre> – photo de <prénom> » ; duo : « Douze points – <titre> – jumeaux de vote : A et B (92 % d'accord) ».
  - Tags : « Douze points » sur toutes les photos ; « Jumeaux de vote » en plus sur les photos de duo (choix après le conseil, § 7).
  - Permissions de la clé : `asset.upload`, `asset.update`, `album.read`, `album.create`, `albumAsset.create`, `tag.read`, `tag.create`, `tag.asset`, `server.about`, `apiKey.read`.
- **Connexion** (écran Services) : Immich, version et permissions de la clé.
- **Fiche et carnet** : la fiche montre les duos et le lien de l'album (adresse publique d'Immich lue dans l'annuaire de l'Anneau, tuile « Immich » ; sans elle, le nom de l'album seul). L'envoi vers carnet ajoute `jumeau` (prénom, accord) par invité et `album` (nom, lien) : champs nouveaux, ignorés par carnet tant qu'il ne les affiche pas.

## 3. Parcours

- **Téléphone, pendant toute la soirée** : icône 📷 en haut à droite de l'écran de notation, du classement et des résultats. Toucher → appareil photo de l'iPhone (`<input type="file" accept="image/*" capture="environment">` : marche en http, contrairement à la caméra dans la page) ; envoi avec barre de progression ; « Photo envoyée · 7 photos ce soir ».
- **Téléphone, après le dévoilement** : bandeau en tête des résultats « Ton jumeau de vote : Camille · 92 % d'accord » + bouton **Immortaliser** (selfie : `capture="user"`). Une fois une photo du duo reçue (de l'un ou l'autre), le bandeau passe à « 📸 Immortalisés » ; on peut en reprendre une.
- **Télé (régie), après le podium** : un dernier écran **« Jumeaux de vote »** avec **tous les duos d'un coup** (mosaïque : prénoms, accord, « réciproques », 📸 quand la photo est arrivée, mis à jour toutes les 5 s) et en bas « Prenez vos téléphones pour vous immortaliser ».

## 4. Design

Couleur et typographie de l'appli inchangées ; la mosaïque reprend les tuiles du podium ; le duo immortalisé s'allume d'un halo de projecteur (animation sobre, coupée si « réduire les animations »).

## 5. Données

- `soiree.immich_album TEXT` (identifiant de l'album).
- `photo(id, soiree_id, participation_id, duo_participation_id NULL, fichier, type, taille, recue_le, immich_id, envoyee_le, essais, erreur)`.
- Suppression d'une soirée : ses photos locales en attente sont effacées ; ce qui est dans Immich y reste.

## 6. Plan

1. `points.jumeaux` + tests.
2. Table, route photo, file d'envoi Immich (faux Immich dans les tests), santé.
3. Jumeaux dans les résultats des téléphones et de la régie ; `test_secret`.
4. Écrans : icône photo, bandeau jumeau, écran « Jumeaux de vote » ; tests d'écran PC et iPhone.
5. Fiche, carnet, Connexion ; coffre (note, variables, stack, flux), dépôt.

**Jamais essayé sur la vraie installation** : l'appareil photo d'iPhone ouvert depuis une page en http, le format envoyé par Safari (HEIC ou JPEG), l'envoi réel vers Immich.

## 7. Après le conseil (19/11/2026)

Intégré sans redemander : ni icône ni bandeau sur l'appareil connecté à la régie (recopié sur la télé) ; accord en tranches, jamais en pourcentage ; une ligne d'explication et la destination des photos ; icône de la soirée sans `capture` et avec plusieurs photos (la Pellicule garde une copie), `capture="user"` seulement pour Immortaliser ; écriture au fil de la réception, verrou d'envoi (un seul album), reprise étape par étape, nettoyage au démarrage, plafond par invité ; barre d'avancement par XHR ; invités sans jumeau absents de la télé.

Choix de Julien :
- tag **neutre « Jumeaux de vote »** sur les photos de duo (plus « scandale ») ; la Gazette pourra s'en servir en mode scandale (« après la soirée Eurovision, un nouveau couple se forme… ») : à ajouter côté Gazette ;
- tous les duos affichés tels quels sur la télé ;
- photo gênante : rien dans l'appli, tri dans Immich ;
- tout codé d'un coup en 1.6.0 ; la sonde devient la liste d'essais sur place.

Écarté pour plus tard : envoi Immich mis en commun dans le socle, photo reliée à la chanson en cours, « némésis » de vote, duos suivis d'une année sur l'autre.
