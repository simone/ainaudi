"""
Views for delegations API endpoints.

Gerarchia: PARTITO -> DELEGATO DI LISTA -> SUB-DELEGATO -> RDL
"""
from rest_framework import viewsets, views, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from elections.models import ConsultazioneElettorale
from territory.models import SezioneElettorale
from .models import DelegatoDiLista, SubDelega, DesignazioneRDL, BatchGenerazioneDocumenti
from .serializers import (
    DelegatoDiListaSerializer,
    SubDelegaSerializer, SubDelegaCreateSerializer,
    DesignazioneRDLSerializer, DesignazioneRDLCreateSerializer, DesignazioneRDLListSerializer,
    BatchGenerazioneDocumentiSerializer,
    MiaCatenaSerializer, SezioneDisponibileSerializer,
    RdlRegistrationForMappatura, MappaturaCreaSerializer,
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
        deleghe_lista = DelegatoDiLista.objects.filter(email=user.email)
        if consultazione:
            deleghe_lista = deleghe_lista.filter(consultazione=consultazione)
        if deleghe_lista.exists():
            result['is_delegato'] = True
            result['deleghe_lista'] = DelegatoDiListaSerializer(deleghe_lista, many=True).data
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
        designazioni_ricevute = DesignazioneRDL.objects.filter(email=user.email, is_attiva=True)
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
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return SubDelegaCreateSerializer
        return SubDelegaSerializer

    def get_queryset(self):
        user = self.request.user
        consultazione_id = self.request.query_params.get('consultazione')

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
    """
    permission_classes = [permissions.IsAuthenticated]

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
            if sd.municipi:
                municipi.update(sd.municipi)

        # Filtra le sezioni
        sezioni = SezioneElettorale.objects.filter(
            Q(comune_id__in=comuni_ids) | Q(municipio__in=list(municipi))
        ).select_related('comune')

        # Per ogni sezione, verifica se ha gia' effettivo/supplente
        result = []
        for sez in sezioni:
            designazioni = DesignazioneRDL.objects.filter(sezione=sez, is_attiva=True)
            ha_effettivo = designazioni.filter(ruolo='EFFETTIVO').exists()
            ha_supplente = designazioni.filter(ruolo='SUPPLENTE').exists()

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
        delegati = DelegatoDiLista.objects.filter(email=user.email)

        comuni_ids = set()
        municipi_ids = set()

        for sd in sub_deleghe:
            comuni_ids.update(sd.comuni.values_list('id', flat=True))
            if sd.municipi:
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
            designazioni = DesignazioneRDL.objects.filter(
                email=reg.email,
                is_attiva=True
            ).exclude(stato='REVOCATA')

            eff = designazioni.filter(ruolo='EFFETTIVO').first()
            sup = designazioni.filter(ruolo='SUPPLENTE').first()

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
                'designazione_effettivo_id': eff.id if eff else None,
                'designazione_supplente_id': sup.id if sup else None,
            })

        return Response(result)

    @action(detail=False, methods=['post'])
    def mappatura(self, request):
        """
        POST /api/deleghe/designazioni/mappatura/

        Crea una nuova designazione (mappatura RDL -> Sezione).
        Se l'utente ha firma autenticata, la designazione è CONFERMATA.
        Altrimenti è in stato BOZZA e richiede conferma.
        """
        serializer = MappaturaCreaSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        designazione = serializer.save()
        return Response(
            DesignazioneRDLSerializer(designazione).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['post'])
    def carica_mappatura(self, request):
        """
        POST /api/delegations/designazioni/carica_mappatura/

        "Fotografa" tutte le assegnazioni (SectionAssignment) nel territorio del delegato
        e crea le designazioni formali (DesignazioneRDL) corrispondenti.

        Questo converte la mappatura operativa fatta tramite app in designazioni formali.

        Ritorna: { created: N, skipped: N, errors: [], total: N }
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

        # Trova il territorio di competenza del delegato
        sub_deleghe = SubDelega.objects.filter(email=user.email, is_attiva=True)
        delegati = DelegatoDiLista.objects.filter(email=user.email, consultazione=consultazione)

        # Determina quali sezioni può vedere
        sezioni_ids = set()

        # Se è delegato, vede tutto il suo territorio
        for delegato in delegati:
            # Per ora prendiamo tutte le sezioni nelle sue regioni/circoscrizioni
            sezioni_ids.update(
                SezioneElettorale.objects.filter(
                    comune__provincia__regione__in=delegato.regioni.all()
                ).values_list('id', flat=True)
            )

        # Se è sub-delegato, vede solo il suo territorio specifico
        for sd in sub_deleghe:
            # Comuni
            sezioni_comuni = SezioneElettorale.objects.filter(comune__in=sd.comuni.all())

            # Se ha municipi specifici, filtra ulteriormente
            if sd.municipi.exists():
                sezioni_comuni = sezioni_comuni.filter(municipio__in=sd.municipi.all())

            sezioni_ids.update(sezioni_comuni.values_list('id', flat=True))

        if not sezioni_ids:
            return Response({
                'error': 'Nessun territorio di competenza trovato per questo utente'
            }, status=status.HTTP_403_FORBIDDEN)

        # Prendi tutte le SectionAssignment nel territorio
        assignments = SectionAssignment.objects.filter(
            sezione_id__in=sezioni_ids,
            consultazione=consultazione
        ).select_related('rdl_registration', 'sezione', 'sezione__comune')

        created = 0
        skipped = 0
        errors = []
        total = 0

        for assignment in assignments:
            total += 1

            try:
                # Mappa role: SectionAssignment usa 'RDL'/'SUPPLENTE', DesignazioneRDL usa 'EFFETTIVO'/'SUPPLENTE'
                ruolo_rdl = 'EFFETTIVO' if assignment.role == 'RDL' else 'SUPPLENTE'

                # Controlla se esiste già una designazione
                existing = DesignazioneRDL.objects.filter(
                    sezione=assignment.sezione,
                    email=assignment.rdl_registration.email,
                    ruolo=ruolo_rdl,
                    is_attiva=True
                ).first()

                if existing:
                    skipped += 1
                    continue

                # Trova sub-delega o delegato appropriato
                sub_delega = None
                delegato_diretto = None

                # Cerca sub-delega che copre questo territorio
                for sd in sub_deleghe:
                    if assignment.sezione.comune in sd.comuni.all():
                        # Verifica municipi se necessario
                        if sd.municipi.exists():
                            if assignment.sezione.municipio in sd.municipi.all():
                                sub_delega = sd
                                break
                        else:
                            sub_delega = sd
                            break

                # Se non trova sub-delega, cerca delegato diretto
                if not sub_delega:
                    for delegato in delegati:
                        if assignment.sezione.comune.provincia.regione in delegato.regioni.all():
                            delegato_diretto = delegato
                            break

                if not sub_delega and not delegato_diretto:
                    errors.append(f'Sezione {assignment.sezione}: nessuna delega trovata')
                    continue

                # Crea designazione
                designazione = DesignazioneRDL.objects.create(
                    sezione=assignment.sezione,
                    sub_delega=sub_delega,
                    delegato=delegato_diretto,
                    email=assignment.rdl_registration.email,
                    nome=assignment.rdl_registration.nome,
                    cognome=assignment.rdl_registration.cognome,
                    telefono=assignment.rdl_registration.telefono or '',
                    ruolo=ruolo_rdl,
                    stato='CONFERMATA' if (sub_delega and sub_delega.tipo_delega == 'FIRMA_AUTENTICATA') or delegato_diretto else 'BOZZA',
                    is_attiva=True
                )
                created += 1

            except Exception as e:
                errors.append(f'Sezione {assignment.sezione}: {str(e)}')

        return Response({
            'created': created,
            'skipped': skipped,
            'errors': errors,
            'total': total
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
        delegati = DelegatoDiLista.objects.filter(email=user.email)
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
            if sd.municipi:
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
                if sd.municipi and designazione.sezione.municipio_id in sd.municipi:
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
                if sd.municipi and designazione.sezione.municipio_id in sd.municipi:
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
    POST /api/deleghe/batch/ - Crea batch
    POST /api/deleghe/batch/{id}/genera/ - Genera i documenti del batch
    """
    serializer_class = BatchGenerazioneDocumentiSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return BatchGenerazioneDocumenti.objects.filter(
            Q(sub_delega__email=user.email) | Q(created_by_email=user.email)
        ).select_related('sub_delega')

    def perform_create(self, serializer):
        serializer.save(created_by_email=self.request.user.email)

    @action(detail=True, methods=['post'])
    def genera(self, request, pk=None):
        """
        POST /api/deleghe/batch/{id}/genera/

        Genera i documenti PDF per il batch.
        """
        batch = self.get_object()

        # Qui andrebbe la logica di generazione PDF
        # Per ora restituiamo un placeholder
        return Response({
            'status': 'in_progress',
            'message': 'Generazione documenti avviata'
        })
