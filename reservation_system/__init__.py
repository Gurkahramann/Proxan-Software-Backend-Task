# Django başladığında uygulamanın her zaman import edilmesini sağlar
# Böylece shared_task bu uygulamayı kullanır
from .celery import app as celery_app

__all__ = ('celery_app',)

