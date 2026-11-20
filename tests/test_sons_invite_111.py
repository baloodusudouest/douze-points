"""1.11.0 : les téléphones des invités restent muets. Aucun fichier de frontend/src/invite/ n'importe lib/sons.js,
ni directement ni par un module qu'il importe (graphe des imports parcouru)."""
import re
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "frontend" / "src"
IMPORT = re.compile(r"""(?:import\s[^'"]*?from\s*|import\s*\(\s*|import\s+)['"]([^'"]+)['"]""")


def _resoudre(depuis: Path, cible: str) -> Path | None:
    if cible.startswith("$lib/"):
        chemin = SRC / "lib" / cible[5:]
    elif cible.startswith("."):
        chemin = (depuis.parent / cible).resolve()
    else:
        return None                       # paquet npm : hors de l'appli
    for essai in (chemin, chemin.with_suffix(".js"), chemin / "index.js"):
        if essai.is_file():
            return essai
    return None


def _atteints(depart: Path) -> set[Path]:
    vus, pile = set(), [depart]
    while pile:
        f = pile.pop()
        if f in vus:
            continue
        vus.add(f)
        for cible in IMPORT.findall(f.read_text(encoding="utf-8")):
            r = _resoudre(f, cible)
            if r:
                pile.append(r)
    return vus


def test_invite_n_importe_jamais_les_sons():
    sons = (SRC / "lib" / "sons.js").resolve()
    assert sons.is_file()
    fichiers = sorted((SRC / "invite").glob("*.svelte")) + sorted((SRC / "invite").glob("*.js"))
    assert fichiers
    for f in fichiers:
        atteints = _atteints(f.resolve())
        assert sons not in atteints, f"{f.name} mène à lib/sons.js"


def test_la_regie_importe_les_sons():
    """Le contrôle a du sens : les écrans de la télé, eux, mènent bien à lib/sons.js."""
    sons = (SRC / "lib" / "sons.js").resolve()
    for nom in ("Accueil.svelte", "Devoilement.svelte", "Reglages.svelte"):
        assert sons in _atteints((SRC / "pages" / nom).resolve()), nom
