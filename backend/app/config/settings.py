import os

from dotenv import load_dotenv

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "PaymentOps AI")
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./paymentops.db",
)

HYPERSWITCH_BASE_URL = os.getenv(
    "HYPERSWITCH_BASE_URL",
    "http://localhost:8080",
)

HYPERSWITCH_API_KEY = os.getenv(
    "HYPERSWITCH_API_KEY",
)

WEBHOOK_SHARED_SECRET = os.getenv("WEBHOOK_SHARED_SECRET")

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

HYPERSWITCH_TIMEOUT_SECONDS = float(
    os.getenv(
        "HYPERSWITCH_TIMEOUT_SECONDS",
        "10",
    )
)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().lower()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash",
)
