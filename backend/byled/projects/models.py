from django.db import models
from django.utils.translation import ugettext_lazy as _
from store.models import Product, ProductPrice


# Create your models here.
class Project(models.Model):
    class OrderStatuses(models.TextChoices):
        COMPLETED = 'COMPLETED', _('Выполнен')
        IN_PROGRESS = 'IN_PROGRESS', _('В Работе')
        DRAFT = 'DRAFT', _('ЧЕРНОВИК')
        CANCELED = 'CANCELED', _('ОТКЛОНЕН')

    title = models.CharField(max_length=255, verbose_name="Название")
    is_exported = models.BooleanField(default=False, blank=True)
    create_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, verbose_name="Создан в")
    changed_at = models.DateTimeField(auto_now=True, blank=True, null=True, verbose_name="Изменен в")
    status = models.CharField(max_length=11, choices=OrderStatuses.choices, blank=True, default=OrderStatuses.DRAFT,
                              verbose_name="Статус заказа")
    discount = models.FloatField(verbose_name='Скидка в % на весь проект', default=0.0)
    owner = models.ForeignKey('users.User', related_name='project_owner', on_delete=models.CASCADE, default=None,
                              null=True, verbose_name="Владелец проекта")
    client = models.ForeignKey('users.User', related_name='client_of_order', on_delete=models.CASCADE, default=None,
                               null=True, verbose_name="Клиент")
    client_address = models.CharField(max_length=255, null=True, blank=True, verbose_name="Адрес клиента")
    reason_of_refuse = models.TextField(blank=True, verbose_name="Причина отклонения проекта")

    def amount(self):
        summary = 0
        rooms_qs = Room.objects.filter(project=self)
        for room in rooms_qs:
            area_qs = Area.objects.filter(room=room)
            for area in area_qs:
                items_qs = AreaItem.objects.filter(area=area)
                for item in items_qs:
                    product_price = ProductPrice.objects.filter(
                        product__id=item.product.id,
                        price_level=self.client.price_level
                    ).first()
                    price = item.product.price
                    if product_price is not None:
                        price = product_price.price
                    summary += item.count * (price * (100 - item.discount) * 0.01)
        return summary

    class Meta:
        verbose_name = "Проект"
        verbose_name_plural = "Проекты"
        indexes = [
            models.Index(fields=['id']),
            models.Index(fields=['title']),
            models.Index(fields=['status']),
            models.Index(fields=['owner']),
            models.Index(fields=['client']),
        ]

    def __str__(self):
        return self.title


class Room(models.Model):
    title = models.CharField(max_length=255, verbose_name="Название")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, default=None,
                                null=True, verbose_name="Проект")
    position = models.PositiveSmallIntegerField(default=0, blank=True, verbose_name="Место в иерархии")
    is_visible = models.BooleanField(default=True, blank=True)

    class Meta:
        verbose_name = "Помещение"
        verbose_name_plural = "Помещения"
        indexes = [
            models.Index(fields=['id']),
            models.Index(fields=['project']),
        ]

    def __str__(self):
        return f'{self.project.title} - {self.title}'


class Area(models.Model):
    title = models.CharField(max_length=255, verbose_name="Название")
    room = models.ForeignKey(Room, on_delete=models.CASCADE, default=None,
                             null=True, verbose_name="Помещение")
    is_visible = models.BooleanField(default=True)
    position = models.PositiveSmallIntegerField(default=0, verbose_name="Место в иерархии")

    class Meta:
        verbose_name = "Зона"
        verbose_name_plural = "Зоны"
        indexes = [
            models.Index(fields=['id']),
            models.Index(fields=['room']),
        ]

    def __str__(self):
        return f'{self.room.project.title} - {self.room.title} - {self.title}'


class AreaItem(models.Model):
    area = models.ForeignKey(Area, on_delete=models.CASCADE, default=None, null=True, verbose_name="Зона")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, default=None, null=True, blank=True,
                                verbose_name="Товар")
    discount = models.PositiveSmallIntegerField(default=0, blank=True, verbose_name="Скидка")
    count = models.PositiveSmallIntegerField(default=0, blank=True, verbose_name="Количество товара")

    price_rub = models.FloatField(blank=True, verbose_name="Цена (ryb)", default=0)
    price_byn = models.FloatField(blank=True, verbose_name="Цена (byn)", default=0)

    class Meta:
        verbose_name = "Элемент зоны"
        verbose_name_plural = "Элементы зон"
        indexes = [
            models.Index(fields=['id']),
            models.Index(fields=['area']),
        ]

    def __str__(self):
        return f'{self.area.room.project.title} - {self.area.room.title} - {self.area.title} - {self.product.name}'
