import base64
import csv
import os
import secrets
import time
from typing import Any
from dotenv import load_dotenv

import httpx
import jwt

load_dotenv()

BASE_URL = "http://localhost:8000"
LABEL = os.getenv("SERVER_IMAGE_TAG")
CSV_FILE = f"tests/complex/results_complex-{LABEL}.csv"

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
REFRESH_TOKEN_EXPIRE_MINUTES = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES"))

ACCESS_TOKEN_WAIT = ACCESS_TOKEN_EXPIRE_MINUTES * 60 + 10   # 70 секунд для 1 мин
REFRESH_REMAINING_WAIT = max(0, REFRESH_TOKEN_EXPIRE_MINUTES * 60 - ACCESS_TOKEN_WAIT + 10)

# ---------------------------------------------------------------------------
# Хелперы
# ---------------------------------------------------------------------------
def generate_pin_code() -> str:
    random_bytes = secrets.token_bytes(6)
    return base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')

def generate_password() -> str:
    return secrets.token_hex(8)

def log_step(step_name: str, status: str, elapsed_ms: float, sleep_ms: float = 0,
             scenario: int = 0):
    """Записывает строку в CSV. total_elapsed_ms = elapsed_ms + sleep_ms."""
    total_elapsed_ms = elapsed_ms + sleep_ms
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["scenario", "step", "status", "elapsed_ms", "sleep_ms", "total_elapsed_ms"])
        writer.writerow([scenario, step_name, status,
                         f"{elapsed_ms:.3f}", f"{sleep_ms:.3f}", f"{total_elapsed_ms:.3f}"])

def measure(label: str, client: httpx.Client, method: str, url: str, **kwargs):
    start = time.perf_counter()
    resp = client.request(method, url, **kwargs)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return resp, elapsed_ms

def decode_user_id_from_access_token(access_token: str) -> int:
    payload = jwt.decode(access_token, options={"verify_signature": False})
    return int(payload["sub"])

def register_user(client: httpx.Client, scenario: int) -> tuple[dict[str, Any], float]:
    """
    Регистрирует пользователя (init + accept).
    Возвращает словарь с данными пользователя и суммарное время запросов.
    """
    pin = generate_pin_code()
    pw = generate_password()

    # register-init
    resp, e1 = measure("register-init", client, "POST", "/auth/register-init",
                       json={"pin_code": pin, "password": pw})
    assert resp.status_code == 201, f"Init failed: {resp.status_code}"
    init_data = resp.json()
    refresh_token = init_data["refresh_token"]
    log_step("register-init", "201", e1, scenario=scenario)

    # register-accept
    resp, e2 = measure("register-accept", client, "POST", "/auth/register-accept",
                       json={"refresh_token": refresh_token})
    assert resp.status_code == 201, f"Accept failed: {resp.status_code}"
    accept_data = resp.json()
    access_token = accept_data["access_token"]
    new_refresh = accept_data["refresh_token"]
    log_step("register-accept", "201", e2, scenario=scenario)

    user_id = decode_user_id_from_access_token(access_token)
    return {"user_id": user_id, "password": pw, "refresh_token": new_refresh, "access_token": access_token}, e1 + e2

# ---------------------------------------------------------------------------
# Сценарий 1
# ---------------------------------------------------------------------------
def scenario1():
    scenario = 1
    print(f"=== Scenario {scenario} started ===")
    total_elapsed_ms = 0.0
    total_sleep_ms = 0.0

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        user, reg_time = register_user(client, scenario)
        total_elapsed_ms += reg_time
        uid, pw, r1, a1 = user["user_id"], user["password"], user["refresh_token"], user["access_token"]

        # validate a1
        resp, e = measure("validate-a1", client, "GET", "/auth/validate-access-token",
                          headers={"Authorization": f"Bearer {a1}"})
        assert resp.status_code == 200
        log_step("validate-a1", "200", e, scenario=scenario)
        total_elapsed_ms += e

        print(f"Scenario {scenario}: waiting {ACCESS_TOKEN_WAIT} s ...")
        time.sleep(ACCESS_TOKEN_WAIT)
        total_sleep_ms += ACCESS_TOKEN_WAIT * 1000

        # validate expired
        resp, e = measure("validate-a1-expired", client, "GET", "/auth/validate-access-token",
                          headers={"Authorization": f"Bearer {a1}"})
        assert resp.status_code == 401
        log_step("validate-a1-expired", "401", e, sleep_ms=ACCESS_TOKEN_WAIT * 1000, scenario=scenario)
        total_elapsed_ms += e

        # refresh
        resp, e = measure("refresh", client, "POST", "/auth/refresh", json={"refresh_token": r1})
        assert resp.status_code == 200
        a2 = resp.json()["access_token"]
        log_step("refresh", "200", e, scenario=scenario)
        total_elapsed_ms += e

        # validate a2
        resp, e = measure("validate-a2", client, "GET", "/auth/validate-access-token",
                          headers={"Authorization": f"Bearer {a2}"})
        assert resp.status_code == 200
        log_step("validate-a2", "200", e, scenario=scenario)
        total_elapsed_ms += e

        # logout
        resp, e = measure("logout", client, "DELETE", "/auth/logout", json={"refresh_token": r1})
        assert resp.status_code == 204
        log_step("logout", "204", e, scenario=scenario)
        total_elapsed_ms += e

        # refresh after revoke
        resp, e = measure("refresh-revoked", client, "POST", "/auth/refresh", json={"refresh_token": r1})
        assert resp.status_code == 401
        log_step("refresh-revoked", "401", e, scenario=scenario)
        total_elapsed_ms += e

        # login with correct data
        resp, e = measure("login-init-valid", client, "POST", "/auth/login-init",
                          json={"user_id": uid, "password": pw})
        assert resp.status_code == 200
        log_step("login-init-valid", "200", e, scenario=scenario)
        total_elapsed_ms += e

    # итоговая строка: elapsed = сумма всех запросов, sleep = сумма ожиданий, total = общее время сценария
    log_step("TOTAL_SCENARIO_1", "OK", total_elapsed_ms, sleep_ms=total_sleep_ms, scenario=scenario)
    print("Scenario 1 finished.")

# ---------------------------------------------------------------------------
# Сценарий 2
# ---------------------------------------------------------------------------
def scenario2():
    scenario = 2
    print(f"=== Scenario {scenario} started ===")
    total_elapsed_ms = 0.0
    total_sleep_ms = 0.0

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        user, reg_time = register_user(client, scenario)
        total_elapsed_ms += reg_time
        uid, pw, r1, a1 = user["user_id"], user["password"], user["refresh_token"], user["access_token"]

        resp, e = measure("validate-a1", client, "GET", "/auth/validate-access-token",
                          headers={"Authorization": f"Bearer {a1}"})
        assert resp.status_code == 200
        log_step("validate-a1", "200", e, scenario=scenario)
        total_elapsed_ms += e

        print(f"Scenario {scenario}: waiting {ACCESS_TOKEN_WAIT} s ...")
        time.sleep(ACCESS_TOKEN_WAIT)
        total_sleep_ms += ACCESS_TOKEN_WAIT * 1000

        resp, e = measure("validate-a1-expired", client, "GET", "/auth/validate-access-token",
                          headers={"Authorization": f"Bearer {a1}"})
        assert resp.status_code == 401
        log_step("validate-a1-expired", "401", e, sleep_ms=ACCESS_TOKEN_WAIT * 1000, scenario=scenario)
        total_elapsed_ms += e

        resp, e = measure("refresh-1", client, "POST", "/auth/refresh", json={"refresh_token": r1})
        assert resp.status_code == 200
        a2 = resp.json()["access_token"]
        log_step("refresh-1", "200", e, scenario=scenario)
        total_elapsed_ms += e

        resp, e = measure("validate-a2", client, "GET", "/auth/validate-access-token",
                          headers={"Authorization": f"Bearer {a2}"})
        assert resp.status_code == 200
        log_step("validate-a2", "200", e, scenario=scenario)
        total_elapsed_ms += e

        print(f"Scenario {scenario}: waiting {REFRESH_REMAINING_WAIT} s ...")
        time.sleep(REFRESH_REMAINING_WAIT)
        total_sleep_ms += REFRESH_REMAINING_WAIT * 1000

        resp, e = measure("refresh-expired", client, "POST", "/auth/refresh", json={"refresh_token": r1})
        assert resp.status_code == 401
        log_step("refresh-expired", "401", e, sleep_ms=REFRESH_REMAINING_WAIT * 1000, scenario=scenario)
        total_elapsed_ms += e

        resp, e = measure("login-init-valid", client, "POST", "/auth/login-init",
                          json={"user_id": uid, "password": pw})
        assert resp.status_code == 200
        log_step("login-init-valid", "200", e, scenario=scenario)
        total_elapsed_ms += e

    log_step("TOTAL_SCENARIO_2", "OK", total_elapsed_ms, sleep_ms=total_sleep_ms, scenario=scenario)
    print("Scenario 2 finished.")

# ---------------------------------------------------------------------------
# Сценарий 3: login с неверным user_id
# ---------------------------------------------------------------------------
def scenario3():
    scenario = 3
    print(f"=== Scenario {scenario} (wrong user_id) started ===")
    total_elapsed_ms = 0.0
    total_sleep_ms = 0.0

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        user, reg_time = register_user(client, scenario)
        total_elapsed_ms += reg_time
        uid, pw, r1, a1 = user["user_id"], user["password"], user["refresh_token"], user["access_token"]

        resp, e = measure("validate-a1", client, "GET", "/auth/validate-access-token",
                          headers={"Authorization": f"Bearer {a1}"})
        assert resp.status_code == 200
        log_step("validate-a1", "200", e, scenario=scenario)
        total_elapsed_ms += e

        resp, e = measure("refresh", client, "POST", "/auth/refresh", json={"refresh_token": r1})
        assert resp.status_code == 200
        a2 = resp.json()["access_token"]
        log_step("refresh", "200", e, scenario=scenario)
        total_elapsed_ms += e

        resp, e = measure("validate-a2", client, "GET", "/auth/validate-access-token",
                          headers={"Authorization": f"Bearer {a2}"})
        assert resp.status_code == 200
        log_step("validate-a2", "200", e, scenario=scenario)
        total_elapsed_ms += e

        resp, e = measure("logout", client, "DELETE", "/auth/logout", json={"refresh_token": r1})
        assert resp.status_code == 204
        log_step("logout", "204", e, scenario=scenario)
        total_elapsed_ms += e

        resp, e = measure("login-init-wrong-uid", client, "POST", "/auth/login-init",
                          json={"user_id": uid + 1, "password": pw})
        assert resp.status_code in (404, 401), f"Unexpected status {resp.status_code}"
        log_step("login-init-wrong-uid", str(resp.status_code), e, scenario=scenario)
        total_elapsed_ms += e

    log_step("TOTAL_SCENARIO_3", "OK", total_elapsed_ms, sleep_ms=total_sleep_ms, scenario=scenario)
    print("Scenario 3 finished.")

# ---------------------------------------------------------------------------
# Сценарий 4: login с неверным password
# ---------------------------------------------------------------------------
def scenario4():
    scenario = 4
    print(f"=== Scenario {scenario} (wrong password) started ===")
    total_elapsed_ms = 0.0
    total_sleep_ms = 0.0

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        user, reg_time = register_user(client, scenario)
        total_elapsed_ms += reg_time
        uid, pw, r1, a1 = user["user_id"], user["password"], user["refresh_token"], user["access_token"]

        resp, e = measure("validate-a1", client, "GET", "/auth/validate-access-token",
                          headers={"Authorization": f"Bearer {a1}"})
        assert resp.status_code == 200
        log_step("validate-a1", "200", e, scenario=scenario)
        total_elapsed_ms += e

        resp, e = measure("refresh", client, "POST", "/auth/refresh", json={"refresh_token": r1})
        assert resp.status_code == 200
        a2 = resp.json()["access_token"]
        log_step("refresh", "200", e, scenario=scenario)
        total_elapsed_ms += e

        resp, e = measure("validate-a2", client, "GET", "/auth/validate-access-token",
                          headers={"Authorization": f"Bearer {a2}"})
        assert resp.status_code == 200
        log_step("validate-a2", "200", e, scenario=scenario)
        total_elapsed_ms += e

        resp, e = measure("logout", client, "DELETE", "/auth/logout", json={"refresh_token": r1})
        assert resp.status_code == 204
        log_step("logout", "204", e, scenario=scenario)
        total_elapsed_ms += e

        resp, e = measure("login-init-wrong-pw", client, "POST", "/auth/login-init",
                          json={"user_id": uid, "password": "wrong_password"})
        assert resp.status_code == 401
        log_step("login-init-wrong-pw", "401", e, scenario=scenario)
        total_elapsed_ms += e

    log_step("TOTAL_SCENARIO_4", "OK", total_elapsed_ms, sleep_ms=total_sleep_ms, scenario=scenario)
    print("Scenario 4 finished.")


if __name__ == "__main__":
    print("Starting complex tests (one-by-one)...")
    for scenario in (
        scenario1,
        scenario2,
        scenario3,
        scenario4,
    ):
        scenario()
        time.sleep(1)
    print("All scenarios done. Results in", CSV_FILE)