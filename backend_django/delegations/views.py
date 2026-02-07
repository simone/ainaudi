"""
Views for delegations API endpoints.

Gerarchia: PARTITO -> DELEGATO DI LISTA -> SUB-DELEGATO -> RDL
"""
from rest_framework import viewsets, views, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from core.permissions import CanManageDelegations, CanGenerateDocuments
from elections.models import ConsultazioneElettorale
from territory.models import SezioneElettorale
from .models import Delegato, SubDelega, DesignazioneRDL, BatchGenerazioneDocumenti
from .serializers import (
    DelegatoSerializer,
    SubDelegaSerializer, SubDelegaCreateSerializer,
    DesignazioneRDLSerializer, DesignazioneRDLCreateSerializer, DesignazioneRDLListSerializer,
    BatchGenerazioneDocumentiSerializer,
    MiaCatenaSerializer, SezioneDisponibileSerializer,
    RdlRegistrationForMappatura,
    ConfermaDesignazioneSerializer, RifiutaDesignazioneSerializer,
)


class MiaCatenaView(views.APIView):
    """
    GET /api/deleghe/mia-catena/

    Restituisce la catena deleghe dell'utente loggato:
    - Se e' Delegato di Lista
    - Se e' Sub-Delegato (e da chi)
    - Le sub-deleghe che ha fatto (se Delegato)
    - Le designazioni RDL che ha fatto (se Sub-Delegato)
    - Le designazioni RDL che ha ricevuto (se RDL)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        consultazione_id = request.query_params.get('consultazione')
        consultazione = None

        if consultazione_id:
            try:
                consultazione = ConsultazioneElettorale.objects.get(id=consultazione_id)
            except ConsultazioneElettorale.DoesNotExist:
                pass

        result = {
            'is_delegato': False,
            'is_sub_delegato': False,
            'is_rdl': False,
            'deleghe_lista': [],
            'sub_deleghe_ricevute': [],
            'sub_deleghe_fatte': [],
            'designazioni_fatte': [],
            'designazioni_ricevute': [],
        }

        # Delegato di Lista?
        deleghe_lista = Delegato.objects.filter(email=user.email)
        if consultazione:
            deleghe_lista = deleghe_lista.filter(consultazione=consultazione)
        if deleghe_lista.exists():
            result['is_delegato'] = True
            result['deleghe_lista'] = DelegatoSerializer(deleghe_lista, many=True).data
            # Sub-deleghe fatte come Delegato
            for dl in deleghe_lista:
                sub_deleghe = dl.sub_deleghe.filter(is_attiva=True)
                result['sub_deleghe_fatte'].extend(
                    SubDelegaSerializer(sub_deleghe, many=True).data
                )
                # Designazioni fatte DIRETTAMENTE come Delegato (senza sub-delega)
                designazioni_dirette = dl.designazioni_rdl_dirette.filter(is_attiva=True)
                result['designazioni_fatte'].extend(
                    DesignazioneRDLListSerializer(designazioni_dirette, many=True).data
                )

        # Sub-Delegato?
        sub_deleghe = SubDelega.objects.filter(email=user.email, is_attiva=True)
        if consultazione:
            sub_deleghe = sub_deleghe.filter(delegato__consultazione=consultazione)
        if sub_deleghe.exists():
            result['is_sub_delegato'] = True
            result['sub_deleghe_ricevute'] = SubDelegaSerializer(sub_deleghe, many=True).data
            # Designazioni fatte come Sub-Delegato
            for sd in sub_deleghe:
                designazioni = sd.designazioni_rdl.filter(is_attiva=True)
                result['designazioni_fatte'].extend(
                    DesignazioneRDLListSerializer(designazioni, many=True).data
                )

        # RDL?
        designazioni_ricevute = DesignazioneRDL.objects.filter(
            Q(effettivo_email=user.email) | Q(supplente_email=user.email),
            is_attiva=True
        )
        if consultazione:
            designazioni_ricevute = designazioni_ricevute.filter(
                sub_delega__delegato__consultazione=consultazione
            )
        if designazioni_ricevute.exists():
            result['is_rdl'] = True
            result['designazioni_ricevute'] = DesignazioneRDLSerializer(
                designazioni_ricevute, many=True
            ).data

        return Response(result)


class SubDelegaViewSet(viewsets.ModelViewSet):
    """
    ViewSet per le Sub-Deleghe.

    GET /api/deleghe/sub-deleghe/ - Lista sub-deleghe (filtrate per consultazione)
    GET /api/deleghe/sub-deleghe/{id}/ - Dettaglio sub-delega
    POST /api/deleghe/sub-deleghe/ - Crea sub-delega (solo Delegato)
    DELETE /api/deleghe/sub-deleghe/{id}/ - Revoca sub-delega

    Permission: can_manage_delegations (Delegato, SubDelegato)
    """
    permission_classes = [permissions.IsAuthenticated, CanManageDelegations]

    def get_serializer_class(self):
        if self.action == 'create':
            return SubDelegaCreateSerializer
        return SubDelegaSerializer

    def get_queryset(self):
        from elections.models import ConsultazioneElettorale

        user = self.request.user
        consultazione_id = self.request.query_params.get('consultazione')

        # Check if consultazione supports sub-delegations
        if consultazione_id:
            try:
                consultazione = ConsultazioneElettorale.objects.get(id=consultazione_id)
                if not consultazione.has_subdelegations():
                    # Referendum-only consultation: no sub-delegations
                    return SubDelega.objects.none()
            except ConsultazioneElettorale.DoesNotExist:
                return SubDelega.objects.none()

        # Un utente vede:
        # 1. Le sub-deleghe che ha ricevuto (email)
        # 2. Le sub-deleghe che ha creato (created_by_email)
        # 3. Le sub-deleghe del delegato associato alla sua email
        qs = SubDelega.objects.filter(
            Q(email=user.email) | Q(delegato__email=user.email) | Q(created_by_email=user.email)
        ).select_related('delegato', 'delegato__consultazione')

        if consultazione_id:
            qs = qs.filter(delegato__consultazione_id=consultazione_id)

        return qs.distinct()

    def perform_create(self, serializer):
        from elections.models import ConsultazioneElettorale

        # Check if consultazione supports sub-delegations
        delegato = serializer.validated_data.get('delegato')
        if delegato and delegato.consultazione:
            if not delegato.consultazione.has_subdelegations():
                from rest_framework.exceptions import ValidationError
                raise ValidationError({
                    'error': 'Sub-deleghe non disponibili per referendum'
                })

        serializer.save(created_by_email=self.request.user.email)

    def destroy(self, request, *args, **kwargs):
        """Revoca invece di cancellare."""
        instance = self.get_object()

        # Verifica che l'utente possa revocare
        if instance.delegato.email != request.user.email and instance.created_by != request.user:
            return Response(
                {'error': 'Non hai i permessi per revocare questa sub-delega'},
                status=status.HTTP_403_FORBIDDEN
            )

        from django.utils import timezone
        instance.is_attiva = False
        instance.revocata_il = timezone.now().date()
        instance.motivo_revoca = request.data.get('motivo', 'Revocata dall\'utente')
        instance.save()

        return Response(status=status.HTTP_204_NO_CONTENT)


class DesignazioneRDLViewSet(viewsets.ModelViewSet):
    """
    ViewSet per le Designazioni RDL.

    GET /api/deleghe/designazioni/ - Lista designazioni (filtrate per consultazione)
    GET /api/deleghe/designazioni/{id}/ - Dettaglio designazione
    POST /api/deleghe/designazioni/ - Crea designazione (solo Sub-Delegato)
    DELETE /api/deleghe/designazioni/{id}/ - Revoca designazione
    GET /api/deleghe/designazioni/sezioni_disponibili/ - Sezioni disponibili per designazione

    Permission: can_manage_delegations (Delegato, SubDelegato)
    """
    permission_classes = [permissions.IsAuthenticated, CanManageDelegations]

    def get_serializer_class(self):
        if self.action == 'create':
            return DesignazioneRDLCreateSerializer
        if self.action == 'list':
            return DesignazioneRDLListSerializer
        return DesignazioneRDLSerializer

    def get_queryset(self):
        user = self.request.user
        consultazione_id = self.request.query_params.get('consultazione')

        # Un utente vede:
        # 1. Le designazioni che ha ricevuto (come RDL)
        # 2. Le designazioni che ha fatto (come Sub-Delegato)
        # 3. Le designazioni che ha fatto direttamente (come Delegato)
        # 4. Le designazioni fatte dai suoi Sub-Delegati (come Delegato)
        qs = DesignazioneRDL.objects.filter(
            Q(email=user.email) |
            Q(sub_delega__email=user.email) |
            Q(delegato__email=user.email) |
            Q(sub_delega__delegato__email=user.email)  # Delegato vede bozze dei suoi sub
        ).select_related(
            'delegato', 'sub_delega', 'sub_delega__delegato',
            'sezione', 'sezione__comune', 'sezione__municipio'
        )

        if consultazione_id:
            qs = qs.filter(
                Q(delegato__consultazione_id=consultazione_id) |
                Q(sub_delega__delegato__consultazione_id=consultazione_id)
            )

        return qs.distinct()

    def destroy(self, request, *args, **kwargs):
        """Revoca invece di cancellare."""
        instance = self.get_object()

        # Verifica che l'utente possa revocare (delegato o sub-delegato)
        can_revoke = False
        if instance.delegato and instance.delegato.email == request.user.email:
            can_revoke = True
        if instance.sub_delega and instance.sub_delega.email == request.user.email:
            can_revoke = True

        if not can_revoke:
            return Response(
                {'error': 'Non hai i permessi per revocare questa designazione'},
                status=status.HTTP_403_FORBIDDEN
            )

        from django.utils import timezone
        instance.is_attiva = False
        instance.revocata_il = timezone.now().date()
        instance.motivo_revoca = request.data.get('motivo', 'Revocata dall\'utente')
        instance.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def sezioni_disponibili(self, request):
        """
        GET /api/deleghe/designazioni/sezioni_disponibili/

        Restituisce le sezioni disponibili per la designazione RDL.
        Filtrate in base al territorio di competenza del Sub-Delegato.
        """
        user = request.user
        consultazione_id = request.query_params.get('consultazione')

        # Trova le sub-deleghe dell'utente
        sub_deleghe = SubDelega.objects.filter(email=user.email, is_attiva=True)
        if consultazione_id:
            sub_deleghe = sub_deleghe.filter(delegato__consultazione_id=consultazione_id)

        if not sub_deleghe.exists():
            return Response([])

        # Raccogli tutti i comuni e municipi di competenza
        comuni_ids = set()
        municipi = set()
        for sd in sub_deleghe:
            comuni_ids.update(sd.comuni.values_list('id', flat=True))
            if sd.municipi and isinstance(sd.municipi, list):
                municipi.update(sd.municipi)

        # Filtra le sezioni
        sezioni = SezioneElettorale.objects.filter(
            Q(comune_id__in=comuni_ids) | Q(municipio__in=list(municipi))
        ).select_related('comune')

        # Per ogni sezione, verifica se ha gia' effettivo/supplente
        result = []
        for sez in sezioni:
            designazione = DesignazioneRDL.objects.filter(
                sezione=sez,
                is_attiva=True,
                stato='CONFERMATA'
            ).first()

            ha_effettivo = False
            ha_supplente = False
            if designazione:
                ha_effettivo = bool(designazione.effettivo_email)
                ha_supplente = bool(designazione.supplente_email)

            result.append({
                'id': sez.id,
                'numero': sez.numero,
                'comune_nome': sez.comune.nome,
                'municipio': sez.municipio.numero if sez.municipio else None,
                'indirizzo': sez.indirizzo or '',
                'ha_effettivo': ha_effettivo,
                'ha_supplente': ha_supplente,
            })

        return Response(SezioneDisponibileSerializer(result, many=True).data)

    @action(detail=False, methods=['get'])
    def rdl_disponibili(self, request):
        """
        GET /api/deleghe/designazioni/rdl_disponibili/

        Restituisce gli RDL approvati disponibili per la mappatura.
        Filtrati in base al territorio di competenza dell'utente.
        """
        from campaign.models import RdlRegistration

        user = request.user
        comune_id = request.query_params.get('comune')
        municipio_id = request.query_params.get('municipio')

        # Trova il territorio di competenza dell'utente
        sub_deleghe = SubDelega.objects.filter(email=user.email, is_attiva=True)
        delegati = Delegato.objects.filter(email=user.email)

        comuni_ids = set()
        municipi_ids = set()

        for sd in sub_deleghe:
            comuni_ids.update(sd.comuni.values_list('id', flat=True))
            if sd.municipi and isinstance(sd.municipi, list):
                municipi_ids.update(sd.municipi)

        # Se è delegato, vede tutto il suo territorio (circoscrizione)
        # Per ora permettiamo a delegati di vedere tutti gli RDL
        is_delegato = delegati.exists()

        # Filtra gli RDL approvati
        qs = RdlRegistration.objects.filter(status='APPROVED').select_related('comune', 'municipio')

        if not is_delegato:
            # Sub-delegato: filtra per territorio di competenza
            if comuni_ids or municipi_ids:
                qs = qs.filter(
                    Q(comune_id__in=comuni_ids) | Q(municipio_id__in=municipi_ids)
                )
            else:
                return Response([])

        # Filtri aggiuntivi
        if comune_id:
            qs = qs.filter(comune_id=comune_id)
        if municipio_id:
            qs = qs.filter(municipio_id=municipio_id)

        # Per ogni RDL, aggiungi info sulle designazioni esistenti
        result = []
        for reg in qs:
            # Cerca designazioni esistenti per questo RDL (per email)
            designazione_effettivo = DesignazioneRDL.objects.filter(
                effettivo_email=reg.email,
                is_attiva=True
            ).exclude(stato='REVOCATA').first()

            designazione_supplente = DesignazioneRDL.objects.filter(
                supplente_email=reg.email,
                is_attiva=True
            ).exclude(stato='REVOCATA').first()

            result.append({
                'id': reg.id,
                'nome': reg.nome,
                'cognome': reg.cognome,
                'email': reg.email,
                'telefono': reg.telefono,
                'comune_nascita': reg.comune_nascita,
                'data_nascita': reg.data_nascita,
                'comune_residenza': reg.comune_residenza,
                'indirizzo_residenza': reg.indirizzo_residenza,
                'comune': {'id': reg.comune.id, 'nome': reg.comune.nome},
                'municipio': {'id': reg.municipio.id, 'nome': reg.municipio.nome} if reg.municipio else None,
                'seggio_preferenza': reg.seggio_preferenza,
                'designazione_effettivo_id': designazione_effettivo.id if designazione_effettivo else None,
                'designazione_supplente_id': designazione_supplente.id if designazione_supplente else None,
            })

        return Response(result)

    # mappatura endpoint removed - use carica_mappatura instead

    @action(detail=False, methods=['post'])
    def carica_mappatura(self, request):
        """
        POST /api/delegations/designazioni/carica_mappatura/

        "Fotografa" tutte le assegnazioni (SectionAssignment) nel territorio del delegato
        e crea le designazioni formali (DesignazioneRDL) corrispondenti.

        NUOVO COMPORTAMENTO (1 record per seggio):
        - Raggruppa SectionAssignment per sezione (effettivo + supplente)
        - Crea 1 DesignazioneRDL per seggio con entrambi i ruoli
        - BOZZE: Sovrascritte sempre
        - CONFERMATE: Skippa se identiche, segnala se discrepanza

        Ritorna: { created: N, updated: N, skipped: N, warnings: [], errors: [], total: N }
        """
        from data.models import SectionAssignment

        user = request.user
        consultazione_id = request.data.get('consultazione_id')

        if not consultazione_id:
            return Response({'error': 'consultazione_id obbligatorio'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            consultazione = ConsultazioneElettorale.objects.get(id=consultazione_id)
        except ConsultazioneElettorale.DoesNotExist:
            return Response({'error': 'Consultazione non trovata'}, status=status.HTTP_404_NOT_FOUND)

        # Usa lo stesso sistema di permessi della gestione sezioni
        from .permissions import get_sezioni_filter_for_user, get_user_delegation_roles

        sezioni_filter = get_sezioni_filter_for_user(user, consultazione_id)

        if sezioni_filter is None:
            return Response({
                'error': 'Nessun territorio di competenza trovato per questo utente'
            }, status=status.HTTP_403_FORBIDDEN)

        # Ottieni le sezioni visibili
        sezioni_visibili = SezioneElettorale.objects.filter(
            sezioni_filter,
            is_attiva=True
        )
        sezioni_ids = set(sezioni_visibili.values_list('id', flat=True))

        if not sezioni_ids:
            return Response({
                'error': 'Nessuna sezione trovata nel tuo territorio di competenza'
            }, status=status.HTTP_403_FORBIDDEN)

        # Ottieni ruoli per trovare sub-deleghe e delegati
        roles = get_user_delegation_roles(user, consultazione_id)
        sub_deleghe = roles['sub_deleghe'].prefetch_related('regioni', 'province', 'comuni')
        delegati = roles['deleghe_lista'].prefetch_related('regioni', 'province', 'comuni')

        # Prendi tutte le SectionAssignment nel territorio
        assignments = SectionAssignment.objects.filter(
            sezione_id__in=sezioni_ids,
            consultazione=consultazione
        ).select_related('rdl_registration', 'sezione', 'sezione__comune', 'sezione__comune__provincia', 'sezione__comune__provincia__regione', 'sezione__municipio')

        # NUOVO: Raggruppa per sezione: {sezione_id: {'effettivo': rdl, 'supplente': rdl}}
        sezioni_map = {}
        for assignment in assignments:
            if not assignment.rdl_registration:
                continue

            sezione_id = assignment.sezione_id
            if sezione_id not in sezioni_map:
                sezioni_map[sezione_id] = {
                    'sezione': assignment.sezione,
                    'effettivo': None,
                    'supplente': None
                }

            if assignment.role == 'RDL':
                sezioni_map[sezione_id]['effettivo'] = assignment.rdl_registration
            elif assignment.role == 'SUPPLENTE':
                sezioni_map[sezione_id]['supplente'] = assignment.rdl_registration

        created = 0
        updated = 0
        skipped = 0
        warnings = []
        errors = []

        # Helper function per verificare se una sezione matcha una sub-delega
        def sezione_matches_subdelega(sezione, sd):
            """Verifica se una sezione è coperta da una sub-delega usando la stessa logica di get_sezioni_filter_for_user"""
            # Check regioni
            regioni_ids = list(sd.regioni.values_list('id', flat=True))
            if regioni_ids:
                if sezione.comune and sezione.comune.provincia and sezione.comune.provincia.regione_id in regioni_ids:
                    return True

            # Check province
            province_ids = list(sd.province.values_list('id', flat=True))
            if province_ids:
                if sezione.comune and sezione.comune.provincia_id in province_ids:
                    return True

            # Check comuni + municipi (con logica AND/OR corretta)
            comuni_ids = list(sd.comuni.values_list('id', flat=True))
            municipi_nums = sd.municipi

            if comuni_ids and municipi_nums:
                # Comuni E municipi: solo quei municipi di quei comuni
                if sezione.comune_id in comuni_ids and sezione.municipio and sezione.municipio.numero in municipi_nums:
                    return True
            elif comuni_ids:
                # Solo comuni: tutte le sezioni di quei comuni
                if sezione.comune_id in comuni_ids:
                    return True
            elif municipi_nums:
                # Solo municipi: tutte le sezioni in quei municipi
                if sezione.municipio and sezione.municipio.numero in municipi_nums:
                    return True

            return False

        # Helper function per verificare se una sezione matcha un delegato
        def sezione_matches_delegato(sezione, delegato):
            """Verifica se una sezione è coperta da un delegato"""
            # Check regioni
            regioni_ids = list(delegato.regioni.values_list('id', flat=True))
            if regioni_ids:
                if sezione.comune and sezione.comune.provincia and sezione.comune.provincia.regione_id in regioni_ids:
                    return True

            # Check province
            province_ids = list(delegato.province.values_list('id', flat=True))
            if province_ids:
                if sezione.comune and sezione.comune.provincia_id in province_ids:
                    return True

            # Check comuni + municipi
            comuni_ids = list(delegato.comuni.values_list('id', flat=True))
            municipi_nums = delegato.municipi

            if comuni_ids and municipi_nums:
                if sezione.comune_id in comuni_ids and sezione.municipio and sezione.municipio.numero in municipi_nums:
                    return True
            elif comuni_ids:
                if sezione.comune_id in comuni_ids:
                    return True
            elif municipi_nums:
                if sezione.municipio and sezione.municipio.numero in municipi_nums:
                    return True

            return False

        for sezione_id, data in sezioni_map.items():
            sezione = data['sezione']
            effettivo = data['effettivo']
            supplente = data['supplente']

            if not effettivo and not supplente:
                continue  # Nessun RDL da importare

            try:
                # Trova sub-delega o delegato appropriato
                sub_delega = None
                delegato_diretto = None

                for sd in sub_deleghe:
                    if sezione_matches_subdelega(sezione, sd):
                        sub_delega = sd
                        break

                if not sub_delega:
                    for delegato in delegati:
                        if sezione_matches_delegato(sezione, delegato):
                            delegato_diretto = delegato
                            break

                if not sub_delega and not delegato_diretto:
                    errors.append(f'Sezione {sezione}: nessuna delega trovata')
                    continue

                # Controlla se esiste già una designazione per questa sezione
                existing = DesignazioneRDL.objects.filter(
                    sezione=sezione,
                    is_attiva=True
                ).first()

                if existing:
                    if existing.stato == 'CONFERMATA':
                        # Verifica se identica (confronta per email)
                        effettivo_match = (not effettivo and not existing.effettivo_email) or \
                                         (effettivo and existing.effettivo_email == effettivo.email)
                        supplente_match = (not supplente and not existing.supplente_email) or \
                                         (supplente and existing.supplente_email == supplente.email)

                        if effettivo_match and supplente_match:
                            skipped += 1
                            continue
                        else:
                            # Discrepanza
                            warnings.append(
                                f'Sezione {sezione}: designazione confermata diversa dalla mappatura attuale. '
                                f'Cancella manualmente per re-importare.'
                            )
                            skipped += 1
                            continue
                    else:
                        # BOZZA: sovrascrivi copiando i dati
                        if effettivo:
                            existing.effettivo_cognome = effettivo.cognome
                            existing.effettivo_nome = effettivo.nome
                            existing.effettivo_email = effettivo.email
                            existing.effettivo_telefono = effettivo.telefono or ''
                            existing.effettivo_luogo_nascita = effettivo.comune_nascita or ''
                            existing.effettivo_data_nascita = effettivo.data_nascita
                            existing.effettivo_domicilio = f"{effettivo.indirizzo_residenza}, {effettivo.comune_residenza}"
                        else:
                            # Cancella effettivo
                            existing.effettivo_cognome = ''
                            existing.effettivo_nome = ''
                            existing.effettivo_email = ''
                            existing.effettivo_telefono = ''
                            existing.effettivo_luogo_nascita = ''
                            existing.effettivo_data_nascita = None
                            existing.effettivo_domicilio = ''

                        if supplente:
                            existing.supplente_cognome = supplente.cognome
                            existing.supplente_nome = supplente.nome
                            existing.supplente_email = supplente.email
                            existing.supplente_telefono = supplente.telefono or ''
                            existing.supplente_luogo_nascita = supplente.comune_nascita or ''
                            existing.supplente_data_nascita = supplente.data_nascita
                            existing.supplente_domicilio = f"{supplente.indirizzo_residenza}, {supplente.comune_residenza}"
                        else:
                            # Cancella supplente
                            existing.supplente_cognome = ''
                            existing.supplente_nome = ''
                            existing.supplente_email = ''
                            existing.supplente_telefono = ''
                            existing.supplente_luogo_nascita = ''
                            existing.supplente_data_nascita = None
                            existing.supplente_domicilio = ''

                        existing.sub_delega = sub_delega
                        existing.delegato = delegato_diretto
                        existing.save()
                        updated += 1
                        continue

                # Crea nuova designazione con snapshot dei dati
                # IMPORTANTE: carica_mappatura crea SEMPRE BOZZE
                # Le designazioni passano a CONFERMATA solo quando:
                # 1. Si genera e approva il batch PDF
                # 2. Un delegato/subdelegato con firma le conferma manualmente
                stato_iniziale = 'BOZZA'

                # Prepara dati designazione
                designazione_data = {
                    'sezione': sezione,
                    'sub_delega': sub_delega,
                    'delegato': delegato_diretto,
                    'stato': stato_iniziale,
                    'is_attiva': True,
                    'created_by_email': user.email
                }

                # Copia dati effettivo
                if effettivo:
                    designazione_data['effettivo_cognome'] = effettivo.cognome
                    designazione_data['effettivo_nome'] = effettivo.nome
                    designazione_data['effettivo_email'] = effettivo.email
                    designazione_data['effettivo_telefono'] = effettivo.telefono or ''
                    designazione_data['effettivo_luogo_nascita'] = effettivo.comune_nascita or ''
                    designazione_data['effettivo_data_nascita'] = effettivo.data_nascita
                    designazione_data['effettivo_domicilio'] = f"{effettivo.indirizzo_residenza}, {effettivo.comune_residenza}"

                # Copia dati supplente
                if supplente:
                    designazione_data['supplente_cognome'] = supplente.cognome
                    designazione_data['supplente_nome'] = supplente.nome
                    designazione_data['supplente_email'] = supplente.email
                    designazione_data['supplente_telefono'] = supplente.telefono or ''
                    designazione_data['supplente_luogo_nascita'] = supplente.comune_nascita or ''
                    designazione_data['supplente_data_nascita'] = supplente.data_nascita
                    designazione_data['supplente_domicilio'] = f"{supplente.indirizzo_residenza}, {supplente.comune_residenza}"

                DesignazioneRDL.objects.create(**designazione_data)
                created += 1

            except Exception as e:
                errors.append(f'Sezione {sezione}: {str(e)}')

        return Response({
            'created': created,
            'updated': updated,
            'skipped': skipped,
            'warnings': warnings,
            'errors': errors,
            'total': len(sezioni_map)
        })

    @action(detail=False, methods=['post'])
    def upload_csv(self, request):
        """
        POST /api/delegations/designazioni/upload_csv/

        Carica un CSV con le designazioni RDL -> Sezione.
        Formato CSV: SEZIONE,COMUNE,MUNICIPIO,EFFETTIVO_EMAIL,SUPPLENTE_EMAIL

        Ritorna: { created: N, updated: N, errors: [], total: N }
        """
        import csv
        import io

        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'Nessun file caricato'}, status=status.HTTP_400_BAD_REQUEST)

        # Leggi CSV
        try:
            decoded_file = file.read().decode('utf-8')
            csv_data = csv.DictReader(io.StringIO(decoded_file))
        except Exception as e:
            return Response({'error': f'Errore lettura CSV: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        created = 0
        updated = 0
        errors = []
        total = 0

        for row_num, row in enumerate(csv_data, start=2):  # Start from 2 (header is row 1)
            total += 1

            try:
                sezione_numero = row.get('SEZIONE', '').strip()
                comune_nome = row.get('COMUNE', '').strip().upper()
                municipio_num = row.get('MUNICIPIO', '').strip()
                effettivo_email = row.get('EFFETTIVO_EMAIL', '').strip().lower()
                supplente_email = row.get('SUPPLENTE_EMAIL', '').strip().lower()

                if not sezione_numero or not comune_nome:
                    errors.append(f'Riga {row_num}: SEZIONE e COMUNE obbligatori')
                    continue

                if not effettivo_email and not supplente_email:
                    errors.append(f'Riga {row_num}: Almeno un RDL (effettivo o supplente) obbligatorio')
                    continue

                # Trova sezione
                from territory.models import Comune, Municipio

                try:
                    comune = Comune.objects.get(nome__iexact=comune_nome)
                except Comune.DoesNotExist:
                    errors.append(f'Riga {row_num}: Comune {comune_nome} non trovato')
                    continue

                sezione_qs = SezioneElettorale.objects.filter(
                    numero=sezione_numero,
                    comune=comune
                )

                if municipio_num:
                    try:
                        municipio = Municipio.objects.get(numero=int(municipio_num), comune=comune)
                        sezione_qs = sezione_qs.filter(municipio=municipio)
                    except (Municipio.DoesNotExist, ValueError):
                        errors.append(f'Riga {row_num}: Municipio {municipio_num} non trovato per {comune_nome}')
                        continue

                sezione = sezione_qs.first()
                if not sezione:
                    errors.append(f'Riga {row_num}: Sezione {sezione_numero} non trovata in {comune_nome}')
                    continue

                # Crea designazioni
                for email, ruolo in [(effettivo_email, 'EFFETTIVO'), (supplente_email, 'SUPPLENTE')]:
                    if not email:
                        continue

                    # Usa la stessa logica di mappatura()
                    serializer = MappaturaCreaSerializer(
                        data={
                            'sezione_id': sezione.id,
                            'rdl_email': email,
                            'ruolo': ruolo
                        },
                        context={'request': request}
                    )

                    if serializer.is_valid():
                        serializer.save()
                        created += 1
                    else:
                        errors.append(f'Riga {row_num} ({ruolo}): {serializer.errors}')

            except Exception as e:
                errors.append(f'Riga {row_num}: Errore imprevisto: {str(e)}')

        return Response({
            'created': created,
            'updated': updated,
            'errors': errors,
            'total': total
        })

    @action(detail=False, methods=['get'])
    def bozze_da_confermare(self, request):
        """
        GET /api/deleghe/designazioni/bozze_da_confermare/

        Restituisce le designazioni in stato BOZZA nel territorio di competenza.
        Solo per utenti con firma autenticata (Delegati o Sub con firma).
        """
        user = request.user
        consultazione_id = request.query_params.get('consultazione')
        comune_id = request.query_params.get('comune')
        municipio_id = request.query_params.get('municipio')

        # Verifica che l'utente possa confermare (delegato o sub con firma)
        delegati = Delegato.objects.filter(email=user.email)
        sub_deleghe_firma = SubDelega.objects.filter(
            email=user.email,
            is_attiva=True,
            tipo_delega='FIRMA_AUTENTICATA'
        )

        if not delegati.exists() and not sub_deleghe_firma.exists():
            return Response(
                {'error': 'Non hai i permessi per confermare designazioni'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Raccogli il territorio di competenza
        comuni_ids = set()
        municipi = set()

        for sd in sub_deleghe_firma:
            comuni_ids.update(sd.comuni.values_list('id', flat=True))
            if sd.municipi and isinstance(sd.municipi, list):
                municipi.update(sd.municipi)

        # Se è delegato, vede le bozze create dalle sue sub-deleghe
        sub_deleghe_ids = set()
        for dl in delegati:
            sub_deleghe_ids.update(dl.sub_deleghe.filter(is_attiva=True).values_list('id', flat=True))
            if consultazione_id:
                # Filtra per consultazione
                pass

        # Query delle bozze
        qs = DesignazioneRDL.objects.filter(
            stato='BOZZA',
            is_attiva=True
        ).select_related(
            'sezione', 'sezione__comune', 'sub_delega', 'delegato'
        )

        # Filtra per territorio
        if comuni_ids or municipi:
            qs = qs.filter(
                Q(sezione__comune_id__in=comuni_ids) |
                Q(sezione__municipio__in=list(municipi))
            )

        # Filtra per sub-deleghe del delegato
        if sub_deleghe_ids:
            qs = qs.filter(sub_delega_id__in=sub_deleghe_ids) | qs

        # Filtri aggiuntivi
        if comune_id:
            qs = qs.filter(sezione__comune_id=comune_id)
        if municipio_id:
            qs = qs.filter(sezione__municipio=municipio_id)

        qs = qs.distinct()

        return Response(DesignazioneRDLListSerializer(qs, many=True).data)

    @action(detail=True, methods=['post'])
    def conferma(self, request, pk=None):
        """
        POST /api/deleghe/designazioni/{id}/conferma/

        Conferma una designazione in stato BOZZA.
        Solo per utenti con firma autenticata.
        """
        designazione = self.get_object()

        if designazione.stato != 'BOZZA':
            return Response(
                {'error': 'Solo le designazioni in BOZZA possono essere confermate'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verifica permessi (delegato o sub con firma nel territorio)
        user = request.user
        has_permission = False

        # È il delegato della catena?
        if designazione.sub_delega and designazione.sub_delega.delegato.email == user.email:
            has_permission = True

        # È un sub-delegato con firma nello stesso territorio?
        if not has_permission:
            sub_deleghe_firma = SubDelega.objects.filter(
                email=user.email,
                is_attiva=True,
                tipo_delega='FIRMA_AUTENTICATA'
            )
            for sd in sub_deleghe_firma:
                if designazione.sezione.comune in sd.comuni.all():
                    has_permission = True
                    break
                if sd.municipi and isinstance(sd.municipi, list) and designazione.sezione.municipio_id in sd.municipi:
                    has_permission = True
                    break

        if not has_permission:
            return Response(
                {'error': 'Non hai i permessi per confermare questa designazione'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Conferma
        designazione.approva(user)

        return Response(DesignazioneRDLSerializer(designazione).data)

    @action(detail=True, methods=['post'])
    def rifiuta(self, request, pk=None):
        """
        POST /api/deleghe/designazioni/{id}/rifiuta/

        Rifiuta (revoca) una designazione in stato BOZZA.
        """
        designazione = self.get_object()

        if designazione.stato != 'BOZZA':
            return Response(
                {'error': 'Solo le designazioni in BOZZA possono essere rifiutate'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verifica permessi (stessi di conferma)
        user = request.user
        has_permission = False

        if designazione.sub_delega and designazione.sub_delega.delegato.email == user.email:
            has_permission = True

        if not has_permission:
            sub_deleghe_firma = SubDelega.objects.filter(
                email=user.email,
                is_attiva=True,
                tipo_delega='FIRMA_AUTENTICATA'
            )
            for sd in sub_deleghe_firma:
                if designazione.sezione.comune in sd.comuni.all():
                    has_permission = True
                    break
                if sd.municipi and isinstance(sd.municipi, list) and designazione.sezione.municipio_id in sd.municipi:
                    has_permission = True
                    break

        if not has_permission:
            return Response(
                {'error': 'Non hai i permessi per rifiutare questa designazione'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = RifiutaDesignazioneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        motivo = serializer.validated_data.get('motivo', '')

        designazione.rifiuta(user, motivo)

        return Response(DesignazioneRDLSerializer(designazione).data)


class BatchGenerazioneDocumentiViewSet(viewsets.ModelViewSet):
    """
    ViewSet per la generazione batch di documenti.

    GET /api/deleghe/batch/ - Lista batch
    POST /api/deleghe/batch/ - Crea batch e collega designazioni
    POST /api/deleghe/batch/{id}/genera/ - Genera i documenti PDF del batch
    POST /api/deleghe/batch/{id}/approva/ - Approva batch e conferma designazioni

    Permission: can_generate_documents (Delegato, SubDelegato)
    """
    serializer_class = BatchGenerazioneDocumentiSerializer
    permission_classes = [permissions.IsAuthenticated, CanGenerateDocuments]

    def get_queryset(self):
        user = self.request.user
        consultazione_id = self.request.query_params.get('consultazione')

        qs = BatchGenerazioneDocumenti.objects.filter(
            created_by_email=user.email
        ).select_related('consultazione')

        if consultazione_id:
            qs = qs.filter(consultazione_id=consultazione_id)

        return qs

    def create(self, request, *args, **kwargs):
        """
        POST /api/deleghe/batch/

        Crea un batch e collega le designazioni selezionate.
        Body: { consultazione_id, designazione_ids: [], tipo }
        """
        consultazione_id = request.data.get('consultazione_id')
        designazione_ids = request.data.get('designazione_ids', [])
        tipo = request.data.get('tipo', 'INDIVIDUALE')

        if not consultazione_id:
            return Response({'error': 'consultazione_id obbligatorio'}, status=status.HTTP_400_BAD_REQUEST)

        if not designazione_ids:
            return Response({'error': 'designazione_ids obbligatorio'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            consultazione = ConsultazioneElettorale.objects.get(id=consultazione_id)
        except ConsultazioneElettorale.DoesNotExist:
            return Response({'error': 'Consultazione non trovata'}, status=status.HTTP_404_NOT_FOUND)

        # Valida che designazioni esistano e siano BOZZA
        designazioni = DesignazioneRDL.objects.filter(
            id__in=designazione_ids,
            stato='BOZZA',
            is_attiva=True
        )

        if designazioni.count() != len(designazione_ids):
            return Response(
                {'error': 'Alcune designazioni non sono in stato BOZZA o non esistono'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Crea batch
        batch = BatchGenerazioneDocumenti.objects.create(
            consultazione=consultazione,
            tipo=tipo,
            stato='BOZZA',
            created_by_email=request.user.email,
            n_designazioni=designazioni.count()
        )

        # Collega designazioni al batch
        designazioni.update(batch_pdf=batch)

        return Response(
            BatchGenerazioneDocumentiSerializer(batch).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def genera(self, request, pk=None):
        """
        POST /api/deleghe/batch/{id}/genera/

        Genera PDF per il batch e invia email.
        """
        batch = self.get_object()

        if batch.stato != 'BOZZA':
            return Response({'error': 'Batch già generato'}, status=status.HTTP_400_BAD_REQUEST)

        # Ottieni designazioni
        designazioni = batch.designazioni.all().select_related(
            'sezione', 'sezione__comune',
            'delegato', 'sub_delega', 'sub_delega__delegato'
        )

        if not designazioni.exists():
            return Response({'error': 'Nessuna designazione collegata al batch'}, status=status.HTTP_400_BAD_REQUEST)

        # Prepara dati per template (placeholder - da implementare con documents app)
        template_data = {
            'delegato': None,  # Da popolare
            'subdelegato': None,  # Da popolare
            'designazioni': [
                {
                    'sezione_numero': des.sezione.numero,
                    'sezione_comune': des.sezione.comune.nome,
                    'sezione_indirizzo': des.sezione.indirizzo,
                    'effettivo_cognome': des.effettivo_cognome if des.effettivo_email else '',
                    'effettivo_nome': des.effettivo_nome if des.effettivo_email else '',
                    'supplente_cognome': des.supplente_cognome if des.supplente_email else '',
                    'supplente_nome': des.supplente_nome if des.supplente_email else '',
                }
                for des in designazioni
            ]
        }

        # TODO: Integrare con documents app per generazione PDF
        # from documents.views import RequestPDFPreviewView
        # pdf_view = RequestPDFPreviewView()
        # response = pdf_view.post(...)

        # Aggiorna stato batch
        from django.utils import timezone
        batch.stato = 'GENERATO'
        batch.data_generazione = timezone.now()
        batch.save()

        return Response({
            'status': 'PDF generato (placeholder)',
            'message': 'Controlla email per confermare',
            'batch_id': batch.id
        })

    @action(detail=True, methods=['post'])
    def approva(self, request, pk=None):
        """
        POST /api/deleghe/batch/{id}/approva/

        Conferma batch PDF e aggiorna designazioni a CONFERMATA.
        """
        batch = self.get_object()

        if batch.stato != 'GENERATO':
            return Response({'error': 'Batch non generato'}, status=status.HTTP_400_BAD_REQUEST)

        # Approva batch (questo conferma anche tutte le designazioni)
        batch.approva(request.user.email)

        return Response({
            'message': f'Batch approvato. {batch.designazioni.count()} designazioni confermate.',
            'batch_id': batch.id,
            'stato': batch.stato
        })
