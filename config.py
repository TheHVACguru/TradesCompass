"""
Centralized configuration for TradesCompass Pro
Manages all API keys and environment variables
"""
import os
from typing import Optional

class Config:
    """Application configuration"""
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///resume_scanner.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # Session
    SECRET_KEY = os.getenv('SESSION_SECRET', 'dev-secret-key-change-in-production')
    
    # Core AI Service
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    XAI_API_KEY = os.getenv('XAI_API_KEY')  # For Grok AI model
    
    # Job Search APIs
    RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY')  # For JSearch
    ZIPRECRUITER_API_KEY = os.getenv('ZIPRECRUITER_API_KEY')
    INDEED_PUBLISHER_ID = os.getenv('INDEED_PUBLISHER_ID')
    USAJOBS_API_KEY = os.getenv('USAJOBS_API_KEY')
    USAJOBS_USER_AGENT = os.getenv('USAJOBS_USER_AGENT', 'TradesCompass')
    
    # External Sourcing APIs
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
    PEOPLEDATA_KEY = os.getenv('PEOPLEDATA_KEY')
    SEEKOUT_API_KEY = os.getenv('SEEKOUT_API_KEY')
    SOURCEHUB_API_KEY = os.getenv('SOURCEHUB_API_KEY')
    
    # Email Processing
    EMAIL_USER = os.getenv('EMAIL_USER')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
    IMAP_SERVER = os.getenv('IMAP_SERVER', 'imap.gmail.com')
    IMAP_PORT = int(os.getenv('IMAP_PORT', '993'))
    EMAIL_FOLDER = os.getenv('EMAIL_FOLDER', 'INBOX')
    EMAIL_CHECK_INTERVAL = int(os.getenv('EMAIL_CHECK_INTERVAL', '300'))
    
    # Salesforce (optional)
    SALESFORCE_USERNAME = os.getenv('SALESFORCE_USERNAME')
    SALESFORCE_PASSWORD = os.getenv('SALESFORCE_PASSWORD')
    SALESFORCE_SECURITY_TOKEN = os.getenv('SALESFORCE_SECURITY_TOKEN')
    
    # SendGrid (optional)
    SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
    SENDGRID_FROM_EMAIL = os.getenv('SENDGRID_FROM_EMAIL')
    
    @classmethod
    def get_missing_keys(cls) -> dict:
        """Check which API keys are missing and return status"""
        status = {
            'core': {
                'openai': bool(cls.OPENAI_API_KEY),
            },
            'job_search': {
                'jsearch': bool(cls.RAPIDAPI_KEY),
                'ziprecruiter': bool(cls.ZIPRECRUITER_API_KEY),
                'indeed': bool(cls.INDEED_PUBLISHER_ID),
                'usajobs': bool(cls.USAJOBS_API_KEY),
            },
            'sourcing': {
                'github': bool(cls.GITHUB_TOKEN),
                'peopledata': bool(cls.PEOPLEDATA_KEY),
                'seekout': bool(cls.SEEKOUT_API_KEY),
                'sourcehub': bool(cls.SOURCEHUB_API_KEY),
            },
            'email': {
                'configured': bool(cls.EMAIL_USER and cls.EMAIL_PASSWORD),
            },
            'optional': {
                'salesforce': bool(cls.SALESFORCE_USERNAME and cls.SALESFORCE_PASSWORD),
                'sendgrid': bool(cls.SENDGRID_API_KEY),
            }
        }
        return status
    
    @classmethod
    def get_sourcing_providers(cls) -> list:
        """Get list of configured sourcing providers"""
        providers = []
        if cls.GITHUB_TOKEN:
            providers.append('GitHub')
        if cls.PEOPLEDATA_KEY:
            providers.append('PeopleDataLabs')
        if cls.SEEKOUT_API_KEY:
            providers.append('SeekOut')
        if cls.SOURCEHUB_API_KEY:
            providers.append('SourceHub')
        return providers
    
    @classmethod
    def get_job_search_providers(cls) -> list:
        """Get list of configured job search providers"""
        providers = []
        if cls.RAPIDAPI_KEY:
            providers.append('JSearch (150,000+ sources)')
        if cls.ZIPRECRUITER_API_KEY:
            providers.append('ZipRecruiter')
        if cls.INDEED_PUBLISHER_ID:
            providers.append('Indeed')
        if cls.USAJOBS_API_KEY:
            providers.append('USAJobs')
        return providers

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}