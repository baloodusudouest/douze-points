"""1.2 : réglages dans l'appli, sauvegarde pour l'Anneau (contrat de sauvegarde 1) et restauration.
Sans réseau : l'Anneau est remplacé par un faux (main.LIRE_ANNEAU, argument lire= de maison.lire_sauvegarde)."""
import json
import urllib.error

import pytest
from fastapi.testclient import TestClient

from app import __version__, main, maison
from app.config import Config
from tests.conftest import MOT_DE_PASSE, connecter, faux_annuaire

WEBHOOK = "http://ha.exemple:8123/api/webhook/essai-douze-points"


@pytest.fixture()
def env(monkeypatch):
    for v in ("MAISON_JETON", "MAISON_JETON_ANCIEN", "DOUZE_POINTS_HA_WEBHOOK", "DOUZE_POINTS_CARNET_JETON"):
        monkeypatch.delenv(v, raising=False)
    return monkeypatch


def demarrer(dossier):
    """Un démarrage de l'appli sur ce dossier de données (comme un redémarrage du conteneur)."""
    main.ETAT.clear()
    main.ETAT["cfg"] = Config(password=MOT_DE_PASSE, data=dossier, static=dossier / "static",
                              attente_connexion=False, limite_invite=100000)
    return TestClient(main.app)


# ---------------------------------------------------------------- reprise depuis la stack, une seule fois

def test_reprise_de_l_ancienne_variable_au_premier_demarrage(tmp_path, env):
    env.setattr(main, "ANNUAIRE", faux_annuaire([]))
    env.setenv("DOUZE_POINTS_HA_WEBHOOK", WEBHOOK)
    with demarrer(tmp_path) as c:
        connecter(c)
        assert c.get("/api/reglages").json() == {"pas_note": 0.5, "ha_webhook": WEBHOOK}
        assert c.get("/api/session").json()["notification"] is True
        journal = c.get("/api/journal").json()
        reprise = [j for j in journal if j["action"] == "reglage_repris"]
        assert [(j["cible"], json.loads(j["detail"])) for j in reprise] == [
            ("ha_webhook", {"variable": "DOUZE_POINTS_HA_WEBHOOK"})]
        assert WEBHOOK not in c.get("/api/journal").text                       # le nom, jamais la valeur
    assert json.loads((tmp_path / "reglages.json").read_text()) == {"ha_webhook": WEBHOOK}
    # second démarrage : la variable a changé (ou disparu), elle n'est plus lue
    env.setenv("DOUZE_POINTS_HA_WEBHOOK", "http://autre.exemple/api/webhook/x")
    with demarrer(tmp_path) as c:
        connecter(c)
        assert c.get("/api/reglages").json()["ha_webhook"] == WEBHOOK
        assert len([j for j in c.get("/api/journal").json() if j["action"] == "reglage_repris"]) == 1
    env.delenv("DOUZE_POINTS_HA_WEBHOOK")
    with demarrer(tmp_path) as c:
        connecter(c)
        assert c.get("/api/reglages").json()["ha_webhook"] == WEBHOOK
    main.ETAT.clear()


def test_sans_variable_le_defaut(client):
    connecter(client)
    assert client.get("/api/reglages").json() == {"pas_note": 0.5, "ha_webhook": ""}
    assert client.get("/api/session").json()["notification"] is False


# ---------------------------------------------------------------- écran Réglages

def test_changer_les_reglages(client, tmp_path):
    connecter(client)
    r = client.put("/api/reglages", json={"ha_webhook": f"  {WEBHOOK} ", "pas_note": 0.25, "inconnu": 3})
    assert r.status_code == 200 and r.json() == {"pas_note": 0.25, "ha_webhook": WEBHOOK}
    assert client.get("/api/session").json()["notification"] is True
    assert json.loads((tmp_path / "reglages.json").read_text()) == {"ha_webhook": WEBHOOK}
    assert WEBHOOK not in client.get("/api/journal").text
    assert client.put("/api/reglages", json={"ha_webhook": ""}).json()["ha_webhook"] == ""


@pytest.mark.parametrize("corps", [{"pas_note": "beaucoup"}, {"pas_note": 0.3}, {"pas_note": True}, {"pas_note": None},
                                   {"ha_webhook": 12}, {"ha_webhook": ["http://x"]}, {"ha_webhook": "pas une adresse"},
                                   {"ha_webhook": WEBHOOK, "pas_note": 0.3}])
def test_mauvais_type_400_et_rien_ne_change(client, corps):
    connecter(client)
    r = client.put("/api/reglages", json=corps)
    assert r.status_code == 400 and r.json()["detail"]
    assert client.get("/api/reglages").json() == {"pas_note": 0.5, "ha_webhook": ""}


def test_reglages_fermes_sans_connexion(client):
    assert client.get("/api/reglages").status_code == 401
    assert client.put("/api/reglages", json={"pas_note": 1}).status_code == 401
    assert client.get("/api/restaurer").status_code == 401
    assert client.post("/api/restaurer", json={"le": "2026-11-15"}).status_code == 401


# ---------------------------------------------------------------- /externe/sauvegarde

def test_sauvegarde_ouverte_par_le_jeton_commun_seul(client, env):
    connecter(client)
    client.put("/api/reglages", json={"ha_webhook": WEBHOOK, "pas_note": 1})
    client.cookies.clear()                                        # l'Anneau n'a pas de session
    env.setenv("MAISON_JETON", "jeton-commun")
    env.setenv("DOUZE_POINTS_CARNET_JETON", "jeton-de-la-paire")
    assert client.get("/externe/sauvegarde").status_code == 404
    assert client.get("/externe/sauvegarde", headers={"Authorization": "Bearer jeton-de-la-paire"}).status_code == 404
    assert client.get("/externe/sauvegarde", headers={"Authorization": "Bearer mauvais"}).status_code == 404
    r = client.get("/externe/sauvegarde", headers={"Authorization": "Bearer jeton-commun"})
    assert r.status_code == 200
    s = r.json()
    assert s["contrat"] == maison.CONTRAT_SAUVEGARDE == 1
    assert s["appli"] == "douze-points" and s["version"] == __version__
    assert s["reglages"] == {"pas_note": 1.0}
    for interdit in ("ha_webhook", "webhook", WEBHOOK, "ha.exemple", MOT_DE_PASSE, "jeton-commun",
                     "DOUZE_POINTS", "MAISON_", "/data", "reglages.json"):
        assert interdit not in r.text, interdit
    assert client.get("/externe/sauvegarde", headers={"X-Maison-Jeton": "jeton-commun"}).status_code == 200


def test_sauvegarde_fermee_si_jeton_commun_vide(client, env):
    env.setenv("MAISON_JETON", "")
    assert client.get("/externe/sauvegarde", headers={"Authorization": "Bearer "}).status_code == 404
    assert client.get("/externe/sauvegarde", headers={"Authorization": "Bearer n-importe-quoi"}).status_code == 404


def test_sante_inchangee(client):
    r = client.get("/health").json()
    assert set(r) == {"ok", "version", "soirees", "soiree_en_cours", "classements_attendus"}


# ---------------------------------------------------------------- restaurer

def anneau(sauvegardes):
    """Faux Anneau : {date: réglages}. Note chaque demande et le jeton joint."""
    demandes = []

    def lire(adresse, jeton):
        demandes.append((adresse, jeton))
        if "?le=" not in adresse:
            return {"dates": sorted(sauvegardes, reverse=True)}
        le = adresse.rsplit("=", 1)[1]
        if le not in sauvegardes:
            raise urllib.error.HTTPError(adresse, 404, "absent", {}, None)
        return {"le": le, "version": "1.2.0", "reglages": sauvegardes[le]}
    lire.demandes = demandes
    return lire


def test_restaurer_dates_differences_application(client, monkeypatch):
    faux = anneau({"2026-11-14": {"pas_note": 0.25, "ha_webhook": "http://intrus.exemple/x", "disparu": 1},
                   "2026-11-15": {"pas_note": 0.5}})
    monkeypatch.setattr(main, "LIRE_ANNEAU", faux)
    connecter(client)
    client.put("/api/reglages", json={"ha_webhook": WEBHOOK})
    assert client.get("/api/restaurer").json() == {"dates": ["2026-11-15", "2026-11-14"]}
    assert faux.demandes[0][0].endswith("/externe/sauvegardes/douze-points")
    assert client.get("/api/restaurer", params={"le": "2026-11-15"}).json() == {
        "le": "2026-11-15", "version": "1.2.0", "differences": []}
    d = client.get("/api/restaurer", params={"le": "2026-11-14"}).json()
    # le webhook (exclu) et une clé que l'appli ne connaît plus ne sont jamais proposés
    assert d["differences"] == [{"cle": "pas_note", "actuel": 0.5, "sauve": 0.25}]
    r = client.post("/api/restaurer", json={"le": "2026-11-14"})
    assert r.status_code == 200
    assert r.json() == {"le": "2026-11-14", "restaures": ["pas_note"], "reglages": {"pas_note": 0.25, "ha_webhook": WEBHOOK}}
    assert client.get("/api/reglages").json() == {"pas_note": 0.25, "ha_webhook": WEBHOOK}
    ligne = next(j for j in client.get("/api/journal").json() if j["action"] == "reglages_restaures")
    assert ligne["cible"] == "2026-11-14" and json.loads(ligne["detail"]) == {"cles": ["pas_note"]}
    assert client.post("/api/restaurer", json={"le": "2026-11-14"}).json()["restaures"] == []     # déjà fait


def test_restaurer_messages_clairs(client, monkeypatch):
    connecter(client)

    def injoignable(adresse, jeton):
        raise OSError("pas d'Anneau")
    monkeypatch.setattr(main, "LIRE_ANNEAU", injoignable)
    for r in (client.get("/api/restaurer"), client.get("/api/restaurer", params={"le": "2026-11-14"}),
              client.post("/api/restaurer", json={"le": "2026-11-14"})):
        assert r.status_code == 503 and "L'Anneau ne répond pas" in r.json()["detail"]
    monkeypatch.setattr(main, "LIRE_ANNEAU", anneau({}))
    r = client.get("/api/restaurer")
    assert r.status_code == 404 and "aucune sauvegarde" in r.json()["detail"]
    r = client.post("/api/restaurer", json={"le": "2026-11-01"})
    assert r.status_code == 404 and "2026-11-01" in r.json()["detail"]
    assert client.get("/api/restaurer", params={"le": "hier"}).status_code == 400
    assert client.post("/api/restaurer", json={}).status_code == 400
    # une sauvegarde abîmée (mauvais type) ne casse rien
    monkeypatch.setattr(main, "LIRE_ANNEAU", anneau({"2026-11-14": {"pas_note": 0.3}}))
    assert client.post("/api/restaurer", json={"le": "2026-11-14"}).status_code == 400
    assert client.get("/api/reglages").json()["pas_note"] == 0.5


def test_restaurer_par_le_vrai_chemin_sans_anneau(client, monkeypatch):
    """Sans faux : maison.lire_sauvegarde vers une adresse injoignable donne le même message clair."""
    monkeypatch.setenv("MAISON_ANNEAU_URL", "http://127.0.0.1:9")
    connecter(client)
    r = client.get("/api/restaurer")
    assert r.status_code == 503 and "L'Anneau ne répond pas" in r.json()["detail"]
