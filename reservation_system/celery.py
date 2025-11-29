"""
Rezervasyon sistemi için Celery yapılandırması.

Celery arka plan işleri için kullanılır, özellikle HOLD rezervasyonlarını işaretlemek için.
"""
import os
from celery import Celery

# Celery için varsayılan Django settings modülünü ayarla
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reservation_system.settings')

app = Celery('reservation_system')

# String kullanmak, worker'ın yapılandırma nesnesini child process'lere serialize etmesini önler
# namespace='CELERY' tüm celery ile ilgili yapılandırma anahtarlarının 'CELERY_' öneki ile başlaması gerektiği anlamına gelir
app.config_from_object('django.conf:settings', namespace='CELERY')

# Tüm kayıtlı Django uygulamalarından task modüllerini yükle
# Tüm kurulu uygulamalardaki tasks.py dosyalarını keşfeder
app.autodiscover_tasks()

