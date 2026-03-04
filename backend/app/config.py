from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # App
    APP_NAME: str = "辽轨智能实训能力评估平台"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./training.db"
    
    # JWT
    SECRET_KEY: str = "liaoning-railway-training-secret-key-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # LLM Proxy
    LLM_PROXY_URL: str = "https://llm-proxy.densematrix.ai"
    LLM_PROXY_KEY: str = "sk-wskhgeyawc"
    LLM_MODEL: str = "gemini-3-flash-preview"
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3100", "http://127.0.0.1:5173"]
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
