from rest_framework_nested import routers
from .viewsets import PostViewSet, CommentViewSet, CategoriesViewSet

router = routers.DefaultRouter()

router.register('api/v1/blog/posts', PostViewSet, basename='posts')
comments_router = routers.NestedSimpleRouter(router, 'api/v1/blog/posts', lookup='post')
comments_router.register('comments', CommentViewSet, basename='comments')
router.register('api/v1/blog/categories', CategoriesViewSet, basename='categories')
