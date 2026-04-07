import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from src.config import settings


class Password:
    """Работа с паролем (хеширование и верификация)"""

    @staticmethod
    def hash(password: str) -> bytes:
        """Хэширует пароль"""
        return bcrypt.hashpw(
            password=password.encode(),
            salt=bcrypt.gensalt()
        )

    @staticmethod
    def verify(password: str, hashed_password: bytes) -> bool:
        """Проверяет пароль (сравнивает с хэшем)"""
        return bcrypt.checkpw(
            password=password.encode(),
            hashed_password=hashed_password
        )


class JWT:
    """Работа с JWT (кодирование, декодирование, выпуск)"""
    algorithm: str = settings.JWT_ALGORITHM
    private_key: str = settings.JWT_PRIVATE_KEY
    public_key: str = settings.JWT_PUBLIC_KEY
    access_token_expire_minutes: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    refresh_token_expire_minutes: int = settings.REFRESH_TOKEN_EXPIRE_MINUTES

    @classmethod
    def encode(cls, payload: dict) -> str:
        """Кодирует JWT"""
        return jwt.encode(payload, cls.private_key, cls.algorithm)

    @classmethod
    def decode(cls, token: str) -> dict:
        """Декодирует JWT"""
        return jwt.decode(token, cls.public_key, [cls.algorithm])

    @classmethod
    def issue_access_token(cls, user_id: int, refresh_token_id: int) -> str:
        """Выпускает Access-токен"""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "refresh_id": str(refresh_token_id),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=cls.access_token_expire_minutes)).timestamp()),
            "type": "access"
        }
        return cls.encode(payload)
