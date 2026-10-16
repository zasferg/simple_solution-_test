from app.core.config import Settings
from app.infrastructure.worker.factory import create_celery_app

celery_app = create_celery_app(Settings())
