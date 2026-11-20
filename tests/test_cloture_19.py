"""1.9.0 : fin du dévoilement sans carnet, « À traiter », clôture (résultat officiel complet), journal pour Gazette
sur /externe/ (jeton commun), photo apéro. Contrat : docs/journal-exemple.json."""
import io
import json
from pathlib import Path

import pytest
from PIL import Image

from app import main
from tests.conftest import Soiree
from tests.test_photos_16 import faux  # noqa: F401 — fixture

JETON = {"Authorization": "Bearer jeton-commun"}
EXEMPLE = Path(__file__).resolve().parent.parent / "docs" / "journal-exemple.json"


@pytest.fixture()
def commun(monkeypatch):
    monkeypatch.setenv("MAISON_JETON", "jeton-commun")


def photo(couleur=(229, 85, 159)):
    sortie = io.BytesIO()
    Image.new("RGB", (1200, 900), couleur).save(sortie, "JPEG")
    return sortie.getvalue()


def devoilee(client, soiree, jury="Aglaé"):
    if jury:
        for i in client.get("/api/invites").json():
            if i["prenom"] == jury:
                client.put(f"/api/invites/{i['id']}", json={"jury": True})
    soiree.tout_le_monde()
    assert client.post(f"/api/soirees/{soiree.id}/devoiler").status_code == 200
    assert client.post(f"/api/soirees/{soiree.id}/terminer").json() == {"ok": True}
    assert client.post(f"/api/soirees/{soiree.id}/terminer").json() == {"ok": True}          # idempotent


def vrais_votes(client, soiree, rang=None):
    corps = [{"chanson_id": c, "jury": 100 - 7 * k, "public": 60 + (k % 3) * 9} for k, c in enumerate(soiree.chansons)]
    if rang:
        for c, r in rang.items():
            corps[c]["rang"] = r
    assert client.put(f"/api/soirees/{soiree.id}/officiel", json={"resultats": corps}).status_code == 200


def test_a_traiter_cloture_et_journal(client, soiree, commun):
    devoilee(client, soiree)
    a = client.get("/api/a-traiter").json()
    assert a["nombre"] == 1 and a["soirees"][0]["a_cloturer"] and a["soirees"][0]["manques"]
    vrais_votes(client, soiree)
    assert client.get("/api/a-traiter").json()["soirees"][0]["manques"] == []
    r = client.post(f"/api/soirees/{soiree.id}/cloturer").json()
    assert r["version"] == 1 and r["carnet"] == "carnet pas réglé : rien n'est envoyé"
    assert client.get("/api/a-traiter").json()["nombre"] == 0
    client.cookies.clear()                                                 # Gazette n'a pas de session
    liste = client.get("/externe/soirees", headers=JETON).json()
    assert liste == [{"id": soiree.id, "nom": "Finale de démonstration", "emission": "finale", "annee": 2027,
                      "version": 1, "le": liste[0]["le"]}]
    j = client.get(f"/externe/soirees/{soiree.id}/journal", headers=JETON).json()
    assert j["format"] == 1 and j["version"] == 1 and j["soiree"]["numero"] == "2027 · Eurovision · Finale"
    assert j["soiree"]["livret"] == "finale" and j["soiree"]["avec_jury_maison"] and j["soiree"]["avec_jury_officiel"]
    assert len(j["podium_maison"]) == 3 and len(j["podium_officiel"]) == 3
    assert len(j["mieux_devines"]) == 3 and len(j["plus_rates"]) == 3 and not set(j["mieux_devines"]) & set(j["plus_rates"])
    assert j["plus_proche"] == j["palmares"][0]["invite"] and all(x["complet"] for x in j["palmares"])
    assert j["commentaires"] and all(c["texte"].startswith("Avis de") for c in j["commentaires"])
    c = j["chansons"][0]
    assert c["officiel"]["jury"] == 100 and c["officiel"]["rang"] is not None and c["ecart"]["rang"] is not None
    assert c["notes"] and {"invite", "note", "rang", "points", "commentaire"} <= set(c["notes"][0])
    assert j["demi"] is None
    # le contrat : mêmes clés que docs/journal-exemple.json (Gazette lit ce fichier)
    exemple = json.loads(EXEMPLE.read_text(encoding="utf-8"))
    assert set(j) == set(exemple) and set(j["soiree"]) == set(exemple["soiree"])
    assert set(j["chansons"][0]) == set(exemple["chansons"][0]) and set(j["invites"][0]) == set(exemple["invites"][0])


def test_reclore_fait_une_nouvelle_version(client, soiree, commun):
    devoilee(client, soiree)
    vrais_votes(client, soiree)
    client.post(f"/api/soirees/{soiree.id}/cloturer")
    vrais_votes(client, soiree, rang={0: 2, 1: 1})                          # le concours a départagé
    assert client.post(f"/api/soirees/{soiree.id}/cloturer").json()["version"] == 2
    v1 = client.get(f"/externe/soirees/{soiree.id}/journal/1", headers=JETON).json()
    v2 = client.get(f"/externe/soirees/{soiree.id}/journal", headers=JETON).json()
    assert v2["version"] == 2 and v2["chansons"][0]["officiel"]["rang_saisi"] == 2
    assert v1["chansons"][0]["officiel"]["rang_saisi"] is None             # une version parue ne change pas
    assert client.get("/externe/soirees", headers=JETON).json()[0]["version"] == 2


def test_cloturer_seulement_apres_le_devoilement(client, soiree):
    assert client.post(f"/api/soirees/{soiree.id}/cloturer").status_code == 409
    assert client.post(f"/api/soirees/{soiree.id}/cloturer", json={"date_finale": "samedi"}).status_code in (409, 422)


def test_toutes_les_routes_externes_fermees_sans_jeton(client, soiree, commun):
    devoilee(client, soiree)
    vrais_votes(client, soiree)
    client.post(f"/api/soirees/{soiree.id}/cloturer")
    client.cookies.clear()
    routes = [r.path for r in main.app.routes if getattr(r, "path", "").startswith("/externe/")]
    assert len(routes) >= 5
    for chemin in routes:
        url = (chemin.replace("{soiree_id}", str(soiree.id)).replace("{version}", "1").replace("{sorte}", "logo"))
        assert client.get(url).status_code == 404, chemin
        assert client.get(url, headers={"Authorization": "Bearer mauvais"}).status_code == 404, chemin


def test_jeton_commun_vide_porte_fermee(client, soiree, monkeypatch):
    monkeypatch.setenv("MAISON_JETON", "")
    devoilee(client, soiree)
    client.post(f"/api/soirees/{soiree.id}/cloturer")
    assert client.get("/externe/soirees", headers={"Authorization": "Bearer "}).status_code == 404


def test_demi_finale_livret_qualifies(client, commun):
    s = Soiree(client, n=12, ouvrir=False)
    with main.base(main.cfg().data) as cx:                         # une première demi-finale
        cx.execute("UPDATE soiree SET emission='demi1' WHERE id=?", (s.id,))
    assert client.post(f"/api/soirees/{s.id}/ouvrir").status_code == 200
    devoilee(client, s, jury=None)
    qualifies = s.chansons[:10:1][:7] + s.chansons[9:12]
    corps = [{"chanson_id": c, "qualifie": c in qualifies} for c in s.chansons]
    client.put(f"/api/soirees/{s.id}/officiel", json={"resultats": corps})
    r = client.post(f"/api/soirees/{s.id}/cloturer", json={"date_finale": "2027-05-15"})
    assert r.status_code == 200, r.text
    j = client.get(f"/externe/soirees/{s.id}/journal", headers=JETON).json()
    d = j["demi"]
    assert j["soiree"]["livret"] == "qualifies" and d["date_finale"] == "2027-05-15"
    assert len(d["notre_top"]) == 10 and len(d["qualifies"]) == 10 and d["flair"][0]["sur"] == 10
    assert j["palmares"] == [] and j["plus_proche"] is None


def test_fin_du_devoilement_n_envoie_rien_a_carnet(client, soiree, monkeypatch):
    envois = []
    monkeypatch.setattr(main, "ENVOYER_CARNET", lambda *a: envois.append(a) or (200, {}))
    import dataclasses
    main.ETAT["cfg"] = dataclasses.replace(main.cfg(), carnet_url="http://carnet.exemple", carnet_jeton="j")
    devoilee(client, soiree)
    assert client.post("/api/carnet/envoyer").json()["soirees"] == 0           # pas clôturée : rien ne part
    assert main.renvoyer_a_carnet() == 0 and not envois
    client.post(f"/api/soirees/{soiree.id}/cloturer")
    assert len(envois) == 1
    client.post(f"/api/soirees/{soiree.id}/cloturer")                          # reclôture : même adresse, remplacée
    assert len(envois) == 2 and envois[0][3] == envois[1][3]


def test_photo_apero(client, soiree, faux, commun):  # noqa: F811
    r = client.put(f"/api/soirees/{soiree.id}/apero", content=photo(), headers={"Content-Type": "application/octet-stream"})
    assert r.status_code == 200, r.text
    nom = r.json()["images"]["apero"]
    assert client.get(f"/api/soirees/{soiree.id}").json()["images"]["apero"] == nom
    assert client.get(f"/api/soirees/{soiree.id}/image/apero").headers["content-type"] == "image/jpeg"
    soiree.entrer("Aglaé")
    assert soiree.etat("Aglaé")["photos"]["soiree"] == 0                         # l'apéro n'est pas une photo d'invité
    main.envoyer_photos()
    assert faux.tags["Apéro"]["ids"] and any(d.endswith("photo apéro") for d in faux.descriptions.values())
    assert client.put(f"/api/soirees/{soiree.id}/image/apero", content=photo()).status_code == 404   # passe par /apero
    assert client.put(f"/api/soirees/{soiree.id}/apero", content=b"pas une photo").status_code == 415
    # figée à la clôture : la remplacer ensuite ne change pas le journal paru
    devoilee(client, soiree)
    client.post(f"/api/soirees/{soiree.id}/cloturer")
    a = client.get(f"/externe/soirees/{soiree.id}/journal/1/image/apero", headers=JETON)
    assert a.status_code == 200
    client.put(f"/api/soirees/{soiree.id}/apero", content=photo((10, 200, 30)), headers={"Content-Type": "application/octet-stream"})
    assert client.get(f"/externe/soirees/{soiree.id}/journal/1/image/apero", headers=JETON).content == a.content
