"""Santé des tâches de fond (1.4, socle 0.9.0) : /health porte version_socle, taches et copie_base ; messages
d'erreur seulement avec le jeton commun ; une copie de nuit ratée fait passer la tâche en retard."""
import asyncio
import sqlite3
from datetime import datetime, timezone

import pytest

from app import maison

COMMUN = "jeton-commun-de-test"


@pytest.fixture()
def registre(monkeypatch):
    neuf = maison.Taches()
    monkeypatch.setattr(maison, "TACHES", neuf)
    return neuf


def test_health_porte_taches_et_copie(registre, client, monkeypatch):
    monkeypatch.setenv("MAISON_JETON", COMMUN)
    d = client.get("/health").json()
    assert d["ok"] is True and d["version_socle"] == "0.11.1"
    noms = {t["nom"]: t for t in d["taches"]}
    assert set(noms) == {"copie-des-bases", "envoi-immich"}      # 1.6 : envoi des photos vers Immich, toutes les 10 min
    assert noms["envoi-immich"]["type"] == "reguliere" and noms["envoi-immich"]["periode_s"] == 600
    assert noms["copie-des-bases"]["type"] == "reguliere" and noms["copie-des-bases"]["periode_s"] == 86400
    assert noms["copie-des-bases"]["etat"] == "jamais"
    assert all("message" not in t for t in d["taches"])                 # sans jeton : pas de message
    assert d["copie_base"]["bases"] == ["douze-points.db"] and d["copie_base"]["le"] is None
    avec = client.get("/health", headers={"Authorization": f"Bearer {COMMUN}"}).json()
    assert all("message" in t for t in avec["taches"])
    assert all("message" not in t for t in client.get("/health", headers={"Authorization": "Bearer faux"}).json()["taches"])


def test_copie_ratee_passe_en_retard(registre, tmp_path, monkeypatch):
    """Une copie de nuit qui échoue : la boucle continue, la tâche passe en retard avec un message court."""
    base = tmp_path / "douze-points.db"
    cx = sqlite3.connect(base)
    cx.execute("CREATE TABLE t (x)")
    cx.commit()
    cx.close()

    def casse(chemins, dossier, ouvrir=None):
        raise OSError("disque plein (essai)")
    monkeypatch.setattr(maison, "copier_bases", casse)
    monkeypatch.setattr(maison, "prochaine_copie", lambda h, *a, **k: datetime.now(timezone.utc))   # pas d'attente

    async def sans_attente(_):
        return None
    asyncio.run(maison.planifier_copie("douze-points", [base], tmp_path / "copies", dormir=sans_attente, tours=1))
    t = {x["nom"]: x for x in registre.etat(avec_messages=True)}["copie-des-bases"]
    assert t["etat"] == "en_retard" and "disque plein" in t["message"]
