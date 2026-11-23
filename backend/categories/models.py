from django.db import models

class Category(models.Model):
    """Setor responsável (ex.: Saneamento básico). As subcategorias detalham o problema."""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"


class Subcategory(models.Model):
    """Tipo de problema dentro de um setor (ex.: Saneamento básico → Esgoto entupido)."""
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category__name', 'name']
        verbose_name = 'subcategoria'
        verbose_name_plural = 'subcategorias'
        constraints = [
            models.UniqueConstraint(fields=['category', 'name'], name='subcategoria_unica_por_setor'),
        ]

    def __str__(self):
        return f'{self.category.name} — {self.name}'

