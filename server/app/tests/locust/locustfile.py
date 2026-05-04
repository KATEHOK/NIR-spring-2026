import base64
import secrets
import jwt
from typing import Any
from locust import HttpUser, task, between

BASE_URL = "http://localhost:8000"

# ---------------------------------------------------------------------------
# Хелперы
# ---------------------------------------------------------------------------
def generate_pin_code() -> str:
    random_bytes = secrets.token_bytes(6)
    return base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')

def generate_password() -> str:
    return secrets.token_hex(8)

def make_fake_otp() -> str:
    return base64.b64encode(b"wrong_otp_123456").decode()

def register_and_get_tokens(user: HttpUser) -> dict[str, Any]:
    """
    Регистрирует нового пользователя через API.
    Возвращает словарь с user_id, password, access_token, refresh_token.
    При ошибке останавливает пользователя и выбрасывает StopIteration.
    """
    pin = generate_pin_code()
    pw = generate_password()
    # init
    with user.client.post("/auth/register-init",
                          json={"pin_code": pin, "password": pw},
                          catch_response=True) as init_resp:
        if init_resp.status_code != 201:
            init_resp.failure(f"Init failed: {init_resp.status_code}")
            user.stop()
            raise StopIteration
        init_data = init_resp.json()
        init_refresh_token = init_data["refresh_token"]
    # accept
    with user.client.post("/auth/register-accept",
                          json={"refresh_token": init_refresh_token},
                          catch_response=True) as accept_resp:
        if accept_resp.status_code != 201:
            accept_resp.failure(f"Accept failed: {accept_resp.status_code}")
            user.stop()
            raise StopIteration
        accept_data = accept_resp.json()
        access_token = accept_data["access_token"]
        refresh_token = accept_data["refresh_token"]
        payload = jwt.decode(access_token, options={"verify_signature": False})
        user_id = int(payload["sub"])
    return {
        "user_id": user_id,
        "password": pw,
        "access_token": access_token,
        "refresh_token": refresh_token,
    }

# ---------------------------------------------------------------------------
# Сценарий 1: только регистрация
# ---------------------------------------------------------------------------
class RegisterUser(HttpUser):
    wait_time = between(1, 2)

    @task
    def register(self):
        try:
            register_and_get_tokens(self)
        except StopIteration:
            return
        self.stop()

# ---------------------------------------------------------------------------
# Сценарий 2: успешный вход по паролю + неверный OTP
# ---------------------------------------------------------------------------
class LoginFailUser(HttpUser):
    wait_time = between(1, 2)

    user_id: int = 0
    password: str = ""
    failures: int = 0

    def on_start(self):
        try:
            tokens = register_and_get_tokens(self)
        except StopIteration:
            return
        self.user_id = tokens["user_id"]
        self.password = tokens["password"]
        self.failures = 0

    @task
    def login_with_wrong_otp(self):
        if self.failures > 3:
            self.stop()
            return
        with self.client.post("/auth/login-init",
                              json={"user_id": self.user_id, "password": self.password},
                              catch_response=True) as init_resp:
            if init_resp.status_code == 200:
                token = init_resp.json()["refresh_token"]
                fake_otp = make_fake_otp()
                with self.client.post("/auth/login-accept",
                                      json={"refresh_token": token, "otp": fake_otp},
                                      catch_response=True) as accept_resp:
                    if accept_resp.status_code == 401:
                        accept_resp.success()
                        self.failures += 1
                    elif accept_resp.status_code == 403:
                        accept_resp.success()
                        self.stop()
                    else:
                        accept_resp.failure(f"Unexpected status: {accept_resp.status_code}")
            else:
                init_resp.failure(f"Login init failed: {init_resp.status_code}")
                self.stop()

# ---------------------------------------------------------------------------
# Сценарий 3: валидация access-токена
# ---------------------------------------------------------------------------
class TokenValidateUser(HttpUser):
    wait_time = between(1, 3)
    access_token: str = ""

    def on_start(self):
        try:
            tokens = register_and_get_tokens(self)
        except StopIteration:
            return
        self.access_token = tokens["access_token"]

    @task
    def validate_token(self):
        with self.client.get("/auth/validate-access-token",
                             headers={"Authorization": f"Bearer {self.access_token}"},
                             catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Validation failed: {resp.status_code}")

# ---------------------------------------------------------------------------
# Сценарий 4: обновление refresh-токена
# ---------------------------------------------------------------------------
class RefreshUser(HttpUser):
    wait_time = between(5, 10)
    accept_refresh_token: str = ""

    def on_start(self):
        try:
            tokens = register_and_get_tokens(self)
        except StopIteration:
            return
        self.accept_refresh_token = tokens["refresh_token"]

    @task
    def refresh_token(self):
        with self.client.post("/auth/refresh",
                              json={"refresh_token": self.accept_refresh_token},
                              catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Refresh failed: {resp.status_code}")

# ---------------------------------------------------------------------------
# Сценарий 5: выход (logout)
# ---------------------------------------------------------------------------
class LogoutUser(HttpUser):
    wait_time = between(1, 2)
    accept_refresh_token: str = ""

    def on_start(self):
        try:
            tokens = register_and_get_tokens(self)
        except StopIteration:
            return
        self.accept_refresh_token = tokens["refresh_token"]

    @task
    def logout(self):
        with self.client.request("DELETE", "/auth/logout",
                                 json={"refresh_token": self.accept_refresh_token},
                                 catch_response=True) as resp:
            if resp.status_code == 204:
                resp.success()
            else:
                resp.failure(f"Logout failed: {resp.status_code}")
        self.stop()