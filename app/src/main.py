import uvicorn
from fastapi import FastAPI
from src.config import settings


app = FastAPI(title="Auth Server")

@app.get("/health")
def health():
    return {"status": "ok"}

# Код с эндпоинтами регистрации, логина, ...
# Для доступа к настройкам: settings.DB_PASSWORD, settings.SECRET_KEY, ...

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.SERVER_IP,
        port=settings.SERVER_PORT,
        reload=True,
    )