# Douze points 1.11.0 — avis du conseil (20/11/2026)

Dossier : `douze-points-1.11.0-dossier.md`. Cinq conseillers, trois relectures croisées, synthèse du président. Les choix de Julien ne changent pas ; voici ce qui change dans le plan.

## Ce qui change

1. **Les téléphones ne doivent pas montrer le gagnant avant la télé** (faille trouvée dans le code). `invite/Spectacle.svelte` lance `DernierVote` dès le dernier pas. Pendant les 6 s du compte à rebours, les téléphones affichent « Regardez la télé » ; ensuite seulement la remontée. `revelation_ms` (main.py) et `duree_revelation` comptent les 6 s.
2. **Compte à rebours dans le dernier pas, calé sur le serveur.** Il part de `pas_le` (heure de début du pas), pas du chargement de l'écran. Une télé rechargée pendant le compte reprend au bon chiffre ; rechargée après, elle n'a plus de compte. En manuel, « suivant » pendant le compte est ignoré.
3. **Un seul roulement de tambour.** Il commence avec le compte à rebours (c'est le « roulement avant le dernier pays ») et continue, en montant, pendant la remontée, jusqu'à la fanfare du gagnant. Pas de second tambour.
4. **Liste arrêtée des sons** (9) : `attente` (musique d'attente), `carillon` (invité connecté), `tous_la` (accord), `point` (un pays, hauteur selon les points, gamme pentatonique), `douze` (12 points), `tambour`, `depasse` (pays dépassé), `fanfare` (gagnant, motif du prélude du *Te Deum* de Charpentier, domaine public, joué par l'appli), `applaudissements`. Les sons fabriqués partagent une même tonalité.
5. **Sur la télé, sans surprise :**
   - le carillon sonne une fois par invité et par soirée, et l'accord une seule fois ;
   - la musique d'attente est plus douce que le reste et s'arrête quand tout le monde est là ;
   - le muet se voit de loin (haut-parleur barré) ;
   - les rafales de sons sont espacées d'au moins 90 ms, avec 6 sons au plus en même temps ;
   - le son reprend après une mise en veille (`resume()` au retour de l'onglet).
6. **« Activer le son », honnête.**
   - Le texte dit que le son se réactive d'un toucher après chaque rechargement, et que le bouton silencieux d'un iPhone coupe le son.
   - Le bouton se commande aussi au clavier ou à la télécommande (focus et Entrée).
7. **Fichiers de Julien.**
   - Réglages décode le fichier dans le navigateur avant de l'envoyer : un fichier illisible est refusé.
   - Un fichier perdu revient en silence au son fabriqué.
   - « Écouter » joue sur l'appareil où les Réglages sont ouverts (la régie charge `sons.js` ; les pages des invités, jamais).
8. **Éclair adouci** : un voile blanc à 50 % au plus, une fois, et rien si le mouvement réduit est demandé.
9. **Commentaires** : seulement les tiens (ton téléphone), pas de ligne si la chanson n'a pas de commentaire. La feuille s'ouvre d'un toucher sur la ligne, jamais depuis la poignée ou les flèches. `HAUTEUR` passe de 56 à 72 px.
10. **Ordre de travail**, un commit par étape :
    1. serveur : réglages, 6 s, routes des sons ;
    2. commentaires ;
    3. compte à rebours et attente des téléphones ;
    4. `sons.js` ;
    5. Réglages.

    Rien de tout cela n'a été essayé sur la vraie télé.

## Écarté

- **Pas à part pour le compte à rebours** : il toucherait `_bornes_auto`, le mode manuel et les téléphones, pour rien ce soir.
- **Bus d'événements, lumières de Home Assistant, citations pour la Gazette** : idées pour plus tard, notées dans les souhaits.
- **Sons coupés par défaut** : Julien a choisi les sons ; le muet et l'interrupteur des Réglages suffisent pour couper d'un geste.
