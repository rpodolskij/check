from typing import Optional

from rest_framework import serializers

from .models import Project, Room, Area, AreaItem
from users.serializers import UserSerializer
from store.models import PriceLevel, ProductPrice
from users.models import User


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


class ProjectSerializer(serializers.ModelSerializer):
    summary_price = serializers.ReadOnlyField(source='amount')
    owner = UserSerializer()
    client = UserSerializer()

    class Meta:
        model = Project
        depth = 1
        fields = '__all__'


class ProjectCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['title', 'client']


class ProjectUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        # fields = ['title', 'owner', 'status', 'reason_of_refuse']
        fields = ['title', 'client_address', 'status', 'reason_of_refuse', 'discount']


class RoomCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['title']


class RoomSerializer(serializers.ModelSerializer):
    # project = ProjectSerializer()

    class Meta:
        model = Room
        fields = '__all__'


class AreaSerializer(serializers.ModelSerializer):
    # room = RoomSerializer()

    class Meta:
        model = Area
        fields = '__all__'


class AreaCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = ['title']


class AreaSetDiscountSerializer(serializers.Serializer):
    discount = serializers.IntegerField(min_value=0, max_value=100)


class AreaItemUpdateSerializer(serializers.Serializer):
    price = serializers.DecimalField(required=False, allow_null=False, max_digits=10, decimal_places=2)


class ProductPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPrice
        fields = (
            'id',
            'price',
            'created_at'
        )


class AreaItemSerializer(serializers.ModelSerializer):
    price = serializers.SerializerMethodField()
    custom_price = serializers.SerializerMethodField()
    price_history = serializers.SerializerMethodField()

    def get_price_history(self, item: AreaItem):

        currency: str = self.context.get('currency')
        if currency is None:
            return []
        user_price_level: str = self.context.get('user_price_level')
        if user_price_level is None:
            return []

        price_level: PriceLevel = get_price_level(user_price_level, currency)
        if price_level is None:
            return []

        product_price: ProductPrice = ProductPrice.objects.filter(
            price_level=price_level,
            product=item.product_id,
        )

        return ProductPriceSerializer(product_price, many=True).data

    def get_price(self, item: AreaItem):
        if (item.product.id_1c in [None, '']):
            return item.product.price
        currency: str = self.context.get('currency')
        if currency is None:
            return 0
            # return -2
        user_price_level: str = self.context.get('user_price_level')
        if user_price_level is None:
            # return -3
            return 0

        if currency == Currencies.byn and (item.price_byn != 0):
            return item.price_byn

        if currency == Currencies.rub and (item.price_rub != 0):
            return item.price_rub

        price_level: PriceLevel = get_price_level(user_price_level, currency)
        if price_level is None:
            return 0
            # return -4

        product_price: ProductPrice = ProductPrice.objects.filter(
            price_level=price_level,
            product=item.product_id,
        ).first()

        if product_price is None:
            return 0
            # return -4

        return product_price.price

    def get_custom_price(self, item: AreaItem):
        currency: str = self.context.get('currency')
        if currency is None:
            return -2
        user_price_level: str = self.context.get('user_price_level')
        if user_price_level is None:
            return -3

        if currency == Currencies.byn and (item.price_byn != 0):
            return item.price_byn

        if currency == Currencies.rub and (item.price_rub != 0):
            return item.price_rub

        return None

    class Meta:
        model = AreaItem
        fields = '__all__'
        depth = 1
