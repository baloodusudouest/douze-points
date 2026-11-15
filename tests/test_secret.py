"""Le secret : avant la fin du dévoilement, la porte invité ne rend rien des autres.

Chaque adresse de la porte invité est appelée dans chaque état de la soirée, avec et sans téléphone reconnu,
et la réponse est fouillée : ni le commentaire d'un autre, ni sa note, ni un total. Une adresse ajoutée à la
porte invité sans être ajoutée ici fait échouer le dernier test.
"""
import json

from app import main
from tests.conftest import PRENOMS

LECTURES = ("etat", "resultats")
MARQUES = [f"Avis de {p}" for p in PRENOMS]


def fuites(texte: str, moi: str | None) -> list[str]:
    """Ce qui ne devrait pas être là : les commentaires des autres, et tout mot de résultat."""
    trouves = [m for m, p in zip(MARQUES, PRENOMS) if p != moi and m in texte]
    return trouves + [mot for mot in ('"total"', '"points"', '"classement": [{', '"moyenne"') if mot in texte]


def lectures(client, soiree, prenom):
    for adresse in LECTURES:
        r = client.get(soiree.url(adresse), headers=soiree.tel.get(prenom, {}) if prenom else {})
        yield adresse, r


def test_rien_des_autres_pendant_la_soiree(client, soiree):
    soiree.tout_le_monde()
    for prenom in (None, "Aglaé", "Désiré"):
        for adresse, r in lectures(client, soiree, prenom):
            assert fuites(r.text, prenom) == [], (adresse, prenom)
    moi = soiree.etat("Aglaé")["moi"]
    assert all(n["commentaire"] == "Avis de Aglaé" for n in moi["notes"].values())      # sa propre copie, oui


def test_rien_des_autres_pendant_le_devoilement(client, soiree):
    soiree.tout_le_monde()
    client.post(f"/api/soirees/{soiree.id}/devoiler")
    client.post(f"/api/soirees/{soiree.id}/pas", json={"pas": 9})
    for prenom in (None, "Aglaé", "Désiré"):
        for adresse, r in lectures(client, soiree, prenom):
            assert fuites(r.text, prenom) == [], (adresse, prenom)
    assert client.get(soiree.url("resultats")).status_code == 409


def test_resultats_ouverts_une_fois_le_devoilement_fini(client, soiree):
    soiree.tout_le_monde()
    client.post(f"/api/soirees/{soiree.id}/devoiler")
    client.post(f"/api/soirees/{soiree.id}/terminer")
    r = client.get(soiree.url("resultats"))
    assert r.status_code == 200 and all(m in r.text for m in MARQUES)
    assert len(r.json()["classement"]) == 12


def test_la_regie_ne_montre_aucune_note_avant_le_devoilement(client, soiree):
    soiree.tout_le_monde()
    texte = client.get(f"/api/soirees/{soiree.id}").text
    assert not any(m in texte for m in MARQUES) and '"valeur"' not in texte and '"points"' not in texte
    assert client.get(f"/api/soirees/{soiree.id}/devoilement").status_code == 409


def test_la_porte_invite_ne_mene_pas_a_la_regie(client, soiree):
    client.cookies.clear()
    assert client.get("/api/soirees").status_code == 401
    assert client.get(f"/api/soirees/{soiree.id}/devoilement").status_code == 401
    assert client.get(soiree.url("etat")).status_code == 200


def test_toutes_les_adresses_invite_sont_couvertes():
    """Les lectures de la porte invité sont exactement celles que ce fichier fouille."""
    lues = {r.path.rsplit("/", 1)[1] for r in main.app.routes
            if getattr(r, "path", "").startswith("/invite/") and "GET" in getattr(r, "methods", ())}
    assert lues == set(LECTURES)
    ecritures = {r.path.rsplit("/", 1)[1] for r in main.app.routes
                 if getattr(r, "path", "").startswith("/invite/") and "GET" not in getattr(r, "methods", ())}
    assert ecritures == {"prenom", "note", "classement", "envoyer", "modifier"}


def test_les_ecritures_ne_rendent_que_sa_propre_copie(client, soiree):
    soiree.tout_le_monde()
    tel = soiree.tel["Aglaé"]
    reponses = [
        client.put(soiree.url("note"), headers=tel, json={"chanson_id": soiree.chansons[0], "valeur": 7, "commentaire": "Avis de Aglaé"}),
        client.put(soiree.url("classement"), headers=tel, json={"auto": True}),
        client.post(soiree.url("envoyer"), headers=tel),
        client.post(soiree.url("modifier"), headers=tel),
    ]
    for r in reponses:
        assert r.status_code == 200 and fuites(json.dumps(r.json(), ensure_ascii=False), "Aglaé") == []
