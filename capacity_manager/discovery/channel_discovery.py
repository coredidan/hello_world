"""
Automatic channel discovery from Grafana.

Discovers network interfaces and channels from Grafana metrics
and classifies them automatically.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Set
import re
from datetime import datetime, timedelta

if False:  # TYPE_CHECKING
    from capacity_manager.api.grafana_client import GrafanaClient
    from capacity_manager.discovery.classifier import ChannelClassifier, ChannelType


@dataclass
class DiscoveredChannel:
    """Represents a discovered network channel."""

    interface_name: str
    description: str
    channel_type: str  # external, inter_site, transport, unknown
    device_name: Optional[str] = None
    capacity_mbps: Optional[float] = None
    current_utilization: Optional[float] = None
    discovered_at: Optional[str] = None
    metrics_available: List[str] = None

    def __post_init__(self):
        if self.metrics_available is None:
            self.metrics_available = []
        if self.discovered_at is None:
            self.discovered_at = datetime.now().isoformat()


@dataclass
class DiscoveryResult:
    """Results of channel discovery process."""

    discovered_channels: List[DiscoveredChannel]
    total_found: int
    by_type: Dict[str, int]
    already_configured: List[str]
    new_channels: List[DiscoveredChannel]
    discovery_time: str


class ChannelDiscovery:
    """Discovers and classifies network channels from Grafana."""

    def __init__(
        self,
        grafana_client: 'GrafanaClient',
        classifier: 'ChannelClassifier',
        existing_channels: Optional[List[str]] = None
    ):
        """
        Initialize channel discovery.

        Args:
            grafana_client: Grafana API client
            classifier: Channel classifier
            existing_channels: List of already configured channel names
        """
        self.grafana_client = grafana_client
        self.classifier = classifier
        self.existing_channels = set(existing_channels or [])

    def discover_channels(
        self,
        datasource: str,
        query_pattern: Optional[str] = None,
        min_capacity_mbps: Optional[float] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> DiscoveryResult:
        """
        Discover network channels from Grafana.

        Args:
            datasource: Grafana datasource name
            query_pattern: Pattern to match interface names (e.g., "ifHCInOctets")
            min_capacity_mbps: Minimum capacity threshold
            exclude_patterns: List of regex patterns to exclude interfaces

        Returns:
            DiscoveryResult with discovered channels
        """
        discovery_start = datetime.now()

        # Query Grafana for interfaces
        interfaces = self._query_interfaces(datasource, query_pattern)

        # Filter out excluded patterns
        if exclude_patterns:
            interfaces = self._filter_excluded(interfaces, exclude_patterns)

        # Classify channels
        discovered = []
        for interface in interfaces:
            channel = self._process_interface(interface, min_capacity_mbps)
            if channel:
                discovered.append(channel)

        # Separate new vs already configured
        new_channels = []
        already_configured = []

        for channel in discovered:
            channel_id = self._generate_channel_id(channel)
            if channel_id in self.existing_channels:
                already_configured.append(channel_id)
            else:
                new_channels.append(channel)

        # Calculate statistics
        by_type = self._calculate_type_stats(discovered)

        return DiscoveryResult(
            discovered_channels=discovered,
            total_found=len(discovered),
            by_type=by_type,
            already_configured=already_configured,
            new_channels=new_channels,
            discovery_time=datetime.now().isoformat()
        )

    def generate_config_yaml(self, channels: List[DiscoveredChannel]) -> str:
        """
        Generate YAML configuration for discovered channels.

        Args:
            channels: List of discovered channels

        Returns:
            YAML configuration string
        """
        yaml_lines = []
        yaml_lines.append("# Discovered channels - generated automatically")
        yaml_lines.append(f"# Generated at: {datetime.now().isoformat()}")
        yaml_lines.append("")

        for channel in channels:
            yaml_lines.append(f"  - name: \"{channel.interface_name}\"")
            yaml_lines.append(f"    type: \"{channel.channel_type}\"")

            if channel.capacity_mbps:
                yaml_lines.append(f"    capacity_mbps: {channel.capacity_mbps}")

            if channel.description:
                yaml_lines.append(f"    description: \"{channel.description}\"")

            if channel.device_name:
                yaml_lines.append(f"    device: \"{channel.device_name}\"")

            # Add placeholder for metrics query
            yaml_lines.append("    metrics_query: \"TODO: Configure metrics query\"")

            # Add placeholder for pricing
            yaml_lines.append("    pricing:")
            yaml_lines.append("      model: \"flat_rate\"  # TODO: Configure pricing")
            yaml_lines.append("      cost_per_month: 0")
            yaml_lines.append("      currency: \"USD\"")

            yaml_lines.append("")

        return "\n".join(yaml_lines)

    def _query_interfaces(
        self,
        datasource: str,
        query_pattern: Optional[str]
    ) -> List[Dict]:
        """
        Query Grafana for network interfaces.

        Args:
            datasource: Grafana datasource name
            query_pattern: Metric pattern to search for

        Returns:
            List of interface dictionaries
        """
        # This is a simplified implementation
        # In real scenario, you would query Grafana API for metrics
        # and extract interface information

        interfaces = []

        # Example query patterns for SNMP data
        patterns = [
            query_pattern if query_pattern else "ifHCInOctets",
            "ifHCOutOctets",
            "ifSpeed",
            "ifAlias"
        ]

        # Query metrics from Grafana
        # This would use the grafana_client.query_metrics() method
        # For now, return structure showing expected format

        # NOTE: Actual implementation would call:
        # metrics = self.grafana_client.query_metrics(datasource, patterns)
        # Then parse and structure the results

        return interfaces

    def _filter_excluded(
        self,
        interfaces: List[Dict],
        exclude_patterns: List[str]
    ) -> List[Dict]:
        """Filter out interfaces matching exclude patterns."""
        compiled_patterns = [re.compile(pattern) for pattern in exclude_patterns]

        filtered = []
        for interface in interfaces:
            name = interface.get('name', '')
            description = interface.get('description', '')

            excluded = False
            for pattern in compiled_patterns:
                if pattern.search(name) or pattern.search(description):
                    excluded = True
                    break

            if not excluded:
                filtered.append(interface)

        return filtered

    def _process_interface(
        self,
        interface: Dict,
        min_capacity_mbps: Optional[float]
    ) -> Optional[DiscoveredChannel]:
        """Process single interface and create DiscoveredChannel."""
        name = interface.get('name', '')
        description = interface.get('description', '')

        if not name:
            return None

        # Classify channel type
        channel_type = self.classifier.classify(description)

        # Extract capacity if available
        capacity = interface.get('capacity_mbps')
        if capacity and min_capacity_mbps and capacity < min_capacity_mbps:
            return None

        # Extract current utilization if available
        utilization = interface.get('utilization_percent')

        return DiscoveredChannel(
            interface_name=name,
            description=description,
            channel_type=channel_type.value,
            device_name=interface.get('device'),
            capacity_mbps=capacity,
            current_utilization=utilization,
            metrics_available=interface.get('metrics', [])
        )

    def _generate_channel_id(self, channel: DiscoveredChannel) -> str:
        """Generate unique identifier for channel."""
        if channel.device_name:
            return f"{channel.device_name}:{channel.interface_name}"
        return channel.interface_name

    def _calculate_type_stats(self, channels: List[DiscoveredChannel]) -> Dict[str, int]:
        """Calculate statistics by channel type."""
        stats = {
            'external': 0,
            'inter_site': 0,
            'transport': 0,
            'unknown': 0
        }

        for channel in channels:
            channel_type = channel.channel_type
            if channel_type in stats:
                stats[channel_type] += 1
            else:
                stats['unknown'] += 1

        return stats

    def find_similar_channels(
        self,
        channel: DiscoveredChannel,
        all_channels: List[DiscoveredChannel],
        similarity_threshold: float = 0.8
    ) -> List[DiscoveredChannel]:
        """
        Find similar channels based on naming patterns.

        Useful for identifying channel groups that might need similar configuration.

        Args:
            channel: Reference channel
            all_channels: All discovered channels
            similarity_threshold: Similarity threshold (0.0 to 1.0)

        Returns:
            List of similar channels
        """
        similar = []

        # Extract common prefix/suffix patterns
        ref_parts = re.split(r'[\d\-_/]+', channel.interface_name)
        ref_prefix = ref_parts[0] if ref_parts else ""

        for other in all_channels:
            if other.interface_name == channel.interface_name:
                continue

            # Check if same device
            if channel.device_name and other.device_name:
                if channel.device_name != other.device_name:
                    continue

            # Check naming similarity
            other_parts = re.split(r'[\d\-_/]+', other.interface_name)
            other_prefix = other_parts[0] if other_parts else ""

            if ref_prefix and other_prefix and ref_prefix == other_prefix:
                similar.append(other)

        return similar
