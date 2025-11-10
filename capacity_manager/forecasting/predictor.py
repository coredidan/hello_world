"""Advanced forecasting module for capacity prediction."""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import statistics
import math


@dataclass
class ForecastPoint:
    """A single forecast point."""
    timestamp: datetime
    predicted_utilization: float
    confidence_lower: float  # Lower bound of confidence interval
    confidence_upper: float  # Upper bound of confidence interval


@dataclass
class ForecastResult:
    """Result of capacity forecasting."""
    channel_name: str
    current_utilization: float
    forecast_points: List[ForecastPoint]

    # Predictions
    days_to_warning: Optional[int] = None
    days_to_critical: Optional[int] = None
    days_to_capacity: Optional[int] = None

    # Forecast quality
    trend_strength: float = 0.0  # 0-1, how strong is the trend
    forecast_confidence: float = 0.0  # 0-1, confidence in forecast

    # Insights
    is_accelerating: bool = False  # Growth rate is increasing
    seasonal_pattern: Optional[str] = None  # weekly, monthly, etc.


class CapacityPredictor:
    """
    Advanced capacity forecasting engine.

    Independent module that uses various algorithms to predict
    future capacity utilization.
    """

    def __init__(
        self,
        warning_threshold: float = 70.0,
        critical_threshold: float = 85.0,
        capacity_threshold: float = 95.0
    ):
        """
        Initialize predictor.

        Args:
            warning_threshold: Warning utilization threshold
            critical_threshold: Critical utilization threshold
            capacity_threshold: Maximum safe utilization
        """
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.capacity_threshold = capacity_threshold

    def forecast_linear(
        self,
        historical_data: List[Tuple[datetime, float]],
        forecast_days: int = 90
    ) -> ForecastResult:
        """
        Linear regression forecast.

        Args:
            historical_data: List of (timestamp, utilization) tuples
            forecast_days: Number of days to forecast

        Returns:
            ForecastResult with predictions
        """
        if len(historical_data) < 2:
            return self._empty_forecast("N/A", 0.0)

        # Sort by timestamp
        sorted_data = sorted(historical_data, key=lambda x: x[0])

        # Convert to numeric values (days from start)
        start_time = sorted_data[0][0]
        x_values = [(dt - start_time).total_seconds() / 86400 for dt, _ in sorted_data]
        y_values = [util for _, util in sorted_data]

        # Calculate linear regression: y = mx + b
        m, b = self._linear_regression(x_values, y_values)

        # Calculate forecast quality metrics
        trend_strength = self._calculate_trend_strength(x_values, y_values, m, b)
        r_squared = self._calculate_r_squared(x_values, y_values, m, b)

        # Generate forecast points
        forecast_points = []
        last_x = x_values[-1]
        current_util = y_values[-1]

        for day in range(1, forecast_days + 1):
            future_x = last_x + day
            predicted = m * future_x + b

            # Calculate confidence interval (wider for further predictions)
            std_error = self._calculate_std_error(x_values, y_values, m, b)
            confidence_width = std_error * math.sqrt(1 + day/len(x_values))

            forecast_point = ForecastPoint(
                timestamp=sorted_data[-1][0] + timedelta(days=day),
                predicted_utilization=max(0, min(100, predicted)),
                confidence_lower=max(0, predicted - 2*confidence_width),
                confidence_upper=min(100, predicted + 2*confidence_width)
            )
            forecast_points.append(forecast_point)

        # Find when thresholds will be crossed
        days_to_warning = self._find_threshold_crossing(
            current_util, m, self.warning_threshold
        )
        days_to_critical = self._find_threshold_crossing(
            current_util, m, self.critical_threshold
        )
        days_to_capacity = self._find_threshold_crossing(
            current_util, m, self.capacity_threshold
        )

        # Check if growth is accelerating
        is_accelerating = self._detect_acceleration(y_values)

        return ForecastResult(
            channel_name="",
            current_utilization=current_util,
            forecast_points=forecast_points,
            days_to_warning=days_to_warning,
            days_to_critical=days_to_critical,
            days_to_capacity=days_to_capacity,
            trend_strength=trend_strength,
            forecast_confidence=r_squared,
            is_accelerating=is_accelerating
        )

    def forecast_exponential_smoothing(
        self,
        historical_data: List[Tuple[datetime, float]],
        forecast_days: int = 90,
        alpha: float = 0.3
    ) -> ForecastResult:
        """
        Exponential smoothing forecast.

        Better for data with trends but no strong seasonality.

        Args:
            historical_data: List of (timestamp, utilization) tuples
            forecast_days: Number of days to forecast
            alpha: Smoothing parameter (0-1)

        Returns:
            ForecastResult with predictions
        """
        if len(historical_data) < 2:
            return self._empty_forecast("N/A", 0.0)

        sorted_data = sorted(historical_data, key=lambda x: x[0])
        values = [util for _, util in sorted_data]

        # Double exponential smoothing (Holt's method)
        # Level and trend components
        level = values[0]
        trend = values[1] - values[0] if len(values) > 1 else 0
        beta = 0.1  # Trend smoothing parameter

        # Smooth the historical data
        for value in values[1:]:
            prev_level = level
            level = alpha * value + (1 - alpha) * (level + trend)
            trend = beta * (level - prev_level) + (1 - beta) * trend

        # Generate forecasts
        forecast_points = []
        current_util = values[-1]

        for day in range(1, forecast_days + 1):
            predicted = level + day * trend

            # Confidence interval based on historical variance
            variance = statistics.variance(values) if len(values) > 2 else 0
            confidence_width = math.sqrt(variance) * math.sqrt(day)

            forecast_point = ForecastPoint(
                timestamp=sorted_data[-1][0] + timedelta(days=day),
                predicted_utilization=max(0, min(100, predicted)),
                confidence_lower=max(0, predicted - 2*confidence_width),
                confidence_upper=min(100, predicted + 2*confidence_width)
            )
            forecast_points.append(forecast_point)

        # Calculate days to thresholds
        days_to_warning = self._find_threshold_crossing(
            current_util, trend, self.warning_threshold
        ) if trend > 0 else None

        days_to_critical = self._find_threshold_crossing(
            current_util, trend, self.critical_threshold
        ) if trend > 0 else None

        days_to_capacity = self._find_threshold_crossing(
            current_util, trend, self.capacity_threshold
        ) if trend > 0 else None

        # Confidence based on data stability
        confidence = 1.0 / (1.0 + statistics.stdev(values) / 10.0) if len(values) > 2 else 0.5

        return ForecastResult(
            channel_name="",
            current_utilization=current_util,
            forecast_points=forecast_points,
            days_to_warning=days_to_warning,
            days_to_critical=days_to_critical,
            days_to_capacity=days_to_capacity,
            trend_strength=min(abs(trend) / 10.0, 1.0),
            forecast_confidence=confidence,
            is_accelerating=self._detect_acceleration(values)
        )

    def forecast_with_seasonality(
        self,
        historical_data: List[Tuple[datetime, float]],
        forecast_days: int = 90,
        period_days: int = 7
    ) -> ForecastResult:
        """
        Forecast with seasonal decomposition.

        Args:
            historical_data: List of (timestamp, utilization) tuples
            forecast_days: Number of days to forecast
            period_days: Seasonal period (7 for weekly, 30 for monthly)

        Returns:
            ForecastResult with seasonal predictions
        """
        if len(historical_data) < period_days * 2:
            # Not enough data for seasonal analysis
            return self.forecast_linear(historical_data, forecast_days)

        sorted_data = sorted(historical_data, key=lambda x: x[0])

        # Decompose into trend and seasonal components
        trend, seasonal = self._seasonal_decomposition(
            [util for _, util in sorted_data],
            period_days
        )

        # Forecast trend
        trend_forecast = self.forecast_linear(
            [(dt, t) for (dt, _), t in zip(sorted_data, trend)],
            forecast_days
        )

        # Apply seasonal pattern to forecast
        forecast_points = []
        for i, point in enumerate(trend_forecast.forecast_points):
            seasonal_index = i % len(seasonal)
            seasonal_adjustment = seasonal[seasonal_index]

            adjusted_pred = point.predicted_utilization + seasonal_adjustment

            forecast_point = ForecastPoint(
                timestamp=point.timestamp,
                predicted_utilization=max(0, min(100, adjusted_pred)),
                confidence_lower=max(0, point.confidence_lower + seasonal_adjustment),
                confidence_upper=min(100, point.confidence_upper + seasonal_adjustment)
            )
            forecast_points.append(forecast_point)

        # Detect seasonal pattern strength
        seasonal_strength = statistics.stdev(seasonal) if len(seasonal) > 1 else 0
        seasonal_pattern = None
        if seasonal_strength > 5:  # More than 5% variation
            if period_days == 7:
                seasonal_pattern = "weekly"
            elif period_days == 30:
                seasonal_pattern = "monthly"
            else:
                seasonal_pattern = f"{period_days}-day cycle"

        result = trend_forecast
        result.forecast_points = forecast_points
        result.seasonal_pattern = seasonal_pattern

        return result

    def _linear_regression(
        self,
        x: List[float],
        y: List[float]
    ) -> Tuple[float, float]:
        """Calculate linear regression coefficients (slope, intercept)."""
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)

        # Slope (m)
        m = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)

        # Intercept (b)
        b = (sum_y - m * sum_x) / n

        return m, b

    def _calculate_r_squared(
        self,
        x: List[float],
        y: List[float],
        m: float,
        b: float
    ) -> float:
        """Calculate R-squared (coefficient of determination)."""
        y_mean = statistics.mean(y)
        ss_tot = sum((yi - y_mean) ** 2 for yi in y)
        ss_res = sum((yi - (m * xi + b)) ** 2 for xi, yi in zip(x, y))

        if ss_tot == 0:
            return 0.0

        return 1 - (ss_res / ss_tot)

    def _calculate_trend_strength(
        self,
        x: List[float],
        y: List[float],
        m: float,
        b: float
    ) -> float:
        """Calculate trend strength (0-1)."""
        r_squared = self._calculate_r_squared(x, y, m, b)
        return r_squared

    def _calculate_std_error(
        self,
        x: List[float],
        y: List[float],
        m: float,
        b: float
    ) -> float:
        """Calculate standard error of regression."""
        residuals = [yi - (m * xi + b) for xi, yi in zip(x, y)]
        mse = sum(r ** 2 for r in residuals) / len(residuals)
        return math.sqrt(mse)

    def _find_threshold_crossing(
        self,
        current_value: float,
        rate: float,
        threshold: float
    ) -> Optional[int]:
        """Find days until threshold is crossed."""
        if current_value >= threshold:
            return 0

        if rate <= 0:
            return None

        days = (threshold - current_value) / rate
        return int(days) if days > 0 else None

    def _detect_acceleration(self, values: List[float]) -> bool:
        """Detect if growth rate is accelerating."""
        if len(values) < 6:
            return False

        # Compare growth rate in first half vs second half
        mid = len(values) // 2
        first_half = values[:mid]
        second_half = values[mid:]

        first_rate = (first_half[-1] - first_half[0]) / len(first_half)
        second_rate = (second_half[-1] - second_half[0]) / len(second_half)

        # Accelerating if second half grows faster
        return second_rate > first_rate * 1.2

    def _seasonal_decomposition(
        self,
        values: List[float],
        period: int
    ) -> Tuple[List[float], List[float]]:
        """
        Simple seasonal decomposition.

        Returns:
            Tuple of (trend, seasonal_component)
        """
        # Calculate moving average for trend
        trend = []
        half_period = period // 2

        for i in range(len(values)):
            start = max(0, i - half_period)
            end = min(len(values), i + half_period + 1)
            trend.append(statistics.mean(values[start:end]))

        # Calculate seasonal component
        detrended = [v - t for v, t in zip(values, trend)]

        # Average values for each position in the period
        seasonal = []
        for i in range(period):
            positions = [detrended[j] for j in range(i, len(detrended), period)]
            seasonal.append(statistics.mean(positions) if positions else 0)

        # Center seasonal component (mean should be 0)
        seasonal_mean = statistics.mean(seasonal)
        seasonal = [s - seasonal_mean for s in seasonal]

        return trend, seasonal

    def _empty_forecast(self, name: str, current: float) -> ForecastResult:
        """Create empty forecast result."""
        return ForecastResult(
            channel_name=name,
            current_utilization=current,
            forecast_points=[],
            forecast_confidence=0.0,
            trend_strength=0.0
        )
