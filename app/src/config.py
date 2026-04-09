import os


def read_secret(env_var_name: str) -> str:
    """Читает секрет из файла, путь к которому указан в переменной окружения."""
    file_path = os.getenv(env_var_name)
    if not file_path:
        raise ValueError(f"Environment variable {env_var_name} is not set")
    try:
        with open(file_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"Secret file not found at {file_path}")


class Settings:
    def __init__(self):
        # Секреты
        self.DB_PASSWORD: str = read_secret("DB_PASSWORD_FILE")
        self.SECRET_KEY: str = read_secret("SECRET_KEY_FILE")

        # Секреты (временно)
        # self.DB_PASSWORD: str = "secret"
        # self.SECRET_KEY: str = "secret"

        # База данных (несекретные параметры)
        self.DB_HOST: str = os.getenv("DB_HOST")
        self.DB_PORT: int = int(os.getenv("DB_PORT"))
        self.DB_USER: str = os.getenv("DB_USER")
        self.DB_NAME: str = os.getenv("DB_NAME")

        # Сервер
        self.SERVER_PORT: int = int(os.getenv("SERVER_PORT"))
        self.SERVER_IP: str = os.getenv("SERVER_IP")
        cors_str: str = os.getenv("SERVER_CORS")
        self.SERVER_CORS: list[str] = [origin.strip() for origin in cors_str.split(",") if origin.strip()]

        # Fault limiting (ограничение количества ошибок)
        self.BAN_PERIOD: int = int(os.getenv("BAN_PERIOD"))
        self.FAULT_LIMIT: int = int(os.getenv("FAULT_LIMIT"))
        self.FAULT_LIMIT_UPDATE_PERIOD: int = int(os.getenv("FAULT_LIMIT_UPDATE_PERIOD"))

        # JWT
        self.JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM")
        self.JWT_PUBLIC_KEY: str = read_secret("JWT_PUBLIC_KEY_FILE")
        self.JWT_PRIVATE_KEY: str = read_secret("JWT_PRIVATE_KEY_FILE")
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
        self.REFRESH_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES"))
        self.FAST_REFRESH_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("FAST_REFRESH_TOKEN_EXPIRE_MINUTES"))

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """Строка асинхронного подключения к PostgreSQL с паролем из секрета."""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()
