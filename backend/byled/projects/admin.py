from django.contrib import admin
from .models import Project, Room, Area, AreaItem
# Register your models here.
admin.site.register(Project)
admin.site.register(Room)
admin.site.register(Area)
admin.site.register(AreaItem)
