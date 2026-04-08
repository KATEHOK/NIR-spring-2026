import base64
import os
import secrets
import jwt
import bcrypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
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
    fast_refresh_token_expire_minutes: int = settings.FAST_REFRESH_TOKEN_EXPIRE_MINUTES

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

    @classmethod
    def issue_refresh_token(cls, fast: bool = False) -> tuple[str, datetime]:
        """Выпускает Refresh-токен (коротко или долгоживущий, вернет (token, exp))"""
        now = datetime.now(timezone.utc)
        token_expire_minutes = cls.fast_refresh_token_expire_minutes if fast else cls.refresh_token_expire_minutes
        return Random.urlsafe(32), now + timedelta(minutes=token_expire_minutes)


class SymmetricEncryption:
    """Симметричное шифрование (AES-256-GCM, по умолчанию на основе SECRET_KEY)"""

    @staticmethod
    def make_aesgcm(key: str) -> AESGCM:
        """Создает 32-байтовый ключ из строчного, на его основе создает шифратор"""
        key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"auth_symmetric_encryption",
        ).derive(key.encode('utf-8'))
        return AESGCM(key)

    app_aesgcm: AESGCM = make_aesgcm(settings.SECRET_KEY)

    @classmethod
    def encrypt(cls, plain: bytes, key: str = None) -> bytes:
        """Шифрует данные. Возвращает nonce(12) + ciphertext"""
        aesgcm = cls.make_aesgcm(key) if key is not None else cls.app_aesgcm
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plain, None)
        return nonce + ciphertext

    @classmethod
    def decrypt(cls, encrypted: bytes, key: str = None) -> bytes:
        """Расшифровывает данные (ожидается nonce(12) + ciphertext)"""
        if len(encrypted) < 12:
            raise ValueError("Encrypted data too short (missing nonce)")
        aesgcm = cls.make_aesgcm(key) if key is not None else cls.app_aesgcm
        nonce = encrypted[:12]
        ciphertext = encrypted[12:]
        return aesgcm.decrypt(nonce, ciphertext, None)


class Random:
    """Генерирует рандомные данные"""

    @staticmethod
    def bytes(length: int = 32) -> bytes:
        """Генерирует случайные байты заданной длины (по умолчанию 32)."""
        return secrets.token_bytes(length)

    @staticmethod
    def hex(length: int = 32) -> str:
        """Генерирует случайную hex-строку (длина строки = 2 * length)."""
        return secrets.token_hex(length)

    @staticmethod
    def urlsafe(length: int = 32) -> str:
        """Генерирует случайную строку в формате base64 (URL-safe)."""
        return secrets.token_urlsafe(length)

    @staticmethod
    def base32(length: int = 16) -> str:
        """
        Генерирует случайную строку в формате Base32 (без padding).
        По умолчанию length=16 байт -> 26 символов Base32.
        """
        random_bytes = secrets.token_bytes(length)
        return base64.b32encode(random_bytes).decode('utf-8').rstrip('=')