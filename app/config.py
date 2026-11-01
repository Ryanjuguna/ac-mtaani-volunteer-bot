import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # App Settings
    APP_NAME: str = "American Corner Mtaani Volunteer Task Manager"
    APP_ENV: str = os.getenv("APP_ENV", "development")
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    
    # Task Trigger Tag (e.g. '@task', '#task')
    TASK_TRIGGER_TAG: str = os.getenv("TASK_TRIGGER_TAG", "@task").lower()
    
    # Gemini AI
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    # WhatsApp Gateway (Green API or mock)
    WHATSAPP_PROVIDER: str = os.getenv("WHATSAPP_PROVIDER", "mock") # "green_api" or "mock"
    GREEN_API_INSTANCE_ID: str = os.getenv("GREEN_API_INSTANCE_ID", "")
    GREEN_API_TOKEN: str = os.getenv("GREEN_API_TOKEN", "")
    MTAANI_GROUP_CHAT_ID: str = os.getenv("MTAANI_GROUP_CHAT_ID", "12036304@g.us")
    COORDINATOR_PHONE: str = os.getenv("COORDINATOR_PHONE", "+254752901669")
    
    # SAFETY LOCK: Prevent messaging real volunteers without permission
    LIVE_SENDING_ENABLED: bool = os.getenv("LIVE_SENDING_ENABLED", "false").lower() in ("true", "1", "yes")
    WHITELISTED_PHONES: list = [os.getenv("COORDINATOR_PHONE", "+254752901669")]
    
    # Google Sheets Integration
    ENABLE_SHEETS_SYNC: bool = os.getenv("ENABLE_SHEETS_SYNC", "false").lower() in ("true", "1", "yes")
    GOOGLE_SHEET_ID: str = os.getenv("GOOGLE_SHEET_ID", "")
    GOOGLE_SERVICE_ACCOUNT_FILE: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials.json")
    
    # Storage
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "./data/tasks.db")
    VOLUNTEERS_FILE: str = os.getenv("VOLUNTEERS_FILE", "./data/volunteers.json")

settings = Settings()
