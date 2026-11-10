from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
	PROJECT_NAME: str = "Task Master API"
	DEBUG: bool = False
	SECRET_KEY: str
	DATABASE_URL: str = "sqlite+aiosqlite:///task_master.db"
	REDIS_URL: str = "redis://localhost:6379"
	ALGORITHM: str = "HS256"
	ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
	
	model_config = SettingsConfigDict(env_file=".env", extra="ignore")

# This reads the .env file automatically!
settings = Settings()
