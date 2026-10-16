from app.core.config import CollectorSettings, Settings
from app.infrastructure.worker.factory import create_celery_app


def test_collect_task_is_registered(settings: Settings) -> None:
    celery_app = create_celery_app(settings)

    assert "prices.collect" in celery_app.tasks


def test_schedule_follows_interval_setting(settings: Settings) -> None:
    settings = settings.model_copy(update={"COLLECTOR": CollectorSettings(INTERVAL_SECONDS=30)})

    entry = create_celery_app(settings).conf.beat_schedule["collect-prices"]

    assert entry == {"task": "prices.collect", "schedule": 30, "options": {"expires": 30}}
