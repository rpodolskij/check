from django.core.management.base import BaseCommand
from integrations.one_c.OneCAPI import OneCAPI

from django.conf import settings

from integrations.tasks import import_all


class Command(BaseCommand):

    def handle(self, *args, **options):
        import_all.delay()

