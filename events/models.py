from django.db import models
from django.db.models import Sum
from django.core.validators import MinValueValidator
from django.utils import timezone
from users.models import User


class Event(models.Model):
    """
    Rezervasyon yapılabilen etkinlik modeli.
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    capacity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=True, help_text='Whether the event is active and can accept reservations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'events'
        ordering = ['start_time']

    def __str__(self) -> str:
        return self.name

    def get_hold_count(self) -> int:
        """
        Aktif HOLD rezervasyonların toplam miktarını döndürür (süresi dolmamış).
        Rezervasyon sayısı değil, miktar toplamı döner.
        """
        active_holds_quantity = self.reservations.filter(
            status='HOLD',
            expires_at__gt=timezone.now()
        ).aggregate(total=Sum('quantity'))['total'] or 0
        return active_holds_quantity

    def get_confirmed_count(self) -> int:
        """
        CONFIRMED rezervasyonların toplam miktarını döndürür.
        Rezervasyon sayısı değil, miktar toplamı döner.
        """
        confirmed_quantity = self.reservations.filter(
            status='CONFIRMED'
        ).aggregate(total=Sum('quantity'))['total'] or 0
        return confirmed_quantity

    def get_available_capacity(self) -> int:
        """
        Kalan kapasiteyi dinamik olarak hesaplar.
        Transaction içinde select_for_update() ile kullanılmalıdır.
        
        Önemli: Rezervasyon sayısı değil, miktar toplamı hesaplanır.
        """
        active_holds_quantity = self.get_hold_count()
        confirmed_quantity = self.get_confirmed_count()
        return self.capacity - (active_holds_quantity + confirmed_quantity)


class Reservation(models.Model):
    """
    İki aşamalı rezervasyon modeli (HOLD ve CONFIRMED).
    """
    class Status(models.TextChoices):
        HOLD = 'HOLD', 'Hold'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        EXPIRED = 'EXPIRED', 'Expired'

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='reservations')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservations')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.HOLD)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)], default=1)
    expires_at = models.DateTimeField(null=True, blank=True)  # HOLD durumu için
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reservations'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"{self.user.username} - {self.event.name} ({self.status})"

