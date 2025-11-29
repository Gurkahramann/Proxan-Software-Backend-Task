from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import timedelta
import threading
import time

from .models import Event, Reservation
from .services import ReservationService

User = get_user_model()


class EventModelTestCase(TestCase):
    """
    Event modeli için unit testler.
    """
    
    def setUp(self):
        """Her test metodundan önce test verilerini hazırlar."""
        self.event = Event.objects.create(
            name='Test Event',
            description='Test Description',
            capacity=100,
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=3),
            is_active=True
        )
    
    def test_event_creation(self):
        """Tüm alanlarla etkinlik oluşturmayı test eder."""
        self.assertEqual(self.event.name, 'Test Event')
        self.assertEqual(self.event.capacity, 100)
        self.assertTrue(self.event.is_active)
        self.assertIsNotNone(self.event.created_at)
    
    def test_event_str_representation(self):
        """Etkinlik string temsilini test eder."""
        self.assertEqual(str(self.event), 'Test Event')
    
    def test_get_available_capacity_no_reservations(self):
        """Rezervasyon olmadan kalan kapasite hesaplamasını test eder."""
        available = self.event.get_available_capacity()
        self.assertEqual(available, 100)
    
    def test_get_hold_count_no_holds(self):
        """HOLD olmadan HOLD sayısını test eder."""
        hold_count = self.event.get_hold_count()
        self.assertEqual(hold_count, 0)
    
    def test_get_confirmed_count_no_confirmed(self):
        """Onaylanmış rezervasyon olmadan onaylanmış sayısını test eder."""
        confirmed_count = self.event.get_confirmed_count()
        self.assertEqual(confirmed_count, 0)
    
    def test_get_hold_count_with_holds(self):
        """Aktif HOLD'larla HOLD sayısı hesaplamasını test eder."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # HOLD rezervasyonları oluştur
        Reservation.objects.create(
            event=self.event,
            user=user,
            status=Reservation.Status.HOLD,
            quantity=5,
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        Reservation.objects.create(
            event=self.event,
            user=user,
            status=Reservation.Status.HOLD,
            quantity=3,
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        hold_count = self.event.get_hold_count()
        self.assertEqual(hold_count, 8)  # 5 + 3 = 8
    
    def test_get_confirmed_count_with_confirmed(self):
        """Onaylanmış rezervasyonlarla onaylanmış sayısı hesaplamasını test eder."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Onaylanmış rezervasyonları oluştur
        Reservation.objects.create(
            event=self.event,
            user=user,
            status=Reservation.Status.CONFIRMED,
            quantity=10
        )
        Reservation.objects.create(
            event=self.event,
            user=user,
            status=Reservation.Status.CONFIRMED,
            quantity=15
        )
        
        confirmed_count = self.event.get_confirmed_count()
        self.assertEqual(confirmed_count, 25)  # 10 + 15 = 25
    
    def test_get_available_capacity_with_reservations(self):
        """Hem HOLD hem de onaylanmış rezervasyonlarla kalan kapasiteyi test eder."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create HOLD reservation
        Reservation.objects.create(
            event=self.event,
            user=user,
            status=Reservation.Status.HOLD,
            quantity=20,
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        # Onaylanmış rezervasyonu oluştur
        Reservation.objects.create(
            event=self.event,
            user=user,
            status=Reservation.Status.CONFIRMED,
            quantity=30
        )
        
        available = self.event.get_available_capacity()
        self.assertEqual(available, 50)  # 100 - 20 - 30 = 50
    
    def test_get_hold_count_excludes_expired(self):
        """Süresi dolmuş HOLD'ların sayılmadığını test eder."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create active HOLD
        Reservation.objects.create(
            event=self.event,
            user=user,
            status=Reservation.Status.HOLD,
            quantity=5,
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        # Create expired HOLD
        Reservation.objects.create(
            event=self.event,
            user=user,
            status=Reservation.Status.HOLD,
            quantity=10,
            expires_at=timezone.now() - timedelta(minutes=1)  # Expired
        )
        
        hold_count = self.event.get_hold_count()
        self.assertEqual(hold_count, 5)  # Sadece aktif HOLD sayıldı


class ReservationServiceTestCase(TestCase):
    """
    ReservationService için unit testler.
    """
    
    def setUp(self):
        """Her test metodundan önce test verilerini hazırlar."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.event = Event.objects.create(
            name='Test Event',
            description='Test Description',
            capacity=100,
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=3),
            is_active=True
        )
    
    def test_create_hold_reservation_success(self):
        """Başarılı HOLD rezervasyon oluşturmayı test eder."""
        reservation = ReservationService.create_hold_reservation(
            event_id=self.event.id,
            user_id=self.user.id,
            quantity=5
        )
        
        self.assertEqual(reservation.status, Reservation.Status.HOLD)
        self.assertEqual(reservation.quantity, 5)
        self.assertIsNotNone(reservation.expires_at)
        self.assertEqual(reservation.user_id, self.user.id)
        self.assertEqual(reservation.event_id, self.event.id)
        
        # Süre dolma zamanının doğru ayarlandığını doğrula (5 dakika)
        expected_expiration = timezone.now() + timedelta(minutes=5)
        time_diff = abs((reservation.expires_at - expected_expiration).total_seconds())
        self.assertLess(time_diff, 10)  # 10 saniye tolerans
    
    def test_create_hold_reservation_insufficient_capacity(self):
        """Yetersiz kapasitede HOLD rezervasyon oluşturmayı test eder."""
        # Kapasiteyi doldur
        Reservation.objects.create(
            event=self.event,
            user=self.user,
            status=Reservation.Status.CONFIRMED,
            quantity=100
        )
        
        with self.assertRaises(ValidationError) as context:
            ReservationService.create_hold_reservation(
                event_id=self.event.id,
                user_id=self.user.id,
                quantity=1
            )
        
        self.assertIn('Insufficient capacity', str(context.exception))
    
    def test_create_hold_reservation_inactive_event(self):
        """Test creating HOLD reservation for inactive event."""
        self.event.is_active = False
        self.event.save()
        
        with self.assertRaises(ValidationError) as context:
            ReservationService.create_hold_reservation(
                event_id=self.event.id,
                user_id=self.user.id,
                quantity=5
            )
        
        self.assertIn('not active', str(context.exception))
    
    def test_confirm_reservation_success(self):
        """Başarılı HOLD rezervasyon onaylamayı test eder."""
        # HOLD rezervasyonu oluştur
        reservation = Reservation.objects.create(
            event=self.event,
            user=self.user,
            status=Reservation.Status.HOLD,
            quantity=5,
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        # Rezervasyonu onayla
        confirmed = ReservationService.confirm_reservation(
            reservation_id=reservation.id,
            user_id=self.user.id
        )
        
        self.assertEqual(confirmed.status, Reservation.Status.CONFIRMED)
        self.assertIsNone(confirmed.expires_at)
        self.assertEqual(confirmed.quantity, 5)
    
    def test_confirm_reservation_wrong_user(self):
        """Test confirming reservation belonging to another user."""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        
        reservation = Reservation.objects.create(
            event=self.event,
            user=self.user,
            status=Reservation.Status.HOLD,
            quantity=5,
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        with self.assertRaises(ValidationError) as context:
            ReservationService.confirm_reservation(
                reservation_id=reservation.id,
                user_id=other_user.id
            )
        
        self.assertIn('own reservations', str(context.exception))
    
    def test_confirm_reservation_not_hold_status(self):
        """HOLD durumunda olmayan rezervasyonu onaylamayı test eder."""
        reservation = Reservation.objects.create(
            event=self.event,
            user=self.user,
            status=Reservation.Status.CONFIRMED,
            quantity=5
        )
        
        with self.assertRaises(ValidationError) as context:
            ReservationService.confirm_reservation(
                reservation_id=reservation.id,
                user_id=self.user.id
            )
        
        self.assertIn('not in HOLD status', str(context.exception))
    
    def test_confirm_reservation_expired(self):
        """Süresi dolmuş rezervasyonu onaylamayı test eder."""
        reservation = Reservation.objects.create(
            event=self.event,
            user=self.user,
            status=Reservation.Status.HOLD,
            quantity=5,
            expires_at=timezone.now() - timedelta(minutes=1)  # Süresi dolmuş
        )
        
        with self.assertRaises(ValidationError) as context:
            ReservationService.confirm_reservation(
                reservation_id=reservation.id,
                user_id=self.user.id
            )
        
        self.assertIn('expired', str(context.exception))
        
        # Not: Exception nedeniyle transaction rollback olduğu için durum değişikliği geri alınır.
        # Önemli olan exception'ın fırlatılmasıdır.
        # Süre dolmasını doğrulamak için expire_old_holds() metodunu kullanın.
        # Bu test, süresi dolmuş rezervasyonların onaylanamayacağını doğrular.
    
    def test_confirm_reservation_insufficient_capacity(self):
        """Kapasite yetersiz hale geldiğinde rezervasyon onaylamayı test eder."""
        # Kapasiteyi diğer rezervasyonlarla doldur
        Reservation.objects.create(
            event=self.event,
            user=self.user,
            status=Reservation.Status.CONFIRMED,
            quantity=96  # 4 kapasite bırak
        )
        
        # 5 için HOLD oluştur (mevcut olandan fazla)
        reservation = Reservation.objects.create(
            event=self.event,
            user=self.user,
            status=Reservation.Status.HOLD,
            quantity=5,
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        with self.assertRaises(ValidationError) as context:
            ReservationService.confirm_reservation(
                reservation_id=reservation.id,
                user_id=self.user.id
            )
        
        self.assertIn('Insufficient capacity', str(context.exception))
    
    def test_cancel_reservation_success(self):
        """Başarılı rezervasyon iptalini test eder."""
        reservation = Reservation.objects.create(
            event=self.event,
            user=self.user,
            status=Reservation.Status.HOLD,
            quantity=5,
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        cancelled = ReservationService.cancel_reservation(
            reservation_id=reservation.id,
            user_id=self.user.id
        )
        
        self.assertEqual(cancelled.status, Reservation.Status.CANCELLED)
    
    def test_cancel_reservation_wrong_user(self):
        """Başka kullanıcıya ait rezervasyonu iptal etmeyi test eder."""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        
        reservation = Reservation.objects.create(
            event=self.event,
            user=self.user,
            status=Reservation.Status.HOLD,
            quantity=5
        )
        
        with self.assertRaises(ValidationError) as context:
            ReservationService.cancel_reservation(
                reservation_id=reservation.id,
                user_id=other_user.id
            )
        
        self.assertIn('own reservations', str(context.exception))
    
    def test_cancel_reservation_already_cancelled(self):
        """Zaten iptal edilmiş rezervasyonu iptal etmeyi test eder."""
        reservation = Reservation.objects.create(
            event=self.event,
            user=self.user,
            status=Reservation.Status.CANCELLED,
            quantity=5
        )
        
        with self.assertRaises(ValidationError) as context:
            ReservationService.cancel_reservation(
                reservation_id=reservation.id,
                user_id=self.user.id
            )
        
        self.assertIn('Cannot cancel', str(context.exception))
    
    def test_expire_old_holds(self):
        """Eski HOLD rezervasyonlarını süresi dolmuş olarak işaretlemeyi test eder."""
        # Süresi dolmuş HOLD oluştur
        expired_reservation = Reservation.objects.create(
            event=self.event,
            user=self.user,
            status=Reservation.Status.HOLD,
            quantity=5,
            expires_at=timezone.now() - timedelta(minutes=1)  # Süresi dolmuş
        )
        
        # Aktif HOLD oluştur
        active_reservation = Reservation.objects.create(
            event=self.event,
            user=self.user,
            status=Reservation.Status.HOLD,
            quantity=3,
            expires_at=timezone.now() + timedelta(minutes=10)  # Hala aktif
        )
        
        # Eski HOLD'ları süresi dolmuş olarak işaretle
        expired_count = ReservationService.expire_old_holds()
        
        self.assertEqual(expired_count, 1)
        
        # Süresi dolmuş rezervasyonu doğrula
        expired_reservation.refresh_from_db()
        self.assertEqual(expired_reservation.status, Reservation.Status.EXPIRED)
        
        # Aktif rezervasyonun hala HOLD olduğunu doğrula
        active_reservation.refresh_from_db()
        self.assertEqual(active_reservation.status, Reservation.Status.HOLD)


class EventAPITestCase(APITestCase):
    """
    Event ViewSet için API testleri.
    """
    
    def setUp(self):
        """Her test metodundan önce test verilerini hazırlar."""
        self.client = APIClient()
        self.events_url = '/api/events/'
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        self.event = Event.objects.create(
            name='Test Event',
            description='Test Description',
            capacity=100,
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=3),
            is_active=True
        )
    
    def test_list_events_authenticated(self):
        """Etkinlikleri listelemenin kimlik doğrulama gerektirdiğini test eder."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.events_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
    
    def test_list_events_unauthenticated(self):
        """Kimlik doğrulama olmadan etkinlikleri listelemenin başarısız olduğunu test eder."""
        response = self.client.get(self.events_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_retrieve_event_details(self):
        """Kapasite bilgisiyle etkinlik detaylarını getirmeyi test eder."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'{self.events_url}{self.event.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('available_capacity', response.data)
        self.assertIn('hold_count', response.data)
        self.assertIn('confirmed_count', response.data)
        self.assertEqual(response.data['available_capacity'], 100)
    
    def test_create_event_superuser_only(self):
        """Sadece superuser'ın etkinlik oluşturabileceğini test eder."""
        # Normal kullanıcı oluşturamaz
        self.client.force_authenticate(user=self.user)
        event_data = {
            'name': 'New Event',
            'description': 'New Description',
            'capacity': 50,
            'start_time': (timezone.now() + timedelta(days=2)).isoformat(),
            'end_time': (timezone.now() + timedelta(days=2, hours=3)).isoformat(),
            'is_active': True
        }
        
        response = self.client.post(self.events_url, event_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Superuser oluşturabilir
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self.events_url, event_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Event')
    
    def test_update_event_superuser_only(self):
        """Sadece superuser'ın etkinlik güncelleyebileceğini test eder."""
        # Normal kullanıcı güncelleyemez
        self.client.force_authenticate(user=self.user)
        update_data = {'name': 'Updated Event'}
        
        response = self.client.patch(
            f'{self.events_url}{self.event.id}/',
            update_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Superuser güncelleyebilir
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f'{self.events_url}{self.event.id}/',
            update_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Event')
    
    def test_delete_event_superuser_only(self):
        """Sadece superuser'ın etkinlik silebileceğini test eder."""
        # Normal kullanıcı silemez
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(f'{self.events_url}{self.event.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Superuser silebilir
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(f'{self.events_url}{self.event.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertIn('deleted successfully', response.data['message'])
        
        # Etkinliğin silindiğini doğrula
        self.assertFalse(Event.objects.filter(id=self.event.id).exists())
    
    def test_filter_events_by_is_active(self):
        """is_active durumuna göre etkinlikleri filtrelemeyi test eder."""
        # Pasif etkinlik oluştur
        inactive_event = Event.objects.create(
            name='Inactive Event',
            description='Inactive',
            capacity=50,
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=2),
            is_active=False
        )
        
        self.client.force_authenticate(user=self.user)
        
        # Aktif etkinlikleri filtrele
        response = self.client.get(f'{self.events_url}?is_active=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.event.id)
        
        # Pasif etkinlikleri filtrele
        response = self.client.get(f'{self.events_url}?is_active=false')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], inactive_event.id)


class ReservationAPITestCase(APITestCase):
    """
    Reservation ViewSet için API testleri.
    """
    
    def setUp(self):
        """Her test metodundan önce test verilerini hazırlar."""
        self.client = APIClient()
        self.reservations_url = '/api/reservations/'
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        
        self.event = Event.objects.create(
            name='Test Event',
            description='Test Description',
            capacity=100,
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=3),
            is_active=True
        )
    
    def test_create_hold_reservation_success(self):
        """API üzerinden başarılı HOLD rezervasyon oluşturmayı test eder."""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(
            f'{self.reservations_url}create_hold/',
            {'event_id': self.event.id, 'quantity': 5},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'HOLD')
        self.assertEqual(response.data['quantity'], 5)
        self.assertIsNotNone(response.data['expires_at'])
    
    def test_create_hold_reservation_insufficient_capacity(self):
        """Kapasite dolu olduğunda HOLD rezervasyon oluşturmayı test eder."""
        # Kapasiteyi doldur
        Reservation.objects.create(
            event=self.event,
            user=self.user,
            status=Reservation.Status.CONFIRMED,
            quantity=100
        )
        
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(
            f'{self.reservations_url}create_hold/',
            {'event_id': self.event.id, 'quantity': 1},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_create_hold_reservation_inactive_event(self):
        """Test creating HOLD reservation for inactive event."""
        self.event.is_active = False
        self.event.save()
        
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(
            f'{self.reservations_url}create_hold/',
            {'event_id': self.event.id, 'quantity': 5},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('not active', str(response.data))
    
    def test_confirm_reservation_success(self):
        """API üzerinden başarılı rezervasyon onaylamayı test eder."""
        reservation = Reservation.objects.create(
            event=self.event,
            user=self.user,
            status=Reservation.Status.HOLD,
            quantity=5,
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(
            f'{self.reservations_url}confirm/',
            {'reservation_id': reservation.id},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'CONFIRMED')
        self.assertIsNone(response.data['expires_at'])
    
    def test_confirm_reservation_wrong_user(self):
        """Test confirming reservation belonging to another user."""
        reservation = Reservation.objects.create(
            event=self.event,
            user=self.user,
            status=Reservation.Status.HOLD,
            quantity=5,
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        self.client.force_authenticate(user=self.other_user)
        
        response = self.client.post(
            f'{self.reservations_url}confirm/',
            {'reservation_id': reservation.id},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_cancel_reservation_success(self):
        """API üzerinden başarılı rezervasyon iptalini test eder."""
        reservation = Reservation.objects.create(
            event=self.event,
            user=self.user,
            status=Reservation.Status.HOLD,
            quantity=5,
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(
            f'{self.reservations_url}{reservation.id}/cancel/',
            {},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'CANCELLED')
    
    def test_list_user_reservations(self):
        """Sadece kullanıcının kendi rezervasyonlarını listelemesini test eder."""
        # Her iki kullanıcı için rezervasyon oluştur
        Reservation.objects.create(
            event=self.event,
            user=self.user,
            status=Reservation.Status.HOLD,
            quantity=5
        )
        Reservation.objects.create(
            event=self.event,
            user=self.other_user,
            status=Reservation.Status.HOLD,
            quantity=3
        )
        
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.reservations_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['user'], self.user.id)


class ConcurrencyTestCase(TransactionTestCase):
    """
    Eşzamanlılık kontrolü ve race condition testleri.
    select_for_update()'in çift rezervasyonu önlediğini doğrular.
    
    Not: Thread'ler veritabanı transaction'larını paylaşamadığı için
    TransactionTestCase kullanılır (TestCase yerine)
    çünkü thread'ler diğer thread'lerin veritabanı değişikliklerini görmelidir.
    Normal TestCase, thread'ler arasında görünür olmayan transaction'lar kullanır.
    """
    
    def setUp(self):
        """Test verilerini hazırlar."""
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        
        self.event = Event.objects.create(
            name='Concurrency Test Event',
            description='Test',
            capacity=10,  # Test için küçük kapasite
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=3),
            is_active=True
        )
    
    def test_concurrent_hold_reservations(self):
        """
        Eşzamanlı HOLD rezervasyonların kapasiteyi aşmadığını test eder.
        Aynı anda rezervasyon yapmaya çalışan birden fazla kullanıcıyı simüle eder.
        """
        from django.db import connections
        
        results = []
        errors = []
        lock = threading.Lock()
        
        def create_reservation(user_id, quantity):
            """Thread içinde rezervasyon oluşturmak için yardımcı fonksiyon."""
            try:
                # En son veriyi almak için etkinliği veritabanından yenile
                event = Event.objects.get(id=self.event.id)
                reservation = ReservationService.create_hold_reservation(
                    event_id=event.id,
                    user_id=user_id,
                    quantity=quantity
                )
                with lock:
                    results.append(reservation)
            except (ValidationError, Event.DoesNotExist) as e:
                with lock:
                    errors.append(str(e))
            except Exception as e:
                with lock:
                    errors.append(f"Unexpected error: {str(e)}")
            finally:
                # Bu thread'deki veritabanı bağlantılarını kapat
                # Bu, "database is being accessed by other users" hatasını önler
                connections.close_all()
        
        # Her biri 5'er rezervasyon yapmaya çalışan 3 eşzamanlı isteği simüle et
        # (toplam 15, ancak kapasite 10)
        threads = []
        for i, user in enumerate([self.user1, self.user2, self.user1]):
            thread = threading.Thread(
                target=create_reservation,
                args=(user.id, 5)
            )
            threads.append(thread)
            thread.start()
        
        # Tüm thread'lerin tamamlanmasını bekle
        for thread in threads:
            thread.join()
        
        # Thread'ler tamamlandıktan sonra tüm bağlantıları kapat
        connections.close_all()
        
        # En son veriyi almak için etkinliği yenile
        self.event.refresh_from_db()
        
        # Toplam rezerve edilen miktarın kapasiteyi aşmadığını doğrula
        total_hold_quantity = sum(r.quantity for r in results)
        total_confirmed_quantity = self.event.get_confirmed_count()
        total_reserved = total_hold_quantity + total_confirmed_quantity
        
        # En az bir istek yetersiz kapasite nedeniyle başarısız olmalı
        # VEYA tüm istekler başarılı oldu ancak toplam kapasiteyi aşmıyor
        self.assertLessEqual(total_reserved, 10, 
                            f"Total reserved ({total_reserved}) exceeds capacity (10). "
                            f"Results: {len(results)}, Errors: {len(errors)}")
        
        # Eğer tüm istekler başarılı olduysa, kapasiteyi aşmadıklarını doğrula
        # (Bu, kilitleme nedeniyle isteklerin sırayla işlenmesi durumunda olabilir)
        if len(errors) == 0:
            self.assertLessEqual(total_reserved, 10, 
                                "All requests succeeded but total exceeds capacity")
