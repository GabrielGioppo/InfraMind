from django.contrib import admin

from denuncias.models import Denuncia


@admin.register(Denuncia)
class DenunciaAdmin(admin.ModelAdmin):
    list_display = ('id', 'tipo', 'status', 'user', 'occurrence', 'created_at')
    list_filter = ('tipo', 'status')
    search_fields = ('descricao', 'user__username')
