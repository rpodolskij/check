from typing import Optional

from rest_framework import viewsets, status
from rest_framework.request import Request
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action, api_view
from byled.responses import ApiErrorCodes, ApiResponse, ApiErrorResponse
from .models import Product, Order, OrderItem, BasketItem, Basket, ProductCategory, PriceLevel, ProductPrice
from .serializers import ProductSerializer, OrderSerializer, OrderItemSerializer, CommentSerializer, \
    OrderItemUpdateSerializer, OrderUpdateSerializer, ProductCreateUpdateSerializer, BasketSerializer, \
    ProductCategorySerializer, ProductPriceSerializer, PriceLevelSerializer
from utils.logging.logger import info, warning
from users.models import User
from django.core.paginator import Paginator
from django.db.models import Q

from .permissions import CsrfExemptSessionAuthentication
from drf_yasg.utils import swagger_auto_schema
from drf_yasg.openapi import Parameter

from django.conf import settings

from integrations.one_c.OneCAPI import OneCAPI


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


def get_basket_by_user(user: User, currency=Currencies.byn):
    basket = user.basket
    basket_items = BasketItem.objects.filter(basket=basket)

    count_for_cycle = basket_items.count()
    count = 0
    amount = 0
    items = list()
    user_price_level = user.price_level

    print('BASKET', currency)
    while count_for_cycle > 0:
        current_item = basket_items.first()
        # todo Скорректировать отображение цены в соответсвтии с уровнем цены и указаной валютой
        product_price = ProductPrice.objects.filter(
            product__basketitem=current_item,
            price_level=get_price_level(user_price_level, currency)
        ).first()
        # product = Product.objects.get(basketitem=current_item)
        item = ProductPriceSerializer(product_price).data
        item['count'] = current_item.count
        # item = {'product': ProductSerializer(product_price.product, many=False).data, 'count': current_item.count}

        count += current_item.count
        amount += current_item.count * product_price.price
        items.append(item)
        basket_items = basket_items.exclude(id=current_item.id)
        count_for_cycle -= 1

    result = ({'count': count, 'amount': amount, 'items': items})
    return result


def get_products_by_order(user: User, order: Order):
    items_qs = OrderItem.objects.filter(order=order).order_by('id')

    serializer = OrderItemSerializer(items_qs, many=True)
    return serializer.data


class ProductsViewSet(viewsets.ViewSet):
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def get_permissions(self):
        if self.action in ['list', 'create']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]

    def parse_filter(self, value):
        field_filter = value
        if field_filter and (type(field_filter) == str):
            field_filter = field_filter.split(',')
        return field_filter

    @swagger_auto_schema(
        operation_summary='Получить список товаров',
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
                description='Поле сортировки (доступны: price). sort=price это по возрастанию. sort=-price это по убыванию.',
                required=False,
                type='str',
            ),
            Parameter(
                name='category',
                in_='query',
                description='Список категорий (чреез запятую)',
                required=False,
                type='str',
            ),
            Parameter(
                name='manufacturer',
                in_='query',
                description='Список производителей (чреез запятую)',
                required=False,
                type='str',
            ),
            Parameter(
                name='type',
                in_='query',
                description='Список типов (чреез запятую)',
                required=False,
                type='str',
            ),
            Parameter(
                name='grade_of_waterproofment',
                in_='query',
                description='Список степеней влагозащиты (чреез запятую)',
                required=False,
                type='str',
            ),
            Parameter(
                name='currency',
                in_='query',
                description='Валюта',
                required=False,
                type='str',
            ),

        ],
        responses={},
        tags=['Товары']
    )
    def list(self, request: Request, ):
        offset = int(request.query_params.get('offset') or 0)
        limit = int(request.query_params.get('limit')) if request.query_params.get('limit') else None
        query = self.request.query_params.get('query')
        sort = self.request.query_params.get('sort')

        category_filter = self.parse_filter(self.request.query_params.get('category'))
        series_filter = self.parse_filter(self.request.query_params.get('series'))
        price_min = int(self.request.query_params.get('price_min') or 0)
        price_max = int(self.request.query_params.get('price_max') or 999999999)
        manufacturer_filter = self.parse_filter(self.request.query_params.get('manufacturer'))
        brands_filter = self.parse_filter(self.request.query_params.get('brands'))
        type_filter = self.parse_filter(self.request.query_params.get('type'))
        voltages_filter = self.parse_filter(self.request.query_params.get('voltages'))
        grade_of_waterproofment_filter = self.parse_filter(self.request.query_params.get('grade_of_waterproofment'))
        currency = self.request.query_params.get('currency') or Currencies.byn

        # group_of_list_filter = self.parse_filter(self.request.query_params.get('group_of_list'))
        # vendor_code_filter = self.parse_filter(self.request.query_params.get('vendor_code'))
        # group_of_list_filter = self.parse_filter(self.request.query_params.get('group_of_list'))
        # group_of_list_filter = self.parse_filter(self.request.query_params.get('group_of_list'))
        # group_of_list_filter = self.parse_filter(self.request.query_params.get('group_of_list'))
        # group_of_list_filter = self.parse_filter(self.request.query_params.get('group_of_list'))
        # group_of_list_filter = self.parse_filter(self.request.query_params.get('group_of_list'))
        # group_of_list_filter = self.parse_filter(self.request.query_params.get('group_of_list'))
        # group_of_list_filter = self.parse_filter(self.request.query_params.get('group_of_list'))
        # group_of_list_filter = self.parse_filter(self.request.query_params.get('group_of_list'))
        # group_of_list_filter = self.parse_filter(self.request.query_params.get('group_of_list'))
        # group_of_list_filter = self.parse_filter(self.request.query_params.get('group_of_list'))
        # group_of_list_filter = self.parse_filter(self.request.query_params.get('group_of_list'))

        product_price_qs = ProductPrice.objects.filter(
            is_archive=False,
        ).select_related('price_level').select_related('product')

        # Выбрать только не архивные
        product_price_qs = product_price_qs.filter(product__is_archive=False)

        # Фильтр в соответствии с уровнем цены пользователя (если указана)
        if request.user.price_level:
            # todo Скорректировать отображение цены в соответсвтии с уровнем цены и указаной валютой
            product_price_qs = product_price_qs.filter(price_level=get_price_level(request.user.price_level, currency))

        # Фильтр по цене
        product_price_qs = product_price_qs.filter(
            Q(price__lte=price_max) | Q(price__gte=price_min)
        )
        # product_qs = Product.objects.all().filter(
        #     Q(prices__price_level=request.user.price_level) &
        #     (Q(prices__price__lte=price_max) | Q(prices__price__gte=price_min))
        #
        # ).prefetch_related('prices')
        # product_qs = product_qs.filter(is_archive=False)

        # Фильтр по названию товара
        if query:
            product_price_qs = product_price_qs.filter(
                Q(product__name__icontains=query) | Q(product__vendor_code__icontains=query)
            )
            #
            # product_qs = product_qs.filter(
            #     Q(name__icontains=query) | Q(vendor_code__icontains=query)
            # )
            #
        if category_filter:
            category_names = set()
            categories_qss = []
            categories = ProductCategory.objects.filter(name__in=category_filter)
            for category in categories:
                category_names.add(category.name)
                if category.children.count() > 0:
                    categories_qss.append(category.children.all())

            while len(categories_qss) > 0:
                new_categories_qss = []
                for categories_qs in categories_qss:
                    for category in categories_qs:
                        category_names.add(category.name)
                        if category.children.count() > 0:
                            new_categories_qss.append(category.children.all())
                categories_qss = new_categories_qss
            category_names = list(category_names)
            product_price_qs = product_price_qs.filter(
                Q(product__category__in=category_names) | Q(product__series__in=category_names))
        # if series_filter:
        #     product_price_qs = product_price_qs.filter(product__series__in=series_filter)
        if manufacturer_filter:
            product_price_qs = product_price_qs.filter(product__manufacturer__in=manufacturer_filter)
        if brands_filter:
            product_price_qs = product_price_qs.filter(product__brand__in=brands_filter)
        if type_filter:
            product_price_qs = product_price_qs.filter(product__type__in=type_filter)
        if voltages_filter:
            product_price_qs = product_price_qs.filter(product__voltage__in=voltages_filter)
        if grade_of_waterproofment_filter:
            product_price_qs = product_price_qs.filter(
                product__grade_of_waterproofment__in=grade_of_waterproofment_filter)

        # Сортировка по доступным полям продукта
        if sort:
            if sort.replace('-', '') in ['price']:
                product_price_qs = product_price_qs.order_by(sort)

        # Вырезка по смещению и лимиту
        product_price_paginated_qs = product_price_qs[offset:]
        if limit:
            product_price_paginated_qs = product_price_paginated_qs[:limit]

        # serializer = ProductSerializer(products, many=True)
        # response = ApiResponse(result={
        #     'totalCount': product_qs.count(),
        #     'items': serializer.data,
        # })

        serializer = ProductPriceSerializer(product_price_paginated_qs, many=True)
        response = ApiResponse(result={
            'totalCount': product_price_qs.count(),
            'items': serializer.data,
        })
        # info(request.path, request.data, response.data)
        return response

    @swagger_auto_schema(
        operation_summary='Добавление (создание) нового товара',
        request_body=ProductCreateUpdateSerializer,
        responses={201: None},
        tags=[
            'Товары'
        ]
    )
    def create(self, request: Request, ):
        serializer = ProductCreateUpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            response = ApiErrorResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ApiErrorCodes.validation,
                message="Ошибка валидации",
                result=serializer.errors
            )
            warning(request.path, request.data, response.data)
            return response
        product = serializer.save()
        response = ApiResponse(status_code=status.HTTP_201_CREATED,
                               message="Товар успешно добавлен",
                               result=ProductSerializer(product).data)
        info(request.path, request.data, response.data)
        return response

    @swagger_auto_schema(
        operation_summary='Изменение существующего товара',
        request_body=ProductSerializer,
        responses={200: None},

        tags=[
            'Товары'
        ]
    )
    def update(self, request: Request, pk=None):
        serializer = ProductCreateUpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            response = ApiErrorResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ApiErrorCodes.validation,
                message="Ошибка валидации",
                result=serializer.errors
            )
            warning(request.path, request.data, response.data)
            return response
        product = Product.objects.filter(id=pk).first()
        if product is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.product_not_found,
                message=f"Товара с id={pk} нет в базе данных"
            )
            warning(request.path, request.data, response.data)
            return response
        serializer.save()
        response = ApiResponse(status_code=status.HTTP_200_OK,
                               message="Товар успешно изменен",
                               result=ProductSerializer(product).data)
        info(request.path, request.data, response.data)
        return response

    @swagger_auto_schema(
        operation_summary='Удаление товара',
        responses={200: None},
        tags=[
            'Товары'
        ]
    )
    def destroy(self, request: Request, pk=None):
        product = Product.objects.filter(id=pk).first()
        if product is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.product_not_found,
                message=f"Товара с id={pk} нет в базе данных"
            )
            warning(request.path, request.data, response.data)
            return response
        product = Product.objects.filter(id=pk)
        product.delete()
        response = ApiResponse(status_code=status.HTTP_200_OK,
                               message="Товар успешно удален",
                               result=ProductSerializer(product).data)
        info(request.path, request.data, response.data)
        return response

    # @action(detail=False, methods=['get'])
    # def search(self, request: Request):
    #     products_set = Product.objects.all()
    #     if 'product_name' in request.query_params:
    #         param = request.query_params['product_name']
    #         products_set = products_set.filter(product_name__icontains=param)
    #     if 'category' in request.query_params:
    #         param = request.query_params['category']
    #         products_set = products_set.filter(category__icontains=param)
    #     if 'manufacturer' in request.query_params:
    #         param = request.query_params['manufacturer']
    #         products_set = products_set.filter(manufacturer__icontains=param)
    #     if 'power_output' in request.query_params:
    #         param = request.query_params['power_output']
    #         products_set = products_set.filter(power_output__icontains=param)
    #     if 'voltage' in request.query_params:
    #         param = request.query_params['voltage']
    #         products_set = products_set.filter(voltage__icontains=param)
    #     if 'cost' in request.query_params:
    #         param = request.query_params['cost']
    #         products_set = products_set.filter(cost__icontains=param)
    #     if 'grade_of_waterproofment' in request.query_params:
    #         param = request.query_params['grade_of_waterproofment']
    #         products_set = products_set.filter(grade_of_waterproofment__icontains=param)
    #     if 'warranty' in request.query_params:
    #         param = request.query_params['warranty']
    #         products_set = products_set.filter(warranty__icontains=param)
    #
    #     serializer = ProductSerializer(products_set, many=True)
    #     response = ApiResponse(result=serializer.data)
    #     info(request.path, request.data, response.data)
    #     return response


class ProductFiltersViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    @swagger_auto_schema(
        operation_summary='Получить список фильтров товаров',

        responses={},
        tags=['Фильтры для прайс листа']
    )
    def list(self, request: Request, ):
        result = {}
        products_qs = Product.objects.all()
        products_qs = products_qs.filter(is_archive=False)
        # Категории
        product_categories_qs = ProductCategory.objects.filter(is_active=True, parent=None)
        # serializer = ProductCategorySerializer(product_categories_qs, many=True)
        # result['categories'] = serializer.data

        # Категории
        # categories = {}
        # for product in products_qs:
        #     if (product.category is None) or (product.category == ''):
        #         continue
        #     if product.category not in categories:
        #         categories[product.category] = []
        #     if (product.series is not None) and (product.series not in categories[product.category]):
        #         if product.series != '':
        #             categories[product.category].append(product.series)
        result['categories'] = ProductCategorySerializer(product_categories_qs, many=True).data

        # Бренды
        brands = []
        for product in products_qs:
            if (product.brand not in brands) and (product.brand is not None):
                brands.append(product.brand)
        result['brands'] = brands
        # Напряжение
        voltages = []
        for product in products_qs:
            if (product.voltage not in voltages) and (product.voltage is not None):
                voltages.append(product.voltage)
        result['voltages'] = voltages
        # Степеньи влагозащиты
        grade_of_waterproofment = []
        for product in products_qs:
            if (product.grade_of_waterproofment not in grade_of_waterproofment) and (
                    product.grade_of_waterproofment is not None):
                grade_of_waterproofment.append(product.grade_of_waterproofment)
        if "" in grade_of_waterproofment:
            grade_of_waterproofment.remove("")
        result['grade_of_waterproofment'] = grade_of_waterproofment

        response = ApiResponse(result=result)
        info(request.path, request.data, response.data)
        return response


class BasketViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    @action(detail=False, methods=['get'], url_path='my')
    @swagger_auto_schema(
        operation_summary='Получить информацию о корзине (список товаров)',
        manual_parameters=[],
        tags=[
            'Корзина'
        ]
    )
    def my(self, request: Request):
        user = request.user

        currency = request.query_params.get('currency') or Currencies.byn

        if Basket.objects.filter(user=user).first() is None:
            basket = Basket(user=user)
            basket.save()
        result = get_basket_by_user(user, currency)
        # basket = user.basket
        # basket_items = BasketItem.objects.filter(basket=basket)
        #
        # count_for_cycle = basket_items.count()
        # count = 0
        # amount = 0
        # items = list()
        #
        # while count_for_cycle > 0:
        #     current_item = basket_items.first()
        #     product = Product.objects.get(basketitem=current_item)
        #     item = {'product': ProductSerializer(product, many=False).data, 'count': current_item.count}
        #     count += current_item.count
        #     amount += current_item.count * product.price
        #     items.append(item)
        #     basket_items = basket_items.exclude(id=current_item.id)
        #     count_for_cycle -= 1
        #
        # result = ({'count': count, 'amount': amount, 'items': items})
        response = ApiResponse(status_code=status.HTTP_200_OK, result=result)
        info(request.path, request.data, response.data)
        return response

    @action(detail=False, methods=['post'], url_path='add', permission_classes=[IsAuthenticated])
    @swagger_auto_schema(
        operation_summary='Добавить товар в корзину',
        manual_parameters=[
            Parameter(
                name='product_id',
                in_='query',
                description='ID товара',
                required=True,
                type='int',
            ),
            Parameter(
                name='count',
                in_='query',
                description='Количество (если больше 0, то добавить; если меньше 0, то удалить)',
                required=False,
                type='int',
                default=1,
            ),
        ],
        tags=[
            'Корзина'
        ]
    )
    def add(self, request: Request):
        user = request.user
        count = int(request.query_params.get('count') or 1)
        product_id = request.query_params.get('product_id')
        product = Product.objects.filter(id=product_id).first()
        if product is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.product_not_found,
                message=f'Товара с id={product_id} нет в базе данных'
            )
            warning(request.path, request.data, response.data)
            return response
        basket = user.basket
        found = False
        item: BasketItem = None

        for basket_item in BasketItem.objects.filter(basket=basket):
            if basket_item.product == product:
                basket_item.count += count
                item = basket_item
                found = True
        if not found:
            item = BasketItem()
            item.basket = basket
            item.count = count
            item.product = product
        if item.count > 0:
            item.save()
            response = ApiResponse(
                status_code=status.HTTP_201_CREATED,
                message=f'Товар с id={product_id} в количестве {count} единиц добавлен в корзину',
                result=get_basket_by_user(user)
            )
        else:
            if found:
                item.delete()
                response = ApiResponse(
                    status_code=status.HTTP_200_OK,
                    message=f'Товар с id={product_id} удален из корзины',
                    result=get_basket_by_user(user)
                )
            else:
                response = ApiResponse(
                    status_code=status.HTTP_200_OK,
                    message=f'Товар с id={product_id} не добавлен в коризну',
                    result=get_basket_by_user(user)
                )

        info(request.path, request.data, response.data)
        return response

    @action(detail=False, methods=['delete'], url_path='clear', permission_classes=[IsAuthenticated])
    @swagger_auto_schema(
        operation_summary='Очистить корзину(свою)',
        tags=[
            'Корзина'
        ]
    )
    def clear(self, request: Request):
        user = request.user
        basket = user.basket
        basket_items = BasketItem.objects.filter(basket=basket)
        basket_items.delete()
        response = ApiResponse(status_code=status.HTTP_200_OK,
                               message="Корзина успешно очищена",
                               result=BasketSerializer(basket).data)
        info(request.path, request.data, response.data)
        return response

    @action(detail=False, methods=['post'], url_path='doorder', permission_classes=[IsAuthenticated])
    @swagger_auto_schema(
        operation_summary='Сделать заказ(создастся заказ, туда перенесутся товары из корзины, корзина очистится)',
        manual_parameters=[

            Parameter(
                name='currency',
                in_='query',
                description='Валюта',
                required=False,
                type='str',
            ),

        ],
        tags=[
            'Корзина'
        ]
    )
    def doorder(self, request: Request):
        user = request.user
        currency = request.query_params.get('currency') or Currencies.byn
        basket = user.basket
        order = Order.objects.create(user=user)
        basket_items = BasketItem.objects.filter(basket=basket)
        if basket_items.first() is None:
            response = ApiResponse(message='в корзине нет ни одного товара')
            info(request.path, request.data, response.data)
            return response
        for item in basket_items:
            orderitem = OrderItem.objects.create()
            orderitem.product = item.product
            orderitem.count = item.count
            orderitem.order = order
            orderitem.save()
            item.delete()

        serializer = OrderSerializer(order, many=False)
        order_info = serializer.data

        amount = 0
        count = 0
        # todo Скорректировать отображение цены в соответсвтии с уровнем цены и указаной валютой
        order_info['products'] = get_products_by_order(user, order.id)
        for product_item in order_info['products']:
            product_price = ProductPrice.objects.filter(
                product__id=product_item['product']['id'],
                price_level=get_price_level(request.user.price_level, currency)
            ).first()
            product_item['product']['price'] = product_price.price
            # amount += product_item['count'] * product_item['product']['price']
            amount += product_item['count'] * product_price.price
            count += product_item['count']
        order_info['totalAmount'] = amount
        order_info['totalCount'] = count
        response = ApiResponse(status_code=status.HTTP_200_OK, result=order_info)
        info(request.path, request.data, response.data)
        return response

        response = ApiResponse(status_code=status.HTTP_201_CREATED,
                               message="Заказ успешно создан",
                               result=OrderSerializer(order).data)
        return response


class OrderViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    @swagger_auto_schema(
        operation_summary='Получить список своих заказов',
        manual_parameters=[
            Parameter(
                name='manager_id',
                in_='query',
                description='ID менеджера заказа',
                required=False,
                type='int',
            ),
            Parameter(
                name='id',
                in_='query',
                description='ID заказа',
                required=False,
                type='int',
            ),
            Parameter(
                name='currency',
                in_='query',
                description='Валюта',
                required=False,
                type='str',
            ),

        ],
        responses={},
        tags=['Заказы']
    )
    def list(self, request: Request):
        user = request.user
        manager_id = self.request.query_params.get('manager_id')
        order_id = self.request.query_params.get('id')
        orders_qs = Order.objects.filter(user=user)
        count_items = orders_qs.count()
        if 'offset' in request.query_params:
            offset = int(self.request.query_params.get('offset'))
        else:
            offset = 0
        if 'limit' in request.query_params:
            limit = int(self.request.query_params.get('limit'))
        else:
            limit = 99999999999

        if manager_id:
            orders_qs = orders_qs.filter(manager=manager_id)
        if order_id:
            orders_qs = orders_qs.filter(id=order_id)
        print(offset, limit)
        currency = request.query_params.get('currency') or Currencies.byn
        orders_qs = orders_qs[offset:offset + limit]
        serializer = OrderSerializer(orders_qs, many=True)
        result = serializer.data
        for order in result:
            amount = 0
            count = 0
            order['products'] = get_products_by_order(user, order['id'])
            for product_item in order['products']:
                product_price = ProductPrice.objects.filter(
                    product__id=product_item['product']['id'],
                    price_level=get_price_level(user.price_level, currency)
                ).first()
                # amount += product_item['count'] * product_item['product']['price']
                amount += product_item['count'] * product_price.price
                product_item['product']['price'] = product_price.price
                count += product_item['count']
            order['totalAmount'] = amount
            order['totalCount'] = count
        response = ApiResponse(status_code=status.HTTP_200_OK, result={
            'count': count_items,
            'items': serializer.data,
        })
        info(request.path, request.data, response.data)
        return response

    @swagger_auto_schema(
        operation_summary='Получить данные одного заказа',
        manual_parameters=[
            Parameter(
                name='currency',
                in_='query',
                description='Валюта',
                required=False,
                type='str',
            ),

        ],
        tags=[
            'Заказы'
        ]
    )
    def retrieve(self, request: Request, pk=None):
        user = request.user

        order = Order.objects.filter(id=pk).first()
        if order is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.order_not_found,
                message=f'Заказ с id={pk} не найден'
            )
            warning(request.path, request.data, response.data)
            return response

        serializer = OrderSerializer(order)
        order_info = serializer.data
        amount = 0
        count = 0
        currency = request.query_params.get('currency') or Currencies.byn
        # todo Скорректировать отображение цены в соответсвтии с уровнем цены и указаной валютой
        order_info['products'] = get_products_by_order(user, order_info['id'])
        for product_item in order_info['products']:
            product_price = ProductPrice.objects.filter(
                product__id=product_item['product']['id'],
                price_level=get_price_level(user.price_level, currency)
            ).first()
            # amount += product_item['count'] * product_item['product']['price']
            amount += product_item['count'] * product_price.price
            product_item['product']['price'] = product_price.price
            count += product_item['count']
        order_info['totalAmount'] = amount
        order_info['totalCount'] = count

        response = ApiResponse(status_code=status.HTTP_200_OK, result=order_info)
        info(request.path, request.data, response.data)
        return response

    @swagger_auto_schema(
        operation_summary='Создать пустой заказ(обязательно с комментарием)',
        request_body=CommentSerializer,
        responses={},
        manual_parameters=[
            Parameter(
                name='manager_id',
                in_='query',
                description='ID менеджера заказа. Если не указать, заказ создастся без менеджера',
                required=False,
                type='int',
            ),
        ],
        tags=['Заказы']
    )
    def create(self, request: Request):
        user = request.user
        order = Order.objects.create(user=user)
        manager_id = self.request.query_params.get('manager_id')
        if manager_id:
            manager = User.objects.filter(id=manager_id, account_type=('MANAGER' or 'ADMIN')).first()
            if manager is not None:
                order.manager = manager
            else:
                response = ApiErrorResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    error_code=ApiErrorCodes.user_not_found,
                    message="Менеджера с таким id нет в базе днных"
                )
                warning(request.path, request.data, response.data)
                return response
        serializer = CommentSerializer(data=request.data)
        if not serializer.is_valid():
            response = ApiErrorResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ApiErrorCodes.validation,
                message="Ошибка валидации",
                result=serializer.errors
            )
            warning(request.path, request.data, response.data)
            return response
        order.comment = serializer.validated_data['comment']
        order.save()
        response = ApiResponse(status_code=status.HTTP_201_CREATED,
                               message="Заказ успешно создан",
                               result=OrderSerializer(order).data)
        info(request.path, request.data, response.data)
        return response

    @swagger_auto_schema(
        operation_summary='Удалить заказ(Пользователь может удалить свой заказ,'
                          ' Мэнеджер - где он мэнеджер, Админ - любой заказ)',
        responses={},
        tags=['Заказы']
    )
    def destroy(self, request: Request, pk=None):
        user = request.user

        order = Order.objects.filter(id=pk).first()
        if order is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.file_not_found,
                message="Заказа с таким  id не существует",
            )
            warning(request.path, request.data, response.data)
            return response
        if user.account_type == 'CLIENT' and order.user != user:
            response = ApiErrorResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                error_code=ApiErrorCodes.bad_credentials,
                message="У вас недостаточно прав для выполнения данного действия"
            )
            warning(request.path, request.data, response.data)
            return response
        if user.account_type == 'MANAGER' and order.manager != user:
            response = ApiErrorResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                error_code=ApiErrorCodes.bad_credentials,
                message="У вас недостаточно прав для выполнения данного действия"
            )
            warning(request.path, request.data, response.data)
            return response
        response = ApiResponse(status_code=status.HTTP_200_OK,
                               message=f"Заказ с id={pk} удален",
                               result=OrderSerializer(order).data)
        info(request.path, request.data, response.data)
        order.delete()
        return response

    @swagger_auto_schema(
        operation_summary='Обновить заказ(Менеджер может обновить свой заказ(где он менеджер),'
                          'Админ - любой заказ)',
        request_body=OrderUpdateSerializer,
        responses={},
        tags=['Заказы']
    )
    def update(self, request: Request, pk=None):
        currency = request.query_params.get('currency') or Currencies.byn
        user = request.user
        order = Order.objects.filter(id=pk).first()
        if order is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.order_not_found,
                message="Заказа с таким  id не существует",
            )
            warning(request.path, request.data, response.data)
            return response
        # if not (user.account_type == 'ADMIN'):
        #     response = ApiErrorResponse(status_code=status.HTTP_403_FORBIDDEN,
        #                                 error_code=ApiErrorCodes.bad_credentials,
        #                                 message="Недостаточно прав для данного действия")
        #     warning(request.path, request.data, response.data)
        #     return response
        serializer = OrderUpdateSerializer(order, data=request.data)
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
        order = Order.objects.filter(id=pk).first()
        if order is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.order_not_found,
                message=f'Заказ с id={pk} не найден'
            )
            warning(request.path, request.data, response.data)
            return response

        serializer = OrderSerializer(order)
        order_info = serializer.data
        amount = 0
        count = 0
        # todo Скорректировать отображение цены в соответсвтии с уровнем цены и указаной валютой
        order_info['products'] = get_products_by_order(user, order_info['id'])
        for product_item in order_info['products']:
            product_price = ProductPrice.objects.filter(
                product__id=product_item['product']['id'],
                price_level=get_price_level(user.price_level, currency)
            ).first()
            # amount += product_item['count'] * product_item['product']['price']
            amount += product_item['count'] * product_price.price
            product_item['product']['price'] = product_price.price
            count += product_item['count']
        order_info['totalAmount'] = amount
        order_info['totalCount'] = count
        response = ApiResponse(status_code=status.HTTP_200_OK,
                               result=order_info)
        info(request.path, request.data, response.data)
        return response

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    @swagger_auto_schema(
        operation_summary='Установить комментарий на заказ(можно только на собственно-созданный заказ)',
        request_body=CommentSerializer,
        responses={200: None},
        tags=['Заказы']
    )
    def setcomment(self, request: Request, pk=None):
        user = request.user
        order = Order.objects.filter(id=pk, user=user).first()
        if order is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.order_not_found,
                message="Заказ не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        serializer = CommentSerializer(order, data=request.data)
        if not serializer.is_valid():
            response = ApiErrorResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ApiErrorCodes.validation,
                message="Ошибка валидации",
                result=serializer.errors
            )
            warning(request.path, request.data, response.data)
            return response
        order.comment = serializer.validated_data['comment']
        order.save()
        response = ApiResponse(status_code=status.HTTP_200_OK,
                               message='Данные успешно обновлены',
                               result=OrderSerializer(order).data)
        info(request.path, request.data, response.data)
        return response

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    @swagger_auto_schema(
        operation_summary='Отправить менеджеру заказ',
        tags=['Заказы']
    )
    def send_to_manager(self, request: Request, pk=None):
        currency = request.query_params.get('currency') or Currencies.byn
        user = request.user
        order = Order.objects.filter(id=pk, user=user).first()
        if order.manager is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.validation,
                message="Менеджер не указан",
            )
            warning(request.path, request.data, response.data)
            return response
        if order is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.order_not_found,
                message="Заказ не найден",
            )
            warning(request.path, request.data, response.data)
            return response

        order.status = Order.OrderStatuses.IN_PROGRESS
        order.save()

        one_c_api = OneCAPI(settings.ONE_C_LOGIN, settings.ONE_C_PASSWORD)
        one_c_api.create_order(order)

        serializer = OrderSerializer(order)
        order_info = serializer.data
        amount = 0
        count = 0

        order_info['products'] = get_products_by_order(user, order_info['id'])
        for product_item in order_info['products']:
            product_price = ProductPrice.objects.filter(
                product__id=product_item['product']['id'],
                price_level=get_price_level(user.price_level, currency)
            ).first()
            # amount += product_item['count'] * product_item['product']['price']
            amount += product_item['count'] * product_price.price
            product_item['product']['price'] = product_price.price
            count += product_item['count']
        order_info['totalAmount'] = amount
        order_info['totalCount'] = count
        return ApiResponse(status.HTTP_200_OK, order_info)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    @swagger_auto_schema(
        operation_summary='Получить список товаров в заказе',
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
        tags=['Заказы']
    )
    def products(self, request: Request, pk=None):  # абсолютно лишний медод
        user = request.user
        order = Order.objects.filter(id=pk, user=user).first()
        if order is None:
            response = ApiErrorResponse(status_code=status.HTTP_404_NOT_FOUND,
                                        error_code=ApiErrorCodes.order_not_found,
                                        message="Заказ не найден")
            warning(request.path, request.data, response.data)
            return response
        # todo Скорректировать отображение цены в соответсвтии с уровнем цены и указаной валютой
        items_qs = OrderItem.objects.filter(order=order)
        if 'offset' in request.query_params:
            offset = int(self.request.query_params.get('offset'))
        else:
            offset = 0
        items_limit = self.request.query_params.get('limit')
        items_qs = items_qs[offset:]
        if items_limit is not None:
            paginator = Paginator(items_qs, items_limit)
            current_page = paginator.get_page(1)
        else:
            current_page = items_qs
        serializer = OrderItemSerializer(current_page, many=True)
        response = ApiResponse(result=serializer.data)
        info(request.path, request.data, response.data)
        return response

    @action(detail=True, methods=['post'], url_path='add', permission_classes=[IsAuthenticated])
    @swagger_auto_schema(
        operation_summary='Добавить товар в заказ',
        manual_parameters=[
            Parameter(
                name='product_id',
                in_='query',
                description='ID товара',
                required=True,
                type='int',
            ),
            Parameter(
                name='count',
                in_='query',
                description='Количество (если больше 0, то добавить; если меньше 0, то удалить)',
                required=False,
                type='int',
                default=1,
            ),
        ],
        tags=[
            'Заказы'
        ]
    )
    def add(self, request: Request, pk: int):
        user = request.user
        count = int(request.query_params.get('count') or 1)
        product_id = request.query_params.get('product_id')
        product = Product.objects.filter(id=product_id).first()
        if product is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.product_not_found,
                message=f'Товара с id={product_id} нет в базе данных'
            )
            warning(request.path, request.data, response.data)
            return response
        order = Order.objects.filter(id=pk).first()
        if order is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.product_not_found,
                message=f'Заказ с id={product_id} не найден'
            )
            warning(request.path, request.data, response.data)
            return response

        # Поиск в заказе айтемов с нужным продуктом
        found = False
        item: OrderItem = None

        for order_item in OrderItem.objects.filter(order=order):
            if order_item.product == product:
                order_item.count += count
                item = order_item
                found = True
        if not found:
            item = OrderItem()
            item.order = order
            item.count = count
            item.product = product

        if item.count > 0:
            item.save()
            response = ApiResponse(
                status_code=status.HTTP_201_CREATED,
                message=f'Товар с id={product_id} в количестве {count} единиц добавлен в корзину',
                result=get_basket_by_user(user)
            )
        else:
            if found:
                item.delete()
                response = ApiResponse(
                    status_code=status.HTTP_200_OK,
                    message=f'Товар с id={product_id} удален из заказа',
                    result=get_basket_by_user(user)
                )
            else:
                response = ApiResponse(
                    status_code=status.HTTP_200_OK,
                    message=f'Товар с id={product_id} не добавлен в заказ',
                    result=get_basket_by_user(user)
                )

        info(request.path, request.data, response.data)
        return response


class OrderItemViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    @swagger_auto_schema(
        operation_summary='Получить список элементов заказа со всех своих заказов',
        responses={},
        tags=['Заказы']
    )
    def list(self, request: Request, order_pk=None):
        # todo Скорректировать отображение цены в соответсвтии с уровнем цены и указаной валютой
        user = request.user
        order = Order.objects.filter(id=order_pk, user=user).first()
        if order is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.order_not_found,
                message="Заказ не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        qs = OrderItem.objects.filter(order=order)
        serializer = OrderItemSerializer(qs, many=True)
        response = ApiResponse(status_code=status.HTTP_200_OK, result=serializer.data)
        info(request.path, request.data, response.data)
        return response

    @swagger_auto_schema(
        operation_summary='Удалить элемент заказа (из любого своего заказа)',
        responses={},
        tags=['Заказы']
    )
    def destroy(self, request: Request, pk=None, order_pk=None):
        user = request.user
        order = Order.objects.filter(id=order_pk, user=user).first()
        if order is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.order_not_found,
                message="Заказ не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        order_item = OrderItem.objects.filter(id=pk).first()
        if order_item is None:
            response = ApiErrorResponse(status_code=status.HTTP_404_NOT_FOUND,
                                        error_code=ApiErrorCodes.order_item_not_found,
                                        message="Нет элемента заказа с таким id")
            warning(request.path, request.data, response.data)
            return response
        response = ApiResponse(status_code=status.HTTP_200_OK,
                               message=f"Заказ с id={pk} удален",
                               result=OrderItemSerializer(order_item).data)
        info(request.path, request.data, response.data)
        order_item.delete()
        return response

    @swagger_auto_schema(
        operation_summary='Создать элемент заказа и добавить в свой заказ',
        manual_parameters=[
            Parameter(
                name='count',
                in_='query',
                description='количество товара',
                required=True,
                type='int',
            ),
            Parameter(
                name='product_id',
                in_='query',
                description='ID товара, который нужно добавить',
                required=True,
                type='int',
            ),
        ],
        responses={},
        tags=['Заказы']
    )
    def create(self, request: Request, order_pk=None):
        user = request.user
        count = self.request.query_params.get('count')
        product_id = self.request.query_params.get('product_id')
        order = Order.objects.filter(id=order_pk, user=user).first()
        if order is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.order_not_found,
                message="Заказ не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        if not (count and product_id):
            response = ApiErrorResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                        message="Недостаточно данных",
                                        error_code=ApiErrorCodes.missing_parameters)
            warning(request.path, request.data, response.data)
            return response
        product = Product.objects.filter(id=product_id).first()
        if product is None:
            response = ApiErrorResponse(status_code=status.HTTP_404_NOT_FOUND,
                                        message="Нет продукта с таким id",
                                        error_code=ApiErrorCodes.product_not_found)
            warning(request.path, request.data, response.data)
            return response
        item = OrderItem.objects.create(order=order, product=product, count=count)
        response = ApiResponse(status_code=status.HTTP_201_CREATED,
                               message="элемент заказа создан",
                               result=OrderItemSerializer(item).data)
        info(request.path, request.data, response.data)
        return response

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    @swagger_auto_schema(
        operation_summary='Установить комментарий на элемент заказа(только из своего заказа)',
        request_body=CommentSerializer,
        responses={200: None},
        tags=['Заказы']
    )
    def setcomment(self, request: Request, order_pk=None, pk=None):
        user = request.user
        order = Order.objects.filter(id=order_pk, user=user)
        if order is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.order_not_found,
                message="Заказ не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        order_item = OrderItem.objects.filter(id=pk).first()
        if order_item is None:
            response = ApiErrorResponse(status_code=status.HTTP_404_NOT_FOUND,
                                        message="Нет элемента заказа с таким id",
                                        error_code=ApiErrorCodes.order_item_not_found)
            warning(request.path, request.data, response.data)
            return response
        serializer = CommentSerializer(order_item, data=request.data)
        if not serializer.is_valid():
            response = ApiErrorResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ApiErrorCodes.validation,
                message="Ошибка валидации",
                result=serializer.errors
            )
            warning(request.path, request.data, response.data)
            return response
        order_item.comment = serializer.validated_data['comment']
        order_item.save()
        response = ApiResponse(status_code=status.HTTP_200_OK,
                               result=OrderItemSerializer(order_item).data)
        info(request.path, request.data, response.data)
        return response

    @swagger_auto_schema(
        operation_summary='Обновить элемент заказа(только из своего заказа)',
        request_body=OrderItemUpdateSerializer,
        responses={200: None},
        tags=['Заказы']
    )
    def update(self, request: Request, pk=None, order_pk=None):
        user = request.user
        order = Order.objects.filter(id=order_pk, user=user)
        if order is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.order_not_found,
                message="Заказ не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        order_item = OrderItem.objects.filter(id=pk).first()
        if order_item is None:
            response = ApiErrorResponse(status_code=status.HTTP_404_NOT_FOUND,
                                        message="Нет элемента заказа с таким id",
                                        error_code=ApiErrorCodes.order_item_not_found)
            warning(request.path, request.data, response.data)
            return response
        serializer = OrderItemUpdateSerializer(order_item, data=request.data)
        if not serializer.is_valid():
            response = ApiErrorResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ApiErrorCodes.validation,
                message="Ошибка валидации",
                result=serializer.errors
            )
            return response
        serializer.save()
        response = ApiResponse(status_code=status.HTTP_200_OK,
                               message='Данные успешно обновлены',
                               result=OrderItemSerializer(order_item).data)
        info(request.path, request.data, response.data)
        return response


class PriceLevelViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    @swagger_auto_schema(
        operation_summary='Получить список уровней цен',
        responses={},
        tags=['Уровни цен']
    )
    def list(self, request: Request, order_pk=None):
        # todo Скорректировать отображение цены уровней цен (заменить на список TextChoices)
        # price_levels_qs = PriceLevel.objects.all()
        # serializer = PriceLevelSerializer(price_levels_qs, many=True)

        price_levels = [
            {
                "name": str(User.PriceLevels.OPT1.name),
                "value": str(User.PriceLevels.OPT1.value),
                "label": str(User.PriceLevels.OPT1.label),
            },
            {
                "name": str(User.PriceLevels.OPT2.name),
                "value": str(User.PriceLevels.OPT2.value),
                "label": str(User.PriceLevels.OPT2.label),
            },
            {
                "name": str(User.PriceLevels.OPT3.name),
                "value": str(User.PriceLevels.OPT3.value),
                "label": str(User.PriceLevels.OPT3.label),
            },
            {
                "name": str(User.PriceLevels.OPT4.name),
                "value": str(User.PriceLevels.OPT4.value),
                "label": str(User.PriceLevels.OPT4.label),
            },
            {
                "name": str(User.PriceLevels.RETAIL_NO_NDS.name),
                "value": str(User.PriceLevels.RETAIL_NO_NDS.value),
                "label": str(User.PriceLevels.RETAIL_NO_NDS.label),
            },
            {
                "name": str(User.PriceLevels.RETAIL_NDS.name),
                "value": str(User.PriceLevels.RETAIL_NDS.value),
                "label": str(User.PriceLevels.RETAIL_NDS.label),
            },

        ]




        response = ApiResponse(status_code=status.HTTP_200_OK, result=price_levels)

        # response = ApiResponse(status_code=status.HTTP_200_OK, result=serializer.data)
        info(request.path, request.data, response.data)
        return response
