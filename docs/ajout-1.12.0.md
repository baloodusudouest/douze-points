# Douze points 1.12.0 — notre pays, sans points

Demande de Julien du 21/11/2026 : « on ne peut pas voter pour son propre pays : il faudrait que l'on puisse voter pour
la France, mettre des commentaires, faire son classement, mais aucun point pour la France. »

## Choix de Julien (cadrage du 21/11/2026, boîtes à choix)

| Question | Choix |
|---|---|
| Qui dit quel pays est exclu | Un réglage « Notre pays », la France par défaut, pour toutes les soirées |
| France classée 1re par un invité | Les points glissent : le 12 va à la 2e de son classement, et ainsi de suite (comme au concours) |
| Au dévoilement et au classement du groupe | À part, hors du tableau, avec la moyenne du groupe |
| Soirées déjà dévoilées | Ne pas y toucher (points figés) |
| Notes de la France dans écarts, affinités, jumeaux | Elles comptent |
| Moment de « Et notre pays ? » | Après le podium (top 3 et cotillons) |
| Fiche et Gazette face aux vrais votes | Vrais points affichés, hors des écarts de rang et du palmarès |
| Bac à sable | Plus tard |
| Méthode | « Oui, et code direct » : pas de Conseil pour cette petite évolution |

## Ce qui est fait

Voir `CHANGELOG.md` (1.12.0). En bref :

- réglage `notre_pays` (code à deux lettres) ; reconnaissance par drapeau, sinon par nom (`app/pays_codes.json`) ;
- `points_du_classement(ordre, exclues)` côté serveur, `pointsDuClassement(ordre, hors)` côté téléphone ;
- `chanson.hors_points` figé au dévoilement ;
- notre pays sort de `classement`, de `marche` (public, dernier vote) et du podium ; `notre_pays` (moyenne, place aux
  notes) dans le dévoilement, la fiche, les résultats des téléphones et le journal de Gazette ;
- comparaisons aux vrais votes sans notre pays (`resultat.sans_exclues`, `points.rerang`).

## Décisions prises en codant

- « Et notre pays ? » passe seul sur la télé au bout du temps du podium, jamais au toucher : un toucher de trop pendant
  le dévoilement aurait sauté le podium. En automatique, le podium dure 10 s de plus (`NOTRE_PAYS_S`).
- Sur le téléphone, la marque « Notre pays · 0 pt » est dans la petite ligne sous le pays (coupée proprement si l'écran
  est étroit) ; le chiffre de gauche affiche 0.
- Le vrai rang de notre pays reste affiché (fiche, Gazette) ; seuls les écarts et le palmarès le laissent de côté.
- Le podium officiel (`podium_officiel`) reste le vrai, notre pays compris : c'est le résultat du concours.

## Jamais essayé sur la vraie installation

Tout : la marque sur un vrai iPhone, le glissement des points avec la France en tête, l'écran « Et notre pays ? » sur
la télé en recopie AirPlay, la fiche imprimée, le magazine de Gazette avec la France sans rang maison.
