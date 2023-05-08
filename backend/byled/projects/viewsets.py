import os.path
import os
import uuid

from decimal import *
from typing import Optional

from rest_framework import viewsets, status, views
from rest_framework.request import Request
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from byled.responses import ApiErrorCodes, ApiResponse, ApiErrorResponse
from .models import Project, Room, Area, AreaItem
from store.models import Product, Basket, BasketItem, Order, OrderItem, ProductPrice, PriceLevel
from store.serializers import OrderSerializer, BasketSerializer, PriceLevelSerializer
from .serializers import ProjectSerializer, ProjectCreateSerializer, ProjectUpdateSerializer, RoomSerializer, \
    RoomCreateUpdateSerializer, AreaSerializer, AreaCreateUpdateSerializer, AreaSetDiscountSerializer, \
    AreaItemSerializer, AreaItemUpdateSerializer
from utils.logging.logger import info, warning
from users.models import User
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .permissions import CsrfExemptSessionAuthentication
from drf_yasg.utils import swagger_auto_schema
from drf_yasg.openapi import Parameter

from django.http.response import HttpResponse, FileResponse

from jinja2 import Environment, FileSystemLoader
from django.conf import settings

import pdfkit
from django.utils.encoding import smart_str

from fpdf import FPDF  # fpdf class
from PIL import ImageFont, Image


class Currencies(object):
    byn = 'BYN'
    rub = 'RUB'


PRICE_LEVEL_MAP = {
    Currencies.byn: {
        User.PriceLevels.OPT1: "5c94e005-00f2-11eb-bab4-4ccc6a42cb23",
        User.PriceLevels.OPT2: "691c60d0-00f2-11eb-bab4-4ccc6a42cb23",
        User.PriceLevels.OPT3: "734541dd-00f2-11eb-bab4-4ccc6a42cb23",
        User.PriceLevels.OPT4: "734541de-00f2-11eb-bab4-4ccc6a42cb23",
        User.PriceLevels.RETAIL_NO_NDS: "5c94e004-00f2-11eb-bab4-4ccc6a42cb23",
        User.PriceLevels.RETAIL_NDS: "4371e6c0-00f2-11eb-bab4-4ccc6a42cb23",
    },
    Currencies.rub: {
        User.PriceLevels.OPT1: "2121ed13-3995-11ed-bb2d-4ccc6a42cb23",
        User.PriceLevels.OPT2: "30a27061-3995-11ed-bb2d-4ccc6a42cb23",
        User.PriceLevels.OPT3: "47b32be1-3995-11ed-bb2d-4ccc6a42cb23",
        User.PriceLevels.OPT4: "47b32be2-3995-11ed-bb2d-4ccc6a42cb23",
        User.PriceLevels.RETAIL_NO_NDS: "5bed9d7f-3995-11ed-bb2d-4ccc6a42cb23",
        User.PriceLevels.RETAIL_NDS: "4e8c5018-3a48-11ed-bb2d-4ccc6a42cb23",
    }
}


def get_price_level(user_price_level, currency=Currencies.byn) -> Optional[PriceLevel]:
    """
    Возвращает объект модели PriceLevel исходя из уровня цены пользователя и указаной валюты (currency)
    :param user_price_level:
    :param currency:
    :return:
    """
    if currency not in PRICE_LEVEL_MAP:
        return None
    if user_price_level not in PRICE_LEVEL_MAP.get(currency):
        return None
    print('GET PRICE LEVEL: ', user_price_level, currency, PRICE_LEVEL_MAP.get(currency).get(user_price_level))
    return PriceLevel.objects.get(id=PRICE_LEVEL_MAP.get(currency).get(user_price_level))


def get_pil_text_size(text, font_size=8, font_path='/code/export-templates/assets/fonts/Montserrat-Regular.ttf'):
    # Параметры по умолчанию соответствуют шрифту и его размеру в контактах титульной страницы
    font = ImageFont.truetype(font_path, font_size)
    size = font.getsize(text)[0]
    return size


class PDF(FPDF):

    def __init__(self, export_settings: dict, owner: dict, orientation='P', unit='pt', format='A4',
                 currency=Currencies.byn):
        self.currency = currency
        self.pdf_w = 595
        self.pdf_h = 842

        self.export_settings = export_settings
        self.owner = owner

        self.number_wight = 8
        self.article_wight = 27
        self.image_wight = 16
        self.description_wight = 33
        self.count_wight = 22
        self.price_wight = 17

        self.number_item_wight = 8
        self.article_item_wight = 36
        self.image_item_wight = 75
        self.description_item_wight = 160
        self.count_item_wight = 18
        self.price_item_wight = 17
        # amount_wight = 34 - захардкожена, т.к не надо ее никуда перетаскивать

        if (export_settings['include_images'] == True):  # and (export_settings['include_properties'] == True):
            self.number_position = 50
            self.article_position = 80
            self.image_position = 158
            self.description_position = 280
            self.count_position = 410
            self.price_position = 466

        if (export_settings['include_images'] == False):  # and (export_settings['include_properties'] == True):
            self.number_position = 50
            self.article_position = 80
            self.image_position = 0
            self.description_position = 210
            self.count_position = 340
            self.price_position = 400

        # elif (export_settings['include_images'] == True) and (export_settings['include_properties'] == False):
        #     self.number_position = 50
        #     self.article_position = 80
        #     self.image_position = 160
        #     self.description_position = 0
        #     self.count_position = 250
        #     self.price_position = 320
        #
        # else:
        #     self.number_position = 50
        #     self.article_position = 80
        #     self.image_position = 0
        #     self.description_position = 0
        #     self.count_position = 140
        #     self.price_position = 210

        self.number_item_position = self.number_position + (self.number_wight / 2) - (self.number_item_wight / 2)
        self.article_item_position = self.article_position + (self.article_wight / 2) - (self.article_item_wight / 2)
        self.image_item_position = self.image_position + (self.image_wight / 2) - (self.image_item_wight / 2)
        self.description_item_position = self.description_position + (self.description_wight / 2) - (
                self.description_item_wight / 2)
        self.count_item_position = self.count_position + (self.count_wight / 2) - (self.count_item_wight / 2)
        self.price_item_position = self.price_position + (self.price_wight / 2) - (self.price_item_wight / 2)

        super(PDF, self).__init__(orientation, unit, format)

    def move_cursor_next_row(self):
        """
        перемещает текущую позицию на 6 по y для маленького пустого места между строками таблицы
        :return:
        """
        self.set_xy(40, self.get_y() + 6)

    def draw_title_page(self):
        """
        Рисует титульную страницу
        :return:
        """
        full_name = self.owner.get('full_name')
        email = self.owner.get('email')
        phone = self.owner.get('phone')

        self.new_page()
        self.image('/code/export-templates/pdf/logo.png', 198, 223, 200)

        self.set_font('MontserratRegular', size=8)

        full_name_px_len = get_pil_text_size(full_name)
        full_name_x = (self.pdf_w / 2) - (
                (full_name_px_len + 15) / 2) + 15  # 15 - это размер иконки + расстояние до нее
        self.set_xy(full_name_x, 384)
        self.cell(h=10, w=full_name_px_len + 1, border=0, fill=False, txt=full_name)
        # self.image('/code/export-templates/pdf/fio.png', self.get_x() + 4, 384, 10)
        self.image('/code/export-templates/pdf/fio.png', full_name_x - 15, 384, 10)

        email_px_len = get_pil_text_size(email)
        email_x = (self.pdf_w / 2) - ((email_px_len + 15) / 2) + 15
        self.set_xy(email_x, 414)
        self.cell(h=10, w=email_px_len + 1, border=0, fill=False, align='C', txt=email)
        # self.image('/code/export-templates/pdf/email.png', self.get_x() + 4, 415, 10)
        self.image('/code/export-templates/pdf/email.png', email_x - 15, 415, 10)

        phone_px_len = get_pil_text_size(phone)
        phone_x = (self.pdf_w / 2) - ((phone_px_len + 15) / 2) + 15
        self.set_xy(phone_x, 445)
        self.cell(h=10, w=phone_px_len + 1, border=0, fill=False, align='C', txt=phone)
        self.image('/code/export-templates/pdf/phone.png', phone_x - 15, 445, 10)
        # self.image('/code/export-templates/pdf/phone.png', self.get_x() + 4, 445, 10)

        self.image('/code/export-templates/pdf/footer.png', 266, 802, 66)

    def new_page(self, x: int = None, y: int = None):
        """
        Добавляет новую страницу и переносит курсор в начало
        :param x: позиция курсора после отработки метода x
        :param y: позиция курсора после отработки метода y
        :return:
        """
        self.add_page()
        if x and y:
            self.set_xy(x, y)

    def draw_page_header(self, project_number: int, x: int = None, y: int = None):
        """
        Рисует верхнюю, общую часть у страницы
        :param x: позиция курсора после отработки метода x
        :param y: позиция курсора после отработки метода y
        :return:
        """
        self.set_font('MontserratRegular', size=8)
        self.image('/code/export-templates/pdf/logo.png', 35, 26, 117, 60)

        contacts_x = 400
        contacts_border = 539  # self.pdf_w - 56
        contacts_width = contacts_border - contacts_x

        full_name = self.owner.get('full_name')
        self.set_xy(contacts_x, 33)
        self.cell(h=10, w=contacts_width, border=0, fill=False, align='R', txt=full_name)
        self.image('/code/export-templates/pdf/fio.png', 545, 33, 10)

        email = self.owner.get('email')
        self.set_xy(contacts_x, 45)
        self.cell(h=10, w=contacts_width, border=0, fill=False, align='R', txt=email)
        self.image('/code/export-templates/pdf/email.png', 545, 46, 10)

        # тут без гибкости т.к длина номера всегда одна
        phone = self.owner.get('phone')
        self.set_xy(contacts_x, 58)
        self.cell(h=10, w=contacts_width, border=0, fill=False, align='R', txt=phone)
        self.image('/code/export-templates/pdf/phone.png', 545, 56, 10)

        self.set_xy(40, 96)
        self.set_font('MontserratSemiBold', size=16)
        self.cell(h=15, w=218, border=0, fill=False, txt=f'КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ')
        self.set_xy(40, 115)
        self.set_font('MontserratMedium', size=12)
        if self.export_settings['specification'] == 'rooms':
            self.cell(h=12, w=218, border=0, fill=False, txt=f'СПЕЦИФИКАЦИЯ ПО ЗОНАМ')
        if self.export_settings['specification'] == 'products':
            self.cell(h=12, w=218, border=0, fill=False, txt=f'СПЕЦИФИКАЦИЯ ПО ПРОДУКТАМ')
        self.set_xy(40, 132)
        self.set_font('MontserratLight', size=8)
        self.cell(h=10, w=51, border=0, fill=False, txt=f'Проект №{project_number}')

        # По умолчанию переносит на позицию для отрисовки хидера таблицы
        if x and y:
            self.set_xy(x, y)
        else:
            self.set_xy(40, 147)

    def draw_page_footer(self):
        """
        Рисует футер страницы
        :return:
        """
        self.set_xy(265, 802)
        self.image('/code/export-templates/pdf/footer.png', self.get_x(), self.get_y(), 66, 14)

        self.set_x(550)
        number = str(self.page_no() - 1)
        self.set_font('MontserratMedium', size=10)
        self.set_text_color(134, 134, 134)
        self.cell(w=20, h=20, border=0, txt=str(number))
        self.set_text_color(12, 13, 13)

    def draw_table_header(self, x: int = None, y: int = None):
        """
        отрисовывает хидер таблицы
        :param x: позиция курсора после отработки метода x
        :param y: позиция курсора после отработки метода y
        :return:
        """
        # pdf.image('table_header.png', pdf.get_x(), pdf.get_y(), 515, 16)
        self.set_fill_color(12, 13, 13)
        self.set_font('MontserratMedium', size=6)
        # current_elem_x_position = 50

        self.cell(h=1, w=515, border=0, fill=True, ln=1)

        # pdf.set_x(current_elem_x_position)
        self.set_x(self.number_position)
        self.cell(h=15, w=7, border=0, fill=False, txt='№')

        # current_elem_x_position = current_elem_x_position + 30
        # pdf.set_x(current_elem_x_position)
        self.set_x(self.article_position)
        self.cell(h=15, w=27, border=0, fill=False, txt='Артикул')

        if self.export_settings['include_images']:
            self.set_x(self.image_position)
            self.cell(h=15, w=16, border=0, fill=False, txt='Фото')

        if self.export_settings['include_properties']:
            self.set_x(self.description_position)
            self.cell(h=15, w=33, border=0, fill=False, txt='Описание')

        self.set_x(self.count_position)
        self.cell(h=15, w=22, border=0, fill=False, txt='Кол-во')

        self.set_x(self.price_position)
        self.cell(h=15, w=17, border=0, fill=False, txt='Цена')

        self.set_x(506)
        self.cell(h=15, w=1, border=0, fill=False, txt='Стоимость')

        self.set_xy(40, self.get_y() + 15)
        self.cell(h=1, w=515, border=0, fill=True, ln=1)

        # По умолчанию переносит на позицию для отрисовки таблицы
        if x and y:
            self.set_xy(x, y)
        else:
            self.set_xy(40, 164)

    def draw_room_and_zone_section(self, room: dict, area: dict, include_room: bool = False, x: int = None,
                                   y: int = None):
        """
        отрисовывает секцию с помещением и зоной
        :param x: позиция курсора после отработки метода x
        :param y: позиция курсора после отработки метода y
        :param room_name: имя помещения
        :param area: зона
        :return:
        """
        zone_name = area.get('title')
        room_name = room.get('title')
        self.set_fill_color(233, 233, 233)
        self.set_font('MontserratRegular', size=8)

        if include_room:
            if len(room_name) > 90:
                room_name = room_name[:90] + '...'
            self.cell(h=18, w=515, border=0, fill=True, txt=f'        {room_name}')
            self.set_x(509)
            total_amount = "{:10.2f}".format(room.get('total_amount'))
            self.cell(h=18, w=10, fill=True, txt=f'{total_amount}')
            self.set_xy(40, self.get_y() + 18)
        self.set_fill_color(240, 240, 240)
        print('ZONE LENGTH: ', len(zone_name))
        if len(zone_name) > 90:
            zone_name = zone_name[:90] + '...'
        self.cell(h=18, w=515, border=0, fill=True, txt=f'           {zone_name}')
        self.set_x(509)
        total_amount = "{:10.2f}".format(area.get('total_amount'))
        self.cell(h=18, w=10, fill=True, txt=f'{total_amount}')

        self.set_xy(40, self.get_y() + 18)
        self.set_fill_color(133, 133, 133)
        self.cell(h=1, w=515, border=0, fill=True, ln=1)
        self.set_x(40)

    def draw_product_group_section(self, product_group_name: str, product_group: dict, x: int = None, y: int = None):
        """
        отрисовывает секцию с помещением и зоной
        :param x: позиция курсора после отработки метода x
        :param y: позиция курсора после отработки метода y
        :param room_name: имя помещения
        :param area: зона
        :return:
        """
        self.set_fill_color(233, 233, 233)
        self.set_font('MontserratRegular', size=8)
        product_group_amount = Decimal(product_group['total_amount']).quantize(Decimal("1.00"))

        self.cell(h=18, w=515, border=0, fill=True, txt=f'        {product_group_name}')
        self.set_x(509)
        self.cell(h=18, w=10, fill=True, txt=f'{product_group_amount}')
        self.set_xy(40, self.get_y() + 18)

        self.set_fill_color(133, 133, 133)
        self.cell(h=1, w=515, border=0, fill=True, ln=1)
        self.set_x(40)

    def draw_area_item(self, number: int, area_item: dict):
        """
        Рисует строку с товаром
        :param number: порядковый номер в секции
        :param product: данные товара
        :return:
        """
        current_y = self.get_y()
        if self.export_settings['include_images']:
            next_item_y = self.get_y() + 57  # изначально берем за самую высокую часть фотографию 57
        else:
            next_item_y = self.get_y() + 7
        self.set_font('MontserratLight', size=6)
        product = area_item.get('product')

        code = product.get('vendor_code')
        description = product.get('name').replace('\t', ' ') + '\n' + product.get('description')
        # if len(description) > 246:
        #     description = description[:243] + '...'
        # todo Скорректировать отображение цены в соответсвтии с уровнем цены и указаной валютой
        price = Decimal(area_item.get('price')).quantize(Decimal("1.00"))
        count = Decimal(area_item.get('count')).quantize(Decimal("1.00"))
        amount = Decimal(price * count).quantize(Decimal("1.00"))

        self.set_x(self.number_item_position)
        self.cell(w=6, h=7, border=0, txt=f'{number}')

        self.set_x(self.article_item_position)
        self.cell(w=25, h=7, border=0, txt=f'{code}')

        if self.export_settings['include_images']:
            self.set_x(self.image_item_position)
            image = area_item.get('product_image')
            # DEST_WIDTH = 75
            # DEST_HEIGHT = 57
            DEST_WIDTH = 75 * 2
            DEST_HEIGHT = 50 * 2
            try:
                reduced_image_filename = f'{image[:len(image) - 4]}.reduced.png'
                # if not os.path.exists(reduced_image_filename):
                img = Image.open(image)
                dest_width = DEST_WIDTH
                multiplier = img.size[0] / dest_width
                dest_height = img.size[1] / multiplier
                img = img.resize(
                    (round(dest_width), round(dest_height)),
                    Image.ANTIALIAS,
                )
                if img.size[1] > DEST_HEIGHT:
                    dest_height = DEST_HEIGHT
                    multiplier = img.size[1] / dest_height
                    dest_width = DEST_WIDTH / multiplier
                    img = img.resize(
                        (round(dest_width), round(dest_height)),
                        Image.ANTIALIAS,
                    )
                print(image, img.size)
                img.save(reduced_image_filename)
                self.image(reduced_image_filename, self.get_x(), self.get_y(), img.size[0] / 2.0)
            except Exception as e:
                print(e)
                self.image('/code/byled/static/images/no_photo.png', self.get_x(), self.get_y(), 75)

        self.set_x(self.description_item_position)
        print(self.get_y())
        self.multi_cell(w=self.description_item_wight, h=7, border=0, txt=f'{description}')
        print(self.get_y())
        if self.export_settings['include_properties']:
            description_key_wight = self.description_item_wight / 2
            description_value_wight = self.description_item_wight - description_key_wight - 1
            self.set_x(self.description_item_position)
            # self.set_y(self.get_y() + 7)
            for key in product.keys():
                if key == 'category':
                    self.draw_characteristic(key, product, 'Категория:', description_key_wight, description_value_wight)
                if key == 'series':
                    series = product.get('series')
                    self.draw_characteristic(key, product, 'Серия:', description_key_wight, description_value_wight)
                if key == 'type':
                    self.draw_characteristic(key, product, 'Тип:', description_key_wight, description_value_wight)
                if key == 'group_of_list':
                    self.draw_characteristic(key, product, 'Группа списка:', description_key_wight,
                                             description_value_wight)
                if key == 'brand':
                    self.draw_characteristic(key, product, 'Бренд:', description_key_wight, description_value_wight)
                if key == 'power_by_1m':
                    self.draw_characteristic(key, product, 'Мощность 1м, Вт:', description_key_wight,
                                             description_value_wight)
                if key == 'led_size':
                    self.draw_characteristic(key, product, 'Размер светодиодов:', description_key_wight,
                                             description_value_wight)
                if key == 'warranty':
                    self.draw_characteristic(key, product, 'Гарантия, мес:', description_key_wight,
                                             description_value_wight)
                if key == 'led_count':
                    self.draw_characteristic(key, product, 'Количество светодиодов:', description_key_wight,
                                             description_value_wight)
                if key == 'voltage':
                    self.draw_characteristic(key, product, 'Рабочее напряжение, В:', description_key_wight,
                                             description_value_wight)
                if key == 'segment_size':
                    self.draw_characteristic(key, product, 'Размер сегмента, мм:', description_key_wight,
                                             description_value_wight)
                if key == 'size':
                    self.draw_characteristic(key, product, 'Размеры (ДхШхВ), мм:', description_key_wight,
                                             description_value_wight)
                if key == 'grade_of_waterproofment':
                    self.draw_characteristic(key, product, 'Степень влагозащиты:', description_key_wight,
                                             description_value_wight)
                if key == 'light_flow':
                    self.draw_characteristic(key, product, 'Световой поток, Лм:', description_key_wight,
                                             description_value_wight)
                if key == 'wire_length':
                    self.draw_characteristic(key, product, 'Длинна провода:', description_key_wight,
                                             description_value_wight)
                if key == 'output_voltage':
                    self.draw_characteristic(key, product, 'Выходное напряжение, В:', description_key_wight,
                                             description_value_wight)
                if key == 'output_current':
                    self.draw_characteristic(key, product, 'Выходной ток, А:', description_key_wight,
                                             description_value_wight)
                if key == 'power':
                    self.draw_characteristic(key, product, 'Мощность, Вт:', description_key_wight,
                                             description_value_wight)
                if key == 'has_fan':
                    self.draw_characteristic(key, product, 'Наличие вентилятора', description_key_wight,
                                             description_value_wight)
                if key == 'scattering_angle':
                    self.draw_characteristic(key, product, 'Угол рассеивания:', description_key_wight,
                                             description_value_wight)
                if key == 'manufacturer':
                    self.draw_characteristic(key, product, 'Производитель:', description_key_wight,
                                             description_value_wight)
                if key == 'packaging':
                    self.draw_characteristic(key, product, 'Используемые упаковки:', description_key_wight,
                                             description_value_wight)
                if key == 'storage_unit':
                    self.draw_characteristic(key, product, 'Единица хранения:', description_key_wight,
                                             description_value_wight)
                if key == 'weight':
                    self.draw_characteristic(key, product, 'Вес:', description_key_wight, description_value_wight)
                if key == 'volume':
                    self.draw_characteristic(key, product, 'Объем:', description_key_wight, description_value_wight)
                if key == 'length':
                    self.draw_characteristic(key, product, 'Длина:', description_key_wight, description_value_wight)
                if key == 'area':
                    self.draw_characteristic(key, product, 'Ширина:', description_key_wight, description_value_wight)

        if self.get_y() > next_item_y:
            next_item_y = self.get_y()

        self.set_y(current_y)
        self.set_x(self.count_item_position)
        self.cell(w=6, h=7, border=0, txt=f'{count}')

        self.set_x(self.price_item_position)
        self.cell(w=6, h=7, border=0, txt=f'{price}')

        self.set_x(515)
        self.cell(w=6, h=7, border=0, txt=f'{amount}')

        self.set_xy(40, next_item_y)

    def page_break_if_needed(self, project_number: int, room: dict = None, area: dict = None,
                             product_group_name: str = None, product_group: dict = None, include_room: bool = False):
        current_y = self.get_y()
        if current_y + 137 >= self.pdf_h:
            self.draw_page_footer()
            # self.draw_page_number()
            self.new_page()
            self.draw_page_header(project_number)
            self.draw_table_header()
            if self.export_settings['specification'] == 'rooms':
                self.draw_room_and_zone_section(room, area, include_room)
            else:
                print(product_group)
                print(product_group_name)
                self.draw_product_group_section(product_group_name=product_group_name, product_group=product_group)
            return True
        else:
            return False

    def calculate_area_amount(self, area: dict):
        area_amount = 0
        for area_item in area.get('area_items'):
            product_count = (area_item.get('count'))
            product = area_item.get('product')
            # todo Скорректировать отображение цены в соответсвтии с уровнем цены и указаной валютой
            product_price = product.get('price')
            product_amount = product_price * product_count
            area_amount += product_amount
        return Decimal(area_amount).quantize(Decimal("1.00"))

    # def calculate_product_group_amount(self, product_group_data: dict):
    #     area_amount = 0
    #     for area_item in area.get('area_items'):
    #         product_count = (area_item.get('count'))
    #         product = area_item.get('product')
    #         product_price = product.get('price')
    #         product_amount = product_price * product_count
    #         area_amount += product_amount
    #     return area_amount

    def calculate_room_amount(self, room: dict):
        # todo Скорректировать отображение цены в соответсвтии с уровнем цены и указаной валютой
        room_amount = 0
        for area in room.get('areas'):
            room_amount += self.calculate_area_amount(area)
        return Decimal(room_amount).quantize(Decimal("1.00"))

    def calculate_project_amount(self, project: dict):
        # todo Скорректировать отображение цены в соответсвтии с уровнем цены и указаной валютой
        project_amount = 0
        if self.export_settings['specification'] == 'rooms':
            for room in project.get('rooms'):
                project_amount += self.calculate_room_amount(room)
        else:
            product_groups = project.get('product_groups')
            for product_group in product_groups.keys():
                project_amount += product_groups[product_group]['total_amount']
        return Decimal(project_amount).quantize(Decimal("1.00"))

    def draw_project_amount(self, project):
        # todo Скорректировать отображение цены в соответсвтии с уровнем цены и указаной валютой
        self.set_xy(40, self.get_y() + 7)
        self.set_fill_color(0, 0, 0)
        self.cell(h=1, w=515, border=0, fill=True)

        self.set_xy(40, self.get_y() + 1)
        self.set_fill_color(254, 251, 220)
        self.cell(h=30, w=515, border=0, fill=True)

        BYN_position = 525
        self.set_font('MontserratRegular', size=8)
        self.set_x(BYN_position)
        # self.cell(h=30, w=30, border=0, txt='BYN')

        project_amount ="{:10.2f}".format(project.get('total_amount'))
        project_amount_x = BYN_position - (4.33 * len(project_amount))
        self.set_x(project_amount_x)

        self.cell(h=30, w=30, border=0, txt=f'{project_amount} {self.currency}')

        self.set_font('MontserratSemiBold', size=8)
        self.set_x(project_amount_x - 38)
        self.cell(h=30, w=30, border=0, txt='Итого: ')

    def draw_characteristic(self, key: str, product: dict, txt: str, description_key_wight: float,
                            description_value_wight: float):
        value = product.get(key)
        if value is not None:
            # print('value :', value)
            if isinstance(value, bool):
                if value:
                    self.cell(w=description_key_wight, h=7, border=0, txt=txt)
                    self.cell(w=description_value_wight, h=7, border=0, txt='Да', align='R', ln=2)
                    self.set_x(self.description_item_position)
            elif isinstance(value, str):
                if value != '':
                    value = str(value).replace('\t', ' ')
                    self.cell(w=description_key_wight, h=7, border=0, txt=txt)
                    self.multi_cell(w=description_value_wight, h=7, border=0, txt=value, align='R')
                    self.set_x(self.description_item_position)
            elif isinstance(value, (int, float)):
                if value != 0:
                    value = str(value)
                    self.cell(w=description_key_wight, h=7, border=0, txt=txt)
                    self.cell(w=description_value_wight, h=7, border=0, txt=value, align='R', ln=2)
                    self.set_x(self.description_item_position)


class ProjectViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    @swagger_auto_schema(
        operation_summary='Добавление(создание) нового проекта',
        request_body=ProjectCreateSerializer,
        responses={201: ProjectSerializer},
        tags=[
            'Проекты'
        ]
    )
    def create(self, request: Request):
        user = request.user
        serializer = ProjectCreateSerializer(data=request.data)
        if not serializer.is_valid():
            resp = ApiErrorResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ApiErrorCodes.validation,
                message="Ошибка валидации",
                result=serializer.errors
            )
            warning(request.path, request.data, resp.data)
            return resp

        # if user.account_type == 'CLIENT':
        #     response = ApiErrorResponse(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         error_code=ApiErrorCodes.bad_credentials,
        #         message="У вас недостаточно прав для выполнения данного действия"
        #     )
        #     warning(request.path, request.data, response.data)
        #     return response
        project = Project.objects.create(title=serializer.validated_data['title'],
                                         client=serializer.validated_data['client'],
                                         owner=user)

        if project.client:
            project.client_address = project.client.company_address
            project.save()
        response = ApiResponse(status_code=status.HTTP_201_CREATED,
                               message="Успешное создание проекта",
                               result=ProjectSerializer(project).data)
        info(request.path, request.data, response.data)
        return response

    @swagger_auto_schema(
        operation_summary='Переименование проекта',
        request_body=ProjectUpdateSerializer,
        responses={201: ProjectSerializer},
        tags=[
            'Проекты'
        ]
    )
    def update(self, request: Request, pk=None):
        user = request.user
        project = Project.objects.filter(id=pk).first()
        if project is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.project_not_found,
                message=f"Проект с id={pk} не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        # if user.account_type == 'CLIENT' or (
        #         user.account_type == 'MANAGER' and project.owner != user):
        #     response = ApiErrorResponse(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         error_code=ApiErrorCodes.bad_credentials,
        #         message="У вас недостаточно прав для выполнения данного действия"
        #     )
        #     warning(request.path, request.data, response.data)
        #     return response

        serializer = ProjectUpdateSerializer(project, data=request.data, partial=True)

        if not serializer.is_valid():
            response = ApiErrorResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ApiErrorCodes.validation,
                message="Ошибка валидации",
                result=serializer.errors
            )
            warning(request.path, request.data, response.data)
            return response

        serializer.save()

        response = ApiResponse(status_code=status.HTTP_200_OK,
                               message=f'Проект с id={pk} успешно переименован',
                               result=ProjectSerializer(project).data)
        info(request.path, request.data, response.data)
        return response

    @swagger_auto_schema(
        operation_summary='Удаление проекта',
        responses={200: ProjectSerializer},
        tags=[
            'Проекты'
        ]
    )
    def destroy(self, request: Request, pk=None):
        user = request.user
        project = Project.objects.filter(id=pk).first()
        if project is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.project_not_found,
                message=f"Проект с id={pk} не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        # if user.account_type == 'CLIENT' or (
        #         user.account_type == 'MANAGER' and project.owner != user):
        #     response = ApiErrorResponse(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         error_code=ApiErrorCodes.bad_credentials,
        #         message="У вас недостаточно прав для выполнения данного действия"
        #     )
        #     warning(request.path, request.data, response.data)
        #     return response
        response = ApiResponse(message=f'Проект с id={pk} успешно удален',
                               result=ProjectSerializer(project).data)
        info(request.path, request.data, response.data)
        project.delete()
        return response

    @action(methods=['post'], url_path='ordering', permission_classes=[IsAuthenticated], detail=True)
    @swagger_auto_schema(
        operation_summary='Перенос товаров в корзину/создание заказа',
        responses={},
        manual_parameters=[
            Parameter(
                name='type',
                in_='query',
                description='Тип операции: "basket" - перенести товары в корзину\n '
                            '"order" - сделать сразу заказ',
                required=False,
                type='string',
            )
        ],
        tags=[
            'Проекты'
        ]
    )
    def ordering(self, request: Request, pk=None):
        user = request.user
        project = Project.objects.filter(id=pk).first()
        type_of_action = request.query_params.get('type')
        if project is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.project_not_found,
                message="Проект не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        # if user.account_type == 'CLIENT' or (
        #         user.account_type == 'MANAGER' and project.owner != user):
        #     response = ApiErrorResponse(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         error_code=ApiErrorCodes.bad_credentials,
        #         message="У вас недостаточно прав для выполнения данного действия"
        #     )
        #     warning(request.path, request.data, response.data)
        #     return response

        if type_of_action is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code=ApiErrorCodes.missing_parameters,
                message="Недостаточно парметров в запросе"
            )
            warning(request.path, request.data, response.data)
            return response
        if type_of_action not in {'basket', 'order'}:
            response = ApiErrorResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code=ApiErrorCodes.missing_parameters,
                message="Неправильный параметр запроса"
            )
            warning(request.path, request.data, response.data)
            return response

        if type_of_action == 'basket':
            basket = project.client.basket
            rooms_qs = Room.objects.filter(project=project)
            for room in rooms_qs:
                area_qs = Area.objects.filter(room=room)
                for area in area_qs:
                    items_qs = AreaItem.objects.filter(area=area)
                    if items_qs.first() is None:
                        response = ApiResponse(message='в проекте нет ни одного товара')
                        info(request.path, request.data, response.data)
                        return response
                    for item in items_qs:
                        old_basket_item = BasketItem.objects.filter(product=item.product,
                                                                    discount=item.discount).first()
                        if old_basket_item is not None:
                            old_basket_item.count += item.count
                            old_basket_item.save()
                        else:
                            BasketItem.objects.create(product=item.product,
                                                      count=item.count,
                                                      discount=item.discount,
                                                      basket=basket)

            response = ApiResponse(status_code=status.HTTP_200_OK,
                                   message='Товары успешно добавлены в корзину',
                                   result=BasketSerializer(basket).data)
            info(request.path, request.data, response.data)
            return response

        elif type_of_action == 'order':
            order = Order.objects.create(user=project.client,
                                         manager=project.owner)
            rooms_qs = Room.objects.filter(project=project)
            for room in rooms_qs:
                area_qs = Area.objects.filter(room=room)
                for area in area_qs:
                    items_qs = AreaItem.objects.filter(area=area)
                    if items_qs.first() is None:
                        response = ApiResponse(message='в проекте нет ни одного товара')
                        info(request.path, request.data, response.data)
                        return response
                    for item in items_qs:
                        old_order_item = OrderItem.objects.filter(product=item.product,
                                                                  discount=item.discount).first()
                        if old_order_item is not None:
                            old_order_item.count += item.count
                            old_order_item.save()
                        else:
                            BasketItem.objects.create(product=item.product,
                                                      count=item.count,
                                                      discount=item.discount,
                                                      order=order)
            response = ApiResponse(status_code=status.HTTP_200_OK,
                                   message='Товары успешно добавлены в заказ',
                                   result=OrderSerializer(order).data)
            info(request.path, request.data, response.data)
            return response

    @swagger_auto_schema(
        operation_summary='Получить список товаров',
        manual_parameters=[
            Parameter(
                name='manager_id',
                in_='query',
                description='ID менеджера',
                required=False,
                type='int',
            ),
            Parameter(
                name='id',
                in_='query',
                description='ID проекта',
                required=False,
                type='int',
            ),
            Parameter(
                name='offset',
                in_='query',
                description='Смещение от начала списка',
                required=False,
                type='int',
                default=0,
            ),
            Parameter(
                name='limit',
                in_='query',
                description='Количество элементов которое нужно вернуть',
                required=False,
                type='int',
            ),
            Parameter(
                name='query',
                in_='query',
                description='Поиск по названию',
                required=False,
                type='str',
            ),
            Parameter(
                name='sort',
                in_='query',
                description="Поля для сортировки. доступны следующие: \n"
                            "'title', '-title', 'id', '-id','create_at',\n"
                            "'-create_at', 'changed_at', '-changed_at', 'status', '-status',\n"
                            "'owner__last_name', '-owner__last_name'. минус перед полем - сортировка по убыванию",
                required=False,
                type='str',
            ),

        ],
        responses={},
        tags=['Проекты']
    )
    def list(self, request: Request):
        user = request.user
        projects_limit = self.request.query_params.get('limit')
        query = self.request.query_params.get('query')

        if user.account_type == 'CLIENT':
            projects_qs = Project.objects.filter(client=user)
        if user.account_type == 'MANAGER':
            projects_qs = Project.objects.filter(
                Q(owner=user) | Q(owner__manager=user)

            )
        if user.account_type == 'ADMIN':
            projects_qs = Project.objects.all()

        manager_id_filter = request.query_params.get('manager_id')
        if manager_id_filter:
            projects_qs = projects_qs.filter(owner=manager_id_filter)

        id_filter = request.query_params.get('id')
        if id_filter:
            projects_qs = projects_qs.filter(id=id_filter)

        if 'sort' in request.query_params:
            sort = self.request.query_params.get('sort')
            if sort in {'title', '-title', 'id', '-id',
                        'create_at', '-create_at', 'changed_at', '-changed_at', 'status', '-status',
                        'owner__last_name', '-owner__last_name'}:
                projects_qs = projects_qs.order_by(sort)

        total_count = projects_qs.count()

        if query is not None:
            projects_qs = projects_qs.filter(title__icontains=query)

        if 'offset' in request.query_params:
            offset = int(self.request.query_params.get('offset'))
        else:
            offset = 0

        projects_qs = projects_qs[offset:]
        if projects_limit is not None:
            paginator = Paginator(projects_qs, projects_limit)
            current_page = paginator.get_page(1)
        else:
            current_page = projects_qs
        serializer = ProjectSerializer(current_page, many=True)
        result = ({'total_count': total_count, 'projects': serializer.data})

        response = ApiResponse(result=result)
        info(request.path, request.data, response.data)
        return response

    @swagger_auto_schema(
        operation_summary='Получить 1 проект по его id',
        tags=['Проекты']
    )
    def retrieve(self, request: Request, pk=None):
        currency = request.query_params.get('currency') or Currencies.byn
        print(1)
        user = request.user
        if user.account_type == 'CLIENT':
            project = Project.objects.filter(client=user, id=pk).first()
        if user.account_type == 'MANAGER':
            project = Project.objects.filter(Q(owner=user) | Q(owner__manager=user), id=pk).first()
        if user.account_type == 'ADMIN':
            project = Project.objects.filter(id=pk).first()
        print(2)
        if project is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.project_not_found,
                message="Проект не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        print(3)
        serializer = ProjectSerializer(project)
        result = serializer.data
        total_sum = 0.0
        rooms = Room.objects.filter(project=project).select_related('project').order_by('position')
        result['rooms'] = []
        result['type'] = 'project'

        for room in rooms:
            room_data = RoomSerializer(room).data
            room_data['areas'] = []
            room_data['type'] = 'room'
            print(4.1)
            for area in Area.objects.filter(room=room).select_related('room').order_by('position'):
                area_data = AreaSerializer(area).data
                area_items_qs = AreaItem.objects.filter(area=area).select_related('area', 'product').order_by('id')
                area_items = []
                print(4.2)
                for area_item in area_items_qs:
                    # todo Скорректировать отображение цены в соответсвтии с уровнем цены и указаной валютой
                    area_item_data = AreaItemSerializer(area_item, context={
                        'currency': currency,
                        'user_price_level': user.price_level,
                    }).data
                    product_price = ProductPrice.objects.filter(
                        product__id=area_item.product.id,
                        price_level=get_price_level(user.price_level, currency)
                    ).first()
                    price = area_item_data.get('price') or 0
                    # if product_price is not None:
                    #     price = product_price.price
                    # area_item_data['product']['price'] = price
                    total_sum += area_item.count * (price - price * (area_item.discount / 100.0))
                    area_items.append(area_item_data)
                    print(4.3)
                area_data['items'] = area_items
                area_data['type'] = 'area'
                room_data['areas'].append(area_data)
                print(4.4)
            result['rooms'].append(room_data)
        print(5)
        result['totalSum'] = total_sum

        response = ApiResponse(result=result)
        info(request.path, request.data, response.data)
        print(6)
        return response

    @action(methods=['get'], url_path='export', permission_classes=[IsAuthenticated], detail=True)
    @swagger_auto_schema(
        operation_summary='Экспорт в PDF',
        tags=['Проекты']
    )
    def export(self, request: Request, pk=None):
        currency = request.query_params.get('currency') or Currencies.byn
        print('Export сбор информации...')
        # todo Скорректировать отображение цены в соответсвтии с уровнем цены и указаной валютой
        user = request.user
        specification = request.query_params.get('specification') or 'rooms'
        include_images = 'include_images' in request.query_params
        include_properties = 'include_properties' in request.query_params

        project = Project.objects.filter(id=pk).first()
        owner = {
            'full_name': project.owner.last_name + ' ' + project.owner.first_name + ' ' + project.owner.middle_name,
            'email': project.owner.email,
            'phone': project.owner.phone
        }
        env = Environment(loader=FileSystemLoader(settings.EXPORT_PDF_TEMPLATE_DIR))
        rooms = []
        area_items_by_category = {}
        project_total_amount = 0
        export_settings = {
            "specification": specification,  # 'rooms' or 'products',
            "include_images": include_images,
            "include_properties": include_properties,
        }

        project_data = {
            'title': f'{project.title}',
            'number': f'{project.id}',
            'rooms': [],
        }
        project_number = int(project_data.get('number'))

        if export_settings['specification'] == "rooms":
            for room in Room.objects.filter(project=project).select_related('project').order_by('position'):
                room_total_amount = 0
                room_data = RoomSerializer(room).data
                room_data['areas'] = []
                for area in Area.objects.filter(room=room).order_by('position'):
                    area_total_amount = 0
                    area_data = AreaSerializer(area).data
                    area_data['area_items'] = []
                    for area_item in AreaItem.objects.filter(area=area):
                        area_item_data = AreaItemSerializer(area_item, context={
                            'currency': currency,
                            'user_price_level': user.price_level,
                        }).data
                        product_image_path = str(area_item.product.image).split('/')[-1]
                        if area_item.product.image:
                            product_image = settings.PRODUCTS_IMAGES_DIR + '/' + product_image_path
                        elif area_item.product.image_url != '':
                            file_name = area_item.product.image_url.split('/')[-1]
                            product_image = os.path.join(settings.MEDIA_ROOT, file_name)
                        else:
                            product_image = '/code/byled/static/images/no_photo.png'
                        if product_image != '/code/byled/static/images/no_photo.png':
                            product_image = product_image[:len(product_image) - 4] + "-thumbnail.png"
                        area_item_data['product_image'] = product_image
                        area_item_data['no_blank_properties'] = area_item.product.get_no_blank_properties()
                        area_data['area_items'].append(area_item_data)
                        product_price = ProductPrice.objects.filter(
                            product__id=area_item.product.id,
                            price_level=get_price_level(user.price_level, currency)
                        ).first()
                        price = area_item_data.get('price')

                        # if product_price is not None:
                        #     price = product_price.price
                        # area_item_data['product']['price'] = price
                        area_total_amount += price * area_item.count
                        print('PRICE: ', price, area_total_amount)
                    area_data['total_amount'] = area_total_amount
                    room_data['areas'].append(area_data)
                    room_total_amount += area_total_amount
                room_data['total_amount'] = room_total_amount
                rooms.append(room_data)
                project_total_amount += room_total_amount
                project_data['rooms'].append(room_data)
        else:

            for room in Room.objects.filter(project=project):
                room_total_amount = 0
                for area in Area.objects.filter(room=room):
                    area_total_amount = 0
                    for area_item in AreaItem.objects.filter(area=area):
                        area_item_data = AreaItemSerializer(area_item, context={
                            'currency': currency,
                            'user_price_level': user.price_level,
                        }).data
                        product_image_path = str(area_item.product.image).split('/')[-1]
                        if area_item.product.image:
                            product_image = settings.PRODUCTS_IMAGES_DIR + '/' + product_image_path
                        elif area_item.product.image_url != '':
                            file_name = area_item.product.image_url.split('/')[-1]
                            product_image = os.path.join(settings.MEDIA_ROOT, file_name)
                        else:
                            product_image = '/code/byled/static/images/no_photo.png'
                        if product_image != '/code/byled/static/images/no_photo.png':
                            product_image = product_image[:len(product_image) - 4] + "-thumbnail.png"
                        area_item_data['product_image'] = product_image
                        area_item_data['no_blank_properties'] = area_item.product.get_no_blank_properties()

                        if area_item.product.category not in area_items_by_category:
                            area_items_by_category[area_item.product.category] = {
                                "total_amount": 0,
                                "area_items": [],
                            }
                        area_items_by_category[area_item.product.category]['area_items'].append(area_item_data)
                        product_price = ProductPrice.objects.filter(
                            product__id=area_item.product.id,
                            price_level=get_price_level(user.price_level, currency)
                        ).first()
                        price = area_item_data.get('price')
                        # if product_price is not None:
                        #     price = product_price.price
                        # area_item_data['product']['price'] = price
                        area_total_amount += price * area_item.count
                        area_items_by_category[area_item.product.category][
                            'total_amount'
                        ] += price * area_item.count

                    room_total_amount += area_total_amount
                project_total_amount += room_total_amount
            project_data['product_groups'] = area_items_by_category
        project_data['total_amount'] = project_total_amount
        print('Генерация PDF...')
        print('project_data: ', project_data)

        pdf = PDF(export_settings=export_settings, owner=owner, orientation='P', unit='pt', format='A4',
                  currency=currency)
        pdf.set_auto_page_break(auto=False)
        # pdf_conf = PDFConf(export_settings)
        print('Загрузка шрифтов')
        # Загрузка шрифта, установка цвета заливки
        pdf.add_font(family='MontserratLight',
                     fname='/code/export-templates/assets/fonts/Montserrat-Light.ttf', uni=True)
        pdf.add_font(family='MontserratSemiBold',
                     fname='/code//export-templates/assets/fonts/Montserrat-SemiBold.ttf', uni=True)
        pdf.add_font(family='MontserratMedium',
                     fname='/code//export-templates/assets/fonts/Montserrat-Medium.ttf', uni=True)
        pdf.add_font(family='MontserratThin',
                     fname='/code//export-templates/assets/fonts/Montserrat-Thin.ttf', uni=True)
        pdf.add_font(family='MontserratRegular',
                     fname='/code//export-templates/assets/fonts/Montserrat-Regular.ttf', uni=True)

        # print(project)
        # print(project_total_amount)
        # print(export_settings)
        #
        # print(area_items_by_category)
        #
        # # todo Трогать для новой генерации нужно только то что ниже (наверное). То что выше - сбор данных
        # pdf = PDF('P', 'pt', 'A4')
        #
        pdf.draw_title_page()
        pdf.add_page()
        pdf.draw_page_header(project_number)
        pdf.draw_table_header()

        # алгоритм по зонам
        if export_settings['specification'] == 'rooms':
            for room in project_data.get('rooms'):
                if not room.get('is_visible'):
                    continue
                areas = room.get('areas')
                for i in range(len(areas)):
                    area = areas[i]
                    if not area.get('is_visible'):
                        continue
                    if i == 0:
                        include_rooms = True
                    else:
                        include_rooms = False
                    if not pdf.page_break_if_needed(project_number=project_number, room=room, area=area,
                                                    include_room=include_rooms):
                        print('DRAW ROOM AND ZONE, AREA: ', area)
                        pdf.draw_room_and_zone_section(room, area, include_room=include_rooms)
                    product_number = 1
                    for area_item in area.get('area_items'):
                        pdf.page_break_if_needed(project_number=project_number, room=room, area=area)
                        pdf.move_cursor_next_row()
                        pdf.draw_area_item(product_number, area_item)
                        product_number += 1
                    pdf.move_cursor_next_row()

        if export_settings['specification'] == 'products':
            product_groups = project_data.get('product_groups')
            for product_group in product_groups.keys():
                if not pdf.page_break_if_needed(project_number=project_number, product_group_name=product_group,
                                                product_group=product_groups[product_group]):
                    pdf.draw_product_group_section(product_group, product_groups[product_group])
                product_number = 1
                area_items = product_groups[product_group]['area_items']

                area_items_by_product_id = {}
                for area_item in area_items:
                    product_id = area_item.get('product').get('id')
                    if product_id not in area_items_by_product_id:
                        area_items_by_product_id[product_id] = area_item
                    else:
                        area_items_by_product_id[product_id]['count'] += area_item.get('count')
                area_items = list(area_items_by_product_id.values())

                print('area_items', area_items)
                for i in range(len(area_items)):
                    pdf.page_break_if_needed(project_number=project_number, product_group_name=product_group,
                                             product_group=product_groups[product_group])
                    area_item = area_items[i]
                    pdf.move_cursor_next_row()
                    pdf.draw_area_item(product_number, area_item)
                    product_number += 1

        pdf.draw_project_amount(project_data)
        pdf.draw_page_footer()

        file_uuid = str(uuid.uuid4())
        pdf.output(f'{settings.EXPORT_PDF_TEMPLATE_DIR}/{file_uuid}.pdf', 'F')

        response = FileResponse(open(f'{settings.EXPORT_PDF_TEMPLATE_DIR}/{file_uuid}.pdf', 'rb'),
                                filename=f'{file_uuid}.pdf',
                                content_type='application/force-download')
        return response


class RoomViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    @swagger_auto_schema(
        operation_summary='Добавление(создание) нового помещения',
        request_body=RoomCreateUpdateSerializer,
        responses={201: RoomSerializer},
        tags=[
            'Помещения'
        ]
    )
    def create(self, request: Request, project_pk=None):
        user = request.user
        project = Project.objects.filter(id=project_pk).first()
        serializer = RoomCreateUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            resp = ApiErrorResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ApiErrorCodes.validation,
                message="Ошибка валидации",
                result=serializer.errors
            )
            warning(request.path, request.data, resp.data)
            return resp

        if project is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.project_not_found,
                message=f"Проект с id={project_pk} не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        # if user.account_type == 'CLIENT' or (
        #         user.account_type == 'MANAGER' and project.owner != user):
        #     response = ApiErrorResponse(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         error_code=ApiErrorCodes.bad_credentials,
        #         message="У вас недостаточно прав для выполнения данного действия"
        #     )
        #     warning(request.path, request.data, response.data)
        #     return response
        last_room = Room.objects.filter(project=project).order_by('position').last()
        if last_room is None:
            highest_position = 0
        else:
            highest_position = last_room.position + 1
        room = Room.objects.create(title=serializer.validated_data['title'],
                                   project=project,
                                   position=highest_position)
        response = ApiResponse(status_code=status.HTTP_201_CREATED,
                               message="Успешное создание помещения",
                               result=RoomSerializer(room).data)
        info(request.path, request.data, response.data)
        return response

    @swagger_auto_schema(
        operation_summary='Переименование помещения',
        request_body=RoomCreateUpdateSerializer,
        responses={200: RoomSerializer},
        tags=[
            'Помещения'
        ]
    )
    def update(self, request: Request, pk=None, project_pk=None):
        user = request.user
        project = Project.objects.filter(id=project_pk).first()
        if project is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.project_not_found,
                message=f"Проект с id={pk} не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        # if user.account_type == 'CLIENT' or (
        #         user.account_type == 'MANAGER' and project.owner != user):
        #     response = ApiErrorResponse(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         error_code=ApiErrorCodes.bad_credentials,
        #         message="У вас недостаточно прав для выполнения данного действия"
        #     )
        #     warning(request.path, request.data, response.data)
        #     return response
        room = Room.objects.filter(id=pk).first()
        if room is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.project_not_found,
                message=f"Помещение id={project_pk} не найдено",
            )
            warning(request.path, request.data, response.data)
            return response
        if room.project != project:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.project_not_found,
                message=f"Помещение с id={pk} не относится к данному проекту",
            )
            warning(request.path, request.data, response.data)
            return response

        serializer = RoomCreateUpdateSerializer(room, data=request.data)

        if not serializer.is_valid():
            response = ApiErrorResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ApiErrorCodes.validation,
                message="Ошибка валидации",
                result=serializer.errors
            )
            warning(request.path, request.data, response.data)
            return response

        serializer.save()

        response = ApiResponse(status_code=status.HTTP_200_OK,
                               message='Данные успешно обновлены',
                               result=RoomSerializer(room).data)
        info(request.path, request.data, response.data)
        return response

    @swagger_auto_schema(
        operation_summary='Удаление помещения',
        responses={200: RoomSerializer},
        tags=[
            'Помещения'
        ]
    )
    def destroy(self, request: Request, pk=None, project_pk=None):
        user = request.user
        project = Project.objects.filter(id=project_pk).first()
        if project is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.project_not_found,
                message=f"Проект с id={project_pk} не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        # if user.account_type == 'CLIENT' or (
        #         user.account_type == 'MANAGER' and project.owner != user):
        #     response = ApiErrorResponse(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         error_code=ApiErrorCodes.bad_credentials,
        #         message="У вас недостаточно прав для выполнения данного действия"
        #     )
        #     warning(request.path, request.data, response.data)
        #     return response
        room = Room.objects.filter(id=pk).first()
        if room is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение с id={pk} не найдено",
            )
            warning(request.path, request.data, response.data)
            return response
        if room.project != project:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение с id={pk} не относится к данному проекту",
            )
            warning(request.path, request.data, response.data)
            return response
        high_rooms = Room.objects.filter(project=project_pk,
                                         position__gt=room.position)  # берем комнаты с иерархией выше чем удаляемая
        for high_room in high_rooms:
            high_room.position -= 1  # и уменьшаем их позицию на 1
            high_room.save()
        response = ApiResponse(message=f'Помещение с id={pk} успешно удалено',
                               status_code=status.HTTP_200_OK,
                               result=RoomSerializer(room).data)
        info(request.path, request.data, response.data)
        room.delete()
        return response

    @action(detail=True, methods=['post'], url_path='changevisible')
    @swagger_auto_schema(
        operation_summary='Скрытие/открытие помещения',
        responses={200: RoomSerializer},
        tags=[
            'Помещения'
        ]
    )
    def changevisible(self, request: Request, pk=None, project_pk=None):
        user = request.user
        project = Project.objects.filter(id=project_pk).first()
        if project is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.project_not_found,
                message=f"Проект с id={project_pk} не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        # if user.account_type == 'CLIENT' or (
        #         user.account_type == 'MANAGER' and project.owner != user):
        #     response = ApiErrorResponse(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         error_code=ApiErrorCodes.bad_credentials,
        #         message="У вас недостаточно прав для выполнения данного действия"
        #     )
        #     warning(request.path, request.data, response.data)
        #     return response
        room = Room.objects.filter(id=pk).first()
        if room is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение с id={pk} не найдено",
            )
            warning(request.path, request.data, response.data)
            return response
        if room.project != project:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение с id={pk} не относится к данному проекту",
            )
            warning(request.path, request.data, response.data)
            return response
        if room.is_visible is True:
            room.is_visible = False
            response = ApiResponse(message=f'Комната с id={pk} успешно скрыта',
                                   status_code=status.HTTP_200_OK,
                                   result=RoomSerializer(room).data)
            info(request.path, request.data, response.data)
            room.save()
        else:
            room.is_visible = True
            response = ApiResponse(message=f'Комната с id={pk} успешно открыта',
                                   status_code=status.HTTP_200_OK,
                                   result=RoomSerializer(room).data)
            info(request.path, request.data, response.data)
            room.save()
        return response

    @action(detail=True, methods=['post'], url_path='changeposition')
    @swagger_auto_schema(
        operation_summary='Перемещение помещения в иерархии',
        manual_parameters=[
            Parameter(
                name='direction',
                in_='query',
                description='Направление перемещения. up - выше, down - ниже',
                required=False,
                type='str',
            )],
        responses={200: RoomSerializer},
        tags=[
            'Помещения'
        ]
    )
    def changeposition(self, request: Request, pk=None, project_pk=None):
        user = request.user
        project = Project.objects.filter(id=project_pk).first()
        if project is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.project_not_found,
                message=f"Проект с id={project_pk} не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        # if user.account_type == 'CLIENT' or (
        #         user.account_type == 'MANAGER' and project.owner != user):
        #     response = ApiErrorResponse(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         error_code=ApiErrorCodes.bad_credentials,
        #         message="У вас недостаточно прав для выполнения данного действия"
        #     )
        #     warning(request.path, request.data, response.data)
        #     return response
        room = Room.objects.filter(id=pk).first()
        if room is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение id={pk} не найдено",
            )
            warning(request.path, request.data, response.data)
            return response
        if room.project != project:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение с id={pk} не относится к данному проекту",
            )
            warning(request.path, request.data, response.data)
            return response
        direction = self.request.query_params.get('direction')
        if direction is None or direction not in {'up', 'down'}:
            response = ApiErrorResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code=ApiErrorCodes.missing_parameters,
                message="Не указан параметр направления перемещения",
            )
            warning(request.path, request.data, response.data)
            return response
        if direction == 'down':
            moving_room = Room.objects.filter(position=room.position + 1).first()
            if moving_room is None:
                response = ApiErrorResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error_code=ApiErrorCodes.validation,
                    message="Невозможно переместить: помещение самое нижнее в иерархии",
                )
                warning(request.path, request.data, response.data)
                return response
            else:
                moving_room.position -= 1
                room.position += 1
                moving_room.save()
                room.save()
                response = ApiResponse(message=f'Помещение с id={pk} успешно перемещено',
                                       status_code=status.HTTP_200_OK,
                                       result=RoomSerializer(room).data)
                info(request.path, request.data, response.data)
                return response
        if direction == 'up':
            moving_room = Room.objects.filter(position=room.position - 1).first()
            if moving_room is None:
                response = ApiErrorResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error_code=ApiErrorCodes.validation,
                    message="Невозможно переместить: помещение самое верхнее в иерархии",
                )
                warning(request.path, request.data, response.data)
                return response
            else:
                moving_room.position += 1
                room.position -= 1
                moving_room.save()
                room.save()
                response = ApiResponse(message=f'Помещение id={pk} успешно перемещено',
                                       status_code=status.HTTP_200_OK,
                                       result=RoomSerializer(room).data)
                info(request.path, request.data, response.data)
                return response

    @action(detail=True, methods=['post'], url_path='copy')
    @swagger_auto_schema(
        operation_summary='Копирование помещения (со всеми входящими элементами)',
        responses={200: RoomSerializer},
        manual_parameters=[
            Parameter(
                name='destination_project_id',
                in_='query',
                description='id проекта в который скопировать помещение',
                required=False,
                type='int',
            )],
        tags=[
            'Помещения'
        ]
    )
    def copy(self, request: Request, pk=None, project_pk=None):
        user = request.user
        dest_project_id = self.request.query_params.get('destination_project_id')
        if dest_project_id:
            destination_project = Project.objects.filter(id=int(dest_project_id)).first()
        else:
            destination_project = Project.objects.filter(id=project_pk).first()

        if destination_project is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.project_not_found,
                message=f"Проект id={project_pk} не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        project = Project.objects.filter(id=project_pk).first()
        if project is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.project_not_found,
                message=f"Проект id={project_pk} не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        # if user.account_type == 'CLIENT' or (
        #         user.account_type == 'MANAGER' and project.owner != user):
        #     response = ApiErrorResponse(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         error_code=ApiErrorCodes.bad_credentials,
        #         message="У вас недостаточно прав для выполнения данного действия"
        #     )
        #     warning(request.path, request.data, response.data)
        #     return response
        room = Room.objects.filter(id=pk).first()
        if room is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.project_not_found,
                message=f"Помещение id={pk} не найдено",
            )
            warning(request.path, request.data, response.data)
            return response
        if room.project != project:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение с id={pk} не относится к данному проекту",
            )
            warning(request.path, request.data, response.data)
            return response
        last_room = Room.objects.filter(project=project).order_by('position').last()
        highest_position = last_room.position + 1
        copy_room = Room.objects.create(title=room.title,
                                        project=destination_project,
                                        position=highest_position)
        areas = Area.objects.filter(room=room)
        for area in areas:
            new_area = Area.objects.create(room=copy_room,
                                           title=area.title,
                                           position=area.position)
            items = AreaItem.objects.filter(area=area)
            for item in items:
                new_item = AreaItem.objects.create(area=new_area,
                                                   count=item.count,
                                                   discount=item.discount,
                                                   product=item.product)

        response = ApiResponse(status_code=status.HTTP_201_CREATED,
                               message="Успешное создание копии помещения",
                               result=RoomSerializer(copy_room).data)
        info(request.path, request.data, response.data)
        return response

    @swagger_auto_schema(
        operation_summary='Получить список помещений',
        manual_parameters=[
            Parameter(
                name='offset',
                in_='query',
                description='Смещение от начала списка',
                required=False,
                type='int',
                default=0,
            ),
            Parameter(
                name='limit',
                in_='query',
                description='Количество элементов которое нужно вернуть',
                required=False,
                type='int',
            ),
        ],
        responses={},
        tags=['Помещения']
    )
    def list(self, request: Request, project_pk=None):
        user = request.user
        project = Project.objects.filter(id=project_pk).first()
        rooms_limit = self.request.query_params.get('limit')
        if project is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.project_not_found,
                message=f"Проект с id={project_pk} не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        # if (user.account_type == 'CLIENT' and project.client != user) or (
        #         user.account_type == 'MANAGER' and project.owner != user):
        #     response = ApiErrorResponse(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         error_code=ApiErrorCodes.bad_credentials,
        #         message="У вас недостаточно прав для выполнения данного действия"
        #     )
        #     warning(request.path, request.data, response.data)
        #     return response

        rooms_qs = Room.objects.filter(project=project).order_by('-position')

        total_count = rooms_qs.count()

        if 'offset' in request.query_params:
            offset = int(self.request.query_params.get('offset'))
        else:
            offset = 0

        projects_qs = rooms_qs[offset:]
        if rooms_limit is not None:
            paginator = Paginator(projects_qs, rooms_limit)
            current_page = paginator.get_page(1)
        else:
            current_page = projects_qs
        serializer = RoomSerializer(current_page, many=True)
        result = ({'total_count': total_count, 'rooms': serializer.data})

        response = ApiResponse(result=result)
        info(request.path, request.data, response.data)
        return response

    @swagger_auto_schema(
        operation_summary='Получить 1 помещение (в конкретном проекте) по его id',
        tags=['Помещения']
    )
    def retrieve(self, request: Request, pk=None, project_pk=None):
        user = request.user
        if user.account_type == 'CLIENT':
            project = Project.objects.filter(client=user, id=project_pk).first()
        if user.account_type == 'MANAGER':
            project = Project.objects.filter(owner=user, id=project_pk).first()
        if user.account_type == 'ADMIN':
            project = Project.objects.filter(id=project_pk).first()
        if project is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.project_not_found,
                message="Проект не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        room = Room.objects.filter(id=pk).first()
        if room is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение id={pk} не найдено",
            )
            warning(request.path, request.data, response.data)
            return response
        if room.project != project:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение с id={pk} не относится к данному проекту",
            )
            warning(request.path, request.data, response.data)
            return response
        serializer = RoomSerializer(room)
        response = ApiResponse(result=serializer.data)
        info(request.path, request.data, response.data)
        return response


class AreaViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    @swagger_auto_schema(
        operation_summary='Добавление(создание) новой зоны',
        request_body=AreaCreateUpdateSerializer,
        responses={201: AreaSerializer},
        tags=[
            'Зоны'
        ]
    )
    def create(self, request: Request, project_pk=None, room_pk=None):
        user = request.user
        serializer = AreaCreateUpdateSerializer(data=request.data)
        project = Project.objects.filter(id=project_pk).first()
        room = Room.objects.filter(id=room_pk).first()
        if not serializer.is_valid():
            response = ApiErrorResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ApiErrorCodes.validation,
                message="Ошибка валидации",
                result=serializer.errors
            )
            warning(request.path, request.data, response.data)
            return response

        if project is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.project_not_found,
                message=f"Проект с id={project_pk} не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        # if user.account_type == 'CLIENT' or (user.account_type == 'MANAGER' and project.owner != user):
        #     response = ApiErrorResponse(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         error_code=ApiErrorCodes.bad_credentials,
        #         message="У вас недостаточно прав для выполнения данного действия"
        #     )
        #     warning(request.path, request.data, response.data)
        #     return response
        if room is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение с id={room_pk} не найдено",
            )
            warning(request.path, request.data, response.data)
            return response
        if room.project != project:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение с id={room_pk} не относится к данному проекту",
            )
            warning(request.path, request.data, response.data)
            return response
        last_area = Area.objects.filter(room=room).order_by('position').last()
        if last_area is None:
            highest_position = 0
        else:
            highest_position = last_area.position + 1
        area = Area.objects.create(title=serializer.validated_data['title'],
                                   room=room,
                                   position=highest_position)
        response = ApiResponse(status_code=status.HTTP_201_CREATED,
                               message="Успешное создание зоны",
                               result=AreaSerializer(area).data)
        info(request.path, request.data, response.data)
        return response

    @swagger_auto_schema(
        operation_summary='Переименование зоны',
        request_body=AreaCreateUpdateSerializer,
        responses={201: AreaSerializer},
        tags=[
            'Зоны'
        ]
    )
    def update(self, request: Request, project_pk=None, room_pk=None, pk=None):
        user = request.user
        serializer = AreaCreateUpdateSerializer(data=request.data)
        project = Project.objects.filter(id=project_pk).first()
        room = Room.objects.filter(id=room_pk).first()
        area = Area.objects.filter(id=pk).first()
        if not serializer.is_valid():
            response = ApiErrorResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ApiErrorCodes.validation,
                message="Ошибка валидации",
                result=serializer.errors
            )
            warning(request.path, request.data, response.data)
            return response

        if project is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.project_not_found,
                message=f"Проект с id={project_pk} не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        # if user.account_type == 'CLIENT' or (user.account_type == 'MANAGER' and project.owner != user):
        #     response = ApiErrorResponse(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         error_code=ApiErrorCodes.bad_credentials,
        #         message="У вас недостаточно прав для выполнения данного действия"
        #     )
        #     warning(request.path, request.data, response.data)
        #     return response
        if room is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение с id={room_pk} не найдено",
            )
            warning(request.path, request.data, response.data)
            return response
        if room.project != project:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение с id={room_pk} не относится к данному проекту",
            )
            warning(request.path, request.data, response.data)
            return response
        if area is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.area_not_found,
                message=f"Зона с id={pk} не найдена",
            )
            warning(request.path, request.data, response.data)
            return response
        if area.room != room:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.area_not_found,
                message=f"Зона с id={pk} не относится к данному помещению",
            )
            warning(request.path, request.data, response.data)
            return response

        serializer = AreaCreateUpdateSerializer(area, data=request.data)

        if not serializer.is_valid():
            response = ApiErrorResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ApiErrorCodes.validation,
                message="Ошибка валидации",
                result=serializer.errors
            )
            warning(request.path, request.data, response.data)
            return response

        serializer.save()

        response = ApiResponse(message='Данные успешно обновлены',
                               status_code=status.HTTP_200_OK,
                               result=AreaSerializer(area).data)
        info(request.path, request.data, response.data)
        return response

    @swagger_auto_schema(
        operation_summary='Удаление зоны',
        request_body=AreaCreateUpdateSerializer,
        responses={201: AreaSerializer},
        tags=[
            'Зоны'
        ]
    )
    def destroy(self, request: Request, project_pk=None, room_pk=None, pk=None):
        user = request.user
        project = Project.objects.filter(id=project_pk).first()
        room = Room.objects.filter(id=room_pk).first()
        area = Area.objects.filter(id=pk).first()

        if project is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.project_not_found,
                message=f"Проект с уid={project_pk} не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        # if user.account_type == 'CLIENT' or (user.account_type == 'MANAGER' and project.owner != user):
        #     response = ApiErrorResponse(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         error_code=ApiErrorCodes.bad_credentials,
        #         message="У вас недостаточно прав для выполнения данного действия"
        #     )
        #     warning(request.path, request.data, response.data)
        #     return response
        if room is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение с id={room_pk} не найдено",
            )
            warning(request.path, request.data, response.data)
            return response
        if room.project != project:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение с id={room_pk} не относится к данному проекту",
            )
            warning(request.path, request.data, response.data)
            return response
        if area is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.area_not_found,
                message=f"Зона с id={pk} не найдена",
            )
            warning(request.path, request.data, response.data)
            return response
        if area.room != room:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.area_not_found,
                message=f"Зона с id={pk} не относится к данному помещению",
            )
            warning(request.path, request.data, response.data)
            return response
        high_areas = Area.objects.filter(room=room_pk,
                                         position__gt=area.position)  # берем зоны с иерархией выше чем удаляемая
        for high_area in high_areas:
            high_area.position -= 1  # и уменьшаем их позицию на 1
            high_area.save()
        response = ApiResponse(message=f'Зона с id={pk} успешно удалена',
                               status_code=status.HTTP_200_OK,
                               result=AreaSerializer(area).data)
        info(request.path, request.data, response.data)
        area.delete()
        return response

    @action(detail=True, methods=['post'], url_path='changevisible')
    @swagger_auto_schema(
        operation_summary='Скрытие/открытие зоны',
        responses={201: AreaSerializer},
        tags=[
            'Зоны'
        ]
    )
    def changevisible(self, request: Request, pk=None, project_pk=None, room_pk=None):
        user = request.user
        project = Project.objects.filter(id=project_pk).first()
        room = Room.objects.filter(id=room_pk).first()
        area = Area.objects.filter(id=pk).first()
        if project is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.project_not_found,
                message=f"Проект с id={project_pk} не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        # if user.account_type == 'CLIENT' or (user.account_type == 'MANAGER' and project.owner != user):
        #     response = ApiErrorResponse(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         error_code=ApiErrorCodes.bad_credentials,
        #         message="У вас недостаточно прав для выполнения данного действия"
        #     )
        #     warning(request.path, request.data, response.data)
        #     return response
        if room is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение с id={room_pk} не найдено",
            )
            warning(request.path, request.data, response.data)
            return response
        if room.project != project:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение с id={room_pk} не относится к данному проекту",
            )
            warning(request.path, request.data, response.data)
            return response
        if area is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.area_not_found,
                message=f"Зона с id={pk} не найдена",
            )
            warning(request.path, request.data, response.data)
            return response
        if area.room != room:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.area_not_found,
                message=f"Зона с id={pk} не относится к данному помещению",
            )
            warning(request.path, request.data, response.data)
            return response
        area.is_visible = not area.is_visible
        area.save()
        message = f'Зона с id={pk} успешно открыта' if area.is_visible else f'Зона с id={pk} успешно скрыта'
        response = ApiResponse(
            message=message,
            status_code=status.HTTP_200_OK,
            result=AreaSerializer(area).data
        )

        info(request.path, request.data, response.data)
        return response

    @action(detail=True, methods=['post'], url_path='changeposition')
    @swagger_auto_schema(
        operation_summary='Перемещение зоны в иерархии',
        manual_parameters=[
            Parameter(
                name='direction',
                in_='query',
                description='Направление перемещения. up - выше, down - ниже',
                required=False,
                type='str'
            )],
        responses={200: AreaSerializer},
        tags=[
            'Зоны'
        ]
    )
    def changeposition(self, request: Request, pk=None, project_pk=None, room_pk=None):
        user = request.user
        project = Project.objects.filter(id=project_pk).first()
        room = Room.objects.filter(id=room_pk).first()
        area = Area.objects.filter(id=pk).first()
        if project is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.project_not_found,
                message=f"Проект с id={project_pk} не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        # if user.account_type == 'CLIENT' or (user.account_type == 'MANAGER' and project.owner != user):
        #     response = ApiErrorResponse(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         error_code=ApiErrorCodes.bad_credentials,
        #         message="У вас недостаточно прав для выполнения данного действия"
        #     )
        #     warning(request.path, request.data, response.data)
        #     return response
        # if user.account_type == 'CLIENT' or (user.account_type == 'MANAGER' and project.owner != user):
        #     response = ApiErrorResponse(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         error_code=ApiErrorCodes.bad_credentials,
        #         message="У вас недостаточно прав для выполнения данного действия"
        #     )
        #     warning(request.path, request.data, response.data)
        #     return response
        if room is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение с id={room_pk} не найдено",
            )
            warning(request.path, request.data, response.data)
            return response
        if room.project != project:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение с id={room_pk} не относится к данному проекту",
            )
            warning(request.path, request.data, response.data)
            return response
        if area is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.area_not_found,
                message=f"Зона с id={pk} не найдена",
            )
            warning(request.path, request.data, response.data)
            return response
        if area.room != room:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.area_not_found,
                message=f"Зона с id={pk} не относится к данному помещению",
            )
            warning(request.path, request.data, response.data)
            return response
        direction = self.request.query_params.get('direction')
        if direction is None or direction not in {'up', 'down'}:
            response = ApiErrorResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code=ApiErrorCodes.validation,
                message="Не указан параметр направления перемещения",
            )
            warning(request.path, request.data, response.data)
            return response
        areas_list = Area.objects.filter(room=room).order_by('position')
        area_index = -1
        for index, item in enumerate(areas_list):
            if item == area:
                area_index = index
                break
        print(areas_list)
        print(area_index)
        if area_index < 0:
            response = ApiErrorResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code=ApiErrorCodes.validation,
                message="Зона не найдена",
            )
            warning(request.path, request.data, response.data)
            return response
        if direction == 'up':
            if area_index == 0:
                response = ApiErrorResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error_code=ApiErrorCodes.validation,
                    message="Невозможно переместить: зона самая верхняя в иерархии",
                )
                warning(request.path, request.data, response.data)
                return response
            second_area = areas_list[area_index - 1]
            second_area.position = area_index
            area.position = area_index - 1
            second_area.save()
            area.save()
            response = ApiResponse(message=f'Зона с id={pk} успешно перемещена',
                                   status_code=status.HTTP_200_OK,
                                   result=AreaSerializer(area).data)
            info(request.path, request.data, response.data)
            return response

            # moving_area = Area.objects.filter(position=area.position + 1).first()
            # if moving_area is None:
            #     response = ApiErrorResponse(
            #         status_code=status.HTTP_400_BAD_REQUEST,
            #         error_code=ApiErrorCodes.validation,
            #         message="Невозможно переместить: зона самая верхняя в иерархии",
            #     )
            #     warning(request.path, request.data, response.data)
            #     return response
            # else:
            #     moving_area.position -= 1
            #     area.position += 1
            #     moving_area.save()
            #     area.save()
            #     response = ApiResponse(message=f'Зона с id={pk} успешно перемещена',
            #                            status_code=status.HTTP_200_OK,
            #                            result=AreaSerializer(area).data)
            #     info(request.path, request.data, response.data)
            #     return response
        if direction == 'down':
            if area_index >= len(areas_list) - 1:
                response = ApiErrorResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error_code=ApiErrorCodes.validation,
                    message="Невозможно переместить: зона самая нижняя в иерархии",
                )
                warning(request.path, request.data, response.data)
                return response
            second_area = areas_list[area_index + 1]
            second_area.position = area_index
            area.position = area_index + 1
            second_area.save()
            area.save()
            # moving_area = Area.objects.filter(position=area.position - 1).first()
            # if moving_area is None:
            #     response = ApiErrorResponse(
            #         status_code=status.HTTP_400_BAD_REQUEST,
            #         error_code=ApiErrorCodes.validation,
            #         message="Невозможно переместить: зона самая нижняя в иерархии",
            #     )
            #     warning(request.path, request.data, response.data)
            #     return response
            # else:
            #     moving_area.position += 1
            #     area.position -= 1
            #     moving_area.save()
            #     area.save()
        response = ApiResponse(message=f'Зона с id={pk} успешно перемещена',
                               status_code=status.HTTP_200_OK,
                               result=RoomSerializer(room).data)
        info(request.path, request.data, response.data)
        return response

    @action(detail=True, methods=['post'], url_path='add', permission_classes=[IsAuthenticated])
    @swagger_auto_schema(
        operation_summary='Добавить товар в зону',
        responses={200: AreaSerializer},
        manual_parameters=[
            Parameter(
                name='count',
                in_='query',
                description='количество товара',
                required=False,
                type='int',
            ),
            Parameter(
                name='product_id',
                in_='query',
                description='id товара',
                required=False,
                type='int',
            ),
        ],
        tags=[
            'Зоны'
        ]
    )
    def add(self, request: Request, pk=None, project_pk=None, room_pk=None):
        user = request.user
        project = Project.objects.filter(id=project_pk).first()
        room = Room.objects.filter(id=room_pk).first()
        area = Area.objects.filter(id=pk).first()
        count = int(request.query_params.get('count') or 1)
        product_id = request.query_params.get('product_id')
        product = Product.objects.filter(id=product_id).first()
        print(project_pk, room_pk, pk, project, room, area)
        if project is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.project_not_found,
                message=f"Проект с id={project_pk} не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        # if user.account_type == 'CLIENT' or (user.account_type == 'MANAGER' and project.owner != user):
        #     response = ApiErrorResponse(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         error_code=ApiErrorCodes.bad_credentials,
        #         message="У вас недостаточно прав для выполнения данного действия"
        #     )
        #     warning(request.path, request.data, response.data)
        #     return response
        if room is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение с id={room_pk} не найдено",
            )
            warning(request.path, request.data, response.data)
            return response
        if room.project != project:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение с id={room_pk} не относится к данному проекту",
            )
            warning(request.path, request.data, response.data)
            return response
        if area is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.area_not_found,
                message=f"Зона с id={pk} не найдена",
            )
            warning(request.path, request.data, response.data)
            return response
        if area.room != room:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.area_not_found,
                message=f"Зона с id={pk} не относится к данному помещению",
            )
            warning(request.path, request.data, response.data)
            return response
        if product is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.product_not_found,
                message=f'Товара с id={product_id} нет в базе данных'
            )
            warning(request.path, request.data, response.data)
            return response
        found = False
        item: AreaItem = None

        for area_item in AreaItem.objects.filter(area=area):
            if area_item.product == product:
                area_item.count += count
                item = area_item
                found = True
                print('a')
        if not found:
            item = AreaItem()
            item.area = area
            item.count = count
            item.product = product
        if item.count > 0:
            item.save()
            response = ApiResponse(
                status_code=status.HTTP_201_CREATED,
                message=f'Товар с id={product_id} в количестве {count} единиц добавлен в зону',
                result=AreaSerializer(area).data
            )
        else:
            if found:
                item.delete()
                response = ApiResponse(
                    status_code=status.HTTP_200_OK,
                    message=f'Товар с id={product_id} удален из зоны',
                    result=AreaSerializer(area).data
                )
            else:
                response = ApiResponse(
                    status_code=status.HTTP_200_OK,
                    message=f'Товар с id={product_id} не добавлен в зону'
                )

        info(request.path, request.data, response.data)
        return response

    @action(detail=True, methods=['post'], url_path='copy')
    @swagger_auto_schema(
        operation_summary='Создание копии зоны',
        responses={201: AreaSerializer},
        manual_parameters=[
            Parameter(
                name='destinationRoomId',
                in_='query',
                description='id помещения, куда копировать зону. Если не указано, создает дубликат в текущем помещении',
                required=False,
                type='int',
            )],
        tags=[
            'Зоны'
        ]
    )
    def copy(self, request: Request, pk=None, project_pk=None, room_pk=None):
        user = request.user
        project = Project.objects.filter(id=project_pk).first()
        room = Room.objects.filter(id=room_pk).first()
        area = Area.objects.filter(id=pk).first()

        destination_room_id = self.request.query_params.get('destinationRoomId')
        if destination_room_id:
            destination_room = Room.objects.filter(id=int(destination_room_id)).first()
        else:
            destination_room = room

        if project is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.project_not_found,
                message=f"Проект id={project_pk} не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        # if user.account_type == 'CLIENT' or (user.account_type == 'MANAGER' and project.owner != user):
        #     response = ApiErrorResponse(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         error_code=ApiErrorCodes.bad_credentials,
        #         message="У вас недостаточно прав для выполнения данного действия"
        #     )
        #     warning(request.path, request.data, response.data)
        #     return response
        if room is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение с id={room_pk} не найдено",
            )
            warning(request.path, request.data, response.data)
            return response
        if room.project != project:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение с id={room_pk} не относится к данному проекту",
            )
            warning(request.path, request.data, response.data)
            return response
        if area is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.area_not_found,
                message=f"Зона с id={pk} не найдена",
            )
            warning(request.path, request.data, response.data)
            return response
        if area.room != room:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.area_not_found,
                message=f"Зона с id={pk} не относится к данному помещению",
            )
            warning(request.path, request.data, response.data)
            return response
        last_area = Area.objects.filter(room=room).order_by('position').last()
        if last_area is None:
            highest_position = 0
        else:
            highest_position = last_area.position + 1
        copy_area = Area.objects.create(title=area.title,
                                        room=destination_room,
                                        position=highest_position)
        items = AreaItem.objects.filter(area=area)
        for item in items:
            new_item = AreaItem.objects.create(area=copy_area,
                                               count=item.count,
                                               discount=item.discount,
                                               product=item.product)
        response = ApiResponse(status_code=status.HTTP_201_CREATED,
                               message=f"Успешное создание копии зоны c id={pk}",
                               result=AreaSerializer(copy_area).data)
        info(request.path, request.data, response.data)
        return response

    @action(detail=True, methods=['post'], url_path='setdiscount')
    @swagger_auto_schema(
        operation_summary='Установиить скидку на товар в зоне',
        request_body=AreaSetDiscountSerializer,
        responses={200: AreaSerializer},
        tags=[
            'Зоны'
        ]
    )
    def setdiscount(self, request: Request, pk=None, project_pk=None, room_pk=None):
        user = request.user
        project = Project.objects.filter(id=project_pk).first()
        room = Room.objects.filter(id=room_pk).first()
        area = Area.objects.filter(id=pk).first()
        item_id = request.query_params.get('id')
        if project is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.project_not_found,
                message=f"Проект с id={project_pk} не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        # if user.account_type == 'CLIENT' or (user.account_type == 'MANAGER' and project.owner != user):
        #     response = ApiErrorResponse(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         error_code=ApiErrorCodes.bad_credentials,
        #         message="У вас недостаточно прав для выполнения данного действия"
        #     )
        #     warning(request.path, request.data, response.data)
        #     return response
        if room is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение с id={room_pk} не найдено",
            )
            warning(request.path, request.data, response.data)
            return response
        if room.project != project:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение с id={room_pk} не относится к данному проекту",
            )
            warning(request.path, request.data, response.data)
            return response
        if area is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.area_not_found,
                message=f"Зона с id={pk} не найдена",
            )
            warning(request.path, request.data, response.data)
            return response
        if area.room != room:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.area_not_found,
                message=f"Зона с id={pk} не относится к данному помещению",
            )
            warning(request.path, request.data, response.data)
            return response
        item = AreaItem.objects.filter(area=area, id=item_id).first()
        if item is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.area_item_not_found,
                message=f"В данной зоне нет элемента с id={item_id}",
            )
            warning(request.path, request.data, response.data)
            return response
        serializer = AreaSetDiscountSerializer(data=request.data)
        if not serializer.is_valid():
            response = ApiErrorResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ApiErrorCodes.validation,
                message="Ошибка валидации",
                result=serializer.errors
            )
            warning(request.path, request.data, response.data)
            return response

        item.discount = serializer.validated_data['discount']
        item.save()

        response = ApiResponse(
            message=f"на товар с id={item_id} установлена скидка в размере{serializer.validated_data['discount']}%",
            status_code=status.HTTP_200_OK,
            result=AreaItemSerializer(item).data)
        info(request.path, request.data, response.data)
        return response

    @swagger_auto_schema(
        operation_summary='Получить список помещений',
        manual_parameters=[
            Parameter(
                name='offset',
                in_='query',
                description='Смещение от начала списка',
                required=False,
                type='int',
                default=0,
            ),
            Parameter(
                name='limit',
                in_='query',
                description='Количество элементов которое нужно вернуть',
                required=False,
                type='int',
            ),
        ],
        responses={},
        tags=['Зоны']
    )
    def list(self, request: Request, project_pk=None, room_pk=None):
        user = request.user
        areas_limit = self.request.query_params.get('limit')
        project = Project.objects.filter(id=project_pk).first()
        if project is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.project_not_found,
                message=f"Проект с id={project_pk} не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        room = Room.objects.filter(id=room_pk, project=project).first()
        if room is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение с id={room_pk} не найдено в проекте с id={project_pk}",
            )
            warning(request.path, request.data, response.data)
            return response
        # if (user.account_type == 'CLIENT' and project.client != user) or (
        #         user.account_type == 'MANAGER' and project.owner != user):
        #     response = ApiErrorResponse(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         error_code=ApiErrorCodes.bad_credentials,
        #         message="У вас недостаточно прав для выполнения данного действия"
        #     )
        #     warning(request.path, request.data, response.data)
        #     return response
        areas_qs = Area.objects.filter(room=room).order_by('-position')

        total_count = areas_qs.count()

        if 'offset' in request.query_params:
            offset = int(self.request.query_params.get('offset'))
        else:
            offset = 0

        areas_qs = areas_qs[offset:]
        if areas_limit is not None:
            paginator = Paginator(areas_qs, areas_limit)
            current_page = paginator.get_page(1)
        else:
            current_page = areas_qs
        serializer = AreaSerializer(current_page, many=True)
        result = ({'total_count': total_count, 'areas': serializer.data})

        response = ApiResponse(result=result)
        info(request.path, request.data, response.data)
        return response

    @action(detail=True, methods=['get'], url_path='items')
    @swagger_auto_schema(
        operation_summary='Список товаров в зоне',
        responses={200: AreaItemSerializer},
        tags=[
            'Зоны'
        ]
    )
    def items(self, request: Request, pk=None, project_pk=None, room_pk=None):
        user = request.user
        project = Project.objects.filter(id=project_pk).first()
        room = Room.objects.filter(id=room_pk).first()
        area = Area.objects.filter(id=pk).first()
        # if (user.account_type == 'CLIENT' and project.client != user) or (
        #         user.account_type == 'MANAGER' and project.owner != user):
        #     response = ApiErrorResponse(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         error_code=ApiErrorCodes.bad_credentials,
        #         message="У вас недостаточно прав для выполнения данного действия"
        #     )
        #     warning(request.path, request.data, response.data)
        #     return response
        if project is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.project_not_found,
                message=f"Проект с id={project_pk} не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        if room is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.project_not_found,
                message=f"Помещение с id={room_pk} не найдено",
            )
            warning(request.path, request.data, response.data)
            return response
        if room.project != project:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение с id={room_pk} не относится к данному проекту",
            )
            warning(request.path, request.data, response.data)
            return response
        if area is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.area_not_found,
                message=f"Зона с id={pk} не найдена",
            )
            warning(request.path, request.data, response.data)
            return response
        if area.room != room:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.area_not_found,
                message=f"Зона с id={pk} не относится к данному помещению",
            )
            warning(request.path, request.data, response.data)
            return response

        items_qs = AreaItem.objects.filter(area=area)
        serializer = AreaItemSerializer(items_qs, many=True)
        response = ApiResponse(result=serializer.data)
        info(request.path, request.data, response.data)
        return response

    @swagger_auto_schema(
        operation_summary='Получить 1 зону (в конкретнм помещении конкретного проекта) по ее id',
        tags=['Зоны']
    )
    def retrieve(self, request: Request, pk=None, project_pk=None, room_pk=None):
        user = request.user
        if user.account_type == 'CLIENT':
            project = Project.objects.filter(client=user, id=project_pk).first()
        if user.account_type == 'MANAGER':
            project = Project.objects.filter(owner=user, id=project_pk).first()
        if user.account_type == 'ADMIN':
            project = Project.objects.filter(id=project_pk).first()
        if project is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.project_not_found,
                message="Проект не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        room = Room.objects.filter(id=room_pk).first()
        if room is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение id={room_pk} не найдено",
            )
            warning(request.path, request.data, response.data)
            return response
        if room.project != project:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.room_not_found,
                message=f"Помещение с id={room_pk} не относится к данному проекту",
            )
            warning(request.path, request.data, response.data)
            return response
        area = Area.objects.filter(id=pk).first()
        if area is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.area_not_found,
                message=f"Зона с id={pk} не найдена",
            )
            warning(request.path, request.data, response.data)
            return response
        if area.room != room:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.area_not_found,
                message=f"Зона с id={pk} не относится к данному помещению",
            )
            warning(request.path, request.data, response.data)
            return response
        serializer = AreaSerializer(area)
        response = ApiResponse(result=serializer.data)
        info(request.path, request.data, response.data)
        return response


class AreaItemAPIView(views.APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    @swagger_auto_schema(
        operation_summary='Изменить элемент зоны',
        manual_parameters=[
            Parameter(
                name='currency',
                in_='query',
                description='currency',
                required=True,
                type='string',
                enum=[Currencies.byn, Currencies.rub],
                default=Currencies.byn
            )],
        request_body=AreaItemUpdateSerializer(),
        tags=['Элементы зоны']
    )
    def patch(self, request: Request, id: int):
        currency = request.query_params.get('currency') or Currencies.byn
        area_item: AreaItem = AreaItem.objects.filter(id=id).first()
        if area_item is None:
            return ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.area_not_found,
                message=f"Не найден area item",
            )

        serializer = AreaItemUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if 'price' in serializer.validated_data:
            price = serializer.validated_data.get('price')
            if currency == Currencies.byn:
                area_item.price_byn = price
            elif currency == Currencies.rub:
                area_item.price_rub = price
        area_item.save()

        return ApiResponse(result=AreaItemSerializer(area_item, context={
            'currency': currency,
            'user_price_level': request.user.price_level,
        }).data)
