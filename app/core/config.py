from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.roles import Rol


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    default_rol: Rol = Rol.ADMINISTRADOR
    cors_origins: str = "*"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origen.strip() for origen in self.cors_origins.split(",") if origen.strip()]


settings = Settings()
