import os

from dotenv import load_dotenv

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "PaymentOps AI")
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./paymentops.db",
)
