"""Le dévoilement sur les téléphones (1.0) : chaque invité part de ses points, puis le jury d'un coup, puis le public
chanson par chanson, de la moins bien servie à la mieux. Le téléphone ne voit jamais plus loin que le pas de l'hôte."""
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
    totaux = [x["total"] for x in d["public"]]
    assert totaux == sorted(totaux)                                     # de la moins servie à la mieux
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
