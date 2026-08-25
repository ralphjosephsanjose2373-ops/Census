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
def previous_month_range(today: Optional[date] = None) -> Tuple[date, date]:
    today = today or date.today()
    first_of_this_month = today.replace(day=1)
    last_of_prev = first_of_this_month - timedelta(days=1)
    first_of_prev = last_of_prev.replace(day=1)
    return first_of_prev, last_of_prev


def month_label(d: date) -> str:
    return f"{month_name[d.month]} {d.year}"


def parse_month(s: str) -> date:
    try:
        return datetime.strptime(s, "%Y-%m").date().replace(day=1)
    except ValueError:
        return datetime.strptime(s, "%Y-%m-%d").date().replace(day=1)

def retry(
    max_attempts: int = 4,
    base_delay: float = 1.5,
    exceptions: Tuple[type, ...] = (Exception,),
) -> Callable[[F], F]:
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

def notify_failure(subject: str, body: str) -> None:
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
