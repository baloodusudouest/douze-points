"""Écarts et affinités (1.3) : le calcul seul, puis dans la fiche et sur les téléphones après le dévoilement."""
from app.points import ECHELLE, affinites
from tests.conftest import PRENOMS

PASSAGE = {10: 1, 20: 2, 30: 3, 40: 4}


def n(**par_chanson):
    """Notes sur 20 → unités de la base."""
    return {int(c[1:]): int(v * ECHELLE) for c, v in par_chanson.items()}


def test_sous_trois_invites_rien():
    notes = {1: n(c10=12, c20=8, c30=5), 2: n(c10=10, c20=9, c30=4)}
    assert affinites(notes, {}, {}, PASSAGE) is None


def test_rubriques():
    notes = {
        1: n(c10=18, c20=10, c30=6, c40=12),     # généreux, proche de 2
        2: n(c10=17, c20=11, c30=5, c40=12),
        3: n(c10=2, c20=10, c30=19, c40=4),      # à l'opposé : la chanson 10 est la plus clivante
    }
    ordres = {1: [10, 40, 20, 30], 2: [10, 40, 20, 30], 3: [20, 30, 10, 40]}   # 3 met 20 (10/20) devant 30 (19/20)
    points = {1: {10: 12, 40: 10, 20: 8, 30: 7}, 2: {10: 12, 40: 10, 20: 8, 30: 7}, 3: {20: 12, 30: 10, 10: 8, 40: 7}}
    a = affinites(notes, ordres, points, PASSAGE)
    assert a["clivante"]["chanson"] == 10 and a["clivante"]["ecart"] == 16
    assert a["clivante"]["haute"] == {"invite": 1, "note": 18} and a["clivante"]["basse"] == {"invite": 3, "note": 2}
    assert a["consensuelle"]["chanson"] == 20 and a["consensuelle"]["ecart"] == 1
    assert a["proches"]["invites"] == [1, 2] and a["proches"]["ecart_moyen"] == 0.75 and a["proches"]["communes"] == 4
    assert set(a["eloignes"]["invites"]) == {1, 3} or set(a["eloignes"]["invites"]) == {2, 3}
    assert a["genereux"]["invite"] in (1, 2) and a["severe"]["invite"] in (1, 2, 3)
    assert a["contre_note"] == [{"invite": 3, "devant": 20, "derriere": 30, "note_devant": 10, "note_derriere": 19, "ecart": 9}]
    assert a["coups_de_coeur"] == []          # chaque chanson qui a reçu un 12 a aussi reçu d'autres points


def test_coup_de_coeur_solitaire():
    notes = {1: n(c10=20, c20=5, c30=5), 2: n(c10=1, c20=15, c30=14), 3: n(c10=0, c20=16, c30=13)}
    points = {1: {10: 12}, 2: {20: 12, 30: 10}, 3: {20: 12, 30: 10}}
    a = affinites(notes, {g: list(points[g]) for g in points}, points, PASSAGE)
    assert a["coups_de_coeur"] == [{"invite": 1, "chanson": 10, "note": 20}]


def test_tout_pareil_rien_a_dire():
    notes = {g: n(c10=10, c20=10, c30=10) for g in (1, 2, 3)}
    a = affinites(notes, {g: [10, 20, 30] for g in notes}, {}, PASSAGE)
    assert a["clivante"] is None and a["consensuelle"] is None
    assert a["proches"] is None and a["eloignes"] is None and a["severe"] is None and a["contre_note"] == []


def test_dans_la_fiche_et_sur_les_telephones(client, soiree):
    soiree.tout_le_monde()
    assert client.post(f"/api/soirees/{soiree.id}/devoiler").status_code == 200
    f = client.get(f"/api/soirees/{soiree.id}/fiche").json()
    a = f["affinites"]
    assert a is not None and a["clivante"]["chanson"] in soiree.chansons
    ids = {i["id"] for i in f["invites"]}
    assert set(a["proches"]["invites"]) <= ids and a["severe"]["invite"] in ids
    # sur les téléphones : rien avant la fin du dévoilement, puis les mêmes affinités
    assert client.get(soiree.url("resultats")).status_code == 409
    assert client.post(f"/api/soirees/{soiree.id}/terminer").status_code == 200
    r = client.get(soiree.url("resultats")).json()
    assert r["affinites"] == a


def test_fiche_a_deux_invites_sans_affinites(client, soiree):
    for prenom in PRENOMS[:2]:
        soiree.noter(prenom, {1: 12, 2: 8, 3: 5})
        soiree.envoyer(prenom)
    assert client.post(f"/api/soirees/{soiree.id}/devoiler", json={"forcer": True}).status_code == 200
    assert client.get(f"/api/soirees/{soiree.id}/fiche").json()["affinites"] is None
