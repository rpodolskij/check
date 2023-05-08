from django.contrib import admin
from .models import Post, Comment, Categories
# Register your models here.
admin.site.register(Post)
admin.site.register(Comment)
admin.site.register(Categories)
