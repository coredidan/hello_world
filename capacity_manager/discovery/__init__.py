"""
Channel discovery and classification module.

This module provides automatic discovery of network channels from Grafana
and their classification based on interface description prefixes.
"""

from capacity_manager.discovery.channel_discovery import ChannelDiscovery
from capacity_manager.discovery.classifier import ChannelClassifier, ClassificationRule

__all__ = [
    'ChannelDiscovery',
    'ChannelClassifier',
    'ClassificationRule',
]
