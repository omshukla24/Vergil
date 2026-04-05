import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    auth0_domain: str = "your_tenant.us.auth0.com"
    auth0_client_id: str = "your_client_id"
    auth0_client_secret: str = "your_client_secret"
    auth0_audience: str = "https://your_api_identifier"
    redis_url: str = "redis://localhost:6379"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
