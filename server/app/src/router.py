from fastapi import APIRouter, status, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from src.dependencies import get_redis, get_db, validate_rid_and_get_sub_from_security_header
from src.schemas import RegisterSchemas, LoginSchemas, RefreshSchema, LogoutSchema
from src.services import RegisterService, LoginService, TokenService, SystemService


auth_router = APIRouter(prefix="/auth", tags=["Auth"])


@auth_router.get("/hello", status_code=status.HTTP_200_OK, summary="Hello-message")
async def get_hello():
    """Приветственное сообщение"""
    return await SystemService.get_hello()


@auth_router.get("/redis-test", status_code=status.HTTP_200_OK, summary="Test Redis connectivity")
async def redis_test(redis: Redis = Depends(get_redis)):
    """Проверка работы Redis: запись и чтение ключа"""
    test_key = "test:connection"
    test_value = b"ok"
    await redis.set(test_key, test_value)
    stored = await redis.get(test_key)
    return {
        "status": "ok",
        "value": stored.decode() if stored else None
    }


@auth_router.get("/touch-db", status_code=status.HTTP_200_OK, summary="Hello-message")
async def touch_db(session: AsyncSession = Depends(get_db)):
    """Тестовое подключение к БД"""
    return await SystemService.touch_db(session)


@auth_router.get("/public-key", summary="Get JWT public key")
async def get_public_key():
    """Публичный ключ и алгоритм для проверки JWT"""
    return await SystemService.get_public_key()


@auth_router.get("/validate-access-token", status_code=status.HTTP_200_OK, summary="Validate access-token")
async def validate_access_token(
        user_id: int = Depends(validate_rid_and_get_sub_from_security_header)
):
    """Проверка корректности access-токена"""
    return {"valid": True, "user_id": user_id}


@auth_router.post("/register-init", status_code=status.HTTP_201_CREATED, summary="Init user register")
async def register_init(
        data: RegisterSchemas.Init.Req,
        redis: Redis = Depends(get_redis),
) -> RegisterSchemas.Init.Resp:
    """Инициализация регистрации пользователя"""
    return await RegisterService.init(data.pin_code, data.password, redis)


@auth_router.post("/register-accept", status_code=status.HTTP_201_CREATED, summary="Accept user register")
async def register_accept(
        data: RegisterSchemas.Accept.Req,
        session: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis),
) -> RegisterSchemas.Accept.Resp:
    """Подтверждение регистрации пользователя"""
    return await RegisterService.accept(data.session_id, session, redis)


@auth_router.post("/login-init", status_code=status.HTTP_200_OK, summary="Init user login")
async def login_init(
        data: LoginSchemas.Init.Req,
        session: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis),
) -> LoginSchemas.Init.Resp:
    """Инициализация входа пользователя"""
    return await LoginService.init(data.user_id, data.password, session, redis)


@auth_router.post("/login-accept", status_code=status.HTTP_200_OK, summary="Accept user login")
async def login_accept(
        data: LoginSchemas.Accept.Req,
        session: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis),
) -> LoginSchemas.Accept.Resp:
    """Подтверждение входа пользователя"""
    return await LoginService.accept(data.session_id, data.otp, session, redis)


@auth_router.post("/refresh", status_code=status.HTTP_200_OK, summary="Issue new access-token")
async def refresh(
        data: RefreshSchema.Req,
        session: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis),
) -> RefreshSchema.Resp:
    """Выпуск нового access-токена"""
    return await TokenService.refresh(data.refresh_token, session, redis)


@auth_router.delete("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Logout user")
async def logout(
        data: LogoutSchema.Req,
        session: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis),
) -> None:
    """Выход пользователя (по refresh-токену)"""
    return await TokenService.logout(data.refresh_token, session, redis)
