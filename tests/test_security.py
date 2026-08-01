# tests/test_security.py
from app.security import hash_password, verify_password

def test_password_hash_and_verify():
    hashed = hash_password("mypassword123")
    assert hashed != "mypassword123"  # plain text store nahi ho raha
    assert verify_password("mypassword123", hashed) is True
    assert verify_password("wrongpassword", hashed) is False