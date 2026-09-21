from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.roles import Rol


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    default_rol: Rol = Rol.ADMINISTRADOR


settings = Settings()
