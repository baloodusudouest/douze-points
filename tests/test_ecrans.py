"""Tests d'écran : une soirée entière jouée dans un vrai navigateur, sur PC et sur téléphone.

Un serveur de démonstration est lancé sur un dossier vide (personnes inventées). À chaque écran : aucune
erreur de page, aucun débordement horizontal. Sans interface compilée ou sans navigateur, ces tests sautent.
"""
import os
import shutil
import socket
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn

from app import carnet, main, maison
from app.config import Config

playwright = pytest.importorskip("playwright.sync_api")
STATIQUE = Path(main.__file__).parent / "static"
MOT_DE_PASSE = "mot-de-passe-de-test"
CAPTURES = os.environ.get("CAPTURES")          # dossier où garder des captures, pour relire les écrans
PC = {"width": 1280, "height": 800}
TELEPHONE = {"width": 390, "height": 844}
PAYSAGE = {"width": 844, "height": 390}
PAYS = ["France", "Suède", "Italie", "Ukraine", "Norvège", "Espagne", "Suisse", "Grèce", "Portugal", "Estonie",
        "Finlande", "Islande", "Pologne", "Autriche"]


def faux_anneau(adresse, jeton):
    """Deux sauvegardes inventées : la plus récente au pas actuel, l'autre au quart de point."""
    if "?le=" not in adresse:
        return {"dates": ["2026-11-15", "2026-11-14"]}
    le = adresse.rsplit("=", 1)[1]
    return {"le": le, "version": "1.2.0", "reglages": {"pas_note": 0.5 if le == "2026-11-15" else 0.25}}


@pytest.fixture(scope="module")
def serveur(tmp_path_factory):
    if not (STATIQUE / "index.html").is_file():
        pytest.skip("interface non compilée (cd frontend && npx vite build)")
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    adresse = f"http://127.0.0.1:{port}"
    main.ETAT.clear()
    main.ETAT["cfg"] = Config(password=MOT_DE_PASSE, data=tmp_path_factory.mktemp("demo"), static=STATIQUE,
                              attente_connexion=False, limite_invite=100000,
                              carnet_url="http://carnet.exemple", carnet_jeton="jeton-de-test")
    # l'Anneau est remplacé par des faux : l'annuaire (adresse des invités) et les sauvegardes des réglages
    vrai_annuaire, vrai_anneau = main.ANNUAIRE, main.LIRE_ANNEAU
    main.ANNUAIRE = maison.Annuaire(url="http://anneau.exemple", jeton="jeton-de-test",
                                    lire=lambda: [{"nom": "Douze points", "locale": adresse}])
    main.LIRE_ANNEAU = faux_anneau
    # carnet est remplacé par un faux (personnes inventées), écrit d'après /douze-points/personnes
    vrai_appel, carnet.appeler = carnet.appeler, lambda url, jeton: [
        {"carnet_id": "AAAA-1", "prenom": "Hélène", "nom": "Hélène DUBOIS"},
        {"carnet_id": "AAAA-2", "prenom": "Henri", "nom": "Henri LEROY"}]
    carnet.oublier()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    fil = threading.Thread(target=srv.run, daemon=True)
    fil.start()
    for _ in range(100):
        try:
            if httpx.get(adresse + "/health").status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.05)
    yield adresse
    srv.should_exit = True
    fil.join(timeout=5)
    main.ETAT.clear()
    main.ANNUAIRE, main.LIRE_ANNEAU = vrai_annuaire, vrai_anneau
    carnet.appeler = vrai_appel
    carnet.oublier()


@pytest.fixture(scope="module")
def navigateur():
    with playwright.sync_playwright() as p:
        try:
            chrome = shutil.which("google-chrome")
            nav = p.chromium.launch(executable_path=chrome) if chrome else p.chromium.launch()
        except Exception as e:      # navigateur absent : on saute, on n'échoue pas
            pytest.skip(f"pas de navigateur pour les tests d'écran : {e}")
        yield nav
        nav.close()


def image_de_demo(taille: str, texte: str) -> dict:
    """Une image inventée, fabriquée dans le navigateur de test n'est pas nécessaire : un PNG uni suffit."""
    import struct, zlib
    largeur, hauteur = (int(x) for x in taille.split("x"))
    ligne = b"\x00" + bytes((229, 85, 159)) * largeur
    def bloc(sorte, contenu):
        return struct.pack(">I", len(contenu)) + sorte + contenu + struct.pack(">I", zlib.crc32(sorte + contenu))
    png = (b"\x89PNG\r\n\x1a\n" + bloc(b"IHDR", struct.pack(">IIBBBBB", largeur, hauteur, 8, 2, 0, 0, 0))
           + bloc(b"IDAT", zlib.compress(ligne * hauteur)) + bloc(b"IEND", b""))
    return {"name": f"{texte}.png", "mimeType": "image/png", "buffer": png}


class Ecran:
    """Une page surveillée : erreurs relevées, débordement mesuré, capture si demandée."""

    def __init__(self, navigateur, taille, tactile=False):
        self.contexte = navigateur.new_context(viewport=taille, has_touch=tactile, locale="fr-FR")
        self.page = self.contexte.new_page()
        self.erreurs = []
        self.page.on("pageerror", lambda e: self.erreurs.append(str(e)))

    def autre_page(self, taille):
        """Une seconde page dans le même navigateur (mêmes cookies) : le téléphone de l'hôte connecté à la régie."""
        autre = Ecran.__new__(Ecran)
        autre.contexte, autre.page, autre.erreurs = self.contexte, self.contexte.new_page(), []
        autre.page.set_viewport_size(taille)
        autre.page.on("pageerror", lambda e: autre.erreurs.append(str(e)))
        return autre

    def verifier(self, nom):
        assert self.erreurs == [], (nom, self.erreurs)
        largeur, fenetre = self.page.evaluate("[document.scrollingElement.scrollWidth, window.innerWidth]")
        assert largeur <= fenetre, f"{nom} : débordement horizontal ({largeur} > {fenetre})"
        if CAPTURES:
            self.page.screenshot(path=f"{CAPTURES}/{nom}.png")


def test_une_soiree_entiere(serveur, navigateur):
    # ---------------- régie, sur PC : préparer
    regie = Ecran(navigateur, PC)
    p = regie.page
    p.goto(serveur)
    # l'ouverture : les projecteurs, le 12 qui brille, puis la page ; elle s'efface seule
    ouverture = p.get_by_role("button", name="Passer l'ouverture")
    ouverture.wait_for()
    p.wait_for_timeout(1500)
    regie.verifier("pc-0-ouverture")
    ouverture.wait_for(state="detached", timeout=5000)
    p.reload()                                                   # une fois par session : pas rejouée
    p.get_by_label("Mot de passe").wait_for()
    assert ouverture.count() == 0
    p.get_by_label("Mot de passe").fill(MOT_DE_PASSE)
    p.get_by_role("button", name="Se connecter").click()
    # Réglages : un nouveau concours entre dans la liste, puis sert à créer la soirée
    p.get_by_role("link", name="Réglages").click()
    p.get_by_label("Nom d'un nouveau concours").fill("Concours de démonstration")
    p.get_by_role("button", name="Ajouter").click()
    p.get_by_role("button", name="Retirer Concours de démonstration").wait_for()
    regie.verifier("pc-0-reglages")
    # Connexion : la tuile de carnet, ce qui y est lu, et « Vérifier »
    p.get_by_role("link", name="Connexion").click()
    p.get_by_role("button", name="Vérifier").click()
    p.get_by_text("2 personnes lues.").wait_for()
    regie.verifier("pc-0-connexion")
    p.get_by_role("link", name="Soirée").click()
    p.get_by_role("combobox").first.select_option("Concours de démonstration")
    p.get_by_label("Ville où le concours est organisé").fill("Villeneuve")
    titre = p.get_by_label("Titre de l'évènement")
    assert titre.input_value() == f"Concours de démonstration Villeneuve {__import__('datetime').date.today().year}, finale"
    titre.fill("Finale de démonstration")                        # l'hôte peut écrire le sien
    regie.verifier("pc-1-nouvelle-soiree")
    p.get_by_role("button", name="Créer la soirée").click()
    p.get_by_label("Coller la liste").fill("\n".join(f"{pays} ; Artiste {i} ; Titre {i}" for i, pays in enumerate(PAYS, 1))
                                          + "\nPays de démonstration ; Artiste 15 ; Titre 15")
    p.get_by_role("button", name="Enregistrer la liste").click()
    p.locator("ol").get_by_text("Autriche").wait_for()
    # un nom inconnu : l'alerte le signale, on le relie à un pays, l'alerte disparaît
    alerte = p.get_by_role("alert", name="Pays sans drapeau")
    alerte.wait_for()
    assert alerte.get_by_text("Pays de démonstration").count() == 1
    regie.verifier("pc-2-pays-inconnu")
    alerte.get_by_label("Pays de « Pays de démonstration »").select_option("MT")
    alerte.wait_for(state="detached")
    assert httpx.get(f"{serveur}/health").status_code == 200
    for prenom in ("Aglaé", "Barnabé", "Célestine"):
        p.get_by_label("Prénom d'un nouvel invité").fill(prenom)
        p.get_by_role("button", name="Ajouter").click()
        p.get_by_role("button", name=prenom, pressed=True).wait_for()
    # un invité choisi dans carnet en tapant le début de son prénom : seul son prénom est gardé
    p.get_by_label("Prénom d'un nouvel invité").fill("he")
    p.get_by_role("button", name="Hélène DUBOIS").wait_for()
    regie.verifier("pc-2-carnet")
    p.get_by_role("button", name="Hélène DUBOIS").click()
    p.get_by_role("button", name="Hélène", pressed=True).wait_for()
    assert p.get_by_text("DUBOIS").count() == 0
    for sorte, taille in (("Logo", "400x160"), ("Bannière", "1200x300"), ("Poster", "600x900")):
        p.get_by_label(f"{sorte} : choisir une image").set_input_files(image_de_demo(taille, sorte))
        p.get_by_alt_text(f"{sorte} de l'évènement").wait_for()
    p.get_by_role("button", name="Retirer : Bannière").click()
    p.get_by_role("button", name="Retirer : Bannière").wait_for(state="detached")
    # la bannière revient par glisser-déposer : une image lâchée sur sa case
    banniere = image_de_demo("1200x300", "Bannière")
    donnees = p.evaluate_handle("""(octets) => { const d = new DataTransfer();
        d.items.add(new File([new Uint8Array(octets)], 'banniere.png', { type: 'image/png' })); return d }""", list(banniere["buffer"]))
    case = p.get_by_label("Bannière : déposer une image ici")
    case.dispatch_event("dragover", {"dataTransfer": donnees})
    p.get_by_text("Lâche l'image ici").wait_for()
    case.dispatch_event("drop", {"dataTransfer": donnees})
    p.get_by_alt_text("Bannière de l'évènement").wait_for()
    regie.verifier("pc-2-preparation")

    # ---------------- écran d'accueil : le QR code se charge
    with p.expect_response(lambda r: r.url.endswith("/qr.svg")) as qr:
        p.get_by_role("button", name="Écran d'accueil").click()
    assert qr.value.status == 200
    lien = p.get_by_label("Lien des invités").input_value()
    assert "/invite/" in lien
    p.get_by_alt_text("QR code du lien des invités").wait_for()
    for texte in ("Logo de l'évènement", "Poster de l'évènement"):
        assert p.get_by_alt_text(texte).evaluate("i => i.complete && i.naturalWidth > 0")
    regie.verifier("pc-3-accueil")
    p.set_viewport_size(PAYSAGE)
    regie.verifier("paysage-3-accueil")
    p.set_viewport_size(PC)
    p.get_by_role("button", name="Fermer").click()

    # ---------------- un invité ouvre le lien avant l'ouverture
    invite = Ecran(navigateur, TELEPHONE, tactile=True)
    t = invite.page
    t.goto(lien)
    t.get_by_role("button", name="Passer l'ouverture").click()   # un toucher la passe
    t.get_by_text("Ça commence bientôt.").wait_for()
    for texte in ("Logo de l'évènement", "Poster de l'évènement"):
        t.get_by_alt_text(texte).wait_for()
        assert t.get_by_alt_text(texte).evaluate("i => i.decode().then(() => i.naturalWidth > 0)")
    assert t.locator("img[src*='/image/banniere']").evaluate("i => i.decode().then(() => i.naturalWidth > 0)")
    invite.verifier("tel-1-bientot")

    # démarrer : le 12 éteint et son bouton, les projecteurs, puis l'écran d'accueil sous la scène
    p.get_by_role("button", name="Démarrer la soirée").click()
    p.get_by_role("button", name="Pas encore").wait_for()
    regie.verifier("pc-4-eteint")
    assert httpx.get(lien.replace("/invite/", "/invite/") + "/api/etat").json()["etat"] == "brouillon"     # rien n'est ouvert avant le bouton
    p.get_by_role("button", name="Démarrer la soirée").click()
    p.get_by_role("button", name="Passer l'ouverture").wait_for()
    p.get_by_alt_text("QR code du lien des invités").wait_for(timeout=6000)      # l'accueil arrive seul, après l'animation
    p.get_by_role("img", name="Douze points").first.wait_for()                    # la scène, en bannière
    p.set_viewport_size(PAYSAGE)
    p.wait_for_timeout(400)
    regie.verifier("paysage-4-accueil-scene")
    p.set_viewport_size(PC)
    regie.verifier("pc-4-accueil-scene")
    # l'hôte passe à la notation depuis l'accueil : même page que les invités, avec en plus l'avancement de chacun
    p.get_by_role("link", name="Passer à la notation").click()
    p.get_by_role("heading", name="Qui es-tu ?").wait_for()
    p.get_by_role("button", name="Célestine").click()
    p.get_by_role("button", name="Les invités").click()
    p.get_by_role("list", name="Avancement des invités").wait_for()
    p.get_by_text("0 classements envoyés sur 4").wait_for()
    p.get_by_text("0 / 15 notées").first.wait_for()               # Célestine vient d'arriver, rien de noté
    regie.verifier("pc-4-hote-invites")
    p.get_by_role("link", name="Retour à la régie").click()
    p.get_by_text("classements envoyés").wait_for()                # de retour sur la même soirée
    # rejouer le démarrage depuis l'écran d'accueil : le noir, le bouton, les projecteurs, puis le QR code
    p.get_by_role("button", name="Écran d'accueil").click()
    p.get_by_role("button", name="Rejouer le démarrage").click()
    p.get_by_role("button", name="Pas encore").wait_for()
    p.get_by_role("button", name="Démarrer la soirée").click()
    p.get_by_alt_text("QR code du lien des invités").wait_for(timeout=6000)
    p.get_by_role("button", name="Fermer").click()
    # une seconde soirée se prépare pendant que la première est en cours ; on passe de l'une à l'autre en cliquant
    p.get_by_role("button", name="Toutes les soirées").click()
    p.get_by_role("list", name="Soirées").get_by_role("button", name="Finale de démonstration").wait_for()
    p.get_by_role("button", name="Nouvelle soirée").click()
    p.get_by_label("Ville où le concours est organisé").fill("Villeneuve")
    p.get_by_role("button", name="Créer la soirée").click()
    p.get_by_role("heading", name="Chansons").wait_for()            # créée, elle s'ouvre : c'est sa préparation
    p.get_by_role("button", name="Toutes les soirées").click()
    assert p.get_by_role("list", name="Soirées").get_by_role("button").count() == 2
    regie.verifier("pc-4-plusieurs-soirees")
    p.set_viewport_size(TELEPHONE)
    regie.verifier("tel-4-plusieurs-soirees")
    p.set_viewport_size(PC)
    seconde = p.get_by_role("list", name="Soirées").get_by_role("button").filter(has_text="En préparation")
    seconde.click()
    p.get_by_role("button", name="Supprimer cette soirée").click()
    p.get_by_role("alertdialog").get_by_role("button", name="Supprimer la soirée").click()
    p.get_by_role("list", name="Soirées").get_by_role("button", name="Finale de démonstration").click()
    p.get_by_text("classements envoyés").wait_for()
    regie.verifier("pc-4-soiree-ouverte")

    # ---------------- l'invité : prénom, notes, classement, envoi
    t.get_by_role("heading", name="Qui es-tu ?").wait_for(timeout=10000)      # la page s'ouvre toute seule
    invite.verifier("tel-2-prenom")
    t.get_by_role("button", name="Aglaé").click()
    t.get_by_text("Note chaque chanson sur 20").wait_for()
    invite.verifier("tel-3-chansons")
    t.get_by_role("button", name="France").click()
    for pays, valeur in (("France", 14), ("Suède", 9.5), ("Italie", 17)):
        t.get_by_role("heading", name=pays).wait_for()          # la fiche suivante est bien ouverte
        t.get_by_label("Note sur 20").fill(str(valeur))
        t.get_by_label("Un mot sur cette chanson").fill(f"Avis {valeur}")
        if valeur == 9.5:
            invite.verifier("tel-4-notation")
        t.get_by_role("button", name="Suivante").click()
    t.get_by_role("heading", name="Ukraine").wait_for()
    # ouverte sans rien toucher : « Retour à la liste » ne note pas l'Ukraine ; l'Italie garde sa note
    invite.verifier("tel-4-notation-boutons")
    t.get_by_role("button", name="Retour à la liste").click()
    assert t.get_by_role("button", name="Ukraine").get_by_text("Noter").count() == 1
    t.get_by_role("button", name="Italie").click()
    assert t.get_by_label("Note sur 20").input_value() == "17"
    t.get_by_role("button", name="Retour à la liste").click()
    # le gros bouton des chansons mène au classement ; celui du classement l'envoie
    assert t.get_by_role("button", name="Envoyer mon classement").count() == 0
    t.get_by_text("12 chansons pas encore notées").wait_for()
    t.get_by_role("button", name="Passer au classement").click()
    t.get_by_text("Italie").wait_for()
    lignes = t.locator("ol li")
    assert "Italie" in lignes.nth(0).text_content() and "France" in lignes.nth(1).text_content()
    t.get_by_role("button", name="Descendre Italie").click()                   # contre ses notes : France devant
    t.get_by_role("button", name="Reclasser d'après mes notes").wait_for()
    assert "France" in lignes.nth(0).text_content()
    invite.verifier("tel-5-classement")
    t.get_by_role("button", name="Envoyer mon classement").first.click()
    t.get_by_text("elles ne recevront aucun point de toi").wait_for()
    invite.verifier("tel-6-confirmer")
    t.get_by_role("alertdialog").get_by_role("button", name="Envoyer mon classement").click()
    t.get_by_text("Classement envoyé.").wait_for()
    t.get_by_role("button", name="Les invités").click()
    t.get_by_text("A envoyé").wait_for()
    invite.verifier("tel-7-invites")

    # ---------------- les deux autres passent par l'adresse des invités, sans écran
    jeton = lien.rsplit("/", 1)[1]
    etat = httpx.get(f"{serveur}/invite/{jeton}/api/etat").json()
    # (Aglaé a noté à l'écran ; Célestine, prise par l'hôte, ne note rien et sera écartée)
    for k, autre in enumerate(g for g in etat["invites"] if not g["pris"]):
        tel = {"X-Telephone": httpx.post(f"{serveur}/invite/{jeton}/api/prenom", json={"participation_id": autre["id"]}).json()["jeton_telephone"]}
        for i, c in enumerate(etat["chansons"]):
            httpx.put(f"{serveur}/invite/{jeton}/api/note", headers=tel,
                      json={"chanson_id": c["id"], "valeur": ((i * (k + 3)) % 41) / 2, "commentaire": "Très scénique" if k == 0 else ""})
        if k == 0:
            httpx.post(f"{serveur}/invite/{jeton}/api/envoyer", headers=tel)

    # ---------------- régie : il en manque un, forcer, puis dévoiler en paysage
    p.get_by_role("button", name="Forcer le dévoilement").click()
    p.get_by_text("son classement du moment sera pris").first.wait_for()
    regie.verifier("pc-5-forcer")
    p.set_viewport_size(PAYSAGE)
    p.get_by_role("button", name="Dévoiler quand même").click()
    p.get_by_text("Touche l'écran pour commencer.").wait_for()
    regie.verifier("paysage-6-devoilement-depart")
    # le téléphone de l'invité part de son propre classement, sans les points des autres
    t.get_by_role("list", name="Classement en direct").wait_for(timeout=10000)
    t.get_by_text("Ton classement").wait_for()
    invite.verifier("tel-8-devoilement-depart")
    suivant = p.get_by_role("button", name="Pas suivant")
    suivant.click(position={"x": 300, "y": 150})                         # pas de jury : la première chanson du public
    t.get_by_text("des autres invités").wait_for(timeout=10000)          # le téléphone a suivi la télé
    t.wait_for_timeout(1600)
    invite.verifier("tel-8-devoilement-public")
    p.wait_for_timeout(600)
    regie.verifier("paysage-7-public")
    for _ in range(40):
        if p.get_by_role("button", name="Terminer").count():
            break
        suivant.click(position={"x": 300, "y": 150})
    p.get_by_text("Le podium de la soirée").wait_for()
    assert p.get_by_role("list", name="Podium").locator("li").count() == 3
    p.wait_for_timeout(600)
    regie.verifier("paysage-8-podium")
    # sur le téléphone : le podium de la soirée, et sous lui celui de l'invité
    t.get_by_role("list", name="Podium de la soirée").wait_for(timeout=10000)
    t.get_by_role("list", name="Ton podium").wait_for()
    t.wait_for_timeout(1300)
    invite.verifier("tel-8-podium")
    p.get_by_role("button", name="Terminer").click()
    p.set_viewport_size(PC)
    p.get_by_text("Soirée dévoilée").wait_for()
    regie.verifier("pc-9-devoilee")
    t.get_by_role("heading", name="Le classement de la soirée").wait_for(timeout=10000)
    t.get_by_role("list", name="Ton podium").wait_for()
    t.get_by_text("Très scénique").first.wait_for()
    invite.verifier("tel-9-resultats")

    # ---------------- la régie sur téléphone, puis archiver
    p.set_viewport_size(TELEPHONE)
    regie.verifier("tel-regie-devoilee")
    p.get_by_role("button", name="Archiver").click()
    p.get_by_role("heading", name="Soirées passées").wait_for()
    regie.verifier("tel-regie-nouvelle")
    t.get_by_text("Cette soirée est terminée.").wait_for(timeout=10000)
    invite.verifier("tel-10-termine")


def test_jury_puis_public_fiche_et_suppression(serveur, navigateur):
    """Seconde soirée, préparée par les adresses de la régie : dévoilement « jury puis public », fiche, vrais votes,
    puis suppression. Les invités sont ceux de la première soirée."""
    regie = Ecran(navigateur, PC)
    p = regie.page
    p.goto(serveur)
    p.get_by_role("button", name="Passer l'ouverture").click()
    p.get_by_label("Mot de passe").fill(MOT_DE_PASSE)
    p.get_by_role("button", name="Se connecter").click()
    p.get_by_role("heading", name="Nouvelle soirée").wait_for()

    # Réglages : deux membres du jury, les autres sont le public
    p.get_by_role("link", name="Réglages").click()
    for prenom in ("Aglaé", "Barnabé"):
        p.get_by_role("button", name=f"{prenom} : jury").click()
        p.get_by_role("button", name=f"{prenom} : jury", pressed=True).wait_for()
    p.get_by_role("button", name="Au quart de point (12,25)").click()
    p.get_by_role("button", name="Au quart de point (12,25)", pressed=True).wait_for()
    regie.verifier("pc-10-pas-de-la-note")
    p.get_by_role("button", name="Au demi-point (12,5)").click()
    p.get_by_role("button", name="Au demi-point (12,5)", pressed=True).wait_for()
    regie.verifier("pc-10-jury")

    api = p.request
    soiree = api.post(f"{serveur}/api/soirees", data={"concours": "Eurovision", "annee": 2027, "emission": "finale", "ville": "Villeneuve"}).json()["id"]
    # collée telle qu'un site de fans la donne : « 🇫🇷 France: Artiste - Titre », en un seul morceau
    drapeaux = ["FR", "SE", "IT", "UA", "NO", "ES", "CH", "GR", "PT", "EE", "FI", "IS", "PL", "AT"]
    emoji = lambda code: "".join(chr(0x1F1E6 + ord(x) - 65) for x in code)
    api.put(f"{serveur}/api/soirees/{soiree}/chansons", data={"texte": "\n".join(
        f"{emoji(code)} {pays}: Artiste {i} - Titre {i}" for i, (pays, code) in enumerate(zip(PAYS, drapeaux), 1))})
    lue_chansons = api.get(f"{serveur}/api/soirees/{soiree}").json()["chansons"]
    assert (lue_chansons[0]["pays"], lue_chansons[0]["code_pays"], lue_chansons[0]["artiste"]) == ("France", "FR", "Artiste 1")
    invites = [i["id"] for i in api.get(f"{serveur}/api/invites").json() if i["actif"]]
    api.put(f"{serveur}/api/soirees/{soiree}/attendus", data={"invites": invites})
    for sorte, taille in (("banniere", "1200x300"), ("logo", "400x400"), ("poster", "600x900")):
        r = api.put(f"{serveur}/api/soirees/{soiree}/image/{sorte}", data=image_de_demo(taille, sorte)["buffer"],
                    headers={"Content-Type": "image/png"})
        assert r.ok, r.text()
    api.post(f"{serveur}/api/soirees/{soiree}/ouvrir")
    lue = api.get(f"{serveur}/api/soirees/{soiree}").json()
    assert lue["nom"] == "Eurovision Villeneuve 2027, finale"
    jeton = lue["jeton_invite"]
    for k, g in enumerate(lue["participants"]):
        tel = {"X-Telephone": httpx.post(f"{serveur}/invite/{jeton}/api/prenom", json={"participation_id": g["id"]}).json()["jeton_telephone"]}
        for i, c in enumerate(lue["chansons"]):
            httpx.put(f"{serveur}/invite/{jeton}/api/note", headers=tel,
                      json={"chanson_id": c["id"], "valeur": ((i * (k + 3)) % 41) / 2, "commentaire": "Refrain entêtant" if i == k else ""})
        httpx.post(f"{serveur}/invite/{jeton}/api/envoyer", headers=tel)

    p.get_by_role("link", name="Soirée").click()
    p.get_by_text("le jury d'un coup, puis le public chanson par chanson").wait_for()
    regie.verifier("pc-11-tous-envoye")
    # l'hôte dévoile depuis son téléphone (connecté à la régie, sur la page des invités) ; la télé suit
    hote = regie.autre_page(TELEPHONE)
    h = hote.page
    h.goto(f"{serveur}/invite/{jeton}")
    h.get_by_role("button", name="Passer l'ouverture").click()
    h.get_by_text("Qui es-tu ?").wait_for()                       # l'hôte ne joue pas ici : il mène quand même
    h.get_by_role("button", name="Dévoiler le classement").click()
    h.get_by_label("Commandes de l'hôte").wait_for(timeout=10000)
    hote.verifier("tel-11-hote-depart")
    p.set_viewport_size(PAYSAGE)
    p.get_by_role("button", name="Reprendre le dévoilement").click()
    p.get_by_text("Touche l'écran pour commencer.").wait_for()
    h.get_by_role("button", name="Suivant", exact=True).click()          # le jury d'un coup, mené du téléphone
    h.get_by_text("Les points du jury").first.wait_for()
    p.get_by_role("list", name="Top 5 du jury").wait_for(timeout=10000)  # la télé a suivi
    h.wait_for_timeout(1600)
    hote.verifier("tel-11-hote-jury")
    h.get_by_role("button", name="Revenir").click()
    p.get_by_text("Touche l'écran pour commencer.").wait_for(timeout=10000)
    # un glissement du doigt vers la droite referme l'écran ; un glissement trop court ne fait rien
    def glisser(dx):
        p.evaluate("""(dx) => {
          const cible = document.querySelector('[aria-label="Pas suivant"]').parentElement
          const ev = (type, x) => { const e = new Event(type, { bubbles: true }); const t = [{ clientX: x, clientY: 200 }]
            Object.defineProperty(e, 'touches', { value: t }); Object.defineProperty(e, 'changedTouches', { value: t }); cible.dispatchEvent(e) }
          ev('touchstart', 100); ev('touchend', 100 + dx)
        }""", dx)
    glisser(40)
    assert p.get_by_text("Touche l'écran pour commencer.").count() == 1
    glisser(250)
    p.get_by_text("Touche l'écran pour commencer.").wait_for(state="detached")
    p.get_by_role("button", name="Reprendre le dévoilement").click()
    p.get_by_text("Touche l'écran pour commencer.").wait_for()
    suivant, vus = p.get_by_role("button", name="Pas suivant"), set()
    for _ in range(40):
        if p.get_by_role("button", name="Terminer").count():
            break
        suivant.click(position={"x": 300, "y": 150})
        for phase in ("Les points du public",):
            if phase not in vus and p.get_by_text(phase).count():
                vus.add(phase)
                p.wait_for_timeout(450)
                regie.verifier("paysage-12-" + phase.rsplit(" ", 1)[1])
                if phase == "Les points du public":
                    p.wait_for_timeout(1300)                 # l'addition est faite, la ligne a pris sa place
                    regie.verifier("paysage-12-public-apres")
        if "top" not in vus and p.get_by_role("list", name="Top 5 du jury").count():
            vus.add("top")
            assert "Les points du public" not in vus                   # entre le jury et le public
            assert p.get_by_role("list", name="Top 5 du jury").locator("li").count() == 5
            p.wait_for_timeout(2600)
            regie.verifier("paysage-12-top5-jury")
            # toutes les chansons sont dans le classement, et aucune ligne ne sort de l'écran
            assert p.get_by_role("list", name="Classement du groupe").locator("li").count() == len(PAYS)
            bas = p.get_by_role("list", name="Classement du groupe").locator("li").last.bounding_box()
            assert bas["y"] + bas["height"] <= p.viewport_size["height"]
    assert vus == {"top", "Les points du public"}
    p.get_by_role("list", name="Podium").wait_for()
    p.wait_for_timeout(1800)                                     # le podium est monté, les cotillons tombent
    regie.verifier("paysage-13-podium")
    p.get_by_role("button", name="Revenir").click()               # le classement complet, sur l'écran de la télé
    p.set_viewport_size({"width": 1920, "height": 1080})
    p.wait_for_timeout(1200)
    regie.verifier("tv-13-classement")
    p.set_viewport_size(PAYSAGE)
    p.wait_for_timeout(1200)
    regie.verifier("paysage-13-classement")
    p.get_by_role("button", name="Tout afficher").click()
    p.get_by_role("button", name="Terminer").click()
    p.set_viewport_size(PC)

    # la fiche de la soirée, puis les vrais votes
    p.get_by_role("button", name="Fiche de la soirée").click()
    p.get_by_role("heading", name="Le classement de la soirée").wait_for()
    p.get_by_role("heading", name="Les commentaires").wait_for()
    assert p.get_by_text("Refrain entêtant").count() >= 1
    regie.verifier("pc-14-fiche")
    # à l'impression : la bannière, le logo et le poster de la soirée, et les drapeaux en images (Windows n'a pas d'émoji)
    p.emulate_media(media="print")
    for nom in ("Bannière", "Logo", "Poster"):
        assert p.get_by_alt_text(f"{nom} de l'évènement").evaluate("i => i.decode().then(() => i.naturalWidth > 0)")
    assert p.locator("img.drapeau-image").count() >= len(PAYS)
    if CAPTURES:
        p.screenshot(path=f"{CAPTURES}/pc-14-fiche-impression.png", full_page=True)
    p.emulate_media(media="screen")
    p.get_by_role("button", name="Saisir les vrais votes").click()
    for pays, jury, public in (("France", 120, 80), ("Suède", 90, 150), ("Italie", 60, 20)):
        p.get_by_label(f"{pays} : vrais points du jury").fill(str(jury))
        p.get_by_label(f"{pays} : vrais points du public").fill(str(public))
    regie.verifier("pc-15-vrais-votes")
    p.get_by_role("button", name="Enregistrer les vrais votes").click()
    p.get_by_role("heading", name="Notre soirée face aux vrais votes").wait_for()
    p.get_by_text("Notre jury et le vrai jury").wait_for()
    regie.verifier("pc-16-comparaison")
    p.set_viewport_size(TELEPHONE)
    regie.verifier("tel-16-fiche")
    with p.expect_download() as tableau:
        p.get_by_role("link", name="Télécharger le tableau").click()
    assert tableau.value.suggested_filename.endswith(".csv")
    p.set_viewport_size(PC)
    p.get_by_role("button", name="Retour").click()

    # supprimer la soirée : confirmation, puis plus rien
    p.get_by_role("button", name="Supprimer cette soirée").click()
    regie.verifier("pc-17-supprimer")
    p.get_by_role("alertdialog").get_by_role("button", name="Supprimer la soirée").click()
    p.get_by_role("heading", name="Nouvelle soirée").wait_for()
    assert httpx.get(f"{serveur}/invite/{jeton}/api/etat").status_code == 404
    regie.verifier("pc-18-apres-suppression")


def test_reglages_webhook_et_restaurer(serveur, navigateur):
    """1.2 : le webhook de Home Assistant se règle dans Réglages ; « Restaurer les réglages » relit une sauvegarde
    chez l'Anneau (faux Anneau), montre les différences et les applique. Sur PC et sur iPhone."""
    for taille, nom in ((PC, "pc"), (TELEPHONE, "tel")):
        ecran = Ecran(navigateur, taille, tactile=taille is TELEPHONE)
        p = ecran.page
        p.goto(serveur)
        p.get_by_role("button", name="Passer l'ouverture").click()
        p.get_by_label("Mot de passe").fill(MOT_DE_PASSE)
        p.get_by_role("button", name="Se connecter").click()
        p.get_by_role("heading", name="Nouvelle soirée").wait_for()
        p.get_by_role("link", name="Réglages").click()
        p.get_by_role("button", name="Au demi-point (12,5)", pressed=True).wait_for()

        champ = p.get_by_label("Adresse du webhook de Home Assistant")
        champ.fill("pas une adresse")
        p.get_by_role("button", name="Enregistrer").click()
        p.get_by_role("alert").filter(has_text="http://").wait_for()
        champ.fill("http://ha.exemple:8123/api/webhook/essai")
        p.get_by_role("button", name="Enregistrer").click()
        p.get_by_text("Adresse enregistrée.").wait_for()
        ecran.verifier(f"{nom}-20-webhook")

        p.get_by_role("button", name="Voir les sauvegardes").click()
        p.get_by_text("Rien à changer : les réglages sont déjà ceux du 2026-11-15.").wait_for()
        p.get_by_label("Date de la sauvegarde").select_option("2026-11-14")
        ecarts = p.get_by_role("list", name="Différences avec la sauvegarde")
        ecarts.get_by_text("au quart de point").wait_for()
        assert "Webhook" not in ecarts.inner_text()                  # jamais dans une sauvegarde
        ecran.verifier(f"{nom}-21-restaurer")
        p.get_by_role("button", name="Restaurer ces réglages").click()
        p.get_by_text("Réglages du 2026-11-14 restaurés : Pas de la note.").wait_for()
        p.get_by_role("button", name="Au quart de point (12,25)", pressed=True).wait_for()
        ecran.verifier(f"{nom}-22-restaure")

        # retour à l'état de départ
        p.get_by_role("button", name="Au demi-point (12,5)").click()
        p.get_by_role("button", name="Au demi-point (12,5)", pressed=True).wait_for()
        champ.fill("")
        p.get_by_role("button", name="Enregistrer").click()
        p.get_by_text("Adresse effacée : pas de notification.").wait_for()
        assert httpx.get(f"{serveur}/externe/sauvegarde").status_code == 404     # sans jeton : porte fermée
        ecran.verifier(f"{nom}-23-fin")
        ecran.contexte.close()


def test_grille_papier_saisie_libelle_et_affinites(serveur, navigateur):
    """1.3 : la grille papier à imprimer, « Saisir sa grille » (un onglet au nom de l'invité), la correction d'un
    libellé soirée ouverte, puis les écarts et affinités dans la fiche et sur un téléphone. Sur PC et sur iPhone."""
    regie = Ecran(navigateur, PC)
    p = regie.page
    p.goto(serveur)
    p.get_by_role("button", name="Passer l'ouverture").click()
    p.get_by_label("Mot de passe").fill(MOT_DE_PASSE)
    p.get_by_role("button", name="Se connecter").click()
    p.get_by_role("heading", name="Nouvelle soirée").wait_for()
    api = p.request
    soiree = api.post(f"{serveur}/api/soirees", data={"concours": "Eurovision", "annee": 2027, "emission": "demi1",
                                                       "nom": "Soirée de la grille"}).json()["id"]
    api.put(f"{serveur}/api/soirees/{soiree}/chansons",
            data={"texte": "\n".join(f"{pays} ; Artiste {i} ; Titre {i}" for i, pays in enumerate(PAYS[:8], 1))})
    for prenom in ("Aglaé", "Barnabé", "Célestine"):          # déjà là si la première soirée a tourné (409 : rien)
        api.post(f"{serveur}/api/invites", data={"prenom": prenom})
    invites = [i["id"] for i in api.get(f"{serveur}/api/invites").json() if i["actif"]]
    api.put(f"{serveur}/api/soirees/{soiree}/attendus", data={"invites": invites})
    api.post(f"{serveur}/api/soirees/{soiree}/ouvrir")
    lue = api.get(f"{serveur}/api/soirees/{soiree}").json()
    jeton = lue["jeton_invite"]

    p.reload()
    p.get_by_role("heading", name="Soirée de la grille").wait_for()
    # la grille papier : une page par invité attendu, plus une vierge
    p.get_by_role("button", name="Grille papier").click()
    p.get_by_role("region", name="Grille vierge").wait_for()
    assert p.get_by_role("region", name=f"Grille de {lue['participants'][0]['prenom']}").count() == 1
    assert p.locator("section.page").count() == len(lue["participants"]) + 1
    regie.verifier("pc-30-grille")
    p.emulate_media(media="print")
    regie.verifier("pc-30-grille-impression")
    p.emulate_media(media="screen")
    p.get_by_role("button", name="Retour").click()

    # corriger un libellé, soirée ouverte
    p.get_by_role("button", name="Corriger le libellé : France").click()
    formulaire = p.get_by_role("form", name="Corriger le libellé")
    formulaire.get_by_label("Titre").fill("Titre corrigé")
    regie.verifier("pc-31-libelle")
    formulaire.get_by_role("button", name="Enregistrer").click()
    p.get_by_text("Artiste 1, Titre corrigé").wait_for()
    assert httpx.get(f"{serveur}/invite/{jeton}/api/etat").json()["chansons"][0]["titre"] == "Titre corrigé"

    # saisir la grille d'un invité : un onglet à part, à son nom
    premier = lue["participants"][0]
    with p.context.expect_page() as attente:
        p.get_by_role("button", name="Saisir sa grille").first.click()
    onglet = attente.value
    onglet.set_viewport_size(TELEPHONE)
    onglet.get_by_text(f"Grille papier de {premier['prenom']}").wait_for(timeout=10000)
    assert "saisie=" not in onglet.url                                   # le jeton ne reste pas dans l'adresse
    ecran_saisie = Ecran.__new__(Ecran)
    ecran_saisie.contexte, ecran_saisie.page, ecran_saisie.erreurs = p.context, onglet, []
    ecran_saisie.verifier("tel-32-saisie")
    onglet.close()
    p.get_by_text("Note").first.wait_for()                               # la régie voit l'invité « en train de noter »

    # tout le monde note (l'invité saisi est d'abord libéré), puis dévoilement et fin
    api.post(f"{serveur}/api/soirees/{soiree}/liberer", data={"participation_id": premier["id"]})
    tels = {}
    for k, g in enumerate(lue["participants"]):
        tel = {"X-Telephone": httpx.post(f"{serveur}/invite/{jeton}/api/prenom", json={"participation_id": g["id"]}).json()["jeton_telephone"]}
        tels[g["prenom"]] = tel
        for i, c in enumerate(lue["chansons"]):
            httpx.put(f"{serveur}/invite/{jeton}/api/note", headers=tel, json={"chanson_id": c["id"], "valeur": ((i * (k + 5)) % 41) / 2})
        httpx.post(f"{serveur}/invite/{jeton}/api/envoyer", headers=tel)
    assert api.post(f"{serveur}/api/soirees/{soiree}/devoiler", data={"forcer": True}).ok
    assert api.post(f"{serveur}/api/soirees/{soiree}/terminer").ok
    p.reload()
    p.get_by_role("button", name="Fiche de la soirée").click()
    p.get_by_role("heading", name="Écarts et affinités").wait_for()
    p.get_by_text("La chanson qui divise").wait_for()
    regie.verifier("pc-33-fiche-affinites")

    # sur un téléphone d'invité, après le dévoilement
    tel = Ecran(navigateur, TELEPHONE, tactile=True)
    t = tel.page
    prenom, jeton_tel = next(iter(tels.items()))
    t.goto(f"{serveur}/invite/{jeton}")
    t.get_by_role("button", name="Passer l'ouverture").click()
    t.evaluate("([cle, valeur]) => localStorage.setItem(cle, valeur)", [f"douze-points:{jeton}", jeton_tel["X-Telephone"]])
    t.reload()                                                           # l'ouverture ne se rejoue pas
    t.get_by_role("heading", name="Écarts et affinités").wait_for(timeout=10000)
    t.get_by_role("heading", name="Écarts et affinités").scroll_into_view_if_needed()
    tel.verifier("tel-33-affinites")
    tel.contexte.close()

    # ménage : la soirée de test disparaît
    assert api.delete(f"{serveur}/api/soirees/{soiree}", data={"confirmation": True}).ok
    regie.contexte.close()
