from rest_framework import routers

from .viewsets import AuthViewSet

router = routers.SimpleRouter()
router.register('api/v1/auth', AuthViewSet, basename='auth')
