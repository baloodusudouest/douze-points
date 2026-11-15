# Douze points — dossier de conception

Version 0.2 du dossier, 15/11/2026. Écrit après les questions de cadrage, puis revu après un passage au conseil (cinq avis indépendants, relecture croisée, synthèse : `claude/douze-points-conseil.md`). Rien n'est codé, rien n'a été essayé sur la vraie installation.

Couleur proposée : **rose de scène `#e5559f`** (à contrôler contre le tableau de `socle/docs/format.md` avant de l'adopter ; la lie-de-vin de Millésime est la couleur la plus proche).

Version publique : les valeurs réelles (adresses, prénoms des invités) passent par les variables de la stack ou par la base de l'appli, jamais par le dépôt.

**Changements depuis la v0.1 (après le conseil et les réponses de l'hôte)**
- **Barème du concours** : le classement de chaque invité donne 12, 10, 8, 7, 6, 5, 4, 3, 2, 1 point à ses dix premières chansons (avant : N, N−1… 1).
- **Plus de page « grand écran » permanente** : quand tous les classements sont envoyés, l'hôte reçoit une **notification sur son téléphone** et **recopie son écran sur la télé (AirPlay)** pour montrer le dévoilement.
- **Sortis de la V1** : la liste automatique (saisie à la main en V1 ; import depuis Wikipédia ou un site de fans plus tard), Intervision, la vue des habitués.
- **Dévoilement court par défaut**, gelé au lancement et rejouable ; « Tout afficher » sans animation en secours.
- **Essais avant le code** : Wi-Fi des invités, recopie d'écran, notification.
- Plus de flux poussé par le serveur : relecture toutes les 3 secondes. Chanson en cours facultative. Libérer un prénom conserve les notes. Vocabulaire des écrans invités revu.

---

## 1. Besoin

Pendant une soirée de concours de chansons regardée à plusieurs à la maison, chaque invité note les chansons sur son téléphone, puis valide son classement. Personne ne voit rien des autres avant la fin. Quand tous les classements sont envoyés, l'hôte dévoile le classement du groupe sur la télé, puis une synthèse de la soirée est produite.

Choix arrêtés :

1. **Concours couverts en V1** : Eurovision (demi-finales et finale) et Eurovision Asia. Une soirée = une émission. Intervision plus tard.
2. **Accès des invités** : sur le Wi-Fi de la maison, par un **QR code** montré par l'hôte. Rien n'est ouvert sur Internet.
3. **Identité** : l'hôte prépare la liste des invités ; chacun **touche son prénom**.
4. **Notation** : **une note sur 20 par chanson, par demi-points**, plus un **commentaire** facultatif.
5. **Pendant le direct**, l'invité voit la chanson en cours (si l'hôte la fait avancer), **son classement provisoire** et **qui a déjà envoyé** (sans aucune note).
6. **Classement de l'invité** : une fois ses notes mises, l'appli propose son classement, tiré de ses notes, qu'il **réordonne par glisser-déposer**. Ses notes sur 20 **ne bougent pas**. Bouton **Envoyer mon classement**. Modifiable jusqu'au dévoilement.
7. **Points** : le classement de chaque invité donne les points **du barème du concours** : 12, 10, 8, 7, 6, 5, 4, 3, 2, 1 à ses dix premières, rien aux suivantes. Le classement du groupe est la somme de ces points.
8. **Dévoilement** : quand **tous les classements sont envoyés** et les points calculés, **l'hôte reçoit une notification sur son téléphone**. Il ouvre le dévoilement et **recopie son écran sur la télé** (AirPlay). **Il peut forcer** sans les retardataires.
9. **Commentaires signés**, au dévoilement et dans la synthèse.
10. **Synthèse de la soirée** : classement du groupe et de chaque invité ; commentaires marquants ; écarts et affinités ; comparaison au vrai résultat. **PDF**.
11. **Liste des chansons** : saisie par l'hôte en V1, dans l'ordre de passage.

Hors périmètre de la V1 : import automatique de la liste, Intervision, vue des habitués, participation à distance, plusieurs critères par chanson.

Écrans : **téléphone** des invités ; **téléphone** de l'hôte (régie et dévoilement, recopié sur la télé) ; **PC** pour préparer la soirée.

Fréquence : quelques soirées par an. Première échéance : demi-finales des 11 et 13 mai 2027, finale le 15 mai (Burgas, 21 h).

---

## 2. Technique

### Étape 0 : trois essais avant le code

Chacun prend moins d'une heure, avec le conteneur du socle déjà en place :

1. **Wi-Fi des invités** : un téléphone qui n'est pas du foyer, connecté au Wi-Fi prévu pour les invités, ouvre-t-il une page du NAS ? (Un réseau « invité » de la box est en général isolé.)
2. **Recopie d'écran** : une page animée ouverte sur l'iPhone de l'hôte, en paysage, recopiée sur la télé : lisible à quatre mètres ? fluide ? que se passe-t-il quand l'iPhone se verrouille ? (Garder l'écran allumé depuis une page demande HTTPS : en http, c'est le toucher régulier de l'hôte qui le tient éveillé.)
3. **Notification** : par quel chemin (voir « Notification de l'hôte »).

Relevé du 15/11/2026 (recherche web) : Eurovision 2027 à Burgas, 11, 13 et 15 mai ; première Eurovision Asia le 14/11/2026 à Bangkok, une seule soirée ; Intervision sans date ni ville confirmées. Sources possibles pour l'import, plus tard : Wikipédia (les deux concours), une API non officielle (Eurovision seulement), sites de fans.

### Pile

Socle commun des applis maison : FastAPI (Python 3.12) + Svelte 5 + Tailwind 4, une image Docker multi-étapes `ghcr.io/baloodusudouest/douze-points`, SQLite dans `/data`. Port proposé **8088** (à confirmer : la valeur de `PORT_IMMICH_SCAN` n'est pas écrite dans la stack).

### Deux portes

| Porte | Qui | Protection | Ce qu'elle permet |
|---|---|---|---|
| Régie (`/`) | l'hôte | mot de passe commun, cookie `maison_session` | tout : soirées, invités, liste, dévoilement, synthèse |
| Invité (`/s/<jeton>`) | les invités, par le QR code | jeton de la soirée, tiré au hasard, valable de l'ouverture à la clôture | choisir son prénom, noter, commenter, classer, envoyer, voir qui a envoyé ; après le dévoilement, voir la synthèse |

- La porte à jeton ne donne jamais accès au reste de l'API ; jeton comparé en temps constant ; soirée close ou jeton vide : porte fermée.
- **Le secret tient côté serveur** : avant la fin du dévoilement, aucune réponse de la porte invité ne contient la note, le commentaire, le classement d'un autre, ni un total. Le test couvre **toutes** les adresses invité et **tous** les états de la soirée, « dévoilement en cours » compris.
- **Un téléphone, un prénom** : au choix du prénom, le téléphone reçoit un jeton personnel gardé dans le navigateur. Tant qu'il n'a rien noté, l'invité peut **changer de prénom lui-même**. Ensuite, l'hôte peut **libérer** un prénom (téléphone changé, navigation privée, erreur) : **les notes et le classement sont conservés** et reviennent au téléphone qui reprend le prénom.
- Entre amis, le prénom suffit : pas de code par invité.
- Limites sur la porte invité : commentaires de 280 caractères, toujours affichés comme du texte ; nombre de demandes par minute.

### Liste des chansons (V1 : à la main)

- L'hôte saisit sur PC : ordre de passage, pays, artiste, titre. Collage d'un bloc de lignes accepté (une chanson par ligne, champs séparés par une tabulation ou un point-virgule), pour copier une liste depuis une page web.
- Réordonner, corriger, ajouter, retirer jusqu'à l'ouverture. Après l'ouverture : corriger un libellé seulement.
- Drapeaux : émojis (les téléphones les affichent ; le dévoilement se montre depuis un iPhone).
- Plus tard : bouton d'import (Wikipédia ou site de fans), qui propose une liste à corriger, jamais une liste imposée.

### Déroulé d'une soirée

États : **brouillon** → **ouverte** → **dévoilement** → **dévoilée** → **archivée**.

- **Chanson en cours** : facultative. Si l'hôte la fait avancer, les téléphones la mettent en avant ; sinon rien ne manque. Un invité peut toujours noter n'importe quelle chanson.
- Notes **enregistrées côté serveur à chaque saisie** : un téléphone qui se verrouille ou se recharge ne perd rien.
- **Classement de l'invité** : tant qu'il n'a rien déplacé, il suit ses notes (à note égale, l'ordre de passage). Dès qu'il déplace une chanson, l'ordre est **le sien**. Une chanson notée ensuite se place juste au-dessus de la première chanson, en partant du haut, dont la note est plus basse ; sinon en bas. **Reclasser d'après mes notes** efface l'ordre fait à la main.
- **Envoyer mon classement** : la soirée le compte comme fini. **Modifier mon classement** le rouvre ; un bandeau dit alors « Pas encore renvoyé » jusqu'au nouvel envoi.
- Mise à jour des écrans : chaque téléphone relit l'état de la soirée toutes les 3 secondes. Pas de connexion gardée ouverte.

### Calcul des points

- Barème du concours : 12, 10, 8, 7, 6, 5, 4, 3, 2, 1 pour les rangs 1 à 10 de chaque invité.
- **Classement de moins de dix chansons** : l'invité donne les points des rangs qu'il a (son premier a 12, son deuxième 10…). Une chanson non notée et une chanson classée onzième valent pareil : zéro.
- **Forcer** : le classement du moment de chaque retardataire est pris tel quel s'il a noté au moins une chanson ; sinon il est écarté. Le dévoilement le dit (« 9 chansons sur 26 »).
- **Égalités** du groupe : le plus grand nombre d'invités ayant donné des points ; puis le plus de 12, de 10, etc. ; puis la meilleure moyenne des notes sur 20 ; sinon ex æquo.
- **Gel** : au lancement du dévoilement, les points sont calculés une fois et enregistrés, avec l'ordre de passage des invités. Une copie de la base est faite au même instant. Plus rien ne se recalcule en direct.

### Notification de l'hôte

Quand le dernier classement attendu arrive :

- la régie, si elle est ouverte, affiche « Tout le monde a envoyé » avec le bouton **Dévoiler** ;
- **notification sur le téléphone** par Home Assistant (l'appli Home Assistant de l'iPhone sait recevoir une notification ; une page web en http ne le peut pas). Douze points appelle une adresse de Home Assistant réglée dans la stack ; adresse vide : pas de notification, la régie seule. Toucher la notification ouvre la régie.

Home Assistant est touché : le master doc est à relire puis à compléter (automatisation déclenchée par un webhook, service `notify` du téléphone) avant de coder cette étape.

### Dévoilement

- Lancé depuis la régie, sur le téléphone de l'hôte, **en paysage**, recopié sur la télé.
- **Court par défaut** : pour chaque invité, ses points de 1 à 7 s'ajoutent d'un coup ; ses **8, 10 et 12 points** sont annoncés un par un, avec sa note sur 20 et son commentaire ; le tableau se réordonne. Huit invités : environ 32 gestes.
- **Complet** au choix : les dix points de chacun, un par un.
- L'hôte avance en touchant l'écran ; **Revenir d'un pas** ; **Tout afficher**, qui montre le classement final sans animation et marche même si rien d'autre ne marche.
- À la fin : le podium, puis la synthèse.
- **Rejouable** : le dévoilement gelé se relance depuis les archives.

### Synthèse et PDF

- Page de synthèse : classement du groupe (points), classement et notes de chaque invité, commentaires, écarts et affinités, comparaison au vrai résultat.
- **Écarts et affinités** : chanson la plus clivante et la plus consensuelle (écart des notes sur 20) ; paires d'invités les plus proches et les plus éloignées ; le plus sévère et le plus généreux (moyenne des notes) ; le coup de cœur solitaire ; les chansons classées à contre-note. Sous trois invités, ces rubriques ne s'affichent pas.
- **Vrai résultat** : saisi par l'hôte après l'émission (rang officiel de chaque chanson ; pour une demi-finale, qualifiée ou non). Proximité de chaque invité et du groupe avec le classement officiel, et « qui avait vu le gagnant ».
- **PDF** A4 produit par le serveur (WeasyPrint) à partir d'une version de la synthèse sans JavaScript, drapeaux remplacés par le nom du pays. Dernière étape du plan : la soirée ne dépend pas de lui.
- **Grille papier de secours** : la régie imprime une grille vierge (chansons × note, puis dix lignes de classement). Si l'appli tombe, la soirée continue.

### Lien avec l'Anneau

`/health` public : ok, version, et des nombres sans aucun nom. Tuile dans la famille « Applis maison » si elle est retenue (§ 7).

### Sécurité

- `DOUZE_POINTS_PASSWORD`, obligatoire : sans lui, le conteneur ne démarre pas.
- Douze points n'écrit chez aucun service extérieur. Seul appel sortant : la notification vers Home Assistant, sans donnée personnelle (ni prénom, ni note). Watchtower désactivé.
- La porte invité est la seule partie de la maison ouverte à des téléphones qui ne sont pas ceux du foyer : limites strictes, et rien d'autre que la soirée en cours.
- Dépôt public : aucun prénom réel, aucune adresse ; invités des tests inventés.

### Variables de la stack (V1)

```
DOUZE_POINTS_PASSWORD=      # mot de passe commun des applis maison, obligatoire
DOUZE_POINTS_ADRESSE=       # adresse de l'appli vue par les téléphones des invités (sert à fabriquer le QR code)
DOUZE_POINTS_HA_WEBHOOK=    # adresse de Home Assistant à appeler quand tous ont envoyé ; vide : pas de notification
```

Volume : `/data` (douze-points.db, sauvegardes/, syntheses/).

---

## 3. Parcours des clics et des écrans

### Régie (l'hôte)

Navigation : rail à gauche sur PC, pilule en bas sur téléphone. Cinq entrées : **Soirée** (ouverture), **Archives**, **Invités**, **Connexion**, **Réglages**. Pas d'entrée « À traiter » : ce qui attend une décision est dans l'écran Soirée.

**Soirée**
- Aucune soirée en cours : **Nouvelle soirée** → concours, année, émission → saisie ou collage de la liste → invités attendus → **Ouvrir la soirée**.
- Soirée ouverte : le **QR code** en grand (à montrer ou à recopier sur la télé à l'arrivée des invités) ; la liste des chansons, avec **Suivante** pour ceux qui veulent tenir la chanson en cours ; les invités et leur état (pas arrivé, en cours « 12 / 26 », envoyé, pas encore renvoyé).
- Quand tous ont envoyé : bouton plein **Dévoiler**. Sinon : **Forcer le dévoilement**, avec la liste de ceux qui manquent, ce qui sera pris pour chacun, et une confirmation.
- Avant de lancer : choix **Court / Complet**, ordre de passage des invités (tiré au sort, modifiable).
- Après : **Synthèse**, **Télécharger le PDF**, **Saisir le vrai résultat**, **Archiver**.
- **Imprimer la grille papier**.
- L'hôte note lui aussi, par le même lien que les invités. La régie ne montre aucune note ni aucun classement avant le dévoilement.

**Archives** : soirées passées par concours et par année ; ouvrir une soirée → synthèse, PDF, **Rejouer le dévoilement**.

**Invités** : liste des prénoms, ajouter, renommer, retirer (un invité retiré reste dans les archives).

**Connexion** : une tuile Home Assistant (voyant, ce qui est envoyé : « tout le monde a envoyé », rien d'autre ; **Envoyer un essai**).

**Réglages** : journal (ouvertures, dévoilements forcés, prénoms libérés), sauvegardes, version, déconnexion.

### Invité (téléphone)

1. Scan du QR code → **« Qui es-tu ? »** : grille de prénoms ; un prénom déjà pris est grisé.
2. Première ouverture : trois lignes d'explication. « Note chaque chanson sur 20. À la fin, range tes chansons : tes dix premières reçoivent 12, 10, 8, 7… 1 point. C'est ce classement qui compte. »
3. Onglet **Chansons** : la liste dans l'ordre de passage (drapeau, pays, artiste, titre, note donnée). Toucher une chanson → grand curseur de 0 à 20, boutons − et + pour le demi-point, commentaire, **Suivante**.
4. Onglet **Mon classement** : ses chansons notées, du premier au dernier, avec le rang, la note et **les points que ce rang donne** (12, 10, 8…) ; un trait sous la dixième. Poignée à droite pour **glisser** une ligne (appui sur la poignée seulement) ; **flèches haut / bas** pour ceux que le glisser gêne. **Reclasser d'après mes notes**.
5. Onglet **Les invités** : qui est arrivé, qui a envoyé. Aucune note.
6. Bouton plein **Envoyer mon classement** : rappel des chansons non notées (« elles ne recevront aucun point de toi »), confirmation. Ensuite : « Classement envoyé », et **Modifier mon classement**.
7. Dévoilement lancé : « Regarde la télé ». Une fois fini : la synthèse.

### Dévoilement (téléphone de l'hôte en paysage, recopié sur la télé)

- Tableau des chansons à gauche (drapeau, pays, total), l'invité en cours à droite.
- Toucher : pas suivant. Les points de 1 à 7 arrivent d'un coup ; puis « 8 points », « 10 points », puis **« Douze points »** en plein écran, avec la note sur 20 et le commentaire de l'invité.
- Coin discret : **Revenir**, **Tout afficher**.
- Fin : podium, puis pages de la synthèse à faire défiler.

---

## 4. Design

- Format commun : toujours sombre, neutres chauds (`#151311`, `#1f1c19`, `#312c27`, `#f2ece2`, `#a89e91`), Inter, titres grands et fins, un seul bouton plein par bloc.
- Couleur de l'appli : **rose de scène `#e5559f`**, sous réserve du tableau du socle.
- **Signature** : le « Douze points » annoncé en plein écran, en très grands chiffres fins, et le tableau qui se réordonne comme celui du concours.
- Téléphone invité : une colonne, cibles de 48 px au moins, curseur large utilisable d'un pouce, rien qui déborde.
- Dévoilement : pensé pour un iPhone en paysage vu sur une télé ; peu de lignes à la fois (le haut du tableau et la chanson qui vient de recevoir), texte très grand, aucun élément de navigation.
- Animation : sobre partout, assumée au dévoilement, avec « Tout afficher » sans animation.

---

## 5. Schéma de données (SQLite, V1)

```
concours(id, nom)                                   -- Eurovision, Eurovision Asia
soiree(id, concours_id, annee, emission[demi1|demi2|finale|unique], date,
       etat[brouillon|ouverte|devoilement|devoilee|archivee],
       jeton_invite, chanson_en_cours_id, mode_devoilement[court|complet], ordre_devoilement_json, pas_devoilement,
       forcee, ouverte_le, devoilee_le)
chanson(id, soiree_id, ordre, pays, code_pays, artiste, titre,
        rang_officiel, qualifie)                    -- vrai résultat, saisi après l'émission
invite(id, prenom, actif, cree_le)
participation(id, soiree_id, invite_id, jeton_telephone, etat[attendu|en_cours|envoye|ecarte],
              classement_main, arrive_le, envoye_le)
note(participation_id, chanson_id, valeur, commentaire, modifie_le)      -- valeur en demi-points, 0 à 20
classement(participation_id, chanson_id, rang)      -- rempli quand l'invité a déplacé une chanson ; sinon le rang se déduit des notes
points(soiree_id, participation_id, chanson_id, rang, points)            -- gelés au lancement du dévoilement
journal(id, date, action, cible, detail_json)
```

La synthèse se recalcule à partir des notes et des points gelés.

---

## 6. Plan

0. **Trois essais** (§ 2) : Wi-Fi des invités, recopie d'écran, notification.
1. Copie du socle : nom, couleur, mot de passe, `/health`, `REPRISE.md`, `CHANGELOG.md`.
2. Soirée, liste des chansons à la main, invités. Tests.
3. Porte invité : prénom, notation, classement (flèches d'abord, glisser-déposer ensuite), envoi, modification. **Test du secret** sur toutes les adresses et tous les états.
4. Régie : états en direct, forcer, gel des points, sauvegarde. Tests du barème (classement de moins de dix chansons, égalités, copie forcée).
5. Dévoilement court, complet, « Tout afficher », rejouer.
6. Synthèse, vrai résultat, grille papier.
7. **Soirée d'essai avec de vrais invités**, en février ou mars 2027, sur une sélection nationale ou une rediffusion : une dizaine de téléphones, la télé, un redémarrage du conteneur en plein dévoilement.
8. Notification par Home Assistant (master doc relu et complété).
9. PDF.
10. Entrée dans la stack, Atlas, tuile de l'Anneau si retenue, tests d'écran (PC, iPhone portrait, iPhone paysage).

Les étapes 1 à 7 font la soirée ; 8 et 9 ne la conditionnent pas.

### Plus tard, après une première vraie soirée

- Import de la liste (Wikipédia ou site de fans) et du vrai résultat.
- Intervision ; vue des habitués (palmarès d'une année sur l'autre).
- Idées du conseil : pronostic scellé avant la première chanson (« qui gagnera vraiment ? ») ; soirées d'un autre genre (dégustation à l'aveugle) avec le même déroulé ; lumières du salon au « Douze points » par Home Assistant ; un cocktail par pays avec Comptoir.

---

## 7. Points ouverts

1. **Port** 8088 à confirmer.
2. **Couleur** à contrôler contre le tableau du socle.
3. **Tuile dans l'Anneau** : oui ou non.
4. **Wi-Fi des invités** : réseau principal ou réseau invité de la box (essai n° 1).
5. **Notification** : nom du service `notify` du téléphone de l'hôte, à lire dans le master doc Home Assistant.
6. **Source de l'import**, plus tard : Wikipédia ou site de fans.
