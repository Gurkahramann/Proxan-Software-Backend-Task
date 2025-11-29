# Reservation System - Django REST Framework API

Django REST Framework (DRF) ile geliştirilmiş, JWT kimlik doğrulama, eşzamanlı rezervasyon yönetimi ve Celery ile Redis kullanarak arka plan iş işleme özelliklerine sahip bir rezervasyon sistemi.

## Mimari

Bu proje **Service Layer Pattern**  kullanır:

- **Models (Entities)**: `models.py` içindeki veri modelleri
- **Services (Service Layer)**: `services.py` içindeki iş mantığı 
- **Views (Controllers)**: `views.py` içindeki controllerlar 
- **Serializers (DTOs)**: Veri doğrulama ve dönüştürme (DTO)

## Docker ile Hızlı Başlangıç (Önerilen)

### Gereksinimler

- Docker ve Docker Compose kurulu
- Git

### Kurulum Adımları

1. **Repository'yi klonlayın**
   ```bash
   git clone <repository-url>
   cd Proxan-Software-Backend-Task
   ```

2. **Ortam değişkenleri dosyasını oluşturun**
   Size gönderdiğim .env dosyasını proje klasörüne ekleyin.

3. **Tüm servisleri oluşturun ve başlatın**
   
   
   Önce container'ları başlatın:
   ```bash
   docker-compose up --build 
   ```
   Container'ların başladığını kontrol edin:
   ```bash
   docker-compose ps
   ```
   
   Tüm servislerin "Up" durumunda olduğunu görmelisiniz. Sonra migration'ları çalıştırın:
   ```bash
   docker-compose exec web python manage.py migrate
   docker-compose exec web python manage.py setup_periodic_tasks
   ```
   
   > **Önemli**: Eğer "service 'web' is not running" hatası alırsanız, önce `docker-compose up -d` komutu ile container'ları başlatmanız gerekir.

   Bu şunları başlatacak:
   - **Django API** (http://localhost:8000)
   - **PostgreSQL** veritabanı
   - **Redis** (Celery için)
   - **Celery Worker** (arka plan görevleri)
   - **Celery Beat** (periyodik görevler)

4. **Superuser oluşturun (yeni bir terminalde)**
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

## Manuel Kurulum (Docker Olmadan)

### Gereksinimler

- Python 3.10+
- PostgreSQL 12+
- Redis 6+
- Virtual environment (önerilir)

### Kurulum Adımları

1. **Repository'yi klonlayın**
   ```bash
   git clone <repository-url>
   cd Proxan-Software-Backend-Task
   ```

2. **Virtual environment oluşturun ve aktif edin**
   ```bash
   python -m venv venv
   # Windows'ta:
   venv\Scripts\activate

3. **Bağımlılıkları yükleyin**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ortam değişkenlerini yapılandırın**
   
    size gönderdiğim .env dosyasını proje klasörüne yapıştırın

5. **PostgreSQL veritabanını oluşturun**
   ```sql
   CREATE DATABASE reservation_system;
   ```

6. **Migration'ları oluşturun ve uygulayın**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
> **Not**: Admin görevleri için gerekli!
7. **Superuser oluşturun**
   ```bash
   python manage.py createsuperuser 
   ```

8. **Periyodik görevleri kurun**
   ```bash
   python manage.py setup_periodic_tasks
   ```

9. **Redis'i başlatın** (Docker ile - ayrı bir terminalde)
   ```bash
   docker run -d -p 6379:6379 --name redis redis:7-alpine
   ```
   
   > **Not**: Eğer yerel Redis kuruluysa, `redis-server` komutu ile de başlatabilirsiniz.

10. **Celery Worker'ı başlatın** (ayrı bir terminalde)
    ```bash
    # Windows'ta:
    celery -A reservation_system worker -l info --pool=solo
    ```

11. **Celery Beat'i başlatın** (ayrı bir terminalde)
    ```bash
    celery -A reservation_system beat -l info
    ```

12. **Django sunucusunu başlatın**
    ```bash
    python manage.py runserver
    ```

Artık API'ye http://localhost:8000 adresinden erişebilirsiniz.

## Testleri Çalıştırma

### Docker ile
```bash
docker-compose exec web python manage.py test
```

### Docker Olmadan
```bash
python manage.py test
```

### Belirli test paketlerini çalıştırma
```bash
# Sadece kullanıcı testleri
python manage.py test users.tests

# Sadece etkinlik testleri
python manage.py test events.tests

```

## API Dokümantasyonu

> **Not**: Detaylı API testleri için Postman Collection dosyasını (`Proxan_Software.postman_collection.json`) kullanabilirsiniz.

### Kimlik Doğrulama Endpoint'leri

#### 1. Kullanıcı Kaydı
Yeni kullanıcı hesabı oluşturur. Kayıt sonrası token döndürmez, kullanıcı ayrıca giriş yapmalıdır.

```http
POST /api/auth/users/register/
Content-Type: application/json

{
  "username": "testuser",
  "email": "test@example.com",
  "password": "securepass123",
  "password2": "securepass123",
  "first_name": "Test",
  "last_name": "User"
}
```

#### 2. Kullanıcı Girişi
Kullanıcı girişi yapar ve JWT access/refresh token'ları döndürür.

```http
POST /api/auth/users/login/
Content-Type: application/json

{
  "username": "testuser",
  "password": "securepass123"
}
```

**Response**: `access` ve `refresh` token'ları döner.

#### 3. Token Yenileme
Access token'ı yenilemek için refresh token kullanılır.

```http
POST /api/token/refresh/
Content-Type: application/json

{
  "refresh": "eyJhbGci..."
}
```

**Response**: Yeni `access` token döner.

#### 4. Çıkış (Logout)
Kullanıcı çıkış yapar. Refresh token'ı kara listeye ekler.

```http
POST /api/auth/users/logout/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "refresh": "eyJhbGci..."
}
```

### Etkinlik Endpoint'leri

#### Etkinlikleri Listele
Tüm etkinlikleri sayfalanmış liste olarak döndürür. Filtreleme yapılabilir.

```http
GET /api/events/
Authorization: Bearer {access_token}
```

**Query Parametreleri**:
- `?is_active=true` - Sadece aktif etkinlikleri getir
- `?start_date=2024-01-01` - Başlangıç tarihine göre filtrele
- `?end_date=2024-12-31` - Bitiş tarihine göre filtrele

**Response**: Her etkinlik için `available_capacity`, `hold_count`, `confirmed_count` bilgileri dahil.

#### Etkinlik Detaylarını Getir
Belirli bir etkinliğin detaylı bilgilerini döndürür.

```http
GET /api/events/{id}/
Authorization: Bearer {access_token}
```

**Response**: Etkinlik detayları, kalan kapasite, HOLD ve CONFIRMED rezervasyon sayıları.

#### Etkinlik Oluştur
Yeni etkinlik oluşturur. **Sadece superuser (admin) yetkisi gerektirir.**

```http
POST /api/events/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "Concert 2025",
  "description": "Annual concert event",
  "capacity": 100,
  "start_time": "2025-12-31T20:00:00Z",
  "end_time": "2025-12-31T23:00:00Z",
  "is_active": true
}
```

#### Etkinlik Güncelle
Mevcut etkinliği günceller. **Sadece superuser (admin) yetkisi gerektirir.**

```http
PUT /api/events/{id}/     # Tüm alanları güncelle
PATCH /api/events/{id}/   # Sadece belirtilen alanları güncelle
Authorization: Bearer {access_token}
Content-Type: application/json
```

#### Etkinlik Sil
Etkinliği siler. **Sadece superuser (admin) yetkisi gerektirir.**

```http
DELETE /api/events/{id}/
Authorization: Bearer {access_token}
```

**Response**: `{"message": "Event deleted successfully."}`

### Rezervasyon Endpoint'leri

#### Kullanıcının Rezervasyonlarını Listele
Giriş yapmış kullanıcının tüm rezervasyonlarını listeler.

```http
GET /api/reservations/
Authorization: Bearer {access_token}
```

#### HOLD Rezervasyon Oluştur
Bir etkinlik için geçici (HOLD) rezervasyon oluşturur.

```http
POST /api/reservations/create_hold/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "event_id": 1,
  "quantity": 2
}
```

**Önemli**: HOLD rezervasyonlar **5 dakika** içinde onaylanmazsa otomatik olarak süresi doluyor. Kapasite kontrolü yapılır.

#### Rezervasyon Onayla
HOLD durumundaki rezervasyonu CONFIRMED (onaylı) durumuna alır.

```http
POST /api/reservations/confirm/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "reservation_id": 1
}
```

**Not**: Sadece kendi rezervasyonunuzu onaylayabilirsiniz. Süresi dolmuş rezervasyonlar onaylanamaz.

#### Rezervasyon İptal Et
Bir rezervasyonu iptal eder (CANCELLED durumuna alır).

```http
POST /api/reservations/{id}/cancel/
Authorization: Bearer {access_token}
```

**Not**: Sadece kendi rezervasyonunuzu iptal edebilirsiniz. İptal edilen rezervasyonlar kapasiteyi serbest bırakır.

## Güvenlik Özellikleri

### JWT Kimlik Doğrulama
- **Access Token**: 1 saat ömür
- **Refresh Token**: 7 gün ömür
- **Token Blacklist**: Çıkışta refresh token'lar kara listeye alınır

### Refresh Token Kara Listesi
- Refresh token'lar veritabanında saklanır (`OutstandingToken`)
- Kara listedeki token'lar yenileme için kullanılamaz
- Tek cihazdan veya tüm cihazlardan çıkışı destekler

## Temel Özellikler

### 1. Eşzamanlılık Kontrolü
- **Pessimistic Locking**: Race condition'ları önlemek için `select_for_update()` kullanır
  - **Konum**: `events/services.py` - `create_hold_reservation()` ve `confirm_reservation()` metodlarında
- **Transaction Güvenliği**: Tüm rezervasyon işlemleri `@transaction.atomic` kullanır
  - **Konum**: `events/services.py` - Tüm rezervasyon metodlarında
- **Kapasite Doğrulama**: Dinamik kapasite hesaplama (Kapasite - Aktif HOLD'lar - Onaylanmış)
  - **Konum**: `events/models.py` - `Event.get_available_capacity()` metodu

### 2. İki Aşamalı Rezervasyon
- **HOLD**: Geçici rezervasyon (5 dakika süre dolma)
  - **Konum**: `events/models.py` - `Reservation.Status.HOLD`
  - **Oluşturma**: `events/services.py` - `create_hold_reservation()`
- **CONFIRMED**: Kalıcı rezervasyon
  - **Konum**: `events/models.py` - `Reservation.Status.CONFIRMED`
  - **Onaylama**: `events/services.py` - `confirm_reservation()`
- **CANCELLED**: Kullanıcı tarafından iptal edilmiş rezervasyon
  - **Konum**: `events/models.py` - `Reservation.Status.CANCELLED`
  - **İptal**: `events/services.py` - `cancel_reservation()`
- **EXPIRED**: Otomatik süresi dolmuş HOLD rezervasyon
  - **Konum**: `events/models.py` - `Reservation.Status.EXPIRED`
  - **Süre Dolma**: `events/services.py` - `expire_old_holds()` ve `events/tasks.py` - `expire_old_hold_reservations()`

### 3. Arka Plan İşleri
- **Celery**: Asenkron görevleri işler
  - **Konum**: `events/tasks.py` - `expire_old_hold_reservations` görevi
  - **Yapılandırma**: `reservation_system/celery.py` ve `reservation_system/settings.py`
- **Redis**: Mesaj broker'ı ve sonuç backend'i
  - **Yapılandırma**: `reservation_system/settings.py` - `CELERY_BROKER_URL` ve `CELERY_RESULT_BACKEND`
- **Periyodik Görevler**: Her dakika HOLD rezervasyonlarını otomatik olarak süresi dolmuş olarak işaretler
  - **Kurulum**: `events/management/commands/setup_periodic_tasks.py`
  - **Çalıştırma**: `python manage.py setup_periodic_tasks`
- **Celery Beat**: Periyodik görevler için zamanlayıcı
  - **Yapılandırma**: `reservation_system/settings.py` - `CELERY_BEAT_SCHEDULER`

### 4. Service Layer Pattern
- Tüm iş mantığı `services.py` içinde
  - **Konum**: `events/services.py` - `ReservationService` sınıfı
- View'lar incedir (sadece istek/yanıt işleme)
  - **Konum**: `events/views.py` - `EventViewSet` ve `ReservationViewSet`

## Proje Yapısı ve Dosya Açıklamaları

###  `core/` - Paylaşılan Bileşenler
Ortak kullanılan modeller ve istisnalar.

- **`models.py`**: 
  - `BaseModel`: Tüm modeller için ortak `created_at` ve `updated_at` alanlarını sağlayan soyut model
- **`exceptions.py`**: 
  - `InsufficientCapacityError`: Yetersiz kapasite hatası (HTTP 409)
  - `ReservationExpiredError`: Süresi dolmuş rezervasyon hatası (HTTP 400)
- **`admin.py`**: Django Admin yapılandırması
- **`apps.py`**: Uygulama yapılandırması

###  `users/` - Kullanıcı Yönetimi
Kullanıcı kimlik doğrulama ve yetkilendirme.

- **`models.py`**: 
  - `User`: Django'nun `AbstractUser`'ını genişleten özel kullanıcı modeli (email unique, created_at, updated_at)
- **`serializers.py`**: 
  - `UserSerializer`: Kullanıcı bilgilerini serialize eder
  - `UserRegistrationSerializer`: Kayıt işlemi için doğrulama yapar
- **`views.py`**: 
  - `UserViewSet`: Kullanıcı kayıt (`register`), giriş (`login`), çıkış (`logout`) endpoint'leri
- **`urls.py`**: Kullanıcı endpoint'lerinin URL routing'i (`/api/auth/users/`)
- **`admin.py`**: Django Admin'de User modeli yönetimi
- **`tests.py`**: Kullanıcı kayıt, giriş, çıkış ve token kara listesi testleri

###  `events/` - Etkinlik ve Rezervasyon Yönetimi
Projenin ana iş mantığı burada.

- **`models.py`**: 
  - `Event`: Etkinlik modeli (name, description, capacity, start_time, end_time, is_active)
    - `get_available_capacity()`: Kalan kapasiteyi hesaplar
    - `get_hold_count()`: Aktif HOLD rezervasyon sayısını döndürür
    - `get_confirmed_count()`: Onaylanmış rezervasyon sayısını döndürür
  - `Reservation`: Rezervasyon modeli (event, user, status, quantity, expires_at)
    - `Status`: HOLD, CONFIRMED, CANCELLED, EXPIRED durumları
- **`services.py`**: 
  - `ReservationService`: Tüm rezervasyon iş mantığı
    - `create_hold_reservation()`: HOLD rezervasyon oluşturur (transaction + lock)
    - `confirm_reservation()`: HOLD'u CONFIRMED'e çevirir (transaction + lock)
    - `cancel_reservation()`: Rezervasyonu iptal eder
    - `expire_old_holds()`: Süresi dolmuş HOLD'ları EXPIRED yapar
- **`views.py`**: 
  - `EventViewSet`: Etkinlik CRUD işlemleri (list, retrieve, create, update, delete)
    - `create/update/delete`: Sadece superuser yetkisi
  - `ReservationViewSet`: Rezervasyon işlemleri (list, create_hold, confirm, cancel)
- **`serializers.py`**: 
  - `EventSerializer`: Etkinlik serialize (available_capacity, hold_count, confirmed_count dahil)
  - `ReservationSerializer`: Rezervasyon serialize
  - `CreateReservationSerializer`: HOLD rezervasyon oluşturma için doğrulama
  - `ConfirmReservationSerializer`: Rezervasyon onaylama için doğrulama
- **`tasks.py`**: 
  - `expire_old_hold_reservations`: Celery görevi - süresi dolmuş HOLD'ları işaretler
- **`management/commands/`**: 
  - `expire_holds.py`: Manuel olarak süresi dolmuş HOLD'ları işaretleme komutu
  - `setup_periodic_tasks.py`: Celery Beat periyodik görevlerini kurma komutu
- **`urls.py`**: Etkinlik ve rezervasyon endpoint'lerinin URL routing'i (`/api/events/`, `/api/reservations/`)
- **`admin.py`**: Django Admin'de Event ve Reservation modelleri yönetimi
- **`tests.py`**: Etkinlik, rezervasyon, service layer ve eşzamanlılık testleri

###  `reservation_system/` - Django Proje Ayarları
Ana Django proje yapılandırması.

- **`settings.py`**: 
  - Django, DRF, JWT, Celery, veritabanı yapılandırmaları
  - `INSTALLED_APPS`: Yüklü uygulamalar listesi
  - `REST_FRAMEWORK`: DRF varsayılan ayarları (authentication, pagination)
  - `SIMPLE_JWT`: JWT token ayarları (lifetime, blacklist)
  - `CELERY_*`: Celery broker ve result backend ayarları
- **`urls.py`**: 
  - Ana URL routing (Django Admin, JWT token endpoint'leri, API endpoint'leri)
- **`celery.py`**: 
  - Celery uygulaması yapılandırması ve otomatik görev keşfi
- **`wsgi.py`**: 
  - WSGI yapılandırması (production deployment için)
- **`asgi.py`**: 
  - ASGI yapılandırması (async deployment için)
- **`__init__.py`**: 
  - Celery uygulamasını Django başlangıcında yükler

## Veritabanı Şeması

### Modeller

- **`User`** (`users/models.py`): 
  - JWT kimlik doğrulama ile özel kullanıcı modeli
  - Alanlar: username, email (unique), password, first_name, last_name, created_at, updated_at
  - Django'nun `AbstractUser`'ını genişletir

- **`Event`** (`events/models.py`): 
  - Kapasite yönetimi ile etkinlik bilgileri
  - Alanlar: name, description, capacity, start_time, end_time, is_active, created_at, updated_at
  - Metodlar: `get_available_capacity()`, `get_hold_count()`, `get_confirmed_count()`

- **`Reservation`** (`events/models.py`): 
  - İki aşamalı rezervasyon sistemi (HOLD → CONFIRMED)
  - Alanlar: event (ForeignKey), user (ForeignKey), status (HOLD/CONFIRMED/CANCELLED/EXPIRED), quantity, expires_at, created_at, updated_at
  - Durumlar: HOLD (5 dakika geçici), CONFIRMED (kalıcı), CANCELLED (iptal), EXPIRED (süresi dolmuş)

### Token Kara Liste Tabloları (djangorestframework-simplejwt)

- **`OutstandingToken`**: 
  - Aktif refresh token'ları saklar
  - Her login'de yeni refresh token bu tabloya eklenir

- **`BlacklistedToken`**: 
  - Kara listedeki refresh token'ları saklar
  - Logout işleminde refresh token bu tabloya eklenir ve bir daha kullanılamaz

##  Test Etme

Proje kapsamlı unit testler içerir:

- **Kullanıcı Kimlik Doğrulama Testleri**: Kayıt, giriş, çıkış, token kara listesi
- **Etkinlik Testleri**: CRUD işlemleri, izinler, filtreleme
- **Rezervasyon Testleri**: Oluşturma, onaylama, iptal, süre dolma
- **Eşzamanlılık Testleri**: Race condition önleme
- **Service Layer Testleri**: İş mantığı doğrulama

Testleri çalıştırın:
```bash
python manage.py test
```

##  Proje Yapısı

```
reservation_system/
├── core/                 # Paylaşılan ayarlar, soyut modeller, istisnalar
├── users/                # Özel User modeli & Kimlik Doğrulama
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   └── tests.py
├── events/               # Etkinlik & Rezervasyon yönetimi
│   ├── models.py
│   ├── services.py       # İŞ MANTIĞI (Kritik)
│   ├── views.py
│   ├── serializers.py
│   ├── tasks.py          # Celery görevleri
│   ├── management/
│   │   └── commands/
│   │       ├── expire_holds.py
│   │       └── setup_periodic_tasks.py
│   └── tests.py
├── reservation_system/   # Django proje ayarları
│   ├── settings.py
│   ├── urls.py
│   └── celery.py
├── docker-compose.yml    # Docker orkestrasyonu
├── Dockerfile           # Django uygulama imajı
├── requirements.txt     # Python bağımlılıkları
└── README.md           # Bu dosya
```

##  Docker Servisleri

| Servis | Container Adı | Port | Açıklama |
|--------|---------------|------|----------|
| Django API | reservation_web | 8000 | Ana API sunucusu |
| PostgreSQL | reservation_db | 5432 | Veritabanı |
| Redis | reservation_redis | 6379 | Celery broker & cache |
| Celery Worker | reservation_celery_worker | - | Arka plan görev işlemcisi |
| Celery Beat | reservation_celery_beat | - | Periyodik görev zamanlayıcısı |

##  Geliştirme Notları

### Eşzamanlılık & Veri Tutarlılığı
- Tüm rezervasyon işlemleri `transaction.atomic()` kullanır
- `select_for_update()` çift rezervasyonu önler
- Kapasite transaction'lar içinde dinamik olarak hesaplanır

### Arka Plan İşleri
- HOLD rezervasyonlar 5 dakika sonra süresi doluyor
- Celery Beat her 1 dakikada bir süresi dolmuş HOLD'ları kontrol eder
- Sadece süresi dolmuş rezervasyonlar süresi dolmuş olarak işaretlenir

## Lisans

Bu proje bir case study uygulamasıdır.
Proxan Software için teknik bir case study olarak geliştirilmiştir.
