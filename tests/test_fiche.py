"""Supprimer une soirée ; la fiche de la soirée, son tableau, les vrais votes et la comparaison."""
from tests.conftest import PRENOMS


def devoiler_avec_jury(client, soiree):
    ids = {i["prenom"]: i["id"] for i in client.get("/api/invites").json()}
    for prenom in ("Aglaé", "Barnabé"):
        client.put(f"/api/invites/{ids[prenom]}", json={"jury": True})
    soiree.tout_le_monde()
    assert client.post(f"/api/soirees/{soiree.id}/devoiler", json={"mode": "jury"}).status_code == 200


def test_la_fiche_n_existe_pas_avant_le_devoilement(client, soiree):
    soiree.tout_le_monde()
    assert client.get(f"/api/soirees/{soiree.id}/fiche").status_code == 409
    assert client.get(f"/api/soirees/{soiree.id}/fiche.csv").status_code == 409


def test_fiche_jury_public_et_coherence(client, soiree):
    devoiler_avec_jury(client, soiree)
    f = client.get(f"/api/soirees/{soiree.id}/fiche").json()
    assert f["a_jury"] and [i["prenom"] for i in f["invites"] if i["jury"]] in (["Aglaé", "Barnabé"], ["Barnabé", "Aglaé"])
    assert len(f["chansons"]) == 12 and f["comparaison"] == {"ensemble": None, "jury": None, "public": None}
    for c in f["chansons"]:
        assert c["jury"]["points"] + c["public"]["points"] == c["points"]            # jury + public = total
        assert sum(v["points"] for v in c["invites"].values()) == c["points"]
        assert len(c["invites"]) == 4 and all(v["commentaire"].startswith("Avis de") for v in c["invites"].values())
    assert sorted(c["rang"] for c in f["chansons"])[0] == 1
    # chaque invité a classé ses douze chansons : rangs 1 à 12
    un = f["invites"][0]["id"]
    assert sorted(c["invites"][str(un)]["rang"] for c in f["chansons"]) == list(range(1, 13))


def test_vrais_votes_et_comparaison(client, soiree):
    devoiler_avec_jury(client, soiree)
    f = client.get(f"/api/soirees/{soiree.id}/fiche").json()
    # les vrais votes recopient exactement nos classements : la comparaison doit être parfaite
    resultats = [{"chanson_id": c["id"], "jury": c["jury"]["points"], "public": c["public"]["points"]} for c in f["chansons"]]
    assert client.put(f"/api/soirees/{soiree.id}/officiel", json={"resultats": resultats}).status_code == 200
    apres = client.get(f"/api/soirees/{soiree.id}/fiche").json()
    for partie in ("jury", "public"):
        assert apres["comparaison"][partie]["meme_gagnant"] is True and apres["comparaison"][partie]["chansons"] == 12
    assert all(c["officiel"]["total"] == c["points"] for c in apres["chansons"])
    # une valeur fausse est refusée ; une case vide efface
    assert client.put(f"/api/soirees/{soiree.id}/officiel", json={"resultats": [{"chanson_id": soiree.chansons[0], "jury": "beaucoup"}]}).status_code == 422
    client.put(f"/api/soirees/{soiree.id}/officiel", json={"resultats": [{"chanson_id": soiree.chansons[0], "jury": "", "public": None}]})
    vide = next(c for c in client.get(f"/api/soirees/{soiree.id}/fiche").json()["chansons"] if c["id"] == soiree.chansons[0])
    assert vide["officiel"] == {"jury": None, "public": None, "total": None, "rang_jury": None, "rang_public": None, "rang": None}


def test_tableau_pour_tableur(client, soiree):
    soiree.noter("Aglaé", {1: 12.5}, commentaire="=SOMME(A1)")
    for prenom in PRENOMS[1:]:
        soiree.noter(prenom, {1: 10, 2: 8})
    client.post(f"/api/soirees/{soiree.id}/devoiler", json={"forcer": True})
    r = client.get(f"/api/soirees/{soiree.id}/fiche.csv")
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    texte = r.content.decode("utf-8-sig")
    lignes = texte.split("\r\n")
    assert lignes[0] == "Finale de démonstration" and lignes[1].startswith("Passage;Pays;Artiste;Titre;Moyenne /20")
    assert len(lignes) == 2 + 12 + 1 and "12,5" in lignes[2]           # virgule décimale
    assert "'=SOMME(A1)" in lignes[2]                                   # pas de formule glissée dans le tableur
    assert ";';" not in texte and not texte.rstrip().endswith(";'")   # 1.3.1 : une cellule vide reste vide
    client.cookies.clear()
    assert client.get(f"/api/soirees/{soiree.id}/fiche.csv").status_code == 401


def test_supprimer_une_soiree(client, soiree, tmp_path):
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    client.put(f"/api/soirees/{soiree.id}/image/logo", content=png)
    fichier = tmp_path / "images" / client.get(f"/api/soirees/{soiree.id}").json()["images"]["logo"]
    soiree.tout_le_monde()
    assert client.delete(f"/api/soirees/{soiree.id}").status_code == 409                     # sans confirmation
    assert client.request("DELETE", f"/api/soirees/{soiree.id}", json={"confirmation": True}).status_code == 200
    assert client.get("/api/soirees").json() == [] and client.get(f"/api/soirees/{soiree.id}").status_code == 404
    assert client.get(soiree.url("etat")).status_code == 404 and not fichier.exists()
    assert (tmp_path / "sauvegardes" / f"soiree-{soiree.id}-avant-suppression.db").is_file()
    assert len(client.get("/api/invites").json()) == 4                                      # les invités restent
    assert client.get("/health").json()["soiree_en_cours"] is False
    # on peut en recréer une tout de suite
    assert client.post("/api/soirees", json={"concours": "Eurovision", "annee": 2027, "emission": "finale"}).status_code == 200
