from django.contrib import admin
from categories.models import Category, Subcategory


class SubcategoryInline(admin.TabularInline):
    model = Subcategory
    extra = 0

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active',)
    search_fields = ('name',)
    inlines = [SubcategoryInline]

admin.site.register(Category, CategoryAdmin)