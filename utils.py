"""
Shared helpers: dates, retry decorator, notifications.
"""

from __future__ import annotations

import logging
import smtplib
import time
from calendar import month_name
from datetime import date, datetime, timedelta
from email.mime.text import MIMEText
from functools import wraps
from typing import Any, Callable, Optional, Tuple, TypeVar

import requests

from config import (
    NOTIFY_EMAIL_TO,
    SLACK_WEBHOOK_URL,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USER,
)

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------
def previous_month_range(today: Optional[date] = None) -> Tuple[date, date]:
    """Return (first_day, last_day) of the previous calendar month."""
    today = today or date.today()
    first_of_this_month = today.replace(day=1)
    last_of_prev = first_of_this_month - timedelta(days=1)
    first_of_prev = last_of_prev.replace(day=1)
    return first_of_prev, last_of_prev


def month_label(d: date) -> str:
    """e.g. 'May 2024'"""
    return f"{month_name[d.month]} {d.year}"


def parse_month(s: str) -> date:
    """
    Parse 'YYYY-MM' or 'YYYY-M' into the first day of that month.
    Raises ValueError on invalid input.
    """
    try:
        return datetime.strptime(s, "%Y-%m").date().replace(day=1)
    except ValueError:
        return datetime.strptime(s, "%Y-%m-%d").date().replace(day=1)


# ---------------------------------------------------------------------------
# Retry with exponential backoff
# ---------------------------------------------------------------------------
def retry(
    max_attempts: int = 4,
    base_delay: float = 1.5,
    exceptions: Tuple[type, ...] = (Exception,),
) -> Callable[[F], F]:
    """
    Simple exponential-backoff retry decorator.
    Retries on the given exceptions (default: any Exception).
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Optional[BaseException] = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        break
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.warning(
                        "%s failed (attempt %d/%d): %s – retrying in %.1fs",
                        func.__name__,
                        attempt,
                        max_attempts,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
            raise last_exc  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator


# ---------------------------------------------------------------------------
# Notifications (optional)
# ---------------------------------------------------------------------------
def notify_failure(subject: str, body: str) -> None:
    """Send failure notification via Slack webhook and/or email if configured."""
    if SLACK_WEBHOOK_URL:
        try:
            requests.post(
                SLACK_WEBHOOK_URL,
                json={"text": f"*{subject}*\n```{body}```"},
                timeout=10,
            )
            logger.info("Slack notification sent")
        except Exception:
            logger.exception("Failed to send Slack notification")

    if SMTP_HOST and NOTIFY_EMAIL_TO and SMTP_USER:
        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = SMTP_USER
            msg["To"] = NOTIFY_EMAIL_TO

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
            logger.info("Email notification sent to %s", NOTIFY_EMAIL_TO)
        except Exception:
            logger.exception("Failed to send email notification")
