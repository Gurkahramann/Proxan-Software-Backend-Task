from typing import Optional
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta

from .models import Event, Reservation


class ReservationService:
    """
    Rezervasyon iş mantığı için servis katmanı.
    
    ÖNEMLİ: Tüm iş mantığı burada olmalıdır, view veya model'de değil.
    """

    HOLD_EXPIRATION_MINUTES = 5

    @staticmethod
    @transaction.atomic
    def create_hold_reservation(event_id: int, user_id: int, quantity: int = 1) -> Reservation:
        """
        Eşzamanlılık kontrolü ile HOLD rezervasyon oluşturur.
        
        Race condition'ları önlemek için select_for_update() kullanır.
        
        Args:
            event_id: Rezervasyon yapılacak etkinlik ID'si
            user_id: Rezervasyon yapan kullanıcı ID'si
            quantity: Rezerve edilecek miktar
            
        Returns:
            HOLD durumunda Reservation nesnesi
            
        Raises:
            ValidationError: Kapasite yetersizse veya etkinlik aktif değilse
        """
        # Eşzamanlı değişiklikleri önlemek için event satırını kilitle
        event = Event.objects.select_for_update().get(id=event_id)
        
        # Etkinliğin aktif olup olmadığını kontrol et
        if not event.is_active:
            raise ValidationError("Event is not active. Reservations cannot be made for inactive events.")
        
        # Kalan kapasiteyi dinamik olarak hesapla
        available = event.get_available_capacity()
        
        if available < quantity:
            raise ValidationError(
                f"Insufficient capacity. Available: {available}, Requested: {quantity}"
            )
        
        # Süre dolma zamanı ile HOLD rezervasyon oluştur
        expires_at = timezone.now() + timedelta(minutes=ReservationService.HOLD_EXPIRATION_MINUTES)
        reservation = Reservation.objects.create(
            event=event,
            user_id=user_id,
            status=Reservation.Status.HOLD,
            quantity=quantity,
            expires_at=expires_at
        )
        
        return reservation

    @staticmethod
    @transaction.atomic
    def confirm_reservation(reservation_id: int, user_id: int) -> Reservation:
        """
        HOLD rezervasyonu onaylar.
        
        Args:
            reservation_id: Onaylanacak rezervasyon ID'si
            user_id: Kullanıcı ID'si (yetkilendirme için)
            
        Returns:
            Onaylanmış Reservation nesnesi
            
        Raises:
            ValidationError: Rezervasyon geçersiz veya süresi dolmuşsa
        """
        reservation = Reservation.objects.select_for_update().get(id=reservation_id)
        
        # Yetkilendirme kontrolü
        if reservation.user_id != user_id:
            raise ValidationError("You can only confirm your own reservations")
        
        # Durum kontrolü
        if reservation.status != Reservation.Status.HOLD:
            raise ValidationError(f"Reservation is not in HOLD status. Current: {reservation.status}")
        
        # Süre dolma kontrolü
        if reservation.expires_at and reservation.expires_at < timezone.now():
            reservation.status = Reservation.Status.EXPIRED
            reservation.save()
            raise ValidationError("Reservation has expired")
        
        # Kapasite kontrolü için event'i kilitle
        event = Event.objects.select_for_update().get(id=reservation.event_id)
        
        # Etkinliğin hala aktif olup olmadığını kontrol et
        if not event.is_active:
            raise ValidationError("Event is not active. Cannot confirm reservation for inactive event.")
        
        available = event.get_available_capacity()
        
        if available < reservation.quantity:
            raise ValidationError("Insufficient capacity to confirm reservation")
        
        # Rezervasyonu onayla
        reservation.status = Reservation.Status.CONFIRMED
        reservation.expires_at = None
        reservation.save()
        
        return reservation

    @staticmethod
    def cancel_reservation(reservation_id: int, user_id: int) -> Reservation:
        """
        Rezervasyonu iptal eder.
        
        Args:
            reservation_id: İptal edilecek rezervasyon ID'si
            user_id: Kullanıcı ID'si (yetkilendirme için)
            
        Returns:
            İptal edilmiş Reservation nesnesi
        """
        reservation = Reservation.objects.get(id=reservation_id)
        
        if reservation.user_id != user_id:
            raise ValidationError("You can only cancel your own reservations")
        
        if reservation.status in [Reservation.Status.CANCELLED, Reservation.Status.EXPIRED]:
            raise ValidationError(f"Cannot cancel reservation with status: {reservation.status}")
        
        reservation.status = Reservation.Status.CANCELLED
        reservation.save()
        
        return reservation

    @staticmethod
    def expire_old_holds() -> int:
        """
        Süresi dolmuş HOLD rezervasyonları süresi dolmuş olarak işaretler (5 dakika).
        
        Sadece expires_at < now olan rezervasyonları işaretler (5 dakika geçmiş).
        5 dakika içindeki rezervasyonlar işaretlenmez.
        
        Celery periyodik görevi tarafından her 1 dakikada bir çağrılır.
        
        Returns:
            Süresi dolmuş olarak işaretlenen rezervasyon sayısı
        """
        now = timezone.now()
        # Sadece expires_at < now olan rezervasyonları işaretle (5 dakika geçmiş)
        expired_count = Reservation.objects.filter(
            status=Reservation.Status.HOLD,
            expires_at__lt=now
        ).update(status=Reservation.Status.EXPIRED)
        
        return expired_count

