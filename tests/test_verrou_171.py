"""1.7.1 : plusieurs téléphones qui écrivent en même temps ne font plus d'erreur 500 (« database is locked »).

Cause (journal du Bac à sable, 19/11/2026, 7 téléphones) : une transaction lisait d'abord, puis écrivait ; si un autre
téléphone avait écrit entre-temps, SQLite refusait l'écriture tout de suite, sans attendre. `base()` prend maintenant
le tour d'écriture dès le début (BEGIN IMMEDIATE) et attend son tour."""
import threading

from app import base
from tests.conftest import PRENOMS


def test_ecritures_simultanees_sans_refus(tmp_path):
    base.preparer(tmp_path)
    with base.base(tmp_path) as cx:
        cx.execute("CREATE TABLE essai(id INTEGER PRIMARY KEY, n INT)")
        cx.executemany("INSERT INTO essai(n) VALUES(?)", [(0,)] + [(i,) for i in range(50)])
    erreurs = []

    def travail():
        for _ in range(40):
            try:
                with base.base(tmp_path) as cx:
                    lecture = cx.execute("SELECT n FROM essai")      # lecture laissée ouverte, comme _porte ou _moi
                    lecture.fetchone()
                    cx.execute("UPDATE essai SET n=n+1 WHERE id=1")
                    cx.execute("SELECT n FROM essai").fetchone()
                    cx.execute("UPDATE essai SET n=n+1 WHERE id=1")
            except Exception as e:  # noqa: BLE001
                erreurs.append(repr(e))

    fils = [threading.Thread(target=travail) for _ in range(8)]
    for f in fils:
        f.start()
    for f in fils:
        f.join()
    assert erreurs == []
    with base.base(tmp_path) as cx:
        assert cx.execute("SELECT n FROM essai WHERE id=1").fetchone()[0] == 8 * 40 * 2


def test_annulee_si_erreur(tmp_path):
    base.preparer(tmp_path)
    try:
        with base.base(tmp_path) as cx:
            cx.execute("INSERT INTO concours(nom) VALUES('Concours annulé')")
            raise RuntimeError("panne au milieu")
    except RuntimeError:
        pass
    with base.base(tmp_path) as cx:
        assert not cx.execute("SELECT 1 FROM concours WHERE nom='Concours annulé'").fetchone()


def test_telephones_qui_notent_en_meme_temps(client, soiree):
    """Quatre téléphones notent toutes les chansons en même temps pendant que la régie relit l'état : aucune 500."""
    for p in PRENOMS:
        soiree.entrer(p)
    codes = []

    def noter(k, prenom):
        for i, chanson in enumerate(soiree.chansons):
            r = client.put(soiree.url("note"), headers=soiree.tel[prenom],
                           json={"chanson_id": chanson, "valeur": ((i * (k + 3)) % 41) / 2, "commentaire": f"Mot {i}"})
            codes.append(r.status_code)
            codes.append(client.get(soiree.url("etat"), headers=soiree.tel[prenom]).status_code)

    fils = [threading.Thread(target=noter, args=(k, p)) for k, p in enumerate(PRENOMS)]
    for f in fils:
        f.start()
    for f in fils:
        f.join()
    assert set(codes) == {200}
    for p in PRENOMS:
        assert len(soiree.etat(p)["moi"]["notes"]) == len(soiree.chansons)
