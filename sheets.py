"""
Google Sheets read / write / formatting helpers.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import HEADERS
from utils import retry

logger = logging.getLogger(__name__)


def _get_service(credentials: Credentials):
    return build("sheets", "v4", credentials=credentials, cache_discovery=False)


def get_sheet_id_by_name(service: Any, spreadsheet_id: str, title: str) -> int:
    """Return the numeric sheetId for a given sheet title."""
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for sheet in meta.get("sheets", []):
        props = sheet.get("properties", {})
        if props.get("title") == title:
            return int(props["sheetId"])
    raise ValueError(f"Sheet '{title}' not found in spreadsheet {spreadsheet_id}")


@retry(max_attempts=3, base_delay=1.5)
def get_existing_values(
    credentials: Credentials,
    spreadsheet_id: str,
    sheet_name: str,
) -> List[List[Any]]:
    """Return all values currently in the sheet (may be empty)."""
    service = _get_service(credentials)
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=sheet_name)
        .execute()
    )
    return result.get("values", [])


def month_already_exists(values: List[List[Any]], month_label: str) -> bool:
    """Check whether a row with the given month label already exists."""
    for row in values:
        if row and str(row[0]).strip() == month_label:
            return True
    return False


@retry(max_attempts=3, base_delay=1.5)
def ensure_headers(
    credentials: Credentials,
    spreadsheet_id: str,
    sheet_name: str,
    values: List[List[Any]],
) -> None:
    """Write the header row if the sheet is currently empty."""
    if values:
        return

    service = _get_service(credentials)
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A1",
        valueInputOption="USER_ENTERED",
        body={"values": [HEADERS], "majorDimension": "ROWS"},
    ).execute()

    # Bold the header row + freeze it
    sheet_id = get_sheet_id_by_name(service, spreadsheet_id, sheet_name)
    requests = [
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                },
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"bold": True},
                    }
                },
                "fields": "userEnteredFormat.textFormat.bold",
            }
        },
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {"frozenRowCount": 1},
                },
                "fields": "gridProperties.frozenRowCount",
            }
        },
    ]
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": requests}
    ).execute()
    logger.info("Wrote header row and froze first row")


@retry(max_attempts=3, base_delay=1.5)
def write_and_format_row(
    credentials: Credentials,
    spreadsheet_id: str,
    sheet_name: str,
    row: List[Any],
    existing_row_count: int,
) -> int:
    """
    Append a data row and format the CTR column as percent.
    Returns the 1-based row number that was written.
    """
    service = _get_service(credentials)
    next_row = existing_row_count + 1
    range_name = f"{sheet_name}!A{next_row}"

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption="USER_ENTERED",
        body={"values": [row], "majorDimension": "ROWS"},
    ).execute()

    # Format CTR column (index 13 → column N) as 0.0%
    sheet_id = get_sheet_id_by_name(service, spreadsheet_id, sheet_name)
    requests = [
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": next_row - 1,
                    "endRowIndex": next_row,
                    "startColumnIndex": 13,
                    "endColumnIndex": 14,
                },
                "cell": {
                    "userEnteredFormat": {
                        "numberFormat": {"type": "PERCENT", "pattern": "0.0%"}
                    }
                },
                "fields": "userEnteredFormat.numberFormat",
            }
        }
    ]
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": requests}
    ).execute()

    logger.info("Wrote data to row %d", next_row)
    return next_row
