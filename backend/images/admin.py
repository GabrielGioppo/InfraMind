from django.contrib import admin
from images.models import Image

class ImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'occurrence', 'user', 'uploaded_at',)

admin.site.register(Image, ImageAdmin)
