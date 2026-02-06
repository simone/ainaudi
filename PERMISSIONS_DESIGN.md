# Sistema Permessi Granulare - Design Document

**Data**: 2026-02-06
**Obiettivo**: Implementare permessi granulari basati su Django permissions per controllare accesso a funzionalità

---

## Requisiti

1. **Ogni voce di menu** ha un permesso specifico
2. **Endpoint protetti** da permission check
3. **Eccezione**: `GET /api/elections/active/` accessibile a TUTTI gli autenticati
4. **Regola**: Se consultazione non attiva E utente senza permessi → accesso negato
5. **Superuser**: bypassa tutti i controlli

---

## Permessi Definiti

| Permesso | Codename | Descrizione | Chi lo ha |
|----------|----------|-------------|-----------|
| **Territory Management** | `can_manage_territory` | Gestione territorio (regioni, province, comuni, sezioni) | Solo Superuser |
| **KPI Viewing** | `can_view_kpi` | Visualizzazione dashboard KPI | Delegato, SubDelegato, KPI_VIEWER role |
| **Elections Management** | `can_manage_elections` | Gestione consultazioni, schede, liste, candidati | Superuser, Delegato (limitato) |
| **Delegations Management** | `can_manage_delegations` | Gestione catena deleghe (sub-deleghe, designazioni) | Delegato, SubDelegato (limitato) |
| **RDL Management** | `can_manage_rdl` | Gestione RDL registrations (approvazione, import) | Delegato, SubDelegato |
| **Scrutinio Access** | `has_scrutinio_access` | Inserimento dati scrutinio | RDL, Delegato, SubDelegato |
| **Resources Viewing** | `can_view_resources` | Accesso risorse/documenti | Tutti autenticati (default) |
| **AI Assistant** | `can_ask_to_ai_assistant` | Accesso chatbot AI | Tutti autenticati (default) |
| **Documents Generation** | `can_generate_documents` | Generazione PDF deleghe | Delegato, SubDelegato |
| **Incidents Management** | `can_manage_incidents` | Segnalazioni incidenti | RDL, Delegato, SubDelegato |

---

## Mapping Permessi → Ruoli

### Superuser
```python
ALL_PERMISSIONS = True  # Bypass check
```

### Delegato di Lista
```python
permissions = [
    'can_view_kpi',
    'can_manage_elections',  # Solo consultazioni del suo territorio
    'can_manage_delegations',
    'can_manage_rdl',
    'has_scrutinio_access',
    'can_view_resources',
    'can_ask_to_ai_assistant',
    'can_generate_documents',
    'can_manage_incidents',
]
```

### SubDelegato
```python
permissions = [
    'can_view_kpi',
    'can_manage_delegations',  # Solo sue sub-deleghe
    'can_manage_rdl',
    'has_scrutinio_access',
    'can_view_resources',
    'can_ask_to_ai_assistant',
    'can_generate_documents',
    'can_manage_incidents',
]
```

### RDL
```python
permissions = [
    'has_scrutinio_access',
    'can_view_resources',
    'can_ask_to_ai_assistant',
    'can_manage_incidents',  # Solo propri incident
]
```

### KPI_VIEWER (Ruolo speciale)
```python
permissions = [
    'can_view_kpi',
    'can_view_resources',
]
```

---

## Implementazione Django

### 1. Definizione Permessi in Model

**File**: `backend_django/core/models.py`

```python
from django.db import models
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

class CustomPermission(models.Model):
    """
    Proxy model per definire custom permissions.
    Non crea tabella, usa django.contrib.auth.Permission.
    """
    class Meta:
        managed = False
        default_permissions = ()
        permissions = [
            ('can_manage_territory', 'Can manage territory (regions, provinces, comuni, sections)'),
            ('can_view_kpi', 'Can view KPI dashboard'),
            ('can_manage_elections', 'Can manage elections and ballots'),
            ('can_manage_delegations', 'Can manage delegations chain'),
            ('can_manage_rdl', 'Can manage RDL registrations'),
            ('has_scrutinio_access', 'Can enter section scrutinio data'),
            ('can_view_resources', 'Can view resources and documents'),
            ('can_ask_to_ai_assistant', 'Can use AI assistant chatbot'),
            ('can_generate_documents', 'Can generate PDF documents'),
            ('can_manage_incidents', 'Can manage incident reports'),
        ]
```

### 2. Migration per Creare Permessi

**File**: `backend_django/core/migrations/XXXX_add_custom_permissions.py`

```python
from django.db import migrations

def create_permissions(apps, schema_editor):
    """Crea permessi custom se non esistono"""
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')

    # Get or create content type per "core" app
    content_type, _ = ContentType.objects.get_or_create(
        app_label='core',
        model='custompermission'
    )

    permissions = [
        ('can_manage_territory', 'Can manage territory'),
        ('can_view_kpi', 'Can view KPI dashboard'),
        ('can_manage_elections', 'Can manage elections'),
        ('can_manage_delegations', 'Can manage delegations'),
        ('can_manage_rdl', 'Can manage RDL registrations'),
        ('has_scrutinio_access', 'Can enter scrutinio data'),
        ('can_view_resources', 'Can view resources'),
        ('can_ask_to_ai_assistant', 'Can use AI assistant'),
        ('can_generate_documents', 'Can generate documents'),
        ('can_manage_incidents', 'Can manage incidents'),
    ]

    for codename, name in permissions:
        Permission.objects.get_or_create(
            codename=codename,
            content_type=content_type,
            defaults={'name': name}
        )

class Migration(migrations.Migration):
    dependencies = [
        ('core', 'XXXX_previous_migration'),
    ]

    operations = [
        migrations.RunPython(create_permissions),
    ]
```

### 3. Assegnazione Automatica Permessi

**File**: `backend_django/core/auth_utils.py`

```python
def assign_permissions_for_role(user, role):
    """
    Assegna permessi basati sul ruolo.
    Chiamata da ensure_role_assigned() e signals.
    """
    from django.contrib.auth.models import Permission
    from core.models import RoleAssignment

    # Superuser ha tutto
    if user.is_superuser:
        return

    # Mapping ruolo → permessi
    role_permissions = {
        RoleAssignment.Role.DELEGATO: [
            'can_view_kpi',
            'can_manage_elections',
            'can_manage_delegations',
            'can_manage_rdl',
            'has_scrutinio_access',
            'can_view_resources',
            'can_ask_to_ai_assistant',
            'can_generate_documents',
            'can_manage_incidents',
        ],
        RoleAssignment.Role.SUB_DELEGATO: [
            'can_view_kpi',
            'can_manage_delegations',
            'can_manage_rdl',
            'has_scrutinio_access',
            'can_view_resources',
            'can_ask_to_ai_assistant',
            'can_generate_documents',
            'can_manage_incidents',
        ],
        RoleAssignment.Role.RDL: [
            'has_scrutinio_access',
            'can_view_resources',
            'can_ask_to_ai_assistant',
            'can_manage_incidents',
        ],
        RoleAssignment.Role.KPI_VIEWER: [
            'can_view_kpi',
            'can_view_resources',
        ],
    }

    codenames = role_permissions.get(role, [])

    # Rimuovi permessi precedenti del gruppo core
    user.user_permissions.filter(
        content_type__app_label='core',
        content_type__model='custompermission'
    ).delete()

    # Assegna nuovi permessi
    permissions = Permission.objects.filter(
        codename__in=codenames,
        content_type__app_label='core',
        content_type__model='custompermission'
    )

    user.user_permissions.add(*permissions)
```

### 4. Aggiornamento PermissionsView

**File**: `backend_django/core/views.py`

```python
class PermissionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Superuser ha tutto
        if user.is_superuser:
            return Response({
                'is_superuser': True,
                'can_manage_territory': True,
                'can_view_kpi': True,
                'can_manage_elections': True,
                'can_manage_delegations': True,
                'can_manage_rdl': True,
                'has_scrutinio_access': True,
                'can_view_resources': True,
                'can_ask_to_ai_assistant': True,
                'can_generate_documents': True,
                'can_manage_incidents': True,

                # Backwards compatibility
                'sections': True,
                'referenti': True,
                'kpi': True,
                'upload_sezioni': True,
                'gestione_rdl': True,
            })

        # Check permessi Django
        permissions = {
            'is_superuser': False,
            'can_manage_territory': user.has_perm('core.can_manage_territory'),
            'can_view_kpi': user.has_perm('core.can_view_kpi'),
            'can_manage_elections': user.has_perm('core.can_manage_elections'),
            'can_manage_delegations': user.has_perm('core.can_manage_delegations'),
            'can_manage_rdl': user.has_perm('core.can_manage_rdl'),
            'has_scrutinio_access': user.has_perm('core.has_scrutinio_access'),
            'can_view_resources': user.has_perm('core.can_view_resources'),
            'can_ask_to_ai_assistant': user.has_perm('core.can_ask_to_ai_assistant'),
            'can_generate_documents': user.has_perm('core.can_generate_documents'),
            'can_manage_incidents': user.has_perm('core.can_manage_incidents'),

            # Backwards compatibility (deprecare in futuro)
            'sections': user.has_perm('core.has_scrutinio_access'),
            'referenti': user.has_perm('core.can_manage_rdl'),
            'kpi': user.has_perm('core.can_view_kpi'),
            'upload_sezioni': user.has_perm('core.can_manage_territory'),
            'gestione_rdl': user.has_perm('core.can_manage_rdl'),
        }

        return Response(permissions)
```

---

## Protezione Endpoints

### Custom Permission Classes

**File**: `backend_django/core/permissions.py`

```python
from rest_framework.permissions import BasePermission

class HasPermission(BasePermission):
    """
    Generic permission checker.
    Usage: permission_classes = [HasPermission('can_view_kpi')]
    """
    def __init__(self, perm_codename):
        self.perm_codename = perm_codename
        super().__init__()

    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        return request.user.has_perm(f'core.{self.perm_codename}')

# Shortcut classes
class CanManageTerritory(HasPermission):
    def __init__(self):
        super().__init__('can_manage_territory')

class CanViewKPI(HasPermission):
    def __init__(self):
        super().__init__('can_view_kpi')

class CanManageElections(HasPermission):
    def __init__(self):
        super().__init__('can_manage_elections')

class CanManageDelegations(HasPermission):
    def __init__(self):
        super().__init__('can_manage_delegations')

class CanManageRDL(HasPermission):
    def __init__(self):
        super().__init__('can_manage_rdl')

class HasScrutinioAccess(HasPermission):
    def __init__(self):
        super().__init__('has_scrutinio_access')

class CanViewResources(HasPermission):
    def __init__(self):
        super().__init__('can_view_resources')

class CanGenerateDocuments(HasPermission):
    def __init__(self):
        super().__init__('can_generate_documents')

class CanManageIncidents(HasPermission):
    def __init__(self):
        super().__init__('can_manage_incidents')
```

### Decorator per Function-Based Views

```python
from functools import wraps
from rest_framework.response import Response

def require_permission(perm_codename):
    """
    Decorator per controllare permesso.
    Usage: @require_permission('can_view_kpi')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            if not request.user.has_perm(f'core.{perm_codename}'):
                return Response(
                    {'error': 'Non hai il permesso necessario'},
                    status=403
                )

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
```

---

## Applicazione Permessi per App

### KPI
```python
# backend_django/kpi/views.py
from core.permissions import CanViewKPI

class KPIDatiView(APIView):
    permission_classes = [IsAuthenticated, CanViewKPI]
    # ...

class KPISezioniView(APIView):
    permission_classes = [IsAuthenticated, CanViewKPI]
    # ...
```

### Territory
```python
# backend_django/territory/views.py
from core.permissions import CanManageTerritory

class RegioneViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # Read: tutti possono leggere (per select dropdown)
            return [IsAuthenticated()]
        else:
            # Write: solo can_manage_territory
            return [IsAuthenticated(), CanManageTerritory()]
```

### Elections
```python
# backend_django/elections/views.py
from core.permissions import CanManageElections

class ConsultazioniListView(ListAPIView):
    permission_classes = [IsAuthenticated, CanManageElections]
    # ...

class ConsultazioneAttivaView(APIView):
    permission_classes = [IsAuthenticated]  # ECCEZIONE: tutti possono vedere
    # ...

class SchedaElettoraleDetailView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        # Check permesso per PATCH/PUT
        if not request.user.has_perm('core.can_manage_elections'):
            return Response({'error': 'Non autorizzato'}, status=403)
        # ...
```

### Delegations
```python
# backend_django/delegations/views.py
from core.permissions import CanManageDelegations

class SubDelegaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, CanManageDelegations]
    # ...

class DesignazioneRDLViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, CanManageDelegations]
    # ...
```

### Data (RDL Management)
```python
# backend_django/data/views.py
from core.permissions import CanManageRDL, HasScrutinioAccess

class RdlRegistrationListView(APIView):
    permission_classes = [IsAuthenticated, CanManageRDL]
    # ...

class ScrutinioSaveView(APIView):
    permission_classes = [IsAuthenticated, HasScrutinioAccess]
    # ...
```

### Resources
```python
# backend_django/resources/views.py
from core.permissions import CanViewResources

class RisorseView(ListAPIView):
    permission_classes = [IsAuthenticated, CanViewResources]
    # ...
```

### Documents
```python
# backend_django/documents/views.py
from core.permissions import CanGenerateDocuments

class GeneratePDFView(APIView):
    permission_classes = [IsAuthenticated, CanGenerateDocuments]
    # ...
```

### Incidents
```python
# backend_django/incidents/views.py
from core.permissions import CanManageIncidents

class IncidentReportViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, CanManageIncidents]
    # ...
```

---

## Frontend: Menu Condizionale

### App.js Navigation

```javascript
const { permissions } = useAuth();

// Menu items con permessi
const menuItems = [
    {
        label: 'Dashboard',
        path: '/dashboard',
        icon: 'fas fa-tachometer-alt',
        show: true,  // Sempre visibile
    },
    {
        label: 'KPI',
        path: '/kpi',
        icon: 'fas fa-chart-line',
        show: permissions.can_view_kpi,
    },
    {
        label: 'Scrutinio',
        path: '/scrutinio',
        icon: 'fas fa-vote-yea',
        show: permissions.has_scrutinio_access,
    },
    {
        label: 'Gestione RDL',
        path: '/rdl',
        icon: 'fas fa-users',
        show: permissions.can_manage_rdl,
    },
    {
        label: 'Deleghe',
        path: '/deleghe',
        icon: 'fas fa-sitemap',
        show: permissions.can_manage_delegations,
    },
    {
        label: 'Designazioni',
        path: '/designazioni',
        icon: 'fas fa-clipboard-list',
        show: permissions.can_manage_delegations,
    },
    {
        label: 'Mappatura',
        path: '/mappatura',
        icon: 'fas fa-map-marked-alt',
        show: permissions.can_manage_delegations,
    },
    {
        label: 'Elezioni',
        path: '/elezioni',
        icon: 'fas fa-vote',
        show: permissions.can_manage_elections,
    },
    {
        label: 'Territorio',
        path: '/territorio',
        icon: 'fas fa-globe',
        show: permissions.can_manage_territory,
    },
    {
        label: 'Risorse',
        path: '/risorse',
        icon: 'fas fa-book',
        show: permissions.can_view_resources,
    },
    {
        label: 'Documenti',
        path: '/documenti',
        icon: 'fas fa-file-pdf',
        show: permissions.can_generate_documents,
    },
    {
        label: 'Incidenti',
        path: '/incidenti',
        icon: 'fas fa-exclamation-triangle',
        show: permissions.can_manage_incidents,
    },
    {
        label: 'AI Assistant',
        path: '/ai',
        icon: 'fas fa-robot',
        show: permissions.can_ask_to_ai_assistant,
    },
];

// Render only visible items
{menuItems.filter(item => item.show).map(item => (
    <NavLink to={item.path} key={item.path}>
        <i className={item.icon}></i> {item.label}
    </NavLink>
))}
```

---

## Regola Consultazione Attiva

**Logica**:
1. User fa login
2. Frontend chiama `/api/elections/active/` (sempre accessibile)
3. Se consultazione attiva:
   - User vede dashboard con consultazione corrente
   - Menu mostrato in base ai permessi
4. Se consultazione NON attiva:
   - Se user ha almeno un permesso gestionale → accesso concesso
   - Se user non ha permessi → redirect a pagina "Nessuna consultazione attiva"

**Implementazione Frontend**:

```javascript
// App.js
const CheckConsultationAccess = () => {
    const { activeElection, permissions } = useAuth();

    // Se consultazione attiva, OK
    if (activeElection) {
        return <Outlet />;
    }

    // Se NO consultazione attiva, check permessi gestionali
    const hasManagementPermissions =
        permissions.is_superuser ||
        permissions.can_manage_elections ||
        permissions.can_manage_territory ||
        permissions.can_manage_delegations ||
        permissions.can_manage_rdl;

    if (hasManagementPermissions) {
        // Permetti accesso anche senza consultazione attiva
        return <Outlet />;
    }

    // Altrimenti, mostra pagina "Nessuna consultazione attiva"
    return (
        <div className="alert alert-warning">
            <h3>Nessuna consultazione elettorale attiva</h3>
            <p>Al momento non ci sono consultazioni elettorali attive. Verrai avvisato quando una nuova consultazione sarà disponibile.</p>
        </div>
    );
};
```

---

## Testing Permessi

### Unit Tests

```python
# backend_django/core/tests/test_permissions.py

class PermissionsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(email='test@example.com')
        self.delegato = User.objects.create(email='delegato@example.com')

        # Assegna ruolo Delegato
        from core.auth_utils import assign_permissions_for_role
        assign_permissions_for_role(self.delegato, RoleAssignment.Role.DELEGATO)

    def test_delegato_has_kpi_permission(self):
        self.assertTrue(self.delegato.has_perm('core.can_view_kpi'))

    def test_delegato_has_no_territory_permission(self):
        self.assertFalse(self.delegato.has_perm('core.can_manage_territory'))

    def test_rdl_has_scrutinio_access(self):
        rdl = User.objects.create(email='rdl@example.com')
        assign_permissions_for_role(rdl, RoleAssignment.Role.RDL)

        self.assertTrue(rdl.has_perm('core.has_scrutinio_access'))

    def test_rdl_cannot_manage_elections(self):
        rdl = User.objects.create(email='rdl@example.com')
        assign_permissions_for_role(rdl, RoleAssignment.Role.RDL)

        self.assertFalse(rdl.has_perm('core.can_manage_elections'))

    def test_kpi_view_requires_permission(self):
        client = APIClient()
        client.force_authenticate(user=self.user)

        # User senza permesso
        response = client.get('/api/kpi/dati')
        self.assertEqual(response.status_code, 403)

        # Delegato con permesso
        client.force_authenticate(user=self.delegato)
        response = client.get('/api/kpi/dati')
        self.assertEqual(response.status_code, 200)
```

---

## Migration Plan

### Phase 1: Creare Permessi
1. ✅ Definire CustomPermission model
2. ✅ Creare migration per permessi
3. ✅ Eseguire migration

### Phase 2: Assegnazione Automatica
1. ✅ Implementare assign_permissions_for_role()
2. ✅ Aggiornare signals per assegnare permessi quando si crea RoleAssignment
3. ✅ Script di migrazione per assegnare permessi agli utenti esistenti

### Phase 3: Backend Protection
1. ✅ Creare permission classes (CanViewKPI, etc.)
2. ✅ Aggiornare ogni view con permission_classes appropriata
3. ✅ Testing endpoint protection

### Phase 4: Frontend
1. ✅ Aggiornare PermissionsView per ritornare flags
2. ✅ Aggiornare AuthContext per gestire nuovi permessi
3. ✅ Implementare menu condizionale
4. ✅ Implementare CheckConsultationAccess

### Phase 5: Testing & Rollout
1. ✅ Unit tests per permessi
2. ✅ Integration tests per endpoint protection
3. ✅ Manual testing con diversi ruoli
4. ✅ Deploy

---

## Checklist Implementazione

- [ ] core/models.py: CustomPermission model
- [ ] core/migrations/XXXX_add_custom_permissions.py
- [ ] core/auth_utils.py: assign_permissions_for_role()
- [ ] core/permissions.py: Permission classes
- [ ] core/views.py: Aggiornare PermissionsView
- [ ] core/signals.py: Auto-assegnare permessi su RoleAssignment create
- [ ] Script: Migrare permessi per utenti esistenti
- [ ] kpi/views.py: Aggiungere CanViewKPI
- [ ] territory/views.py: Aggiungere CanManageTerritory (write only)
- [ ] elections/views.py: Aggiungere CanManageElections (eccetto active)
- [ ] delegations/views.py: Aggiungere CanManageDelegations
- [ ] data/views.py: Aggiungere CanManageRDL, HasScrutinioAccess
- [ ] resources/views.py: Aggiungere CanViewResources
- [ ] documents/views.py: Aggiungere CanGenerateDocuments
- [ ] incidents/views.py: Aggiungere CanManageIncidents
- [ ] src/AuthContext.js: Gestire nuovi permessi
- [ ] src/App.js: Menu condizionale + CheckConsultationAccess
- [ ] Tests: Unit + Integration
- [ ] Documentation: Aggiornare SECURITY_REVIEW.md

---

**Fine Design Document**
