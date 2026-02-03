"""
Admin views for Magic Link authentication.
"""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, get_user_model
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views import View

User = get_user_model()
signer = TimestampSigner()


class AdminMagicLinkRequestView(View):
    """Request a magic link for admin login."""
    template_name = 'admin/magic_link_request.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('admin:index')
        return render(request, self.template_name)

    def post(self, request):
        email = request.POST.get('email', '').strip().lower()

        if not email:
            messages.error(request, 'Inserisci un indirizzo email.')
            return render(request, self.template_name)

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

        return render(request, self.template_name, {'email_sent': True, 'email': email})


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


