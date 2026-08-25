from __future__ import annotations

import logging
from datetime import date

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Filter,
    FilterExpression,
    Metric,
    RunReportRequest,
)
from google.oauth2.credentials import Credentials

from config import CHANNELS, CUSTOM_EVENTS
from models import GA4Data
from utils import retry

logger = logging.getLogger(__name__)


@retry(max_attempts=4, base_delay=2.0)
def fetch_ga4_data(
    credentials: Credentials,
    property_id: str,
    start: date,
    end: date,
) -> GA4Data:
    client = BetaAnalyticsDataClient(credentials=credentials)
    date_range = DateRange(
        start_date=start.isoformat(),
        end_date=end.isoformat(),
    )

    result = GA4Data()

    request = RunReportRequest(
        property=property_id,
        metrics=[
            Metric(name="activeUsers"),
            Metric(name="newUsers"),
            Metric(name="eventCount"),
            Metric(name="userEngagementDuration"),
        ],
        date_ranges=[date_range],
    )

    response = client.run_report(request)

    if response.rows:
        mv = response.rows[0].metric_values
        result.users = int(mv[0].value)
        result.new_users = int(mv[1].value)
        result.events = int(mv[2].value)
        result.engagement_time = int(mv[3].value)

    request = RunReportRequest(
        property=property_id,
        dimensions=[
            Dimension(name="sessionDefaultChannelGroup")
        ],
        metrics=[
            Metric(name="engagedSessions")
        ],
        date_ranges=[date_range],
    )

    response = client.run_report(request)

    channel_map = {ch: 0 for ch in CHANNELS}

    for row in response.rows:
        channel = row.dimension_values[0].value

        if channel in channel_map:
            channel_map[channel] += int(
                row.metric_values[0].value
            )

    result.engaged_sessions_by_channel = [
        channel_map[ch] for ch in CHANNELS
    ]

    if CUSTOM_EVENTS:
        request = RunReportRequest(
            property=property_id,
            dimensions=[
                Dimension(name="eventName")
            ],
            metrics=[
                Metric(name="activeUsers")
            ],
            date_ranges=[date_range],
            dimension_filter=FilterExpression(
                filter=Filter(
                    field_name="eventName",
                    in_list_filter=Filter.InListFilter(
                        values=CUSTOM_EVENTS
                    ),
                )
            ),
        )

        response = client.run_report(request)

        for row in response.rows:
            event_name = row.dimension_values[0].value

            if event_name in result.custom_event_users:
                result.custom_event_users[event_name] = int(
                    row.metric_values[0].value
                )

    logger.debug(
        "GA4 raw → users=%s new=%s events=%s eng_time=%s channels=%s custom=%s",
        result.users,
        result.new_users,
        result.events,
        result.engagement_time,
        result.engaged_sessions_by_channel,
        result.custom_event_users,
    )

    return result