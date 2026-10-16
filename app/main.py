from app.core.config import Settings
from app.infrastructure.application.factory import create_app

app = create_app(Settings())
