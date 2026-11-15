# Journal des versions

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
