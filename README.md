# Capacity Manager

CLI утилита для анализа метрик Grafana и управления пропускной способностью каналов связи.

## Описание

Capacity Manager - это инструмент для ежедневного мониторинга загрузки каналов связи оператора. Утилита:

- Собирает метрики из Grafana (интерфейсный трафик, утилизация)
- Анализирует загрузку внешних каналов, транспортных каналов между оборудованием и межплощадочных каналов
- Выявляет критические и проблемные зоны (пороги >70% warning, >85% critical)
- Генерирует отчёты в разных форматах (консоль, HTML, CSV, Excel)
- Предоставляет рекомендации по расширению каналов

Идеально подходит для ежедневного просмотра высшим руководством компании оператора связи.

## Особенности

- **Модульная архитектура**: каждый компонент независим и может быть изменён без влияния на другие
- **Множество форматов отчётов**: красивый вывод в консоль, HTML для просмотра в браузере, CSV/Excel для анализа
- **Автоматическое обнаружение каналов**:
  - Автоматический поиск интерфейсов в Grafana
  - Классификация на основе префиксов в описании интерфейсов
  - Настраиваемые правила классификации с приоритетами
  - Автоматическая генерация конфигурации для новых каналов
  - Фильтрация по типам, пропускной способности, исключающим паттернам
- **Расширенное прогнозирование**:
  - Линейная регрессия для трендового анализа
  - Экспоненциальное сглаживание (метод Хольта)
  - Обнаружение сезонности и паттернов
  - Прогноз на 90 дней вперёд с доверительными интервалами
  - Определение ускорения роста загрузки
- **Интеллектуальные рекомендации**:
  - Структурированные рекомендации с приоритетами (CRITICAL, HIGH, MEDIUM, LOW)
  - Специфичные для типа канала рекомендации
  - Оценка сроков реализации и бюджета
  - Конкретные action items для технических команд
  - Оценка бизнес-влияния
- **Финансовая аналитика**:
  - Расчёт стоимости каналов с поддержкой разных моделей ценообразования
  - Модели: фиксированная ставка, за Mbps, ступенчатая, по трафику, **burstable 95%**
  - Burstable billing с расчётом по 95-му перцентилю (стандарт индустрии)
  - Оценка стоимости расширения (CAPEX, OPEX)
  - Финансовые сводки с разбивкой по типам каналов
  - Выявление неиспользуемых мощностей и их стоимости
  - Топ самых дорогих каналов
  - ROI анализ для оптимизаций
- **Анализ трендов**: определение направления изменения загрузки и прогнозирование
- **Гибкая конфигурация**: YAML конфигурация с поддержкой переменных окружения
- **Три типа каналов**: внешние, транспортные, межплощадочные

## Установка

### Требования

- Python 3.8+
- Доступ к Grafana API
- API токен Grafana

### Установка из исходников

```bash
# Клонировать репозиторий
git clone <repo-url>
cd hello_world

# Установить зависимости
pip install -r requirements.txt

# Установить пакет
pip install -e .
```

## Конфигурация

1. Скопировать пример конфигурации:
```bash
cp config.example.yaml config.yaml
```

2. Отредактировать `config.yaml`:

```yaml
grafana:
  url: "https://your-grafana.com"
  token: "$GRAFANA_TOKEN"  # или вставить токен напрямую
  verify_ssl: true

channels:
  - name: "Internet-Provider1"
    type: "external"
    capacity_mbps: 10000
    description: "Primary Internet uplink"
    site_a: "MSK-DC1"
    device_a: "CORE-RTR-01"
    interface_pattern: "GigabitEthernet0/0/1"
```

3. Установить переменную окружения с токеном:
```bash
export GRAFANA_TOKEN="your-api-token-here"
```

### Получение API токена Grafana

1. Войти в Grafana
2. Перейти в Configuration → API Keys
3. Создать новый ключ с правами Viewer
4. Скопировать токен

## Использование

### Проверка подключения

```bash
capacity-manager check
```

### Генерация отчёта в консоль

```bash
capacity-manager report
```

### Генерация HTML отчёта

```bash
capacity-manager report --format html --output report.html
```

### Генерация Excel отчёта

```bash
capacity-manager report --format excel --hours 48
```

### Генерация всех форматов

```bash
capacity-manager report --format all
```

### Поиск критических каналов

```bash
capacity-manager alert --threshold 85
```

### Детальная информация по каналу

```bash
capacity-manager detail "Internet-Provider1" --hours 24
```

### Автоматическое обнаружение новых каналов

```bash
# Включить discovery в config.yaml (discovery.enabled: true), затем:
capacity-manager discover

# Сохранить найденные каналы в YAML файл
capacity-manager discover --output discovered_channels.yaml

# Показать только внешние каналы
capacity-manager discover --filter-type external
```

## Команды

### `capacity-manager check`

Проверка подключения к Grafana и доступности datasources.

**Опции:**
- `-c, --config` - путь к файлу конфигурации (по умолчанию: config.yaml)
- `-v, --verbose` - подробный вывод

### `capacity-manager report`

Генерация полного отчёта по загрузке каналов.

**Опции:**
- `-h, --hours` - количество часов для анализа (по умолчанию: из config)
- `-f, --format` - формат отчёта: console, html, csv, excel, all (по умолчанию: console)
- `-o, --output` - путь для сохранения файла
- `-c, --config` - путь к конфигурации
- `-v, --verbose` - подробный вывод

**Примеры:**
```bash
# Консольный отчёт за последние 24 часа
capacity-manager report

# HTML отчёт за последние 48 часов
capacity-manager report --hours 48 --format html

# Все форматы
capacity-manager report --format all
```

### `capacity-manager alert`

Список каналов, превышающих порог загрузки.

**Опции:**
- `-t, --threshold` - порог утилизации в процентах (по умолчанию: 85)
- `-c, --config` - путь к конфигурации

**Пример:**
```bash
# Каналы с загрузкой > 70%
capacity-manager alert --threshold 70
```

### `capacity-manager detail`

Детальная информация по конкретному каналу.

**Аргументы:**
- `channel_name` - имя канала из конфигурации

**Опции:**
- `-h, --hours` - количество часов для анализа (по умолчанию: 24)
- `-c, --config` - путь к конфигурации

**Пример:**
```bash
capacity-manager detail "Internet-Provider1" --hours 48
```

### `capacity-manager discover`

Автоматическое обнаружение и классификация новых каналов в Grafana.

**Опции:**
- `-o, --output` - путь для сохранения YAML конфигурации найденных каналов
- `--show-stats/--no-stats` - показать/скрыть статистику (по умолчанию: показать)
- `-t, --filter-type` - фильтр по типу канала: external, inter_site, transport, all (по умолчанию: all)
- `-c, --config` - путь к конфигурации

**Примеры:**
```bash
# Обнаружить все новые каналы
capacity-manager discover

# Сохранить конфигурацию найденных каналов
capacity-manager discover --output discovered.yaml

# Показать только внешние каналы
capacity-manager discover --filter-type external

# Показать только транспортные каналы без статистики
capacity-manager discover -t transport --no-stats
```

**Как работает Discovery:**

1. **Автоматический поиск**: утилита ищет интерфейсы в Grafana по настроенным метрикам (например, `ifHCInOctets`)
2. **Классификация**: каждый найденный интерфейс классифицируется по префиксу в описании:
   - `EXT:`, `IX:`, `PEER:`, `TRANSIT:`, `ISP:` → external
   - `SITE:`, `WAN:`, `MPLS:` → inter_site
   - `TRANSPORT:`, `DWDM:`, `FIBER:`, `L2:`, `TRUNK:` → transport
3. **Фильтрация**: исключаются уже настроенные каналы и интерфейсы, соответствующие exclude_patterns
4. **Генерация конфигурации**: для новых каналов автоматически создаётся YAML конфигурация

**Настройка правил классификации:**

В `config.yaml` можно настроить собственные правила:

```yaml
discovery:
  enabled: true
  datasource: "prometheus"
  min_capacity_mbps: 100.0

  exclude_patterns:
    - "^lo"      # loopback
    - "^vlan"    # VLANs
    - "test"     # тестовые интерфейсы

  classification_rules:
    - prefix: "IX:"
      channel_type: "external"
      priority: 90
      description: "Internet Exchange"

    - prefix: "WAN:"
      channel_type: "inter_site"
      priority: 90
      description: "WAN links"
```

**Приоритеты правил:**
- Правила с более высоким priority проверяются первыми
- Первое совпадение определяет тип канала
- Рекомендуется: 100 для точных маркеров, 80-90 для общих префиксов

## Архитектура

Проект построен по модульному принципу:

```
capacity_manager/
├── models/            # Модели данных (Channel, Metrics, Analysis)
├── config/            # Управление конфигурацией
├── grafana_api/       # Клиент Grafana API
├── metrics_collector/ # Сбор метрик
├── analyzer/          # Анализ загрузки и трендов
├── forecasting/       # Прогнозирование
├── recommendations/   # Интеллектуальные рекомендации
├── cost_calculator/   # Финансовая аналитика
├── discovery/         # Автоматическое обнаружение каналов (NEW!)
├── reporters/         # Генерация отчётов (Console, HTML, CSV)
├── cli/               # CLI интерфейс
└── utils/             # Вспомогательные утилиты
```

Каждый модуль независим и может быть изменён/заменён без влияния на другие компоненты.

Подробнее см. [ARCHITECTURE.md](ARCHITECTURE.md)

## Расширенная аналитика

### Прогнозирование

Утилита использует несколько алгоритмов прогнозирования:

1. **Линейная регрессия** - для стабильных трендов
2. **Экспоненциальное сглаживание (Holt's method)** - для данных с трендом
3. **Сезонная декомпозиция** - для выявления повторяющихся паттернов

Прогноз включает:
- Предсказание загрузки на 90 дней вперёд
- Доверительные интервалы (95%)
- Точные даты достижения порогов (warning, critical, capacity)
- Обнаружение ускорения роста
- Выявление сезонных паттернов (недельные, месячные)

Пример вывода:
```
📊 Forecast (90 days):

  ⚠️  Warning threshold in 23 days
  🚨 Critical threshold in 45 days
  📈 95% capacity in 67 days
  ⚡ Growth is accelerating!
  📅 Seasonal pattern detected: weekly
```

### Интеллектуальные рекомендации

Система генерирует структурированные рекомендации с учётом:
- **Текущей загрузки** и трендов
- **Типа канала** (external, inter-site, transport)
- **Прогноза** будущей загрузки
- **Ошибок** и проблем качества
- **Паттернов трафика**

Каждая рекомендация включает:
- **Приоритет**: CRITICAL, HIGH, MEDIUM, LOW
- **Тип действия**: upgrade_capacity, optimize_traffic, investigate_errors, и др.
- **Описание проблемы**
- **Конкретные action items** для команды
- **Временные рамки** (в неделях)
- **Оценка стоимости**: low, medium, high
- **Бизнес-влияние**

Пример рекомендации:
```
🚨 CRITICAL PRIORITY:

  Немедленное расширение канала Internet-Provider1
  Канал загружен на 89.5%, что превышает критический порог 85%.
  Высокий риск перегрузки и деградации сервиса.

  Timeline: 2 weeks
  Estimated cost: high

  Action items:
    • Срочно согласовать расширение пропускной способности с провайдером
    • Текущая емкость: 10000 Mbps
    • Рекомендуемая емкость: 40000 Mbps
    • Подготовить технико-коммерческое предложение для руководства
    • Установить срок реализации: 1-2 недели

  Business impact: КРИТИЧНО: Риск потери клиентов из-за деградации
  качества сервиса. Возможны штрафы по SLA.
```

### Финансовая аналитика

Система поддерживает расчёт стоимости каналов и финансовый анализ.

**Модели ценообразования:**

1. **Flat Rate** - фиксированная ежемесячная стоимость
   ```yaml
   pricing:
     model: "flat_rate"
     monthly_cost: 80000
     setup_fee: 50000
   ```

2. **Per-Mbps** - оплата за каждый Mbps пропускной способности
   ```yaml
   pricing:
     model: "per_mbps"
     cost_per_mbps_month: 50  # $50 за Mbps в месяц
     setup_fee: 5000
   ```

3. **Tiered** - ступенчатое ценообразование со скидками за объём
   ```yaml
   pricing:
     model: "tiered"
     tiers:
       - up_to_mbps: 10000
         cost_per_mbps: 30
       - up_to_mbps: 40000
         cost_per_mbps: 25
   ```

4. **Usage-Based** - оплата по фактическому использованию трафика
   ```yaml
   pricing:
     model: "usage_based"
     monthly_cost: 15000  # Базовая стоимость
     cost_per_gb: 0.05    # За GB сверх included
     included_gb_month: 100000  # 100TB included
   ```

5. **Burstable 95%** - стандартная модель с биллингом по 95-му перцентилю
   ```yaml
   pricing:
     model: "burstable_95"
     committed_rate_mbps: 1000  # Минимальный commit
     burstable_rate_mbps: 10000 # Максимальный burst
     cost_per_mbps_month: 40    # Цена за Mbps
   ```

   **Как работает burstable billing:**
   - Система собирает измерения трафика (обычно каждые 5 минут) за месяц
   - Сортирует все значения по возрастанию
   - Отбрасывает верхние 5% (пиковые нагрузки)
   - Биллинг идёт по 95-му перцентилю или committed rate (что больше)
   - Позволяет иметь кратковременные буртсы без дополнительной оплаты

   **Пример:** 10G порт с 1G commit
   - Если 95-й перцентиль = 3.5G → биллинг 3.5G × $40 = $140/месяц
   - Если 95-й перцентиль = 0.8G → биллинг 1G × $40 = $40/месяц (commit)
   - Можно буртсить до 10G в течение 5% времени без штрафов

**Финансовые отчёты включают:**
- Общие затраты (месяц/год)
- Разбивку по типам каналов
- Среднюю стоимость за Mbps
- Стоимость неиспользуемых мощностей
- Топ самых дорогих каналов
- Прогнозируемые затраты с учётом рекомендаций

Пример вывода:
```
💰 Financial Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Metric                          Value
───────────────────────────────────────────
Total Monthly Cost              $1,189,500.00
Total Yearly Cost               $14,274,000.00

External Channels               $1,061,000.00
Inter-Site Channels             $102,500.00
Transport Channels              $26,000.00

Total Capacity                  214,000 Mbps
Avg Cost per Mbps               $5.56/month
Avg Utilization                 62.3%

Unused Capacity                 80,702 Mbps
Unused Capacity Cost            $448,704.11/month

💸 Top 5 Most Expensive Channels:
  1. IX-Moscow: $1,010,000.00/month (40,000 Mbps @ $25.25/Mbps)
  2. MSK-DC1-to-SPB-DC1: $87,000.00/month (100,000 Mbps @ $0.87/Mbps)
  ...
```

## Типы каналов

### External (внешние)
Интернет-каналы, пиринги с другими операторами, международные каналы.

### Inter-Site (межплощадочные)
Каналы между площадками/ЦОДами компании.

### Transport (транспортные)
Внутриплощадочные каналы между оборудованием (core-aggregation, aggregation-access).

## Пороги и рекомендации

| Уровень | Утилизация | Статус | Рекомендации |
|---------|-----------|--------|--------------|
| Normal | < 70% | ✅ Норма | Штатная работа |
| Warning | 70-85% | ⚠️ Внимание | Планирование расширения в течение 1-2 месяцев |
| Critical | > 85% | 🚨 Критично | Немедленное расширение в течение 1-2 недель |

## Форматы отчётов

### Console (консоль)
Красивый вывод с таблицами, цветами и иконками (через Rich library).

### HTML
Интерактивный HTML отчёт с графиками и визуализацией. Идеален для отправки руководству.

### CSV
Простой CSV файл для импорта в Excel/Google Sheets.

### Excel
Многостраничный Excel файл с:
- Summary (сводка)
- All Channels (все каналы)
- Critical (критические)
- Warning (предупреждения)

## Примеры использования

### Ежедневный отчёт для руководства

```bash
# Генерация HTML отчёта за последние 24 часа
capacity-manager report --format html --output /var/www/reports/daily.html

# Отправка по email (требуется настройка mail)
echo "Daily capacity report" | mail -s "Capacity Report" -a /var/www/reports/daily.html cto@company.com
```

### Мониторинг критических каналов

```bash
# Проверка каналов с загрузкой > 85%
capacity-manager alert --threshold 85

# Если есть критические - детальный анализ
capacity-manager detail "Critical-Channel-Name" --hours 48
```

### Автоматизация через cron

```bash
# Добавить в crontab
# Ежедневный отчёт в 9:00
0 9 * * * /usr/local/bin/capacity-manager report --format html --output /var/www/reports/daily_$(date +\%Y\%m\%d).html

# Проверка критических каждый час
0 * * * * /usr/local/bin/capacity-manager alert --threshold 85 | mail -s "Capacity Alert" ops@company.com
```

## Разработка

### Структура модулей

Каждый модуль полностью независим:

- **models/** - только структуры данных, без зависимостей
- **config/** - зависит только от models
- **grafana_api/** - только HTTP клиент, зависит от models
- **metrics_collector/** - использует grafana_api, возвращает models
- **analyzer/** - работает только с models, независим от источника данных
- **reporters/** - работают только с models
- **cli/** - оркеструет все модули

### Добавление нового типа отчёта

1. Создать класс в `reporters/`
2. Реализовать метод, принимающий `CapacityReport`
3. Добавить опцию в CLI

### Добавление нового источника метрик

1. Создать клиент в новом модуле (аналог `grafana_api/`)
2. Реализовать collector, возвращающий `ChannelMetrics`
3. Остальные модули работают без изменений

## Troubleshooting

### Проблема: Connection failed / Grafana не доступен

**Симптомы:**
```
✗ Connection failed
Grafana API request failed: 403 Forbidden
```

**Возможные причины и решения:**

1. **Неверный URL или токен**
   ```bash
   # Проверьте настройки в config.yaml
   grafana:
     url: "https://your-grafana.com"
     token: "$GRAFANA_TOKEN"
   ```

2. **Проблемы с сетью/прокси**
   - Grafana за прокси: добавьте хост в `NO_PROXY`
   - DNS не разрешается: используйте IP адрес вместо hostname
   - Firewall блокирует: проверьте правила доступа

   ```bash
   # Проверка доступности
   curl -H "Authorization: Bearer YOUR_TOKEN" https://grafana.com/api/health
   ```

3. **Токен устарел или недостаточно прав**
   - Создайте новый API ключ в Grafana: Configuration → API Keys
   - Минимальные права: Viewer

4. **SSL/TLS проблемы**
   ```yaml
   grafana:
     verify_ssl: false  # Только для тестирования!
   ```

### Проблема: No channels found при discovery

**Симптомы:**
```
Total channels found: 0
New channels: 0
```

**Решения:**

1. **Проверьте, что discovery включен**
   ```yaml
   discovery:
     enabled: true
   ```

2. **Проверьте datasource**
   ```bash
   capacity-manager check  # Покажет доступные datasources
   ```

3. **Снизьте min_capacity_mbps**
   ```yaml
   discovery:
     min_capacity_mbps: 10.0  # Вместо 100.0
   ```

4. **Проверьте exclude_patterns**
   - Возможно, паттерны исключают нужные интерфейсы
   - Временно уберите exclude_patterns для теста

### Проблема: Каналы классифицируются как "unknown"

**Причина:** Описания интерфейсов не соответствуют префиксам правил.

**Решение:** Добавьте свои правила классификации:

```yaml
discovery:
  classification_rules:
    - prefix: "YOUR_PREFIX:"
      channel_type: "external"  # или inter_site, transport
      priority: 100
      case_sensitive: false
```

**Примеры префиксов:**
- External: `IX:`, `PEER:`, `TRANSIT:`, `ISP:`
- Inter-site: `SITE:`, `WAN:`, `MPLS:`
- Transport: `DWDM:`, `FIBER:`, `L2:`, `TRUNK:`

### Проблема: ModuleNotFoundError

**Симптом:**
```
ModuleNotFoundError: No module named 'click'
```

**Решение:**
```bash
pip install -r requirements.txt
# Или
pip install click rich pandas pyyaml jinja2 plotly openpyxl
```

### Проблема: Configuration errors

**Симптомы:**
```
Configuration errors:
  - Warning threshold must be less than critical threshold
```

**Решение:** Проверьте config.yaml на ошибки:
```bash
# Запустите валидацию
capacity-manager -c config.yaml check
```

**Типичные ошибки:**
- `warning_percent >= critical_percent` (должно быть меньше)
- Пустые обязательные поля (url, token, name)
- Отрицательные значения (capacity, thresholds)
- Неверный тип канала (должен быть: external, inter_site, transport)

### Проблема: Медленная работа

**Решения:**

1. **Уменьшите временной диапазон**
   ```bash
   capacity-manager report --hours 1  # Вместо 24
   ```

2. **Уменьшите количество каналов**
   - Анализируйте только критичные каналы
   - Используйте фильтры и tags

3. **Оптимизируйте запросы к Grafana**
   ```yaml
   metrics:
     sample_interval_minutes: 15  # Вместо 5
   ```

### Проблема: Неверные метрики / пустые данные

**Проверьте:**

1. **Правильные имена метрик**
   ```yaml
   metrics:
     traffic_in_metric: "ifHCInOctets"   # Для SNMP
     # или
     traffic_in_metric: "interface_traffic_in"  # Для Prometheus
   ```

2. **Правильный datasource_uid**
   ```bash
   # Получить список datasources
   capacity-manager check
   ```

3. **Временной диапазон**
   - Проверьте, что данные есть за запрошенный период
   - Попробуйте меньший диапазон: `--hours 1`

### Получение помощи

1. **Логи с подробностями:**
   ```bash
   capacity-manager -v report  # Verbose mode
   ```

2. **Проверка подключения:**
   ```bash
   capacity-manager check
   ```

3. **Тестовый запуск discovery:**
   ```bash
   python3 demo_discovery.py
   ```

4. **Создайте issue:**
   - https://github.com/your-repo/issues
   - Приложите вывод команд выше
   - Укажите версию: `capacity-manager --version`

## Лицензия

MIT

## Поддержка

Для вопросов и предложений создавайте issues в репозитории.
