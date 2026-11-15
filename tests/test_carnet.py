"""Les invités choisis dans carnet. carnet est remplacé par un faux, écrit d'après la vraie adresse
/douze-points/personnes (carnet 2.22.1) : {"personnes": [{"carnet_id", "prenom", "nom"}]}. Personnes inventées."""
import dataclasses

import pytest

from app import carnet, main
from tests.conftest import PRENOMS, connecter

FAUX = [
    {"carnet_id": "AAAA-1", "prenom": "Hélène", "nom": "Hélène DUBOIS"},
    {"carnet_id": "AAAA-2", "prenom": "Henri", "nom": "Henri LEROY"},
    {"carnet_id": "AAAA-3", "prenom": "Aglaé", "nom": "Aglaé MARCHAND"},
    {"carnet_id": "AAAA-4", "prenom": "Jean-Marc", "nom": "Jean-Marc de la FONTAINE"},
    {"carnet_id": "AAAA-5", "prenom": "", "nom": "Garage du Centre"},
]


@pytest.fixture()
def relie(client, monkeypatch):
    appels = []
    def faux(url, jeton):
        appels.append((url, jeton))
        return FAUX
    monkeypatch.setattr(carnet, "appeler", faux)
    carnet.oublier()
    main.ETAT["cfg"] = dataclasses.replace(main.ETAT["cfg"], carnet_url="http://carnet.exemple", carnet_jeton="jeton-de-test")
    connecter(client)
    yield appels
    carnet.oublier()


def test_sans_reglage_carnet_n_est_pas_lu(client):
    connecter(client)
    assert client.get("/api/carnet/personnes?q=he").json() == {"relie": False, "personnes": []}
    assert client.get("/api/services").json()[0]["regle"] is False


def test_chercher_en_tapant(client, relie):
    cherche = lambda q: [p["nom"] for p in client.get("/api/carnet/personnes", params={"q": q}).json()["personnes"]]
    assert cherche("he") == ["Hélène DUBOIS", "Henri LEROY"]            # sans accent, début de prénom
    assert cherche("LER") == ["Henri LEROY"]                            # début de nom
    assert cherche("hel dub") == ["Hélène DUBOIS"]                      # prénom et nom
    assert cherche("marc") == ["Aglaé MARCHAND", "Jean-Marc de la FONTAINE"]      # début d'un nom, second prénom composé
    assert cherche("gar") == [] and cherche("") == [] and cherche("zz") == []      # ni entreprise, ni saisie vide
    assert relie == [("http://carnet.exemple", "jeton-de-test")]        # une seule lecture : la liste est gardée dix minutes


def test_ajouter_depuis_carnet_ne_garde_que_le_prenom(client, relie):
    identifiant = client.post("/api/invites", json={"carnet_id": "AAAA-1"}).json()["id"]
    assert client.post("/api/invites", json={"carnet_id": "AAAA-1"}).json()["id"] == identifiant     # pas de doublon
    assert [i["prenom"] for i in client.get("/api/invites").json()] == ["Hélène"]
    assert "DUBOIS" not in client.get("/api/invites").text
    # prénom déjà pris par un invité saisi à la main : l'initiale du nom les distingue
    client.post("/api/invites", json={"prenom": "Aglaé"})
    client.post("/api/invites", json={"carnet_id": "AAAA-3"})
    assert sorted(i["prenom"] for i in client.get("/api/invites").json()) == ["Aglaé", "Aglaé M.", "Hélène"]
    assert client.post("/api/invites", json={"carnet_id": "inconnu"}).status_code == 404


def test_connexion_verifier_et_carnet_muet(client, relie, monkeypatch):
    tuile = client.get("/api/services").json()[0]
    assert tuile["regle"] is True and tuile["ok"] is None and tuile["ecrit"] == "Rien."
    assert client.get("/api/services?verifier=true").json()[0]["detail"] == "4 personnes lues."
    def muet(url, jeton):
        raise ConnectionError("carnet arrêté")
    monkeypatch.setattr(carnet, "appeler", muet)
    carnet.oublier()
    assert client.get("/api/services?verifier=true").json()[0]["ok"] is False
    assert client.get("/api/carnet/personnes?q=he").status_code == 502
    assert client.post("/api/invites", json={"prenom": "Barnabé"}).status_code == 200      # à la main, toujours possible


def test_ferme_sans_connexion(client):
    assert client.get("/api/carnet/personnes?q=he").status_code == 401
    assert client.get("/api/services").status_code == 401
