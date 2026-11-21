"""Fabrique docs/journal-exemple.json (finale) et docs/journal-exemple-demi.json : le contrat lu par Gazette 0.28.0.
Soirées inventées (Pays 1…, invités Aglaé, Barnabé…), jouées par l'API dans un dossier temporaire.
Lancer depuis la racine du dépôt : python tools/journal_exemple.py"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
os.environ["MAISON_JETON"] = "jeton-exemple"

from fastapi.testclient import TestClient  # noqa: E402

from app import main  # noqa: E402
from app.config import Config  # noqa: E402
from tests.conftest import MOT_DE_PASSE, Soiree, faux_annuaire  # noqa: E402


def jouer(client, demi: bool) -> dict:
    s = Soiree(client, n=12, ouvrir=False)
    with main.base(main.cfg().data) as cx:
        if demi:
            cx.execute("UPDATE soiree SET emission='demi1', nom='Première demi-finale de démonstration' WHERE id=?", (s.id,))
        cx.execute("UPDATE soiree SET ville='Villeneuve', date='2027-05-15' WHERE id=?", (s.id,))
        if not demi:      # 1.12 : notre pays (France), noté et classé mais sans points : « hors_points », « notre_pays »
            cx.execute("UPDATE chanson SET pays='France', code_pays='FR' WHERE id=?", (s.chansons[3],))
    client.post(f"/api/soirees/{s.id}/ouvrir")
    if not demi:
        for i in client.get("/api/invites").json():
            if i["prenom"] == "Aglaé":
                client.put(f"/api/invites/{i['id']}", json={"jury": True})
    s.tout_le_monde()
    client.post(f"/api/soirees/{s.id}/devoiler")
    client.post(f"/api/soirees/{s.id}/terminer")
    if demi:
        corps = [{"chanson_id": c, "qualifie": k in (0, 1, 2, 4, 5, 7, 8, 9, 10, 11)} for k, c in enumerate(s.chansons)]
    else:
        corps = [{"chanson_id": c, "jury": 120 - 9 * k, "public": 40 + (k * 37) % 90} for k, c in enumerate(s.chansons)]
    client.put(f"/api/soirees/{s.id}/officiel", json={"resultats": corps})
    client.post(f"/api/soirees/{s.id}/cloturer", json={"date_finale": "2027-05-15"} if demi else {})
    return client.get(f"/externe/soirees/{s.id}/journal", headers={"Authorization": "Bearer jeton-exemple"}).json()


def main_():
    for demi, nom in ((False, "journal-exemple.json"), (True, "journal-exemple-demi.json")):
        with tempfile.TemporaryDirectory() as d:
            main.ETAT.clear()
            main.ANNUAIRE = faux_annuaire([{"nom": "Douze points", "locale": "http://192.0.2.10:8088"}])
            main.ETAT["cfg"] = Config(password=MOT_DE_PASSE, data=Path(d), static=Path(d) / "static",
                                      attente_connexion=False, limite_invite=100000)
            with TestClient(main.app) as client:
                j = jouer(client, demi)
            j["le"] = "2027-05-16T10:00:00+02:00"
            (RACINE / "docs" / nom).write_text(json.dumps(j, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(nom, len(json.dumps(j)))


if __name__ == "__main__":
    main_()
