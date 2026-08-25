from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from config import CHANNELS, CUSTOM_EVENTS


@dataclass
class GA4Data:
    users: int = 0
    new_users: int = 0
    events: int = 0
    engagement_time: int = 0  # total seconds of user engagement
    engaged_sessions_by_channel: List[int] = field(default_factory=lambda: [0] * len(CHANNELS))
    custom_event_users: Dict[str, int] = field(
        default_factory=lambda: {e: 0 for e in CUSTOM_EVENTS}
    )

    @property
    def avg_engagement_mmss(self) -> str:
        if self.users == 0:
            return "0:00"
        avg_seconds = self.engagement_time / self.users
        minutes = int(avg_seconds // 60)
        seconds = int(avg_seconds % 60)
        return f"{minutes}:{seconds:02d}"


@dataclass
class SearchConsoleData:
    clicks: int = 0
    impressions: int = 0
    ctr: float = 0.0
    position: float = 0.0
