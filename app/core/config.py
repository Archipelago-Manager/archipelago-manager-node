from typing import Literal
from pydantic import (
        BaseModel,
        AnyUrl,
        PostgresDsn,
        computed_field
        )
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class PostgresSettings(BaseModel):
    SERVER: str
    PORT: int = 5432
    USER: str
    PASSWORD: str = ""
    DB: str = ""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
            env_file=".env",
            env_ignore_empty=True,
            env_nested_delimiter='_'
            )

    ARCHIPELAGO_PORT_START: int = 38281
    ARCHIPELAGO_PORT_END: int = 38300

    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    DB_BACKEND: Literal["sqlite", "postgres"] = "sqlite"

    SQLITE_FILE_NAME: str | None = f"database_{ENVIRONMENT}.db"

    POSTGRES: PostgresSettings | None = None

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> AnyUrl | PostgresDsn:
        if self.DB_BACKEND == "postgres":
            return MultiHostUrl.build(
                scheme="postgresql+psycopg",
                username=self.POSTGRES.USER,
                password=self.POSTGRES.PASSWORD,
                host=self.POSTGRES.SERVER,
                port=self.POSTGRES.PORT,
                path=self.POSTGRES.DB,
            )
        else:  # Default to sqlite
            return AnyUrl(f"sqlite:///{self.SQLITE_FILE_NAME}")


settings = Settings()
