"""1.11.0 : sons sur la télé (réglages, fichiers de l'hôte) et compte à rebours avant la révélation (+6 s).
Le temps est simulé (`main.horloge`)."""
import pytest

from app import main
from tests.conftest import connecter
from tests.test_auto_18 import Horloge, action, jury_puis_public, lu  # noqa: F401

MP3 = b"ID3\x04\x00\x00\x00\x00\x00\x00" + b"\x00" * 64
M4A = b"\x00\x00\x00\x18ftypM4A \x00\x00\x00\x00" + b"\x00" * 64
OGG = b"OggS\x00\x02" + b"\x00" * 64
WAV = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 64


@pytest.fixture()
def temps(monkeypatch):
    h = Horloge(1000.0)
    monkeypatch.setattr(main, "horloge", h)
    return h


def test_reglages_des_sons(client):
    connecter(client)
    r = client.get("/api/reglages").json()
    assert r["sons"] is True and r["volume_sons"] == 70                  # oui par défaut, volume 70
    r = client.put("/api/reglages", json={"sons": False, "volume_sons": 35})
    assert r.status_code == 200 and r.json()["sons"] is False and r.json()["volume_sons"] == 35
    for faux in ({"sons": "oui"}, {"sons": 1}, {"volume_sons": 101}, {"volume_sons": -1}, {"volume_sons": 50.5},
                 {"volume_sons": True}, {"volume_sons": "70"}):
        assert client.put("/api/reglages", json=faux).status_code == 400, faux
    assert client.get("/api/reglages").json()["volume_sons"] == 35       # rien n'a changé


def test_reglages_des_sons_dans_la_sauvegarde(client, monkeypatch):
    connecter(client)
    client.put("/api/reglages", json={"sons": False, "volume_sons": 40})
    monkeypatch.setenv("MAISON_JETON", "jeton-commun-de-test")
    r = client.get("/externe/sauvegarde", headers={"Authorization": "Bearer jeton-commun-de-test"})
    assert r.status_code == 200, r.text
    reglages = r.json()["reglages"]
    assert reglages["sons"] is False and reglages["volume_sons"] == 40


def test_routes_des_sons(client, tmp_path):
    connecter(client)
    liste = client.get("/api/sons").json()
    assert [x["nom"] for x in liste] == list(main.SONS) and len(liste) == 9 and not any(x["fichier"] for x in liste)
    for nom, contenu in (("fanfare", MP3), ("carillon", M4A), ("tambour", OGG), ("douze", WAV)):
        r = client.put(f"/api/sons/{nom}", content=contenu, headers={"Content-Type": "application/octet-stream"})
        assert r.status_code == 200, (nom, r.text)
    presents = {x["nom"] for x in client.get("/api/sons").json() if x["fichier"]}
    assert presents == {"fanfare", "carillon", "tambour", "douze"}
    r = client.get("/api/sons/fanfare")
    assert r.status_code == 200 and r.content == MP3 and r.headers["content-type"].startswith("audio/mpeg")
    assert (tmp_path / "sons" / "fanfare.mp3").is_file()
    # un autre format remplace l'ancien fichier (un seul par son)
    assert client.put("/api/sons/fanfare", content=WAV).status_code == 200
    assert sorted(f.name for f in (tmp_path / "sons").glob("fanfare.*")) == ["fanfare.wav"]
    # revenir au son de l'appli
    assert client.delete("/api/sons/fanfare").json()["fichier"] is False
    assert client.get("/api/sons/fanfare").status_code == 404
    assert client.delete("/api/sons/fanfare").status_code == 200          # déjà retiré : sans effet


def test_sons_taille_type_et_nom(client):
    connecter(client)
    trop = b"ID3" + b"\x00" * (main.SON_MAX + 1)
    assert client.put("/api/sons/point", content=trop).status_code == 413
    for faux in (b"\x89PNG\r\n\x1a\n" + b"\x00" * 40, b"<svg></svg>", b"", b"RIFF\x00\x00\x00\x00AVI "):
        assert client.put("/api/sons/point", content=faux).status_code == 415, faux[:8]
    for methode in ("get", "delete"):
        assert getattr(client, methode)("/api/sons/inconnu").status_code == 404
    assert client.put("/api/sons/inconnu", content=MP3).status_code == 404
    assert client.put("/api/sons/..%2Freglages", content=MP3).status_code in (404, 405)    # jamais hors de sons/


def test_sons_derriere_la_session(client):
    # sans connexion : rien
    assert client.get("/api/sons").status_code == 401
    assert client.put("/api/sons/fanfare", content=MP3).status_code == 401
    assert client.get("/api/sons/fanfare").status_code == 401
    assert client.delete("/api/sons/fanfare").status_code == 401


def test_revelation_compte_six_secondes(client, soiree, temps):
    assert main.COMPTE_REBOURS == 6.0
    assert abs(main.duree_revelation(12) - (6 + 1.32 + 0.9 + 60 + 5)) < 1e-9
    jury_puis_public(client, soiree)                     # 12 chansons, jury puis public : dernier pas = 13
    action(client, soiree, "aller", pas=13)
    d = lu(client, soiree)
    assert d["pas"] == 13 and d["auto"]["ecoule_ms"] == 0
    temps.t += 2.5
    assert lu(client, soiree)["auto"]["ecoule_ms"] == 2500             # la télé rechargée reprend au bon chiffre
    # le téléphone d'un invité : même temps écoulé, et la révélation compte les 6 s
    tel = soiree.tel["Aglaé"]
    i = client.get(soiree.url("devoilement"), headers=tel).json()
    assert i["compte_ms"] == 6000 and i["revelation_ms"] == 66000 and i["auto"]["ecoule_ms"] == 2500


def test_suivant_ignore_pendant_le_compte(client, soiree, temps):
    client.put("/api/reglages", json={"devoilement_auto": False})
    jury_puis_public(client, soiree)
    action(client, soiree, "aller", pas=13)
    temps.t += 3
    r = action(client, soiree, "suivant")
    assert r["pas"] == 13 and r["ignore"] == "compte_a_rebours"      # au toucher, pendant le compte : rien
    assert action(client, soiree, "suivant", depuis=13)["pas"] == 14   # la télé qui a fini : toujours écoutée
    action(client, soiree, "aller", pas=13)
    temps.t += 6
    assert action(client, soiree, "suivant")["pas"] == 14             # après le compte : le podium
    client.put("/api/reglages", json={"devoilement_auto": True})
