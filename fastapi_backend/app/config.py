from pydantic import BaseSettings
from typing import List
from functools import lru_cache
from fastapi_mail import ConnectionConfig

class Settings(BaseSettings):
    app_name: str = "DACoT API"
    mongo_uri: str
    mail_user: str
    mail_pass: str
    mail_config: ConnectionConfig = None
    mail_enabled: bool = False
    mail_extra_targets: List[str] = list()
    authjwt_secret_key: str
    apikey_users_file: str = '/app/fake_users.json'

settings = Settings()

if settings.mail_user and settings.mail_pass:
    settings.mail_config = ConnectionConfig(
        MAIL_USERNAME=settings.mail_user,
        MAIL_PASSWORD=settings.mail_pass,
        MAIL_PORT=587,
        MAIL_FROM='system-no-reply@dacot.uoct.cl',
        MAIL_SERVER='smtp.gmail.com',
        MAIL_TLS=True,
        MAIL_SSL=False,
        USE_CREDENTIALS=True,
        TEMPLATE_FOLDER='/app/email_templates/'
    )
    settings.mail_enabled = False

@lru_cache()
def get_settings():
    return settings
