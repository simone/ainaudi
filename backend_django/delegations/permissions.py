"""
Permission helpers based on delegation chain.

I permessi derivano dalla catena delle deleghe:
- DelegatoDiLista → può gestire tutte le sezioni nella sua giurisdizione
- SubDelega → può gestire solo le sezioni nei comuni/municipi assegnati
- DesignazioneRDL → può inserire dati solo nella sezione assegnata
"""
from django.db.models import Q
from .models import DelegatoDiLista, SubDelega, DesignazioneRDL


def get_user_delegation_roles(user, consultazione_id=None):
    """
    Determina i ruoli dell'utente nella catena delle deleghe.

    Returns:
        dict: {
            'is_delegato': bool,
            'is_sub_delegato': bool,
            'is_rdl': bool,
            'deleghe_lista': QuerySet[DelegatoDiLista],
            'sub_deleghe': QuerySet[SubDelega],
            'designazioni': QuerySet[DesignazioneRDL],
        }
    """
    # Delegato di Lista?
    deleghe_lista = DelegatoDiLista.objects.filter(user=user)
    if consultazione_id:
        deleghe_lista = deleghe_lista.filter(consultazione_id=consultazione_id)

    # Sub-Delegato?
    sub_deleghe = SubDelega.objects.filter(user=user, is_attiva=True)
    if consultazione_id:
        sub_deleghe = sub_deleghe.filter(delegato__consultazione_id=consultazione_id)

    # RDL?
    designazioni = DesignazioneRDL.objects.filter(user=user, is_attiva=True)
    if consultazione_id:
        designazioni = designazioni.filter(
            Q(delegato__consultazione_id=consultazione_id) |
            Q(sub_delega__delegato__consultazione_id=consultazione_id)
        )

    return {
        'is_delegato': deleghe_lista.exists(),
        'is_sub_delegato': sub_deleghe.exists(),
        'is_rdl': designazioni.exists(),
        'deleghe_lista': deleghe_lista,
        'sub_deleghe': sub_deleghe,
        'designazioni': designazioni,
    }


def get_sezioni_filter_for_user(user, consultazione_id=None):
    """
    Restituisce un Q filter per le sezioni che l'utente può vedere/gestire.

    Logica:
    - SubDelegato: solo sezioni nei comuni/municipi assegnati (anche se superuser)
    - Delegato: sezioni nel suo territorio (regioni/province/comuni/municipi)
    - Superuser/Admin senza deleghe: tutte le sezioni
    - RDL: solo la sezione assegnata

    Returns:
        Q | None: Q filter per le sezioni, o None se nessun accesso
    """
    roles = get_user_delegation_roles(user, consultazione_id)

    # IMPORTANTE: Se l'utente ha una sub-delega attiva, applica SEMPRE il filtro territoriale
    # anche se è superuser. Questo permette ai superuser di testare le funzionalità di sub-delegato.
    # Se vuole vedere tutto, deve usare l'admin Django.

    # Se è sub-delegato, applica il filtro (priorità alta, anche per superuser)
    if roles['is_sub_delegato']:
        sezioni_filter = None

        for sub_delega in roles['sub_deleghe'].prefetch_related('regioni', 'province', 'comuni'):
            # Filtra per regioni
            regioni_ids = list(sub_delega.regioni.values_list('id', flat=True))
            if regioni_ids:
                new_filter = Q(comune__provincia__regione_id__in=regioni_ids)
                sezioni_filter = new_filter if sezioni_filter is None else (sezioni_filter | new_filter)

            # Filtra per province
            province_ids = list(sub_delega.province.values_list('id', flat=True))
            if province_ids:
                new_filter = Q(comune__provincia_id__in=province_ids)
                sezioni_filter = new_filter if sezioni_filter is None else (sezioni_filter | new_filter)

            # Filtra per comuni
            comuni_ids = list(sub_delega.comuni.values_list('id', flat=True))
            if comuni_ids:
                new_filter = Q(comune_id__in=comuni_ids)
                sezioni_filter = new_filter if sezioni_filter is None else (sezioni_filter | new_filter)

            # Filtra per municipi (grandi città)
            if sub_delega.municipi:
                new_filter = Q(municipio__numero__in=sub_delega.municipi)
                sezioni_filter = new_filter if sezioni_filter is None else (sezioni_filter | new_filter)

        if sezioni_filter is not None:
            return sezioni_filter
        # Se sub-delegato senza territorio configurato, continua con altri ruoli

    # Superuser senza sub-delega attiva: vede tutto
    if user.is_superuser:
        return Q()

    # Se è delegato, può vedere le sezioni nel suo territorio
    if roles['is_delegato']:
        sezioni_filter = None

        for delega in roles['deleghe_lista'].prefetch_related(
            'territorio_regioni', 'territorio_province', 'territorio_comuni'
        ):
            # Filtra per regioni
            regioni_ids = list(delega.territorio_regioni.values_list('id', flat=True))
            if regioni_ids:
                new_filter = Q(comune__provincia__regione_id__in=regioni_ids)
                sezioni_filter = new_filter if sezioni_filter is None else (sezioni_filter | new_filter)

            # Filtra per province
            province_ids = list(delega.territorio_province.values_list('id', flat=True))
            if province_ids:
                new_filter = Q(comune__provincia_id__in=province_ids)
                sezioni_filter = new_filter if sezioni_filter is None else (sezioni_filter | new_filter)

            # Filtra per comuni
            comuni_ids = list(delega.territorio_comuni.values_list('id', flat=True))
            if comuni_ids:
                new_filter = Q(comune_id__in=comuni_ids)
                sezioni_filter = new_filter if sezioni_filter is None else (sezioni_filter | new_filter)

            # Filtra per municipi (grandi città)
            if delega.territorio_municipi:
                roma_filter = Q(municipio__numero__in=delega.territorio_municipi)
                sezioni_filter = roma_filter if sezioni_filter is None else (sezioni_filter | roma_filter)

        # Se non ha territorio specificato, non vede niente (deve configurare)
        return sezioni_filter

    # Se è solo RDL, non può vedere la lista sezioni (solo la sua)
    return None


def get_sezioni_for_rdl(user, consultazione_id=None):
    """
    Restituisce le sezioni specifiche assegnate all'utente come RDL.

    Returns:
        list[int]: Lista di sezione IDs
    """
    designazioni = DesignazioneRDL.objects.filter(
        user=user,
        is_attiva=True
    )
    if consultazione_id:
        designazioni = designazioni.filter(
            Q(delegato__consultazione_id=consultazione_id) |
            Q(sub_delega__delegato__consultazione_id=consultazione_id)
        )

    return list(designazioni.values_list('sezione_id', flat=True))


def can_manage_sezione(user, sezione, consultazione_id=None):
    """
    Verifica se l'utente può gestire (assegnare RDL, vedere dati) una specifica sezione.

    Returns:
        bool
    """
    if user.is_superuser:
        return True

    roles = get_user_delegation_roles(user, consultazione_id)

    # Delegato può gestire tutto
    if roles['is_delegato']:
        return True

    # Sub-delegato può gestire solo sezioni nel suo territorio
    if roles['is_sub_delegato']:
        for sub_delega in roles['sub_deleghe'].prefetch_related('regioni', 'province', 'comuni'):
            # Check regioni
            if sezione.comune and sezione.comune.provincia:
                if sub_delega.regioni.filter(id=sezione.comune.provincia.regione_id).exists():
                    return True

            # Check province
            if sezione.comune:
                if sub_delega.province.filter(id=sezione.comune.provincia_id).exists():
                    return True

            # Check comuni
            if sub_delega.comuni.filter(id=sezione.comune_id).exists():
                return True

            # Check municipi (grandi città)
            if sub_delega.municipi and sezione.municipio:
                if sezione.municipio.numero in sub_delega.municipi:
                    return True

    return False


def can_enter_section_data(user, sezione, consultazione_id=None):
    """
    Verifica se l'utente può inserire dati per una sezione.

    Può inserire dati:
    - Delegato/SubDelegato (possono sempre inserire)
    - RDL assegnato a quella sezione

    Returns:
        bool
    """
    if user.is_superuser:
        return True

    roles = get_user_delegation_roles(user, consultazione_id)

    # Delegato o Sub-delegato possono sempre inserire
    if roles['is_delegato'] or roles['is_sub_delegato']:
        return can_manage_sezione(user, sezione, consultazione_id)

    # RDL può inserire solo nella sua sezione
    if roles['is_rdl']:
        return DesignazioneRDL.objects.filter(
            user=user,
            sezione=sezione,
            is_attiva=True
        ).exists()

    return False


def has_referenti_permission(user, consultazione_id=None):
    """
    Verifica se l'utente può gestire referenti (designare RDL).
    Solo Delegato e Sub-Delegato possono.
    """
    if user.is_superuser:
        return True

    roles = get_user_delegation_roles(user, consultazione_id)
    return roles['is_delegato'] or roles['is_sub_delegato']


def has_kpi_permission(user, consultazione_id=None):
    """
    Verifica se l'utente può vedere i KPI.
    Delegato, Sub-Delegato, e chi ha ruolo KPI_VIEWER.
    """
    if user.is_superuser:
        return True

    roles = get_user_delegation_roles(user, consultazione_id)
    if roles['is_delegato'] or roles['is_sub_delegato']:
        return True

    # Fallback: check RoleAssignment for KPI_VIEWER
    # Filter by consultazione if provided (global roles have consultazione=null)
    from core.models import RoleAssignment
    from django.db.models import Q
    filter_q = Q(user=user, role='KPI_VIEWER', is_active=True)
    if consultazione_id:
        filter_q &= Q(consultazione_id=consultazione_id) | Q(consultazione__isnull=True)
    return RoleAssignment.objects.filter(filter_q).exists()
