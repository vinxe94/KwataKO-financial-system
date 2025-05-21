import os
from datetime import timedelta


class Config:
    # Base directory
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # Database
    SQLITE_DB = os.path.join(BASE_DIR, 'financial.db')
    DATABASE_PATH = os.path.join(BASE_DIR, 'financial.db')
    
    # Security
    SECRET_KEY = 'dev-key-12345'  # Change this in production
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # Allow HTTP in development
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    
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
