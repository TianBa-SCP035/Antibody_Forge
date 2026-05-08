from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = PROJECT_ROOT / "config" / "local" / "vita_server.env"


class Settings(BaseSettings):
    app_env: str = "local"
    app_name: str = "Antibody Forge API"
    host: str = "0.0.0.0"
    port: int = 9091
    debug: bool = False

    database_url: str = "mysql+pymysql://root:@localhost:3306/bbctg_vita"
    secret_key: str = "please-change-me"

    repository_root: Path = Field(default=PROJECT_ROOT / "repository")
    legacy_titer_upload_root: Path | None = None
    cors_origins: str = "http://localhost:5777,http://127.0.0.1:5777"

    yunzhijia_appid: str = ""
    yunzhijia_appsecret: str = ""
    equip_appid: str = ""
    equip_appsecret: str = ""
    cell_db_url: str = ""
    dev_user_openid: str = ""
    dev_user_name: str = "周科钢 Kegang Zhou"

    model_config = SettingsConfigDict(
        env_file=DEFAULT_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def model_post_init(self, __context: Any) -> None:
        if not self.repository_root.is_absolute():
            self.repository_root = (PROJECT_ROOT / self.repository_root).resolve()
        if self.legacy_titer_upload_root and not self.legacy_titer_upload_root.is_absolute():
            self.legacy_titer_upload_root = (PROJECT_ROOT / self.legacy_titer_upload_root).resolve()

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
