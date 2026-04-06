from fastapi import APIRouter, status, Header
from src.repository import AsyncAuthRepo


auth_router = APIRouter(prefix="/auth", tags=["Auth"])


@auth_router.get("/hello", status_code=status.HTTP_200_OK, summary="Hello-message")
async def get_hello():
    """Приветственное сообщение"""
    return {"msg": "Hello World!"}


@auth_router.get("/touch_db", status_code=status.HTTP_200_OK, summary="Hello-message")
async def touch_db():
    """Тестовое подключение к БД"""
    return {"msg": await AsyncAuthRepo.select_hello()}


@auth_router.post("/register_init", status_code=status.HTTP_201_CREATED, summary="Init user register")
async def register_init(user_data):
    """Инициализация регистрации пользователя"""
    ...


@auth_router.post("/register_accept", status_code=status.HTTP_201_CREATED, summary="Init user register")
async def register_accept(user_data):
    """Подтверждение регистрации пользователя"""
    ...


@auth_router.post("/login_init", status_code=status.HTTP_200_OK, summary="Init user login")
async def login_init(user_data):
    """Инициализация входа пользователя"""
    ...


@auth_router.post("/login_accept", status_code=status.HTTP_200_OK, summary="Accept user login")
async def login_accept(user_data):
    """Подтверждение входа пользователя"""
    ...


@auth_router.post("/refresh", status_code=status.HTTP_200_OK, summary="Issue new access-token")
async def refresh(refresh_token: str):
    """Выпуск нового access-токена"""
    ...


@auth_router.get("/auth", status_code=status.HTTP_200_OK, summary="Validate access-token")
async def auth(access_token: str = Header(...)):
    """Валидация access-токена"""
    ...


@auth_router.delete("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Logout user")
async def logout(refresh_token: str):
    """Выход пользователя (по refresh-токену)"""
    ...
