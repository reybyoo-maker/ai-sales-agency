import os

MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.6-flash')
PORTFOLIO_URL = os.getenv('PORTFOLIO_URL', 'https://reynaldi-sonjaya.lynk.id/p/Reylandingpage')
WA_NUMBER = os.getenv('WA_NUMBER', '')
TIMEZONE = os.getenv('TIMEZONE', 'Asia/Jakarta')
DAILY_OUTREACH_LIMIT = int(os.getenv('DAILY_OUTREACH_LIMIT', '50'))
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '5'))
MIN_MINUTES_BETWEEN_SENDS = int(os.getenv('MIN_MINUTES_BETWEEN_SENDS', '15'))
