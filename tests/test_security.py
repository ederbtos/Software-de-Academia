from app.core.security import create_access_token, decode_token


def test_jwt_roundtrip():
    token = create_access_token({"sub": 10, "scope": "tenant", "role": "admin", "schema": "academia_fit"})
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "10"
    assert payload["scope"] == "tenant"
    assert payload["schema"] == "academia_fit"
