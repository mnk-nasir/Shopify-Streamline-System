"""
config.py

Centralized config for the Shopify orders companion script.
Reads values from a .env file (via python-dotenv) where appropriate.
"""
from pathlib import Path
from dotenv import load_dotenv
import os

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

def getenv(k: str, default=None):
    v = os.getenv(k)
    return v if v is not None else default

# Harvest
HARVEST_TOKEN = getenv("HARVEST_TOKEN")  # Bearer token for Harvest API
HARVEST_ACCOUNT_ID = getenv("HARVEST_ACCOUNT_ID")  # Account/client id used in invoices

# Trello
TRELLO_KEY = getenv("TRELLO_KEY")
TRELLO_TOKEN = getenv("TRELLO_TOKEN")
TRELLO_LIST_ID = getenv("TRELLO_LIST_ID")  # list id where to create cards

# Zoho
ZOHO_ACCESS_TOKEN = getenv("ZOHO_ACCESS_TOKEN")

# Mailchimp
MAILCHIMP_API_KEY = getenv("MAILCHIMP_API_KEY")
MAILCHIMP_LIST_ID = getenv("MAILCHIMP_LIST_ID")
MAILCHIMP_SERVER_PREFIX = getenv("MAILCHIMP_SERVER_PREFIX")  # e.g., "us1"

# Gmail / SMTP (simple)
GMAIL_SMTP_SERVER = getenv("GMAIL_SMTP_SERVER", "smtp.gmail.com")
GMAIL_SMTP_PORT = getenv("GMAIL_SMTP_PORT", "587")
GMAIL_SMTP_USER = getenv("GMAIL_SMTP_USER")
GMAIL_SMTP_PASS = getenv("GMAIL_SMTP_PASS")

# App-level defaults
OUTPUT_DIR = getenv("OUTPUT_DIR", str(ROOT / "outputs"))

# Coupon and tags
COUPON_THRESHOLD = float(getenv("COUPON_THRESHOLD", "50"))
COUPON_CODE = getenv("COUPON_CODE", "COUPON15")
MAILCHIMP_HIGH_ORDER_TAG = getenv("MAILCHIMP_HIGH_ORDER_TAG", "high-order")

def as_dict():
    return {
        "HARVEST_TOKEN": HARVEST_TOKEN,
        "HARVEST_ACCOUNT_ID": HARVEST_ACCOUNT_ID,
        "TRELLO_KEY": TRELLO_KEY,
        "TRELLO_TOKEN": TRELLO_TOKEN,
        "TRELLO_LIST_ID": TRELLO_LIST_ID,
        "ZOHO_ACCESS_TOKEN": ZOHO_ACCESS_TOKEN,
        "MAILCHIMP_API_KEY": MAILCHIMP_API_KEY,
        "MAILCHIMP_LIST_ID": MAILCHIMP_LIST_ID,
        "MAILCHIMP_SERVER_PREFIX": MAILCHIMP_SERVER_PREFIX,
        "GMAIL_SMTP_SERVER": GMAIL_SMTP_SERVER,
        "GMAIL_SMTP_PORT": GMAIL_SMTP_PORT,
        "GMAIL_SMTP_USER": GMAIL_SMTP_USER,
        "OUTPUT_DIR": OUTPUT_DIR,
    }
