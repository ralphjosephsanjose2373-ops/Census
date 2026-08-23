"""
Configuration loader and constants.
All secrets and environment-specific values come from environment variables
or a .env file.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Paths & credentials
# ---------------------------------------------------------------------------
SERVICE_ACCOUNT_FILE = Path(
    os.getenv("SERVICE_ACCOUNT_FILE", "service-account.json")
).expanduser().resolve()

SHEET_ID = os.getenv("SHEET_ID", "").strip()
SHEET_NAME = os.getenv("SHEET_NAME", "2024").strip()
GA4_PROPERTY_ID = os.getenv("GA4_PROPERTY_ID", "").strip()  # e.g. properties/123456789
SITE_URL = os.getenv("SITE_URL", "https://www.ideellmarknadsforing.se/").strip()
LOG_FILE = Path(os.getenv("LOG_FILE", "data_integration.log")).expanduser()

# Optional notification (leave empty to disable)
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "").strip()
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
NOTIFY_EMAIL_TO = os.getenv("NOTIFY_EMAIL_TO", "").strip()

# ---------------------------------------------------------------------------
# Google API scopes
# ---------------------------------------------------------------------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly",
]

# ---------------------------------------------------------------------------
# Business constants (easy to change without touching logic)
# ---------------------------------------------------------------------------
# Order is preserved when writing to the sheet
CHANNELS = [
    "Organic Social",
    "Direct",
    "Organic Search",
    "Referral",
]

CUSTOM_EVENTS = [
    "user_spent_2_minutes",
    "bli_medlem_klick",
]

# Column headers written when the sheet is empty
HEADERS = [
    "Month",
    "Users",
    "New Users",
    "Events",
    "Avg Engagement (mm:ss)",
    "Eng. Sessions – Organic Social",
    "Eng. Sessions – Direct",
    "Eng. Sessions – Organic Search",
    "Eng. Sessions – Referral",
    "Users – spent ≥2 min",
    "Users – Bli medlem click",
    "GSC Clicks",
    "GSC Impressions",
    "GSC CTR",
    "GSC Avg Position",
]


def validate_config() -> None:
    """Fail fast with clear messages if required settings are missing."""
    errors: list[str] = []

    if not SERVICE_ACCOUNT_FILE.exists():
        errors.append(f"SERVICE_ACCOUNT_FILE not found: {SERVICE_ACCOUNT_FILE}")
    if not SHEET_ID:
        errors.append("SHEET_ID is required")
    if not GA4_PROPERTY_ID:
        errors.append("GA4_PROPERTY_ID is required (e.g. properties/123456789)")
    if not SITE_URL:
        errors.append("SITE_URL is required")

    if errors:
        raise SystemExit(
            "Configuration errors:\n  - " + "\n  - ".join(errors)
            + "\n\nSee .env.example for required variables."
        )
