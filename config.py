import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Notification Configuration
NOTIFICATION_METHOD = os.getenv('NOTIFICATION_METHOD', 'email').lower()  # 'email' or 'sms'

# Email Configuration
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USE_TLS = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
EMAIL_FROM = os.getenv('EMAIL_FROM')
EMAIL_TO = os.getenv('EMAIL_TO')

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_FROM_NUMBER = os.getenv('TWILIO_FROM_NUMBER')
TWILIO_TO_NUMBER = os.getenv('TWILIO_TO_NUMBER')

# URLs
VISA_BULLETIN_BASE_URL = 'https://travel.state.gov/content/travel/en/legal/visa-law0/visa-bulletin.html'

# File paths
DATA_DIR = 'data'
LOGS_DIR = 'logs'
HISTORY_FILE = os.path.join(DATA_DIR, 'visa_bulletin_history.json')
STATE_FILE = os.path.join(DATA_DIR, 'scraper_state.json')

# Scraping Configuration
SCRAPE_INTERVAL_MINUTES = 15  # Run every 15 minutes during business hours
TIMEZONE = 'America/New_York'  # Eastern Time

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.path.join(LOGS_DIR, 'visa_scraper.log')
