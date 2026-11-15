"""Le calcul, sans base ni réseau : classement d'un invité, barème du concours, classement du groupe.

Les notes sont en quarts de point entiers (0 à 80 pour 0 à 20, `ECHELLE` = 4) : aucune comparaison de nombres à virgule.
(Jusqu'à la 0.10, en demi-points ; la base est convertie une fois, voir base.preparer.)
"""
from __future__ import annotations

ECHELLE = 4                                  # une note de 20 est rangée 80
BAREME = (12, 10, 8, 7, 6, 5, 4, 3, 2, 1)   # rangs 1 à 10 de chaque invité ; rien au-delà


def classement_par_notes(notes: dict[int, int], ordre_passage: dict[int, int]) -> list[int]:
    """Chansons notées, de la mieux notée à la moins bien notée ; à note égale, l'ordre de passage."""
    return sorted(notes, key=lambda c: (-notes[c], ordre_passage.get(c, 0)))


def inserer(ordre: list[int], chanson: int, notes: dict[int, int]) -> list[int]:
    """Place une chanson nouvellement notée dans un ordre fait à la main, sans toucher au reste :
    juste au-dessus de la première chanson, en partant du haut, dont la note est plus basse ; sinon en bas."""
    if chanson in ordre:
        return list(ordre)
    for i, autre in enumerate(ordre):
        if notes.get(autre, 0) < notes[chanson]:
            return ordre[:i] + [chanson] + ordre[i:]
    return list(ordre) + [chanson]


def points_du_classement(ordre: list[int]) -> dict[int, int]:
    """12, 10, 8… 1 pour les dix premières. Un classement plus court donne les points des rangs qu'il a."""
    return {chanson: BAREME[rang] for rang, chanson in enumerate(ordre[:len(BAREME)])}


def classement_groupe(chansons: list[int], points: dict[int, dict[int, int]],
                      notes: dict[int, dict[int, int]], ordre_passage: dict[int, int]) -> list[dict]:
    """Somme des points de chaque invité, puis départage :
    le plus d'invités ayant donné des points, le plus de 12, de 10…, la meilleure moyenne des notes.
    `points` et `notes` : par invité, puis par chanson. Deux chansons que rien ne départage ont le même rang."""
    lignes = []
    for c in chansons:
        recus = [p[c] for p in points.values() if c in p]
        valeurs = [n[c] for n in notes.values() if c in n]
        moyenne = sum(valeurs) / len(valeurs) if valeurs else -1.0
        cle = (sum(recus), len(recus), tuple(recus.count(b) for b in BAREME), moyenne)
        lignes.append({"chanson": c, "total": sum(recus), "votants": len(recus),
                       "moyenne": None if moyenne < 0 else round(moyenne / ECHELLE, 2), "_cle": cle})
    lignes.sort(key=lambda l: (-l["_cle"][0], -l["_cle"][1], tuple(-x for x in l["_cle"][2]), -l["_cle"][3],
                               ordre_passage.get(l["chanson"], 0)))
    rang = 0
    for i, l in enumerate(lignes):
        if i == 0 or l["_cle"] != lignes[i - 1]["_cle"]:
            rang = i + 1
        l["rang"] = rang
    for l in lignes:
        del l["_cle"]
    return lignes
