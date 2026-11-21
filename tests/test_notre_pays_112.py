"""1.12 : notre pays, sans points (choix de Julien du 21/11/2026). Les invités notent, commentent et classent notre pays
comme les autres ; ses points glissent à la chanson suivante ; il sort du tableau, du dernier vote du public et du
podium ; « Et notre pays ? » après le podium ; figé au dévoilement."""
import json
from pathlib import Path

from app import resultat
from app.points import place_aux_notes, points_du_classement, rerang
from tests.conftest import PRENOMS, Soiree

RACINE = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------- calculs purs

def test_les_points_glissent():
    assert points_du_classement([5, 1, 2, 3], exclues={5}) == {1: 12, 2: 10, 3: 8}
    ordre = list(range(1, 13))
    p = points_du_classement(ordre, exclues={1})
    assert 1 not in p and p[2] == 12 and p[11] == 1 and 12 not in p      # la 11e prend le dernier point
    assert points_du_classement(ordre) == points_du_classement(ordre, exclues=())


def test_place_aux_notes_et_rerang():
    moy = {1: 15.0, 2: 12.0, 3: 15.0, 4: None, 5: 9.5}
    assert place_aux_notes(moy, 2) == 3 and place_aux_notes(moy, 1) == 1 and place_aux_notes(moy, 3) == 1
    assert place_aux_notes(moy, 4) is None
    assert rerang({7: 1, 8: 2, 9: 3}, {7}) == {8: 1, 9: 2}


def test_vrais_rangs_sans_notre_pays():
    off = {1: 1.0, 2: 2.0, 3: 3.0, 4: None}
    assert resultat.sans_exclues(off, {2}) == {1: 1.0, 3: 2.0, 4: None}
    assert resultat.sans_exclues(off, set()) == off


def test_table_des_pays_recopiee():
    """app/pays_codes.json = CODES de frontend/src/lib/pays.js (tools/pays_codes.py)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("pays_codes", RACINE / "tools" / "pays_codes.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert json.loads((RACINE / "app" / "pays_codes.json").read_text(encoding="utf-8")) == mod.lire_js()


# ---------------------------------------------------------------- par l'API

def soiree_avec_france(client, n=12, france=4):
    """Pays 1…n, la chanson n° `france` s'appelle « France » (sans drapeau : reconnue par son nom)."""
    s = Soiree(client, n=n, ouvrir=False)
    texte = "\n".join(("France" if i == france else f"Pays {i}") + f"\tArtiste {i}\tTitre {i}" for i in range(1, n + 1))
    s.chansons = [x["id"] for x in client.put(f"/api/soirees/{s.id}/chansons", json={"texte": texte}).json()["chansons"]]
    assert client.post(f"/api/soirees/{s.id}/ouvrir").status_code == 200
    s.france = s.chansons[france - 1]
    return s


def noter_france_premiere(s):
    """Chacun met la France à 20 (1re de son classement), puis le reste en décroissant, et envoie."""
    for k, prenom in enumerate(PRENOMS):
        notes = {i: max(0.0, 19.0 - i - k) for i in range(1, len(s.chansons) + 1)}
        notes[s.chansons.index(s.france) + 1] = 20.0
        s.noter(prenom, notes, commentaire=f"Avis de {prenom}")
        assert s.envoyer(prenom).status_code == 200


def test_reglage_par_defaut_et_controle(client, soiree):
    assert client.get("/api/reglages").json()["notre_pays"] == "FR"
    for faux in ("FRA", "F", 12, "1A"):
        assert client.put("/api/reglages", json={"notre_pays": faux}).status_code == 400
    assert client.put("/api/reglages", json={"notre_pays": "be"}).json()["notre_pays"] == "BE"
    assert client.put("/api/reglages", json={"notre_pays": ""}).json()["notre_pays"] == ""


def test_le_telephone_voit_la_marque(client):
    s = soiree_avec_france(client)
    s.entrer("Aglaé")
    marques = {c["id"]: c["hors_points"] for c in s.etat("Aglaé")["chansons"]}
    assert marques[s.france] is True and sum(marques.values()) == 1


def test_noter_classer_commenter_mais_aucun_point(client):
    s = soiree_avec_france(client)
    noter_france_premiere(s)
    # le classement de l'invité garde la France en tête
    assert s.etat("Aglaé")["moi"]["classement"][0] == s.france
    assert client.post(f"/api/soirees/{s.id}/devoiler").status_code == 200
    f = client.get(f"/api/soirees/{s.id}/fiche").json()
    fr = next(c for c in f["chansons"] if c["id"] == s.france)
    assert fr["hors_points"] and fr["points"] == 0 and fr["rang"] is None and fr["moyenne"] == 20.0
    for v in fr["invites"].values():
        assert v["points"] == 0 and v["rang"] == 1 and v["commentaire"].startswith("Avis de")
    # le 12 de chacun est allé à la chanson suivante de son classement
    for i in f["invites"]:
        donnes = sorted((c["invites"][str(i["id"])]["points"] for c in f["chansons"] if str(i["id"]) in c["invites"]),
                        reverse=True)
        assert donnes[:10] == [12, 10, 8, 7, 6, 5, 4, 3, 2, 1]
    assert sorted(c["rang"] for c in f["chansons"] if c["rang"] is not None)[0] == 1
    assert len([c for c in f["chansons"] if c["rang"] is not None]) == 11
    assert f["notre_pays"][0]["chanson"] == s.france and f["notre_pays"][0]["place_notes"] == 1


def test_hors_du_devoilement_puis_et_notre_pays(client):
    s = soiree_avec_france(client)
    noter_france_premiere(s)
    client.post(f"/api/soirees/{s.id}/devoiler", json={"mode": "court"})
    d = client.get(f"/api/soirees/{s.id}/devoilement").json()
    assert s.france not in d["marche"]["public"] and len(d["marche"]["public"]) == 11
    assert s.france not in [l["chanson"] for l in d["classement"]]
    assert d["notre_pays"] == [{"chanson": s.france, "moyenne": 20.0, "place_notes": 1, "sur": 12, "notes": 4}]
    tel = client.get(s.url("devoilement"), headers=s.tel["Aglaé"]).json()
    assert "notre_pays" not in tel                                         # pas avant le podium
    assert next(c for c in tel["chansons"] if c["id"] == s.france)["hors_points"] is True
    assert str(s.france) not in tel["moi"]["points"]
    client.post(f"/api/soirees/{s.id}/pas", json={"pas": d["marche"]["fin"]})
    tel = client.get(s.url("devoilement"), headers=s.tel["Aglaé"]).json()
    assert tel["notre_pays"][0]["chanson"] == s.france


def test_sans_reglage_la_france_recoit_ses_points(client):
    s = soiree_avec_france(client)
    client.put("/api/reglages", json={"notre_pays": ""})
    noter_france_premiere(s)
    client.post(f"/api/soirees/{s.id}/devoiler")
    f = client.get(f"/api/soirees/{s.id}/fiche").json()
    fr = next(c for c in f["chansons"] if c["id"] == s.france)
    assert not fr["hors_points"] and fr["points"] == 48 and fr["rang"] == 1 and f["notre_pays"] == []


def test_fige_au_devoilement(client):
    s = soiree_avec_france(client)
    noter_france_premiere(s)
    client.post(f"/api/soirees/{s.id}/devoiler")
    client.put("/api/reglages", json={"notre_pays": ""})              # changer d'avis après coup ne change rien
    f = client.get(f"/api/soirees/{s.id}/fiche").json()
    assert next(c for c in f["chansons"] if c["id"] == s.france)["hors_points"]


def test_comparaison_aux_vrais_votes_sans_notre_pays(client):
    s = soiree_avec_france(client)
    noter_france_premiere(s)
    client.post(f"/api/soirees/{s.id}/devoiler")
    client.post(f"/api/soirees/{s.id}/terminer")
    # vrais votes : la France 1re ; puis le même ordre que la maison
    corps = [{"chanson_id": c, "jury": 500 if c == s.france else 300 - 10 * k, "public": 0} for k, c in enumerate(s.chansons)]
    client.put(f"/api/soirees/{s.id}/officiel", json={"resultats": corps})
    f = client.get(f"/api/soirees/{s.id}/fiche").json()
    fr = next(c for c in f["chansons"] if c["id"] == s.france)
    assert fr["officiel"]["rang"] == 1 and fr["ecart"]["rang"] is None   # vrais points affichés, hors comparaison
    assert f["comparaison"]["ensemble"]["chansons"] == 11
    assert all(x["complet"] for x in f["palmares"])
