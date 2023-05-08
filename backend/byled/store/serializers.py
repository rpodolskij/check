from rest_framework import serializers

from .models import Product, Basket, Order, OrderItem, BasketItem, ProductCategory, ProductPrice, PriceLevel

from users.serializers import UserSerializer, UserManagerSerializer


class PriceLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceLevel
        exclude = ['products']


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = '__all__'

    def get_image(self, obj: Product):
        if (str(obj.image_url) != ''):
            return str(obj.image_url).replace('/uploads/byled', '')
        if str(obj.image) != '':
            return f"/uploads/products/{str(obj.image).split('/')[-1]}"
        else:
            return f"/static/images/no_photo.png"


class ProductPriceSerializer(serializers.ModelSerializer):
    product = ProductSerializer()

    class Meta:
        model = ProductPrice
        fields = '__all__'
        depth = 1


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        exclude = ['id']


class BasketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Basket
        fields = '__all__'


class BasketItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BasketItem
        fields = '__all__'


class OrderSerializer(serializers.ModelSerializer):
    user = UserSerializer(required=True)
    manager = UserSerializer(required=False)
    summary_price = serializers.ReadOnlyField(source='amount')

    class Meta:
        model = Order
        depth = 1
        fields = '__all__'


class OrderUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['comment', 'status', 'manager']


class OrderItemSerializer(serializers.ModelSerializer):
    summary_price = serializers.ReadOnlyField(source='amount')

    class Meta:
        model = OrderItem
        depth = 1
        fields = '__all__'


class OrderItemUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        exclude = ['order']


class CommentSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True)


class ProductCategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    def get_children(self, obj: ProductCategory):
        return ProductCategorySerializer(obj.children, many=True).data

    class Meta:
        model = ProductCategory
        fields = [
            'id', 'name', 'children'
        ]
