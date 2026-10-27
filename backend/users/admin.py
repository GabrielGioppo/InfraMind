from django.contrib import admin
from users.models import User

class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'user_type', 'cidade', 'uf', 'is_active')
    search_fields = ('username', 'email', 'cpf', 'cidade')

admin.site.register(User, UserAdmin)
