# Reprise — Douze points

À lire en premier. Mis à jour le 15/11/2026, version 0.4.0.

## Où on en est

- Dossier v0.3 (`docs/dossier.md`, avec les décisions prises en codant en fin de fichier), conseil passé (`docs/conseil.md`).
- **Une soirée se joue de bout en bout** : préparer, écran d'accueil et QR code, ouvrir, noter et classer sur les téléphones, envoyer, forcer, dévoiler en paysage, résultats sur les téléphones, archiver, rejouer.
- **Jamais essayé sur la vraie installation**, ni sur un vrai iPhone : tout a été vu dans le navigateur des tests (PC, 390 × 844, 844 × 390). Le glisser au doigt, la recopie d'écran et le partage de l'image depuis Safari en http restent à constater.
- Atlas est à jour (1.6.12) : service dans `data/homelab.yml`, tuile dans `data/anneau-services.yaml`, fiche et flux. **Le déploiement sur le NAS reste à faire par l'hôte** (stack Portainer, variable DOUZE_POINTS_ADRESSE, services.yaml de l'Anneau).

## Où est quoi

- `app/points.py` : le calcul seul (classement d'un invité, barème, départage du groupe).
- `app/base.py` : schéma SQLite, sauvegarde.
- `app/main.py` : la régie sous `/api/…` (mot de passe commun), la porte invité sous `/invite/<jeton>/api/…` (en-tête `X-Telephone` : le jeton personnel du téléphone).
- `frontend/src/pages/` : la régie (`Soiree`, `Accueil`, `Devoilement`) ; `frontend/src/invite/Invite.svelte` : le téléphone des invités ; `main.js` choisit selon l'adresse.
- `tests/test_ecrans.py` : une soirée entière dans un navigateur (`CAPTURES=/un/dossier` garde des captures).
- `tests/test_secret.py` : avant la fin du dévoilement, la porte invité ne rend rien des autres. **Toute nouvelle adresse sous `/invite/` doit y être ajoutée**, sinon le test échoue.

## Prochaine étape

1. Déploiement sur le NAS, puis premier essai sur place (voir les essais plus bas).
2. Synthèse de la soirée (écarts et affinités), vrai résultat, grille papier de secours.
3. Soirée d'essai avec de vrais invités.
4. Notification par Home Assistant (master doc à relire et compléter), puis PDF.

Petits manques connus : ordre du dévoilement non modifiable ; pas de correction d'un libellé de chanson à l'écran après l'ouverture (l'adresse existe côté serveur) ; pas de retrait d'un invité de la liste à l'écran.

## Essais à faire sur place avant la première soirée

- un téléphone qui n'est pas du foyer ouvre l'appli sur le Wi-Fi de la maison ;
- le dévoilement sur l'iPhone en paysage, recopié sur la télé ;
- la notification par Home Assistant.

## Points ouverts

Voir `docs/dossier.md` § 7 : service de notification, logo de l'affiche, source du futur import.

## Échéance

Soirée d'essai avec de vrais invités en février ou mars 2027 ; demi-finales les 11 et 13 mai 2027, finale le 15 mai.
