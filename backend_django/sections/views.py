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

from .models import SectionAssignment, DatiSezione, DatiScheda, RdlRegistration
from elections.models import ConsultazioneElettorale
from territorio.models import SezioneElettorale, Comune, Municipio


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


def section_to_legacy_values(dati_sezione, candidate_names, list_names):
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
        9...: candidate votes,
        ...: list votes,
        last: incongruenze
    ]
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

    # Get first DatiScheda for ballot-level data
    dati_scheda = dati_sezione.schede.first()
    if dati_scheda:
        values[2] = dati_scheda.schede_ricevute or ''
        values[3] = dati_scheda.schede_autenticate or ''
        values[6] = dati_scheda.schede_bianche or ''
        values[7] = dati_scheda.schede_nulle or ''
        values[8] = dati_scheda.schede_contestate or ''

        # Extract candidate/list votes from JSON voti
        voti = dati_scheda.voti or {}
        preferenze = voti.get('preferenze', {})
        liste = voti.get('liste', {})

        # Candidate votes in order
        for name in candidate_names:
            values.append(preferenze.get(name, ''))

        # List votes in order
        for name in list_names:
            values.append(liste.get(name, ''))
    else:
        # No data yet - add empty values for candidates and lists
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
    - Dettaglio per municipio (Roma)
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

        # Group by comune
        per_comune = {}
        per_municipio = {}

        for sezione in sezioni:
            comune_nome = sezione.comune.nome
            is_assigned = sezione.id in assigned_sezioni_ids

            if comune_nome not in per_comune:
                per_comune[comune_nome] = {'totale': 0, 'assegnate': 0}

            per_comune[comune_nome]['totale'] += 1
            if is_assigned:
                per_comune[comune_nome]['assegnate'] += 1

            # Track municipio for Roma
            if sezione.municipio:
                mun_num = sezione.municipio.numero
                if mun_num not in per_municipio:
                    per_municipio[mun_num] = {'visibili': 0, 'assegnate': 0}
                per_municipio[mun_num]['visibili'] += 1
                if is_assigned:
                    per_municipio[mun_num]['assegnate'] += 1

        result['perComune'] = per_comune
        result['perMunicipio'] = per_municipio

        return Response(result)


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

        # Get user's section assignments for the active consultation
        assignments = SectionAssignment.objects.filter(
            user=request.user,
            consultazione=consultazione,
        ).select_related(
            'sezione', 'sezione__comune'
        )

        rows = []
        for assignment in assignments:
            sezione = assignment.sezione

            # Get or create DatiSezione for this section
            dati_sezione, _ = DatiSezione.objects.prefetch_related('schede').get_or_create(
                sezione=sezione,
                consultazione=consultazione
            )

            values = section_to_legacy_values(dati_sezione, candidate_names, list_names)

            rows.append({
                'comune': sezione.comune.nome,
                'sezione': sezione.numero,
                'email': request.user.email,
                'values': values,
            })

        return Response({'rows': rows})


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
            ).select_related('user').first()

            # Get or create DatiSezione
            dati_sezione = DatiSezione.objects.prefetch_related('schede').filter(
                sezione=sezione,
                consultazione=consultazione
            ).first()

            if dati_sezione:
                values = section_to_legacy_values(dati_sezione, candidate_names, list_names)
            else:
                # No data - create empty values
                values = [''] * (9 + len(candidate_names) + len(list_names) + 1)

            rows.append({
                'comune': sezione.comune.nome,
                'sezione': sezione.numero,
                'email': assignment.user.email if assignment else '',
                'values': values,
            })

        return Response({'rows': rows})


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
        consultazione = get_consultazione_attiva()
        if not consultazione:
            return Response({'error': 'Nessuna consultazione attiva'}, status=400)

        comune_nome = request.data.get('comune')
        sezione_numero = request.data.get('sezione')
        values = request.data.get('values', [])

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

        # Get candidates and lists to parse values array
        candidate_names, list_names = get_candidates_and_lists(consultazione)

        # Parse values array (legacy format)
        def parse_int(val):
            if val == '' or val is None:
                return None
            try:
                return int(val)
            except (ValueError, TypeError):
                return None

        # Get or create DatiSezione
        dati_sezione, created = DatiSezione.objects.get_or_create(
            sezione=sezione,
            consultazione=consultazione
        )

        # Update DatiSezione fields from values array
        if len(values) > 0:
            dati_sezione.elettori_maschi = parse_int(values[0])
        if len(values) > 1:
            dati_sezione.elettori_femmine = parse_int(values[1])
        if len(values) > 4:
            dati_sezione.votanti_maschi = parse_int(values[4])
        if len(values) > 5:
            dati_sezione.votanti_femmine = parse_int(values[5])

        dati_sezione.inserito_da = request.user
        dati_sezione.inserito_at = timezone.now()

        # Check if complete
        dati_sezione.is_complete = all([
            dati_sezione.elettori_maschi is not None,
            dati_sezione.elettori_femmine is not None,
            dati_sezione.votanti_maschi is not None,
            dati_sezione.votanti_femmine is not None,
        ])

        dati_sezione.save()

        # Get or create DatiScheda for the first ballot
        from elections.models import SchedaElettorale
        scheda = SchedaElettorale.objects.filter(
            tipo_elezione__consultazione=consultazione
        ).first()

        if scheda:
            dati_scheda, _ = DatiScheda.objects.get_or_create(
                dati_sezione=dati_sezione,
                scheda=scheda
            )

            # Parse ballot-level data
            if len(values) > 2:
                dati_scheda.schede_ricevute = parse_int(values[2])
            if len(values) > 3:
                dati_scheda.schede_autenticate = parse_int(values[3])
            if len(values) > 6:
                dati_scheda.schede_bianche = parse_int(values[6])
            if len(values) > 7:
                dati_scheda.schede_nulle = parse_int(values[7])
            if len(values) > 8:
                dati_scheda.schede_contestate = parse_int(values[8])

            # Parse candidate and list votes
            fP = 9  # First preference index
            fL = fP + len(candidate_names)  # First list index

            preferenze = {}
            for i, name in enumerate(candidate_names):
                if fP + i < len(values) and values[fP + i] != '':
                    preferenze[name] = parse_int(values[fP + i])

            liste = {}
            for i, name in enumerate(list_names):
                if fL + i < len(values) and values[fL + i] != '':
                    liste[name] = parse_int(values[fL + i])

            dati_scheda.voti = {
                'preferenze': preferenze,
                'liste': liste,
            }

            # Get incongruenze (last value)
            lL = fL + len(list_names)
            if lL < len(values):
                dati_scheda.errori_validazione = values[lL] if values[lL] else None

            dati_scheda.inserito_at = timezone.now()
            dati_scheda.save()

        return Response({'success': True, 'is_complete': dati_sezione.is_complete})


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
            ).select_related('user').first()

            municipio_str = f"Municipio {sezione.municipio.numero}" if sezione.municipio else ""
            email = assignment.user.email if assignment else ""

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

        # Find or create the user
        user, created = User.objects.get_or_create(
            email=email.lower(),
            defaults={'display_name': email.split('@')[0]}
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
            user=user,
            role=SectionAssignment.Role.RDL,
            assigned_by=request.user,
        )

        # Also assign RDL role to the user if not already assigned
        from core.models import RoleAssignment as CoreRoleAssignment
        CoreRoleAssignment.objects.get_or_create(
            user=user,
            role='RDL',
            defaults={
                'assigned_by': request.user,
                'is_active': True
            }
        )

        return Response({
            'success': True,
            'comune': sezione.comune.nome,
            'sezione': sezione.numero,
            'email': user.email
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
    - Superusers
    - ADMIN role
    - DELEGATE with scope on the comune being uploaded
    """
    permission_classes = [permissions.IsAuthenticated]
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
        from .models import RdlRegistration
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
        comune_nome = request.data.get('comune', '').strip()
        municipio_num = request.data.get('municipio')

        # Validate required fields
        if not email or not nome or not cognome or not telefono or not comune_nome:
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

        # Find comune
        try:
            comune = Comune.objects.prefetch_related('municipi').get(nome__iexact=comune_nome)
        except Comune.DoesNotExist:
            return Response({'error': f'Comune non trovato: {comune_nome}'}, status=404)

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


class RdlRegistrationListView(APIView):
    """
    List RDL registrations for delegates.

    GET /api/rdl/registrations?status=PENDING

    Returns registrations filtered by delegate's scope.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from core.models import RoleAssignment
        from .models import RdlRegistration

        # Check permission
        user_roles = RoleAssignment.objects.filter(
            user=request.user,
            is_active=True,
            role__in=['ADMIN', 'DELEGATE', 'SUBDELEGATE']
        ).select_related('scope_regione', 'scope_provincia', 'scope_comune')

        if not user_roles.exists() and not request.user.is_superuser:
            return Response({'error': 'Non autorizzato'}, status=403)

        # Build filter based on scope
        registrations_filter = Q()
        has_global_access = False

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

        if request.user.is_superuser:
            has_global_access = True

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
            'municipio', 'user', 'approved_by'
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
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, action):
        from core.models import RoleAssignment
        from .models import RdlRegistration

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
        Check if user has permission to approve RDL for this comune/municipio.
        Follows the same scope logic as the registration list view.
        """
        if user.is_superuser:
            return True

        from core.models import RoleAssignment

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
                    # If registration has no municipio but delegate is municipio-scoped, deny
                    # (they can only manage their specific municipio)

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
    """
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, pk):
        from .models import RdlRegistration
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
        from .models import RdlRegistration

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
        Follows the same scope logic as the registration list view.
        """
        if user.is_superuser:
            return True

        from core.models import RoleAssignment

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


class RdlRegistrationImportView(APIView):
    """
    Import RDL registrations from CSV.

    POST /api/rdl/registrations/import
    Content-Type: multipart/form-data

    CSV format:
    EMAIL,NOME,COGNOME,TELEFONO,COMUNE_NASCITA,DATA_NASCITA,COMUNE_RESIDENZA,INDIRIZZO_RESIDENZA,COMUNE_SEGGIO,MUNICIPIO,SEGGIO_PREFERENZA
    mario.rossi@example.com,Mario,Rossi,3331234567,Milano,1985-03-15,Roma,Via Roma 1,ROMA,5,Scuola Manzoni

    Required columns: EMAIL, NOME, COGNOME, TELEFONO, COMUNE_NASCITA, DATA_NASCITA, COMUNE_RESIDENZA, INDIRIZZO_RESIDENZA, COMUNE_SEGGIO
    Optional columns: MUNICIPIO, SEGGIO_PREFERENZA

    COMUNE_SEGGIO = Comune dove si trova il seggio in cui l'RDL intende operare
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        from .models import RdlRegistration
        from datetime import datetime

        if 'file' not in request.FILES:
            return Response({'error': 'Nessun file caricato'}, status=400)

        file = request.FILES['file']
        if not file.name.endswith('.csv'):
            return Response({'error': 'Il file deve essere in formato CSV'}, status=400)

        try:
            content = file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(content))
        except Exception as e:
            return Response({'error': f'Errore lettura CSV: {str(e)}'}, status=400)

        # Validate headers - all personal data fields are required
        required_headers = {
            'EMAIL', 'NOME', 'COGNOME', 'TELEFONO',
            'COMUNE_NASCITA', 'DATA_NASCITA',
            'COMUNE_RESIDENZA', 'INDIRIZZO_RESIDENZA',
            'COMUNE_SEGGIO'
        }
        missing_headers = required_headers - set(reader.fieldnames or [])
        if missing_headers:
            return Response({
                'error': f'Intestazioni mancanti: {", ".join(sorted(missing_headers))}'
            }, status=400)

        created = 0
        updated = 0
        errors = []

        for i, row in enumerate(reader, start=2):
            try:
                email = row['EMAIL'].lower().strip()
                nome = row['NOME'].strip()
                cognome = row['COGNOME'].strip()
                telefono = row['TELEFONO'].strip()
                comune_nascita = row['COMUNE_NASCITA'].strip()
                data_nascita_str = row['DATA_NASCITA'].strip()
                comune_residenza = row['COMUNE_RESIDENZA'].strip()
                indirizzo_residenza = row['INDIRIZZO_RESIDENZA'].strip()
                comune_nome = row['COMUNE_SEGGIO'].upper().strip()
                municipio_num = row.get('MUNICIPIO', '').strip()
                seggio_preferenza = row.get('SEGGIO_PREFERENZA', '').strip()

                # Validate required fields
                if not email or not nome or not cognome or not telefono:
                    errors.append(f'Riga {i}: email, nome, cognome e telefono sono obbligatori')
                    continue

                if not comune_nascita or not data_nascita_str or not comune_residenza or not indirizzo_residenza:
                    errors.append(f'Riga {i}: dati anagrafici incompleti (comune/data nascita, residenza)')
                    continue

                if not comune_nome:
                    errors.append(f'Riga {i}: comune del seggio mancante')
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
                    continue

                # Find comune
                try:
                    comune = Comune.objects.select_related(
                        'provincia', 'provincia__regione'
                    ).prefetch_related('municipi').get(nome__iexact=comune_nome)
                except Comune.DoesNotExist:
                    errors.append(f'Riga {i}: Comune non trovato: {comune_nome}')
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
                            continue
                elif has_municipi:
                    errors.append(f'Riga {i}: Municipio obbligatorio per {comune_nome}')
                    continue

                # Check permission (with municipio for proper scope checking)
                if not self._has_permission(request.user, comune, municipio):
                    errors.append(f'Riga {i}: Non autorizzato per {comune_nome}')
                    continue

                # Create or update registration
                registration, was_created = RdlRegistration.objects.update_or_create(
                    email=email,
                    comune=comune,
                    defaults={
                        'nome': nome,
                        'cognome': cognome,
                        'telefono': telefono,
                        'comune_nascita': comune_nascita,
                        'data_nascita': data_nascita,
                        'comune_residenza': comune_residenza,
                        'indirizzo_residenza': indirizzo_residenza,
                        'seggio_preferenza': seggio_preferenza,
                        'municipio': municipio,
                        'status': RdlRegistration.Status.APPROVED,
                        'source': 'IMPORT',
                        'approved_by': request.user,
                        'approved_at': timezone.now(),
                    }
                )

                # Approve if it was pending
                if not was_created and registration.status == 'PENDING':
                    registration.approve(request.user)

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
            result['errors'] = errors[:10]
            if len(errors) > 10:
                result['errors'].append(f'... e altri {len(errors) - 10} errori')

        return Response(result)

    def _has_permission(self, user, comune, municipio=None):
        """
        Check if user has permission to import RDL for this comune/municipio.
        Follows the same scope logic as other registration views.
        """
        if user.is_superuser:
            return True

        from core.models import RoleAssignment

        # Check ADMIN or global scope
        if RoleAssignment.objects.filter(
            user=user,
        ).filter(
            Q(role='ADMIN') | Q(scope_type='global')
        ).exists():
            return True

        # Get user's delegate roles (import only allowed for DELEGATE, not SUBDELEGATE)
        user_roles = RoleAssignment.objects.filter(
            user=user,
            is_active=True,
            role='DELEGATE'
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
    """
    permission_classes = [permissions.IsAuthenticated]

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
        ).select_related('user', 'rdl_registration')

        # Get RDL registrations for territory check
        rdl_reg_ids = [a.rdl_registration_id for a in assignments if a.rdl_registration_id]
        rdl_registrations = {
            r.id: r for r in RdlRegistration.objects.filter(id__in=rdl_reg_ids).select_related('municipio')
        }

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

            assignment_map[a.sezione_id][a.role] = {
                'assignment_id': a.id,
                'user_id': a.user_id,
                'user_email': a.user.email,
                'user_nome': a.user.display_name or a.user.email.split('@')[0],
                'rdl_registration_id': a.rdl_registration_id,
                'territorio_mismatch': territorio_mismatch,
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

            plesso_data['sezioni'].append({
                'id': sezione.id,
                'numero': sezione.numero,
                'indirizzo': sezione.indirizzo,
                'municipio': sezione.municipio.numero if sezione.municipio else None,
                'comune': sezione.comune.nome if sezione.comune else None,
                'effettivo': effettivo,
                'supplente': supplente,
                'warning': has_warning,  # supplente senza effettivo
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

                # Municipi (solo Roma ha municipi)
                if sub_delega.municipi:
                    for mun_num in sub_delega.municipi:
                        if mun_num not in result['municipi']:
                            result['municipi'].append(mun_num)
                    result['is_limited'] = True

                    # Se ha municipi ma nessun comune esplicito, aggiungi Roma
                    if not sub_delega.comuni.exists():
                        from territorio.models import Comune
                        roma = Comune.objects.filter(nome__iexact='Roma').first()
                        if roma and roma.nome not in [c['nome'] for c in result['comuni']]:
                            result['comuni'].append({
                                'id': roma.id,
                                'nome': roma.nome,
                            })

        # Delegato: check their territory
        elif roles['is_delegato']:
            for delega in roles['deleghe_lista'].prefetch_related('territorio_comuni'):
                for comune in delega.territorio_comuni.all():
                    if comune.nome not in [c['nome'] for c in result['comuni']]:
                        result['comuni'].append({
                            'id': comune.id,
                            'nome': comune.nome,
                        })
                if delega.territorio_municipi:
                    for mun_num in delega.territorio_municipi:
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
    """
    permission_classes = [permissions.IsAuthenticated]

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
        municipio_id = request.query_params.get('municipio_id')
        municipio_numero = request.query_params.get('municipio')
        if municipio_id:
            filters &= Q(municipio_id=municipio_id)
        elif municipio_numero:
            try:
                filters &= Q(municipio__numero=int(municipio_numero))
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
            'comune', 'municipio', 'user'
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

        result = []
        for reg in rdl_registrations:
            assignments_data = assignment_map.get(reg.id, {'effettivo': [], 'supplente': []})
            result.append({
                'rdl_registration_id': reg.id,
                'user_id': reg.user_id,
                'email': reg.email,
                'nome': reg.nome,
                'cognome': reg.cognome,
                'full_name': f"{reg.cognome} {reg.nome}",
                'telefono': reg.telefono,
                'seggio_preferenza': reg.seggio_preferenza,
                'comune': reg.comune.nome,
                'comune_id': reg.comune_id,
                'municipio': f"Municipio {reg.municipio.numero}" if reg.municipio else None,
                'municipio_id': reg.municipio_id,
                'municipio_numero': reg.municipio.numero if reg.municipio else None,
                'sezioni_effettivo': assignments_data['effettivo'],
                'sezioni_supplente': assignments_data['supplente'],
                'totale_sezioni': len(assignments_data['effettivo']) + len(assignments_data['supplente']),
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
    """
    permission_classes = [permissions.IsAuthenticated]

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
            rdl_reg = RdlRegistration.objects.select_related('user', 'comune', 'municipio').get(
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

        # Get or create user from registration
        if rdl_reg.user:
            user = rdl_reg.user
        else:
            user, _ = User.objects.get_or_create(
                email=rdl_reg.email.lower(),
                defaults={
                    'display_name': f"{rdl_reg.nome} {rdl_reg.cognome}",
                    'first_name': rdl_reg.nome,
                    'last_name': rdl_reg.cognome,
                }
            )
            rdl_reg.user = user
            rdl_reg.save(update_fields=['user'])

        # Delete existing assignment for this role on this sezione
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
                'user': user,  # Legacy field, derivato da rdl_registration.user
                'assigned_by': request.user,
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
            assignment = SectionAssignment.objects.get(
                pk=assignment_id,
                consultazione=consultazione
            )
        except SectionAssignment.DoesNotExist:
            return Response({'error': 'Assegnazione non trovata'}, status=404)

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
    """
    permission_classes = [permissions.IsAuthenticated]

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
            rdl_reg = RdlRegistration.objects.select_related('user').get(
                pk=rdl_registration_id,
                status='APPROVED'
            )
        except RdlRegistration.DoesNotExist:
            return Response({'error': 'RDL registration non trovata o non approvata'}, status=404)

        # Get or create user
        if rdl_reg.user:
            user = rdl_reg.user
        else:
            from core.models import User
            user, _ = User.objects.get_or_create(
                email=rdl_reg.email.lower(),
                defaults={
                    'display_name': f"{rdl_reg.nome} {rdl_reg.cognome}",
                    'first_name': rdl_reg.nome,
                    'last_name': rdl_reg.cognome,
                }
            )
            rdl_reg.user = user
            rdl_reg.save(update_fields=['user'])

        # Get sezioni
        sezioni = SezioneElettorale.objects.filter(pk__in=sezioni_ids, is_attiva=True)
        if sezioni.count() != len(sezioni_ids):
            return Response({'error': 'Alcune sezioni non trovate'}, status=404)

        assigned = []
        with transaction.atomic():
            for sezione in sezioni:
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
                        'user': user,  # Legacy field
                        'role': ruolo,
                        'assigned_by': request.user,
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
