"""Main CLI module - orchestrates all components."""

import click
import logging
from pathlib import Path
from datetime import datetime, timedelta
from rich.console import Console

from ..config.settings import Config
from ..grafana_api.client import GrafanaClient
from ..metrics_collector.collector import MetricsCollector
from ..analyzer.capacity_analyzer import CapacityAnalyzer
from ..reporters.console_reporter import ConsoleReporter
from ..reporters.html_reporter import HTMLReporter
from ..reporters.csv_reporter import CSVReporter
from ..models.channel import Channel, ChannelType
from ..discovery.channel_discovery import ChannelDiscovery
from ..discovery.classifier import ChannelClassifier, ClassificationRule, ChannelType as DiscoveryChannelType


console = Console()
logger = logging.getLogger(__name__)


@click.group()
@click.option('--config', '-c', default='config.yaml', help='Path to config file')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def main(ctx, config, verbose):
    """
    Capacity Manager - CLI tool for Grafana metrics analysis.

    Analyzes network channel utilization and generates capacity management reports.
    """
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Load config
    try:
        ctx.ensure_object(dict)
        ctx.obj['config_path'] = config

        config_file = Path(config)
        if not config_file.exists():
            console.print(f"[yellow]Config file not found: {config}[/]")
            console.print(f"[yellow]Use 'config.example.yaml' as template[/]")
            ctx.obj['config'] = None
        else:
            cfg = Config.from_yaml(config)

            # Validate config
            errors = cfg.validate()
            if errors:
                console.print("[red]Configuration errors:[/]")
                for error in errors:
                    console.print(f"  - {error}")
                raise click.Abort()

            ctx.obj['config'] = cfg
            logger.info(f"Configuration loaded from {config}")

    except Exception as e:
        console.print(f"[red]Failed to load config: {e}[/]")
        raise click.Abort()


@main.command()
@click.pass_context
def check(ctx):
    """Quick health check of Grafana connection."""
    config = ctx.obj.get('config')
    if not config:
        console.print("[red]Config not loaded[/]")
        return

    console.print("[cyan]Testing Grafana connection...[/]")

    try:
        client = GrafanaClient(
            url=config.grafana.url,
            token=config.grafana.token,
            verify_ssl=config.grafana.verify_ssl,
            timeout=config.grafana.timeout
        )

        if client.test_connection():
            console.print("[green]✓ Connection successful[/]")

            # Get datasources
            datasources = client.get_datasources()
            console.print(f"[green]✓ Found {len(datasources)} datasource(s)[/]")

            for ds in datasources:
                console.print(f"  - {ds.get('name')} ({ds.get('type')})")

            # Test metrics collector
            collector = MetricsCollector(client, config.grafana.datasource_uid)
            if collector.test_collection():
                console.print("[green]✓ Metrics collection ready[/]")
            else:
                console.print("[yellow]⚠ Metrics collection test failed[/]")

        else:
            console.print("[red]✗ Connection failed[/]")

    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/]")
        logger.exception("Connection check failed")


@main.command()
@click.option('--hours', '-h', default=None, type=int, help='Hours of data to analyze')
@click.option('--format', '-f', type=click.Choice(['console', 'html', 'csv', 'excel', 'all']), default='console', help='Output format')
@click.option('--output', '-o', help='Output file path (for html/csv/excel)')
@click.pass_context
def report(ctx, hours, format, output):
    """Generate capacity management report."""
    config = ctx.obj.get('config')
    if not config:
        console.print("[red]Config not loaded[/]")
        return

    # Determine time range
    if hours is None:
        hours = config.metrics.default_hours

    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)

    console.print(f"[cyan]Generating capacity report...[/]")
    console.print(f"Period: {start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%Y-%m-%d %H:%M')}")

    try:
        # Initialize components
        client = GrafanaClient(
            url=config.grafana.url,
            token=config.grafana.token,
            verify_ssl=config.grafana.verify_ssl,
            timeout=config.grafana.timeout
        )

        collector = MetricsCollector(client, config.grafana.datasource_uid)
        analyzer = CapacityAnalyzer(
            warning_threshold=config.thresholds.warning_percent,
            critical_threshold=config.thresholds.critical_percent
        )

        # Convert channel definitions to Channel objects
        channels = [
            Channel(
                name=ch.name,
                channel_type=ChannelType(ch.type),
                capacity_mbps=ch.capacity_mbps,
                description=ch.description,
                site_a=ch.site_a,
                site_b=ch.site_b,
                device_a=ch.device_a,
                device_b=ch.device_b,
                tags=ch.tags
            )
            for ch in config.channels
        ]

        console.print(f"[cyan]Collecting metrics for {len(channels)} channels...[/]")

        # Collect metrics
        metrics_list = collector.collect_multiple_channels(channels, start_time, end_time)

        if not metrics_list:
            console.print("[yellow]No metrics collected[/]")
            return

        console.print(f"[green]✓ Collected metrics for {len(metrics_list)} channels[/]")

        # Analyze
        console.print("[cyan]Analyzing capacity...[/]")
        capacity_report = analyzer.analyze_multiple_channels(metrics_list, start_time, end_time)

        console.print("[green]✓ Analysis complete[/]")
        console.print()

        # Generate reports
        if format == 'console' or format == 'all':
            reporter = ConsoleReporter(console)
            reporter.print_report(capacity_report, show_details=True)

        if format == 'html' or format == 'all':
            output_path = output or f"{config.report.output_dir}/capacity_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            html_reporter = HTMLReporter()
            html_file = html_reporter.generate_report(capacity_report, output_path)
            console.print(f"[green]✓ HTML report saved to: {html_file}[/]")

        if format == 'csv' or format == 'all':
            output_path = output or f"{config.report.output_dir}/capacity_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            csv_reporter = CSVReporter()
            csv_file = csv_reporter.export_to_csv(capacity_report, output_path)
            console.print(f"[green]✓ CSV report saved to: {csv_file}[/]")

        if format == 'excel' or format == 'all':
            output_path = output or f"{config.report.output_dir}/capacity_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            csv_reporter = CSVReporter()
            excel_file = csv_reporter.export_to_excel(capacity_report, output_path)
            console.print(f"[green]✓ Excel report saved to: {excel_file}[/]")

    except Exception as e:
        console.print(f"[red]Error generating report: {e}[/]")
        logger.exception("Report generation failed")


@main.command()
@click.option('--threshold', '-t', type=float, default=85.0, help='Utilization threshold (%)')
@click.pass_context
def alert(ctx, threshold):
    """List channels above utilization threshold."""
    config = ctx.obj.get('config')
    if not config:
        console.print("[red]Config not loaded[/]")
        return

    end_time = datetime.now()
    start_time = end_time - timedelta(hours=1)  # Last hour

    try:
        # Initialize components
        client = GrafanaClient(
            url=config.grafana.url,
            token=config.grafana.token,
            verify_ssl=config.grafana.verify_ssl
        )

        collector = MetricsCollector(client, config.grafana.datasource_uid)

        # Convert channels
        channels = [
            Channel(
                name=ch.name,
                channel_type=ChannelType(ch.type),
                capacity_mbps=ch.capacity_mbps,
                description=ch.description
            )
            for ch in config.channels
        ]

        # Collect metrics
        metrics_list = collector.collect_multiple_channels(channels, start_time, end_time)

        # Filter by threshold
        alerts = [m for m in metrics_list if m.max_utilization_percent >= threshold]

        if not alerts:
            console.print(f"[green]✓ No channels above {threshold}% utilization[/]")
            return

        console.print(f"[yellow]⚠ {len(alerts)} channel(s) above {threshold}% utilization:[/]")
        console.print()

        for m in sorted(alerts, key=lambda x: x.max_utilization_percent, reverse=True):
            status = "🚨 CRITICAL" if m.max_utilization_percent >= 85 else "⚠️  WARNING"
            console.print(
                f"{status}: [bold]{m.channel.name}[/] - "
                f"{m.max_utilization_percent:.1f}% "
                f"({m.traffic_in_mbps:.1f} / {m.traffic_out_mbps:.1f} Mbps)"
            )

    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        logger.exception("Alert check failed")


@main.command()
@click.argument('channel_name')
@click.option('--hours', '-h', default=24, type=int, help='Hours of data')
@click.pass_context
def detail(ctx, channel_name, hours):
    """Show detailed information for a specific channel."""
    config = ctx.obj.get('config')
    if not config:
        console.print("[red]Config not loaded[/]")
        return

    # Find channel in config
    channel_def = None
    for ch in config.channels:
        if ch.name.lower() == channel_name.lower():
            channel_def = ch
            break

    if not channel_def:
        console.print(f"[red]Channel not found: {channel_name}[/]")
        return

    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)

    try:
        # Initialize components
        client = GrafanaClient(
            url=config.grafana.url,
            token=config.grafana.token,
            verify_ssl=config.grafana.verify_ssl
        )

        collector = MetricsCollector(client, config.grafana.datasource_uid)
        analyzer = CapacityAnalyzer(
            warning_threshold=config.thresholds.warning_percent,
            critical_threshold=config.thresholds.critical_percent
        )

        # Create channel
        channel = Channel(
            name=channel_def.name,
            channel_type=ChannelType(channel_def.type),
            capacity_mbps=channel_def.capacity_mbps,
            description=channel_def.description,
            site_a=channel_def.site_a,
            site_b=channel_def.site_b,
            device_a=channel_def.device_a,
            device_b=channel_def.device_b
        )

        # Collect metrics
        metrics = collector.collect_channel_metrics(channel, start_time, end_time)

        if not metrics:
            console.print("[yellow]No metrics collected[/]")
            return

        # Analyze
        analysis = analyzer.analyze_channel(metrics)

        # Display
        reporter = ConsoleReporter(console)
        reporter.print_channel_details(analysis)

    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        logger.exception("Detail view failed")


@main.command()
@click.option('--output', '-o', help='Output YAML file for discovered channels')
@click.option('--show-stats/--no-stats', default=True, help='Show discovery statistics')
@click.option('--filter-type', '-t', type=click.Choice(['external', 'inter_site', 'transport', 'all']), default='all', help='Filter by channel type')
@click.pass_context
def discover(ctx, output, show_stats, filter_type):
    """
    Discover and classify network channels from Grafana.

    Automatically finds network interfaces in Grafana and classifies them
    based on interface description prefixes configured in the config file.
    """
    config = ctx.obj.get('config')
    if not config:
        console.print("[red]Config not loaded[/]")
        return

    if not config.discovery.enabled:
        console.print("[yellow]⚠ Discovery is disabled in config[/]")
        console.print("[yellow]Set discovery.enabled: true in your config file[/]")
        return

    console.print("[cyan]🔍 Starting channel discovery...[/]")
    console.print(f"Datasource: {config.discovery.datasource}")
    console.print(f"Query pattern: {config.discovery.query_pattern}")
    console.print(f"Min capacity: {config.discovery.min_capacity_mbps} Mbps")
    console.print()

    try:
        # Initialize Grafana client
        client = GrafanaClient(
            url=config.grafana.url,
            token=config.grafana.token,
            verify_ssl=config.grafana.verify_ssl,
            timeout=config.grafana.timeout
        )

        # Build classifier from config rules
        classification_rules = []
        if config.discovery.auto_classify and config.discovery.classification_rules:
            for rule_cfg in config.discovery.classification_rules:
                channel_type_map = {
                    'external': DiscoveryChannelType.EXTERNAL,
                    'inter_site': DiscoveryChannelType.INTER_SITE,
                    'transport': DiscoveryChannelType.TRANSPORT
                }
                channel_type = channel_type_map.get(rule_cfg.channel_type, DiscoveryChannelType.UNKNOWN)

                rule = ClassificationRule(
                    prefix=rule_cfg.prefix,
                    channel_type=channel_type,
                    priority=rule_cfg.priority,
                    case_sensitive=rule_cfg.case_sensitive,
                    description=rule_cfg.description
                )
                classification_rules.append(rule)

        classifier = ChannelClassifier(rules=classification_rules if classification_rules else None)

        # Get existing channel names to avoid duplicates
        existing_channels = [ch.name for ch in config.channels]

        # Initialize discovery
        discovery = ChannelDiscovery(
            grafana_client=client,
            classifier=classifier,
            existing_channels=existing_channels
        )

        # Perform discovery
        console.print("[cyan]Querying Grafana for interfaces...[/]")
        result = discovery.discover_channels(
            datasource=config.discovery.datasource,
            query_pattern=config.discovery.query_pattern,
            min_capacity_mbps=config.discovery.min_capacity_mbps,
            exclude_patterns=config.discovery.exclude_patterns
        )

        console.print(f"[green]✓ Discovery complete[/]")
        console.print()

        # Show statistics
        if show_stats:
            console.print("[cyan]📊 Discovery Statistics:[/]")
            console.print(f"Total channels found: [bold]{result.total_found}[/]")
            console.print(f"Already configured: [yellow]{len(result.already_configured)}[/]")
            console.print(f"New channels: [green]{len(result.new_channels)}[/]")
            console.print()

            console.print("[cyan]By Type:[/]")
            for channel_type, count in result.by_type.items():
                console.print(f"  {channel_type}: {count}")
            console.print()

        # Filter channels by type if requested
        channels_to_show = result.new_channels
        if filter_type != 'all':
            channels_to_show = [
                ch for ch in result.new_channels
                if ch.channel_type == filter_type
            ]

        # Display new channels
        if channels_to_show:
            console.print(f"[cyan]🆕 New Channels ({len(channels_to_show)}):[/]")
            console.print()

            for ch in channels_to_show:
                type_color = {
                    'external': 'blue',
                    'inter_site': 'magenta',
                    'transport': 'cyan',
                    'unknown': 'yellow'
                }.get(ch.channel_type, 'white')

                console.print(f"[bold]{ch.interface_name}[/]")
                console.print(f"  Type: [{type_color}]{ch.channel_type}[/{type_color}]")
                if ch.description:
                    console.print(f"  Description: {ch.description}")
                if ch.device_name:
                    console.print(f"  Device: {ch.device_name}")
                if ch.capacity_mbps:
                    console.print(f"  Capacity: {ch.capacity_mbps:.0f} Mbps")
                if ch.current_utilization:
                    console.print(f"  Current utilization: {ch.current_utilization:.1f}%")
                console.print()
        else:
            console.print("[yellow]No new channels found[/]")
            console.print()

        # Generate YAML output if requested
        if output and result.new_channels:
            yaml_content = discovery.generate_config_yaml(result.new_channels)

            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(yaml_content)

            console.print(f"[green]✓ Configuration saved to: {output}[/]")
            console.print(f"[yellow]⚠ Review and adjust the configuration before adding to your main config[/]")

    except Exception as e:
        console.print(f"[red]Error during discovery: {e}[/]")
        logger.exception("Discovery failed")


if __name__ == '__main__':
    main()
