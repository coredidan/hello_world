"""Configuration management module."""

import yaml
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path
import os


@dataclass
class GrafanaConfig:
    """Grafana connection settings."""

    url: str
    token: str
    verify_ssl: bool = True
    timeout: int = 30
    datasource_uid: Optional[str] = None


@dataclass
class ThresholdsConfig:
    """Utilization thresholds."""

    warning_percent: float = 70.0
    critical_percent: float = 85.0


@dataclass
class ReportConfig:
    """Report generation settings."""

    output_dir: str = "./reports"
    include_graphs: bool = True
    top_channels_limit: int = 20


@dataclass
class MetricsConfig:
    """Metrics collection settings."""

    # Time range for metrics
    default_hours: int = 24

    # Metric names in Grafana/Prometheus
    traffic_in_metric: str = "ifInOctets"
    traffic_out_metric: str = "ifOutOctets"
    errors_in_metric: str = "ifInErrors"
    errors_out_metric: str = "ifOutErrors"

    # Sampling
    sample_interval_minutes: int = 5


@dataclass
class ChannelDefinition:
    """Channel definition from config."""

    name: str
    type: str  # external, transport, inter_site
    capacity_mbps: float
    description: Optional[str] = None
    site_a: Optional[str] = None
    site_b: Optional[str] = None
    device_a: Optional[str] = None
    device_b: Optional[str] = None
    interface_pattern: Optional[str] = None  # Regex pattern to match interfaces
    tags: List[str] = field(default_factory=list)


@dataclass
class Config:
    """Main configuration class."""

    grafana: GrafanaConfig
    thresholds: ThresholdsConfig = field(default_factory=ThresholdsConfig)
    report: ReportConfig = field(default_factory=ReportConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    channels: List[ChannelDefinition] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, file_path: str) -> "Config":
        """Load configuration from YAML file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {file_path}")

        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # Parse Grafana config
        grafana_data = data.get('grafana', {})
        # Support environment variables in token
        token = grafana_data.get('token', '')
        if token.startswith('$'):
            token = os.getenv(token[1:], token)

        grafana = GrafanaConfig(
            url=grafana_data.get('url', ''),
            token=token,
            verify_ssl=grafana_data.get('verify_ssl', True),
            timeout=grafana_data.get('timeout', 30),
            datasource_uid=grafana_data.get('datasource_uid')
        )

        # Parse thresholds
        thresholds_data = data.get('thresholds', {})
        thresholds = ThresholdsConfig(
            warning_percent=thresholds_data.get('warning_percent', 70.0),
            critical_percent=thresholds_data.get('critical_percent', 85.0)
        )

        # Parse report config
        report_data = data.get('report', {})
        report = ReportConfig(
            output_dir=report_data.get('output_dir', './reports'),
            include_graphs=report_data.get('include_graphs', True),
            top_channels_limit=report_data.get('top_channels_limit', 20)
        )

        # Parse metrics config
        metrics_data = data.get('metrics', {})
        metrics = MetricsConfig(
            default_hours=metrics_data.get('default_hours', 24),
            traffic_in_metric=metrics_data.get('traffic_in_metric', 'ifInOctets'),
            traffic_out_metric=metrics_data.get('traffic_out_metric', 'ifOutOctets'),
            errors_in_metric=metrics_data.get('errors_in_metric', 'ifInErrors'),
            errors_out_metric=metrics_data.get('errors_out_metric', 'ifOutErrors'),
            sample_interval_minutes=metrics_data.get('sample_interval_minutes', 5)
        )

        # Parse channels
        channels_data = data.get('channels', [])
        channels = [
            ChannelDefinition(
                name=ch.get('name', ''),
                type=ch.get('type', 'external'),
                capacity_mbps=ch.get('capacity_mbps', 0),
                description=ch.get('description'),
                site_a=ch.get('site_a'),
                site_b=ch.get('site_b'),
                device_a=ch.get('device_a'),
                device_b=ch.get('device_b'),
                interface_pattern=ch.get('interface_pattern'),
                tags=ch.get('tags', [])
            )
            for ch in channels_data
        ]

        return cls(
            grafana=grafana,
            thresholds=thresholds,
            report=report,
            metrics=metrics,
            channels=channels
        )

    @classmethod
    def from_dict(cls, data: Dict) -> "Config":
        """Create config from dictionary."""
        # Similar to from_yaml but accepts dict directly
        return cls.from_yaml_dict(data)

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []

        # Validate Grafana config
        if not self.grafana.url:
            errors.append("Grafana URL is required")
        if not self.grafana.token:
            errors.append("Grafana token is required")

        # Validate thresholds
        if self.thresholds.warning_percent >= self.thresholds.critical_percent:
            errors.append("Warning threshold must be less than critical threshold")
        if self.thresholds.warning_percent <= 0 or self.thresholds.critical_percent <= 0:
            errors.append("Thresholds must be positive")

        # Validate channels
        for idx, channel in enumerate(self.channels):
            if not channel.name:
                errors.append(f"Channel {idx}: name is required")
            if channel.capacity_mbps <= 0:
                errors.append(f"Channel {channel.name}: capacity must be positive")
            if channel.type not in ['external', 'transport', 'inter_site']:
                errors.append(f"Channel {channel.name}: invalid type '{channel.type}'")

        return errors
