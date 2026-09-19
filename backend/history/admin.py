from django.contrib import admin
from history.models import OccurrenceHistory


class OccurrenceHistoryAdmin(admin.ModelAdmin):
    list_display = ('occurrence', 'user', 'previous_status', 'new_status', 'change_type', 'changed_at')
    list_filter = ('change_type',)
    search_fields = ('occurrence__title',)


admin.site.register(OccurrenceHistory, OccurrenceHistoryAdmin)
