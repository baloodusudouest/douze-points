"""Réglages lus dans l'environnement du conteneur. Aucune valeur personnelle dans le code."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from . import maison

APPLI = "douze-points"
NOM = "Douze points"


@dataclass(frozen=True)
class Config:
    password: str
    data: Path
    static: Path
    attente_connexion: bool = True   # délai anti-essais ; coupé dans les tests
    adresse: str = ""                # repli de l'adresse vue par les téléphones des invités (QR code, lien) ;
                                     # 1.1 : l'adresse locale de la tuile « Douze points » de l'Anneau passe d'abord
    ha_webhook: str = ""             # adresse de Home Assistant appelée quand tous ont envoyé ; vide : rien
    limite_invite: int = 240         # demandes par minute et par téléphone sur la porte invité
    carnet_url: str = ""             # carnet vu depuis le conteneur ; avec le jeton : invités choisis en tapant leur nom
    carnet_jeton: str = ""           # DOUZE_POINTS_CARNET_JETON (même valeur que CARNET_JETON_DOUZE_POINTS côté carnet),
                                     # sinon MAISON_JETON (1.1) ; vide : carnet n'est pas lu


def charger() -> Config:
    mot_de_passe = maison.mot_de_passe("DOUZE_POINTS_PASSWORD")     # 1.1 : MAISON_PASSWORD, repli sur l'ancien nom
    if len(mot_de_passe) < 12:
        raise SystemExit("MAISON_PASSWORD (ou DOUZE_POINTS_PASSWORD) est absent ou trop court (12 caractères au moins) : "
                         "Douze points ne démarre pas.")
    return Config(
        password=mot_de_passe,
        data=Path(os.environ.get("DOUZE_POINTS_DATA", "/data")),
        static=Path(__file__).parent / "static",
        adresse=os.environ.get("DOUZE_POINTS_ADRESSE", "").strip().rstrip("/"),
        ha_webhook=os.environ.get("DOUZE_POINTS_HA_WEBHOOK", "").strip(),
        carnet_url=os.environ.get("DOUZE_POINTS_CARNET_URL", "").strip().rstrip("/"),
        carnet_jeton=maison.jeton_a_envoyer("DOUZE_POINTS_CARNET_JETON"),   # 1.1 : l'ancien d'abord, puis MAISON_JETON
    )
