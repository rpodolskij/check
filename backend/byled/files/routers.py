from rest_framework_nested import routers
from .viewsets import FileViewSet

router = routers.DefaultRouter()

router.register('api/v1/files', FileViewSet, basename='files')
