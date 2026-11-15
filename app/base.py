"""La base SQLite de Douze points : une connexion par appel, mode WAL."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

CONCOURS_DE_DEPART = ("Eurovision", "Eurovision Asia")

SCHEMA = """
CREATE TABLE IF NOT EXISTS soiree(
  id INTEGER PRIMARY KEY, concours TEXT NOT NULL, annee INTEGER NOT NULL, emission TEXT NOT NULL,
  date TEXT, nom TEXT NOT NULL, logo TEXT,
  etat TEXT NOT NULL DEFAULT 'brouillon',          -- brouillon, ouverte, devoilement, devoilee, archivee
  jeton_invite TEXT NOT NULL UNIQUE, chanson_en_cours INTEGER,
  mode_devoilement TEXT NOT NULL DEFAULT 'court', ordre_devoilement TEXT, pas_devoilement INTEGER NOT NULL DEFAULT 0,
  forcee INTEGER NOT NULL DEFAULT 0, tous_envoye_le TEXT, cree_le TEXT NOT NULL, ouverte_le TEXT, devoilee_le TEXT);
CREATE TABLE IF NOT EXISTS chanson(
  id INTEGER PRIMARY KEY, soiree_id INTEGER NOT NULL REFERENCES soiree(id) ON DELETE CASCADE,
  ordre INTEGER NOT NULL, pays TEXT NOT NULL, code_pays TEXT, artiste TEXT, titre TEXT,
  rang_officiel INTEGER, qualifie INTEGER);
CREATE TABLE IF NOT EXISTS invite(
  id INTEGER PRIMARY KEY, prenom TEXT NOT NULL, actif INTEGER NOT NULL DEFAULT 1, cree_le TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS participation(
  id INTEGER PRIMARY KEY, soiree_id INTEGER NOT NULL REFERENCES soiree(id) ON DELETE CASCADE,
  invite_id INTEGER NOT NULL REFERENCES invite(id), jeton_telephone TEXT,
  etat TEXT NOT NULL DEFAULT 'attendu',            -- attendu, en_cours, envoye, ecarte
  classement_main INTEGER NOT NULL DEFAULT 0, arrive_le TEXT, envoye_le TEXT,
  UNIQUE(soiree_id, invite_id));
CREATE TABLE IF NOT EXISTS note(
  participation_id INTEGER NOT NULL REFERENCES participation(id) ON DELETE CASCADE,
  chanson_id INTEGER NOT NULL REFERENCES chanson(id) ON DELETE CASCADE,
  valeur INTEGER NOT NULL, commentaire TEXT NOT NULL DEFAULT '', modifie_le TEXT NOT NULL,
  PRIMARY KEY(participation_id, chanson_id));
CREATE TABLE IF NOT EXISTS classement(
  participation_id INTEGER NOT NULL REFERENCES participation(id) ON DELETE CASCADE,
  chanson_id INTEGER NOT NULL REFERENCES chanson(id) ON DELETE CASCADE, rang INTEGER NOT NULL,
  PRIMARY KEY(participation_id, chanson_id));
CREATE TABLE IF NOT EXISTS points(
  soiree_id INTEGER NOT NULL REFERENCES soiree(id) ON DELETE CASCADE,
  participation_id INTEGER NOT NULL, chanson_id INTEGER NOT NULL, rang INTEGER NOT NULL, points INTEGER NOT NULL,
  PRIMARY KEY(participation_id, chanson_id));
CREATE TABLE IF NOT EXISTS reglage(
  cle TEXT PRIMARY KEY, valeur TEXT NOT NULL);      -- 1.0 : réglages de l'appli (pas de la note…)
CREATE TABLE IF NOT EXISTS concours(
  id INTEGER PRIMARY KEY, nom TEXT NOT NULL UNIQUE COLLATE NOCASE, actif INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS alias_pays(
  cle TEXT PRIMARY KEY, code TEXT NOT NULL);         -- 0.9 : un nom de pays inconnu, relié à un pays par l'hôte
CREATE TABLE IF NOT EXISTS journal(
  id INTEGER PRIMARY KEY, date TEXT NOT NULL, action TEXT NOT NULL, cible TEXT, detail TEXT);
"""


def fichier(data: Path) -> Path:
    return data / "douze-points.db"


def ouvrir(data: Path) -> sqlite3.Connection:
    cx = sqlite3.connect(fichier(data), timeout=10)
    cx.row_factory = sqlite3.Row
    cx.execute("PRAGMA journal_mode=WAL")
    cx.execute("PRAGMA foreign_keys=ON")
    return cx


def preparer(data: Path) -> None:
    cx = ouvrir(data)
    try:
        cx.executescript(SCHEMA)
        # 0.3 : images de l'évènement. `logo` existait ; bannière et poster s'ajoutent aux bases déjà créées.
        colonnes = {r["name"] for r in cx.execute("PRAGMA table_info(soiree)")}
        for colonne in ("banniere", "poster", "ville"):      # 0.4 : ville où le concours est organisé
            if colonne not in colonnes:
                cx.execute(f"ALTER TABLE soiree ADD COLUMN {colonne} TEXT")
        # 0.4 : la liste des concours se règle dans l'appli. Une base neuve part avec ces deux-là.
        # 0.5 : un invité choisi dans carnet garde le numéro de sa fiche (jamais son nom complet)
        if "carnet_id" not in {r["name"] for r in cx.execute("PRAGMA table_info(invite)")}:
            cx.execute("ALTER TABLE invite ADD COLUMN carnet_id TEXT")
        # 0.5 : jury ou public. `invite.jury` se règle dans l'appli ; `participation.jury` est figé au dévoilement.
        for table in ("invite", "participation"):
            if "jury" not in {r["name"] for r in cx.execute(f"PRAGMA table_info({table})")}:
                cx.execute(f"ALTER TABLE {table} ADD COLUMN jury INTEGER NOT NULL DEFAULT 0")
        # 0.5 : les vrais votes du concours, saisis après coup (points du jury et du public pour chaque chanson)
        for colonne in ("officiel_jury", "officiel_public"):
            if colonne not in {r["name"] for r in cx.execute("PRAGMA table_info(chanson)")}:
                cx.execute(f"ALTER TABLE chanson ADD COLUMN {colonne} INTEGER")
        # 1.0 : les notes passent des demi-points aux quarts de point (le pas de la note se règle : 1, ½ ou ¼).
        # Faite une seule fois : la ligne « echelle_notes » le retient.
        if not cx.execute("SELECT 1 FROM reglage WHERE cle='echelle_notes'").fetchone():
            cx.execute("UPDATE note SET valeur = valeur * 2")
            cx.execute("INSERT INTO reglage(cle, valeur) VALUES('echelle_notes', '4')")
        cx.execute("INSERT OR IGNORE INTO reglage(cle, valeur) VALUES('pas_note', '0.5')")
        if not cx.execute("SELECT 1 FROM concours").fetchone():
            cx.executemany("INSERT INTO concours(nom) VALUES(?)", [(nom,) for nom in CONCOURS_DE_DEPART])
        cx.commit()
    finally:
        cx.close()


@contextmanager
def base(data: Path):
    """Une transaction : validée à la sortie, annulée si une erreur remonte."""
    cx = ouvrir(data)
    try:
        yield cx
        cx.commit()
    except BaseException:
        cx.rollback()
        raise
    finally:
        cx.close()


def sauvegarder(data: Path, nom: str) -> Path:
    """Copie cohérente de la base (API de sauvegarde de SQLite), faite au lancement d'un dévoilement."""
    dossier = data / "sauvegardes"
    dossier.mkdir(parents=True, exist_ok=True)
    cible = dossier / nom
    source, copie = ouvrir(data), sqlite3.connect(cible)
    try:
        source.backup(copie)
    finally:
        copie.close()
        source.close()
    return cible
