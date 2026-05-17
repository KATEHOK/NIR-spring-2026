import base64
import hashlib
import os
import secrets
import jwt
import bcrypt
import asyncio
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from datetime import datetime, timedelta
from src.utils import datetime_utcnow
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

    @classmethod
    async def async_hash(cls, password: str) -> bytes:
        """Вызывает хэширование пароля (в отдельном потоке)"""
        return await asyncio.to_thread(cls.hash, password)

    @classmethod
    async def async_verify(cls, password: str, hashed_password: bytes) -> bool:
        """Вызывает проверку пароля (в отдельном потоке)"""
        return await asyncio.to_thread(cls.verify, password, hashed_password)



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
        now_aware = datetime_utcnow(False)
        payload = {
            "sub": str(user_id),
            "rid": str(refresh_token_id),
            "iat": int(now_aware.timestamp()),
            "exp": int((now_aware + timedelta(minutes=cls.access_token_expire_minutes)).timestamp()),
            "type": "access"
        }
        return cls.encode(payload)

    @classmethod
    def issue_refresh_token(cls) -> tuple[str, datetime]:
        """Выпускает Refresh-токен (вернет (token, exp))"""
        return Random.urlsafe(32), datetime_utcnow() + timedelta(minutes=cls.refresh_token_expire_minutes)


class SymmetricEncryption:
    """Симметричное шифрование (AES-256-GCM, по умолчанию на основе SECRET_KEY)"""

    @staticmethod
    def make_aesgcm(key: bytes) -> AESGCM:
        key = hashlib.sha256(key).digest()
        return AESGCM(key)

    app_aesgcm: AESGCM = make_aesgcm(settings.SECRET_KEY.encode("utf-8"))

    @classmethod
    def encrypt(cls, plain: bytes, key: bytes = None) -> bytes:
        """Шифрует данные. Возвращает nonce(12) + ciphertext"""
        aesgcm = cls.make_aesgcm(key) if key is not None else cls.app_aesgcm
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plain, None)
        return nonce + ciphertext

    @classmethod
    def decrypt(cls, encrypted: bytes, key: bytes = None) -> bytes:
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

    @classmethod
    def base32(cls, length: int = 16) -> str:
        """
        Генерирует случайную строку в формате Base32 (без padding).
        По умолчанию length=16 байт -> 26 символов Base32.
        """
        random_bytes = cls.bytes(length)
        return base64.b32encode(random_bytes).decode('utf-8').rstrip('=')

    @classmethod
    def session_id(cls):
        return cls.urlsafe(32)
