"""Le dévoilement sur les téléphones (1.0) : chaque invité part de ses points, puis le jury d'un coup, puis le public
chanson par chanson, de la plus mal placée par le jury à la mieux placée. Le téléphone ne voit jamais plus loin que le pas de l'hôte."""
from tests.conftest import PRENOMS

MARQUES = [f"Avis de {p}" for p in PRENOMS]


def lire(client, soiree, prenom=None):
    r = client.get(soiree.url("devoilement"), headers=soiree.tel.get(prenom, {}) if prenom else {})
    assert r.status_code == 200, r.text
    return r.json()


def mettre_jury(client, soiree, prenoms):
    for i in client.get("/api/invites").json():
        if i["prenom"] in prenoms:
            assert client.put(f"/api/invites/{i['id']}", json={"jury": True}).status_code == 200


def test_ferme_avant_le_devoilement(client, soiree):
    soiree.tout_le_monde()
    assert client.get(soiree.url("devoilement")).status_code == 409


def test_au_pas_pres_et_sans_double_compte(client, soiree):
    mettre_jury(client, soiree, ["Aglaé"])
    soiree.tout_le_monde()
    assert client.post(f"/api/soirees/{soiree.id}/devoiler").status_code == 200
    assert client.get(f"/api/soirees/{soiree.id}").json()["mode_devoilement"] == "jury"     # « auto » a choisi

    d = lire(client, soiree, "Barnabé")
    assert d["pas"] == 0 and d["avec_jury"] and d["fin"] == 1 + 12 + 1
    assert d["jury"] is None and d["public"] == [] and "classement" not in d
    assert sorted(d["moi"]["points"].values(), reverse=True) == [12, 10, 8, 7, 6, 5, 4, 3, 2, 1]
    assert not any(m in str(d) for m in MARQUES) and "note" not in str(d)

    client.post(f"/api/soirees/{soiree.id}/pas", json={"pas": 1})       # le jury d'un coup
    d = lire(client, soiree, "Barnabé")
    assert sum(d["jury"].values()) == 58 and d["public"] == []
    assert sum(lire(client, soiree, "Aglaé")["jury"].values()) == 0       # Aglaé est le jury : ses points sont déjà les siens

    client.post(f"/api/soirees/{soiree.id}/pas", json={"pas": 4})       # trois chansons du public
    d = lire(client, soiree, "Barnabé")
    assert len(d["public"]) == 3
    jury = d["jury"]
    au_jury = [jury[str(x["chanson"])] for x in d["public"]]
    assert au_jury == sorted(au_jury)                                   # de la plus mal placée par le jury à la mieux
    moi = d["moi"]["points"]
    assert all(x["autres"] == x["total"] - moi.get(str(x["chanson"]), 0) for x in d["public"])

    client.post(f"/api/soirees/{soiree.id}/pas", json={"pas": 99})      # le podium
    for prenom in [None, *PRENOMS]:
        d = lire(client, soiree, prenom)
        assert d["pas"] == d["fin"] and len(d["public"]) == 12
        moi = (d["moi"] or {"points": {}})["points"]
        autres = {x["chanson"]: x["autres"] for x in d["public"]}
        for l in d["classement"]:
            c = str(l["chanson"])
            assert moi.get(c, 0) + d["jury"][c] + autres[l["chanson"]] == l["total"], prenom


def test_sans_jury_tout_le_monde_est_le_public(client, soiree):
    soiree.tout_le_monde()
    client.post(f"/api/soirees/{soiree.id}/devoiler")
    d = lire(client, soiree, "Désiré")
    assert not d["avec_jury"] and d["fin"] == 12 + 1
    client.post(f"/api/soirees/{soiree.id}/pas", json={"pas": 1})
    assert lire(client, soiree, "Désiré")["jury"] is None and len(lire(client, soiree, "Désiré")["public"]) == 1


def test_vrais_votes_visibles_par_les_invites(client, soiree):
    soiree.tout_le_monde()
    client.post(f"/api/soirees/{soiree.id}/devoiler")
    client.post(f"/api/soirees/{soiree.id}/terminer")
    client.put(f"/api/soirees/{soiree.id}/officiel",
               json={"resultats": [{"chanson_id": soiree.chansons[0], "jury": 100, "public": 50}]})
    r = client.get(soiree.url("resultats")).json()
    v = next(x for x in r["vrais"] if x["chanson"] == soiree.chansons[0])
    assert v["jury"] == 100 and v["total"] == 150 and v["rang"] == 1 and v["notre_rang"] >= 1
    assert r["comparaison"]["ensemble"]["chansons"] == 1


def test_ordre_du_public_suit_le_classement_du_jury():
    """1.6.1 : les points du public partent de la chanson la plus mal placée par le jury, pas de celle qui reçoit le
    moins de points du public (sinon l'ordre trahit le résultat du public). Égalité au jury : la dernière passée d'abord."""
    from app.main import _marche
    chansons = [{"id": c, "ordre": c} for c in (1, 2, 3, 4)]
    d = {"chansons": chansons, "invites": [
        {"id": 10, "jury": True, "points": [{"chanson": 1, "points": 12}, {"chanson": 2, "points": 1},
                                            {"chanson": 3, "points": 8}, {"chanson": 4, "points": 1}]},
        {"id": 20, "jury": False, "points": [{"chanson": 1, "points": 1}, {"chanson": 2, "points": 12},
                                             {"chanson": 3, "points": 10}, {"chanson": 4, "points": 8}]},
    ]}
    m = _marche(d)
    assert m["jures"] == [10]
    assert m["public"] == [4, 2, 3, 1]            # jury : 4 et 2 à 1 point (4 passée après), puis 3 (8), puis 1 (12)
    assert m["fin"] == 1 + 4 + 1


def test_ordre_du_public_sans_jury():
    """Sans jury, l'ordre suit les points reçus, du moins au plus."""
    from app.main import _marche
    d = {"chansons": [{"id": c, "ordre": c} for c in (1, 2, 3)], "invites": [
        {"id": 10, "jury": False, "points": [{"chanson": 1, "points": 12}, {"chanson": 2, "points": 1},
                                             {"chanson": 3, "points": 8}]}]}
    assert _marche(d)["public"] == [2, 3, 1]
