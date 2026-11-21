"""Tests d'écran : une soirée entière jouée dans un vrai navigateur, sur PC et sur téléphone.

Un serveur de démonstration est lancé sur un dossier vide (personnes inventées). À chaque écran : aucune
erreur de page, aucun débordement horizontal. Sans interface compilée ou sans navigateur, ces tests sautent.
"""
import dataclasses
import os
import re
import shutil
import socket
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn

from app import carnet, immich, main, maison
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
                              carnet_url="http://carnet.exemple", carnet_jeton="jeton-de-test",
                              immich_url="http://immich.exemple", immich_cle="cle-de-test")
    # 1.6 : Immich est remplacé par un faux (tests/test_photos_16.py)
    from tests.test_photos_16 import FauxImmich
    vrai_client = immich.CLIENT
    immich.CLIENT = httpx.Client(transport=httpx.MockTransport(FauxImmich()))
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
    immich.CLIENT = vrai_client


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


# 1.11.0 : un faux AudioContext (aucun son réel dans les tests) ; il compte les contextes créés et les sources
# lancées, et lib/sons.js note chaque son demandé dans window.__DOUZE_POINTS_SONS.
FAUX_AUDIO = """
window.__DOUZE_POINTS_SONS = []
window.__AUDIO = { contextes: 0, sources: 0 }
class FauxParam { constructor(v) { this.value = v } setValueAtTime(v) { this.value = v; return this }
  linearRampToValueAtTime(v) { this.value = v; return this } exponentialRampToValueAtTime(v) { this.value = v; return this }
  setTargetAtTime(v) { this.value = v; return this } cancelScheduledValues() { return this } }
class FauxNoeud { constructor() { this.gain = new FauxParam(1); this.frequency = new FauxParam(440); this.detune = new FauxParam(0)
    this.Q = new FauxParam(1); this.playbackRate = new FauxParam(1); this.type = ''; this.buffer = null; this.loop = false }
  connect(n) { return n } disconnect() {} start() { window.__AUDIO.sources++ } stop() {} }
class FauxContexte {
  constructor() { window.__AUDIO.contextes++; this.state = 'suspended'; this.sampleRate = 8000; this.destination = new FauxNoeud()
    this.t0 = performance.now(); this.onstatechange = null }
  get currentTime() { return (performance.now() - this.t0) / 1000 }
  resume() { this.state = 'running'; if (this.onstatechange) this.onstatechange(); return Promise.resolve() }
  createGain() { return new FauxNoeud() } createOscillator() { return new FauxNoeud() }
  createBufferSource() { return new FauxNoeud() } createBiquadFilter() { return new FauxNoeud() }
  createBuffer(c, n, sr) { const d = new Float32Array(n); return { duration: n / sr, getChannelData: () => d } }
  decodeAudioData() { return Promise.reject(new Error('faux contexte')) }
}
window.AudioContext = FauxContexte
window.webkitAudioContext = FauxContexte
"""


def wav_de_demo() -> bytes:
    """Un vrai petit WAV (0,1 s de silence, 8 kHz, 16 bits), que le navigateur sait lire."""
    import struct
    donnees = b"\x00\x00" * 800
    return (b"RIFF" + struct.pack("<I", 36 + len(donnees)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, 8000, 16000, 2, 16)
            + b"data" + struct.pack("<I", len(donnees)) + donnees)


def sons_demandes(page) -> list:
    return page.evaluate("window.__DOUZE_POINTS_SONS || []")


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
    regie.contexte.add_init_script(FAUX_AUDIO)
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
    # 1.9 : le dévoilement, automatique par défaut, et le temps de chaque étape
    assert p.get_by_role("group", name="Manuel ou automatique").get_by_role("button", name="Automatique").get_attribute("aria-pressed") == "true"
    assert p.get_by_label("Public, en secondes").input_value() == "5"
    regie.verifier("pc-0-reglages")
    # Connexion : la tuile de carnet, ce qui y est lu, et « Vérifier »
    p.get_by_role("link", name="Connexion").click()
    p.get_by_role("button", name="Vérifier").first.click()      # carnet (Immich a sa tuile aussi, 1.6)
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
    # 1.13 : le « ? » du collage propose un prompt pour obtenir la liste avec une IA (titre de la soirée dedans)
    p.get_by_role("button", name="Un prompt pour obtenir la liste des chansons").click()
    bulle = p.get_by_role("dialog", name="Prompt pour obtenir la liste")
    texte = bulle.get_by_label("Texte du prompt").input_value()
    assert "Finale de démonstration" in texte and "Ordre;Pays;Artiste;Titre;Jury;Public;Rang" in texte
    bulle.get_by_role("button", name="Copier").click()
    bulle.get_by_role("status").wait_for()
    regie.verifier("pc-1-prompt-liste")
    bulle.get_by_role("button", name="Fermer").click()
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
    # 1.11.0 : la musique d'attente, et le haut-parleur de la télé (muet gardé par l'écran, bien visible)
    assert "attente" in sons_demandes(p)
    p.get_by_role("button", name="Couper le son").click()
    p.get_by_role("button", name="Remettre le son", pressed=True).wait_for()
    assert p.evaluate("localStorage.getItem('douze-points:muet')") == "1"
    regie.verifier("pc-3-accueil-muet")
    p.get_by_role("button", name="Remettre le son").click()
    p.get_by_role("button", name="Couper le son", pressed=False).wait_for()
    p.set_viewport_size(PAYSAGE)
    regie.verifier("paysage-3-accueil")
    p.set_viewport_size(PC)
    p.get_by_role("button", name="Fermer").click()

    # ---------------- un invité ouvre le lien avant l'ouverture
    invite = Ecran(navigateur, TELEPHONE, tactile=True)
    invite.contexte.add_init_script(FAUX_AUDIO)
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
    # 1.9 : le mode d'emploi (deux téléphones animés), au pas de note de la soirée ; un toucher le referme
    p.get_by_role("button", name="Mode d'emploi").click()
    p.get_by_role("region", name="Mode d'emploi").get_by_role("heading", name="Comment noter").wait_for()       # 1 sur 4 arrivé
    p.wait_for_timeout(1800)
    regie.verifier("pc-4-mode-d-emploi")
    p.get_by_role("button", name="Fermer le mode d'emploi").click()
    p.get_by_role("region", name="Mode d'emploi").wait_for(state="detached")
    # 1.10.3 : petit écran en paysage (iPhone) : le QR code ne recouvre plus les boutons, les téléphones du mode
    # d'emploi sont à l'échelle (rien de coupé, le bouton « Envoyer » sous la liste)
    p.set_viewport_size(PAYSAGE)
    p.wait_for_timeout(300)
    qr = p.get_by_alt_text("QR code du lien des invités").bounding_box()
    for nom in ("Mode d'emploi", "Fermer", "Rejouer le démarrage"):
        b = p.get_by_role("button", name=nom, exact=True).bounding_box()
        assert qr["y"] + qr["height"] <= b["y"] + 1 or qr["x"] + qr["width"] <= b["x"] + 1 or b["x"] + b["width"] <= qr["x"] + 1, nom
        assert b["y"] + b["height"] <= PAYSAGE["height"], nom
    regie.verifier("paysage-4-accueil")
    p.get_by_role("button", name="Mode d'emploi").click()
    region = p.get_by_role("region", name="Mode d'emploi")
    region.wait_for()
    p.wait_for_timeout(700)
    defauts = p.evaluate("""() => {
      const d = []
      for (const tel of document.querySelectorAll('.tel')) {
        const t = tel.getBoundingClientRect()
        for (const el of tel.querySelectorAll('.carte, .voisine, .rangs li, .bouton, .petit, .pays')) {
          const r = el.getBoundingClientRect()
          if (r.right > t.right + 0.5 || r.left < t.left - 0.5) d.push('dépasse : ' + el.className + ' ' + el.textContent.trim().slice(0, 20))
        }
        for (const el of tel.querySelectorAll('.carte .nom, .voisine .nom')) if (el.scrollWidth > el.clientWidth + 1) d.push('coupé : ' + el.textContent.trim().slice(0, 20))
        const liste = tel.querySelector('.rangs'), bouton = tel.querySelector('.bouton')
        if (liste && bouton && liste.getBoundingClientRect().bottom > bouton.getBoundingClientRect().top + 0.5) d.push('bouton sur la liste')
        if (bouton && bouton.getBoundingClientRect().bottom > t.bottom + 0.5) d.push('bouton hors du téléphone')
      }
      return d
    }""")
    assert defauts == [], defauts
    regie.verifier("paysage-4-mode-d-emploi")
    p.get_by_role("button", name="Fermer le mode d'emploi").click()
    region.wait_for(state="detached")
    p.set_viewport_size(PC)
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
            # 1.9 (6b) : la France (14) est juste au-dessus, sa place parmi les chansons déjà notées
            t.get_by_role("dialog").get_by_text("2e de tes 2 chansons").wait_for()
            assert t.get_by_role("dialog").get_by_text("Juste au-dessus").count() == 0      # pas de libellé : la carte
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
    # 1.12 : la France (notre pays) est classée 1re mais ne prend aucun point : le 12 va à l'Italie, 2e
    assert "Notre pays · 0 pt" in lignes.nth(0).text_content() and lignes.nth(0).locator("span.chiffre").first.text_content() == "0"
    assert lignes.nth(1).locator("span.chiffre").first.text_content() == "12"
    assert t.get_by_role("dialog").count() == 0                              # les flèches n'ouvrent pas la feuille
    t.wait_for_timeout(1200)
    invite.verifier("tel-5-classement")
    # 1.11.0 : sous chaque chanson, le début de son commentaire ; un toucher le montre en entier (feuille du bas)
    ligne = t.get_by_role("button", name="Voir le commentaire sur France")
    assert "« Avis 14 »" in ligne.text_content()
    ligne.click()
    feuille = t.get_by_role("dialog", name="Commentaire sur France")
    feuille.get_by_text("« Avis 14 »").wait_for()
    feuille.get_by_text("noté 14 sur 20").wait_for()
    t.wait_for_timeout(400)                                                  # la feuille a fini de monter
    invite.verifier("tel-5-commentaire")
    feuille.get_by_role("button", name="Fermer").click()
    feuille.wait_for(state="detached")
    # puis le glisser par la poignée marche toujours (lignes de 72 px) : l'Italie remonte d'une ligne…
    poignee = t.get_by_role("button", name="Glisser Italie").bounding_box()
    x, y = poignee["x"] + poignee["width"] / 2, poignee["y"] + poignee["height"] / 2
    t.mouse.move(x, y)
    t.mouse.down()
    t.mouse.move(x, y - 40, steps=4)
    t.mouse.move(x, y - 76, steps=4)
    t.mouse.up()
    t.wait_for_timeout(300)
    assert "Italie" in lignes.nth(0).text_content() and "France" in lignes.nth(1).text_content()
    assert t.get_by_role("dialog").count() == 0                              # la poignée n'ouvre pas la feuille
    t.get_by_role("button", name="Descendre Italie").click()                 # … et redescend : l'ordre d'avant
    t.wait_for_timeout(300)
    assert "France" in lignes.nth(0).text_content()
    t.get_by_role("button", name="Envoyer mon classement").first.click()
    t.get_by_text("elles ne recevront aucun point de toi").wait_for()
    invite.verifier("tel-6-confirmer")
    t.get_by_role("alertdialog").get_by_role("button", name="Envoyer mon classement").click()
    t.get_by_text("Classement envoyé.").wait_for()
    t.get_by_role("button", name="Les invités").click()
    t.get_by_text("A envoyé").wait_for()
    invite.verifier("tel-7-invites")
    # 1.6 : l'icône photo, pendant toute la soirée ; la photo part vers l'album (faux Immich)
    t.get_by_role("button", name="Ajouter des photos de la soirée").wait_for()
    t.locator('input[type="file"]').first.set_input_files(image_de_demo("40x30", "photo-soiree"))
    t.get_by_text("Photo envoyée").wait_for()
    invite.verifier("tel-7-photo-envoyee")

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
    # 1.7.0 : le dernier vote du public, joué en accéléré (le rythme réel : lib/dernier.js, testé par node)
    vite = "window.__DOUZE_POINTS_RYTHME = {rapide: 200, lent: 60, pause: 300, final: 100, minimum: 20}"
    p.evaluate(vite)
    t.evaluate(vite)
    compte = p.get_by_role("timer", name=re.compile("La révélation dans"))
    for _ in range(40):
        if compte.count() or p.get_by_text("Le dernier vote du public").count():
            break
        suivant.click(position={"x": 300, "y": 150})
    # 1.11.0 : le compte à rebours (8b) sur la télé ; le téléphone dit « Regardez la télé » (rien du gagnant)
    compte.wait_for(timeout=3000)
    p.get_by_text("La révélation dans…").wait_for()
    t.get_by_text("Regardez la télé").wait_for(timeout=5000)
    assert t.get_by_role("group", name="Le dernier vote du public").count() == 0
    invite.verifier("tel-8-regardez-la-tele")
    p.wait_for_timeout(700)
    regie.verifier("paysage-7-compte-a-rebours")
    suivant.click(position={"x": 300, "y": 150}, force=True)               # pendant le compte : sans effet
    assert compte.count() == 1
    compte.wait_for(state="detached", timeout=8000)
    dernier_tv = p.get_by_role("group", name="Le dernier vote du public")
    dernier_tv.wait_for()
    dernier_tv.get_by_text("Vainqueur", exact=True).wait_for(timeout=10000)          # fin de l'animation sur la télé
    p.wait_for_timeout(500)
    regie.verifier("paysage-7-dernier-vote")
    dernier_tel = t.get_by_role("group", name="Le dernier vote du public")
    dernier_tel.wait_for(timeout=10000)                                    # le téléphone a suivi, et joue aussi
    dernier_tel.get_by_text("Vainqueur", exact=True).wait_for(timeout=10000)
    assert dernier_tel.get_by_text("pour gagner").count() == 0            # « + X » disparaît à la fin
    invite.verifier("tel-8-dernier-vote")
    # recharger au dernier pas : la fin tout de suite, sans rejouer la montée
    t.reload()
    t.get_by_role("group", name="Le dernier vote du public").get_by_text("Vainqueur", exact=True).wait_for(timeout=10000)
    for _ in range(5):
        if p.get_by_role("button", name="Voir les jumeaux de vote").count():
            break
        suivant.click(position={"x": 300, "y": 150})
    p.get_by_text("Le podium de la soirée").wait_for()
    assert p.get_by_role("list", name="Podium").locator("li").count() == 3
    p.wait_for_timeout(600)
    regie.verifier("paysage-8-podium")
    # 1.11.0 : la télé a demandé ses sons (un seul contexte audio) ; le téléphone de l'invité, aucun
    demandes = sons_demandes(p)
    for nom in ("point", "tambour", "fanfare", "applaudissements"):
        assert nom in demandes, (nom, demandes)
    assert p.evaluate("window.__AUDIO.contextes") == 1 and p.evaluate("window.__AUDIO.sources") > 0
    assert sons_demandes(t) == [] and t.evaluate("window.__AUDIO.contextes") == 0
    # sur le téléphone : le podium de la soirée, et sous lui celui de l'invité
    t.get_by_role("list", name="Podium de la soirée").wait_for(timeout=10000)
    t.get_by_role("list", name="Ton podium").wait_for()
    t.get_by_role("region", name="Et notre pays ?").wait_for()                # 1.12 : notre pays, après le podium
    assert "France" not in t.get_by_role("list", name="Podium de la soirée").text_content()
    t.wait_for_timeout(1300)
    invite.verifier("tel-8-podium")
    # 1.8 : le bouton des jumeaux est sous le podium ; en haut ne reste que « Revenir »
    bouton = p.get_by_role("button", name="Voir les jumeaux de vote").bounding_box()
    assert bouton["y"] > p.get_by_role("list", name="Podium").bounding_box()["y"]
    assert p.get_by_role("button", name="Fermer").count() == 0
    # 1.12 : après le temps du podium, la télé passe à « Et notre pays ? » (moyenne du groupe, place aux notes)
    notre = p.get_by_role("region", name="Et notre pays ?")
    notre.wait_for(timeout=25000)
    assert "France" in notre.text_content() and "/20" in notre.text_content()
    p.wait_for_timeout(600)
    regie.verifier("paysage-8-notre-pays")
    p.get_by_role("button", name="Voir les jumeaux de vote").click()
    # 1.6 : la télé passe aux jumeaux de vote, tous les duos d'un coup (tranches, jamais de pourcentage)
    p.get_by_role("heading", name="Les jumeaux de vote").wait_for()
    duos = p.get_by_role("list", name="Duos de jumeaux de vote").locator("li")
    textes = duos.all_text_contents()
    assert len(textes) == 2 and any("Aglaé↓Hélène" in x for x in textes) and not any("%" in x for x in textes), textes
    p.wait_for_timeout(900)
    regie.verifier("paysage-8-jumeaux")
    # le téléphone d'Aglaé : son jumeau, et « Immortaliser » (selfie) ; la photo du duo allume le duo sur la télé
    t.get_by_text("Ton jumeau de vote : Hélène").wait_for(timeout=10000)
    invite.verifier("tel-8-jumeau")
    t.locator('input[capture="user"]').set_input_files(image_de_demo("40x30", "selfie"))
    t.get_by_text("📸 Immortalisés").wait_for(timeout=10000)
    # 1.8 : le selfie passe en grand (polaroïd), puis se range dans la carte du duo
    p.locator("figure.polaroid").get_by_role("img", name="Selfie de Aglaé et Hélène").wait_for(timeout=10000)
    p.wait_for_timeout(900)
    regie.verifier("paysage-8-jumeaux-selfie-en-grand")
    p.locator("figure.polaroid").wait_for(state="detached", timeout=10000)
    duos.get_by_role("img", name="Selfie de Aglaé et Hélène").wait_for()
    p.wait_for_timeout(700)
    regie.verifier("paysage-8-jumeaux-immortalises")
    # 1.6.2 : sans Immich réglé, le jumeau reste affiché, mais ni « Immortaliser » ni l'icône 📷
    cfg_photos = main.ETAT["cfg"]
    main.ETAT["cfg"] = dataclasses.replace(cfg_photos, immich_cle="")
    try:
        t.reload()
        t.get_by_text("Ton jumeau de vote : Hélène").wait_for(timeout=10000)
        assert t.locator('input[capture="user"]').count() == 0
        assert t.get_by_role("button", name="Ajouter des photos de la soirée").count() == 0
        assert t.get_by_text("Les photos vont dans l'album").count() == 0
    finally:
        main.ETAT["cfg"] = cfg_photos
    t.reload()
    t.get_by_text("Ton jumeau de vote : Hélène").wait_for(timeout=10000)
    p.get_by_role("button", name="Fermer").click()
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
    regie.contexte.add_init_script(FAUX_AUDIO)
    p = regie.page
    p.goto(serveur)
    p.get_by_role("button", name="Passer l'ouverture").click()
    p.get_by_label("Mot de passe").fill(MOT_DE_PASSE)
    p.get_by_role("button", name="Se connecter").click()
    p.get_by_role("heading", name="Nouvelle soirée").wait_for()

    # Réglages : deux membres du jury, les autres sont le public ; 1.9 : dévoilement en manuel (tout au toucher)
    p.get_by_role("link", name="Réglages").click()
    p.get_by_role("group", name="Manuel ou automatique").get_by_role("button", name="Manuel").click()
    p.get_by_role("group", name="Manuel ou automatique").get_by_role("button", name="Manuel").and_(p.locator('[aria-pressed="true"]')).wait_for()
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
        if p.get_by_role("button", name="Voir les jumeaux de vote").count():
            break
        p.wait_for_timeout(150)
        if "compte" not in vus and p.get_by_role("timer", name=re.compile("La révélation dans")).count():
            # 1.11.0 : pendant le compte à rebours, le téléphone de l'hôte dit « Regardez la télé », « Suivant » éteint
            vus.add("compte")
            h.get_by_text("Regardez la télé").wait_for(timeout=5000)
            assert h.get_by_role("button", name="Suivant", exact=True).is_disabled()
            hote.verifier("tel-12-hote-regardez-la-tele")
            regie.verifier("paysage-12-compte-a-rebours")
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
            # 1.12 : sauf notre pays (la France, réglage par défaut), qui ne reçoit pas de points
            assert p.get_by_role("list", name="Classement du groupe").locator("li").count() == len(PAYS) - 1
            bas = p.get_by_role("list", name="Classement du groupe").locator("li").last.bounding_box()
            assert bas["y"] + bas["height"] <= p.viewport_size["height"]
    assert vus == {"top", "Les points du public", "compte"}
    # 1.11.0 : sur la télé, le top 5 du jury a sonné ; sur le téléphone de l'hôte (page des invités), aucun son
    assert "point" in sons_demandes(p) or "douze" in sons_demandes(p)
    assert sons_demandes(h) == [] and h.evaluate("window.__AUDIO.contextes") == 0
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
    p.get_by_role("button", name="Voir les jumeaux de vote").click()
    p.get_by_role("heading", name="Les jumeaux de vote").wait_for()
    p.get_by_role("button", name="Fermer").click()
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
    assert p.request.put(f"{serveur}/api/reglages", data={"devoilement_auto": True}).ok      # 1.9 : retour au défaut


def test_reglages_webhook_et_restaurer(serveur, navigateur):
    """1.2 : le webhook de Home Assistant se règle dans Réglages ; « Restaurer les réglages » relit une sauvegarde
    chez l'Anneau (faux Anneau), montre les différences et les applique. Sur PC et sur iPhone."""
    for taille, nom in ((PC, "pc"), (TELEPHONE, "tel")):
        ecran = Ecran(navigateur, taille, tactile=taille is TELEPHONE)
        ecran.contexte.add_init_script(FAUX_AUDIO)
        p = ecran.page
        p.goto(serveur)
        p.get_by_role("button", name="Passer l'ouverture").click()
        p.get_by_label("Mot de passe").fill(MOT_DE_PASSE)
        p.get_by_role("button", name="Se connecter").click()
        p.get_by_role("heading", name="Nouvelle soirée").wait_for()
        p.get_by_role("link", name="Réglages").click()
        p.get_by_role("button", name="Au demi-point (12,5)", pressed=True).wait_for()

        # 1.11.0 : les sons (Réglages › Dévoilement) : interrupteur, volume, les 9 sons, écouter, remplacer, revenir
        sons = p.get_by_role("list", name="Les sons")
        sons.locator("li").nth(8).wait_for()
        assert sons.locator("li").count() == 9
        interrupteur = p.get_by_role("switch", name="Sons sur la télé")
        assert interrupteur.get_attribute("aria-checked") == "true"
        interrupteur.click()
        p.get_by_role("switch", name="Sons sur la télé", checked=False).wait_for()
        interrupteur.click()
        p.get_by_role("switch", name="Sons sur la télé", checked=True).wait_for()
        p.get_by_role("button", name="Écouter : Fanfare du gagnant").click()
        assert "fanfare" in sons_demandes(p)
        fichier = p.get_by_label("Remplacer par un fichier : Fanfare du gagnant")
        fichier.set_input_files(image_de_demo("4x4", "pas-un-son"))           # illisible : refusé avant l'envoi
        p.get_by_text("ne se lit pas dans ce navigateur").wait_for()
        fichier.set_input_files({"name": "fanfare.wav", "mimeType": "audio/wav", "buffer": wav_de_demo()})
        p.get_by_text("Fanfare du gagnant : remplacé par « fanfare.wav ».").wait_for()
        sons.get_by_text("Fichier de l'hôte").wait_for()
        assert httpx.get(f"{serveur}/api/sons").status_code == 401                # derrière la session
        ecran.verifier(f"{nom}-19-sons")
        p.get_by_role("button", name="Revenir au son de l'appli : Fanfare du gagnant").click()
        p.get_by_text("Fanfare du gagnant : de nouveau le son de l'appli.").wait_for()
        assert sons.get_by_text("Fichier de l'hôte").count() == 0

        champ = p.get_by_label("Adresse du webhook de Home Assistant")
        champ.fill("pas une adresse")
        p.get_by_role("button", name="Enregistrer").click()
        p.get_by_role("alert").filter(has_text="http://").wait_for()
        champ.fill("http://ha.exemple:8123/api/webhook/essai")
        p.get_by_role("button", name="Enregistrer").click()
        p.get_by_text("Adresse enregistrée (rien n'est encore envoyé).").wait_for()
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
    # 1.8 : toute la liste d'un coup, une case note et une case mot ; une note hors barème bloque le passage
    grille = onglet.get_by_role("list", name="Grille à recopier")
    assert grille.locator("li").count() == len(lue["chansons"])
    notes_cases = grille.get_by_role("textbox", name="sur 20")
    notes_cases.nth(0).fill("15,5")
    grille.get_by_role("textbox", name="Son mot sur").nth(0).fill("Belle voix")
    notes_cases.nth(1).fill("21")
    notes_cases.nth(2).click()
    onglet.get_by_text("La note va de 0 à 20").first.wait_for()
    notes_cases.nth(1).fill("12")
    notes_cases.nth(2).fill("18")
    onglet.get_by_role("button", name="Passer au classement").click()       # attend les enregistrements
    onglet.get_by_text("Rangé d'après tes notes").wait_for(timeout=10000)
    ecran_saisie.verifier("tel-32-saisie-classement")
    moi = next(g for g in api.get(f"{serveur}/api/soirees/{soiree}").json()["participants"] if g["id"] == premier["id"])
    assert moi["notees"] == 3
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

    # 1.9 : « À traiter » (une demi-finale : les qualifiés), puis la clôture
    p.get_by_role("link", name="À traiter").click()
    p.get_by_role("heading", name="À traiter").wait_for()
    p.get_by_role("button").filter(has_text="Soirée de la grille").first.click()
    qualifies = p.get_by_role("list", name="Qualifiés").get_by_role("checkbox")
    qualifies.nth(0).check()
    qualifies.nth(2).check()
    p.get_by_text("2 qualifiés cochés").wait_for()
    regie.verifier("pc-34-a-traiter-demi")
    p.get_by_role("button", name="Clôturer la soirée").click()
    p.get_by_text("Soirée clôturée (résultat officiel n° 1)").wait_for()
    p.get_by_role("button").filter(has_text="Clôturée le").first.wait_for()
    regie.verifier("pc-34-a-traiter-cloturee")

    # ménage : la soirée de test disparaît
    assert api.delete(f"{serveur}/api/soirees/{soiree}", data={"confirmation": True}).ok
    regie.contexte.close()
