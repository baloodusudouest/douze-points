"""Réglages lus dans l'environnement du conteneur. Aucune valeur personnelle dans le code."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

APPLI = "douze-points"
NOM = "Douze points"


@dataclass(frozen=True)
class Config:
    password: str
    data: Path
    static: Path
    attente_connexion: bool = True   # délai anti-essais ; coupé dans les tests
    adresse: str = ""                # adresse de l'appli vue par les téléphones des invités (QR code, lien)
    ha_webhook: str = ""             # adresse de Home Assistant appelée quand tous ont envoyé ; vide : rien
    limite_invite: int = 240         # demandes par minute et par téléphone sur la porte invité


def charger() -> Config:
    mot_de_passe = os.environ.get("DOUZE_POINTS_PASSWORD", "")
    if len(mot_de_passe) < 12:
        raise SystemExit("DOUZE_POINTS_PASSWORD est absent ou trop court (12 caractères au moins) : "
                         "Douze points ne démarre pas.")
    return Config(
        password=mot_de_passe,
        data=Path(os.environ.get("DOUZE_POINTS_DATA", "/data")),
        static=Path(__file__).parent / "static",
        adresse=os.environ.get("DOUZE_POINTS_ADRESSE", "").strip().rstrip("/"),
        ha_webhook=os.environ.get("DOUZE_POINTS_HA_WEBHOOK", "").strip(),
    )
