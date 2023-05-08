import os

from celery import Celery
from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'byled.settings')

app = Celery('byled', broker='pyamqp://guest:guest@rabbitmq')

app.conf.beat_schedule = {
    'import-all-from-1c-evety-5min': {
        'task': 'integrations.tasks.import_all',
        'schedule': settings.ONE_C_SYNC_INTERVAL,
    },
}
app.conf.timezone = 'UTC'

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()
