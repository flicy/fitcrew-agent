from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BODYOS_", env_file=None, extra="ignore", populate_by_name=True
    )

    environment: str = "development"
    database_url: str = "sqlite+pysqlite:///:memory:"
    encryption_key: SecretStr = SecretStr("")
    owner_token: SecretStr = SecretStr("")
    identity_pepper: SecretStr = SecretStr("")
    internal_token: SecretStr = SecretStr("")
    model_proxy_token: SecretStr = SecretStr("")
    public_base_url: str = "http://127.0.0.1:8000"
    codex_command: str = "codex"
    hermes_command: str = "hermes"
    hermes_model: str = "gpt-5.3-codex-spark"
    model_timeout_seconds: int = 120
    study_start_date: str = ""
    log_level: str = "INFO"
    feishu_app_id: str = Field(default="", validation_alias="FEISHU_APP_ID")
    feishu_app_secret: SecretStr = Field(
        default=SecretStr(""), validation_alias="FEISHU_APP_SECRET"
    )
    feishu_allowed_group_id: str = Field(
        default="", validation_alias="FEISHU_ALLOWED_GROUP_ID"
    )
    proactive_group_enabled: bool = False
    group_timezone: str = "Asia/Shanghai"
    group_morning_time: str = "09:00"
    group_evening_time: str = "20:30"
    group_weekly_weekday: int = 2
    group_weekly_time: str = "12:15"
    group_quiet_start: str = "22:00"
    group_quiet_end: str = "08:00"


@lru_cache
def get_settings() -> Settings:
    return Settings()
