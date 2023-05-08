from django.core.management.base import BaseCommand, CommandError
from integrations.one_c.OneCAPI import OneCAPI

from django.conf import settings

from store.models import Product
import math
import random


class Command(BaseCommand):

    def handle(self, *args, **options):

        products_qs = Product.objects.all()
        for product in products_qs:
            product.price = random.randint(100, 10000)
            product.count = random.randint(0, 50)
            product.save()
