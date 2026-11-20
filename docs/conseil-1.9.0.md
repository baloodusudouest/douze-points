# Douze points 1.9.0 — conseil (20/11/2026)

Cinq conseillers (Contradicteur, Premiers principes, Expansionniste, Œil extérieur, Exécutant), relecture croisée
anonyme, verdict du président. Les choix de Julien n'étaient pas à rediscuter.

## Accord
- Le contrat avant le code : `docs/journal-exemple.json` (et `-demi`), avec une version de format et les faits bruts
  (notes, points, vrais votes), pas seulement les calculs.
- Un seul plan pour la remontée : pas de copie de `plan()` en Python ; le serveur fixe un plafond, la télé dit quand
  elle a fini.
- Module `app/resultat.py` (le nom `journal` est déjà la fonction du journal des actions).
- Plus aucun envoi à carnet sans clôture (`envoyer_soiree`, « Renvoyer », boucle des 10 min).
- Photo apéro exclue des compteurs et des duos ; « 60 s » = la remontée seule.

## Écarté
- Trois rythmes au lieu d'un temps par étape ; repousser la notation 6b et le mode d'emploi : contraire aux choix.
- Palmarès sur plusieurs années, webhook Home Assistant, collage d'un tableau (Expansionniste) : plus tard.

## Retenu (changements au dossier)
1. Étape 0 : le contrat écrit et fabriqué par `tools/journal_exemple.py` ; un test vérifie que le journal a ses clés.
2. Réglages dans `reglages.json` (`REGLAGES_DEFAUTS`), pas dans la table `reglage`.
3. Révélation : plafond = entrée + 0,9 s + remontée (réglage) + 5 s ; la télé envoie `suivant` avec `depuis` (ignoré si
   le pas a changé) ; rythme accéléré à proportion, pause de 2 s gardée, 30 ms au moins par étape.
4. Fin du podium : par `/regard` ou la télé (`terminer` idempotent, sans carnet) ; changer de mode en plein dévoilement
   repart de maintenant.
5. Clôture permise avec ce qui est saisi (ce qui manque est affiché) ; reclôture = nouvelle version, carnet remplacé
   (même adresse) ; journal écrit après la réponse de carnet ; `archiver` n'est plus appelé « clôture ».
6. Journal : version précise servie (`/journal/<version>`), images figées à la clôture, toutes les routes `/externe/`
   fermées sans jeton (test qui les parcourt).
7. Reprise : les soirées déjà dévoilées sont clôturées d'office, sans journal.
8. Mode d'emploi : bouton chez l'hôte ; à la notation, une phrase dit que le mot peut paraître dans le magazine.

## Non fait (à savoir)
- Gazette lit les photos Immich avec sa propre clé (`GAZETTE_IMMICH_CLE`, prévue dans le dossier Gazette).
- Le jeton commun donne aussi les prénoms et commentaires aux autres applis maison (même règle que les sauvegardes).
- Pas de répétition prévue : Bac à sable mis à jour plus tard (choix de Julien).
