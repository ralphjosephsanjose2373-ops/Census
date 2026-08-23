"""
Google Search Console data fetching.
"""

from __future__ import annotations

import logging
from datetime import date

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from models import SearchConsoleData
from utils import retry

logger = logging.getLogger(__name__)


@retry(max_attempts=4, base_delay=2.0)
def fetch_search_console_data(
    credentials: Credentials,
    site_url: str,
    start: date,
    end: date,
) -> SearchConsoleData:
    """Fetch aggregate Search Console metrics for the given date range."""
    service = build(
        "searchconsole",
        "v1",
        credentials=credentials,
        cache_discovery=False,
    )

    body = {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "dimensions": [],
        "aggregationType": "auto",
        "rowLimit": 1,
    }

    response = (
        service.searchanalytics()
        .query(siteUrl=site_url, body=body)
        .execute()
    )

    if "rows" in response and response["rows"]:
        row = response["rows"][0]
        data = SearchConsoleData(
            clicks=int(row.get("clicks", 0)),
            impressions=int(row.get("impressions", 0)),
            ctr=float(row.get("ctr", 0.0)),
            position=float(row.get("position", 0.0)),
        )
    else:
        data = SearchConsoleData()

    logger.debug(
        "GSC raw → clicks=%s impressions=%s ctr=%.4f position=%.2f",
        data.clicks,
        data.impressions,
        data.ctr,
        data.position,
    )
    return data
