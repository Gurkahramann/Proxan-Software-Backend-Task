"""
Rezervasyon sistemi projesi için WSGI yapılandırması.

WSGI çağrılabilirini ``application`` adlı modül seviyesinde bir değişken olarak açığa çıkarır.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reservation_system.settings')

application = get_wsgi_application()
