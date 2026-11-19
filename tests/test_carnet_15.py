"""1.5 : la soirée dévoilée part à carnet 3.1 (adresse commune des événements), avec note moyenne, classement et
podium de chaque invité ; identifiant maison gardé à l'ajout depuis carnet ; envoi gardé et réessayé. Personnes
inventées."""
import dataclasses

import pytest

from app import carnet, main
from tests.conftest import PRENOMS, Soiree

FAUX = [{"carnet_id": "AAAA-3", "personne_id": "p-00000000aa", "prenom": "Aglaé", "nom": "Aglaé MARCHAND"},
        {"carnet_id": "AAAA-9", "personne_id": "p-00000000bb", "prenom": "Zoé", "nom": "Zoé MARTIN"}]


@pytest.fixture()
def relie(client, monkeypatch):
    monkeypatch.setattr(carnet, "appeler", lambda url, jeton: FAUX)
    carnet.oublier()
    main.ETAT["cfg"] = dataclasses.replace(main.ETAT["cfg"], carnet_url="http://carnet.exemple", carnet_jeton="jeton-de-test")
    envois = {"appels": [], "arrete": False}

    def faux(url, jeton, methode, chemin, corps):
        if envois["arrete"]:
            raise ConnectionError("refusé")
        envois["appels"].append((methode, chemin, corps))
        return 200, {"reconnues": 1, "a_rattacher": []}
    monkeypatch.setattr(main, "ENVOYER_CARNET", faux)
    yield envois
    carnet.oublier()


def _jouer(client, soiree):
    soiree.tout_le_monde()
    assert client.post(f"/api/soirees/{soiree.id}/devoiler").status_code == 200
    return client.post(f"/api/soirees/{soiree.id}/terminer").json()


def test_15_soiree_envoyee_apres_le_devoilement(client, relie):
    soiree = Soiree(client, n=6, ouvrir=False)
    zoe = client.post("/api/invites", json={"carnet_id": "AAAA-9"}).json()["id"]          # choisie dans carnet
    ids = [i["id"] for i in client.get("/api/invites").json() if i["prenom"] in PRENOMS] + [zoe]
    client.put(f"/api/soirees/{soiree.id}/attendus", json={"invites": ids})
    soiree.part = {g["prenom"]: g["id"] for g in client.get(f"/api/soirees/{soiree.id}").json()["participants"]}
    assert client.post(f"/api/soirees/{soiree.id}/ouvrir").status_code == 200
    soiree.tout_le_monde()
    soiree.noter("Zoé", {i: 10 for i in range(1, 7)})
    soiree.envoyer("Zoé")
    client.post(f"/api/soirees/{soiree.id}/devoiler")
    r = client.post(f"/api/soirees/{soiree.id}/terminer").json()
    assert r["carnet"] == "envoyé à carnet"
    methode, chemin, corps = relie["appels"][-1]
    assert methode == "PUT" and chemin == f"/evenements/douze-points/soiree-{soiree.id}"
    assert corps["type"] == "douze_points" and corps["titre"] == "Finale de démonstration"
    assert corps["lien"] == f"http://192.0.2.10:8088/#/soiree/{soiree.id}"
    z = next(p for p in corps["personnes"] if p["nom"] == "Zoé")
    assert z["personne_id"] == "p-00000000bb" and z["donnees"]["moyenne"] is not None
    a = next(p for p in corps["personnes"] if p["nom"] == "Aglaé")
    assert "personne_id" not in a                                       # tapée à la main : carnet cherchera le prénom
    assert len(a["donnees"]["top3"]) == 3 and isinstance(a["donnees"]["classement"], int)
    r = a["donnees"]["remarques"]                                       # les plus sévères d'abord (points de 12 à 0)
    assert r and r[0]["commentaire"] == "Avis de Aglaé" and [x["points"] for x in r] == sorted(x["points"] for x in r)
    assert all(0 <= x["points"] <= 12 for x in r) and len(r) <= 5


def test_15_carnet_arrete_envoi_garde_puis_renvoye(client, relie):
    soiree = Soiree(client, n=6)
    relie["arrete"] = True
    r = _jouer(client, soiree)
    assert "envoi gardé" in r["carnet"]
    relie["arrete"] = False
    assert main.renvoyer_a_carnet() == 1 and main.renvoyer_a_carnet() == 0
    assert client.post("/api/carnet/envoyer").json() == {"soirees": 1, "envoyees": 1, "en_attente": 0}


def test_15_sans_carnet_rien_ne_part(client):
    soiree = Soiree(client, n=6)
    assert _jouer(client, soiree)["carnet"] == "carnet pas réglé : rien n'est envoyé"
