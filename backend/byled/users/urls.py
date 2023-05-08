from django.contrib import admin
from django.urls import path, include

from .routers import router as users_router

urlpatterns = [
    path('', include(users_router.urls)),
]
