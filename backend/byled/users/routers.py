from rest_framework import routers

from .viewsets import UserViewSet

router = routers.DefaultRouter()
router.register('api/v1/users', UserViewSet, basename='user')
