"""1.13.1 : « Douze points ne reconnaît pas les HEIC » (Julien, 22/11/2026). Le logo, la bannière et le poster
refusaient une photo d'iPhone en HEIC (415). Ils l'acceptent maintenant et la rangent en JPEG (lisible partout)."""
import io

from PIL import Image

from app import main
from tests.conftest import Soiree


def heic(largeur=64, hauteur=48) -> bytes:
    import pillow_heif
    pillow_heif.register_heif_opener()
    b = io.BytesIO()
    Image.new("RGB", (largeur, hauteur), "red").save(b, "HEIF")
    return b.getvalue()


def test_logo_en_heic_range_en_jpeg(client):
    s = Soiree(client, ouvrir=False)
    for sorte in ("logo", "banniere", "poster"):
        r = client.put(f"/api/soirees/{s.id}/image/{sorte}", content=heic())
        assert r.status_code == 200, r.text
        nom = r.json()["images"][sorte]
        assert nom.endswith(".jpg")
        lu = client.get(f"/api/soirees/{s.id}/image/{sorte}")
        assert lu.status_code == 200 and lu.content[:3] == b"\xff\xd8\xff"
        with Image.open(io.BytesIO(lu.content)) as im:
            assert im.size == (64, 48)
    # aucun fichier HEIC provisoire ne traîne
    assert not list((main.cfg().data / "images").glob(".*"))


def test_heic_illisible_refuse_proprement(client):
    s = Soiree(client, ouvrir=False)
    faux = b"\x00\x00\x00\x18ftypheic" + b"\x00" * 200
    r = client.put(f"/api/soirees/{s.id}/image/logo", content=faux)
    assert r.status_code == 415 and "HEIC" in r.json()["detail"]
    assert not list((main.cfg().data / "images").glob("*"))


def test_autres_formats_inchanges(client):
    s = Soiree(client, ouvrir=False)
    assert client.put(f"/api/soirees/{s.id}/image/logo", content=b"pas une image").status_code == 415
    assert client.put(f"/api/soirees/{s.id}/image/logo", content=b"\x89PNG\r\n\x1a\n" + b"\x00" * (7 * 1024 * 1024)).status_code == 413
