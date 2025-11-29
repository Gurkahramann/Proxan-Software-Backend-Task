from rest_framework import serializers
from .models import Event, Reservation


class EventSerializer(serializers.ModelSerializer):
    """
    Etkinlik okuma/yazma işlemleri için serializer.
    
    İçerir:
    - available_capacity: Kalan kapasite
    - hold_count: HOLD rezervasyon sayısı (miktar toplamı)
    - confirmed_count: CONFIRMED rezervasyon sayısı (miktar toplamı)
    """
    available_capacity = serializers.SerializerMethodField()
    hold_count = serializers.SerializerMethodField()
    confirmed_count = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'id', 'name', 'description', 'capacity', 'available_capacity',
            'hold_count', 'confirmed_count',
            'start_time', 'end_time', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_available_capacity(self, obj) -> int:
        """
        Serializasyon için kalan kapasiteyi hesaplar.
        Not: Sadece görüntüleme içindir. Gerçek kapasite kontrolü servislerde yapılır.
        """
        return obj.get_available_capacity()

    def get_hold_count(self, obj) -> int:
        """
        Aktif HOLD rezervasyonların toplam miktarını döndürür.
        """
        return obj.get_hold_count()

    def get_confirmed_count(self, obj) -> int:
        """
        CONFIRMED rezervasyonların toplam miktarını döndürür.
        """
        return obj.get_confirmed_count()


class ReservationSerializer(serializers.ModelSerializer):
    """
    Rezervasyon okuma işlemleri için serializer.
    """
    event_name = serializers.CharField(source='event.name', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Reservation
        fields = [
            'id', 'event', 'event_name', 'user', 'user_username',
            'status', 'quantity', 'expires_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'status', 'created_at', 'updated_at']


class CreateReservationSerializer(serializers.Serializer):
    """
    HOLD rezervasyon oluşturma için serializer.
    Service katmanına göndermeden önce girdiyi doğrular.
    """
    event_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)

    def validate_event_id(self, value):
        try:
            event = Event.objects.get(id=value)
            if not event.is_active:
                raise serializers.ValidationError("Event is not active. Reservations cannot be made for inactive events.")
        except Event.DoesNotExist:
            raise serializers.ValidationError("Event does not exist")
        return value


class ConfirmReservationSerializer(serializers.Serializer):
    """
    Rezervasyon onaylama için serializer.
    """
    reservation_id = serializers.IntegerField()

    def validate_reservation_id(self, value):
        if not Reservation.objects.filter(id=value).exists():
            raise serializers.ValidationError("Reservation does not exist")
        return value

