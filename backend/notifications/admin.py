from django.contrib import admin
from notifications.models import Notificacao


class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ('user', 'tipo', 'canal', 'status', 'created_at')
    list_filter = ('tipo', 'canal', 'status')


admin.site.register(Notificacao, NotificacaoAdmin)
