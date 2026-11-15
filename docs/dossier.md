# Douze points — dossier de conception

Version 0.3 du dossier, 15/11/2026. Écrit après les questions de cadrage, puis revu après un passage au conseil (cinq avis indépendants, relecture croisée, synthèse : `claude/douze-points-conseil.md`). Rien n'est codé, rien n'a été essayé sur la vraie installation.

Couleur proposée : **rose de scène `#e5559f`** (à contrôler contre le tableau de `socle/docs/format.md` avant de l'adopter ; la lie-de-vin de Millésime est la couleur la plus proche).

Version publique : les valeurs réelles (adresses, prénoms des invités) passent par les variables de la stack ou par la base de l'appli, jamais par le dépôt.

**Changements de la v0.3**
- **Écran d'accueil de la soirée** : QR code, logo et nom de l'évènement, à recopier sur la télé (AirPlay) et à envoyer en image par WhatsApp avec le lien.
- Port **8088** confirmé ; **tuile dans l'Anneau** retenue ; tous les invités sont sur le Wi-Fi de la maison.

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
2. **Accès des invités** : tous sont sur le Wi-Fi de la maison. L'hôte montre un **écran d'accueil** (logo, nom de l'évènement, QR code) sur la télé et l'envoie par **WhatsApp** avec le lien, pour scanner ou ouvrir avant le début. Rien n'est ouvert sur Internet : le lien ne répond qu'une fois le téléphone sur le Wi-Fi de la maison.
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

1. **Wi-Fi des invités** : tous seront sur le Wi-Fi de la maison. Vérification de deux minutes : un téléphone qui n'est pas du foyer, sur ce Wi-Fi, ouvre une page du NAS.
2. **Recopie d'écran** : une page animée ouverte sur l'iPhone de l'hôte, en paysage, recopiée sur la télé : lisible à quatre mètres ? fluide ? que se passe-t-il quand l'iPhone se verrouille ? (Garder l'écran allumé depuis une page demande HTTPS : en http, c'est le toucher régulier de l'hôte qui le tient éveillé.)
3. **Notification** : par quel chemin (voir « Notification de l'hôte »).

Relevé du 15/11/2026 (recherche web) : Eurovision 2027 à Burgas, 11, 13 et 15 mai ; première Eurovision Asia le 14/11/2026 à Bangkok, une seule soirée ; Intervision sans date ni ville confirmées. Sources possibles pour l'import, plus tard : Wikipédia (les deux concours), une API non officielle (Eurovision seulement), sites de fans.

### Pile

Socle commun des applis maison : FastAPI (Python 3.12) + Svelte 5 + Tailwind 4, une image Docker multi-étapes `ghcr.io/baloodusudouest/douze-points`, SQLite dans `/data`. Port **8088** (confirmé libre par l'hôte le 15/11/2026).

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

### Écran d'accueil de la soirée

- Une page de la régie, en plein écran, faite pour un iPhone en paysage recopié sur la télé : **logo**, **nom de l'évènement** (« Finale 2027 chez… », saisi par l'hôte), **QR code** de la porte invité, et une ligne « Connecte-toi au Wi-Fi de la maison, puis scanne ».
- **Partager** : la même affiche en image (PNG fabriqué par le serveur) et le lien, par la feuille de partage de l'iPhone, donc vers WhatsApp. En http, si le partage direct de l'image n'est pas proposé par le navigateur : bouton **Enregistrer l'image** et bouton **Copier le lien**.
- **Logo** : celui de Douze points par défaut ; l'hôte peut déposer sa propre image pour une soirée (gardée dans `/data`, jamais dans le dépôt). L'appli n'embarque le logo officiel d'aucun concours.
- Le QR code et le lien portent l'adresse locale de l'appli (`DOUZE_POINTS_ADRESSE`) : ouverts hors du Wi-Fi de la maison, ils ne répondent pas. L'affiche le dit.
- Le lien reste le même de la création de la soirée à sa clôture : il peut partir par WhatsApp plusieurs jours avant. Tant que la soirée n'est pas ouverte, il montre le nom de l'évènement et « Ça commence bientôt ».

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

`/health` public : ok, version, et des nombres sans aucun nom (soirées archivées, soirée en cours ou non, classements attendus). **Tuile retenue**, famille « Applis maison » : ligne à ajouter dans `atlas/data/anneau-services.yaml` à la mise en stack.

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
- Aucune soirée en cours : **Nouvelle soirée** → concours, année, émission, **nom de l'évènement**, logo facultatif → saisie ou collage de la liste → invités attendus. Dès ce moment : **Écran d'accueil** et **Partager** (le lien existe déjà). Puis **Ouvrir la soirée**.
- Soirée ouverte : bouton **Écran d'accueil** (logo, nom, QR code, à recopier sur la télé à l'arrivée des invités) et **Partager** ; la liste des chansons, avec **Suivante** pour ceux qui veulent tenir la chanson en cours ; les invités et leur état (pas arrivé, en cours « 12 / 26 », envoyé, pas encore renvoyé).
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

1. Scan du QR code ou lien reçu par WhatsApp → le nom de l'évènement, puis **« Qui es-tu ? »** : grille de prénoms ; un prénom déjà pris est grisé.
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
soiree(id, concours_id, annee, emission[demi1|demi2|finale|unique], date, nom, logo,
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
2. Soirée, liste des chansons à la main, invités, écran d'accueil et partage. Tests.
3. Porte invité : prénom, notation, classement (flèches d'abord, glisser-déposer ensuite), envoi, modification. **Test du secret** sur toutes les adresses et tous les états.
4. Régie : états en direct, forcer, gel des points, sauvegarde. Tests du barème (classement de moins de dix chansons, égalités, copie forcée).
5. Dévoilement court, complet, « Tout afficher », rejouer.
6. Synthèse, vrai résultat, grille papier.
7. **Soirée d'essai avec de vrais invités**, en février ou mars 2027, sur une sélection nationale ou une rediffusion : une dizaine de téléphones, la télé, un redémarrage du conteneur en plein dévoilement.
8. Notification par Home Assistant (master doc relu et complété).
9. PDF.
10. Entrée dans la stack (port 8088), Atlas, tuile de l'Anneau, tests d'écran (PC, iPhone portrait, iPhone paysage).

Les étapes 1 à 7 font la soirée ; 8 et 9 ne la conditionnent pas.

### Plus tard, après une première vraie soirée

- Import de la liste (Wikipédia ou site de fans) et du vrai résultat.
- Intervision ; vue des habitués (palmarès d'une année sur l'autre).
- Idées du conseil : pronostic scellé avant la première chanson (« qui gagnera vraiment ? ») ; soirées d'un autre genre (dégustation à l'aveugle) avec le même déroulé ; lumières du salon au « Douze points » par Home Assistant ; un cocktail par pays avec Comptoir.

---

## 7. Points ouverts

1. **Couleur** à contrôler contre le tableau du socle.
2. **Notification** : nom du service `notify` du téléphone de l'hôte, à lire dans le master doc Home Assistant.
3. **Logo de Douze points** : à dessiner (étape 1 du plan, avec l'icône de l'appli).
4. **Source de l'import**, plus tard : Wikipédia ou site de fans.

---

## Décisions prises en codant l'étape 1 (15/11/2026)

- **Adresse de la porte invité** : `/invite/<jeton>` (et son API sous `/invite/<jeton>/api/…`), comme les autres applis maison, à la place du `/s/<jeton>` écrit au § 2.
- **Le lien vaut de la création de la soirée à son archivage** (le tableau des portes disait « de l'ouverture à la clôture »). En brouillon, il ne rend que le nom de l'évènement.
- **Couleur** : rose de scène `#e5559f`, contrôlée contre le tableau du socle (aucune appli en rose ; à ajouter au tableau).
- **Une seule soirée ouverte à la fois.**
- **Toucher à un classement envoyé le rouvre** (changer une note, déplacer une chanson) : il redevient « pas encore renvoyé ».
- **Retirer une note** est possible ; la chanson sort alors du classement.
- **Deux prénoms identiques** sont refusés dans la liste des invités : ajouter une initiale.
- **Le journal ne contient aucun prénom**, seulement des numéros.
- La première image (0.1.0) contient le serveur complet des étapes 2 à 5 (soirée, porte invité, gel des points, données du dévoilement) et une régie réduite à la liste des soirées. Les écrans viennent ensuite.

## Décisions prises en codant les écrans (0.2.0, 15/11/2026)

- **Deux entrées dans la régie**, Soirée et Réglages (le § 3 en prévoyait cinq) : les invités se gèrent dans la préparation de la soirée, les soirées passées sous l'écran Soirée. Pas d'écran Connexion tant que la notification Home Assistant n'existe pas.
- **Dévoilement** : les commandes (Revenir, Tout afficher, Fermer) sont en haut à droite, pour ne recouvrir ni le commentaire ni le podium sur un iPhone en paysage. En portrait, l'écran demande de tourner le téléphone.
- **Affiche à partager** : dessinée dans le navigateur (pas de PNG fabriqué par le serveur). En http, « Partager l'image » enregistre l'image et « Copier le lien » sélectionne le lien quand le presse-papiers est fermé aux pages.
- **Logo** (0.2.1) : le « 12 » sous un projecteur, dessin propre à l'appli (`frontend/src/lib/Logo.svelte`, `frontend/public/icone.svg`). Le logo d'un concours n'y entre pas, même stylisé : ce sont des marques déposées. Le dépôt d'une image par soirée est fait en 0.3.0 (voir plus bas).
- **Drapeaux** : déduits du nom du pays en français (table dans `frontend/src/lib/pays.js`) ; un pays inconnu de la table n'a pas de drapeau.
- **Ordre du dévoilement** : tiré au sort ; il ne se modifie pas encore.

## Ajouts de la 0.3.0 (15/11/2026, demandes de l'hôte)

- **Images de l'évènement** : logo, bannière, poster, tous facultatifs, déposés depuis la régie (préparation et soirée ouverte). Le logo remplace le « 12 » partout où il sert d'emblème ; la bannière coiffe le téléphone des invités ; le poster accompagne le QR code sur l'écran d'accueil et l'affiche, et l'écran « Ça commence bientôt ». Formats PNG, JPEG, WebP reconnus à leurs premiers octets ; pas de SVG (il peut porter du script) ; 6 Mo au plus. Les invités les lisent par leur lien (`/invite/<jeton>/image/<sorte>`), qui ne rend rien d'autre.
- Ces images sont celles que l'hôte choisit de déposer : l'appli n'en embarque aucune et le dépôt public non plus.
- **Ouverture animée** (`frontend/src/lib/Ouverture.svelte`) : trois projecteurs, le « 12 » qui brille, la lumière qui révèle la page. Jouée à l'ouverture de la régie et du lien des invités, une fois par session.

## Ajout de la 0.4.0 (15/11/2026, demande de l'hôte)

- **Liste des concours réglable** (Réglages › Concours) : table `concours(id, nom, actif)`, qui part avec Eurovision et Eurovision Asia. Un concours retiré disparaît de la liste proposée ; les soirées déjà créées gardent son nom. Intervision ou toute autre soirée à notes s'ajoute donc sans nouvelle version.
- **Ville et titre** : la création d'une soirée demande la ville où le concours est organisé (colonne `soiree.ville`) ; le titre est fabriqué (concours, ville, année, émission) tant que l'hôte n'écrit pas le sien. Même règle côté serveur (`titre_evenement`) et côté écran (`titreEvenement`).

## Ajouts de la 0.5.0 (15/11/2026, demandes de l'hôte)

- **carnet** : Douze points lit `GET /douze-points/personnes` de carnet (2.22.1) avec son propre jeton : prénom et nom des fiches, rien d'autre, sans entreprises ni personnes décédées. La liste est gardée dix minutes en mémoire. D'une personne choisie, la base ne garde que le prénom (plus l'initiale du nom si le prénom est déjà pris) et le numéro de sa fiche ; son nom complet n'est jamais enregistré ni montré aux invités. Variables : `DOUZE_POINTS_CARNET_URL`, `DOUZE_POINTS_CARNET_JETON` (= `CARNET_JETON_DOUZE_POINTS` côté carnet). L'écran Connexion existe donc maintenant (trois entrées dans la régie).
- **Jury et public** : `invite.jury` se règle dans Réglages › Invités ; `participation.jury` est figé au lancement du dévoilement. Mode de dévoilement `jury` : les points du jury par chanson dans l'ordre de passage (avec qui a donné quoi), puis ceux du public en partant de la dernière du classement du jury. Le calcul ne change pas : le total d'une chanson reste la somme des points de tous les invités. Le mode demande au moins un membre du jury et un du public parmi ceux qui ont noté.
- **Podium et cotillons** à la fin de tout dévoilement (pas de cotillons si l'appareil demande moins d'animations).
- **Fiche de la soirée** (`GET /api/soirees/<id>/fiche`, `fiche.csv`) : disponible une fois le dévoilement lancé, jamais avant. Elle remplace la « synthèse » et le PDF côté serveur du § 2 : l'impression du navigateur fait le PDF. Restent à y ajouter : écarts et affinités.
- **Vrais votes** (`PUT /api/soirees/<id>/officiel`) : points du vrai jury et du vrai public par chanson, saisis après coup (colonnes `chanson.officiel_jury`, `officiel_public`). Comparaison : même gagnant, chansons communes dans les trois premières, écart moyen de rang, pour l'ensemble, le jury et le public.
- **Suppression d'une soirée** (`DELETE /api/soirees/<id>` avec confirmation) : tout ce qui lui appartient part, les invités restent ; sauvegarde de la base juste avant.

## Ajouts de la 0.6.0 (15/11/2026, demandes de l'hôte)

- **Démarrage en trois temps** : écran éteint (`pages/Lancement.svelte`, le « 12 » gris et le bouton), projecteurs (`lib/Ouverture.svelte` avec `toujours`), écran d'accueil. La soirée ne s'ouvre aux invités qu'au clic sur le bouton de l'écran éteint.
- **Scène** (`lib/Scene.svelte`) : bannière animée en continu en haut de l'écran d'accueil ; le « 12 » n'est donc plus répété dans le texte (un logo déposé s'y affiche toujours).
- **L'hôte et la notation** : lien « Passer à la notation » vers `/invite/<jeton>` ; la page des invités, quand elle est ouverte par un appareil connecté à la régie, lit `/api/soirees/<id>` pour montrer l'avancement de chacun. Aucune adresse nouvelle ; la porte invité ne change pas, et la régie ne rend toujours ni note ni commentaire avant le dévoilement.
- **Fiche de notation** : trois boutons. « Précédente » et « Suivante » n'enregistrent que si la note ou le mot ont été modifiés.

## Ajouts de la 0.7.0 (15/11/2026, demandes de l'hôte)

- **Plusieurs soirées à la fois** : la règle « une seule soirée ouverte » du 15/11 est levée. L'écran Soirée s'ouvre sur la liste des soirées non archivées (ou tout droit sur la soirée s'il n'y en a qu'une) ; celle qu'on a choisie est gardée le temps de la session, pour y revenir après la notation.
- **Rejouer le démarrage** depuis l'écran d'accueil : l'écran éteint, le bouton et les projecteurs se rejouent ; la soirée, déjà ouverte, n'est pas touchée.
