from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    db_path: str = str(Path.home() / "AppData" / "Roaming" / "takt" / "takt.db")
    port: int = 8080
    cors_origins: str = "*"

    model_config = {"env_prefix": "TAKT_"}


settings = Settings()
