"""Security regression tests for the pre-launch security audit fixes."""

import base64
import hashlib
import hmac
import json
import time

import pytest

from app.core.ssrf import validate_public_url, SSRFError, safe_parse_xml
from app.api.auth import _verify_hs256


def _make_jwt(claims: dict, secret: str, alg: str = "HS256") -> str:
    def seg(obj):
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()
    header = seg({"alg": alg, "typ": "JWT"})
    payload = seg(claims)
    sig = base64.urlsafe_b64encode(
        hmac.new(secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    ).rstrip(b"=").decode()
    return f"{header}.{payload}.{sig}"


class TestJWTVerification:
    SECRET = "test-jwt-secret"

    def test_valid_token_accepted(self):
        tok = _make_jwt({"sub": "u1", "email": "a@b.com", "exp": time.time() + 99}, self.SECRET)
        assert _verify_hs256(tok, self.SECRET)["sub"] == "u1"

    def test_bad_signature_rejected(self):
        tok = _make_jwt({"sub": "u1", "exp": time.time() + 99}, self.SECRET)
        with pytest.raises(ValueError):
            _verify_hs256(tok, "wrong-secret")

    def test_alg_none_forgery_rejected(self):
        header = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode()
        payload = base64.urlsafe_b64encode(b'{"sub":"admin","role":"service"}').rstrip(b"=").decode()
        forged = f"{header}.{payload}."
        with pytest.raises(ValueError):
            _verify_hs256(forged, self.SECRET)

    def test_expired_token_rejected(self):
        tok = _make_jwt({"sub": "u1", "exp": time.time() - 10}, self.SECRET)
        with pytest.raises(ValueError):
            _verify_hs256(tok, self.SECRET)

    def test_missing_exp_rejected(self):
        tok = _make_jwt({"sub": "u1"}, self.SECRET)
        with pytest.raises(ValueError):
            _verify_hs256(tok, self.SECRET)


class TestSSRF:
    @pytest.mark.parametrize("url", [
        "http://169.254.169.254/latest/meta-data/",
        "http://localhost:6379/",
        "http://127.0.0.1/admin",
        "http://10.0.0.5/",
        "http://192.168.1.1/",
        "http://[::1]/",
        "file:///etc/passwd",
        "gopher://x/",
        "https://example.com:22/",
    ])
    def test_internal_and_bad_urls_blocked(self, url):
        with pytest.raises(SSRFError):
            validate_public_url(url)

    def test_public_url_allowed(self):
        assert validate_public_url("https://example.com/")


class TestXMLGuard:
    def test_billion_laughs_blocked(self):
        payload = (b'<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">'
                   b'<!ENTITY lol2 "&lol;&lol;">]><r>&lol2;</r>')
        with pytest.raises(SSRFError):
            safe_parse_xml(payload)

    def test_xxe_doctype_blocked(self):
        payload = (b'<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM '
                   b'"file:///etc/passwd">]><r>&xxe;</r>')
        with pytest.raises(SSRFError):
            safe_parse_xml(payload)

    def test_clean_xml_parses(self):
        root = safe_parse_xml(b'<?xml version="1.0"?><rss><channel><item>x</item></channel></rss>')
        assert root.find(".//item").text == "x"


class TestEdgeTokenValidation:
    def test_public_edge_config_rejects_injection_token(self):
        from fastapi.testclient import TestClient
        from app.main import app
        c = TestClient(app)
        r = c.get("/edge/v1/config", params={"token": "or_x&or=(id.gte.0)", "url": "/"})
        assert r.status_code == 400
        r2 = c.get("/edge/v1/config", params={"token": "or_abcDEF123", "url": "/"})
        assert r2.status_code == 200 and r2.json() == {"directives": []}


class TestSecurityHeaders:
    def test_headers_present(self):
        from fastapi.testclient import TestClient
        from app.main import app
        c = TestClient(app)
        r = c.get("/edge/v1/omnirank.js")
        assert r.headers.get("X-Content-Type-Options") == "nosniff"
        assert r.headers.get("X-Frame-Options") == "DENY"
