from django.contrib import admin
from notifications.models import Notificacao


@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'occurrence', 'canal', 'tipo', 'status', 'created_at', 'sent_at')
    list_filter = ('canal', 'tipo', 'status')
    search_fields = ('titulo', 'mensagem', 'user__username')
