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
from documents.models import Template
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
            'subdelegati_disponibili': subdelegati_disponibili,
            'is_superuser': request.user.is_superuser
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def riprendi(self, request, pk=None):
        """
        GET /api/processi/{id}/riprendi/

        Riprende un processo esistente (BOZZA, SELEZIONE_TEMPLATE, IN_GENERAZIONE, GENERATO).
        Restituisce lo stato corrente + dati per riprendere il wizard dal punto giusto.

        Response: {
            processo_id: int,
            stato: str,
            resume_step: int (1-6),
            template_choices: {...},
            delegati_disponibili: [...],
            subdelegati_disponibili: [...],
            is_superuser: bool,
            // Se già configurato:
            selected_template_ind: int|null,
            selected_template_cum: int|null,
            selected_delegato: int|null,
            selected_subdelegato: int|null,
            dati_delegato: {...},
            has_documento_individuale: bool,
            has_documento_cumulativo: bool,
        }
        """
        processo = self.get_object()

        if processo.stato in ['APPROVATO', 'ANNULLATO', 'INVIATO']:
            return Response(
                {'error': 'Processo non riprendibile (già completato o annullato)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Determine resume step based on stato
        if processo.stato == 'SELEZIONE_TEMPLATE':
            resume_step = 1  # Start from beginning
        elif processo.stato == 'BOZZA':
            if processo.template_individuale and processo.documento_individuale:
                resume_step = 5  # Go to cumulativo generation
            elif processo.template_individuale:
                resume_step = 4  # Go to individuale generation
            else:
                resume_step = 1  # Not yet configured
        elif processo.stato == 'IN_GENERAZIONE':
            resume_step = 4  # Resume individuale generation
        elif processo.stato == 'GENERATO':
            resume_step = 6  # Go to confirmation
        else:
            resume_step = 1

        # Get template choices and delegati (same as create)
        template_choices = self._get_template_choices(processo.consultazione)

        from .models import SubDelega

        delegati_disponibili = []
        for delegato in Delegato.objects.filter(consultazione=processo.consultazione):
            delegati_disponibili.append({
                'id': delegato.id,
                'nome_completo': delegato.nome_completo,
                'carica': delegato.carica,
                'email': delegato.email,
                'is_current_user': delegato.email == request.user.email
            })

        subdelegati_disponibili = []
        for subdelega in SubDelega.objects.filter(
            delegato__consultazione=processo.consultazione,
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
            'stato': processo.stato,
            'resume_step': resume_step,
            'template_choices': template_choices,
            'delegati_disponibili': delegati_disponibili,
            'subdelegati_disponibili': subdelegati_disponibili,
            'is_superuser': request.user.is_superuser,
            'selected_template_ind': processo.template_individuale_id,
            'selected_template_cum': processo.template_cumulativo_id,
            'selected_delegato': processo.delegato_id,
            'selected_subdelegato': processo.dati_delegato.get('_subdelegato_id') if processo.dati_delegato else None,
            'dati_delegato': processo.dati_delegato or {},
            'has_documento_individuale': bool(processo.documento_individuale),
            'has_documento_cumulativo': bool(processo.documento_cumulativo),
        })

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

        # Pre-fetch tutti gli assignments in una sola query
        all_assignments = SectionAssignment.objects.filter(
            sezione__in=sezioni,
            consultazione=processo.consultazione,
            rdl_registration__isnull=False,
        ).select_related('rdl_registration', 'sezione')

        # Raggruppa per sezione_id
        assignments_by_sezione = {}
        for a in all_assignments:
            assignments_by_sezione.setdefault(a.sezione_id, []).append(a)

        # Pre-fetch designazioni BOZZA esistenti
        existing_bozze = {
            d.sezione_id: d
            for d in DesignazioneRDL.objects.filter(
                sezione__in=sezioni,
                is_attiva=True,
                stato='BOZZA'
            )
        }

        to_update = []
        to_create = []

        for sezione in sezioni:
            sezione_assignments = assignments_by_sezione.get(sezione.id, [])

            effettivo = None
            supplente = None
            for assignment in sezione_assignments:
                if assignment.role == 'RDL':
                    effettivo = assignment.rdl_registration
                elif assignment.role == 'SUPPLENTE':
                    supplente = assignment.rdl_registration

            if not effettivo and not supplente:
                errori.append(f'Sezione {sezione.numero}: nessun RDL assegnato')
                continue

            def _snapshot_fields(eff, sup):
                data = {}
                if eff:
                    data.update({
                        'effettivo_cognome': eff.cognome,
                        'effettivo_nome': eff.nome,
                        'effettivo_email': eff.email,
                        'effettivo_telefono': eff.telefono or '',
                        'effettivo_luogo_nascita': eff.comune_nascita or '',
                        'effettivo_data_nascita': eff.data_nascita,
                        'effettivo_domicilio': f"{eff.indirizzo_residenza}, {eff.comune_residenza}"
                    })
                else:
                    data.update({
                        'effettivo_cognome': '', 'effettivo_nome': '', 'effettivo_email': '',
                        'effettivo_telefono': '', 'effettivo_luogo_nascita': '',
                        'effettivo_data_nascita': None, 'effettivo_domicilio': ''
                    })
                if sup:
                    data.update({
                        'supplente_cognome': sup.cognome,
                        'supplente_nome': sup.nome,
                        'supplente_email': sup.email,
                        'supplente_telefono': sup.telefono or '',
                        'supplente_luogo_nascita': sup.comune_nascita or '',
                        'supplente_data_nascita': sup.data_nascita,
                        'supplente_domicilio': f"{sup.indirizzo_residenza}, {sup.comune_residenza}"
                    })
                else:
                    data.update({
                        'supplente_cognome': '', 'supplente_nome': '', 'supplente_email': '',
                        'supplente_telefono': '', 'supplente_luogo_nascita': '',
                        'supplente_data_nascita': None, 'supplente_domicilio': ''
                    })
                return data

            existing = existing_bozze.get(sezione.id)

            if existing:
                existing.processo = processo
                existing.sub_delega = sub_delega
                existing.delegato = delegato
                for k, v in _snapshot_fields(effettivo, supplente).items():
                    setattr(existing, k, v)
                to_update.append(existing)
            else:
                to_create.append(DesignazioneRDL(
                    processo=processo,
                    sezione=sezione,
                    sub_delega=sub_delega,
                    delegato=delegato,
                    stato='BOZZA',
                    is_attiva=True,
                    created_by_email=request.user.email,
                    **_snapshot_fields(effettivo, supplente)
                ))

        if errori:
            return Response({'error': 'Errori nella creazione designazioni', 'dettagli': errori}, status=status.HTTP_400_BAD_REQUEST)

        if not to_create and not to_update:
            return Response({'error': 'Nessuna designazione creata'}, status=status.HTTP_400_BAD_REQUEST)

        # Bulk operations (skip signals, much faster)
        if to_update:
            update_fields = [
                'processo', 'sub_delega', 'delegato',
                'effettivo_cognome', 'effettivo_nome', 'effettivo_email',
                'effettivo_telefono', 'effettivo_luogo_nascita', 'effettivo_data_nascita',
                'effettivo_domicilio',
                'supplente_cognome', 'supplente_nome', 'supplente_email',
                'supplente_telefono', 'supplente_luogo_nascita', 'supplente_data_nascita',
                'supplente_domicilio',
            ]
            DesignazioneRDL.objects.bulk_update(to_update, update_fields, batch_size=500)

        if to_create:
            DesignazioneRDL.objects.bulk_create(to_create, batch_size=500)

        designazioni_create = to_update + to_create

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
    def genera_individuale(self, request, pk=None):
        """
        POST /api/processi/{id}/genera_individuale/

        Step 4: Genera PDF individuale in batch (25 designazioni per chiamata).
        Il frontend chiama ripetutamente fino a completamento.
        Fasi: generating (genera batch) → merging (merge finale) → completed.

        Response:
        {
            "success": true,
            "completed": false,
            "phase": "generating",  // "generating" | "merging" | "completed"
            "generated": 25,
            "total": 1500,
            "percentage": 1
        }
        """
        processo = self.get_object()

        if processo.stato not in ['BOZZA', 'IN_GENERAZIONE', 'GENERATO']:
            return Response(
                {'error': 'Processo non configurato o già completato'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not processo.template_individuale:
            return Response(
                {'error': 'Template individuale non configurato'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Setta stato IN_GENERAZIONE al primo batch
        if processo.stato == 'BOZZA':
            processo.stato = 'IN_GENERAZIONE'
            processo.save(update_fields=['stato'])

        reset = request.data.get('reset', False)

        try:
            result = self._genera_pdf_individuale_batch(processo, batch_size=25, reset=reset)
            processo.save()

            return Response({
                'success': True,
                'completed': result['completed'],
                'phase': result.get('phase', 'generating'),
                'generated': result['generated'],
                'total': result['total'],
                'percentage': result['percentage'],
            })
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("Errore generazione PDF individuale")
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

    def _serve_pdf(self, processo, field_name, filename):
        """Serve un PDF: redirect a GCS se disponibile, altrimenti FileResponse."""
        from django.http import FileResponse, Http404
        from django.shortcuts import redirect

        file_field = getattr(processo, field_name)
        if not file_field:
            raise Http404(f"Documento {field_name} non ancora generato")

        # Se il file è su GCS (ha un URL pubblico), redirect diretto
        # Evita timeout su file grandi trasferiti attraverso Django/GAE
        try:
            file_url = file_field.url
            if 'storage.googleapis.com' in file_url:
                return redirect(file_url)
        except Exception:
            pass

        return FileResponse(
            file_field.open('rb'),
            as_attachment=True,
            filename=filename
        )

    @action(detail=True, methods=['get'])
    def download_individuale(self, request, pk=None):
        """GET /api/processi/{id}/download_individuale/ - Scarica PDF individuale."""
        processo = self.get_object()
        return self._serve_pdf(processo, 'documento_individuale',
                               f'designazioni_individuale_{processo.id}.pdf')

    @action(detail=True, methods=['get'])
    def download_cumulativo(self, request, pk=None):
        """GET /api/processi/{id}/download_cumulativo/ - Scarica PDF cumulativo."""
        processo = self.get_object()
        return self._serve_pdf(processo, 'documento_cumulativo',
                               f'designazioni_cumulativo_{processo.id}.pdf')

    @action(detail=True, methods=['get'], url_path='pdf-urls')
    def pdf_urls(self, request, pk=None):
        """
        GET /api/processi/{id}/pdf-urls/

        Restituisce URL diretti ai PDF (GCS) per il frontend viewer.
        Evita problemi CORS con redirect e timeout su file grandi.
        """
        processo = self.get_object()
        result = {}
        if processo.documento_individuale:
            try:
                result['individuale_url'] = processo.documento_individuale.url
            except Exception:
                result['individuale_url'] = None
        if processo.documento_cumulativo:
            try:
                result['cumulativo_url'] = processo.documento_cumulativo.url
            except Exception:
                result['cumulativo_url'] = None
        return Response(result)

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
        templates_ind = Template.objects.filter(
            consultazione=consultazione,
            template_type='DESIGNATION_SINGLE',
            is_active=True
        )

        # Template cumulativi (DESIGNATION_MULTI)
        templates_cum = Template.objects.filter(
            consultazione=consultazione,
            template_type='DESIGNATION_MULTI',
            is_active=True
        )

        return {
            'individuali': [
                {
                    'id': t.id,
                    'nome': t.name,
                    'tipo': t.template_type,
                    'variabili': self._extract_variables_from_template(t)
                }
                for t in templates_ind
            ],
            'cumulativi': [
                {
                    'id': t.id,
                    'nome': t.name,
                    'tipo': t.template_type,
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

    def _genera_pdf_individuale_batch(self, processo, batch_size=25, reset=False):
        """
        Genera PDF individuale in batch: ogni batch salva un piccolo PDF separato.
        Al completamento, il merge è una chiamata separata.

        Fasi:
        1. generating: genera batch_N.pdf (25 designazioni per chiamata)
        2. merging: unisce tutti i batch nel documento finale
        3. completed: tutto fatto

        Returns:
            {'completed': bool, 'phase': str, 'generated': int, 'total': int, 'percentage': int}
        """
        from documents.pdf_generator import PDFGenerator
        from documents.template_types import DesignationSingleType
        from django.core.files.base import ContentFile
        from django.core.files.storage import default_storage
        from django.utils import timezone
        import pikepdf
        import io
        import json
        import logging

        logger = logging.getLogger(__name__)

        designazioni = list(
            processo.designazioni.all().select_related(
                'sezione', 'sezione__comune', 'sezione__municipio'
            ).order_by('sezione__numero')
        )
        total = len(designazioni)

        # Progress file: traccia quante pagine sono state generate
        progress_path = f'deleghe/processi/processo_{processo.id}_progress.json'
        batch_dir = f'deleghe/processi/processo_{processo.id}_batches'

        # Reset: elimina tutto il progresso precedente
        if reset:
            self._cleanup_batch_files(default_storage, progress_path, batch_dir, total)

        # Leggi progresso attuale
        progress_data = {'generated': 0, 'total': total, 'phase': 'generating'}
        if default_storage.exists(progress_path):
            try:
                with default_storage.open(progress_path, 'rb') as f:
                    progress_data = json.loads(f.read().decode('utf-8'))
            except Exception:
                pass

        offset = progress_data.get('generated', 0)
        phase = progress_data.get('phase', 'generating')

        # FASE 2: Merge (tutti i batch generati, ora unisci)
        if phase == 'merging' or (phase == 'generating' and offset >= total):
            logger.info(f"[BatchGen] Processo {processo.id}: MERGE fase, {offset}/{total} batch generati")
            return self._merge_batches(processo, total, batch_size, progress_path, batch_dir)

        # FASE 1: Genera batch
        if offset >= total:
            offset = 0  # Safeguard

        template_file = processo.template_individuale.template_file
        template_bytes = io.BytesIO(template_file.read())
        template_file.close()

        batch_end = min(offset + batch_size, total)
        batch_num = offset // batch_size

        logger.info(f"[BatchGen] Processo {processo.id}: generazione batch {batch_num} ({offset}-{batch_end}/{total})")

        batch_pdf = pikepdf.Pdf.new()
        source_pdfs = []
        for designazione in designazioni[offset:batch_end]:
            data = DesignationSingleType.serialize(processo, designazione)
            template_bytes.seek(0)
            generator = PDFGenerator(template_bytes, data)
            pdf_output = generator.generate_from_template(processo.template_individuale)
            src = pikepdf.Pdf.open(pdf_output)
            batch_pdf.pages.extend(src.pages)
            source_pdfs.append(src)

        # Salva batch compresso
        batch_output = io.BytesIO()
        batch_pdf.save(batch_output, compress_streams=True)
        for sp in source_pdfs:
            sp.close()
        batch_pdf.close()

        batch_path = f'{batch_dir}/batch_{batch_num:04d}.pdf'
        if default_storage.exists(batch_path):
            default_storage.delete(batch_path)
        default_storage.save(batch_path, ContentFile(batch_output.getvalue()))

        generated = batch_end
        all_generated = generated >= total

        # Aggiorna progresso
        new_progress = {
            'generated': generated,
            'total': total,
            'phase': 'merging' if all_generated else 'generating'
        }
        if default_storage.exists(progress_path):
            default_storage.delete(progress_path)
        default_storage.save(
            progress_path,
            ContentFile(json.dumps(new_progress).encode('utf-8'))
        )

        # Se tutti generati, la prossima chiamata farà il merge
        percentage = int(generated / total * 100) if total > 0 else 100
        # Cap at 95% during generation, reserve 95-100% for merge
        if not all_generated:
            percentage = min(percentage, 95)

        return {
            'completed': False,  # Merge non ancora fatto
            'phase': 'merging' if all_generated else 'generating',
            'generated': generated,
            'total': total,
            'percentage': percentage,
        }

    def _merge_batches(self, processo, total, batch_size, progress_path, batch_dir):
        """Merge tutti i batch PDF nel documento finale."""
        from django.core.files.base import ContentFile
        from django.core.files.storage import default_storage
        from django.utils import timezone
        import pikepdf
        import io
        import logging

        logger = logging.getLogger(__name__)

        merged_pdf = pikepdf.Pdf.new()
        n_batches = (total + batch_size - 1) // batch_size
        batch_pdfs = []

        logger.info(f"[BatchGen] Processo {processo.id}: merge {n_batches} batch")

        for i in range(n_batches):
            bp = f'{batch_dir}/batch_{i:04d}.pdf'
            if default_storage.exists(bp):
                batch_bytes = io.BytesIO()
                with default_storage.open(bp, 'rb') as f:
                    batch_bytes.write(f.read())
                batch_bytes.seek(0)
                batch_pdf = pikepdf.Pdf.open(batch_bytes)
                merged_pdf.pages.extend(batch_pdf.pages)
                batch_pdfs.append(batch_pdf)

        final_output = io.BytesIO()
        merged_pdf.save(final_output, compress_streams=True,
                       object_stream_mode=pikepdf.ObjectStreamMode.generate)
        for bp in batch_pdfs:
            bp.close()
        merged_pdf.close()

        logger.info(f"[BatchGen] Processo {processo.id}: merge completato, size={len(final_output.getvalue())} bytes")

        processo.documento_individuale.save(
            f'processo_{processo.id}_individuale.pdf',
            ContentFile(final_output.getvalue()),
            save=False
        )
        processo.data_generazione_individuale = timezone.now()
        processo.n_pagine = total

        # Cleanup batch files
        self._cleanup_batch_files(default_storage, progress_path, batch_dir, total)

        return {
            'completed': True,
            'phase': 'completed',
            'generated': total,
            'total': total,
            'percentage': 100,
        }

    @staticmethod
    def _cleanup_batch_files(storage, progress_path, batch_dir, total, batch_size=100):
        """Rimuove i file temporanei dei batch."""
        if storage.exists(progress_path):
            storage.delete(progress_path)
        n_batches = (total + batch_size - 1) // batch_size
        for i in range(n_batches + 1):
            bp = f'{batch_dir}/batch_{i:04d}.pdf'
            if storage.exists(bp):
                storage.delete(bp)

    def _genera_pdf_cumulativo(self, processo):
        """
        Genera PDF cumulativo (multi-pagina con tutte le sezioni).

        Crea un unico PDF multi-pagina contenente tutte le designazioni.
        Il template viene letto una sola volta.
        """
        from documents.pdf_generator import PDFGenerator
        from documents.template_types import DesignationMultiType
        from django.core.files.base import ContentFile
        from django.utils import timezone
        import io

        designazioni = processo.designazioni.all().select_related(
            'sezione', 'sezione__comune', 'sezione__municipio'
        ).order_by('sezione__numero')

        data = DesignationMultiType.serialize(processo, designazioni)

        # Leggi il template UNA volta in memoria
        template_file = processo.template_cumulativo.template_file
        template_bytes = io.BytesIO(template_file.read())
        template_file.close()

        generator = PDFGenerator(template_bytes, data)
        pdf_bytes = generator.generate_from_template(processo.template_cumulativo)

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

        # Verifica che il documento sia stato generato
        if not processo.documento_individuale:
            return Response(
                {
                    'success': False,
                    'error': 'Il documento di designazione non è ancora stato generato. Genera il PDF prima di inviare le email.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Opzione: allega PDF designazione
        allega_designazione = request.data.get('allega_designazione', False)

        # Avvia invio batch email
        try:
            result = RDLEmailService.invia_notifiche_processo_batch(
                processo, request.user.email, batch_size=50,
                allega_designazione=allega_designazione
            )

            return Response({
                'success': True,
                'message': 'Invio email avviato in batch mode',
                'sent': result['sent'],
                'remaining': result['remaining'],
                'total': result['total'],
                'n_designazioni': n_designazioni
            }, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            logger.error(f"Errore invio email processo {processo.id}: {e}", exc_info=True)
            return Response(
                {
                    'success': False,
                    'error': f'Errore durante l\'invio email: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='mie-designazioni',
            permission_classes=[permissions.IsAuthenticated])
    def mie_designazioni(self, request):
        """
        Restituisce le designazioni dell'utente loggato (RDL).

        GET /api/deleghe/processi/mie-designazioni/?consultazione_id=1

        Response:
        {
            "has_designazioni": true,
            "consultazione": {...},
            "designazioni": [
                {
                    "id": 1,
                    "sezione": {...},
                    "tipo": "EFFETTIVO",  # o "SUPPLENTE" o "EFFETTIVO+SUPPLENTE"
                    "processo": {...}
                }
            ]
        }
        """
        user_email = request.user.email
        consultazione_id = request.GET.get('consultazione_id')

        if not consultazione_id:
            # Prendi consultazione attiva
            from elections.models import ConsultazioneElettorale
            consultazione = ConsultazioneElettorale.objects.filter(is_attiva=True).first()
            if not consultazione:
                return Response({
                    'has_designazioni': False,
                    'message': 'Nessuna consultazione attiva'
                })
            consultazione_id = consultazione.id

        # Trova designazioni RDL (sia effettivo che supplente)
        # Include TEST designazioni per testing purposes
        designazioni = DesignazioneRDL.objects.filter(
            Q(effettivo_email=user_email) | Q(supplente_email=user_email),
            processo__consultazione_id=consultazione_id,
            processo__stato__in=['APPROVATO', 'INVIATO', 'TEST'],
            stato='CONFERMATA',
            is_attiva=True
        ).select_related(
            'processo', 'processo__consultazione',
            'sezione', 'sezione__comune'
        ).order_by('sezione__numero')

        if not designazioni.exists():
            return Response({
                'has_designazioni': False,
                'message': 'Nessuna designazione trovata'
            })

        # Raggruppa per sezione (un RDL può essere sia effettivo che supplente)
        sezioni_map = {}
        for des in designazioni:
            sezione_id = des.sezione_id
            if sezione_id not in sezioni_map:
                sezioni_map[sezione_id] = {
                    'designazione': des,
                    'is_effettivo': False,
                    'is_supplente': False
                }

            if des.effettivo_email == user_email:
                sezioni_map[sezione_id]['is_effettivo'] = True
            if des.supplente_email == user_email:
                sezioni_map[sezione_id]['is_supplente'] = True

        # Costruisci response
        designazioni_list = []
        for sezione_id, data in sezioni_map.items():
            des = data['designazione']

            # Determina tipo
            if data['is_effettivo'] and data['is_supplente']:
                tipo = 'EFFETTIVO+SUPPLENTE'
            elif data['is_effettivo']:
                tipo = 'EFFETTIVO'
            else:
                tipo = 'SUPPLENTE'

            designazioni_list.append({
                'id': des.id,
                'tipo': tipo,
                'sezione': {
                    'id': des.sezione.id,
                    'numero': des.sezione.numero,
                    'indirizzo': des.sezione.indirizzo,
                    'comune': des.sezione.comune.nome if des.sezione.comune else 'N/A'
                },
                'processo': {
                    'id': des.processo.id,
                    'stato': des.processo.stato
                }
            })

        consultazione = designazioni.first().processo.consultazione

        # Verifica se esiste almeno un processo con documento individuale generato
        processi_ids = set(des.processo_id for des in designazioni)
        has_documento = ProcessoDesignazione.objects.filter(
            id__in=processi_ids,
            documento_individuale__isnull=False,
        ).exclude(documento_individuale='').exists()

        return Response({
            'has_designazioni': True,
            'has_documento': has_documento,
            'consultazione': {
                'id': consultazione.id,
                'nome': consultazione.nome
            },
            'designazioni': designazioni_list,
            'totale_sezioni': len(designazioni_list)
        })

    def _generate_test_pdf_response(self, consultazione_id):
        """
        Generate a fake PDF for TEST processes.

        Returns a simple PDF with:
        - Title: "DESIGNAZIONI - PERIODO TEST"
        - Message: "Le designazioni non sono ancora disponibili durante il test"
        - Creation date
        """
        from io import BytesIO
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from datetime import datetime

        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)

        # Document metadata
        c.setTitle("Designazioni Test")

        # Page content
        y_position = 750
        c.setFont("Helvetica-Bold", 18)
        c.drawString(50, y_position, "DESIGNAZIONI - PERIODO TEST")

        y_position -= 60
        c.setFont("Helvetica", 12)
        c.drawString(50, y_position, "Le designazioni non sono ancora disponibili durante il periodo test")

        y_position -= 30
        c.drawString(50, y_position, "della piattaforma.")

        y_position -= 60
        c.setFont("Helvetica", 11)
        c.drawString(50, y_position, f"Documento generato il: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

        y_position -= 30
        c.setFont("Helvetica-Oblique", 10)
        c.drawString(50, y_position, "Questo è un documento temporaneo per il periodo di test.")

        c.save()
        buffer.seek(0)
        pdf_bytes = buffer.getvalue()

        # Get consultazione for filename
        try:
            consultazione = ConsultazioneElettorale.objects.get(id=consultazione_id)
            consultazione_nome = consultazione.nome[:30]
        except ConsultazioneElettorale.DoesNotExist:
            consultazione_nome = "Test"

        filename = f"Designazione_Test_{consultazione_nome}.pdf"

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        response['Content-Length'] = len(pdf_bytes)

        return response

    @action(detail=False, methods=['get'], url_path='download-mia-nomina',
            permission_classes=[permissions.IsAuthenticated])
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
        if not (request.user.is_superuser or request.user.has_perm('core.can_download_designazioni')):
            return Response({'error': 'Download designazioni non ancora disponibile.'}, status=403)

        logger = logging.getLogger(__name__)
        user_email = request.user.email
        consultazione_id = request.GET.get('consultazione_id')

        if not consultazione_id:
            return Response({'error': 'consultazione_id richiesto'}, status=400)

        # Trova designazioni RDL (tutte le sezioni in cui compare come effettivo o supplente)
        designazioni = DesignazioneRDL.objects.filter(
            Q(effettivo_email=user_email) | Q(supplente_email=user_email),
            processo__consultazione_id=consultazione_id,
            processo__stato__in=['APPROVATO', 'INVIATO', 'TEST'],
            stato='CONFERMATA',
            is_attiva=True
        ).select_related('processo', 'sezione').order_by('sezione__numero')

        if not designazioni.exists():
            return Response({
                'error': 'Nessuna designazione trovata per questa consultazione'
            }, status=404)

        # Verifica che il documento sia stato generato
        processo = designazioni.first().processo
        if not processo.documento_individuale:
            return Response({
                'error': 'Il documento di designazione non è ancora stato generato.'
            }, status=404)

        # Se è un processo TEST, genera un PDF finto per indicare che è in test
        if processo.stato == 'TEST':
            return self._generate_test_pdf_response(consultazione_id)

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

    @action(detail=False, methods=['get'], url_path='download-designazione-rdl',
            permission_classes=[permissions.IsAuthenticated])
    def download_designazione_rdl(self, request):
        """
        Delegato scarica il PDF di designazione per un RDL specifico.

        GET /api/processi/download-designazione-rdl/?consultazione_id=1&email=rdl@example.com
        """
        logger = logging.getLogger(__name__)
        consultazione_id = request.GET.get('consultazione_id')
        rdl_email = request.GET.get('email')

        if not consultazione_id or not rdl_email:
            return Response({'error': 'consultazione_id e email richiesti'}, status=400)

        # Trova designazioni per questo RDL
        designazioni = DesignazioneRDL.objects.filter(
            Q(effettivo_email=rdl_email) | Q(supplente_email=rdl_email),
            processo__consultazione_id=consultazione_id,
            processo__stato__in=['APPROVATO', 'INVIATO', 'TEST'],
            stato='CONFERMATA',
            is_attiva=True
        ).select_related('processo', 'sezione')

        if not designazioni.exists():
            return Response({'error': 'Nessuna designazione trovata'}, status=404)

        # Verifica che l'utente sia il delegato del processo (o superuser)
        processo = designazioni.first().processo
        if not request.user.is_superuser:
            if not (processo.delegato and processo.delegato.email == request.user.email):
                return Response({'error': 'Non autorizzato'}, status=403)

        if not processo.documento_individuale:
            return Response({
                'error': 'Il documento di designazione non è ancora stato generato per questo processo.'
            }, status=404)

        try:
            pdf_bytes = PDFExtractionService.estrai_pagine_rdl(designazioni, rdl_email)

            filename = f"Designazione_RDL_{rdl_email.split('@')[0]}.pdf"
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            response['Content-Length'] = len(pdf_bytes)

            return response

        except Exception as e:
            logger.error(f"Errore download designazione RDL: {e}", exc_info=True)
            return Response({'error': str(e)}, status=500)


# Alias per retrocompatibilità con URL esistenti
BatchGenerazioneDocumentiViewSet = ProcessoDesignazioneViewSet
