def test_unknown_route_uses_error_envelope(client):
    response = client.get("/api/no-existe")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["codigo"] == "RECURSO_NO_ENCONTRADO"
    assert "mensaje" in body["error"]
    assert body["error"]["detalles"] == []
