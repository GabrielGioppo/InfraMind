from django.contrib import admin
from logs.models import Log


class LogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'model_name', 'object_id', 'ip_address', 'device', 'created_at')
    search_fields = ('action', 'model_name', 'ip_address')
    list_filter = ('action',)


admin.site.register(Log, LogAdmin)
