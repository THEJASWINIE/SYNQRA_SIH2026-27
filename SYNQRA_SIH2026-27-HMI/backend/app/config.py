"""Backend configuration.

Every configurable value is read from the environment, with a development-safe
default. No credential is defined here or anywhere else in source (NFR-011); when
authentication arrives (M12) its secrets are supplied by the environment too.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HMI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "0.0.0.0"
    port: int = 8000

    # Origins allowed to call this API. Comma-separated in the environment,
    # e.g. HMI_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
    #
    # The default names the four fixed dev origins of the HMI build (frontend
    # package.json): control room 5173, TRUCK_01 3001, TRUCK_02 3002, Mine-Cast 3003.
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:3001,http://127.0.0.1:3001,"
        "http://localhost:3002,http://127.0.0.1:3002,"
        "http://localhost:3003,http://127.0.0.1:3003"
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
