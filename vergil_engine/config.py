import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    auth0_domain: str = "dev-zj40rdlscwsa521x.us.auth0.com"
    auth0_client_id: str = "FD1kHnwhxOB8h7GLlfLI7o4knFd3b3SN"
    auth0_client_secret: str = "p9LDgYF6dY5EE9LSkQ2iDOF8gtreEJzt7tQh2y3Lbi2cvsI513248K4-4dO77yMK"
    auth0_audience: str = "https://vergil.local/api"
    redis_url: str = "redis://localhost:6379"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
