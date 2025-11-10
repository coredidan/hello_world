"""Data models for channels and interfaces."""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ChannelType(Enum):
    """Type of channel."""
    EXTERNAL = "external"  # Внешние каналы
    TRANSPORT = "transport"  # Транспортные каналы между оборудованием
    INTER_SITE = "inter_site"  # Межплощадочные каналы


class UtilizationLevel(Enum):
    """Utilization level thresholds."""
    NORMAL = "normal"  # < 70%
    WARNING = "warning"  # 70-85%
    CRITICAL = "critical"  # > 85%


@dataclass
class Channel:
    """Represents a network channel/interface."""

    name: str
    channel_type: ChannelType
    capacity_mbps: float
    description: Optional[str] = None

    # Location info
    site_a: Optional[str] = None
    site_b: Optional[str] = None
    device_a: Optional[str] = None
    device_b: Optional[str] = None

    # Additional metadata
    tags: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        """Validate channel data."""
        if self.capacity_mbps <= 0:
            raise ValueError("Capacity must be positive")


@dataclass
class ChannelMetrics:
    """Metrics for a channel."""

    channel: Channel
    timestamp: datetime

    # Traffic metrics (in Mbps)
    traffic_in_mbps: float
    traffic_out_mbps: float

    # Peak values
    peak_in_mbps: Optional[float] = None
    peak_out_mbps: Optional[float] = None

    # Average values
    avg_in_mbps: Optional[float] = None
    avg_out_mbps: Optional[float] = None

    # Errors and discards
    errors_in: int = 0
    errors_out: int = 0
    discards_in: int = 0
    discards_out: int = 0

    @property
    def utilization_in_percent(self) -> float:
        """Calculate input utilization percentage."""
        if self.channel.capacity_mbps == 0:
            return 0.0
        return (self.traffic_in_mbps / self.channel.capacity_mbps) * 100

    @property
    def utilization_out_percent(self) -> float:
        """Calculate output utilization percentage."""
        if self.channel.capacity_mbps == 0:
            return 0.0
        return (self.traffic_out_mbps / self.channel.capacity_mbps) * 100

    @property
    def max_utilization_percent(self) -> float:
        """Get maximum utilization (in or out)."""
        return max(self.utilization_in_percent, self.utilization_out_percent)

    @property
    def utilization_level(self) -> UtilizationLevel:
        """Determine utilization level."""
        max_util = self.max_utilization_percent
        if max_util >= 85:
            return UtilizationLevel.CRITICAL
        elif max_util >= 70:
            return UtilizationLevel.WARNING
        else:
            return UtilizationLevel.NORMAL
