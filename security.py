import jwt
from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash
from config import settings 
# Secrets & Algorithm Configuration

# Initialize password hashing engine (pwdlib using recommended algorithms like bcrypt/argon2)
password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hashes a plain-text password."""
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain-text password against a stored hash."""
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    """Generates a signed JWT access token with an expiration time."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
	