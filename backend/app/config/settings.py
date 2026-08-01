"""Application settings loaded from environment variables via pydantic-settings."""
from functools import lru_cache
from typing import List, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        env_ignore_empty=True,
    )

    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "Temple AI Crowd Management System"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Enterprise AI-powered crowd management for temple festivals"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    API_V1_PREFIX: str = "/api/v1"

    # ── Security (placeholder — full JWT in Phase 6) ──────────────────────────
    SECRET_KEY: str = "change-this-super-secret-key-in-production-min-32-chars"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # ── PostgreSQL / Supabase ──────────────────────────────────────────────────
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "temple_crowd_db"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "root"
    POSTGRES_POOL_SIZE: int = 20
    POSTGRES_MAX_OVERFLOW: int = 40
    POSTGRES_POOL_RECYCLE: int = 3600
    POSTGRES_POOL_TIMEOUT: int = 30

    # ── Supabase ──────────────────────────────────────────────────────────────
    SUPABASE_DATABASE_URL: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    REDIS_MAX_CONNECTIONS: int = 50
    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 5

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: Union[List[str], str] = ["*"]
    ALLOWED_METHODS: Union[List[str], str] = ["*"]
    ALLOWED_HEADERS: Union[List[str], str] = ["*"]
    ALLOW_CREDENTIALS: bool = True

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    LOG_ROTATION: str = "100 MB"
    LOG_RETENTION: str = "30 days"

    # ── WebSocket ─────────────────────────────────────────────────────────────
    WS_HEARTBEAT_INTERVAL: int = 30

    # ── System Defaults ───────────────────────────────────────────────────────
    MAX_CAMERAS: int = 200
    DEFAULT_FPS: int = 15
    DEFAULT_CONFIDENCE: float = 0.5
    DEFAULT_IOU: float = 0.45
    DEFAULT_DETECTION_FPS: int = 5
    DEFAULT_SNAPSHOT_INTERVAL: int = 30
    DEFAULT_ALERT_INTERVAL: int = 300

    # ── AI / YOLO ─────────────────────────────────────────────────────────────
    AI_MODEL_PATH: str = "models/yolo11x.pt"   # relative to CWD or absolute
    AI_MODEL_NAME: str = "yolo11x.pt"
    AI_DEVICE: str = "auto"                     # "auto" | "cuda" | "cpu"

    @property
    def DATABASE_URL(self) -> str:
        if self.SUPABASE_DATABASE_URL:
            url = self.SUPABASE_DATABASE_URL.strip()
            if "://" in url:
                scheme, rest = url.split("://", 1)
                if "@" in rest:
                    parts = rest.rsplit("@", 1)
                    user_pass = parts[0]
                    host_db = parts[1]
                    if ":" in user_pass:
                        user, passwd = user_pass.split(":", 1)
                        import urllib.parse
                        passwd_unquoted = urllib.parse.unquote(passwd)
                        encoded_passwd = urllib.parse.quote_plus(passwd_unquoted)
                        rest = f"{user}:{encoded_passwd}@{host_db}"
                url = f"postgresql+asyncpg://{rest}"
            return url
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Sync URL used by Alembic migrations."""
        if self.SUPABASE_DATABASE_URL:
            url = self.SUPABASE_DATABASE_URL.strip()
            if "://" in url:
                scheme, rest = url.split("://", 1)
                if "@" in rest:
                    parts = rest.rsplit("@", 1)
                    user_pass = parts[0]
                    host_db = parts[1]
                    if ":" in user_pass:
                        user, passwd = user_pass.split(":", 1)
                        import urllib.parse
                        passwd_unquoted = urllib.parse.unquote(passwd)
                        encoded_passwd = urllib.parse.quote_plus(passwd_unquoted)
                        rest = f"{user}:{encoded_passwd}@{host_db}"
                url = f"postgresql+psycopg2://{rest}"
            return url
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return (
                f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:"
                f"{self.REDIS_PORT}/{self.REDIS_DB}"
            )
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @field_validator("ALLOWED_ORIGINS", "ALLOWED_METHODS", "ALLOWED_HEADERS", mode="before")
    @classmethod
    def parse_list_from_string(cls, v: object) -> object:
        if isinstance(v, str):
            v_str = v.strip()
            if v_str.startswith("[") and v_str.endswith("]"):
                try:
                    import json
                    return json.loads(v_str)
                except Exception:
                    pass
            return [item.strip() for item in v_str.split(",") if item.strip()]
        return v


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton)."""
    return Settings()


settings: Settings = get_settings()
