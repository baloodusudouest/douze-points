"""Variables communes de la maison (module app/maison.py du socle, copié tel quel).
1.2 : les anciens noms ne sont plus lus (DOUZE_POINTS_PASSWORD, DOUZE_POINTS_CARNET_JETON, DOUZE_POINTS_ADRESSE).
Sans réseau : l'Anneau et carnet sont remplacés par des faux. Adresses de la plage de documentation."""
import dataclasses

import pytest

from app import carnet, config as config_mod, main, maison
from tests.conftest import connecter, faux_annuaire

VARIABLES = ("MAISON_PASSWORD", "MAISON_JETON", "MAISON_JETON_ANCIEN", "MAISON_LECTURE_SEULE",
             "DOUZE_POINTS_PASSWORD", "DOUZE_POINTS_CARNET_JETON", "DOUZE_POINTS_ADRESSE", "DOUZE_POINTS_HA_WEBHOOK")


@pytest.fixture()
def env(monkeypatch, tmp_path):
    for v in VARIABLES:
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("DOUZE_POINTS_DATA", str(tmp_path))
    return monkeypatch


def test_copie_du_module_non_retouchee():
    assert maison.CONTRAT == 3
    assert maison.empreinte_calculee() == maison.empreinte_ecrite()


def test_mot_de_passe_commun_seul(env):
    env.setenv("DOUZE_POINTS_PASSWORD", "ancien-mot-de-passe")        # l'ancien nom seul ne suffit plus
    with pytest.raises(SystemExit, match="MAISON_PASSWORD est absent ou trop court"):
        config_mod.charger()
    env.setenv("MAISON_PASSWORD", "mot-de-passe-commun")
    assert config_mod.charger().password == "mot-de-passe-commun"
    env.setenv("MAISON_PASSWORD", "court")                            # douze caractères au moins, comme avant
    with pytest.raises(SystemExit, match="MAISON_PASSWORD"):
        config_mod.charger()


def test_jeton_envoye_a_carnet_commun_seul(env):
    env.setenv("MAISON_PASSWORD", "mot-de-passe-commun")
    env.setenv("DOUZE_POINTS_CARNET_JETON", "jeton-de-la-paire")      # l'ancien jeton par paire n'est plus lu
    assert config_mod.charger().carnet_jeton == ""                    # carnet n'est pas lu
    env.setenv("MAISON_JETON", "jeton-commun")
    assert config_mod.charger().carnet_jeton == "jeton-commun"


def test_carnet_recoit_le_jeton_commun(client, env):
    """Le jeton commun part bien dans la demande à carnet /douze-points/personnes."""
    env.setenv("MAISON_PASSWORD", "mot-de-passe-commun")
    env.setenv("MAISON_JETON", "jeton-commun")
    env.setenv("DOUZE_POINTS_CARNET_JETON", "jeton-de-la-paire")
    appels = []
    env.setattr(carnet, "appeler", lambda url, jeton: appels.append((url, jeton)) or [])
    carnet.oublier()
    lu = config_mod.charger()
    main.ETAT["cfg"] = dataclasses.replace(main.ETAT["cfg"], carnet_url="http://carnet.exemple", carnet_jeton=lu.carnet_jeton)
    connecter(client)
    assert client.get("/api/carnet/personnes", params={"q": "he"}).json()["relie"] is True
    assert appels == [("http://carnet.exemple", "jeton-commun")]
    assert "DOUZE_POINTS_CARNET_JETON" not in client.get("/api/services").text
    carnet.oublier()


def test_le_jeton_commun_n_ouvre_pas_la_regie(client, env):
    """MAISON_JETON n'ouvre que /externe/sauvegarde : ni la régie ni la porte invité."""
    env.setenv("MAISON_JETON", "jeton-commun")
    entete = {"Authorization": "Bearer jeton-commun"}
    assert client.get("/api/soirees", headers=entete).status_code == 401
    assert client.get("/api/reglages", headers=entete).status_code == 401
    assert client.get("/api/services", headers={"X-Maison-Jeton": "jeton-commun"}).status_code == 401


def test_adresse_des_invites_par_l_anneau_toujours_locale(client, monkeypatch):
    """L'adresse locale de la tuile « Douze points », même quand la régie est ouverte par Tailscale : les
    téléphones des invités ne sont pas sur le réseau privé."""
    monkeypatch.setattr(main, "ANNUAIRE", faux_annuaire([
        {"nom": "Douze points", "locale": "http://192.0.2.20:8088/", "privee": "https://douze.exemple.ts.net"},
        {"nom": "carnet", "locale": "http://192.0.2.20:8096"}]))
    connecter(client)
    sid = client.post("/api/soirees", json={"concours": "Eurovision", "annee": 2027, "emission": "finale"}).json()["id"]
    for hote in ("192.0.2.20:8088", "douze.exemple.ts.net", "100.100.1.2:8088"):
        h = {"Host": hote}
        assert client.get("/api/session", headers=h).json()["adresse"] == "http://192.0.2.20:8088"
        s = client.get(f"/api/soirees/{sid}", headers=h).json()
        assert s["lien"] == f"http://192.0.2.20:8088/invite/{s['jeton_invite']}"
    assert client.get(f"/api/soirees/{sid}/qr.svg").status_code == 200


def test_sans_anneau_pas_de_qr_code(client, monkeypatch, env):
    """Plus de repli : DOUZE_POINTS_ADRESSE posée n'est pas lue ; sans tuile ou sans Anneau, message clair."""
    env.setenv("DOUZE_POINTS_ADRESSE", "http://192.0.2.10:8088")
    connecter(client)
    sid = client.post("/api/soirees", json={"concours": "Eurovision", "annee": 2027, "emission": "finale"}).json()["id"]

    def injoignable():
        raise OSError("pas d'Anneau")
    for annuaire in (faux_annuaire([{"nom": "carnet", "locale": "http://192.0.2.20:8096"}]),
                     maison.Annuaire(url="http://anneau.exemple", jeton="jeton-commun", lire=injoignable),
                     maison.Annuaire(url="http://anneau.exemple", jeton="")):       # sans jeton : l'Anneau n'est pas lu
        monkeypatch.setattr(main, "ANNUAIRE", annuaire)
        assert client.get("/api/session").json()["adresse"] == ""
        assert client.get(f"/api/soirees/{sid}").json()["lien"] == ""
        r = client.get(f"/api/soirees/{sid}/qr.svg")
        assert r.status_code == 409 and "Anneau" in r.json()["detail"] and "DOUZE_POINTS" not in r.json()["detail"]
