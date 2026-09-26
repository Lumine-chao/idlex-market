"""闲置易二手交易平台 服务端配置"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "闲置易二手交易平台"
    db_url: str = "sqlite+aiosqlite:///./idlex.db"
    secret_key: str = "idlex-dev-secret-key-change-in-prod"
    jwt_algorithm: str = "HS256"
    access_token_expire: int = 7200        # 2 小时
    refresh_token_expire: int = 604800     # 7 天
    upload_dir: str = "./uploads"
    public_base: str = "/static"
    dev_sms_return_code: bool = True       # 开发模式：接口直接返回验证码，方便演示


settings = Settings()