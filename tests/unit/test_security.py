from app.core import security


def test_password_hash_roundtrip():
    hashed = security.hash_password("correct horse")
    assert hashed != "correct horse"
    assert security.verify_password("correct horse", hashed)
    assert not security.verify_password("wrong horse", hashed)


def test_verify_password_rejects_broken_hash():
    assert not security.verify_password("anything", "not-a-valid-hash")


def test_session_tokens_are_random_and_hashed():
    a, b = security.generate_session_token(), security.generate_session_token()
    assert a != b
    assert len(a) >= 40
    assert security.hash_session_token(a) == security.hash_session_token(a)
    assert security.hash_session_token(a) != a
