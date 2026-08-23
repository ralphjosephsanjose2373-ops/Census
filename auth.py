"""
Google service-account authentication.
"""

from __future__ import annotations

from google.oauth2 import service_account

from config import SCOPES, SERVICE_ACCOUNT_FILE


def load_credentials() -> service_account.Credentials:
    """Load service-account credentials with the required scopes."""
    return service_account.Credentials.from_service_account_file(
        str(SERVICE_ACCOUNT_FILE),
        scopes=SCOPES,
    )
