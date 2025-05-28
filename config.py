import os
from datetime import timedelta


class Config:
    # Get the base directory of the application
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # Database configuration
    DATABASE_PATH = os.path.join(BASE_DIR, 'instance', 'financial.db')
    
    # Flask configuration
    SECRET_KEY = 'your-secret-key-here'  # Change this in production
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    SESSION_COOKIE_SECURE = False  # Set to True in production
    SESSION_COOKIE_HTTPONLY = True
    
    # Security configuration
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPER = True
    PASSWORD_REQUIRE_LOWER = True
    PASSWORD_REQUIRE_DIGIT = True
    PASSWORD_REQUIRE_SPECIAL = True
    
    # Application settings
    DEBUG = False
    TESTING = False
    ENV = 'production'
    
    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FILE = os.path.join(BASE_DIR, 'logs', 'app.log')
    
    # Feature flags
    ENABLE_ANALYTICS = True
    ENABLE_BUDGET_ALERTS = True
    ENABLE_SAVINGS_GOALS = True
