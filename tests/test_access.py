from app.core.security.headers import CSP


def test_without_owner_every_page_leads_to_setup(client):
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/setup")


def test_health_is_public(client):
    assert client.get("/health").get_json() == {"status": "ok"}


def test_signed_out_owner_is_sent_to_login(client, owner):
    response = client.get("/account/security")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_api_answers_json_401_when_signed_out(client, owner):
    response = client.get("/account/security", headers={"Accept": "application/json"})
    assert response.status_code == 401
    assert response.get_json() == {"error": "Authentication required."}


def test_unknown_page_is_404_once_signed_in(signed_in):
    assert signed_in.get("/does-not-exist").status_code == 404


def test_security_headers_on_every_page(client, owner):
    response = client.get("/login")
    assert response.headers["Content-Security-Policy"] == CSP
    assert "unsafe-inline" not in CSP and "unsafe-eval" not in CSP
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Cache-Control"] == "no-store"


def test_pages_have_no_inline_script_or_style(signed_in):
    for path in ("/", "/account/security"):
        html = signed_in.get(path).get_data(as_text=True)
        assert "<script>" not in html and "style=" not in html and "<style" not in html


def test_static_urls_are_versioned(signed_in):
    html = signed_in.get("/").get_data(as_text=True)
    assert "/static/css/core/tokens.css?v=" in html
