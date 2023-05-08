from byled.celery import app
from integrations.one_c.OneCAPI import OneCAPI
from django.utils.timezone import get_current_timezone
from threading import Lock

from datetime import datetime, timedelta

from django.conf import settings

from .models import Synchronization


# @app.on_after_configure.connect
# def setup_periodic_tasks(sender, **kwargs):
#     sender.add_perioddic_task(15, import_all.s(), expires=3600)


@app.task(bind=True)
def import_all(self):
    print('Check start sync')
    last_synchronization: Synchronization = Synchronization.objects.order_by('-started_at').first()
    if last_synchronization:
        delta: timedelta = datetime.now(tz=get_current_timezone()) - last_synchronization.started_at
        if delta.seconds > 4 * 3600:
            last_synchronization.is_running = False
            last_synchronization.save()
        if last_synchronization and last_synchronization.is_running:
            print('Previously update is not completed')
            return
    synchronization: Synchronization = Synchronization(
        started_at=datetime.now(tz=get_current_timezone()),
        is_running=True,
    )
    synchronization.save()

    print('Import starting...')
    one_c_api = OneCAPI(settings.ONE_C_LOGIN, settings.ONE_C_PASSWORD)
    one_c_api.import_all()
    one_c_api.update_database()
    print('Import ended')
    synchronization.is_running = False
    synchronization.success = True
    synchronization.ended_at = datetime.now(tz=get_current_timezone())
    synchronization.save()
