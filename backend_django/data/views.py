"""
Views for sections API endpoints.
Only exposes endpoints needed by the frontend.
"""
import csv
import io
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from django.db.models import Q
from django.db import transaction

from core.permissions import (
    CanManageRDL, HasScrutinioAccess, CanManageDelegations, CanManageMappatura,
    CanManageTerritory
)
from .models import SectionAssignment, DatiSezione, DatiScheda
from campaign.models import RdlRegistration
from elections.models import ConsultazioneElettorale
from territory.models import SezioneElettorale, Comune, Municipio
from delegations.models import DesignazioneRDL


def get_consultazione_attiva():
    """Get the currently active consultation."""
    return ConsultazioneElettorale.objects.filter(is_attiva=True).first()


def resolve_comune_id(value):
    """
    Resolve comune_id from various formats:
    - numeric ID (1, "1")
    - comune name ("Roma", "Milano")
    Returns the numeric ID or None if not found.
    """
    if not value:
        return None

    # Try numeric ID first
    try:
        return int(value)
    except (ValueError, TypeError):
        pass

    # Try by name (case-insensitive)
    comune = Comune.objects.filter(nome__iexact=value).first()
    if comune:
        return comune.id

    return None


def get_locked_assignments(sezione_ids, consultazione):
    """
    Restituisce un dict {sezione_id: {'RDL': bool, 'SUPPLENTE': bool}}
    indicando quali ruoli sono bloccati da designazioni confermate.
    Un assignment è bloccato se corrisponde a una designazione CONFERMATA attiva.
    """
    if not sezione_ids:
        return {}

    designazioni = DesignazioneRDL.objects.filter(
        sezione_id__in=sezione_ids,
        stato='CONFERMATA',
        is_attiva=True,
    ).filter(
        Q(delegato__consultazione=consultazione) |
        Q(sub_delega__delegato__consultazione=consultazione)
    ).values('sezione_id', 'effettivo_email', 'supplente_email')

    # Carica gli assignment correnti per queste sezioni
    assignments = SectionAssignment.objects.filter(
        sezione_id__in=sezione_ids,
        consultazione=consultazione,
    ).select_related('rdl_registration')

    # Mappa: sezione_id -> {role -> email}
    assignment_emails = {}
    for a in assignments:
        if a.rdl_registration:
            assignment_emails.setdefault(a.sezione_id, {})[a.role] = a.rdl_registration.email.lower()

    locks = {}
    for d in designazioni:
        sid = d['sezione_id']
        curr = assignment_emails.get(sid, {})
        eff_locked = bool(
            d['effettivo_email'] and
            curr.get('RDL', '').lower() == d['effettivo_email'].lower()
        )
        sup_locked = bool(
            d['supplente_email'] and
            curr.get('SUPPLENTE', '').lower() == d['supplente_email'].lower()
        )
        # Merge: if multiple designazioni exist, any lock wins
        existing = locks.get(sid, {'RDL': False, 'SUPPLENTE': False})
        locks[sid] = {
            'RDL': existing['RDL'] or eff_locked,
            'SUPPLENTE': existing['SUPPLENTE'] or sup_locked,
        }
    return locks


def is_assignment_locked(sezione, consultazione, role, rdl_registration):
    """
    Check if a specific assignment is locked by a confirmed designation.
    Returns (bool, designated_email) tuple.
    """
    email_field = 'effettivo_email' if role == 'RDL' else 'supplente_email'

    designazione = DesignazioneRDL.objects.filter(
        sezione=sezione,
        stato='CONFERMATA',
        is_attiva=True,
    ).filter(
        Q(delegato__consultazione=consultazione) |
        Q(sub_delega__delegato__consultazione=consultazione)
    ).exclude(**{email_field: ''}).exclude(**{email_field: None}).first()

    if not designazione:
        return False, None

    designated_email = getattr(designazione, email_field, '')
    if designated_email and rdl_registration and rdl_registration.email.lower() == designated_email.lower():
        return True, designated_email

    return False, None


def parse_municipio_number(value):
    """
    Parse municipio number from various formats:
    - "Municipio XV" (Roman numeral)
    - "Municipio 15" (Arabic)
    - "15" or "XV" (just the number)
    Returns int or 0 if parsing fails.
    """
    if not value:
        return 0

    # Roman numeral mapping
    roman_to_int = {
        'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
        'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10,
        'XI': 11, 'XII': 12, 'XIII': 13, 'XIV': 14, 'XV': 15,
        'XVI': 16, 'XVII': 17, 'XVIII': 18, 'XIX': 19, 'XX': 20
    }

    # Extract the number part
    num_part = value.replace('Municipio ', '').strip().upper()

    # Try Roman numeral first
    if num_part in roman_to_int:
        return roman_to_int[num_part]

    # Try Arabic numeral
    try:
        return int(num_part)
    except ValueError:
        return 0


def get_candidates_and_lists(consultazione):
    """Get ordered list of candidate names and list names for the consultation."""
    from elections.models import Candidato, ListaElettorale

    candidates = list(Candidato.objects.filter(
        lista__scheda__tipo_elezione__consultazione=consultazione
    ).order_by('lista', 'posizione_lista').values_list('cognome', 'nome'))
    candidate_names = [f"{c[0]} {c[1]}" for c in candidates]

    list_names = list(ListaElettorale.objects.filter(
        scheda__tipo_elezione__consultazione=consultazione
    ).order_by('ordine_scheda').values_list('nome', flat=True))

    return candidate_names, list_names


def get_scheda_turno_attivo(consultazione):
    """
    Get the scheda for the active turno based on today's date.

    Logic:
    - If today >= data_inizio_turno of a turno=2 scheda, return that scheda
    - Otherwise return the turno=1 scheda
    - Falls back to first available scheda if turno fields not set
    """
    from elections.models import SchedaElettorale
    from datetime import date

    today = date.today()

    # Get all schede for this consultazione ordered by turno desc (2 first, then 1)
    schede = SchedaElettorale.objects.filter(
        tipo_elezione__consultazione=consultazione
    ).order_by('-turno', 'ordine')

    # First check if there's a turno=2 scheda with data_inizio_turno <= today
    for scheda in schede:
        if scheda.turno == 2 and scheda.data_inizio_turno:
            if today >= scheda.data_inizio_turno:
                return scheda

    # Otherwise return the first turno=1 scheda (or any scheda if none with turno=1)
    turno1 = schede.filter(turno=1).first()
    if turno1:
        return turno1

    # Fallback to first scheda
    return schede.first()


def section_to_legacy_values(dati_sezione, candidate_names, list_names, scheda_attiva=None):
    """
    Convert DatiSezione to legacy values array format.
    Format: [
        0: nElettoriMaschi,
        1: nElettoriDonne,
        2: schedeRicevute,
        3: schedeAutenticate,
        4: nVotantiMaschi,
        5: nVotantiDonne,
        6: schedeBianche,
        7: schedeNulle,
        8: schedeContestate,
        9...: candidate votes OR votiSi/votiNo for referendum,
        ...: list votes,
        last: incongruenze
    ]

    Args:
        dati_sezione: The DatiSezione instance
        candidate_names: List of candidate names
        list_names: List of list names
        scheda_attiva: Optional SchedaElettorale for the active turno.
                       If provided, only returns data for that scheda's turno.
    """
    # Base values
    values = [
        dati_sezione.elettori_maschi or '',
        dati_sezione.elettori_femmine or '',
        '',  # schedeRicevute (from DatiScheda)
        '',  # schedeAutenticate (from DatiScheda)
        dati_sezione.votanti_maschi or '',
        dati_sezione.votanti_femmine or '',
        '',  # schedeBianche (from DatiScheda)
        '',  # schedeNulle (from DatiScheda)
        '',  # schedeContestate (from DatiScheda)
    ]

    # Get DatiScheda for the active turno's scheda (or first if not specified)
    if scheda_attiva:
        dati_scheda = dati_sezione.schede.filter(scheda=scheda_attiva).first()
    else:
        dati_scheda = dati_sezione.schede.first()
    if dati_scheda:
        values[2] = dati_scheda.schede_ricevute or ''
        values[3] = dati_scheda.schede_autenticate or ''
        values[6] = dati_scheda.schede_bianche or ''
        values[7] = dati_scheda.schede_nulle or ''
        values[8] = dati_scheda.schede_contestate or ''

        # Extract votes from JSON voti
        voti = dati_scheda.voti or {}

        # Check if referendum (no candidates/lists)
        is_referendum = len(candidate_names) == 0 and len(list_names) == 0

        if is_referendum:
            # Referendum: add votiSi and votiNo at indices 9 and 10
            referendum_voti = voti.get('referendum', {})
            values.append(referendum_voti.get('si') if referendum_voti.get('si') is not None else '')
            values.append(referendum_voti.get('no') if referendum_voti.get('no') is not None else '')
        else:
            # Regular election: candidate and list votes
            preferenze = voti.get('preferenze', {})
            liste = voti.get('liste', {})

            # Candidate votes in order
            for name in candidate_names:
                values.append(preferenze.get(name, ''))

            # List votes in order
            for name in list_names:
                values.append(liste.get(name, ''))
    else:
        # No data yet - add empty values
        is_referendum = len(candidate_names) == 0 and len(list_names) == 0
        if is_referendum:
            values.extend(['', ''])  # votiSi, votiNo
        else:
            values.extend(['' for _ in candidate_names])
            values.extend(['' for _ in list_names])

    # Add incongruenze at the end
    values.append(dati_scheda.errori_validazione if dati_scheda else '')

    return values


class SectionsStatsView(APIView):
    """
    Get statistics about sections for the current user's territory.

    GET /api/sections/stats

    Returns statistics filtered by user's delegation scope:
    - Totale Italia (sezioni, comuni)
    - Tue sezioni visibili (basate sulla catena deleghe)
    - Assegnate/Non assegnate
    - Dettaglio per comune
    - Dettaglio per municipio
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        consultazione = get_consultazione_attiva()

        # Get total stats for Italy
        totale_sezioni = SezioneElettorale.objects.filter(is_attiva=True).count()
        totale_comuni = Comune.objects.filter(sezioni__is_attiva=True).distinct().count()

        result = {
            'totale': {
                'sezioni': totale_sezioni,
                'comuni': totale_comuni,
            },
            'visibili': {
                'sezioni': 0,
                'assegnate': 0,
                'nonAssegnate': 0,
            },
            'perComune': {},
            'perMunicipio': {},
        }

        if not consultazione:
            return Response(result)

        # Get sections filter based on delegation chain
        from delegations.permissions import get_sezioni_filter_for_user

        sezioni_filter = get_sezioni_filter_for_user(request.user, consultazione.id)

        # If no filter (no access), return just totals
        if sezioni_filter is None:
            return Response(result)

        # Get visible sezioni with their assignments
        sezioni = SezioneElettorale.objects.filter(
            sezioni_filter,
            is_attiva=True
        ).select_related('comune', 'municipio')

        # Count assignments
        sezioni_ids = list(sezioni.values_list('id', flat=True))
        assigned_sezioni_ids = set(
            SectionAssignment.objects.filter(
                sezione_id__in=sezioni_ids,
                consultazione=consultazione,
            ).values_list('sezione_id', flat=True)
        )

        visibili_count = len(sezioni_ids)
        assegnate_count = len(assigned_sezioni_ids)

        result['visibili'] = {
            'sezioni': visibili_count,
            'assegnate': assegnate_count,
            'nonAssegnate': visibili_count - assegnate_count,
        }

        # Group by comune (with id and municipi)
        comuni_dict = {}
        per_municipio = {}

        for sezione in sezioni:
            comune = sezione.comune
            comune_id = comune.id
            is_assigned = sezione.id in assigned_sezioni_ids

            if comune_id not in comuni_dict:
                comuni_dict[comune_id] = {
                    'id': comune_id,
                    'nome': comune.nome,
                    'totale': 0,
                    'assegnate': 0,
                    'municipi_dict': {},
                }

            comuni_dict[comune_id]['totale'] += 1
            if is_assigned:
                comuni_dict[comune_id]['assegnate'] += 1

            # Track municipio for large cities
            if sezione.municipio:
                mun_num = sezione.municipio.numero
                mun_nome = sezione.municipio.nome

                # Global municipio stats
                if mun_num not in per_municipio:
                    per_municipio[mun_num] = {'visibili': 0, 'assegnate': 0}
                per_municipio[mun_num]['visibili'] += 1
                if is_assigned:
                    per_municipio[mun_num]['assegnate'] += 1

                # Per-comune municipio stats
                if mun_num not in comuni_dict[comune_id]['municipi_dict']:
                    comuni_dict[comune_id]['municipi_dict'][mun_num] = {
                        'numero': mun_num,
                        'nome': mun_nome,
                        'visibili': 0,
                        'assegnate': 0,
                    }
                comuni_dict[comune_id]['municipi_dict'][mun_num]['visibili'] += 1
                if is_assigned:
                    comuni_dict[comune_id]['municipi_dict'][mun_num]['assegnate'] += 1

        # Convert to array format expected by frontend
        comuni_list = []
        for comune_data in comuni_dict.values():
            # Convert municipi dict to sorted list
            municipi_list = sorted(
                comune_data['municipi_dict'].values(),
                key=lambda m: m['numero']
            )
            comuni_list.append({
                'id': comune_data['id'],
                'nome': comune_data['nome'],
                'totale': comune_data['totale'],
                'assegnate': comune_data['assegnate'],
                'municipi': municipi_list if municipi_list else None,
            })

        # Also keep perComune for backward compatibility
        per_comune = {c['nome']: {'totale': c['totale'], 'assegnate': c['assegnate']} for c in comuni_list}

        result['comuni'] = comuni_list
        result['perComune'] = per_comune
        result['perMunicipio'] = per_municipio

        return Response(result)


class SectionsUpdateView(APIView):
    """
    Update a section's indirizzo and denominazione.

    PATCH /api/sections/<id>/
    {
        "indirizzo": "Via Roma, 1",
        "denominazione": "Scuola Mazzini"
    }
    """
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        try:
            sezione = SezioneElettorale.objects.get(pk=pk)
        except SezioneElettorale.DoesNotExist:
            return Response({'error': 'Sezione non trovata'}, status=404)

        # Check user has permission based on delegation chain
        consultazione = get_consultazione_attiva()
        from delegations.permissions import get_sezioni_filter_for_user

        sezioni_filter = get_sezioni_filter_for_user(request.user, consultazione.id if consultazione else None)
        if sezioni_filter is not None:
            if not SezioneElettorale.objects.filter(sezioni_filter, pk=pk).exists():
                return Response({'error': 'Non hai i permessi per questa sezione'}, status=403)

        # Update allowed fields
        if 'indirizzo' in request.data:
            sezione.indirizzo = request.data['indirizzo']
        if 'denominazione' in request.data:
            sezione.denominazione = request.data['denominazione']

        sezione.save()

        return Response({
            'id': sezione.id,
            'numero': sezione.numero,
            'indirizzo': sezione.indirizzo,
            'denominazione': sezione.denominazione,
        })


class SectionsListView(APIView):
    """
    List sections for a comune with pagination.

    GET /api/sections/list/?comune_id=123&page=1&page_size=200

    Returns paginated list of sections filtered by user's delegation scope.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        comune_id = request.query_params.get('comune_id')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 200))

        if not comune_id:
            return Response({'error': 'comune_id è obbligatorio'}, status=400)

        consultazione = get_consultazione_attiva()

        # Get sections filter based on delegation chain
        from delegations.permissions import get_sezioni_filter_for_user

        sezioni_filter = get_sezioni_filter_for_user(request.user, consultazione.id if consultazione else None)

        # Build query
        queryset = SezioneElettorale.objects.filter(
            comune_id=comune_id,
            is_attiva=True
        ).select_related('municipio').order_by('numero')

        # Apply user's territory filter if any
        if sezioni_filter is not None:
            queryset = queryset.filter(sezioni_filter)

        # Count total
        total = queryset.count()

        # Paginate
        start = (page - 1) * page_size
        end = start + page_size
        sezioni = queryset[start:end]

        # Serialize
        results = []
        for sez in sezioni:
            results.append({
                'id': sez.id,
                'numero': sez.numero,
                'indirizzo': sez.indirizzo,
                'denominazione': sez.denominazione,
                'municipio': {
                    'numero': sez.municipio.numero,
                    'nome': sez.municipio.nome,
                } if sez.municipio else None,
            })

        return Response({
            'results': results,
            'count': total,
            'has_next': end < total,
            'page': page,
            'page_size': page_size,
        })


class SectionsOwnView(APIView):
    """
    Get sections assigned to the current user (as RDL).

    GET /api/sections/own

    Returns format expected by frontend: {rows: [{comune, sezione, email, values: [...]}]}
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        consultazione = get_consultazione_attiva()
        if not consultazione:
            return Response({'rows': []})

        candidate_names, list_names = get_candidates_and_lists(consultazione)

        # Get the scheda for the active turno (based on today's date)
        scheda_attiva = get_scheda_turno_attivo(consultazione)

        # Get user's section assignments for the active consultation
        assignments = SectionAssignment.objects.filter(
            rdl_registration__email=request.user.email,
            consultazione=consultazione,
        ).select_related(
            'sezione', 'sezione__comune', 'rdl_registration'
        )

        rows = []
        for assignment in assignments:
            sezione = assignment.sezione

            # Get or create DatiSezione for this section
            dati_sezione, _ = DatiSezione.objects.prefetch_related('schede').get_or_create(
                sezione=sezione,
                consultazione=consultazione
            )

            values = section_to_legacy_values(dati_sezione, candidate_names, list_names, scheda_attiva)

            rows.append({
                'comune': sezione.comune.nome,
                'sezione': sezione.numero,
                'email': request.user.email,
                'values': values,
            })

        # Include turno info in response
        turno_info = None
        if scheda_attiva:
            turno_info = {
                'turno': scheda_attiva.turno,
                'scheda_nome': scheda_attiva.nome,
                'is_ballottaggio': scheda_attiva.turno == 2,
            }

        return Response({'rows': rows, 'turno': turno_info})


class SectionsAssignedView(APIView):
    """
    Get sections assigned by the current user (as DELEGATE/SUBDELEGATE).

    GET /api/sections/assigned

    I permessi derivano dalla catena delle deleghe:
    - Delegato: vede tutte le sezioni
    - Sub-Delegato: vede solo le sezioni nei suoi comuni/municipi

    Returns format expected by frontend: {rows: [{comune, sezione, email, values: [...]}]}
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        consultazione = get_consultazione_attiva()
        if not consultazione:
            return Response({'rows': []})

        candidate_names, list_names = get_candidates_and_lists(consultazione)

        # Get the scheda for the active turno (based on today's date)
        scheda_attiva = get_scheda_turno_attivo(consultazione)

        # Get sections filter based on delegation chain
        from delegations.permissions import get_sezioni_filter_for_user

        sezioni_filter = get_sezioni_filter_for_user(request.user, consultazione.id)

        # If no access, return empty
        if sezioni_filter is None:
            return Response({'rows': []})

        # Get all sezioni with their assignments
        sezioni = SezioneElettorale.objects.filter(
            sezioni_filter,
            is_attiva=True
        ).select_related('comune')

        rows = []
        for sezione in sezioni:
            # Get assignment for this section
            assignment = SectionAssignment.objects.filter(
                sezione=sezione,
                consultazione=consultazione,
            ).select_related('rdl_registration').first()

            # Get or create DatiSezione
            dati_sezione = DatiSezione.objects.prefetch_related('schede').filter(
                sezione=sezione,
                consultazione=consultazione
            ).first()

            if dati_sezione:
                values = section_to_legacy_values(dati_sezione, candidate_names, list_names, scheda_attiva)
            else:
                # No data - create empty values
                values = [''] * (9 + len(candidate_names) + len(list_names) + 1)

            rows.append({
                'comune': sezione.comune.nome,
                'sezione': sezione.numero,
                'email': assignment.rdl_registration.email if assignment and assignment.rdl_registration else '',
                'values': values,
            })

        # Include turno info in response
        turno_info = None
        if scheda_attiva:
            turno_info = {
                'turno': scheda_attiva.turno,
                'scheda_nome': scheda_attiva.nome,
                'is_ballottaggio': scheda_attiva.turno == 2,
            }

        return Response({'rows': rows, 'turno': turno_info})


class SectionsSaveView(APIView):
    """
    Save section data.

    POST /api/sections
    {
        "comune": "ROMA",
        "sezione": 123,
        "values": [
            nElettoriMaschi,    # 0
            nElettoriDonne,     # 1
            schedeRicevute,     # 2
            schedeAutenticate,  # 3
            nVotantiMaschi,     # 4
            nVotantiDonne,      # 5
            schedeBianche,      # 6
            schedeNulle,        # 7
            schedeContestate,   # 8
            ...candidate_votes, # 9 to 9+len(candidates)-1
            ...list_votes,      # after candidates
            incongruenze        # last
        ]
    }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Save section voting data.

        Expected JSON format:
        {
            "comune": "Roma",
            "sezione": 123,
            "dati_sezione": {
                "elettori_maschi": 100,
                "elettori_femmine": 90,
                "votanti_maschi": 50,
                "votanti_femmine": 45
            },
            "dati_scheda": {
                "schede_ricevute": 200,
                "schede_autenticate": 195,
                "schede_bianche": 2,
                "schede_nulle": 1,
                "schede_contestate": 0,
                "voti_si": 45,           // Referendum only
                "voti_no": 50,           // Referendum only
                "preferenze": {...},     // Elections with candidates
                "liste": {...}           // Elections with lists
            },
            "errori": ["error1", "error2"]
        }
        """
        consultazione = get_consultazione_attiva()
        if not consultazione:
            return Response({'error': 'Nessuna consultazione attiva'}, status=400)

        comune_nome = request.data.get('comune')
        sezione_numero = request.data.get('sezione')
        dati_sezione_input = request.data.get('dati_sezione', {})
        dati_scheda_input = request.data.get('dati_scheda', {})
        errori = request.data.get('errori')

        if not comune_nome or sezione_numero is None:
            return Response({'error': 'comune e sezione sono obbligatori'}, status=400)

        # Find the sezione
        try:
            comune = Comune.objects.get(nome__iexact=comune_nome)
            sezione = SezioneElettorale.objects.get(comune=comune, numero=sezione_numero)
        except (Comune.DoesNotExist, SezioneElettorale.DoesNotExist):
            return Response({'error': 'Sezione non trovata'}, status=404)

        # Check user has permission based on delegation chain
        from delegations.permissions import can_enter_section_data

        if not can_enter_section_data(request.user, sezione, consultazione.id):
            return Response({'error': 'Non hai i permessi per questa sezione'}, status=403)

        # Get or create DatiSezione
        dati_sezione, created = DatiSezione.objects.get_or_create(
            sezione=sezione,
            consultazione=consultazione
        )

        # Update DatiSezione fields from structured input
        dati_sezione.elettori_maschi = dati_sezione_input.get('elettori_maschi')
        dati_sezione.elettori_femmine = dati_sezione_input.get('elettori_femmine')
        dati_sezione.votanti_maschi = dati_sezione_input.get('votanti_maschi')
        dati_sezione.votanti_femmine = dati_sezione_input.get('votanti_femmine')

        dati_sezione.inserito_da_email = request.user.email
        dati_sezione.inserito_at = timezone.now()

        # Check if complete
        dati_sezione.is_complete = all([
            dati_sezione.elettori_maschi is not None,
            dati_sezione.elettori_femmine is not None,
            dati_sezione.votanti_maschi is not None,
            dati_sezione.votanti_femmine is not None,
        ])

        dati_sezione.save()

        # Get the scheda for the active turno based on today's date
        scheda = get_scheda_turno_attivo(consultazione)

        if scheda:
            dati_scheda, _ = DatiScheda.objects.get_or_create(
                dati_sezione=dati_sezione,
                scheda=scheda
            )

            # Update ballot-level data from structured input
            dati_scheda.schede_ricevute = dati_scheda_input.get('schede_ricevute')
            dati_scheda.schede_autenticate = dati_scheda_input.get('schede_autenticate')
            dati_scheda.schede_bianche = dati_scheda_input.get('schede_bianche')
            dati_scheda.schede_nulle = dati_scheda_input.get('schede_nulle')
            dati_scheda.schede_contestate = dati_scheda_input.get('schede_contestate')

            # Build voti object
            voti = {}

            # Referendum votes (voti_si, voti_no)
            voti_si = dati_scheda_input.get('voti_si')
            voti_no = dati_scheda_input.get('voti_no')
            if voti_si is not None or voti_no is not None:
                voti['referendum'] = {
                    'si': voti_si,
                    'no': voti_no,
                }

            # Election preferenze (candidates)
            preferenze = dati_scheda_input.get('preferenze')
            if preferenze:
                voti['preferenze'] = preferenze

            # Election liste (lists)
            liste = dati_scheda_input.get('liste')
            if liste:
                voti['liste'] = liste

            dati_scheda.voti = voti if voti else None

            # Save errors
            if errori:
                dati_scheda.errori_validazione = ', '.join(errori) if isinstance(errori, list) else errori
            else:
                dati_scheda.errori_validazione = None

            dati_scheda.inserito_at = timezone.now()
            dati_scheda.save()

        return Response({'success': True, 'is_complete': dati_sezione.is_complete})


# =============================================================================
# SCRUTINIO ENDPOINTS (new structured API for vote data entry)
# =============================================================================

class ScrutinioInfoView(APIView):
    """
    Get scrutinio info: consultation details and all schede with their structure.

    GET /api/scrutinio/info

    Returns:
    {
        "consultazione": {
            "id": 1,
            "nome": "Referendum Costituzionale 2026",
            "data_inizio": "2026-06-08"
        },
        "schede": [
            {
                "id": 1,
                "nome": "Quesito 1 - Separazione Carriere",
                "colore": "#87CEEB",
                "ordine": 0,
                "tipo": "referendum",
                "schema": {"tipo": "si_no", "opzioni": ["SI", "NO"]}
            },
            ...
        ]
    }

    Permission: has_scrutinio_access (RDL, Delegato, SubDelegato)
    """
    permission_classes = [permissions.IsAuthenticated, HasScrutinioAccess]

    def get(self, request):
        from elections.models import SchedaElettorale, TipoElezione

        consultazione = get_consultazione_attiva()
        if not consultazione:
            return Response({'error': 'Nessuna consultazione attiva'}, status=400)

        # Get all schede for the current turno
        schede = SchedaElettorale.objects.filter(
            tipo_elezione__consultazione=consultazione
        ).select_related('tipo_elezione').order_by('ordine')

        schede_list = []
        for scheda in schede:
            schede_list.append({
                'id': scheda.id,
                'nome': scheda.nome,
                'colore': scheda.colore,
                'ordine': scheda.ordine,
                'turno': scheda.turno,
                'tipo_elezione': scheda.tipo_elezione.tipo,
                'tipo_elezione_display': scheda.tipo_elezione.get_tipo_display(),
                'schema': scheda.schema_voti,
                'testo_quesito': scheda.testo_quesito,
            })

        return Response({
            'consultazione': {
                'id': consultazione.id,
                'nome': consultazione.nome,
                'data_inizio': consultazione.data_inizio,
                'data_fine': consultazione.data_fine,
            },
            'schede': schede_list,
        })


class ScrutinioSezioniView(APIView):
    """
    Get user's sections with structured data organized by scheda.

    GET /api/scrutinio/sezioni?page=1&page_size=50

    Visibility:
    - RDL: sections assigned via SectionAssignment
    - Delegato/SubDelegato: all sections in their territory (paginated)

    Query params:
    - page: page number (default 1)
    - page_size: items per page (default 50, max 50)

    Returns:
    {
        "sezioni": [...],
        "total": 150,
        "page": 1,
        "page_size": 50,
        "has_more": true
    }

    Permission: has_scrutinio_access (RDL, Delegato, SubDelegato)
    """
    permission_classes = [permissions.IsAuthenticated, HasScrutinioAccess]

    def get(self, request):
        from elections.models import SchedaElettorale
        from delegations.permissions import get_sezioni_filter_for_user, get_user_delegation_roles

        consultazione = get_consultazione_attiva()
        if not consultazione:
            return Response({'sezioni': [], 'total': 0, 'page': 1, 'page_size': 50, 'has_more': False})

        # Pagination params
        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except (ValueError, TypeError):
            page = 1
        try:
            page_size = min(50, max(1, int(request.query_params.get('page_size', 50))))
        except (ValueError, TypeError):
            page_size = 50

        # Get all schede for the consultation
        schede = SchedaElettorale.objects.filter(
            tipo_elezione__consultazione=consultazione
        ).order_by('ordine')

        # Collect sezioni from multiple sources, tracking which are "mine"
        my_sezioni_ids = set()  # Sections assigned to me as RDL
        territory_sezioni_ids = set()  # Sections visible due to delegation territory

        # 1. RDL: sections from DesignazioneRDL (these are "mine")
        from delegations.models import DesignazioneRDL
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
            if sezioni_filter is not None:
                # Q() means "all sections" for superusers
                if sezioni_filter == Q():
                    # Don't load ALL sections for superuser in scrutinio
                    # They should use admin or specific filters
                    pass
                else:
                    # Solo sezioni mappate (con almeno un SectionAssignment)
                    mapped_sezioni_ids = set(SectionAssignment.objects.filter(
                        sezione__in=SezioneElettorale.objects.filter(
                            sezioni_filter, is_attiva=True
                        ),
                        consultazione=consultazione,
                    ).values_list('sezione_id', flat=True).distinct())
                    # Exclude sections already in my_sezioni_ids
                    territory_sezioni_ids.update(mapped_sezioni_ids - my_sezioni_ids)

        sezioni_ids = my_sezioni_ids | territory_sezioni_ids

        if not sezioni_ids:
            return Response({'sezioni': [], 'total': 0, 'page': page, 'page_size': page_size, 'has_more': False})

        # Total count
        total = len(sezioni_ids)

        # Load sezioni with pagination - "my" sections always first
        from django.db.models import Case, When, Value, IntegerField
        sezioni_qs = SezioneElettorale.objects.filter(
            id__in=sezioni_ids
        ).select_related('comune', 'municipio').annotate(
            is_mine_order=Case(
                When(id__in=my_sezioni_ids, then=Value(0)),
                default=Value(1),
                output_field=IntegerField()
            )
        ).order_by('is_mine_order', 'comune__nome', 'numero')

        # Apply pagination
        offset = (page - 1) * page_size
        sezioni_page = sezioni_qs[offset:offset + page_size]
        has_more = offset + page_size < total

        # Prefetch assignments (effettivo/supplente) for all sections in page
        sezioni_page_ids = [s.id for s in sezioni_page]
        assignments_by_sezione = {}
        for a in SectionAssignment.objects.filter(
            sezione_id__in=sezioni_page_ids,
            consultazione=consultazione,
        ).select_related('rdl_registration'):
            if a.rdl_registration:
                assignments_by_sezione.setdefault(a.sezione_id, {})[a.role] = {
                    'nome': f"{a.rdl_registration.cognome} {a.rdl_registration.nome}".strip(),
                    'email': a.rdl_registration.email,
                    'telefono': a.rdl_registration.telefono or '',
                }

        sezioni_list = []
        for sezione in sezioni_page:
            # Get or create DatiSezione
            dati_sezione, _ = DatiSezione.objects.prefetch_related('schede').get_or_create(
                sezione=sezione,
                consultazione=consultazione
            )

            # Build dati_seggio
            dati_seggio = {
                'elettori_maschi': dati_sezione.elettori_maschi,
                'elettori_femmine': dati_sezione.elettori_femmine,
                'votanti_maschi': dati_sezione.votanti_maschi,
                'votanti_femmine': dati_sezione.votanti_femmine,
            }

            # Build schede data
            schede_data = {}
            for scheda in schede:
                dati_scheda = dati_sezione.schede.filter(scheda=scheda).first()
                if dati_scheda:
                    schede_data[str(scheda.id)] = {
                        'schede_ricevute': dati_scheda.schede_ricevute,
                        'schede_autenticate': dati_scheda.schede_autenticate,
                        'schede_bianche': dati_scheda.schede_bianche,
                        'schede_nulle': dati_scheda.schede_nulle,
                        'schede_contestate': dati_scheda.schede_contestate,
                        'voti': dati_scheda.voti,
                        'errori': dati_scheda.errori_validazione,
                    }
                else:
                    schede_data[str(scheda.id)] = None

            sez_assignments = assignments_by_sezione.get(sezione.id, {})
            sezioni_list.append({
                'comune': sezione.comune.nome,
                'sezione': sezione.numero,
                'denominazione': sezione.denominazione,
                'indirizzo': sezione.indirizzo,
                'is_mia': sezione.id in my_sezioni_ids,
                'dati_seggio': dati_seggio,
                'schede': schede_data,
                'effettivo': sez_assignments.get('RDL'),
                'supplente': sez_assignments.get('SUPPLENTE'),
            })

        return Response({
            'sezioni': sezioni_list,
            'total': total,
            'total_mie': len(my_sezioni_ids),
            'total_territorio': len(territory_sezioni_ids),
            'page': page,
            'page_size': page_size,
            'has_more': has_more
        })


class ScrutinioSaveView(APIView):
    """
    Save scrutinio data with structured format.

    POST /api/scrutinio/save
    {
        "comune": "Roma",
        "sezione": 123,
        "dati_seggio": {
            "elettori_maschi": 500,
            "elettori_femmine": 520,
            "votanti_maschi": 250,
            "votanti_femmine": 260
        },
        "schede": {
            "1": {  // scheda_id
                "schede_ricevute": 1020,
                "schede_autenticate": 1018,
                "schede_bianche": 5,
                "schede_nulle": 3,
                "schede_contestate": 0,
                "voti": {"si": 300, "no": 200}
            },
            ...
        }
    }

    Permission: has_scrutinio_access (RDL, Delegato, SubDelegato)
    """
    permission_classes = [permissions.IsAuthenticated, HasScrutinioAccess]

    def post(self, request):
        from elections.models import SchedaElettorale
        from delegations.permissions import can_enter_section_data

        consultazione = get_consultazione_attiva()
        if not consultazione:
            return Response({'error': 'Nessuna consultazione attiva'}, status=400)

        comune_nome = request.data.get('comune')
        sezione_numero = request.data.get('sezione')
        dati_seggio = request.data.get('dati_seggio', {})
        schede_data = request.data.get('schede', {})

        if not comune_nome or sezione_numero is None:
            return Response({'error': 'comune e sezione sono obbligatori'}, status=400)

        # Find the sezione
        try:
            comune = Comune.objects.get(nome__iexact=comune_nome)
            sezione = SezioneElettorale.objects.get(comune=comune, numero=sezione_numero)
        except (Comune.DoesNotExist, SezioneElettorale.DoesNotExist):
            return Response({'error': 'Sezione non trovata'}, status=404)

        # Check permission
        if not can_enter_section_data(request.user, sezione, consultazione.id):
            return Response({'error': 'Non hai i permessi per questa sezione'}, status=403)

        with transaction.atomic():
            # Get or create DatiSezione
            dati_sezione, _ = DatiSezione.objects.get_or_create(
                sezione=sezione,
                consultazione=consultazione
            )

            # Update dati_seggio
            dati_sezione.elettori_maschi = dati_seggio.get('elettori_maschi')
            dati_sezione.elettori_femmine = dati_seggio.get('elettori_femmine')
            dati_sezione.votanti_maschi = dati_seggio.get('votanti_maschi')
            dati_sezione.votanti_femmine = dati_seggio.get('votanti_femmine')
            dati_sezione.inserito_da_email = request.user.email
            dati_sezione.inserito_at = timezone.now()

            # Check if complete
            dati_sezione.is_complete = all([
                dati_sezione.elettori_maschi is not None,
                dati_sezione.elettori_femmine is not None,
                dati_sezione.votanti_maschi is not None,
                dati_sezione.votanti_femmine is not None,
            ])

            dati_sezione.save()

            # Update each scheda
            for scheda_id, scheda_values in schede_data.items():
                if scheda_values is None:
                    continue

                try:
                    scheda = SchedaElettorale.objects.get(
                        id=int(scheda_id),
                        tipo_elezione__consultazione=consultazione
                    )
                except SchedaElettorale.DoesNotExist:
                    continue

                dati_scheda, _ = DatiScheda.objects.get_or_create(
                    dati_sezione=dati_sezione,
                    scheda=scheda
                )

                dati_scheda.schede_ricevute = scheda_values.get('schede_ricevute')
                dati_scheda.schede_autenticate = scheda_values.get('schede_autenticate')
                dati_scheda.schede_bianche = scheda_values.get('schede_bianche')
                dati_scheda.schede_nulle = scheda_values.get('schede_nulle')
                dati_scheda.schede_contestate = scheda_values.get('schede_contestate')
                dati_scheda.voti = scheda_values.get('voti')
                dati_scheda.errori_validazione = scheda_values.get('errori')
                dati_scheda.inserito_at = timezone.now()
                dati_scheda.save()

        return Response({
            'success': True,
            'is_complete': dati_sezione.is_complete
        })


# =============================================================================
# RDL ASSIGNMENT ENDPOINTS (for DELEGATE/SUBDELEGATE)
# =============================================================================

class RdlEmailsView(APIView):
    """
    Get list of available RDL emails for assignment.

    GET /api/rdl/emails

    Returns list of users who can be assigned as RDL.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from core.models import User
        from delegations.permissions import has_referenti_permission

        consultazione = get_consultazione_attiva()

        # Check user has referenti permission (from delegation chain)
        if not has_referenti_permission(request.user, consultazione.id if consultazione else None):
            return Response({'error': 'Non autorizzato'}, status=403)

        # Return all users (for now, could be filtered by role in future)
        users = User.objects.filter(is_active=True).values_list('email', flat=True)
        return Response({'emails': list(users)})


class RdlSectionsView(APIView):
    """
    Get all sections with their RDL assignments for the active consultation.

    GET /api/rdl/sections

    I permessi derivano dalla catena delle deleghe:
    - Delegato: vede tutte le sezioni
    - Sub-Delegato: vede solo le sezioni nei suoi comuni/municipi

    Returns format expected by frontend:
    {
        "assigned": [[sezione, comune, municipio, email], ...],
        "unassigned": [[sezione, comune, municipio, ""], ...]
    }
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        consultazione = get_consultazione_attiva()
        if not consultazione:
            return Response({'assigned': [], 'unassigned': []})

        # Get sections filter based on delegation chain
        from delegations.permissions import get_sezioni_filter_for_user, has_referenti_permission

        # Check if user can manage referenti
        if not has_referenti_permission(request.user, consultazione.id):
            return Response({'error': 'Non autorizzato'}, status=403)

        sezioni_filter = get_sezioni_filter_for_user(request.user, consultazione.id)

        # If no access, return empty
        if sezioni_filter is None:
            return Response({'assigned': [], 'unassigned': []})

        # Get all sezioni with their assignments
        sezioni = SezioneElettorale.objects.filter(
            sezioni_filter,
            is_attiva=True
        ).select_related('comune', 'comune__provincia', 'municipio').order_by('comune__nome', 'numero')

        assigned = []
        unassigned = []

        for sezione in sezioni:
            assignment = SectionAssignment.objects.filter(
                sezione=sezione,
                consultazione=consultazione,
            ).select_related('rdl_registration').first()

            municipio_str = f"Municipio {sezione.municipio.numero}" if sezione.municipio else ""
            email = assignment.rdl_registration.email if assignment and assignment.rdl_registration else ""

            # Format: [comune, sezione_numero, municipio, email] - matches frontend expectation
            row = [sezione.comune.nome, sezione.numero, municipio_str, email]

            if email:
                assigned.append(row)
            else:
                unassigned.append(row)

        return Response({'assigned': assigned, 'unassigned': unassigned})


class RdlAssignView(APIView):
    """
    Assign an RDL to a section.

    POST /api/rdl/assign
    {
        "comune": "ROMA",
        "sezione": 123,
        "email": "rdl@example.com"
    }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from core.models import User
        from delegations.permissions import has_referenti_permission, can_manage_sezione

        consultazione = get_consultazione_attiva()
        if not consultazione:
            return Response({'error': 'Nessuna consultazione attiva'}, status=400)

        # Check user has referenti permission (from delegation chain)
        if not has_referenti_permission(request.user, consultazione.id):
            return Response({'error': 'Non autorizzato'}, status=403)

        comune_nome = request.data.get('comune')
        sezione_numero = request.data.get('sezione')
        email = request.data.get('email')

        if not comune_nome or sezione_numero is None or not email:
            return Response({'error': 'comune, sezione e email sono obbligatori'}, status=400)

        # Find the sezione
        try:
            comune = Comune.objects.get(nome__iexact=comune_nome)
            sezione = SezioneElettorale.objects.get(comune=comune, numero=sezione_numero)
        except (Comune.DoesNotExist, SezioneElettorale.DoesNotExist):
            return Response({'error': 'Sezione non trovata'}, status=404)

        # Find or create the user (for role assignment)
        user, user_created = User.objects.get_or_create(
            email=email.lower(),
            defaults={'display_name': email.split('@')[0]}
        )

        # Find or create RdlRegistration for this email/comune
        from campaign.models import RdlRegistration
        rdl_reg, reg_created = RdlRegistration.objects.get_or_create(
            email=email.lower(),
            comune=comune,
            defaults={
                'nome': email.split('@')[0],
                'cognome': '',
                'telefono': '',
                'comune_nascita': comune.nome,
                'data_nascita': '1970-01-01',
                'comune_residenza': comune.nome,
                'indirizzo_residenza': '',
                'consultazione': consultazione,
                'status': 'APPROVED',
                'source': 'MANUAL',
            }
        )

        # Delete existing assignments
        SectionAssignment.objects.filter(
            sezione=sezione,
            consultazione=consultazione,
        ).delete()

        # Create new assignment
        assignment = SectionAssignment.objects.create(
            sezione=sezione,
            consultazione=consultazione,
            rdl_registration=rdl_reg,
            role=SectionAssignment.Role.RDL,
            assigned_by_email=request.user.email,
        )

        # Also assign RDL role to the user if not already assigned
        from core.models import RoleAssignment as CoreRoleAssignment
        CoreRoleAssignment.objects.get_or_create(
            user=user,
            role='RDL',
            defaults={
                'assigned_by_email': request.user.email,
                'is_active': True
            }
        )

        return Response({
            'success': True,
            'comune': sezione.comune.nome,
            'sezione': sezione.numero,
            'email': email.lower()
        })


class RdlUnassignView(APIView):
    """
    Remove RDL assignment from a section.

    POST /api/rdl/unassign
    {
        "comune": "ROMA",
        "sezione": 123
    }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from delegations.permissions import has_referenti_permission

        consultazione = get_consultazione_attiva()
        if not consultazione:
            return Response({'error': 'Nessuna consultazione attiva'}, status=400)

        # Check user has referenti permission (from delegation chain)
        if not has_referenti_permission(request.user, consultazione.id):
            return Response({'error': 'Non autorizzato'}, status=403)

        comune_nome = request.data.get('comune')
        sezione_numero = request.data.get('sezione')

        if not comune_nome or sezione_numero is None:
            return Response({'error': 'comune e sezione sono obbligatori'}, status=400)

        # Find the sezione
        try:
            comune = Comune.objects.get(nome__iexact=comune_nome)
            sezione = SezioneElettorale.objects.get(comune=comune, numero=sezione_numero)
        except (Comune.DoesNotExist, SezioneElettorale.DoesNotExist):
            return Response({'error': 'Sezione non trovata'}, status=404)

        # Delete existing assignments
        deleted, _ = SectionAssignment.objects.filter(
            sezione=sezione,
            consultazione=consultazione,
        ).delete()

        return Response({
            'success': True,
            'comune': sezione.comune.nome,
            'sezione': sezione.numero,
            'removed': deleted > 0
        })


# =============================================================================
# SECTIONS UPLOAD (CSV)
# =============================================================================

class SectionsUploadView(APIView):
    """
    Upload sections from CSV file.

    POST /api/sections/upload
    Content-Type: multipart/form-data

    CSV format:
    SEZIONE,COMUNE,MUNICIPIO,INDIRIZZO
    1,ROMA,3,"VIA DI SETTEBAGNI, 231"
    ...

    Only allowed for:
    - Superusers (via can_manage_territory)
    - ADMIN role
    - DELEGATE with scope on the comune being uploaded

    Permission: can_manage_territory (Superuser only)
    """
    permission_classes = [permissions.IsAuthenticated, CanManageTerritory]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        from core.models import RoleAssignment

        # Check if file was uploaded
        if 'file' not in request.FILES:
            return Response({'error': 'Nessun file caricato'}, status=400)

        file = request.FILES['file']

        # Check file extension
        if not file.name.endswith('.csv'):
            return Response({'error': 'Il file deve essere in formato CSV'}, status=400)

        # Parse CSV
        try:
            content = file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(content))
        except Exception as e:
            return Response({'error': f'Errore lettura CSV: {str(e)}'}, status=400)

        # Validate headers
        required_headers = {'SEZIONE', 'COMUNE', 'MUNICIPIO', 'INDIRIZZO'}
        if not required_headers.issubset(set(reader.fieldnames or [])):
            return Response({
                'error': f'Intestazioni richieste: {", ".join(required_headers)}. '
                         f'Trovate: {", ".join(reader.fieldnames or [])}'
            }, status=400)

        # Collect rows and validate
        rows = list(reader)
        if not rows:
            return Response({'error': 'Il file CSV è vuoto'}, status=400)

        # Get unique comuni from CSV
        comuni_names = set(row['COMUNE'].upper().strip() for row in rows)

        # Validate comuni exist
        comuni_map = {}
        for nome in comuni_names:
            try:
                comune = Comune.objects.get(nome__iexact=nome)
                comuni_map[nome] = comune
            except Comune.DoesNotExist:
                return Response({'error': f'Comune non trovato: {nome}'}, status=400)

        # Check permission for each comune
        for nome, comune in comuni_map.items():
            if not self._has_upload_permission(request.user, comune):
                return Response({
                    'error': f'Non hai i permessi per caricare sezioni per il comune: {nome}'
                }, status=403)

        # Process rows
        created = 0
        updated = 0
        errors = []

        with transaction.atomic():
            for i, row in enumerate(rows, start=2):  # Start at 2 (after header)
                try:
                    sezione_num = int(row['SEZIONE'].strip())
                    comune_nome = row['COMUNE'].upper().strip()
                    municipio_num = row['MUNICIPIO'].strip()
                    indirizzo = row['INDIRIZZO'].strip().strip('"')

                    comune = comuni_map[comune_nome]

                    # Find or create municipio if specified
                    municipio = None
                    if municipio_num:
                        try:
                            municipio_num = int(municipio_num)
                            municipio, _ = Municipio.objects.get_or_create(
                                comune=comune,
                                numero=municipio_num,
                                defaults={'nome': f'Municipio {municipio_num}'}
                            )
                        except ValueError:
                            pass  # Non-numeric municipio, skip

                    # Create or update sezione
                    sezione, was_created = SezioneElettorale.objects.update_or_create(
                        comune=comune,
                        numero=sezione_num,
                        defaults={
                            'municipio': municipio,
                            'indirizzo': indirizzo,
                            'is_attiva': True,
                        }
                    )

                    if was_created:
                        created += 1
                    else:
                        updated += 1

                except Exception as e:
                    errors.append(f'Riga {i}: {str(e)}')

        result = {
            'success': True,
            'created': created,
            'updated': updated,
            'total': created + updated,
        }

        if errors:
            result['errors'] = errors[:10]  # Limit errors shown
            if len(errors) > 10:
                result['errors'].append(f'... e altri {len(errors) - 10} errori')

        return Response(result)

    def _has_upload_permission(self, user, comune):
        """Check if user has permission to upload sections for this comune."""
        if user.is_superuser:
            return True

        from core.models import RoleAssignment

        # Check for ADMIN role
        if RoleAssignment.objects.filter(
            user=user,
            role='ADMIN',
        ).exists():
            return True

        # Check for DELEGATE role on this comune
        if RoleAssignment.objects.filter(
            user=user,
            role='DELEGATE',
            is_active=True,
            scope_comune=comune
        ).exists():
            return True

        # Check for DELEGATE role on the provincia
        if RoleAssignment.objects.filter(
            user=user,
            role='DELEGATE',
            is_active=True,
            scope_provincia=comune.provincia
        ).exists():
            return True

        # Check for DELEGATE role on the regione
        if RoleAssignment.objects.filter(
            user=user,
            role='DELEGATE',
            is_active=True,
            scope_regione=comune.provincia.regione
        ).exists():
            return True

        return False


# =============================================================================
# RDL REGISTRATION ENDPOINTS
# =============================================================================

class RdlRegistrationSelfView(APIView):
    """
    Self-registration for RDL candidates.

    POST /api/rdl/register
    {
        "email": "rdl@example.com",
        "nome": "Mario",
        "cognome": "Rossi",
        "telefono": "3331234567",
        "comune": "ROMA",
        "municipio": 5  // optional
    }

    This is a PUBLIC endpoint - no authentication required.
    Creates a PENDING registration that must be approved by a delegate.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from campaign.models import RdlRegistration
        from datetime import datetime

        email = request.data.get('email', '').lower().strip()
        nome = request.data.get('nome', '').strip()
        cognome = request.data.get('cognome', '').strip()
        telefono = request.data.get('telefono', '').strip()
        comune_nascita = request.data.get('comune_nascita', '').strip()
        data_nascita_str = request.data.get('data_nascita', '').strip()
        comune_residenza = request.data.get('comune_residenza', '').strip()
        indirizzo_residenza = request.data.get('indirizzo_residenza', '').strip()
        seggio_preferenza = request.data.get('seggio_preferenza', '').strip()
        # Fuorisede info
        fuorisede = request.data.get('fuorisede')
        comune_domicilio = request.data.get('comune_domicilio', '').strip()
        indirizzo_domicilio = request.data.get('indirizzo_domicilio', '').strip()
        comune_id = request.data.get('comune_id')
        comune_nome = request.data.get('comune', '').strip()
        municipio_num = request.data.get('municipio')

        # Validate required fields - accept either comune_id or comune name
        if not email or not nome or not cognome or not telefono or not (comune_id or comune_nome):
            return Response({
                'error': 'Email, nome, cognome, telefono e comune sono obbligatori'
            }, status=400)

        if not comune_nascita or not data_nascita_str or not comune_residenza or not indirizzo_residenza:
            return Response({
                'error': 'Comune di nascita, data di nascita, comune di residenza e indirizzo sono obbligatori'
            }, status=400)

        # Validate email format
        import re
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            return Response({'error': 'Email non valida'}, status=400)

        # Parse data_nascita
        data_nascita = None
        if data_nascita_str:
            try:
                data_nascita = datetime.strptime(data_nascita_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        # Find comune - support both comune_id (preferred) and comune name (legacy)
        try:
            if comune_id:
                comune = Comune.objects.prefetch_related('municipi').get(id=comune_id)
            elif comune_nome:
                comune = Comune.objects.prefetch_related('municipi').get(nome__iexact=comune_nome)
            else:
                return Response({'error': 'Comune non specificato'}, status=400)
        except Comune.DoesNotExist:
            return Response({'error': f'Comune non trovato: {comune_id or comune_nome}'}, status=404)

        # Check if municipio is required (comune has municipalities)
        has_municipi = comune.municipi.exists()
        if has_municipi and not municipio_num:
            return Response({'error': 'Il municipio è obbligatorio per questo comune'}, status=400)

        # Find municipio if specified
        municipio = None
        if municipio_num:
            municipio = Municipio.objects.filter(
                comune=comune,
                numero=municipio_num
            ).first()
            if has_municipi and not municipio:
                return Response({'error': f'Municipio {municipio_num} non trovato'}, status=400)

        # Create registration (allow duplicates - delegates will manage them)
        registration = RdlRegistration.objects.create(
            email=email,
            nome=nome,
            cognome=cognome,
            telefono=telefono,
            comune_nascita=comune_nascita,
            data_nascita=data_nascita,
            comune_residenza=comune_residenza,
            indirizzo_residenza=indirizzo_residenza,
            fuorisede=fuorisede,
            comune_domicilio=comune_domicilio,
            indirizzo_domicilio=indirizzo_domicilio,
            seggio_preferenza=seggio_preferenza,
            comune=comune,
            municipio=municipio,
            status=RdlRegistration.Status.PENDING,
            source='SELF'
        )

        return Response({
            'success': True,
            'message': 'Richiesta inviata. Riceverai una notifica quando sarà approvata.',
            'id': registration.id
        }, status=201)


class SezioniSearchPublicView(APIView):
    """
    PUBLIC endpoint for searching sezioni (sections) by comune.
    Used by RDL self-registration form for sezione autocomplete.

    GET /api/sections/search-public/?comune_id=1&q=numero
    Returns: [
        {"id": 1, "numero": 1, "denominazione": "Scuola...", "indirizzo": "Via..."},
        ...
    ]
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        comune_id = request.query_params.get('comune_id')
        q = request.query_params.get('q', '').strip()

        if not comune_id:
            return Response({'error': 'comune_id required'}, status=400)

        try:
            comune = Comune.objects.get(pk=comune_id)
        except Comune.DoesNotExist:
            return Response({'error': 'Comune not found'}, status=404)

        # Get all active sezioni for this comune
        sezioni = SezioneElettorale.objects.filter(
            comune=comune,
            is_attiva=True
        ).order_by('numero')

        # Filter by search query if provided
        if q:
            sezioni = sezioni.filter(
                Q(numero__icontains=q) |
                Q(denominazione__icontains=q) |
                Q(indirizzo__icontains=q)
            )

        # Limit to 20 results
        results = []
        for sezione in sezioni[:20]:
            results.append({
                'id': sezione.id,
                'numero': sezione.numero,
                'denominazione': sezione.denominazione or '',
                'indirizzo': sezione.indirizzo or '',
                'municipio': {
                    'numero': sezione.municipio.numero,
                    'nome': sezione.municipio.nome
                } if sezione.municipio else None,
            })

        return Response(results)


class RdlRegistrationListView(APIView):
    """
    List RDL registrations for delegates.

    GET /api/rdl/registrations?status=PENDING

    Returns registrations filtered by delegate's scope.
    Supports both Delegato/SubDelega and RoleAssignment permission systems.

    Permission: can_manage_rdl (Delegato, SubDelegato)
    """
    permission_classes = [permissions.IsAuthenticated, CanManageRDL]

    def get(self, request):
        from core.models import RoleAssignment
        from campaign.models import RdlRegistration
        from delegations.permissions import get_user_delegation_roles

        user = request.user
        registrations_filter = Q()
        has_global_access = False
        has_permission = False

        # 1. Superuser has global access
        if user.is_superuser:
            has_global_access = True
            has_permission = True

        # 2. Check delegation chain (Delegato / SubDelega) - PREFERRED
        if not has_permission:
            delegation_roles = get_user_delegation_roles(user)

            if delegation_roles['is_delegato']:
                has_permission = True
                # Build filter based on delegato's territory
                for delega in delegation_roles['deleghe_lista'].prefetch_related(
                    'regioni', 'province', 'comuni'
                ):
                    regioni_ids = list(delega.regioni.values_list('id', flat=True))
                    province_ids = list(delega.province.values_list('id', flat=True))
                    comuni_ids = list(delega.comuni.values_list('id', flat=True))
                    municipi_nums = delega.municipi

                    if not regioni_ids and not province_ids and not comuni_ids and not municipi_nums:
                        # No territory restriction = global access
                        has_global_access = True
                    else:
                        if regioni_ids:
                            registrations_filter |= Q(comune__provincia__regione_id__in=regioni_ids)
                        if province_ids:
                            registrations_filter |= Q(comune__provincia_id__in=province_ids)
                        if comuni_ids and municipi_nums:
                            registrations_filter |= Q(comune_id__in=comuni_ids, municipio__numero__in=municipi_nums)
                        elif comuni_ids:
                            registrations_filter |= Q(comune_id__in=comuni_ids)

            if delegation_roles['is_sub_delegato']:
                has_permission = True
                # Build filter based on sub_delega's territory
                for sub_delega in delegation_roles['sub_deleghe'].prefetch_related('regioni', 'province', 'comuni'):
                    regioni_ids = list(sub_delega.regioni.values_list('id', flat=True))
                    province_ids = list(sub_delega.province.values_list('id', flat=True))
                    comuni_ids = list(sub_delega.comuni.values_list('id', flat=True))
                    municipi_nums = sub_delega.municipi

                    if regioni_ids:
                        registrations_filter |= Q(comune__provincia__regione_id__in=regioni_ids)
                    if province_ids:
                        registrations_filter |= Q(comune__provincia_id__in=province_ids)
                    if comuni_ids and municipi_nums:
                        registrations_filter |= Q(comune_id__in=comuni_ids, municipio__numero__in=municipi_nums)
                    elif comuni_ids:
                        registrations_filter |= Q(comune_id__in=comuni_ids)

        # 3. Fallback: Check RoleAssignment (legacy system)
        if not has_permission:
            user_roles = RoleAssignment.objects.filter(
                user=user,
                is_active=True,
                role__in=['ADMIN', 'DELEGATE', 'SUBDELEGATE']
            ).select_related('scope_regione', 'scope_provincia', 'scope_comune')

            if user_roles.exists():
                has_permission = True
                for role in user_roles:
                    if role.scope_type == 'global' or role.role == 'ADMIN':
                        has_global_access = True
                        break
                    elif role.scope_type == 'regione' and role.scope_regione:
                        registrations_filter |= Q(comune__provincia__regione=role.scope_regione)
                    elif role.scope_type == 'provincia' and role.scope_provincia:
                        registrations_filter |= Q(comune__provincia=role.scope_provincia)
                    elif role.scope_type == 'comune' and role.scope_comune:
                        registrations_filter |= Q(comune=role.scope_comune)
                    elif role.scope_type == 'municipio' and role.scope_comune and role.scope_value:
                        registrations_filter |= Q(
                            comune=role.scope_comune,
                            municipio__numero=parse_municipio_number(role.scope_value)
                        )

        # No permission from any source
        if not has_permission:
            return Response({'error': 'Non autorizzato'}, status=403)

        if has_global_access:
            registrations_filter = Q()

        # Filter by status if specified
        status_filter = request.query_params.get('status')
        if status_filter:
            registrations_filter &= Q(status=status_filter)

        # Filter by territorio (cascading filters)
        regione_filter = request.query_params.get('regione')
        if regione_filter:
            registrations_filter &= Q(comune__provincia__regione_id=regione_filter)

        provincia_filter = request.query_params.get('provincia')
        if provincia_filter:
            registrations_filter &= Q(comune__provincia_id=provincia_filter)

        comune_filter = request.query_params.get('comune')
        if comune_filter:
            registrations_filter &= Q(comune_id=comune_filter)

        municipio_filter = request.query_params.get('municipio')
        if municipio_filter:
            registrations_filter &= Q(municipio_id=municipio_filter)

        registrations = RdlRegistration.objects.filter(
            registrations_filter
        ).select_related(
            'comune', 'comune__provincia', 'comune__provincia__regione',
            'municipio', 'campagna'
        ).order_by('-requested_at')

        result = []
        for reg in registrations:
            result.append({
                'id': reg.id,
                'email': reg.email,
                'nome': reg.nome,
                'cognome': reg.cognome,
                'telefono': reg.telefono,
                'comune_nascita': reg.comune_nascita,
                'data_nascita': reg.data_nascita.isoformat() if reg.data_nascita else None,
                'comune_residenza': reg.comune_residenza,
                'indirizzo_residenza': reg.indirizzo_residenza,
                # Fuorisede info
                'fuorisede': reg.fuorisede,
                'comune_domicilio': reg.comune_domicilio,
                'indirizzo_domicilio': reg.indirizzo_domicilio,
                'seggio_preferenza': reg.seggio_preferenza,
                # Territorio info
                'comune': reg.comune.nome,
                'comune_id': reg.comune_id,
                'provincia': reg.comune.provincia.nome if reg.comune.provincia else None,
                'provincia_id': reg.comune.provincia_id if reg.comune.provincia else None,
                'regione': reg.comune.provincia.regione.nome if reg.comune.provincia and reg.comune.provincia.regione else None,
                'regione_id': reg.comune.provincia.regione_id if reg.comune.provincia and reg.comune.provincia.regione else None,
                'municipio': f"Municipio {reg.municipio.numero}" if reg.municipio else None,
                'municipio_id': reg.municipio_id,
                'status': reg.status,
                'source': reg.source,
                # Campagna info (for audit)
                'campagna_nome': reg.campagna.nome if reg.campagna else None,
                'campagna_slug': reg.campagna.slug if reg.campagna else None,
                'requested_at': reg.requested_at.isoformat(),
                'approved_by': reg.approved_by.email if reg.approved_by else None,
                'approved_at': reg.approved_at.isoformat() if reg.approved_at else None,
                'rejection_reason': reg.rejection_reason,
                'notes': reg.notes,
            })

        return Response({'registrations': result})


class RdlRegistrationApproveView(APIView):
    """
    Approve or reject an RDL registration.

    POST /api/rdl/registrations/{id}/approve
    POST /api/rdl/registrations/{id}/reject
    {
        "reason": "Motivo del rifiuto"  // only for reject
    }

    Permission: can_manage_rdl (Delegato, SubDelegato)
    """
    permission_classes = [permissions.IsAuthenticated, CanManageRDL]

    def post(self, request, pk, action):
        from core.models import RoleAssignment
        from campaign.models import RdlRegistration

        # Get registration
        try:
            registration = RdlRegistration.objects.select_related(
                'comune', 'municipio'
            ).get(pk=pk)
        except RdlRegistration.DoesNotExist:
            return Response({'error': 'Registrazione non trovata'}, status=404)

        # Check permission for this comune
        if not self._has_permission(request.user, registration.comune, registration.municipio):
            return Response({'error': 'Non autorizzato per questo comune'}, status=403)

        if registration.status != 'PENDING':
            return Response({
                'error': f'Registrazione già {registration.get_status_display()}'
            }, status=400)

        if action == 'approve':
            user = registration.approve(request.user)
            return Response({
                'success': True,
                'message': f'RDL {registration.full_name} approvato',
                'user_id': user.id
            })
        elif action == 'reject':
            reason = request.data.get('reason', '')
            registration.reject(request.user, reason)
            return Response({
                'success': True,
                'message': f'RDL {registration.full_name} rifiutato'
            })
        else:
            return Response({'error': 'Azione non valida'}, status=400)

    def _has_permission(self, user, comune, municipio=None):
        """
        Check if user has permission to approve/reject RDL for this comune/municipio.
        Uses both Delegato/SubDelega and RoleAssignment systems.
        """
        if user.is_superuser:
            return True

        from core.models import RoleAssignment
        from delegations.permissions import get_user_delegation_roles

        # 1. Check delegation chain (Delegato / SubDelega) - PREFERRED
        delegation_roles = get_user_delegation_roles(user)

        # Check as Delegato
        if delegation_roles['is_delegato']:
            for delega in delegation_roles['deleghe_lista'].prefetch_related(
                'regioni', 'province', 'comuni'
            ):
                regioni_ids = list(delega.regioni.values_list('id', flat=True))
                province_ids = list(delega.province.values_list('id', flat=True))
                comuni_ids = list(delega.comuni.values_list('id', flat=True))
                municipi_nums = delega.municipi

                # No territory restriction = global access
                if not regioni_ids and not province_ids and not comuni_ids and not municipi_nums:
                    return True

                # Check regione
                if regioni_ids and comune.provincia.regione_id in regioni_ids:
                    return True

                # Check provincia
                if province_ids and comune.provincia_id in province_ids:
                    return True

                # Check comune
                if comuni_ids and comune.id in comuni_ids:
                    # If municipi specified, must match
                    if municipi_nums and municipio:
                        if municipio.numero in municipi_nums:
                            return True
                    elif not municipi_nums:
                        return True

        # Check as SubDelegato
        if delegation_roles['is_sub_delegato']:
            for sub_delega in delegation_roles['sub_deleghe'].prefetch_related('regioni', 'province', 'comuni'):
                regioni_ids = list(sub_delega.regioni.values_list('id', flat=True))
                province_ids = list(sub_delega.province.values_list('id', flat=True))
                comuni_ids = list(sub_delega.comuni.values_list('id', flat=True))
                municipi_nums = sub_delega.municipi

                # Check regione
                if regioni_ids and comune.provincia.regione_id in regioni_ids:
                    return True

                # Check provincia
                if province_ids and comune.provincia_id in province_ids:
                    return True

                # Check comune
                if comuni_ids and comune.id in comuni_ids:
                    # If municipi specified, must match
                    if municipi_nums and municipio:
                        if municipio.numero in municipi_nums:
                            return True
                    elif not municipi_nums:
                        return True

        # 2. Fallback: Check RoleAssignment (legacy system)
        # Check ADMIN or global scope
        if RoleAssignment.objects.filter(
            user=user,
        ).filter(
            Q(role='ADMIN') | Q(scope_type='global')
        ).exists():
            return True

        # Get user's delegate/subdelegate roles
        user_roles = RoleAssignment.objects.filter(
            user=user,
            is_active=True,
            role__in=['DELEGATE', 'SUBDELEGATE']
        ).select_related('scope_regione', 'scope_provincia', 'scope_comune')

        for role in user_roles:
            # Regione-level: can approve anything in that regione
            if role.scope_type == 'regione' and role.scope_regione:
                if comune.provincia.regione_id == role.scope_regione_id:
                    return True
            # Provincia-level: can approve anything in that provincia
            elif role.scope_type == 'provincia' and role.scope_provincia:
                if comune.provincia_id == role.scope_provincia_id:
                    return True
            # Comune-level: can approve anything in that comune
            elif role.scope_type == 'comune' and role.scope_comune:
                if comune.id == role.scope_comune_id:
                    return True
            # Municipio-level: can only approve registrations for that specific municipio
            elif role.scope_type == 'municipio' and role.scope_comune and role.scope_value:
                if comune.id == role.scope_comune_id:
                    # If the registration has a municipio, check it matches
                    if municipio:
                        if municipio.numero == parse_municipio_number(role.scope_value):
                            return True

        return False


class RdlRegistrationEditView(APIView):
    """
    Edit an RDL registration (full editing by delegate).

    PUT /api/rdl/registrations/{id}
    {
        "email": "rdl@example.com",
        "nome": "Mario",
        "cognome": "Rossi",
        "telefono": "333...",
        "comune_nascita": "Roma",
        "data_nascita": "1990-01-01",
        "comune_residenza": "Roma",
        "indirizzo_residenza": "Via...",
        "seggio_preferenza": "Scuola...",
        "municipio": 5,
        "notes": "Note"
    }

    Permission: can_manage_rdl (Delegato, SubDelegato)
    """
    permission_classes = [permissions.IsAuthenticated, CanManageRDL]

    def put(self, request, pk):
        from campaign.models import RdlRegistration
        from datetime import datetime

        try:
            registration = RdlRegistration.objects.select_related(
                'comune', 'comune__provincia', 'comune__provincia__regione', 'municipio'
            ).get(pk=pk)
        except RdlRegistration.DoesNotExist:
            return Response({'error': 'Registrazione non trovata'}, status=404)

        # Check permission (respects municipio scope)
        if not self._has_permission(request.user, registration.comune, registration.municipio):
            return Response({'error': 'Non autorizzato'}, status=403)

        # Update fields
        if 'email' in request.data:
            registration.email = request.data['email'].lower().strip()
        if 'nome' in request.data:
            registration.nome = request.data['nome']
        if 'cognome' in request.data:
            registration.cognome = request.data['cognome']
        if 'telefono' in request.data:
            registration.telefono = request.data['telefono']
        if 'comune_nascita' in request.data:
            registration.comune_nascita = request.data['comune_nascita']
        if 'data_nascita' in request.data:
            data_nascita_str = request.data['data_nascita']
            if data_nascita_str:
                try:
                    registration.data_nascita = datetime.strptime(data_nascita_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            else:
                registration.data_nascita = None
        if 'comune_residenza' in request.data:
            registration.comune_residenza = request.data['comune_residenza']
        if 'indirizzo_residenza' in request.data:
            registration.indirizzo_residenza = request.data['indirizzo_residenza']
        if 'seggio_preferenza' in request.data:
            registration.seggio_preferenza = request.data['seggio_preferenza']
        if 'notes' in request.data:
            registration.notes = request.data['notes']
        if 'municipio' in request.data:
            municipio_num = request.data['municipio']
            if municipio_num:
                registration.municipio = Municipio.objects.filter(
                    comune=registration.comune,
                    numero=municipio_num
                ).first()
            else:
                registration.municipio = None

        registration.save()

        return Response({
            'success': True,
            'message': 'Registrazione aggiornata'
        })

    def delete(self, request, pk):
        from campaign.models import RdlRegistration

        try:
            registration = RdlRegistration.objects.select_related(
                'comune', 'comune__provincia', 'comune__provincia__regione', 'municipio'
            ).get(pk=pk)
        except RdlRegistration.DoesNotExist:
            return Response({'error': 'Registrazione non trovata'}, status=404)

        if not self._has_permission(request.user, registration.comune, registration.municipio):
            return Response({'error': 'Non autorizzato'}, status=403)

        registration.delete()
        return Response({'success': True, 'message': 'Registrazione eliminata'})

    def _has_permission(self, user, comune, municipio=None):
        """
        Check if user has permission to edit/delete RDL registration.
        Uses both Delegato/SubDelega and RoleAssignment systems.
        """
        if user.is_superuser:
            return True

        from core.models import RoleAssignment
        from delegations.permissions import get_user_delegation_roles

        # 1. Check delegation chain (Delegato / SubDelega) - PREFERRED
        delegation_roles = get_user_delegation_roles(user)

        # Check as Delegato
        if delegation_roles['is_delegato']:
            for delega in delegation_roles['deleghe_lista'].prefetch_related(
                'regioni', 'province', 'comuni'
            ):
                regioni_ids = list(delega.regioni.values_list('id', flat=True))
                province_ids = list(delega.province.values_list('id', flat=True))
                comuni_ids = list(delega.comuni.values_list('id', flat=True))
                municipi_nums = delega.municipi

                # No territory restriction = global access
                if not regioni_ids and not province_ids and not comuni_ids and not municipi_nums:
                    return True

                # Check regione
                if regioni_ids and comune.provincia.regione_id in regioni_ids:
                    return True

                # Check provincia
                if province_ids and comune.provincia_id in province_ids:
                    return True

                # Check comune
                if comuni_ids and comune.id in comuni_ids:
                    # If municipi specified, must match
                    if municipi_nums and municipio:
                        if municipio.numero in municipi_nums:
                            return True
                    elif not municipi_nums:
                        return True

        # Check as SubDelegato
        if delegation_roles['is_sub_delegato']:
            for sub_delega in delegation_roles['sub_deleghe'].prefetch_related('regioni', 'province', 'comuni'):
                regioni_ids = list(sub_delega.regioni.values_list('id', flat=True))
                province_ids = list(sub_delega.province.values_list('id', flat=True))
                comuni_ids = list(sub_delega.comuni.values_list('id', flat=True))
                municipi_nums = sub_delega.municipi

                # Check regione
                if regioni_ids and comune.provincia.regione_id in regioni_ids:
                    return True

                # Check provincia
                if province_ids and comune.provincia_id in province_ids:
                    return True

                # Check comune
                if comuni_ids and comune.id in comuni_ids:
                    # If municipi specified, must match
                    if municipi_nums and municipio:
                        if municipio.numero in municipi_nums:
                            return True
                    elif not municipi_nums:
                        return True

        # 2. Fallback: Check RoleAssignment (legacy system)
        # Check ADMIN or global scope
        if RoleAssignment.objects.filter(
            user=user,
        ).filter(
            Q(role='ADMIN') | Q(scope_type='global')
        ).exists():
            return True

        # Get user's delegate/subdelegate roles
        user_roles = RoleAssignment.objects.filter(
            user=user,
            is_active=True,
            role__in=['DELEGATE', 'SUBDELEGATE']
        ).select_related('scope_regione', 'scope_provincia', 'scope_comune')

        for role in user_roles:
            # Regione-level: can manage anything in that regione
            if role.scope_type == 'regione' and role.scope_regione:
                if comune.provincia.regione_id == role.scope_regione_id:
                    return True
            # Provincia-level: can manage anything in that provincia
            elif role.scope_type == 'provincia' and role.scope_provincia:
                if comune.provincia_id == role.scope_provincia_id:
                    return True
            # Comune-level: can manage anything in that comune
            elif role.scope_type == 'comune' and role.scope_comune:
                if comune.id == role.scope_comune_id:
                    return True
            # Municipio-level: can only manage registrations for that specific municipio
            elif role.scope_type == 'municipio' and role.scope_comune and role.scope_value:
                if comune.id == role.scope_comune_id:
                    if municipio and municipio.numero == parse_municipio_number(role.scope_value):
                        return True

        return False


class RdlRegistrationRetryView(APIView):
    """
    Retry failed CSV records after user correction.
    Accepts JSON array of corrected records.

    Permission: can_manage_rdl (Delegato, SubDelegato)
    """
    permission_classes = [permissions.IsAuthenticated, CanManageRDL]

    def post(self, request):
        from campaign.models import RdlRegistration
        from datetime import datetime

        records = request.data.get('records', [])
        if not records:
            return Response({'error': 'Nessun record da processare'}, status=400)

        created = 0
        updated = 0
        errors = []

        for record in records:
            try:
                row_number = record.get('row_number', '?')
                email = record.get('email', '').lower().strip()
                nome = record.get('nome', '').strip()
                cognome = record.get('cognome', '').strip()
                telefono = record.get('telefono', '').strip()
                comune_nascita = record.get('comune_nascita', '').strip()
                data_nascita_str = record.get('data_nascita', '').strip()
                comune_residenza = record.get('comune_residenza', '').strip()
                indirizzo_residenza = record.get('indirizzo_residenza', '').strip()
                comune_id = record.get('comune_id')  # If user selected from dropdown
                municipio_id = record.get('municipio_id')  # If user selected from dropdown
                seggio_preferenza = record.get('seggio_preferenza', '').strip()
                fuorisede_str = record.get('fuorisede', '').upper()
                comune_domicilio = record.get('comune_domicilio', '').strip()
                indirizzo_domicilio = record.get('indirizzo_domicilio', '').strip()
                notes = record.get('notes', '').strip()
                note_correzione = record.get('note_correzione', '').strip()

                # Combine notes with correction notes
                if note_correzione:
                    if notes:
                        notes = f"{notes}\n\n[Correzione Import CSV]\n{note_correzione}"
                    else:
                        notes = f"[Correzione Import CSV]\n{note_correzione}"

                # Parse fuorisede
                fuorisede = fuorisede_str in ['SI', 'SÌ', 'YES', 'TRUE', '1'] if fuorisede_str else None

                # Validate required fields
                if not email or not nome or not cognome or not telefono:
                    errors.append(f'Riga {row_number}: campi obbligatori mancanti')
                    continue

                if not comune_nascita or not data_nascita_str or not comune_residenza or not indirizzo_residenza:
                    errors.append(f'Riga {row_number}: dati anagrafici incompleti')
                    continue

                if not comune_id:
                    errors.append(f'Riga {row_number}: comune del seggio non selezionato')
                    continue

                # Parse date
                data_nascita = None
                try:
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                        try:
                            data_nascita = datetime.strptime(data_nascita_str, fmt).date()
                            break
                        except ValueError:
                            continue
                    if not data_nascita:
                        raise ValueError(f'Formato data non riconosciuto: {data_nascita_str}')
                except ValueError as e:
                    errors.append(f'Riga {row_number}: {str(e)}')
                    continue

                # Get comune
                try:
                    comune = Comune.objects.select_related(
                        'provincia', 'provincia__regione'
                    ).prefetch_related('municipi').get(pk=comune_id)
                except Comune.DoesNotExist:
                    errors.append(f'Riga {row_number}: Comune non trovato')
                    continue

                # Get municipio
                municipio = None
                if municipio_id:
                    try:
                        municipio = Municipio.objects.get(pk=municipio_id, comune=comune)
                    except Municipio.DoesNotExist:
                        pass

                # Check permission using the same logic as import
                import_view = RdlRegistrationImportView()
                if not import_view._has_permission(request.user, comune, municipio):
                    errors.append(f'Riga {row_number}: Non autorizzato per {comune.nome}')
                    continue

                # Create or update
                defaults_dict = {
                    'nome': nome,
                    'cognome': cognome,
                    'telefono': telefono,
                    'comune_nascita': comune_nascita,
                    'data_nascita': data_nascita,
                    'comune_residenza': comune_residenza,
                    'indirizzo_residenza': indirizzo_residenza,
                    'seggio_preferenza': seggio_preferenza,
                    'municipio': municipio,
                    'source': 'IMPORT',
                    'status': RdlRegistration.Status.PENDING,
                }

                if fuorisede is not None:
                    defaults_dict['fuorisede'] = fuorisede
                if comune_domicilio:
                    defaults_dict['comune_domicilio'] = comune_domicilio
                if indirizzo_domicilio:
                    defaults_dict['indirizzo_domicilio'] = indirizzo_domicilio
                if notes:
                    defaults_dict['notes'] = notes

                registration, was_created = RdlRegistration.objects.update_or_create(
                    email=email,
                    comune=comune,
                    defaults=defaults_dict
                )

                if was_created:
                    created += 1
                else:
                    updated += 1

            except Exception as e:
                errors.append(f'Riga {row_number}: {str(e)}')

        return Response({
            'success': True,
            'created': created,
            'updated': updated,
            'total': created + updated,
            'errors': errors if errors else None
        })


class RdlRegistrationImportView(APIView):
    """
    Import RDL registrations from CSV with interactive column mapping.

    Two-step process:
    1. POST with ?analyze=true: Returns found columns and suggested mapping
    2. POST with mapping JSON: Imports data using provided mapping

    Required fields:
    - EMAIL, NOME, COGNOME, TELEFONO
    - COMUNE_NASCITA, DATA_NASCITA
    - COMUNE_RESIDENZA, INDIRIZZO_RESIDENZA
    - COMUNE_SEGGIO (where RDL will operate)

    Optional fields:
    - MUNICIPIO, SEGGIO_PREFERENZA, FUORISEDE
    - COMUNE_DOMICILIO, INDIRIZZO_DOMICILIO (for fuorisede)
    - NOTES (additional comments)

    Permission: can_manage_rdl (Delegato, SubDelegato)
    """
    permission_classes = [permissions.IsAuthenticated, CanManageRDL]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        from campaign.models import RdlRegistration
        from datetime import datetime

        # Step 1: Analyze CSV and return columns
        if request.query_params.get('analyze') == 'true':
            return self._analyze_csv(request)

        # Step 2: Import with mapping
        return self._import_with_mapping(request)

    def _analyze_csv(self, request):
        """Analyze CSV and return columns with suggested mapping."""
        if 'file' not in request.FILES:
            return Response({'error': 'Nessun file caricato'}, status=400)

        file = request.FILES['file']
        if not file.name.endswith('.csv'):
            return Response({'error': 'Il file deve essere in formato CSV'}, status=400)

        try:
            content = file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(content))
            fieldnames = reader.fieldnames or []
        except Exception as e:
            return Response({'error': f'Errore lettura CSV: {str(e)}'}, status=400)

        # Required fields for RDL registration
        required_fields = [
            {'key': 'EMAIL', 'label': 'Email', 'required': True},
            {'key': 'NOME', 'label': 'Nome', 'required': True},
            {'key': 'COGNOME', 'label': 'Cognome', 'required': True},
            {'key': 'TELEFONO', 'label': 'Telefono', 'required': True},
            {'key': 'COMUNE_NASCITA', 'label': 'Comune nascita', 'required': True},
            {'key': 'DATA_NASCITA', 'label': 'Data nascita', 'required': True},
            {'key': 'COMUNE_RESIDENZA', 'label': 'Comune residenza', 'required': True},
            {'key': 'INDIRIZZO_RESIDENZA', 'label': 'Indirizzo residenza', 'required': True},
            {'key': 'COMUNE_SEGGIO', 'label': 'Comune seggio', 'required': True},
        ]

        optional_fields = [
            {'key': 'PROVINCIA_SEGGIO', 'label': 'Provincia seggio', 'required': False},
            {'key': 'MUNICIPIO', 'label': 'Municipio (per Roma)', 'required': False},
            {'key': 'SEGGIO_PREFERENZA', 'label': 'Seggio preferenza', 'required': False},
            {'key': 'FUORISEDE', 'label': 'Fuorisede (SI/NO)', 'required': False},
            {'key': 'COMUNE_DOMICILIO', 'label': 'Comune domicilio', 'required': False},
            {'key': 'INDIRIZZO_DOMICILIO', 'label': 'Indirizzo domicilio', 'required': False},
            {'key': 'NOTES', 'label': 'Note', 'required': False},
        ]

        # Auto-suggest mapping based on column similarity
        suggested_mapping = {}
        for field in required_fields + optional_fields:
            # Try exact match first
            if field['key'] in fieldnames:
                suggested_mapping[field['key']] = field['key']
                continue

            # Try fuzzy match
            field_lower = field['key'].lower()
            label_lower = field['label'].lower()

            for col in fieldnames:
                col_lower = col.lower()
                col_upper = col.upper()

                # Email matching
                if field['key'] == 'EMAIL' and ('email' in col_lower or 'mail' in col_lower or 'e-mail' in col_lower):
                    suggested_mapping[field['key']] = col
                    break
                # Nome matching
                elif field['key'] == 'NOME' and 'nome' in col_lower:
                    suggested_mapping[field['key']] = col
                    break
                # Cognome matching
                elif field['key'] == 'COGNOME' and 'cognome' in col_lower:
                    suggested_mapping[field['key']] = col
                    break
                # Telefono matching
                elif field['key'] == 'TELEFONO' and ('telefono' in col_lower or 'phone' in col_lower or 'tel' in col_lower):
                    suggested_mapping[field['key']] = col
                    break
                # Comune nascita
                elif field['key'] == 'COMUNE_NASCITA' and ('nascita' in col_lower and 'comune' in col_lower):
                    suggested_mapping[field['key']] = col
                    break
                # Data nascita
                elif field['key'] == 'DATA_NASCITA' and ('nascita' in col_lower and 'data' in col_lower):
                    suggested_mapping[field['key']] = col
                    break
                # Comune residenza
                elif field['key'] == 'COMUNE_RESIDENZA' and ('residen' in col_lower and 'comune' in col_lower):
                    suggested_mapping[field['key']] = col
                    break
                # Indirizzo residenza
                elif field['key'] == 'INDIRIZZO_RESIDENZA' and ('residen' in col_lower and 'indirizzo' in col_lower):
                    suggested_mapping[field['key']] = col
                    break
                # Comune seggio/domicilio
                elif field['key'] == 'COMUNE_SEGGIO' and ('comune' in col_lower and ('lazio' in col_lower or 'vorresti' in col_lower or 'funzione' in col_lower)):
                    suggested_mapping[field['key']] = col
                    break
                elif field['key'] == 'PROVINCIA_SEGGIO' and ('provincia' in col_lower and ('lazio' in col_lower or 'seggio' in col_lower or 'funzione' in col_lower)):
                    suggested_mapping[field['key']] = col
                    break
                elif field['key'] == 'COMUNE_DOMICILIO' and ('domicilio' in col_lower and 'comune' in col_lower):
                    suggested_mapping[field['key']] = col
                    break
                # Municipio
                elif field['key'] == 'MUNICIPIO' and ('municip' in col_lower or 'roma' in col_lower):
                    suggested_mapping[field['key']] = col
                    break
                # Fuorisede
                elif field['key'] == 'FUORISEDE' and ('fuori' in col_lower or 'sede' in col_lower):
                    suggested_mapping[field['key']] = col
                    break
                # Seggio preferenza
                elif field['key'] == 'SEGGIO_PREFERENZA' and ('sezione' in col_lower or 'seggio' in col_lower):
                    suggested_mapping[field['key']] = col
                    break
                # Notes/Comment
                elif field['key'] == 'NOTES' and ('note' in col_lower or 'comment' in col_lower):
                    suggested_mapping[field['key']] = col
                    break

        return Response({
            'columns': fieldnames,
            'required_fields': required_fields,
            'optional_fields': optional_fields,
            'suggested_mapping': suggested_mapping
        })

    def _import_with_mapping(self, request):
        """Import CSV using provided column mapping."""
        from campaign.models import RdlRegistration
        from datetime import datetime

        if 'file' not in request.FILES:
            return Response({'error': 'Nessun file caricato'}, status=400)

        file = request.FILES['file']
        if not file.name.endswith('.csv'):
            return Response({'error': 'Il file deve essere in formato CSV'}, status=400)

        # Get mapping from request body
        mapping = request.data.get('mapping')
        if not mapping:
            return Response({'error': 'Mapping mancante'}, status=400)

        try:
            if isinstance(mapping, str):
                import json
                mapping = json.loads(mapping)
        except Exception as e:
            return Response({'error': f'Errore parsing mapping: {str(e)}'}, status=400)

        try:
            content = file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(content))
        except Exception as e:
            return Response({'error': f'Errore lettura CSV: {str(e)}'}, status=400)

        # Validate required fields are mapped
        required_keys = ['EMAIL', 'NOME', 'COGNOME', 'TELEFONO', 'COMUNE_NASCITA', 'DATA_NASCITA',
                        'COMUNE_RESIDENZA', 'INDIRIZZO_RESIDENZA', 'COMUNE_SEGGIO']
        missing = [k for k in required_keys if not mapping.get(k)]
        if missing:
            return Response({
                'error': f'Campi obbligatori non mappati: {", ".join(missing)}'
            }, status=400)

        created = 0
        updated = 0
        skipped = 0  # Records outside user's territory
        errors = []
        failed_records = []  # Store full record data for correction modal

        # Get user territory summary for better error messages
        from delegations.permissions import get_user_delegation_roles
        delegation_roles = get_user_delegation_roles(request.user)
        user_territory_info = []

        if delegation_roles['is_delegato']:
            for delega in delegation_roles['deleghe_lista'].prefetch_related(
                'regioni', 'province', 'comuni'
            ):
                territori = []
                if delega.regioni.exists():
                    territori.append(f"Regioni: {', '.join(delega.regioni.values_list('nome', flat=True))}")
                if delega.province.exists():
                    territori.append(f"Province: {', '.join(delega.province.values_list('nome', flat=True))}")
                if delega.comuni.exists():
                    territori.append(f"Comuni: {', '.join(delega.comuni.values_list('nome', flat=True)[:5])}")
                if territori:
                    user_territory_info.append(' - '.join(territori))

        if delegation_roles['is_sub_delegato']:
            for sub_delega in delegation_roles['sub_deleghe'].prefetch_related('regioni', 'province', 'comuni'):
                territori = []
                if sub_delega.regioni.exists():
                    territori.append(f"Regioni: {', '.join(sub_delega.regioni.values_list('nome', flat=True))}")
                if sub_delega.province.exists():
                    territori.append(f"Province: {', '.join(sub_delega.province.values_list('nome', flat=True))}")
                if sub_delega.comuni.exists():
                    comuni_names = list(sub_delega.comuni.values_list('nome', flat=True))
                    if len(comuni_names) <= 3:
                        territori.append(f"Comuni: {', '.join(comuni_names)}")
                    else:
                        territori.append(f"Comuni: {', '.join(comuni_names[:3])} e altri {len(comuni_names)-3}")
                if sub_delega.municipi:
                    territori.append(f"Municipi: {', '.join(map(str, sub_delega.municipi))}")
                if territori:
                    user_territory_info.append(' - '.join(territori))

        # Helper function to get mapped value
        def get_mapped_value(row, key):
            col = mapping.get(key)
            return row.get(col, '').strip() if col else ''

        for i, row in enumerate(reader, start=2):
            try:
                # Use mapping to extract values
                email = get_mapped_value(row, 'EMAIL').lower()
                nome = get_mapped_value(row, 'NOME')
                cognome = get_mapped_value(row, 'COGNOME')
                telefono = get_mapped_value(row, 'TELEFONO')
                comune_nascita = get_mapped_value(row, 'COMUNE_NASCITA')
                data_nascita_str = get_mapped_value(row, 'DATA_NASCITA')
                comune_residenza = get_mapped_value(row, 'COMUNE_RESIDENZA')
                indirizzo_residenza = get_mapped_value(row, 'INDIRIZZO_RESIDENZA')
                comune_nome = get_mapped_value(row, 'COMUNE_SEGGIO').upper()
                provincia_nome = get_mapped_value(row, 'PROVINCIA_SEGGIO').upper() if get_mapped_value(row, 'PROVINCIA_SEGGIO') else None
                municipio_str = get_mapped_value(row, 'MUNICIPIO')
                seggio_preferenza = get_mapped_value(row, 'SEGGIO_PREFERENZA')
                fuorisede_str = get_mapped_value(row, 'FUORISEDE').upper()
                comune_domicilio = get_mapped_value(row, 'COMUNE_DOMICILIO')
                indirizzo_domicilio = get_mapped_value(row, 'INDIRIZZO_DOMICILIO')
                notes = get_mapped_value(row, 'NOTES')

                # Parse fuorisede
                fuorisede = fuorisede_str in ['SI', 'SÌ', 'YES', 'TRUE', '1'] if fuorisede_str else None

                # Extract municipio number (handle formats like "Municipio 15 - Cassia/Flaminia")
                municipio_num = ''
                if municipio_str:
                    import re
                    match = re.search(r'\d+', municipio_str)
                    if match:
                        municipio_num = match.group()

                # Build record data for error tracking
                record_data = {
                    'row_number': i,
                    'email': email,
                    'nome': nome,
                    'cognome': cognome,
                    'telefono': telefono,
                    'comune_nascita': comune_nascita,
                    'data_nascita': data_nascita_str,
                    'comune_residenza': comune_residenza,
                    'indirizzo_residenza': indirizzo_residenza,
                    'comune_seggio': comune_nome,
                    'provincia_seggio': provincia_nome if provincia_nome else '',
                    'municipio': municipio_str,
                    'seggio_preferenza': seggio_preferenza,
                    'fuorisede': fuorisede_str,
                    'comune_domicilio': comune_domicilio,
                    'indirizzo_domicilio': indirizzo_domicilio,
                    'notes': notes,
                }

                # Validate required fields
                if not email or not nome or not cognome or not telefono:
                    errors.append(f'Riga {i}: email, nome, cognome e telefono sono obbligatori')
                    failed_records.append({**record_data, 'error_fields': ['email', 'nome', 'cognome', 'telefono'], 'error_message': 'Campi obbligatori mancanti'})
                    continue

                if not comune_nascita or not data_nascita_str or not comune_residenza or not indirizzo_residenza:
                    errors.append(f'Riga {i}: dati anagrafici incompleti (comune/data nascita, residenza)')
                    failed_records.append({**record_data, 'error_fields': ['comune_nascita', 'data_nascita', 'comune_residenza', 'indirizzo_residenza'], 'error_message': 'Dati anagrafici incompleti'})
                    continue

                if not comune_nome:
                    errors.append(f'Riga {i}: comune del seggio mancante')
                    failed_records.append({**record_data, 'error_fields': ['comune_seggio'], 'error_message': 'Comune del seggio mancante'})
                    continue

                # Parse date
                data_nascita = None
                try:
                    # Accept multiple date formats
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                        try:
                            data_nascita = datetime.strptime(data_nascita_str, fmt).date()
                            break
                        except ValueError:
                            continue
                    if not data_nascita:
                        raise ValueError(f'Formato data non riconosciuto: {data_nascita_str}')
                except ValueError as e:
                    errors.append(f'Riga {i}: {str(e)}')
                    failed_records.append({**record_data, 'error_fields': ['data_nascita'], 'error_message': str(e)})
                    continue

                # Find comune with intelligent search
                comune = None
                comune_nome_clean = comune_nome.split('(')[0].strip()  # Remove province suffix like "(FR)"

                # Try 1: Exact match with provincia filter (if available)
                if provincia_nome:
                    try:
                        # Search by comune name + provincia name or sigla
                        comune = Comune.objects.select_related(
                            'provincia', 'provincia__regione'
                        ).prefetch_related('municipi').filter(
                            nome__iexact=comune_nome_clean
                        ).filter(
                            Q(provincia__nome__iexact=provincia_nome) | Q(provincia__sigla__iexact=provincia_nome)
                        ).first()
                    except Exception:
                        pass

                # Try 2: Exact match without provincia (case-insensitive)
                if not comune:
                    try:
                        comune = Comune.objects.select_related(
                            'provincia', 'provincia__regione'
                        ).prefetch_related('municipi').get(nome__iexact=comune_nome_clean)
                    except Comune.DoesNotExist:
                        pass
                    except Comune.MultipleObjectsReturned:
                        # Multiple comuni with same name - check if provincia was provided
                        if provincia_nome:
                            # Already tried with provincia above, so this shouldn't happen
                            comuni_list = list(Comune.objects.filter(nome__iexact=comune_nome_clean).select_related('provincia').values_list('nome', 'provincia__nome'))
                            errors.append(f'Riga {i}: Comune ambiguo "{comune_nome_clean}" (trovati: {", ".join([f"{c[0]} ({c[1]})" for c in comuni_list[:3]])})')
                            failed_records.append({**record_data, 'error_fields': ['comune_seggio'], 'error_message': f'Comune ambiguo'})
                        else:
                            # No provincia provided, ask for it
                            comuni_list = list(Comune.objects.filter(nome__iexact=comune_nome_clean).select_related('provincia').values_list('nome', 'provincia__nome'))
                            errors.append(f'Riga {i}: Comune ambiguo "{comune_nome_clean}" (trovati: {", ".join([f"{c[0]} ({c[1]})" for c in comuni_list[:3]])}). Aggiungi colonna PROVINCIA_SEGGIO al CSV.')
                            failed_records.append({**record_data, 'error_fields': ['comune_seggio'], 'error_message': f'Comune ambiguo. Serve provincia'})
                        continue

                # Try 3: Normalize and retry (handle extra spaces, case issues)
                if not comune:
                    # Normalize: remove extra spaces, standardize case
                    comune_normalized = ' '.join(comune_nome_clean.split()).strip()

                    # Try again with normalized name
                    try:
                        comune = Comune.objects.select_related(
                            'provincia', 'provincia__regione'
                        ).prefetch_related('municipi').get(nome__iexact=comune_normalized)
                    except (Comune.DoesNotExist, Comune.MultipleObjectsReturned):
                        pass

                # Try 4: Partial match - "Guidonia" → "Guidonia Montecelio"
                if not comune and len(comune_nome_clean) >= 4:
                    # Search for comuni that contain the search term as a complete word
                    query = Comune.objects.filter(
                        nome__icontains=comune_nome_clean
                    ).select_related('provincia', 'provincia__regione').prefetch_related('municipi')

                    # Filter by provincia if available
                    if provincia_nome:
                        query = query.filter(
                            Q(provincia__nome__iexact=provincia_nome) | Q(provincia__sigla__iexact=provincia_nome)
                        )

                    possibili = query

                    # Filter: the search term must be a complete word in the comune name
                    # "Guidonia" matches "Guidonia Montecelio" ✓
                    # "Guid" does NOT match "Guidonia Montecelio" ✗
                    matches = []
                    comune_lower = comune_nome_clean.lower()
                    for c in possibili:
                        c_words = c.nome.lower().split()
                        # Check if search term is a complete word or if comune name starts with it
                        if comune_lower in c_words or c.nome.lower().startswith(comune_lower):
                            matches.append(c)

                    if len(matches) == 1:
                        comune = matches[0]
                    elif len(matches) > 1:
                        comuni_list = [(c.nome, c.provincia.nome) for c in matches[:3]]
                        errors.append(f'Riga {i}: Comune ambiguo "{comune_nome_clean}" (possibili: {", ".join([f"{c[0]} ({c[1]})" for c in comuni_list])})')
                        failed_records.append({**record_data, 'error_fields': ['comune_seggio'], 'error_message': f'Comune ambiguo: {", ".join([c.nome for c in matches[:3]])}'})
                        continue

                # Try 5: Fuzzy search (prefix + similarity) for typos like "SERRRONE" → "Serrone"
                if not comune:
                    # Search by prefix (at least 5 chars or 80% of name)
                    min_chars = min(5, int(len(comune_nome_clean) * 0.8))
                    if len(comune_nome_clean) >= min_chars:
                        prefix = comune_nome_clean[:min_chars]
                        query = Comune.objects.filter(
                            nome__istartswith=prefix
                        ).select_related('provincia', 'provincia__regione').prefetch_related('municipi')

                        # Filter by provincia if available
                        if provincia_nome:
                            query = query.filter(
                                Q(provincia__nome__iexact=provincia_nome) | Q(provincia__sigla__iexact=provincia_nome)
                            )

                        possibili = query

                        # Filter by Levenshtein-like similarity
                        matches = []
                        comune_upper = comune_nome_clean.upper().replace(' ', '')
                        for c in possibili:
                            c_upper = c.nome.upper().replace(' ', '')
                            # Simple similarity: same length or differ by 1-2 chars
                            if abs(len(c_upper) - len(comune_upper)) <= 2:
                                # Check if very similar (allow 1-2 char difference)
                                diff = sum(1 for a, b in zip(c_upper, comune_upper) if a != b)
                                if diff <= 2 or c_upper == comune_upper:
                                    matches.append(c)

                        if len(matches) == 1:
                            comune = matches[0]
                        elif len(matches) > 1:
                            comuni_list = [(c.nome, c.provincia.nome) for c in matches[:3]]
                            errors.append(f'Riga {i}: Comune ambiguo "{comune_nome_clean}" (possibili: {", ".join([f"{c[0]} ({c[1]})" for c in comuni_list])})')
                            failed_records.append({**record_data, 'error_fields': ['comune_seggio'], 'error_message': 'Comune ambiguo. Specifica provincia'})
                            continue

                if not comune:
                    errors.append(f'Riga {i}: Comune non trovato: {comune_nome}')
                    failed_records.append({**record_data, 'error_fields': ['comune_seggio'], 'error_message': f'Comune non trovato: {comune_nome}'})
                    continue

                # Find municipio
                municipio = None
                has_municipi = comune.municipi.exists()
                if municipio_num:
                    try:
                        municipio = Municipio.objects.get(
                            comune=comune,
                            numero=int(municipio_num)
                        )
                    except (Municipio.DoesNotExist, ValueError):
                        if has_municipi:
                            errors.append(f'Riga {i}: Municipio {municipio_num} non trovato per {comune_nome}')
                            failed_records.append({**record_data, 'error_fields': ['municipio'], 'error_message': f'Municipio {municipio_num} non trovato', 'comune_obj': {'id': comune.id, 'nome': comune.nome}})
                            continue
                elif has_municipi:
                    errors.append(f'Riga {i}: Municipio obbligatorio per {comune_nome}')
                    failed_records.append({**record_data, 'error_fields': ['municipio'], 'error_message': 'Municipio obbligatorio', 'comune_obj': {'id': comune.id, 'nome': comune.nome}})
                    continue

                # Check permission (with municipio for proper scope checking)
                if not self._has_permission(request.user, comune, municipio):
                    # Skip records outside user's territory (not an error to correct)
                    skipped += 1
                    continue

                # Create or update registration
                defaults_dict = {
                    'nome': nome,
                    'cognome': cognome,
                    'telefono': telefono,
                    'comune_nascita': comune_nascita,
                    'data_nascita': data_nascita,
                    'comune_residenza': comune_residenza,
                    'indirizzo_residenza': indirizzo_residenza,
                    'seggio_preferenza': seggio_preferenza,
                    'municipio': municipio,
                    'source': 'IMPORT',
                    'status': RdlRegistration.Status.PENDING,  # Import creates PENDING registrations
                }

                # Add optional fields
                if fuorisede is not None:
                    defaults_dict['fuorisede'] = fuorisede
                if comune_domicilio:
                    defaults_dict['comune_domicilio'] = comune_domicilio
                if indirizzo_domicilio:
                    defaults_dict['indirizzo_domicilio'] = indirizzo_domicilio
                if notes:
                    defaults_dict['notes'] = notes

                # Check if registration already exists
                try:
                    existing = RdlRegistration.objects.get(email=email, comune=comune)

                    # Skip if already APPROVED (confermato)
                    if existing.status == RdlRegistration.Status.APPROVED:
                        skipped += 1
                        continue

                    # Update if not approved (PENDING, REJECTED, etc.)
                    for key, value in defaults_dict.items():
                        setattr(existing, key, value)
                    existing.save()
                    updated += 1

                except RdlRegistration.DoesNotExist:
                    # Create new registration
                    RdlRegistration.objects.create(
                        email=email,
                        comune=comune,
                        **defaults_dict
                    )
                    created += 1

            except Exception as e:
                errors.append(f'Riga {i}: {str(e)}')
                failed_records.append({
                    'row_number': i,
                    'email': get_mapped_value(row, 'EMAIL'),
                    'nome': get_mapped_value(row, 'NOME'),
                    'cognome': get_mapped_value(row, 'COGNOME'),
                    'error_fields': [],
                    'error_message': str(e)
                })

        result = {
            'success': True,
            'created': created,
            'updated': updated,
            'skipped': skipped,
            'total': created + updated,
        }

        if errors:
            result['errors'] = errors[:10]
            if len(errors) > 10:
                result['errors'].append(f'... e altri {len(errors) - 10} errori')

        if failed_records:
            result['failed_records'] = failed_records

        # Add user territory info for context
        if user_territory_info and (failed_records or skipped > 0):
            result['user_territory'] = user_territory_info

        return Response(result)

    def _has_permission(self, user, comune, municipio=None):
        """
        Check if user has permission to import RDL for this comune/municipio.
        Uses both Delegato/SubDelega and RoleAssignment systems.
        """
        if user.is_superuser:
            return True

        from core.models import RoleAssignment
        from delegations.permissions import get_user_delegation_roles

        # 1. Check delegation chain (Delegato / SubDelega) - PREFERRED
        delegation_roles = get_user_delegation_roles(user)

        # Check as Delegato
        if delegation_roles['is_delegato']:
            for delega in delegation_roles['deleghe_lista'].prefetch_related(
                'regioni', 'province', 'comuni'
            ):
                regioni_ids = list(delega.regioni.values_list('id', flat=True))
                province_ids = list(delega.province.values_list('id', flat=True))
                comuni_ids = list(delega.comuni.values_list('id', flat=True))
                municipi_nums = delega.municipi

                # No territory restriction = global access
                if not regioni_ids and not province_ids and not comuni_ids and not municipi_nums:
                    return True

                # Check regione
                if regioni_ids and comune.provincia.regione_id in regioni_ids:
                    return True

                # Check provincia
                if province_ids and comune.provincia_id in province_ids:
                    return True

                # Check comune
                if comuni_ids and comune.id in comuni_ids:
                    # If municipi specified, must match
                    if municipi_nums and municipio:
                        if municipio.numero in municipi_nums:
                            return True
                    elif not municipi_nums:
                        return True

        # Check as SubDelegato
        if delegation_roles['is_sub_delegato']:
            for sub_delega in delegation_roles['sub_deleghe'].prefetch_related('regioni', 'province', 'comuni'):
                regioni_ids = list(sub_delega.regioni.values_list('id', flat=True))
                province_ids = list(sub_delega.province.values_list('id', flat=True))
                comuni_ids = list(sub_delega.comuni.values_list('id', flat=True))
                municipi_nums = sub_delega.municipi

                # Check regione
                if regioni_ids and comune.provincia.regione_id in regioni_ids:
                    return True

                # Check provincia
                if province_ids and comune.provincia_id in province_ids:
                    return True

                # Check comune
                if comuni_ids and comune.id in comuni_ids:
                    # If municipi specified, must match
                    if municipi_nums and municipio:
                        if municipio.numero in municipi_nums:
                            return True
                    elif not municipi_nums:
                        return True

        # 2. Fallback: Check RoleAssignment (legacy system)
        # Check ADMIN or global scope
        if RoleAssignment.objects.filter(
            user=user,
        ).filter(
            Q(role='ADMIN') | Q(scope_type='global')
        ).exists():
            return True

        # Get user's delegate roles
        user_roles = RoleAssignment.objects.filter(
            user=user,
            is_active=True,
            role__in=['DELEGATE', 'SUBDELEGATE']
        ).select_related('scope_regione', 'scope_provincia', 'scope_comune')

        for role in user_roles:
            # Regione-level: can import for anything in that regione
            if role.scope_type == 'regione' and role.scope_regione:
                if comune.provincia.regione_id == role.scope_regione_id:
                    return True
            # Provincia-level: can import for anything in that provincia
            elif role.scope_type == 'provincia' and role.scope_provincia:
                if comune.provincia_id == role.scope_provincia_id:
                    return True
            # Comune-level: can import for anything in that comune
            elif role.scope_type == 'comune' and role.scope_comune:
                if comune.id == role.scope_comune_id:
                    return True
            # Municipio-level: can only import for that specific municipio
            elif role.scope_type == 'municipio' and role.scope_comune and role.scope_value:
                if comune.id == role.scope_comune_id:
                    if municipio and municipio.numero == parse_municipio_number(role.scope_value):
                        return True

        return False


# =============================================================================
# PUBLIC ENDPOINTS (No auth required)
# =============================================================================

class RdlRegistrationStatusView(APIView):
    """
    Check if RDL registration is available.

    GET /api/rdl/register/status

    Registration is available when there's a future consultation (even if not active).
    Returns the consultation name and available comuni (those with delegate coverage).
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from django.utils import timezone
        from elections.models import ConsultazioneElettorale
        from core.models import RoleAssignment

        today = timezone.now().date()

        # Find any consultation that ends today or in the future
        future_consultation = ConsultazioneElettorale.objects.filter(
            data_fine__gte=today
        ).order_by('data_inizio').first()

        if future_consultation:
            # Get comuni with delegate coverage
            delegate_roles = RoleAssignment.objects.filter(
                role__in=['ADMIN', 'DELEGATE', 'SUBDELEGATE'],
            ).select_related('scope_regione', 'scope_provincia', 'scope_comune')

            has_global_delegate = delegate_roles.filter(
                Q(scope_type='global') | Q(role='ADMIN')
            ).exists()

            available_comuni = []
            if has_global_delegate:
                # All comuni available - don't list them all
                available_comuni = None
            else:
                # Get unique comuni with delegate coverage
                regioni_ids = set()
                province_ids = set()
                comuni_ids = set()

                for role in delegate_roles:
                    if role.scope_regione_id:
                        regioni_ids.add(role.scope_regione_id)
                    elif role.scope_provincia_id:
                        province_ids.add(role.scope_provincia_id)
                    elif role.scope_comune_id:
                        comuni_ids.add(role.scope_comune_id)

                scope_filter = Q(pk__isnull=True)
                if regioni_ids:
                    scope_filter |= Q(provincia__regione_id__in=regioni_ids)
                if province_ids:
                    scope_filter |= Q(provincia_id__in=province_ids)
                if comuni_ids:
                    scope_filter |= Q(id__in=comuni_ids)

                comuni = Comune.objects.filter(scope_filter).select_related(
                    'provincia', 'provincia__regione'
                ).prefetch_related('municipi').order_by('nome')[:50]  # Limit for performance

                for comune in comuni:
                    municipi = list(comune.municipi.order_by('numero').values('id', 'numero', 'nome'))
                    available_comuni.append({
                        'id': comune.id,
                        'nome': comune.nome,
                        'label': f"{comune.nome} ({comune.provincia.sigla}) {comune.provincia.regione.nome.upper()}",
                        'provincia_sigla': comune.provincia.sigla,
                        'regione': comune.provincia.regione.nome,
                        'has_municipi': len(municipi) > 0,
                        'municipi': municipi
                    })

            # Get election types for this consultation
            from elections.models import TipoElezione
            tipi_elezione = list(future_consultation.tipi_elezione.values_list('tipo', flat=True))

            return Response({
                'available': True,
                'consultation': {
                    'id': future_consultation.id,
                    'nome': future_consultation.nome,
                    'data_inizio': future_consultation.data_inizio.isoformat(),
                    'data_fine': future_consultation.data_fine.isoformat(),
                    'tipi_elezione': tipi_elezione,  # ['REFERENDUM', 'EUROPEE', etc.]
                },
                'comuni': available_comuni,  # None if global, list otherwise
                'comuni_count': len(available_comuni) if available_comuni is not None else None
            })
        else:
            return Response({
                'available': False,
                'message': 'Nessuna consultazione in programma'
            })


# =============================================================================
# MAPPATURA ENDPOINTS (NEW - Per Sezione / Per RDL workflow)
# =============================================================================

class MappaturaDebugView(APIView):
    """
    Debug endpoint to check user's territory and delegation info.
    GET /api/mappatura/debug/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from delegations.permissions import get_user_delegation_roles, get_sezioni_filter_for_user
        from delegations.models import SubDelega

        consultazione = get_consultazione_attiva()
        if not consultazione:
            return Response({'error': 'Nessuna consultazione attiva'})

        roles = get_user_delegation_roles(request.user, consultazione.id)

        # Get sub-deleghe details
        sub_deleghe_info = []
        for sd in roles['sub_deleghe']:
            sub_deleghe_info.append({
                'id': sd.id,
                'nome': f"{sd.cognome} {sd.nome}",
                'comuni': list(sd.comuni.values_list('nome', flat=True)),
                'municipi': sd.municipi,
                'tipo_delega': sd.tipo_delega,
                'is_attiva': sd.is_attiva,
            })

        # Get filter
        sezioni_filter = get_sezioni_filter_for_user(request.user, consultazione.id)

        # Count sezioni with filter
        sezioni_count = 0
        if sezioni_filter is not None:
            sezioni_count = SezioneElettorale.objects.filter(sezioni_filter, is_attiva=True).count()

        return Response({
            'user': {
                'id': request.user.id,
                'email': request.user.email,
                'is_superuser': request.user.is_superuser,
            },
            'roles': {
                'is_delegato': roles['is_delegato'],
                'is_sub_delegato': roles['is_sub_delegato'],
                'is_rdl': roles['is_rdl'],
            },
            'sub_deleghe': sub_deleghe_info,
            'filter': str(sezioni_filter) if sezioni_filter else 'None (no access)',
            'sezioni_count': sezioni_count,
        })


class MappaturaSezioniView(APIView):
    """
    Get sections grouped by plesso for mappatura.

    GET /api/mappatura/sezioni/
        ?comune_id=1
        ?municipio_id=5 or ?municipio=15 (numero)
        ?plesso=<denominazione>
        ?filter_status=all|assigned|unassigned

    Returns sections grouped by plesso (denominazione) with assignment info.
    Also returns user's territory info for filtering UI.

    Permission: can_manage_mappatura (Delegato, SubDelegato)
    """
    permission_classes = [permissions.IsAuthenticated, CanManageMappatura]

    def get(self, request):
        from delegations.permissions import get_sezioni_filter_for_user, has_referenti_permission, get_user_delegation_roles
        from collections import defaultdict
        import logging
        logger = logging.getLogger(__name__)

        consultazione = get_consultazione_attiva()
        if not consultazione:
            return Response({'error': 'Nessuna consultazione attiva'}, status=400)

        # Check permission
        if not has_referenti_permission(request.user, consultazione.id):
            return Response({'error': 'Non autorizzato'}, status=403)

        # Get user's territory info for UI
        user_territorio = self._get_user_territorio(request.user, consultazione.id)

        # Debug: log territory info
        logger.info(f"MappaturaSezioni - User: {request.user.email}, Territorio: {user_territorio}")

        # Get base filter from delegation chain
        sezioni_filter = get_sezioni_filter_for_user(request.user, consultazione.id)

        # Debug: log filter
        logger.info(f"MappaturaSezioni - sezioni_filter: {sezioni_filter}")

        if sezioni_filter is None:
            return Response({'plessi': [], 'territorio': user_territorio})

        # Apply additional filters
        filters = Q(is_attiva=True) & sezioni_filter

        comune_param = request.query_params.get('comune_id')
        if comune_param:
            comune_id = resolve_comune_id(comune_param)
            if comune_id:
                filters &= Q(comune_id=comune_id)

        # Support both municipio_id (record ID) and municipio (numero)
        municipio_id = request.query_params.get('municipio_id')
        municipio_numero = request.query_params.get('municipio')
        if municipio_id:
            filters &= Q(municipio_id=municipio_id)
        elif municipio_numero:
            try:
                filters &= Q(municipio__numero=int(municipio_numero))
            except ValueError:
                pass

        plesso = request.query_params.get('plesso')
        if plesso:
            filters &= Q(denominazione__icontains=plesso)

        # Get sezioni with assignments
        sezioni = SezioneElettorale.objects.filter(filters).select_related(
            'comune', 'municipio'
        ).order_by('denominazione', 'numero')

        # Get all assignments for these sezioni
        sezioni_ids = [s.id for s in sezioni]
        assignments = SectionAssignment.objects.filter(
            sezione_id__in=sezioni_ids,
            consultazione=consultazione,
        ).select_related('rdl_registration')

        # Get RDL registrations for territory check
        rdl_reg_ids = [a.rdl_registration_id for a in assignments if a.rdl_registration_id]
        rdl_registrations = {
            r.id: r for r in RdlRegistration.objects.filter(id__in=rdl_reg_ids).select_related('municipio')
        }

        # Compute locks from confirmed designations
        locks_map = get_locked_assignments(sezioni_ids, consultazione)

        # Index assignments by sezione_id and role
        # Also track which plessi each RDL is assigned to
        assignment_map = defaultdict(dict)
        rdl_plessi_map = defaultdict(set)  # rdl_registration_id -> set of plesso names

        for a in assignments:
            # Get plesso name and sezione for this assignment
            sez = next((s for s in sezioni if s.id == a.sezione_id), None)
            if sez:
                plesso_nome = sez.denominazione or sez.indirizzo or f"Sezione {sez.numero}"
                if a.rdl_registration_id:
                    rdl_plessi_map[a.rdl_registration_id].add(plesso_nome)

            # Check territory mismatch
            territorio_mismatch = False
            if a.rdl_registration_id and sez:
                rdl_reg = rdl_registrations.get(a.rdl_registration_id)
                if rdl_reg:
                    # Check municipio mismatch
                    if rdl_reg.municipio_id and sez.municipio_id:
                        if rdl_reg.municipio_id != sez.municipio_id:
                            territorio_mismatch = True
                    # Check comune mismatch (if no municipio)
                    elif rdl_reg.comune_id and sez.comune_id:
                        if rdl_reg.comune_id != sez.comune_id:
                            territorio_mismatch = True

            # Get user info from rdl_registration
            rdl_reg = rdl_registrations.get(a.rdl_registration_id)
            user_email = rdl_reg.email if rdl_reg else ''
            user_nome = f"{rdl_reg.nome} {rdl_reg.cognome}" if rdl_reg else user_email.split('@')[0] if user_email else ''

            # Costruisci domicilio completo (priorità: domicilio > residenza)
            domicilio = ''
            if rdl_reg:
                if rdl_reg.comune_domicilio and rdl_reg.indirizzo_domicilio:
                    domicilio = f"{rdl_reg.indirizzo_domicilio}, {rdl_reg.comune_domicilio}"
                elif rdl_reg.indirizzo_residenza and rdl_reg.comune_residenza:
                    domicilio = f"{rdl_reg.indirizzo_residenza}, {rdl_reg.comune_residenza}"

            assignment_map[a.sezione_id][a.role] = {
                'assignment_id': a.id,
                'user_email': user_email,
                'user_nome': user_nome,
                'rdl_registration_id': a.rdl_registration_id,
                'territorio_mismatch': territorio_mismatch,
                # Campi completi RDL per designazioni
                'cognome': rdl_reg.cognome if rdl_reg else '',
                'nome': rdl_reg.nome if rdl_reg else '',
                'email': user_email,
                'telefono': rdl_reg.telefono if rdl_reg else '',
                'data_nascita': rdl_reg.data_nascita.strftime('%d/%m/%Y') if (rdl_reg and rdl_reg.data_nascita) else '',
                'luogo_nascita': rdl_reg.comune_nascita if rdl_reg else '',
                'domicilio': domicilio
            }

        # Add multi_plesso flag to assignments
        for sezione_id, roles in assignment_map.items():
            for role, data in roles.items():
                rdl_id = data.get('rdl_registration_id')
                if rdl_id:
                    data['multi_plesso'] = len(rdl_plessi_map[rdl_id]) > 1

        # Get filter_status parameter: 'all' (default), 'assigned', 'unassigned'
        filter_status = request.query_params.get('filter_status', 'all')

        # Group by plesso
        plessi_map = defaultdict(lambda: {
            'sezioni': [],
            'complete': 0,  # sezioni con effettivo
            'supplenti': 0,  # sezioni con supplente
            'warning': 0,  # sezioni con supplente ma senza effettivo
            'totale': 0,
            'indirizzo': '',
            'municipio': None,  # numero del municipio
        })

        # Total counts (before filtering)
        total_count = 0
        assigned_count = 0

        for sezione in sezioni:
            # D-01: Plesso = denominazione_seggio (se presente) altrimenti indirizzo_seggio
            plesso_nome = sezione.denominazione or sezione.indirizzo or f"Sezione {sezione.numero}"
            plesso_data = plessi_map[plesso_nome]

            if not plesso_data['indirizzo'] and sezione.indirizzo:
                plesso_data['indirizzo'] = sezione.indirizzo

            # Set municipio from first sezione (all sezioni in a plesso should be in same municipio)
            if plesso_data['municipio'] is None and sezione.municipio:
                plesso_data['municipio'] = sezione.municipio.numero

            sez_assignments = assignment_map.get(sezione.id, {})
            effettivo = sez_assignments.get('RDL')
            supplente = sez_assignments.get('SUPPLENTE')

            is_complete = effettivo is not None
            has_supplente = supplente is not None
            # Warning: supplente senza effettivo
            has_warning = has_supplente and not is_complete

            # Count totals before filtering
            total_count += 1
            if is_complete:
                assigned_count += 1

            # Apply filter_status
            if filter_status == 'unassigned' and is_complete:
                continue
            if filter_status == 'assigned' and not is_complete:
                continue

            sezione_locks = locks_map.get(sezione.id, {})
            plesso_data['sezioni'].append({
                'id': sezione.id,
                'numero': sezione.numero,
                'indirizzo': sezione.indirizzo,
                'municipio': sezione.municipio.numero if sezione.municipio else None,
                'comune': sezione.comune.nome if sezione.comune else None,
                'effettivo': effettivo,
                'supplente': supplente,
                'warning': has_warning,  # supplente senza effettivo
                'effettivo_locked': sezione_locks.get('RDL', False),
                'supplente_locked': sezione_locks.get('SUPPLENTE', False),
            })
            plesso_data['totale'] += 1
            if is_complete:
                plesso_data['complete'] += 1
            if has_supplente:
                plesso_data['supplenti'] += 1
            if has_warning:
                plesso_data['warning'] += 1

        # Convert to list and filter empty plessi
        plessi = []
        for denominazione, data in sorted(plessi_map.items()):
            if data['sezioni']:  # Only include if has sezioni
                plessi.append({
                    'denominazione': denominazione,
                    'indirizzo': data['indirizzo'],
                    'municipio': data['municipio'],
                    'sezioni': data['sezioni'],
                    'complete': data['complete'],
                    'supplenti': data['supplenti'],
                    'warning': data['warning'],  # count of sezioni with supplente but no effettivo
                    'totale': data['totale'],
                })

        return Response({
            'plessi': plessi,
            'totals': {
                'sezioni': total_count,
                'assigned': assigned_count,
                'unassigned': total_count - assigned_count,
            },
            'territorio': user_territorio,
        })

    def _get_user_territorio(self, user, consultazione_id):
        """
        Get user's territory info based on delegation chain.
        Returns info about which comuni/municipi the user can see.
        """
        from delegations.permissions import get_user_delegation_roles

        result = {
            'comuni': [],
            'municipi': [],
            'is_limited': False,  # True if user has limited territory
        }

        roles = get_user_delegation_roles(user, consultazione_id)

        # Sub-delegato: check their specific territory (anche se superuser)
        if roles['is_sub_delegato']:
            for sub_delega in roles['sub_deleghe'].prefetch_related('comuni'):
                # Comuni
                for comune in sub_delega.comuni.all():
                    if comune.nome not in [c['nome'] for c in result['comuni']]:
                        result['comuni'].append({
                            'id': comune.id,
                            'nome': comune.nome,
                        })

                # Municipi (grandi città)
                if sub_delega.municipi:
                    for mun_num in sub_delega.municipi:
                        if mun_num not in result['municipi']:
                            result['municipi'].append(mun_num)
                    result['is_limited'] = True

                    # Se ha municipi ma nessun comune esplicito, aggiungi i comuni che li contengono
                    if not sub_delega.comuni.exists():
                        from territory.models import Municipio
                        municipi_comuni = Municipio.objects.filter(
                            numero__in=sub_delega.municipi
                        ).values_list('comune_id', 'comune__nome').distinct()
                        for comune_id, comune_nome in municipi_comuni:
                            if comune_nome not in [c['nome'] for c in result['comuni']]:
                                result['comuni'].append({
                                    'id': comune_id,
                                    'nome': comune_nome,
                                })

        # Delegato: check their territory
        elif roles['is_delegato']:
            for delega in roles['deleghe_lista'].prefetch_related('comuni'):
                for comune in delega.comuni.all():
                    if comune.nome not in [c['nome'] for c in result['comuni']]:
                        result['comuni'].append({
                            'id': comune.id,
                            'nome': comune.nome,
                        })
                if delega.municipi:
                    for mun_num in delega.municipi:
                        if mun_num not in result['municipi']:
                            result['municipi'].append(mun_num)
                    result['is_limited'] = True

        return result


class MappaturaRdlView(APIView):
    """
    Get list of available RDL with their section assignments.

    GET /api/mappatura/rdl/
        ?comune_id=1
        ?municipio_id=5
        ?search=<nome/cognome/email>

    Returns RDL registrations (APPROVED) with their current assignments.

    Permission: can_manage_mappatura (Delegato, SubDelegato)
    """
    permission_classes = [permissions.IsAuthenticated, CanManageMappatura]

    def get(self, request):
        from delegations.permissions import has_referenti_permission
        from core.models import RoleAssignment

        consultazione = get_consultazione_attiva()
        if not consultazione:
            return Response({'error': 'Nessuna consultazione attiva'}, status=400)

        # Check permission
        if not has_referenti_permission(request.user, consultazione.id):
            return Response({'error': 'Non autorizzato'}, status=403)

        # Build filter for RDL registrations
        filters = Q(status='APPROVED')

        comune_param = request.query_params.get('comune_id')
        if comune_param:
            comune_id = resolve_comune_id(comune_param)
            if comune_id:
                filters &= Q(comune_id=comune_id)

        # Support both municipio_id (record ID) and municipio (numero)
        # RDL disponibili per un municipio:
        # 1. RDL con quel municipio specifico
        # 2. RDL dello stesso comune senza municipio (disponibili per tutto il comune)
        municipio_id = request.query_params.get('municipio_id')
        municipio_numero = request.query_params.get('municipio')
        if municipio_id:
            filters &= (Q(municipio_id=municipio_id) | Q(municipio__isnull=True))
        elif municipio_numero:
            try:
                filters &= (Q(municipio__numero=int(municipio_numero)) | Q(municipio__isnull=True))
            except ValueError:
                pass

        search = request.query_params.get('search', '').strip()
        if search:
            filters &= (
                Q(nome__icontains=search) |
                Q(cognome__icontains=search) |
                Q(email__icontains=search)
            )

        # Apply scope filter based on user's delegation
        scope_filter = self._get_scope_filter(request.user)
        if scope_filter:
            filters &= scope_filter

        rdl_registrations = RdlRegistration.objects.filter(filters).select_related(
            'comune', 'municipio'
        ).order_by('cognome', 'nome')

        # Get all assignments for these RDL
        rdl_ids = [r.id for r in rdl_registrations]
        assignments = SectionAssignment.objects.filter(
            rdl_registration_id__in=rdl_ids,
            consultazione=consultazione,
        ).select_related('sezione', 'sezione__comune', 'sezione__municipio')

        # Index assignments by rdl_registration_id
        # Also create a lookup for RDL registrations for territory check
        rdl_reg_map = {r.id: r for r in rdl_registrations}

        from collections import defaultdict
        assignment_map = defaultdict(lambda: {'effettivo': [], 'supplente': []})
        for a in assignments:
            # Check territory mismatch
            territorio_mismatch = False
            rdl_reg = rdl_reg_map.get(a.rdl_registration_id)
            if rdl_reg and a.sezione:
                # Check municipio mismatch
                if rdl_reg.municipio_id and a.sezione.municipio_id:
                    if rdl_reg.municipio_id != a.sezione.municipio_id:
                        territorio_mismatch = True
                # Check comune mismatch (if no municipio)
                elif rdl_reg.comune_id and a.sezione.comune_id:
                    if rdl_reg.comune_id != a.sezione.comune_id:
                        territorio_mismatch = True

            key = 'effettivo' if a.role == 'RDL' else 'supplente'
            assignment_map[a.rdl_registration_id][key].append({
                'assignment_id': a.id,
                'sezione_id': a.sezione_id,
                'numero': a.sezione.numero,
                'municipio': a.sezione.municipio.numero if a.sezione.municipio else None,
                'territorio_mismatch': territorio_mismatch,
                # D-01: Plesso = denominazione_seggio (se presente) altrimenti indirizzo_seggio
                'plesso': a.sezione.denominazione or a.sezione.indirizzo or f"Sezione {a.sezione.numero}",
            })

        # ── Enrich sezioni_vicine with assignment status ──────────
        # Collect all section numeri from all RDLs' sezioni_vicine
        vicine_numeri_by_comune = defaultdict(set)
        for reg in rdl_registrations:
            for plesso in (reg.sezioni_vicine or []):
                for num in plesso.get('sezioni', []):
                    vicine_numeri_by_comune[reg.comune_id].add(num)

        # Batch fetch section IDs
        vicine_sez_map = {}  # (comune_id, numero) -> sezione_id
        for cid, numeri in vicine_numeri_by_comune.items():
            for sez in SezioneElettorale.objects.filter(
                comune_id=cid, numero__in=numeri
            ).only('id', 'numero', 'comune_id'):
                vicine_sez_map[(cid, sez.numero)] = sez.id

        # Fetch assignments for those sections
        vicine_sez_ids = set(vicine_sez_map.values())
        vicine_assign_map = {}  # sezione_id -> {'RDL': name, 'SUPPLENTE': name}
        if vicine_sez_ids:
            for a in SectionAssignment.objects.filter(
                sezione_id__in=vicine_sez_ids,
                consultazione=consultazione,
            ).select_related('rdl_registration'):
                entry = vicine_assign_map.setdefault(a.sezione_id, {})
                label = f"{a.rdl_registration.cognome} {a.rdl_registration.nome}" if a.rdl_registration else "?"
                entry[a.role] = label

        def _enrich_plessi_vicini(reg):
            plessi = []
            for plesso in (reg.sezioni_vicine or []):
                sezioni_detail = []
                for num in sorted(plesso.get('sezioni', [])):
                    sez_id = vicine_sez_map.get((reg.comune_id, num))
                    if not sez_id:
                        continue
                    occ = vicine_assign_map.get(sez_id, {})
                    sezioni_detail.append({
                        'id': sez_id,
                        'numero': num,
                        'effettivo': occ.get('RDL'),
                        'supplente': occ.get('SUPPLENTE'),
                    })
                plessi.append({
                    'indirizzo': plesso.get('indirizzo', ''),
                    'distanza_km': plesso.get('distanza_km', 0),
                    'sezioni': sezioni_detail,
                    'has_free_effettivo': any(s['effettivo'] is None for s in sezioni_detail),
                    'has_free_supplente': any(s['supplente'] is None for s in sezioni_detail),
                })
            return plessi

        result = []
        for reg in rdl_registrations:
            assignments_data = assignment_map.get(reg.id, {'effettivo': [], 'supplente': []})
            result.append({
                'rdl_registration_id': reg.id,
                'email': reg.email,
                'nome': reg.nome,
                'cognome': reg.cognome,
                'full_name': f"{reg.cognome} {reg.nome}",
                'telefono': reg.telefono,
                'seggio_preferenza': reg.seggio_preferenza,
                'notes': reg.notes,
                'comune': reg.comune.nome,
                'comune_id': reg.comune_id,
                'municipio': f"Municipio {reg.municipio.numero}" if reg.municipio else None,
                'municipio_id': reg.municipio_id,
                'municipio_numero': reg.municipio.numero if reg.municipio else None,
                'sezioni_effettivo': assignments_data['effettivo'],
                'sezioni_supplente': assignments_data['supplente'],
                'totale_sezioni': len(assignments_data['effettivo']) + len(assignments_data['supplente']),
                'sezioni_vicine': _enrich_plessi_vicini(reg),
            })

        return Response({'rdl': result})

    def _get_scope_filter(self, user):
        """Get filter based on user's delegation scope."""
        from core.models import RoleAssignment

        if user.is_superuser:
            return None

        # Check for global access
        if RoleAssignment.objects.filter(
            user=user,
        ).filter(Q(role='ADMIN') | Q(scope_type='global')).exists():
            return None

        # Build filter from user's roles
        user_roles = RoleAssignment.objects.filter(
            user=user,
            is_active=True,
            role__in=['DELEGATE', 'SUBDELEGATE']
        ).select_related('scope_regione', 'scope_provincia', 'scope_comune')

        scope_filter = Q(pk__isnull=True)  # Start with nothing

        for role in user_roles:
            if role.scope_type == 'regione' and role.scope_regione:
                scope_filter |= Q(comune__provincia__regione=role.scope_regione)
            elif role.scope_type == 'provincia' and role.scope_provincia:
                scope_filter |= Q(comune__provincia=role.scope_provincia)
            elif role.scope_type == 'comune' and role.scope_comune:
                scope_filter |= Q(comune=role.scope_comune)
            elif role.scope_type == 'municipio' and role.scope_comune and role.scope_value:
                scope_filter |= Q(
                    comune=role.scope_comune,
                    municipio__numero=parse_municipio_number(role.scope_value)
                )

        return scope_filter


class MappaturaAssegnaView(APIView):
    """
    Assign/unassign RDL to section.

    POST /api/mappatura/assegna/
    {
        "sezione_id": 123,
        "rdl_registration_id": 10,
        "ruolo": "RDL"  // or "SUPPLENTE"
    }

    DELETE /api/mappatura/assegna/{assignment_id}/

    Permission: can_manage_mappatura (Delegato, SubDelegato)
    """
    permission_classes = [permissions.IsAuthenticated, CanManageMappatura]

    def post(self, request):
        from delegations.permissions import has_referenti_permission
        from core.models import User

        consultazione = get_consultazione_attiva()
        if not consultazione:
            return Response({'error': 'Nessuna consultazione attiva'}, status=400)

        if not has_referenti_permission(request.user, consultazione.id):
            return Response({'error': 'Non autorizzato'}, status=403)

        sezione_id = request.data.get('sezione_id')
        rdl_registration_id = request.data.get('rdl_registration_id')
        ruolo = request.data.get('ruolo', 'RDL')

        if not sezione_id or not rdl_registration_id:
            return Response({'error': 'sezione_id e rdl_registration_id sono obbligatori'}, status=400)

        if ruolo not in ['RDL', 'SUPPLENTE']:
            return Response({'error': 'ruolo deve essere RDL o SUPPLENTE'}, status=400)

        # Get sezione
        try:
            sezione = SezioneElettorale.objects.select_related('comune').get(pk=sezione_id)
        except SezioneElettorale.DoesNotExist:
            return Response({'error': 'Sezione non trovata'}, status=404)

        # Get RDL registration
        try:
            rdl_reg = RdlRegistration.objects.select_related('comune', 'municipio').get(
                pk=rdl_registration_id,
                status='APPROVED'
            )
        except RdlRegistration.DoesNotExist:
            return Response({'error': 'RDL registration non trovata o non approvata'}, status=404)

        # Validate territory match: RDL must be in same territory as sezione
        # If RDL has municipio, sezione must be in same municipio
        if rdl_reg.municipio:
            if not sezione.municipio or sezione.municipio_id != rdl_reg.municipio_id:
                return Response({
                    'error': f'L\'RDL è registrato per il Municipio {rdl_reg.municipio.numero}, '
                             f'ma la sezione appartiene a un municipio diverso'
                }, status=400)
        # If RDL has only comune (no municipio), sezione must be in same comune
        elif rdl_reg.comune_id != sezione.comune_id:
            return Response({
                'error': f'L\'RDL è registrato per il comune di {rdl_reg.comune.nome}, '
                         f'ma la sezione appartiene al comune di {sezione.comune.nome}'
            }, status=400)

        # Get or create user from registration email
        user, _ = User.objects.get_or_create(
            email=rdl_reg.email.lower(),
            defaults={
                'display_name': f"{rdl_reg.nome} {rdl_reg.cognome}",
                'first_name': rdl_reg.nome,
                'last_name': rdl_reg.cognome,
            }
        )

        # Check if existing assignment for this role is locked by confirmed designation
        existing = SectionAssignment.objects.filter(
            sezione=sezione,
            consultazione=consultazione,
            role=ruolo
        ).select_related('rdl_registration').first()

        if existing:
            locked, designated_email = is_assignment_locked(
                sezione, consultazione, ruolo, existing.rdl_registration
            )
            if locked:
                return Response({
                    'error': f'Questa assegnazione è bloccata da una designazione confermata '
                             f'({designated_email}). Revoca prima la designazione.'
                }, status=409)

        # Delete existing assignment for this role on this sezione
        if existing:
            existing.delete()
        # Also delete any leftover for different role
        SectionAssignment.objects.filter(
            sezione=sezione,
            consultazione=consultazione,
            role=ruolo
        ).delete()

        # Also delete any existing assignment for this RDL on this sezione
        # (RDL can't be both effettivo and supplente on same sezione)
        SectionAssignment.objects.filter(
            sezione=sezione,
            consultazione=consultazione,
            rdl_registration=rdl_reg
        ).delete()

        # Create new assignment - use rdl_registration as primary key
        assignment, created = SectionAssignment.objects.update_or_create(
            sezione=sezione,
            consultazione=consultazione,
            rdl_registration=rdl_reg,
            defaults={
                'role': ruolo,
                'assigned_by_email': request.user.email,
            }
        )

        return Response({
            'success': True,
            'assignment_id': assignment.id,
            'sezione_id': sezione.id,
            'sezione_numero': sezione.numero,
            'rdl_registration_id': rdl_reg.id,
            'user_email': user.email,
            'ruolo': ruolo,
        })

    def delete(self, request, assignment_id):
        from delegations.permissions import has_referenti_permission

        consultazione = get_consultazione_attiva()
        if not consultazione:
            return Response({'error': 'Nessuna consultazione attiva'}, status=400)

        if not has_referenti_permission(request.user, consultazione.id):
            return Response({'error': 'Non autorizzato'}, status=403)

        try:
            assignment = SectionAssignment.objects.select_related('rdl_registration').get(
                pk=assignment_id,
                consultazione=consultazione
            )
        except SectionAssignment.DoesNotExist:
            return Response({'error': 'Assegnazione non trovata'}, status=404)

        # Check if assignment is locked by confirmed designation
        locked, designated_email = is_assignment_locked(
            assignment.sezione, consultazione, assignment.role, assignment.rdl_registration
        )
        if locked:
            return Response({
                'error': f'Assegnazione bloccata da designazione confermata ({designated_email}). '
                         f'Revoca prima la designazione.'
            }, status=409)

        assignment.delete()

        return Response({
            'success': True,
            'removed': True,
            'assignment_id': assignment_id,
        })


class MappaturaAssegnaBulkView(APIView):
    """
    Bulk assign RDL to multiple sections (same plesso).

    POST /api/mappatura/assegna-bulk/
    {
        "rdl_registration_id": 10,
        "sezioni_ids": [123, 124, 125],
        "ruolo": "RDL"
    }

    Permission: can_manage_mappatura (Delegato, SubDelegato)
    """
    permission_classes = [permissions.IsAuthenticated, CanManageMappatura]

    def post(self, request):
        from delegations.permissions import has_referenti_permission
        from core.models import User

        consultazione = get_consultazione_attiva()
        if not consultazione:
            return Response({'error': 'Nessuna consultazione attiva'}, status=400)

        if not has_referenti_permission(request.user, consultazione.id):
            return Response({'error': 'Non autorizzato'}, status=403)

        rdl_registration_id = request.data.get('rdl_registration_id')
        sezioni_ids = request.data.get('sezioni_ids', [])
        ruolo = request.data.get('ruolo', 'RDL')

        if not rdl_registration_id or not sezioni_ids:
            return Response({'error': 'rdl_registration_id e sezioni_ids sono obbligatori'}, status=400)

        if ruolo not in ['RDL', 'SUPPLENTE']:
            return Response({'error': 'ruolo deve essere RDL o SUPPLENTE'}, status=400)

        # Get RDL registration
        try:
            rdl_reg = RdlRegistration.objects.select_related('comune', 'municipio').get(
                pk=rdl_registration_id,
                status='APPROVED'
            )
        except RdlRegistration.DoesNotExist:
            return Response({'error': 'RDL registration non trovata o non approvata'}, status=404)

        # Get or create user from email
        from core.models import User
        user, _ = User.objects.get_or_create(
            email=rdl_reg.email.lower(),
            defaults={
                'display_name': f"{rdl_reg.nome} {rdl_reg.cognome}",
                'first_name': rdl_reg.nome,
                'last_name': rdl_reg.cognome,
            }
        )

        # Get sezioni
        sezioni = SezioneElettorale.objects.filter(pk__in=sezioni_ids, is_attiva=True)
        if sezioni.count() != len(sezioni_ids):
            return Response({'error': 'Alcune sezioni non trovate'}, status=404)

        # Pre-compute locks for all requested sezioni
        locks_map = get_locked_assignments(sezioni_ids, consultazione)

        assigned = []
        skipped = []
        with transaction.atomic():
            for sezione in sezioni:
                # Check if existing assignment is locked
                sezione_locks = locks_map.get(sezione.id, {})
                role_key = ruolo  # 'RDL' or 'SUPPLENTE'
                if sezione_locks.get(role_key, False):
                    skipped.append({
                        'sezione_id': sezione.id,
                        'sezione_numero': sezione.numero,
                        'motivo': 'Designazione confermata',
                    })
                    continue

                # Delete existing assignment for this role
                SectionAssignment.objects.filter(
                    sezione=sezione,
                    consultazione=consultazione,
                    role=ruolo
                ).delete()

                # Delete any existing assignment for this RDL on this sezione
                SectionAssignment.objects.filter(
                    sezione=sezione,
                    consultazione=consultazione,
                    rdl_registration=rdl_reg
                ).delete()

                # Create/update assignment - use rdl_registration as primary key
                assignment, _ = SectionAssignment.objects.update_or_create(
                    sezione=sezione,
                    consultazione=consultazione,
                    rdl_registration=rdl_reg,
                    defaults={
                        'role': ruolo,
                        'assigned_by_email': request.user.email,
                    }
                )
                assigned.append({
                    'assignment_id': assignment.id,
                    'sezione_id': sezione.id,
                    'sezione_numero': sezione.numero,
                })

        return Response({
            'success': True,
            'rdl_registration_id': rdl_reg.id,
            'user_email': user.email,
            'ruolo': ruolo,
            'assigned': assigned,
            'skipped': skipped,
            'count': len(assigned),
        })


class ComuniSearchView(APIView):
    """
    Public search for comuni (for RDL self-registration).

    GET /api/rdl/comuni/search?q=rom

    Returns comuni matching the query in format: "Roma (RM) LAZIO"

    Only returns comuni where there's at least one delegate assigned
    (at comune, provincia, or regione level).
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from core.models import RoleAssignment
        from django.db.models import Case, When, Value, IntegerField

        query = request.query_params.get('q', '').strip()

        if len(query) < 2:
            return Response({'comuni': []})

        # Get all active delegate assignments
        delegate_roles = RoleAssignment.objects.filter(
            role__in=['ADMIN', 'DELEGATE', 'SUBDELEGATE'],
        ).select_related('scope_regione', 'scope_provincia', 'scope_comune')

        # Check for global delegate coverage
        has_global_delegate = delegate_roles.filter(
            Q(scope_type='global') | Q(role='ADMIN')
        ).exists()

        if has_global_delegate:
            # Global delegate: all comuni are valid
            comuni_filter = Q(nome__icontains=query)
        else:
            # Build specific filter based on delegate scopes
            # Get unique scopes
            regioni_ids = set()
            province_ids = set()
            comuni_ids = set()

            for role in delegate_roles:
                if role.scope_regione_id:
                    regioni_ids.add(role.scope_regione_id)
                elif role.scope_provincia_id:
                    province_ids.add(role.scope_provincia_id)
                elif role.scope_comune_id:
                    comuni_ids.add(role.scope_comune_id)

            # Build OR filter for all scopes
            scope_filter = Q(pk__isnull=True)  # Start with nothing (False)
            if regioni_ids:
                scope_filter |= Q(provincia__regione_id__in=regioni_ids)
            if province_ids:
                scope_filter |= Q(provincia_id__in=province_ids)
            if comuni_ids:
                scope_filter |= Q(id__in=comuni_ids)

            comuni_filter = Q(nome__icontains=query) & scope_filter

        # Search comuni with delegate coverage
        comuni = Comune.objects.filter(
            comuni_filter
        ).select_related(
            'provincia', 'provincia__regione'
        ).prefetch_related('municipi').annotate(
            # Priority: 1 = exact match, 2 = starts with, 3 = contains
            match_priority=Case(
                When(nome__iexact=query, then=Value(1)),
                When(nome__istartswith=query, then=Value(2)),
                default=Value(3),
                output_field=IntegerField()
            )
        ).order_by('match_priority', 'nome')[:20]  # Limit to 20 results

        result = []
        for comune in comuni:
            # Format: "Roma (RM) LAZIO"
            label = f"{comune.nome} ({comune.provincia.sigla}) {comune.provincia.regione.nome.upper()}"
            # Get actual municipi for this comune
            municipi = list(comune.municipi.order_by('numero').values('id', 'numero', 'nome'))
            result.append({
                'id': comune.id,
                'nome': comune.nome,
                'label': label,
                'provincia_sigla': comune.provincia.sigla,
                'regione': comune.provincia.regione.nome,
                'has_municipi': len(municipi) > 0,
                'municipi': municipi
            })

        return Response({'comuni': result})
