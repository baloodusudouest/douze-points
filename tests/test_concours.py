"""La liste des concours, réglée dans l'appli."""
from tests.conftest import connecter


def noms(client, actifs=True):
    return [c["nom"] for c in client.get("/api/concours").json() if c["actif"] or not actifs]


def test_liste_de_depart_ajout_et_creation(client):
    connecter(client)
    assert noms(client) == ["Eurovision", "Eurovision Asia"]
    nouvelle = {"concours": "Melodifestivalen", "annee": 2027, "emission": "finale", "nom": "Soirée suédoise"}
    assert client.post("/api/soirees", json=nouvelle).status_code == 422            # pas encore dans la liste
    assert client.post("/api/concours", json={"nom": "  Melodifestivalen "}).status_code == 200
    assert client.post("/api/concours", json={"nom": "melodifestivalen"}).status_code == 409   # déjà là, à la casse près
    assert client.post("/api/concours", json={"nom": "  "}).status_code == 422
    assert noms(client) == ["Eurovision", "Eurovision Asia", "Melodifestivalen"]
    assert client.post("/api/soirees", json=nouvelle).status_code == 200
    assert client.get("/api/soirees").json()[0]["concours"] == "Melodifestivalen"


def test_retirer(client, soiree):
    liste = {c["nom"]: c for c in client.get("/api/concours").json()}
    assert liste["Eurovision"]["soirees"] == 1
    # sans soirée : effacé pour de bon
    assert client.delete(f"/api/concours/{liste['Eurovision Asia']['id']}").status_code == 200
    assert noms(client, actifs=False) == ["Eurovision"]
    # le dernier ne se retire pas
    assert client.delete(f"/api/concours/{liste['Eurovision']['id']}").status_code == 409
    # avec une soirée : retiré de la liste proposée, la soirée garde son nom, et il peut revenir
    client.post("/api/concours", json={"nom": "Intervision"})
    assert client.delete(f"/api/concours/{liste['Eurovision']['id']}").status_code == 200
    assert noms(client) == ["Intervision"]
    assert client.get(f"/api/soirees/{soiree.id}").json()["concours"] == "Eurovision"
    assert client.post("/api/concours", json={"nom": "Eurovision"}).status_code == 200
    assert noms(client) == ["Eurovision", "Intervision"]


def test_ferme_sans_connexion(client):
    assert client.get("/api/concours").status_code == 401
    assert client.post("/api/concours", json={"nom": "X"}).status_code == 401
