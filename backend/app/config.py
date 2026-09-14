from pydantic_settings import BaseSettings, SettingsConfigDict

# 已知不安全的預設密鑰值，正式環境絕不允許使用（此常數本身用於偵測並阻擋弱密鑰，非真正弱點）
_INSECURE_DEFAULT_SECRET = "dev-secret-key"  # nosec B105


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://erp_user:erp_pass_2025@localhost:5432/acrylic_erp"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = _INSECURE_DEFAULT_SECRET
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    TENANT_ID: str = "default"
    MEDIA_ROOT: str = "/app/media"
    DEFAULT_SHEET_LENGTH_MM: float = 2000.0
    DEFAULT_SHEET_WIDTH_MM: float = 1000.0
    DEFAULT_KERF_MM: float = 3.0
    CAI_SIZE_MM: float = 300.0

    # 資安相關：環境識別與CORS白名單
    ENVIRONMENT: str = "development"  # development | production
    CORS_ORIGINS: str = "http://localhost:3000"  # 逗號分隔多個網域

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


settings = Settings()

# 資安防呆：正式環境絕不允許使用預設弱密鑰或過短的密鑰啟動，
# 避免部署時忘記設定SECRET_KEY導致JWT可被任意偽造
if settings.is_production:
    if settings.SECRET_KEY == _INSECURE_DEFAULT_SECRET:
        raise RuntimeError(
            "正式環境（ENVIRONMENT=production）偵測到 SECRET_KEY 仍是不安全的預設值，"
            "請在 .env 設定一組至少32字元的隨機密鑰後再啟動。"
            "可用指令產生： python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )
    if len(settings.SECRET_KEY) < 32:
        raise RuntimeError(
            f"正式環境 SECRET_KEY 長度僅 {len(settings.SECRET_KEY)} 字元，至少需要32字元以確保安全性。"
        )
