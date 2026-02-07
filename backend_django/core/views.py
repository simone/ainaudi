"""
Views for core authentication and user management.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
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


@method_decorator(csrf_exempt, name='dispatch')
class MagicLinkRequestView(APIView):
    """
    Request a magic link to be sent to email.

    POST /api/auth/magic-link/request/
    {
        "email": "user@example.com"
    }
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # No authentication needed
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

        # Check if user exists
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'error': 'Email non registrata. Contatta il tuo delegato o sub-delegato per farti abilitare al sistema.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Generate signed token with user ID (not email)
        token = signer.sign(str(user.id))

        # Build magic link URL
        magic_link = f"{settings.FRONTEND_URL}/?token={token}"

        # Send email
        try:
            send_mail(
                subject='Accesso AInaudi',
                message=f'''
Ciao,

Clicca sul seguente link per accedere a AInaudi:

{magic_link}

Il link è valido per {settings.MAGIC_LINK_TOKEN_EXPIRY // 60} minuti.

Se non hai richiesto questo link, ignora questa email.

AInaudi - Gestione Elettorale
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


@method_decorator(csrf_exempt, name='dispatch')
class MagicLinkVerifyView(APIView):
    """
    Verify a magic link token and authenticate user.

    POST /api/auth/magic-link/verify/
    {
        "token": "email:timestamp:signature"
    }
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # No authentication needed
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
            user_id = signer.unsign(
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

        # Find user by ID
        try:
            user = User.objects.get(id=int(user_id))
        except (User.DoesNotExist, ValueError):
            return Response(
                {'error': 'Utente non trovato.'},
                status=status.HTTP_404_NOT_FOUND
            )

        created = False

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

    Ritorna permessi basati su django.contrib.auth.permissions assegnati
    automaticamente dai signals in base alla catena delle deleghe.

    Returns:
    {
        "is_superuser": true/false,
        "can_manage_territory": true/false,
        "can_view_kpi": true/false,
        "can_manage_elections": true/false,
        "can_manage_delegations": true/false,
        "can_manage_rdl": true/false,
        "has_scrutinio_access": true/false,
        "can_view_resources": true/false,
        "can_ask_to_ai_assistant": true/false,
        "can_generate_documents": true/false,
        "can_manage_incidents": true/false,

        # Backwards compatibility (deprecati)
        "sections": true/false,
        "referenti": true/false,
        "kpi": true/false,
        "upload_sezioni": true/false,
        "gestione_rdl": true/false,

        # Info sulla catena deleghe
        "is_delegato": true/false,
        "is_sub_delegato": true/false,
        "is_rdl": true/false,
    }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from delegations.models import Delegato, SubDelega, DesignazioneRDL

        user = request.user
        consultazione_id = request.query_params.get('consultazione')

        # Superuser has all permissions
        if user.is_superuser:
            return Response({
                'is_superuser': True,
                'can_manage_territory': True,
                'can_view_kpi': True,
                'can_manage_elections': True,
                'can_manage_delegations': True,
                'can_manage_rdl': True,
                'has_scrutinio_access': True,
                'can_view_resources': True,
                'can_ask_to_ai_assistant': True,
                'can_generate_documents': True,
                'can_manage_incidents': True,

                # Backwards compatibility
                'sections': True,
                'referenti': True,
                'kpi': True,
                'upload_sezioni': True,
                'gestione_rdl': True,

                # Catena deleghe
                'is_delegato': True,
                'is_sub_delegato': True,
                'is_rdl': True,
            })

        # Check delegation chain for info flags
        # 1. Is user a Delegato?
        deleghe_lista = Delegato.objects.filter(email=user.email)
        if consultazione_id:
            deleghe_lista = deleghe_lista.filter(consultazione_id=consultazione_id)
        is_delegato = deleghe_lista.exists()

        # 2. Is user a Sub-Delegato?
        sub_deleghe = SubDelega.objects.filter(email=user.email, is_attiva=True)
        if consultazione_id:
            sub_deleghe = sub_deleghe.filter(delegato__consultazione_id=consultazione_id)
        is_sub_delegato = sub_deleghe.exists()

        # 3. Is user an RDL?
        designazioni = DesignazioneRDL.objects.filter(
            Q(effettivo_email=user.email) | Q(supplente_email=user.email),
            is_attiva=True
        )
        if consultazione_id:
            designazioni = designazioni.filter(
                Q(delegato__consultazione_id=consultazione_id) |
                Q(sub_delega__delegato__consultazione_id=consultazione_id)
            )
        is_rdl = designazioni.exists()

        # Check Django permissions (assegnati automaticamente dai signals)
        permissions = {
            'is_superuser': False,
            'can_manage_territory': user.has_perm('core.can_manage_territory'),
            'can_view_kpi': user.has_perm('core.can_view_kpi'),
            'can_manage_elections': user.has_perm('core.can_manage_elections'),
            'can_manage_delegations': user.has_perm('core.can_manage_delegations'),
            'can_manage_rdl': user.has_perm('core.can_manage_rdl'),
            'has_scrutinio_access': user.has_perm('core.has_scrutinio_access'),
            'can_view_resources': user.has_perm('core.can_view_resources'),
            'can_ask_to_ai_assistant': user.has_perm('core.can_ask_to_ai_assistant'),
            'can_generate_documents': user.has_perm('core.can_generate_documents'),
            'can_manage_incidents': user.has_perm('core.can_manage_incidents'),

            # Backwards compatibility (deprecare in futuro)
            'sections': user.has_perm('core.has_scrutinio_access'),
            'referenti': user.has_perm('core.can_manage_rdl'),
            'kpi': user.has_perm('core.can_view_kpi'),
            'upload_sezioni': user.has_perm('core.can_manage_territory'),
            'gestione_rdl': user.has_perm('core.can_manage_rdl'),

            # Info sulla catena deleghe
            'is_delegato': is_delegato,
            'is_sub_delegato': is_sub_delegato,
            'is_rdl': is_rdl,
        }

        return Response(permissions)
