import base64
import csv
import os
import secrets

import httpx
import jwt
import pytest

BASE_URL = "http://localhost:8000"
CSV_FILE = "results_api_integrations.csv"

# ---------------------------------------------------------------------------
# Хелперы
# ---------------------------------------------------------------------------
def generate_pin_code() -> str:
    """Генерирует 8-символьный Base64 URL-safe без padding, как в Android-приложении."""
    random_bytes = secrets.token_bytes(6)  # 6 байт -> 8 символов Base64
    return base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')

def generate_password() -> str:
    return secrets.token_hex(8)  # 16 символов hex

def log_result(test_name: str, endpoint: str, status_code: int, elapsed_ms: float, csv_file: str = CSV_FILE):
    """Добавляет строку в CSV-файл с результатами."""
    file_exists = os.path.isfile(csv_file)
    with open(csv_file, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["test_name", "endpoint", "status_code", "elapsed_ms"])
        writer.writerow([test_name, endpoint, status_code, f"{elapsed_ms:.3f}"])

def decode_access_token_without_verify(token: str) -> dict:
    """Декодирует access-токен без проверки подписи для извлечения payload."""
    return jwt.decode(token, options={"verify_signature": False})

# ---------------------------------------------------------------------------
# Фикстуры
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def client():
    """HTTP-клиент с базовым URL."""
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as c:
        yield c

@pytest.fixture(scope="function")
def register_init(client):
    """Инициализация регистрации. Возвращает данные + elapsed_time_ms."""
    pin_code = generate_pin_code()
    password = generate_password()
    resp = client.post("/auth/register-init", json={"pin_code": pin_code, "password": password})
    assert resp.status_code == 201, f"Register init failed: {resp.text}"
    data = resp.json()
    return {
        "pin_code": pin_code,
        "password": password,
        "init_refresh_token": data["refresh_token"],
        "key_part": data["key_part"],
        "elapsed_time_ms": resp.elapsed.total_seconds() * 1000,
    }

@pytest.fixture(scope="function")
def register_accept(client, register_init):
    """Подтверждение регистрации. Возвращает токены + elapsed_time_ms."""
    resp = client.post("/auth/register-accept", json={"refresh_token": register_init["init_refresh_token"]})
    assert resp.status_code == 201, f"Register accept failed: {resp.text}"
    data = resp.json()
    payload = decode_access_token_without_verify(data["access_token"])
    return {
        "user_id": int(payload["sub"]),
        "access_token": data["access_token"],
        "accept_refresh_token": data["refresh_token"],
        "elapsed_time_ms": resp.elapsed.total_seconds() * 1000,
    }

@pytest.fixture(scope="function")
def registered_user(client, register_init, register_accept):
    """Полный цикл регистрации. Объединяет все данные."""
    return {
        **register_init,
        **register_accept,
        "init_elapsed_ms": register_init["elapsed_time_ms"],
        "accept_elapsed_ms": register_accept["elapsed_time_ms"],
    }