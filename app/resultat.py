"""1.9.0 : les calculs du résultat officiel d'une soirée clôturée (journal lu par Gazette pour « Good Evening Europe! »), sans base ni
réseau. Choix de Julien et du conseil du 20/11/2026 (coffre : « Gazette — Dossier — Ajout du 20-11-2026 ») :

- tous les calculs sont faits ici (source unique), Gazette ne fait que la mise en page ;
- écart = en rang seulement ; ex æquo officiel = rang moyen (sauf rang officiel saisi par l'hôte) ;
- « plus proche du vrai résultat » = écart de rang moyen entre le classement personnel de l'invité et le classement
  officiel, sur les chansons classées des deux côtés ; un invité qui n'a pas tout classé en est exclu ; départage :
  le plus de chansons du vrai podium dans son propre podium, puis l'ordre alphabétique ;
- un pays absent du classement officiel est ignoré ;
- demi-finale : l'UER ne publie que les qualifiés le soir même ; on compte les qualifiés trouvés dans le top 10 de
  chacun.

Les identifiants sont ceux des chansons (int) et des participations (int)."""
from __future__ import annotations

VERSION_CONTRAT = 1


def rangs_moyens(points: dict[int, int | None], saisis: dict[int, int | None] | None = None) -> dict[int, float | None]:
    """Rang officiel de chaque chanson d'après ses points ; ex æquo = rang moyen (deux deuxièmes : 2,5 chacun).
    Un rang saisi à la main par l'hôte l'emporte. Sans points ni rang saisi : None (pays ignoré)."""
    saisis = saisis or {}
    connus = sorted((v for v in points.values() if v is not None), reverse=True)
    sortie: dict[int, float | None] = {}
    for c, v in points.items():
        if saisis.get(c) is not None:
            sortie[c] = float(saisis[c])
        elif v is None:
            sortie[c] = None
        else:
            premier = connus.index(v) + 1
            n = connus.count(v)
            sortie[c] = premier + (n - 1) / 2
    return sortie


def sans_exclues(officiel: dict[int, float | None], exclues) -> dict[int, float | None]:
    """1.12 : le classement officiel sans notre pays (qui ne reçoit pas nos points, donc hors de toute comparaison) :
    chaque rang perd une place par pays exclu classé devant lui. Les pays exclus disparaissent du résultat."""
    exclues = set(exclues)
    devant = [officiel[c] for c in exclues if officiel.get(c) is not None]
    return {c: (None if r is None else r - sum(1 for x in devant if x < r))
            for c, r in officiel.items() if c not in exclues}


def ecarts(maison: dict[int, int | None], officiel: dict[int, float | None]) -> dict[int, float]:
    """Écart de rang (valeur absolue) chanson par chanson, sur les chansons classées des deux côtés."""
    return {c: abs(maison[c] - officiel[c]) for c in maison
            if maison.get(c) is not None and officiel.get(c) is not None}


def mieux_et_moins_bien(ecart: dict[int, float], ordre: dict[int, int], n: int = 3) -> tuple[list[int], list[int]]:
    """Les n chansons les mieux devinées (plus petit écart) et les n plus ratées (plus grand écart) ;
    à écart égal, l'ordre de passage. Une chanson n'est jamais dans les deux listes."""
    tri = sorted(ecart, key=lambda c: (ecart[c], ordre.get(c, 0)))
    mieux = tri[:n]
    rates = [c for c in sorted(ecart, key=lambda c: (-ecart[c], ordre.get(c, 0))) if c not in mieux][:n]
    return mieux, rates


def palmares(classements: dict[int, dict[int, int]], officiel: dict[int, float | None], nb_chansons: int,
             prenoms: dict[int, str]) -> list[dict]:
    """Les invités, du plus proche du vrai résultat au plus loin. `classements` : par invité, son rang de chaque
    chanson. Rend [{"invite", "ecart_moyen", "complet", "podium_trouve"}] ; les incomplets en fin de liste."""
    podium_vrai = {c for c, r in officiel.items() if r is not None and r <= 3}
    sortie = []
    for i, rangs in classements.items():
        e = ecarts(rangs, officiel)
        if not e:
            continue
        complet = len(rangs) >= nb_chansons
        podium = {c for c, r in rangs.items() if r <= 3}
        sortie.append({"invite": i, "ecart_moyen": round(sum(e.values()) / len(e), 2), "complet": complet,
                       "podium_trouve": len(podium & podium_vrai)})
    sortie.sort(key=lambda x: (not x["complet"], x["ecart_moyen"], -x["podium_trouve"], prenoms.get(x["invite"], "")))
    return sortie


def demi_finale(maison: dict[int, int | None], qualifies: set[int], classements: dict[int, dict[int, int]],
                moyennes: dict[int, float], prenoms: dict[int, str], top: int = 10) -> dict:
    """Le livret « qualifiés » d'une demi-finale.
    - `flair` : qualifiés trouvés par chaque invité dans son top 10, du meilleur au moins bon ;
    - `notre_top` : notre top 10 (rang maison), chacun qualifié ou non ;
    - `pleure` : nos chansons du top 10 éliminées ; `deteste` : qualifiées que la maison avait classées tout en bas
      (hors de notre top 10, les plus mal classées d'abord, 3 au plus) ;
    - `coup_de_coeur` / `nul_point` : meilleure et pire note moyenne de la maison ;
    - `favoris` : nos 3 favoris parmi les qualifiés (pour la finale)."""
    classees = sorted((c for c in maison if maison[c] is not None), key=lambda c: maison[c])
    notre_top = classees[:top]
    flair = []
    for i, rangs in classements.items():
        sien = {c for c, r in rangs.items() if r <= top}
        flair.append({"invite": i, "trouves": len(sien & qualifies), "sur": len(qualifies)})
    flair.sort(key=lambda x: (-x["trouves"], prenoms.get(x["invite"], "")))
    hors_top = [c for c in reversed(classees) if c in qualifies and c not in notre_top]
    notees = [c for c in moyennes if moyennes[c] is not None]
    return {
        "flair": flair,
        "notre_top": [{"chanson": c, "qualifie": c in qualifies} for c in notre_top],
        "pleure": [c for c in notre_top if c not in qualifies],
        "deteste": hors_top[:3],
        "coup_de_coeur": max(notees, key=lambda c: (moyennes[c], -maison.get(c, 99) if maison.get(c) else 0)) if notees else None,
        "nul_point": min(notees, key=lambda c: (moyennes[c], -(maison.get(c) or 0))) if notees else None,
        "favoris": [c for c in classees if c in qualifies][:3],
    }


def numero(annee: int, concours: str, type_soiree: str) -> str:
    """Le numéro proposé du livret : « 2027 · Eurovision · Finale » (corrigeable dans Gazette)."""
    return f"{annee} · {concours} · {type_soiree}"
