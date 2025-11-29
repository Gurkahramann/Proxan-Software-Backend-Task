"""
Events uygulaması için Celery görevleri.
"""
from celery import shared_task
from events.services import ReservationService


@shared_task(name='expire_old_hold_reservations')
def expire_old_hold_reservations():
    """
    Süresi dolmuş HOLD rezervasyonları işaretlemek için periyodik görev.
    
    Her 1 dakikada bir çalışır ve süresi dolmuş rezervasyonları kontrol eder.
    Sadece 5 dakika geçmiş rezervasyonları işaretler.
    
    Mantık:
    - Görev her 1 dakikada bir çalışır (sık kontrol)
    - Sadece expires_at < now olan rezervasyonları işaretler (5 dakika geçmiş)
    - 5 dakika içindeki rezervasyonlar işaretlenmez
    
    Returns:
        Süresi dolmuş olarak işaretlenen rezervasyon sayısı
    """
    expired_count = ReservationService.expire_old_holds()
    return expired_count

