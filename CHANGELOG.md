# Journal des versions

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
