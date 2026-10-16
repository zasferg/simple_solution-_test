from celery import Celery

from app.core.config import Settings
from app.domain.prices.tasks import collect_prices


def create_celery_app(settings: Settings) -> Celery:
    """
    Build the Celery application with the price collection schedule.

    Importing `collect_prices` registers the shared task; the schedule takes its name
    from the task itself. A run that waited longer than one interval is dropped
    (`expires`), because the next run is already queued.
    """
    celery_app = Celery("price_tracker", broker=settings.REDIS.URL)
    interval = settings.COLLECTOR.INTERVAL_SECONDS
    celery_app.conf.update(
        timezone="UTC",
        task_ignore_result=True,
        broker_connection_retry_on_startup=True,
        beat_schedule={
            "collect-prices": {
                "task": collect_prices.name,
                "schedule": interval,
                "options": {"expires": interval},
            },
        },
    )
    return celery_app
