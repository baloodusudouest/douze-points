# Douze points 1.7.0 — dossier : l'animation du dernier vote du public (19/11/2026)

## 1. Besoin
Pour le dernier pays qui reçoit les points du public (dernier pas avant le podium), une animation comme à la finale de l'Eurovision Asia 2026 (direct YouTube `casZJ_zOPlA`, vers 2 h 25 min 58 s ; décrite d'après 4 captures de l'utilisateur). Choix de l'utilisateur (19/11/2026, 20 h 28 à 20 h 35) :
- étiquettes en français : « En tête », « + X points pour gagner », « Vainqueur » ;
- la carte du dernier pays monte l'échelle des places **très vite**, puis **ralentit pour les 5 dernières places** (de la 6e à la 2e) ; arrivée à « + 1 point pour gagner », **pause de 2 secondes**, puis montée **rapide** jusqu'au total final s'il dépasse le premier ;
- s'il passe devant : place 01, « Vainqueur », l'ancien premier glisse en 02 ;
- s'il ne passe pas devant : il s'arrête où il est, « + X points pour gagner » disparaît, « Vainqueur » se pose au-dessus du pays en tête, avec des cotillons ; puis le top 3 ;
- beaucoup de pays : les places passent une par une, rapidement ;
- sur la télé (écran de l'hôte recopié) **et** sur les téléphones des invités.
- Les boutons « Revenir » / « Suivant » restent à l'hôte seul (déjà le cas dans Douze points : visibles seulement si le téléphone est connecté ; le Bac à sable les montrait à tort sur les téléphones simulés, corrigé dans le Bac à sable).

## 2. Technique
- Composant commun `frontend/src/lib/DernierVote.svelte`, monté par `pages/Devoilement.svelte` (télé) et `invite/Spectacle.svelte` (téléphone) au **dernier pas « public »** (pas = nombre d'étapes), à la place du tableau ; le pas suivant reste le podium (l'hôte avance comme avant).
- Entrées : les totaux de toutes les chansons après ce pas, l'identifiant du dernier pays et les points qu'il reçoit à ce pas. Le reste est calculé dans le composant (fonctions pures dans `lib/dernier.js`, testées) : total de départ, total du premier des autres, place d'un total (1 + nombre d'autres ayant un total **supérieur ou égal** : à égalité, le dernier pays reste sous le premier, comme sur la capture 170/170 en 02), et le **plan de la montée** : une liste d'étapes (total affiché, place, durée).
- Rythme : places au-delà de la 6e : très vite (≈ 1,2 s en tout) ; de la 6e à la 2e : ≈ 0,8 s par place ; au total du premier (« + 1 point ») : pause 2 s ; puis le reste en ≈ 0,6 s. Sans dépassement : les mêmes vitesses jusqu'au total final, puis « Vainqueur » sur le premier et cotillons.
- Les deux écrans jouent l'animation chacun de leur côté en arrivant à ce pas (pas de synchronisation fine : quelques dixièmes d'écart). Revenir sur ce pas la rejoue.
- Échelle : toutes les places tiennent dans la hauteur (taille des pastilles calculée sur la hauteur et le nombre de pays, comme le tableau actuel).
- Préférence « réduire les animations » : on saute à l'état final.
- Aucune modification du serveur.

## 3. Parcours
Hôte : … dernier pays du public → l'écran montre l'échelle, « En tête » à gauche, le dernier pays à droite avec « + X points pour gagner » → montée → « Vainqueur » → « Suivant » → podium (inchangé). Invités : la même chose sur leur téléphone (portrait : cartes plus étroites).

## 4. Design
Reprend la capture : colonne centrale arrondie (dégradé du thème de Douze points), pastilles 01…N, la place occupée entourée ; cartes « pilule » : nom, drapeau, total dans un bloc de couleur ; étiquettes en pastille au-dessus des cartes. Couleurs du thème de Douze points (rose/violet), pas celles de l'émission.

## 5. Données
Aucune nouvelle donnée.

## 6. Plan
1. `lib/dernier.js` (place, plan de la montée) + tests unitaires (node --test ou vitest déjà présent ?).
2. `lib/DernierVote.svelte` ; branchement télé et téléphone.
3. Tests d'écran PC et iPhone (aucune erreur, pas de débordement, « Vainqueur » visible à la fin, cas sans dépassement).
4. Version 1.7.0, CHANGELOG, REPRISE, coffre ; puis Bac à sable (Douze points 1.7.0 embarqué, téléphones simulés vus comme invités).
