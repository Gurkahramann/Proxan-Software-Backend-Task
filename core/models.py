"""
Rezervasyon sistemi için soyut temel modeller.
"""
from django.db import models


class BaseModel(models.Model):
    """
    Ortak alanları (created_at, updated_at) içeren soyut temel model.
    Tüm modeller bu sınıftan türetilerek otomatik olarak oluşturulma ve güncellenme zamanlarını alır.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
