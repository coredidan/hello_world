"""HTML reporter - generates HTML capacity reports."""

from pathlib import Path
from datetime import datetime
from jinja2 import Template

from ..models.analysis import CapacityReport


class HTMLReporter:
    """
    Generates HTML capacity reports.

    Independent module that only knows about data models.
    """

    def __init__(self):
        """Initialize HTML reporter."""
        self.template = self._get_template()

    def generate_report(self, report: CapacityReport, output_path: str) -> Path:
        """
        Generate HTML report and save to file.

        Args:
            report: Capacity report
            output_path: Output file path

        Returns:
            Path to generated file
        """
        html_content = self.template.render(
            report=report,
            critical_channels=report.get_critical_channels(),
            warning_channels=report.get_warning_channels(),
            top_channels=report.get_top_utilized(limit=20),
            generation_time=datetime.now()
        )

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return output_file

    def _get_template(self) -> Template:
        """Get Jinja2 template for HTML report."""
        template_str = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Capacity Management Report</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #f5f7fa;
            color: #2c3e50;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header p { opacity: 0.9; font-size: 1.1em; }

        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .summary-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .summary-card h3 {
            color: #7f8c8d;
            font-size: 0.9em;
            text-transform: uppercase;
            margin-bottom: 10px;
        }
        .summary-card .value {
            font-size: 2.5em;
            font-weight: bold;
            color: #2c3e50;
        }
        .summary-card.critical .value { color: #e74c3c; }
        .summary-card.warning .value { color: #f39c12; }
        .summary-card.normal .value { color: #27ae60; }

        .section {
            background: white;
            border-radius: 8px;
            padding: 25px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .section h2 {
            font-size: 1.8em;
            margin-bottom: 20px;
            color: #2c3e50;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 10px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ecf0f1;
        }
        th {
            background: #f8f9fa;
            font-weight: 600;
            color: #2c3e50;
            text-transform: uppercase;
            font-size: 0.85em;
        }
        tr:hover { background: #f8f9fa; }

        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }
        .badge-critical { background: #fee; color: #e74c3c; }
        .badge-warning { background: #fff3cd; color: #f39c12; }
        .badge-normal { background: #d4edda; color: #27ae60; }

        .util-bar {
            width: 100px;
            height: 8px;
            background: #ecf0f1;
            border-radius: 4px;
            overflow: hidden;
        }
        .util-fill {
            height: 100%;
            transition: width 0.3s ease;
        }
        .util-normal { background: #27ae60; }
        .util-warning { background: #f39c12; }
        .util-critical { background: #e74c3c; }

        .footer {
            text-align: center;
            padding: 20px;
            color: #7f8c8d;
            font-size: 0.9em;
        }

        @media print {
            body { background: white; }
            .section { box-shadow: none; border: 1px solid #ddd; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Capacity Management Report</h1>
            <p>
                Period: {{ report.period_start.strftime('%Y-%m-%d %H:%M') }} - {{ report.period_end.strftime('%Y-%m-%d %H:%M') }}<br>
                Generated: {{ generation_time.strftime('%Y-%m-%d %H:%M:%S') }}
            </p>
        </div>

        <div class="summary">
            <div class="summary-card">
                <h3>Total Channels</h3>
                <div class="value">{{ report.summary.total_channels }}</div>
            </div>
            <div class="summary-card critical">
                <h3>Critical</h3>
                <div class="value">{{ report.summary.critical_channels }}</div>
                <small>{{ "%.1f"|format(report.summary.critical_percent) }}%</small>
            </div>
            <div class="summary-card warning">
                <h3>Warning</h3>
                <div class="value">{{ report.summary.warning_channels }}</div>
                <small>{{ "%.1f"|format(report.summary.warning_percent) }}%</small>
            </div>
            <div class="summary-card normal">
                <h3>Normal</h3>
                <div class="value">{{ report.summary.normal_channels }}</div>
            </div>
            <div class="summary-card">
                <h3>Avg Utilization</h3>
                <div class="value">{{ "%.1f"|format(report.summary.avg_utilization_percent) }}%</div>
            </div>
            <div class="summary-card">
                <h3>Max Utilization</h3>
                <div class="value">{{ "%.1f"|format(report.summary.max_utilization_percent) }}%</div>
            </div>
        </div>

        {% if critical_channels %}
        <div class="section">
            <h2>🚨 Critical Channels</h2>
            <table>
                <thead>
                    <tr>
                        <th>Channel Name</th>
                        <th>Type</th>
                        <th>Capacity</th>
                        <th>Utilization</th>
                        <th>Traffic In/Out</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% for analysis in critical_channels %}
                    <tr>
                        <td><strong>{{ analysis.metrics.channel.name }}</strong></td>
                        <td>{{ analysis.metrics.channel.channel_type.value }}</td>
                        <td>{{ "%.0f"|format(analysis.metrics.channel.capacity_mbps) }} Mbps</td>
                        <td>
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <strong>{{ "%.1f"|format(analysis.metrics.max_utilization_percent) }}%</strong>
                                <div class="util-bar">
                                    <div class="util-fill util-critical" style="width: {{ analysis.metrics.max_utilization_percent }}%"></div>
                                </div>
                            </div>
                        </td>
                        <td>{{ "%.1f"|format(analysis.metrics.traffic_in_mbps) }} / {{ "%.1f"|format(analysis.metrics.traffic_out_mbps) }} Mbps</td>
                        <td><span class="badge badge-critical">CRITICAL</span></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% endif %}

        {% if warning_channels %}
        <div class="section">
            <h2>⚠️ Warning Channels</h2>
            <table>
                <thead>
                    <tr>
                        <th>Channel Name</th>
                        <th>Type</th>
                        <th>Capacity</th>
                        <th>Utilization</th>
                        <th>Trend</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% for analysis in warning_channels %}
                    <tr>
                        <td><strong>{{ analysis.metrics.channel.name }}</strong></td>
                        <td>{{ analysis.metrics.channel.channel_type.value }}</td>
                        <td>{{ "%.0f"|format(analysis.metrics.channel.capacity_mbps) }} Mbps</td>
                        <td>
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <strong>{{ "%.1f"|format(analysis.metrics.max_utilization_percent) }}%</strong>
                                <div class="util-bar">
                                    <div class="util-fill util-warning" style="width: {{ analysis.metrics.max_utilization_percent }}%"></div>
                                </div>
                            </div>
                        </td>
                        <td>{{ analysis.trend_direction or 'N/A' }}</td>
                        <td><span class="badge badge-warning">WARNING</span></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% endif %}

        <div class="section">
            <h2>📈 Top Utilized Channels</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Channel Name</th>
                        <th>Type</th>
                        <th>Capacity</th>
                        <th>Utilization</th>
                        <th>Traffic</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% for analysis in top_channels %}
                    <tr>
                        <td>{{ loop.index }}</td>
                        <td><strong>{{ analysis.metrics.channel.name }}</strong></td>
                        <td>{{ analysis.metrics.channel.channel_type.value }}</td>
                        <td>{{ "%.0f"|format(analysis.metrics.channel.capacity_mbps) }} Mbps</td>
                        <td>
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <strong>{{ "%.1f"|format(analysis.metrics.max_utilization_percent) }}%</strong>
                                <div class="util-bar">
                                    {% if analysis.metrics.max_utilization_percent >= 85 %}
                                    <div class="util-fill util-critical" style="width: {{ analysis.metrics.max_utilization_percent }}%"></div>
                                    {% elif analysis.metrics.max_utilization_percent >= 70 %}
                                    <div class="util-fill util-warning" style="width: {{ analysis.metrics.max_utilization_percent }}%"></div>
                                    {% else %}
                                    <div class="util-fill util-normal" style="width: {{ analysis.metrics.max_utilization_percent }}%"></div>
                                    {% endif %}
                                </div>
                            </div>
                        </td>
                        <td>{{ "%.1f"|format(analysis.metrics.traffic_in_mbps) }} / {{ "%.1f"|format(analysis.metrics.traffic_out_mbps) }} Mbps</td>
                        <td>
                            {% if analysis.is_critical %}
                            <span class="badge badge-critical">CRITICAL</span>
                            {% elif analysis.is_warning %}
                            <span class="badge badge-warning">WARNING</span>
                            {% else %}
                            <span class="badge badge-normal">NORMAL</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p>Generated by Capacity Manager v{{ report.version }}</p>
        </div>
    </div>
</body>
</html>
        """
        return Template(template_str)
