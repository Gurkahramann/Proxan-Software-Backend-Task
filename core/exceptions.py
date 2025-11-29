"""
Rezervasyon sistemi için özel istisna sınıfları.
"""
from rest_framework.exceptions import APIException


class InsufficientCapacityError(APIException):
    """
    Rezervasyon için yeterli kapasite olmadığında fırlatılır.
    HTTP 409 Conflict döner.
    """
    status_code = 409
    default_detail = 'Insufficient capacity for this reservation.'
    default_code = 'insufficient_capacity'


class ReservationExpiredError(APIException):
    """
    Süresi dolmuş bir rezervasyonu onaylamaya çalışıldığında fırlatılır.
    HTTP 400 Bad Request döner.
    """
    status_code = 400
    default_detail = 'Reservation has expired.'
    default_code = 'reservation_expired'

