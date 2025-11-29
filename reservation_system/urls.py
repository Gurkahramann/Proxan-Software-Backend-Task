"""
Rezervasyon sistemi URL yapılandırması.
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),
    
    # JWT Token endpoint'leri
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # API endpoint'leri
    path('api/auth/', include('users.urls')),  # Kullanıcı kimlik doğrulama
    path('api/', include('events.urls')),  # Etkinlik ve rezervasyon
]
