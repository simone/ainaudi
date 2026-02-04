"""
Views for CampagnaReclutamento API endpoints.

Public endpoints:
- GET /api/campagna/{slug}/ - Info pubblica campagna
- POST /api/campagna/{slug}/registra/ - Registrazione pubblica
- GET /campagna/{slug} - HTML page with OG meta tags (for social sharing)

Admin/delegate endpoints:
- GET/POST /api/deleghe/campagne/ - CRUD campagne
- GET/PUT/DELETE /api/deleghe/campagne/{id}/ - Dettaglio campagna
"""
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.views import View
from django.conf import settings

from .models import DelegatoDiLista, SubDelega
from campaign.models import CampagnaReclutamento
from .serializers import (
    CampagnaReclutamentoSerializer,
    CampagnaReclutamentoCreateSerializer,
    CampagnaReclutamentoPublicSerializer,
    CampagnaRegistrazioneSerializer,
)
from .permissions import get_user_delegation_roles


# =============================================================================
# Public endpoints (no authentication required)
# =============================================================================

class CampagnaOGView(View):
    """
    Serve HTML page with Open Graph meta tags for social media sharing.

    GET /campagna/{slug}

    Returns HTML that:
    - Contains proper OG meta tags for Facebook, Twitter, etc.
    - Redirects browser to the React SPA
    """

    def get(self, request, slug):
        campagna = get_object_or_404(
            CampagnaReclutamento,
            slug=slug,
            stato__in=['ATTIVA', 'CHIUSA']
        )

        # Build the canonical URL
        frontend_url = getattr(settings, 'FRONTEND_URL', request.build_absolute_uri('/'))
        canonical_url = f"{frontend_url.rstrip('/')}/campagna/{slug}"

        # Get logo URL
        logo_url = f"{frontend_url.rstrip('/')}/favicon.svg"

        # Prepare description (escape HTML)
        import html
        raw_desc = campagna.descrizione[:200] if campagna.descrizione else "Diventa Rappresentante di Lista e tutela la democrazia!"
        if len(campagna.descrizione or '') > 200:
            raw_desc += "..."
        # Replace newlines with spaces for meta tags
        description = html.escape(raw_desc.replace('\n', ' ').replace('\r', ' '))
        title = html.escape(campagna.nome)

        # Build HTML with OG tags
        html_content = f'''<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title} - Diventa RDL</title>

    <!-- Open Graph / Facebook -->
    <meta property="og:type" content="website">
    <meta property="og:url" content="{canonical_url}">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    <meta property="og:image" content="{logo_url}">
    <meta property="og:locale" content="it_IT">
    <meta property="og:site_name" content="AInaudi">

    <!-- Twitter -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:url" content="{canonical_url}">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{description}">
    <meta name="twitter:image" content="{logo_url}">

    <!-- Standard meta -->
    <meta name="description" content="{description}">
    <link rel="canonical" href="{canonical_url}">

    <!-- Redirect to React SPA after a short delay for crawlers -->
    <meta http-equiv="refresh" content="0; url={canonical_url}">

    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #0d6efd 0%, #0a58ca 50%, #084298 100%);
            color: white;
            text-align: center;
            padding: 20px;
        }}
        .container {{
            max-width: 600px;
        }}
        h1 {{
            font-size: 2rem;
            margin-bottom: 1rem;
        }}
        p {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        a {{
            color: white;
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <p>{description}</p>
        <p>Reindirizzamento in corso... <a href="{canonical_url}">Clicca qui</a> se non vieni reindirizzato.</p>
    </div>
</body>
</html>'''

        return HttpResponse(html_content, content_type='text/html')


class CampagnaPublicView(APIView):
    """
    Public campaign info.

    GET /api/campagna/{slug}/
    Returns public campaign info for the registration page.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        campagna = get_object_or_404(
            CampagnaReclutamento,
            slug=slug,
            stato__in=['ATTIVA', 'CHIUSA']  # Hide drafts
        )
        serializer = CampagnaReclutamentoPublicSerializer(campagna)
        return Response(serializer.data)


class CampagnaRegistraView(APIView):
    """
    Public registration via campaign.

    POST /api/campagna/{slug}/registra/
    Creates an RdlRegistration linked to the campaign.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, slug):
        campagna = get_object_or_404(
            CampagnaReclutamento,
            slug=slug,
            stato='ATTIVA'
        )

        serializer = CampagnaRegistrazioneSerializer(
            data=request.data,
            context={'campagna': campagna}
        )

        if serializer.is_valid():
            registration = serializer.save()

            response_data = {
                'success': True,
                'message': (
                    campagna.messaggio_conferma
                    if campagna.messaggio_conferma
                    else 'Registrazione completata con successo.'
                ),
                'id': registration.id,
                'richiede_approvazione': campagna.richiedi_approvazione
            }

            if campagna.richiedi_approvazione:
                response_data['message'] += ' La tua richiesta sarà valutata dal delegato.'

            return Response(response_data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =============================================================================
# Admin/delegate endpoints (authentication required)
# =============================================================================

class CampagnaListCreateView(APIView):
    """
    List and create campaigns.

    GET /api/deleghe/campagne/
    POST /api/deleghe/campagne/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """List campaigns visible to the user.

        Un delegato/sub-delegato può vedere:
        1. Campagne che ha creato
        2. Campagne collegate alle sue deleghe
        3. Campagne di altri delegati/sub-delegati della stessa consultazione
           (per coordinamento, tutti i referenti vedono tutte le campagne attive)
        """
        user = request.user

        if user.is_superuser:
            queryset = CampagnaReclutamento.objects.all()
        else:
            roles = get_user_delegation_roles(user)

            if not roles['is_delegato'] and not roles['is_sub_delegato']:
                # Non è né delegato né sub-delegato: mostra solo le proprie
                queryset = CampagnaReclutamento.objects.filter(
                    created_by_email=user.email
                )
            else:
                # È delegato o sub-delegato: mostra tutte le campagne delle consultazioni
                # a cui partecipa (per coordinamento tra referenti)
                consultazione_ids = set()

                for delega in roles['deleghe_lista']:
                    if delega.consultazione_id:
                        consultazione_ids.add(delega.consultazione_id)

                for sub_delega in roles['sub_deleghe'].select_related('delegato'):
                    if sub_delega.delegato and sub_delega.delegato.consultazione_id:
                        consultazione_ids.add(sub_delega.delegato.consultazione_id)

                if consultazione_ids:
                    # Mostra tutte le campagne delle consultazioni a cui partecipa
                    queryset = CampagnaReclutamento.objects.filter(
                        consultazione_id__in=consultazione_ids
                    )
                else:
                    # Fallback: solo le proprie o collegate
                    delegato_ids = list(roles['deleghe_lista'].values_list('id', flat=True))
                    sub_delega_ids = list(roles['sub_deleghe'].values_list('id', flat=True))

                    queryset = CampagnaReclutamento.objects.filter(
                        created_by_email=user.email
                    ) | CampagnaReclutamento.objects.filter(
                        delegato_id__in=delegato_ids
                    ) | CampagnaReclutamento.objects.filter(
                        sub_delega_id__in=sub_delega_ids
                    )

        queryset = queryset.select_related(
            'consultazione', 'delegato', 'sub_delega'
        ).prefetch_related(
            'territorio_regioni', 'territorio_province', 'territorio_comuni'
        ).distinct().order_by('-data_apertura')

        serializer = CampagnaReclutamentoSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Create a new campaign."""
        user = request.user
        roles = get_user_delegation_roles(user)

        if not user.is_superuser and not roles['is_delegato'] and not roles['is_sub_delegato']:
            return Response(
                {'error': 'Solo delegati e sub-delegati possono creare campagne'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = CampagnaReclutamentoCreateSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            campagna = serializer.save()
            return Response(
                CampagnaReclutamentoSerializer(campagna).data,
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CampagnaDetailView(APIView):
    """
    Retrieve, update or delete a campaign.

    GET /api/deleghe/campagne/{id}/
    PUT /api/deleghe/campagne/{id}/
    DELETE /api/deleghe/campagne/{id}/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, pk, user):
        """Get campaign if user has access."""
        campagna = get_object_or_404(CampagnaReclutamento, pk=pk)

        if user.is_superuser:
            return campagna

        # Check ownership
        if campagna.created_by_email == user.email:
            return campagna

        roles = get_user_delegation_roles(user)
        delegato_ids = list(roles['deleghe_lista'].values_list('id', flat=True))
        sub_delega_ids = list(roles['sub_deleghe'].values_list('id', flat=True))

        if campagna.delegato_id in delegato_ids or campagna.sub_delega_id in sub_delega_ids:
            return campagna

        return None

    def get(self, request, pk):
        campagna = self.get_object(pk, request.user)
        if not campagna:
            return Response(
                {'error': 'Non autorizzato'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = CampagnaReclutamentoSerializer(campagna)
        return Response(serializer.data)

    def put(self, request, pk):
        campagna = self.get_object(pk, request.user)
        if not campagna:
            return Response(
                {'error': 'Non autorizzato'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = CampagnaReclutamentoCreateSerializer(
            campagna,
            data=request.data,
            partial=True,
            context={'request': request}
        )

        if serializer.is_valid():
            campagna = serializer.save()
            return Response(CampagnaReclutamentoSerializer(campagna).data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        campagna = self.get_object(pk, request.user)
        if not campagna:
            return Response(
                {'error': 'Non autorizzato'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Don't allow deletion of active campaigns with registrations
        if campagna.stato == 'ATTIVA' and campagna.n_registrazioni > 0:
            return Response(
                {'error': 'Non è possibile eliminare una campagna attiva con registrazioni'},
                status=status.HTTP_400_BAD_REQUEST
            )

        campagna.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CampagnaAttivaView(APIView):
    """
    Activate a campaign.

    POST /api/deleghe/campagne/{id}/attiva/
    Changes campaign state from BOZZA to ATTIVA.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        campagna = get_object_or_404(CampagnaReclutamento, pk=pk)
        user = request.user

        # Check ownership
        if not user.is_superuser:
            if campagna.created_by_email != user.email:
                roles = get_user_delegation_roles(user)
                delegato_ids = list(roles['deleghe_lista'].values_list('id', flat=True))
                sub_delega_ids = list(roles['sub_deleghe'].values_list('id', flat=True))

                if campagna.delegato_id not in delegato_ids and campagna.sub_delega_id not in sub_delega_ids:
                    return Response(
                        {'error': 'Non autorizzato'},
                        status=status.HTTP_403_FORBIDDEN
                    )

        if campagna.stato != 'BOZZA':
            return Response(
                {'error': 'Solo le campagne in bozza possono essere attivate'},
                status=status.HTTP_400_BAD_REQUEST
            )

        campagna.stato = 'ATTIVA'
        campagna.save()

        return Response(CampagnaReclutamentoSerializer(campagna).data)


class CampagnaChiudiView(APIView):
    """
    Close a campaign.

    POST /api/deleghe/campagne/{id}/chiudi/
    Changes campaign state from ATTIVA to CHIUSA.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        campagna = get_object_or_404(CampagnaReclutamento, pk=pk)
        user = request.user

        # Check ownership
        if not user.is_superuser:
            if campagna.created_by_email != user.email:
                roles = get_user_delegation_roles(user)
                delegato_ids = list(roles['deleghe_lista'].values_list('id', flat=True))
                sub_delega_ids = list(roles['sub_deleghe'].values_list('id', flat=True))

                if campagna.delegato_id not in delegato_ids and campagna.sub_delega_id not in sub_delega_ids:
                    return Response(
                        {'error': 'Non autorizzato'},
                        status=status.HTTP_403_FORBIDDEN
                    )

        if campagna.stato != 'ATTIVA':
            return Response(
                {'error': 'Solo le campagne attive possono essere chiuse'},
                status=status.HTTP_400_BAD_REQUEST
            )

        campagna.stato = 'CHIUSA'
        campagna.save()

        return Response(CampagnaReclutamentoSerializer(campagna).data)
