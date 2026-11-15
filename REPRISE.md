# Reprise — Douze points

À lire en premier. Mis à jour le 15/11/2026, version 0.1.0.

## Où on en est

- Dossier v0.3 (`docs/dossier.md`, avec les décisions prises en codant en fin de fichier), conseil passé (`docs/conseil.md`).
- **Serveur écrit et testé** (`app/`) : soirées, liste des chansons (saisie ou collage), invités, porte invité (prénom, notes, classement, envoi), forcer, gel des points au barème 12-10-8…1, données du dévoilement, `/health`.
- **Interface : presque rien.** Copie du socle renommée (couleur, icône, connexion, réglages) et une page qui liste les soirées. Aucun écran pour préparer une soirée, noter ou dévoiler.
- **Jamais essayé sur la vraie installation.** L'appli n'est pas dans la stack.

## Où est quoi

- `app/points.py` : le calcul seul (classement d'un invité, barème, départage du groupe).
- `app/base.py` : schéma SQLite, sauvegarde.
- `app/main.py` : la régie sous `/api/…` (mot de passe commun), la porte invité sous `/invite/<jeton>/api/…` (en-tête `X-Telephone` : le jeton personnel du téléphone).
- `tests/test_secret.py` : avant la fin du dévoilement, la porte invité ne rend rien des autres. **Toute nouvelle adresse sous `/invite/` doit y être ajoutée**, sinon le test échoue.

## Prochaine étape

Les écrans, dans cet ordre (plan du dossier, § 6) :

1. régie : préparer une soirée (liste, invités), écran d'accueil avec QR code, partage ;
2. invité : prénom, notation, classement à glisser, envoi ;
3. régie : états en direct, forcer, dévoilement (court, complet, « Tout afficher »).

Puis synthèse, vrai résultat, grille papier ; soirée d'essai ; notification Home Assistant ; PDF ; entrée dans la stack (port 8088), Atlas, tuile de l'Anneau.

Restent à écrire côté serveur : l'affiche (QR code et image à partager), la synthèse (écarts et affinités), le vrai résultat, la notification, le PDF.

## Essais à faire sur place avant la première soirée

- un téléphone qui n'est pas du foyer ouvre l'appli sur le Wi-Fi de la maison ;
- le dévoilement sur l'iPhone en paysage, recopié sur la télé ;
- la notification par Home Assistant.

## Points ouverts

Voir `docs/dossier.md` § 7 : service de notification, logo de l'affiche, source du futur import.

## Échéance

Soirée d'essai avec de vrais invités en février ou mars 2027 ; demi-finales les 11 et 13 mai 2027, finale le 15 mai.
