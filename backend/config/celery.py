import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs
app.autodiscover_tasks()

# Configure periodic tasks
app.conf.beat_schedule = {
    'detect-overlaps-daily': {
        'task': 'overlaps.tasks.detect_all_overlaps',
        'schedule': crontab(hour=6, minute=0),  # Run at 6 AM daily
    },
    'send-overlap-notifications': {
        'task': 'overlaps.tasks.send_overlap_notifications',
        'schedule': crontab(minute=0, hour='*/2'),  # Run every 2 hours
    },
    'update-trip-statuses': {
        'task': 'overlaps.tasks.update_trip_statuses',
        'schedule': crontab(hour=0, minute=30),  # Run at 12:30 AM daily
    },
    'detect-cross-path-overlaps': {
        'task': 'overlaps.tasks.detect_cross_path_overlaps',
        'schedule': crontab(day_of_week=1, hour=7, minute=0),  # Run Monday at 7 AM
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')