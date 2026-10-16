"""Contract: service information, liveness and CORS."""


def test_root_describes_the_service(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"servicio": "SafeVision AI backend", "docs": "/docs"}


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_configured_frontend_origin_is_allowed(client):
    response = client.options(
        "/api/eventos",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_other_origins_are_not_allowed(client):
    response = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in response.headers
