from django.core.management.base import BaseCommand, CommandError
from integrations.one_c.OneCAPI import OneCAPI

from django.conf import settings


class Command(BaseCommand):

    def handle(self, *args, **options):
        one_c_api = OneCAPI(settings.ONE_C_LOGIN, settings.ONE_C_PASSWORD)
        products = one_c_api.get_products()
        print(products)
