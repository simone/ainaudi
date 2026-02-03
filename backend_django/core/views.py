"""
Views for core authentication and user management.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from .models import RoleAssignment
from .serializers import (
    UserSerializer,
    UserProfileSerializer,
    RoleAssignmentSerializer,
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
        magic_link = f"{settings.FRONTEND_URL}/?token={token}"

        # Send email
        try:
            send_mail(
                subject='Accesso RDL 5 Stelle',
                message=f'''
Ciao,

Clicca sul seguente link per accedere a RDL 5 Stelle:

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


class ImpersonateView(APIView):
    """
    Impersonate another user (superuser only).

    POST /api/auth/impersonate/
    {
        "email": "user@example.com"
    }

    Returns JWT tokens for the specified user.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo i superuser possono usare l\'impersonation'},
                status=status.HTTP_403_FORBIDDEN
            )

        email = request.data.get('email')
        if not email:
            return Response(
                {'error': 'Email obbligatoria'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            target_user = User.objects.get(email=email.lower())
        except User.DoesNotExist:
            return Response(
                {'error': f'Utente {email} non trovato'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Generate JWT tokens for the target user
        tokens = get_tokens_for_user(target_user)

        return Response({
            'user': UserSerializer(target_user).data,
            'impersonated_by': request.user.email,
            **tokens,
        })


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


class SearchUsersView(APIView):
    """
    Search users by email (for impersonation and autocomplete).

    GET /api/auth/users/search/?q=searchterm

    Returns list of matching user emails.
    Only available to superusers.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo i superuser possono cercare utenti'},
                status=status.HTTP_403_FORBIDDEN
            )

        query = request.query_params.get('q', '').strip()
        if len(query) < 2:
            return Response({'emails': []})

        users = User.objects.filter(
            email__icontains=query
        ).values_list('email', flat=True)[:20]

        return Response({'emails': list(users)})


class PermissionsView(APIView):
    """
    Get the current user's permissions for the frontend.

    GET /api/permissions
    GET /api/permissions?consultazione=1

    I permessi derivano dalla CATENA DELLE DELEGHE, non da ruoli assegnati:
    - Delegato di Lista → può creare sub-deleghe, designare RDL, vedere KPI
    - Sub-Delegato → può designare RDL, vedere KPI
    - RDL → può inserire dati sezione

    Returns:
    {
        "sections": true/false,    # Can enter section data (RDL)
        "referenti": true/false,   # Can assign RDL (DELEGATE, SUBDELEGATE)
        "kpi": true/false,         # Can view KPI dashboard
        "is_delegato": true/false,
        "is_sub_delegato": true/false,
        "is_rdl": true/false
    }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from delegations.models import DelegatoDiLista, SubDelega, DesignazioneRDL

        user = request.user
        consultazione_id = request.query_params.get('consultazione')

        # Superuser has all permissions
        if user.is_superuser:
            return Response({
                'sections': True,
                'referenti': True,
                'kpi': True,
                'upload_sezioni': True,
                'gestione_rdl': True,
                'is_delegato': True,
                'is_sub_delegato': True,
                'is_rdl': True,
            })

        # Check delegation chain for permissions
        # 1. Is user a Delegato di Lista?
        deleghe_lista = DelegatoDiLista.objects.filter(user=user)
        if consultazione_id:
            deleghe_lista = deleghe_lista.filter(consultazione_id=consultazione_id)
        is_delegato = deleghe_lista.exists()

        # 2. Is user a Sub-Delegato?
        sub_deleghe = SubDelega.objects.filter(user=user, is_attiva=True)
        if consultazione_id:
            sub_deleghe = sub_deleghe.filter(delegato__consultazione_id=consultazione_id)
        is_sub_delegato = sub_deleghe.exists()

        # 3. Is user an RDL?
        designazioni = DesignazioneRDL.objects.filter(user=user, is_attiva=True)
        if consultazione_id:
            designazioni = designazioni.filter(
                Q(delegato__consultazione_id=consultazione_id) |
                Q(sub_delega__delegato__consultazione_id=consultazione_id)
            )
        is_rdl = designazioni.exists()

        # Also check for explicit role assignments (backwards compatibility + KPI_VIEWER)
        roles = RoleAssignment.objects.filter(
            user=user,
            is_active=True
        ).values_list('role', flat=True)
        roles_set = set(roles)

        # ADMIN role has all permissions
        if 'ADMIN' in roles_set:
            return Response({
                'sections': True,
                'referenti': True,
                'kpi': True,
                'upload_sezioni': True,
                'gestione_rdl': True,
                'is_delegato': is_delegato,
                'is_sub_delegato': is_sub_delegato,
                'is_rdl': is_rdl,
            })

        # Calculate permissions based on delegation chain
        permissions = {
            # Delegato e Sub-Delegato possono gestire referenti (designare RDL)
            'referenti': is_delegato or is_sub_delegato,

            # RDL può inserire dati sezione, ma anche delegato/sub-delegato
            'sections': is_rdl or is_delegato or is_sub_delegato,

            # KPI visibile a delegato, sub-delegato, o chi ha ruolo KPI_VIEWER
            'kpi': is_delegato or is_sub_delegato or ('KPI_VIEWER' in roles_set),

            # Solo delegato può caricare sezioni
            'upload_sezioni': is_delegato,

            # Delegato e Sub-Delegato possono gestire registrazioni RDL
            'gestione_rdl': is_delegato or is_sub_delegato,

            # Info sulla posizione nella catena
            'is_delegato': is_delegato,
            'is_sub_delegato': is_sub_delegato,
            'is_rdl': is_rdl,
        }

        return Response(permissions)
