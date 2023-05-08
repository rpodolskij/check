from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import ugettext_lazy as _

from .models import User, ActionKey


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('avatar', 'last_name', 'first_name', 'middle_name', 'phone', 'company_name',
                                         'company_address', 'position', 'account_type', 'manager', 'is_confirmed', 'price_level')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'account_type', 'password1', 'password2'),
        }),
    )
    list_display = (
        'email', 'account_type', 'last_name', 'first_name', 'middle_name', 'manager', 'phone', 'company_name',
        'position',
        'is_confirmed'
    )
    search_fields = (
        'email', 'first_name', 'last_name', 'middle_name', 'phone', 'company_name', 'position', 'company_address',
        'account_type'
    )
    ordering = ('first_name', 'last_name', 'middle_name', 'is_confirmed')


admin.site.register(ActionKey)
