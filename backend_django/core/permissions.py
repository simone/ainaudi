"""
Custom permission classes per Django REST Framework.

Implementa controlli granulari basati su django.contrib.auth.permissions.
Ogni permission class verifica se l'utente ha il permesso Django appropriato.

Usage:
    class MyView(APIView):
        permission_classes = [IsAuthenticated, CanViewKPI]
"""
from rest_framework.permissions import BasePermission


class HasCustomPermission(BasePermission):
    """
    Base permission class che verifica un permesso custom.

    Args:
        permission_codename: Il codename del permesso (es. 'can_view_kpi')

    Usage:
        permission_classes = [HasCustomPermission('can_view_kpi')]
    """
    permission_codename = None

    def __init__(self, permission_codename=None):
        if permission_codename:
            self.permission_codename = permission_codename
        super().__init__()

    def has_permission(self, request, view):
        # Superuser bypassa tutti i controlli
        if request.user and request.user.is_superuser:
            return True

        # Check permesso Django
        if not self.permission_codename:
            return False

        return request.user.has_perm(f'core.{self.permission_codename}')

    def get_message(self):
        """Messaggio di errore personalizzato."""
        return f'Permesso richiesto: {self.permission_codename}'


class IsSuperAdmin(BasePermission):
    """
    Permission: Solo superadmin (is_staff=True).

    Questo permesso verifica che l'utente sia uno staff member (admin Django).
    Usato per endpoint di amministrazione che non devono essere accessibili
    a delegati o altri ruoli.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff

    def get_message(self):
        return 'Solo gli amministratori possono accedere a questa risorsa'


# ============================================================================
# PERMESSI GRANULARI - Uno per ogni voce del menu
# ============================================================================

class CanViewDashboard(HasCustomPermission):
    """
    Permission: Visualizzazione dashboard principale.

    Ruoli: Delegato, SubDelegato
    """
    permission_codename = 'can_view_dashboard'


class CanManageTerritory(HasCustomPermission):
    """
    Permission: Gestione territorio (regioni, province, comuni, sezioni).

    Ruoli: Solo superuser
    """
    permission_codename = 'can_manage_territory'


class CanManageElections(HasCustomPermission):
    """
    Permission: Gestione consultazioni elettorali (schede, liste, candidati).

    Ruoli: Superuser, Delegato
    """
    permission_codename = 'can_manage_elections'


class CanManageCampaign(HasCustomPermission):
    """
    Permission: Gestione campagne reclutamento RDL.

    Ruoli: Delegato, SubDelegato
    """
    permission_codename = 'can_manage_campaign'


class CanManageRDL(HasCustomPermission):
    """
    Permission: Gestione RDL registrations (approvazione, import CSV).

    Ruoli: Delegato, SubDelegato
    """
    permission_codename = 'can_manage_rdl'


class CanManageSections(HasCustomPermission):
    """
    Permission: Gestione sezioni elettorali (CRUD sezioni).

    Ruoli: Delegato, SubDelegato
    """
    permission_codename = 'can_manage_sections'


class CanManageMappatura(HasCustomPermission):
    """
    Permission: Mappatura RDL → Sezioni (assegnamento RDL a seggi).

    Ruoli: Delegato, SubDelegato
    """
    permission_codename = 'can_manage_mappatura'


class CanManageDelegations(HasCustomPermission):
    """
    Permission: Gestione catena deleghe (delegati, sub-deleghe).

    Ruoli: Delegato
    """
    permission_codename = 'can_manage_delegations'


class CanManageDesignazioni(HasCustomPermission):
    """
    Permission: Gestione designazioni RDL formali (documenti ufficiali).

    Ruoli: Delegato, SubDelegato
    """
    permission_codename = 'can_manage_designazioni'


class CanManageTemplates(HasCustomPermission):
    """
    Permission: Gestione template PDF.

    Ruoli: Delegato, SubDelegato
    """
    permission_codename = 'can_manage_templates'


class HasScrutinioAccess(HasCustomPermission):
    """
    Permission: Inserimento dati scrutinio.

    Ruoli: RDL, Delegato, SubDelegato
    """
    permission_codename = 'has_scrutinio_access'


class CanViewResources(HasCustomPermission):
    """
    Permission: Accesso risorse/documenti.

    Ruoli: Tutti gli utenti con ruolo
    """
    permission_codename = 'can_view_resources'


class CanViewLiveResults(HasCustomPermission):
    """
    Permission: Visualizzazione risultati live (scrutinio aggregato).

    Ruoli: Delegato, SubDelegato
    """
    permission_codename = 'can_view_live_results'


class CanViewKPI(HasCustomPermission):
    """
    Permission: Visualizzazione dashboard KPI/Diretta.

    Ruoli: Delegato, SubDelegato, KPI_VIEWER
    """
    permission_codename = 'can_view_kpi'


class CanManageMassEmail(HasCustomPermission):
    """
    Permission: Gestione email massiva (template + invio).

    Ruoli: Solo superuser (admin)
    """
    permission_codename = 'can_manage_mass_email'


# ============================================================================
# PERMESSI EXTRA / FUTURE FEATURES
# ============================================================================

class CanAskToAIAssistant(HasCustomPermission):
    """
    Permission: Accesso chatbot AI (futuro).

    Ruoli: Tutti autenticati (default)
    """
    permission_codename = 'can_ask_to_ai_assistant'


class CanGenerateDocuments(BasePermission):
    """
    Permission: Generazione PDF deleghe.

    Ruoli: Delegato, SubDelegato con firma autenticata
    """
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True

        # Import qui per evitare circular imports
        from delegations.models import Delegato, SubDelega

        # Check se è Delegato
        if Delegato.objects.filter(email=request.user.email).exists():
            return True

        # Check se è SubDelegato con firma autenticata
        if SubDelega.objects.filter(
            email=request.user.email,
            is_attiva=True,
            tipo_delega='FIRMA_AUTENTICATA'
        ).exists():
            return True

        return False


class CanManageIncidents(HasCustomPermission):
    """
    Permission: Gestione segnalazioni incidenti.

    Ruoli: RDL, Delegato, SubDelegato
    """
    permission_codename = 'can_manage_incidents'


class IsAdminForWriteOperations(BasePermission):
    """
    Permission speciale per Territory endpoints.

    - Read (GET): Tutti autenticati
    - Write (POST/PUT/PATCH/DELETE): Solo superuser
    """
    def has_permission(self, request, view):
        # Tutti possono leggere
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return request.user and request.user.is_authenticated

        # Solo superuser può scrivere
        return request.user and request.user.is_superuser
