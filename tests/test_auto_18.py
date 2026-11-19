"""1.8.0 : les points du public passent seuls toutes les 5 s, pas tenu par le serveur (conseil 1.8.0).
Le temps est simulé : `main.horloge` est remplacée. Une régie qui regarde appelle /regard toutes les 2 s."""
import threading

import pytest

from app import base as base_mod
from app import main
from tests.conftest import PRENOMS


class Horloge:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


@pytest.fixture()
def temps(monkeypatch):
    h = Horloge()
    monkeypatch.setattr(main, "horloge", h)
    return h


def jury_puis_public(client, soiree):
    for i in client.get("/api/invites").json():
        if i["prenom"] == "Aglaé":
            client.put(f"/api/invites/{i['id']}", json={"jury": True})
    soiree.tout_le_monde()
    assert client.post(f"/api/soirees/{soiree.id}/devoiler").status_code == 200
    # 12 chansons : pas 1 = top du jury, pas 2 à 13 = le public (13 = le dernier pays), 14 = podium


def action(client, soiree, nom, **x):
    r = client.post(f"/api/soirees/{soiree.id}/pas", json={"action": nom, **x})
    assert r.status_code == 200, r.text
    return r.json()


def lu(client, soiree):
    return client.get(f"/api/soirees/{soiree.id}/devoilement").json()


def regarder(client, soiree, temps, jusqua):
    """La régie regarde, toutes les 2 s, jusqu'à l'heure dite."""
    while temps.t + 2 <= jusqua:
        temps.t += 2
        client.post(f"/api/soirees/{soiree.id}/regard")
    temps.t = jusqua
    client.post(f"/api/soirees/{soiree.id}/regard")


def test_le_public_passe_seul_toutes_les_5_secondes(client, soiree, temps):
    jury_puis_public(client, soiree)
    assert lu(client, soiree)["pas"] == 0
    action(client, soiree, "suivant")                       # le top 5 du jury : au toucher
    regarder(client, soiree, temps, 1030)
    d = lu(client, soiree)
    assert d["pas"] == 1 and not d["auto"]["actif"]          # le jury n'avance pas seul
    r = action(client, soiree, "suivant")                    # premier pays du public
    assert r["pas"] == 2 and r["auto"] == {"actif": True, "pause": False, "prochain_dans": 5000, "duree": 5000}
    regarder(client, soiree, temps, 1034.9)
    assert lu(client, soiree)["pas"] == 2
    regarder(client, soiree, temps, 1035.0)
    d = lu(client, soiree)
    assert d["pas"] == 3 and d["auto"]["prochain_dans"] == 5000
    regarder(client, soiree, temps, 1030 + 5 * 11)            # 11 pays plus tard : le dernier pays, lancé seul
    d = lu(client, soiree)
    assert d["pas"] == 13 and not d["auto"]["actif"] and d["auto"]["prochain_dans"] is None
    regarder(client, soiree, temps, 1200)
    assert lu(client, soiree)["pas"] == 13                    # le podium reste au toucher
    assert action(client, soiree, "suivant")["pas"] == 14


def test_pause_reprendre_et_revenir(client, soiree, temps):
    jury_puis_public(client, soiree)
    action(client, soiree, "aller", pas=2)
    regarder(client, soiree, temps, 1012)                     # 2 pays passés seuls
    assert lu(client, soiree)["pas"] == 4
    r = action(client, soiree, "pause")
    assert r["pas"] == 4 and r["auto"]["pause"] and r["auto"]["prochain_dans"] is None
    regarder(client, soiree, temps, 1060)
    assert lu(client, soiree)["pas"] == 4                     # en pause : rien ne bouge
    r = action(client, soiree, "reprendre")
    assert r["pas"] == 4 and r["auto"]["prochain_dans"] == 5000   # un pays entier avant le suivant
    regarder(client, soiree, temps, 1065)
    assert lu(client, soiree)["pas"] == 5
    r = action(client, soiree, "revenir")                     # revenir sur un pays : on le regarde, en pause
    assert r["pas"] == 4 and r["auto"]["pause"]
    regarder(client, soiree, temps, 1100)
    assert lu(client, soiree)["pas"] == 4


def test_suivant_pile_a_l_echeance_n_est_pas_perdu(client, soiree, temps):
    """L'écran croit être au pas 2 (lecture d'il y a une seconde) ; le serveur est déjà au 3 : « suivant » mène au 4."""
    jury_puis_public(client, soiree)
    action(client, soiree, "aller", pas=2)
    regarder(client, soiree, temps, 1005.0)
    assert action(client, soiree, "suivant")["pas"] == 4
    assert action(client, soiree, "pause")["pas"] == 4        # une pause ne recule jamais


def test_sans_regie_l_horloge_s_arrete_puis_pause(client, soiree, temps):
    """iPhone verrouillé ou reprise le lendemain : rien ne défile sans personne devant l'écran."""
    jury_puis_public(client, soiree)
    action(client, soiree, "aller", pas=2)                    # à 1000
    temps.t = 1600                                            # dix minutes sans régie
    assert lu(client, soiree)["pas"] == 2                     # au plus GARDE_REGIE secondes comptées (4 s < 5 s)
    client.post(f"/api/soirees/{soiree.id}/regard")           # la régie revient
    d = lu(client, soiree)
    assert d["pas"] == 2 and d["auto"]["pause"]
    assert action(client, soiree, "reprendre")["auto"]["prochain_dans"] == 5000


def test_ancien_corps_et_action_inconnue(client, soiree, temps):
    jury_puis_public(client, soiree)
    assert client.post(f"/api/soirees/{soiree.id}/pas", json={"pas": 14}).json()["pas"] == 14   # « Tout afficher »
    assert client.post(f"/api/soirees/{soiree.id}/pas", json={"action": "sauter"}).status_code == 422


def test_telephones_suivent_le_pas_et_savent_le_gagnant(client, soiree, temps):
    jury_puis_public(client, soiree)
    action(client, soiree, "aller", pas=2)
    regarder(client, soiree, temps, 1010)
    d = client.get(soiree.url("devoilement"), headers=soiree.tel["Barnabé"]).json()
    assert d["pas"] == 4 and d["auto"]["actif"] and "gagnant" not in d
    regarder(client, soiree, temps, 1010 + 5 * 9)
    d = client.get(soiree.url("devoilement"), headers=soiree.tel["Barnabé"]).json()
    regie = lu(client, soiree)
    assert d["pas"] == 13 and d["gagnant"] == regie["classement"][0]["chanson"] and "classement" not in d


def test_les_relectures_ne_font_pas_la_queue(client, soiree, temps):
    """Une écriture longue en cours n'empêche ni la télé ni les téléphones de relire (lecture sans verrou)."""
    jury_puis_public(client, soiree)
    tenu, fini = threading.Event(), threading.Event()

    def ecriture_longue():
        with base_mod.base(main.cfg().data) as cx:
            cx.execute("UPDATE soiree SET nom=nom WHERE id=?", (soiree.id,))
            tenu.set()
            fini.wait(10)

    f = threading.Thread(target=ecriture_longue)
    f.start()
    tenu.wait(5)
    try:
        assert client.get(f"/api/soirees/{soiree.id}/devoilement").status_code == 200
        assert client.get(soiree.url("devoilement"), headers=soiree.tel[PRENOMS[1]]).status_code == 200
        assert client.get(soiree.url("etat"), headers=soiree.tel[PRENOMS[1]]).status_code == 200
    finally:
        fini.set()
        f.join()


def test_revenir_avant_le_public_ne_laisse_pas_de_pause(client, soiree, temps):
    """Revenir du jury au départ, puis repartir : le public défile tout seul, sans « Reprendre »."""
    jury_puis_public(client, soiree)
    action(client, soiree, "suivant")                 # le jury
    assert not action(client, soiree, "revenir")["auto"]["pause"]
    action(client, soiree, "suivant")
    r = action(client, soiree, "suivant")             # premier pays du public
    assert r["pas"] == 2 and r["auto"]["actif"] and not r["auto"]["pause"]
    action(client, soiree, "pause")
    r = action(client, soiree, "aller", pas=14)       # « Tout afficher » puis revenir : pas de pause en réserve
    assert action(client, soiree, "revenir")["pas"] == 13
    assert not lu(client, soiree)["auto"]["pause"]
