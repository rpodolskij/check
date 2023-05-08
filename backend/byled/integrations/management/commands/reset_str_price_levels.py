from django.core.management.base import BaseCommand
from integrations.one_c.OneCAPI import OneCAPI

from django.conf import settings

from users.models import User
from store.models import PriceLevel


class Command(BaseCommand):

    def handle(self, *args, **options):
        ids = [
            'LV1',
            'LV2',
            'LV3',
            'LV4',
            'LV5',
        ]
        for id in ids:
            if not PriceLevel.objects.filter(id=id).first():
                PriceLevel.objects.create(
                    id=id,
                    name=id,
                )
