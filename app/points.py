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


def points_du_classement(ordre: list[int], exclues=()) -> dict[int, int]:
    """12, 10, 8… 1 pour les dix premières. Un classement plus court donne les points des rangs qu'il a.
    1.12 : `exclues` (notre pays) gardent leur place dans le classement mais ne reçoivent rien ; leurs points glissent
    à la suivante, comme au concours (le 12 va à la première chanson qui n'est pas exclue)."""
    retenues = [c for c in ordre if c not in set(exclues)]
    return {chanson: BAREME[rang] for rang, chanson in enumerate(retenues[:len(BAREME)])}


def place_aux_notes(moyennes: dict[int, float | None], chanson: int) -> int | None:
    """1.12 : la place qu'une chanson aurait eue d'après la moyenne des notes du groupe (1 = la mieux notée ; à
    moyenne égale, la même place). Sans moyenne : None."""
    m = moyennes.get(chanson)
    if m is None:
        return None
    return 1 + sum(1 for c, v in moyennes.items() if c != chanson and v is not None and v > m)


def rerang(rangs: dict[int, int], exclues) -> dict[int, int]:
    """1.12 : un classement d'invité sans les chansons exclues, renuméroté de 1 à n (pour les comparaisons avec le
    vrai classement, où notre pays n'entre pas)."""
    garde = sorted((r, c) for c, r in rangs.items() if c not in set(exclues) and r is not None)
    return {c: i + 1 for i, (_, c) in enumerate(garde)}


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


# ---------------------------------------------------------------- écarts et affinités (1.3)

AFFINITES_MINIMUM = 3       # sous trois invités, ces rubriques ne disent rien : elles ne sont pas données
COMMUNES_MINIMUM = 3        # deux invités ne se comparent que sur au moins trois chansons notées par les deux


def affinites(notes: dict[int, dict[int, int]], ordres: dict[int, list[int]], points: dict[int, dict[int, int]],
              ordre_passage: dict[int, int]) -> dict | None:
    """Écarts et affinités d'une soirée, à partir des notes (en unités d'ECHELLE), du classement retenu de chacun
    et des points figés. Tout est rendu par identifiants (invités, chansons) ; les notes sont rendues sur 20.

    - clivante / consensuelle : la chanson dont les notes vont du plus loin au plus près (écart entre la plus haute
      et la plus basse note), notée par au moins trois invités ; à écart égal, l'ordre de passage ;
    - proches / eloignes : les deux invités dont les notes se ressemblent le plus / le moins (écart moyen sur les
      chansons notées par les deux, trois au moins) ;
    - severe / genereux : la plus basse et la plus haute moyenne des notes ;
    - coups_de_coeur : un 12 donné à une chanson qui n'a reçu aucun autre point de personne ;
    - contre_note : dans le classement d'un invité, une chanson placée devant une autre mieux notée par lui
      (les trois plus grands écarts de note de la soirée, un par invité au plus).
    Rend None sous trois invités."""
    gens = [g for g in notes if notes[g]]
    if len(gens) < AFFINITES_MINIMUM:
        return None
    sur20 = lambda v: round(v / ECHELLE, 2)

    # chansons : écart entre la plus haute et la plus basse note
    parChanson: dict[int, list[tuple[int, int]]] = {}
    for g in gens:
        for c, v in notes[g].items():
            parChanson.setdefault(c, []).append((v, g))
    candidates = [(c, vs) for c, vs in parChanson.items() if len(vs) >= AFFINITES_MINIMUM]

    def chanson(c, vs):
        haut, bas = max(vs), min(vs)
        return {"chanson": c, "ecart": sur20(haut[0] - bas[0]), "haute": {"invite": haut[1], "note": sur20(haut[0])},
                "basse": {"invite": bas[1], "note": sur20(bas[0])}, "moyenne": sur20(sum(v for v, _ in vs) / len(vs))}

    clivante = consensuelle = None
    if candidates:
        ecart = lambda cv: max(cv[1])[0] - min(cv[1])[0]
        cliv = sorted(candidates, key=lambda cv: (-ecart(cv), ordre_passage.get(cv[0], 0)))[0]
        cons = sorted(candidates, key=lambda cv: (ecart(cv), ordre_passage.get(cv[0], 0)))[0]
        clivante, consensuelle = chanson(*cliv), chanson(*cons)
        if clivante["chanson"] == consensuelle["chanson"]:       # toutes les chansons au même écart : rien à dire
            clivante = consensuelle = None

    # paires d'invités : écart moyen de leurs notes sur les chansons communes
    paires = []
    for i, a in enumerate(gens):
        for b in gens[i + 1:]:
            communes = set(notes[a]) & set(notes[b])
            if len(communes) >= COMMUNES_MINIMUM:
                moyen = sum(abs(notes[a][c] - notes[b][c]) for c in communes) / len(communes)
                paires.append((moyen, a, b, len(communes)))
    paire = lambda p: {"invites": [p[1], p[2]], "ecart_moyen": sur20(p[0]), "communes": p[3]}
    proches = eloignes = None
    if len(paires) >= 2:
        paires.sort(key=lambda p: (p[0], p[1], p[2]))
        proches, eloignes = paire(paires[0]), paire(paires[-1])
        if paires[0][0] == paires[-1][0]:
            proches = eloignes = None

    # sévère et généreux : moyenne des notes
    moyennes = sorted((sum(notes[g].values()) / len(notes[g]), g) for g in gens)
    severe = genereux = None
    if moyennes[0][0] != moyennes[-1][0]:
        severe = {"invite": moyennes[0][1], "moyenne": sur20(moyennes[0][0])}
        genereux = {"invite": moyennes[-1][1], "moyenne": sur20(moyennes[-1][0])}

    # coups de cœur solitaires : un 12, et aucun autre point de personne pour cette chanson
    coups = []
    for g in gens:
        for c, pts in (points.get(g) or {}).items():
            if pts == BAREME[0] and not any(points.get(h, {}).get(c) for h in gens if h != g):
                coups.append({"invite": g, "chanson": c, "note": sur20(notes[g][c]) if c in notes[g] else None})
    coups.sort(key=lambda x: ordre_passage.get(x["chanson"], 0))

    # classées à contre-note : le plus grand écart de note entre une chanson et une autre placée devant elle
    contre = []
    for g in gens:
        ordre = [c for c in ordres.get(g) or [] if c in notes[g]]
        meilleur = None
        for i, devant in enumerate(ordre):
            for derriere in ordre[i + 1:]:
                d = notes[g][derriere] - notes[g][devant]
                if d > 0 and (meilleur is None or d > meilleur[0]):
                    meilleur = (d, devant, derriere)
        if meilleur:
            d, devant, derriere = meilleur
            contre.append({"invite": g, "devant": devant, "derriere": derriere, "note_devant": sur20(notes[g][devant]),
                           "note_derriere": sur20(notes[g][derriere]), "ecart": sur20(d)})
    contre.sort(key=lambda x: (-x["ecart"], x["invite"]))

    return {"clivante": clivante, "consensuelle": consensuelle, "proches": proches, "eloignes": eloignes,
            "severe": severe, "genereux": genereux, "coups_de_coeur": coups, "contre_note": contre[:3]}


# ================================================================ 1.6 : jumeaux de vote
# Tranches d'accord (écart moyen des notes, sur 20) : jamais de pourcentage, qui laisserait deviner les notes de l'autre
# (conseil du 19/11/2026). La dernière tranche n'a pas de borne.
TRANCHES = ((1.0, "Jumeaux parfaits"), (2.0, "Très proches"), (3.5, "Proches"), (None, "Âmes sœurs… de loin"))


def tranche(ecart_moyen: float) -> str:
    for borne, nom in TRANCHES:
        if borne is None or ecart_moyen < borne:
            return nom
    return TRANCHES[-1][1]


def jumeaux(notes: dict[int, dict[int, int]]) -> dict[int, dict]:
    """Le jumeau de vote de chaque invité : l'autre invité dont les notes ressemblent le plus aux siennes (plus petit
    écart moyen sur les chansons notées par les deux, COMMUNES_MINIMUM au moins ; à égalité, le plus petit identifiant).
    Un invité sans assez de chansons en commun avec personne n'a pas de jumeau (absent du résultat).
    Rend {invité: {"jumeau", "ecart_moyen" (sur 20), "communes", "tranche"}}."""
    gens = sorted(g for g in notes if notes[g])
    sortie: dict[int, dict] = {}
    for a in gens:
        meilleur = None
        for b in gens:
            if b == a:
                continue
            communes = set(notes[a]) & set(notes[b])
            if len(communes) < COMMUNES_MINIMUM:
                continue
            moyen = sum(abs(notes[a][c] - notes[b][c]) for c in communes) / len(communes)
            if meilleur is None or (moyen, b) < (meilleur[0], meilleur[1]):
                meilleur = (moyen, b, len(communes))
        if meilleur:
            ecart = round(meilleur[0] / ECHELLE, 2)
            sortie[a] = {"jumeau": meilleur[1], "ecart_moyen": ecart, "communes": meilleur[2], "tranche": tranche(ecart)}
    return sortie


def duos(js: dict[int, dict]) -> list[dict]:
    """Les duos à immortaliser, tirés des jumeaux : chaque paire une seule fois. Réciproques (A a B, B a A) d'abord,
    puis du plus petit écart au plus grand. Rend [{"invites": [a, b], "reciproques", "ecart_moyen", "tranche"}] ;
    pour un duo non réciproque, `a` est celui qui a choisi `b`."""
    vus: dict[tuple[int, int], dict] = {}
    for a in sorted(js):
        b = js[a]["jumeau"]
        cle = (min(a, b), max(a, b))
        if cle in vus:
            continue
        reciproques = js.get(b, {}).get("jumeau") == a
        premier = cle if reciproques else (a, b)
        vus[cle] = {"invites": list(premier), "reciproques": reciproques, "ecart_moyen": js[a]["ecart_moyen"],
                    "tranche": js[a]["tranche"]}
    return sorted(vus.values(), key=lambda d: (not d["reciproques"], d["ecart_moyen"], d["invites"]))
