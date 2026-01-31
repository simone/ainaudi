"""
Views for core authentication and user management.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from .models import IdentityProviderLink, RoleAssignment
from .serializers import (
    UserSerializer,
    UserProfileSerializer,
    RoleAssignmentSerializer,
    GoogleLoginSerializer,
    MagicLinkRequestSerializer,
    MagicLinkVerifySerializer,
)

User = get_user_model()
signer = TimestampSigner()


def get_tokens_for_user(user):
    """Generate JWT tokens for a user."""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class GoogleLoginView(APIView):
    """
    Authenticate user with Google OAuth2 ID token.

    POST /api/auth/google/
    {
        "id_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6..."
    }
    """
    permission_classes = [AllowAny]
    serializer_class = GoogleLoginSerializer

    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['id_token']

        try:
            # Verify the Google ID token
            idinfo = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                settings.SOCIALACCOUNT_PROVIDERS['google']['APP']['client_id']
            )

            # Extract user info
            google_uid = idinfo['sub']
            email = idinfo.get('email')
            email_verified = idinfo.get('email_verified', False)

            if not email or not email_verified:
                return Response(
                    {'error': 'Email non verificata'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Find or create user
            user = None

            # Check if we have an existing link
            try:
                link = IdentityProviderLink.objects.get(
                    provider=IdentityProviderLink.Provider.GOOGLE,
                    provider_uid=google_uid
                )
                user = link.user
                link.last_used_at = timezone.now()
                link.save(update_fields=['last_used_at'])
            except IdentityProviderLink.DoesNotExist:
                # Check if user exists by email
                try:
                    user = User.objects.get(email=email)
                except User.DoesNotExist:
                    # Create new user
                    user = User.objects.create_user(
                        email=email,
                        display_name=idinfo.get('name', ''),
                        first_name=idinfo.get('given_name', ''),
                        last_name=idinfo.get('family_name', ''),
                        avatar_url=idinfo.get('picture'),
                    )

                # Create identity provider link
                IdentityProviderLink.objects.create(
                    user=user,
                    provider=IdentityProviderLink.Provider.GOOGLE,
                    provider_uid=google_uid,
                    provider_email=email,
                    is_primary=not user.identity_links.exists(),
                    last_used_at=timezone.now(),
                )

            # Update last login
            user.last_login = timezone.now()
            user.last_login_ip = self.get_client_ip(request)
            user.save(update_fields=['last_login', 'last_login_ip'])

            # Generate JWT tokens
            tokens = get_tokens_for_user(user)

            return Response({
                'user': UserSerializer(user).data,
                **tokens,
            })

        except ValueError as e:
            return Response(
                {'error': f'Token non valido: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    def get_client_ip(self, request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class MagicLinkRequestView(APIView):
    """
    Request a magic link to be sent to email.

    POST /api/auth/magic-link/request/
    {
        "email": "user@example.com"
    }
    """
    permission_classes = [AllowAny]
    serializer_class = MagicLinkRequestSerializer

    def post(self, request):
        if not settings.FEATURE_FLAGS.get('MAGIC_LINK', True):
            return Response(
                {'error': 'Magic Link non abilitato'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = MagicLinkRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email'].lower()

        # Generate signed token
        token = signer.sign(email)

        # Build magic link URL
        magic_link = f"{settings.FRONTEND_URL}/auth/magic-link?token={token}"

        # Send email
        try:
            send_mail(
                subject='Accesso RDL Referendum',
                message=f'''
Ciao,

Clicca sul seguente link per accedere a RDL Referendum:

{magic_link}

Il link è valido per {settings.MAGIC_LINK_TOKEN_EXPIRY // 60} minuti.

Se non hai richiesto questo link, ignora questa email.

Movimento 5 Stelle
                '''.strip(),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception as e:
            return Response(
                {'error': f'Errore invio email: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            'message': 'Email inviata. Controlla la tua casella di posta.',
        })


class MagicLinkVerifyView(APIView):
    """
    Verify a magic link token and authenticate user.

    POST /api/auth/magic-link/verify/
    {
        "token": "email:timestamp:signature"
    }
    """
    permission_classes = [AllowAny]
    serializer_class = MagicLinkVerifySerializer

    def post(self, request):
        if not settings.FEATURE_FLAGS.get('MAGIC_LINK', True):
            return Response(
                {'error': 'Magic Link non abilitato'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = MagicLinkVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']

        try:
            # Verify token signature and expiry
            email = signer.unsign(
                token,
                max_age=settings.MAGIC_LINK_TOKEN_EXPIRY
            )
        except SignatureExpired:
            return Response(
                {'error': 'Link scaduto. Richiedine uno nuovo.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except BadSignature:
            return Response(
                {'error': 'Link non valido.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find or create user
        user, created = User.objects.get_or_create(
            email=email,
            defaults={'display_name': email.split('@')[0]}
        )

        # Create/update identity provider link
        link, _ = IdentityProviderLink.objects.update_or_create(
            user=user,
            provider=IdentityProviderLink.Provider.MAGIC_LINK,
            defaults={
                'provider_uid': email,
                'provider_email': email,
                'last_used_at': timezone.now(),
            }
        )

        # Update last login
        user.last_login = timezone.now()
        user.last_login_ip = self.get_client_ip(request)
        user.save(update_fields=['last_login', 'last_login_ip'])

        # Generate JWT tokens
        tokens = get_tokens_for_user(user)

        return Response({
            'user': UserSerializer(user).data,
            'created': created,
            **tokens,
        })

    def get_client_ip(self, request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Get or update the current user's profile.

    GET /api/auth/profile/
    PUT/PATCH /api/auth/profile/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return UserSerializer
        return UserProfileSerializer


class UserRolesView(generics.ListAPIView):
    """
    Get the current user's role assignments.

    GET /api/auth/roles/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = RoleAssignmentSerializer

    def get_queryset(self):
        return RoleAssignment.objects.filter(
            user=self.request.user,
            is_active=True
        ).select_related('scope_regione', 'scope_provincia', 'scope_comune')
