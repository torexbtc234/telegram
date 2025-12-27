"""
Configuration settings using Pydantic
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    """Application settings"""
    
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_GROUP_ID: str = os.getenv("TELEGRAM_GROUP_ID", "")
    TELEGRAM_ADMIN_IDS: str = os.getenv("TELEGRAM_ADMIN_IDS", "")
    
    # Server Configuration
    PORT: int = int(os.getenv("PORT", 8000))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # WebSocket Configuration
    WS_PING_INTERVAL: int = int(os.getenv("WS_PING_INTERVAL", 30))
    WS_PING_TIMEOUT: int = int(os.getenv("WS_PING_TIMEOUT", 60))
    WS_MAX_SIZE: int = int(os.getenv("WS_MAX_SIZE", 10485760))  # 10MB
    
    # Session Configuration
    SESSION_TIMEOUT: int = int(os.getenv("SESSION_TIMEOUT", 86400))  # 24 hours
    MAX_SESSIONS: int = int(os.getenv("MAX_SESSIONS", 1000))
    CLEANUP_INTERVAL: int = int(os.getenv("CLEANUP_INTERVAL", 300))  # 5 minutes
    
    # File Configuration
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", 52428800))  # 50MB
    TEMP_DIR: str = os.getenv("TEMP_DIR", "./temp")
    ALLOWED_EXTENSIONS: str = os.getenv(
        "ALLOWED_EXTENSIONS", 
        "jpg,jpeg,png,gif,mp3,mp4,ogg,pdf,doc,docx,txt"
    )
    
    # Security
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "https://yourdomain.com,http://localhost:3000")
    ENABLE_CORS: bool = os.getenv("ENABLE_CORS", "True").lower() == "true"
    RATE_LIMIT: int = int(os.getenv("RATE_LIMIT", 100))
    
    # Redis Configuration (optional)
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")
    REDIS_ENABLED: bool = os.getenv("REDIS_ENABLED", "False").lower() == "true"
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[str] = os.getenv("LOG_FILE")
    
    # Monitoring
    ENABLE_METRICS: bool = os.getenv("ENABLE_METRICS", "True").lower() == "true"
    METRICS_PORT: int = int(os.getenv("METRICS_PORT", 9090))
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def get_allowed_origins_list(self) -> List[str]:
        """Get allowed origins as list"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    def get_allowed_extensions_list(self) -> List[str]:
        """Get allowed file extensions as list"""
        return [ext.strip().lower() for ext in self.ALLOWED_EXTENSIONS.split(",")]
    
    def get_admin_ids_list(self) -> List[int]:
        """Get admin IDs as list"""
        if not self.TELEGRAM_ADMIN_IDS:
            return []
        return [int(id_str.strip()) for id_str in self.TELEGRAM_ADMIN_IDS.split(",")]

# Global settings instance
settings = Settings()
