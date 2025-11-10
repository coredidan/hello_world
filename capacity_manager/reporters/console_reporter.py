"""Console reporter - outputs beautiful tables to console using Rich."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from typing import List

from ..models.analysis import CapacityReport, ChannelAnalysis
from ..models.channel import UtilizationLevel, ChannelType


class ConsoleReporter:
    """
    Generates console reports using Rich library.

    Independent module that only knows about data models.
    """

    def __init__(self, console: Console = None):
        """
        Initialize console reporter.

        Args:
            console: Rich Console instance (creates new if None)
        """
        self.console = console or Console()

    def print_report(self, report: CapacityReport, show_details: bool = True):
        """
        Print complete capacity report to console.

        Args:
            report: Capacity report to print
            show_details: Whether to show detailed channel info
        """
        # Print header
        self._print_header(report)

        # Print summary
        self._print_summary(report)

        # Print critical channels
        if report.get_critical_channels():
            self._print_critical_channels(report.get_critical_channels())

        # Print warning channels
        if report.get_warning_channels():
            self._print_warning_channels(report.get_warning_channels())

        # Print top utilized channels
        if show_details:
            self._print_top_channels(report)

        # Print by type breakdown
        if show_details:
            self._print_by_type(report)

    def _print_header(self, report: CapacityReport):
        """Print report header."""
        title = Text("CAPACITY MANAGEMENT REPORT", style="bold white on blue")
        subtitle = (
            f"Period: {report.period_start.strftime('%Y-%m-%d %H:%M')} - "
            f"{report.period_end.strftime('%Y-%m-%d %H:%M')}\n"
            f"Generated: {report.report_date.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        panel = Panel(
            subtitle,
            title=title,
            border_style="blue",
            padding=(1, 2)
        )
        self.console.print(panel)
        self.console.print()

    def _print_summary(self, report: CapacityReport):
        """Print summary statistics."""
        summary = report.summary

        table = Table(title="📊 Summary Statistics", box=box.ROUNDED)
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", justify="right", style="white")

        table.add_row("Total Channels", str(summary.total_channels))
        table.add_row(
            "Critical Channels",
            f"[bold red]{summary.critical_channels}[/] ({summary.critical_percent:.1f}%)"
        )
        table.add_row(
            "Warning Channels",
            f"[bold yellow]{summary.warning_channels}[/] ({summary.warning_percent:.1f}%)"
        )
        table.add_row(
            "Normal Channels",
            f"[green]{summary.normal_channels}[/]"
        )
        table.add_row("", "")  # Separator
        table.add_row("External Channels", str(summary.external_channels))
        table.add_row("Transport Channels", str(summary.transport_channels))
        table.add_row("Inter-Site Channels", str(summary.inter_site_channels))
        table.add_row("", "")  # Separator
        table.add_row("Avg Utilization", f"{summary.avg_utilization_percent:.1f}%")
        table.add_row("Max Utilization", f"{summary.max_utilization_percent:.1f}%")

        self.console.print(table)
        self.console.print()

    def _print_critical_channels(self, channels: List[ChannelAnalysis]):
        """Print critical channels."""
        table = Table(
            title="🚨 CRITICAL CHANNELS (>85% utilization)",
            box=box.HEAVY,
            border_style="red"
        )

        table.add_column("Channel", style="white", no_wrap=False)
        table.add_column("Type", style="cyan")
        table.add_column("Capacity", justify="right")
        table.add_column("Utilization", justify="right")
        table.add_column("In/Out", justify="right")

        for analysis in channels:
            ch = analysis.metrics.channel
            m = analysis.metrics

            table.add_row(
                ch.name,
                ch.channel_type.value,
                f"{ch.capacity_mbps:.0f} Mbps",
                f"[bold red]{m.max_utilization_percent:.1f}%[/]",
                f"{m.utilization_in_percent:.1f}% / {m.utilization_out_percent:.1f}%"
            )

        self.console.print(table)
        self.console.print()

    def _print_warning_channels(self, channels: List[ChannelAnalysis]):
        """Print warning channels."""
        table = Table(
            title="⚠️  WARNING CHANNELS (70-85% utilization)",
            box=box.ROUNDED,
            border_style="yellow"
        )

        table.add_column("Channel", style="white", no_wrap=False)
        table.add_column("Type", style="cyan")
        table.add_column("Capacity", justify="right")
        table.add_column("Utilization", justify="right")
        table.add_column("Trend", justify="center")

        for analysis in channels:
            ch = analysis.metrics.channel
            m = analysis.metrics

            trend_icon = self._get_trend_icon(analysis.trend_direction)

            table.add_row(
                ch.name,
                ch.channel_type.value,
                f"{ch.capacity_mbps:.0f} Mbps",
                f"[bold yellow]{m.max_utilization_percent:.1f}%[/]",
                trend_icon
            )

        self.console.print(table)
        self.console.print()

    def _print_top_channels(self, report: CapacityReport):
        """Print top utilized channels."""
        top_channels = report.get_top_utilized(limit=10)

        table = Table(title="📈 Top 10 Most Utilized Channels", box=box.SIMPLE)

        table.add_column("#", justify="right", style="dim")
        table.add_column("Channel", style="white")
        table.add_column("Type", style="cyan")
        table.add_column("Utilization", justify="right")
        table.add_column("Traffic", justify="right", style="blue")
        table.add_column("Status", justify="center")

        for idx, analysis in enumerate(top_channels, 1):
            ch = analysis.metrics.channel
            m = analysis.metrics

            util_color = self._get_util_color(m.max_utilization_percent)
            status_icon = self._get_status_icon(analysis)

            table.add_row(
                str(idx),
                ch.name,
                ch.channel_type.value,
                f"[{util_color}]{m.max_utilization_percent:.1f}%[/]",
                f"{m.traffic_in_mbps:.1f} / {m.traffic_out_mbps:.1f} Mbps",
                status_icon
            )

        self.console.print(table)
        self.console.print()

    def _print_by_type(self, report: CapacityReport):
        """Print breakdown by channel type."""
        self.console.print("[bold]Breakdown by Channel Type:[/]")
        self.console.print()

        for channel_type in [ChannelType.EXTERNAL, ChannelType.INTER_SITE, ChannelType.TRANSPORT]:
            channels = report.get_channels_by_type(channel_type)
            if not channels:
                continue

            type_name = channel_type.value.replace('_', ' ').title()
            critical = sum(1 for c in channels if c.is_critical)
            warning = sum(1 for c in channels if c.is_warning)
            avg_util = sum(c.metrics.max_utilization_percent for c in channels) / len(channels)

            self.console.print(
                f"  [cyan]{type_name}[/]: {len(channels)} channels | "
                f"Avg: {avg_util:.1f}% | "
                f"[red]Critical: {critical}[/] | "
                f"[yellow]Warning: {warning}[/]"
            )

        self.console.print()

    def print_channel_details(self, analysis: ChannelAnalysis):
        """Print detailed information for a single channel."""
        ch = analysis.metrics.channel
        m = analysis.metrics

        # Create details table
        table = Table(title=f"Channel Details: {ch.name}", box=box.DOUBLE_EDGE)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Type", ch.channel_type.value)
        table.add_row("Capacity", f"{ch.capacity_mbps} Mbps")
        if ch.description:
            table.add_row("Description", ch.description)
        if ch.site_a:
            table.add_row("Site A", ch.site_a)
        if ch.site_b:
            table.add_row("Site B", ch.site_b)

        table.add_row("", "")
        table.add_row("Current Utilization", f"{m.max_utilization_percent:.1f}%")
        table.add_row("Traffic In", f"{m.traffic_in_mbps:.1f} Mbps ({m.utilization_in_percent:.1f}%)")
        table.add_row("Traffic Out", f"{m.traffic_out_mbps:.1f} Mbps ({m.utilization_out_percent:.1f}%)")

        if m.peak_in_mbps:
            table.add_row("Peak In", f"{m.peak_in_mbps:.1f} Mbps")
        if m.peak_out_mbps:
            table.add_row("Peak Out", f"{m.peak_out_mbps:.1f} Mbps")

        if analysis.trend_direction:
            table.add_row("Trend", f"{analysis.trend_direction} ({analysis.trend_rate_percent:.2f}%/day)")

        self.console.print(table)
        self.console.print()

        # Print recommendations
        if analysis.recommendations:
            self.console.print("[bold]Recommendations:[/]")
            for rec in analysis.recommendations:
                self.console.print(f"  • {rec}")
            self.console.print()

    def _get_util_color(self, utilization: float) -> str:
        """Get color for utilization percentage."""
        if utilization >= 85:
            return "red"
        elif utilization >= 70:
            return "yellow"
        else:
            return "green"

    def _get_status_icon(self, analysis: ChannelAnalysis) -> str:
        """Get status icon for analysis."""
        if analysis.is_critical:
            return "[red]🚨[/]"
        elif analysis.is_warning:
            return "[yellow]⚠️ [/]"
        else:
            return "[green]✅[/]"

    def _get_trend_icon(self, trend: str) -> str:
        """Get trend icon."""
        if trend == "increasing":
            return "📈"
        elif trend == "decreasing":
            return "📉"
        else:
            return "➡️ "
