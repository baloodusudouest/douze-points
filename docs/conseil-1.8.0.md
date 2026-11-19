# Douze points 1.8.0 — conseil (20/11/2026)

Cinq conseillers (Contradicteur, Premiers principes, Expansionniste, Œil extérieur, Exécutant), relecture croisée
anonyme, verdict du président. Les choix de Julien (validés sur visuels) n'étaient pas à rediscuter.

## Accord
- Le seul vrai risque est le pas automatique : `POST /pas` enregistrait un numéro calculé par l'écran sur une lecture
  vieille d'une seconde ; une Pause ou un Suivant pouvait faire reculer le spectacle, deux régies se contredire.
- Il faut une horloge remplaçable en test (`maintenant()` est une chaîne à la seconde).
- « Les pays en lice » pouvait sauter (animation seulement si l'écran a vu le pas juste avant).

## Écarté
- Lancer le dernier pays au toucher, trois lettres sous les drapeaux (Œil extérieur) : contraire aux choix de Julien.
- Couper le polaroïd et les deux colonnes (Exécutant) : demandés par Julien ; le HEIC se règle à la réception.
- Home Assistant, Gazette, carnet, générique de fin (Expansionniste) : plus tard (noté dans REPRISE).

## Retenu (changements au dossier)
1. Les écrans envoient une **action** (`suivant`, `revenir`, `pause`, `reprendre`, `aller`) ; le serveur, dans une
   seule transaction, fige le pas effectif, applique l'action, remet `pas_le`. **Revenir met en pause.** Horloge
   `main.horloge()`.
2. **Lectures sans verrou d'écriture** (`base.lecture()`) pour les relectures de chaque seconde.
3. `pas_le` vide ou ancien : jamais de saut. Le défilement ne part qu'après une action ; reprendre un dévoilement
   le met en pause.
4. Télé : n'envoie rien d'elle-même ; relit le serveur à l'échéance ; l'animation des pays en lice se joue dès qu'on
   entre dans le dernier pas depuis un pas plus tôt vu sur cet écran (pas seulement le pas juste avant).
5. **Égalité** au sommet : étiquette « Égalité », le vainqueur est celui du classement de la soirée (départage).
6. Selfies de duo : **vignette JPEG réduite** faite à la réception (Pillow, pillow-heif pour le HEIC), gardée pour la
   télé ; l'original part à Immich comme avant ; vignettes effacées à l'archivage ou avec la soirée.
7. Saisie : « Passer au classement » attend la fin des enregistrements en cours ; une note refusée bloque le passage.
8. **Écran allumé** (Wake Lock) pendant le dévoilement, relecture immédiate au retour au premier plan.
9. Tests en temps simulé : deux régies, Pause puis reprise, Suivant pile à l'échéance, soirée reprise après coup.
