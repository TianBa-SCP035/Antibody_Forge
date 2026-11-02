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
DEFAULT_DATABASE_URL = "mysql+pymysql://root:@localhost:3306/bbctg_vita"
DEFAULT_SECRET_KEY = "please-change-me"
MIN_PROD_SECRET_LENGTH = 32


class Settings(BaseSettings):
    app_env: str = DETECTED_APP_ENV
    app_name: str = "Antibody Forge API"
    host: str = "0.0.0.0"
    port: int = 8888
    debug: bool = False
    enable_scheduler: bool = False

    database_url: str = DEFAULT_DATABASE_URL
    secret_key: str = DEFAULT_SECRET_KEY

    repository_root: Path = Field(default=PROJECT_ROOT / "repository")
    cors_origins: str = "http://localhost:5555,http://127.0.0.1:5555"
    upload_max_mb: int = 50

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
    one_db_url: str = ""
    labillion_base_url: str = ""
    labillion_username: str = ""
    labillion_password: str = ""
    labillion_platform_id: str = ""
    # 外部系统回调校验：留空不校验；令牌走请求头 X-Callback-Token，IP 用英文逗号分隔
    labillion_callback_token: str = ""
    labillion_callback_ips: str = ""
    order_sync_token: str = ""
    order_sync_ips: str = ""
    order_sync_max_mb: int = 20
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
    def upload_max_bytes(self) -> int:
        return max(self.upload_max_mb, 1) * 1024 * 1024

    def runtime_problems(self) -> list[str]:
        """生产环境不能带着开发默认值启动。"""
        if self.app_env != "prod":
            return []
        problems = []
        if self.database_url == DEFAULT_DATABASE_URL:
            problems.append("DATABASE_URL 未配置")
        if self.secret_key == DEFAULT_SECRET_KEY or len(self.secret_key) < MIN_PROD_SECRET_LENGTH:
            problems.append(f"SECRET_KEY 未配置或短于 {MIN_PROD_SECRET_LENGTH} 位")
        origins = self.cors_origin_list
        if "*" in origins or any("example" in item for item in origins):
            problems.append("CORS_ORIGINS 只能填实际前端域名（同域部署可留空），不能是 * 或示例域名")
        if self.debug:
            problems.append("DEBUG 不能开启")
        return problems

    @property
    def should_start_scheduler(self) -> bool:
        return self.enable_scheduler or self.app_env == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()
