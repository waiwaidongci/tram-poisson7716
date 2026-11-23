import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
import jwt
from src.config.settings import JWT_SECRET


def digest(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 210_000).hex()


def hash_password(password):
    salt = secrets.token_hex(16)
    return f'{salt}${digest(password, salt)}'


def matches(password, encoded):
    salt, expected = encoded.split('$', maxsplit=1)
    return hmac.compare_digest(digest(password, salt), expected)


def token(username, role):
    timestamp = datetime.now(UTC)
    return jwt.encode({'sub': username, 'role': role, 'iat': timestamp,
                       'exp': timestamp + timedelta(hours=8)}, JWT_SECRET, algorithm='HS256')


def subject(encoded):
    return jwt.decode(encoded, JWT_SECRET, algorithms=['HS256'], options={'require': ['sub', 'exp']})['sub']
