"""1.13.1 : toucher un invité attendu ne relit plus toute la soirée ; la réponse du PUT donne la liste à jour."""
from tests.conftest import Soiree


def test_put_attendus_rend_la_liste(client):
    s = Soiree(client, ouvrir=False)
    ids = [i["id"] for i in client.get("/api/invites").json()]
    r = client.put(f"/api/soirees/{s.id}/attendus", json={"invites": ids[:2]})
    assert r.status_code == 200 and len(r.json()["participants"]) == 2
    assert len(client.get(f"/api/soirees/{s.id}").json()["participants"]) == 2
