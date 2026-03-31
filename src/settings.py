from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gcp_project_id: str
    gcp_location: str = "us-central1"
    gemini_model: str = "gemini-2.5-flash-preview-04-17"


settings = Settings()
