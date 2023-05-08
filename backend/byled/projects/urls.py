from django.urls import path, include

from .routers import router as projects_router, rooms_router, areas_router
from . import viewsets

urlpatterns = [
    path('', include(projects_router.urls)),
    path('', include(rooms_router.urls)),
    path('', include(areas_router.urls)),
    path('api/v1/area-items/<int:id>', viewsets.AreaItemAPIView.as_view()),
]
