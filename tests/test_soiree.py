"""La régie et la porte invité : préparer, noter, classer, envoyer, forcer, dévoiler."""
from app import main
from tests.conftest import PRENOMS, Soiree, connecter


def test_sante_publique_sans_aucun_nom(client, soiree):
    soiree.entrer("Aglaé")
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "version": main.__version__, "soirees": 0, "soiree_en_cours": True,
                        "classements_attendus": 4}
    assert not any(p in r.text for p in PRENOMS)


def test_regie_fermee_sans_connexion(client):
    for chemin in ("/api/soirees", "/api/invites", "/api/journal"):
        assert client.get(chemin).status_code == 401


def test_collage_de_la_liste(client):
    lignes = main.lire_collage("1. ; France ; Une artiste ; Un titre\nSuède\tUn groupe\tUn autre titre\n\n3\tItalie")
    assert lignes == [{"pays": "France", "artiste": "Une artiste", "titre": "Un titre"},
                      {"pays": "Suède", "artiste": "Un groupe", "titre": "Un autre titre"},
                      {"pays": "Italie", "artiste": "", "titre": ""}]


def test_lien_avant_ouverture_puis_liste_figee(client):
    s = Soiree(client, ouvrir=False)
    assert client.get(f"/api/soirees/{s.id}").json()["lien"] == f"http://192.0.2.10:8088/invite/{s.jeton}"
    avant = s.etat()
    assert avant["etat"] == "brouillon" and avant["nom"] == "Finale de démonstration" and "chansons" not in avant
    assert client.post(s.url("prenom"), json={"participation_id": s.part["Aglaé"]}).status_code == 409
    client.post(f"/api/soirees/{s.id}/ouvrir")
    assert client.put(f"/api/soirees/{s.id}/chansons", json={"texte": "Pays A"}).status_code == 409
    assert len(s.etat()["chansons"]) == 12


def test_mauvais_jeton_et_soiree_archivee(client, soiree):
    assert client.get("/invite/pas-le-bon/api/etat").status_code == 404
    soiree.tout_le_monde()
    client.post(f"/api/soirees/{soiree.id}/devoiler")
    client.post(f"/api/soirees/{soiree.id}/terminer")
    assert client.get(soiree.url("etat")).status_code == 200
    assert client.post(f"/api/soirees/{soiree.id}/archiver").status_code == 200
    assert client.get(soiree.url("etat")).status_code == 404


def test_un_telephone_un_prenom(client, soiree):
    tel = soiree.entrer("Aglaé")
    # un autre téléphone ne peut pas prendre le même prénom
    assert client.post(soiree.url("prenom"), json={"participation_id": soiree.part["Aglaé"]}).status_code == 409
    # mauvais prénom touché, rien de noté : on en change soi-même, l'ancien redevient libre
    r = client.post(soiree.url("prenom"), headers=tel, json={"participation_id": soiree.part["Barnabé"]})
    assert r.status_code == 200
    soiree.tel["Barnabé"] = {"X-Telephone": r.json()["jeton_telephone"]}
    assert {i["prenom"]: i["pris"] for i in soiree.etat()["invites"]}["Aglaé"] is False
    # une fois qu'on a noté, on ne change plus seul
    soiree.noter("Barnabé", {1: 12})
    r = client.post(soiree.url("prenom"), headers=soiree.tel["Barnabé"], json={"participation_id": soiree.part["Aglaé"]})
    assert r.status_code == 409


def test_liberer_un_prenom_conserve_les_notes(client, soiree):
    soiree.noter("Aglaé", {1: 15.5, 2: 9}, commentaire="Très bien")
    assert client.post(f"/api/soirees/{soiree.id}/liberer", json={"participation_id": soiree.part["Aglaé"]}).status_code == 200
    # l'ancien téléphone n'est plus reconnu
    assert client.put(soiree.url("note"), headers=soiree.tel["Aglaé"],
                      json={"chanson_id": soiree.chansons[2], "valeur": 3}).status_code == 403
    soiree.entrer("Aglaé")
    moi = soiree.etat("Aglaé")["moi"]
    assert moi["notes"][str(soiree.chansons[0])] == {"valeur": 15.5, "commentaire": "Très bien"}
    assert len(moi["notes"]) == 2


def test_notes_demi_points_et_bornes(client, soiree):
    tel = soiree.entrer("Aglaé")
    for valeur, attendu in ((0, 200), (20, 200), (13.5, 200), (13.2, 422), (20.5, 422), (-1, 422), ("douze", 422)):
        r = client.put(soiree.url("note"), headers=tel, json={"chanson_id": soiree.chansons[0], "valeur": valeur})
        assert r.status_code == attendu, valeur
    r = client.put(soiree.url("note"), headers=tel, json={"chanson_id": soiree.chansons[0], "valeur": 10, "commentaire": "x" * 500})
    assert len(r.json()["moi"]["notes"][str(soiree.chansons[0])]["commentaire"]) == 280
    # retirer une note
    r = client.put(soiree.url("note"), headers=tel, json={"chanson_id": soiree.chansons[0], "valeur": None})
    assert r.json()["moi"]["notes"] == {}


def test_classement_suit_les_notes_puis_reste_celui_de_l_invite(client, soiree):
    c = soiree.chansons
    soiree.noter("Aglaé", {1: 10, 2: 18, 3: 10, 4: 5})
    assert soiree.etat("Aglaé")["moi"]["classement"] == [c[1], c[0], c[2], c[3]]
    tel = soiree.tel["Aglaé"]
    # à la main : la 4 (5/20) en tête, contre ses notes
    r = client.put(soiree.url("classement"), headers=tel, json={"ordre": [c[3], c[1], c[0], c[2]]})
    assert r.status_code == 200 and r.json()["moi"]["classement_main"] is True
    # une chanson notée ensuite (15/20) se range au-dessus de la première plus basse, ici la 4 en tête
    soiree.noter("Aglaé", {5: 15})
    moi = soiree.etat("Aglaé")["moi"]
    assert moi["classement"] == [c[4], c[3], c[1], c[0], c[2]]
    assert moi["notes"][str(c[3])]["valeur"] == 5          # les notes n'ont pas bougé
    # un ordre incomplet ou avec une chanson non notée est refusé
    assert client.put(soiree.url("classement"), headers=tel, json={"ordre": [c[3], c[1]]}).status_code == 409
    assert client.put(soiree.url("classement"), headers=tel, json={"ordre": [c[3], c[1], c[0], c[2], c[4], c[5]]}).status_code == 409
    # reclasser d'après mes notes
    r = client.put(soiree.url("classement"), headers=tel, json={"auto": True})
    assert r.json()["moi"]["classement"] == [c[1], c[4], c[0], c[2], c[3]] and r.json()["moi"]["classement_main"] is False


def test_envoyer_modifier_et_pas_encore_renvoye(client, soiree):
    tel = soiree.entrer("Aglaé")
    assert client.post(soiree.url("envoyer"), headers=tel).status_code == 409      # rien de noté
    soiree.noter("Aglaé", {1: 12})
    assert soiree.envoyer("Aglaé").json() == {"ok": True, "tous_envoye": False}
    assert soiree.etat("Aglaé")["moi"]["etat"] == "envoye"
    soiree.noter("Aglaé", {2: 14})                                                 # toucher sa copie la rouvre
    assert soiree.etat("Aglaé")["moi"]["etat"] == "en_cours"
    assert client.get(f"/api/soirees/{soiree.id}").json()["tous_envoye"] is False


def test_devoiler_refuse_tant_que_tous_n_ont_pas_envoye_puis_forcer(client, soiree):
    c = soiree.chansons
    soiree.noter("Aglaé", {i: 20 - i for i in range(1, 13)})
    soiree.envoyer("Aglaé")
    soiree.noter("Barnabé", {3: 18, 1: 12, 2: 6})          # trois chansons, pas envoyé
    soiree.entrer("Célestine")                              # arrivée, rien noté ; Désiré jamais venu
    assert client.post(f"/api/soirees/{soiree.id}/devoiler").status_code == 409
    apercu = client.get(f"/api/soirees/{soiree.id}/forcer").json()
    assert apercu == {"pris": [{"prenom": "Barnabé", "notees": 3}], "ecartes": ["Célestine", "Désiré"]}
    assert client.post(f"/api/soirees/{soiree.id}/devoiler", json={"forcer": True}).status_code == 200
    d = client.get(f"/api/soirees/{soiree.id}/devoilement").json()
    assert d["forcee"] is True and sorted(i["prenom"] for i in d["invites"]) == ["Aglaé", "Barnabé"]
    barnabe = next(i for i in d["invites"] if i["prenom"] == "Barnabé")
    assert barnabe["notees"] == 3 and barnabe["envoye"] is False
    # un classement de trois chansons donne 8, 10, 12 (du plus petit au douze)
    assert [(p["chanson"], p["points"]) for p in barnabe["points"]] == [(c[1], 8), (c[0], 10), (c[2], 12)]
    aglae = next(i for i in d["invites"] if i["prenom"] == "Aglaé")
    assert [p["points"] for p in aglae["points"]] == [1, 2, 3, 4, 5, 6, 7, 8, 10, 12]
    # groupe : chanson 1 = 12 + 10, chanson 3 = 8 + 12, chanson 2 = 10 + 8
    assert [(l["chanson"], l["total"]) for l in d["classement"][:3]] == [(c[0], 22), (c[2], 20), (c[1], 18)]
    etats = {g["prenom"]: g["etat"] for g in client.get(f"/api/soirees/{soiree.id}").json()["participants"]}
    assert etats["Célestine"] == "ecarte" and etats["Désiré"] == "ecarte"


def test_points_geles_et_sauvegarde(client, soiree, tmp_path):
    soiree.tout_le_monde()
    assert client.get(f"/api/soirees/{soiree.id}").json()["tous_envoye"] is True
    assert client.post(f"/api/soirees/{soiree.id}/devoiler", json={"mode": "complet"}).status_code == 200
    assert (tmp_path / "sauvegardes" / f"soiree-{soiree.id}-avant-devoilement.db").is_file()
    avant = client.get(f"/api/soirees/{soiree.id}/devoilement").json()
    assert avant["mode"] == "complet" and len(avant["invites"]) == 4
    # plus personne ne peut noter ni classer : les points ne bougent plus
    tel = soiree.tel["Aglaé"]
    assert client.put(soiree.url("note"), headers=tel, json={"chanson_id": soiree.chansons[0], "valeur": 0}).status_code == 409
    assert client.put(soiree.url("classement"), headers=tel, json={"auto": True}).status_code == 409
    assert client.post(soiree.url("envoyer"), headers=tel).status_code == 409
    # le pas est gardé côté serveur ; relancer le dévoilement est refusé
    client.post(f"/api/soirees/{soiree.id}/pas", json={"pas": 7})
    apres = client.get(f"/api/soirees/{soiree.id}/devoilement").json()
    assert apres["pas"] == 7 and apres["classement"] == avant["classement"] and apres["invites"] == avant["invites"]
    assert client.post(f"/api/soirees/{soiree.id}/devoiler").status_code == 409


def test_une_seule_soiree_en_cours(client, soiree):
    autre = client.post("/api/soirees", json={"concours": "Eurovision Asia", "annee": 2027, "emission": "unique",
                                              "nom": "Autre soirée"}).json()["id"]
    client.put(f"/api/soirees/{autre}/chansons", json={"texte": "Pays A\nPays B"})
    ids = [i["id"] for i in client.get("/api/invites").json()]
    client.put(f"/api/soirees/{autre}/attendus", json={"invites": ids[:2]})
    assert client.post(f"/api/soirees/{autre}/ouvrir").status_code == 409


def test_journal_sans_prenom(client, soiree):
    soiree.noter("Aglaé", {1: 12})
    client.post(f"/api/soirees/{soiree.id}/liberer", json={"participation_id": soiree.part["Aglaé"]})
    texte = client.get("/api/journal").text
    assert "prenom_libere" in texte and not any(p in texte for p in PRENOMS)


def test_qr_code_du_lien(client, soiree):
    r = client.get(f"/api/soirees/{soiree.id}/qr.svg")
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/svg") and b"<svg" in r.content
    client.cookies.clear()
    assert client.get(f"/api/soirees/{soiree.id}/qr.svg").status_code == 401


def test_titre_fabrique_avec_la_ville(client):
    connecter(client)
    assert main.titre_evenement("Eurovision", 2027, "finale", "Burgas") == "Eurovision Burgas 2027, finale"
    assert main.titre_evenement("Eurovision", 2027, "demi1", "") == "Eurovision 2027, première demi-finale"
    assert main.titre_evenement("Eurovision Asia", 2026, "unique", "Bangkok") == "Eurovision Asia Bangkok 2026"
    identifiant = client.post("/api/soirees", json={"concours": "Eurovision", "annee": 2027, "emission": "demi2",
                                                    "ville": " Burgas "}).json()["id"]
    lue = client.get(f"/api/soirees/{identifiant}").json()
    assert lue["nom"] == "Eurovision Burgas 2027, seconde demi-finale" and lue["ville"] == "Burgas"
    # un titre écrit par l'hôte est gardé tel quel
    client.post(f"/api/soirees/{identifiant}/ouvrir")
    autre = client.post("/api/soirees", json={"concours": "Eurovision", "annee": 2027, "emission": "finale",
                                              "ville": "Burgas", "nom": "La grande finale"}).json()["id"]
    assert client.get(f"/api/soirees/{autre}").json()["nom"] == "La grande finale"
