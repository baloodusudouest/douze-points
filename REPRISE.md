# Reprise — Douze points

À lire en premier. Mis à jour le 22/11/2026, version 1.13.1.

## Où on en est

- **1.13.1 (22/11/2026)** : `image_deposer` accepte le HEIC (`_format_photo`, conversion `ecran.vignette` en JPEG,
  `ecran.COTE_IMAGE`) ; `Images.svelte` (accept, extension .heic au glisser-déposer). `Soiree.svelte` : `basculer`
  optimiste, `fileAttendus` (envois en file, `demarrer` l'attend). GET soirées, soirée, invités en `lecture()`.
  `lire_collage` : ordre de passage en tête de ligne (rangement si complet et sans doublon). **Jamais essayé sur la
  vraie installation.**
- **1.13.0 (22/11/2026)** : « ? » du collage (`pages/PromptListe.svelte`, monté dans `Soiree.svelte` avec
  l'intitulé en `children`) ; `lire_collage` lit jury, public, rang (`_nombre_colle`), saute l'en-tête et les « ``` » ;
  `chansons_remplacer` les écrit dans `officiel_*`. Tests : `tests/test_collage_113.py`. **Jamais essayé sur la vraie
  installation.** Bac à sable pas mis à jour.
- **1.12.0 (22/11/2026)** : notre pays, sans points (`docs/ajout-1.12.0.md`).
  - Réglage `notre_pays` (FR par défaut, vide = aucun). `main.py`, section « 1.12 » : `CODES_PAYS`
    (`app/pays_codes.json`, refait par `python tools/pays_codes.py` après toute modification de `lib/pays.js`),
    `code_de`, `exclues(s, chansons)` (réglage avant le dévoilement, colonne `chanson.hors_points` ensuite),
    `_avec_marque`, `_notre_pays_bilan`. `devoiler` pose `hors_points` et appelle `points_du_classement(ordre, hors)`.
    `_devoilement` : `classement` sans notre pays, `notre_pays` ; `_marche` ne l'appelle pas et dit `notre_pays` ;
    `_duree_pas` : podium + `NOTRE_PAYS_S`. `_fiche` / `_resultat` : comparaisons avec `resultat.sans_exclues` et
    `points.rerang`. Contrat du journal : `chansons[].hors_points`, `notre_pays` (exemples refaits).
  - Interface : `lib/NotrePays.svelte` ; `pointsDuClassement` (`lib/pays.js`) dans `invite/Invite.svelte` et
    `invite/SaisieGrille.svelte` ; `Devoilement.svelte` (`d.notres`, `vueNotre` au bout de `duree_podium`) ;
    `Spectacle.svelte` (`n.notres`) ; `Fiche.svelte` (`rangSansNous`) ; `Reglages.svelte` (section Notre pays) ;
    `Grille.svelte`, `Soiree.svelte`, `VraisVotes.svelte`.
  - **Jamais essayé sur la vraie installation.** Bac à sable pas mis à jour (choix de Julien : plus tard).

- **1.11.0 (20/11/2026)** : `docs/ajout-1.11.0.md`, `docs/conseil-1.11.0.md`.
  - Sons de la télé : `lib/sons.js` (seul module audio ; `installer()` dans `App.svelte`, `regler()` sur chaque écran
    de la télé, `jouer`, `boucle`/`arreter`, `enchainer`, `ecouterSon`, `decoder` ; `window.__DOUZE_POINTS_SONS` note
    les sons demandés pour les tests). **Ne jamais l'importer depuis `src/invite/`** (`tests/test_sons_invite_111.py`
    parcourt les imports). `lib/BoutonSon.svelte` (haut-parleur, « Activer le son ») dans `Accueil` et `Devoilement`.
  - Serveur (`main.py`, section « 1.11 ») : `SONS`, `SON_MAX`, `_type_son`, routes `/api/sons…`, fichiers dans
    `<données>/sons/` ; réglages `sons`, `volume_sons`.
  - Compte à rebours : `COMPTE_REBOURS` (6 s) dans `duree_revelation` ; `_pas_auto` rend `auto.ecoule_ms` (temps passé
    dans le pas effectif) ; `POST /pas` ignore `suivant` sans `depuis` pendant le compte. `lib/CompteRebours.svelte`
    monté par `Devoilement` (`aller(n, ecoule)`, `compte`, `finCompte`, voile) ; `Spectacle` : `regardezTele`,
    `compte_ms`, remontée en `revelation_ms - compte_ms`.
  - Classement du téléphone : `HAUTEUR = 72`, `feuille` (id de la chanson montrée) dans `invite/Invite.svelte`.
  - **Jamais essayé sur la vraie installation** : aucun son entendu sur une vraie télé (ni en recopie AirPlay, ni le
    bouton silencieux de l'iPhone, ni un fichier mp3/m4a de l'hôte lu par Safari), le compte à rebours sur la télé,
    la feuille du commentaire sous un vrai doigt. La fanfare est écrite de mémoire : à écouter. Bac à sable pas mis à
    jour ici.

- **1.10.3 (20/11/2026)** : petit écran en paysage. `Accueil.svelte` : barre des boutons sortie du flux fixe (elle a sa place sous la grille), QR code `height: min(50vh, 70vw); max-height: 100%` dans une rangée `minmax(0,1fr)`. `ModeEmploi.svelte` : `.tel` à l'échelle (`--l`, `font-size: calc(var(--l) / 24)`, tout en em, rangées du classement en 1,9 em). Test : fin du bloc « mode d'emploi » de `test_une_soiree_entiere` (paysage). **Jamais essayé sur la vraie installation.**
- **1.10.2 (20/11/2026)** : copies communes du socle 0.11.1 (titre « Pour le relier » quand le réglage est dans l'appli).
- **1.10.1 (20/11/2026)** : copies communes du socle 0.11.0 (guide facultatif des fiches).
- **1.10.0 (20/11/2026)** : fiches « Connexion » communes (contrat 3, socle 0.10.0) : `SERVICES` dans `main.py` (section « fiches Connexion »), `maison.monter_services` après la garde, écran `$lib/services/Services.svelte` (commun, signé : ne pas le retoucher ici). Ancienne `/api/services` à retirer en 1.11.0. **Jamais essayé sur la vraie installation.**
- **1.9.0 (20/11/2026)** : `docs/ajout-1.9.0.md`, `docs/conseil-1.9.0.md`.
  - Réglages (`REGLAGES_DEFAUTS`, `DUREES`, `reglages.json`) : `devoilement_auto`, `duree_*`. Changer de mode remet
    `pas_le` des dévoilements en cours.
  - `_duree_pas`, `duree_revelation(nb)`, `_pas_auto` (toutes les étapes, `auto.terminer` après le podium, `auto.mode`),
    `/regard` termine le dévoilement quand le podium a eu son temps, `POST /pas` `suivant` + `depuis`, `devoiler` lance
    l'horloge. `terminer` idempotent, sans carnet.
  - Clôture : `soiree.cloturee_le`, `chanson.officiel_rang`, `chanson.officiel_qualifie`, `journal_soiree`, `GET
    /api/a-traiter`, `POST /api/soirees/<id>/cloturer`, `_resultat()` (contrat `resultat.VERSION_CONTRAT` = 1),
    `_figer_images` (`/data/journaux/<soirée>/<version>/`), routes `/externe/soirees…` (`_porte_externe`). Contrat :
    `docs/journal-exemple*.json`, refaits par `python tools/journal_exemple.py` (un test compare les clés).
  - Photo apéro : `PUT /api/soirees/<id>/apero`, sorte d'image `apero`, ligne `photo` (participation 0, `apero=1`),
    tag « Apéro ». `ecran.vignette(…, cote)`.
  - Interface : `pages/ATraiter.svelte` (entrée « À traiter » dans `App.svelte`, pastille), `Reglages.svelte` (section
    Dévoilement), `Images.svelte` (photo apéro), `Fiche.svelte` (écarts, palmarès), `lib/dernier.js` (`echelle`,
    `dureePlan`, `notesExemple`), `DernierVote` (`maxMs`, `onfini`), `Devoilement` (réglages, `finRevelation`, fin
    auto du podium, « Suite dans N s »), `Spectacle` (`revelation_ms`), `EcranJumeaux` (`dureeSelfie`),
    `invite/Invite.svelte` (notation 6b : `voisins`, snippet `voisine`), `lib/ModeEmploi.svelte` + `Accueil.svelte`.
  - **Jamais essayé sur la vraie installation** : tout. Bac à sable pas mis à jour (choix de Julien ; il a la 1.7.1).
    Gazette 0.28.0 (le magazine) se construit sur le contrat `docs/journal-exemple.json`.
- **1.8.0 (20/11/2026)** : `docs/ajout-1.8.0.md`, `docs/conseil-1.8.0.md`.
  - Serveur (`main.py`, section « 1.8 ») : `horloge()` (remplacée en test), `_pas_auto(s, marche, t)` → pas effectif +
    `auto {actif, pause, prochain_dans, duree}` (dans `_devoilement`), `POST /pas` par actions, `POST /regard`
    (`vu_le`, `GARDE_REGIE` 4 s), colonnes `soiree.pas_le`, `pause_auto`, `vu_le`. `invite_devoilement` rend `auto` et,
    au dernier pas, `gagnant`. `base.lecture()` pour `devoilement`, `invite_devoilement`, `invite_etat`, `jumeaux_regie`,
    `photo_ecran` (ne jamais écrire dedans).
  - Selfies : `app/ecran.py` (`vignette`, Pillow + pillow-heif), colonne `photo.ecran`, `_jumeaux` rend `photo`,
    `GET /api/soirees/<id>/photos/<id>`, `_effacer_vignettes` à l'archivage, `nettoyer_photos` les connaît.
  - Interface : `lib/dernier.js` (`colonnes`, `caseDe`, `placesAutres`, `avance`, `dureeEntree`), `lib/DernierVote.svelte`
    (phase d'entrée, drapeaux seuls, deux colonnes, avance, égalité, `gagnant`), `pages/Devoilement.svelte` (`agir`,
    `appliquer`, `relire` à l'échéance, regard, Wake Lock, barre de temps, Pause, bouton des jumeaux sous le podium),
    `invite/Spectacle.svelte` (actions, regard et Wake Lock pour l'hôte), `pages/EcranJumeaux.svelte` (file, en grand
    6 s, carte), `invite/SaisieGrille.svelte` (branché dans `Invite.svelte` en mode saisie, `passer()`).
  - **Jamais essayé sur la vraie installation** : le défilement sur la télé en recopie AirPlay, le Wake Lock sur l'iPhone
    de l'hôte, un vrai selfie d'iPhone (HEIC ou JPEG) sur la télé, la saisie sur iPhone. Bac à sable pas encore mis à
    jour (choix de Julien : plus tard ; Douze points 1.8.0, commit à reporter dans `applis.yaml`).
  - Plus tard (conseil) : Home Assistant au changement de pays et au vainqueur, générique de fin des selfies, selfies
    dans Gazette et carnet, avance gardée en base, rejouer une soirée en accéléré dans le Bac à sable (`horloge`).
- **1.7.1 (20/11/2026)** : `app/base.py`, `base()` en `BEGIN IMMEDIATE` (`isolation_level = None`, `COMMIT` / `ROLLBACK` à la main), `ATTENTE = 30` s. Corrige les 500 « database is locked » (plusieurs téléphones qui écrivent). Tests : `tests/test_verrou_171.py`. **Jamais essayé sur la vraie installation** (vu dans le Bac à sable seulement). À venir : 1.8.0 (public automatique, pays en lice, photo du duo à l'écran, bouton des jumeaux sous le podium, saisie de grille directe), visuels validés le 20/11/2026.
- **1.7.0 (19/11/2026)** : animation du dernier vote du public (`lib/dernier.js` pur et testé par node, `lib/DernierVote.svelte`) montée au dernier pas du public par `pages/Devoilement.svelte` (télé, `dernierPas`, `animerDernier` posé dans `aller()` quand on vient du pas d'avant, totaux = `cumul(pas)`) et `invite/Spectacle.svelte` (téléphone, `animerDernier` posé dans `lire()` quand ce téléphone a vu le pas d'avant). Rythme réel `RYTHME` ; tests d'écran accélérés par `window.__DOUZE_POINTS_RYTHME`. **Jamais essayé sur la vraie installation** : la télé en recopie AirPlay (fluidité), de vrais iPhone.
- **1.6.2 (19/11/2026)** : `invite/Jumeaux.svelte` reçoit `photos` ; le jumeau s'affiche toujours (`Invite.svelte`), « Immortaliser » seulement si Immich est réglé. Test dans `test_ecrans.py`.
- **1.6.1 (19/11/2026)** : points du public appelés de la chanson la plus mal placée par le jury à la mieux placée (`main._marche`, avant : points du public croissants). Sans jury : points reçus croissants. Tests dans `tests/test_devoilement_telephones.py`. `pages/EcranJumeaux.svelte` : prénoms l'un sous l'autre, jamais coupés (capture de Julien).
- **1.6.0 (19/11/2026)** : jumeaux de vote et photos de la soirée vers Immich (`docs/ajout-1.6.0.md`, conseil `docs/conseil-1.6.0.md`). `app/points.py` : `jumeaux`, `duos`, `tranche` (purs). `app/immich.py` : un appel par fonction, `CLIENT` remplacé par un faux Immich dans les tests. `main.py`, section « 1.6 » : `_jumeaux` (participants qui ont des points), `invite_photo` (corps brut écrit au fil de l'eau, `X-Duo`), `envoyer_photos` (verrou, étapes `immich_id` → `dans_album` → `decrite` → `taguee`), `_boucle_immich` (tâche `envoi-immich`, 600 s), `nettoyer_photos` (démarrage), `GET /api/soirees/<id>/jumeaux`, `POST /api/photos/envoyer` ; `etat.photos`, `resultats.jumeaux`, carnet `donnees.jumeau` / `donnees.album`. Interface : `invite/Photo.svelte` (XHR, sans `capture` + `multiple` ; `capture="user"` pour Immortaliser), `invite/Jumeaux.svelte`, `pages/EcranJumeaux.svelte` (après « Terminer »), section de la Fiche. Rien sur l'appareil connecté à la régie. Tests : `tests/test_photos_16.py`, `test_ecrans.py` (photo, jumeau, immortalisés). **Jamais essayé sur la vraie installation** : voir « Essais à faire sur place ».
- **1.5.0 (19/11/2026)** : la soirée dévoilée part à carnet 3.1. `main.py`, section « 1.5 » : `ENVOYER_CARNET` (= `carnet.envoyer`, remplacé dans les tests), `_corps_soiree` (d'après `_fiche` : moyenne, classement = rang du groupe de la chanson n° 1 de l'invité, top3, remarques (commentaires, 5 au plus, triés par points donnés puis note) ; identifiant `invite.personne_id`, sinon retrouvé par `carnet_id` dans la liste de carnet), `envoyer_soiree` (appelé par `terminer`), table `envoi_carnet` (nouvel essai, `renvoyer_a_carnet`, `_boucle_carnet` toutes les 10 min), route `POST /api/carnet/envoyer`. `invite_ajouter` garde `personne_id`. Interface : `#/soiree/<id>` (App.svelte, Soiree.svelte), bloc « Envoi vers carnet » (Réglages). Tests : `tests/test_carnet_15.py`. Jamais essayé sur la vraie installation.

- **1.4.0 (18/11/2026)** : santé des tâches de fond (socle 0.9.0, `app/maison.py` recopié, ne pas le modifier). `main.cycle` lance `maison.planifier_copie("douze-points", [base.fichier(data)], <data>/copies, "01:20")` (tâche asyncio annulée à l'arrêt) ; aucune autre tâche déclarée (pas de boucle de fond ni de tâche longue). `/health` fusionne `maison.sante(request, jeton_commun=maison.jetons(), session_ok=...)`. Un seul worker uvicorn (registre en mémoire). Tests : `tests/test_sante_taches.py` ; `test_sante_inchangee` et `test_sante_publique_sans_aucun_nom` relisent les anciens champs et acceptent les nouveaux. **Jamais essayé sur la vraie installation** (ni la copie de nuit, ni la remise en place d'une copie).
- **1.3.0 (17/11/2026)** : écarts et affinités (fiche + téléphones après le dévoilement), grille papier à imprimer, « Saisir sa grille » par l'hôte, correction d'un libellé soirée ouverte. Voir CHANGELOG et `docs/dossier.md` (Ajouts de la 1.3.0).
  - `app/points.py` : `affinites()` (pur, testé seul) ; `app/main.py` : `_fiche` → `affinites`, `invite_resultats` → `affinites`, `POST /api/soirees/<id>/saisie`, `chanson_corriger` (pays vide 422, chanson inconnue 404).
  - Frontend : `lib/Affinites.svelte`, `pages/Grille.svelte`, `pages/Soiree.svelte` (boutons Grille papier, Saisir sa grille, crayon des libellés), `invite/Invite.svelte` (mode saisie : `sessionStorage`, bandeau « Grille papier de … »).
  - **Jamais essayé sur la vraie installation** : impression réelle de la grille, ouverture de l'onglet de saisie sur iPhone (Safari et les fenêtres ouvertes par une page), affinités avec de vraies notes.
- **1.2.0 (16/11/2026)** : réglages dans l'appli, sauvegarde et restauration ; anciens noms retirés. Module `app/maison.py` au contrat 2 (copie du socle, ne pas le modifier ici).
  - `app/config.py` : `maison.mot_de_passe()` seul (« MAISON_PASSWORD est absent ou trop court… »), `carnet_jeton = maison.jeton_a_envoyer()` seul. Plus de champs `adresse` ni `ha_webhook` dans `Config`.
  - `app/main.py`, bloc « réglages d'usage (1.2) » : `pas_note` reste dans la table `reglage` ; `ha_webhook` est dans `/data/reglages.json` (`maison.Reglages`, repris une fois de `DOUZE_POINTS_HA_WEBHOOK`, ligne `reglage_repris` au journal avec le nom de la variable, jamais la valeur). `GET/PUT /api/reglages` (400 si mauvais type), `GET/POST /api/restaurer` (faux Anneau dans les tests : `main.LIRE_ANNEAU`), `GET /externe/sauvegarde` (jeton commun ; `EXCLUS_SAUVEGARDE = ("ha_webhook",)`).
  - `main.adresse()` : l'annuaire de l'Anneau seul, toujours l'adresse locale ; sans Anneau : pas de QR code (409, message `SANS_ADRESSE`).
  - `frontend/src/pages/Reglages.svelte` : sections « Notification Home Assistant » et « Restaurer les réglages ».
  - Tests : `tests/test_reglages.py`, `tests/test_maison.py`, écran `test_reglages_webhook_et_restaurer` (PC et iPhone).
  - **Déploiement en deux temps** : d'abord la nouvelle image avec la stack actuelle (les réglages sont repris des anciennes variables au premier démarrage), vérifier Réglages, puis la nouvelle stack sans les anciennes lignes (`DOUZE_POINTS_PASSWORD`, `DOUZE_POINTS_CARNET_JETON`, `DOUZE_POINTS_ADRESSE`, `DOUZE_POINTS_HA_WEBHOOK`). Attention : la 1.2 ne lit plus `DOUZE_POINTS_PASSWORD` ni `DOUZE_POINTS_CARNET_JETON` : `MAISON_PASSWORD` et `MAISON_JETON` doivent être dans la stack avant la nouvelle image, et la tuile « Douze points » de l'Anneau doit avoir son adresse locale, sinon pas de QR code.
  - **Jamais essayé sur la vraie installation** (ni la reprise, ni la collecte par l'Anneau, ni la restauration).
- **1.1.0 (16/11/2026)** : variables communes (module `app/maison.py`, copie du socle 0.5.0 : ne pas le modifier ici, `python tools/diffuser_maison.py ../douze-points` depuis le socle). `config.charger` lit `MAISON_PASSWORD` (repli `DOUZE_POINTS_PASSWORD`) et le jeton pour carnet par `maison.jeton_a_envoyer("DOUZE_POINTS_CARNET_JETON")` ; `main.adresse()` + `ANNUAIRE` donnent l'adresse des invités (tuile « Douze points », toujours la locale, repli `DOUZE_POINTS_ADRESSE`). Aucune porte ne reçoit de jeton d'une autre appli ; pas de lecture seule. Jamais essayé sur la vraie installation : les nouvelles variables ne sont pas encore dans la stack (tout passe par les anciens noms). Tests : `tests/test_maison.py`.
- Dossier v0.3 (`docs/dossier.md`, avec les décisions prises en codant en fin de fichier), conseil passé (`docs/conseil.md`).
- **Une soirée se joue de bout en bout** : préparer, écran d'accueil et QR code, ouvrir, noter et classer sur les téléphones, envoyer, forcer, dévoiler en paysage, résultats sur les téléphones, archiver, rejouer.
- **Jamais essayé sur la vraie installation**, ni sur un vrai iPhone : tout a été vu dans le navigateur des tests (PC, 390 × 844, 844 × 390). Le glisser au doigt, la recopie d'écran et le partage de l'image depuis Safari en http restent à constater.
- Atlas est à jour (1.6.12) : service dans `data/homelab.yml`, tuile dans `data/anneau-services.yaml`, fiche et flux. **Le déploiement sur le NAS reste à faire par l'hôte** (stack Portainer, adresse locale de la tuile « Douze points » dans services.yaml de l'Anneau). Atlas est à recopier depuis le coffre pour la 1.2 (variables retirées).

## Où est quoi

- `app/points.py` : le calcul seul (classement d'un invité, barème, départage du groupe).
- `app/base.py` : schéma SQLite, sauvegarde de la base (au dévoilement).
- `/data/reglages.json` : réglages d'usage hors base (webhook de Home Assistant).
- `/data/sons/` (1.11) : les fichiers de son de l'hôte (`<nom>.<ext>`, un par son), hors sauvegarde des réglages.
- `frontend/src/lib/sons.js` (1.11) : tous les sons, sur la télé et les Réglages seulement.
- `app/main.py` : la régie sous `/api/…` (mot de passe commun), la porte invité sous `/invite/<jeton>/api/…` (en-tête `X-Telephone` : le jeton personnel du téléphone).
- `frontend/src/pages/` : la régie (`Soiree`, `Accueil`, `Devoilement`) ; `frontend/src/invite/Invite.svelte` : le téléphone des invités ; `main.js` choisit selon l'adresse.
- `tests/test_ecrans.py` : une soirée entière dans un navigateur (`CAPTURES=/un/dossier` garde des captures).
- `app/carnet.py` : lecture de carnet (prénoms et noms), remplacée par un faux dans les tests.
- `frontend/src/pages/Fiche.svelte` : la fiche de la soirée ; `Services.svelte` : l'écran Connexion.
- `tests/test_secret.py` : avant la fin du dévoilement, la porte invité ne rend rien des autres. **Toute nouvelle adresse sous `/invite/` doit y être ajoutée**, sinon le test échoue.

## Prochaine étape

1. Déployée sur le NAS le 16/11/2026 (1.2.0) : mettre la 1.3.0 (tirer `:latest`, redémarrer, aucune variable nouvelle), puis essais sur place (grille imprimée, saisie depuis l'iPhone).
2. Soirée d'essai avec de vrais invités.
3. Notification par Home Assistant quand tous ont envoyé (master doc à relire et compléter).

Fait depuis la 0.3 : concours réglables, ville et titre fabriqué, carnet, jury et public, podium, fiche de la soirée avec vrais votes, suppression.

Petits manques connus : aucun noté (l'ordre du dévoilement reste tiré au sort, choix de l'hôte du 17/11/2026).

## Essais à faire sur place avant la première soirée

- **1.6 (photos)** : créer la clé Immich « douze-points » (permissions dans le README), poser `DOUZE_POINTS_IMMICH_CLE`, Connexion › Vérifier ; sur un iPhone d'invité en http : l'icône 📷 propose Photothèque / Prendre une photo, plusieurs photos partent (format reçu : HEIC ou JPEG, poids) ; « Immortaliser » ouvre bien l'appareil en selfie ; verrouiller l'écran pendant un envoi ; dans Immich : album « AAAA-MM-JJ titre », date des photos, description, tags « Douze points » et « Jumeaux de vote » ; arrêter Immich, envoyer, le redémarrer : la photo arrive au tour suivant ; sur la télé (iPhone de l'hôte recopié) : pas d'icône photo, écran des jumeaux lisible.
- un téléphone qui n'est pas du foyer ouvre l'appli sur le Wi-Fi de la maison ;
- le dévoilement sur l'iPhone en paysage, recopié sur la télé ;
- la notification par Home Assistant.

## Points ouverts

Voir `docs/dossier.md` § 7 : service de notification, logo de l'affiche, source du futur import.

## Échéance

Soirée d'essai avec de vrais invités en février ou mars 2027 ; demi-finales les 11 et 13 mai 2027, finale le 15 mai.
