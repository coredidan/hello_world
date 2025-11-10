"""Recommendations engine - generates actionable insights."""

from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

from ..models.channel import ChannelMetrics, ChannelType, UtilizationLevel
from ..forecasting.predictor import ForecastResult


class RecommendationPriority(Enum):
    """Priority level for recommendations."""
    CRITICAL = "critical"  # Immediate action required
    HIGH = "high"  # Action needed soon
    MEDIUM = "medium"  # Plan for action
    LOW = "low"  # Monitor


class RecommendationType(Enum):
    """Type of recommendation."""
    UPGRADE_CAPACITY = "upgrade_capacity"
    OPTIMIZE_TRAFFIC = "optimize_traffic"
    INVESTIGATE_ERRORS = "investigate_errors"
    MONITOR = "monitor"
    IMPLEMENT_QOS = "implement_qos"
    ADD_REDUNDANCY = "add_redundancy"
    BALANCE_LOAD = "balance_load"


@dataclass
class Recommendation:
    """A single actionable recommendation."""

    priority: RecommendationPriority
    type: RecommendationType
    title: str
    description: str
    action_items: List[str]

    # Timeline
    timeline_weeks: Optional[int] = None  # Recommended timeline in weeks

    # Impact
    estimated_cost: Optional[str] = None  # "low", "medium", "high"
    business_impact: Optional[str] = None

    # Technical details
    technical_notes: List[str] = None

    def __post_init__(self):
        if self.technical_notes is None:
            self.technical_notes = []


class RecommendationEngine:
    """
    Generates intelligent recommendations for capacity management.

    Independent module that analyzes metrics and forecasts to provide
    actionable business recommendations.
    """

    def __init__(
        self,
        warning_threshold: float = 70.0,
        critical_threshold: float = 85.0
    ):
        """
        Initialize recommendation engine.

        Args:
            warning_threshold: Warning threshold percentage
            critical_threshold: Critical threshold percentage
        """
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

    def generate_recommendations(
        self,
        metrics: ChannelMetrics,
        forecast: Optional[ForecastResult] = None
    ) -> List[Recommendation]:
        """
        Generate recommendations for a channel.

        Args:
            metrics: Current channel metrics
            forecast: Forecast results (optional)

        Returns:
            List of recommendations, sorted by priority
        """
        recommendations = []

        # Critical utilization recommendations
        if metrics.max_utilization_percent >= self.critical_threshold:
            recommendations.extend(
                self._critical_utilization_recommendations(metrics, forecast)
            )

        # Warning level recommendations
        elif metrics.max_utilization_percent >= self.warning_threshold:
            recommendations.extend(
                self._warning_utilization_recommendations(metrics, forecast)
            )

        # Error-based recommendations
        if metrics.errors_in > 0 or metrics.errors_out > 0:
            recommendations.extend(
                self._error_recommendations(metrics)
            )

        # Traffic pattern recommendations
        recommendations.extend(
            self._traffic_pattern_recommendations(metrics)
        )

        # Forecast-based recommendations
        if forecast:
            recommendations.extend(
                self._forecast_based_recommendations(metrics, forecast)
            )

        # Channel type specific recommendations
        recommendations.extend(
            self._channel_type_recommendations(metrics)
        )

        # Sort by priority
        priority_order = {
            RecommendationPriority.CRITICAL: 0,
            RecommendationPriority.HIGH: 1,
            RecommendationPriority.MEDIUM: 2,
            RecommendationPriority.LOW: 3
        }
        recommendations.sort(key=lambda r: priority_order[r.priority])

        return recommendations

    def _critical_utilization_recommendations(
        self,
        metrics: ChannelMetrics,
        forecast: Optional[ForecastResult]
    ) -> List[Recommendation]:
        """Generate recommendations for critical utilization."""
        recs = []

        # Immediate capacity upgrade
        rec = Recommendation(
            priority=RecommendationPriority.CRITICAL,
            type=RecommendationType.UPGRADE_CAPACITY,
            title=f"Немедленное расширение канала {metrics.channel.name}",
            description=(
                f"Канал загружен на {metrics.max_utilization_percent:.1f}%, "
                f"что превышает критический порог {self.critical_threshold}%. "
                "Высокий риск перегрузки и деградации сервиса."
            ),
            action_items=[
                "Срочно согласовать расширение пропускной способности с провайдером",
                f"Текущая емкость: {metrics.channel.capacity_mbps} Mbps",
                f"Рекомендуемая емкость: {self._calculate_recommended_capacity(metrics)} Mbps",
                "Подготовить технико-коммерческое предложение для руководства",
                "Установить срок реализации: 1-2 недели"
            ],
            timeline_weeks=2,
            estimated_cost=self._estimate_upgrade_cost(metrics),
            business_impact=(
                "КРИТИЧНО: Риск потери клиентов из-за деградации качества сервиса. "
                "Возможны штрафы по SLA."
            ),
            technical_notes=[
                f"Пиковая нагрузка IN: {metrics.peak_in_mbps:.1f} Mbps",
                f"Пиковая нагрузка OUT: {metrics.peak_out_mbps:.1f} Mbps",
                f"Средняя нагрузка: {(metrics.avg_in_mbps + metrics.avg_out_mbps) / 2:.1f} Mbps"
            ]
        )
        recs.append(rec)

        # Immediate traffic optimization
        rec = Recommendation(
            priority=RecommendationPriority.CRITICAL,
            type=RecommendationType.OPTIMIZE_TRAFFIC,
            title="Немедленная оптимизация трафика",
            description="До расширения канала необходимо оптимизировать текущий трафик",
            action_items=[
                "Проанализировать топ-потребителей трафика",
                "Внедрить/скорректировать политики QoS",
                "Рассмотреть возможность temporary traffic shaping",
                "Проверить наличие аномального трафика",
                "Оценить возможность переноса некритичного трафика на другие каналы"
            ],
            timeline_weeks=1,
            estimated_cost="low",
            business_impact="Временная мера для предотвращения немедленной перегрузки"
        )
        recs.append(rec)

        return recs

    def _warning_utilization_recommendations(
        self,
        metrics: ChannelMetrics,
        forecast: Optional[ForecastResult]
    ) -> List[Recommendation]:
        """Generate recommendations for warning level utilization."""
        recs = []

        # Determine timeline based on forecast
        timeline_weeks = 8  # Default
        if forecast and forecast.days_to_critical:
            if forecast.days_to_critical < 30:
                timeline_weeks = 4
            elif forecast.days_to_critical < 60:
                timeline_weeks = 6

        rec = Recommendation(
            priority=RecommendationPriority.HIGH,
            type=RecommendationType.UPGRADE_CAPACITY,
            title=f"Планирование расширения канала {metrics.channel.name}",
            description=(
                f"Канал загружен на {metrics.max_utilization_percent:.1f}%. "
                "Рекомендуется запланировать расширение пропускной способности."
            ),
            action_items=[
                "Инициировать процесс планирования расширения",
                f"Целевая емкость: {self._calculate_recommended_capacity(metrics)} Mbps",
                "Получить коммерческие предложения от провайдеров",
                "Запланировать бюджет на следующий квартал",
                f"Рекомендуемый срок реализации: {timeline_weeks} недель"
            ],
            timeline_weeks=timeline_weeks,
            estimated_cost=self._estimate_upgrade_cost(metrics),
            business_impact=(
                "ВЫСОКИЙ: Без расширения возможна деградация качества "
                "в ближайшие 1-2 месяца."
            )
        )
        recs.append(rec)

        # Monitoring recommendation
        rec = Recommendation(
            priority=RecommendationPriority.MEDIUM,
            type=RecommendationType.MONITOR,
            title="Усиленный мониторинг канала",
            description="Установить дополнительные точки контроля",
            action_items=[
                "Настроить ежедневные уведомления о загрузке",
                "Добавить канал в список критичных для мониторинга",
                "Создать dashboard для руководства",
                "Установить alert при превышении 80%"
            ],
            timeline_weeks=1,
            estimated_cost="low"
        )
        recs.append(rec)

        return recs

    def _error_recommendations(self, metrics: ChannelMetrics) -> List[Recommendation]:
        """Generate recommendations based on error rates."""
        recs = []

        total_errors = metrics.errors_in + metrics.errors_out

        if total_errors > 100:  # Significant error count
            rec = Recommendation(
                priority=RecommendationPriority.HIGH,
                type=RecommendationType.INVESTIGATE_ERRORS,
                title="Расследование ошибок на канале",
                description=(
                    f"Обнаружено {total_errors} ошибок "
                    f"(IN: {metrics.errors_in}, OUT: {metrics.errors_out}). "
                    "Требуется техническое расследование."
                ),
                action_items=[
                    "Проверить физическое состояние линии",
                    "Проанализировать логи оборудования",
                    "Проверить уровень сигнала (для оптики)",
                    "Связаться с провайдером для диагностики",
                    "Рассмотреть необходимость замены оборудования/кабеля"
                ],
                timeline_weeks=2,
                estimated_cost="medium",
                business_impact="Ошибки могут привести к потере пакетов и деградации сервиса",
                technical_notes=[
                    f"Errors IN: {metrics.errors_in}",
                    f"Errors OUT: {metrics.errors_out}",
                    "Рекомендуется детальный анализ типов ошибок"
                ]
            )
            recs.append(rec)

        return recs

    def _traffic_pattern_recommendations(
        self,
        metrics: ChannelMetrics
    ) -> List[Recommendation]:
        """Generate recommendations based on traffic patterns."""
        recs = []

        # Check for asymmetric traffic
        util_diff = abs(metrics.utilization_in_percent - metrics.utilization_out_percent)

        if util_diff > 40:
            direction = "входящего" if metrics.utilization_in_percent > metrics.utilization_out_percent else "исходящего"

            rec = Recommendation(
                priority=RecommendationPriority.MEDIUM,
                type=RecommendationType.OPTIMIZE_TRAFFIC,
                title="Анализ асимметричного трафика",
                description=(
                    f"Значительная разница между входящим ({metrics.utilization_in_percent:.1f}%) "
                    f"и исходящим ({metrics.utilization_out_percent:.1f}%) трафиком."
                ),
                action_items=[
                    f"Проанализировать источники {direction} трафика",
                    "Проверить корректность work балансировки нагрузки",
                    "Оценить возможность оптимизации маршрутизации",
                    "Рассмотреть внедрение кэширования (для входящего трафика)",
                    "Проверить наличие аномалий или DDoS атак"
                ],
                timeline_weeks=3,
                estimated_cost="low",
                technical_notes=[
                    f"Utilization IN: {metrics.utilization_in_percent:.1f}%",
                    f"Utilization OUT: {metrics.utilization_out_percent:.1f}%",
                    f"Разница: {util_diff:.1f}%"
                ]
            )
            recs.append(rec)

        return recs

    def _forecast_based_recommendations(
        self,
        metrics: ChannelMetrics,
        forecast: ForecastResult
    ) -> List[Recommendation]:
        """Generate recommendations based on forecast."""
        recs = []

        # Accelerating growth warning
        if forecast.is_accelerating:
            rec = Recommendation(
                priority=RecommendationPriority.HIGH,
                type=RecommendationType.UPGRADE_CAPACITY,
                title="Ускоряющийся рост загрузки",
                description=(
                    "Обнаружено ускорение роста загрузки канала. "
                    "Стандартные прогнозы могут быть неточны."
                ),
                action_items=[
                    "Провести детальный анализ причин ускоренного роста",
                    "Скорректировать планы расширения с учетом ускорения",
                    "Рассмотреть поэтапное расширение емкости",
                    "Установить более частый мониторинг (ежедневно)",
                    "Подготовить план быстрого реагирования"
                ],
                timeline_weeks=4,
                estimated_cost="high",
                business_impact=(
                    "Ускоренный рост может привести к более быстрому достижению "
                    "критических порогов, чем ожидалось."
                ),
                technical_notes=[
                    f"Уверенность прогноза: {forecast.forecast_confidence:.1%}",
                    f"Сила тренда: {forecast.trend_strength:.1%}"
                ]
            )
            recs.append(rec)

        # Near-term critical threshold crossing
        if forecast.days_to_critical and forecast.days_to_critical < 30:
            rec = Recommendation(
                priority=RecommendationPriority.CRITICAL,
                type=RecommendationType.UPGRADE_CAPACITY,
                title=f"Критический порог будет достигнут через {forecast.days_to_critical} дней",
                description=(
                    "По прогнозам, критический уровень загрузки будет достигнут "
                    "в ближайшее время."
                ),
                action_items=[
                    "СРОЧНО: Ускорить процесс расширения канала",
                    "Рассмотреть временные меры (traffic shaping, QoS)",
                    "Подготовить план действий на случай перегрузки",
                    "Информировать руководство о критической ситуации",
                    "Рассмотреть аренду временного резервного канала"
                ],
                timeline_weeks=2,
                estimated_cost="high",
                business_impact="КРИТИЧНО: Высокий риск перегрузки в ближайшее время"
            )
            recs.append(rec)

        # Seasonal pattern detected
        if forecast.seasonal_pattern:
            rec = Recommendation(
                priority=RecommendationPriority.LOW,
                type=RecommendationType.MONITOR,
                title=f"Обнаружена сезонная модель: {forecast.seasonal_pattern}",
                description="Загрузка канала следует предсказуемому паттерну",
                action_items=[
                    "Использовать сезонность для планирования работ",
                    "Планировать обслуживание в периоды низкой нагрузки",
                    "Оптимизировать backup операции с учетом сезонности",
                    "Учитывать паттерн при планировании расширения"
                ],
                timeline_weeks=None,
                estimated_cost="low",
                technical_notes=[
                    f"Паттерн: {forecast.seasonal_pattern}",
                    "Можно использовать для предиктивного масштабирования"
                ]
            )
            recs.append(rec)

        return recs

    def _channel_type_recommendations(
        self,
        metrics: ChannelMetrics
    ) -> List[Recommendation]:
        """Generate channel type specific recommendations."""
        recs = []

        # External channels
        if metrics.channel.channel_type == ChannelType.EXTERNAL:
            if metrics.max_utilization_percent > 60:  # Lower threshold for external
                rec = Recommendation(
                    priority=RecommendationPriority.MEDIUM,
                    type=RecommendationType.ADD_REDUNDANCY,
                    title="Рассмотреть добавление резервного внешнего канала",
                    description=(
                        "Для критичных внешних каналов рекомендуется иметь резервирование"
                    ),
                    action_items=[
                        "Оценить стоимость резервного канала",
                        "Рассмотреть подключение к другому провайдеру",
                        "Настроить автоматическое переключение (failover)",
                        "Реализовать балансировку нагрузки между каналами"
                    ],
                    timeline_weeks=12,
                    estimated_cost="high",
                    business_impact="Повышение отказоустойчивости внешнего подключения"
                )
                recs.append(rec)

        # Inter-site channels
        elif metrics.channel.channel_type == ChannelType.INTER_SITE:
            if metrics.max_utilization_percent > 70:
                rec = Recommendation(
                    priority=RecommendationPriority.HIGH,
                    type=RecommendationType.BALANCE_LOAD,
                    title="Балансировка межплощадочного трафика",
                    description="Рассмотреть перераспределение трафика между площадками",
                    action_items=[
                        "Проанализировать возможность использования альтернативных маршрутов",
                        "Оптимизировать размещение ресурсов между площадками",
                        "Рассмотреть локальное кэширование данных",
                        "Оценить целесообразность CDN для статичного контента"
                    ],
                    timeline_weeks=6,
                    estimated_cost="medium",
                    business_impact="Снижение нагрузки на межплощадочные каналы"
                )
                recs.append(rec)

        # Transport channels
        elif metrics.channel.channel_type == ChannelType.TRANSPORT:
            if metrics.max_utilization_percent > 75:
                rec = Recommendation(
                    priority=RecommendationPriority.MEDIUM,
                    type=RecommendationType.IMPLEMENT_QOS,
                    title="Оптимизация QoS на транспортном канале",
                    description="Настроить приоритизацию трафика",
                    action_items=[
                        "Классифицировать трафик по приоритетам",
                        "Внедрить/скорректировать политики QoS",
                        "Гарантировать полосу для критичных приложений",
                        "Ограничить некритичный трафик (backup, updates)"
                    ],
                    timeline_weeks=3,
                    estimated_cost="low",
                    technical_notes=[
                        "Рекомендуется приоритизация: Voice > Video > Data > Best Effort"
                    ]
                )
                recs.append(rec)

        return recs

    def _calculate_recommended_capacity(self, metrics: ChannelMetrics) -> float:
        """Calculate recommended channel capacity."""
        # Target utilization: 50-60% of capacity
        target_utilization = 0.55

        # Use peak traffic as baseline
        peak_traffic = max(
            metrics.peak_in_mbps or metrics.traffic_in_mbps,
            metrics.peak_out_mbps or metrics.traffic_out_mbps
        )

        # Add 20% growth buffer
        recommended = (peak_traffic / target_utilization) * 1.2

        # Round up to common capacity increments
        increments = [100, 1000, 10000, 40000, 100000]
        for increment in increments:
            if recommended <= increment:
                return increment

        return recommended

    def _estimate_upgrade_cost(self, metrics: ChannelMetrics) -> str:
        """Estimate relative cost of upgrade."""
        current_capacity = metrics.channel.capacity_mbps
        recommended = self._calculate_recommended_capacity(metrics)

        increase_factor = recommended / current_capacity

        if increase_factor < 1.5:
            return "medium"
        elif increase_factor < 2.5:
            return "high"
        else:
            return "very high"
