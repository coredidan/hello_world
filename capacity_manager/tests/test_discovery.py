"""Unit tests for discovery module."""

import unittest
from capacity_manager.discovery.classifier import (
    ChannelClassifier,
    ClassificationRule,
    ChannelType
)
from capacity_manager.discovery.channel_discovery import (
    ChannelDiscovery,
    DiscoveredChannel,
    DiscoveryResult
)


class TestChannelClassifier(unittest.TestCase):
    """Test cases for ChannelClassifier."""

    def setUp(self):
        """Set up test fixtures."""
        self.classifier = ChannelClassifier()

    def test_classify_external_channels(self):
        """Test classification of external channels."""
        test_cases = [
            ("IX: Moscow Exchange", ChannelType.EXTERNAL),
            ("PEER: Provider AS12345", ChannelType.EXTERNAL),
            ("TRANSIT: Level3", ChannelType.EXTERNAL),
            ("ISP: Local provider", ChannelType.EXTERNAL),
        ]

        for description, expected_type in test_cases:
            with self.subTest(description=description):
                result = self.classifier.classify(description)
                self.assertEqual(result, expected_type)

    def test_classify_inter_site_channels(self):
        """Test classification of inter-site channels."""
        test_cases = [
            ("SITE: DC1-DC2", ChannelType.INTER_SITE),
            ("WAN: Moscow-SPB", ChannelType.INTER_SITE),
            ("MPLS: Network link", ChannelType.INTER_SITE),
        ]

        for description, expected_type in test_cases:
            with self.subTest(description=description):
                result = self.classifier.classify(description)
                self.assertEqual(result, expected_type)

    def test_classify_transport_channels(self):
        """Test classification of transport channels."""
        test_cases = [
            ("TRANSPORT: Core link", ChannelType.TRANSPORT),
            ("DWDM: Fiber", ChannelType.TRANSPORT),
            ("FIBER: Dark fiber", ChannelType.TRANSPORT),
            ("L2: Layer 2", ChannelType.TRANSPORT),
            ("TRUNK: Aggregation", ChannelType.TRANSPORT),
        ]

        for description, expected_type in test_cases:
            with self.subTest(description=description):
                result = self.classifier.classify(description)
                self.assertEqual(result, expected_type)

    def test_classify_unknown(self):
        """Test classification of unknown channels."""
        result = self.classifier.classify("Random interface description")
        self.assertEqual(result, ChannelType.UNKNOWN)

    def test_case_insensitive_matching(self):
        """Test case-insensitive pattern matching."""
        # Default rules are case-insensitive
        result1 = self.classifier.classify("ix: lowercase")
        result2 = self.classifier.classify("IX: uppercase")
        result3 = self.classifier.classify("Ix: Mixed")

        self.assertEqual(result1, ChannelType.EXTERNAL)
        self.assertEqual(result2, ChannelType.EXTERNAL)
        self.assertEqual(result3, ChannelType.EXTERNAL)

    def test_priority_ordering(self):
        """Test that higher priority rules are checked first."""
        rules = [
            ClassificationRule("TEST:", ChannelType.EXTERNAL, priority=50),
            ClassificationRule("TEST:SPECIAL:", ChannelType.TRANSPORT, priority=100),
        ]
        classifier = ChannelClassifier(rules=rules)

        # Higher priority rule should match first
        result = classifier.classify("TEST:SPECIAL: Something")
        self.assertEqual(result, ChannelType.TRANSPORT)

    def test_batch_classification(self):
        """Test batch classification of multiple interfaces."""
        interfaces = [
            {"name": "eth0", "description": "IX: Test"},
            {"name": "eth1", "description": "WAN: Test"},
            {"name": "eth2", "description": "Unknown"},
        ]

        results = self.classifier.classify_batch(interfaces)

        self.assertEqual(len(results), 3)
        self.assertEqual(results["eth0"], ChannelType.EXTERNAL)
        self.assertEqual(results["eth1"], ChannelType.INTER_SITE)
        self.assertEqual(results["eth2"], ChannelType.UNKNOWN)

    def test_statistics(self):
        """Test statistics calculation."""
        classifications = {
            "eth0": ChannelType.EXTERNAL,
            "eth1": ChannelType.EXTERNAL,
            "eth2": ChannelType.INTER_SITE,
            "eth3": ChannelType.TRANSPORT,
            "eth4": ChannelType.UNKNOWN,
        }

        stats = self.classifier.get_statistics(classifications)

        self.assertEqual(stats['total'], 5)
        self.assertEqual(stats['external'], 2)
        self.assertEqual(stats['inter_site'], 1)
        self.assertEqual(stats['transport'], 1)
        self.assertEqual(stats['unknown'], 1)

    def test_add_rule(self):
        """Test adding new classification rule."""
        initial_count = len(self.classifier.rules)

        new_rule = ClassificationRule(
            "CUSTOM:",
            ChannelType.EXTERNAL,
            priority=95
        )
        self.classifier.add_rule(new_rule)

        self.assertEqual(len(self.classifier.rules), initial_count + 1)

        # Test that the new rule works
        result = self.classifier.classify("CUSTOM: test interface")
        self.assertEqual(result, ChannelType.EXTERNAL)


class TestDiscoveredChannel(unittest.TestCase):
    """Test cases for DiscoveredChannel."""

    def test_create_discovered_channel(self):
        """Test creating a DiscoveredChannel instance."""
        channel = DiscoveredChannel(
            interface_name="eth0",
            description="IX: Test",
            channel_type="external",
            device_name="router-01",
            capacity_mbps=10000.0,
            current_utilization=65.5
        )

        self.assertEqual(channel.interface_name, "eth0")
        self.assertEqual(channel.description, "IX: Test")
        self.assertEqual(channel.channel_type, "external")
        self.assertEqual(channel.device_name, "router-01")
        self.assertEqual(channel.capacity_mbps, 10000.0)
        self.assertEqual(channel.current_utilization, 65.5)
        self.assertIsNotNone(channel.discovered_at)

    def test_discovered_channel_defaults(self):
        """Test default values for DiscoveredChannel."""
        channel = DiscoveredChannel(
            interface_name="eth0",
            description="Test",
            channel_type="external"
        )

        self.assertIsNone(channel.device_name)
        self.assertIsNone(channel.capacity_mbps)
        self.assertIsNone(channel.current_utilization)
        self.assertIsNotNone(channel.discovered_at)
        self.assertIsInstance(channel.metrics_available, list)


class TestChannelDiscovery(unittest.TestCase):
    """Test cases for ChannelDiscovery."""

    def setUp(self):
        """Set up test fixtures."""
        self.classifier = ChannelClassifier()
        self.discovery = ChannelDiscovery(
            grafana_client=None,  # Mock
            classifier=self.classifier,
            existing_channels=["existing-eth0"]
        )

    def test_generate_channel_id(self):
        """Test channel ID generation."""
        channel_with_device = DiscoveredChannel(
            interface_name="eth0",
            description="Test",
            channel_type="external",
            device_name="router-01"
        )

        channel_without_device = DiscoveredChannel(
            interface_name="eth1",
            description="Test",
            channel_type="external"
        )

        id1 = self.discovery._generate_channel_id(channel_with_device)
        id2 = self.discovery._generate_channel_id(channel_without_device)

        self.assertEqual(id1, "router-01:eth0")
        self.assertEqual(id2, "eth1")

    def test_calculate_type_stats(self):
        """Test statistics calculation."""
        channels = [
            DiscoveredChannel("eth0", "IX: Test", "external"),
            DiscoveredChannel("eth1", "IX: Test2", "external"),
            DiscoveredChannel("eth2", "WAN: Test", "inter_site"),
            DiscoveredChannel("eth3", "DWDM: Test", "transport"),
            DiscoveredChannel("eth4", "Unknown", "unknown"),
        ]

        stats = self.discovery._calculate_type_stats(channels)

        self.assertEqual(stats['external'], 2)
        self.assertEqual(stats['inter_site'], 1)
        self.assertEqual(stats['transport'], 1)
        self.assertEqual(stats['unknown'], 1)

    def test_generate_config_yaml(self):
        """Test YAML configuration generation."""
        channels = [
            DiscoveredChannel(
                interface_name="eth0",
                description="IX: Test",
                channel_type="external",
                device_name="router-01",
                capacity_mbps=10000.0
            )
        ]

        yaml_output = self.discovery.generate_config_yaml(channels)

        self.assertIn("eth0", yaml_output)
        self.assertIn("external", yaml_output)
        self.assertIn("router-01", yaml_output)
        self.assertIn("10000", yaml_output)
        self.assertIn("pricing:", yaml_output)
        self.assertIn("metrics_query:", yaml_output)

    def test_filter_excluded(self):
        """Test filtering of excluded interfaces."""
        interfaces = [
            {"name": "eth0", "description": "Valid"},
            {"name": "lo0", "description": "Loopback"},
            {"name": "vlan100", "description": "VLAN"},
            {"name": "mgmt0", "description": "Management"},
        ]

        exclude_patterns = ["^lo", "^vlan", "^mgmt"]

        filtered = self.discovery._filter_excluded(interfaces, exclude_patterns)

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['name'], "eth0")


if __name__ == '__main__':
    unittest.main()
