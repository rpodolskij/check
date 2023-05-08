import requests
from django.conf import settings
import json
import base64
from datetime import datetime
import os

from django.db import transaction

from store.models import Product, ProductCategory
from PIL import Image

from store.models import Order, Product, OrderItem, PriceLevel, ProductPrice
import decimal

NULL_1C = "00000000-0000-0000-0000-000000000000"


class OneCAPI(object):

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = (self.username, self.password)

    def check_connection(self):
        response = self.session.get(
            f'{settings.ONE_C_HOST}/ping',
        )
        if response.status_code == 200:
            print('connected')
            return True

        else:
            print('connection failed, wrong username or password')
            return False

    def get_products(self):
        response = self.session.post(
            f'{settings.ONE_C_HOST}/getgoods',
            json={
                "key": "ff0718f9-a52e-49e0-978c-491a316bc6dd",
                "ОnlyChanges": "false",
            }
        )
        print('GET PRODUCTS', response.status_code)
        # print(response.status_code, response.content)
        response_json = json.loads(response.text)
        products = response_json.get('goods')
        groups = response_json.get('groups')
        # products = json.loads(response_json.get('goods'))
        for k, v in enumerate(products):
            products[k] = v.get('product')
        return products, groups

    def get_picture(self, id):
        os.makedirs(f'{settings.ONE_C_TEMP_DIR}/images/', exist_ok=True)
        images_filenames = os.listdir(f'{settings.ONE_C_TEMP_DIR}/images/')
        short_images_filenames = []
        for idx, filename in enumerate(images_filenames):
            name, ext = os.path.splitext(filename)
            short_images_filenames.append(name)
        if id in short_images_filenames:
            dest_path = os.path.join(settings.PRODUCTS_IMAGES_DIR, f'{id}.png')
            src_path = f'{settings.ONE_C_TEMP_DIR}/images/{images_filenames[short_images_filenames.index(id)]}'
            thumbnail_path = os.path.join(settings.PRODUCTS_IMAGES_DIR, f'{id}-thumbnail.png')
            if not os.path.exists(dest_path):
                image = Image.open(src_path)
                image = image.convert('RGBA')
                image.save(dest_path)
            if not os.path.exists(thumbnail_path):
                image = Image.open(src_path)
                image = image.convert('RGBA')
                dest_width = 200
                multiplier = image.size[0] / dest_width
                dest_height = image.size[1] / multiplier
                image = image.resize(
                    (round(dest_width), round(dest_height)),
                    Image.ANTIALIAS,
                )
                image.save(thumbnail_path)
            return dest_path
        response = self.session.post(
            f'{settings.ONE_C_HOST}/getpicture',
            json={
                "key": "ff0718f9-a52e-49e0-978c-491a316bc6dd",
                "PicturesID": "{}".format(id),
            }
        )
        os.makedirs(f'{settings.ONE_C_TEMP_DIR}/images/', exist_ok=True)

        if json.loads(response.text)['result'] == "ok":

            picture_data = json.loads(response.text)['pucture']
            picture_binary_data = picture_data['file_binary']

            decoded_picture_binary_data = base64.b64decode(picture_binary_data)
            filename, ext = os.path.splitext(picture_data["file_name"])
            file_path = f'{settings.ONE_C_TEMP_DIR}/images/{id}{ext}'
            picture = (open(file_path, 'ab'))
            picture.write(decoded_picture_binary_data)
            picture.close()

            dest_path = os.path.join(settings.PRODUCTS_IMAGES_DIR, f'{id}.png')
            src_path = file_path
            thumbnail_path = os.path.join(settings.PRODUCTS_IMAGES_DIR, f'{id}-thumbnail.png')
            if not os.path.exists(dest_path):
                image = Image.open(src_path)
                image = image.convert('RGBA')
                image.save(dest_path)
            if not os.path.exists(thumbnail_path):
                image = Image.open(src_path)
                image = image.convert('RGBA')
                dest_width = 200
                multiplier = image.size[0] / dest_width
                dest_height = image.size[1] / multiplier
                image = image.resize(
                    (round(dest_width), round(dest_height)),
                    Image.ANTIALIAS,
                )
                image.save(thumbnail_path)

            return dest_path
        else:
            return None

    def create_order(self, order: Order):
        print('Create order')
        client = order.user
        products = []
        created_at: datetime = order.create_at
        items_qs = OrderItem.objects.filter(order=order)
        for item in items_qs:
            product_price = ProductPrice.objects.filter(
                product__id=item.product.id,
                price_level=client.price_level
            ).first()
            products.append({
                "id_1c": item.product.id_1c,
                "quantity": item.count,
                "price": product_price.price,
            })
        url = f"{settings.ONE_C_HOST}/CreateOrder"
        data = {
            "key": "ff0718f9-a52e-49e0-978c-491a316bc6dd",
            "data": {
                "id": str(order.id),
                "id_1c": "7aeb6d72-a4f4-11eb-baf6-4ccc6a42cb29",
                "date": created_at.strftime("%Y%m%d"),
                "unp": "192679270",
                "goods": products
            }
        }

        response = self.session.post(
            url,
            json=data
        )
        # request = self.session.post(
        #     f"{settings.ONE_C_HOST}/UT_Empty/hs/trade/CreateOrder",
        #     json={
        #         "key": "ff0718f9-a52e-49e0-978c-491a316bc6dd",
        #         "data": {
        #             "id": order.id,
        #             "id_1c": "7aeb6d72-a4f4-11eb-baf6-4ccc6a42cb29",
        #             "date": "20210424",
        #             "unp": "192679270",
        #             "goods": [
        #                 {
        #                     "id_1c": "af4219f8-2288-11eb-bac0-4ccc6a42cb23",
        #                     "quantity": 4,
        #                     "price": 1000
        #                 },
        #                 {
        #                     "id_1c": "7b581459-557b-11eb-bad3-4ccc6a42cb23",
        #                     "quantity": 1,
        #                     "price": 5000
        #                 }
        #             ]
        #         }
        #     }
        # )

        response_info = response.text
        return response_info

    def import_all(self):

        print('Import products...')
        pictures_dict = dict()
        products, groups = self.get_products()
        os.makedirs(settings.ONE_C_TEMP_DIR, exist_ok=True)

        products_file = open(f'{settings.ONE_C_TEMP_DIR}/products.json', 'w')
        products_file.write(json.dumps(products, indent=4, ensure_ascii=False))
        products_file.close()

        groups_file = open(f'{settings.ONE_C_TEMP_DIR}/groups.json', 'w')
        groups_file.write(json.dumps(groups, indent=4, ensure_ascii=False))
        groups_file.close()

        print('products imported')
        print('Import images...')
        os.makedirs(settings.PRODUCTS_IMAGES_DIR, exist_ok=True)

        for idx, item in enumerate(products):
            picture_id = (item['PicturesID'])
            if picture_id == NULL_1C:
                continue
            picture_file_path = self.get_picture(picture_id)
            if picture_file_path:
                pictures_dict[picture_id] = picture_file_path

        pictures_dict_file = open(f'{settings.ONE_C_TEMP_DIR}/pictures.json', 'w')
        pictures_dict_file.write(json.dumps(pictures_dict))
        pictures_dict_file.close()
        print('Images imported')

    @transaction.atomic()
    def update_categories(self, categories_list, parent=None):
        for category_info in categories_list:
            id = category_info.get('Group_ID')
            name = category_info.get('Group_Name')
            category = ProductCategory.objects.create(
                parent=parent,
                code=id,
                name=name,
                is_active=True,
            )
            children = category_info.get('rows')
            self.update_categories(children, category)

    @transaction.atomic()
    def update_products(self):
        # ProductPrice.objects.all().delete()
        price_level_by_id = {}
        products_data_list = json.loads(open(f'{settings.ONE_C_TEMP_DIR}/products.json', 'r').read())

        products = Product.objects.all()
        product_by_id = {
            product.id_1c: product for product in products
        }
        # Отправить все продукты в архив
        for product in products:
            product.is_archive = True
            product.save()

        images_dict = json.loads(open(f'{settings.ONE_C_TEMP_DIR}/pictures.json', 'r').read())

        for product_info in products_data_list:

            if product_info.get('ID') in product_by_id:
                product: Product = product_by_id[product_info.get('ID')]

            else:
                product: Product = Product()

            product_category = ProductCategory.objects.filter(code=product_info.get('Group_ID')).first()
            product.category = product_category.name if product_category else ''
            # product.category = ''
            product.series = ''
            product.name = product_info.get('Name')
            product.code = product_info.get('Code')
            product.id_1c = product_info.get('ID')
            product.is_archive = False
            # Подсчет количества
            product.count = 0
            try:
                for warehouse in product_info.get('Stores'):
                    product.count += int(warehouse.get('Value'))
            except Exception as e:
                print(e)
                print('Не удалось вычислить остатки')
            # Загрузка уровней цен

            for price_type in product_info.get('Prices'):
                price_level = PriceLevel.objects.filter(id=price_type.get('ID')).first()
                if not price_level:
                    price_level = PriceLevel.objects.create(
                        id=price_type.get('ID'),
                        name=price_type.get('Name')
                    )
                price_level_by_id[price_level.id] = price_level

            image_id = product_info.get('PicturesID')
            if image_id and (image_id != '00000000-0000-0000-0000-000000000000'):
                if image_id in images_dict:
                    path = images_dict.get(image_id).split('/')
                    path = path[2:]
                    path = '/'.join(path)
                    product.image = path

            for property_info in product_info.get('Properties'):
                try:
                    product.set_property(property_info.get('Name'), property_info.get('Value'))
                except Exception as e:
                    print(
                        f"Ошибка при сохранении свойства {property_info.get('Name')} со значением {property_info.get('Value')}")

            product.save()

            try:
                for price_type in product_info.get('Prices'):
                    price_id = price_type.get('ID')
                    if price_id in price_level_by_id.keys():
                        for index, price in enumerate(ProductPrice.objects.filter(
                                price_level=price_level_by_id.get(price_id),
                                product=product,
                        )):
                            if index != 0:
                                price.is_archive = True
                                price.save()
                        price: ProductPrice = ProductPrice.objects.filter(
                            price_level=price_level_by_id.get(price_id),
                            product=product,
                        ).first()
                        if product.id_1c == "50d2490f-4e93-11ec-bb0c-4ccc6a42cb23":
                            print('IMPORT PRICE: ', decimal.Decimal(price.price),
                                  decimal.Decimal(price_type.get('Value')))
                        if price and (decimal.Decimal(price.price) == decimal.Decimal(price_type.get('Value'))):
                            continue

                        price = ProductPrice.objects.create(
                            price_level=price_level_by_id.get(price_id),
                            product=product,
                            price=float(price_type.get('Value')),
                        )
                        # product.price = max(product.price, float(price_type.get('Value')))
            except Exception as e:
                print(e)
                print('Не удалось вычислить стоимость')

    @transaction.atomic()
    def update_database(self):
        # PriceLevel.objects.all().delete()
        groups_data_list = json.loads(open(f'{settings.ONE_C_TEMP_DIR}/groups.json', 'r').read())
        categories_qs = ProductCategory.objects.all().delete()
        self.update_categories(groups_data_list.get('rows'))
        self.update_products()

        print('Database updated')
