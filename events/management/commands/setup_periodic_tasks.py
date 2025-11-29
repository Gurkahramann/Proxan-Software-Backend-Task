"""
Celery Beat için periyodik görevleri kurmak için Django yönetim komutu.
HOLD rezervasyonlarını işaretlemek için periyodik görev oluşturur.

Kullanım: python manage.py setup_periodic_tasks
"""
from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule


class Command(BaseCommand):
    help = 'Celery Beat için periyodik görevleri kurar (HOLD rezervasyonlarını işaretle)'

    def handle(self, *args, **options):
        """
        HOLD rezervasyonlarını işaretlemek için periyodik görevi oluşturur veya günceller.
        
        Not: Görev her 1 dakikada bir çalışır, ancak sadece 5 dakika geçmiş rezervasyonları işaretler.
        """
        # Her 1 dakika için interval schedule oluştur
        # Bu kontrol sıklığıdır, süre dolma zamanı değil
        schedule, created = IntervalSchedule.objects.get_or_create(
            every=1,
            period=IntervalSchedule.MINUTES,
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('Created interval schedule: Every 1 minute (check frequency)')
            )
        else:
            self.stdout.write('Interval schedule already exists')

        # Create or update the periodic task
        task, created = PeriodicTask.objects.get_or_create(
            name='Expire Old HOLD Reservations',
            defaults={
                'task': 'expire_old_hold_reservations',
                'interval': schedule,
                'enabled': True,
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    'Created periodic task: "Expire Old HOLD Reservations"'
                )
            )
        else:
            task.interval = schedule
            task.enabled = True
            task.save()
            self.stdout.write(
                self.style.SUCCESS(
                    'Updated periodic task: "Expire Old HOLD Reservations"'
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                '\n✅ Periodic task setup complete!'
                '\n\nTask Behavior:'
                '\n  - Runs every 1 minute to CHECK for expired reservations'
                '\n  - Only expires reservations where 5 minutes have passed'
                '\n  - Reservations still within 5-minute window remain as HOLD'
                '\n\nTo start Celery Beat, run: celery -A reservation_system beat -l info'
            )
        )

