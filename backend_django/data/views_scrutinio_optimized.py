"""
Optimized scrutinio views with preload pattern and optimistic locking.

These views implement:
1. Lightweight preload of all sections for an RDL (miei-seggi-light)
2. On-demand detail fetch (sezione-detail)
3. Optimistic locking for concurrent updates (sezione-save)
"""
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.db.models import Q, Count, Case, When, F
from django.utils import timezone

from core.permissions import HasScrutinioAccess
from .models import DatiSezione, DatiScheda, SectionAssignment
from elections.models import ConsultazioneElettorale, SchedaElettorale
from territory.models import SezioneElettorale
from delegations.models import DesignazioneRDL
from delegations.permissions import get_sezioni_filter_for_user, get_user_delegation_roles


def get_consultazione_attiva():
    """Get the currently active consultation."""
    return ConsultazioneElettorale.objects.filter(is_attiva=True).first()


class ScrutinioMieiSeggiLightView(APIView):
    """
    Lightweight preload of sections for the authenticated RDL.

    GET /api/scrutinio/miei-seggi-light?consultazione_id=1

    Returns minimal data for quick loading:
    - section ID and basic info (comune, numero, indirizzo)
    - progresso percentuale (calculated real-time)
    - ultimo aggiornamento timestamp

    Response cached on frontend with version key.

    Permission: has_scrutinio_access (RDL, Delegato, SubDelegato)
    """
    permission_classes = [permissions.IsAuthenticated, HasScrutinioAccess]

    def get(self, request):
        consultazione_id = request.query_params.get('consultazione_id')
        if consultazione_id:
            try:
                consultazione = ConsultazioneElettorale.objects.get(id=consultazione_id)
            except ConsultazioneElettorale.DoesNotExist:
                return Response({'error': 'Consultazione non trovata'}, status=404)
        else:
            consultazione = get_consultazione_attiva()

        if not consultazione:
            return Response({
                'version': None,
                'consultazione_id': None,
                'seggi': [],
                'total': 0
            })

        # Get user's accessible sections (same logic as ScrutinioSezioniView)
        my_sezioni_ids = set()
        territory_sezioni_ids = set()

        # 1. RDL: sections from DesignazioneRDL (confirmed designations)
        designazioni = DesignazioneRDL.objects.filter(
            Q(effettivo_email=request.user.email) | Q(supplente_email=request.user.email),
            is_attiva=True,
            stato='CONFERMATA',
        ).filter(
            Q(delegato__consultazione=consultazione) |
            Q(sub_delega__delegato__consultazione=consultazione)
        ).values_list('sezione_id', flat=True)
        my_sezioni_ids.update(designazioni)

        # 2. Delegato/SubDelegato: sections from their territory (solo mappate)
        roles = get_user_delegation_roles(request.user, consultazione.id)
        if roles['is_delegato'] or roles['is_sub_delegato']:
            sezioni_filter = get_sezioni_filter_for_user(request.user, consultazione.id)
            if sezioni_filter is not None and sezioni_filter != Q():
                # Solo sezioni mappate (con almeno un SectionAssignment)
                mapped_sezioni_ids = set(SectionAssignment.objects.filter(
                    sezione__in=SezioneElettorale.objects.filter(
                        sezioni_filter, is_attiva=True
                    ),
                    consultazione=consultazione,
                ).values_list('sezione_id', flat=True).distinct())
                territory_sezioni_ids.update(mapped_sezioni_ids - my_sezioni_ids)

        sezioni_ids = my_sezioni_ids | territory_sezioni_ids

        if not sezioni_ids:
            return Response({
                'version': consultazione.data_version.isoformat() if consultazione.data_version else None,
                'consultazione_id': consultazione.id,
                'seggi': [],
                'total': 0
            })

        # Count total schede for this consultation (for progress calculation)
        total_schede = SchedaElettorale.objects.filter(
            tipo_elezione__consultazione=consultazione
        ).count()

        # Load sections with minimal data
        sezioni = SezioneElettorale.objects.filter(
            id__in=sezioni_ids
        ).select_related('comune', 'municipio').order_by('comune__nome', 'numero')

        # Get DatiSezione with progress calculation
        seggi_light = []
        for sezione in sezioni:
            # Get DatiSezione for progress calculation
            try:
                dati_sezione = DatiSezione.objects.get(
                    sezione=sezione,
                    consultazione=consultazione
                )

                # Calculate progress: count non-null fields in DatiScheda
                schede_complete = 0
                for dati_scheda in dati_sezione.schede.all():
                    # A scheda is complete if key fields are filled
                    if (dati_scheda.schede_ricevute is not None and
                        dati_scheda.schede_autenticate is not None and
                        dati_scheda.voti):
                        schede_complete += 1

                if total_schede > 0:
                    progresso = int((schede_complete / total_schede) * 100)
                else:
                    progresso = 0

                ultimo_aggiornamento = dati_sezione.updated_at
                is_completo = dati_sezione.is_complete

            except DatiSezione.DoesNotExist:
                progresso = 0
                ultimo_aggiornamento = None
                is_completo = False

            seggi_light.append({
                'sezione_id': sezione.id,
                'comune': sezione.comune.nome,
                'numero_sezione': sezione.numero,
                'denominazione': sezione.denominazione or '',
                'indirizzo': sezione.indirizzo or '',
                'progresso_percentuale': progresso,
                'is_completo': is_completo,
                'ultimo_aggiornamento': ultimo_aggiornamento.isoformat() if ultimo_aggiornamento else None
            })

        return Response({
            'version': consultazione.data_version.isoformat() if consultazione.data_version else None,
            'consultazione_id': consultazione.id,
            'seggi': seggi_light,
            'total': len(seggi_light)
        })


class ScrutinioSezioneDetailView(APIView):
    """
    Get detailed data for a specific section (real-time, no cache).

    GET /api/scrutinio/sezioni/{sezione_id}?consultazione_id=1

    Returns full DatiSezione + all DatiScheda with version for optimistic locking.

    Permission: has_scrutinio_access (RDL, Delegato, SubDelegato)
    """
    permission_classes = [permissions.IsAuthenticated, HasScrutinioAccess]

    def get(self, request, sezione_id):
        consultazione_id = request.query_params.get('consultazione_id')
        if consultazione_id:
            try:
                consultazione = ConsultazioneElettorale.objects.get(id=consultazione_id)
            except ConsultazioneElettorale.DoesNotExist:
                return Response({'error': 'Consultazione non trovata'}, status=404)
        else:
            consultazione = get_consultazione_attiva()

        if not consultazione:
            return Response({'error': 'Nessuna consultazione attiva'}, status=404)

        # Verify user has access to this section
        try:
            sezione = SezioneElettorale.objects.get(id=sezione_id)
        except SezioneElettorale.DoesNotExist:
            return Response({'error': 'Sezione non trovata'}, status=404)

        # Check permission (same logic as other scrutinio views)
        my_sezioni_ids = set()
        designazioni = DesignazioneRDL.objects.filter(
            Q(effettivo_email=request.user.email) | Q(supplente_email=request.user.email),
            is_attiva=True,
            stato='CONFERMATA',
        ).filter(
            Q(delegato__consultazione=consultazione) |
            Q(sub_delega__delegato__consultazione=consultazione)
        ).values_list('sezione_id', flat=True)
        my_sezioni_ids.update(designazioni)

        roles = get_user_delegation_roles(request.user, consultazione.id)
        if roles['is_delegato'] or roles['is_sub_delegato']:
            sezioni_filter = get_sezioni_filter_for_user(request.user, consultazione.id)
            if sezioni_filter is not None and sezioni_filter != Q():
                has_territory_access = SezioneElettorale.objects.filter(
                    sezioni_filter,
                    id=sezione_id
                ).exists()
                if has_territory_access:
                    my_sezioni_ids.add(sezione_id)

        if sezione_id not in my_sezioni_ids:
            return Response({'error': 'Non hai accesso a questa sezione'}, status=403)

        # Get or create DatiSezione
        dati_sezione, created = DatiSezione.objects.get_or_create(
            sezione=sezione,
            consultazione=consultazione,
            defaults={
                'inserito_da_email': request.user.email,
                'inserito_at': timezone.now()
            }
        )

        # Get all schede for this consultation
        schede = SchedaElettorale.objects.filter(
            tipo_elezione__consultazione=consultazione
        ).order_by('ordine')

        # Build schede data
        schede_data = []
        for scheda in schede:
            dati_scheda, _ = DatiScheda.objects.get_or_create(
                dati_sezione=dati_sezione,
                scheda=scheda
            )

            schede_data.append({
                'scheda_id': scheda.id,
                'scheda_nome': scheda.nome,
                'scheda_colore': scheda.colore,
                'version': dati_scheda.version,
                'schede_ricevute': dati_scheda.schede_ricevute,
                'schede_autenticate': dati_scheda.schede_autenticate,
                'schede_bianche': dati_scheda.schede_bianche,
                'schede_nulle': dati_scheda.schede_nulle,
                'schede_contestate': dati_scheda.schede_contestate,
                'voti': dati_scheda.voti or {},
                'updated_at': dati_scheda.updated_at.isoformat() if dati_scheda.updated_at else None,
                'updated_by_email': dati_scheda.updated_by_email
            })

        return Response({
            'sezione_id': sezione.id,
            'sezione': {
                'comune': sezione.comune.nome,
                'numero': sezione.numero,
                'denominazione': sezione.denominazione,
                'indirizzo': sezione.indirizzo
            },
            'version': dati_sezione.version,
            'dati_seggio': {
                'elettori_maschi': dati_sezione.elettori_maschi,
                'elettori_femmine': dati_sezione.elettori_femmine,
                'votanti_maschi': dati_sezione.votanti_maschi,
                'votanti_femmine': dati_sezione.votanti_femmine,
                'is_complete': dati_sezione.is_complete,
                'is_verified': dati_sezione.is_verified
            },
            'schede': schede_data,
            'ultimo_aggiornamento': dati_sezione.updated_at.isoformat() if dati_sezione.updated_at else None,
            'updated_by_email': dati_sezione.updated_by_email
        })


class ScrutinioSezioneSaveView(APIView):
    """
    Save section data with optimistic locking.

    POST /api/scrutinio/sezioni/{sezione_id}/save
    Body:
    {
        "consultazione_id": 1,
        "version": 5,
        "dati_seggio": {...},
        "schede": [...]
    }

    Returns 200 with new version on success, 409 on conflict.

    Permission: has_scrutinio_access (RDL, Delegato, SubDelegato)
    """
    permission_classes = [permissions.IsAuthenticated, HasScrutinioAccess]

    def post(self, request, sezione_id):
        consultazione_id = request.data.get('consultazione_id')
        expected_version = request.data.get('version')
        dati_seggio = request.data.get('dati_seggio', {})
        schede_data = request.data.get('schede', [])

        if not consultazione_id:
            return Response({'error': 'consultazione_id richiesto'}, status=400)

        if expected_version is None:
            return Response({'error': 'version richiesto per optimistic locking'}, status=400)

        try:
            consultazione = ConsultazioneElettorale.objects.get(id=consultazione_id)
        except ConsultazioneElettorale.DoesNotExist:
            return Response({'error': 'Consultazione non trovata'}, status=404)

        try:
            sezione = SezioneElettorale.objects.get(id=sezione_id)
        except SezioneElettorale.DoesNotExist:
            return Response({'error': 'Sezione non trovata'}, status=404)

        # Verify access (same as detail view)
        my_sezioni_ids = set()
        designazioni = DesignazioneRDL.objects.filter(
            Q(effettivo_email=request.user.email) | Q(supplente_email=request.user.email),
            is_attiva=True,
            stato='CONFERMATA',
        ).filter(
            Q(delegato__consultazione=consultazione) |
            Q(sub_delega__delegato__consultazione=consultazione)
        ).values_list('sezione_id', flat=True)
        my_sezioni_ids.update(designazioni)

        roles = get_user_delegation_roles(request.user, consultazione.id)
        if roles['is_delegato'] or roles['is_sub_delegato']:
            sezioni_filter = get_sezioni_filter_for_user(request.user, consultazione.id)
            if sezioni_filter is not None and sezioni_filter != Q():
                has_territory_access = SezioneElettorale.objects.filter(
                    sezioni_filter,
                    id=sezione_id
                ).exists()
                if has_territory_access:
                    my_sezioni_ids.add(sezione_id)

        if sezione_id not in my_sezioni_ids:
            return Response({'error': 'Non hai accesso a questa sezione'}, status=403)

        # Optimistic locking transaction
        try:
            with transaction.atomic():
                # Lock DatiSezione for update
                dati_sezione = DatiSezione.objects.select_for_update().get(
                    sezione=sezione,
                    consultazione=consultazione
                )

                # Check version
                if dati_sezione.version != expected_version:
                    return Response({
                        'error': 'conflict',
                        'message': f'I dati sono stati modificati da un altro utente ({dati_sezione.updated_by_email}). Ricarica la pagina.',
                        'current_version': dati_sezione.version,
                        'updated_by': dati_sezione.updated_by_email,
                        'updated_at': dati_sezione.updated_at.isoformat()
                    }, status=409)

                # Update DatiSezione
                dati_sezione.elettori_maschi = dati_seggio.get('elettori_maschi')
                dati_sezione.elettori_femmine = dati_seggio.get('elettori_femmine')
                dati_sezione.votanti_maschi = dati_seggio.get('votanti_maschi')
                dati_sezione.votanti_femmine = dati_seggio.get('votanti_femmine')
                dati_sezione.is_complete = dati_seggio.get('is_complete', False)
                dati_sezione.version = F('version') + 1
                dati_sezione.updated_by_email = request.user.email
                dati_sezione.save()
                dati_sezione.refresh_from_db()  # Get new version value

                # Update DatiScheda
                for scheda_data in schede_data:
                    scheda_id = scheda_data.get('scheda_id')
                    if not scheda_id:
                        continue

                    try:
                        dati_scheda = DatiScheda.objects.select_for_update().get(
                            dati_sezione=dati_sezione,
                            scheda_id=scheda_id
                        )

                        # Update fields
                        dati_scheda.schede_ricevute = scheda_data.get('schede_ricevute')
                        dati_scheda.schede_autenticate = scheda_data.get('schede_autenticate')
                        dati_scheda.schede_bianche = scheda_data.get('schede_bianche')
                        dati_scheda.schede_nulle = scheda_data.get('schede_nulle')
                        dati_scheda.schede_contestate = scheda_data.get('schede_contestate')
                        dati_scheda.voti = scheda_data.get('voti', {})
                        dati_scheda.version = F('version') + 1
                        dati_scheda.updated_by_email = request.user.email
                        dati_scheda.save()

                    except DatiScheda.DoesNotExist:
                        # Should not happen if properly created
                        continue

                # Invalidate cache: touch ConsultazioneElettorale.data_version
                ConsultazioneElettorale.objects.filter(id=consultazione.id).update(
                    data_version=timezone.now()
                )

                return Response({
                    'success': True,
                    'new_version': dati_sezione.version,
                    'message': 'Dati salvati con successo'
                })

        except DatiSezione.DoesNotExist:
            return Response({'error': 'DatiSezione non trovato'}, status=404)
        except Exception as e:
            return Response({
                'error': 'Errore durante il salvataggio',
                'detail': str(e)
            }, status=500)
