from django.core.management.base import BaseCommand, CommandError
from integrations.one_c.OneCAPI import OneCAPI

from django.conf import settings

from store.models import Product, Order, OrderItem


class Command(BaseCommand):

    def handle(self, *args, **options):
        one_c_api = OneCAPI(settings.ONE_C_LOGIN, settings.ONE_C_PASSWORD)
        order = Order.objects.filter(status='CREATED').first()
        if order is None:
            print('New orders not found')
            return
        one_c_api.create_order(order)
