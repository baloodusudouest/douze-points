"""1.6 : les photos de la soirée envoyées à Immich, côté serveur (clé DOUZE_POINTS_IMMICH_CLE, jamais vue des téléphones).

Chaque fonction fait un seul appel et laisse remonter les erreurs réseau : la file d'envoi (main.envoyer_photos) décide
du nouvel essai. `CLIENT` se remplace dans les tests par un faux Immich (httpx.MockTransport).

Permissions de la clé : asset.upload, asset.update, album.read, album.create, albumAsset.create, tag.read, tag.create,
tag.asset, apiKey.read (contrôle de l'écran Connexion).
"""
from __future__ import annotations

from pathlib import Path

import httpx

PERMISSIONS = ("asset.upload", "asset.update", "album.read", "album.create", "albumAsset.create",
               "tag.read", "tag.create", "tag.asset")
DELAI = httpx.Timeout(10.0, read=60.0, write=120.0)     # une photo de 25 Mo sur le réseau de la stack
CLIENT: httpx.Client | None = None                      # tests : un faux Immich


class ImmichErreur(Exception):
    """Immich a répondu, mais pas ce qu'il fallait (statut inattendu). `statut` dit lequel."""

    def __init__(self, message: str, statut: int = 0):
        super().__init__(message)
        self.statut = statut


def regle(cfg) -> bool:
    return bool(cfg.immich_url and cfg.immich_cle)


def _appel(cfg, methode: str, chemin: str, **kw) -> httpx.Response:
    entetes = {"x-api-key": cfg.immich_cle, "Accept": "application/json"}
    if CLIENT is not None:
        r = CLIENT.request(methode, cfg.immich_url + chemin, headers=entetes, **kw)
    else:
        with httpx.Client(timeout=DELAI) as c:
            r = c.request(methode, cfg.immich_url + chemin, headers=entetes, **kw)
    return r


def _json(r: httpx.Response, *attendus: int):
    if r.status_code not in attendus:
        try:
            detail = r.json().get("message")
        except (ValueError, AttributeError):
            detail = ""
        if isinstance(detail, list):
            detail = " ; ".join(str(x) for x in detail)
        raise ImmichErreur(f"Immich a répondu {r.status_code}{(' : ' + str(detail)[:120]) if detail else ''}",
                           r.status_code)
    try:
        return r.json()
    except ValueError:
        return {}


def envoyer_image(cfg, chemin: Path, type_mime: str, identifiant: str, quand: str) -> tuple[str, bool]:
    """Envoie une image ; rend (identifiant Immich, doublon). Une image déjà connue d'Immich (même contenu) rend
    l'identifiant de celle qui existe (statut « duplicate ») : un nouvel essai après une coupure ne crée rien."""
    with open(chemin, "rb") as f:
        r = _appel(cfg, "POST", "/api/assets",
                   data={"deviceAssetId": identifiant, "deviceId": "douze-points",
                         "fileCreatedAt": quand, "fileModifiedAt": quand},
                   files={"assetData": (chemin.name, f, type_mime)})
    d = _json(r, 200, 201)
    if not d.get("id"):
        raise ImmichErreur("Immich n'a pas rendu d'identifiant pour la photo.")
    return str(d["id"]), d.get("status") == "duplicate"


def creer_album(cfg, nom: str, ids: list[str]) -> str:
    d = _json(_appel(cfg, "POST", "/api/albums", json={"albumName": nom, "assetIds": ids}), 200, 201)
    if not d.get("id"):
        raise ImmichErreur("Immich n'a pas rendu d'identifiant pour l'album.")
    return str(d["id"])


def ajouter_album(cfg, album: str, ids: list[str]) -> bool:
    """Ajoute à un album existant. Rend False si l'album n'existe plus (supprimé dans Immich : à recréer).
    Une photo déjà dans l'album n'est pas une erreur."""
    r = _appel(cfg, "PUT", f"/api/albums/{album}/assets", json={"ids": ids})
    if r.status_code in (400, 404):
        return False
    for x in _json(r, 200, 201) or []:
        if isinstance(x, dict) and not x.get("success") and x.get("error") not in ("duplicate", None):
            raise ImmichErreur(f"Ajout à l'album refusé ({x.get('error')}).")
    return True


def decrire(cfg, asset: str, description: str) -> None:
    _json(_appel(cfg, "PUT", f"/api/assets/{asset}", json={"description": description}), 200)


def taguer(cfg, nom: str, ids: list[str]) -> None:
    """Le tag est créé s'il n'existe pas (PUT /api/tags : création ou reprise), puis posé sur les photos."""
    tags = _json(_appel(cfg, "PUT", "/api/tags", json={"tags": [nom]}), 200, 201) or []
    tag = next((t for t in tags if isinstance(t, dict) and (t.get("value") == nom or t.get("name") == nom)), None)
    if not tag:
        raise ImmichErreur(f"Immich n'a pas rendu le tag « {nom} ».")
    _json(_appel(cfg, "PUT", f"/api/tags/{tag['id']}/assets", json={"ids": ids}), 200, 201)


def verifier(cfg) -> dict:
    """Pour l'écran Connexion : version d'Immich, permissions de la clé, celles qui manquent."""
    if not regle(cfg):
        return {"regle": False}
    try:
        v = _json(_appel(cfg, "GET", "/api/server/version"), 200)
        cle = _json(_appel(cfg, "GET", "/api/api-keys/me"), 200)
    except ImmichErreur as e:
        return {"regle": True, "ok": False, "message": str(e)}
    except httpx.HTTPError as e:
        return {"regle": True, "ok": False, "message": f"Immich injoignable ({type(e).__name__})"}
    perms = list(cle.get("permissions") or [])
    manque = [] if "all" in perms else [p for p in PERMISSIONS if p not in perms]
    version = ".".join(str(v.get(k, "")) for k in ("major", "minor", "patch")) if v else ""
    return {"regle": True, "ok": not manque, "version": version, "manque": manque,
            "message": "" if not manque else "Permissions manquantes : " + ", ".join(manque)}
