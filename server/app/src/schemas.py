from pydantic import BaseModel


class TokensPairSchema(BaseModel):
    """Миксин с парой токенов (access и refresh)"""
    refresh_token: str
    access_token: str


class RegisterSchemas:
    class Init:
        class Req(BaseModel):
            """Входные данные при инициализации регистрации пользователя"""
            pin_code: str
            password: str

        class Resp(BaseModel):
            """Выходные данные при инициализации регистрации пользователя"""
            session_id: str
            key_part: str

    class Accept:
        class Req(BaseModel):
            """Входные данные при подтверждении регистрации пользователя"""
            session_id: str

        class Resp(TokensPairSchema):
            """Выходные данные при подтверждении регистрации пользователя"""


class LoginSchemas:
    class Init:
        class Req(BaseModel):
            """Входные данные при инициализации входа пользователя"""
            user_id: int
            password: str

        class Resp(BaseModel):
            """Выходные данные при инициализации входа пользователя"""
            session_id: str
            challenge: str

    class Accept:
        class Req(BaseModel):
            """Входные данные при подтверждении входа пользователя"""
            session_id: str
            otp: str

        class Resp(TokensPairSchema):
            """Выходные данные при подтверждении входа пользователя"""


class RefreshSchema:
    class Req(BaseModel):
        """Входные данные при обновлении access-токена"""
        refresh_token: str

    class Resp(TokensPairSchema):
        """Выходные данные при обновлении access-токена"""


class LogoutSchema:
    class Req(BaseModel):
        """Входные данные при выходе из системы"""
        refresh_token: str
