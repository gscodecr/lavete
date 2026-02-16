from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "La Vete Admin"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "changethis"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    DATABASE_URL: str = "sqlite+aiosqlite:///./lavete.db"
    
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:8000", "http://localhost:3000"]

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
