from django.contrib import admin

from .models import Basket, BasketItem, Order, OrderItem, Product, ProductCategory, PriceLevel, ProductPrice


class ProductAdmin(admin.ModelAdmin):
    list_display = ('vendor_code', 'name', 'count', 'is_archive')
    search_fields = ('name', 'category', 'brand', 'manufacturer')
    list_filter = ('category', 'brand', 'is_archive', 'type', 'manufacturer')

class ProductPriceAdmin(admin.ModelAdmin):
    list_display = ('price_level', 'product', 'price', 'created_at')
    search_fields = ('product__name',)
    list_filter = ('price_level', )



# Register your models here.
admin.site.register(Basket)
admin.site.register(BasketItem)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Product, ProductAdmin)
admin.site.register(ProductCategory)
admin.site.register(PriceLevel)
admin.site.register(ProductPrice, ProductPriceAdmin)
