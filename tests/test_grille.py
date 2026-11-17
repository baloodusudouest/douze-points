"""Grille papier (1.3) : l'hôte recopie la grille d'un invité à sa place ; correction d'un libellé soirée ouverte."""
from urllib.parse import urlsplit

from tests.conftest import Soiree


def jeton_du_lien(lien: str) -> str:
    morceaux = urlsplit(lien)
    assert morceaux.fragment.startswith("saisie=")
    return morceaux.fragment.removeprefix("saisie=")


def test_saisie_au_nom_d_un_invite(client, soiree):
    r = client.post(f"/api/soirees/{soiree.id}/saisie", json={"participation_id": soiree.part["Célestine"]})
    assert r.status_code == 200
    lien = r.json()["lien"]
    assert lien.startswith(f"/invite/{soiree.jeton}#saisie=") and set(r.json()) == {"lien"}   # aucune note, rien d'autre
    tel = {"X-Telephone": jeton_du_lien(lien)}
    etat = client.get(soiree.url("etat"), headers=tel).json()
    assert etat["moi"]["prenom"] == "Célestine"
    # l'hôte note et envoie à sa place, comme sur un téléphone
    for c in soiree.chansons[:3]:
        assert client.put(soiree.url("note"), headers=tel, json={"chanson_id": c, "valeur": 15}).status_code == 200
    assert client.post(soiree.url("envoyer"), headers=tel).status_code == 200
    p = next(g for g in client.get(f"/api/soirees/{soiree.id}").json()["participants"] if g["prenom"] == "Célestine")
    assert p["etat"] == "envoye" and p["notees"] == 3
    # le journal garde la saisie, jamais le jeton
    journal = client.get("/api/journal").text
    assert "saisie_papier" in journal and tel["X-Telephone"] not in journal


def test_saisie_reprend_la_main_sur_le_telephone(client, soiree):
    soiree.noter("Aglaé", {1: 12, 2: 9})
    ancien = soiree.tel["Aglaé"]
    lien = client.post(f"/api/soirees/{soiree.id}/saisie", json={"participation_id": soiree.part["Aglaé"]}).json()["lien"]
    nouveau = {"X-Telephone": jeton_du_lien(lien)}
    assert client.get(soiree.url("etat"), headers=ancien).json()["moi"] is None           # le téléphone perd la main
    moi = client.get(soiree.url("etat"), headers=nouveau).json()["moi"]
    assert moi["prenom"] == "Aglaé" and len(moi["notes"]) == 2                              # ses notes restent


def test_saisie_seulement_soiree_ouverte(client):
    brouillon = Soiree(client, ouvrir=False)
    r = client.post(f"/api/soirees/{brouillon.id}/saisie", json={"participation_id": brouillon.part["Aglaé"]})
    assert r.status_code == 409
    assert client.post(f"/api/soirees/{brouillon.id}/ouvrir").status_code == 200
    assert client.post(f"/api/soirees/{brouillon.id}/saisie", json={"participation_id": 999}).status_code == 404


def test_saisie_demande_la_regie(client, soiree):
    client.post("/api/deconnexion")
    r = client.post(f"/api/soirees/{soiree.id}/saisie", json={"participation_id": soiree.part["Aglaé"]})
    assert r.status_code == 401


def test_corriger_un_libelle_soiree_ouverte(client, soiree):
    c = soiree.chansons[0]
    assert client.put(f"/api/chansons/{c}", json={"pays": "Pays corrigé", "artiste": "Artiste", "titre": "Titre"}).status_code == 200
    chanson = next(x for x in soiree.etat()["chansons"] if x["id"] == c)
    assert (chanson["pays"], chanson["artiste"], chanson["titre"]) == ("Pays corrigé", "Artiste", "Titre")
    assert client.put(f"/api/chansons/{c}", json={"pays": "   "}).status_code == 422
    assert client.put("/api/chansons/99999", json={"titre": "x"}).status_code == 404
