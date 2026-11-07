def test_phrase_subdomain_is_optional_and_editable(client, auth_headers):
    payload = {"texte": "Demat deoc'h", "theme": "rencontres", "niveau": "A1", "langue": "br"}
    created = client.post("/api/phrases/", headers=auth_headers["admin"], json=payload)
    assert created.status_code == 201
    phrase_id = created.json()["id"]
    assert created.json()["subdomain"] is None

    updated = client.patch(
        f"/api/phrases/{phrase_id}",
        headers=auth_headers["admin"],
        json={"subdomain": "saluer-et-prendre-conge"},
    )
    assert updated.status_code == 200
    assert updated.json()["subdomain"] == "saluer-et-prendre-conge"
    assert client.get(f"/api/phrases/{phrase_id}").json()["subdomain"] == "saluer-et-prendre-conge"
