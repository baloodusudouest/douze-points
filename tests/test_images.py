"""Les images de l'évènement : logo, bannière, poster déposés par l'hôte."""
from tests.conftest import connecter

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 64


def test_deposer_lire_remplacer_retirer(client, soiree, tmp_path):
    base = f"/api/soirees/{soiree.id}"
    assert client.get(base).json()["images"] == {"logo": None, "banniere": None, "poster": None, "apero": None}
    for sorte, contenu, type_mime in (("logo", PNG, "image/png"), ("banniere", JPEG, "image/jpeg"), ("poster", WEBP, "image/webp")):
        assert client.put(f"{base}/image/{sorte}", content=contenu).status_code == 200
        r = client.get(f"{base}/image/{sorte}")
        assert r.status_code == 200 and r.content == contenu and r.headers["content-type"] == type_mime
    premier = client.get(base).json()["images"]["logo"]
    client.put(f"{base}/image/logo", content=JPEG)
    second = client.get(base).json()["images"]["logo"]
    assert second != premier and second.endswith(".jpg")              # le nom change : les écrans rechargent
    assert not (tmp_path / "images" / premier).exists()               # l'ancien fichier est retiré
    assert client.delete(f"{base}/image/logo").status_code == 200
    assert client.get(base).json()["images"]["logo"] is None and client.get(f"{base}/image/logo").status_code == 404
    assert not (tmp_path / "images" / second).exists()


def test_refus(client, soiree):
    base = f"/api/soirees/{soiree.id}/image"
    assert client.put(f"{base}/logo", content=b"<svg xmlns='http://www.w3.org/2000/svg'><script/></svg>").status_code == 415
    assert client.put(f"{base}/logo", content=b"pas une image").status_code == 415
    assert client.put(f"{base}/logo", content=PNG + b"\x00" * (6 * 1024 * 1024)).status_code == 413
    assert client.put(f"{base}/fond", content=PNG).status_code == 404
    client.cookies.clear()
    assert client.put(f"{base}/logo", content=PNG).status_code == 401
    assert client.get(f"{base}/logo").status_code == 401


def test_les_invites_voient_les_images_par_leur_lien(client, soiree):
    client.put(f"/api/soirees/{soiree.id}/image/poster", content=PNG)
    client.cookies.clear()
    etat = client.get(soiree.url("etat")).json()
    assert etat["images"]["poster"] and etat["images"]["logo"] is None
    r = client.get(f"/invite/{soiree.jeton}/image/poster")
    assert r.status_code == 200 and r.content == PNG
    assert client.get(f"/invite/{soiree.jeton}/image/logo").status_code == 404
    assert client.get("/invite/pas-le-bon/image/poster").status_code == 404
    assert client.get(f"/invite/{soiree.jeton}/image/../douze-points.db").status_code in (404, 405)
