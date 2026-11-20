"""1.8 : la vignette d'écran d'un selfie de duo, montrée sur la télé (écran des jumeaux de vote).

Un selfie d'iPhone pèse plusieurs mégaoctets et arrive parfois en HEIC, que le navigateur d'une télé ne lit pas
(conseil 1.8.0). À la réception, on en fait une copie JPEG réduite, tournée dans le bon sens. L'original part à Immich
comme avant ; la vignette reste sur le NAS jusqu'à l'archivage de la soirée."""
from __future__ import annotations

import logging
from pathlib import Path

COTE = 1600          # plus grand côté, en pixels
QUALITE = 82

try:
    from PIL import Image, ImageOps
except ImportError:  # pragma: no cover — image sans Pillow : pas de vignette, la carte garde « 📸 immortalisés »
    Image = None

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception:  # noqa: BLE001 — pas de HEIC : JPEG, PNG et WebP restent lus
    pass


def vignette(source: Path, cible: Path, cote: int = COTE) -> bool:
    """Écrit `cible` (JPEG réduit à `cote` px) d'après `source`. Rend False si l'image ne se lit pas : jamais d'erreur.
    1.9 : sert aussi à la photo apéro (2400 px)."""
    if Image is None:
        return False
    try:
        with Image.open(source) as im:
            im = ImageOps.exif_transpose(im)
            im.thumbnail((cote, cote))
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            provisoire = cible.with_name("." + cible.name + ".part")
            im.save(provisoire, "JPEG", quality=QUALITE, optimize=True)
            provisoire.replace(cible)
        return True
    except Exception as e:  # noqa: BLE001
        logging.getLogger("douze-points").warning("Vignette d'écran impossible : %s", type(e).__name__)
        return False
