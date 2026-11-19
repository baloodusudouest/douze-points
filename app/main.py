"""Douze points : les soirées de concours de chansons à la maison (FastAPI + interface Svelte compilée).

Deux portes :
- la régie, sous /api/…, derrière le mot de passe commun (cookie de l'appli ou cookie « maison_session ») ;
- la porte invité, sous /invite/<jeton>/api/…, ouverte par le jeton de la soirée (QR code). Elle ne rend
  jamais la note, le commentaire ou le classement d'un autre invité, ni un total, avant la fin du dévoilement.
"""
from __future__ import annotations

import asyncio
import contextlib
import csv
import hmac
import io
import json
import logging
import math
import random
import re
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime
import urllib.error

import segno
from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from . import __version__, carnet, maison
from .auth import COMMUN, DUREE, Sessions, en_https
from .base import base, fichier, preparer, sauvegarder
from .config import APPLI, Config, charger
from .points import ECHELLE, affinites, classement_groupe, classement_par_notes, inserer, points_du_classement

ETAT: dict = {}
PUBLIQUES = ("/api/connexion", "/api/session")
EMISSIONS = ("demi1", "demi2", "finale", "unique")
LIBELLES = {"demi1": "première demi-finale", "demi2": "seconde demi-finale", "finale": "finale", "unique": ""}
IMAGES = ("logo", "banniere", "poster")


def titre_evenement(concours: str, annee: int, emission: str, ville: str = "") -> str:
    """Le titre fabriqué quand l'hôte n'en écrit pas : « Eurovision Burgas 2027, finale ».
    La même règle est écrite dans frontend/src/lib/pays.js (titreEvenement) : les deux vont ensemble."""
    debut = " ".join(x for x in (concours, ville, str(annee)) if x)
    return f"{debut}, {LIBELLES[emission]}" if LIBELLES.get(emission) else debut
IMAGE_MAX = 6 * 1024 * 1024
# Formats acceptés, reconnus à leurs premiers octets (jamais au nom du fichier). Pas de SVG : il peut porter du script.
SIGNATURES = ((b"\x89PNG\r\n\x1a\n", "png", "image/png"), (b"\xff\xd8\xff", "jpg", "image/jpeg"))
COMMENTAIRE_MAX = 280


def maintenant() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def cfg() -> Config:
    return ETAT["cfg"]


ANNUAIRE = maison.Annuaire()
SANS_ADRESSE = ("Aucune adresse pour les invités : l'Anneau ne répond pas, ou sa tuile « Douze points » n'a pas "
                "d'adresse locale. Pas de QR code ni de lien tant qu'elle manque.")


def adresse() -> str:
    """Adresse de Douze points pour les téléphones des invités (QR code, lien), lue dans l'Anneau (tuile
    « Douze points »). Toujours l'adresse locale : les invités ne sont pas sur Tailscale, même quand la régie est
    ouverte par lui. 1.2 : plus de variable de repli ; sans Anneau, pas de QR code (message clair)."""
    return ANNUAIRE.adresse("Douze points", prive=False)


# ================================================================ réglages d'usage (1.2)
# `pas_note` reste dans la table `reglage` de la base (1.0) ; les autres sont dans /data/reglages.json
# (maison.Reglages) : repris une fois de l'ancienne variable de la stack au premier démarrage, puis seul l'écran
# Réglages fait foi.
REGLAGES_DEFAUTS = {"ha_webhook": ""}
REGLAGES_VARIABLES = {"ha_webhook": "DOUZE_POINTS_HA_WEBHOOK"}
# Jamais dans une sauvegarde (maison.est_secret l'écarte déjà ; la liste le dit en clair).
EXCLUS_SAUVEGARDE = ("ha_webhook",)
PAS_NOTE = {1.0: "1", 0.5: "0.5", 0.25: "0.25"}
LIRE_ANNEAU = None          # tests : un faux Anneau pour maison.lire_sauvegarde (argument lire=)
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _lire_generation(c: Config) -> int:
    try:
        return int((c.data / "session_generation").read_text().strip())
    except (OSError, ValueError):
        return 0


@asynccontextmanager
async def cycle(app: FastAPI):
    c = ETAT.get("cfg") or charger()
    c.data.mkdir(parents=True, exist_ok=True)
    preparer(c.data)
    reglages = maison.Reglages(c.data / "reglages.json", REGLAGES_DEFAUTS, REGLAGES_VARIABLES)
    if reglages.repris:
        with base(c.data) as cx:
            for k in reglages.repris:      # le nom de la variable seulement, jamais sa valeur
                journal(cx, "reglage_repris", k, {"variable": REGLAGES_VARIABLES[k]})
    ETAT.update(cfg=c, reglages=reglages, sessions=Sessions(APPLI, c.password, _lire_generation(c)),
                debits=defaultdict(deque))
    # 1.4 (socle 0.9.0) : copie cohérente de douze-points.db chaque nuit (heure de Paris, maison.HEURES_COPIE)
    # vers <data>/copies ; c'est la seule tâche de fond de l'appli (tâche « copie-des-bases » dans /health).
    copie = asyncio.create_task(maison.planifier_copie(APPLI, [fichier(c.data)], c.data / "copies",
                                                       maison.HEURES_COPIE[APPLI]))
    envois = asyncio.create_task(_boucle_carnet())     # 1.5 : nouvel essai des soirées pas encore reçues par carnet
    try:
        yield
    finally:
        for tache in (copie, envois):     # arrêt propre des boucles
            tache.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await tache


app = FastAPI(title=APPLI, version=__version__, lifespan=cycle, docs_url=None, redoc_url=None)


# ================================================================ sécurité

@app.middleware("http")
async def garde(request: Request, appel):
    chemin = request.url.path
    if chemin.startswith("/api/"):
        if chemin not in PUBLIQUES and not ETAT["sessions"].connecte(request.cookies):
            return JSONResponse({"detail": "Connexion nécessaire."}, status_code=401)
    elif chemin.startswith("/invite/") and "/api/" in chemin:
        # Porte invité : un plafond de demandes par téléphone (ou par adresse), sur une minute glissante
        # 1.3.3 : plafond par téléphone (en-tête X-Telephone, ou adresse) ET plafond par adresse (20 téléphones) :
        # changer d'en-tête à chaque demande ne contourne plus la limite ; la table est purgée
        adresse = request.client.host if request.client else "?"
        debits, t, limite = ETAT["debits"], time.monotonic(), cfg().limite_invite
        if len(debits) > 2000:
            for k in [k for k, f in debits.items() if not f or t - f[-1] > 60]:
                del debits[k]
        files = [(debits[("tel", request.headers.get("x-telephone") or adresse)], limite),
                 (debits[("adresse", adresse)], limite * 20)]
        for file, plafond in files:
            while file and t - file[0] > 60:
                file.popleft()
            if len(file) >= plafond:
                return JSONResponse({"detail": "Trop de demandes : attends un instant."}, status_code=429)
        for file, _ in files:
            file.append(t)
    reponse = await appel(request)
    if "/api/" in chemin:
        reponse.headers["Cache-Control"] = "no-store"
    return reponse


def journal(cx, action: str, cible: str = "", detail: dict | None = None) -> None:
    """Jamais de prénom ni de note dans le journal : des numéros seulement."""
    cx.execute("INSERT INTO journal(date, action, cible, detail) VALUES(?,?,?,?)",
               (maintenant(), action, cible, json.dumps(detail or {}, ensure_ascii=False)))


# ================================================================ public

@app.get("/health")
def sante(request: Request):
    """Pour la tuile de l'Anneau : des nombres, aucun nom. 1.4 : + version_socle, taches, copie_base (socle 0.9.0) ;
    messages d'erreur des tâches seulement avec le jeton commun MAISON_JETON ou une session."""
    with base(cfg().data) as cx:
        archivees = cx.execute("SELECT COUNT(*) FROM soiree WHERE etat IN ('devoilee','archivee')").fetchone()[0]
        en_cours = cx.execute("SELECT id FROM soiree WHERE etat IN ('ouverte','devoilement') ORDER BY id DESC").fetchone()
        attendus = cx.execute("SELECT COUNT(*) FROM participation WHERE soiree_id=? AND etat IN ('attendu','en_cours')",
                              (en_cours["id"],)).fetchone()[0] if en_cours else 0
    sessions = ETAT.get("sessions")
    return {"ok": True, "version": __version__, "soirees": archivees,
            "soiree_en_cours": bool(en_cours), "classements_attendus": attendus,
            **maison.sante(request, jeton_commun=maison.jetons(),
                           session_ok=bool(sessions and sessions.connecte(request.cookies)))}


# ================================================================ connexion (régie)

@app.get("/api/session")
def session(request: Request):
    return {"connecte": ETAT["sessions"].connecte(request.cookies), "version": __version__,
            "adresse": adresse(), "notification": bool(ETAT["reglages"].get("ha_webhook")),
            "carnet": carnet.regle(cfg())}


@app.post("/api/connexion")
async def connexion(request: Request, corps: dict = Body(...)):
    s = ETAT["sessions"]
    if cfg().attente_connexion:
        await asyncio.sleep(s.attente())
    if not s.verifier_mot_de_passe(str(corps.get("mot_de_passe", ""))):
        raise HTTPException(401, "Mot de passe incorrect.")
    r = JSONResponse({"ok": True})
    r.set_cookie(s.cookie, s.creer(), max_age=DUREE, httponly=True, samesite="strict", secure=en_https(request))
    return r


@app.post("/api/deconnexion")
def deconnexion():
    s = ETAT["sessions"]
    s.generation += 1
    try:
        (cfg().data / "session_generation").write_text(str(s.generation))
    except OSError:
        pass  # volume en lecture seule : la déconnexion vaut jusqu'au prochain redémarrage
    r = JSONResponse({"ok": True})
    r.delete_cookie(s.cookie)
    r.delete_cookie(COMMUN)      # « Se déconnecter » ferme aussi la connexion commune
    return r


# ================================================================ lectures communes

def _soiree(cx, soiree_id: int):
    s = cx.execute("SELECT * FROM soiree WHERE id=?", (soiree_id,)).fetchone()
    if not s:
        raise HTTPException(404, "Soirée inconnue.")
    return s


def _chansons(cx, soiree_id: int) -> list[dict]:
    return [dict(r) for r in cx.execute(
        "SELECT id, ordre, pays, code_pays, artiste, titre, officiel_jury, officiel_public FROM chanson "
        "WHERE soiree_id=? ORDER BY ordre", (soiree_id,))]


def _notes(cx, participation_id: int) -> dict[int, int]:
    return {r["chanson_id"]: r["valeur"] for r in
            cx.execute("SELECT chanson_id, valeur FROM note WHERE participation_id=?", (participation_id,))}


def _ordre(cx, participation, chansons: list[dict]) -> list[int]:
    """Le classement d'un invité : le sien s'il a déplacé une chanson, sinon celui de ses notes."""
    notes = _notes(cx, participation["id"])
    passage = {c["id"]: c["ordre"] for c in chansons}
    if not participation["classement_main"]:
        return classement_par_notes(notes, passage)
    ordre = [r["chanson_id"] for r in cx.execute(
        "SELECT chanson_id FROM classement WHERE participation_id=? ORDER BY rang", (participation["id"],))
        if r["chanson_id"] in notes]
    for c in classement_par_notes(notes, passage):      # filet : une chanson notée absente de l'ordre
        ordre = inserer(ordre, c, notes)
    return ordre


def _ecrire_ordre(cx, participation_id: int, ordre: list[int]) -> None:
    cx.execute("DELETE FROM classement WHERE participation_id=?", (participation_id,))
    cx.executemany("INSERT INTO classement(participation_id, chanson_id, rang) VALUES(?,?,?)",
                   [(participation_id, c, i + 1) for i, c in enumerate(ordre)])


def _participants(cx, soiree_id: int) -> list[dict]:
    """Qui est attendu, arrivé, a envoyé : jamais de note."""
    lignes = cx.execute(
        "SELECT p.id, i.prenom, i.jury, p.etat, p.jeton_telephone IS NOT NULL AS pris, "
        "(SELECT COUNT(*) FROM note n WHERE n.participation_id=p.id) AS notees "
        "FROM participation p JOIN invite i ON i.id=p.invite_id WHERE p.soiree_id=? ORDER BY i.prenom COLLATE NOCASE",
        (soiree_id,))
    return [{"id": r["id"], "prenom": r["prenom"], "jury": bool(r["jury"]), "etat": r["etat"], "pris": bool(r["pris"]),
             "notees": r["notees"]} for r in lignes]


def _images(s) -> dict:
    """Pour chaque image de l'évènement : absente (None), ou le nom de son fichier (il change à chaque dépôt,
    ce qui sert de version pour que les écrans rechargent la nouvelle)."""
    return {sorte: s[sorte] for sorte in IMAGES}


def _resume(s) -> dict:
    return {"id": s["id"], "concours": s["concours"], "annee": s["annee"], "emission": s["emission"],
            "date": s["date"], "nom": s["nom"], "ville": s["ville"], "etat": s["etat"], "images": _images(s)}


def _format_image(contenu: bytes):
    if contenu[:4] == b"RIFF" and contenu[8:12] == b"WEBP":
        return "webp", "image/webp"
    for debut, extension, type_mime in SIGNATURES:
        if contenu.startswith(debut):
            return extension, type_mime
    return None


def _servir_image(s, sorte: str):
    if sorte not in IMAGES or not s[sorte]:
        raise HTTPException(404, "Pas d'image.")
    fichier = cfg().data / "images" / s[sorte]
    if not fichier.is_file():
        raise HTTPException(404, "Pas d'image.")
    return FileResponse(fichier, headers={"Cache-Control": "private, max-age=86400", "X-Content-Type-Options": "nosniff"})


# ================================================================ régie : invités

@app.get("/api/invites")
def invites():
    with base(cfg().data) as cx:
        return [{"id": r["id"], "prenom": r["prenom"], "actif": r["actif"], "jury": bool(r["jury"])}
                for r in cx.execute("SELECT id, prenom, actif, jury FROM invite ORDER BY prenom COLLATE NOCASE")]


def _prenom(corps: dict) -> str:
    prenom = " ".join(str(corps.get("prenom", "")).split())[:40]
    if not prenom:
        raise HTTPException(422, "Il faut un prénom.")
    return prenom


@app.post("/api/invites")
def invite_ajouter(corps: dict = Body(...)):
    """Un prénom tapé à la main, ou une personne choisie dans carnet (`carnet_id`). De carnet, Douze points ne
    garde que le prénom (avec l'initiale du nom si le prénom est déjà pris) et le numéro de la fiche."""
    carnet_id = str(corps.get("carnet_id") or "")
    with base(cfg().data) as cx:
        pris = lambda p: cx.execute("SELECT 1 FROM invite WHERE prenom=? COLLATE NOCASE AND actif=1", (p,)).fetchone()
        if carnet_id:
            deja = cx.execute("SELECT id FROM invite WHERE carnet_id=?", (carnet_id,)).fetchone()
            if deja:        # déjà venu : le même invité, remis dans la liste s'il en avait été retiré
                cx.execute("UPDATE invite SET actif=1 WHERE id=?", (deja["id"],))
                return {"id": deja["id"]}
            personne = next((p for p in _carnet(carnet.personnes) if p["carnet_id"] == carnet_id), None)
            if not personne:
                raise HTTPException(404, "Cette personne n'est plus dans carnet.")
            prenom = personne["prenom"][:40]
            if pris(prenom) and carnet.initiale(personne):
                prenom = f"{prenom} {carnet.initiale(personne)}."[:40]
        else:
            prenom = _prenom(corps)
        if pris(prenom):
            raise HTTPException(409, "Ce prénom est déjà dans la liste : ajoute une initiale pour les distinguer.")
        personne_id = (personne.get("personne_id") or None) if carnet_id else None    # 1.5 : identifiant maison
        return {"id": cx.execute("INSERT INTO invite(prenom, carnet_id, personne_id, cree_le) VALUES(?,?,?,?)",
                                 (prenom, carnet_id or None, personne_id, maintenant())).lastrowid}


def _carnet(lecture, *suite):
    """Un appel à carnet, avec une réponse claire s'il ne répond pas."""
    try:
        return lecture(cfg(), *suite)
    except Exception as e:      # carnet arrêté, jeton refusé, réseau : la soirée se prépare quand même à la main
        raise HTTPException(502, f"carnet ne répond pas ({type(e).__name__}) : ajoute le prénom à la main.")


@app.get("/api/carnet/personnes")
def carnet_personnes(q: str = ""):
    """Les personnes de carnet dont le prénom ou le nom commence par ce qui est tapé (huit au plus)."""
    if not carnet.regle(cfg()):
        return {"relie": False, "personnes": []}
    return {"relie": True, "personnes": _carnet(carnet.chercher, q[:60])}


@app.get("/api/services")
def services(verifier: bool = False):
    """Écran Connexion : une tuile par service extérieur. « Vérifier » relit carnet pour de bon, sans rien écrire."""
    c = {"id": "carnet", "nom": "carnet", "regle": carnet.regle(cfg()), "ok": None, "detail": "",
         "lit": "Le prénom et le nom des fiches, pour choisir les invités en tapant leur nom. Rien d'autre.",
         "ecrit": "Rien.", "reglage": "DOUZE_POINTS_CARNET_URL, et le jeton commun MAISON_JETON"}
    if c["regle"] and verifier:
        try:
            c.update(ok=True, detail=f"{len(carnet.personnes(cfg(), frais=True))} personnes lues.")
        except Exception as e:
            c.update(ok=False, detail=f"carnet ne répond pas ({type(e).__name__}).")
    return [c]


@app.put("/api/invites/{invite_id}")
def invite_modifier(invite_id: int, corps: dict = Body(...)):
    with base(cfg().data) as cx:
        if "prenom" in corps:
            cx.execute("UPDATE invite SET prenom=? WHERE id=?", (_prenom(corps), invite_id))
        if "jury" in corps:       # membre du jury ; les autres sont le public
            cx.execute("UPDATE invite SET jury=? WHERE id=?", (1 if corps["jury"] else 0, invite_id))
        if "actif" in corps:      # retiré de la liste, gardé dans les archives
            cx.execute("UPDATE invite SET actif=? WHERE id=?", (1 if corps["actif"] else 0, invite_id))
    return {"ok": True}


# ================================================================ régie : concours

LIBELLE_PAS = {"1": "au point près", "0.5": "par demi-points", "0.25": "par quarts de point"}


def _reglage(cx, cle: str) -> str:
    r = cx.execute("SELECT valeur FROM reglage WHERE cle=?", (cle,)).fetchone()
    return r["valeur"] if r else ""


def tous_reglages(cx) -> dict:
    return {"pas_note": float(_reglage(cx, "pas_note")), **ETAT["reglages"].tout()}


def _pas_note(v) -> str:
    if isinstance(v, bool):
        raise HTTPException(400, "Le pas de la note est 1, 0,5 ou 0,25.")
    try:
        cle_pas = PAS_NOTE.get(float(v))
    except (TypeError, ValueError):
        cle_pas = None
    if cle_pas is None:
        raise HTTPException(400, "Le pas de la note est 1, 0,5 ou 0,25.")
    return cle_pas


def _ha_webhook(v) -> str:
    if v is None:
        return ""
    if not isinstance(v, str):
        raise HTTPException(400, "L'adresse du webhook de Home Assistant est un texte.")
    v = v.strip()
    if v and not re.match(r"^https?://\S+$", v):
        raise HTTPException(400, "L'adresse du webhook de Home Assistant commence par http:// ou https://, ou reste vide.")
    return v


def changer_reglages(cx, corps: dict) -> dict:
    """Vérifie tout avant d'écrire (une valeur fausse : 400, rien n'est changé). Clés inconnues ignorées.
    Le journal garde la valeur du pas, jamais l'adresse du webhook."""
    if not isinstance(corps, dict):
        raise HTTPException(400, "Réglages attendus sous forme d'objet.")
    pas = _pas_note(corps["pas_note"]) if "pas_note" in corps else None
    propres = {}
    if "ha_webhook" in corps:
        propres["ha_webhook"] = _ha_webhook(corps["ha_webhook"])
    if pas is not None:
        cx.execute("INSERT INTO reglage(cle, valeur) VALUES('pas_note', ?) "
                   "ON CONFLICT(cle) DO UPDATE SET valeur=excluded.valeur", (pas,))
        journal(cx, "reglage", "pas_note", {"valeur": pas})
    if propres:
        try:
            ETAT["reglages"].changer(propres)
        except (TypeError, ValueError) as e:
            raise HTTPException(400, f"Réglage refusé : {e}.")
        for k, v in propres.items():
            journal(cx, "reglage", k, {"rempli": bool(v)})
    return tous_reglages(cx)


@app.get("/api/reglages")
def reglages_lire():
    with base(cfg().data) as cx:
        return tous_reglages(cx)


@app.put("/api/reglages")
def reglages_ecrire(corps: dict = Body(...)):
    """`pas_note` : 1, 0.5 ou 0.25 (les notes déjà données restent telles quelles ; les suivantes suivent le pas).
    `ha_webhook` : adresse du webhook de Home Assistant, ou vide."""
    with base(cfg().data) as cx:
        return changer_reglages(cx, corps)


# ---------------------------------------------------------------- restaurer (sauvegardes gardées par l'Anneau)

def _lire_anneau(le: str = "") -> dict:
    """Une sauvegarde de Douze points chez l'Anneau ; erreurs traduites en messages clairs (404 / 503)."""
    try:
        r = maison.lire_sauvegarde(APPLI, le, lire=LIRE_ANNEAU)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise HTTPException(404, "L'Anneau n'a pas de sauvegarde de Douze points"
                                     + (f" pour le {le}." if le else "."))
        raise HTTPException(503, f"L'Anneau a refusé la demande ({e.code}) : rien n'est restauré.")
    except Exception as e:      # Anneau arrêté, réseau, réponse illisible : jamais d'erreur de page
        raise HTTPException(503, f"L'Anneau ne répond pas ({type(e).__name__}) : rien n'est restauré.")
    if not isinstance(r, dict):
        raise HTTPException(503, "L'Anneau a répondu quelque chose d'illisible : rien n'est restauré.")
    return r


def _date(le) -> str:
    le = str(le or "").strip()
    if not DATE.match(le):
        raise HTTPException(400, "Date attendue sous la forme AAAA-MM-JJ.")
    return le


def _sauves(le: str) -> dict:
    r = _lire_anneau(le)
    if not isinstance(r.get("reglages"), dict):
        raise HTTPException(404, f"L'Anneau n'a pas de réglages de Douze points pour le {le}.")
    return r


@app.get("/api/restaurer")
def restaurer_lire(le: str = ""):
    """Sans date : les jours sauvegardés chez l'Anneau. Avec une date : ce qui changerait (avant → sauvegardé)."""
    if not le:
        dates = _lire_anneau().get("dates") or []
        if not dates:
            raise HTTPException(404, "L'Anneau n'a encore aucune sauvegarde de Douze points.")
        return {"dates": [str(d) for d in dates]}
    le = _date(le)
    r = _sauves(le)
    with base(cfg().data) as cx:
        actuels = tous_reglages(cx)
    return {"le": le, "version": r.get("version", ""),
            "differences": maison.differences(actuels, r["reglages"], EXCLUS_SAUVEGARDE)}


@app.post("/api/restaurer")
def restaurer(corps: dict = Body(...)):
    """Applique les réglages sauvegardés ce jour-là qui diffèrent d'aujourd'hui (réglages seulement : ni soirée,
    ni invité, ni note). Permis même en lecture seule : rien n'est écrit chez un autre service."""
    le = _date(corps.get("le") if isinstance(corps, dict) else "")
    r = _sauves(le)
    with base(cfg().data) as cx:
        diffs = maison.differences(tous_reglages(cx), r["reglages"], EXCLUS_SAUVEGARDE)
        reglages = changer_reglages(cx, {d["cle"]: d["sauve"] for d in diffs}) if diffs else tous_reglages(cx)
        journal(cx, "reglages_restaures", le, {"cles": [d["cle"] for d in diffs]})
    return {"le": le, "restaures": [d["cle"] for d in diffs], "reglages": reglages}


@app.get("/api/concours")
def concours_lire():
    """La liste des concours proposés à la création d'une soirée, avec le nombre de soirées de chacun."""
    with base(cfg().data) as cx:
        return [dict(r) for r in cx.execute(
            "SELECT c.id, c.nom, c.actif, (SELECT COUNT(*) FROM soiree s WHERE s.concours=c.nom) AS soirees "
            "FROM concours c ORDER BY c.nom COLLATE NOCASE")]


@app.post("/api/concours")
def concours_ajouter(corps: dict = Body(...)):
    nom = " ".join(str(corps.get("nom", "")).split())[:60]
    if not nom:
        raise HTTPException(422, "Il faut un nom de concours.")
    with base(cfg().data) as cx:
        existant = cx.execute("SELECT id, actif FROM concours WHERE nom=?", (nom,)).fetchone()
        if existant and existant["actif"]:
            raise HTTPException(409, "Ce concours est déjà dans la liste.")
        if existant:        # retiré auparavant : il revient
            cx.execute("UPDATE concours SET actif=1, nom=? WHERE id=?", (nom, existant["id"]))
            return {"id": existant["id"]}
        return {"id": cx.execute("INSERT INTO concours(nom) VALUES(?)", (nom,)).lastrowid}


@app.delete("/api/concours/{concours_id}")
def concours_retirer(concours_id: int):
    """Retiré de la liste proposée. Les soirées déjà créées gardent son nom ; sans soirée, il est effacé."""
    with base(cfg().data) as cx:
        c = cx.execute("SELECT nom FROM concours WHERE id=?", (concours_id,)).fetchone()
        if not c:
            raise HTTPException(404, "Concours inconnu.")
        if cx.execute("SELECT COUNT(*) FROM concours WHERE actif=1 AND id<>?", (concours_id,)).fetchone()[0] == 0:
            raise HTTPException(409, "Il faut garder au moins un concours dans la liste.")
        if cx.execute("SELECT 1 FROM soiree WHERE concours=?", (c["nom"],)).fetchone():
            cx.execute("UPDATE concours SET actif=0 WHERE id=?", (concours_id,))
        else:
            cx.execute("DELETE FROM concours WHERE id=?", (concours_id,))
    return {"ok": True}


# ================================================================ régie : soirées

@app.get("/api/soirees")
def soirees():
    with base(cfg().data) as cx:
        return [_resume(s) for s in cx.execute("SELECT * FROM soiree ORDER BY id DESC")]


@app.post("/api/soirees")
def soiree_creer(corps: dict = Body(...)):
    concours, emission = str(corps.get("concours", "")), str(corps.get("emission", ""))
    nom = " ".join(str(corps.get("nom", "")).split())[:80]
    ville = " ".join(str(corps.get("ville", "")).split())[:60]
    try:
        annee = int(corps.get("annee"))
    except (TypeError, ValueError):
        raise HTTPException(422, "Il faut une année.")
    if emission not in EMISSIONS or not 1956 <= annee <= 2100:
        raise HTTPException(422, "Concours, année et émission sont nécessaires.")
    with base(cfg().data) as cx:
        connu = cx.execute("SELECT nom FROM concours WHERE nom=? AND actif=1", (concours,)).fetchone()
        if not connu:
            raise HTTPException(422, "Ce concours n'est pas dans la liste : ajoute-le dans les Réglages.")
        concours = connu["nom"]
        nom = nom or titre_evenement(concours, annee, emission, ville)[:80]      # sans titre écrit : il est fabriqué
        soiree_id = cx.execute(
            "INSERT INTO soiree(concours, annee, emission, date, nom, ville, jeton_invite, cree_le) VALUES(?,?,?,?,?,?,?,?)",
            (concours, annee, emission, str(corps.get("date") or "")[:10] or None, nom, ville or None,
             secrets.token_urlsafe(18), maintenant())).lastrowid
        journal(cx, "soiree_creee", str(soiree_id))
    return {"id": soiree_id}


@app.get("/api/soirees/{soiree_id}")
def soiree_lire(soiree_id: int):
    """La régie ne voit aucune note ni aucun classement avant le dévoilement : l'hôte note lui aussi."""
    with base(cfg().data) as cx:
        s = _soiree(cx, soiree_id)
        gens = _participants(cx, soiree_id)
        attendus = [g for g in gens if g["etat"] != "ecarte"]
        return {**_resume(s), "jeton_invite": s["jeton_invite"], "chanson_en_cours": s["chanson_en_cours"],
                "mode_devoilement": s["mode_devoilement"], "pas_devoilement": s["pas_devoilement"],
                "forcee": bool(s["forcee"]), "chansons": _chansons(cx, soiree_id), "participants": gens,
                "tous_envoye": bool(attendus) and all(g["etat"] == "envoye" for g in attendus),
                "lien": f"{lien}/invite/{s['jeton_invite']}" if (lien := adresse()) else ""}


@app.put("/api/soirees/{soiree_id}/image/{sorte}")
async def image_deposer(soiree_id: int, sorte: str, request: Request):
    """Logo, bannière ou poster de l'évènement, déposés par l'hôte. Gardés dans /data/images, jamais dans le dépôt."""
    if sorte not in IMAGES:
        raise HTTPException(404, "Image inconnue.")
    contenu = await request.body()
    if len(contenu) > IMAGE_MAX:
        raise HTTPException(413, "Image trop lourde : 6 Mo au plus.")
    trouve = _format_image(contenu)
    if not trouve:
        raise HTTPException(415, "Format non reconnu : il faut une image PNG, JPEG ou WebP.")
    dossier = cfg().data / "images"
    dossier.mkdir(parents=True, exist_ok=True)
    nom = f"soiree-{soiree_id}-{sorte}-{secrets.token_hex(4)}.{trouve[0]}"
    with base(cfg().data) as cx:
        ancien = _soiree(cx, soiree_id)[sorte]
        (dossier / nom).write_bytes(contenu)
        cx.execute(f"UPDATE soiree SET {sorte}=? WHERE id=?", (nom, soiree_id))
    if ancien:
        (dossier / ancien).unlink(missing_ok=True)
    return {"images": {sorte: nom}}


@app.delete("/api/soirees/{soiree_id}/image/{sorte}")
def image_retirer(soiree_id: int, sorte: str):
    if sorte not in IMAGES:
        raise HTTPException(404, "Image inconnue.")
    with base(cfg().data) as cx:
        ancien = _soiree(cx, soiree_id)[sorte]
        cx.execute(f"UPDATE soiree SET {sorte}=NULL WHERE id=?", (soiree_id,))
    if ancien:
        (cfg().data / "images" / ancien).unlink(missing_ok=True)
    return {"ok": True}


@app.get("/api/soirees/{soiree_id}/image/{sorte}")
def image_lire(soiree_id: int, sorte: str):
    with base(cfg().data) as cx:
        s = _soiree(cx, soiree_id)
    return _servir_image(s, sorte)


@app.get("/api/soirees/{soiree_id}/qr.svg")
def qr(soiree_id: int):
    """Le QR code du lien des invités, pour l'écran d'accueil. Clair sur fond sombre, bord compris."""
    with base(cfg().data) as cx:
        s = _soiree(cx, soiree_id)
    lien = adresse()
    if not lien:
        raise HTTPException(409, SANS_ADRESSE)
    tampon = io.BytesIO()
    segno.make(f"{lien}/invite/{s['jeton_invite']}", error="m").save(
        tampon, kind="svg", scale=10, border=3, dark="#151311", light="#f2ece2", xmldecl=False)
    return Response(tampon.getvalue(), media_type="image/svg+xml")


def cle_pays(nom: str) -> str:
    """Un nom de pays sans accents ni majuscules (même règle que l'interface, frontend/src/lib/pays.js)."""
    import unicodedata
    simple = "".join(c for c in unicodedata.normalize("NFD", nom.casefold()) if unicodedata.category(c) != "Mn")
    return simple.replace("'", " ").replace("\u2019", " ").strip()


DRAPEAU_EN_TETE = re.compile("^\\s*([\U0001F1E6-\U0001F1FF]{2})\\s*")


def lire_collage(texte: str) -> list[dict]:
    """Une chanson par ligne ; champs séparés par une tabulation ou un point-virgule : pays, artiste, titre.
    Un numéro de passage en tête de ligne est accepté et ignoré : c'est l'ordre des lignes qui compte.
    0.8 : une ligne copiée d'un site de fans, « 🇧🇹 Bhutan: Artiste - Titre », est aussi comprise : le drapeau
    donne le code du pays, puis le pays avant « : », l'artiste et le titre de part et d'autre de « - »."""
    chansons = []
    for ligne in texte.splitlines():
        champs = [c.strip() for c in (ligne.split("\t") if "\t" in ligne else ligne.split(";"))]
        if champs and champs[0].rstrip(".").isdigit():
            champs = champs[1:]
        champs = [c for c in champs] + ["", "", ""]
        pays, artiste, titre, code = champs[0], champs[1], champs[2], ""
        m = DRAPEAU_EN_TETE.match(pays)
        if m:
            code = "".join(chr(ord(x) - 0x1F1E6 + 65) for x in m.group(1))
            pays = pays[m.end():]
        if not artiste and not titre and ": " in pays:
            pays, suite = pays.split(": ", 1)
            artiste, _, titre = suite.partition(" - ")
        if pays.strip():
            chansons.append({"pays": pays.strip(), "artiste": artiste.strip(), "titre": titre.strip(), "code_pays": code})
    return chansons


@app.put("/api/soirees/{soiree_id}/chansons")
def chansons_remplacer(soiree_id: int, corps: dict = Body(...)):
    """Brouillon : la liste entière, dans l'ordre de passage (lignes, ou texte collé)."""
    chansons = lire_collage(str(corps["texte"])) if "texte" in corps else list(corps.get("chansons") or [])
    with base(cfg().data) as cx:      # les noms de pays déjà reliés par l'hôte reçoivent leur drapeau
        alias = {r["cle"]: r["code"] for r in cx.execute("SELECT cle, code FROM alias_pays")}
    for c in chansons:
        if not c.get("code_pays") and cle_pays(str(c.get("pays", ""))) in alias:
            c["code_pays"] = alias[cle_pays(str(c["pays"]))]
    if len(chansons) > 60:
        raise HTTPException(422, "Soixante chansons au plus.")
    with base(cfg().data) as cx:
        if _soiree(cx, soiree_id)["etat"] != "brouillon":
            raise HTTPException(409, "La soirée est ouverte : seuls les libellés se corrigent encore.")
        cx.execute("DELETE FROM chanson WHERE soiree_id=?", (soiree_id,))
        for i, c in enumerate(chansons):
            pays = " ".join(str(c.get("pays", "")).split())[:60]
            if not pays:
                raise HTTPException(422, f"Ligne {i + 1} : il manque le pays.")
            cx.execute("INSERT INTO chanson(soiree_id, ordre, pays, code_pays, artiste, titre) VALUES(?,?,?,?,?,?)",
                       (soiree_id, i + 1, pays, str(c.get("code_pays") or "")[:2].upper() or None,
                        str(c.get("artiste") or "").strip()[:120], str(c.get("titre") or "").strip()[:120]))
        return {"chansons": _chansons(cx, soiree_id)}


@app.put("/api/chansons/{chanson_id}")
def chanson_corriger(chanson_id: int, corps: dict = Body(...)):
    """Corriger un libellé, à tout moment. L'ordre ne change plus une fois la soirée ouverte."""
    if "pays" in corps and not " ".join(str(corps["pays"] or "").split()):
        raise HTTPException(422, "Il faut le pays.")
    with base(cfg().data) as cx:
        if not cx.execute("SELECT 1 FROM chanson WHERE id=?", (chanson_id,)).fetchone():
            raise HTTPException(404, "Chanson inconnue.")
        for champ, taille in (("pays", 60), ("artiste", 120), ("titre", 120), ("code_pays", 2)):
            if champ in corps:
                cx.execute(f"UPDATE chanson SET {champ}=? WHERE id=?", (str(corps[champ] or "").strip()[:taille], chanson_id))
    return {"ok": True}


@app.put("/api/chansons/{chanson_id}/pays")
def chanson_pays(chanson_id: int, corps: dict = Body(...)):
    """Le drapeau d'une chanson dont le pays n'est pas reconnu, choisi par l'hôte. Avec `retenir`, le nom du pays
    (`nom`) est relié à ce code pour les prochaines listes collées. Possible à tout moment, même soirée ouverte."""
    code = str(corps.get("code") or "").strip().upper()
    if not re.fullmatch(r"[A-Z]{2}", code):
        raise HTTPException(422, "Il faut le code du pays, deux lettres (FR, KR…).")
    with base(cfg().data) as cx:
        if not cx.execute("SELECT 1 FROM chanson WHERE id=?", (chanson_id,)).fetchone():
            raise HTTPException(404, "Chanson inconnue.")
        cx.execute("UPDATE chanson SET code_pays=? WHERE id=?", (code, chanson_id))
        nom = cle_pays(str(corps.get("nom") or ""))
        if corps.get("retenir") and nom:
            cx.execute("INSERT INTO alias_pays(cle, code) VALUES(?,?) ON CONFLICT(cle) DO UPDATE SET code=excluded.code", (nom, code))
    return {"ok": True}


@app.get("/api/alias-pays")
def alias_pays():
    with base(cfg().data) as cx:
        return [dict(r) for r in cx.execute("SELECT cle, code FROM alias_pays ORDER BY cle")]


@app.delete("/api/alias-pays/{cle}")
def alias_pays_retirer(cle: str):
    with base(cfg().data) as cx:
        cx.execute("DELETE FROM alias_pays WHERE cle=?", (cle,))
    return {"ok": True}


@app.put("/api/soirees/{soiree_id}/attendus")
def attendus(soiree_id: int, corps: dict = Body(...)):
    """Les invités attendus. Retirer quelqu'un qui a déjà noté est refusé : on l'écarte au dévoilement."""
    voulus = {int(i) for i in corps.get("invites") or []}
    with base(cfg().data) as cx:
        if _soiree(cx, soiree_id)["etat"] not in ("brouillon", "ouverte"):
            raise HTTPException(409, "Le dévoilement a commencé.")
        actuels = {r["invite_id"]: r["id"] for r in
                   cx.execute("SELECT id, invite_id FROM participation WHERE soiree_id=?", (soiree_id,))}
        for invite_id in voulus - set(actuels):
            cx.execute("INSERT INTO participation(soiree_id, invite_id) VALUES(?,?)", (soiree_id, invite_id))
        for invite_id in set(actuels) - voulus:
            if cx.execute("SELECT 1 FROM note WHERE participation_id=?", (actuels[invite_id],)).fetchone():
                raise HTTPException(409, "Cet invité a déjà noté : il ne peut plus être retiré.")
            cx.execute("DELETE FROM participation WHERE id=?", (actuels[invite_id],))
        return {"participants": _participants(cx, soiree_id)}


@app.post("/api/soirees/{soiree_id}/ouvrir")
def soiree_ouvrir(soiree_id: int):
    with base(cfg().data) as cx:
        s = _soiree(cx, soiree_id)
        if s["etat"] != "brouillon":
            raise HTTPException(409, "La soirée est déjà ouverte.")
        if not _chansons(cx, soiree_id) or not _participants(cx, soiree_id):
            raise HTTPException(409, "Il faut au moins une chanson et un invité attendu.")
        cx.execute("UPDATE soiree SET etat='ouverte', ouverte_le=? WHERE id=?", (maintenant(), soiree_id))
        journal(cx, "soiree_ouverte", str(soiree_id))
    return {"ok": True}


@app.post("/api/soirees/{soiree_id}/chanson-en-cours")
def chanson_en_cours(soiree_id: int, corps: dict = Body(...)):
    """Facultatif : l'hôte peut tenir la chanson en cours, ou ne jamais s'en servir."""
    with base(cfg().data) as cx:
        chanson = corps.get("chanson_id")
        if chanson is not None and not cx.execute("SELECT 1 FROM chanson WHERE id=? AND soiree_id=?",
                                                  (chanson, soiree_id)).fetchone():
            raise HTTPException(404, "Chanson inconnue.")
        cx.execute("UPDATE soiree SET chanson_en_cours=? WHERE id=?", (chanson, soiree_id))
    return {"ok": True}


@app.post("/api/soirees/{soiree_id}/liberer")
def liberer(soiree_id: int, corps: dict = Body(...)):
    """Téléphone changé, navigation privée, mauvais prénom touché : le prénom redevient libre.
    Les notes et le classement restent, et reviennent au téléphone qui reprend le prénom."""
    with base(cfg().data) as cx:
        cx.execute("UPDATE participation SET jeton_telephone=NULL WHERE id=? AND soiree_id=?",
                   (int(corps.get("participation_id", 0)), soiree_id))
        journal(cx, "prenom_libere", str(soiree_id), {"participation": corps.get("participation_id")})
    return {"ok": True}


@app.post("/api/soirees/{soiree_id}/saisie")
def saisie_papier(soiree_id: int, corps: dict = Body(...)):
    """1.3 : grille papier. L'hôte recopie la grille d'un invité : il reçoit un lien vers l'écran de notation au nom
    de cet invité (un jeton de téléphone neuf, dans la partie « # » du lien : jamais envoyé au serveur par le
    navigateur, jamais écrit dans le journal). Le téléphone qui tenait ce prénom le perd ; notes et classement
    déjà faits restent. Cette adresse ne rend aucune note : la régie ne voit rien avant le dévoilement."""
    with base(cfg().data) as cx:
        s = _soiree(cx, soiree_id)
        if s["etat"] != "ouverte":
            raise HTTPException(409, "La saisie d'une grille papier se fait pendant la soirée ouverte.")
        p = cx.execute("SELECT * FROM participation WHERE id=? AND soiree_id=?",
                       (int(corps.get("participation_id", 0)), soiree_id)).fetchone()
        if not p or p["etat"] == "ecarte":
            raise HTTPException(404, "Invité inconnu pour cette soirée.")
        jeton = secrets.token_urlsafe(24)
        cx.execute("UPDATE participation SET jeton_telephone=?, arrive_le=COALESCE(arrive_le, ?), "
                   "etat=CASE WHEN etat='attendu' THEN 'en_cours' ELSE etat END WHERE id=?",
                   (jeton, maintenant(), p["id"]))
        journal(cx, "saisie_papier", str(soiree_id), {"participation": p["id"], "telephone_remplace": bool(p["jeton_telephone"])})
    return {"lien": f"/invite/{s['jeton_invite']}#saisie={jeton}"}


# ================================================================ régie : dévoilement

def _retenus(cx, soiree_id: int, forcer: bool) -> tuple[list, list]:
    """Qui compte, qui est écarté. Sans forcer, tout le monde doit avoir envoyé."""
    retenus, ecartes = [], []
    for p in cx.execute("SELECT * FROM participation WHERE soiree_id=?", (soiree_id,)).fetchall():
        a_note = bool(cx.execute("SELECT 1 FROM note WHERE participation_id=?", (p["id"],)).fetchone())
        if p["etat"] == "envoye" and a_note:
            retenus.append(p)
        elif not forcer:
            raise HTTPException(409, "Tout le monde n'a pas envoyé son classement.")
        else:
            (retenus if a_note else ecartes).append(p)
    return retenus, ecartes


@app.get("/api/soirees/{soiree_id}/forcer")
def forcer_apercu(soiree_id: int):
    """Ce que « forcer » ferait, avant de confirmer : qui serait pris avec combien de chansons, qui serait écarté."""
    with base(cfg().data) as cx:
        _soiree(cx, soiree_id)
        retards = [g for g in _participants(cx, soiree_id) if g["etat"] != "envoye"]
        return {"pris": [{"prenom": g["prenom"], "notees": g["notees"]} for g in retards if g["notees"]],
                "ecartes": [g["prenom"] for g in retards if not g["notees"]]}


@app.post("/api/soirees/{soiree_id}/devoiler")
def devoiler(soiree_id: int, corps: dict = Body(default={})):
    """Gèle les points : calculés une fois, enregistrés, plus jamais recalculés. Sauvegarde la base avant."""
    forcer, mode = bool(corps.get("forcer")), str(corps.get("mode") or "auto")
    if mode not in ("auto", "court", "complet", "jury"):
        raise HTTPException(422, "Mode inconnu.")
    with base(cfg().data) as cx:
        s = _soiree(cx, soiree_id)
        if s["etat"] != "ouverte":
            raise HTTPException(409, "Le dévoilement n'est possible que pendant une soirée ouverte.")
        retenus, ecartes = _retenus(cx, soiree_id, forcer)
        if not retenus:
            raise HTTPException(409, "Personne n'a noté : rien à dévoiler.")
        jures = {r["id"] for r in cx.execute("SELECT id FROM invite WHERE jury=1")}
        nb_jury = sum(1 for p in retenus if p["invite_id"] in jures)
        if mode == "auto":          # 1.0 : jury puis public dès qu'il y a un jury et un public, sinon tout le monde ensemble
            mode = "jury" if 0 < nb_jury < len(retenus) else "court"
        if mode == "jury" and not 0 < nb_jury < len(retenus):
            raise HTTPException(409, "Pour « jury puis public », il faut au moins un membre du jury et un du public "
                                     "parmi ceux qui ont noté (Réglages › Invités).")
    sauvegarder(cfg().data, f"soiree-{soiree_id}-avant-devoilement.db")
    with base(cfg().data) as cx:
        chansons = _chansons(cx, soiree_id)
        cx.execute("DELETE FROM points WHERE soiree_id=?", (soiree_id,))
        for p in retenus:
            ordre = _ordre(cx, p, chansons)
            cx.executemany("INSERT INTO points(soiree_id, participation_id, chanson_id, rang, points) VALUES(?,?,?,?,?)",
                           [(soiree_id, p["id"], c, ordre.index(c) + 1, pts)
                            for c, pts in points_du_classement(ordre).items()])
            _ecrire_ordre(cx, p["id"], ordre)           # le classement retenu est figé lui aussi
            cx.execute("UPDATE participation SET jury=? WHERE id=?", (1 if p["invite_id"] in jures else 0, p["id"]))
        for p in ecartes:
            cx.execute("UPDATE participation SET etat='ecarte' WHERE id=?", (p["id"],))
        passage = [p["id"] for p in retenus]
        random.shuffle(passage)
        # 1.3.1 : un double appui ne relance pas le tirage pendant l'animation
        if not cx.execute("UPDATE soiree SET etat='devoilement', forcee=?, mode_devoilement=?, ordre_devoilement=?, "
                          "pas_devoilement=0 WHERE id=? AND etat='ouverte'",
                          (1 if forcer else 0, mode, json.dumps(passage), soiree_id)).rowcount:
            raise HTTPException(409, "Le dévoilement est déjà lancé.")
        journal(cx, "devoilement_lance", str(soiree_id),
                {"force": forcer, "retenus": len(retenus), "ecartes": len(ecartes)})
    return {"ok": True}


def _devoilement(cx, s) -> dict:
    """Tout ce qu'il faut pour jouer le dévoilement, à partir des points gelés."""
    chansons = _chansons(cx, s["id"])
    passage = {c["id"]: c["ordre"] for c in chansons}
    points: dict[int, dict[int, int]] = defaultdict(dict)
    for r in cx.execute("SELECT participation_id, chanson_id, points FROM points WHERE soiree_id=?", (s["id"],)):
        points[r["participation_id"]][r["chanson_id"]] = r["points"]
    notes = {p: _notes(cx, p) for p in points}
    invites = []
    for pid in json.loads(s["ordre_devoilement"] or "[]"):
        p = cx.execute("SELECT p.etat, p.jury, i.prenom FROM participation p JOIN invite i ON i.id=p.invite_id WHERE p.id=?",
                       (pid,)).fetchone()
        commentaires = {r["chanson_id"]: r["commentaire"] for r in
                        cx.execute("SELECT chanson_id, commentaire FROM note WHERE participation_id=?", (pid,))}
        donnes = sorted(points[pid].items(), key=lambda cp: cp[1])      # du plus petit au douze
        invites.append({"id": pid, "prenom": p["prenom"], "jury": bool(p["jury"]), "notees": len(notes[pid]),
                        "envoye": p["etat"] == "envoye",
                        "points": [{"chanson": c, "points": pts, "note": notes[pid][c] / ECHELLE,
                                    "commentaire": commentaires.get(c, "")} for c, pts in donnes]})
    d = {"mode": s["mode_devoilement"], "pas": s["pas_devoilement"], "forcee": bool(s["forcee"]), "images": _images(s),
         "chansons": chansons, "invites": invites, "etat": s["etat"],
         "classement": classement_groupe([c["id"] for c in chansons], points, notes, passage)}
    d["marche"] = _marche(d)
    return d


def _marche(d: dict) -> dict:
    """Les pas du dévoilement, les mêmes sur la télé et sur chaque téléphone (1.0).
    Pas 0 : le départ (sur un téléphone, les points de l'invité). Pas 1, s'il y a un jury : tous les points du jury
    d'un coup. Puis un pas par chanson pour les points du public, de celle qui en reçoit le moins à celle qui en
    reçoit le plus (égalité : la dernière passée d'abord). Dernier pas (`fin`) : le podium.
    Sans jury, ou si tout le monde est du jury, tous les invités forment le public."""
    jures = [i["id"] for i in d["invites"] if i["jury"]]
    if len(jures) == len(d["invites"]):
        jures = []
    total = {c["id"]: 0 for c in d["chansons"]}
    for i in d["invites"]:
        if i["id"] not in jures:
            for p in i["points"]:
                total[p["chanson"]] += p["points"]
    passage = {c["id"]: c["ordre"] for c in d["chansons"]}
    public = sorted(total, key=lambda c: (total[c], -passage[c]))
    return {"jures": jures, "public": public, "fin": (1 if jures else 0) + len(public) + 1}


@app.get("/api/soirees/{soiree_id}/devoilement")
def devoilement(soiree_id: int):
    with base(cfg().data) as cx:
        s = _soiree(cx, soiree_id)
        if s["etat"] not in ("devoilement", "devoilee", "archivee"):
            raise HTTPException(409, "Le dévoilement n'a pas commencé.")
        return _devoilement(cx, s)


@app.post("/api/soirees/{soiree_id}/pas")
def pas(soiree_id: int, corps: dict = Body(...)):
    """Où en est le dévoilement : gardé côté serveur, pour reprendre après un redémarrage."""
    with base(cfg().data) as cx:
        cx.execute("UPDATE soiree SET pas_devoilement=? WHERE id=? AND etat='devoilement'",
                   (max(0, int(corps.get("pas", 0))), soiree_id))
    return {"ok": True}


@app.post("/api/soirees/{soiree_id}/terminer")
def terminer(soiree_id: int):
    """Fin du dévoilement : la synthèse s'ouvre aux invités. 1.5 : la soirée part à carnet."""
    with base(cfg().data) as cx:
        if _soiree(cx, soiree_id)["etat"] != "devoilement":
            raise HTTPException(409, "Aucun dévoilement en cours.")
        cx.execute("UPDATE soiree SET etat='devoilee', devoilee_le=? WHERE id=?", (maintenant(), soiree_id))
    return {"ok": True, "carnet": envoyer_soiree(soiree_id)}


# ================================================================ 1.5 : la soirée envoyée à carnet 3.1
#
# Décision de Julien du 19/11/2026 (dossier « coffre Contacts » v2) : après le dévoilement, la soirée part à l'adresse
# commune des événements de carnet (`PUT /evenements/douze-points/soiree-<id>`) : nom, date, lien de la soirée, et pour
# chaque invité son identifiant maison (sinon son prénom), sa note moyenne, son classement (rang, au classement du
# groupe, de sa chanson n° 1) et son podium. carnet range la soirée dans la fiche et le coffre Contacts. Un envoi raté
# est gardé et réessayé toutes les 10 minutes ; « Envoyer à carnet » (Réglages) reprend toutes les soirées dévoilées.

ENVOYER_CARNET = carnet.envoyer        # remplacé dans les tests


def _corps_soiree(cx, s) -> dict:
    f = _fiche(cx, s)
    ids_carnet = {r["id"]: (r["personne_id"], r["carnet_id"]) for r in cx.execute(
        "SELECT p.id, i.personne_id, i.carnet_id FROM participation p JOIN invite i ON i.id = p.invite_id WHERE p.soiree_id=?",
        (s["id"],))}
    par_carnet = {}
    if carnet.regle(cfg()) and any(c and not pid for pid, c in ids_carnet.values()):
        try:
            par_carnet = {p["carnet_id"]: p.get("personne_id") or "" for p in carnet.personnes(cfg())}
        except Exception:  # noqa: BLE001 — carnet arrêté : le prénom part seul, carnet le cherchera
            par_carnet = {}
    rang_groupe = {c["id"]: c["rang"] for c in f["chansons"]}
    pays = {c["id"]: c["pays"] for c in f["chansons"]}
    personnes = []
    for i in f["invites"]:
        mes = sorted(((c["invites"][str(i["id"])]["rang"], c["id"]) for c in f["chansons"]
                      if str(i["id"]) in c["invites"] and c["invites"][str(i["id"])]["rang"]), key=lambda x: x[0])
        pid, cid = ids_carnet.get(i["id"], (None, None))
        x = {"nom": i["prenom"], "role": "jury" if i["jury"] else "public",
             "donnees": {"moyenne": i["moyenne"], "classement": rang_groupe.get(mes[0][1]) if mes else None,
                         "top3": [pays[c] for _, c in mes[:3]]}}
        if pid or par_carnet.get(cid or ""):
            x["personne_id"] = pid or par_carnet[cid]
        personnes.append(x)
    date_ = s["date"] or (s["devoilee_le"] or maintenant())[:10]
    lien = adresse()
    return {"type": "douze_points", "date": date_[:10], "titre": s["nom"],
            "resume": " · ".join(str(x) for x in (s["concours"], s["annee"], s["emission"]) if x),
            "lien": f"{lien}/#/soiree/{s['id']}" if lien.startswith(("http://", "https://")) else "",
            "personnes": personnes}


def envoyer_soiree(soiree_id: int) -> str:
    """Envoie une soirée dévoilée à carnet ; gardée pour un nouvel essai si carnet ne répond pas."""
    if not carnet.regle(cfg()):
        return "carnet pas réglé : rien n'est envoyé"
    with base(cfg().data) as cx:
        s = _soiree(cx, soiree_id)
        if s["etat"] not in ("devoilee", "archivee"):
            return ""
        corps = _corps_soiree(cx, s)
    erreur = ""
    try:
        statut, rep = ENVOYER_CARNET(cfg().carnet_url, cfg().carnet_jeton, "PUT", f"/evenements/douze-points/soiree-{soiree_id}", corps)
        if statut in (401, 404, 405) or statut >= 500:
            erreur = "carnet trop ancien (3.1 nécessaire)" if statut in (404, 405) else f"carnet a répondu {statut}"
    except Exception as e:  # noqa: BLE001 — carnet arrêté, réseau
        erreur = f"carnet injoignable ({type(e).__name__})"
    with base(cfg().data) as cx:
        if erreur:
            cx.execute("INSERT INTO envoi_carnet(soiree_id, essais, erreur, le) VALUES(?,1,?,?) ON CONFLICT(soiree_id) "
                       "DO UPDATE SET essais = essais + 1, erreur = excluded.erreur, le = excluded.le",
                       (soiree_id, erreur, maintenant()))
            journal(cx, "carnet_en_attente", str(soiree_id))
            return f"{erreur} : envoi gardé, nouvel essai dans 10 minutes"
        cx.execute("DELETE FROM envoi_carnet WHERE soiree_id=?", (soiree_id,))
        journal(cx, "carnet_envoye", str(soiree_id), {"statut": statut})
    if statut >= 400:
        return f"refusé par carnet ({rep.get('detail', statut)})"
    a_rattacher = rep.get("a_rattacher") or []
    return "envoyé à carnet" + (f" ({len(a_rattacher)} invité(s) à rattacher dans carnet)" if a_rattacher else "")


def renvoyer_a_carnet() -> int:
    """Nouvel essai des soirées en attente ; rend le nombre envoyé."""
    with base(cfg().data) as cx:
        ids = [r["soiree_id"] for r in cx.execute("SELECT soiree_id FROM envoi_carnet ORDER BY soiree_id")]
    return sum(1 for i in ids if envoyer_soiree(i).startswith(("envoyé", "refusé")))


async def _boucle_carnet() -> None:
    while True:
        await asyncio.sleep(600)
        try:
            await asyncio.to_thread(renvoyer_a_carnet)
        except Exception as e:  # noqa: BLE001 — la boucle ne s'arrête jamais
            logging.getLogger("douze-points").warning("Envoi vers carnet : %s", e)


@app.post("/api/carnet/envoyer")
def carnet_envoyer_tout():
    """Réglages › « Envoyer à carnet » : toutes les soirées dévoilées (reprise de l'historique)."""
    with base(cfg().data) as cx:
        ids = [r["id"] for r in cx.execute("SELECT id FROM soiree WHERE etat IN ('devoilee','archivee') ORDER BY id")]
    resultats = [envoyer_soiree(i) for i in ids]
    with base(cfg().data) as cx:
        attente = cx.execute("SELECT COUNT(*) FROM envoi_carnet").fetchone()[0]
    return {"soirees": len(ids), "envoyees": sum(1 for r in resultats if r.startswith("envoyé")), "en_attente": attente}


@app.post("/api/soirees/{soiree_id}/archiver")
def archiver(soiree_id: int):
    """Clôture : le lien des invités ne répond plus."""
    with base(cfg().data) as cx:
        if _soiree(cx, soiree_id)["etat"] != "devoilee":
            raise HTTPException(409, "Seule une soirée dévoilée s'archive.")
        cx.execute("UPDATE soiree SET etat='archivee' WHERE id=?", (soiree_id,))
    return {"ok": True}


@app.delete("/api/soirees/{soiree_id}")
def soiree_supprimer(soiree_id: int, corps: dict = Body(default={})):
    """Supprime une soirée et tout ce qui lui appartient (chansons, notes, classements, points, images).
    Les invités restent dans la liste. La base est sauvegardée juste avant : une suppression par erreur se rattrape."""
    if corps.get("confirmation") is not True:
        raise HTTPException(409, "La suppression demande une confirmation.")
    with base(cfg().data) as cx:
        s = _soiree(cx, soiree_id)
    sauvegarder(cfg().data, f"soiree-{soiree_id}-avant-suppression.db")
    with base(cfg().data) as cx:
        cx.execute("DELETE FROM soiree WHERE id=?", (soiree_id,))
        journal(cx, "soiree_supprimee", str(soiree_id), {"etat": s["etat"]})
    for sorte in IMAGES:
        if s[sorte]:
            (cfg().data / "images" / s[sorte]).unlink(missing_ok=True)
    return {"ok": True}


# ================================================================ régie : fiche de la soirée et vrais votes

def _rangs(points: dict[int, int | None]) -> dict[int, int | None]:
    """Rang de chaque chanson d'après ses points (les ex æquo partagent le rang) ; sans points : pas de rang."""
    connus = sorted((v for v in points.values() if v is not None), reverse=True)
    return {c: (connus.index(v) + 1 if v is not None else None) for c, v in points.items()}


def _fiche(cx, s) -> dict:
    """Tout ce qui s'est dit pendant la soirée, à partir des points figés : notes, commentaires, classement du
    groupe, du jury, du public, et la comparaison avec les vrais votes quand ils ont été saisis."""
    d = _devoilement(cx, s)
    chansons, passage = d["chansons"], {c["id"]: c["ordre"] for c in d["chansons"]}
    ids = [c["id"] for c in chansons]
    points = {i["id"]: {p["chanson"]: p["points"] for p in i["points"]} for i in d["invites"]}
    notes = {i["id"]: _notes(cx, i["id"]) for i in d["invites"]}
    rangs = {i["id"]: {r["chanson_id"]: r["rang"] for r in cx.execute(
        "SELECT chanson_id, rang FROM classement WHERE participation_id=?", (i["id"],))} for i in d["invites"]}
    commentaires = {i["id"]: {r["chanson_id"]: r["commentaire"] for r in cx.execute(
        "SELECT chanson_id, commentaire FROM note WHERE participation_id=?", (i["id"],))} for i in d["invites"]}

    def partie(membres):        # classement d'une partie des invités (jury, ou public)
        lignes = classement_groupe(ids, {m: points[m] for m in membres}, {m: notes[m] for m in membres}, passage)
        return {l["chanson"]: {"points": l["total"], "rang": l["rang"] if membres else None} for l in lignes}

    jury = partie([i["id"] for i in d["invites"] if i["jury"]])
    public = partie([i["id"] for i in d["invites"] if not i["jury"]])
    groupe = {l["chanson"]: l for l in d["classement"]}
    off_jury = {c["id"]: c["officiel_jury"] for c in chansons}
    off_public = {c["id"]: c["officiel_public"] for c in chansons}
    off_total = {c: (None if off_jury[c] is None and off_public[c] is None else (off_jury[c] or 0) + (off_public[c] or 0)) for c in ids}
    rj, rp, rt = _rangs(off_jury), _rangs(off_public), _rangs(off_total)

    def comparer(nous: dict[int, int | None], eux: dict[int, int | None]):
        """Notre classement face au vrai : même gagnant, chansons communes dans les trois premières, écart moyen de rang."""
        communs = [c for c in ids if nous.get(c) is not None and eux.get(c) is not None]
        if not communs:
            return None
        premier = lambda r: {c for c in communs if r[c] == 1}
        trois = lambda r: {c for c in communs if r[c] <= 3}
        return {"meme_gagnant": bool(premier(nous) & premier(eux)), "trois_premieres": len(trois(nous) & trois(eux)),
                "ecart_moyen": round(sum(abs(nous[c] - eux[c]) for c in communs) / len(communs), 1), "chansons": len(communs)}

    a_jury = any(i["jury"] for i in d["invites"])
    # 1.3 : écarts et affinités, sur les classements figés au dévoilement (rendus par identifiants)
    ordres = {i: sorted(r, key=r.get) for i, r in rangs.items()}
    return {
        "soiree": {**_resume(s), "forcee": bool(s["forcee"])}, "a_jury": a_jury,
        "affinites": affinites(notes, ordres, points, passage),
        "invites": [{"id": i["id"], "prenom": i["prenom"], "jury": i["jury"], "notees": i["notees"],
                     "moyenne": round(sum(notes[i["id"]].values()) / len(notes[i["id"]]) / ECHELLE, 2)} for i in d["invites"]],
        "chansons": [{
            "id": c["id"], "ordre": c["ordre"], "pays": c["pays"], "code_pays": c["code_pays"], "artiste": c["artiste"],
            "titre": c["titre"], "moyenne": groupe[c["id"]]["moyenne"], "points": groupe[c["id"]]["total"],
            "rang": groupe[c["id"]]["rang"], "jury": jury[c["id"]], "public": public[c["id"]],
            "officiel": {"jury": off_jury[c["id"]], "public": off_public[c["id"]], "total": off_total[c["id"]],
                         "rang_jury": rj[c["id"]], "rang_public": rp[c["id"]], "rang": rt[c["id"]]},
            "invites": {str(i["id"]): {"note": notes[i["id"]][c["id"]] / ECHELLE, "rang": rangs[i["id"]].get(c["id"]),
                                       "points": points[i["id"]].get(c["id"], 0),
                                       "commentaire": commentaires[i["id"]].get(c["id"], "")}
                        for i in d["invites"] if c["id"] in notes[i["id"]]},
        } for c in chansons],
        "comparaison": {
            "ensemble": comparer({c: groupe[c]["rang"] for c in ids}, rt),
            "jury": comparer({c: jury[c]["rang"] for c in ids}, rj) if a_jury else None,
            "public": comparer({c: public[c]["rang"] for c in ids}, rp) if a_jury else None,
        },
    }


def _soiree_devoilee(cx, soiree_id: int):
    s = _soiree(cx, soiree_id)
    if s["etat"] not in ("devoilement", "devoilee", "archivee"):
        raise HTTPException(409, "La fiche n'existe qu'une fois le dévoilement lancé : avant, personne ne voit les notes.")
    return s


@app.get("/api/soirees/{soiree_id}/fiche")
def fiche(soiree_id: int):
    with base(cfg().data) as cx:
        return _fiche(cx, _soiree_devoilee(cx, soiree_id))


@app.get("/api/soirees/{soiree_id}/fiche.csv")
def fiche_csv(soiree_id: int):
    """La même fiche en tableau, pour un tableur : une ligne par chanson, séparateur point-virgule."""
    with base(cfg().data) as cx:
        f = _fiche(cx, _soiree_devoilee(cx, soiree_id))
    fr = lambda v: "" if v is None else str(v).replace(".", ",")
    tete = ["Passage", "Pays", "Artiste", "Titre", "Moyenne /20", "Points", "Rang", "Points jury", "Rang jury",
            "Points public", "Rang public", "Vrai jury", "Rang vrai jury", "Vrai public", "Rang vrai public",
            "Vrai total", "Vrai rang"]
    for i in f["invites"]:
        role = " (jury)" if i["jury"] else ""
        tete += [f"{i['prenom']}{role} : note", f"{i['prenom']} : rang", f"{i['prenom']} : points", f"{i['prenom']} : commentaire"]
    sortie = io.StringIO()
    tableau = csv.writer(sortie, delimiter=";", lineterminator="\r\n")
    tableau.writerow([f["soiree"]["nom"]])
    tableau.writerow(tete)
    for c in f["chansons"]:
        o = c["officiel"]
        ligne = [c["ordre"], c["pays"], c["artiste"], c["titre"], fr(c["moyenne"]), c["points"], c["rang"],
                 c["jury"]["points"], fr(c["jury"]["rang"]), c["public"]["points"], fr(c["public"]["rang"]),
                 fr(o["jury"]), fr(o["rang_jury"]), fr(o["public"]), fr(o["rang_public"]), fr(o["total"]), fr(o["rang"])]
        for i in f["invites"]:
            v = c["invites"].get(str(i["id"]))
            ligne += [fr(v["note"]), fr(v["rang"]), v["points"], v["commentaire"]] if v else ["", "", "", ""]
        # une cellule qui commence par = + - @ serait lue comme une formule par un tableur : on la désamorce
        # 1.3.1 : une cellule vide restait « ' » (x[:1] vaut "" et "" est dans toute chaîne)
        tableau.writerow([("'" + x) if isinstance(x, str) and x and x[0] in "=+-@\t\r" else x for x in ligne])
    return Response("\ufeff" + sortie.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="douze-points-soiree-{soiree_id}.csv"'})


@app.put("/api/soirees/{soiree_id}/officiel")
def officiel(soiree_id: int, corps: dict = Body(...)):
    """Les vrais votes du concours, saisis après coup : points du jury et du public pour chaque chanson.
    Une case vide efface la valeur. Rien d'autre ne change : nos points restent figés."""
    def nombre(v):
        if v is None or v == "":
            return None
        try:
            n = int(v)
        except (TypeError, ValueError):
            raise HTTPException(422, "Les vrais votes sont des nombres de points.")
        if not 0 <= n <= 9999:
            raise HTTPException(422, "Les vrais votes sont des nombres de points.")
        return n
    with base(cfg().data) as cx:
        _soiree(cx, soiree_id)
        for r in corps.get("resultats") or []:
            cx.execute("UPDATE chanson SET officiel_jury=?, officiel_public=? WHERE id=? AND soiree_id=?",
                       (nombre(r.get("jury")), nombre(r.get("public")), int(r.get("chanson_id", 0)), soiree_id))
    return {"ok": True}


@app.get("/api/journal")
def lire_journal():
    with base(cfg().data) as cx:
        return [dict(r) for r in cx.execute("SELECT date, action, cible, detail FROM journal ORDER BY id DESC LIMIT 200")]


# ================================================================ porte invité

def _porte(cx, jeton: str):
    """La soirée de ce jeton, comparé en temps constant. Brouillon : le lien existe déjà (« ça commence bientôt »).
    Archivée : la porte est fermée."""
    trouvee = None
    for s in cx.execute("SELECT * FROM soiree WHERE etat<>'archivee'").fetchall():
        if hmac.compare_digest(s["jeton_invite"].encode(), jeton.encode()):
            trouvee = s
    if not jeton or trouvee is None:
        raise HTTPException(404, "Ce lien n'est plus valable.")
    return trouvee


def _moi(cx, s, request: Request, exiger: bool = True):
    """La participation du téléphone qui appelle, reconnue par son jeton personnel (en-tête X-Telephone)."""
    jeton = request.headers.get("x-telephone", "")
    if jeton:
        for p in cx.execute("SELECT * FROM participation WHERE soiree_id=? AND jeton_telephone IS NOT NULL",
                            (s["id"],)).fetchall():
            if hmac.compare_digest(p["jeton_telephone"].encode(), jeton.encode()):
                return p
    if exiger:
        raise HTTPException(403, "Choisis d'abord ton prénom.")
    return None


def _ma_copie(cx, s, p, chansons: list[dict]) -> dict:
    notes = {r["chanson_id"]: {"valeur": r["valeur"] / ECHELLE, "commentaire": r["commentaire"]} for r in
             cx.execute("SELECT chanson_id, valeur, commentaire FROM note WHERE participation_id=?", (p["id"],))}
    prenom = cx.execute("SELECT prenom FROM invite WHERE id=?", (p["invite_id"],)).fetchone()["prenom"]
    return {"id": p["id"], "prenom": prenom, "etat": p["etat"], "classement_main": bool(p["classement_main"]),
            "notes": notes, "classement": _ordre(cx, p, chansons)}


@app.get("/invite/{jeton}/api/etat")
def invite_etat(jeton: str, request: Request):
    """Tout ce qu'un téléphone a le droit de savoir. Des autres : le prénom, arrivé ou non, envoyé ou non."""
    with base(cfg().data) as cx:
        s = _porte(cx, jeton)
        etat = {"nom": s["nom"], "concours": s["concours"], "annee": s["annee"], "emission": s["emission"],
                "etat": s["etat"], "pas_note": float(_reglage(cx, "pas_note")), "bareme": [12, 10, 8, 7, 6, 5, 4, 3, 2, 1], "images": _images(s)}
        if s["etat"] == "brouillon":
            return etat
        chansons = [{k: c[k] for k in ("id", "ordre", "pays", "code_pays", "artiste", "titre")}
                    for c in _chansons(cx, s["id"])]
        p = _moi(cx, s, request, exiger=False)
        return {**etat, "chansons": chansons, "chanson_en_cours": s["chanson_en_cours"],
                "invites": [{"id": g["id"], "prenom": g["prenom"], "pris": g["pris"], "envoye": g["etat"] == "envoye"}
                            for g in _participants(cx, s["id"]) if g["etat"] != "ecarte"],
                "moi": _ma_copie(cx, s, p, chansons) if p else None}


def _ouverte(s) -> None:
    if s["etat"] != "ouverte":
        raise HTTPException(409, "Les notes sont closes." if s["etat"] != "brouillon" else "La soirée n'a pas commencé.")


@app.post("/invite/{jeton}/api/prenom")
def invite_prenom(jeton: str, request: Request, corps: dict = Body(...)):
    """Un téléphone, un prénom. Tant qu'il n'a rien noté, l'invité peut en changer lui-même."""
    with base(cfg().data) as cx:
        s = _porte(cx, jeton)
        _ouverte(s)
        cible = cx.execute("SELECT * FROM participation WHERE id=? AND soiree_id=?",
                           (int(corps.get("participation_id", 0)), s["id"])).fetchone()
        if not cible:
            raise HTTPException(404, "Prénom inconnu pour cette soirée.")
        ancien = _moi(cx, s, request, exiger=False)
        if ancien and ancien["id"] == cible["id"]:
            return {"jeton_telephone": ancien["jeton_telephone"]}
        if cible["jeton_telephone"]:
            raise HTTPException(409, "Ce prénom est déjà pris sur un autre téléphone : demande à l'hôte de le libérer.")
        if ancien:
            if cx.execute("SELECT 1 FROM note WHERE participation_id=?", (ancien["id"],)).fetchone():
                raise HTTPException(409, "Tu as déjà noté sous un autre prénom : demande à l'hôte.")
            cx.execute("UPDATE participation SET jeton_telephone=NULL, etat='attendu', arrive_le=NULL WHERE id=?",
                       (ancien["id"],))
        nouveau = secrets.token_urlsafe(24)
        # 1.3.1 : deux téléphones sur le même prénom au même instant : seul le premier l'obtient
        pris = cx.execute("UPDATE participation SET jeton_telephone=?, arrive_le=COALESCE(arrive_le, ?), "
                          "etat=CASE WHEN etat='attendu' THEN 'en_cours' ELSE etat END "
                          "WHERE id=? AND jeton_telephone IS NULL",
                          (nouveau, maintenant(), cible["id"])).rowcount
        if not pris:
            raise HTTPException(409, "Ce prénom est déjà pris sur un autre téléphone : demande à l'hôte de le libérer.")
        return {"jeton_telephone": nouveau}


@app.put("/invite/{jeton}/api/note")
def invite_noter(jeton: str, request: Request, corps: dict = Body(...)):
    """Enregistrée tout de suite : un téléphone qui se verrouille ne perd rien.
    `valeur` de 0 à 20, au pas réglé (1, ½ ou ¼ point) ; `valeur` absente ou nulle : la note est retirée."""
    with base(cfg().data) as cx:
        s = _porte(cx, jeton)
        _ouverte(s)
        p = _moi(cx, s, request)
        chanson = cx.execute("SELECT id FROM chanson WHERE id=? AND soiree_id=?",
                             (int(corps.get("chanson_id", 0)), s["id"])).fetchone()
        if not chanson:
            raise HTTPException(404, "Chanson inconnue.")
        chansons = _chansons(cx, s["id"])
        if corps.get("valeur") is None:
            cx.execute("DELETE FROM note WHERE participation_id=? AND chanson_id=?", (p["id"], chanson["id"]))
            cx.execute("DELETE FROM classement WHERE participation_id=? AND chanson_id=?", (p["id"], chanson["id"]))
        else:
            pas_note = float(_reglage(cx, "pas_note"))
            message = f"La note va de 0 à 20, {LIBELLE_PAS[str(_reglage(cx, 'pas_note'))]}."
            try:
                unites = float(corps["valeur"]) * ECHELLE
            except (TypeError, ValueError):
                raise HTTPException(422, message)
            if not math.isfinite(unites) or unites != int(unites) or not 0 <= unites <= 20 * ECHELLE or unites % (pas_note * ECHELLE):
                raise HTTPException(422, message)

            commentaire = str(corps.get("commentaire") or "").strip()[:COMMENTAIRE_MAX]
            cx.execute("INSERT INTO note(participation_id, chanson_id, valeur, commentaire, modifie_le) VALUES(?,?,?,?,?) "
                       "ON CONFLICT(participation_id, chanson_id) DO UPDATE SET valeur=excluded.valeur, "
                       "commentaire=excluded.commentaire, modifie_le=excluded.modifie_le",
                       (p["id"], chanson["id"], int(unites), commentaire, maintenant()))
            if p["classement_main"]:        # l'ordre fait à la main ne bouge pas : la nouvelle venue s'y range
                _ecrire_ordre(cx, p["id"], _ordre(cx, p, chansons))
        _rouvrir(cx, p)
        return {"moi": _ma_copie(cx, s, cx.execute("SELECT * FROM participation WHERE id=?", (p["id"],)).fetchone(), chansons)}


def _rouvrir(cx, p) -> None:
    """Toucher à une copie envoyée la rouvre : « pas encore renvoyé » jusqu'au nouvel envoi."""
    if p["etat"] == "envoye":
        cx.execute("UPDATE participation SET etat='en_cours', envoye_le=NULL WHERE id=?", (p["id"],))


@app.put("/invite/{jeton}/api/classement")
def invite_classer(jeton: str, request: Request, corps: dict = Body(...)):
    """`ordre` : toutes les chansons notées, dans l'ordre voulu. `auto` : revenir au classement des notes."""
    with base(cfg().data) as cx:
        s = _porte(cx, jeton)
        _ouverte(s)
        p = _moi(cx, s, request)
        chansons = _chansons(cx, s["id"])
        if corps.get("auto"):
            cx.execute("DELETE FROM classement WHERE participation_id=?", (p["id"],))
            cx.execute("UPDATE participation SET classement_main=0 WHERE id=?", (p["id"],))
        else:
            ordre = [int(c) for c in corps.get("ordre") or []]
            if sorted(ordre) != sorted(_notes(cx, p["id"])):
                raise HTTPException(409, "Le classement doit contenir chaque chanson notée, une seule fois.")
            _ecrire_ordre(cx, p["id"], ordre)
            cx.execute("UPDATE participation SET classement_main=1 WHERE id=?", (p["id"],))
        _rouvrir(cx, p)
        return {"moi": _ma_copie(cx, s, cx.execute("SELECT * FROM participation WHERE id=?", (p["id"],)).fetchone(), chansons)}


@app.post("/invite/{jeton}/api/envoyer")
def invite_envoyer(jeton: str, request: Request):
    with base(cfg().data) as cx:
        s = _porte(cx, jeton)
        _ouverte(s)
        p = _moi(cx, s, request)
        if not cx.execute("SELECT 1 FROM note WHERE participation_id=?", (p["id"],)).fetchone():
            raise HTTPException(409, "Note au moins une chanson avant d'envoyer.")
        cx.execute("UPDATE participation SET etat='envoye', envoye_le=? WHERE id=?", (maintenant(), p["id"]))
        restants = cx.execute("SELECT COUNT(*) FROM participation WHERE soiree_id=? AND etat<>'envoye'", (s["id"],)).fetchone()[0]
        if restants == 0 and not s["tous_envoye_le"]:
            cx.execute("UPDATE soiree SET tous_envoye_le=? WHERE id=?", (maintenant(), s["id"]))
    return {"ok": True, "tous_envoye": restants == 0}


@app.post("/invite/{jeton}/api/modifier")
def invite_modifier(jeton: str, request: Request):
    with base(cfg().data) as cx:
        s = _porte(cx, jeton)
        _ouverte(s)
        _rouvrir(cx, _moi(cx, s, request))
    return {"ok": True}


@app.get("/invite/{jeton}/image/{sorte}")
def invite_image(jeton: str, sorte: str):
    """Les images de l'évènement, pour le téléphone des invités. Rien d'autre que l'image."""
    with base(cfg().data) as cx:
        s = _porte(cx, jeton)
    return _servir_image(s, sorte)


@app.get("/invite/{jeton}/api/devoilement")
def invite_devoilement(jeton: str, request: Request):
    """Le dévoilement sur le téléphone d'un invité (1.0), au pas où l'hôte l'a mené et pas plus loin : ni les points
    du jury avant leur pas, ni ceux du public d'une chanson pas encore appelée, ni notes ni commentaires.
    Chaque ligne additionne les points de l'invité, ceux du jury et ceux des autres invités (les siens ne sont
    jamais comptés deux fois)."""
    with base(cfg().data) as cx:
        s = _porte(cx, jeton)
        if s["etat"] not in ("devoilement", "devoilee"):
            raise HTTPException(409, "Le dévoilement n'a pas commencé.")
        d = _devoilement(cx, s)
        p = _moi(cx, s, request, exiger=False)
    m = d["marche"]
    moi = next((i for i in d["invites"] if p and i["id"] == p["id"]), None)
    pas = m["fin"] if s["etat"] == "devoilee" else max(0, min(d["pas"], m["fin"]))
    debut = 1 if m["jures"] else 0

    def somme(du_jury: bool, chanson: int, sans_moi: bool = True) -> int:
        return sum(x["points"] for i in d["invites"] if (i["id"] in m["jures"]) == du_jury and not (sans_moi and i is moi)
                   for x in i["points"] if x["chanson"] == chanson)

    ids = [c["id"] for c in d["chansons"]]
    appelees = m["public"][:max(0, min(len(m["public"]), pas - debut))]
    sortie = {
        "etat": s["etat"], "pas": pas, "fin": m["fin"], "avec_jury": bool(m["jures"]), "nb_public": len(m["public"]),
        "chansons": [{k: c[k] for k in ("id", "ordre", "pays", "code_pays", "artiste", "titre")} for c in d["chansons"]],
        "moi": {"prenom": moi["prenom"], "jury": moi["id"] in m["jures"],
                "points": {str(x["chanson"]): x["points"] for x in moi["points"]}} if moi else None,
        "jury": {str(c): somme(True, c) for c in ids} if m["jures"] and pas >= 1 else None,
        "public": [{"chanson": c, "autres": somme(False, c), "total": somme(False, c, sans_moi=False)} for c in appelees],
    }
    if pas >= m["fin"]:
        sortie["classement"] = d["classement"]
    return sortie


@app.get("/invite/{jeton}/api/resultats")
def invite_resultats(jeton: str):
    """Fermé tant que le dévoilement n'est pas fini. Avec les vrais votes du concours dès que l'hôte les a saisis."""
    with base(cfg().data) as cx:
        s = _porte(cx, jeton)
        if s["etat"] != "devoilee":
            raise HTTPException(409, "Les résultats ne sont pas encore dévoilés.")
        f = _fiche(cx, s)
        return {**_devoilement(cx, s), "vrais": [{"chanson": c["id"], **c["officiel"], "notre_rang": c["rang"]}
                                                 for c in f["chansons"]],
                "comparaison": f["comparaison"], "affinites": f["affinites"]}


# ================================================================ sauvegarde des réglages (pour l'Anneau)

@app.get("/externe/sauvegarde")
def externe_sauvegarde(request: Request):
    """Les réglages d'usage, collectés chaque nuit par l'Anneau. Porte ouverte par le jeton commun seul ;
    MAISON_JETON vide : porte fermée. Jamais de variable, de chemin ni de secret (ha_webhook exclu)."""
    acceptes = maison.jetons()
    if not acceptes or not maison.jeton_valide(maison.jeton_propose(request.headers), acceptes):
        raise HTTPException(404, "Introuvable.")
    with base(cfg().data) as cx:
        reglages = tous_reglages(cx)
    return maison.sauvegarde(APPLI, __version__, reglages, exclus=EXCLUS_SAUVEGARDE)


# ================================================================ interface

@app.get("/{chemin:path}")
def interface(chemin: str):
    statique = cfg().static
    fichier = (statique / chemin).resolve() if chemin else None
    if fichier and fichier.is_file() and statique.resolve() in fichier.parents:
        return FileResponse(fichier)
    index = statique / "index.html"
    if index.is_file():
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
    return JSONResponse({"detail": "Interface non compilée."}, status_code=404)
