"""Le calcul seul : classement d'un invité, barème, départage du groupe."""
from app.points import BAREME, classement_groupe, classement_par_notes, inserer, points_du_classement


def test_classement_par_notes_puis_ordre_de_passage():
    notes = {1: 30, 2: 36, 3: 30, 4: 10}
    assert classement_par_notes(notes, {1: 1, 2: 2, 3: 3, 4: 4}) == [2, 1, 3, 4]


def test_bareme_du_concours_pour_les_dix_premieres():
    points = points_du_classement(list(range(1, 15)))
    assert [points[i] for i in range(1, 11)] == [12, 10, 8, 7, 6, 5, 4, 3, 2, 1] == list(BAREME)
    assert all(i not in points for i in range(11, 15))


def test_classement_court_donne_les_points_des_rangs_qu_il_a():
    assert points_du_classement([7, 3, 9]) == {7: 12, 3: 10, 9: 8}


def test_insertion_dans_un_ordre_fait_a_la_main():
    notes = {1: 20, 2: 36, 3: 10, 9: 30}
    # ordre à la main qui contredit les notes : 1 (10/20) devant 2 (18/20)
    assert inserer([1, 2, 3], 9, notes) == [9, 1, 2, 3]       # 15/20 passe au-dessus de la première plus basse
    notes[9] = 4
    assert inserer([1, 2, 3], 9, notes) == [1, 2, 3, 9]       # plus basse que toutes : en bas
    assert inserer([1, 9, 2], 9, notes) == [1, 9, 2]          # déjà rangée : rien ne bouge


def test_groupe_somme_et_departages():
    passage = {1: 1, 2: 2, 3: 3, 4: 4}
    # 1 et 2 ont 12 points chacune : 2 les tient de deux invités, elle passe devant
    points = {"a": {1: 12, 2: 6}, "b": {2: 6, 3: 10}}
    notes = {"a": {1: 40, 2: 30}, "b": {2: 30, 3: 38}}
    lignes = classement_groupe([1, 2, 3, 4], points, notes, passage)
    assert [(l["chanson"], l["total"], l["rang"]) for l in lignes] == [(2, 12, 1), (1, 12, 2), (3, 10, 3), (4, 0, 4)]


def test_groupe_plus_de_douze_puis_moyenne_puis_ex_aequo():
    passage = {1: 1, 2: 2, 3: 3, 4: 4}
    points = {"a": {1: 12, 2: 10, 3: 8, 4: 8}, "b": {1: 10, 2: 12, 3: 8, 4: 8}}
    notes = {"a": {1: 40, 2: 30, 3: 20, 4: 20}, "b": {1: 20, 2: 20, 3: 20, 4: 20}}
    lignes = classement_groupe([1, 2, 3, 4], points, notes, passage)
    # 1 et 2 : même total, mêmes votants, un 12 et un 10 chacune ; la moyenne des notes départage (1 : 15, 2 : 12,5)
    assert [l["chanson"] for l in lignes[:2]] == [1, 2] and [l["rang"] for l in lignes[:2]] == [1, 2]
    # 3 et 4 : rien ne les départage, même rang, dans l'ordre de passage
    assert [(l["chanson"], l["rang"]) for l in lignes[2:]] == [(3, 3), (4, 3)]
