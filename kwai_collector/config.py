from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

A1_Radar = "A1_Radar"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KWAI_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    max_tentativas: int = Field(
        default=3,
        ge=1,
    )

    backoff_base: float = Field(
        default=1.0,
        ge=0,
    )

    delay: float = Field(
        default=0.0,
        ge=0,
    )

    cookie: str | None = None

    adb_path: str = "adb"

    adb_serial: str | None = None

    kwai_package: str = "com.kwai.video"

    max_comment_scrolls: int = Field(
        default=100,
        ge=1,
    )


settings = Settings()