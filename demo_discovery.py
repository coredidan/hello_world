#!/usr/bin/env python3
"""
Demo script to show how channel discovery and classification works.
This simulates discovery without needing real Grafana connection.
"""

from capacity_manager.discovery.classifier import ChannelClassifier, ClassificationRule, ChannelType
from capacity_manager.discovery.channel_discovery import ChannelDiscovery, DiscoveredChannel
from capacity_manager.config.settings import Config
from datetime import datetime

print("="*80)
print("CAPACITY MANAGER - CHANNEL DISCOVERY DEMO")
print("="*80)

# Load configuration
print("\n1. Loading configuration from config.test.yaml...")
config = Config.from_yaml('config.test.yaml')
print(f"   ✓ Loaded {len(config.discovery.classification_rules)} classification rules")
print(f"   ✓ Min capacity threshold: {config.discovery.min_capacity_mbps} Mbps")

# Build classifier from config
print("\n2. Building classifier...")
classification_rules = []
for rule_cfg in config.discovery.classification_rules:
    channel_type_map = {
        'external': ChannelType.EXTERNAL,
        'inter_site': ChannelType.INTER_SITE,
        'transport': ChannelType.TRANSPORT
    }
    channel_type = channel_type_map.get(rule_cfg.channel_type, ChannelType.UNKNOWN)

    rule = ClassificationRule(
        prefix=rule_cfg.prefix,
        channel_type=channel_type,
        priority=rule_cfg.priority,
        case_sensitive=rule_cfg.case_sensitive,
        description=rule_cfg.description
    )
    classification_rules.append(rule)

classifier = ChannelClassifier(rules=classification_rules)
print(f"   ✓ Classifier ready with {len(classifier.rules)} rules")

# Simulate discovered interfaces (this would come from Grafana in real scenario)
print("\n3. Simulating interface discovery...")
simulated_interfaces = [
    {
        'name': 'GigabitEthernet0/0/1',
        'description': 'IX: Moscow Internet Exchange peering',
        'device': 'CORE-RTR-01',
        'capacity_mbps': 10000,
        'utilization_percent': 65.5
    },
    {
        'name': 'GigabitEthernet0/0/2',
        'description': 'PEER: Rostelecom AS12389',
        'device': 'CORE-RTR-01',
        'capacity_mbps': 10000,
        'utilization_percent': 45.2
    },
    {
        'name': 'TenGigE0/1/0',
        'description': 'TRANSIT: Level3 AS3356',
        'device': 'CORE-RTR-01',
        'capacity_mbps': 10000,
        'utilization_percent': 78.9
    },
    {
        'name': 'HundredGigE0/2/0',
        'description': 'WAN: MSK-DC1 to SPB-DC1',
        'device': 'CORE-RTR-01',
        'capacity_mbps': 100000,
        'utilization_percent': 52.3
    },
    {
        'name': 'HundredGigE0/2/1',
        'description': 'SITE: MSK-DC1 to EKB-DC1',
        'device': 'CORE-RTR-02',
        'capacity_mbps': 40000,
        'utilization_percent': 38.7
    },
    {
        'name': 'TenGigE0/3/0',
        'description': 'DWDM: Transport to AGG-01',
        'device': 'CORE-RTR-01',
        'capacity_mbps': 20000,
        'utilization_percent': 25.1
    },
    {
        'name': 'TenGigE0/3/1',
        'description': 'TRUNK: Core to Aggregation',
        'device': 'CORE-RTR-02',
        'capacity_mbps': 20000,
        'utilization_percent': 31.4
    },
    {
        'name': 'TenGigE0/3/2',
        'description': 'L2: Internal transport',
        'device': 'CORE-RTR-03',
        'capacity_mbps': 10000,
        'utilization_percent': 15.8
    },
    {
        'name': 'lo0',
        'description': 'Loopback interface',
        'device': 'CORE-RTR-01',
        'capacity_mbps': 0,
        'utilization_percent': 0
    },
    {
        'name': 'mgmt0',
        'description': 'Management interface',
        'device': 'CORE-RTR-01',
        'capacity_mbps': 1000,
        'utilization_percent': 5.2
    },
]

print(f"   Found {len(simulated_interfaces)} interfaces")

# Classify each interface
print("\n4. Classifying interfaces...")
discovered_channels = []

for interface in simulated_interfaces:
    # Apply filters
    if interface['capacity_mbps'] < config.discovery.min_capacity_mbps:
        print(f"   ⊝ Skipped {interface['name']}: capacity below threshold")
        continue

    # Check exclude patterns
    import re
    excluded = False
    for pattern in config.discovery.exclude_patterns:
        if re.match(pattern, interface['name']):
            print(f"   ⊝ Excluded {interface['name']}: matches pattern '{pattern}'")
            excluded = True
            break

    if excluded:
        continue

    # Classify
    channel_type = classifier.classify(interface['description'])

    discovered = DiscoveredChannel(
        interface_name=interface['name'],
        description=interface['description'],
        channel_type=channel_type.value,
        device_name=interface['device'],
        capacity_mbps=interface['capacity_mbps'],
        current_utilization=interface['utilization_percent']
    )

    discovered_channels.append(discovered)

    type_emoji = {
        'external': '🌐',
        'inter_site': '🔗',
        'transport': '📡',
        'unknown': '❓'
    }

    emoji = type_emoji.get(channel_type.value, '?')
    print(f"   {emoji} {interface['name']:25} → {channel_type.value:12} ({interface['description'][:40]})")

# Statistics
print("\n5. Statistics:")
stats = classifier.get_statistics({ch.interface_name: ChannelType(ch.channel_type) for ch in discovered_channels})
print(f"   Total discovered: {stats['total']}")
print(f"   External:         {stats['external']}")
print(f"   Inter-site:       {stats['inter_site']}")
print(f"   Transport:        {stats['transport']}")
print(f"   Unknown:          {stats['unknown']}")

# Generate YAML configuration
print("\n6. Generating YAML configuration...")
discovery = ChannelDiscovery(
    grafana_client=None,
    classifier=classifier,
    existing_channels=[]
)

yaml_output = discovery.generate_config_yaml(discovered_channels)

# Save to file
output_file = 'discovered_channels_demo.yaml'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(yaml_output)

print(f"   ✓ Configuration saved to: {output_file}")

# Show preview
print("\n7. Preview of generated YAML:")
print("-" * 80)
print(yaml_output[:800])
if len(yaml_output) > 800:
    print("   ...")
    print("   [truncated - see full file in discovered_channels_demo.yaml]")
print("-" * 80)

print("\n" + "="*80)
print("✓ DEMO COMPLETE!")
print("="*80)
print("\nSummary:")
print(f"  • Discovered {len(discovered_channels)} channels")
print(f"  • External channels: {stats['external']}")
print(f"  • Inter-site channels: {stats['inter_site']}")
print(f"  • Transport channels: {stats['transport']}")
print(f"  • Configuration saved to: {output_file}")
print("\nNext steps:")
print("  1. Review the generated YAML file")
print("  2. Adjust pricing and metrics_query for each channel")
print("  3. Add to your config.yaml channels section")
print("  4. Run: capacity-manager report")
print()
