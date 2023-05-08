from rest_framework_nested import routers
from .viewsets import ProductsViewSet, BasketViewSet, OrderViewSet, OrderItemViewSet, ProductFiltersViewSet, \
    PriceLevelViewSet

router = routers.DefaultRouter()

router.register('api/v1/store/products', ProductsViewSet, basename='products')
router.register('api/v1/store/basket', BasketViewSet, basename='basket')
router.register('api/v1/store/orders', OrderViewSet, basename='order')
router.register('api/v1/store/product-filters', ProductFiltersViewSet, basename='product-filters')
router.register('api/v1/store/price-levels', PriceLevelViewSet, basename='price-levels')
items_router = routers.NestedSimpleRouter(router, 'api/v1/store/orders', lookup='order')
items_router.register('items', OrderItemViewSet, basename='item')
