"""1.13 : la liste collée peut porter les vrais votes (jury, public, rang) quand le concours a déjà eu lieu ; ils
remplissent tout de suite les vrais votes de la soirée. Colonnes vides : rien (concours pas encore passé)."""
import pytest
from fastapi import HTTPException

from app import main
from tests.conftest import Soiree

LISTE = """Pays;Artiste;Titre;Jury;Public;Rang
France;Une artiste;Un titre;180;95;3
Suède;Un groupe;Un autre titre;250;1 040;1
Italie;Quelqu'un;Encore un titre;;;
"""


def test_lire_les_vrais_votes():
    l = main.lire_collage(LISTE)
    assert [x["pays"] for x in l] == ["France", "Suède", "Italie"]                  # l'en-tête est sauté
    assert (l[0]["jury"], l[0]["public"], l[0]["rang"]) == (180, 95, 3)
    assert l[1]["public"] == 1040                                                    # « 1 040 » : espace des milliers
    assert (l[2]["jury"], l[2]["public"], l[2]["rang"]) == (None, None, None)
    assert main.lire_collage("Suède\tGroupe\tTitre\t12\t-\t—")[0]["public"] is None
    # la réponse d'une IA, collée avec son bloc de code
    assert [x["pays"] for x in main.lire_collage("```csv\nFrance;A;T;;;\n```")] == ["France"]


@pytest.mark.parametrize("ligne", ["France;A;T;douze;;", "France;A;T;;;0", "France;A;T;;;120", "France;A;T;-3;;"])
def test_nombre_faux_refuse(ligne):
    with pytest.raises(HTTPException) as e:
        main.lire_collage(ligne)
    assert e.value.status_code == 422 and "Ligne 1" in e.value.detail


def test_les_vrais_votes_sont_enregistres(client):
    s = Soiree(client, ouvrir=False)
    r = client.put(f"/api/soirees/{s.id}/chansons", json={"texte": LISTE})
    assert r.status_code == 200, r.text
    ch = r.json()["chansons"]
    assert [(c["officiel_jury"], c["officiel_public"], c["officiel_rang"]) for c in ch] == [
        (180, 95, 3), (250, 1040, 1), (None, None, None)]
    assert client.put(f"/api/soirees/{s.id}/chansons", json={"texte": "France;A;T;x;;"}).status_code == 422


def test_ordre_de_passage_en_tete():
    """1.13.1 : « Ordre;Pays;… » : la liste est rangée d'après l'ordre de passage donné."""
    l = main.lire_collage("Ordre;Pays;Artiste;Titre;Jury;Public;Rang\n2;Suède;B;T;;;\n1;France;A;T;10;20;3\n3;Italie;C;T;;;")
    assert [x["pays"] for x in l] == ["France", "Suède", "Italie"] and l[0]["jury"] == 10
    # un numéro manquant ou en double : l'ordre des lignes, comme avant
    assert [x["pays"] for x in main.lire_collage("2;Suède\n2;France\nItalie")] == ["Suède", "France", "Italie"]
