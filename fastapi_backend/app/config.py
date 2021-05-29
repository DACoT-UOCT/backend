from pydantic import BaseSettings
from typing import List
from functools import lru_cache


class ConnectionConfig(BaseSettings):
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_PORT: int = 587
    MAIL_FROM: str = 'system-no-reply@dacot.uoct.cl'
    MAIL_SERVER: str = 'smtp.gmail.com'
    MAIL_TLS: bool = True
    MAIL_SSL: bool = False
    USE_CREDENTIALS: bool = True
    TEMPLATES_DIR: str = '/app/email_templates/'


class Settings(BaseSettings):
    app_name: str = "DACoT API"
    mongo_uri: str
    mail_user: str
    mail_pass: str
    mail_config: ConnectionConfig = None
    authjwt_secret_key: str
    apikey_users_file: str = '/app/fake_users.json'

settings = Settings()

if settings.mail_user:
    settings.mail_config = ConnectionConfig(MAIL_USERNAME=settings.mail_user, MAIL_PASSWORD=settings.mail_pass)

@lru_cache()
def get_settings():
    return settings
