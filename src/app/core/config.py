from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass(frozen=True)
class Settings:
    MONGO_DSN: str = os.getenv("MONGO_DSN", "mongodb://localhost:27017")
    MONGO_DB: str = os.getenv("MONGO_DB", "planerProj2")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ90")
    JWT_ALG: str = os.getenv("JWT_ALG", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
    PROJECT_DIR: Path = Path(__file__).resolve().parents[2]
    TEMPLATES_DIR: Path = PROJECT_DIR / "src" / "app" / "templates"

    @property
    def access_token_timedelta(self) -> timedelta:
        return timedelta(minutes=self.JWT_EXPIRE_MINUTES)


settings = Settings()
