# Reprise — Douze points

À lire en premier. Mis à jour le 17/11/2026, version 1.3.0.

## Où on en est

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

- un téléphone qui n'est pas du foyer ouvre l'appli sur le Wi-Fi de la maison ;
- le dévoilement sur l'iPhone en paysage, recopié sur la télé ;
- la notification par Home Assistant.

## Points ouverts

Voir `docs/dossier.md` § 7 : service de notification, logo de l'affiche, source du futur import.

## Échéance

Soirée d'essai avec de vrais invités en février ou mars 2027 ; demi-finales les 11 et 13 mai 2027, finale le 15 mai.
