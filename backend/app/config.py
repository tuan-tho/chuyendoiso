import os
from dotenv import load_dotenv # type: ignore

load_dotenv()

class Settings:
    PROJECT_NAME: str = "KTX-DNU Backend"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "PLEASE_CHANGE_ME")  # đổi khi deploy
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./ktx_dnu.db")
    CORS_ORIGINS: list[str] = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://127.0.0.1:5500,http://localhost:5500").split(",") if o.strip()]

settings = Settings()
