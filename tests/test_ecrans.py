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

from app import main
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
                              attente_connexion=False, adresse=adresse, limite_invite=100000)
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
    p.get_by_role("link", name="Soirée").click()
    p.get_by_role("combobox").first.select_option("Concours de démonstration")
    p.get_by_label("Ville où le concours est organisé").fill("Villeneuve")
    titre = p.get_by_label("Titre de l'évènement")
    assert titre.input_value() == f"Concours de démonstration Villeneuve {__import__('datetime').date.today().year}, finale"
    titre.fill("Finale de démonstration")                        # l'hôte peut écrire le sien
    regie.verifier("pc-1-nouvelle-soiree")
    p.get_by_role("button", name="Créer la soirée").click()
    p.get_by_label("Coller la liste").fill("\n".join(f"{pays} ; Artiste {i} ; Titre {i}" for i, pays in enumerate(PAYS, 1)))
    p.get_by_role("button", name="Enregistrer la liste").click()
    p.get_by_text("Autriche").wait_for()
    for prenom in ("Aglaé", "Barnabé", "Célestine"):
        p.get_by_label("Prénom d'un nouvel invité").fill(prenom)
        p.get_by_role("button", name="Ajouter").click()
        p.get_by_role("button", name=prenom, pressed=True).wait_for()
    for sorte, taille in (("Logo", "400x160"), ("Bannière", "1200x300"), ("Poster", "600x900")):
        p.get_by_label(f"{sorte} : choisir une image").set_input_files(image_de_demo(taille, sorte))
        p.get_by_alt_text(f"{sorte} de l'évènement").wait_for()
    p.get_by_role("button", name="Retirer : Bannière").click()
    p.get_by_role("button", name="Retirer : Bannière").wait_for(state="detached")
    p.get_by_label("Bannière : choisir une image").set_input_files(image_de_demo("1200x300", "Bannière"))
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

    p.get_by_role("button", name="Ouvrir la soirée").click()
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
    t.get_by_role("button", name="Retour à la liste").click()
    t.get_by_role("button", name="Mon classement", exact=True).click()
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
    for k, autre in enumerate(g for g in etat["invites"] if g["prenom"] != "Aglaé"):
        tel = {"X-Telephone": httpx.post(f"{serveur}/invite/{jeton}/api/prenom", json={"participation_id": autre["id"]}).json()["jeton_telephone"]}
        for i, c in enumerate(etat["chansons"]):
            httpx.put(f"{serveur}/invite/{jeton}/api/note", headers=tel,
                      json={"chanson_id": c["id"], "valeur": ((i * (k + 3)) % 41) / 2, "commentaire": "Très scénique" if i == 2 else ""})
        if k == 0:
            httpx.post(f"{serveur}/invite/{jeton}/api/envoyer", headers=tel)

    # ---------------- régie : il en manque un, forcer, puis dévoiler en paysage
    p.get_by_role("button", name="Forcer le dévoilement").click()
    p.get_by_text("son classement du moment sera pris").wait_for()
    regie.verifier("pc-5-forcer")
    p.set_viewport_size(PAYSAGE)
    p.get_by_role("button", name="Dévoiler quand même").click()
    p.get_by_text("Touche l'écran pour commencer.").wait_for()
    regie.verifier("paysage-6-devoilement-depart")
    suivant = p.get_by_role("button", name="Pas suivant")
    vu_douze = False
    for _ in range(40):
        if p.get_by_role("button", name="Terminer").count():
            break
        suivant.click(position={"x": 300, "y": 150})
        if not vu_douze and p.get_by_text("Douze points", exact=True).locator("visible=true").count():
            vu_douze = True
            p.wait_for_timeout(500)
            regie.verifier("paysage-7-douze-points")
    assert vu_douze
    p.get_by_text("Le choix de la soirée").wait_for()
    p.wait_for_timeout(600)
    regie.verifier("paysage-8-podium")

    # le téléphone de l'invité ne sait rien tant que ce n'est pas terminé
    t.get_by_text("Regarde la télé.").wait_for(timeout=10000)
    invite.verifier("tel-8-regarde-la-tele")
    p.get_by_role("button", name="Terminer").click()
    p.set_viewport_size(PC)
    p.get_by_text("Soirée dévoilée").wait_for()
    regie.verifier("pc-9-devoilee")
    t.get_by_role("heading", name="Le classement de la soirée").wait_for(timeout=10000)
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
