from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone


def power_setter(value: str):
    if value.isdecimal():
        return float(value)
    if "-" in value:
        if len(value.split('-')) == 3:
            return 230.0
    return 0.0


# Create your models here.
class Product(models.Model):
    id_1c = models.CharField(max_length=255, verbose_name='ID 1C', default='', blank=True)
    name = models.CharField(max_length=255, verbose_name="Название товара")
    price = models.FloatField(blank=True, verbose_name="Цена", default=0)
    code = models.CharField(max_length=255, null=True, default=None, blank=True, verbose_name="Код товара")
    count = models.IntegerField(blank=False, default=0, verbose_name='Количество товара на складе')

    # Описание
    image = models.ImageField(verbose_name='Изображение', null=True, blank=True, default=None)
    image_url = models.CharField(verbose_name='Ссылка на изображение', max_length=255, blank=True, default='')
    description = models.TextField(blank=True, verbose_name="Текстовое описание")

    # Основные параметры учета
    category = models.CharField(max_length=255, blank=True, verbose_name="Категория", default='', null=True)
    series = models.CharField(max_length=255, blank=True, default='', verbose_name="Серия", null=True)
    type = models.CharField(max_length=255, blank=True, verbose_name="Тип номенклатуры")
    characteristics = models.TextField(blank=True, verbose_name="Характеристики")
    group_of_list = models.CharField(max_length=255, blank=True, verbose_name="Группа списка")

    # Дополнительные реквизиты

    vendor_code = models.CharField(max_length=255, blank=True, null=True, verbose_name='Артикул', default='')
    brand = models.CharField(max_length=255, blank=True, null=True, verbose_name='Бренд')
    short_description = models.CharField(max_length=255, blank=True, null=True, verbose_name='Краткое наименование')
    power_by_1m = models.FloatField(blank=True, default=0.0, verbose_name="Мощность 1м, Вт")
    led_size = models.FloatField(blank=False, default=0.0, verbose_name='Размер светодиодов')
    warranty = models.IntegerField(blank=True, default=0, verbose_name="Гарантия, мес")
    led_count = models.IntegerField(blank=True, default=0, verbose_name='Количество светодиодов')
    voltage = models.FloatField(blank=True, default=0.0, verbose_name="Рабочее напряжение, В")
    segment_size = models.FloatField(blank=True, default=0.0, verbose_name="Размер сегмента, мм")
    size = models.CharField(max_length=255, blank=True, default='0x0x0', verbose_name="Размеры (ДхШхВ), мм")
    grade_of_waterproofment = models.CharField(max_length=7, blank=True, verbose_name="Степень влагозащиты")
    light_flow = models.FloatField(default=0.0, verbose_name='Световой поток, Лм')
    wire_length = models.FloatField(default=0.0, verbose_name='Длинна провода')
    output_voltage = models.FloatField(blank=True, default=0.0, verbose_name="Выходное напряжение, В")
    output_current = models.FloatField(blank=True, default=0.0, verbose_name="Выходной ток, А")
    power = models.FloatField(blank=True, default=0, verbose_name="Мощность, Вт")
    has_fan = models.BooleanField(default=False, verbose_name='Наличие вентилятора')
    scattering_angle = models.FloatField(default=0.0, verbose_name='Угол рассеивания')

    # Сведения о производителе
    manufacturer = models.CharField(max_length=50, blank=True, verbose_name="Производитель")

    # Планирование и маркетинг
    sales_rating = models.FloatField(default=0.0, verbose_name='Рейтинг продаж')

    # Единицы измерения и условия хранения
    packaging = models.CharField(max_length=255, blank=True, verbose_name='Используемые упаковки')
    storage_unit = models.CharField(max_length=255, blank=True, verbose_name='Единица хранения')
    weight = models.FloatField(default=0.0, blank=False, verbose_name='Вес')
    volume = models.FloatField(default=0.0, blank=False, verbose_name='Объем')
    length = models.FloatField(default=0.0, blank=False, verbose_name='Длина')
    area = models.FloatField(default=0.0, blank=False, verbose_name='Площадь')

    # Регламентированый и финансовый учет
    vat_rate = models.FloatField(default=0.0, blank=False, verbose_name='Ставка НДС, %')

    is_archive = models.BooleanField(default=True, verbose_name='Архивный (не отображается в прайс листе)')

    def get_no_blank_properties(self):
        property_names = [
            # Основные параметры учета
            'category',
            'series',

            # Доплнительные реквизиты
            'brand',
            'power_by_1m',
            'led_size',
            'warranty',
            'led_count',
            'voltage',
            'segment_size',
            'size',
            'grade_of_waterproofment',
            'light_flow',
            'wire_length',
            'output_voltage',
            'output_current',
            'power',
            'has_fan',
            'scattering_angle',

            # Сведения о производителе
            'manufacturer',

            # Единицы измерения и условия хранения
            'packaging',
            'storage_unit',
            'weight',
            'volume',
            'length',
            'area',

            # Регламентированый и финансовый учет
            'vat_rate'

        ]
        properties = []
        blank_values = [None, '', 0, ' ', '0', '-', '0x0x0', '0х0х0']
        for field in self._meta.get_fields():
            if field.name in property_names:
                property_value = self.__getattribute__(field.name)
                if property_value not in blank_values:
                    properties.append({
                        'name': field.verbose_name,
                        'value': property_value,
                    })
        return properties

    def set_property(self, name, value):
        convert_table = {
            'Артикул': {
                'transform_func': str,
                'attribute': 'vendor_code'
            },
            'Бренд': {
                'transform_func': str,
                'attribute': 'brand'
            },
            'Краткое наименование': {
                'transform_func': str,
                'attribute': 'short_description'
            },
            'Мощность 1м, Вт': {
                'transform_func': power_setter,
                'attribute': 'power_by_1m'
            },
            'Размер светодиодов': {
                'transform_func': float,
                'attribute': 'led_size'
            },
            'Гарантия, мес': {
                'transform_func': int,
                'attribute': 'warranty'
            },
            'Количество светодиодов': {
                'transform_func': int,
                'attribute': 'led_count'
            },

            'Рабочее напряжение, В': {
                'transform_func': power_setter,
                'attribute': 'voltage'
            },
            'Размер сегмента, мм': {
                'transform_func': float,
                'attribute': 'segment_size'
            },
            'Размеры (ДхШхВ), мм': {
                'transform_func': str,
                'attribute': 'size'
            },
            'Степень влагозащиты': {
                'transform_func': str,
                'attribute': 'grade_of_waterproofment'
            },
            'Световой поток, Лм': {
                'transform_func': float,
                'attribute': 'light_flow'
            },
            'Длинна провода': {
                'transform_func': float,
                'attribute': 'wire_length'
            },
            'Выходное напряжение, В': {
                'transform_func': float,
                'attribute': 'output_voltage'
            },
            'Выходной ток, А': {
                'transform_func': float,
                'attribute': 'output_current'
            },
            'Мощность, Вт': {
                'transform_func': float,
                'attribute': 'power'
            },
            'Наличие вентилятора': {
                'transform_func': bool,
                'attribute': 'has_fan'
            },
            'Угол рассеивания': {
                'transform_func': float,
                'attribute': 'scattering_angle'
            },
            'Производитель': {
                'transform_func': str,
                'attribute': 'manufacturer'
            },
            'Рейтинг продаж': {
                'transform_func': float,
                'attribute': 'sales_rating'
            },
            'Используемые упаковки': {
                'transform_func': str,
                'attribute': 'packaging'
            },
            'Единица хранения': {
                'transform_func': str,
                'attribute': 'storage_unit'
            },
            'Вес': {
                'transform_func': float,
                'attribute': 'weight'
            },
            'Объем': {
                'transform_func': float,
                'attribute': 'volume'
            },
            'Длина': {
                'transform_func': float,
                'attribute': 'length'
            },
            'Площадь': {
                'transform_func': float,
                'attribute': 'area'
            },
            'Ставка НДС': {
                'transform_func': float,
                'attribute': 'vat_rate'
            },
            'Категория': {
                'transform_func': str,
                'attribute': 'category'
            },
            'Тип номенклатуры': {
                'transform_func': str,
                'attribute': 'type'
            },
            'Характеристики': {
                'transform_func': str,
                'attribute': 'characteristics'
            },
            'Группа списка': {
                'transform_func': str,
                'attribute': 'group_of_list'
            },
            'CATEGORYNAME': {
                'transform_func': str,
                'attribute': 'category'
            },
            'SeriesName': {
                'transform_func': str,
                'attribute': 'series'
            },
        }
        if name in convert_table:
            attr_name = convert_table[name].get('attribute')
            attr_value = convert_table[name].get('transform_func')(value)
            self.__setattr__(attr_name, attr_value)

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'

    def __str__(self):
        return self.name


class PriceLevel(models.Model):
    id = models.CharField(max_length=255, unique=True, verbose_name="ID", primary_key=True)
    name = models.CharField(max_length=255, verbose_name="Название")
    products = models.ManyToManyField(Product, through='ProductPrice')

    class Meta:
        verbose_name = 'Уровень цены'
        verbose_name_plural = 'Уровни цен'

    def __str__(self):
        return self.name


class ProductPrice(models.Model):
    price_level = models.ForeignKey(
        PriceLevel,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Уровень цены"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Товар"
    )
    price = models.FloatField(blank=True, verbose_name="Цена", default=0)
    is_archive = models.BooleanField(default=False, blank=False, null=False)
    created_at = models.DateTimeField(editable=False, default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Цена товара'
        verbose_name_plural = 'Цены товаров'

    def save(self, *args, **kwargs):
        if not self.id:
            self.created_at = timezone.now()
        return super(ProductPrice, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.price_level.name} - {self.price}'


class ProductCategory(models.Model):
    parent = models.ForeignKey('ProductCategory', on_delete=models.CASCADE, related_name='children', null=True, default=None, blank=True)
    code = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255, null=True, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Категория товаров'
        verbose_name_plural = 'Категории товаров'

    def __str__(self):
        return self.name


class Basket(models.Model):
    user = models.OneToOneField('users.User', on_delete=models.CASCADE, default=None, null=True,
                                verbose_name="Пользователь")

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'


class BasketItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, default=None, null=True, verbose_name="Продукт")
    count = models.SmallIntegerField(default=0, verbose_name="Количество")
    basket = models.ForeignKey(Basket, on_delete=models.CASCADE, default=None, null=True, verbose_name="Корзины")
    discount = models.PositiveSmallIntegerField(default=0, blank=True, verbose_name="Скидка")

    class Meta:
        verbose_name = 'Элемент корзины'
        verbose_name_plural = 'Элементы корзины'


class Order(models.Model):
    class OrderStatuses(models.TextChoices):
        CREATED = 'CREATED', _('Создан')
        COMPLETED = 'COMPLETED', _('Выполнен')
        IN_PROGRESS = 'IN_PROGRESS', _('В Работе')

    user = models.ForeignKey('users.User', on_delete=models.CASCADE, verbose_name="Пользователь")
    create_at = models.DateTimeField(auto_now_add=True, null=True, verbose_name="Создан в")
    comment = models.TextField(blank=True, verbose_name="Комментарий")
    status = models.CharField(max_length=11, choices=OrderStatuses.choices, default=OrderStatuses.CREATED,
                              verbose_name="Статус заказа")
    manager = models.ForeignKey('users.User', related_name='manager_of_order', on_delete=models.CASCADE, default=None,
                                null=True, verbose_name="Менеджер", blank=True)

    @property
    def amount(self):
        items = OrderItem.objects.filter(order=self)
        result = 0
        for item in items:
            result += item.amount
        return result

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-create_at']


class OrderItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, default=None, null=True, verbose_name="Товар")
    count = models.SmallIntegerField(default=0, verbose_name="Количество")
    comment = models.TextField(blank=True, verbose_name="Комментарий")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, default=None, null=True, verbose_name="Заказ")
    discount = models.PositiveSmallIntegerField(default=0, blank=True, verbose_name="Скидка")

    @property
    def amount(self):
        return (self.product.cost * (100 - self.discount) * 0.01) * self.count

    class Meta:
        verbose_name = 'Элемент заказа'
        verbose_name_plural = 'Элементы заказа'
