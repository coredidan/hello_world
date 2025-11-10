"""Cost calculation module for capacity management."""

from dataclasses import dataclass, field
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum


class PricingModel(Enum):
    """Pricing model type."""
    FLAT_RATE = "flat_rate"  # Фиксированная ставка за весь канал
    PER_MBPS = "per_mbps"  # Цена за Mbps
    TIERED = "tiered"  # Ступенчатая (скидки за объём)
    USAGE_BASED = "usage_based"  # По фактическому использованию
    BURSTABLE_95 = "burstable_95"  # Burstable billing по 95-му перцентилю


@dataclass
class ChannelPricing:
    """Pricing configuration for a channel."""

    # Базовые параметры
    pricing_model: PricingModel
    currency: str = "USD"

    # Flat rate pricing
    monthly_cost: Optional[float] = None  # Фиксированная ежемесячная стоимость

    # Per-Mbps pricing
    cost_per_mbps_month: Optional[float] = None  # Стоимость за Mbps в месяц

    # Tiered pricing (скидки за объём)
    tiers: List[Dict[str, float]] = field(default_factory=list)
    # Example: [{"up_to_mbps": 1000, "cost_per_mbps": 10}, {"up_to_mbps": 10000, "cost_per_mbps": 8}]

    # One-time costs
    setup_fee: float = 0.0  # Единовременный платёж за подключение
    upgrade_fee_percent: float = 0.0  # % от стоимости при расширении

    # Usage-based pricing
    cost_per_gb: Optional[float] = None  # Стоимость за GB трафика
    included_gb_month: float = 0.0  # Включённый трафик в месяц

    # Burstable 95th percentile pricing
    committed_rate_mbps: Optional[float] = None  # Минимальная гарантированная скорость
    burstable_rate_mbps: Optional[float] = None  # Максимальная скорость (burst limit)
    percentile_samples: List[float] = field(default_factory=list)  # Samples для расчёта 95%

    # Additional costs
    support_cost_month: float = 0.0  # Поддержка
    sla_cost_month: float = 0.0  # Расширенное SLA

    # Contract terms
    contract_term_months: int = 12  # Срок контракта
    early_termination_penalty: float = 0.0  # Штраф за досрочное расторжение

    # Notes
    notes: str = ""


@dataclass
class CostBreakdown:
    """Detailed cost breakdown."""

    # Base costs
    base_cost: float  # Базовая стоимость канала
    support_cost: float = 0.0
    sla_cost: float = 0.0

    # Usage costs
    usage_cost: float = 0.0  # Стоимость трафика (если применимо)

    # Total
    monthly_total: float = 0.0
    yearly_total: float = 0.0

    # Breakdown by components
    cost_components: Dict[str, float] = field(default_factory=dict)


@dataclass
class UpgradeCostEstimate:
    """Cost estimate for channel upgrade."""

    # Current state
    current_capacity_mbps: float
    current_monthly_cost: float

    # Proposed upgrade
    proposed_capacity_mbps: float
    proposed_monthly_cost: float

    # Costs
    one_time_costs: float  # Setup/upgrade fees
    monthly_increase: float  # Увеличение ежемесячной стоимости
    yearly_increase: float  # Годовое увеличение

    # ROI metrics
    cost_per_additional_mbps: float  # Стоимость за каждый дополнительный Mbps
    roi_months: Optional[int] = None  # Окупаемость (если применимо)

    # Savings potential
    potential_savings: Optional[float] = None  # Возможная экономия от оптимизации


@dataclass
class FinancialSummary:
    """Financial summary for all channels."""

    # Total costs
    total_monthly_cost: float
    total_yearly_cost: float

    # By channel type
    external_channels_cost: float = 0.0
    inter_site_channels_cost: float = 0.0
    transport_channels_cost: float = 0.0

    # Projected costs (with recommendations)
    projected_monthly_cost: Optional[float] = None
    projected_yearly_cost: Optional[float] = None
    projected_increase_percent: Optional[float] = None

    # Top expensive channels
    top_expensive_channels: List[Dict[str, float]] = field(default_factory=list)

    # Cost efficiency metrics
    avg_cost_per_mbps: float = 0.0
    total_capacity_mbps: float = 0.0
    total_utilization_percent: float = 0.0

    # Waste metrics
    unused_capacity_mbps: float = 0.0
    unused_capacity_cost: float = 0.0  # Деньги на неиспользуемую емкость


class CostCalculator:
    """
    Calculate costs for capacity management.

    Independent module for financial analysis.
    """

    def __init__(self, default_currency: str = "USD"):
        """
        Initialize cost calculator.

        Args:
            default_currency: Default currency code
        """
        self.default_currency = default_currency

    def calculate_channel_cost(
        self,
        capacity_mbps: float,
        pricing: ChannelPricing,
        utilization_percent: Optional[float] = None,
        traffic_gb_month: Optional[float] = None
    ) -> CostBreakdown:
        """
        Calculate cost for a channel.

        Args:
            capacity_mbps: Channel capacity in Mbps
            pricing: Pricing configuration
            utilization_percent: Current utilization percentage
            traffic_gb_month: Monthly traffic in GB (for usage-based)

        Returns:
            CostBreakdown with detailed costs
        """
        breakdown = CostBreakdown(base_cost=0.0)
        components = {}

        # Calculate base cost based on pricing model
        if pricing.pricing_model == PricingModel.FLAT_RATE:
            base_cost = pricing.monthly_cost or 0.0
            components["Flat Rate"] = base_cost

        elif pricing.pricing_model == PricingModel.PER_MBPS:
            base_cost = capacity_mbps * (pricing.cost_per_mbps_month or 0.0)
            components["Capacity Cost"] = base_cost

        elif pricing.pricing_model == PricingModel.TIERED:
            base_cost = self._calculate_tiered_cost(capacity_mbps, pricing.tiers)
            components["Tiered Capacity Cost"] = base_cost

        elif pricing.pricing_model == PricingModel.USAGE_BASED:
            # Base cost + usage overage
            base_cost = pricing.monthly_cost or 0.0
            components["Base Cost"] = base_cost

            if traffic_gb_month:
                overage_gb = max(0, traffic_gb_month - pricing.included_gb_month)
                usage_cost = overage_gb * (pricing.cost_per_gb or 0.0)
                breakdown.usage_cost = usage_cost
                components["Usage Cost"] = usage_cost

        elif pricing.pricing_model == PricingModel.BURSTABLE_95:
            # Burstable billing with 95th percentile
            # Calculate 95th percentile from samples or use current utilization
            if pricing.percentile_samples and len(pricing.percentile_samples) > 0:
                percentile_95 = self._calculate_95th_percentile(pricing.percentile_samples)
            elif utilization_percent is not None:
                # Estimate 95th percentile from current utilization
                # Assume current utilization is typical
                percentile_95 = capacity_mbps * (utilization_percent / 100.0)
            else:
                # No data - use committed rate
                percentile_95 = pricing.committed_rate_mbps or capacity_mbps

            # Billing is based on max of (committed_rate, 95th_percentile)
            billable_mbps = max(
                pricing.committed_rate_mbps or 0,
                percentile_95
            )

            # Don't exceed burstable limit
            if pricing.burstable_rate_mbps:
                billable_mbps = min(billable_mbps, pricing.burstable_rate_mbps)

            base_cost = billable_mbps * (pricing.cost_per_mbps_month or 0.0)
            components["Burstable 95th Percentile"] = base_cost
            components[f"  - Billable Rate"] = billable_mbps
            components[f"  - 95th Percentile"] = percentile_95
            if pricing.committed_rate_mbps:
                components[f"  - Committed Rate"] = pricing.committed_rate_mbps

        else:
            base_cost = 0.0

        breakdown.base_cost = base_cost

        # Additional costs
        if pricing.support_cost_month > 0:
            breakdown.support_cost = pricing.support_cost_month
            components["Support"] = pricing.support_cost_month

        if pricing.sla_cost_month > 0:
            breakdown.sla_cost = pricing.sla_cost_month
            components["SLA"] = pricing.sla_cost_month

        # Calculate totals
        breakdown.monthly_total = (
            breakdown.base_cost +
            breakdown.support_cost +
            breakdown.sla_cost +
            breakdown.usage_cost
        )
        breakdown.yearly_total = breakdown.monthly_total * 12
        breakdown.cost_components = components

        return breakdown

    def estimate_upgrade_cost(
        self,
        current_capacity_mbps: float,
        proposed_capacity_mbps: float,
        pricing: ChannelPricing,
        current_cost: Optional[CostBreakdown] = None
    ) -> UpgradeCostEstimate:
        """
        Estimate cost of upgrading a channel.

        Args:
            current_capacity_mbps: Current capacity
            proposed_capacity_mbps: Proposed new capacity
            pricing: Pricing configuration
            current_cost: Current cost breakdown (optional)

        Returns:
            UpgradeCostEstimate with cost analysis
        """
        # Calculate current cost if not provided
        if current_cost is None:
            current_cost = self.calculate_channel_cost(current_capacity_mbps, pricing)

        # Calculate proposed cost
        proposed_cost = self.calculate_channel_cost(proposed_capacity_mbps, pricing)

        # Calculate one-time costs
        one_time_costs = pricing.setup_fee
        if pricing.upgrade_fee_percent > 0:
            upgrade_value = proposed_cost.monthly_total - current_cost.monthly_total
            one_time_costs += upgrade_value * (pricing.upgrade_fee_percent / 100)

        # Calculate increases
        monthly_increase = proposed_cost.monthly_total - current_cost.monthly_total
        yearly_increase = monthly_increase * 12

        # Cost per additional Mbps
        capacity_increase = proposed_capacity_mbps - current_capacity_mbps
        cost_per_additional_mbps = monthly_increase / capacity_increase if capacity_increase > 0 else 0

        return UpgradeCostEstimate(
            current_capacity_mbps=current_capacity_mbps,
            current_monthly_cost=current_cost.monthly_total,
            proposed_capacity_mbps=proposed_capacity_mbps,
            proposed_monthly_cost=proposed_cost.monthly_total,
            one_time_costs=one_time_costs,
            monthly_increase=monthly_increase,
            yearly_increase=yearly_increase,
            cost_per_additional_mbps=cost_per_additional_mbps
        )

    def calculate_financial_summary(
        self,
        channels_with_costs: List[tuple]  # List of (channel, cost_breakdown, channel_type)
    ) -> FinancialSummary:
        """
        Calculate financial summary for all channels.

        Args:
            channels_with_costs: List of tuples (channel, cost_breakdown, channel_type)

        Returns:
            FinancialSummary with aggregate financial data
        """
        from ..models.channel import ChannelType

        total_monthly = 0.0
        by_type = {
            ChannelType.EXTERNAL: 0.0,
            ChannelType.INTER_SITE: 0.0,
            ChannelType.TRANSPORT: 0.0
        }
        total_capacity = 0.0
        total_utilization = 0.0
        expensive_channels = []

        for channel, cost, channel_type in channels_with_costs:
            monthly_cost = cost.monthly_total
            total_monthly += monthly_cost

            # By type
            if channel_type in by_type:
                by_type[channel_type] += monthly_cost

            # Capacity
            capacity = getattr(channel, 'capacity_mbps', 0)
            total_capacity += capacity

            # Utilization
            utilization = getattr(channel, 'max_utilization_percent', 0)
            total_utilization += utilization

            # Track expensive channels
            expensive_channels.append({
                'name': getattr(channel, 'name', 'Unknown'),
                'cost': monthly_cost,
                'capacity': capacity,
                'cost_per_mbps': monthly_cost / capacity if capacity > 0 else 0
            })

        # Sort and get top expensive
        expensive_channels.sort(key=lambda x: x['cost'], reverse=True)
        top_expensive = expensive_channels[:10]

        # Calculate averages
        num_channels = len(channels_with_costs)
        avg_utilization = total_utilization / num_channels if num_channels > 0 else 0
        avg_cost_per_mbps = total_monthly / total_capacity if total_capacity > 0 else 0

        # Calculate waste
        unused_capacity = total_capacity * (1 - avg_utilization / 100)
        unused_cost = unused_capacity * avg_cost_per_mbps

        return FinancialSummary(
            total_monthly_cost=total_monthly,
            total_yearly_cost=total_monthly * 12,
            external_channels_cost=by_type.get(ChannelType.EXTERNAL, 0),
            inter_site_channels_cost=by_type.get(ChannelType.INTER_SITE, 0),
            transport_channels_cost=by_type.get(ChannelType.TRANSPORT, 0),
            top_expensive_channels=top_expensive,
            avg_cost_per_mbps=avg_cost_per_mbps,
            total_capacity_mbps=total_capacity,
            total_utilization_percent=avg_utilization,
            unused_capacity_mbps=unused_capacity,
            unused_capacity_cost=unused_cost
        )

    def _calculate_tiered_cost(
        self,
        capacity_mbps: float,
        tiers: List[Dict[str, float]]
    ) -> float:
        """Calculate cost using tiered pricing."""
        if not tiers:
            return 0.0

        # Sort tiers by capacity
        sorted_tiers = sorted(tiers, key=lambda t: t.get('up_to_mbps', 0))

        total_cost = 0.0
        remaining_capacity = capacity_mbps

        for tier in sorted_tiers:
            tier_limit = tier.get('up_to_mbps', float('inf'))
            tier_price = tier.get('cost_per_mbps', 0)

            if remaining_capacity <= 0:
                break

            # Calculate how much capacity falls into this tier
            capacity_in_tier = min(remaining_capacity, tier_limit)
            total_cost += capacity_in_tier * tier_price
            remaining_capacity -= capacity_in_tier

        # If capacity exceeds all tiers, use last tier price
        if remaining_capacity > 0 and sorted_tiers:
            last_tier_price = sorted_tiers[-1].get('cost_per_mbps', 0)
            total_cost += remaining_capacity * last_tier_price

        return total_cost

    def calculate_roi(
        self,
        investment: float,
        monthly_savings: float
    ) -> int:
        """
        Calculate ROI in months.

        Args:
            investment: One-time investment cost
            monthly_savings: Monthly cost savings

        Returns:
            Number of months to break even
        """
        if monthly_savings <= 0:
            return 0

        return int(investment / monthly_savings)

    def _calculate_95th_percentile(self, samples: List[float]) -> float:
        """
        Calculate 95th percentile from utilization samples.

        Args:
            samples: List of utilization measurements (in Mbps)

        Returns:
            95th percentile value

        This is the standard burstable billing method:
        - Take all samples for the billing period (usually 5-min intervals for a month)
        - Sort them
        - Discard top 5%
        - Bill based on the highest remaining value
        """
        if not samples:
            return 0.0

        # Sort samples
        sorted_samples = sorted(samples)

        # Calculate 95th percentile index
        # We want to discard top 5%, so we take value at 95% position
        percentile_index = int(len(sorted_samples) * 0.95)

        # Handle edge case
        if percentile_index >= len(sorted_samples):
            percentile_index = len(sorted_samples) - 1

        return sorted_samples[percentile_index]

    def format_currency(
        self,
        amount: float,
        currency: Optional[str] = None
    ) -> str:
        """
        Format amount as currency string.

        Args:
            amount: Amount to format
            currency: Currency code (uses default if None)

        Returns:
            Formatted currency string
        """
        curr = currency or self.default_currency

        # Simple formatting
        if curr == "USD":
            return f"${amount:,.2f}"
        elif curr == "EUR":
            return f"€{amount:,.2f}"
        elif curr == "RUB":
            return f"₽{amount:,.2f}"
        else:
            return f"{amount:,.2f} {curr}"
