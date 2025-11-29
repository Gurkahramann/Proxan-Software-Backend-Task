from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from datetime import timedelta
from django.utils import timezone

User = get_user_model()


class UserModelTestCase(TestCase):
    """
    User modeli için unit testler.
    """
    
    def setUp(self):
        """Her test metodundan önce test verilerini hazırlar."""
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User'
        }
    
    def test_create_user(self):
        """Tüm alanlarla kullanıcı oluşturmayı test eder."""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('testpass123'))
        self.assertFalse(user.is_superuser)
        self.assertIsNotNone(user.created_at)
    
    def test_create_superuser(self):
        """Superuser oluşturmayı test eder."""
        user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
    
    def test_user_str_representation(self):
        """Kullanıcı string temsilini test eder."""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(str(user), 'testuser')


class UserRegistrationAPITestCase(APITestCase):
    """
    Kullanıcı kayıt endpoint'i için API testleri.
    """
    
    def setUp(self):
        """Test client ve base URL'i hazırlar."""
        self.client = APIClient()
        self.register_url = '/api/auth/users/register/'
        self.valid_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'securepass123',
            'password2': 'securepass123',
            'first_name': 'New',
            'last_name': 'User'
        }
    
    def test_register_user_success(self):
        """Başarılı kullanıcı kaydını test eder."""
        response = self.client.post(self.register_url, self.valid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['user']['username'], 'newuser')
        self.assertNotIn('refresh', response.data)  # No tokens on registration
        self.assertNotIn('access', response.data)  # No tokens on registration
        
        # Kullanıcının veritabanında oluşturulduğunu doğrula
        user = User.objects.get(username='newuser')
        self.assertEqual(user.email, 'newuser@example.com')
    
    def test_register_user_password_mismatch(self):
        """Eşleşmeyen şifrelerle kaydı test eder."""
        invalid_data = self.valid_data.copy()
        invalid_data['password2'] = 'differentpass'
        
        response = self.client.post(self.register_url, invalid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
    
    def test_register_user_duplicate_username(self):
        """Tekrarlanan kullanıcı adıyla kaydı test eder."""
        # İlk kullanıcıyı oluştur
        self.client.post(self.register_url, self.valid_data, format='json')
        
        # Tekrar oluşturmayı dene
        response = self.client.post(self.register_url, self.valid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)
    
    def test_register_user_weak_password(self):
        """Zayıf şifreyle kaydı test eder."""
        weak_data = self.valid_data.copy()
        weak_data['password'] = '123'  # Çok kısa
        weak_data['password2'] = '123'
        
        response = self.client.post(self.register_url, weak_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
    
    def test_register_user_missing_fields(self):
        """Eksik zorunlu alanlarla kaydı test eder."""
        incomplete_data = {
            'username': 'incomplete',
            # Email, password vb. eksik
        }
        
        response = self.client.post(self.register_url, incomplete_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserLoginAPITestCase(APITestCase):
    """
    Kullanıcı giriş endpoint'i için API testleri.
    """
    
    def setUp(self):
        """Test kullanıcısı ve client'ı hazırlar."""
        self.client = APIClient()
        self.login_url = '/api/auth/users/login/'
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_login_success(self):
        """Başarılı girişin token döndürmesini test eder."""
        response = self.client.post(
            self.login_url,
            {'username': 'testuser', 'password': 'testpass123'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'testuser')
    
    def test_login_invalid_credentials(self):
        """Geçersiz kimlik bilgileriyle girişi test eder."""
        response = self.client.post(
            self.login_url,
            {'username': 'testuser', 'password': 'wrongpass'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
        self.assertNotIn('access', response.data)
    
    def test_login_missing_username(self):
        """Kullanıcı adı olmadan girişi test eder."""
        response = self.client.post(
            self.login_url,
            {'password': 'testpass123'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_login_missing_password(self):
        """Şifre olmadan girişi test eder."""
        response = self.client.post(
            self.login_url,
            {'username': 'testuser'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)


class UserLogoutAPITestCase(APITestCase):
    """
    Çıkış endpoint'leri için API testleri.
    """
    
    def setUp(self):
        """Test kullanıcısı, token'ları ve client'ı hazırlar."""
        self.client = APIClient()
        self.logout_url = '/api/auth/users/logout/'
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Çıkış testi için token'ları oluştur
        self.refresh_token1 = RefreshToken.for_user(self.user)
        self.access_token1 = str(self.refresh_token1.access_token)
        self.refresh_token_str1 = str(self.refresh_token1)
    
    def test_logout_success(self):
        """Başarılı çıkışın refresh token'ı kara listeye eklemesini test eder."""
        # Kimlik doğrula
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')
        
        # Logout
        response = self.client.post(
            self.logout_url,
            {'refresh': self.refresh_token_str1},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # Token'ın kara listede olduğunu doğrula
        outstanding_token = OutstandingToken.objects.filter(
            user_id=self.user.id,
            jti=self.refresh_token1['jti']
        ).first()
        self.assertIsNotNone(outstanding_token)
        
        blacklisted = BlacklistedToken.objects.filter(token=outstanding_token).exists()
        self.assertTrue(blacklisted)
    
    def test_logout_without_refresh_token(self):
        """Refresh token olmadan çıkışı test eder."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')
        
        response = self.client.post(self.logout_url, {}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_logout_without_authentication(self):
        """Access token olmadan çıkışı test eder."""
        response = self.client.post(
            self.logout_url,
            {'refresh': self.refresh_token_str1},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_logout_invalid_token(self):
        """Geçersiz refresh token ile çıkışı test eder."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')
        
        response = self.client.post(
            self.logout_url,
            {'refresh': 'invalid.token.here'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_blacklisted_token_cannot_refresh(self):
        """Kara listedeki refresh token'ın yeni access token almak için kullanılamayacağını test eder."""
        # Çıkış yap (token'ı kara listeye ekle)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')
        self.client.post(
            self.logout_url,
            {'refresh': self.refresh_token_str1},
            format='json'
        )
        
        # Kara listedeki token ile yenilemeyi dene
        response = self.client.post(
            '/api/token/refresh/',
            {'refresh': self.refresh_token_str1},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
