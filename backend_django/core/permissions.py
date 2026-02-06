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


class CanManageTerritory(HasCustomPermission):
    """
    Permission: Gestione territorio (regioni, province, comuni, sezioni).

    Solo superuser.
    """
    permission_codename = 'can_manage_territory'


class CanViewKPI(HasCustomPermission):
    """
    Permission: Visualizzazione dashboard KPI.

    Ruoli: Delegato, SubDelegato, KPI_VIEWER
    """
    permission_codename = 'can_view_kpi'


class CanManageElections(HasCustomPermission):
    """
    Permission: Gestione consultazioni elettorali.

    Ruoli: Superuser, Delegato
    """
    permission_codename = 'can_manage_elections'


class CanManageDelegations(HasCustomPermission):
    """
    Permission: Gestione catena deleghe (sub-deleghe, designazioni).

    Ruoli: Delegato, SubDelegato (limitato)
    """
    permission_codename = 'can_manage_delegations'


class CanManageRDL(HasCustomPermission):
    """
    Permission: Gestione RDL registrations (approvazione, import).

    Ruoli: Delegato, SubDelegato
    """
    permission_codename = 'can_manage_rdl'


class HasScrutinioAccess(HasCustomPermission):
    """
    Permission: Inserimento dati scrutinio.

    Ruoli: RDL, Delegato, SubDelegato
    """
    permission_codename = 'has_scrutinio_access'


class CanViewResources(HasCustomPermission):
    """
    Permission: Accesso risorse/documenti.

    Ruoli: Tutti autenticati (default)
    """
    permission_codename = 'can_view_resources'


class CanAskToAIAssistant(HasCustomPermission):
    """
    Permission: Accesso chatbot AI.

    Ruoli: Tutti autenticati (default)
    """
    permission_codename = 'can_ask_to_ai_assistant'


class CanGenerateDocuments(HasCustomPermission):
    """
    Permission: Generazione PDF deleghe.

    Ruoli: Delegato, SubDelegato
    """
    permission_codename = 'can_generate_documents'


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
