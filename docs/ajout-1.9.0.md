# Douze points 1.9.0 — dossier : dévoilement réglable, À traiter et clôture, journal pour Gazette, photo apéro, notation (20/11/2026)

Réunit deux conversations de Julien du 20/11/2026 (coffre : « Souhaits — Douze points » et « Gazette — Dossier — Ajout du
20-11-2026 — édition spéciale Eurovision ») :
- conversation « Bac à sable » : dévoilement automatique réglable, clôture et section À traiter, notation façon 6b,
  mode d'emploi sur la télé (canevas « Douze points 1.8 – public automatique, pays en lice, jumeaux », visuels 6b et 7) ;
- conversation « Journal Eurovision spécial » (grill + conseil déjà passés, arbitrage de Julien) : photo apéro, fiche
  enrichie, bouton « Résultat officiel complet » qui fige un journal lu par Gazette sur `/externe/…`.
Ces demandes devaient aller dans la 1.8.0, publiée sans elles : elles forment la 1.9.0. Gazette 0.28.0 (le magazine
« Good Evening Europe! ») suit, sur le journal défini ici.

## 1. Besoin

1. **Réglages › Dévoilement** : **manuel** (tout au toucher, public compris, comme avant la 1.8.0) ou **automatique**,
   et un **temps par étape** :
   | Étape | Défaut |
   |---|---|
   | Départ (écran d'attente → top 5 du jury) | 10 s |
   | Jury (top 5, tous les points du jury d'un coup) | 15 s |
   | Public (chaque pays jusqu'à l'avant-dernier) | 5 s |
   | Révélation (dernier vote du public) : **durée maximum de la remontée** | 60 s |
   | Podium, puis l'écran des jumeaux | 15 s |
   | Selfie d'un duo en grand | 6 s |
   | Mode d'emploi sur la télé | 30 s |
   Remontée plus longue que le temps de révélation : **rythme accéléré à proportion**, **pause de 2 s à « + 1 point »
   gardée**. Pause / Reprendre restent à l'hôte en automatique.
2. **Fin du dévoilement ≠ clôture.** Le passage du podium aux jumeaux ouvre les résultats sur les téléphones, **sans**
   envoyer à carnet. La soirée part à carnet **quand Julien la clôture**.
3. **Nouvelle section « À traiter »** (rail / pilule, nombre sur la tuile) : par soirée dévoilée non clôturée, saisir les
   **points du jury officiel**, du **public officiel**, le **rang officiel** (ex æquo), pour une **demi-finale** les
   **qualifiés**, puis **« Clôturer · résultat officiel complet »** : fige un **journal** versionné et daté (tous les
   calculs), envoie la soirée à carnet, et rend le journal lisible par Gazette. Une soirée clôturée peut être
   **reclôturée** (vrais votes d'une demi saisis après la finale) : nouvelle version du journal, nouvel envoi.
4. **Journal pour Gazette** (`/externe/`, jeton commun) : contrat `docs/journal-exemple.json` (copié dans Gazette).
   Finale : rangs maison et officiels, podiums, écarts, 3 mieux devinés et 3 plus ratés, palmarès des invités
   (plus proche = écart de rang moyen), commentaires signés, duos et photos (Immich), images de l'évènement et photo
   apéro, numéro proposé (« 2027 · Eurovision · Finale »). Demi : qualifiés devinés par invité, « on les pleure », « on
   les déteste », coup de cœur et nul point maison, nos 3 favoris parmi les qualifiés.
   Règles : ex æquo officiel = rang moyen (sauf rang officiel saisi) ; invité qui n'a pas tout classé exclu du « plus
   proche » ; pays absent du classement officiel ignoré ; jury absent → éléments jury absents.
5. **Fiche PDF** (faite pour être envoyée) : écart de rang maison / réel en jury et en public, palmarès, tous les
   commentaires ; colonnes jury masquées sans jury.
6. **Photo apéro** : bouton chez l'hôte (prise ou choisie sur son téléphone), une par soirée, remplaçable ; envoyée dans
   l'album Immich de la soirée avec le tag « Apéro » ; remplace le logo (logo sinon) sur l'écran d'accueil, la liste des
   soirées, la fiche ; dans le journal.
7. **Notation façon 6b** (choix de Julien) : la chanson notée en grande carte rose entre ses deux voisines (pays,
   titre, note) parmi les chansons déjà notées, sa place (« 6e de tes 11 chansons »), combien plus haut et plus bas,
   « Même note que … », « Ta meilleure / plus petite note pour l'instant ».
8. **Mode d'emploi sur la télé** (visuel 7) : quand tous les invités attendus ont choisi leur prénom, l'écran d'accueil
   montre 30 s (réglable) deux téléphones animés (notation 6b, classement glissé), **au pas de note de la soirée**
   (entier, demi ou quart), puis revient au QR code.

## 2. Technique

- **Réglages** : clés dans la table `reglage` (`devoilement_mode`, `duree_depart`, `duree_jury`, `duree_public`,
  `duree_revelation`, `duree_podium`, `duree_selfie`, `duree_mode_emploi`), `GET/PUT /api/reglages` (bornes : 2 à
  600 s), sauvegardées par l'Anneau comme les autres.
- **Pas automatique généralisé** (`_pas_auto`) : durée du pas selon l'étape (départ, jury, public, révélation, podium).
  En manuel : jamais actif. Révélation : `points.duree_revelation()` — le même plan que `lib/dernier.js` (porté en
  Python, testé contre lui) borné par le réglage, + entrée des drapeaux + 5 s sur « Vainqueur ». Podium écoulé : le
  serveur termine le dévoilement (sans carnet) au prochain `/regard` ou à la demande de la télé (`POST /terminer`,
  idempotent).
- **Clôture** : `soiree.cloturee_le`, table `journal_soiree(soiree_id, version, le, contenu)`, `POST
  /api/soirees/<id>/cloturer` (dévoilée, vrais votes complets : points ou qualifiés), `chanson.officiel_rang`,
  `chanson.officiel_qualifie`, `PUT /officiel` élargi. `terminer` n'envoie plus à carnet ; `envoyer_soiree` est appelé
  par la clôture (et la boucle des envois en attente). `GET /api/a-traiter` (tuile et liste).
- **Journal** : `app/journal.py` pur (calculs, testés seuls) ; `GET /externe/soirees` (soirées clôturées : id, nom,
  type, version, date) et `GET /externe/soirees/<id>/journal` (dernière version) ; images `GET
  /externe/soirees/<id>/image/<sorte>` ; jeton commun, porte fermée sans jeton. Rien sous `/invite/`.
- **Photo apéro** : sorte d'image `apero` (comme logo, bannière, poster) + ligne `photo` (participation 0, `apero=1`)
  pour l'envoi à Immich (tag « Apéro », description « photo apéro »).
- **Interface** : `pages/ATraiter.svelte` (nouvelle entrée), `pages/Reglages.svelte` (section Dévoilement),
  `lib/dernier.js` (`echelle(plan, maxMs)`), `DernierVote` (rythme borné), `Devoilement` / `Spectacle` (étapes
  automatiques, fin automatique), `EcranJumeaux` (durée du selfie), `invite/Invite.svelte` (notation 6b),
  `lib/ModeEmploi.svelte` + `Accueil.svelte`, `Fiche.svelte` (écarts, palmarès, commentaires), `Soiree.svelte`
  (photo apéro).

## 3. Parcours

Préparer → ouvrir (QR code) → tout le monde est là : mode d'emploi 30 s → notes (écran 6b) → envoyer → Dévoiler :
départ 10 s, jury 15 s, public 5 s par pays, révélation ≤ 60 s, podium 15 s, jumeaux (selfies 6 s en grand) → le
lendemain (ou après la finale pour une demi) : À traiter › vrais votes › Clôturer → carnet + journal → Gazette.

## 4. Design

Visuels 6b et 7 du canevas. À traiter : une tuile par soirée à clôturer (nombre de cases restantes), formulaire en
tableau (pays, jury, public, rang ; demi : case « qualifié »), bouton plein « Clôturer · résultat officiel complet ».
Réglages › Dévoilement : interrupteur manuel / automatique, sept champs en secondes.

## 5. Données

Base : colonnes `soiree.cloturee_le`, `chanson.officiel_rang`, `chanson.officiel_qualifie`, `photo.apero`, table
`journal_soiree`. Sorte d'image `apero`. Journal : prénoms, identifiants carnet / maison, identifiants Immich des
photos, commentaires signés : seulement derrière le jeton commun (Gazette), jamais sous `/invite/`.

## 6. Plan

1. `journal.py` + tests ; réglages ; `_pas_auto` généralisé + `duree_revelation` + tests en temps simulé.
2. Clôture, À traiter, `/externe/`, `terminer` sans carnet ; photo apéro.
3. Interface : Réglages, À traiter, dévoilement automatique, révélation bornée, notation 6b, mode d'emploi, fiche.
4. Tests d'écran, version, CHANGELOG, REPRISE, coffre. Bac à sable : plus tard (choix de Julien).

## Décisions du conseil (20/11/2026)

Voir `docs/conseil-1.9.0.md`. En bref : contrat `docs/journal-exemple.json` d'abord ; réglages dans `reglages.json` ;
pas de portage Python du plan (plafond serveur + `suivant depuis` envoyé par la télé) ; clôture permise avec ce qui
est saisi, reclôture en nouvelle version ; module `resultat.py` ; images figées ; versions servies ; soirées anciennes
clôturées d'office ; bouton du mode d'emploi chez l'hôte.
