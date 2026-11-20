"""1.9.0 : dévoilement automatique réglable (toutes les étapes, temps des Réglages) ou manuel (tout au toucher) ;
la révélation a un plafond, la télé dit quand elle a fini ; le podium écoulé termine le dévoilement sans carnet."""
from tests.test_auto_18 import Horloge, action, jury_puis_public, lu, regarder  # noqa: F401
import pytest

from app import main


@pytest.fixture()
def temps(monkeypatch):
    h = Horloge(1000.0)
    monkeypatch.setattr(main, "horloge", h)
    return h


def test_tout_s_enchaine_jusqu_aux_jumeaux(client, soiree, temps):
    jury_puis_public(client, soiree)                          # dévoilé à 1000 (12 chansons, jury puis public)
    d = lu(client, soiree)
    assert d["pas"] == 0 and d["auto"]["actif"] and d["auto"]["prochain_dans"] == 10000 and d["auto"]["mode"] == "auto"
    regarder(client, soiree, temps, 1010)
    assert lu(client, soiree)["pas"] == 1                     # le top 5 du jury, seul après 10 s
    regarder(client, soiree, temps, 1025)
    assert lu(client, soiree)["pas"] == 2                     # 15 s de jury
    regarder(client, soiree, temps, 1080)
    d = lu(client, soiree)
    assert d["pas"] == 13                                     # 11 pays à 5 s : le dernier vote du public
    plafond = main.duree_revelation(12)
    assert d["auto"]["duree"] == int(plafond * 1000) and 66 < plafond < 68
    regarder(client, soiree, temps, 1080 + plafond)
    assert lu(client, soiree)["pas"] == 14                    # le podium
    regarder(client, soiree, temps, 1080 + plafond + 14.9)
    assert lu(client, soiree)["etat"] == "devoilement"
    regarder(client, soiree, temps, 1080 + plafond + 15)
    assert lu(client, soiree)["etat"] == "devoilee"           # les jumeaux : terminé seul
    assert client.post(f"/api/soirees/{soiree.id}/terminer").json() == {"ok": True}   # la télé aussi : sans effet


def test_la_tele_finit_la_revelation_plus_tot(client, soiree, temps):
    jury_puis_public(client, soiree)
    action(client, soiree, "aller", pas=13)
    assert action(client, soiree, "suivant", depuis=12)["pas"] == 13       # trop tard : déjà ailleurs, ignoré
    assert action(client, soiree, "suivant", depuis=13)["pas"] == 14       # animation finie : podium tout de suite


def test_manuel_tout_au_toucher(client, soiree, temps):
    client.put("/api/reglages", json={"devoilement_auto": False})
    jury_puis_public(client, soiree)
    regarder(client, soiree, temps, 1500)
    d = lu(client, soiree)
    assert d["pas"] == 0 and not d["auto"]["actif"] and d["auto"]["mode"] == "manuel"
    action(client, soiree, "aller", pas=2)
    regarder(client, soiree, temps, 1600)
    assert lu(client, soiree)["pas"] == 2                     # le public aussi, au toucher
    # repasser en automatique en plein dévoilement : ça repart d'ici
    client.put("/api/reglages", json={"devoilement_auto": True})
    action(client, soiree, "reprendre")
    regarder(client, soiree, temps, 1605)
    assert lu(client, soiree)["pas"] == 3


def test_temps_reglables_et_bornes(client, soiree, temps):
    r = client.put("/api/reglages", json={"duree_public": 8, "duree_jury": 20, "duree_revelation": 45})
    assert r.status_code == 200 and r.json()["duree_public"] == 8
    for faux in ({"duree_public": 1}, {"duree_jury": 9999}, {"duree_podium": "15"}, {"duree_selfie": 2.5},
                 {"devoilement_auto": "oui"}):
        assert client.put("/api/reglages", json=faux).status_code == 400, faux
    jury_puis_public(client, soiree)
    action(client, soiree, "aller", pas=2)
    assert lu(client, soiree)["auto"]["duree"] == 8000
    assert abs(main.duree_revelation(12) - (1.32 + 0.9 + 45 + 5)) < 1e-9
