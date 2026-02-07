"""
Scrutinio aggregato view per delegati/sub-delegati.

Fornisce navigazione gerarchica dei dati di scrutinio:
Regione → Provincia → Comune → Municipio → Sezione

Con skip automatico se c'è solo una entità a un livello.
"""
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Sum, Count, Q, F, Case, When, FloatField
from django.db.models.functions import Coalesce

from core.permissions import CanViewKPI
from .models import DatiSezione, DatiScheda
from elections.models import ConsultazioneElettorale, SchedaElettorale
from territory.models import Regione, Provincia, Comune, Municipio, SezioneElettorale
from delegations.permissions import get_sezioni_filter_for_user, get_user_delegation_roles


def get_consultazione_attiva():
    """Get the currently active consultation."""
    return ConsultazioneElettorale.objects.filter(is_attiva=True).first()


class ScrutinioAggregatoView(APIView):
    """
    Endpoint per visualizzazione gerarchica aggregata dello scrutinio.

    GET /api/scrutinio/aggregato?consultazione_id=1&regione_id=12&provincia_id=58&comune_id=5432

    Navigazione drill-down:
    1. Nessun parametro → Lista regioni con dati aggregati
    2. regione_id → Lista province in quella regione
    3. provincia_id → Lista comuni in quella provincia
    4. comune_id → Lista municipi (se esistono) o sezioni
    5. municipio_id → Lista sezioni in quel municipio

    Skip automatico: Se c'è solo una entità al livello, restituisce direttamente il livello successivo.

    Permission: can_view_kpi (Delegati, SubDelegati che supervisionano)
    """
    permission_classes = [permissions.IsAuthenticated, CanViewKPI]

    def get(self, request):
        consultazione_id = request.query_params.get('consultazione_id')
        regione_id = request.query_params.get('regione_id')
        provincia_id = request.query_params.get('provincia_id')
        comune_id = request.query_params.get('comune_id')
        municipio_id = request.query_params.get('municipio_id')

        if consultazione_id:
            try:
                consultazione = ConsultazioneElettorale.objects.get(id=consultazione_id)
            except ConsultazioneElettorale.DoesNotExist:
                return Response({'error': 'Consultazione non trovata'}, status=404)
        else:
            consultazione = get_consultazione_attiva()

        if not consultazione:
            return Response({'error': 'Nessuna consultazione attiva'}, status=404)

        # Get user's accessible sections
        roles = get_user_delegation_roles(request.user, consultazione.id)

        # Allow superusers, delegati, and sub-delegati
        if not (request.user.is_superuser or roles['is_delegato'] or roles['is_sub_delegato']):
            return Response({'error': 'Accesso riservato a delegati e sub-delegati'}, status=403)

        sezioni_filter = get_sezioni_filter_for_user(request.user, consultazione.id)
        if sezioni_filter is None and not request.user.is_superuser:
            return Response({'error': 'Nessuna sezione accessibile'}, status=403)

        # Build base queryset for accessible sections
        sezioni_qs = SezioneElettorale.objects.filter(
            sezioni_filter,
            is_attiva=True
        )

        # Determine drill-down level and return aggregated data
        if municipio_id:
            # Level 5: Sezioni in municipio
            return self._get_sezioni_in_municipio(municipio_id, consultazione, sezioni_qs)
        elif comune_id:
            # Level 4: Municipi in comune (or sezioni if no municipi)
            return self._get_municipi_or_sezioni(comune_id, consultazione, sezioni_qs)
        elif provincia_id:
            # Level 3: Comuni in provincia
            return self._get_comuni_in_provincia(provincia_id, consultazione, sezioni_qs)
        elif regione_id:
            # Level 2: Province in regione
            return self._get_province_in_regione(regione_id, consultazione, sezioni_qs)
        else:
            # Level 1: Regioni
            return self._get_regioni(consultazione, sezioni_qs)

    def _get_regioni(self, consultazione, sezioni_qs):
        """Level 1: Aggregate by Regione."""
        # Get unique regions from accessible sections
        regioni_ids = sezioni_qs.values_list('comune__provincia__regione_id', flat=True).distinct()
        regioni = Regione.objects.filter(id__in=regioni_ids).order_by('nome')

        # If only one region, skip to provinces
        if regioni.count() == 1:
            regione = regioni.first()
            return self._get_province_in_regione(regione.id, consultazione, sezioni_qs)

        # Calculate summary for all accessible sections (Italia totale)
        summary = self._aggregate_sezioni(sezioni_qs, consultazione)
        summary['nome'] = 'Italia'
        summary['tipo'] = 'root'

        # Aggregate data by region
        data = []
        for regione in regioni:
            sezioni_in_regione = sezioni_qs.filter(comune__provincia__regione=regione)
            aggregated = self._aggregate_sezioni(sezioni_in_regione, consultazione)

            data.append({
                'id': regione.id,
                'tipo': 'regione',
                'nome': regione.nome,
                'sigla': regione.codice_istat,
                **aggregated
            })

        # Sort by totale_sezioni descending
        data.sort(key=lambda x: x['totale_sezioni'], reverse=True)

        return Response({
            'level': 'regioni',
            'consultazione_id': consultazione.id,
            'breadcrumbs': [{'tipo': 'root', 'nome': 'Italia'}],
            'summary': summary,
            'items': data
        })

    def _get_province_in_regione(self, regione_id, consultazione, sezioni_qs):
        """Level 2: Aggregate by Provincia in a Regione."""
        try:
            regione = Regione.objects.get(id=regione_id)
        except Regione.DoesNotExist:
            return Response({'error': 'Regione non trovata'}, status=404)

        # Filter sections in this region
        sezioni_in_regione = sezioni_qs.filter(comune__provincia__regione=regione)

        # Calculate summary for the region
        summary = self._aggregate_sezioni(sezioni_in_regione, consultazione)
        summary['nome'] = regione.nome
        summary['tipo'] = 'regione'
        summary['id'] = regione.id

        # Get unique provinces
        province_ids = sezioni_in_regione.values_list('comune__provincia_id', flat=True).distinct()
        province = Provincia.objects.filter(id__in=province_ids).order_by('nome')

        # If only one provincia, skip to comuni
        if province.count() == 1:
            provincia = province.first()
            return self._get_comuni_in_provincia(provincia.id, consultazione, sezioni_qs)

        # Aggregate data by provincia
        data = []
        for provincia in province:
            sezioni_in_provincia = sezioni_in_regione.filter(comune__provincia=provincia)
            aggregated = self._aggregate_sezioni(sezioni_in_provincia, consultazione)

            data.append({
                'id': provincia.id,
                'tipo': 'provincia',
                'nome': provincia.nome,
                'sigla': provincia.sigla,
                **aggregated
            })

        # Sort by totale_sezioni descending
        data.sort(key=lambda x: x['totale_sezioni'], reverse=True)

        return Response({
            'level': 'province',
            'consultazione_id': consultazione.id,
            'regione_id': regione.id,
            'breadcrumbs': [
                {'tipo': 'root', 'nome': 'Italia'},
                {'tipo': 'regione', 'id': regione.id, 'nome': regione.nome}
            ],
            'summary': summary,
            'items': data
        })

    def _get_comuni_in_provincia(self, provincia_id, consultazione, sezioni_qs):
        """Level 3: Aggregate by Comune in a Provincia."""
        try:
            provincia = Provincia.objects.get(id=provincia_id)
        except Provincia.DoesNotExist:
            return Response({'error': 'Provincia non trovata'}, status=404)

        regione = provincia.regione

        # Filter sections in this provincia
        sezioni_in_provincia = sezioni_qs.filter(comune__provincia=provincia)

        # Calculate summary for the provincia
        summary = self._aggregate_sezioni(sezioni_in_provincia, consultazione)
        summary['nome'] = provincia.nome
        summary['sigla'] = provincia.sigla
        summary['tipo'] = 'provincia'
        summary['id'] = provincia.id

        # Get unique comuni
        comuni_ids = sezioni_in_provincia.values_list('comune_id', flat=True).distinct()
        comuni = Comune.objects.filter(id__in=comuni_ids).order_by('nome')

        # If only one comune, skip to municipi or sezioni
        if comuni.count() == 1:
            comune = comuni.first()
            return self._get_municipi_or_sezioni(comune.id, consultazione, sezioni_qs)

        # Aggregate data by comune
        data = []
        for comune in comuni:
            sezioni_in_comune = sezioni_in_provincia.filter(comune=comune)
            aggregated = self._aggregate_sezioni(sezioni_in_comune, consultazione)

            data.append({
                'id': comune.id,
                'tipo': 'comune',
                'nome': comune.nome,
                'provincia_sigla': provincia.sigla,
                **aggregated
            })

        # Sort by totale_sezioni descending
        data.sort(key=lambda x: x['totale_sezioni'], reverse=True)

        return Response({
            'level': 'comuni',
            'consultazione_id': consultazione.id,
            'regione_id': regione.id,
            'provincia_id': provincia.id,
            'breadcrumbs': [
                {'tipo': 'root', 'nome': 'Italia'},
                {'tipo': 'regione', 'id': regione.id, 'nome': regione.nome},
                {'tipo': 'provincia', 'id': provincia.id, 'nome': provincia.nome}
            ],
            'summary': summary,
            'items': data
        })

    def _get_municipi_or_sezioni(self, comune_id, consultazione, sezioni_qs):
        """Level 4: Aggregate by Municipio (if exists) or Sezioni."""
        try:
            comune = Comune.objects.get(id=comune_id)
        except Comune.DoesNotExist:
            return Response({'error': 'Comune non trovato'}, status=404)

        provincia = comune.provincia
        regione = provincia.regione

        # Filter sections in this comune
        sezioni_in_comune = sezioni_qs.filter(comune=comune)

        # Calculate summary for the comune
        summary = self._aggregate_sezioni(sezioni_in_comune, consultazione)
        summary['nome'] = comune.nome
        summary['tipo'] = 'comune'
        summary['id'] = comune.id

        # Check if this comune has municipi
        municipi_ids = sezioni_in_comune.filter(municipio__isnull=False).values_list('municipio_id', flat=True).distinct()

        if municipi_ids:
            municipi = Municipio.objects.filter(id__in=municipi_ids).order_by('numero')

            # If only one municipio, skip to sezioni
            if municipi.count() == 1:
                municipio = municipi.first()
                return self._get_sezioni_in_municipio(municipio.id, consultazione, sezioni_qs)

            # Aggregate data by municipio
            data = []
            for municipio in municipi:
                sezioni_in_municipio = sezioni_in_comune.filter(municipio=municipio)
                aggregated = self._aggregate_sezioni(sezioni_in_municipio, consultazione)

                data.append({
                    'id': municipio.id,
                    'tipo': 'municipio',
                    'nome': municipio.nome,
                    'numero': municipio.numero,
                    **aggregated
                })

            # Sort by totale_sezioni descending
            data.sort(key=lambda x: x['totale_sezioni'], reverse=True)

            return Response({
                'level': 'municipi',
                'consultazione_id': consultazione.id,
                'regione_id': regione.id,
                'provincia_id': provincia.id,
                'comune_id': comune.id,
                'breadcrumbs': [
                    {'tipo': 'root', 'nome': 'Italia'},
                    {'tipo': 'regione', 'id': regione.id, 'nome': regione.nome},
                    {'tipo': 'provincia', 'id': provincia.id, 'nome': provincia.nome},
                    {'tipo': 'comune', 'id': comune.id, 'nome': comune.nome}
                ],
                'summary': summary,
                'items': data
            })
        else:
            # No municipi, go directly to sezioni
            return self._get_sezioni_list(sezioni_in_comune, consultazione, comune, provincia, regione)

    def _get_sezioni_in_municipio(self, municipio_id, consultazione, sezioni_qs):
        """Level 5: List Sezioni in a Municipio."""
        try:
            municipio = Municipio.objects.get(id=municipio_id)
        except Municipio.DoesNotExist:
            return Response({'error': 'Municipio non trovato'}, status=404)

        comune = municipio.comune
        provincia = comune.provincia
        regione = provincia.regione

        # Filter sections in this municipio
        sezioni_in_municipio = sezioni_qs.filter(municipio=municipio)

        return self._get_sezioni_list(sezioni_in_municipio, consultazione, comune, provincia, regione, municipio)

    def _get_sezioni_list(self, sezioni_qs, consultazione, comune, provincia, regione, municipio=None):
        """Final level: List individual sezioni with their data."""
        # Calculate summary for the municipio or comune
        summary = self._aggregate_sezioni(sezioni_qs, consultazione)
        if municipio:
            summary['nome'] = municipio.nome
            summary['numero'] = municipio.numero
            summary['tipo'] = 'municipio'
            summary['id'] = municipio.id
        else:
            summary['nome'] = comune.nome
            summary['tipo'] = 'comune'
            summary['id'] = comune.id

        sezioni = sezioni_qs.order_by('numero')

        data = []
        for sezione in sezioni:
            # Get DatiSezione
            try:
                dati_sezione = DatiSezione.objects.get(sezione=sezione, consultazione=consultazione)

                totale_elettori = (dati_sezione.elettori_maschi or 0) + (dati_sezione.elettori_femmine or 0)
                totale_votanti = (dati_sezione.votanti_maschi or 0) + (dati_sezione.votanti_femmine or 0)
                affluenza = round((totale_votanti / totale_elettori * 100), 2) if totale_elettori > 0 else 0

                # Get schede data
                schede_data = []
                for dati_scheda in dati_sezione.schede.all():
                    schede_data.append({
                        'scheda_id': dati_scheda.scheda_id,
                        'scheda_nome': dati_scheda.scheda.nome,
                        'voti': dati_scheda.voti or {}
                    })

                data.append({
                    'id': sezione.id,
                    'tipo': 'sezione',
                    'numero': sezione.numero,
                    'denominazione': sezione.denominazione,
                    'indirizzo': sezione.indirizzo,
                    'totale_elettori': totale_elettori,
                    'totale_votanti': totale_votanti,
                    'affluenza_percentuale': affluenza,
                    'is_complete': dati_sezione.is_complete,
                    'schede': schede_data
                })
            except DatiSezione.DoesNotExist:
                # No data yet
                data.append({
                    'id': sezione.id,
                    'tipo': 'sezione',
                    'numero': sezione.numero,
                    'denominazione': sezione.denominazione,
                    'indirizzo': sezione.indirizzo,
                    'totale_elettori': 0,
                    'totale_votanti': 0,
                    'affluenza_percentuale': 0,
                    'is_complete': False,
                    'schede': []
                })

        breadcrumbs = [
            {'tipo': 'root', 'nome': 'Italia'},
            {'tipo': 'regione', 'id': regione.id, 'nome': regione.nome},
            {'tipo': 'provincia', 'id': provincia.id, 'nome': provincia.nome},
            {'tipo': 'comune', 'id': comune.id, 'nome': comune.nome}
        ]

        if municipio:
            breadcrumbs.append({'tipo': 'municipio', 'id': municipio.id, 'nome': municipio.nome})

        return Response({
            'level': 'sezioni',
            'consultazione_id': consultazione.id,
            'regione_id': regione.id,
            'provincia_id': provincia.id,
            'comune_id': comune.id,
            'municipio_id': municipio.id if municipio else None,
            'breadcrumbs': breadcrumbs,
            'summary': summary,
            'items': data
        })

    def _aggregate_sezioni(self, sezioni_qs, consultazione):
        """
        Aggregate data for a set of sezioni.
        Returns: totale_elettori, totale_votanti, affluenza_percentuale, sezioni_complete, totale_sezioni, schede_aggregate
        """
        dati_sezioni = DatiSezione.objects.filter(
            sezione__in=sezioni_qs,
            consultazione=consultazione
        )

        # Aggregate elettori and votanti
        aggregated = dati_sezioni.aggregate(
            totale_elettori_m=Coalesce(Sum('elettori_maschi'), 0),
            totale_elettori_f=Coalesce(Sum('elettori_femmine'), 0),
            totale_votanti_m=Coalesce(Sum('votanti_maschi'), 0),
            totale_votanti_f=Coalesce(Sum('votanti_femmine'), 0),
            sezioni_complete=Count('id', filter=Q(is_complete=True))
        )

        totale_elettori = aggregated['totale_elettori_m'] + aggregated['totale_elettori_f']
        totale_votanti = aggregated['totale_votanti_m'] + aggregated['totale_votanti_f']
        affluenza = round((totale_votanti / totale_elettori * 100), 2) if totale_elettori > 0 else 0

        # Aggregate schede results
        schede = SchedaElettorale.objects.filter(tipo_elezione__consultazione=consultazione)
        schede_aggregate = []

        for scheda in schede:
            # For referendum: aggregate SI/NO
            if scheda.schema_voti and scheda.schema_voti.get('tipo') == 'si_no':
                dati_schede = DatiScheda.objects.filter(
                    dati_sezione__sezione__in=sezioni_qs,
                    dati_sezione__consultazione=consultazione,
                    scheda=scheda
                )

                totale_si = 0
                totale_no = 0
                for ds in dati_schede:
                    if ds.voti:
                        # Handle None values explicitly (some records may have voti={'si': None})
                        totale_si += ds.voti.get('si', 0) or 0
                        totale_no += ds.voti.get('no', 0) or 0

                schede_aggregate.append({
                    'scheda_id': scheda.id,
                    'scheda_nome': scheda.nome,
                    'voti': {'si': totale_si, 'no': totale_no}
                })
            # For elections: aggregate by list
            else:
                # TODO: Implement aggregation for liste/candidati
                schede_aggregate.append({
                    'scheda_id': scheda.id,
                    'scheda_nome': scheda.nome,
                    'voti': {}  # Placeholder
                })

        return {
            'totale_sezioni': sezioni_qs.count(),
            'sezioni_complete': aggregated['sezioni_complete'],
            'totale_elettori': totale_elettori,
            'totale_votanti': totale_votanti,
            'affluenza_percentuale': affluenza,
            'schede': schede_aggregate
        }
