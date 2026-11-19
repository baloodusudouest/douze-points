"""Lecture de carnet (les contacts de la maison) : prénoms et noms, pour choisir les invités en tapant leur nom.

Douze points lit l'adresse /douze-points/personnes de carnet (jeton commun). 1.5 : après le dévoilement, la soirée part
à l'adresse commune des événements de carnet 3.1 (`PUT /evenements/douze-points/soiree-<id>`), avec la note moyenne,
le classement et le podium de chaque invité ; un envoi raté est gardé et réessayé.
La liste est gardée dix minutes en mémoire ; rien n'en est écrit dans la base tant qu'un invité n'est pas choisi.
"""
from __future__ import annotations

import time
import unicodedata

import httpx

DUREE = 600
_memoire: dict = {"le": 0.0, "personnes": None}


def appeler(url: str, jeton: str) -> list[dict]:
    """Le seul appel réseau du module (remplacé dans les tests par un faux carnet)."""
    r = httpx.get(f"{url}/douze-points/personnes", headers={"Authorization": f"Bearer {jeton}"}, timeout=5)
    r.raise_for_status()
    return r.json()["personnes"]


def regle(cfg) -> bool:
    return bool(cfg.carnet_url and cfg.carnet_jeton)


def personnes(cfg, frais: bool = False) -> list[dict]:
    if not regle(cfg):
        return []
    if frais or _memoire["personnes"] is None or time.monotonic() - _memoire["le"] > DUREE:
        lues = appeler(cfg.carnet_url, cfg.carnet_jeton)
        _memoire.update(le=time.monotonic(), personnes=[
            {"carnet_id": str(p["carnet_id"]), "personne_id": str(p.get("personne_id") or ""),   # 1.5 : identifiant maison
             "prenom": str(p["prenom"]).strip(), "nom": str(p["nom"]).strip()}
            for p in lues if p.get("carnet_id") and str(p.get("prenom") or "").strip()])
    return _memoire["personnes"]


def oublier() -> None:
    _memoire.update(le=0.0, personnes=None)


def cle(texte: str) -> str:
    """Sans accents ni majuscules : « helene » trouve « Hélène »."""
    return "".join(c for c in unicodedata.normalize("NFD", texte.casefold()) if unicodedata.category(c) != "Mn")


def chercher(cfg, saisie: str, limite: int = 8) -> list[dict]:
    """Les personnes dont le prénom ou un mot du nom commence par chaque mot tapé."""
    mots = cle(saisie).split()
    if not mots:
        return []
    trouves = []
    for p in personnes(cfg):
        debuts = cle(f"{p['prenom']} {p['nom']}").replace("-", " ").split()
        if all(any(d.startswith(m) for d in debuts) for m in mots):
            trouves.append(p)
    trouves.sort(key=lambda p: (cle(p["prenom"]), cle(p["nom"])))
    return trouves[:limite]


def initiale(personne: dict) -> str:
    """L'initiale du nom de famille : le nom de la fiche, prénom retiré."""
    reste = [m for m in personne["nom"].split() if cle(m) not in {cle(x) for x in personne["prenom"].split()}]
    return reste[-1][0].upper() if reste else ""


def envoyer(url: str, jeton: str, methode: str, chemin: str, corps: dict | None) -> tuple[int, dict]:
    """1.5 : un envoi vers carnet 3.1 : (statut, réponse). Exceptions réseau laissées à l'appelant (remplacé dans les tests)."""
    r = httpx.request(methode, f"{url}{chemin}", json=corps, headers={"Authorization": f"Bearer {jeton}"}, timeout=8)
    try:
        donnees = r.json()
    except ValueError:
        donnees = {}
    return r.status_code, donnees if isinstance(donnees, dict) else {}
