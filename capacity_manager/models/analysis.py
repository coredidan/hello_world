"""Data models for analysis results."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, TYPE_CHECKING
from datetime import datetime
from .channel import Channel, ChannelMetrics, UtilizationLevel

if TYPE_CHECKING:
    from ..forecasting.predictor import ForecastResult
    from ..recommendations.engine import Recommendation
    from ..cost_calculator.calculator import CostBreakdown, UpgradeCostEstimate, FinancialSummary


@dataclass
class ChannelAnalysis:
    """Analysis result for a single channel."""

    metrics: ChannelMetrics

    # Trend analysis
    trend_direction: Optional[str] = None  # "increasing", "decreasing", "stable"
    trend_rate_percent: Optional[float] = None  # Rate of change per day

    # Predictions
    days_to_warning: Optional[int] = None
    days_to_critical: Optional[int] = None
    days_to_capacity: Optional[int] = None  # Days to 95% utilization

    # Legacy recommendations (simple strings)
    recommendations: List[str] = field(default_factory=list)

    # Advanced analytics (optional)
    forecast: Optional['ForecastResult'] = None
    structured_recommendations: List['Recommendation'] = field(default_factory=list)

    # Forecast insights
    forecast_confidence: Optional[float] = None  # 0-1
    is_accelerating: bool = False
    seasonal_pattern: Optional[str] = None

    # Financial data (optional)
    cost_breakdown: Optional['CostBreakdown'] = None
    upgrade_cost_estimate: Optional['UpgradeCostEstimate'] = None

    @property
    def is_critical(self) -> bool:
        """Check if channel is in critical state."""
        return self.metrics.utilization_level == UtilizationLevel.CRITICAL

    @property
    def is_warning(self) -> bool:
        """Check if channel is in warning state."""
        return self.metrics.utilization_level == UtilizationLevel.WARNING

    @property
    def needs_attention(self) -> bool:
        """Check if channel needs attention."""
        return self.is_critical or self.is_warning


@dataclass
class SummaryStats:
    """Summary statistics for capacity report."""

    total_channels: int
    critical_channels: int
    warning_channels: int
    normal_channels: int

    # By channel type
    external_channels: int = 0
    transport_channels: int = 0
    inter_site_channels: int = 0

    # Avg utilization
    avg_utilization_percent: float = 0.0
    max_utilization_percent: float = 0.0

    @property
    def critical_percent(self) -> float:
        """Percentage of critical channels."""
        if self.total_channels == 0:
            return 0.0
        return (self.critical_channels / self.total_channels) * 100

    @property
    def warning_percent(self) -> float:
        """Percentage of warning channels."""
        if self.total_channels == 0:
            return 0.0
        return (self.warning_channels / self.total_channels) * 100


@dataclass
class CapacityReport:
    """Complete capacity management report."""

    report_date: datetime
    period_start: datetime
    period_end: datetime

    # Analysis results
    channel_analyses: List[ChannelAnalysis]

    # Summary
    summary: SummaryStats

    # Financial summary (optional)
    financial_summary: Optional['FinancialSummary'] = None

    # Metadata
    generated_by: str = "Capacity Manager"
    version: str = "0.3.0"

    def get_critical_channels(self) -> List[ChannelAnalysis]:
        """Get list of critical channels."""
        return [a for a in self.channel_analyses if a.is_critical]

    def get_warning_channels(self) -> List[ChannelAnalysis]:
        """Get list of warning channels."""
        return [a for a in self.channel_analyses if a.is_warning]

    def get_channels_by_type(self, channel_type) -> List[ChannelAnalysis]:
        """Get channels filtered by type."""
        return [
            a for a in self.channel_analyses
            if a.metrics.channel.channel_type == channel_type
        ]

    def get_top_utilized(self, limit: int = 10) -> List[ChannelAnalysis]:
        """Get top N most utilized channels."""
        sorted_channels = sorted(
            self.channel_analyses,
            key=lambda a: a.metrics.max_utilization_percent,
            reverse=True
        )
        return sorted_channels[:limit]
