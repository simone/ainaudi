"""
Views for elections API endpoints.
Only exposes endpoints needed by the frontend.
"""
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions

from .models import (
    ConsultazioneElettorale, TipoElezione, SchedaElettorale,
    ListaElettorale, Candidato,
)


def get_consultazione_attiva():
    """
    Get the most relevant consultation:
    1. First, try to find a consultation happening today (data_inizio <= today <= data_fine)
    2. Otherwise, get the first future consultation (data_inizio > today)
    3. If no future consultations, get the most recent past one
    """
    today = timezone.now().date()

    # 1. Consultazione in corso oggi
    in_corso = ConsultazioneElettorale.objects.filter(
        is_attiva=True,
        data_inizio__lte=today,
        data_fine__gte=today
    ).first()
    if in_corso:
        return in_corso

    # 2. Prima consultazione futura (attiva)
    futura = ConsultazioneElettorale.objects.filter(
        is_attiva=True,
        data_inizio__gt=today
    ).order_by('data_inizio').first()
    if futura:
        return futura

    # 3. Fallback: qualsiasi consultazione attiva
    return ConsultazioneElettorale.objects.filter(is_attiva=True).first()


def serialize_consultazione(consultazione):
    """Serialize a consultation with its schede."""
    if not consultazione:
        return {}

    schede = []
    for tipo in consultazione.tipi_elezione.all():
        for scheda in tipo.schede.all():
            schede.append({
                'id': scheda.id,
                'nome': scheda.nome,
                'colore': scheda.colore,
                'tipo': tipo.tipo,
                'testo_quesito': scheda.testo_quesito,
                'schema_voti': scheda.schema_voti,
            })

    return {
        'id': consultazione.id,
        'nome': consultazione.nome,
        'data_inizio': consultazione.data_inizio,
        'data_fine': consultazione.data_fine,
        'is_attiva': consultazione.is_attiva,
        'descrizione': consultazione.descrizione,
        'schede': schede,
    }


class ConsultazioniListView(APIView):
    """
    List all consultations for the switcher.

    GET /api/elections/consultazioni/

    Returns consultations ordered by date (future first, then past).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()

        # Tutte le consultazioni, ordinate: future (asc) poi passate (desc)
        future = list(ConsultazioneElettorale.objects.filter(
            data_inizio__gte=today
        ).order_by('data_inizio'))

        past = list(ConsultazioneElettorale.objects.filter(
            data_inizio__lt=today
        ).order_by('-data_inizio'))

        all_consultazioni = future + past

        results = []
        for c in all_consultazioni:
            is_current = c.data_inizio <= today <= c.data_fine
            is_future = c.data_inizio > today
            results.append({
                'id': c.id,
                'nome': c.nome,
                'data_inizio': c.data_inizio,
                'data_fine': c.data_fine,
                'is_attiva': c.is_attiva,
                'is_current': is_current,
                'is_future': is_future,
            })

        return Response(results)


class ConsultazioneAttivaView(APIView):
    """
    Get the currently active electoral consultation.

    GET /api/elections/consultazioni/attiva/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        consultazione = get_consultazione_attiva()
        return Response(serialize_consultazione(consultazione))


class ConsultazioneDetailView(APIView):
    """
    Get a specific consultation by ID.

    GET /api/elections/consultazioni/<id>/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            consultazione = ConsultazioneElettorale.objects.get(pk=pk)
        except ConsultazioneElettorale.DoesNotExist:
            return Response({'error': 'Consultazione non trovata'}, status=404)

        return Response(serialize_consultazione(consultazione))


class SchedaElettoraleDetailView(APIView):
    """
    Get or update a specific electoral ballot.

    GET /api/elections/schede/<id>/
    PATCH /api/elections/schede/<id>/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            scheda = SchedaElettorale.objects.select_related('tipo_elezione').get(pk=pk)
        except SchedaElettorale.DoesNotExist:
            return Response({'error': 'Scheda non trovata'}, status=404)

        return Response({
            'id': scheda.id,
            'nome': scheda.nome,
            'colore': scheda.colore,
            'ordine': scheda.ordine,
            'tipo': scheda.tipo_elezione.tipo,
            'tipo_display': scheda.tipo_elezione.get_tipo_display(),
            'testo_quesito': scheda.testo_quesito,
            'schema_voti': scheda.schema_voti,
            'tipo_elezione_id': scheda.tipo_elezione_id,
            'consultazione_id': scheda.tipo_elezione.consultazione_id,
            'consultazione_nome': scheda.tipo_elezione.consultazione.nome,
        })

    def patch(self, request, pk):
        # Solo utenti con permessi referenti possono modificare
        if not request.user.is_superuser:
            # Check delegation chain for permissions
            from delegations.models import DelegatoDiLista, SubDelega
            is_delegato = DelegatoDiLista.objects.filter(email=request.user.email).exists()
            is_sub_delegato = SubDelega.objects.filter(email=request.user.email, is_attiva=True).exists()
            if not is_delegato and not is_sub_delegato:
                return Response({'error': 'Non hai i permessi per modificare le schede'}, status=403)

        try:
            scheda = SchedaElettorale.objects.get(pk=pk)
        except SchedaElettorale.DoesNotExist:
            return Response({'error': 'Scheda non trovata'}, status=404)

        # Aggiorna solo i campi forniti
        if 'nome' in request.data:
            scheda.nome = request.data['nome']
        if 'colore' in request.data:
            scheda.colore = request.data['colore']
        if 'ordine' in request.data:
            scheda.ordine = request.data['ordine']
        if 'testo_quesito' in request.data:
            scheda.testo_quesito = request.data['testo_quesito']
        if 'schema_voti' in request.data:
            scheda.schema_voti = request.data['schema_voti']

        scheda.save()

        return Response({
            'id': scheda.id,
            'nome': scheda.nome,
            'colore': scheda.colore,
            'ordine': scheda.ordine,
            'tipo': scheda.tipo_elezione.tipo,
            'testo_quesito': scheda.testo_quesito,
            'schema_voti': scheda.schema_voti,
        })


class ElectionListsView(APIView):
    """
    Get electoral lists for the active consultation.

    GET /api/election/lists

    Returns format expected by frontend: {values: [[nome1], [nome2], ...]}
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        consultazione = get_consultazione_attiva()
        if not consultazione:
            return Response({'values': []})

        # Get all lists for this consultation
        liste = ListaElettorale.objects.filter(
            scheda__tipo_elezione__consultazione=consultazione
        ).order_by('ordine_scheda').values_list('nome', flat=True)

        # Format expected by frontend: [[nome1], [nome2], ...]
        values = [[nome] for nome in liste]

        return Response({'values': values})


class ElectionCandidatesView(APIView):
    """
    Get candidates for the active consultation.

    GET /api/election/candidates

    Returns format expected by frontend: {values: [nome1, nome2, ...]}
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        consultazione = get_consultazione_attiva()
        if not consultazione:
            return Response({'values': []})

        # Get all candidates for this consultation
        candidati = Candidato.objects.filter(
            lista__scheda__tipo_elezione__consultazione=consultazione
        ).order_by('lista', 'posizione_lista')

        # Format expected by frontend: array of names
        values = [f"{c.cognome} {c.nome}" for c in candidati]

        return Response({'values': values})
