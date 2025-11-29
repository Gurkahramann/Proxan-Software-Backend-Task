"""
Rezervasyon sistemi projesi için ASGI yapılandırması.

ASGI çağrılabilirini ``application`` adlı modül seviyesinde bir değişken olarak açığa çıkarır.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reservation_system.settings')

application = get_asgi_application()
