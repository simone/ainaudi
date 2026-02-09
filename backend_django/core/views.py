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

⏱️  Il link è valido per {validity_minutes} minuti.

Se non hai richiesto questo accesso, ignora questa email.
La tua sicurezza è importante per noi.

---
AInaudi - Piattaforma Gestione Elettorale
Movimento 5 Stelle
        '''.strip()

        # HTML version (modern and professional)
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
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow: hidden; max-width: 100%;">

                    <!-- Header con branding M5S -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #000000 0%, #1a1a1a 100%); padding: 30px 40px; text-align: center;">
                            <div style="background-color: #FFCC00; display: inline-block; padding: 12px 24px; border-radius: 6px; margin-bottom: 15px;">
                                <h1 style="margin: 0; font-size: 28px; color: #000000; font-weight: 700; letter-spacing: -0.5px;">
                                    AInaudi
                                </h1>
                            </div>
                            <p style="margin: 10px 0 0 0; color: #FFCC00; font-size: 14px; font-weight: 500; text-transform: uppercase; letter-spacing: 1px;">
                                Gestione Elettorale
                            </p>
                        </td>
                    </tr>

                    <!-- Consultazione badge -->
                    <tr>
                        <td style="padding: 25px 40px 0 40px; text-align: center;">
                            <div style="background: linear-gradient(135deg, #FFCC00 0%, #FFD633 100%); border-radius: 8px; padding: 16px 24px; display: inline-block; box-shadow: 0 2px 4px rgba(255,204,0,0.3);">
                                <p style="margin: 0; color: #000000; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">
                                    📋 Consultazione attiva
                                </p>
                                <p style="margin: 0; color: #000000; font-size: 16px; font-weight: 700;">
                                    {consultazione_nome}
                                </p>
                                {f'<p style="margin: 4px 0 0 0; color: #333333; font-size: 13px; font-weight: 500;">{data_fmt}</p>' if consultazione and consultazione.data_inizio else ''}
                            </div>
                        </td>
                    </tr>

                    <!-- Saluto personalizzato -->
                    <tr>
                        <td style="padding: 30px 40px 20px 40px;">
                            <h2 style="margin: 0 0 15px 0; font-size: 22px; color: #000000; font-weight: 600;">
                                Ciao {user_name}! 👋
                            </h2>
                            <p style="margin: 0 0 20px 0; font-size: 16px; line-height: 1.6; color: #333333;">
                                Hai richiesto l'accesso sicuro alla piattaforma <strong>AInaudi</strong>.
                                Clicca sul pulsante qui sotto per accedere immediatamente.
                            </p>
                        </td>
                    </tr>

                    <!-- CTA Button -->
                    <tr>
                        <td style="padding: 0 40px 30px 40px; text-align: center;">
                            <a href="{magic_link}" style="display: inline-block; background: linear-gradient(135deg, #FFCC00 0%, #FFD633 100%); color: #000000; text-decoration: none; padding: 16px 40px; border-radius: 6px; font-size: 16px; font-weight: 700; letter-spacing: 0.3px; box-shadow: 0 4px 12px rgba(255,204,0,0.4); transition: all 0.3s ease;">
                                🔐 Accedi alla Piattaforma
                            </a>
                            <p style="margin: 20px 0 0 0; font-size: 13px; color: #666666; line-height: 1.5;">
                                Oppure copia e incolla questo link nel tuo browser:<br/>
                                <span style="color: #999999; font-size: 12px; word-break: break-all;">{magic_link}</span>
                            </p>
                        </td>
                    </tr>

                    <!-- Info box -->
                    <tr>
                        <td style="padding: 0 40px 30px 40px;">
                            <div style="background-color: #fffbf0; border-left: 4px solid #FFCC00; padding: 15px 20px; border-radius: 4px;">
                                <p style="margin: 0 0 8px 0; font-size: 14px; color: #000000; font-weight: 600;">
                                    ⏱️  Validità del link
                                </p>
                                <p style="margin: 0; font-size: 14px; line-height: 1.5; color: #555555;">
                                    Questo link è valido per <strong>{validity_minutes} minuti</strong> per garantire la massima sicurezza del tuo accesso.
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

                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8f9fa; padding: 25px 40px; text-align: center; border-top: 1px solid #e9ecef;">
                            <p style="margin: 0 0 8px 0; font-size: 13px; color: #666666; font-weight: 600;">
                                AInaudi - Piattaforma Gestione Elettorale
                            </p>
                            <p style="margin: 0; font-size: 12px; color: #999999;">
                                Movimento 5 Stelle
                            </p>
                            <p style="margin: 12px 0 0 0; font-size: 11px; color: #aaaaaa; line-height: 1.4;">
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
            send_mail(
                subject=f'🔐 Accesso AInaudi - {consultazione_nome}',
                message=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
                html_message=html_message,
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
