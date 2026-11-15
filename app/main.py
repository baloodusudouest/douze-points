"""Douze points : les soirées de concours de chansons à la maison (FastAPI + interface Svelte compilée).

Deux portes :
- la régie, sous /api/…, derrière le mot de passe commun (cookie de l'appli ou cookie « maison_session ») ;
- la porte invité, sous /invite/<jeton>/api/…, ouverte par le jeton de la soirée (QR code). Elle ne rend
  jamais la note, le commentaire ou le classement d'un autre invité, ni un total, avant la fin du dévoilement.
"""
from __future__ import annotations

import asyncio
import hmac
import io
import json
import random
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime
import segno
from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from . import __version__
from .auth import COMMUN, DUREE, Sessions
from .base import base, preparer, sauvegarder
from .config import APPLI, Config, charger
from .points import classement_groupe, classement_par_notes, inserer, points_du_classement

ETAT: dict = {}
PUBLIQUES = ("/api/connexion", "/api/session")
CONCOURS = ("Eurovision", "Eurovision Asia")
EMISSIONS = ("demi1", "demi2", "finale", "unique")
COMMENTAIRE_MAX = 280


def maintenant() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def cfg() -> Config:
    return ETAT["cfg"]


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
    ETAT.update(cfg=c, sessions=Sessions(APPLI, c.password, _lire_generation(c)), debits=defaultdict(deque))
    yield


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
        cle = request.headers.get("x-telephone") or (request.client.host if request.client else "?")
        file, t = ETAT["debits"][cle], time.monotonic()
        while file and t - file[0] > 60:
            file.popleft()
        if len(file) >= cfg().limite_invite:
            return JSONResponse({"detail": "Trop de demandes : attends un instant."}, status_code=429)
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
def sante():
    """Pour la tuile de l'Anneau : des nombres, aucun nom."""
    with base(cfg().data) as cx:
        archivees = cx.execute("SELECT COUNT(*) FROM soiree WHERE etat IN ('devoilee','archivee')").fetchone()[0]
        en_cours = cx.execute("SELECT id FROM soiree WHERE etat IN ('ouverte','devoilement') ORDER BY id DESC").fetchone()
        attendus = cx.execute("SELECT COUNT(*) FROM participation WHERE soiree_id=? AND etat IN ('attendu','en_cours')",
                              (en_cours["id"],)).fetchone()[0] if en_cours else 0
    return {"ok": True, "version": __version__, "soirees": archivees,
            "soiree_en_cours": bool(en_cours), "classements_attendus": attendus}


# ================================================================ connexion (régie)

@app.get("/api/session")
def session(request: Request):
    return {"connecte": ETAT["sessions"].connecte(request.cookies), "version": __version__,
            "adresse": cfg().adresse, "notification": bool(cfg().ha_webhook)}


@app.post("/api/connexion")
async def connexion(corps: dict = Body(...)):
    s = ETAT["sessions"]
    if cfg().attente_connexion:
        await asyncio.sleep(s.attente())
    if not s.verifier_mot_de_passe(str(corps.get("mot_de_passe", ""))):
        raise HTTPException(401, "Mot de passe incorrect.")
    r = JSONResponse({"ok": True})
    r.set_cookie(s.cookie, s.creer(), max_age=DUREE, httponly=True, samesite="strict")
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
        "SELECT id, ordre, pays, code_pays, artiste, titre, rang_officiel, qualifie FROM chanson "
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
        "SELECT p.id, i.prenom, p.etat, p.jeton_telephone IS NOT NULL AS pris, "
        "(SELECT COUNT(*) FROM note n WHERE n.participation_id=p.id) AS notees "
        "FROM participation p JOIN invite i ON i.id=p.invite_id WHERE p.soiree_id=? ORDER BY i.prenom COLLATE NOCASE",
        (soiree_id,))
    return [{"id": r["id"], "prenom": r["prenom"], "etat": r["etat"], "pris": bool(r["pris"]), "notees": r["notees"]}
            for r in lignes]


def _resume(s) -> dict:
    return {"id": s["id"], "concours": s["concours"], "annee": s["annee"], "emission": s["emission"],
            "date": s["date"], "nom": s["nom"], "etat": s["etat"]}


# ================================================================ régie : invités

@app.get("/api/invites")
def invites():
    with base(cfg().data) as cx:
        return [dict(r) for r in cx.execute("SELECT id, prenom, actif FROM invite ORDER BY prenom COLLATE NOCASE")]


def _prenom(corps: dict) -> str:
    prenom = " ".join(str(corps.get("prenom", "")).split())[:40]
    if not prenom:
        raise HTTPException(422, "Il faut un prénom.")
    return prenom


@app.post("/api/invites")
def invite_ajouter(corps: dict = Body(...)):
    prenom = _prenom(corps)
    with base(cfg().data) as cx:
        if cx.execute("SELECT 1 FROM invite WHERE prenom=? COLLATE NOCASE AND actif=1", (prenom,)).fetchone():
            raise HTTPException(409, "Ce prénom est déjà dans la liste : ajoute une initiale pour les distinguer.")
        return {"id": cx.execute("INSERT INTO invite(prenom, cree_le) VALUES(?,?)", (prenom, maintenant())).lastrowid}


@app.put("/api/invites/{invite_id}")
def invite_modifier(invite_id: int, corps: dict = Body(...)):
    with base(cfg().data) as cx:
        if "prenom" in corps:
            cx.execute("UPDATE invite SET prenom=? WHERE id=?", (_prenom(corps), invite_id))
        if "actif" in corps:      # retiré de la liste, gardé dans les archives
            cx.execute("UPDATE invite SET actif=? WHERE id=?", (1 if corps["actif"] else 0, invite_id))
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
    try:
        annee = int(corps.get("annee"))
    except (TypeError, ValueError):
        raise HTTPException(422, "Il faut une année.")
    if concours not in CONCOURS or emission not in EMISSIONS or not nom or not 1956 <= annee <= 2100:
        raise HTTPException(422, "Concours, année, émission et nom de l'évènement sont nécessaires.")
    with base(cfg().data) as cx:
        soiree_id = cx.execute(
            "INSERT INTO soiree(concours, annee, emission, date, nom, jeton_invite, cree_le) VALUES(?,?,?,?,?,?,?)",
            (concours, annee, emission, str(corps.get("date") or "")[:10] or None, nom,
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
                "lien": f"{cfg().adresse}/invite/{s['jeton_invite']}" if cfg().adresse else ""}


@app.get("/api/soirees/{soiree_id}/qr.svg")
def qr(soiree_id: int):
    """Le QR code du lien des invités, pour l'écran d'accueil. Clair sur fond sombre, bord compris."""
    with base(cfg().data) as cx:
        s = _soiree(cx, soiree_id)
    if not cfg().adresse:
        raise HTTPException(409, "Aucune adresse n'est réglée dans la stack (DOUZE_POINTS_ADRESSE).")
    tampon = io.BytesIO()
    segno.make(f"{cfg().adresse}/invite/{s['jeton_invite']}", error="m").save(
        tampon, kind="svg", scale=10, border=3, dark="#151311", light="#f2ece2", xmldecl=False)
    return Response(tampon.getvalue(), media_type="image/svg+xml")


def lire_collage(texte: str) -> list[dict]:
    """Une chanson par ligne ; champs séparés par une tabulation ou un point-virgule : pays, artiste, titre.
    Un numéro de passage en tête de ligne est accepté et ignoré : c'est l'ordre des lignes qui compte."""
    chansons = []
    for ligne in texte.splitlines():
        champs = [c.strip() for c in (ligne.split("\t") if "\t" in ligne else ligne.split(";"))]
        if champs and champs[0].rstrip(".").isdigit():
            champs = champs[1:]
        champs = [c for c in champs] + ["", "", ""]
        if champs[0]:
            chansons.append({"pays": champs[0], "artiste": champs[1], "titre": champs[2]})
    return chansons


@app.put("/api/soirees/{soiree_id}/chansons")
def chansons_remplacer(soiree_id: int, corps: dict = Body(...)):
    """Brouillon : la liste entière, dans l'ordre de passage (lignes, ou texte collé)."""
    chansons = lire_collage(str(corps["texte"])) if "texte" in corps else list(corps.get("chansons") or [])
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
    with base(cfg().data) as cx:
        for champ, taille in (("pays", 60), ("artiste", 120), ("titre", 120), ("code_pays", 2)):
            if champ in corps:
                cx.execute(f"UPDATE chanson SET {champ}=? WHERE id=?", (str(corps[champ] or "").strip()[:taille], chanson_id))
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
        if cx.execute("SELECT 1 FROM soiree WHERE etat IN ('ouverte','devoilement') AND id<>?", (soiree_id,)).fetchone():
            raise HTTPException(409, "Une autre soirée est en cours : termine-la d'abord.")
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
    forcer, mode = bool(corps.get("forcer")), str(corps.get("mode") or "court")
    if mode not in ("court", "complet"):
        raise HTTPException(422, "Mode inconnu.")
    with base(cfg().data) as cx:
        s = _soiree(cx, soiree_id)
        if s["etat"] != "ouverte":
            raise HTTPException(409, "Le dévoilement n'est possible que pendant une soirée ouverte.")
        retenus, ecartes = _retenus(cx, soiree_id, forcer)
        if not retenus:
            raise HTTPException(409, "Personne n'a noté : rien à dévoiler.")
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
        for p in ecartes:
            cx.execute("UPDATE participation SET etat='ecarte' WHERE id=?", (p["id"],))
        passage = [p["id"] for p in retenus]
        random.shuffle(passage)
        cx.execute("UPDATE soiree SET etat='devoilement', forcee=?, mode_devoilement=?, ordre_devoilement=?, "
                   "pas_devoilement=0 WHERE id=?", (1 if forcer else 0, mode, json.dumps(passage), soiree_id))
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
        p = cx.execute("SELECT p.etat, i.prenom FROM participation p JOIN invite i ON i.id=p.invite_id WHERE p.id=?",
                       (pid,)).fetchone()
        commentaires = {r["chanson_id"]: r["commentaire"] for r in
                        cx.execute("SELECT chanson_id, commentaire FROM note WHERE participation_id=?", (pid,))}
        donnes = sorted(points[pid].items(), key=lambda cp: cp[1])      # du plus petit au douze
        invites.append({"id": pid, "prenom": p["prenom"], "notees": len(notes[pid]), "envoye": p["etat"] == "envoye",
                        "points": [{"chanson": c, "points": pts, "note": notes[pid][c] / 2,
                                    "commentaire": commentaires.get(c, "")} for c, pts in donnes]})
    return {"mode": s["mode_devoilement"], "pas": s["pas_devoilement"], "forcee": bool(s["forcee"]),
            "chansons": chansons, "invites": invites,
            "classement": classement_groupe([c["id"] for c in chansons], points, notes, passage)}


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
    """Fin du dévoilement : la synthèse s'ouvre aux invités."""
    with base(cfg().data) as cx:
        if _soiree(cx, soiree_id)["etat"] != "devoilement":
            raise HTTPException(409, "Aucun dévoilement en cours.")
        cx.execute("UPDATE soiree SET etat='devoilee', devoilee_le=? WHERE id=?", (maintenant(), soiree_id))
    return {"ok": True}


@app.post("/api/soirees/{soiree_id}/archiver")
def archiver(soiree_id: int):
    """Clôture : le lien des invités ne répond plus."""
    with base(cfg().data) as cx:
        if _soiree(cx, soiree_id)["etat"] != "devoilee":
            raise HTTPException(409, "Seule une soirée dévoilée s'archive.")
        cx.execute("UPDATE soiree SET etat='archivee' WHERE id=?", (soiree_id,))
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
    notes = {r["chanson_id"]: {"valeur": r["valeur"] / 2, "commentaire": r["commentaire"]} for r in
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
                "etat": s["etat"], "bareme": [12, 10, 8, 7, 6, 5, 4, 3, 2, 1]}
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
        cx.execute("UPDATE participation SET jeton_telephone=?, arrive_le=COALESCE(arrive_le, ?), "
                   "etat=CASE WHEN etat='attendu' THEN 'en_cours' ELSE etat END WHERE id=?",
                   (nouveau, maintenant(), cible["id"]))
        return {"jeton_telephone": nouveau}


@app.put("/invite/{jeton}/api/note")
def invite_noter(jeton: str, request: Request, corps: dict = Body(...)):
    """Enregistrée tout de suite : un téléphone qui se verrouille ne perd rien.
    `valeur` de 0 à 20 par demi-points ; `valeur` absente ou nulle : la note est retirée."""
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
            try:
                demis = float(corps["valeur"]) * 2
            except (TypeError, ValueError):
                raise HTTPException(422, "La note va de 0 à 20, par demi-points.")
            if demis != int(demis) or not 0 <= demis <= 40:
                raise HTTPException(422, "La note va de 0 à 20, par demi-points.")
            commentaire = str(corps.get("commentaire") or "").strip()[:COMMENTAIRE_MAX]
            cx.execute("INSERT INTO note(participation_id, chanson_id, valeur, commentaire, modifie_le) VALUES(?,?,?,?,?) "
                       "ON CONFLICT(participation_id, chanson_id) DO UPDATE SET valeur=excluded.valeur, "
                       "commentaire=excluded.commentaire, modifie_le=excluded.modifie_le",
                       (p["id"], chanson["id"], int(demis), commentaire, maintenant()))
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


@app.get("/invite/{jeton}/api/resultats")
def invite_resultats(jeton: str):
    """Fermé tant que le dévoilement n'est pas fini : le téléphone ne devance jamais la télé."""
    with base(cfg().data) as cx:
        s = _porte(cx, jeton)
        if s["etat"] != "devoilee":
            raise HTTPException(409, "Les résultats ne sont pas encore dévoilés.")
        return _devoilement(cx, s)


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
