# Conseil 1.7.0 — l'animation du dernier vote du public (19/11/2026)

Cinq conseillers (Contradicteur, Premiers principes, Expansionniste, Regard extérieur, Exécutant), synthèse.

## Retenu
- **Une seule valeur animée** : le total affiché du dernier pays ; la place et les étiquettes en découlent. Calcul pur dans `lib/dernier.js` (`place`, `pourGagner`, `plan`, `premier`), testé par `node --test` (pas de nouvelle dépendance).
- **Totaux d'avant ce pas** : la télé passe `cumul(pas)` (pas le tableau trié en retard) ; le tri est figé pendant l'animation.
- **Rejouer seulement en direct** : l'animation se joue si l'écran a vu le pas précédent (« Suivant ») ; au rechargement, pour un téléphone arrivé en retard ou en revenant du podium : la fin tout de suite.
- **Minuteries** : chaîne de `setTimeout` annulée au démontage (« Suivant » pendant l'animation passe au podium, « Revenir » la quitte proprement).
- **Cas limites** : égalité exacte avec le premier (il reste 2e, le premier gagne, pas de pause) ; déjà premier avant ce pas (il compte sans monter) ; zéro point (pas d'étape) ; une seule chanson ; beaucoup de pays (durée minimale par place).
- **Pause de 2 s** seulement s'il va dépasser le premier, au total du premier (« + 1 point pour gagner »).
- **Téléphone en portrait** : cartes étroites, « + X pts pour gagner ».
- **Accessibilité** : « réduire les animations » → la fin directe, et le vainqueur annoncé dans une zone `aria-live`.
- Tests d'écran (PC paysage et iPhone) avec un rythme accéléré par `window.__DOUZE_POINTS_RYTHME`, jamais posé en soirée.

## Écarté pour l'instant
Son et vibration ; cotillons aux couleurs du drapeau ; ligne personnelle (« ton 12 points ! ») ; écran gardé allumé. Pistes notées pour plus tard.
