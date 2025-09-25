import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webapps2025.settings")
app = Celery("webapps2025")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
