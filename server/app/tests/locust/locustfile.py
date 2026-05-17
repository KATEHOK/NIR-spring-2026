import base64
import secrets
import os
import time
from typing import Callable
from locust import HttpUser, task, between
from locust.clients import HttpSession

BASE_URL = "http://localhost:8000"
WAIT_TIME = between(0.5, 1)
SESSION_EXPIRE_SECONDS = int(os.getenv("SESSION_EXPIRE_MINUTES")) * 60
REFRESH_TOKEN_EXPIRE_SECONDS = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES")) * 60
JWT_EXPIRE_SECONDS = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")) * 60
JWT_VALIDATE_ITERATIONS = 10
JWT_REFRESH_ITERATIONS = 10
LOGIN_ITERATIONS = 10
LOGIN_FAULTS_LIMIT = int(os.getenv("FAULTS_LIMIT"))


class Helper:
    client: HttpSession

    def __init__(self, client):
        self.client = client

    def register_init_req(
            self,
            pin_code: str,
            password: str,
            prevent_failure: bool = False,
    ) -> dict[str, int | str]:
        with self.client.post(
            "/auth/register-init",
            json={"pin_code": pin_code, "password": password},
            catch_response=True
        ) as resp:
            if resp.status_code == 201:
                resp.success()
                return {
                    "status_code": resp.status_code,
                    "password": password,
                    "session_id": resp.json().get("session_id")
                }
            else:
                if prevent_failure:
                    resp.success()
                else:
                    resp.failure(f"Register init failed: {resp.status_code}")
                return {
                    "status_code": resp.status_code,
                }

    def register_accept_req(
            self,
            session_id: str,
            prevent_failure: bool = False,
            prevent_statuses_failure: tuple[int, ...] = (),
    ) -> dict[str, int | str]:
        with self.client.post(
            "/auth/register-accept",
            json={"session_id": session_id},
            catch_response=True
        ) as resp:
            if resp.status_code == 201:
                resp.success()
                return {
                    "status_code": resp.status_code,
                    "access_token": resp.json().get("access_token"),
                    "refresh_token": resp.json().get("refresh_token"),
                }
            else:
                if prevent_failure or resp.status_code in prevent_statuses_failure:
                    resp.success()
                else:
                    resp.failure(f"Register accept failed: {resp.status_code}")
                return {
                    "status_code": resp.status_code,
                }

    def login_init_req(
            self,
            user_id: int,
            password: str,
            prevent_failure: bool = False,
            prevent_statuses_failure: tuple[int, ...] = (),
    ) -> dict[str, int | str] | None:
        with self.client.post(
            "/auth/login-init",
            json={"user_id": user_id, "password": password},
            catch_response=True
        ) as resp:
            if resp.status_code == 200:
                resp.success()
                return {
                    "status_code": resp.status_code,
                    "session_id": resp.json().get("session_id"),
                    "challenge": resp.json().get("challenge"),
                }
            else:
                if prevent_failure or resp.status_code in prevent_statuses_failure:
                    resp.success()
                else:
                    resp.failure(f"Login init failed: {resp.status_code}")
                return {
                    "status_code": resp.status_code,
                }

    def login_accept_req(
            self,
            session_id: str,
            otp: str,
            prevent_failure: bool = False,
            prevent_statuses_failure: tuple[int, ...] = (),
    ) -> dict[str, int | str]:
        with self.client.post(
            "/auth/login-accept",
            json={"session_id": session_id, "otp": otp},
            catch_response=True
        ) as resp:
            if resp.status_code == 200:
                resp.success()
                return {
                    "status_code": resp.status_code,
                    "access_token": resp.json().get("access_token"),
                    "refresh_token": resp.json().get("refresh_token"),
                }
            else:
                if prevent_failure or resp.status_code in prevent_statuses_failure:
                    resp.success()
                else:
                    resp.failure(f"Login accept failed: {resp.status_code}")
                return {
                    "status_code": resp.status_code
                }

    def get_id_req(
            self,
            access_token: str,
            prevent_failure: bool = False,
            prevent_statuses_failure: tuple[int, ...] = (),
    ) -> dict[str, int]:
        with self.client.get(
            "/auth/validate-access-token",
            headers={"Authorization": f"Bearer {access_token}"},
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
                return {
                    "status_code": resp.status_code,
                    "user_id": int(resp.json().get("user_id")),
                }
            else:
                if prevent_failure or resp.status_code in prevent_statuses_failure:
                    resp.success()
                else:
                    resp.failure(f"Failed get id by access-token: {resp.status_code}")
                return {
                    "status_code": resp.status_code,
                }

    def get_refreshed_access_token_req(
            self,
            refresh_token: str,
            prevent_failure: bool = False,
            prevent_statuses_failure: tuple[int, ...] = (),
    ) -> dict[str, int | str]:
        with self.client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
                return {
                    "status_code": resp.status_code,
                    "access_token": resp.json().get("access_token"),
                }
            else:
                if prevent_failure or resp.status_code in prevent_statuses_failure:
                    resp.success()
                else:
                    resp.failure(f"Failed refresh access-token: {resp.status_code}")
                return {
                    "status_code": resp.status_code,
                }

    def logout_req(self, refresh_token: str, prevent_failure: bool = False) -> dict[str, bool | int]:
        with self.client.delete(
            "/auth/logout",
            json={"refresh_token": refresh_token},
            catch_response=True,
        ) as resp:
            if resp.status_code == 204 or prevent_failure:
                resp.success()
            else:
                resp.failure(f"Failed logout: {resp.status_code}")
            return {
                "status_code": resp.status_code,
            }

    def register(self, task: Callable, sleep_s: float = None) -> dict[str, str]:
        pin_code = self.generate_pin_code()
        password = self.generate_password()
        resp = self.register_init_req(pin_code, password)
        if resp["status_code"] != 201:
            Helper.raise_task_assertion_error(task, "register init", resp["status_code"])
        if sleep_s is not None:
            time.sleep(sleep_s)
        resp = self.register_accept_req(resp["session_id"])
        if resp["status_code"] != 201:
            Helper.raise_task_assertion_error(task, "register accept", resp["status_code"])
        return {
            "password": password,
            "access_token": resp["access_token"],
            "refresh_token": resp["refresh_token"]
        }

    def login(
            self,
            user_id: int,
            password: str,
            task: Callable,
            sleep_s: float = None,
            prevent_failure: bool = False,
            prevent_wrong_user_id_failure: bool = False,
            prevent_wrong_password_failure: bool = False,
            prevent_wrong_otp_failure: bool = False,
            prevent_banned_user_failure: bool = False,
    ) -> dict[str, str] | None:
        allowed_failures = []
        if prevent_wrong_user_id_failure:
            allowed_failures.append(404)
        if prevent_banned_user_failure:
            allowed_failures.append(403)
        if prevent_wrong_password_failure:
            allowed_failures.append(401)
        resp = self.login_init_req(user_id, password, prevent_failure, tuple(allowed_failures))
        if resp["status_code"] != 200:
            if not prevent_failure and resp["status_code"] not in allowed_failures:
                Helper.raise_task_assertion_error(task, "login init", resp["status_code"])
            return None
        if sleep_s is not None:
            time.sleep(sleep_s)
        allowed_failures = []
        if prevent_banned_user_failure:
            allowed_failures.append(403)
        if prevent_wrong_otp_failure:
            allowed_failures.append(401)
        resp = self.login_accept_req(
            resp["session_id"],
            self.make_fake_otp(),
            prevent_failure,
            tuple(allowed_failures)
        )
        if resp["status_code"] != 201:
            if not prevent_failure and resp["status_code"] not in allowed_failures:
                Helper.raise_task_assertion_error(task, "login accept", resp["status_code"])
            return None
        return {
            "access_token": resp["access_token"],
            "refresh_token": resp["refresh_token"]
        }

    def register_and_get_id(self, task: Callable, sleep_s: float = None) -> dict[str, int | str]:
        user_data: dict[str, int | str] = self.register(task, sleep_s)
        if sleep_s is not None:
            time.sleep(sleep_s)
        resp = self.get_id_req(user_data["access_token"])
        if resp["status_code"] != 200:
            Helper.raise_task_assertion_error(task, "validate access-token", resp["status_code"])
        user_data["user_id"] = resp["user_id"]
        return user_data

    def logout(
            self,
            refresh_token: str,
            task: Callable,
            prevent_failure: bool = False,
    ):
        user_data = self.logout_req(refresh_token, prevent_failure)
        if not prevent_failure and user_data["status_code"] != 204:
            Helper.raise_task_assertion_error(task, "logout", user_data["status_code"])

    @staticmethod
    def raise_task_assertion_error(task: Callable, failed_step: str = None, failed_code: int = None):
        failed_step = f": step '{failed_step}' - {failed_code}" if failed_step is not None else ""
        raise AssertionError(f"Failed task '{task.__name__}'{failed_step}")

    @staticmethod
    def generate_pin_code() -> str:
        random_bytes = secrets.token_bytes(6)
        return base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')

    @staticmethod
    def generate_password() -> str:
        return secrets.token_hex(8)

    @staticmethod
    def make_fake_otp() -> str:
        return base64.b64encode(b"wrong_otp_123456").decode()

    @staticmethod
    def make_fake_jwt() -> str:
        return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"

class RegisterUser(HttpUser):
    helper: Helper
    host = BASE_URL
    wait_time = WAIT_TIME
    weight = 1

    def on_start(self):
        self.helper = Helper(self.client)

    @task(1)
    def task_register(self):
        self.helper.register(self.task_register, sleep_s=1)


class AccessTokenValidateUser(HttpUser):
    helper: Helper
    host = BASE_URL
    wait_time = WAIT_TIME
    weight = 10

    def on_start(self):
        self.helper = Helper(self.client)

    def loop(
            self,
            access_token: str,
            task: Callable,
            iterations: int = JWT_VALIDATE_ITERATIONS
    ):
        if not isinstance(iterations, int) or iterations < 0:
            raise ValueError(f"Invalid 'iterations': expected not negative 'int', got {repr(iterations)}")
        while iterations > 0:
            iterations -= 1
            time.sleep(0.5)
            resp = self.helper.get_id_req(access_token, prevent_statuses_failure=(401,))
            if resp["status_code"] not in (200, 401):
                Helper.raise_task_assertion_error(
                    task,
                    f"validate access-token: {resp['status_code']}",
                    resp["status_code"]
                )

    @task(10)
    def task_validate_valid(self):
        user_data = self.helper.register(self.task_validate_valid)
        self.loop(user_data["access_token"], self.task_validate_valid)

    @task(2)
    def task_validate_expired(self):
        user_data = self.helper.register(self.task_validate_expired)
        time.sleep(JWT_EXPIRE_SECONDS)
        self.loop(user_data["access_token"], self.task_validate_expired)

    @task(1)
    def task_validate_invalid(self):
        access_token = self.helper.make_fake_jwt()
        self.loop(access_token, self.task_validate_invalid)


class RefreshUser(HttpUser):
    helper: Helper
    host = BASE_URL
    wait_time = WAIT_TIME
    weight = 3

    def on_start(self):
        self.helper = Helper(self.client)

    def loop(
            self,
            refresh_token: str,
            task: Callable,
            iterations: int = JWT_REFRESH_ITERATIONS
    ):
        if not isinstance(iterations, int) or iterations < 0:
            raise ValueError(f"Invalid 'iterations': expected not negative 'int', got {repr(iterations)}")
        while iterations > 0:
            iterations -= 1
            time.sleep(0.5)
            resp = self.helper.get_refreshed_access_token_req(
                refresh_token,
                prevent_statuses_failure=(401,)
            )
            if resp["status_code"] not in (200, 401):
                Helper.raise_task_assertion_error(
                    task,
                    f"refresh access-token: {resp['status_code']}",
                    resp["status_code"]
                )

    @task(8)
    def task_refresh_valid(self):
        user_data = self.helper.register(self.task_refresh_valid)
        self.loop(user_data["refresh_token"], self.task_refresh_valid)

    @task(2)
    def task_refresh_expired(self):
        user_data = self.helper.register(self.task_refresh_expired)
        time.sleep(REFRESH_TOKEN_EXPIRE_SECONDS)
        self.loop(user_data["refresh_token"], self.task_refresh_expired)

    @task(1)
    def task_refresh_revoked(self):
        user_data = self.helper.register(self.task_refresh_revoked)
        self.helper.logout(user_data["refresh_token"], self.task_refresh_revoked)
        self.loop(user_data["refresh_token"], self.task_refresh_revoked)

    @task(1)
    def task_refresh_invalid(self):
        refresh_token = "fake_refresh_token"
        self.loop(refresh_token, self.task_refresh_invalid)


class LoginUser(HttpUser):
    helper: Helper
    host = BASE_URL
    wait_time = WAIT_TIME
    weight = 5

    def on_start(self):
        self.helper = Helper(self.client)

    def loop(
            self,
            user_id: int,
            password: str,
            task: Callable,
            iterations: int = LOGIN_ITERATIONS,
            prevent_failure: bool = False,
            allow_wrong_user_id: bool = False,
            allow_banned_user: bool = False,
            allow_wrong_password: bool = False,
            allow_wrong_otp: bool = False,
    ):
        if not isinstance(iterations, int) or iterations < 0:
            raise ValueError(f"Invalid 'iterations': expected not negative 'int', got {repr(iterations)}")
        sleep_s = 0.5
        while iterations > 0:
            iterations -= 1
            time.sleep(sleep_s)
            self.helper.login(
                user_id,
                password,
                task,
                sleep_s,
                prevent_failure,
                allow_wrong_user_id,
                allow_wrong_password,
                allow_wrong_otp,
                allow_banned_user,
            )

    @task(1)
    def task_wrong_user_id(self):
        self.loop(
            user_id=0,
            password="fake_password",
            task=self.task_wrong_user_id,
            allow_wrong_user_id=True,
        )

    @task(1)
    def task_banned_user(self):
        user_data = self.helper.register_and_get_id(self.task_banned_user)
        self.loop(
            user_id=user_data["user_id"],
            password=user_data['password'],
            task=self.task_banned_user,
            iterations=LOGIN_FAULTS_LIMIT + 1,
            prevent_failure=True,
        )
        self.loop(
            user_id=user_data["user_id"],
            password=user_data['password'],
            task=self.task_banned_user,
            allow_wrong_otp=True,
            allow_banned_user=True,
        )

    @task(3)
    def task_wrong_password(self):
        user_data = self.helper.register_and_get_id(self.task_wrong_password)
        self.loop(
            user_id=user_data["user_id"],
            password=f"{user_data['password']}_fake",
            task=self.task_wrong_password,
            allow_wrong_password=True,
            allow_banned_user=True,
        )

    @task(2)
    def task_wrong_otp(self):
        user_data = self.helper.register_and_get_id(self.task_wrong_otp)
        self.loop(
            user_id=user_data["user_id"],
            password=user_data['password'],
            task=self.task_wrong_otp,
            allow_wrong_otp=True,
            allow_banned_user=True,
        )
