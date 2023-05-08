#from rest_framework import routers
from .viewsets import ProjectViewSet, RoomViewSet, AreaViewSet
from rest_framework_nested import routers

router = routers.SimpleRouter()
router.register('api/v1/projects', ProjectViewSet, basename='projects')
rooms_router = routers.NestedSimpleRouter(router, 'api/v1/projects', lookup='project')
rooms_router.register('rooms', RoomViewSet, basename='rooms')
areas_router = routers.NestedSimpleRouter(rooms_router, 'rooms', lookup='room')
areas_router.register('areas', AreaViewSet, basename='areas')
