# Deribit price tracker

Сервис раз в минуту забирает с биржи [Deribit](https://docs.deribit.com/) index price `btc_usd` и `eth_usd`, сохраняет в PostgreSQL тикер, цену и время (UNIX timestamp) и отдаёт сохранённые данные через HTTP API на FastAPI.

- Сбор: Celery (worker со встроенным beat) + Redis как брокер, клиент биржи на aiohttp.
- Хранение: PostgreSQL, SQLAlchemy 2.0 (async, asyncpg), миграции Alembic.
- API: FastAPI, три GET-метода с обязательным query-параметром `ticker`.

## Быстрый старт

Нужны Docker и Docker Compose.

```bash
cp .env.example .env
docker compose up --build -d      # или: make up
```

Поднимаются четыре контейнера: `db` (PostgreSQL), `redis`, `api` (при старте применяет миграции) и `worker` (Celery worker + beat). Через минуту после старта в базе появятся первые цены:

```bash
curl "http://localhost:8000/v1/prices/latest?ticker=btc_usd"
```

Документация API (Swagger): http://localhost:8000/docs

Остановить: `docker compose down` (или `make down`). Логи api и worker: `make logs`.

## API

Все методы — `GET`, параметр `ticker` обязателен и принимает `btc_usd` или `eth_usd`. Время — UNIX timestamp в секундах, UTC.

| Метод | Параметры | Ответ |
|---|---|---|
| `/v1/prices` | `ticker`, `limit` (1–1000, по умолчанию 100), `offset` (по умолчанию 0) | Все сохранённые цены тикера, от старых к новым |
| `/v1/prices/latest` | `ticker` | Последняя цена тикера; `404`, если данных ещё нет |
| `/v1/prices/range` | `ticker`, `date_from`, `date_to`, `limit`, `offset` | Цены с `date_from <= timestamp <= date_to`; `422`, если `date_from > date_to` |
| `/health` | — | `{"status": "ok"}` |

Пример ответа:

```json
{"ticker": "btc_usd", "price": "81182.63000000", "timestamp": 1792053031}
```

Цена отдаётся строкой, чтобы не терять точность (см. Design decisions). Ошибки имеют вид `{"detail": ...}`: неверный или отсутствующий `ticker` и параметры вне допустимых границ дают `422`.

## Переменные окружения

Вложенные настройки разделяются `__`.

| Переменная | Обязательна | По умолчанию | Назначение |
|---|---|---|---|
| `DATABASE__URL` | да | — | `postgresql+asyncpg://user:password@host:port/db` |
| `REDIS__URL` | да | — | Брокер Celery, `redis://host:port/db` |
| `DERIBIT__BASE_URL` | нет | `https://www.deribit.com/api/v2` | Для тестовой биржи: `https://test.deribit.com/api/v2` |
| `DERIBIT__TIMEOUT_SECONDS` | нет | `10` | Таймаут запроса к бирже |
| `COLLECTOR__INTERVAL_SECONDS` | нет | `60` | Период сбора |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | для compose | — | Учётные данные контейнера PostgreSQL |

## Локальная разработка

Нужен [uv](https://docs.astral.sh/uv/).

```bash
uv sync                      # зависимости, включая dev
make lint                    # ruff + mypy (strict)
make test-unit               # unit-тесты, без внешних сервисов
docker compose up -d db      # PostgreSQL для интеграционных тестов (порт 5432)
make test                    # все тесты; переменные берутся из .env.test
```

Интеграционные тесты пересоздают базу `tracker_test`, применяют к ней миграции Alembic (так проверяются и сами миграции) и после прогона откатывают их. Если PostgreSQL недоступен, интеграционные тесты пропускаются с понятным сообщением.

Новая миграция: `uv run alembic revision --autogenerate -m "..."` (с `DATABASE__URL`, указывающим на базу).

## Структура

```
app/
├── main.py                     # точка входа API:    app = create_app(Settings())
├── worker.py                   # точка входа Celery: celery_app = create_celery_app(Settings())
├── core/config.py              # Settings (pydantic-settings)
├── domain/prices/              # предметная область «цены»
│   ├── types.py                #   Ticker
│   ├── schemas.py              #   IndexPrice
│   ├── interfaces.py           #   PriceClient, PriceRepository (Protocol)
│   ├── exceptions.py           #   PriceFetchError, PriceNotFoundError, InvalidDateRangeError
│   ├── services.py             #   PriceCollectorService, PriceQueryService
│   └── tasks.py                #   Celery-задача сбора
├── infrastructure/
│   ├── deribit/client.py       # DeribitClient (aiohttp)
│   ├── database/               # таблицы, репозиторий, сессии, миграции
│   ├── errors/                 # BaseError со статусом HTTP и обработчик
│   ├── application/factory.py  # create_app
│   └── worker/factory.py       # create_celery_app
└── presentation/api/           # зависимости FastAPI, healthcheck, эндпоинты v1
tests/
├── fakes.py                    # FakePriceClient, InMemoryPriceRepository
├── unit/{core,domain,infrastructure,presentation}/
└── integration/                # репозиторий на настоящем PostgreSQL
```

Зависимости слоёв: `presentation → domain → infrastructure`. Сервисы домена (`services.py`) работают только с протоколами `PriceClient` и `PriceRepository` и не импортируют SQLAlchemy, aiohttp или FastAPI. Реализации подставляются в двух местах: в зависимостях FastAPI (`presentation/api/dependencies.py`) и в Celery-задаче (`domain/prices/tasks.py`).

## Design decisions

1. **Слои и раскладка как в наших внутренних сервисах:** `core / domain / infrastructure / presentation`, домен разбит по предметным областям (`domain/prices`). Бизнес-логика в сервисах, доступ к бирже и к базе — в инфраструктуре, HTTP — в presentation.

2. **Интерфейсы через `typing.Protocol`, зависимости через конструкторы.** `PriceCollectorService` получает клиента биржи и репозиторий в `__init__` и не знает, что это Deribit и PostgreSQL. Реализации и тестовые фейки ничего не наследуют: им достаточно совпадать по методам (структурная типизация). Отдельный DI-фреймворк не нужен: зависимостей мало, и все связи видны в двух местах — FastAPI `Depends` и Celery-задаче.

3. **Нет глобального состояния.** Настройки создаются в точке входа и передаются вниз, а не кэшируются на уровне модуля. Engine базы живёт в `app.state` и закрывается в lifespan; Celery-задача сама создаёт и закрывает engine и HTTP-сессию. Модульные объекты есть только там, где их требуют инструменты: `app.main:app` для uvicorn, `app.worker:celery_app` для Celery CLI (он не умеет запускаться из функции-фабрики), а также роутеры FastAPI (декларация маршрутов, не изменяемое состояние).

4. **Celery и aiohttp: `asyncio.run` в задаче.** Встроенной поддержки `async def` в задачах в Celery 5.5/5.6 нет, поэтому каждый запуск задачи получает свой event loop через `asyncio.run`. Цена — новый цикл и новое подключение к базе раз в минуту, это незаметно. Форк `celery-asyncio` рассматривали и отказались: alpha-версия, в задании требуется Celery. Будь выбор свободным, для асинхронных периодических задач подошёл бы taskiq. Задача объявлена через `@shared_task`: ей не нужен объект приложения при импорте.

5. **Redis как брокер.** Потеря одной минутной задачи некритична — через минуту будет следующая, — поэтому гарантии доставки RabbitMQ не нужны, а Redis проще в настройке. Брокер задаётся одной переменной `REDIS__URL`.

6. **Время — по собственным часам, одно на запуск.** `timestamp` — время получения цен в секундах UTC; оба тикера одного запуска пишутся с одинаковым временем. Поле `usOut` из ответа Deribit не используется: в документации метода его нет.

7. **Точность цены.** В базе `Numeric(20, 8)`, в коде `Decimal`; JSON биржи разбирается сразу в `Decimal` (`parse_float=Decimal`), так что цена нигде не проходит через `float`. В ответе API цена — строка (стандартная сериализация `Decimal` в pydantic), чтобы клиент не потерял точность.

8. **Идемпотентность.** Уникальное ограничение `(ticker, timestamp)` и `INSERT ... ON CONFLICT DO NOTHING`: повторный запуск или второй экземпляр beat не создают дублей. Это же ограничение служит индексом для всех трёх запросов API.

9. **Устойчивость сбора.** Цены тикеров запрашиваются параллельно; если биржа не отдала цену одного тикера (сеть, таймаут, ошибка API, неожиданный ответ), он пропускается с предупреждением в логе, а остальные сохраняются. Любое другое исключение — ошибка в коде, и она не проглатывается. Ретраев нет сознательно: следующий сбор через минуту. Если понадобится непрерывный ряд без пропусков, это первое, что стоит добавить.

10. **`expires` у периодической задачи равен интервалу.** Если worker простаивал, после возвращения он не выполнит пачку накопившихся задач с устаревшим временем — устаревшие просто отбрасываются.

11. **Пагинация и порядок.** Выдача отсортирована по возрастанию времени, поэтому страницы `limit`/`offset` не «съезжают», пока в таблицу добавляются новые строки. Размер страницы ограничен 1000.

12. **Контейнеры.** В задании предложено два контейнера (приложение и база), но Celery без брокера не работает, а worker и API — разные процессы. Поэтому их четыре: `db`, `redis`, `api`, `worker`. Beat встроен в worker (`-B`): при одном worker'е это проще отдельного контейнера, а при масштабировании beat выносится отдельно (дубли и так отсекает уникальное ограничение). Миграции выполняются при старте `api`, worker стартует после того, как `api` стал здоровым. В production миграции стоит вынести в отдельный job.

13. **Тесты.** Сервисы проверяются с фейками без сети и базы; клиент биржи — против локального HTTP-сервера (`aiohttp.test_utils`); API — через `httpx.ASGITransport` с подменой сервиса в `dependency_overrides`; репозиторий и миграции — на настоящем PostgreSQL (SQLite отличается поведением `Numeric` и `ON CONFLICT`).

