from __future__ import annotations

from google.oauth2 import service_account

from config import SCOPES, SERVICE_ACCOUNT_FILE


def load_credentials() -> service_account.Credentials:
    return service_account.Credentials.from_service_account_file(
        str(SERVICE_ACCOUNT_FILE),
        scopes=SCOPES,
    )
