"""
Süresi dolmuş HOLD rezervasyonları işaretlemek için Django yönetim komutu.

Kullanım: python manage.py expire_holds
"""
from django.core.management.base import BaseCommand
from events.services import ReservationService


class Command(BaseCommand):
    help = 'Süresi dolmuş HOLD rezervasyonlarını süresi dolmuş olarak işaretler'

    def handle(self, *args, **options):
        """
        Süre dolma mantığını çalıştırır.
        Service katmanı metodunu çağırır.
        """
        expired_count = ReservationService.expire_old_holds()
        
        if expired_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully expired {expired_count} reservation(s)'
                )
            )
        else:
            self.stdout.write('No reservations to expire')

