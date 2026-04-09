from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.common.config import settings


def hash_password(password: str) -> str:
    """
    Hashes a password using bcrypt.
    Bcrypt handles salting automatically.
    """
    # 1. Convert the plain-text string to bytes (utf-8)
    pwd_bytes = password.encode("utf-8")

    # 2. Generate a salt and hash the password
    # default rounds is 12, which is the current industry balance for speed/security
    hashed_bytes = bcrypt.hashpw(pwd_bytes, bcrypt.gensalt())

    # 3. Return as a string so it can be stored in the SQLite String column
    return hashed_bytes.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Checks if a plain-text password matches the stored hash.
    """
    # Convert both to bytes for the comparison
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")

    # bcrypt.checkpw extracts the salt from the hash automatically
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """
    Creates a signed JWT. The 'data' dict usually contains
    the username as the 'sub' (subject) claim.
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})

    # Sign the token with your SECRET_KEY from .env
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict | None:
    """
    Decodes and validates a token. Returns the payload if valid,
    otherwise returns None.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None
