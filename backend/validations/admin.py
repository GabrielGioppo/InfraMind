from django.contrib import admin
from validations.models import Validation

class ValidationAdmin(admin.ModelAdmin):
    list_display = ('user', 'occurrence', 'validated_at',)

admin.site.register(Validation, ValidationAdmin)
