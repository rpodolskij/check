from django.core.management.base import BaseCommand
from integrations.one_c.OneCAPI import OneCAPI

from django.conf import settings

from users.models import User
from store.models import PriceLevel


class Command(BaseCommand):

    def handle(self, *args, **options):
        for user in User.objects.all():
            user.price_level = None
            user.save()
        price_level = PriceLevel.objects.filter(id='4371e6c0-00f2-11eb-bab4-4ccc6a42cb23').first()
        if price_level:
            for user in User.objects.all():
                user.price_level = price_level
                user.save()

