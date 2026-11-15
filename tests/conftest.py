"""Outils communs aux tests : une appli sur un dossier vide, et une soirée inventée (personnes inventées)."""
import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import Config

MOT_DE_PASSE = "mot-de-passe-de-test"
PRENOMS = ["Aglaé", "Barnabé", "Célestine", "Désiré"]


@pytest.fixture()
def client(tmp_path):
    main.ETAT.clear()
    main.ETAT["cfg"] = Config(password=MOT_DE_PASSE, data=tmp_path, static=tmp_path / "static",
                              attente_connexion=False, adresse="http://192.0.2.10:8088", limite_invite=100000)
    with TestClient(main.app) as c:
        yield c
    main.ETAT.clear()


def connecter(client):
    assert client.post("/api/connexion", json={"mot_de_passe": MOT_DE_PASSE}).status_code == 200


class Soiree:
    """Une soirée de démonstration : `n` chansons (Pays 1…n) et quatre invités inventés."""

    def __init__(self, client, n=12, ouvrir=True):
        self.c = client
        connecter(client)
        self.id = client.post("/api/soirees", json={"concours": "Eurovision", "annee": 2027, "emission": "finale",
                                                    "nom": "Finale de démonstration"}).json()["id"]
        texte = "\n".join(f"Pays {i}\tArtiste {i}\tTitre {i}" for i in range(1, n + 1))
        self.chansons = [x["id"] for x in client.put(f"/api/soirees/{self.id}/chansons", json={"texte": texte}).json()["chansons"]]
        ids = [client.post("/api/invites", json={"prenom": p}).json()["id"] for p in PRENOMS]
        gens = client.put(f"/api/soirees/{self.id}/attendus", json={"invites": ids}).json()["participants"]
        self.part = {g["prenom"]: g["id"] for g in gens}
        self.jeton = client.get(f"/api/soirees/{self.id}").json()["jeton_invite"]
        self.tel = {}
        if ouvrir:
            assert client.post(f"/api/soirees/{self.id}/ouvrir").status_code == 200

    def url(self, suite):
        return f"/invite/{self.jeton}/api/{suite}"

    def entrer(self, prenom):
        r = self.c.post(self.url("prenom"), json={"participation_id": self.part[prenom]})
        assert r.status_code == 200, r.text
        self.tel[prenom] = {"X-Telephone": r.json()["jeton_telephone"]}
        return self.tel[prenom]

    def noter(self, prenom, notes, commentaire=""):
        """notes : {rang de passage (1…n): note sur 20}"""
        tel = self.tel.get(prenom) or self.entrer(prenom)
        for passage, valeur in notes.items():
            r = self.c.put(self.url("note"), headers=tel, json={"chanson_id": self.chansons[passage - 1],
                                                                 "valeur": valeur, "commentaire": commentaire})
            assert r.status_code == 200, r.text

    def envoyer(self, prenom):
        return self.c.post(self.url("envoyer"), headers=self.tel[prenom])

    def etat(self, prenom=None):
        return self.c.get(self.url("etat"), headers=self.tel.get(prenom, {})).json()

    def tout_le_monde(self):
        """Chacun note toutes les chansons, différemment, et envoie."""
        n = len(self.chansons)
        for k, prenom in enumerate(PRENOMS):
            self.noter(prenom, {i: ((i * (k + 3)) % 41) / 2 for i in range(1, n + 1)}, commentaire=f"Avis de {prenom}")
            assert self.envoyer(prenom).status_code == 200


@pytest.fixture()
def soiree(client):
    return Soiree(client)
