from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

from .models import User
from .serializers import UserSerializer, UserRegistrationSerializer


class UserViewSet(viewsets.ModelViewSet):
    """
    User ViewSet for registration and authentication.
    This is equivalent to Spring's @RestController.
    
    Views are thin - they only handle request parsing and return responses.
    Business logic (if needed) would go in a Service layer.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]  # Allow registration/login without auth

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        """
        User registration endpoint.
        POST /api/auth/users/register/
        
        This is like Spring's @PostMapping("/register").
        Note: Registration does NOT return tokens. User must login separately.
        """
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Only return user data, no tokens
            return Response({
                'user': UserSerializer(user).data,
                'message': 'User registered successfully. Please login to get access token.'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def login(self, request):
        """
        User login endpoint (JWT token generation).
        POST /api/auth/users/login/
        
        This is like Spring's @PostMapping("/login").
        """
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                {'error': 'Username and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = authenticate(username=username, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_200_OK)
        
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        """
        User logout endpoint.
        POST /api/auth/users/logout/
        
        Blacklists the refresh token, making it unusable.
        This is like Spring Security's logout that invalidates the token.
        """
        try:
            # Get the refresh token from request body
            refresh_token = request.data.get('refresh')
            
            if not refresh_token:
                return Response(
                    {'error': 'Refresh token is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get the token object
            token = RefreshToken(refresh_token)
            
            # Blacklist the refresh token
            # This adds it to the database blacklist table
            token.blacklist()
            
            return Response(
                {'message': 'Successfully logged out. Token has been blacklisted.'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': f'Invalid token or already blacklisted: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

