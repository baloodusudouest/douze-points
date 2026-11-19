# Douze points 1.8.0 — dossier : public sans cliquer, pays en lice, photo des duos, saisie directe (20/11/2026)

Demandes de Julien du 19/11/2026 à minuit, visuels validés le 20/11/2026 (canevas « Douze points 1.8 – public
automatique, pays en lice, jumeaux »), choix pris par questions à choix.

## 1. Besoin

1. **Points du public sans cliquer** : le même écran qu'aujourd'hui (tableau + « 14 + 9 = 23 »), mais chaque pays
   passe seul au bout de **5 secondes**. Le dernier pays se lance seul aussi (5 s après l'avant-dernier). L'hôte garde
   Revenir et Suivant, plus **Pause / Reprendre**. Le top 5 du jury et le podium restent au toucher (l'hôte lance le
   public, puis le podium).
2. **Les pays en lice** : au dernier vote, une animation pose **tous les pays** sur l'échelle des places (un par un,
   vite) ; puis le dernier pays part de **sa place après le jury** (ses seuls points du jury) et monte jusqu'à sa place
   finale au rythme de la 1.7.0 (très vite, puis lentement de la 6e à la 2e, 2 s à « + 1 point », puis d'un coup).
   Les autres pays : **drapeau seul** ; nom + drapeau gardés pour le pays en tête et pour celui qui reste à noter.
   Quand le dernier pays dépasse, l'avance s'affiche : **« + 3 points »** (choix de Julien). S'il y a trop de pays pour
   l'écran, la liste est **coupée en deux** : moitié haute à gauche, moitié basse à droite. Télé et téléphones.
3. **Bouton des jumeaux sous le podium** (télé), plus en haut à droite. En haut ne reste que « Revenir ».
4. **Photo d'un duo à l'écran** : quand un duo s'immortalise, son selfie s'affiche sur la télé **en grand 6 s**
   (polaroïd), puis **dans la carte du duo**, qui s'allume.
5. **Saisir sa grille** (hôte, grille papier) : la liste des pays tout de suite, une case **note** et une case
   **mot** par chanson ; puis **son classement à la main** (étape existante : glisser ou flèches), puis Envoyer.

## 2. Technique

- **Pas automatique tenu par le serveur** (et non par un écran) : la télé, le téléphone de l'hôte et ceux des invités
  lisent tous le même pas ; deux écrans de régie ouverts ne font jamais avancer deux fois. Colonnes ajoutées à
  `soiree` : `pas_le` (REAL, heure du dernier changement de pas, horloge du serveur) et `pause_auto` (0/1).
  `_pas_effectif(s, marche)` : si le dévoilement est en cours, sans pause, et que le pas est un pas du public avant le
  dernier, `pas + (maintenant − pas_le) // 5 s`, au plus le dernier pas du public. `POST /pas` accepte `pause`
  (facultatif) et remet `pas_le` à maintenant. `GET /devoilement` (régie) et `/invite/…/devoilement` rendent le pas
  effectif et `auto = {actif, pause, prochain_dans (ms), duree: 5000}`. Pas de tâche de fond.
- Télé (`Devoilement.svelte`) : barre de temps tirée de `prochain_dans`, avance localement à l'échéance puis se cale
  sur le serveur (relu chaque seconde, comme aujourd'hui). Téléphones (`Spectacle.svelte`) : ils suivent le pas comme
  aujourd'hui (relecture).
- **Pays en lice** : `lib/DernierVote.svelte` gagne une phase d'entrée (drapeaux posés un par un, 120 ms chacun, 2,5 s
  au plus) avant la montée ; `lib/dernier.js` gagne `colonnes(nb, hauteur, seuil)` (1 ou 2) et `case(place, nb,
  colonnes)` (colonne et rang d'une place), purs et testés par node. En 2 colonnes : [drapeaux + carte en tête | échelle
  1..h | carte du dernier pays | échelle h+1..N | drapeaux]. Seuil : 30 px par place sur la télé, 22 px en compact.
- **Photo des duos** : aujourd'hui la copie du NAS est effacée dès qu'Immich l'a. En 1.8, **les selfies de duo
  restent** sur le NAS jusqu'à la suppression de la soirée (les autres photos : comme avant). `_jumeaux` rend
  `photo` (identifiant du dernier selfie du duo dont le fichier existe). Nouvelle route régie
  `GET /api/soirees/<id>/photos/<photo_id>` (mot de passe commun, selfies de duo seulement, type d'image d'après le
  fichier). `EcranJumeaux.svelte` : un selfie qui apparaît après l'ouverture de l'écran passe en grand 6 s (file
  d'attente s'il en arrive plusieurs), puis dans la carte ; ceux déjà là à l'ouverture vont directement dans leur
  carte. Image illisible (HEIC sur un navigateur qui ne le lit pas) : la carte garde « 📸 immortalisés ».
- **Saisie directe** : `invite/SaisieGrille.svelte`, montré à la place de la liste des chansons quand l'onglet est
  ouvert en mode saisie. Note écrite au clavier (virgule acceptée, pas de note réglé par l'hôte vérifié par le serveur
  comme aujourd'hui), mot ; enregistrement à la sortie de la case (`PUT note`, existant). Ensuite « Passer au
  classement » (existant).

## 3. Parcours

Hôte : Dévoiler → top 5 du jury (toucher) → toucher : premier pays du public → les pays passent seuls toutes les 5 s
(barre de temps ; Pause, Revenir, Suivant) → 5 s après l'avant-dernier : « Les pays en lice », la montée, Vainqueur
(+ avance), cotillons → toucher : podium → « Voir les jumeaux de vote » sous le podium → mosaïque des duos ; chaque
selfie de duo arrive en grand puis dans sa carte. Grille papier : Soirée › Saisir sa grille → liste avec notes et mots
→ Passer au classement → ranger → Envoyer.

## 4. Design

D'après le canevas : mêmes couleurs que la 1.7.0 (rose `#e5559f`, jaune `#ffd84d`, cartes `#f6f0ff`), drapeaux seuls
en pastilles rondes, étiquette jaune « + 3 points » à côté de « Vainqueur ». Barre de temps rose sous l'addition,
« Pays suivant dans 3 s ». Bouton plein rose « Voir les jumeaux de vote » sous le podium, phrase d'aide dessous.
Polaroïd blanc pour le selfie en grand, éclair blanc bref à l'arrivée (pas d'éclair avec « Réduire les animations »).
Saisie : une ligne par chanson (numéro, drapeau, pays, case note de 48 px), case du mot dessous, points calculés en
direct sous le pays.

## 5. Données

Base : `soiree.pas_le REAL`, `soiree.pause_auto INTEGER DEFAULT 0` (ajoutées au démarrage si absentes). Photos :
selfies de duo gardés dans `/data/photos/<soirée>/` après l'envoi à Immich ; effacés avec la soirée. Rien ne sort
de plus vers Immich ni vers carnet. Sur la télé, un selfie de duo est vu par tout le salon : c'est voulu (demande de
Julien) ; les autres photos de la soirée restent invisibles dans l'appli.

## 6. Plan

1. Serveur : colonnes, `_pas_effectif`, `POST /pas` (pause), les deux `devoilement` ; selfies gardés ; route photo ;
   `_jumeaux.photo`. Tests API (temps simulé par `main.MAINTENANT`).
2. `dernier.js` : `colonnes`, `case` + tests node. `DernierVote.svelte` : entrée, drapeaux, 2 colonnes, avance.
3. `Devoilement.svelte` : auto, barre, Pause ; bouton des jumeaux sous le podium. `Spectacle.svelte` : rien de plus
   que suivre le pas (vérifier).
4. `EcranJumeaux.svelte` : selfies, grand puis carte. `SaisieGrille.svelte` + branchement dans `Invite.svelte`.
5. Tests d'écran (PC, iPhone, télé), version 1.8.0, CHANGELOG, REPRISE ; coffre. Bac à sable : plus tard (choix de
   Julien).

## Décisions du conseil (20/11/2026)

Voir `docs/conseil-1.8.0.md` : actions au lieu d'un numéro de pas (Revenir met en pause), lectures sans verrou,
`pas_le` jamais pris d'avant, télé qui n'envoie rien seule, égalité, vignette JPEG des selfies de duo, saisie qui
attend ses enregistrements, écran allumé pendant le dévoilement, tests en temps simulé.
