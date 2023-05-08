from django.core.management.base import BaseCommand
from integrations.one_c.OneCAPI import OneCAPI

from django.conf import settings

from users.models import User
from store.models import PriceLevel


class Command(BaseCommand):

    def handle(self, *args, **options):

        for user in User.objects.all():
            user.price_level = ''
            user.save()


