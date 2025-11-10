"""
Channel classifier based on interface description prefixes.

Classifies discovered channels into types (external, inter_site, transport)
based on configurable prefix rules.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict
from enum import Enum


class ChannelType(Enum):
    """Channel type classification."""
    EXTERNAL = "external"
    INTER_SITE = "inter_site"
    TRANSPORT = "transport"
    UNKNOWN = "unknown"


@dataclass
class ClassificationRule:
    """Rule for classifying channels based on description prefix."""

    prefix: str
    channel_type: ChannelType
    priority: int = 0  # Higher priority rules are checked first
    case_sensitive: bool = False
    description: Optional[str] = None

    def matches(self, interface_description: str) -> bool:
        """Check if interface description matches this rule."""
        if not interface_description:
            return False

        desc = interface_description if self.case_sensitive else interface_description.lower()
        prefix = self.prefix if self.case_sensitive else self.prefix.lower()

        return desc.startswith(prefix)


class ChannelClassifier:
    """Classifies channels based on interface description patterns."""

    def __init__(self, rules: Optional[List[ClassificationRule]] = None):
        """
        Initialize classifier with rules.

        Args:
            rules: List of classification rules. If None, uses default rules.
        """
        self.rules = rules if rules else self._get_default_rules()
        # Sort rules by priority (highest first)
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def classify(self, interface_description: str) -> ChannelType:
        """
        Classify channel based on interface description.

        Args:
            interface_description: Interface description string

        Returns:
            ChannelType enum value
        """
        for rule in self.rules:
            if rule.matches(interface_description):
                return rule.channel_type

        return ChannelType.UNKNOWN

    def classify_batch(self, interfaces: List[Dict[str, str]]) -> Dict[str, ChannelType]:
        """
        Classify multiple interfaces.

        Args:
            interfaces: List of dicts with 'name' and 'description' keys

        Returns:
            Dict mapping interface name to channel type
        """
        results = {}
        for interface in interfaces:
            name = interface.get('name', '')
            description = interface.get('description', '')
            results[name] = self.classify(description)

        return results

    def get_statistics(self, classifications: Dict[str, ChannelType]) -> Dict[str, int]:
        """
        Get statistics on classified channels.

        Args:
            classifications: Dict mapping interface name to channel type

        Returns:
            Dict with counts per channel type
        """
        stats = {
            'external': 0,
            'inter_site': 0,
            'transport': 0,
            'unknown': 0,
            'total': len(classifications)
        }

        for channel_type in classifications.values():
            if channel_type == ChannelType.EXTERNAL:
                stats['external'] += 1
            elif channel_type == ChannelType.INTER_SITE:
                stats['inter_site'] += 1
            elif channel_type == ChannelType.TRANSPORT:
                stats['transport'] += 1
            else:
                stats['unknown'] += 1

        return stats

    def add_rule(self, rule: ClassificationRule) -> None:
        """Add a new classification rule and re-sort by priority."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def _get_default_rules(self) -> List[ClassificationRule]:
        """
        Get default classification rules.

        These are common patterns for telecom networks but should be
        customized based on actual naming conventions.
        """
        return [
            # External channels (internet, peering, transit)
            ClassificationRule(
                prefix="EXT:",
                channel_type=ChannelType.EXTERNAL,
                priority=100,
                description="Explicit external channel marker"
            ),
            ClassificationRule(
                prefix="IX:",
                channel_type=ChannelType.EXTERNAL,
                priority=90,
                description="Internet Exchange peering"
            ),
            ClassificationRule(
                prefix="PEER:",
                channel_type=ChannelType.EXTERNAL,
                priority=90,
                description="Peering connection"
            ),
            ClassificationRule(
                prefix="TRANSIT:",
                channel_type=ChannelType.EXTERNAL,
                priority=90,
                description="Transit provider"
            ),
            ClassificationRule(
                prefix="ISP:",
                channel_type=ChannelType.EXTERNAL,
                priority=85,
                description="ISP connection"
            ),

            # Inter-site channels
            ClassificationRule(
                prefix="SITE:",
                channel_type=ChannelType.INTER_SITE,
                priority=100,
                description="Explicit site interconnection"
            ),
            ClassificationRule(
                prefix="WAN:",
                channel_type=ChannelType.INTER_SITE,
                priority=90,
                description="Wide Area Network link"
            ),
            ClassificationRule(
                prefix="MPLS:",
                channel_type=ChannelType.INTER_SITE,
                priority=85,
                description="MPLS network"
            ),

            # Transport channels
            ClassificationRule(
                prefix="TRANSPORT:",
                channel_type=ChannelType.TRANSPORT,
                priority=100,
                description="Explicit transport marker"
            ),
            ClassificationRule(
                prefix="DWDM:",
                channel_type=ChannelType.TRANSPORT,
                priority=90,
                description="Dense Wavelength Division Multiplexing"
            ),
            ClassificationRule(
                prefix="FIBER:",
                channel_type=ChannelType.TRANSPORT,
                priority=85,
                description="Fiber optic link"
            ),
            ClassificationRule(
                prefix="L2:",
                channel_type=ChannelType.TRANSPORT,
                priority=80,
                description="Layer 2 transport"
            ),
            ClassificationRule(
                prefix="TRUNK:",
                channel_type=ChannelType.TRANSPORT,
                priority=80,
                description="Transport trunk"
            ),
        ]
