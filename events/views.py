from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError

from .models import Event, Reservation
from .serializers import (
    EventSerializer,
    ReservationSerializer,
    CreateReservationSerializer,
    ConfirmReservationSerializer
)
from .services import ReservationService


class EventViewSet(viewsets.ModelViewSet):
    """
    Etkinlik CRUD işlemleri için ViewSet.
    
    View'lar incedir - sadece istek/yanıt işleme yapar, iş mantığı Service katmanında.
    
    Endpoint'ler:
    - GET /api/events/ - Tüm etkinlikleri listele (sayfalama ile) - Tüm kimlik doğrulanmış kullanıcılar
    - GET /api/events/{id}/ - Etkinlik detaylarını getir - Tüm kimlik doğrulanmış kullanıcılar
    - POST /api/events/ - Etkinlik oluştur - Sadece superuser (admin)
    - PUT /api/events/{id}/ - Etkinlik güncelle - Sadece superuser (admin)
    - DELETE /api/events/{id}/ - Etkinlik sil - Sadece superuser (admin)
    """
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        """
        Tüm etkinlikleri listeler.
        GET /api/events/
        
        Query parametreleri:
        - ?is_active=true - Aktif duruma göre filtrele
        - ?start_date=2024-01-01 - Başlangıç tarihine göre filtrele
        - ?end_date=2024-12-31 - Bitiş tarihine göre filtrele
        - ?page=1 - Sayfalama (sayfa başına 20 öğe)
        """
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """
        Etkinlik detaylarını getirir.
        GET /api/events/{id}/
        
        Dönen alanlar:
        - available_capacity: Kalan kapasite
        - hold_count: HOLD rezervasyon sayısı (miktar toplamı)
        - confirmed_count: CONFIRMED rezervasyon sayısı (miktar toplamı)
        """
        return super().retrieve(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """
        Yeni etkinlik oluşturur.
        POST /api/events/
        
        Sadece superuser (admin) etkinlik oluşturabilir.
        """
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only superuser (admin) can create events.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """
        Etkinliği günceller.
        PUT /api/events/{id}/
        
        Sadece superuser (admin) etkinlik güncelleyebilir.
        """
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only superuser (admin) can update events.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """
        Etkinliği kısmen günceller.
        PATCH /api/events/{id}/
        
        Sadece superuser (admin) etkinlik güncelleyebilir.
        """
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only superuser (admin) can update events.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        Etkinliği siler.
        DELETE /api/events/{id}/
        
        Sadece superuser (admin) etkinlik silebilir.
        Başarı mesajı ile JSON yanıt döner.
        """
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only superuser (admin) can delete events.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        instance = self.get_object()
        self.perform_destroy(instance)
        
        return Response(
            {'message': 'Event deleted successfully.'},
            status=status.HTTP_200_OK
        )

    def get_queryset(self):
        """
        Tarih aralığı ve aktif duruma göre filtreleme yapar.
        """
        queryset = super().get_queryset()
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        is_active = self.request.query_params.get('is_active')
        
        if start_date:
            queryset = queryset.filter(start_time__gte=start_date)
        if end_date:
            queryset = queryset.filter(end_time__lte=end_date)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset


class ReservationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Rezervasyon görüntüleme ve yönetimi için ViewSet.
    """
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Kullanıcılar sadece kendi rezervasyonlarını görebilir.
        """
        return Reservation.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def create_hold(self, request):
        """
        HOLD rezervasyon oluşturur.
        POST /api/reservations/create_hold/
        
        İş mantığı için Service katmanını çağırır.
        """
        serializer = CreateReservationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            reservation = ReservationService.create_hold_reservation(
                event_id=serializer.validated_data['event_id'],
                user_id=request.user.id,
                quantity=serializer.validated_data.get('quantity', 1)
            )
            return Response(
                ReservationSerializer(reservation).data,
                status=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Event.DoesNotExist:
            return Response(
                {'error': 'Event not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'])
    def confirm(self, request):
        """
        HOLD rezervasyonu onaylar.
        POST /api/reservations/confirm/
        """
        serializer = ConfirmReservationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            reservation = ReservationService.confirm_reservation(
                reservation_id=serializer.validated_data['reservation_id'],
                user_id=request.user.id
            )
            return Response(
                ReservationSerializer(reservation).data,
                status=status.HTTP_200_OK
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Reservation.DoesNotExist:
            return Response(
                {'error': 'Reservation not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Rezervasyonu iptal eder.
        POST /api/reservations/{id}/cancel/
        """
        try:
            reservation = ReservationService.cancel_reservation(
                reservation_id=pk,
                user_id=request.user.id
            )
            return Response(
                ReservationSerializer(reservation).data,
                status=status.HTTP_200_OK
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Reservation.DoesNotExist:
            return Response(
                {'error': 'Reservation not found'},
                status=status.HTTP_404_NOT_FOUND
            )

