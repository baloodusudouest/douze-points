# Journal des versions

## 1.11.0 — 20 novembre 2026 (sons sur la télé, compte à rebours avant la révélation, commentaires dans le classement)
Trois demandes de Julien du 20/11/2026 ; dossier `docs/ajout-1.11.0.md`, conseil `docs/conseil-1.11.0.md` (le
conseil prime là où ils diffèrent).
- **Sons sur la télé seulement** (`frontend/src/lib/sons.js`, jamais importé par `src/invite/` : un test parcourt les
  imports). Neuf sons fabriqués par le navigateur (Web Audio), tous en ré majeur : `attente`, `carillon`, `tous_la`,
  `point` (gamme pentatonique, plus haut avec plus de points), `douze`, `tambour`, `depasse`, `fanfare` (motif du
  prélude du *Te Deum* de Charpentier, domaine public, joué par oscillateurs), `applaudissements`. Un seul
  AudioContext, créé au premier geste sur la régie ; gain général (volume × muet) ; rafales espacées d'au moins 90 ms,
  6 voix au plus ; `resume()` au retour sur l'onglet.
  - Écran du QR code : musique d'attente en boucle tant qu'il manque quelqu'un, carillon une fois par invité qui
    arrive (pas pour ceux déjà là à l'ouverture de l'écran), accord « tout le monde est là » une seule fois.
  - Dévoilement : un son par pays (public, et chaque ligne du top 5 du jury), « douze » quand le pays a reçu un 12 ;
    un seul roulement de tambour, du compte à rebours jusqu'au gagnant ; un son par pays dépassé pendant la remontée
    (`DernierVote` : `ondepasse`, au rythme de l'animation, même accélérée) ; fanfare puis applaudissements au gagnant.
  - Haut-parleur sur la télé (muet gardé par l'écran, barré et rose quand il est coupé) ; « Activer le son » quand le
    navigateur le bloque, avec : « Le son se réactive d'un toucher après chaque rechargement. Sur iPhone, le bouton
    silencieux le coupe. »
  - Réglages › Dévoilement : interrupteur « Sons sur la télé », volume, la liste des 9 sons avec « Écouter »,
    « Remplacer par un fichier » (lu dans le navigateur avant l'envoi : refusé s'il ne se lit pas) et « Revenir au son
    de l'appli ».
  - Serveur : réglages `sons` (oui) et `volume_sons` (70), dans la sauvegarde des réglages ; `GET /api/sons`,
    `PUT/GET/DELETE /api/sons/<nom>` (derrière la session, 5 Mo au plus, mp3/m4a/ogg/wav reconnus aux premiers
    octets, un fichier par son dans `<données>/sons/`). Les fichiers ne sont pas dans la sauvegarde des réglages.
- **Compte à rebours « 8b »** avant la remontée du dernier pays (`lib/CompteRebours.svelte`) : 5 → 0, un cadre blanc
  qui se resserre puis le grand chiffre fin au halo rose ; « La révélation dans… » au-dessus ; un voile blanc léger
  après le 0. Mouvement réduit : les chiffres seuls, toujours 6 s. Calé sur l'heure du serveur (`auto.ecoule_ms`,
  d'après `pas_le`) : une télé rechargée pendant le compte reprend au bon chiffre ; après, plus de compte.
  `duree_revelation()` + 6 s ; `revelation_ms` des téléphones compte aussi les 6 s (`compte_ms` à part).
  « Suivant » au toucher est ignoré pendant le compte (télé, téléphone de l'hôte, et serveur sauf `depuis`).
- **Téléphones pendant le compte** : « Regardez la télé » (et rien du dernier pays dans le bandeau), puis la remontée ;
  avant, ils pouvaient montrer le gagnant avant la télé (faille relevée par le conseil).
- **Commentaires dans le classement du téléphone** : sous « 3e · noté 15 », une ligne tronquée de son commentaire
  (rien s'il n'y en a pas) ; un toucher sur la ligne ouvre une feuille en bas (pays, note, commentaire entier) ;
  poignée et flèches inchangées. Lignes de 72 px (avant 56).
- Pas fait : la ligne de commentaire dans l'exemple du mode d'emploi de la télé (les téléphones dessinés sont serrés,
  1.10.3) ; le retrait de l'ancienne route `/api/services` annoncé en 1.10.0 (toujours là).
- Tests : `tests/test_sons_111.py`, `tests/test_sons_invite_111.py`, tests d'écran (compte à rebours, « Regardez la
  télé », commentaire + feuille + glisser, faux AudioContext : sons demandés sur la télé, aucun sur les téléphones,
  Réglages des sons sur PC et iPhone). Tests : 167.
- **Jamais essayé sur la vraie installation** : aucun son n'a été entendu sur une vraie télé (tests avec un faux
  AudioContext seulement).

## 1.10.3 — 20 novembre 2026 (écran télé sur un petit écran en paysage)
- Vu par Julien sur iPhone en paysage (captures du 20/11/2026) :
  - **écran du QR code** : le QR code recouvrait « Mode d'emploi » et le bouton « Rejouer le démarrage » (la barre des boutons flottait par-dessus). La barre a maintenant sa propre place en bas ; le QR code tient dans la place qui reste ;
  - **mode d'emploi** : textes coupés dans les deux téléphones (« Juste au-dess… », « Nor… », note coupée à droite) et « Envoyer mon classement » par-dessus la liste. Les téléphones sont désormais dessinés à l'échelle : tout est en em et leur taille de texte suit leur largeur (sur la télé, la même taille qu'avant).
- Test d'écran : en paysage 844 × 390, aucun bouton sous le QR code, rien de coupé ni de sorti des téléphones, le bouton sous la liste. Tests : 158.
- **Jamais essayé sur la vraie installation.**

## 1.10.2 — 20 novembre 2026 (socle 0.11.1)
- Copies communes du socle 0.11.1 : sur une fiche « Connexion », le titre devient « Pour le relier » quand le réglage se fait dans Réglages de l'appli (et non dans la stack).
- **Jamais essayé sur la vraie installation.**

## 1.10.1 — 20 novembre 2026 (socle 0.11.0)
- `maison.py` et l'interface commune du socle 0.11.0 (guide facultatif d'une fiche « Connexion » ; Douze points n'en a pas besoin).

## 1.10.0 — 20 novembre 2026 (fiches « Connexion » communes, contrat 3)
- L'écran « Connexion » passe à l'écran commun des applis maison (socle 0.10.0, `$lib/services/`) : deux fiches dépliées (carnet, Immich), « Vérifier » ne teste que son service, l'âge du dernier essai est affiché.
- Serveur : registre `SERVICES` (`maison.Services`) et `GET /api/maison/services`, `POST /api/maison/services/{id}/verifier` (session ou `ANNEAU_CLE`, au plus un essai toutes les 30 s, rien d'écrit). La fiche « État » de l'Anneau les lit.
- `maison.py` du socle 0.10.0 (contrat 3). Nouvelle variable facultative `ANNEAU_CLE`.
- L'ancienne route `/api/services` reste en 1.10.0 (plus lue par l'interface) : retirée en 1.11.0. `pages/Services.svelte` est retiré.
- Tests : `tests/test_fiches_connexion.py`.
- **Jamais essayé sur la vraie installation.**

## 1.9.0 — 20 novembre 2026 (dévoilement réglable, À traiter et clôture, résultat officiel pour Gazette, photo apéro, notation)
Réunit deux conversations de Julien du 20/11/2026 (« Bac à sable » et « Journal Eurovision spécial ») ; dossier
`docs/ajout-1.9.0.md`, conseil `docs/conseil-1.9.0.md`.
- **Réglages › Dévoilement** : manuel (tout au toucher, le public aussi) ou automatique, et un temps par étape :
  départ (10 s), jury (15 s), chaque pays du public (5 s), révélation = durée maximum de la remontée (60 s), podium
  (15 s), selfie d'un duo en grand (6 s), mode d'emploi sur la télé (30 s). En automatique, tout s'enchaîne jusqu'aux
  jumeaux ; l'hôte garde Pause, Revenir, Suivant ; changer de mode en plein dévoilement repart de maintenant.
- **Révélation bornée** : remontée plus longue que le temps réglé → rythme accéléré à proportion, pause de 2 s à
  « + 1 point » gardée. La télé dit au serveur quand l'animation est jouée (`suivant` avec `depuis`).
- **La fin du dévoilement n'envoie plus à carnet.** Nouvelle section **À traiter** (nombre sur l'entrée) : vrais votes
  du jury et du public, rang officiel (ex æquo), qualifiés pour une demi-finale (et date de la finale), puis
  **Clôturer la soirée** : envoi à carnet et **résultat officiel** figé (version 1, 2… à chaque nouvelle clôture,
  carnet remplacé). Les soirées déjà dévoilées sont clôturées d'office.
- **Résultat officiel pour Gazette** (« Good Evening Europe! ») : `GET /externe/soirees`,
  `/externe/soirees/<id>/journal[/<version>]`, images figées `…/journal/<version>/image/<sorte>`, jeton commun (porte
  fermée sans lui). Contrat `docs/journal-exemple.json` et `docs/journal-exemple-demi.json` (fabriqués par
  `tools/journal_exemple.py`). Calculs dans `app/resultat.py` : rang moyen des ex æquo, écarts, 3 mieux devinés et 3
  plus ratés, palmarès (plus proche = écart de rang moyen, incomplets à part), demi : qualifiés trouvés, « on les
  pleure », « on les déteste », coup de cœur, nul point, favoris.
- **Fiche** : écart de rang maison / réel en jury, en public et au total, palmarès des invités ; photo apéro à la
  place du logo.
- **Photo apéro** (Images de l'évènement) : prise ou choisie sur le téléphone de l'hôte (HEIC lu), copie réduite qui
  remplace le logo (écran d'accueil, fiche, journal) ; l'original part dans l'album Immich (tag « Apéro »).
- **Notation façon 6b** sur les téléphones : la chanson en grande carte rose entre ses voisines déjà notées (pays,
  titre, note), sa place, combien plus haut et plus bas, « Même note que … ». La notation dit que le mot peut paraître
  dans le magazine de la soirée.
- **Mode d'emploi sur la télé** : quand tous les invités attendus ont choisi leur prénom, l'écran d'accueil montre
  deux téléphones animés (notation, classement) au pas de note de la soirée, 30 s (réglable) ; bouton « Mode d'emploi »
  pour le remontrer.
- Tests : `test_resultat_19.py`, `test_cloture_19.py`, `test_auto_19.py`, `echelle` et `notesExemple` (node), tests
  d'écran (réglages, notation 6b, mode d'emploi, À traiter d'une demi-finale et clôture).


## 1.8.0 — 20 novembre 2026 (public sans cliquer, pays en lice, selfies des duos, saisie directe)
Choix de Julien du 20/11/2026, visuels validés sur un canevas ; dossier `docs/ajout-1.8.0.md`, conseil `docs/conseil-1.8.0.md`.
- **Les points du public passent seuls**, toutes les 5 secondes, avec une barre de temps ; le dernier pays aussi.
  Le top 5 du jury et le podium restent au toucher. L'hôte garde Revenir et Suivant, et gagne **Pause / Reprendre**
  (télé et téléphone de l'hôte). **Revenir** sur un pays met le défilement en pause.
- **Le pas est tenu par le serveur** : les écrans envoient des actions (`suivant`, `revenir`, `pause`, `reprendre`,
  `aller`), jamais un numéro de pas (avant, une lecture vieille d'une seconde pouvait faire reculer le spectacle).
  Une régie qui regarde le dit toutes les 2 s (`POST /api/soirees/<id>/regard`) : sans elle, l'horloge s'arrête et le
  défilement se retrouve en pause (iPhone verrouillé, télé éteinte, dévoilement repris le lendemain). L'écran de la
  régie reste allumé pendant le dévoilement (Wake Lock).
- **Les pays en lice** : au dernier vote, tous les pays se posent sur l'échelle, un par un ; les autres pays n'ont que
  leur drapeau, le pays en tête et le dernier pays gardent nom et drapeau ; puis le dernier pays monte de sa place
  après le jury jusqu'à sa place finale (rythme de la 1.7.0). Quand il dépasse : « Vainqueur » et son avance
  (« + 3 points »). Égalité au sommet : « Égalité », le vainqueur est celui du classement de la soirée. Trop de pays
  pour la hauteur de l'écran : l'échelle est **coupée en deux** (moitié haute à gauche, moitié basse à droite).
  L'animation se joue dès qu'un écran arrive au dernier pas depuis un pas plus tôt (une relecture manquée ne la saute plus).
- **Le bouton des jumeaux est sous le podium** (« Voir les jumeaux de vote »), plus en haut à droite.
- **Le selfie d'un duo s'affiche sur la télé** : en grand 6 s (polaroïd), puis dans la carte du duo. Le serveur en fait
  une vignette JPEG réduite à la réception (Pillow, pillow-heif pour le HEIC), servie à la régie seule
  (`GET /api/soirees/<id>/photos/<photo>`), effacée à l'archivage ; l'original part à Immich comme avant. Le téléphone du
  duo prévient que le selfie s'affiche sur la télé.
- **Saisir sa grille** : toute la liste d'un coup, une case note et une case mot par chanson, points en direct ; puis
  le classement à la main (étape existante). « Passer au classement » attend la fin des enregistrements ; une note hors
  barème le bloque.
- Les relectures de chaque seconde (télé, téléphones, écran des jumeaux) ne prennent plus le tour d'écriture
  (`base.lecture()`).
- Tests : `tests/test_auto_18.py` (temps simulé : défilement, pause, Suivant pile à l'échéance, régie absente, deux
  lectures pendant une écriture longue), `tests/test_photos_ecran_18.py`, calculs `colonnes`, `caseDe`,
  `placesAutres`, `avance`, `dureeEntree` (node), tests d'écran (pays en lice, bouton sous le podium, selfie en grand
  puis dans la carte, saisie directe).


## 1.7.1 — 20 novembre 2026 (plus d'erreurs 500 quand plusieurs téléphones notent en même temps)
- **Correction** : avec plusieurs téléphones qui notaient ou envoyaient en même temps, certaines demandes échouaient en erreur 500 (`sqlite3.OperationalError: database is locked`, journal du Bac à sable du 19/11/2026, 7 téléphones). Une transaction lisait d'abord puis écrivait ; si un autre téléphone avait écrit entre-temps, SQLite refusait l'écriture tout de suite, sans attendre. `base()` prend maintenant le tour d'écriture dès le début (`BEGIN IMMEDIATE`) et attend son tour jusqu'à 30 s (avant : 10 s).
- Tests : `tests/test_verrou_171.py` (8 écritures simultanées : 281 refus sur 320 avant, aucun après ; annulation sur erreur ; 4 téléphones qui notent en même temps que la relecture de l'état).


## 1.7.0 — 19 novembre 2026 (l'animation du dernier vote du public)
- **Le dernier vote du public** se joue comme à la finale de l'Eurovision Asia 2026, sur la télé et sur les téléphones : au centre l'échelle des places, à gauche le pays en tête (« En tête »), à droite le dernier pays (« + X points pour gagner ») qui monte l'échelle très vite, ralentit de la 6e à la 2e place, s'arrête 2 secondes à « + 1 point pour gagner », puis monte d'un coup jusqu'à son total s'il dépasse le premier (« Vainqueur », l'ancien premier glisse en 2e). S'il ne passe pas devant, il s'arrête où il est, « + X » disparaît et « Vainqueur » se pose sur le premier. Cotillons, puis le podium au pas suivant. Choix de Julien du 19/11/2026 (`docs/ajout-1.7.0.md`, `docs/conseil-1.7.0.md`).
- L'animation ne se joue qu'en direct (« Suivant ») ; au rechargement ou pour un téléphone arrivé en retard, la fin s'affiche tout de suite. « Réduire les animations » : la fin directe.
- `frontend/src/lib/dernier.js` (calculs, testés par `node --test` via `tests/test_dernier_js.py`), `frontend/src/lib/DernierVote.svelte` ; test d'écran du dernier vote (télé et téléphone, rechargement).
- Les boutons « Revenir » / « Suivant » du dévoilement restent à l'hôte seul (téléphone connecté) : c'était déjà le cas ; le Bac à sable les montrait sur ses téléphones simulés (corrigé dans le Bac à sable 0.1.5).


## 1.6.2 — 19 novembre 2026 (le jumeau de vote même sans Immich)
- **« Ton jumeau de vote » toujours affiché** sur les téléphones après le dévoilement, même quand Immich n'est pas réglé (clé `DOUZE_POINTS_IMMICH_CLE` absente). Avant, le bandeau entier disparaissait avec les photos. Sans Immich, ni « Immortaliser » ni l'icône 📷 (pas d'album où envoyer). Remarqué par Julien dans le Bac à sable le 19/11/2026.
- Test d'écran : sans clé Immich, le jumeau reste, ni bouton selfie ni icône.

## 1.6.1 — 19 novembre 2026 (ordre des points du public, prénoms des jumeaux)
- **Points du public dans l'ordre du concours** (demande de Julien du 19/11/2026) : au dévoilement, les points du public sont appelés en partant de la chanson **la plus mal placée par le jury** jusqu'à la mieux placée, comme à l'Eurovision. Avant, l'appli partait de la chanson qui recevait le moins de points du public, ce qui laissait deviner le résultat du public. Égalité au jury : la dernière passée d'abord. Sans jury (ou si tout le monde est du jury), rien ne change : de la chanson qui reçoit le moins de points à celle qui en reçoit le plus.
- **Écran des jumeaux de vote** (capture de Julien du 19/11/2026) : les prénoms étaient coupés (« Thiba… », « Grégoire … ») dès quatre duos par ligne, ce qui cachait aussi l'initiale qui distingue deux invités du même prénom. Les deux prénoms sont maintenant l'un sous l'autre (⇅ réciproques, ↓ sinon), en entier, sur deux lignes s'il le faut, jamais « … ».
- Même ordre sur la télé et sur les téléphones (`_marche`, fixé par le serveur). Tests : `test_ordre_du_public_suit_le_classement_du_jury`, `test_ordre_du_public_sans_jury`.

## 1.6.0 — 19 novembre 2026 (jumeaux de vote et photos de la soirée)
- **Jumeaux de vote** (demande de Julien du 19/11/2026, `docs/ajout-1.6.0.md`, conseil `docs/conseil-1.6.0.md`) : une fois le classement figé, chaque invité a son jumeau, l'invité dont les notes ressemblent le plus aux siennes (3 chansons communes au moins). L'accord est dit en tranches (« Jumeaux parfaits », « Très proches », « Proches », « Âmes sœurs… de loin »), jamais en pourcentage, qui laisserait deviner les notes de l'autre.
  - **Télé** : « Terminer » ouvre les résultats sur les téléphones et passe à l'écran « Les jumeaux de vote », tous les duos d'un coup (réciproques d'abord) ; un duo s'allume (📸 immortalisés) dès qu'une photo de lui arrive.
  - **Téléphones** : en tête des résultats, « Ton jumeau de vote : … » (ou « Tu es le jumeau de vote de … ») et le bouton **Immortaliser** (appareil photo en selfie) ; une photo de l'un ou de l'autre suffit à « Immortalisés », on peut en reprendre une.
  - Fiche de la soirée : les duos, le nombre de photos, le nom et le lien de l'album, « Renvoyer maintenant ». Envoi vers carnet : `donnees.jumeau` (prénom, tranche) et `donnees.album` (nom, lien) pour chaque invité.
- **Photos de la soirée** : icône 📷 en haut des écrans des invités, de l'ouverture à l'archivage. Elle propose la photothèque ou l'appareil photo, plusieurs photos d'un coup ; la Pellicule garde une copie. Barre d'avancement ; « Photo envoyée · 7 photos ce soir ». Jamais sur l'appareil connecté à la régie (recopié sur la télé). Les invités ne voient pas les photos des autres.
  - `PUT /invite/<jeton>/api/photo` (JPEG, PNG, WebP, HEIC ; 25 Mo au plus ; 150 par invité et par soirée ; en-tête `X-Duo` pour un duo), écrite sur le disque au fil de la réception dans `/data/photos/<soirée>/`.
  - **Envoi vers Immich côté serveur** (`app/immich.py`, clé `DOUZE_POINTS_IMMICH_CLE`) : image, album « AAAA-MM-JJ titre » créé par l'appli (un seul, même avec deux photos à la fois ; recréé s'il a été supprimé dans Immich), description (« Douze points – titre – photo de … » ou « … jumeaux de vote : A et B »), tags « Douze points » et « Jumeaux de vote » (duos). Reprise à l'étape où chaque photo s'était arrêtée (une image déjà envoyée n'est jamais renvoyée), nouvel essai toutes les 10 minutes (tâche `envoi-immich` dans `/health`), copie du NAS effacée une fois tout fait ; au démarrage, ménage des fichiers sans ligne.
  - Écran Connexion : tuile Immich (version, permissions de la clé).
- Base : `soiree.immich_album`, table `photo`. Variables nouvelles : `DOUZE_POINTS_IMMICH_URL` (défaut `http://immich_server:2283`), `DOUZE_POINTS_IMMICH_CLE`.

## 1.5.0 — 19 novembre 2026 (la soirée envoyée à carnet)
- **Après le dévoilement, la soirée part à carnet 3.1** (décision de Julien du 19/11/2026, dossier « coffre Contacts » v2) : `PUT /evenements/douze-points/soiree-<id>` avec le nom, la date, le lien de la soirée (`#/soiree/<id>`, qui l'ouvre directement) et, pour chaque invité, son identifiant maison (sinon son prénom), sa note moyenne, son classement (rang au classement du groupe de sa chanson n° 1), son podium et ses remarques (5 au plus, les plus sévères d'abord : points donnés de 12 à 0, puis note), que la Gazette reprend pour ses brèves. carnet range la soirée sur la fiche et dans le coffre Contacts ; un invité qu'il ne reconnaît pas va dans son À traiter.
- Un invité choisi dans carnet garde aussi son identifiant maison (`invite.personne_id`) ; pour un invité plus ancien, il est retrouvé dans carnet au moment de l'envoi.
- Envoi raté (carnet arrêté, trop ancien) : gardé et réessayé toutes les 10 minutes ; Réglages › « Envoyer toutes les soirées à carnet » reprend l'historique.

## 1.4.0 — 18 novembre 2026 (santé des tâches de fond)
- **Tâches suivies dans `/health`** (module commun `maison.py` du socle 0.9.1) : `/health` garde ses champs (des nombres, aucun nom) et ajoute `version_socle`, `taches` et `copie_base`. Les messages d'erreur des tâches n'y paraissent qu'avec le jeton commun `MAISON_JETON` ou une session.
  - Douze points n'a ni boucle régulière ni tâche longue à elle (tout se fait pendant la requête) : la seule tâche suivie est `copie-des-bases` (régulière, 24 h).
- **Copie cohérente de la base chaque nuit à 01:20, heure de Paris** : `douze-points.db` copiée par l'API de sauvegarde de SQLite et vérifiée vers `/data/copies/douze-points-derniere.db` (écrasée chaque nuit ; Hyper Backup tient l'historique). Les copies d'avant dévoilement et d'avant suppression (`/data/sauvegardes`) ne changent pas.
- Rien d'autre ne change.

## 1.3.7 — 18 novembre 2026 (réglages secrets reconnus par mots)
- `maison.py` du socle 0.8.2 (audit M3) : les réglages secrets sont reconnus par mots (« motdepasse », « apiKey », « login »…) et une adresse avec identifiant est écartée ; la sauvegarde dit ce qu'elle a écarté (champ `ecartes`, noms seulement).

## 1.3.6 — 18 novembre 2026 (texte de la notification)
- Réglages : la notification Home Assistant est dite **pas encore active** (titre et texte), l'écran ne la promet plus ; « Adresse enregistrée (rien n'est encore envoyé) » (décision du 18/11/2026, Q7 de l'audit). La notification reste une idée.

## 1.3.5 — 18 novembre 2026 (cookies Secure)
- **Cookies `Secure` en https** (audit du 17/11/2026, même correctif dans toutes les applis maison) : ouverte en https (directement, derrière Tailscale Serve qui le dit par `X-Forwarded-Proto`, ou d'après l'origine de la page), l'appli pose ses cookies de session avec l'attribut `Secure` : ils ne partent jamais en clair. En http (adresse locale), rien ne change.
- `entrypoint.sh` refuse de lancer l'appli en root quand `/data` appartient à root (dossier créé par Docker) et dit le remède ; dépannage seulement : `MAISON_ROOT_ACCEPTE=oui`.

## 1.3.4 — 18 novembre 2026 (révocation du cookie commun)
- **« Se déconnecter » dans l'Anneau ferme vraiment la connexion commune** (audit du 17/11/2026, même correctif dans toutes les applis maison) : le cookie commun `maison_session` porte maintenant la génération tenue par l'Anneau (« génération.expiration.signature ») ; « Se déconnecter » l'augmente, et chaque appli la lit dans l'annuaire de l'Anneau (`/externe/services`, au plus une minute de retard) : un cookie commun d'avant la déconnexion ne vaut plus nulle part. Si l'Anneau ne répond pas, le cookie reste accepté comme avant (rien ne se bloque). **Toutes les applis doivent être à jour ensemble** ; une seule reconnexion est demandée après la mise à jour.
- Module commun `maison.py` (socle 0.8.0) : `generation_commune()`, `definir_generation_commune()` ; l'annuaire lit aussi `generation_commune` (une ancienne réponse de l'Anneau, liste seule, reste lue).

## 1.3.3 — 17 novembre 2026 (corrections de l'audit, suite)
- Porte des invités : changer l'en-tête `X-Telephone` à chaque demande ne contourne plus la limite de débit (plafond par téléphone, plus un plafond par adresse égal à 20 téléphones) ; la table des débits est purgée au-delà de 2 000 entrées.

## 1.3.2 — 17 novembre 2026 (connexion plus sûre)
- **Connexion plus sûre** (audit du 17/11/2026, même correctif dans toutes les applis maison) :
  - un cookie portant un caractère non ASCII donnait une erreur 500 sur toute l'API ; il est maintenant simplement refusé ;
  - les clés qui signent les cookies (celui de l'appli et le cookie commun `maison_session` posé par l'Anneau) sont tirées du mot de passe par PBKDF2 : un cookie capté sur le réseau local ne permet plus de chercher le mot de passe à grande vitesse. **Toutes les applis doivent être à jour ensemble** ; une seule reconnexion est demandée après la mise à jour ;
  - des essais de mot de passe lancés en parallèle ne contournent plus le délai : au-delà de 30 essais en 5 minutes, tout est refusé sans comparer.
- Module commun `maison.py` (socle 0.7.0) : l'annuaire de l'Anneau est relu 30 s après un échec (avant : 10 min sans adresses après un redémarrage de la stack) ; un réglage `nan` ou infini est refusé ; un `reglages.json` abîmé est mis de côté (`.corrompu`) au lieu d'être écrasé.

## 1.3.1 — 17 novembre 2026 (corrections de l'audit)
- **Bug** : dans le tableau pour tableur (`fiche.csv`), chaque cellule vide sortait en « ' » (artistes absents, commentaires vides). Elle reste vide ; les débuts de formule (`= + - @`, tabulation, retour chariot) sont toujours désamorcés.
- Deux téléphones qui touchent le même prénom au même instant : seul le premier l'obtient, le second reçoit « déjà pris » (avant, il écrasait le jeton du premier, qui ne pouvait plus noter).
- Un double appui sur « Dévoiler » ne relance plus le tirage de l'ordre pendant l'animation (409 « déjà lancé »).
- Une note `NaN` ou infinie est refusée proprement (422) au lieu d'une erreur 500.
- Intégration continue : l'image n'est plus publiée si les tests échouent.

## 1.3.0 — 17 novembre 2026

- **Écarts et affinités** dans la fiche de la soirée, et sur les téléphones des invités une fois le dévoilement fini : la chanson qui divise et celle qui rassemble (écart entre la plus haute et la plus basse note, trois notes au moins), les deux invités qui notent le plus pareil et ceux qui ne sont d'accord sur rien (écart moyen sur trois chansons communes au moins), le plus sévère et le plus généreux, les coups de cœur solitaires (un 12 sans aucun autre point de personne), les chansons classées à contre-note (les trois plus grands écarts). Rien sous trois invités. Calcul dans `app/points.py` (`affinites`), sur les classements figés au dévoilement.
- **Grille papier de secours** (écran Soirée, « Grille papier », en préparation et pendant la soirée) : une page à imprimer par invité attendu, à son prénom, et une vierge : chansons dans l'ordre de passage, note sur 20, mot, puis les dix lignes du classement.
- **Saisir sa grille** (soirée ouverte, à côté de chaque invité) : l'hôte recopie une grille papier remplie. Un onglet s'ouvre sur l'écran de notation au nom de l'invité ; il note, range et envoie à sa place. Le jeton est dans la partie « # » du lien (jamais envoyé au serveur ni écrit au journal) et reste dans cet onglet : le prénom de l'hôte, gardé par son navigateur, n'est pas touché. Si le téléphone de l'invité tenait son prénom, une confirmation le dit : il perd la main, ses notes restent. `POST /api/soirees/<id>/saisie` (régie seulement, aucune note rendue).
- **Corriger un libellé** de chanson pendant la soirée (crayon dans « Chanson en cours ») : pays, artiste, titre ; l'ordre ne change pas. Un pays vide est refusé, une chanson inconnue répond 404.
- Retirés de la liste, au choix de l'hôte : ordre du dévoilement modifiable, retrait d'un invité à l'écran (déjà possible).
- Tests : `tests/test_affinites.py`, `tests/test_grille.py`, écran `test_grille_papier_saisie_libelle_et_affinites` (PC et iPhone, grille en impression comprise).

## 1.2.0 — 16 novembre 2026

- **Les réglages se changent dans l'appli.** L'adresse du webhook de Home Assistant quitte la stack pour l'écran Réglages, à côté du pas de la note. Au premier démarrage, elle est reprise une fois de `DOUZE_POINTS_HA_WEBHOOK` si la stack la porte encore (une ligne au journal), puis la variable n'est plus lue.
- **Sauvegarde par l'Anneau** : `GET /externe/sauvegarde`, ouvert par le jeton commun seul, rend le pas de la note et la version. Le webhook n'en sort jamais.
- **Restaurer les réglages** dans Réglages : choisir un jour, voir ce qui changerait (avant → sauvegardé), confirmer. Anneau injoignable ou rien de sauvegardé : un message clair.
- **Anciens noms retirés** : `DOUZE_POINTS_PASSWORD` (seul `MAISON_PASSWORD` compte), `DOUZE_POINTS_CARNET_JETON` (seul `MAISON_JETON` part vers carnet), `DOUZE_POINTS_ADRESSE` (l'adresse des invités vient seulement de l'Anneau ; sans lui, pas de QR code et un message le dit).
- Un réglage de mauvais type est refusé avec un message (400) ; rien n'est changé.
- Tests : reprise une seule fois, réglages, porte de sauvegarde (jeton commun seul, rien de secret), restauration, et un écran Réglages vérifié sur PC et sur iPhone.

## 1.1.0 — 16/11/2026

- **Variables communes de la maison** (module `app/maison.py` du socle 0.5.0, copié tel quel) :
  - mot de passe : `MAISON_PASSWORD`, repli sur `DOUZE_POINTS_PASSWORD` (toujours 12 caractères au moins) ;
  - jeton envoyé à carnet (`/douze-points/personnes`) : `DOUZE_POINTS_CARNET_JETON` tant qu'il est dans la stack, puis le jeton commun `MAISON_JETON` (carnet ≥ 2.25.0 l'accepte) ;
  - adresse des invités (QR code, lien) : l'adresse **locale** de la tuile « Douze points » de l'Anneau (`/externe/services`, Anneau 0.7.0), même quand la régie est ouverte par Tailscale, car les téléphones des invités n'y sont pas ; repli sur `DOUZE_POINTS_ADRESSE`.
- Pas de lecture seule : Douze points n'écrit chez aucun service. `DOUZE_POINTS_HA_WEBHOOK` et les liens des invités (`/invite/…`) ne changent pas.
- Rien ne change tant que la stack n'a pas les nouvelles variables : chaque ancien nom reste lu.
- Tests : copie du module non retouchée, mot de passe commun puis repli, jeton envoyé (ancien d'abord), le jeton commun n'ouvre pas la régie, adresse par l'Anneau puis repli.

## 1.0.1 — 15/11/2026

- **Curseur de la note plus gros** : barre épaisse remplie de rose jusqu'à la note, gros bouton rond facile à tenir au pouce (façon A choisie par l'hôte parmi quatre propositions).

## 1.0.0 — 15/11/2026

- **Le dévoilement se joue sur les téléphones.** On ne quitte plus le concours des yeux : chaque invité suit le classement sur son téléphone, l'hôte le mène depuis le sien (« Dévoiler le classement » dans Les invités, puis Revenir / Suivant / Terminer la soirée), même s'il ne note pas lui-même.
  - Départ : le classement de l'invité avec ses points. Puis tous les points du jury d'un coup, puis ceux du public chanson par chanson, de la moins servie à la mieux servie.
  - Chaque ligne : le pays, ses points à lui (Moi), le jury, les autres invités, le total à droite ; les totaux s'additionnent, puis les lignes changent de place.
  - Fin : le podium de la soirée, et sous lui le podium de l'invité (repris en tête de ses résultats).
  - Le téléphone ne reçoit jamais plus que le pas atteint (ni notes ni commentaires avant la fin).
  - L'écran télé reste facultatif et suit les mêmes pas, menés du téléphone ou de lui-même. Le choix « court / complet / jury puis public » disparaît : jury puis public dès qu'il y a les deux.
- **Vrais votes depuis le téléphone de l'hôte**, après le dévoilement ; tous les invités voient la comparaison dans leurs résultats.
- **Fiche imprimée** : bannière, logo et poster de la soirée, et drapeaux en images (Windows n'affiche pas les drapeaux en émoji). Navigation masquée et fond blanc à l'impression.
- **Pas de la note** dans Réglages : au point, au demi-point ou au quart de point. Les notes sont désormais rangées en quarts de point ; une base existante est convertie une fois au démarrage.

## 0.10.1 — 15/11/2026

- **Classement complet au dévoilement** : toutes les chansons tiennent dans la hauteur de l'écran ; les lignes rapetissent sur un iPhone au lieu d'être coupées, et gardent leur taille sur une télé.
- **Glisser vers la droite pour sortir** du dévoilement sur l'iPhone (rappel discret en haut de l'écran sur les écrans tactiles).

## 0.10.0 — 15/11/2026

- **Top 5 du jury** : dans le dévoilement « jury puis public », un écran entre les deux phases montre les cinq meilleurs du jury, du cinquième au premier, avant de passer aux points du public.

## 0.9.2 — 15/11/2026

- **Notation : deux boutons** en bas, « Retour à la liste » et « Suivante » en violet (« Terminer » sur la dernière chanson). Le lien « Retour à la liste » du haut et les boutons Précédente / Enregistrer sont retirés. Les deux boutons enregistrent ce qui a été modifié ; une chanson ouverte sans rien toucher n'est pas notée.

## 0.9.1 — 15/11/2026

- **Le gros bouton des invités suit les étapes** : dans Chansons, « Passer au classement » (en plein quand tout est noté, sinon avec le nombre de chansons qui restent) ; dans Mon classement, « Envoyer mon classement ».

## 0.9.0 — 15/11/2026

- **Pays sans drapeau** : dès la liste enregistrée, une alerte montre les chansons dont le pays n'est pas reconnu. On choisit le pays dans une liste (tous les pays, en français, avec leur drapeau) ; « Retenir ces noms » relie le nom inconnu à ce pays pour les prochaines listes collées. L'alerte reste visible pendant la soirée tant qu'il en manque.
- **Noms officiels reconnus** : « Republic of Korea », « Korea, Republic of », « Russian Federation », « Iran (Islamic Republic of) »…, en anglais et en français.

## 0.8.1 — 15/11/2026

- **Drapeaux pour tous les pays** : la table des noms couvre maintenant tous les pays de la norme ISO, en français et en anglais (« Bhutan » comme « Bhoutan »), plus les noms courants (Corée du Sud, Kosovo, Royaume-Uni, Tchéquie…). Avant, seuls une soixantaine de noms en français étaient reconnus. Un drapeau collé en tête de ligne reste prioritaire.

## 0.8.0 — 15/11/2026

- **Dévoilement plus lisible** : noms et chiffres plus petits, le pays sur une ligne et l'artiste et le titre en dessous, le total toujours visible dans le tableau. Les commandes ne recouvrent plus le titre.
- **Deux couleurs** : le jury en bleu, le public en rose (titre de l'étape, ligne qui reçoit, grands chiffres). En mode « jury puis public », chaque ligne porte une barre fine à deux couleurs : sa part de jury et sa part de public, et une légende en haut.
- **L'addition** : aux points du public, on voit « points du jury + points du public », puis le total qui compte jusqu'à sa nouvelle valeur ; les totaux du tableau comptent aussi au lieu de sauter.
- **Déplacement en deux temps, plus doux** : les points s'ajoutent sur place, puis la ligne glisse à sa nouvelle place (près d'une seconde, mouvement adouci au départ et à l'arrivée).
- **La dernière étape n'est plus sautée** : avant, le podium arrivait à la place de la dernière annonce.
- **Listes collées d'un site de fans** : une ligne « 🇧🇹 Pays: Artiste - Titre » en un seul morceau est découpée (drapeau, pays, artiste, titre). Les soirées déjà saisies ainsi s'affichent découpées elles aussi, sans rien réécrire.

## 0.7.0 — 15/11/2026

- **Plusieurs soirées** : on en crée autant qu'on veut (les deux demi-finales et la finale, par exemple) ; l'écran Soirée en montre la liste, et un clic ouvre celle qu'on veut. Plusieurs peuvent être en cours en même temps, chacune avec son lien, ses invités et ses notes. « Toutes les soirées » ramène à la liste.
- **Rejouer le démarrage** : sur l'écran d'accueil, une icône repart du noir (le « 12 » éteint, le bouton, les projecteurs) jusqu'au QR code, sans rien changer à la soirée.

## 0.6.0 — 15/11/2026

- **Démarrer la soirée** (à la place d'« Ouvrir ») : d'abord un écran dans le noir, le « 12 » éteint et un bouton ; au clic, la soirée s'ouvre aux invités, les projecteurs s'allument sur le « 12 », puis vient l'écran d'accueil avec le QR code.
- **Scène en bannière** en haut de l'écran d'accueil : une rampe de cinq projecteurs dont les faisceaux balaient doucement le « 12 », sans s'arrêter (fixes si l'appareil demande moins d'animations).
- **« Passer à la notation »**, à côté de « Copier le lien » : l'hôte note sur la même page que ses invités. Connecté à la régie, son onglet « Les invités » lui montre en plus combien de chansons chacun a notées et qui a envoyé, sans aucune note ni commentaire, et un lien de retour à la régie.
- **Notation : Précédente, Enregistrer, Suivante.** Changer de chanson enregistre ce qui a été modifié ; une chanson ouverte sans rien toucher n'est plus notée par mégarde.

## 0.5.0 — 15/11/2026

- **Invités choisis dans carnet** : en tapant le début d'un prénom ou d'un nom, carnet propose ses fiches (carnet 2.22.1, adresse `/douze-points/personnes`, jeton `DOUZE_POINTS_CARNET_JETON`). Douze points ne garde que le prénom (avec l'initiale du nom si le prénom est déjà pris). Sans carnet, ou s'il ne répond pas, on ajoute à la main comme avant. Nouvel écran **Connexion** avec la tuile carnet et « Vérifier ».
- **Jury et public** : Réglages › Invités dit qui est du jury ; les autres sont le public. Nouveau dévoilement **« Jury puis public »**, comme au concours : les points du jury chanson par chanson dans l'ordre de passage, puis ceux du public en remontant depuis la dernière du classement du jury. Tous les points comptent pareil ; le rôle de chacun est figé au lancement.
- **Podium** des trois premières à la fin de tout dévoilement, avec des cotillons.
- **Fiche de la soirée** : classement du groupe, du jury et du public, notes et points de chacun, commentaires ; elle s'imprime (ou s'enregistre en PDF) et se télécharge en tableau (CSV). On y saisit plus tard les **vrais votes** du jury et du public : la fiche compare alors notre soirée au concours.
- **Supprimer une soirée** (une soirée d'essai, par exemple), après confirmation ; la base est sauvegardée juste avant.
- **Images** : glisser-déposer d'une image sur sa case.

## 0.4.0 — 15/11/2026

- Réglages › Concours : ajouter un concours à la liste proposée à la création d'une soirée, en retirer un (les soirées déjà faites gardent son nom ; il en reste toujours au moins un). La liste part avec Eurovision et Eurovision Asia.
- Nouvelle soirée : on donne la ville où le concours est organisé, et le titre de l'évènement se fabrique tout seul (« Eurovision Burgas 2027, finale ») ; il reste modifiable.

## 0.3.0 — 15/11/2026

- Images de l'évènement, déposées par l'hôte pendant la préparation ou la soirée : **logo** (à la place du « 12 » sur l'écran d'accueil, l'affiche, les écrans d'attente et le départ du dévoilement), **bannière** (en haut du téléphone des invités), **poster** (écran d'accueil, affiche, écran « Ça commence bientôt »). PNG, JPEG ou WebP, 6 Mo au plus, reconnus à leur contenu ; gardées dans `/data/images`.
- Ouverture animée : trois projecteurs viennent sur le « 12 », qui se met à briller, puis sa lumière révèle la page. Une fois par session, 2,6 secondes, un toucher la passe ; pas jouée si l'appareil demande moins d'animations.

## 0.2.1 — 15/11/2026

- Logo : le « 12 » sous un projecteur (icône de l'appli, écran d'accueil, affiche à partager, départ du dévoilement, écrans d'attente des invités).

## 0.2.0 — 15/11/2026

- Régie : créer une soirée, coller la liste des chansons, choisir et ajouter les invités, écran d'accueil (« 12 », nom de l'évènement, QR code), copier le lien, partager l'affiche en image, ouvrir la soirée, suivre qui a envoyé, libérer un prénom, tenir la chanson en cours, forcer, archiver, rejouer une soirée passée.
- Invités : « Ça commence bientôt », choix du prénom, notation (curseur et demi-points, commentaire), classement à glisser par la poignée ou aux flèches, envoi, modification, résultats après le dévoilement.
- Dévoilement en paysage : court (8, 10, 12) ou complet, « Douze points » en grand, tableau qui se réordonne, Revenir, Tout afficher, podium ; le pas est gardé côté serveur.
- Serveur : QR code du lien des invités.
- Tests d'écran : une soirée entière jouée dans un navigateur, sur PC, téléphone et paysage.

## 0.1.0 — 15/11/2026

- Serveur : soirées, liste des chansons (saisie ou collage), invités, porte invité par jeton (prénom, notes sur 20 par demi-points, commentaires, classement fait à la main ou d'après les notes, envoi), forcer le dévoilement, points gelés au barème 12-10-8…1, départage des égalités, sauvegarde de la base avant le dévoilement.
- Tests : calcul, parcours d'une soirée, secret de la porte invité.
- Interface : copie du socle (connexion, réglages) et liste des soirées. Les écrans viennent ensuite.

## Conception — 15/11/2026

- Dossier de conception v0.2 et compte rendu du conseil.
- Dossier v0.3 : écran d'accueil de la soirée (logo, nom, QR code) à recopier sur la télé et à partager ; port 8088 ; tuile dans l'Anneau.
