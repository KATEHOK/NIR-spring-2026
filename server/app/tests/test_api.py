import base64

import pytest
from conftest import log_result

# ---------------------------------------------------------------------------
# 0. Прогрев стенда (установление сессии и тд)
# ---------------------------------------------------------------------------

def test_warmup(client):
    resp = client.get("/auth/touch-db")
    elapsed = resp.elapsed.total_seconds() * 1000
    log_result("test_warmup", "/auth/touch-db", resp.status_code, elapsed)
    assert resp.status_code == 200

# ---------------------------------------------------------------------------
# 1. Доступность БД (SELECT 'Hello World!')
# ---------------------------------------------------------------------------
def test_touch_db(client):
    resp = client.get("/auth/touch-db")
    elapsed = resp.elapsed.total_seconds() * 1000
    log_result("test_touch_db", "/auth/touch-db", resp.status_code, elapsed)
    assert resp.status_code == 200
    data = resp.json()
    assert "msg" in data

# ---------------------------------------------------------------------------
# 2. Регистрация
# ---------------------------------------------------------------------------
def test_register_init_success(register_init):
    data = register_init
    assert "init_refresh_token" in data
    assert "key_part" in data
    log_result("test_register_init_success", "/auth/register-init", 201, data["elapsed_time_ms"])

def test_register_accept_success(register_accept):
    data = register_accept
    assert "access_token" in data
    assert "accept_refresh_token" in data
    log_result("test_register_accept_success", "/auth/register-accept", 201, data["elapsed_time_ms"])

def test_register_accept_invalid_token(client):
    resp = client.post("/auth/register-accept", json={"refresh_token": "invalid_token_123"})
    elapsed = resp.elapsed.total_seconds() * 1000
    log_result("test_register_accept_invalid_token", "/auth/register-accept", resp.status_code, elapsed)
    assert resp.status_code in (401, 400), f"Unexpected status: {resp.status_code}"

# ---------------------------------------------------------------------------
# 3. Инициализация входа
# ---------------------------------------------------------------------------
def test_login_init_success(client, registered_user):
    u = registered_user
    resp = client.post("/auth/login-init", json={"user_id": u["user_id"], "password": u["password"]})
    elapsed = resp.elapsed.total_seconds() * 1000
    log_result("test_login_init_success", "/auth/login-init", resp.status_code, elapsed)
    assert resp.status_code == 200
    data = resp.json()
    assert "challenge" in data
    assert "refresh_token" in data

def test_login_init_wrong_password(client, registered_user):
    u = registered_user
    resp = client.post("/auth/login-init", json={"user_id": u["user_id"], "password": "wrong_password"})
    elapsed = resp.elapsed.total_seconds() * 1000
    log_result("test_login_init_wrong_password", "/auth/login-init", resp.status_code, elapsed)
    assert resp.status_code == 401

def test_login_init_nonexistent_user(client):
    resp = client.post("/auth/login-init", json={"user_id": 99999, "password": "any"})
    elapsed = resp.elapsed.total_seconds() * 1000
    log_result("test_login_init_nonexistent_user", "/auth/login-init", resp.status_code, elapsed)
    assert resp.status_code in (404, 401)

# ---------------------------------------------------------------------------
# 4. Подтверждение входа (неудачное)
# ---------------------------------------------------------------------------
def test_login_accept_wrong_otp(client, registered_user):
    u = registered_user
    login_init_resp = client.post("/auth/login-init", json={"user_id": u["user_id"], "password": u["password"]})
    assert login_init_resp.status_code == 200
    refresh_token = login_init_resp.json()["refresh_token"]
    fake_otp = base64.b64encode(b"wrong_otp").decode()
    resp = client.post("/auth/login-accept", json={"refresh_token": refresh_token, "otp": fake_otp})
    elapsed = resp.elapsed.total_seconds() * 1000
    log_result("test_login_accept_wrong_otp", "/auth/login-accept", resp.status_code, elapsed)
    assert resp.status_code == 401

def test_login_accept_without_init(client):
    fake_otp = base64.b64encode(b"wrong_otp").decode()
    resp = client.post("/auth/login-accept", json={"refresh_token": "no_init_token", "otp": fake_otp})
    elapsed = resp.elapsed.total_seconds() * 1000
    log_result("test_login_accept_without_init", "/auth/login-accept", resp.status_code, elapsed)
    assert resp.status_code == 401

# ---------------------------------------------------------------------------
# 5. Обновление токенов
# ---------------------------------------------------------------------------
def test_refresh_success(client, registered_user):
    u = registered_user
    resp = client.post("/auth/refresh", json={"refresh_token": u["accept_refresh_token"]})
    elapsed = resp.elapsed.total_seconds() * 1000
    log_result("test_refresh_success", "/auth/refresh", resp.status_code, elapsed)
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["refresh_token"] == u["accept_refresh_token"]

def test_refresh_revoked_token(client, registered_user):
    u = registered_user
    logout_resp = client.request("DELETE", "/auth/logout", json={"refresh_token": u["accept_refresh_token"]})
    assert logout_resp.status_code == 204
    resp = client.post("/auth/refresh", json={"refresh_token": u["accept_refresh_token"]})
    elapsed = resp.elapsed.total_seconds() * 1000
    log_result("test_refresh_revoked_token", "/auth/refresh", resp.status_code, elapsed)
    assert resp.status_code == 401

# ---------------------------------------------------------------------------
# 6. Валидация access-токена
# ---------------------------------------------------------------------------
def test_validate_access_token_valid(client, registered_user):
    u = registered_user
    resp = client.get("/auth/validate-access-token", headers={"Authorization": f"Bearer {u['access_token']}"})
    elapsed = resp.elapsed.total_seconds() * 1000
    log_result("test_validate_access_token_valid", "/auth/validate-access-token", resp.status_code, elapsed)
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["user_id"] == u["user_id"]

def test_validate_access_token_invalid(client):
    resp = client.get("/auth/validate-access-token", headers={"Authorization": "Bearer invalid.token.here"})
    elapsed = resp.elapsed.total_seconds() * 1000
    log_result("test_validate_access_token_invalid", "/auth/validate-access-token", resp.status_code, elapsed)
    assert resp.status_code == 401

# ---------------------------------------------------------------------------
# 7. Выход
# ---------------------------------------------------------------------------
def test_logout_success(client, registered_user):
    u = registered_user
    resp = client.request("DELETE", "/auth/logout", json={"refresh_token": u["accept_refresh_token"]})
    elapsed = resp.elapsed.total_seconds() * 1000
    log_result("test_logout_success", "/auth/logout", resp.status_code, elapsed)
    assert resp.status_code == 204

def test_logout_revoked(client, registered_user):
    u = registered_user
    client.request("DELETE", "/auth/logout", json={"refresh_token": u["accept_refresh_token"]})
    resp = client.request("DELETE", "/auth/logout", json={"refresh_token": u["accept_refresh_token"]})
    elapsed = resp.elapsed.total_seconds() * 1000
    log_result("test_logout_revoked", "/auth/logout", resp.status_code, elapsed)
    assert resp.status_code == 204

# ---------------------------------------------------------------------------
# 8. Публичный ключ и проверка подписи
# ---------------------------------------------------------------------------
def test_public_key_and_signature_verification(client, registered_user):
    import jwt
    pub_resp = client.get("/auth/public-key")
    assert pub_resp.status_code == 200
    pub_data = pub_resp.json()
    algorithm = pub_data["algorithm"]
    public_key = pub_data["public_key"]

    access_token = registered_user["access_token"]

    try:
        payload = jwt.decode(
            access_token,
            public_key,
            algorithms=[algorithm],
            options={"verify_iat": False}   # сервер работает с utc, часовой пояс клиента может отличаться
        )
        user_id_from_token = int(payload["sub"])
        assert user_id_from_token == registered_user["user_id"]
        log_result("test_public_key_and_signature_verification", "/auth/public-key", 200, pub_resp.elapsed.total_seconds() * 1000)
    except jwt.InvalidTokenError as e:
        pytest.fail(f"Signature verification failed: {e}")