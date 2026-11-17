"""1.3.1 (audit du 17/11/2026) : double dévoilement, note non finie, prénom pris entre deux."""
from app import main
from tests.conftest import PRENOMS


def test_double_devoilement_refuse(client, soiree):
    for prenom in PRENOMS:
        soiree.noter(prenom, {1: 10, 2: 8})
    assert client.post(f"/api/soirees/{soiree.id}/devoiler", json={"forcer": True}).status_code == 200
    ordre = client.get(f"/api/soirees/{soiree.id}").json().get("ordre_devoilement")
    assert client.post(f"/api/soirees/{soiree.id}/devoiler", json={"forcer": True}).status_code == 409
    assert client.get(f"/api/soirees/{soiree.id}").json().get("ordre_devoilement") == ordre


def test_note_non_finie_refusee(client, soiree):
    tel = soiree.entrer(PRENOMS[0])
    for v in ("nan", "inf", "-inf"):
        r = client.put(soiree.url("note"), headers=tel, json={"chanson_id": soiree.chansons[0], "valeur": v})
        assert r.status_code == 422, (v, r.status_code)


def test_prenom_pris_entre_la_lecture_et_l_ecriture(client, soiree, monkeypatch):
    """Le second téléphone n'écrase plus le jeton du premier."""
    from app import base as base_mod
    pid = soiree.part[PRENOMS[0]]
    with base_mod.base(main.cfg().data) as cx:
        cx.execute("UPDATE participation SET jeton_telephone='deja-pris' WHERE id=?", (pid,))
    r = client.post(soiree.url("prenom"), json={"participation_id": pid})
    assert r.status_code == 409
    with base_mod.base(main.cfg().data) as cx:
        assert cx.execute("SELECT jeton_telephone FROM participation WHERE id=?", (pid,)).fetchone()[0] == "deja-pris"
