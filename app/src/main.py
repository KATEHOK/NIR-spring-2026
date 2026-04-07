import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.router import auth_router


app = FastAPI(title="Auth Server")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.SERVER_CORS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.SERVER_IP,
        port=settings.SERVER_PORT,
        reload=True,
    )