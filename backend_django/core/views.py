"""
Views for core authentication and user management.
"""
import random
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
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

        # Generate 6-digit OTP code for in-app verification (PWA)
        otp_code = f"{random.randint(0, 999999):06d}"
        cache_key = f"magic_link_otp_{user.id}"
        cache.set(cache_key, otp_code, timeout=settings.MAGIC_LINK_TOKEN_EXPIRY)

        # Build magic link URL
        magic_link = f"{settings.FRONTEND_URL}/?token={token}"

        # Get active consultazione for context
        from elections.models import ConsultazioneElettorale
        consultazione = ConsultazioneElettorale.objects.filter(is_attiva=True).first()

        consultazione_nome = consultazione.nome if consultazione else "Elezioni in corso"
        consultazione_data = ""
        if consultazione and consultazione.data_inizio:
            from datetime import datetime
            data_fmt = consultazione.data_inizio.strftime('%d/%m/%Y')
            consultazione_data = f" - {data_fmt}"

        # Send email with HTML template
        user_name = user.display_name or user.email.split('@')[0].title()
        validity_minutes = settings.MAGIC_LINK_TOKEN_EXPIRY // 60

        # Plain text version (fallback)
        text_message = f'''
Ciao {user_name},

Hai richiesto l'accesso alla piattaforma AInaudi per la gestione di:
{consultazione_nome}{consultazione_data}

Clicca sul seguente link per accedere in modo sicuro:

{magic_link}

Oppure inserisci questo codice direttamente nell'app:

{otp_code}

⏱️  Il link e il codice sono validi per {validity_minutes} minuti.

Se non hai richiesto questo accesso, ignora questa email.
La tua sicurezza è importante per noi.

---
AInaudi - Piattaforma Gestione Elettorale
Movimento 5 Stelle
        '''.strip()

        # HTML version (modern and professional - Referendum M5S colors)
        html_message = f'''
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Accesso AInaudi</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5; padding: 20px 0;">
        <tr>
            <td align="center" style="padding: 0 12px;">
                <table cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow: hidden; width: 100%; max-width: 600px;">

                    <!-- Header con branding AInaudi -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #1B2A5B 0%, #0D1B3E 100%); padding: 30px 40px; text-align: center;">
                            <h1 style="margin: 0 0 8px 0; font-size: 28px; color: #FFFFFF; font-weight: 700; letter-spacing: -0.5px;">
                                <span style="color: #F5A623;">AI</span>naudi
                            </h1>
                            <p style="margin: 0; color: rgba(255,255,255,0.9); font-size: 14px; font-weight: 500; text-transform: uppercase; letter-spacing: 1px;">
                                Gestione Elettorale
                            </p>
                        </td>
                    </tr>

                    <!-- Consultazione badge -->
                    <tr>
                        <td style="padding: 25px 40px 0 40px; text-align: center;">
                            <div style="background: linear-gradient(135deg, #1B2A5B 0%, #0D1B3E 100%); border-radius: 8px; padding: 16px 24px; display: inline-block; box-shadow: 0 2px 4px rgba(44,95,111,0.3);">
                                <p style="margin: 0; color: #FFC800; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">
                                    📋 Consultazione attiva
                                </p>
                                <p style="margin: 0; color: #FFFFFF; font-size: 16px; font-weight: 700;">
                                    {consultazione_nome}
                                </p>
                                {f'<p style="margin: 4px 0 0 0; color: #E0E0E0; font-size: 13px; font-weight: 500;">{data_fmt}</p>' if consultazione and consultazione.data_inizio else ''}
                            </div>
                        </td>
                    </tr>

                    <!-- Saluto personalizzato -->
                    <tr>
                        <td style="padding: 30px 40px 20px 40px;">
                            <h2 style="margin: 0 0 15px 0; font-size: 22px; color: #1B2A5B; font-weight: 600;">
                                Ciao {user_name}! 👋
                            </h2>
                            <p style="margin: 0 0 20px 0; font-size: 16px; line-height: 1.6; color: #333333;">
                                Hai richiesto l'accesso sicuro alla piattaforma <strong style="color: #F5A623;">AInaudi</strong>.
                                Clicca sul pulsante qui sotto per accedere immediatamente.
                            </p>
                        </td>
                    </tr>

                    <!-- CTA Button -->
                    <tr>
                        <td style="padding: 0 40px 30px 40px; text-align: center;">
                            <a href="{magic_link}" style="display: inline-block; background-color: #F2CB13; color: #2E2D2C; text-decoration: none; padding: 16px 40px; border-radius: 12px; font-size: 16px; font-weight: 600; letter-spacing: 0.3px; box-shadow: 0 4px 12px rgba(242,203,19,0.4); transition: all 0.3s ease;">
                                🔐 Accedi alla Piattaforma
                            </a>
                            <div style="margin: 25px 0 0 0; padding: 20px; background-color: #f8f9fa; border-radius: 8px; border: 1px solid #e9ecef;">
                                <p style="margin: 0 0 10px 0; font-size: 14px; color: #666666; font-weight: 600;">
                                    Stai usando l'app? Inserisci questo codice:
                                </p>
                                <p style="margin: 0; font-size: 36px; font-weight: 700; color: #1B2A5B; letter-spacing: 8px; font-family: monospace;">
                                    {otp_code}
                                </p>
                            </div>
                            <p style="margin: 15px 0 0 0; font-size: 12px; color: #999999; line-height: 1.5;">
                                Oppure copia e incolla questo link nel browser:<br/>
                                <span style="word-break: break-all;">{magic_link}</span>
                            </p>
                        </td>
                    </tr>

                    <!-- Info box -->
                    <tr>
                        <td style="padding: 0 40px 30px 40px;">
                            <div style="background-color: #E8F4F8; border-left: 4px solid #2C5F6F; padding: 15px 20px; border-radius: 4px;">
                                <p style="margin: 0 0 8px 0; font-size: 14px; color: #1B2A5B; font-weight: 600;">
                                    ⏱️  Validità del link
                                </p>
                                <p style="margin: 0; font-size: 14px; line-height: 1.5; color: #555555;">
                                    Questo link è valido per <strong style="color: #F5A623;">{validity_minutes} minuti</strong> per garantire la massima sicurezza del tuo accesso.
                                </p>
                            </div>
                        </td>
                    </tr>

                    <!-- Security notice -->
                    <tr>
                        <td style="padding: 0 40px 30px 40px;">
                            <div style="background-color: #f8f9fa; border-radius: 6px; padding: 20px; text-align: center;">
                                <p style="margin: 0 0 10px 0; font-size: 14px; color: #666666; line-height: 1.6;">
                                    🔒 <strong>Sicurezza garantita</strong><br/>
                                    Non hai richiesto questo accesso? Ignora questa email.<br/>
                                    Il link scadrà automaticamente e nessuno potrà accedere al tuo account.
                                </p>
                            </div>
                        </td>
                    </tr>

                    <!-- Footer con barra gialla M5S -->
                    <tr>
                        <td style="background: linear-gradient(to bottom, #f8f9fa 0%, #f8f9fa 10%, #FFC800 10%, #FFC800 100%); padding: 25px 40px; text-align: center; border-top: 1px solid #e9ecef;">
                            <p style="margin: 0 0 8px 0; font-size: 13px; color: #666666; font-weight: 600;">
                                AInaudi - Piattaforma Gestione Elettorale
                            </p>
                            <p style="margin: 0 0 15px 0; font-size: 12px; color: #999999;">
                                Movimento 5 Stelle
                            </p>
                            <p style="margin: 0; font-size: 11px; color: #aaaaaa; line-height: 1.4;">
                                Questa è una email automatica, si prega di non rispondere.<br/>
                                Per assistenza contatta il tuo delegato o sub-delegato.
                            </p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        '''.strip()

        try:
            import logging
            logger = logging.getLogger(__name__)

            # Log email configuration for debugging
            logger.info(f"Email Backend: {settings.EMAIL_BACKEND}")
            logger.info(f"Email Host: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
            logger.info(f"Email From: {settings.DEFAULT_FROM_EMAIL}")

            send_mail(
                subject=f'🔐 Accesso AInaudi - {consultazione_nome}',
                message=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
                html_message=html_message,
            )
            logger.info(f"✅ Magic link email sent to {email}")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"❌ Error sending magic link email: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

            return Response(
                {'error': f'Errore invio email: {type(e).__name__}. Contatta l\'amministratore.'},
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

        token = serializer.validated_data.get('token')
        otp = serializer.validated_data.get('otp')
        email = serializer.validated_data.get('email')

        if token:
            # Method 1: Signed token verification (magic link click)
            try:
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

            try:
                user = User.objects.get(id=int(user_id))
            except (User.DoesNotExist, ValueError):
                return Response(
                    {'error': 'Utente non trovato.'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Method 2: OTP + email verification (in-app code entry)
            try:
                user = User.objects.get(email=email.lower())
            except User.DoesNotExist:
                return Response(
                    {'error': 'Utente non trovato.'},
                    status=status.HTTP_404_NOT_FOUND
                )

            cache_key = f"magic_link_otp_{user.id}"
            stored_otp = cache.get(cache_key)

            if not stored_otp:
                return Response(
                    {'error': 'Codice scaduto. Richiedine uno nuovo.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if otp != stored_otp:
                return Response(
                    {'error': 'Codice non valido.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # OTP used successfully, delete it
            cache.delete(cache_key)

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


class ClientErrorView(APIView):
    """
    POST /api/client-errors/

    Receives frontend JavaScript errors and logs them to Cloud Logging.
    On App Engine, Cloud Error Reporting picks these up automatically.
    No auth required - errors can happen before/during login.
    """
    permission_classes = []  # No auth - errors can happen on login screen
    throttle_classes = []    # Allow error reports even if throttled

    def post(self, request):
        import logging
        logger = logging.getLogger('frontend')

        error_msg = request.data.get('message', 'Unknown frontend error')
        stack = request.data.get('stack', '')
        component_stack = request.data.get('componentStack', '')
        url = request.data.get('url', '')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        user_email = ''
        if request.user and request.user.is_authenticated:
            user_email = request.user.email

        # Format as a Python-style error so Cloud Error Reporting groups it
        logger.error(
            'Frontend error: %s\n'
            'URL: %s\n'
            'User: %s\n'
            'User-Agent: %s\n'
            'Stack: %s\n'
            'Component Stack: %s',
            error_msg, url, user_email, user_agent, stack, component_stack,
        )

        return Response({'ok': True})


class PermissionsView(APIView):
    """
    Get the current user's permissions for the frontend.

    GET /api/permissions
    GET /api/permissions?consultazione=1

    Ritorna permessi basati su django.contrib.auth.permissions assegnati
    automaticamente dai signals in base alla catena delle deleghe.

    Ogni voce del menu ha il suo permesso specifico.

    Returns:
    {
        "is_superuser": true/false,

        # Menu permissions (15 voci)
        "can_view_dashboard": true/false,        # Dashboard
        "can_manage_territory": true/false,      # Territorio
        "can_manage_elections": true/false,      # Consultazione
        "can_manage_campaign": true/false,       # Campagne
        "can_manage_rdl": true/false,            # Gestione RDL
        "can_manage_sections": true/false,       # Gestione Sezioni
        "can_manage_mappatura": true/false,      # Mappatura
        "can_manage_delegations": true/false,    # Catena Deleghe
        "can_manage_designazioni": true/false,   # Designazioni
        "can_manage_templates": true/false,      # Template PDF
        "can_generate_documents": true/false,    # Genera Moduli
        "has_scrutinio_access": true/false,      # Scrutinio
        "can_view_resources": true/false,        # Risorse
        "can_view_live_results": true/false,     # Risultati Live
        "can_view_kpi": true/false,              # Diretta (KPI)

        # Future features
        "can_ask_to_ai_assistant": true/false,
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

                # Menu permissions (uno per voce)
                'can_view_dashboard': True,
                'can_manage_territory': True,
                'can_manage_elections': True,
                'can_manage_campaign': True,
                'can_manage_rdl': True,
                'can_manage_sections': True,
                'can_manage_mappatura': True,
                'can_manage_delegations': True,
                'can_manage_designazioni': True,
                'can_manage_templates': True,
                'can_generate_documents': True,
                'has_scrutinio_access': True,
                'can_view_resources': True,
                'can_view_live_results': True,
                'can_view_kpi': True,

                # Admin-only
                'can_manage_mass_email': True,
                'can_manage_events': True,

                # Future features
                'can_ask_to_ai_assistant': True,
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

            # Menu permissions (uno per voce)
            'can_view_dashboard': user.has_perm('core.can_view_dashboard'),
            'can_manage_territory': user.has_perm('core.can_manage_territory'),
            'can_manage_elections': user.has_perm('core.can_manage_elections'),
            'can_manage_campaign': user.has_perm('core.can_manage_campaign'),
            'can_manage_rdl': user.has_perm('core.can_manage_rdl'),
            'can_manage_sections': user.has_perm('core.can_manage_sections'),
            'can_manage_mappatura': user.has_perm('core.can_manage_mappatura'),
            'can_manage_delegations': user.has_perm('core.can_manage_delegations'),
            'can_manage_designazioni': user.has_perm('core.can_manage_designazioni'),
            'can_manage_templates': user.has_perm('core.can_manage_templates'),
            'can_generate_documents': user.has_perm('core.can_generate_documents'),
            'has_scrutinio_access': user.has_perm('core.has_scrutinio_access'),
            'can_view_resources': user.has_perm('core.can_view_resources'),
            'can_view_live_results': user.has_perm('core.can_view_live_results'),
            'can_view_kpi': user.has_perm('core.can_view_kpi'),

            # Admin-only
            'can_manage_mass_email': user.has_perm('core.can_manage_mass_email'),
            'can_manage_events': user.has_perm('core.can_manage_events'),

            # Future features
            'can_ask_to_ai_assistant': user.has_perm('core.can_ask_to_ai_assistant'),
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
