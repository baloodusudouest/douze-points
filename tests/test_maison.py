"""1.1 : variables communes de la maison (module app/maison.py du socle, copié tel quel).
Sans réseau : l'Anneau et carnet sont remplacés par des faux. Adresses de la plage de documentation."""
import dataclasses

import pytest

from app import carnet, config as config_mod, main, maison
from tests.conftest import connecter

VARIABLES = ("MAISON_PASSWORD", "MAISON_JETON", "MAISON_JETON_ANCIEN", "MAISON_LECTURE_SEULE",
             "DOUZE_POINTS_PASSWORD", "DOUZE_POINTS_CARNET_JETON", "DOUZE_POINTS_ADRESSE")


@pytest.fixture()
def env(monkeypatch, tmp_path):
    for v in VARIABLES:
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("DOUZE_POINTS_DATA", str(tmp_path))
    return monkeypatch


def test_copie_du_module_non_retouchee():
    assert maison.CONTRAT == 1
    assert maison.empreinte_calculee() == maison.empreinte_ecrite()


def test_mot_de_passe_commun_puis_ancien_nom(env):
    env.setenv("DOUZE_POINTS_PASSWORD", "ancien-mot-de-passe")
    assert config_mod.charger().password == "ancien-mot-de-passe"
    env.setenv("MAISON_PASSWORD", "mot-de-passe-commun")
    assert config_mod.charger().password == "mot-de-passe-commun"
    env.setenv("MAISON_PASSWORD", "court")                       # douze caractères au moins, comme avant
    with pytest.raises(SystemExit, match="MAISON_PASSWORD"):
        config_mod.charger()
    env.delenv("MAISON_PASSWORD")
    env.delenv("DOUZE_POINTS_PASSWORD")
    with pytest.raises(SystemExit, match="DOUZE_POINTS_PASSWORD"):
        config_mod.charger()


def test_jeton_envoye_a_carnet_ancien_d_abord_puis_commun(env):
    env.setenv("MAISON_PASSWORD", "mot-de-passe-commun")
    assert config_mod.charger().carnet_jeton == ""                       # rien de posé : carnet n'est pas lu
    env.setenv("MAISON_JETON", "jeton-commun")
    assert config_mod.charger().carnet_jeton == "jeton-commun"
    env.setenv("DOUZE_POINTS_CARNET_JETON", "jeton-de-la-paire")        # transition : l'ancien passe d'abord
    assert config_mod.charger().carnet_jeton == "jeton-de-la-paire"


def test_carnet_recoit_le_jeton_commun(client, env):
    """Le jeton commun part bien dans la demande à carnet /douze-points/personnes."""
    env.setenv("MAISON_PASSWORD", "mot-de-passe-commun")
    env.setenv("MAISON_JETON", "jeton-commun")
    appels = []
    env.setattr(carnet, "appeler", lambda url, jeton: appels.append((url, jeton)) or [])
    carnet.oublier()
    lu = config_mod.charger()
    main.ETAT["cfg"] = dataclasses.replace(main.ETAT["cfg"], carnet_url="http://carnet.exemple", carnet_jeton=lu.carnet_jeton)
    connecter(client)
    assert client.get("/api/carnet/personnes", params={"q": "he"}).json()["relie"] is True
    assert appels == [("http://carnet.exemple", "jeton-commun")]
    carnet.oublier()


def test_le_jeton_commun_n_ouvre_pas_la_regie(client, env):
    """Douze points ne reçoit aucun jeton d'une autre appli : MAISON_JETON n'ouvre ni la régie ni rien d'autre."""
    env.setenv("MAISON_JETON", "jeton-commun")
    entete = {"Authorization": "Bearer jeton-commun"}
    assert client.get("/api/soirees", headers=entete).status_code == 401
    assert client.get("/api/services", headers={"X-Maison-Jeton": "jeton-commun"}).status_code == 401


def _annuaire(services):
    return maison.Annuaire(url="http://anneau.exemple", jeton="jeton-commun", lire=lambda: services)


def test_adresse_des_invites_par_l_anneau_toujours_locale(client, monkeypatch):
    """L'adresse locale de la tuile « Douze points » passe avant DOUZE_POINTS_ADRESSE, même quand la régie est
    ouverte par Tailscale : les téléphones des invités ne sont pas sur le réseau privé."""
    monkeypatch.setattr(main, "ANNUAIRE", _annuaire([
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


def test_adresse_des_invites_repli_sur_la_variable(client, monkeypatch):
    # Anneau qui ne connaît pas la tuile, puis Anneau injoignable : DOUZE_POINTS_ADRESSE (conftest : 192.0.2.10)
    connecter(client)
    sid = client.post("/api/soirees", json={"concours": "Eurovision", "annee": 2027, "emission": "finale"}).json()["id"]
    def injoignable():
        raise OSError("pas d'Anneau")
    for annuaire in (_annuaire([{"nom": "carnet", "locale": "http://192.0.2.20:8096"}]),
                     maison.Annuaire(url="http://anneau.exemple", jeton="jeton-commun", lire=injoignable),
                     maison.Annuaire(url="http://anneau.exemple", jeton="")):       # sans jeton : l'Anneau n'est pas lu
        monkeypatch.setattr(main, "ANNUAIRE", annuaire)
        assert client.get("/api/session").json()["adresse"] == "http://192.0.2.10:8088"
        s = client.get(f"/api/soirees/{sid}").json()
        assert s["lien"] == f"http://192.0.2.10:8088/invite/{s['jeton_invite']}"
    # ni tuile ni variable : pas de QR code, message clair
    main.ETAT["cfg"] = dataclasses.replace(main.ETAT["cfg"], adresse="")
    r = client.get(f"/api/soirees/{sid}/qr.svg")
    assert r.status_code == 409 and "DOUZE_POINTS_ADRESSE" in r.json()["detail"]
    assert client.get(f"/api/soirees/{sid}").json()["lien"] == ""
