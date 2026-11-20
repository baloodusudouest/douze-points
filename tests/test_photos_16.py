"""1.6 : jumeaux de vote et photos de la soirée vers Immich (faux Immich, aucun réseau)."""
import dataclasses
import json

import httpx
import pytest

from app import immich, main
from app.points import duos, jumeaux, tranche

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 200
HEIC = b"\x00\x00\x00\x18ftypheic" + b"\x00" * 200


# ---------------------------------------------------------------- calcul pur

def test_jumeaux_et_duos():
    # notes en quarts de point : A et B presque pareils, C proche de B, D loin de tous
    notes = {1: {1: 40, 2: 60, 3: 20}, 2: {1: 42, 2: 58, 3: 22}, 3: {1: 50, 2: 50, 3: 30}, 4: {1: 0, 2: 80, 3: 80}}
    js = jumeaux(notes)
    assert js[1]["jumeau"] == 2 and js[2]["jumeau"] == 1 and js[3]["jumeau"] == 2
    assert js[1]["tranche"] == "Jumeaux parfaits"
    d = duos(js)
    assert d[0]["invites"] == [1, 2] and d[0]["reciproques"]          # les réciproques d'abord
    assert [1, 2] not in [x["invites"] for x in d[1:]]                  # chaque paire une fois
    assert [x["invites"] for x in d] == [[1, 2], [3, 2], [4, 1]]        # puis du plus proche au plus lointain
    assert not d[1]["reciproques"] and d[2]["tranche"] == "Âmes sœurs… de loin"


def test_sans_assez_de_chansons_communes_pas_de_jumeau():
    js = jumeaux({1: {1: 40, 2: 40, 3: 40}, 2: {4: 40, 5: 40, 6: 40}})
    assert js == {}


def test_tranches_sans_pourcentage():
    assert tranche(0.5) == "Jumeaux parfaits" and tranche(1.5) == "Très proches"
    assert tranche(3) == "Proches" and tranche(9) == "Âmes sœurs… de loin"


# ---------------------------------------------------------------- faux Immich

class FauxImmich:
    def __init__(self):
        self.assets, self.albums, self.tags, self.descriptions = {}, {}, {}, {}
        self.appels, self.panne, self.sans_album = [], False, False

    def __call__(self, req: httpx.Request) -> httpx.Response:
        if self.panne:
            raise httpx.ConnectError("Immich arrêté (essai)")
        assert req.headers["x-api-key"] == "cle-de-test"
        chemin, m = req.url.path, req.method
        self.appels.append((m, chemin))
        corps = json.loads(req.content) if req.headers.get("content-type", "").startswith("application/json") else None
        if m == "POST" and chemin == "/api/assets":
            contenu = req.content
            for aid, c in self.assets.items():
                if c == contenu:
                    return httpx.Response(200, json={"id": aid, "status": "duplicate"})
            aid = f"asset-{len(self.assets) + 1}"
            self.assets[aid] = contenu
            return httpx.Response(201, json={"id": aid, "status": "created"})
        if m == "POST" and chemin == "/api/albums":
            alb = f"album-{len(self.albums) + 1}"
            self.albums[alb] = {"nom": corps["albumName"], "ids": list(corps["assetIds"])}
            return httpx.Response(201, json={"id": alb})
        if m == "PUT" and chemin.startswith("/api/albums/"):
            alb = chemin.split("/")[3]
            if alb not in self.albums or self.sans_album:
                return httpx.Response(404, json={"message": "Not found"})
            self.albums[alb]["ids"] += corps["ids"]
            return httpx.Response(200, json=[{"id": i, "success": True} for i in corps["ids"]])
        if m == "PUT" and chemin.startswith("/api/assets/"):
            self.descriptions[chemin.split("/")[3]] = corps["description"]
            return httpx.Response(200, json={})
        if m == "PUT" and chemin == "/api/tags":
            nom = corps["tags"][0]
            self.tags.setdefault(nom, {"id": f"tag-{len(self.tags) + 1}", "ids": []})
            return httpx.Response(200, json=[{"id": self.tags[nom]["id"], "value": nom, "name": nom}])
        if m == "PUT" and chemin.startswith("/api/tags/"):
            tid = chemin.split("/")[3]
            nom = next(n for n, t in self.tags.items() if t["id"] == tid)
            self.tags[nom]["ids"] += corps["ids"]
            return httpx.Response(200, json=[{"id": i, "success": True} for i in corps["ids"]])
        if m == "GET" and chemin == "/api/server/version":
            return httpx.Response(200, json={"major": 2, "minor": 3, "patch": 1})
        if m == "GET" and chemin == "/api/api-keys/me":
            return httpx.Response(200, json={"permissions": list(immich.PERMISSIONS)})
        return httpx.Response(404, json={"message": "?"})


@pytest.fixture()
def faux(client, monkeypatch):
    f = FauxImmich()
    monkeypatch.setattr(immich, "CLIENT", httpx.Client(transport=httpx.MockTransport(f)))
    main.ETAT["cfg"] = dataclasses.replace(main.ETAT["cfg"], immich_url="http://immich.exemple", immich_cle="cle-de-test")
    monkeypatch.setattr(main, "_envoyer_photos_sans_erreur", lambda: None)     # les tests envoient à la main
    return f


def envoyer(client, soiree, prenom, contenu=JPEG, duo=None):
    entetes = {**soiree.tel[prenom], "Content-Type": "application/octet-stream"}
    if duo is not None:
        entetes["X-Duo"] = str(duo)
    return client.put(soiree.url("photo"), headers=entetes, content=contenu)


def devoilee(client, soiree):
    soiree.tout_le_monde()
    assert client.post(f"/api/soirees/{soiree.id}/devoiler").status_code == 200
    assert client.post(f"/api/soirees/{soiree.id}/terminer").status_code == 200


# ---------------------------------------------------------------- photos

def test_photo_pendant_la_soiree_puis_envoi_vers_immich(client, soiree, faux):
    soiree.entrer("Aglaé")
    assert soiree.etat("Aglaé")["photos"] == {"actives": True, "soiree": 0, "miennes": 0, "plafond": 150}
    r = envoyer(client, soiree, "Aglaé")
    assert r.status_code == 200 and r.json()["photos"]["miennes"] == 1
    assert envoyer(client, soiree, "Aglaé", HEIC).status_code == 200
    r = main.envoyer_photos()
    assert r == {"envoyees": 2, "en_attente": 0, "erreur": ""}
    (album,) = faux.albums.values()
    assert album["nom"].endswith("Finale de démonstration") and len(album["ids"]) == 2
    assert faux.tags["Douze points"]["ids"] == album["ids"] and "Jumeaux de vote" not in faux.tags
    assert all(d.startswith("Douze points – Finale de démonstration – photo de Aglaé") for d in faux.descriptions.values())
    assert not list((main.cfg().data / "photos" / str(soiree.id)).iterdir())     # copies du NAS effacées


def test_immich_absent_garde_et_reprend_a_l_etape(client, soiree, faux):
    soiree.entrer("Barnabé")
    envoyer(client, soiree, "Barnabé")
    faux.panne = True
    r = main.envoyer_photos()
    assert r["envoyees"] == 0 and r["en_attente"] == 1 and "injoignable" in r["erreur"]
    faux.panne = False
    assert main.envoyer_photos()["envoyees"] == 1
    # une coupure après l'envoi de l'image : le nouvel essai ne la renvoie pas
    envoyer(client, soiree, "Barnabé", JPEG + b"2")
    with main.base(main.cfg().data) as cx:
        pid = cx.execute("SELECT id FROM photo WHERE envoyee_le IS NULL").fetchone()["id"]
    aid, _ = immich.envoyer_image(main.cfg(), main.cfg().data / "photos" / str(soiree.id) /
                                  cx_fichier(pid), "image/jpeg", "x", "2027-05-15T21:00:00+02:00")
    with main.base(main.cfg().data) as cx:
        cx.execute("UPDATE photo SET immich_id=? WHERE id=?", (aid, pid))
    n = len(faux.assets)
    assert main.envoyer_photos()["envoyees"] == 1 and len(faux.assets) == n
    assert len(faux.albums) == 1


def cx_fichier(pid):
    with main.base(main.cfg().data) as cx:
        return cx.execute("SELECT fichier FROM photo WHERE id=?", (pid,)).fetchone()["fichier"]


def test_album_supprime_dans_immich_est_recree(client, soiree, faux):
    soiree.entrer("Aglaé")
    envoyer(client, soiree, "Aglaé")
    main.envoyer_photos()
    faux.sans_album = True
    envoyer(client, soiree, "Aglaé", JPEG + b"b")
    main.envoyer_photos()
    assert len(faux.albums) == 2


def test_refus(client, soiree, faux):
    soiree.entrer("Aglaé")
    assert envoyer(client, soiree, "Aglaé", b"<svg></svg>" * 3).status_code == 415
    assert client.put(soiree.url("photo"), content=JPEG).status_code == 403              # sans prénom
    assert envoyer(client, soiree, "Aglaé", duo=soiree.part["Barnabé"]).status_code == 422   # duo avant dévoilement
    gros = JPEG + b"\x00" * main.PHOTO_MAX
    assert envoyer(client, soiree, "Aglaé", gros).status_code == 413
    assert not [f for f in (main.cfg().data / "photos" / str(soiree.id)).iterdir()]    # rien de gardé


def test_brouillon_et_archivee(client, faux):
    from tests.conftest import Soiree
    s = Soiree(client, ouvrir=False)
    s.c.post(s.url("prenom"), json={"participation_id": s.part["Aglaé"]})     # refusé (pas ouverte) : pas de téléphone
    assert client.put(s.url("photo"), content=JPEG).status_code == 409
    client.post(f"/api/soirees/{s.id}/ouvrir")
    devoilee(client, s)
    assert envoyer(client, s, "Aglaé").status_code == 200                         # encore après le dévoilement
    client.post(f"/api/soirees/{s.id}/archiver")
    assert envoyer(client, s, "Aglaé").status_code == 404                         # archivée : lien fermé


def test_sans_cle_pas_d_icone(client, soiree):
    soiree.entrer("Aglaé")
    assert soiree.etat("Aglaé")["photos"]["actives"] is False
    assert envoyer(client, soiree, "Aglaé").status_code == 409


# ---------------------------------------------------------------- jumeaux

def test_jumeaux_sur_les_telephones_et_la_tele(client, soiree, faux):
    devoilee(client, soiree)
    tele = client.get(f"/api/soirees/{soiree.id}/jumeaux").json()
    assert tele["duos"] and all(d["tranche"] for d in tele["duos"])
    assert "%" not in json.dumps(tele, ensure_ascii=False) and "ecart" not in json.dumps(tele)
    duo = tele["duos"][0]
    a, b = duo["invites"][0], duo["invites"][1]
    pa = next(p for p, i in soiree.part.items() if i == a["id"])
    res = client.get(soiree.url("resultats"), headers=soiree.tel[pa]).json()["jumeaux"]
    assert res["a_jumeau"] and any(d["cle"] == duo["cle"] for d in res["miens"])
    # immortaliser : la photo du duo
    assert envoyer(client, soiree, pa, duo=b["id"]).status_code == 200
    assert client.get(f"/api/soirees/{soiree.id}/jumeaux").json()["duos"][0]["photos"] == 1
    main.envoyer_photos()
    assert faux.tags["Jumeaux de vote"]["ids"]
    assert any("jumeaux de vote : " in d for d in faux.descriptions.values())
    # un duo qui n'est pas le sien est refusé
    autres = [i for i in soiree.part.values() if i not in (a["id"], b["id"])]
    pas_le_mien = [x for x in autres if not any({a["id"], x} == {y["id"] for y in d["invites"]} for d in tele["duos"])]
    if pas_le_mien:
        assert envoyer(client, soiree, pa, duo=pas_le_mien[0]).status_code == 422
    assert envoyer(client, soiree, pa, duo=a["id"]).status_code == 422             # soi-même


def test_jumeaux_fermes_avant_le_devoilement(client, soiree, faux):
    soiree.tout_le_monde()
    assert client.get(f"/api/soirees/{soiree.id}/jumeaux").status_code == 409
    assert client.get(soiree.url("resultats"), headers=soiree.tel["Aglaé"]).status_code == 409


def test_le_jumeau_part_a_carnet(client, soiree, faux, monkeypatch):
    envois = []
    monkeypatch.setattr(main, "ENVOYER_CARNET", lambda *a: envois.append(a[4]) or (200, {}))
    main.ETAT["cfg"] = dataclasses.replace(main.cfg(), carnet_url="http://carnet.exemple", carnet_jeton="j")
    monkeypatch.setattr(main.carnet, "personnes", lambda *a, **k: [])
    soiree.tout_le_monde()
    envoyer(client, soiree, "Aglaé")
    main.envoyer_photos()
    client.post(f"/api/soirees/{soiree.id}/devoiler")
    client.post(f"/api/soirees/{soiree.id}/terminer")
    assert not envois                                                   # 1.9 : à la clôture seulement
    client.post(f"/api/soirees/{soiree.id}/cloturer")
    (corps,) = envois
    avec = [p for p in corps["personnes"] if "jumeau" in p["donnees"]]
    assert avec and all(p["donnees"]["jumeau"]["accord"] and "%" not in p["donnees"]["jumeau"]["accord"] for p in avec)
    assert all(p["donnees"]["album"]["nom"].endswith("Finale de démonstration") for p in corps["personnes"])


def test_connexion_immich(client, faux):
    from tests.conftest import connecter
    connecter(client)
    tuiles = {t["id"]: t for t in client.get("/api/services?verifier=true").json()}
    assert tuiles["immich"]["ok"] is True and "2.3.1" in tuiles["immich"]["detail"]


def test_suppression_efface_les_photos_en_attente(client, soiree, faux):
    soiree.entrer("Aglaé")
    envoyer(client, soiree, "Aglaé")
    client.request("DELETE", f"/api/soirees/{soiree.id}", json={"confirmation": True})
    assert not (main.cfg().data / "photos" / str(soiree.id)).exists()
