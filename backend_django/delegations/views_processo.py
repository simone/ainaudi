"""
ViewSet per ProcessoDesignazione - Workflow completo designazioni RDL.

Workflow:
1. POST /api/processi/ - Avvia processo (fotografa mappatura, analizza template)
2. PATCH /api/processi/{id}/configura/ - Configura template + dati delegato + genera PDF
3. POST /api/processi/{id}/conferma/ - Conferma processo (designazioni → CONFERMATE)
4. POST /api/processi/{id}/annulla/ - Annulla processo (elimina tutto)
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from django.http import HttpResponse
from django.db.models import Q
import logging

from .models import ProcessoDesignazione, DesignazioneRDL, Delegato, SubDelega, EmailDesignazioneLog
from .services import RDLEmailService, PDFExtractionService
from core.redis_client import get_redis_client
from .serializers import (
    ProcessoDesignazioneSerializer,
    AvviaProcessoSerializer,
    ConfiguraProcessoSerializer,
    TemplateChoiceSerializer,
    CampiRichiestiSerializer
)
from core.permissions import CanGenerateDocuments
from elections.models import ConsultazioneElettorale
from data.models import SectionAssignment
from campaign.models import RdlRegistration
from documents.models import Template, TemplateType
from territory.models import SezioneElettorale


class ProcessoDesignazioneViewSet(viewsets.ModelViewSet):
    """
    ViewSet per gestire i processi di designazione RDL.

    GET /api/processi/ - Lista processi
    POST /api/processi/ - Avvia nuovo processo
    PATCH /api/processi/{id}/configura/ - Configura template e genera PDF
    POST /api/processi/{id}/conferma/ - Conferma processo
    POST /api/processi/{id}/annulla/ - Annulla processo
    """
    serializer_class = ProcessoDesignazioneSerializer
    permission_classes = [permissions.IsAuthenticated, CanGenerateDocuments]

    def get_queryset(self):
        """Returns processi based on user's territorial scope or created by user."""
        from .permissions import get_sezioni_filter_for_user
        from django.db.models import Q

        user = self.request.user
        consultazione_id = self.request.query_params.get('consultazione')

        # Get territorial filter for user
        sezioni_filter = get_sezioni_filter_for_user(user, consultazione_id)

        if sezioni_filter is None:
            # User has no territorial permissions, can only access own processi
            qs = ProcessoDesignazione.objects.filter(
                created_by_email=user.email
            ).select_related('consultazione', 'delegato', 'template_individuale', 'template_cumulativo')
        else:
            # Get sezioni IDs in user's territory
            sezioni_ids = SezioneElettorale.objects.filter(sezioni_filter).values_list('id', flat=True)

            # Get processi that contain designazioni for sections in user's territory
            processo_ids = DesignazioneRDL.objects.filter(
                sezione_id__in=sezioni_ids,
                processo__isnull=False
            ).values_list('processo_id', flat=True).distinct()

            # Include processi in user's territory OR created by user
            qs = ProcessoDesignazione.objects.filter(
                Q(id__in=processo_ids) | Q(created_by_email=user.email)
            ).select_related('consultazione', 'delegato', 'template_individuale', 'template_cumulativo')

        if consultazione_id:
            qs = qs.filter(consultazione_id=consultazione_id)

        return qs.order_by('-created_at')

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        POST /api/processi/

        Step 1: Avvia processo
        - Fotografa mappatura (crea DesignazioneRDL)
        - Analizza template disponibili
        - Restituisce template choices + schema campi richiesti

        Body: {
            consultazione_id: int,
            sezione_ids: [int, ...]
        }

        Response: {
            processo_id: int,
            template_choices: {
                individuali: [{id, nome, tipo, variabili}],
                cumulativi: [{id, nome, tipo, variabili}]
            },
            delegati_disponibili: [{id, nome_completo, carica_display}],
            campi_richiesti: [{field_name, field_type, label, required, current_value}]
        }
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[ProcessoDesignazione.create] request.data: {request.data}")

        serializer = AvviaProcessoSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"[ProcessoDesignazione.create] Validation errors: {serializer.errors}")
        serializer.is_valid(raise_exception=True)

        consultazione_id = serializer.validated_data['consultazione_id']
        sezione_ids = serializer.validated_data['sezione_ids']

        try:
            consultazione = ConsultazioneElettorale.objects.get(id=consultazione_id)
        except ConsultazioneElettorale.DoesNotExist:
            return Response({'error': 'Consultazione non trovata'}, status=status.HTTP_404_NOT_FOUND)

        # Valida sezioni e verifica permessi
        from territory.models import SezioneElettorale
        from data.models import SectionAssignment

        sezioni = SezioneElettorale.objects.filter(id__in=sezione_ids)
        if not sezioni.exists():
            return Response({'error': 'Nessuna sezione trovata'}, status=status.HTTP_400_BAD_REQUEST)

        # Verifica che nessuna sezione sia già confermata
        errori = []
        for sezione in sezioni:
            confirmed = DesignazioneRDL.objects.filter(
                sezione=sezione,
                is_attiva=True,
                stato='CONFERMATA'
            ).first()
            if confirmed:
                errori.append(f'Sezione {sezione.numero}: già confermata in altro processo')

        if errori:
            return Response({'error': 'Sezioni non disponibili', 'dettagli': errori}, status=status.HTTP_400_BAD_REQUEST)

        # Determina il comune dalle sezioni selezionate
        sezione_sample = sezioni.first()
        comune = sezione_sample.comune if sezione_sample else None

        # Step 1: Crea processo SENZA designazioni (solo salva sezioni)
        processo = ProcessoDesignazione.objects.create(
            consultazione=consultazione,
            comune=comune,
            stato='SELEZIONE_TEMPLATE',
            created_by_email=request.user.email,
            sezione_ids=sezione_ids,  # Salva le sezioni per crearle dopo
            n_designazioni=len(sezione_ids)
        )

        # Step 2: Analizza template disponibili
        template_choices = self._get_template_choices(consultazione)

        # Step 5: Determina chi è l'utente corrente (Delegato o SubDelegato)
        from .models import SubDelega

        delegato_corrente = Delegato.objects.filter(
            email=request.user.email,
            consultazione=consultazione
        ).first()

        subdelegato_corrente = SubDelega.objects.filter(
            email=request.user.email,
            is_attiva=True,
            delegato__consultazione=consultazione
        ).first()

        # Step 6: Prepara liste complete di delegati e subdelegati disponibili
        delegati_disponibili = []
        for delegato in Delegato.objects.filter(consultazione=consultazione):
            delegati_disponibili.append({
                'id': delegato.id,
                'nome_completo': delegato.nome_completo,
                'carica': delegato.carica,
                'email': delegato.email,
                'is_current_user': delegato.email == request.user.email
            })

        subdelegati_disponibili = []
        for subdelega in SubDelega.objects.filter(
            delegato__consultazione=consultazione,
            is_attiva=True
        ):
            subdelegati_disponibili.append({
                'id': subdelega.id,
                'nome_completo': subdelega.nome_completo,
                'email': subdelega.email,
                'is_current_user': subdelega.email == request.user.email
            })

        return Response({
            'processo_id': processo.id,
            'template_choices': template_choices,
            'delegati_disponibili': delegati_disponibili,
            'subdelegati_disponibili': subdelegati_disponibili
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def get_campi_richiesti(self, request, pk=None):
        """
        POST /api/processi/{id}/get_campi_richiesti/

        Analizza i template selezionati ed estrae i campi richiesti.

        Body: {
            template_individuale_id: int,
            template_cumulativo_id: int,
            delegato_id: int (optional),
            subdelegato_id: int (optional)
        }

        Response: {
            campi: [{field_name, field_type, label, required, current_value}]
        }
        """
        processo = self.get_object()

        template_ind_id = request.data.get('template_individuale_id')
        template_cum_id = request.data.get('template_cumulativo_id')
        delegato_id = request.data.get('delegato_id')
        subdelegato_id = request.data.get('subdelegato_id')

        if not template_ind_id or not template_cum_id:
            return Response(
                {'error': 'template_individuale_id e template_cumulativo_id obbligatori'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            template_ind = Template.objects.get(id=template_ind_id)
            template_cum = Template.objects.get(id=template_cum_id)
        except Template.DoesNotExist:
            return Response({'error': 'Template non trovato'}, status=status.HTTP_404_NOT_FOUND)

        # Estrai variabili dai template
        variabili = set()

        vars_ind = self._extract_variables_from_template(template_ind)
        vars_cum = self._extract_variables_from_template(template_cum)

        print(f"[DEBUG] Template individuale '{template_ind.name}' - variabili estratte: {vars_ind}")
        print(f"[DEBUG] Template cumulativo '{template_cum.name}' - variabili estratte: {vars_cum}")

        variabili.update(vars_ind)
        variabili.update(vars_cum)

        print(f"[DEBUG] Variabili unite totali: {variabili}")

        # Ottieni il delegato/subdelegato per pre-compilare i valori
        entity = None
        if delegato_id:
            try:
                entity = Delegato.objects.get(id=delegato_id)
            except Delegato.DoesNotExist:
                pass
        elif subdelegato_id:
            try:
                from .models import SubDelega
                entity = SubDelega.objects.get(id=subdelegato_id)
            except SubDelega.DoesNotExist:
                pass

        # Genera schema campi richiesti
        campi_richiesti = self._generate_campi_schema(variabili, entity)

        return Response({
            'campi': campi_richiesti
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'])
    @transaction.atomic
    def configura(self, request, pk=None):
        """
        PATCH /api/processi/{id}/configura/

        Step 3: Configura template + dati delegato + genera PDF sincrono

        Body: {
            template_individuale_id: int,
            template_cumulativo_id: int,
            delegato_id: int (optional),
            subdelegato_id: int (optional),
            dati_delegato: {...}  // Snapshot completo dati delegato
        }

        Response: {
            success: true,
            documento_individuale_url: str,
            documento_cumulativo_url: str
        }
        """
        processo = self.get_object()

        if processo.stato not in ['SELEZIONE_TEMPLATE', 'BOZZA']:
            return Response(
                {'error': 'Processo già configurato o non più modificabile'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ConfiguraProcessoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        template_ind_id = serializer.validated_data['template_individuale_id']
        template_cum_id = serializer.validated_data['template_cumulativo_id']
        delegato_id = serializer.validated_data.get('delegato_id')
        subdelegato_id = serializer.validated_data.get('subdelegato_id')
        dati_delegato = serializer.validated_data['dati_delegato']

        # Valida template
        try:
            template_ind = Template.objects.get(id=template_ind_id, consultazione=processo.consultazione)
            template_cum = Template.objects.get(id=template_cum_id, consultazione=processo.consultazione)
        except Template.DoesNotExist:
            return Response({'error': 'Template non trovato'}, status=status.HTTP_404_NOT_FOUND)

        # Valida delegato e sub_delega (almeno uno deve essere fornito)
        delegato = None
        sub_delega = None

        if delegato_id:
            try:
                delegato = Delegato.objects.get(id=delegato_id, consultazione=processo.consultazione)
            except Delegato.DoesNotExist:
                return Response({'error': 'Delegato non trovato'}, status=status.HTTP_404_NOT_FOUND)

        if subdelegato_id:
            try:
                sub_delega = SubDelega.objects.get(id=subdelegato_id, is_attiva=True)
                if sub_delega.delegato.consultazione != processo.consultazione:
                    return Response({'error': 'SubDelegato non appartiene alla consultazione'}, status=status.HTTP_400_BAD_REQUEST)
            except SubDelega.DoesNotExist:
                return Response({'error': 'SubDelegato non trovato'}, status=status.HTTP_404_NOT_FOUND)

        if not delegato and not sub_delega:
            return Response({'error': 'Deve essere fornito almeno uno tra delegato e subdelegato'}, status=status.HTTP_400_BAD_REQUEST)

        # Step 1: Crea designazioni dalle sezioni salvate
        from territory.models import SezioneElettorale
        from data.models import SectionAssignment

        sezioni = SezioneElettorale.objects.filter(id__in=processo.sezione_ids)
        errori = []
        designazioni_create = []

        for sezione in sezioni:
            # Cerca SectionAssignment per questa sezione
            assignments = SectionAssignment.objects.filter(
                sezione=sezione,
                consultazione=processo.consultazione
            ).select_related('rdl_registration')

            effettivo = None
            supplente = None
            for assignment in assignments:
                if not assignment.rdl_registration:
                    continue
                if assignment.role == 'RDL':
                    effettivo = assignment.rdl_registration
                elif assignment.role == 'SUPPLENTE':
                    supplente = assignment.rdl_registration

            if not effettivo and not supplente:
                errori.append(f'Sezione {sezione.numero}: nessun RDL assegnato')
                continue

            # Cerca designazione BOZZA esistente (riusa se esiste)
            existing = DesignazioneRDL.objects.filter(
                sezione=sezione,
                is_attiva=True,
                stato='BOZZA'
            ).first()

            if existing:
                # Riusa la designazione esistente
                existing.processo = processo
                existing.sub_delega = sub_delega
                existing.delegato = delegato

                # Aggiorna snapshot dati RDL
                if effettivo:
                    existing.effettivo_cognome = effettivo.cognome
                    existing.effettivo_nome = effettivo.nome
                    existing.effettivo_email = effettivo.email
                    existing.effettivo_telefono = effettivo.telefono or ''
                    existing.effettivo_luogo_nascita = effettivo.comune_nascita or ''
                    existing.effettivo_data_nascita = effettivo.data_nascita
                    existing.effettivo_domicilio = f"{effettivo.indirizzo_residenza}, {effettivo.comune_residenza}"
                else:
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
                    existing.supplente_cognome = ''
                    existing.supplente_nome = ''
                    existing.supplente_email = ''
                    existing.supplente_telefono = ''
                    existing.supplente_luogo_nascita = ''
                    existing.supplente_data_nascita = None
                    existing.supplente_domicilio = ''

                existing.save()
                designazioni_create.append(existing)
            else:
                # Crea nuova designazione
                designazione_data = {
                    'processo': processo,
                    'sezione': sezione,
                    'sub_delega': sub_delega,
                    'delegato': delegato,
                    'stato': 'BOZZA',
                    'is_attiva': True,
                    'created_by_email': request.user.email
                }

                # Snapshot effettivo
                if effettivo:
                    designazione_data.update({
                        'effettivo_cognome': effettivo.cognome,
                        'effettivo_nome': effettivo.nome,
                        'effettivo_email': effettivo.email,
                        'effettivo_telefono': effettivo.telefono or '',
                        'effettivo_luogo_nascita': effettivo.comune_nascita or '',
                        'effettivo_data_nascita': effettivo.data_nascita,
                        'effettivo_domicilio': f"{effettivo.indirizzo_residenza}, {effettivo.comune_residenza}"
                    })

                # Snapshot supplente
                if supplente:
                    designazione_data.update({
                        'supplente_cognome': supplente.cognome,
                        'supplente_nome': supplente.nome,
                        'supplente_email': supplente.email,
                        'supplente_telefono': supplente.telefono or '',
                        'supplente_luogo_nascita': supplente.comune_nascita or '',
                        'supplente_data_nascita': supplente.data_nascita,
                        'supplente_domicilio': f"{supplente.indirizzo_residenza}, {supplente.comune_residenza}"
                    })

                designazione = DesignazioneRDL.objects.create(**designazione_data)
                designazioni_create.append(designazione)

        if errori:
            return Response({'error': 'Errori nella creazione designazioni', 'dettagli': errori}, status=status.HTTP_400_BAD_REQUEST)

        if not designazioni_create:
            return Response({'error': 'Nessuna designazione creata'}, status=status.HTTP_400_BAD_REQUEST)

        # Step 2: Salva configurazione processo
        processo.template_individuale = template_ind
        processo.template_cumulativo = template_cum
        processo.delegato = delegato
        processo.dati_delegato = dati_delegato
        processo.n_designazioni = len(designazioni_create)
        processo.stato = 'BOZZA'  # Ora che le designazioni sono create, processo è BOZZA
        processo.save()

        # Step 3: Aggiorna dati delegato su DB (se presente)
        if delegato:
            for field, value in dati_delegato.items():
                if hasattr(delegato, field) and value:
                    setattr(delegato, field, value)
            delegato.save()

        return Response({
            'success': True,
            'processo': ProcessoDesignazioneSerializer(processo).data
        })

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def genera_individuale(self, request, pk=None):
        """
        POST /api/processi/{id}/genera_individuale/

        Step 4: Genera PDF individuale (uno per sezione)
        """
        processo = self.get_object()

        if processo.stato not in ['BOZZA', 'IN_GENERAZIONE']:
            return Response(
                {'error': 'Processo non configurato o già completato'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not processo.template_individuale:
            return Response(
                {'error': 'Template individuale non configurato'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            self._genera_pdf_individuale(processo)
            processo.save()

            return Response({
                'success': True,
                'documento_url': request.build_absolute_uri(processo.documento_individuale.url) if processo.documento_individuale else None
            })
        except Exception as e:
            return Response(
                {'error': f'Errore generazione PDF individuale: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def genera_cumulativo(self, request, pk=None):
        """
        POST /api/processi/{id}/genera_cumulativo/

        Step 5: Genera PDF cumulativo (multi-pagina)
        """
        processo = self.get_object()

        if processo.stato not in ['BOZZA', 'IN_GENERAZIONE']:
            return Response(
                {'error': 'Processo non configurato o già completato'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not processo.template_cumulativo:
            return Response(
                {'error': 'Template cumulativo non configurato'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            self._genera_pdf_cumulativo(processo)

            # Se entrambi i PDF sono generati, cambia stato
            if processo.documento_individuale and processo.documento_cumulativo:
                processo.stato = 'GENERATO'

            processo.save()

            return Response({
                'success': True,
                'documento_url': request.build_absolute_uri(processo.documento_cumulativo.url) if processo.documento_cumulativo else None
            })
        except Exception as e:
            return Response(
                {'error': f'Errore generazione PDF cumulativo: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def download_individuale(self, request, pk=None):
        """
        GET /api/processi/{id}/download_individuale/

        Scarica il documento PDF individuale.
        """
        from django.http import FileResponse, Http404

        processo = self.get_object()

        if not processo.documento_individuale:
            raise Http404("Documento individuale non ancora generato")

        return FileResponse(
            processo.documento_individuale.open('rb'),
            as_attachment=True,
            filename=f'designazioni_individuale_{processo.id}.pdf'
        )

    @action(detail=True, methods=['get'])
    def download_cumulativo(self, request, pk=None):
        """
        GET /api/processi/{id}/download_cumulativo/

        Scarica il documento PDF cumulativo.
        """
        from django.http import FileResponse, Http404

        processo = self.get_object()

        if not processo.documento_cumulativo:
            raise Http404("Documento cumulativo non ancora generato")

        return FileResponse(
            processo.documento_cumulativo.open('rb'),
            as_attachment=True,
            filename=f'designazioni_cumulativo_{processo.id}.pdf'
        )

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def conferma(self, request, pk=None):
        """
        POST /api/processi/{id}/conferma/

        Step 3: Conferma processo
        - Stato processo: GENERATO → APPROVATO
        - Stato designazioni: BOZZA → CONFERMATA
        """
        processo = self.get_object()

        if processo.stato != 'GENERATO':
            return Response(
                {'error': 'Processo non ancora generato o già confermato'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Approva processo
        processo.stato = 'APPROVATO'
        processo.approvata_at = timezone.now()
        processo.approvata_da_email = request.user.email
        processo.save()

        # Conferma designazioni
        designazioni = processo.designazioni.filter(stato='BOZZA')
        designazioni.update(
            stato='CONFERMATA',
            data_approvazione=timezone.now()
        )

        return Response({
            'success': True,
            'designazioni_confermate': designazioni.count()
        })

    @action(detail=False, methods=['get'])
    def archivio(self, request):
        """
        GET /api/processi/archivio/?consultazione=X&comune_id=Y&tipo=completati|storico

        Lista processi per comune:
        - tipo=completati: Solo APPROVATO (default)
        - tipo=storico: ANNULLATO e altri stati non completati (audit)

        Include sezioni associate e documenti generati.
        """
        consultazione_id = request.query_params.get('consultazione')
        comune_id = request.query_params.get('comune_id')
        tipo = request.query_params.get('tipo', 'completati')

        if not consultazione_id or not comune_id:
            return Response(
                {'error': 'consultazione e comune_id obbligatori'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Filtra processi per tipo
        if tipo == 'storico':
            # Storico: processi annullati o non completati
            processi = self.get_queryset().filter(
                consultazione_id=consultazione_id,
                stato__in=['ANNULLATO', 'BOZZA', 'IN_GENERAZIONE', 'GENERATO']
            )
        else:
            # Completati: solo approvati
            processi = self.get_queryset().filter(
                consultazione_id=consultazione_id,
                stato='APPROVATO'
            )

        # Filtra per comune tramite designazioni
        from territory.models import SezioneElettorale
        sezioni_comune = SezioneElettorale.objects.filter(comune_id=comune_id).values_list('id', flat=True)

        processo_ids = DesignazioneRDL.objects.filter(
            processo__in=processi,
            sezione_id__in=sezioni_comune
        ).values_list('processo_id', flat=True).distinct()

        processi = processi.filter(id__in=processo_ids)

        # Serializza con dettagli
        risultati = []
        for processo in processi:
            designazioni = processo.designazioni.filter(
                sezione_id__in=sezioni_comune
            ).select_related('sezione').order_by('sezione__numero')

            # Informazioni delegato/subdelegato dal snapshot dati_delegato
            delegato_info = None
            if processo.dati_delegato:
                nome = processo.dati_delegato.get('nome', '')
                cognome = processo.dati_delegato.get('cognome', '')
                # Check se è subdelegato
                is_subdelegato = '_subdelegato_id' in processo.dati_delegato
                tipo = 'Sub-Delegato' if is_subdelegato else 'Delegato'
                delegato_info = {
                    'nome_completo': f"{cognome} {nome}".strip() or 'N/A',
                    'tipo': tipo,
                    'email': processo.created_by_email
                }

            sezioni_list = [
                {
                    'id': d.sezione.id,
                    'numero': d.sezione.numero,
                    'indirizzo': d.sezione.indirizzo or '',
                    # RDL Effettivo (dettagliato)
                    'effettivo_cognome': d.effettivo_cognome,
                    'effettivo_nome': d.effettivo_nome,
                    'effettivo_data_nascita': d.effettivo_data_nascita.strftime('%d/%m/%Y') if d.effettivo_data_nascita else None,
                    'effettivo_luogo_nascita': d.effettivo_luogo_nascita or None,
                    'effettivo_domicilio': d.effettivo_domicilio or None,
                    # RDL Supplente (dettagliato)
                    'supplente_cognome': d.supplente_cognome or None,
                    'supplente_nome': d.supplente_nome or None,
                    'supplente_data_nascita': d.supplente_data_nascita.strftime('%d/%m/%Y') if d.supplente_data_nascita else None,
                    'supplente_luogo_nascita': d.supplente_luogo_nascita or None,
                    'supplente_domicilio': d.supplente_domicilio or None
                }
                for d in designazioni
            ]

            risultati.append({
                'id': processo.id,
                'stato': processo.stato,
                'created_at': processo.created_at.isoformat(),
                'approvata_at': processo.approvata_at.isoformat() if processo.approvata_at else None,
                'created_by_email': processo.created_by_email,
                'delegato': delegato_info,
                'n_designazioni': designazioni.count(),
                'template_individuale': {
                    'id': processo.template_individuale.id,
                    'name': processo.template_individuale.name
                } if processo.template_individuale else None,
                'template_cumulativo': {
                    'id': processo.template_cumulativo.id,
                    'name': processo.template_cumulativo.name
                } if processo.template_cumulativo else None,
                'documento_individuale_url': request.build_absolute_uri(processo.documento_individuale.url) if processo.documento_individuale else None,
                'documento_cumulativo_url': request.build_absolute_uri(processo.documento_cumulativo.url) if processo.documento_cumulativo else None,
                'sezioni': sezioni_list
            })

        return Response(risultati, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def annulla(self, request, pk=None):
        """
        POST /api/processi/{id}/annulla/

        Step 4: Annulla processo
        - Elimina designazioni collegate
        - Stato processo: ANNULLATO
        - Designazioni ritornano disponibili per nuovo processo
        """
        processo = self.get_object()

        if processo.stato == 'APPROVATO':
            return Response(
                {'error': 'Processo già approvato, non può essere annullato'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Elimina designazioni (o scollega se vogliamo conservarle)
        designazioni = processo.designazioni.all()
        designazioni_count = designazioni.count()
        designazioni.delete()  # Elimina designazioni

        # Annulla processo
        processo.stato = 'ANNULLATO'
        processo.save()

        return Response({
            'success': True,
            'designazioni_eliminate': designazioni_count
        })

    # ========== Helper Methods ==========

    def _sezione_matches_subdelega(self, sezione, sd):
        """Verifica se una sezione è coperta da una sub-delega."""
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

        # Check comuni + municipi
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

    def _sezione_matches_delegato(self, sezione, delegato):
        """Verifica se una sezione è coperta da un delegato."""
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

    def _get_template_choices(self, consultazione):
        """Restituisce template disponibili per la consultazione."""
        # Template individuali (DESIGNATION_SINGLE)
        tipo_single = TemplateType.objects.filter(code='DESIGNATION_SINGLE').first()
        templates_ind = Template.objects.filter(
            consultazione=consultazione,
            template_type=tipo_single,
            is_active=True
        ) if tipo_single else Template.objects.none()

        # Template cumulativi (DESIGNATION_MULTI)
        tipo_multi = TemplateType.objects.filter(code='DESIGNATION_MULTI').first()
        templates_cum = Template.objects.filter(
            consultazione=consultazione,
            template_type=tipo_multi,
            is_active=True
        ) if tipo_multi else Template.objects.none()

        return {
            'individuali': [
                {
                    'id': t.id,
                    'nome': t.name,
                    'tipo': t.template_type.code,
                    'variabili': self._extract_variables_from_template(t)
                }
                for t in templates_ind
            ],
            'cumulativi': [
                {
                    'id': t.id,
                    'nome': t.name,
                    'tipo': t.template_type.code,
                    'variabili': self._extract_variables_from_template(t)
                }
                for t in templates_cum
            ]
        }

    def _extract_variables_from_template(self, template):
        """
        Estrae variabili delegato/subdelegato dal template (field_mappings).

        I template supportano espressioni come:
        - "$.delegato.nome + ' ' + $.delegato.cognome"
        - "$.delegato.luogo_nascita"

        Questa funzione cerca tutti i pattern $.delegato.* e $.subdelegato.*
        anche all'interno di espressioni complesse.
        """
        import re

        if not template.field_mappings:
            print(f"[DEBUG] Template '{template.name}' (id={template.id}) - NO field_mappings")
            return []

        print(f"[DEBUG] Template '{template.name}' (id={template.id}) - field_mappings: {template.field_mappings}")

        variables = set()

        # Pattern regex per trovare tutti i $.delegato.campo o $.subdelegato.campo
        # anche dentro espressioni come "$.delegato.nome + ' ' + $.delegato.cognome"
        pattern = r'\$\.(delegato|subdelegato)\.([a-zA-Z_][a-zA-Z0-9_]*)'

        for mapping in template.field_mappings:
            jsonpath = mapping.get('jsonpath', '')
            print(f"[DEBUG]   Processing jsonpath: {jsonpath}")

            # Cerca tutti i match del pattern nell'espressione
            matches = re.findall(pattern, jsonpath)
            print(f"[DEBUG]   Matches trovati: {matches}")

            for match in matches:
                # match è una tupla: ('delegato', 'nome') o ('subdelegato', 'cognome')
                prefix = match[0]  # 'delegato' o 'subdelegato'
                field = match[1]   # 'nome', 'cognome', etc.
                variables.add(f"{prefix}.{field}")

        print(f"[DEBUG] Template '{template.name}' - variabili finali: {sorted(list(variables))}")
        return sorted(list(variables))

    def _get_delegati_disponibili(self, user, consultazione):
        """Restituisce delegati disponibili per l'utente."""
        # TODO: Filtrare in base a territorio utente
        delegati = Delegato.objects.filter(consultazione=consultazione)

        return [
            {
                'id': d.id,
                'nome_completo': d.nome_completo,
                'carica_display': d.get_carica_display()
            }
            for d in delegati
        ]

    def _get_campi_richiesti(self, entity):
        """
        Genera schema campi richiesti per delegato/subdelegato.

        Args:
            entity: Delegato o SubDelega object
        """
        # Campi minimi sempre richiesti
        campi = [
            {'field_name': 'cognome', 'field_type': 'text', 'label': 'Cognome', 'required': True, 'current_value': entity.cognome if entity else ''},
            {'field_name': 'nome', 'field_type': 'text', 'label': 'Nome', 'required': True, 'current_value': entity.nome if entity else ''},
            {'field_name': 'luogo_nascita', 'field_type': 'text', 'label': 'Luogo di nascita', 'required': True, 'current_value': getattr(entity, 'luogo_nascita', '') if entity else ''},
            {'field_name': 'data_nascita', 'field_type': 'date', 'label': 'Data di nascita', 'required': True, 'current_value': entity.data_nascita.isoformat() if entity and hasattr(entity, 'data_nascita') and entity.data_nascita else ''},
        ]

        # Campi specifici per Delegato
        if entity and hasattr(entity, 'carica'):
            campi.extend([
                {'field_name': 'carica', 'field_type': 'text', 'label': 'Carica', 'required': True, 'current_value': entity.carica or ''},
                {'field_name': 'circoscrizione', 'field_type': 'text', 'label': 'Circoscrizione', 'required': False, 'current_value': entity.circoscrizione or ''},
                {'field_name': 'data_nomina', 'field_type': 'date', 'label': 'Data nomina', 'required': True, 'current_value': entity.data_nomina.isoformat() if entity.data_nomina else ''},
                {'field_name': 'numero_protocollo_nomina', 'field_type': 'text', 'label': 'Numero protocollo nomina', 'required': False, 'current_value': entity.numero_protocollo_nomina or ''},
            ])

        # Campi comuni
        campi.extend([
            {'field_name': 'email', 'field_type': 'email', 'label': 'Email', 'required': False, 'current_value': entity.email if entity else ''},
            {'field_name': 'telefono', 'field_type': 'tel', 'label': 'Telefono', 'required': False, 'current_value': getattr(entity, 'telefono', '') if entity else ''},
            {'field_name': 'domicilio', 'field_type': 'text', 'label': 'Domicilio', 'required': False, 'current_value': getattr(entity, 'domicilio', '') if entity else ''},
        ])

        return campi

    def _generate_campi_schema(self, variabili, entity):
        """
        Genera schema dinamico dei campi basato sulle variabili dei template.

        Args:
            variabili: set di nomi variabili estratte dai template (es. {'delegato.cognome', 'delegato.nome'})
            entity: Delegato o SubDelega object per pre-compilare i valori

        Returns:
            Lista di dict con schema campi [{field_name, field_type, label, required, current_value}]
        """
        # Mapping variabile → configurazione campo
        field_config = {
            'cognome': {'type': 'text', 'label': 'Cognome', 'required': True},
            'nome': {'type': 'text', 'label': 'Nome', 'required': True},
            'luogo_nascita': {'type': 'text', 'label': 'Luogo di nascita', 'required': True},
            'data_nascita': {'type': 'date', 'label': 'Data di nascita', 'required': True},
            'carica': {'type': 'text', 'label': 'Carica', 'required': True},
            'circoscrizione': {'type': 'text', 'label': 'Circoscrizione', 'required': False},
            'data_nomina': {'type': 'date', 'label': 'Data nomina', 'required': True},
            'numero_protocollo_nomina': {'type': 'text', 'label': 'Numero protocollo nomina', 'required': False},
            'email': {'type': 'email', 'label': 'Email', 'required': False},
            'telefono': {'type': 'tel', 'label': 'Telefono', 'required': False},
            'domicilio': {'type': 'text', 'label': 'Domicilio', 'required': False},
        }

        campi = []
        for var in sorted(variabili):
            # Rimuovi prefisso 'delegato.' o 'subdelegato.'
            if var.startswith('delegato.'):
                field_name = var[9:]  # len('delegato.') = 9
            elif var.startswith('subdelegato.'):
                field_name = var[12:]  # len('subdelegato.') = 12
            else:
                # Variabile senza prefisso (non dovrebbe succedere dopo il filtro in _extract_variables_from_template)
                continue

            config = field_config.get(field_name, {
                'type': 'text',
                'label': field_name.replace('_', ' ').title(),
                'required': False
            })

            # Ottieni valore corrente dall'entity
            current_value = ''
            if entity and hasattr(entity, field_name):
                value = getattr(entity, field_name)
                if value is not None:
                    # Formatta date in ISO format
                    if config['type'] == 'date' and hasattr(value, 'isoformat'):
                        current_value = value.isoformat()
                    else:
                        current_value = str(value)

            campi.append({
                'field_name': field_name,
                'field_type': config['type'],
                'label': config['label'],
                'required': config['required'],
                'current_value': current_value
            })

        return campi

    def _genera_pdf_individuale(self, processo):
        """
        Genera PDF individuale: UN SINGOLO PDF multi-pagina con una pagina per sezione.

        Ogni pagina contiene la designazione per una singola sezione.
        """
        from documents.pdf_generator import PDFGenerator
        from django.core.files.base import ContentFile
        from django.utils import timezone
        from PyPDF2 import PdfWriter

        designazioni = processo.designazioni.all().select_related(
            'sezione', 'sezione__comune', 'sezione__municipio'
        ).order_by('sezione__numero')

        # Crea writer per PDF multi-pagina
        writer = PdfWriter()

        for designazione in designazioni:
            # Prepara dati per singola designazione
            data = {
                'delegato': processo.dati_delegato,
                'designazioni': [{
                    'effettivo_cognome': designazione.effettivo_cognome,
                    'effettivo_nome': designazione.effettivo_nome,
                    'effettivo_data_nascita': designazione.effettivo_data_nascita,
                    'effettivo_luogo_nascita': designazione.effettivo_luogo_nascita,
                    'effettivo_domicilio': designazione.effettivo_domicilio,
                    'supplente_cognome': designazione.supplente_cognome or '',
                    'supplente_nome': designazione.supplente_nome or '',
                    'supplente_data_nascita': designazione.supplente_data_nascita,
                    'supplente_luogo_nascita': designazione.supplente_luogo_nascita or '',
                    'supplente_domicilio': designazione.supplente_domicilio or '',
                    'sezione_numero': designazione.sezione.numero,
                    'sezione_indirizzo': designazione.sezione.indirizzo or '',
                    'comune_nome': designazione.sezione.comune.nome if designazione.sezione.comune else '',
                }]
            }

            # Genera PDF per questa sezione (singola pagina)
            generator = PDFGenerator(processo.template_individuale.template_file, data)
            pdf_bytes = generator.generate_from_template(processo.template_individuale)

            # Importa la pagina nel writer multi-pagina
            from PyPDF2 import PdfReader
            pdf_reader = PdfReader(pdf_bytes)
            for page in pdf_reader.pages:
                writer.add_page(page)

        # Salva PDF multi-pagina
        import io
        output = io.BytesIO()
        writer.write(output)
        output.seek(0)

        processo.documento_individuale.save(
            f'processo_{processo.id}_individuale.pdf',
            ContentFile(output.read()),
            save=False
        )
        processo.data_generazione_individuale = timezone.now()
        processo.n_pagine = designazioni.count()

    def _genera_pdf_cumulativo(self, processo):
        """
        Genera PDF cumulativo (multi-pagina con tutte le sezioni).

        Crea un unico PDF multi-pagina contenente tutte le designazioni.
        """
        from documents.pdf_generator import generate_pdf
        from django.core.files.base import ContentFile
        from django.utils import timezone

        designazioni = processo.designazioni.all().select_related(
            'sezione', 'sezione__comune', 'sezione__municipio'
        ).order_by('sezione__numero')

        # Prepara dati per tutte le designazioni
        data = {
            'delegato': processo.dati_delegato,
            'designazioni': [
                {
                    'effettivo_cognome': d.effettivo_cognome,
                    'effettivo_nome': d.effettivo_nome,
                    'effettivo_data_nascita': d.effettivo_data_nascita,
                    'effettivo_luogo_nascita': d.effettivo_luogo_nascita,
                    'effettivo_domicilio': d.effettivo_domicilio,
                    'supplente_cognome': d.supplente_cognome or '',
                    'supplente_nome': d.supplente_nome or '',
                    'supplente_data_nascita': d.supplente_data_nascita,
                    'supplente_luogo_nascita': d.supplente_luogo_nascita or '',
                    'supplente_domicilio': d.supplente_domicilio or '',
                    'sezione_numero': d.sezione.numero,
                    'sezione_indirizzo': d.sezione.indirizzo or '',
                    'comune_nome': d.sezione.comune.nome if d.sezione.comune else '',
                }
                for d in designazioni
            ]
        }

        # Genera PDF cumulativo (multi-pagina)
        pdf_bytes = generate_pdf(processo.template_cumulativo, data)

        # Salva PDF nel processo
        processo.documento_cumulativo.save(
            f'processo_{processo.id}_cumulativo.pdf',
            ContentFile(pdf_bytes.read()),
            save=False
        )
        processo.data_generazione_cumulativo = timezone.now()
        processo.n_pagine = designazioni.count()

    @action(detail=True, methods=['post'], url_path='invia-email')
    def invia_email(self, request, pk=None):
        """
        Invia email di notifica a tutti gli RDL del processo.

        POST /api/processi/{id}/invia-email/

        Precondizioni:
        - Processo in stato APPROVATO
        - Email non già inviate (email_inviate_at = null)

        Response:
        {
            "success": true,
            "message": "Invio email avviato in background",
            "task_id": "email_task_123_abc123",
            "n_designazioni": 12
        }
        """
        logger = logging.getLogger(__name__)
        processo = self.get_object()

        # Validazioni
        if processo.stato != ProcessoDesignazione.Stato.APPROVATO:
            return Response(
                {
                    'success': False,
                    'error': 'Il processo deve essere in stato APPROVATO per inviare le email'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if processo.email_inviate_at:
            return Response(
                {
                    'success': False,
                    'error': 'Le email sono già state inviate per questo processo',
                    'data_invio': processo.email_inviate_at.isoformat()
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Controlla che ci siano designazioni
        n_designazioni = processo.designazioni.filter(
            stato='CONFERMATA',
            is_attiva=True
        ).count()

        if n_designazioni == 0:
            return Response(
                {
                    'success': False,
                    'error': 'Nessuna designazione confermata da notificare'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Avvia invio asincrono
        try:
            task_id = RDLEmailService.invia_notifiche_processo_async(processo, request.user.email)

            # Ritorna task_id per progress tracking
            return Response({
                'success': True,
                'message': 'Invio email avviato in background',
                'task_id': task_id,
                'n_designazioni': n_designazioni
            }, status=status.HTTP_202_ACCEPTED)  # 202 = Accepted (async)

        except Exception as e:
            logger.error(f"Errore avvio task email processo {processo.id}: {e}", exc_info=True)
            return Response(
                {
                    'success': False,
                    'error': f'Errore durante l\'avvio dell\'invio email: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], url_path='email-progress')
    def email_progress(self, request, pk=None):
        """
        Recupera progress dell'invio email.

        GET /api/processi/{id}/email-progress/

        Response:
        {
            "status": "PROGRESS",
            "current": 50,
            "total": 100,
            "sent": 48,
            "failed": 2,
            "percentage": 50
        }
        """
        processo = self.get_object()

        # Trova task_id più recente per questo processo
        redis = get_redis_client()
        if not redis:
            return Response({
                'status': 'NOT_FOUND',
                'message': 'Redis non disponibile'
            }, status=404)

        task_key = f"email_task_current_{processo.id}"
        task_id = redis.get(task_key)

        if not task_id:
            return Response({
                'status': 'NOT_FOUND',
                'message': 'Nessun invio email in corso'
            }, status=404)

        # Recupera progress
        progress = RDLEmailService.get_task_progress(task_id)

        # Calcola percentuale
        if progress.get('total', 0) > 0:
            progress['percentage'] = int((progress['current'] / progress['total']) * 100)
        else:
            progress['percentage'] = 0

        return Response(progress)

    @action(detail=False, methods=['get'], url_path='download-mia-nomina')
    def download_mia_nomina(self, request):
        """
        RDL scarica copia della propria designazione (PDF personalizzato).

        GET /api/processi/download-mia-nomina/?consultazione_id=1

        Workflow:
        1. Trova processi APPROVATO o INVIATO per la consultazione
        2. Trova designazioni dell'RDL (effettivo o supplente con email utente)
        3. Estrae pagine del PDF individuale corrispondenti alle sezioni RDL
        4. Ritorna PDF come file response (visualizzabile in PDFViewer)
        """
        logger = logging.getLogger(__name__)
        user_email = request.user.email
        consultazione_id = request.GET.get('consultazione_id')

        if not consultazione_id:
            return Response({'error': 'consultazione_id richiesto'}, status=400)

        # Trova designazioni RDL (tutte le sezioni in cui compare come effettivo o supplente)
        designazioni = DesignazioneRDL.objects.filter(
            Q(effettivo_email=user_email) | Q(supplente_email=user_email),
            processo__consultazione_id=consultazione_id,
            processo__stato__in=['APPROVATO', 'INVIATO'],
            stato='CONFERMATA',
            is_attiva=True
        ).select_related('processo', 'sezione').order_by('sezione__numero_sezione')

        if not designazioni.exists():
            return Response({
                'error': 'Nessuna designazione trovata per questa consultazione'
            }, status=404)

        # Determina ruoli: può essere effettivo per alcune sezioni E supplente per altre
        sezioni_effettivo = []
        sezioni_supplente = []

        for des in designazioni:
            if des.effettivo_email == user_email:
                sezioni_effettivo.append(des.sezione_id)
            if des.supplente_email == user_email:
                sezioni_supplente.append(des.sezione_id)

        # Tipo RDL per filename e cache
        if sezioni_effettivo and sezioni_supplente:
            tipo_rdl = 'EFFETTIVO+SUPPLENTE'
        elif sezioni_effettivo:
            tipo_rdl = 'EFFETTIVO'
        else:
            tipo_rdl = 'SUPPLENTE'

        # Estrai PDF personalizzato con tutte le sezioni (indipendentemente dal ruolo)
        try:
            pdf_bytes = PDFExtractionService.estrai_pagine_rdl(
                designazioni=designazioni,
                user_email=user_email  # Per cache key
            )

            # Ritorna PDF come file response
            consultazione_nome = designazioni[0].processo.consultazione.nome
            filename = f"Designazione_RDL_{tipo_rdl}_{consultazione_nome[:30]}.pdf"

            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            response['Content-Length'] = len(pdf_bytes)

            logger.info(
                f"PDF nomina scaricato da {user_email}: "
                f"{designazioni.count()} sezioni, tipo {tipo_rdl}"
            )

            return response

        except Exception as e:
            logger.error(f"Errore download nomina: {e}", exc_info=True)
            return Response({
                'error': f'Errore durante la generazione del PDF: {str(e)}'
            }, status=500)


# Alias per retrocompatibilità con URL esistenti
BatchGenerazioneDocumentiViewSet = ProcessoDesignazioneViewSet
