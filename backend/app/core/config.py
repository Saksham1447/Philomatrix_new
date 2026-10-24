import json
from typing import List, Union

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_DEFAULT_JWT_SECRET = "super_secret_jwt_key_philomatrix_2026_change_in_production"


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "PHILOMATRIX SOFTWARE"
    API_V1_STR: str = "/api/v1"

    # Security
    JWT_SECRET: str = _DEFAULT_JWT_SECRET
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # MongoDB Atlas. A URI is mandatory in production; development tests inject a client.
    MONGODB_URI: str | None = None
    MONGODB_DB_PREFIX: str = "philomatrix"
    # Reserved for the user-controlled migration source. Application code never consumes it.
    LEGACY_DATABASE_URL: str = ""

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, value: Union[str, List[str]]) -> List[str]:
        if isinstance(value, str):
            if value.startswith("[") and value.endswith("]"):
                try:
                    return json.loads(value)
                except (TypeError, ValueError):
                    pass
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, list):
            return value
        return []

    # Super Admin Bootstrap
    SUPERADMIN_EMAIL: str = "superadmin@philomatrix.local"
    SUPERADMIN_PASSWORD: str = "Philomatrix@2026"

    @model_validator(mode="after")
    def validate_production_configuration(self):
        if self.ENVIRONMENT.strip().lower() == "production":
            if not self.MONGODB_URI:
                raise ValueError("MONGODB_URI is required in production")
            if self.JWT_SECRET == _DEFAULT_JWT_SECRET:
                raise ValueError("JWT_SECRET must be explicitly configured in production")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
