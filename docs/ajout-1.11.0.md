# Douze points 1.11.0 — dossier (20/11/2026)

Trois demandes de Julien du 20/11/2026, cadrées par questions à choix. Il a demandé de tout coder ce soir, puis de mettre à jour le Bac à sable dans la foulée.

## 1. Besoin

1. **Sons sur la télé uniquement** (les téléphones restent muets) :
   - **Origine :** sons fabriqués par l'appli (Web Audio, aucun fichier, aucun droit). Dans Réglages, chaque son peut être remplacé par un fichier à Julien.
   - **Écran du QR code :**
     - musique d'attente douce en boucle ;
     - carillon à chaque invité qui se connecte ;
     - accord quand tout le monde est là.
   - **Points du jury et du public :**
     - un son par pays, qui monte avec les points ;
     - fanfare à 12 points ;
     - roulement de tambour avant le dernier pays du public.
   - **Révélation et podium :**
     - roulement de tambour pendant la remontée ;
     - un son à chaque pays dépassé ;
     - fanfare et applaudissements pour le gagnant.
   - **Réglages › Dévoilement :** sons oui / non, un volume général, bouton muet sur la télé.
   - **Démarrage :** si le navigateur bloque le son, un bouton « Activer le son » s'affiche sur le premier écran. Un clic suffit pour la soirée.
   - **Rythme :** les sons suivent l'animation, en automatique comme en manuel, y compris quand la remontée accélère.
2. **Compte à rebours avant la révélation** (visuel 8b choisi) :
   - **Quand :** sur la télé, seulement avant la remontée du dernier pays (le dernier pas du public).
   - **Déroulé :** 5 → 0, une seconde par chiffre. Un cadre blanc part des bords de l'écran et se resserre ; à mi-chemin, il s'efface et laisse place à un grand chiffre fin (halo rose). Puis un éclair blanc, et la révélation.
3. **Commentaires dans le classement (téléphone) :**
   - Sous chaque chanson, une ligne en petit sous « 3e · noté 15 » montre le début de son commentaire.
   - Toucher la ligne montre le commentaire en entier.
   - La poignée et les flèches doivent continuer de marcher.

## 2. Technique

- **Sons :** module `frontend/src/lib/sons.js`.
  - Un seul `AudioContext`, créé au premier geste de l'utilisateur. Un gain général porte le volume et le muet.
  - Synthèse : oscillateurs et enveloppes pour le carillon, l'accord et la fanfare ; bruit filtré pour le tambour et les applaudissements ; musique d'attente en arpège lent.
  - Fonctions : `jouer(nom, options)` et `boucle(nom)` / `arreter(nom)`.
  - Fichier de Julien : si un fichier existe pour un nom, il est décodé une fois (`decodeAudioData`) et joué à la place du son fabriqué.
- **Fichiers de Julien :**
  - Rangés dans `/data/sons/<nom>.<ext>` ; liste et routes `GET/PUT/DELETE /api/sons/<nom>` derrière le mot de passe commun.
  - Formats : mp3, m4a, ogg, wav ; 5 Mo au plus. Le type est vérifié par les premiers octets.
  - Inclus dans la sauvegarde de nuit ? Non : un fichier n'est pas un réglage. Seul son nom est noté.
- **Réglages :** `sons` (oui par défaut), `volume_sons` (0 à 100, défaut 70), à côté des durées du dévoilement. Le muet de la télé est local à l'écran (`localStorage`, avec repli s'il est refusé).
- **Écrans qui jouent :** seulement les écrans de la télé.
  - `Accueil.svelte` (QR code) : boucle d'attente, carillon par nouvel invité, accord à « tout le monde est là ».
  - `Devoilement.svelte` : jury, public, révélation, podium.
  - Le téléphone d'un invité ne charge pas `sons.js`.
- **Points :**
  - Le son d'un pays au public a une hauteur qui monte avec le nombre de points.
  - 12 points : fanfare.
  - Juste avant le pas de la révélation : roulement de tambour.
- **Compte à rebours :**
  - Composant `lib/CompteRebours.svelte`, joué au début du pas de la révélation, avant `DernierVote`.
  - Côté serveur : `duree_revelation` ajoute 6 s, pour que le pas automatique ne parte pas avant la fin.
  - Mouvement réduit demandé par le système : les chiffres s'affichent sans le cadre qui bouge, toujours 6 s.
  - Le tambour joue pendant le compte, l'éclair blanc à 0.
- **Révélation :**
  - `DernierVote` signale chaque dépassement (`ondepasse`) et le gagnant ; `sons.js` joue un son à chaque dépassement.
  - Si la remontée accélère, les sons suivent ses étapes (aucun minuteur à part).
- **Classement du téléphone :**
  - `HAUTEUR` des lignes passe d'environ 64 px à 80 px pour faire place à une ligne de commentaire (tronquée).
  - Toucher la ligne ouvre une feuille en bas de l'écran avec le commentaire entier (et le pays, la note). La hauteur des lignes reste fixe : le glisser et les flèches ne changent pas.
  - La poignée et les flèches n'ouvrent pas la feuille.
- **Tests :**
  - Sons : appels de `sons.js` vérifiés par un faux `AudioContext` dans les tests d'écran.
  - Compte à rebours : présence, 6 chiffres, durée automatique +6 s.
  - Classement : la ligne de commentaire, la feuille, puis glisser après fermeture.
  - Routes des fichiers de son : taille, type, mot de passe.
  - Aucun son sur le téléphone.

## 3. Écrans

- **Télé :**
  - un petit bouton haut-parleur (muet / son) en haut de l'écran ;
  - « Activer le son » au premier écran si le son est bloqué ;
  - le compte à rebours plein écran.
- **Réglages › Dévoilement :**
  - « Sons sur la télé » (interrupteur) et le curseur de volume ;
  - la liste des 11 sons, chacun avec « Écouter », « Remplacer par un fichier » et « Revenir au son de l'appli ».
- **Téléphone :** la ligne de commentaire sous chaque chanson du classement, et la feuille du commentaire entier.

## 4. Questions pour le conseil

1. **Synthèse ou fichiers :** les sons fabriqués par le navigateur sont-ils assez bons pour une soirée, ou faut-il des fichiers libres de droits (CC0) embarqués dès le départ ?
2. **Compte à rebours :** il vit dans le dernier pas, ce qui allonge `duree_revelation` de 6 s. Faut-il plutôt un pas à part ?
3. **Le téléphone de l'hôte qui sert aussi de télé :** risque de son sur le téléphone ?
4. **Commentaire :** feuille du bas, ou ligne qui s'agrandit ?
5. **Tout en une version (1.11.0) :** est-ce trop risqué ?
