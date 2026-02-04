"""
Views for CampagnaReclutamento API endpoints.

Public endpoints:
- GET /api/campagna/{slug}/ - Info pubblica campagna
- POST /api/campagna/{slug}/registra/ - Registrazione pubblica

Admin/delegate endpoints:
- GET/POST /api/deleghe/campagne/ - CRUD campagne
- GET/PUT/DELETE /api/deleghe/campagne/{id}/ - Dettaglio campagna
"""
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

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
        """List campaigns visible to the user."""
        user = request.user

        if user.is_superuser:
            queryset = CampagnaReclutamento.objects.all()
        else:
            # Get campaigns created by user or linked to their deleghe
            roles = get_user_delegation_roles(user)

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
