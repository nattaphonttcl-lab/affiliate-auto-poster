from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import Settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    *,
    subject: str,
    settings: Settings,
    extra_claims: dict[str, object] | None = None,
) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, object] = {"sub": subject, "exp": expire}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token_payload(
    *, token: str, settings: Settings
) -> dict[str, object] | None:
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError:
        return None

    if not isinstance(payload, dict):
        return None

    return payload


def decode_access_token(*, token: str, settings: Settings) -> str | None:
    payload = decode_access_token_payload(token=token, settings=settings)
    if payload is None:
        return None

    subject = payload.get("sub")
    if not isinstance(subject, str):
        return None

    return subject
