from pydantic_settings import BaseSettings

class Settings(BaseSettings):
	PROJECT_NAME: str = "Task Master API"
	DEBUG: bool = False
	SECRET_KEY: str
	DATABASE_URL: str = "sqlite+aiosqlite:///task_master.db"
	ALGORITHM: str = "HS256"
	ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
	
	class Config:
		env_file = ".env"

# This reads the .env file automatically!
settings = Settings()
