# CLAUDE.MD - AI Assistant Guide

This file provides context and guidelines for AI assistants working with the Capacity Manager codebase.

## Project Overview

**Capacity Manager** is a CLI utility for telecom operators to monitor and analyze communication channel capacity using Grafana metrics.

### Core Purpose
- Monitor channel utilization (external, inter-site, transport)
- Predict capacity issues before they occur
- Generate executive-ready reports (Console, HTML, CSV, Excel)
- Provide intelligent recommendations for capacity upgrades
- Calculate financial impact of capacity decisions

### Technology Stack
- **Language**: Python 3.8+
- **CLI Framework**: Click (assumed) or argparse
- **Data Visualization**: Rich (console), Matplotlib/Plotly (charts)
- **Data Processing**: Pandas, NumPy
- **API Client**: requests
- **Configuration**: YAML with environment variable support
- **Forecasting**: statsmodels, scikit-learn

## Architecture

### Modular Design Principles

The project follows strict modular separation:

```
capacity_manager/
├── models/              # Data models (DTOs) - NO dependencies
├── config/              # Configuration management - depends on models only
├── grafana_api/         # Grafana HTTP client - depends on models, config
├── metrics_collector/   # Metrics collection - uses grafana_api
├── analyzer/            # Analysis engine - depends on models only
├── forecasting/         # Prediction algorithms - depends on models only
├── recommendations/     # Recommendation engine - depends on models only
├── cost_calculator/     # Financial calculations - depends on models only
├── discovery/           # Auto-discovery of channels - NEW module
├── reporters/           # Report generators - depends on models only
├── cli/                 # CLI orchestration - uses all modules
└── utils/               # Helpers - NO dependencies
```

### Key Design Patterns

1. **Dependency Injection**: Modules receive dependencies rather than creating them
2. **Single Responsibility**: Each module has one clear purpose
3. **Data Models as Contracts**: All modules communicate via shared model classes
4. **Strategy Pattern**: Multiple reporters, analyzers, pricing models

## Key Files

### Entry Points
- `capacity_manager/cli/main.py` - CLI command definitions
- `capacity_manager/__main__.py` - Package entry point

### Core Models (models/)
- `channel.py` - Channel, ChannelType, PricingModel definitions
- `analysis.py` - AnalysisResult, Forecast, Recommendation structures

### Business Logic
- `analyzer/capacity_analyzer.py` - Utilization calculation, threshold detection
- `forecasting/predictor.py` - Trend analysis, 90-day forecasting
- `recommendations/engine.py` - Intelligent recommendation generation
- `cost_calculator/calculator.py` - Financial modeling (5 pricing models)
- `discovery/channel_discovery.py` - Auto-discovery of new channels
- `discovery/classifier.py` - Rule-based channel classification

### Data Access
- `grafana_api/client.py` - Grafana API client
- `metrics_collector/collector.py` - Metrics aggregation

### Output
- `reporters/console_reporter.py` - Rich terminal output
- `reporters/html_reporter.py` - HTML reports with charts
- `reporters/csv_reporter.py` - CSV/Excel export

## Configuration

### Config Structure (config.yaml)

```yaml
grafana:
  url: "https://grafana.example.com"
  token: "$GRAFANA_TOKEN"  # Environment variable substitution
  verify_ssl: true

channels:
  - name: "Internet-Provider1"
    type: "external"  # external | inter_site | transport
    capacity_mbps: 10000
    site_a: "MSK-DC1"
    device_a: "CORE-RTR-01"
    interface_pattern: "GigabitEthernet0/0/1"
    pricing:
      model: "burstable_95"  # flat_rate | per_mbps | tiered | usage_based | burstable_95
      committed_rate_mbps: 1000
      cost_per_mbps_month: 40

discovery:
  enabled: true
  datasource: "prometheus"
  min_capacity_mbps: 100.0
  classification_rules:
    - prefix: "IX:"
      channel_type: "external"
      priority: 90

thresholds:
  warning: 70
  critical: 85
```

## Common Tasks

### Adding a New Channel Type

1. Update `models/channel.py`:
   ```python
   class ChannelType(Enum):
       EXTERNAL = "external"
       INTER_SITE = "inter_site"
       TRANSPORT = "transport"
       NEW_TYPE = "new_type"  # Add here
   ```

2. Update `recommendations/engine.py` to handle new type
3. Update classification rules in `discovery/classifier.py`

### Adding a New Report Format

1. Create `reporters/new_reporter.py`:
   ```python
   class NewReporter:
       def generate(self, report: CapacityReport) -> None:
           # Implementation
   ```

2. Register in `cli/main.py`

### Adding a New Pricing Model

1. Update `models/channel.py`:
   ```python
   class PricingModel(Enum):
       NEW_MODEL = "new_model"
   ```

2. Implement calculation in `cost_calculator/calculator.py`:
   ```python
   def _calculate_new_model(self, channel: Channel, metrics: ChannelMetrics) -> ChannelCost:
       # Implementation
   ```

### Adding a New Discovery Rule

Add to `config.yaml`:
```yaml
discovery:
  classification_rules:
    - prefix: "CUSTOM:"
      channel_type: "external"
      priority: 95
      description: "Custom channel marker"
```

## Development Guidelines

### Code Style
- Follow PEP 8
- Use type hints for all function signatures
- Docstrings for public methods (Google style)
- Keep functions focused and small (<50 lines)

### Error Handling
- Use custom exceptions from `models/exceptions.py` (if exists)
- Provide clear error messages for users
- Log errors with context for debugging

### Testing Strategy
- Unit tests: Test each module independently
- Integration tests: Test Grafana API interaction
- Mock external dependencies (Grafana API)

### Adding New Dependencies
1. Add to `requirements.txt`
2. Consider impact on module independence
3. Document in this file

## Important Patterns

### Threshold Detection
```python
if utilization >= critical_threshold:  # 85%
    status = "critical"
elif utilization >= warning_threshold:  # 70%
    status = "warning"
else:
    status = "normal"
```

### Forecast Horizon
- Default: 90 days
- Calculates: warning_date, critical_date, capacity_date
- Methods: Linear regression + Holt's exponential smoothing

### Burstable Billing (95th Percentile)
- Industry standard for telecom
- Collects samples over billing period
- Sorts and discards top 5%
- Bills at max(95th_percentile, committed_rate)

### Channel Classification Priority
- Higher priority rules checked first (100 > 90 > 80)
- First match wins
- Default fallback: "unknown"

## CLI Commands

```bash
# Check connectivity
capacity-manager check

# Generate reports
capacity-manager report [--format console|html|csv|excel|all] [--hours 24]

# Find critical channels
capacity-manager alert [--threshold 85]

# Channel details
capacity-manager detail "Channel-Name" [--hours 24]

# Auto-discover new channels
capacity-manager discover [--output discovered.yaml] [--filter-type external]
```

## Gotchas and Considerations

### 1. Grafana Query Performance
- Large time ranges (>7 days) can be slow
- Use appropriate aggregation intervals
- Consider caching for frequently-accessed data

### 2. Time Zones
- Ensure consistent timezone handling between Grafana and local system
- Metrics are typically in UTC

### 3. Interface Naming
- Interface patterns must match exact Grafana metric labels
- Case-sensitive matching
- Use regex for flexible matching if needed

### 4. Discovery False Positives
- Loopback, VLAN interfaces should be excluded
- Use `exclude_patterns` in config
- Validate discovered channels before adding to production config

### 5. Pricing Model Selection
- `burstable_95` requires historical sample data
- `usage_based` needs accurate traffic volume metrics
- `tiered` requires careful tier boundary definition

### 6. Forecast Accuracy
- Requires minimum 7 days of historical data
- Accuracy degrades beyond 90 days
- Non-linear growth patterns may need manual adjustment

## Dependencies

### Core
- `requests` - HTTP client for Grafana API
- `pyyaml` - Configuration parsing
- `click` - CLI framework (or `argparse`)

### Data Processing
- `pandas` - Data manipulation
- `numpy` - Numerical operations
- `statsmodels` - Time series forecasting
- `scikit-learn` - Machine learning algorithms

### Visualization
- `rich` - Terminal formatting
- `matplotlib` or `plotly` - Charts for HTML reports
- `openpyxl` - Excel file generation

### Optional
- `requests-cache` - API response caching
- `python-dotenv` - Environment variable management

## Deployment

### Installation
```bash
pip install -e .  # Development mode
# or
pip install .     # Production mode
```

### Configuration
1. Copy `config.example.yaml` to `config.yaml`
2. Set `GRAFANA_TOKEN` environment variable
3. Configure channels or use discovery

### Automation
```bash
# Daily report (cron example)
0 9 * * * /usr/local/bin/capacity-manager report --format html --output /var/www/reports/daily.html

# Hourly alerts
0 * * * * /usr/local/bin/capacity-manager alert --threshold 85 | mail -s "Alert" ops@company.com
```

## Future Enhancements

### Potential Additions
- [ ] Database backend for historical storage
- [ ] REST API for programmatic access
- [ ] Webhook notifications (Slack, Teams)
- [ ] Multi-tenant support
- [ ] Custom alerting rules
- [ ] Integration with ticketing systems
- [ ] Machine learning for anomaly detection
- [ ] What-if scenario modeling

## Contributing

When making changes:
1. Maintain module independence
2. Update tests
3. Update documentation (README.md, this file)
4. Follow existing code style
5. Test with real Grafana instance
6. Consider backward compatibility

## Troubleshooting

### Common Issues

**"Connection to Grafana failed"**
- Check `grafana.url` in config
- Verify `GRAFANA_TOKEN` is set
- Check SSL certificate if `verify_ssl: true`

**"No data returned for channel"**
- Verify `interface_pattern` matches Grafana metrics
- Check datasource name in config
- Verify time range includes data

**"Discovery finds no channels"**
- Check `discovery.enabled: true`
- Verify datasource is accessible
- Review `exclude_patterns` - may be too broad

**"Forecast not available"**
- Requires minimum 7 days of data
- Check for gaps in historical data
- Verify sufficient data points

## Resources

- **README.md** - User-facing documentation
- **ARCHITECTURE.md** - Detailed architecture overview
- **config.example.yaml** - Configuration template
- **demo_discovery.py** - Discovery feature example

## Contact

For questions about the codebase, refer to repository issues or maintainer contact in README.md.
