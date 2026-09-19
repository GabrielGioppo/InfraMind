# users/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """Model para usuários do sistema"""
    
    USER_TYPE_CHOICES = [
        ('citizen', 'Cidadão'),
        ('admin', 'Administrador'),
    ]
    
    # Remova os campos que já existem no AbstractUser
    # Não precisa redefinir email, username, password, etc.
    
    user_type = models.CharField(
        max_length=10,
        choices=USER_TYPE_CHOICES,
        default='citizen'
    )
    date_of_birth = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.username