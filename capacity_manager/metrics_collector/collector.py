"""Metrics collector module - independent from other business logic."""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import logging
import statistics

from ..grafana_api.client import GrafanaClient, GrafanaAPIError
from ..models.channel import Channel, ChannelMetrics, ChannelType

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collects metrics from Grafana for channels.

    This module is independent and can work with any Grafana instance.
    It converts raw Grafana data into ChannelMetrics objects.
    """

    def __init__(
        self,
        grafana_client: GrafanaClient,
        datasource_uid: Optional[str] = None
    ):
        """
        Initialize metrics collector.

        Args:
            grafana_client: Grafana API client instance
            datasource_uid: Default datasource UID (auto-detect if None)
        """
        self.client = grafana_client
        self._datasource_uid = datasource_uid

    @property
    def datasource_uid(self) -> Optional[str]:
        """Get datasource UID (auto-detect if not set)."""
        if self._datasource_uid is None:
            datasources = self.client.get_datasources()
            if datasources:
                # Use first Prometheus datasource
                for ds in datasources:
                    if ds.get('type') == 'prometheus':
                        self._datasource_uid = ds.get('uid')
                        logger.info(f"Auto-detected datasource: {self._datasource_uid}")
                        break
                # Fallback to first datasource
                if self._datasource_uid is None:
                    self._datasource_uid = datasources[0].get('uid')
                    logger.warning(f"Using first available datasource: {self._datasource_uid}")
        return self._datasource_uid

    def collect_channel_metrics(
        self,
        channel: Channel,
        start_time: datetime,
        end_time: datetime,
        interface_filter: Optional[str] = None
    ) -> Optional[ChannelMetrics]:
        """
        Collect metrics for a specific channel.

        Args:
            channel: Channel definition
            start_time: Start of time range
            end_time: End of time range
            interface_filter: Interface name/pattern for filtering

        Returns:
            ChannelMetrics object or None if collection fails
        """
        try:
            # Build interface filter for PromQL
            if_filter = interface_filter or channel.name

            # Query traffic metrics
            traffic_in = self._query_traffic_metric(
                interface=if_filter,
                direction='in',
                start=start_time,
                end=end_time
            )

            traffic_out = self._query_traffic_metric(
                interface=if_filter,
                direction='out',
                start=start_time,
                end=end_time
            )

            # Query error metrics
            errors_in = self._query_error_metric(
                interface=if_filter,
                direction='in',
                start=start_time,
                end=end_time
            )

            errors_out = self._query_error_metric(
                interface=if_filter,
                direction='out',
                start=start_time,
                end=end_time
            )

            # Process results
            traffic_in_stats = self._process_timeseries(traffic_in)
            traffic_out_stats = self._process_timeseries(traffic_out)

            # Convert bytes/s to Mbps (multiply by 8 / 1_000_000)
            current_in_mbps = (traffic_in_stats.get('current', 0) * 8) / 1_000_000
            current_out_mbps = (traffic_out_stats.get('current', 0) * 8) / 1_000_000
            peak_in_mbps = (traffic_in_stats.get('max', 0) * 8) / 1_000_000
            peak_out_mbps = (traffic_out_stats.get('max', 0) * 8) / 1_000_000
            avg_in_mbps = (traffic_in_stats.get('avg', 0) * 8) / 1_000_000
            avg_out_mbps = (traffic_out_stats.get('avg', 0) * 8) / 1_000_000

            return ChannelMetrics(
                channel=channel,
                timestamp=datetime.now(),
                traffic_in_mbps=current_in_mbps,
                traffic_out_mbps=current_out_mbps,
                peak_in_mbps=peak_in_mbps,
                peak_out_mbps=peak_out_mbps,
                avg_in_mbps=avg_in_mbps,
                avg_out_mbps=avg_out_mbps,
                errors_in=int(errors_in.get('total', 0)),
                errors_out=int(errors_out.get('total', 0))
            )

        except Exception as e:
            logger.error(f"Failed to collect metrics for channel {channel.name}: {e}")
            return None

    def collect_multiple_channels(
        self,
        channels: List[Channel],
        start_time: datetime,
        end_time: datetime
    ) -> List[ChannelMetrics]:
        """
        Collect metrics for multiple channels.

        Args:
            channels: List of channels
            start_time: Start of time range
            end_time: End of time range

        Returns:
            List of ChannelMetrics (excludes failed collections)
        """
        results = []
        for channel in channels:
            metrics = self.collect_channel_metrics(channel, start_time, end_time)
            if metrics:
                results.append(metrics)
        return results

    def _query_traffic_metric(
        self,
        interface: str,
        direction: str,
        start: datetime,
        end: datetime
    ) -> Dict[str, Any]:
        """Query traffic metric (in/out octets)."""
        metric_name = 'ifInOctets' if direction == 'in' else 'ifOutOctets'

        # PromQL query - adjust based on your actual metric names
        query = f'rate({metric_name}{{ifDescr=~".*{interface}.*"}}[5m])'

        result = self.client.query_prometheus(
            datasource_uid=self.datasource_uid,
            query=query,
            start=start,
            end=end
        )

        return result

    def _query_error_metric(
        self,
        interface: str,
        direction: str,
        start: datetime,
        end: datetime
    ) -> Dict[str, Any]:
        """Query error metric."""
        metric_name = 'ifInErrors' if direction == 'in' else 'ifOutErrors'

        query = f'increase({metric_name}{{ifDescr=~".*{interface}.*"}}[{self._get_range_duration(start, end)}])'

        result = self.client.query_prometheus(
            datasource_uid=self.datasource_uid,
            query=query,
            start=start,
            end=end
        )

        return result

    def _process_timeseries(self, data: Dict[str, Any]) -> Dict[str, float]:
        """
        Process Grafana timeseries data and extract statistics.

        Args:
            data: Raw Grafana query result

        Returns:
            Dictionary with current, max, avg, min values
        """
        try:
            # Extract values from Grafana response
            # Structure: {'results': {'A': {'frames': [...]}}}
            frames = data.get('results', {}).get('A', {}).get('frames', [])

            if not frames:
                return {'current': 0, 'max': 0, 'avg': 0, 'min': 0}

            # Extract values from first frame
            frame = frames[0]
            values = []

            # Parse frame data (structure varies by datasource)
            if 'data' in frame and 'values' in frame['data']:
                # Time series data
                value_series = frame['data']['values']
                if len(value_series) > 1:
                    values = [v for v in value_series[1] if v is not None]

            if not values:
                return {'current': 0, 'max': 0, 'avg': 0, 'min': 0}

            return {
                'current': values[-1] if values else 0,
                'max': max(values),
                'avg': statistics.mean(values),
                'min': min(values)
            }

        except Exception as e:
            logger.warning(f"Failed to process timeseries: {e}")
            return {'current': 0, 'max': 0, 'avg': 0, 'min': 0}

    def _get_range_duration(self, start: datetime, end: datetime) -> str:
        """Get range duration as Prometheus duration string."""
        delta = end - start
        hours = int(delta.total_seconds() / 3600)
        if hours < 1:
            minutes = int(delta.total_seconds() / 60)
            return f"{minutes}m"
        elif hours < 24:
            return f"{hours}h"
        else:
            days = int(hours / 24)
            return f"{days}d"

    def test_collection(self) -> bool:
        """
        Test if metrics collection is working.

        Returns:
            True if test successful
        """
        try:
            # Test connection
            if not self.client.test_connection():
                logger.error("Grafana connection test failed")
                return False

            # Test datasource
            if not self.datasource_uid:
                logger.error("No datasource available")
                return False

            logger.info("Metrics collection test passed")
            return True

        except Exception as e:
            logger.error(f"Metrics collection test failed: {e}")
            return False
