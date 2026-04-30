"""
Production Configuration for GenAI Stock Market System
"""
import os
from datetime import timedelta

class Config:
    """Base configuration"""
    
    # Application Settings
    APP_NAME = "GenAI Stock Market Intelligence"
    VERSION = "2.0.0"
    DEBUG = False
    TESTING = False
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-this-in-production')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'change-this-too')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DB_URL', 
        'postgresql://postgres:Taran%4017@localhost:5432/StockDB'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_size': 10,
        'max_overflow': 20,
        'pool_recycle': 3600,
    }
    
    # CORS Settings
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    CORS_ALLOW_HEADERS = ['Content-Type', 'Authorization']
    CORS_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    
    # Cache Configuration
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CACHE_DEFAULT_TIMEOUT = 3600  # 1 hour
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/1')
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    RATELIMIT_HEADERS_ENABLED = True
    
    # Model Configuration
    MODEL_DIR = os.getenv('MODEL_DIR', 'saved_models')
    MODEL_TRAINING_BATCH_SIZE = 32
    MODEL_SEQUENCE_LENGTH = 60
    MODEL_PREDICTION_DAYS = 5
    
    # Stock Data Configuration
    NSE_LIST_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
    DATA_FETCH_PERIOD = "5y"
    DATA_UPDATE_INTERVAL = 3600  # Update every hour
    
    # Screener Configuration
    SCREENER_MAX_RESULTS = 100
    SCREENER_TIMEOUT = 300  # 5 minutes
    
    # Prediction Configuration
    PREDICTION_CONFIDENCE_THRESHOLD = 0.7
    DEFAULT_CAPITAL = 100000
    DEFAULT_RISK_PERCENTAGE = 2.0
    MIN_RISK_REWARD_RATIO = 1.5
    
    # Logging Configuration
    LOG_DIR = os.getenv('LOG_DIR', 'logs')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    
    # Email Notifications (optional)
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')
    
    # Celery Configuration (for async tasks)
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/2')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/3')
    
    # Monitoring
    SENTRY_DSN = os.getenv('SENTRY_DSN')
    PROMETHEUS_ENABLED = os.getenv('PROMETHEUS_ENABLED', 'true').lower() == 'true'
    
    # Feature Flags
    ENABLE_ENSEMBLE_MODEL = True
    ENABLE_SENTIMENT_ANALYSIS = True
    ENABLE_FUNDAMENTAL_ANALYSIS = True
    ENABLE_AUTO_RETRAINING = True
    
    # API Configuration
    API_TITLE = "GenAI Stock Market API"
    API_VERSION = "v2"
    API_DESCRIPTION = "Advanced stock screening and AI prediction system"
    API_DOCS_URL = "/api/docs"
    
    # Backup Configuration
    BACKUP_ENABLED = True
    BACKUP_DIR = os.getenv('BACKUP_DIR', 'backups')
    BACKUP_RETENTION_DAYS = 30


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    LOG_LEVEL = 'DEBUG'
    CORS_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000']
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Stricter security
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Production rate limits
    RATELIMIT_DEFAULT = "1000 per day;100 per hour;10 per minute"
    
    # Enhanced logging
    LOG_LEVEL = 'WARNING'
    
    # Production cache
    CACHE_TYPE = 'redis'
    CACHE_DEFAULT_TIMEOUT = 7200  # 2 hours


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    CACHE_TYPE = 'simple'
    RATELIMIT_ENABLED = False


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(env=None):
    """Get configuration based on environment"""
    if env is None:
        env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])


# Model Architecture Configurations
MODEL_CONFIGS = {
    'attention_lstm': {
        'hidden_dim': 128,
        'num_layers': 3,
        'dropout': 0.3,
        'num_heads': 8,
        'learning_rate': 0.001,
        'epochs': 50
    },
    'ensemble': {
        'hidden_dim': 128,
        'learning_rate': 0.001,
        'epochs': 50,
        'models': ['attention_lstm', 'transformer']
    }
}


# Screening Strategy Configurations
SCREENING_CONFIGS = {
    'piotroski': {
        'min_score': 7,
        'max_stocks': 50,
        'timeout': 600
    },
    'momentum': {
        'lookback_days': 20,
        'min_return': 5.0,
        'volume_threshold': 1.2,
        'max_stocks': 100
    },
    'swing': {
        'rsi_range': (30, 70),
        'macd_threshold': 0,
        'bb_distance': 0.05,
        'max_stocks': 100
    },
    'breakout': {
        'distance_from_high': 2.0,  # percentage
        'volume_threshold': 1.5,
        'lookback_period': 252,  # 1 year
        'max_stocks': 50
    },
    'value': {
        'max_pe': 15,
        'max_pb': 3,
        'min_dividend_yield': 2,
        'min_roe': 15,
        'max_debt_equity': 100,
        'min_score': 3,
        'max_stocks': 100
    }
}


# Technical Indicator Configurations
TECHNICAL_INDICATORS = {
    'macd': {
        'fast_period': 12,
        'slow_period': 26,
        'signal_period': 9
    },
    'rsi': {
        'period': 14,
        'overbought': 70,
        'oversold': 30
    },
    'bollinger_bands': {
        'period': 20,
        'std_dev': 2
    },
    'adx': {
        'period': 14,
        'strong_trend': 25
    },
    'supertrend': {
        'period': 10,
        'multiplier': 3
    },
    'stochastic': {
        'k_period': 14,
        'd_period': 3
    }
}