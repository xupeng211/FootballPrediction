from src.utils.crypto_utils import CryptoUtils
from unittest.mock import patch
import pytest
import os

pytestmark = pytest.mark.unit
def test_generate_short_id_large_length():
    result = CryptoUtils.generate_short_id(40)
    assert len(result) ==40
def test_hash_string_invalid_algorithm():
    with pytest.raises(ValueError):
        CryptoUtils.hash_string("text[", algorithm = os.getenv("TEST_CRYPTO_UTILS_ALGORITHM_11"))": def test_hash_and_verify_password_fallback():": with patch("]src.utils.crypto_utils.HAS_BCRYPT[", False):": salt = os.getenv("TEST_CRYPTO_UTILS_SALT_11"): hashed = CryptoUtils.hash_password("]secret[", salt=salt)": assert hashed.startswith("]$2b$12$")" assert CryptoUtils.verify_password("secret[", hashed)" assert not CryptoUtils.verify_password("]wrong[", hashed)"]" def test_generate_token_and_salt():""
    token = CryptoUtils.generate_token(4)
    salt = CryptoUtils.generate_salt(4)
    assert len(token) ==8  # hex string length is 2*length
    assert len(salt) ==8