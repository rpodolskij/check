from django.core.management.base import BaseCommand, CommandError
from integrations.one_c.OneCAPI import OneCAPI

from django.conf import settings


class Command(BaseCommand):

    def handle(self, *args, **options):
        one_c_api = OneCAPI(settings.ONE_C_LOGIN, settings.ONE_C_PASSWORD)
        one_c_api.get_picture("57e7e61a-9e3d-11eb-baf4-4ccc6a42cb23")
