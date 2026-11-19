"""1.8.0 : le selfie d'un duo gagne une vignette d'écran (JPEG réduit, tourné), montrée sur la télé ; effacée à
l'archivage. Les autres photos de la soirée n'en ont pas et ne sont jamais servies à la régie."""
import io

from PIL import Image

from app import main
from tests.test_photos_16 import JPEG, devoilee, envoyer, faux  # noqa: F401 — fixture


def vraie_photo(l=3000, h=2000, sens=6):
    im = Image.new("RGB", (l, h), (229, 85, 159))
    exif = Image.Exif()
    exif[0x0112] = sens                       # 6 : l'iPhone l'a prise en portrait
    sortie = io.BytesIO()
    im.save(sortie, "JPEG", exif=exif, quality=90)
    return sortie.getvalue()


def duo_de(client, soiree):
    tele = client.get(f"/api/soirees/{soiree.id}/jumeaux").json()
    duo = tele["duos"][0]
    a, b = duo["invites"]
    pa = next(p for p, i in soiree.part.items() if i == a["id"])
    return duo, pa, b


def test_vignette_du_selfie_de_duo(client, soiree, faux):  # noqa: F811
    devoilee(client, soiree)
    duo, pa, b = duo_de(client, soiree)
    assert duo["photo"] is None
    assert envoyer(client, soiree, pa, vraie_photo(), duo=b["id"]).status_code == 200
    duo = client.get(f"/api/soirees/{soiree.id}/jumeaux").json()["duos"][0]
    assert duo["photos"] == 1 and duo["photo"]
    r = client.get(f"/api/soirees/{soiree.id}/photos/{duo['photo']}")
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    im = Image.open(io.BytesIO(r.content))
    assert im.size == (1067, 1600)            # réduite à 1600 px et tournée en portrait
    main.envoyer_photos()                     # l'original part à Immich et quitte le NAS ; la vignette reste
    assert client.get(f"/api/soirees/{soiree.id}/photos/{duo['photo']}").status_code == 200
    assert client.post(f"/api/soirees/{soiree.id}/archiver").status_code == 200
    assert client.get(f"/api/soirees/{soiree.id}/photos/{duo['photo']}").status_code == 404
    assert not list((main.cfg().data / "photos" / str(soiree.id)).glob("*.ecran.jpg"))


def test_photo_illisible_ou_hors_duo(client, soiree, faux):  # noqa: F811
    devoilee(client, soiree)
    duo, pa, b = duo_de(client, soiree)
    assert envoyer(client, soiree, pa, JPEG, duo=b["id"]).status_code == 200      # tronquée : reçue, sans vignette
    duo = client.get(f"/api/soirees/{soiree.id}/jumeaux").json()["duos"][0]
    assert duo["photos"] == 1 and duo["photo"] is None
    assert envoyer(client, soiree, pa, vraie_photo()).status_code == 200          # photo de la soirée, pas de duo
    with main.base(main.cfg().data) as cx:
        ids = [r["id"] for r in cx.execute("SELECT id FROM photo WHERE soiree_id=?", (soiree.id,))]
    assert all(client.get(f"/api/soirees/{soiree.id}/photos/{i}").status_code == 404 for i in ids)


def test_nettoyage_au_demarrage_garde_les_vignettes(client, soiree, faux):  # noqa: F811
    devoilee(client, soiree)
    duo, pa, b = duo_de(client, soiree)
    envoyer(client, soiree, pa, vraie_photo(), duo=b["id"])
    main.nettoyer_photos()
    duo = client.get(f"/api/soirees/{soiree.id}/jumeaux").json()["duos"][0]
    assert client.get(f"/api/soirees/{soiree.id}/photos/{duo['photo']}").status_code == 200
