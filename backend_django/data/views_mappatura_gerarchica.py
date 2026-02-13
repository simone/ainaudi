"""
MappaturaGerarchica API View
Navigazione gerarchica per mappatura RDL → Sezioni
Struttura: Regione → Provincia → Comune → Municipio → Sezione
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.db.models import Count, Q, OuterRef, Subquery, Exists
from core.permissions import CanManageMappatura
from territory.models import Regione, Provincia, Comune, Municipio, SezioneElettorale
from elections.models import ConsultazioneElettorale
from data.models import SectionAssignment
from data.views import get_locked_assignments
from campaign.models import RdlRegistration
from delegations.permissions import get_sezioni_filter_for_user


class MappaturaGerarchicaView(APIView):
    """
    Navigazione gerarchica per mappatura RDL-Sezioni

    Query params:
    - consultazione_id: ID consultazione (required)
    - level: regione|provincia|comune|municipio|sezione (default: regione)
    - regione_id: Filter by regione
    - provincia_id: Filter by provincia
    - comune_id: Filter by comune
    - municipio_id: Filter by municipio
    - search: Search term per filtrare
    """

    permission_classes = [permissions.IsAuthenticated, CanManageMappatura]

    def get(self, request):
        consultazione_id = request.query_params.get('consultazione_id')
        if not consultazione_id:
            return Response({'error': 'consultazione_id required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            consultazione = ConsultazioneElettorale.objects.get(id=consultazione_id)
        except ConsultazioneElettorale.DoesNotExist:
            return Response({'error': 'Consultazione not found'}, status=status.HTTP_404_NOT_FOUND)

        # Get user's accessible sections (use empty Q() if None = no restrictions)
        sezioni_filter = get_sezioni_filter_for_user(request.user, consultazione_id) or Q()

        search = request.query_params.get('search', '').strip()

        # Get filters from path
        regione_id = request.query_params.get('regione_id')
        provincia_id = request.query_params.get('provincia_id')
        comune_id = request.query_params.get('comune_id')
        municipio_id = request.query_params.get('municipio_id')

        # Deduce level from path parameters
        if municipio_id:
            return self._get_sezioni(sezioni_filter, consultazione, comune_id, municipio_id, search)
        elif comune_id:
            # Check if comune has municipi
            has_municipi = Municipio.objects.filter(comune_id=comune_id).exists()
            if has_municipi:
                return self._get_municipi(sezioni_filter, consultazione, comune_id, search)
            else:
                return self._get_sezioni(sezioni_filter, consultazione, comune_id, None, search)
        elif provincia_id:
            return self._get_comuni(sezioni_filter, consultazione, provincia_id, search)
        elif regione_id:
            return self._get_province(sezioni_filter, consultazione, regione_id, search)
        else:
            return self._get_regioni(sezioni_filter, consultazione, search)

    def _get_regioni(self, sezioni_filter, consultazione, search):
        """Regioni con statistiche assegnazioni"""

        # Get accessible sezioni
        accessible_sezioni = SezioneElettorale.objects.filter(
            sezioni_filter,
            is_attiva=True
        )

        # Aggregate by regione
        regioni = Regione.objects.filter(
            province__comuni__sezioni__in=accessible_sezioni
        ).distinct()

        if search:
            regioni = regioni.filter(nome__icontains=search)

        regioni = regioni.order_by('nome')

        result = []
        for regione in regioni:
            # Count sezioni in this regione
            sezioni_regione = accessible_sezioni.filter(
                comune__provincia__regione=regione
            )

            totale_sezioni = sezioni_regione.count()

            # Count assigned sezioni
            sezioni_assegnate = sezioni_regione.filter(
                Exists(
                    SectionAssignment.objects.filter(
                        sezione=OuterRef('pk'),
                        consultazione=consultazione,
                        rdl_registration__isnull=False
                    )
                )
            ).count()

            sezioni_non_assegnate = totale_sezioni - sezioni_assegnate
            percentuale = (sezioni_assegnate / totale_sezioni * 100) if totale_sezioni > 0 else 0

            # Count available RDL (approved and in this regione)
            rdl_disponibili = RdlRegistration.objects.filter(
                status='APPROVED',
                comune__provincia__regione=regione
            ).exclude(
                # Exclude RDL already assigned to a section for this consultazione
                Exists(
                    SectionAssignment.objects.filter(
                        rdl_registration=OuterRef('pk'),
                        consultazione=consultazione
                    )
                )
            ).count()

            result.append({
                'id': regione.id,
                'tipo': 'regione',
                'nome': regione.nome,
                'codice': regione.codice_istat,
                'totale_sezioni': totale_sezioni,
                'sezioni_assegnate': sezioni_assegnate,
                'sezioni_non_assegnate': sezioni_non_assegnate,
                'percentuale_assegnazione': round(percentuale, 1),
                'rdl_disponibili': rdl_disponibili
            })

        # Summary totals
        totale_sezioni_all = sum(r['totale_sezioni'] for r in result)
        sezioni_assegnate_all = sum(r['sezioni_assegnate'] for r in result)
        sezioni_non_assegnate_all = sum(r['sezioni_non_assegnate'] for r in result)
        rdl_disponibili_all = sum(r['rdl_disponibili'] for r in result)
        percentuale_all = (sezioni_assegnate_all / totale_sezioni_all * 100) if totale_sezioni_all > 0 else 0

        return Response({
            'level': 'regioni',
            'items': result,
            'auto_skip': len(result) == 1,  # Skip if only one regione
            'summary': {
                'tipo': 'Nazionale',
                'nome': 'Italia',
                'totale_sezioni': totale_sezioni_all,
                'sezioni_assegnate': sezioni_assegnate_all,
                'sezioni_non_assegnate': sezioni_non_assegnate_all,
                'percentuale_assegnazione': round(percentuale_all, 1),
                'rdl_disponibili': rdl_disponibili_all
            }
        })

    def _get_province(self, sezioni_filter, consultazione, regione_id, search):
        """Province con statistiche assegnazioni"""

        if not regione_id:
            return Response({'error': 'regione_id required'}, status=status.HTTP_400_BAD_REQUEST)

        accessible_sezioni = SezioneElettorale.objects.filter(
            sezioni_filter,
            is_attiva=True,
            comune__provincia__regione_id=regione_id
        )

        province = Provincia.objects.filter(
            regione_id=regione_id,
            comuni__sezioni__in=accessible_sezioni
        ).distinct()

        if search:
            province = province.filter(nome__icontains=search)

        province = province.order_by('nome')

        result = []
        for provincia in province:
            sezioni_provincia = accessible_sezioni.filter(
                comune__provincia=provincia
            )

            totale_sezioni = sezioni_provincia.count()

            sezioni_assegnate = sezioni_provincia.filter(
                Exists(
                    SectionAssignment.objects.filter(
                        sezione=OuterRef('pk'),
                        consultazione=consultazione,
                        rdl_registration__isnull=False
                    )
                )
            ).count()

            sezioni_non_assegnate = totale_sezioni - sezioni_assegnate
            percentuale = (sezioni_assegnate / totale_sezioni * 100) if totale_sezioni > 0 else 0

            # Count available RDL
            rdl_disponibili = RdlRegistration.objects.filter(
                status='APPROVED',
                comune__provincia=provincia
            ).exclude(
                Exists(
                    SectionAssignment.objects.filter(
                        rdl_registration=OuterRef('pk'),
                        consultazione=consultazione
                    )
                )
            ).count()

            result.append({
                'id': provincia.id,
                'tipo': 'provincia',
                'nome': provincia.nome,
                'sigla': provincia.sigla,
                'codice': provincia.codice_istat,
                'totale_sezioni': totale_sezioni,
                'sezioni_assegnate': sezioni_assegnate,
                'sezioni_non_assegnate': sezioni_non_assegnate,
                'percentuale_assegnazione': round(percentuale, 1),
                'rdl_disponibili': rdl_disponibili
            })

        totale_sezioni_all = sum(r['totale_sezioni'] for r in result)
        sezioni_assegnate_all = sum(r['sezioni_assegnate'] for r in result)
        rdl_disponibili_all = sum(r['rdl_disponibili'] for r in result)
        sezioni_non_assegnate_all = sum(r['sezioni_non_assegnate'] for r in result)
        percentuale_all = (sezioni_assegnate_all / totale_sezioni_all * 100) if totale_sezioni_all > 0 else 0

        # Get regione name for breadcrumb
        regione = Regione.objects.get(id=regione_id)

        return Response({
            'level': 'province',
            'items': result,
            'auto_skip': len(result) == 1,  # Skip if only one provincia
            'summary': {
                'tipo': 'Regione',
                'nome': regione.nome,
                'totale_sezioni': totale_sezioni_all,
                'sezioni_assegnate': sezioni_assegnate_all,
                'sezioni_non_assegnate': sezioni_non_assegnate_all,
                'percentuale_assegnazione': round(percentuale_all, 1),
                'rdl_disponibili': rdl_disponibili_all
            }
        })

    def _get_comuni(self, sezioni_filter, consultazione, provincia_id, search):
        """Comuni con statistiche assegnazioni"""

        if not provincia_id:
            return Response({'error': 'provincia_id required'}, status=status.HTTP_400_BAD_REQUEST)

        accessible_sezioni = SezioneElettorale.objects.filter(
            sezioni_filter,
            is_attiva=True,
            comune__provincia_id=provincia_id
        )

        comuni = Comune.objects.filter(
            provincia_id=provincia_id,
            sezioni__in=accessible_sezioni
        ).distinct()

        if search:
            comuni = comuni.filter(nome__icontains=search)

        comuni = comuni.order_by('nome')

        result = []
        for comune in comuni:
            sezioni_comune = accessible_sezioni.filter(comune=comune)

            totale_sezioni = sezioni_comune.count()

            sezioni_assegnate = sezioni_comune.filter(
                Exists(
                    SectionAssignment.objects.filter(
                        sezione=OuterRef('pk'),
                        consultazione=consultazione,
                        rdl_registration__isnull=False
                    )
                )
            ).count()

            sezioni_non_assegnate = totale_sezioni - sezioni_assegnate
            percentuale = (sezioni_assegnate / totale_sezioni * 100) if totale_sezioni > 0 else 0

            # Count designazioni CONFERMATE per questo comune
            from delegations.models import DesignazioneRDL
            designazioni_confermate = DesignazioneRDL.objects.filter(
                sezione__in=sezioni_comune,
                stato='CONFERMATA',
                is_attiva=True
            ).values('sezione_id').distinct().count()

            # Mappature nuove = sezioni mappate MA NON designate
            mappature_nuove = sezioni_assegnate - designazioni_confermate

            # Check if comune has municipi
            has_municipi = Municipio.objects.filter(comune=comune).exists()

            # Count available RDL
            rdl_disponibili = RdlRegistration.objects.filter(
                status='APPROVED',
                comune=comune
            ).exclude(
                Exists(
                    SectionAssignment.objects.filter(
                        rdl_registration=OuterRef('pk'),
                        consultazione=consultazione
                    )
                )
            ).count()

            result.append({
                'id': comune.id,
                'tipo': 'comune',
                'nome': comune.nome,
                'codice': comune.codice_istat,
                'has_municipi': has_municipi,
                'totale_sezioni': totale_sezioni,
                'sezioni_assegnate': sezioni_assegnate,
                'sezioni_non_assegnate': sezioni_non_assegnate,
                'percentuale_assegnazione': round(percentuale, 1),
                'rdl_disponibili': rdl_disponibili,
                'designazioni_confermate': designazioni_confermate,
                'mappature_nuove': mappature_nuove
            })

        # Ordina per mappature nuove (priorità alta), poi per RDL disponibili, poi per nome
        result.sort(key=lambda x: (-x['mappature_nuove'], -x['rdl_disponibili'], x['nome']))

        totale_sezioni_all = sum(r['totale_sezioni'] for r in result)
        sezioni_assegnate_all = sum(r['sezioni_assegnate'] for r in result)
        sezioni_non_assegnate_all = sum(r['sezioni_non_assegnate'] for r in result)
        rdl_disponibili_all = sum(r['rdl_disponibili'] for r in result)
        percentuale_all = (sezioni_assegnate_all / totale_sezioni_all * 100) if totale_sezioni_all > 0 else 0

        # Get provincia name for breadcrumb
        provincia = Provincia.objects.get(id=provincia_id)

        return Response({
            'level': 'comuni',
            'items': result,
            'auto_skip': len(result) == 1,  # Skip if only one comune
            'summary': {
                'tipo': 'Provincia di',
                'nome': provincia.nome,
                'totale_sezioni': totale_sezioni_all,
                'sezioni_assegnate': sezioni_assegnate_all,
                'sezioni_non_assegnate': sezioni_non_assegnate_all,
                'percentuale_assegnazione': round(percentuale_all, 1),
                'rdl_disponibili': rdl_disponibili_all
            }
        })

    def _get_municipi(self, sezioni_filter, consultazione, comune_id, search):
        """Municipi con statistiche assegnazioni"""

        if not comune_id:
            return Response({'error': 'comune_id required'}, status=status.HTTP_400_BAD_REQUEST)

        accessible_sezioni = SezioneElettorale.objects.filter(
            sezioni_filter,
            is_attiva=True,
            comune_id=comune_id
        )

        # Get ALL municipi for this comune (not just those with sezioni already assigned)
        municipi = Municipio.objects.filter(
            comune_id=comune_id
        )

        if search:
            municipi = municipi.filter(nome__icontains=search)

        municipi = municipi.order_by('numero')

        result = []
        for municipio in municipi:
            sezioni_municipio = accessible_sezioni.filter(municipio=municipio)

            totale_sezioni = sezioni_municipio.count()

            sezioni_assegnate = sezioni_municipio.filter(
                Exists(
                    SectionAssignment.objects.filter(
                        sezione=OuterRef('pk'),
                        consultazione=consultazione,
                        rdl_registration__isnull=False
                    )
                )
            ).count()

            sezioni_non_assegnate = totale_sezioni - sezioni_assegnate
            percentuale = (sezioni_assegnate / totale_sezioni * 100) if totale_sezioni > 0 else 0

            # Count available RDL for this municipio
            # Include: RDL with this specific municipio + RDL of same comune without municipio
            rdl_disponibili = RdlRegistration.objects.filter(
                status='APPROVED',
                comune_id=comune_id
            ).filter(
                Q(municipio=municipio) | Q(municipio__isnull=True)
            ).exclude(
                Exists(
                    SectionAssignment.objects.filter(
                        rdl_registration=OuterRef('pk'),
                        consultazione=consultazione
                    )
                )
            ).count()

            result.append({
                'id': municipio.id,
                'tipo': 'municipio',
                'nome': municipio.nome,
                'numero': municipio.numero,
                'totale_sezioni': totale_sezioni,
                'sezioni_assegnate': sezioni_assegnate,
                'sezioni_non_assegnate': sezioni_non_assegnate,
                'percentuale_assegnazione': round(percentuale, 1),
                'rdl_disponibili': rdl_disponibili
            })

        # Sort by RDL disponibili (descending), then by numero
        result.sort(key=lambda x: (-x['rdl_disponibili'], x['numero']))

        totale_sezioni_all = sum(r['totale_sezioni'] for r in result)
        sezioni_assegnate_all = sum(r['sezioni_assegnate'] for r in result)
        sezioni_non_assegnate_all = sum(r['sezioni_non_assegnate'] for r in result)
        percentuale_all = (sezioni_assegnate_all / totale_sezioni_all * 100) if totale_sezioni_all > 0 else 0

        # Get comune name for breadcrumb
        comune = Comune.objects.get(id=comune_id)

        # Count available RDL for this comune (RDL are registered per comune, not per municipio)
        rdl_disponibili_all = RdlRegistration.objects.filter(
            status='APPROVED',
            comune_id=comune_id
        ).exclude(
            Exists(
                SectionAssignment.objects.filter(
                    rdl_registration=OuterRef('pk'),
                    consultazione=consultazione
                )
            )
        ).count()

        return Response({
            'level': 'municipi',
            'items': result,
            'auto_skip': len(result) <= 1,  # Skip if 0 or 1 municipio
            'summary': {
                'tipo': 'Comune di',
                'nome': comune.nome,
                'totale_sezioni': totale_sezioni_all,
                'sezioni_assegnate': sezioni_assegnate_all,
                'sezioni_non_assegnate': sezioni_non_assegnate_all,
                'percentuale_assegnazione': round(percentuale_all, 1),
                'rdl_disponibili': rdl_disponibili_all
            }
        })

    def _get_sezioni(self, sezioni_filter, consultazione, comune_id, municipio_id, search):
        """Sezioni con dettaglio assegnazioni RDL"""

        if not comune_id:
            return Response({'error': 'comune_id required'}, status=status.HTTP_400_BAD_REQUEST)

        accessible_sezioni = SezioneElettorale.objects.filter(
            sezioni_filter,
            is_attiva=True,
            comune_id=comune_id
        )

        if municipio_id:
            # Show sections with this municipio OR sections without municipio (to be assigned)
            accessible_sezioni = accessible_sezioni.filter(
                Q(municipio_id=municipio_id) | Q(municipio__isnull=True)
            )

        accessible_sezioni = accessible_sezioni.select_related(
            'comune',
            'comune__provincia',
            'municipio'
        ).order_by('numero')

        # Prefetch assignments (indexed by sezione_id and role)
        from collections import defaultdict
        assignments_map = defaultdict(dict)
        for assignment in SectionAssignment.objects.filter(
            sezione__in=accessible_sezioni,
            consultazione=consultazione
        ).select_related('rdl_registration'):
            assignments_map[assignment.sezione_id][assignment.role] = assignment

        # Compute locks from confirmed designations
        sezioni_ids = [s.id for s in accessible_sezioni]
        locks_map = get_locked_assignments(sezioni_ids, consultazione)

        result = []
        for sezione in accessible_sezioni:
            # Search filter
            if search:
                search_lower = search.lower()
                if not (
                    search_lower in str(sezione.numero).lower() or
                    search_lower in (sezione.denominazione or '').lower() or
                    search_lower in (sezione.indirizzo or '').lower()
                ):
                    continue

            sez_assignments = assignments_map.get(sezione.id, {})

            rdl_effettivo = None
            rdl_supplente = None

            for role_key, label in [('RDL', 'effettivo'), ('SUPPLENTE', 'supplente')]:
                assignment = sez_assignments.get(role_key)
                if assignment and assignment.rdl_registration:
                    rdl = assignment.rdl_registration

                    # Costruisci domicilio completo (priorità: domicilio > residenza)
                    domicilio = ''
                    if rdl.comune_domicilio and rdl.indirizzo_domicilio:
                        domicilio = f"{rdl.indirizzo_domicilio}, {rdl.comune_domicilio}"
                    elif rdl.indirizzo_residenza and rdl.comune_residenza:
                        domicilio = f"{rdl.indirizzo_residenza}, {rdl.comune_residenza}"

                    rdl_info = {
                        'id': rdl.id,
                        'nome': rdl.nome,
                        'cognome': rdl.cognome,
                        'email': rdl.email,
                        'telefono': rdl.telefono or '',
                        'data_nascita': rdl.data_nascita.strftime('%d/%m/%Y') if rdl.data_nascita else '',
                        'luogo_nascita': rdl.comune_nascita or '',
                        'domicilio': domicilio
                    }

                    if label == 'effettivo':
                        rdl_effettivo = rdl_info
                    else:
                        rdl_supplente = rdl_info

            sezione_locks = locks_map.get(sezione.id, {})
            result.append({
                'id': sezione.id,
                'tipo': 'sezione',
                'numero': sezione.numero,
                'nome': sezione.denominazione or f"Sezione {sezione.numero}",
                'denominazione': sezione.denominazione or '',
                'indirizzo': sezione.indirizzo or '',
                'municipio': sezione.municipio.nome if sezione.municipio else None,
                'is_assegnata': rdl_effettivo is not None,
                'rdl_effettivo': rdl_effettivo,
                'rdl_supplente': rdl_supplente,
                'effettivo_locked': sezione_locks.get('RDL', False),
                'supplente_locked': sezione_locks.get('SUPPLENTE', False),
            })

        totale_sezioni = len(result)
        sezioni_assegnate = sum(1 for r in result if r['is_assegnata'])
        sezioni_non_assegnate = totale_sezioni - sezioni_assegnate
        percentuale = (sezioni_assegnate / totale_sezioni * 100) if totale_sezioni > 0 else 0

        # Get comune/municipio name for breadcrumb
        if municipio_id:
            municipio = Municipio.objects.get(id=municipio_id)
            nome_contesto = f"{municipio.comune.nome} - {municipio.nome}"
        else:
            comune = Comune.objects.get(id=comune_id)
            nome_contesto = comune.nome

        return Response({
            'level': 'sezioni',
            'items': result,
            'summary': {
                'tipo': 'Municipio' if municipio_id else 'Comune di',
                'nome': nome_contesto,
                'totale_sezioni': totale_sezioni,
                'sezioni_assegnate': sezioni_assegnate,
                'sezioni_non_assegnate': sezioni_non_assegnate,
                'percentuale_assegnazione': round(percentuale, 1)
            },
            'filters': {
                'comune_id': comune_id,
                'municipio_id': municipio_id
            }
        })
