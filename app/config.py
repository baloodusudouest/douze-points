"""Réglages lus dans l'environnement du conteneur. Aucune valeur personnelle dans le code.

1.2 : seuls restent ici ce qui tient à l'installation (mot de passe et jeton communs, dossier de données, adresse
de carnet dans la stack). Les réglages d'usage se changent dans l'écran Réglages (voir main.REGLAGES_DEFAUTS).
"""
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
    limite_invite: int = 240         # demandes par minute et par téléphone sur la porte invité
    carnet_url: str = ""             # carnet vu depuis le conteneur ; avec le jeton : invités choisis en tapant leur nom
    carnet_jeton: str = ""           # le jeton commun MAISON_JETON ; vide : carnet n'est pas lu


def charger() -> Config:
    mot_de_passe = maison.mot_de_passe()                            # 1.2 : MAISON_PASSWORD seul
    if len(mot_de_passe) < 12:
        raise SystemExit("MAISON_PASSWORD est absent ou trop court (12 caractères au moins) : "
                         "Douze points ne démarre pas.")
    return Config(
        password=mot_de_passe,
        data=Path(os.environ.get("DOUZE_POINTS_DATA", "/data")),
        static=Path(__file__).parent / "static",
        carnet_url=os.environ.get("DOUZE_POINTS_CARNET_URL", "").strip().rstrip("/"),
        carnet_jeton=maison.jeton_a_envoyer(),                      # 1.2 : MAISON_JETON seul
    )
