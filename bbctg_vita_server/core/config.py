from functools import lru_cache
import os
from pathlib import Path
import sys
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _detect_app_env() -> str:
    if sys.platform.startswith("win"):
        return "local"
    if PROJECT_ROOT.parent.name.lower() == "prod":
        return "prod"
    return "test"


def _resolve_env_file() -> Path:
    explicit_env_file = os.getenv("VITA_SERVER_ENV_FILE")
    if explicit_env_file:
        return Path(os.path.expandvars(explicit_env_file)).expanduser()
    app_env = (os.getenv("APP_ENV") or _detect_app_env()).strip().lower()
    return PROJECT_ROOT / "config" / app_env / "vita_server.env"


DETECTED_APP_ENV = _detect_app_env()
DEFAULT_ENV_FILE = _resolve_env_file()


class Settings(BaseSettings):
    app_env: str = DETECTED_APP_ENV
    app_name: str = "Antibody Forge API"
    host: str = "0.0.0.0"
    port: int = 8888
    debug: bool = False
    enable_scheduler: bool = False

    database_url: str = "mysql+pymysql://root:@localhost:3306/bbctg_vita"
    secret_key: str = "please-change-me"

    repository_root: Path = Field(default=PROJECT_ROOT / "repository")
    cors_origins: str = "http://localhost:5555,http://127.0.0.1:5555"

    yunzhijia_appid: str = ""
    yunzhijia_appsecret: str = ""
    drm_enabled: bool = True
    drm_lib_dir: str = ""
    drm_server_ssl: bool = False
    drm_server_host: str = ""
    drm_server_port: int = 0
    drm_user_id: str = ""
    drm_password: str = ""
    drm_config_path: Path = Field(default=PROJECT_ROOT / "repository" / "cache" / "drm")
    drm_encrypt_owner_id: str = ""
    drm_encrypt_secret_level_id: int = 1
    equip_appid: str = ""
    equip_appsecret: str = ""
    cell_db_url: str = ""
    employee_db_url: str = ""
    dev_user_openid: str = ""
    dev_user_name: str = "周科钢 Kegang Zhou"
    labillion_base_url: str = ""
    labillion_username: str = ""
    labillion_password: str = ""
    public_api_base_url: str = ""

    model_config = SettingsConfigDict(
        env_file=DEFAULT_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def model_post_init(self, __context: Any) -> None:
        self.app_env = (self.app_env or "local").strip().lower()
        if not self.repository_root.is_absolute():
            self.repository_root = (PROJECT_ROOT / self.repository_root).resolve()
        if not self.drm_config_path.is_absolute():
            self.drm_config_path = (PROJECT_ROOT / self.drm_config_path).resolve()

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def should_start_scheduler(self) -> bool:
        return self.enable_scheduler or self.app_env == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()
