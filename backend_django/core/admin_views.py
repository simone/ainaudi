"""
Admin views for Magic Link and Google OAuth authentication.
"""
import secrets
import urllib.parse
import requests

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, get_user_model
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views import View
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from .models import IdentityProviderLink

User = get_user_model()
signer = TimestampSigner()


class AdminGoogleOAuthStartView(View):
    """Start Google OAuth flow - redirect to Google."""

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('admin:index')

        # Generate state token for CSRF protection
        state = secrets.token_urlsafe(32)
        request.session['google_oauth_state'] = state

        # Build Google OAuth URL
        google_client_id = settings.SOCIALACCOUNT_PROVIDERS['google']['APP']['client_id']

        # Use base URL without path (like production)
        redirect_uri = request.build_absolute_uri('/').rstrip('/')

        params = {
            'client_id': google_client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'openid email profile',
            'state': state,
            'prompt': 'select_account',
        }

        auth_url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode(params)
        return redirect(auth_url)


class AdminGoogleOAuthCallbackView(View):
    """Handle Google OAuth callback."""

    def get(self, request):
        # Check if this is an OAuth callback (has code or error parameter)
        code = request.GET.get('code')
        error = request.GET.get('error')
        state = request.GET.get('state', '')

        # If no OAuth parameters, redirect to admin
        if not code and not error and not state:
            return redirect('admin:index')

        # Verify state
        stored_state = request.session.pop('google_oauth_state', None)

        if not state or state != stored_state:
            messages.error(request, 'Errore di sicurezza. Riprova.')
            return redirect('admin_magic_link_request')

        # Check for errors from Google
        if error:
            messages.error(request, f'Errore Google: {error}')
            return redirect('admin_magic_link_request')

        # Verify we have authorization code
        if not code:
            messages.error(request, 'Codice di autorizzazione mancante.')
            return redirect('admin_magic_link_request')

        # Exchange code for tokens
        google_client_id = settings.SOCIALACCOUNT_PROVIDERS['google']['APP']['client_id']
        google_client_secret = settings.SOCIALACCOUNT_PROVIDERS['google']['APP'].get('secret', '')
        redirect_uri = request.build_absolute_uri('/').rstrip('/')

        token_response = requests.post('https://oauth2.googleapis.com/token', data={
            'code': code,
            'client_id': google_client_id,
            'client_secret': google_client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        })

        if token_response.status_code != 200:
            messages.error(request, 'Errore durante lo scambio del token.')
            return redirect('admin_magic_link_request')

        tokens = token_response.json()
        id_token_jwt = tokens.get('id_token')

        if not id_token_jwt:
            messages.error(request, 'Token ID mancante.')
            return redirect('admin_magic_link_request')

        # Verify ID token
        try:
            idinfo = id_token.verify_oauth2_token(
                id_token_jwt,
                google_requests.Request(),
                google_client_id
            )
        except ValueError as e:
            messages.error(request, f'Token non valido: {str(e)}')
            return redirect('admin_magic_link_request')

        # Extract user info
        google_uid = idinfo['sub']
        email = idinfo.get('email')
        email_verified = idinfo.get('email_verified', False)

        if not email or not email_verified:
            messages.error(request, 'Email Google non verificata.')
            return redirect('admin_magic_link_request')

        # Find or create user
        user = None
        try:
            link = IdentityProviderLink.objects.get(
                provider=IdentityProviderLink.Provider.GOOGLE,
                provider_uid=google_uid
            )
            user = link.user
            link.last_used_at = timezone.now()
            link.save(update_fields=['last_used_at'])
        except IdentityProviderLink.DoesNotExist:
            try:
                user = User.objects.get(email=email)
                IdentityProviderLink.objects.create(
                    user=user,
                    provider=IdentityProviderLink.Provider.GOOGLE,
                    provider_uid=google_uid,
                    provider_email=email,
                    is_primary=not user.identity_links.exists(),
                    last_used_at=timezone.now(),
                )
            except User.DoesNotExist:
                messages.error(request, 'Nessun account associato a questa email Google. Contatta il delegato della tua zona.')
                return redirect('admin_magic_link_request')

        # Check if user is staff
        if not user.is_staff:
            messages.error(request, 'Non hai i permessi per accedere all\'admin.')
            return redirect('admin_magic_link_request')

        # Log user in
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        # Update last login info
        user.last_login = timezone.now()
        user.last_login_ip = self.get_client_ip(request)
        user.save(update_fields=['last_login', 'last_login_ip'])

        messages.success(request, f'Benvenuto, {user.display_name or user.email}!')
        return redirect('admin:index')

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class AdminMagicLinkRequestView(View):
    """Request a magic link for admin login."""
    template_name = 'admin/magic_link_request.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('admin:index')
        google_client_id = settings.SOCIALACCOUNT_PROVIDERS.get('google', {}).get('APP', {}).get('client_id', '')
        return render(request, self.template_name, {'google_client_id': google_client_id})

    def post(self, request):
        email = request.POST.get('email', '').strip().lower()
        google_client_id = settings.SOCIALACCOUNT_PROVIDERS.get('google', {}).get('APP', {}).get('client_id', '')

        if not email:
            messages.error(request, 'Inserisci un indirizzo email.')
            return render(request, self.template_name, {'google_client_id': google_client_id})

        # Check if user exists and is staff
        try:
            user = User.objects.get(email=email)
            if not user.is_staff:
                # Don't reveal if user exists but isn't staff
                messages.success(
                    request,
                    'Se l\'email è registrata, riceverai un link di accesso.'
                )
                return render(request, self.template_name, {'email_sent': True})
        except User.DoesNotExist:
            # Don't reveal if user doesn't exist
            messages.success(
                request,
                'Se l\'email è registrata, riceverai un link di accesso.'
            )
            return render(request, self.template_name, {'email_sent': True})

        # Generate signed token
        token = signer.sign(email)

        # Build magic link URL for admin
        magic_link = request.build_absolute_uri(f'/admin/magic-link/verify/?token={token}')

        # Send email
        try:
            send_mail(
                subject='Accesso Admin RDL 5 Stelle',
                message=f'''
Ciao {user.display_name or user.email},

Clicca sul seguente link per accedere all'area amministrazione di RDL 5 Stelle:

{magic_link}

Il link è valido per {settings.MAGIC_LINK_TOKEN_EXPIRY // 60} minuti.

Se non hai richiesto questo link, ignora questa email.

Movimento 5 Stelle
                '''.strip(),
                html_message=f'''
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: #004b6b; padding: 20px; text-align: center;">
        <h1 style="color: #e9d483; margin: 0;">RDL 5 Stelle</h1>
    </div>
    <div style="padding: 30px; background: #f9f9f9;">
        <p>Ciao <strong>{user.display_name or user.email}</strong>,</p>
        <p>Clicca sul pulsante per accedere all'area amministrazione:</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{magic_link}"
               style="background: #e30413; color: white; padding: 15px 30px;
                      text-decoration: none; border-radius: 5px; font-weight: bold;">
                Accedi all'Admin
            </a>
        </p>
        <p style="color: #666; font-size: 14px;">
            Il link è valido per {settings.MAGIC_LINK_TOKEN_EXPIRY // 60} minuti.<br>
            Se non hai richiesto questo link, ignora questa email.
        </p>
    </div>
    <div style="background: #004b6b; padding: 15px; text-align: center;">
        <p style="color: #e9d483; margin: 0; font-size: 12px;">Movimento 5 Stelle</p>
    </div>
</div>
                '''.strip(),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            messages.success(
                request,
                'Se l\'email è registrata, riceverai un link di accesso.'
            )
        except Exception as e:
            messages.error(request, f'Errore invio email. Riprova più tardi.')

        return render(request, self.template_name, {'email_sent': True, 'email': email, 'google_client_id': google_client_id})


class AdminMagicLinkVerifyView(View):
    """Verify magic link token and log user into admin."""

    def get(self, request):
        token = request.GET.get('token', '')

        if not token:
            messages.error(request, 'Token mancante.')
            return redirect('admin:login')

        try:
            # Verify token signature and expiry
            email = signer.unsign(
                token,
                max_age=settings.MAGIC_LINK_TOKEN_EXPIRY
            )
        except SignatureExpired:
            messages.error(request, 'Link scaduto. Richiedine uno nuovo.')
            return redirect('admin_magic_link_request')
        except BadSignature:
            messages.error(request, 'Link non valido.')
            return redirect('admin:login')

        # Find user
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, 'Utente non trovato.')
            return redirect('admin:login')

        # Check if user is staff
        if not user.is_staff:
            messages.error(request, 'Non hai i permessi per accedere all\'admin.')
            return redirect('admin:login')

        # Update/create identity provider link
        IdentityProviderLink.objects.update_or_create(
            user=user,
            provider=IdentityProviderLink.Provider.MAGIC_LINK,
            defaults={
                'provider_uid': email,
                'provider_email': email,
                'last_used_at': timezone.now(),
            }
        )

        # Log user in
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        # Update last login info
        user.last_login = timezone.now()
        user.last_login_ip = self.get_client_ip(request)
        user.save(update_fields=['last_login', 'last_login_ip'])

        messages.success(request, f'Benvenuto, {user.display_name or user.email}!')
        return redirect('admin:index')

    def get_client_ip(self, request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class AdminGoogleLoginView(View):
    """Handle Google OAuth login for admin."""

    def get(self, request):
        """Redirect to magic link page (Google login is now embedded there)."""
        if request.user.is_authenticated:
            return redirect('admin:index')
        return redirect('admin_magic_link_request')

    def post(self, request):
        """Verify Google ID token and log user in."""
        credential = request.POST.get('credential', '')

        if not credential:
            messages.error(request, 'Token Google mancante.')
            return redirect('admin_magic_link_request')

        try:
            # Verify the Google ID token
            google_client_id = settings.SOCIALACCOUNT_PROVIDERS['google']['APP']['client_id']
            idinfo = id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                google_client_id
            )

            # Extract user info
            google_uid = idinfo['sub']
            email = idinfo.get('email')
            email_verified = idinfo.get('email_verified', False)

            if not email or not email_verified:
                messages.error(request, 'Email Google non verificata.')
                return redirect('admin_magic_link_request')

            # Find user by email or Google UID
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
                    # Create identity provider link for existing user
                    IdentityProviderLink.objects.create(
                        user=user,
                        provider=IdentityProviderLink.Provider.GOOGLE,
                        provider_uid=google_uid,
                        provider_email=email,
                        is_primary=not user.identity_links.exists(),
                        last_used_at=timezone.now(),
                    )
                except User.DoesNotExist:
                    messages.error(request, 'Nessun account admin associato a questa email Google.')
                    return redirect('admin_magic_link_request')

            # Check if user is staff
            if not user.is_staff:
                messages.error(request, 'Non hai i permessi per accedere all\'admin.')
                return redirect('admin:login')

            # Log user in
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            # Update last login info
            user.last_login = timezone.now()
            user.last_login_ip = self.get_client_ip(request)
            user.save(update_fields=['last_login', 'last_login_ip'])

            messages.success(request, f'Benvenuto, {user.display_name or user.email}!')
            return redirect('admin:index')

        except ValueError as e:
            messages.error(request, f'Token Google non valido: {str(e)}')
            return redirect('admin_magic_link_request')

    def get_client_ip(self, request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
