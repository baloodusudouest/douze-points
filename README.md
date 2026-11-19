# Douze points

Appli maison pour les soirées de concours de chansons : chaque invité note les chansons sur son téléphone, range son classement, et le classement du groupe est dévoilé à la fin, façon concours (12, 10, 8… 1 point).

État : une soirée se joue de bout en bout (voir `REPRISE.md`, puis `docs/dossier.md`). Jamais essayée sur la vraie installation.

## Installation

Service à placer dans la stack (voir `docker-compose.yml` et `.env.example`). Variables lues :

| Variable | Rôle |
|---|---|
| `MAISON_PASSWORD` | mot de passe commun des applis maison, obligatoire (12 caractères au moins) |
| `MAISON_JETON` | jeton commun : demandes à carnet, annuaire de l'Anneau, sauvegarde des réglages ; vide : rien de tout cela |
| `MAISON_ANNEAU_URL` | facultatif, adresse de l'Anneau dans la stack (défaut `http://anneau:8094`) |
| `DOUZE_POINTS_CARNET_URL` | carnet vu depuis le conteneur ; vide : les invités s'ajoutent à la main |
| `DOUZE_POINTS_IMMICH_URL` | 1.6 : Immich vu depuis le conteneur (défaut `http://immich_server:2283`) |
| `DOUZE_POINTS_IMMICH_CLE` | 1.6 : clé d'API Immich propre à Douze points (permissions : asset.upload, asset.update, album.read, album.create, albumAsset.create, tag.read, tag.create, tag.asset, apiKey.read) ; vide : pas de photos |

L'adresse donnée aux invités (QR code, lien) est l'adresse **locale** de la tuile « Douze points » de l'Anneau. Si l'Anneau ne répond pas, pas de QR code : l'écran le dit.

## Réglages et sauvegarde

Les réglages d'usage se changent dans l'écran **Réglages** : pas de la note (au point, au demi-point, au quart de point) et adresse du webhook de Home Assistant. Ce dernier est repris une seule fois de l'ancienne variable `DOUZE_POINTS_HA_WEBHOOK` au premier démarrage de la 1.2, puis seul l'écran fait foi.

L'Anneau collecte chaque nuit les réglages par `GET /externe/sauvegarde` (jeton commun ; contrat de sauvegarde 1). Le webhook n'en sort jamais. « Restaurer les réglages » relit une sauvegarde chez l'Anneau, montre les différences et les applique après confirmation.
