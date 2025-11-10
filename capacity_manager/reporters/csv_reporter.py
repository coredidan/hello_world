"""CSV/Excel reporter - exports data to spreadsheet formats."""

import csv
from pathlib import Path
from typing import Optional
import pandas as pd

from ..models.analysis import CapacityReport


class CSVReporter:
    """
    Exports capacity reports to CSV/Excel.

    Independent module that only knows about data models.
    """

    def export_to_csv(self, report: CapacityReport, output_path: str) -> Path:
        """
        Export report to CSV file.

        Args:
            report: Capacity report
            output_path: Output file path

        Returns:
            Path to generated file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Write header
            writer.writerow([
                'Channel Name',
                'Type',
                'Capacity (Mbps)',
                'Traffic In (Mbps)',
                'Traffic Out (Mbps)',
                'Utilization In (%)',
                'Utilization Out (%)',
                'Max Utilization (%)',
                'Peak In (Mbps)',
                'Peak Out (Mbps)',
                'Avg In (Mbps)',
                'Avg Out (Mbps)',
                'Errors In',
                'Errors Out',
                'Status',
                'Trend',
                'Trend Rate (%/day)',
                'Days to Warning',
                'Days to Critical',
                'Site A',
                'Site B',
                'Device A',
                'Device B',
                'Description'
            ])

            # Write data
            for analysis in report.channel_analyses:
                ch = analysis.metrics.channel
                m = analysis.metrics

                status = 'CRITICAL' if analysis.is_critical else 'WARNING' if analysis.is_warning else 'NORMAL'

                writer.writerow([
                    ch.name,
                    ch.channel_type.value,
                    f"{ch.capacity_mbps:.0f}",
                    f"{m.traffic_in_mbps:.2f}",
                    f"{m.traffic_out_mbps:.2f}",
                    f"{m.utilization_in_percent:.2f}",
                    f"{m.utilization_out_percent:.2f}",
                    f"{m.max_utilization_percent:.2f}",
                    f"{m.peak_in_mbps:.2f}" if m.peak_in_mbps else '',
                    f"{m.peak_out_mbps:.2f}" if m.peak_out_mbps else '',
                    f"{m.avg_in_mbps:.2f}" if m.avg_in_mbps else '',
                    f"{m.avg_out_mbps:.2f}" if m.avg_out_mbps else '',
                    m.errors_in,
                    m.errors_out,
                    status,
                    analysis.trend_direction or '',
                    f"{analysis.trend_rate_percent:.2f}" if analysis.trend_rate_percent else '',
                    analysis.days_to_warning or '',
                    analysis.days_to_critical or '',
                    ch.site_a or '',
                    ch.site_b or '',
                    ch.device_a or '',
                    ch.device_b or '',
                    ch.description or ''
                ])

        return output_file

    def export_to_excel(self, report: CapacityReport, output_path: str) -> Path:
        """
        Export report to Excel file with multiple sheets.

        Args:
            report: Capacity report
            output_path: Output file path

        Returns:
            Path to generated file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Prepare data for DataFrame
        data = []
        for analysis in report.channel_analyses:
            ch = analysis.metrics.channel
            m = analysis.metrics

            status = 'CRITICAL' if analysis.is_critical else 'WARNING' if analysis.is_warning else 'NORMAL'

            data.append({
                'Channel Name': ch.name,
                'Type': ch.channel_type.value,
                'Capacity (Mbps)': ch.capacity_mbps,
                'Traffic In (Mbps)': m.traffic_in_mbps,
                'Traffic Out (Mbps)': m.traffic_out_mbps,
                'Utilization In (%)': m.utilization_in_percent,
                'Utilization Out (%)': m.utilization_out_percent,
                'Max Utilization (%)': m.max_utilization_percent,
                'Peak In (Mbps)': m.peak_in_mbps,
                'Peak Out (Mbps)': m.peak_out_mbps,
                'Avg In (Mbps)': m.avg_in_mbps,
                'Avg Out (Mbps)': m.avg_out_mbps,
                'Errors In': m.errors_in,
                'Errors Out': m.errors_out,
                'Status': status,
                'Trend': analysis.trend_direction,
                'Trend Rate (%/day)': analysis.trend_rate_percent,
                'Days to Warning': analysis.days_to_warning,
                'Days to Critical': analysis.days_to_critical,
                'Site A': ch.site_a,
                'Site B': ch.site_b,
                'Device A': ch.device_a,
                'Device B': ch.device_b,
                'Description': ch.description
            })

        df_all = pd.DataFrame(data)

        # Create summary DataFrame
        summary_data = {
            'Metric': [
                'Total Channels',
                'Critical Channels',
                'Warning Channels',
                'Normal Channels',
                'External Channels',
                'Transport Channels',
                'Inter-Site Channels',
                'Avg Utilization (%)',
                'Max Utilization (%)'
            ],
            'Value': [
                report.summary.total_channels,
                report.summary.critical_channels,
                report.summary.warning_channels,
                report.summary.normal_channels,
                report.summary.external_channels,
                report.summary.transport_channels,
                report.summary.inter_site_channels,
                f"{report.summary.avg_utilization_percent:.2f}",
                f"{report.summary.max_utilization_percent:.2f}"
            ]
        }
        df_summary = pd.DataFrame(summary_data)

        # Write to Excel with multiple sheets
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df_summary.to_excel(writer, sheet_name='Summary', index=False)
            df_all.to_excel(writer, sheet_name='All Channels', index=False)

            # Critical channels
            if report.get_critical_channels():
                critical_data = [d for d in data if d['Status'] == 'CRITICAL']
                pd.DataFrame(critical_data).to_excel(writer, sheet_name='Critical', index=False)

            # Warning channels
            if report.get_warning_channels():
                warning_data = [d for d in data if d['Status'] == 'WARNING']
                pd.DataFrame(warning_data).to_excel(writer, sheet_name='Warning', index=False)

        return output_file
