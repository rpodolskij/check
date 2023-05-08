from django.urls import path, include

from .routers import router as blog_router, comments_router

urlpatterns = [
    path('', include(blog_router.urls)),
    path('', include(comments_router.urls)),
]