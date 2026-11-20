"""1.9.0 : les calculs du journal (app/journal.py), seuls."""
from app import resultat as journal


def test_rangs_moyens_ex_aequo_et_saisis():
    r = journal.rangs_moyens({1: 300, 2: 250, 3: 250, 4: 100, 5: None})
    assert r == {1: 1.0, 2: 2.5, 3: 2.5, 4: 4.0, 5: None}
    # le rang officiel saisi par l'hôte l'emporte (départage du concours)
    r = journal.rangs_moyens({1: 300, 2: 250, 3: 250}, {2: 2, 3: 3})
    assert r == {1: 1.0, 2: 2.0, 3: 3.0}


def test_ecarts_ignorent_les_pays_absents():
    assert journal.ecarts({1: 1, 2: 2, 3: 3}, {1: 2.0, 2: None, 3: 3.0}) == {1: 1.0, 3: 0.0}


def test_mieux_et_moins_bien_sans_doublon():
    mieux, rates = journal.mieux_et_moins_bien({1: 0, 2: 4, 3: 1, 4: 7, 5: 2}, {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}, n=3)
    assert mieux == [1, 3, 5] and rates == [4, 2]


def test_palmares_plus_proche_et_incomplets():
    officiel = {1: 1.0, 2: 2.0, 3: 3.0, 4: 4.0}
    classements = {10: {1: 1, 2: 2, 3: 3, 4: 4},       # parfait
                   11: {1: 2, 2: 1, 3: 4, 4: 3},       # écart 1
                   12: {1: 1, 2: 2}}                   # n'a pas tout classé : en fin de liste
    p = journal.palmares(classements, officiel, 4, {10: "Aglaé", 11: "Barnabé", 12: "Célestine"})
    assert [x["invite"] for x in p] == [10, 11, 12]
    assert p[0]["ecart_moyen"] == 0 and p[0]["complet"] and p[0]["podium_trouve"] == 3
    assert not p[2]["complet"]


def test_palmares_departage_par_le_podium():
    officiel = {1: 1.0, 2: 2.0, 3: 3.0, 4: 4.0}
    classements = {10: {1: 4, 2: 2, 3: 3, 4: 1}, 11: {1: 1, 2: 2, 3: 4, 4: 3}}   # même écart moyen (1,5 / 0,5) ? non :
    p = journal.palmares(classements, officiel, 4, {10: "Zoé", 11: "Aglaé"})
    assert p[0]["invite"] == 11
    egal = {10: {1: 2, 2: 1, 3: 3, 4: 4}, 11: {1: 1, 2: 2, 3: 4, 4: 3}}            # écart 0,5 chacun
    p = journal.palmares(egal, officiel, 4, {10: "Zoé", 11: "Aglaé"})
    assert p[0]["podium_trouve"] >= p[1]["podium_trouve"]


def test_demi_finale():
    maison = {c: c for c in range(1, 16)}                 # la chanson c est c-ième chez nous
    qualifies = {1, 2, 3, 4, 5, 6, 7, 12, 14, 15}
    classements = {10: {c: c for c in range(1, 16)}, 11: {c: 16 - c for c in range(1, 16)}}
    moyennes = {c: 20 - c for c in range(1, 16)}
    d = journal.demi_finale(maison, qualifies, classements, moyennes, {10: "Aglaé", 11: "Barnabé"})
    assert d["flair"][0] == {"invite": 10, "trouves": 7, "sur": 10}
    assert d["pleure"] == [8, 9, 10]
    assert d["deteste"] == [15, 14, 12]
    assert d["coup_de_coeur"] == 1 and d["nul_point"] == 15
    assert d["favoris"] == [1, 2, 3]
    assert len(d["notre_top"]) == 10 and d["notre_top"][7] == {"chanson": 8, "qualifie": False}


def test_numero():
    assert journal.numero(2027, "Eurovision", "Finale") == "2027 · Eurovision · Finale"
