#!/usr/bin/env python3
"""
_░▒███████
░██▓▒░░▒▓██
██▓▒░__░▒▓██___██████
██▓▒░____░▓███▓__░▒▓██
██▓▒░___░▓██▓_____░▒▓██
██▓▒░_______________░▒▓██
██▓▒░______________░▒▓██
 ██▓▒░____________░▒▓██
  ██▓▒░__________░▒▓██
   ██▓▒░________░▒▓██
    ██▓▒░_____░▒▓██
      ██▓▒░__░▒▓██
        █▓▒░░▒▓██
         ░▒▓██
       ░▒▓██
     ░▒▓██
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from typing import Any, List

from auth import load_credentials
from config import (
    GA4_PROPERTY_ID,
    HEADERS,
    LOG_FILE,
    SHEET_ID,
    SHEET_NAME,
    SITE_URL,
    validate_config,
)
from ga4 import fetch_ga4_data
from models import GA4Data, SearchConsoleData
from search_console import fetch_search_console_data
from sheets import (
    ensure_headers,
    get_existing_values,
    month_already_exists,
    write_and_format_row,
)
from utils import month_label, notify_failure, parse_month, previous_month_range

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("main")


def build_row(label: str, ga4: GA4Data, gsc: SearchConsoleData) -> List[Any]:
    return [
        label,
        ga4.users,
        ga4.new_users,
        ga4.events,
        ga4.avg_engagement_mmss,
        *ga4.engaged_sessions_by_channel,
        ga4.custom_event_users.get("user_spent_2_minutes", 0),
        ga4.custom_event_users.get("bli_medlem_klick", 0),
        gsc.clicks,
        gsc.impressions,
        gsc.ctr,
        round(gsc.position, 1),
    ]


def run(target_month: date | None = None, dry_run: bool = False) -> None:
    validate_config()
    credentials = load_credentials()

    if target_month is None:
        start, end = previous_month_range()
    else:
        # Use the whole calendar month
        from datetime import timedelta
        start = target_month.replace(day=1)
        if start.month == 12:
            next_month = start.replace(year=start.year + 1, month=1, day=1)
        else:
            next_month = start.replace(month=start.month + 1, day=1)
        end = next_month - timedelta(days=1)

    label = month_label(start)
    logger.info("Processing period: %s  (%s → %s)", label, start, end)

    ga4 = GA4Data()
    gsc = SearchConsoleData()

    try:
        ga4 = fetch_ga4_data(credentials, GA4_PROPERTY_ID, start, end)
        logger.info(
            "GA4 OK | users=%s  new=%s  events=%s  channels=%s  custom=%s",
            ga4.users,
            ga4.new_users,
            ga4.events,
            ga4.engaged_sessions_by_channel,
            ga4.custom_event_users,
        )
    except Exception:
        logger.exception("Failed to fetch GA4 data")
        notify_failure(
            "GA4 Sheets Reporter – GA4 fetch failed",
            f"Could not fetch GA4 data for {label}",
        )

    try:
        gsc = fetch_search_console_data(credentials, SITE_URL, start, end)
        logger.info(
            "GSC OK | clicks=%s  impressions=%s  ctr=%.4f  position=%.1f",
            gsc.clicks,
            gsc.impressions,
            gsc.ctr,
            gsc.position,
        )
    except Exception:
        logger.exception("Failed to fetch Search Console data")
        notify_failure(
            "GA4 Sheets Reporter – GSC fetch failed",
            f"Could not fetch Search Console data for {label}",
        )

    row = build_row(label, ga4, gsc)

    if dry_run:
        logger.info("DRY-RUN – would write the following row:")
        for header, value in zip(HEADERS, row):
            logger.info("  %-35s : %s", header, value)
        return

    try:
        existing = get_existing_values(credentials, SHEET_ID, SHEET_NAME)

        if month_already_exists(existing, label):
            logger.warning(
                "Month '%s' already exists in the sheet – skipping write. "
                "Delete the row manually if you want to re-run.",
                label,
            )
            return

        ensure_headers(credentials, SHEET_ID, SHEET_NAME, existing)

        if not existing:
            existing = [HEADERS] 

        write_and_format_row(
            credentials,
            SHEET_ID,
            SHEET_NAME,
            row,
            existing_row_count=len(existing),
        )
        logger.info("Successfully wrote data for %s", label)

    except Exception:
        logger.exception("Failed to write to Google Sheets")
        notify_failure(
            "GA4 Sheets Reporter – Sheets write failed",
            f"Could not write data for {label} to the spreadsheet.",
        )
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch previous-month (or specified month) GA4 + GSC data and write to Google Sheets."
    )
    parser.add_argument(
        "--month",
        metavar="YYYY-MM",
        help="Process a specific month instead of the previous calendar month (e.g. 2025-03)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch data and print the row that would be written, but do not touch the sheet.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    target: date | None = None

    if args.month:
        try:
            target = parse_month(args.month)
        except ValueError:
            logger.error("Invalid --month format. Use YYYY-MM (e.g. 2025-03)")
            sys.exit(1)

    run(target_month=target, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
