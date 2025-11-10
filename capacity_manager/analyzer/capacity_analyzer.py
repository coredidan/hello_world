"""Capacity analyzer module - independent analysis logic."""

from typing import List, Optional
from datetime import datetime, timedelta
import logging

from ..models.channel import ChannelMetrics, UtilizationLevel
from ..models.analysis import ChannelAnalysis, CapacityReport, SummaryStats

logger = logging.getLogger(__name__)


class CapacityAnalyzer:
    """
    Analyzes channel metrics for capacity management.

    This module is independent and only works with data models.
    It doesn't depend on Grafana or any external services.
    """

    def __init__(
        self,
        warning_threshold: float = 70.0,
        critical_threshold: float = 85.0
    ):
        """
        Initialize capacity analyzer.

        Args:
            warning_threshold: Warning threshold percentage
            critical_threshold: Critical threshold percentage
        """
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

    def analyze_channel(
        self,
        metrics: ChannelMetrics,
        historical_metrics: Optional[List[ChannelMetrics]] = None
    ) -> ChannelAnalysis:
        """
        Analyze a single channel.

        Args:
            metrics: Current channel metrics
            historical_metrics: Historical metrics for trend analysis

        Returns:
            ChannelAnalysis result
        """
        analysis = ChannelAnalysis(metrics=metrics)

        # Add recommendations based on utilization
        analysis.recommendations = self._generate_recommendations(metrics)

        # Perform trend analysis if historical data available
        if historical_metrics and len(historical_metrics) > 1:
            trend = self._analyze_trend(historical_metrics)
            analysis.trend_direction = trend['direction']
            analysis.trend_rate_percent = trend['rate']

            # Predict days to thresholds
            if trend['direction'] == 'increasing' and trend['rate'] > 0:
                analysis.days_to_warning = self._predict_days_to_threshold(
                    current_util=metrics.max_utilization_percent,
                    trend_rate=trend['rate'],
                    threshold=self.warning_threshold
                )
                analysis.days_to_critical = self._predict_days_to_threshold(
                    current_util=metrics.max_utilization_percent,
                    trend_rate=trend['rate'],
                    threshold=self.critical_threshold
                )

        return analysis

    def analyze_multiple_channels(
        self,
        metrics_list: List[ChannelMetrics],
        period_start: datetime,
        period_end: datetime
    ) -> CapacityReport:
        """
        Analyze multiple channels and generate report.

        Args:
            metrics_list: List of channel metrics
            period_start: Analysis period start
            period_end: Analysis period end

        Returns:
            Complete capacity report
        """
        # Analyze each channel
        analyses = [self.analyze_channel(m) for m in metrics_list]

        # Calculate summary statistics
        summary = self._calculate_summary(analyses)

        # Create report
        report = CapacityReport(
            report_date=datetime.now(),
            period_start=period_start,
            period_end=period_end,
            channel_analyses=analyses,
            summary=summary
        )

        return report

    def _generate_recommendations(self, metrics: ChannelMetrics) -> List[str]:
        """Generate recommendations based on metrics."""
        recommendations = []
        util = metrics.max_utilization_percent

        if util >= self.critical_threshold:
            recommendations.append(
                f"КРИТИЧНО: Загрузка канала {util:.1f}% превышает порог {self.critical_threshold}%. "
                "Требуется немедленное увеличение пропускной способности."
            )
            recommendations.append(
                "Рекомендуется: Планирование расширения канала в течение 1-2 недель."
            )
        elif util >= self.warning_threshold:
            recommendations.append(
                f"ВНИМАНИЕ: Загрузка канала {util:.1f}% близка к критической. "
                f"Рекомендуется мониторинг и планирование расширения."
            )
            recommendations.append(
                "Рекомендуется: Планирование расширения канала в течение 1-2 месяцев."
            )

        # Check for errors
        if metrics.errors_in > 0 or metrics.errors_out > 0:
            total_errors = metrics.errors_in + metrics.errors_out
            recommendations.append(
                f"Обнаружены ошибки на интерфейсе (всего: {total_errors}). "
                "Рекомендуется проверка качества линии."
            )

        # Check for discards
        if metrics.discards_in > 0 or metrics.discards_out > 0:
            recommendations.append(
                "Обнаружены отбросы пакетов. Возможна перегрузка или проблемы с QoS."
            )

        # Check utilization imbalance
        util_diff = abs(metrics.utilization_in_percent - metrics.utilization_out_percent)
        if util_diff > 30:
            recommendations.append(
                f"Значительная разница между входящим ({metrics.utilization_in_percent:.1f}%) "
                f"и исходящим ({metrics.utilization_out_percent:.1f}%) трафиком. "
                "Рекомендуется анализ структуры трафика."
            )

        if not recommendations:
            recommendations.append("Канал работает в штатном режиме.")

        return recommendations

    def _analyze_trend(self, historical_metrics: List[ChannelMetrics]) -> dict:
        """
        Analyze trend from historical metrics.

        Returns:
            Dictionary with 'direction' and 'rate' (percent per day)
        """
        if len(historical_metrics) < 2:
            return {'direction': 'stable', 'rate': 0}

        # Sort by timestamp
        sorted_metrics = sorted(historical_metrics, key=lambda m: m.timestamp)

        # Get utilizations over time
        utils = [m.max_utilization_percent for m in sorted_metrics]

        # Simple linear regression to determine trend
        n = len(utils)
        if n < 2:
            return {'direction': 'stable', 'rate': 0}

        # Calculate average rate of change
        changes = []
        for i in range(1, n):
            time_diff_days = (sorted_metrics[i].timestamp - sorted_metrics[i-1].timestamp).total_seconds() / 86400
            if time_diff_days > 0:
                util_change = utils[i] - utils[i-1]
                rate = util_change / time_diff_days
                changes.append(rate)

        if not changes:
            return {'direction': 'stable', 'rate': 0}

        avg_rate = sum(changes) / len(changes)

        # Determine direction
        if abs(avg_rate) < 0.5:  # Less than 0.5% per day
            direction = 'stable'
        elif avg_rate > 0:
            direction = 'increasing'
        else:
            direction = 'decreasing'

        return {'direction': direction, 'rate': abs(avg_rate)}

    def _predict_days_to_threshold(
        self,
        current_util: float,
        trend_rate: float,
        threshold: float
    ) -> Optional[int]:
        """
        Predict days until threshold is reached.

        Args:
            current_util: Current utilization percent
            trend_rate: Rate of change (percent per day)
            threshold: Threshold to predict

        Returns:
            Number of days or None if threshold won't be reached
        """
        if current_util >= threshold:
            return 0

        if trend_rate <= 0:
            return None

        days = (threshold - current_util) / trend_rate
        return int(days) if days > 0 else None

    def _calculate_summary(self, analyses: List[ChannelAnalysis]) -> SummaryStats:
        """Calculate summary statistics from analyses."""
        from ..models.channel import ChannelType

        total = len(analyses)
        critical = sum(1 for a in analyses if a.is_critical)
        warning = sum(1 for a in analyses if a.is_warning)
        normal = total - critical - warning

        # Count by type
        external = sum(
            1 for a in analyses
            if a.metrics.channel.channel_type == ChannelType.EXTERNAL
        )
        transport = sum(
            1 for a in analyses
            if a.metrics.channel.channel_type == ChannelType.TRANSPORT
        )
        inter_site = sum(
            1 for a in analyses
            if a.metrics.channel.channel_type == ChannelType.INTER_SITE
        )

        # Calculate average and max utilization
        if analyses:
            avg_util = sum(a.metrics.max_utilization_percent for a in analyses) / total
            max_util = max(a.metrics.max_utilization_percent for a in analyses)
        else:
            avg_util = 0
            max_util = 0

        return SummaryStats(
            total_channels=total,
            critical_channels=critical,
            warning_channels=warning,
            normal_channels=normal,
            external_channels=external,
            transport_channels=transport,
            inter_site_channels=inter_site,
            avg_utilization_percent=avg_util,
            max_utilization_percent=max_util
        )
