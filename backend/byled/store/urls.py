from django.urls import path, include

from .routers import router as store_router, items_router


urlpatterns = [
    path('', include(store_router.urls)),
    path('', include(items_router.urls)),
]
