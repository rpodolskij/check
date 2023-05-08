from django.urls import path, include

from .routers import router as auth_router

urlpatterns = [
    path('', include(auth_router.urls)),
]
