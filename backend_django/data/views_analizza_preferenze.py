"""
View per analizzare le preferenze RDL e suggerire sezioni da assegnare.
"""
import re
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q

from core.permissions import CanManageDelegations
from campaign.models import RdlRegistration
from territory.models import SezioneElettorale
from .models import SectionAssignment
from .views import get_consultazione_attiva


def parse_numeri_sezione(testo):
    """
    Estrae numeri di sezione dal testo.
    Supporta:
    - Numeri singoli: "123"
    - Virgole: "123, 124, 125"
    - Range: "123-125"
    - Misti: "123, 125-127, 130"

    Returns: set di numeri di sezione (int)
    """
    numeri = set()

    # Remove common prefixes like "Sez.", "Sezione", etc.
    testo = re.sub(r'\b(sez\.?|sezione)\s*', '', testo, flags=re.IGNORECASE)

    # Find all patterns: single numbers or ranges
    # Pattern: one or more digits, optionally followed by dash and more digits
    patterns = re.findall(r'(\d+)(?:\s*[-–]\s*(\d+))?', testo)

    for match in patterns:
        start = int(match[0])
        end = int(match[1]) if match[1] else start

        # Add all numbers in range
        for num in range(start, end + 1):
            numeri.add(num)

    return numeri


class MappaturaAnalizzaPreferenzeView(APIView):
    """
    Analizza la preferenza di un RDL e suggerisce sezioni da assegnare.

    POST /api/mappatura/analizza-preferenze/
    Body: {
        "rdl_registration_id": 123,
        "preferenza": "Sezioni 101, 102, 105-107 o Via Roma"
    }

    Returns: {
        "sezioni_numeri": [sezioni trovate per numero],
        "sezioni_indirizzo": [sezioni trovate per indirizzo],
        "sezioni_plesso": [sezioni trovate per denominazione plesso],
        "totale": int
    }

    Permission: can_manage_delegations (Delegato, SubDelegato)
    """
    permission_classes = [permissions.IsAuthenticated, CanManageDelegations]

    def post(self, request):
        from delegations.permissions import has_referenti_permission

        consultazione = get_consultazione_attiva()
        if not consultazione:
            return Response({'error': 'Nessuna consultazione attiva'}, status=400)

        if not has_referenti_permission(request.user, consultazione.id):
            return Response({'error': 'Non autorizzato'}, status=403)

        rdl_registration_id = request.data.get('rdl_registration_id')
        preferenza = request.data.get('preferenza', '').strip()

        if not rdl_registration_id:
            return Response({'error': 'rdl_registration_id è obbligatorio'}, status=400)

        if not preferenza:
            return Response({'error': 'Nessuna preferenza da analizzare'}, status=400)

        # Get RDL registration
        try:
            rdl_reg = RdlRegistration.objects.select_related('comune', 'municipio').get(
                pk=rdl_registration_id,
                status='APPROVED'
            )
        except RdlRegistration.DoesNotExist:
            return Response({'error': 'RDL registration non trovata o non approvata'}, status=404)

        # Base filter: sezioni in RDL's territory
        base_filter = Q(is_attiva=True, comune=rdl_reg.comune)
        if rdl_reg.municipio:
            base_filter &= Q(municipio=rdl_reg.municipio)

        # Get existing assignments for this consultazione in RDL's territory
        assigned_sezioni_ids = set(
            SectionAssignment.objects.filter(
                consultazione=consultazione,
                sezione__comune=rdl_reg.comune
            ).values_list('sezione_id', flat=True)
        )

        # 1. Parse numeri di sezione
        numeri = parse_numeri_sezione(preferenza)
        sezioni_numeri = []
        if numeri:
            sezioni_by_numero = SezioneElettorale.objects.filter(
                base_filter,
                numero__in=numeri
            ).select_related('comune', 'municipio')

            for sez in sezioni_by_numero:
                is_assigned = sez.id in assigned_sezioni_ids
                # Check who is assigned
                effettivo = None
                supplente = None
                if is_assigned:
                    assignments = SectionAssignment.objects.filter(
                        sezione=sez,
                        consultazione=consultazione
                    ).select_related('rdl_registration')
                    for a in assignments:
                        if a.role == 'RDL':
                            effettivo = f"{a.rdl_registration.cognome} {a.rdl_registration.nome}"
                        else:
                            supplente = f"{a.rdl_registration.cognome} {a.rdl_registration.nome}"

                sezioni_numeri.append({
                    'id': sez.id,
                    'numero': sez.numero,
                    'denominazione': sez.denominazione or '',
                    'indirizzo': sez.indirizzo or '',
                    'comune': sez.comune.nome,
                    'municipio': sez.municipio.numero if sez.municipio else None,
                    'is_assigned': is_assigned,
                    'effettivo': effettivo,
                    'supplente': supplente,
                    'match_type': 'numero'
                })

        # 2. Search by indirizzo (exclude numbers already found)
        sezioni_indirizzo = []
        # Extract potential address keywords (words longer than 3 chars, not numbers)
        words = re.findall(r'\b[a-zA-Zàèéìòù]{4,}\b', preferenza, re.IGNORECASE)
        if words:
            address_query = Q()
            for word in words[:3]:  # Limit to first 3 words to avoid over-matching
                address_query |= Q(indirizzo__icontains=word)

            sezioni_by_address = SezioneElettorale.objects.filter(
                base_filter,
                address_query
            ).exclude(numero__in=numeri).select_related('comune', 'municipio')[:10]

            for sez in sezioni_by_address:
                is_assigned = sez.id in assigned_sezioni_ids
                effettivo = None
                supplente = None
                if is_assigned:
                    assignments = SectionAssignment.objects.filter(
                        sezione=sez,
                        consultazione=consultazione
                    ).select_related('rdl_registration')
                    for a in assignments:
                        if a.role == 'RDL':
                            effettivo = f"{a.rdl_registration.cognome} {a.rdl_registration.nome}"
                        else:
                            supplente = f"{a.rdl_registration.cognome} {a.rdl_registration.nome}"

                sezioni_indirizzo.append({
                    'id': sez.id,
                    'numero': sez.numero,
                    'denominazione': sez.denominazione or '',
                    'indirizzo': sez.indirizzo or '',
                    'comune': sez.comune.nome,
                    'municipio': sez.municipio.numero if sez.municipio else None,
                    'is_assigned': is_assigned,
                    'effettivo': effettivo,
                    'supplente': supplente,
                    'match_type': 'indirizzo'
                })

        # 3. Search by denominazione plesso (exclude numbers already found)
        sezioni_plesso = []
        if words:
            plesso_query = Q()
            for word in words[:3]:
                plesso_query |= Q(denominazione__icontains=word)

            sezioni_by_plesso = SezioneElettorale.objects.filter(
                base_filter,
                plesso_query
            ).exclude(numero__in=numeri).select_related('comune', 'municipio')[:10]

            for sez in sezioni_by_plesso:
                is_assigned = sez.id in assigned_sezioni_ids
                effettivo = None
                supplente = None
                if is_assigned:
                    assignments = SectionAssignment.objects.filter(
                        sezione=sez,
                        consultazione=consultazione
                    ).select_related('rdl_registration')
                    for a in assignments:
                        if a.role == 'RDL':
                            effettivo = f"{a.rdl_registration.cognome} {a.rdl_registration.nome}"
                        else:
                            supplente = f"{a.rdl_registration.cognome} {a.rdl_registration.nome}"

                sezioni_plesso.append({
                    'id': sez.id,
                    'numero': sez.numero,
                    'denominazione': sez.denominazione or '',
                    'indirizzo': sez.indirizzo or '',
                    'comune': sez.comune.nome,
                    'municipio': sez.municipio.numero if sez.municipio else None,
                    'is_assigned': is_assigned,
                    'effettivo': effettivo,
                    'supplente': supplente,
                    'match_type': 'plesso'
                })

        # Combine all results (dedup by id)
        all_sezioni = {}
        for sez in sezioni_numeri + sezioni_indirizzo + sezioni_plesso:
            if sez['id'] not in all_sezioni:
                all_sezioni[sez['id']] = sez

        all_sezioni_list = sorted(all_sezioni.values(), key=lambda x: x['numero'])

        return Response({
            'sezioni_numeri': sezioni_numeri,
            'sezioni_indirizzo': sezioni_indirizzo,
            'sezioni_plesso': sezioni_plesso,
            'all_sezioni': all_sezioni_list,
            'totale': len(all_sezioni),
            'disponibili': len([s for s in all_sezioni_list if not s['is_assigned']]),
            'gia_assegnate': len([s for s in all_sezioni_list if s['is_assigned']])
        })
