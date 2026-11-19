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


ATTENTE = 30          # 1.7.1 : secondes d'attente de son tour d'écriture (avant : 10)


def ouvrir(data: Path) -> sqlite3.Connection:
    cx = sqlite3.connect(fichier(data), timeout=ATTENTE)
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
        if "personne_id" not in {r["name"] for r in cx.execute("PRAGMA table_info(invite)")}:   # 1.5 : identifiant maison
            cx.execute("ALTER TABLE invite ADD COLUMN personne_id TEXT")
        # 1.5 : envoi de la soirée vers carnet en attente d'un nouvel essai
        cx.execute("CREATE TABLE IF NOT EXISTS envoi_carnet(soiree_id INTEGER PRIMARY KEY, essais INTEGER NOT NULL DEFAULT 0, "
                   "erreur TEXT NOT NULL DEFAULT '', le TEXT NOT NULL)")
        # 1.8 : le pas automatique du public (heure du dernier changement de pas, pause, dernière régie qui regarde) ;
        # la vignette d'écran d'un selfie de duo
        colonnes = {r["name"] for r in cx.execute("PRAGMA table_info(soiree)")}
        for colonne, sorte in (("pas_le", "REAL"), ("pause_auto", "INTEGER NOT NULL DEFAULT 0"), ("vu_le", "REAL")):
            if colonne not in colonnes:
                cx.execute(f"ALTER TABLE soiree ADD COLUMN {colonne} {sorte}")
        # 1.6 : photos de la soirée, gardées ici jusqu'à leur arrivée complète dans Immich ; album Immich de la soirée
        if "immich_album" not in {r["name"] for r in cx.execute("PRAGMA table_info(soiree)")}:
            cx.execute("ALTER TABLE soiree ADD COLUMN immich_album TEXT")
        cx.execute("CREATE TABLE IF NOT EXISTS photo(id INTEGER PRIMARY KEY, "
                   "soiree_id INTEGER NOT NULL REFERENCES soiree(id) ON DELETE CASCADE, participation_id INTEGER NOT NULL, "
                   "duo_participation_id INTEGER, fichier TEXT NOT NULL, type TEXT NOT NULL, taille INTEGER NOT NULL, "
                   "recue_le TEXT NOT NULL, immich_id TEXT, dans_album INTEGER NOT NULL DEFAULT 0, "
                   "decrite INTEGER NOT NULL DEFAULT 0, taguee INTEGER NOT NULL DEFAULT 0, envoyee_le TEXT, "
                   "essais INTEGER NOT NULL DEFAULT 0, erreur TEXT NOT NULL DEFAULT '')")
        if "ecran" not in {r["name"] for r in cx.execute("PRAGMA table_info(photo)")}:      # 1.8 : vignette pour la télé
            cx.execute("ALTER TABLE photo ADD COLUMN ecran TEXT")
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
    """Une transaction : validée à la sortie, annulée si une erreur remonte.

    1.7.1 : la transaction prend le tour d'écriture dès le début (BEGIN IMMEDIATE) et attend son tour jusqu'à
    ATTENTE secondes. Avant, elle lisait d'abord puis écrivait : quand un autre téléphone avait écrit entre-temps,
    SQLite refusait tout de suite (« database is locked », erreurs 500 avec 7 téléphones qui notent en même temps)."""
    cx = ouvrir(data)
    cx.isolation_level = None            # transactions menées à la main
    try:
        cx.execute("BEGIN IMMEDIATE")
        yield cx
        cx.execute("COMMIT")
    except BaseException:
        if cx.in_transaction:
            cx.execute("ROLLBACK")
        raise
    finally:
        cx.close()


@contextmanager
def lecture(data: Path):
    """1.8 : une lecture seule, sans prendre le tour d'écriture (BEGIN simple). Pour les relectures de chaque seconde
    (télé, téléphones) : elles ne font plus la queue derrière les écritures. Ne jamais écrire dedans."""
    cx = ouvrir(data)
    cx.isolation_level = None
    try:
        cx.execute("BEGIN")
        yield cx
    finally:
        if cx.in_transaction:
            cx.execute("ROLLBACK")
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
