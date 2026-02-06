# Security Review - Backend API Endpoints

**Data**: 2026-02-06
**Analisi**: Tutti gli endpoint backend con focus su autenticazione e controlli territoriali

---

## Executive Summary

### Situazione Attuale

✅ **Punti di forza:**
- Sistema JWT con Magic Link funzionante
- Controlli territoriali implementati per molte operazioni critiche
- Separazione ruoli (Delegato, SubDelegato, RDL) con permessi distinti
- Funzioni centralizzate per controllo territorio (`get_sezioni_filter_for_user`, `can_enter_section_data`)

❌ **Criticità identificate:**
1. **KPI endpoints SENZA filtri territoriali** - espongono dati globali
2. **Territory endpoints leggibili da TUTTI** gli utenti autenticati
3. **Elections endpoints senza filtri** - visibilità globale consultazioni
4. **Resources/Documents parzialmente pubblici** con logica is_pubblico poco chiara
5. **Mancanza di controllo territorio su READ operations** in molti endpoint

---

## 1. Endpoint per Stato di Autenticazione

### 🔓 PUBBLICI (AllowAny - 8 endpoint)

| Endpoint | Auth | Uso | Rischio |
|----------|------|-----|---------|
| `POST /api/auth/magic-link/request/` | None | Richiesta magic link | ✅ OK |
| `POST /api/auth/magic-link/verify/` | None | Verifica token | ✅ OK |
| `GET /api/risorse/` | None* | Lista risorse pubbliche | ⚠️ Medio |
| `GET /api/risorse/documenti/` | None* | Lista documenti pubblici | ⚠️ Medio |
| `GET /api/risorse/faqs/` | None* | Lista FAQ pubbliche | ⚠️ Medio |
| `GET /api/risorse/pdf-proxy/` | None | Proxy PDF esterni | ⚠️ Alto |
| `GET/POST /api/documents/confirm/` | Token | Conferma PDF via email | ✅ OK |
| `GET /api/documents/media/<path>` | None | Serve file media | ⚠️ Alto |

\* Filtra per `is_pubblico=True` se non autenticato

**Note critiche:**
- **PDFProxyView**: Whitelist domini configurabile, possibile SSRF se mal configurato
- **ServeMediaView**: Path traversal prevention presente ma da verificare
- **Resources con is_pubblico**: Logica poco chiara, rischio leak dati sensibili

---

### 🔒 AUTENTICATI (IsAuthenticated)

Tutti gli altri endpoint richiedono JWT token valido.

---

## 2. Endpoint per Controllo Territoriale

### ✅ CON CONTROLLI TERRITORIO CORRETTI

| Endpoint | Metodo | Controllo | Note |
|----------|--------|-----------|------|
| `GET /api/sections/stats` | GET | `get_sezioni_filter_for_user()` | Statistiche filtrate |
| `GET /api/sections/list/` | GET | `get_sezioni_filter_for_user()` | Sezioni filtrate |
| `PATCH /api/sections/<id>/` | PATCH | `get_sezioni_filter_for_user()` | Verifica sezione visibile |
| `GET /api/sections/assigned` | GET | `get_sezioni_filter_for_user()` | Territorio gestito |
| `GET /api/sections/own` | GET | SectionAssignment + email | Solo sezioni RDL |
| `POST /api/sections/` | POST | `can_enter_section_data()` | Scrittura dati sezione |
| `GET /api/scrutinio/sezioni` | GET | `get_sezioni_filter_for_user()` + RDL check | Sezioni filtrate |
| `POST /api/scrutinio/save` | POST | `can_enter_section_data()` | Scrittura scrutinio |
| `GET /api/delegations/sub-deleghe/` | GET | Filtra per email utente | QuerySet filtrato |
| `DELETE /api/delegations/sub-deleghe/<id>/` | DELETE | Verifica delegato/creator | Ownership check |
| `GET /api/delegations/designazioni/` | GET | Filtra RDL/SubDelegato/Delegato | Ruolo-based |
| `GET /api/delegations/designazioni/sezioni_disponibili/` | GET | `get_sezioni_filter_for_user()` | Territorio sub-delega |
| `POST /api/delegations/designazioni/carica_mappatura/` | POST | `get_sezioni_filter_for_user()` + matching sub-delega | Complesso e corretto |
| `POST /api/delegations/designazioni/<id>/conferma/` | POST | Delegato catena + comune check | Ownership + territorio |
| `GET /api/rdl/registrations` | GET | `_has_permission()` DelegatoDiLista/SubDelega | Territorio completo |
| `PUT /api/rdl/registrations/<id>` | PUT | `_has_permission()` comune + municipi | Per-record check |
| `POST /api/rdl/registrations/<id>/approve` | POST | `_has_permission()` comune + municipi | Per-record check |
| `POST /api/rdl/registrations/<id>/reject` | POST | `_has_permission()` comune + municipi | Per-record check |
| `POST /api/rdl/registrations/import` | POST | `_has_permission()` per ogni record | Batch con skip out-of-scope |

---

### ❌ SENZA CONTROLLI TERRITORIO (Criticità Alta)

| Endpoint | Metodo | Problema | Componenti Frontend | Rischio |
|----------|--------|----------|---------------------|---------|
| `GET /api/kpi/dati` | GET | **NESSUN filtro territorio** | Kpi.js, App.js | 🔴 ALTO |
| `GET /api/kpi/sezioni` | GET | **NESSUN filtro territorio** | Kpi.js | 🔴 ALTO |
| `GET /api/elections/` | GET | Nessun filtro | App.js | 🟡 MEDIO |
| `GET /api/elections/active/` | GET | Nessun filtro | App.js, TemplateList.js | 🟡 MEDIO |
| `GET /api/elections/<id>/` | GET | Nessun filtro | App.js | 🟡 MEDIO |
| `GET /api/elections/ballots/<id>/` | GET | Nessun filtro | - | 🟡 MEDIO |
| `PATCH /api/elections/ballots/<id>/` | PATCH | Check Delegato/SubDelegato ma non territorio | SchedaElettorale.js | 🟡 MEDIO |
| `GET /api/election/lists` | GET | Nessun filtro | Kpi.js | 🟡 MEDIO |
| `GET /api/election/candidates` | GET | Nessun filtro | Kpi.js | 🟡 MEDIO |
| `GET /api/territory/regioni/` | GET | **Tutti vedono tutto** | Molti componenti | 🟠 MEDIO-ALTO |
| `GET /api/territory/province/` | GET | **Tutti vedono tutto** | Molti componenti | 🟠 MEDIO-ALTO |
| `GET /api/territory/comuni/` | GET | **Tutti vedono tutto** | Molti componenti | 🟠 MEDIO-ALTO |
| `GET /api/territory/municipi/` | GET | **Tutti vedono tutto** | Molti componenti | 🟠 MEDIO-ALTO |
| `GET /api/territory/sezioni/` | GET | **Tutti vedono tutto** | GestioneSezioniTerritoriali.js | 🔴 ALTO |

**Impatto:**
- Un RDL di Roma può vedere KPI di tutta Italia
- Un SubDelegato può vedere tutte le consultazioni, non solo quelle del suo territorio
- Tutti gli utenti autenticati vedono l'intero territorio italiano (regioni, province, comuni, sezioni)

---

## 3. Analisi per App Django

### 3.1 CORE (Auth) ✅

| View | Auth | Territorio | Status |
|------|------|------------|--------|
| MagicLinkRequestView | AllowAny | N/A | ✅ OK |
| MagicLinkVerifyView | AllowAny | N/A | ✅ OK |
| UserProfileView | IsAuthenticated | N/A | ✅ OK |
| UserRolesView | IsAuthenticated | N/A | ✅ OK |
| PermissionsView | IsAuthenticated | ✅ Catena deleghe | ✅ OK |
| ImpersonateView | IsAuthenticated | is_superuser | ✅ OK |
| SearchUsersView | IsAuthenticated | is_superuser | ✅ OK |

---

### 3.2 DELEGATIONS ✅

| View | Auth | Territorio | Status |
|------|------|------------|--------|
| MiaCatenaView | IsAuthenticated | ✅ Email filtering | ✅ OK |
| SubDelegaViewSet | IsAuthenticated | ✅ QuerySet filtrato | ✅ OK |
| DesignazioneRDLViewSet | IsAuthenticated | ✅ get_sezioni_filter + ownership | ✅ OK |
| BatchGenerazioneDocumentiViewSet | IsAuthenticated | ✅ created_by_email | ✅ OK |
| CampagnaListCreateView | IsAuthenticated | ⚠️ Nessun filtro | ⚠️ DA VERIFICARE |
| CampagnaDetailView | IsAuthenticated | ⚠️ Nessun filtro | ⚠️ DA VERIFICARE |

**Nota**: Campagne potrebbero beneficiare di filtri territoriali se hanno scope regionale/comunale.

---

### 3.3 DATA (Sections & RDL) ✅

| View | Auth | Territorio | Status |
|------|------|------------|--------|
| SectionsStatsView | IsAuthenticated | ✅ get_sezioni_filter | ✅ OK |
| SectionsListView | IsAuthenticated | ✅ get_sezioni_filter | ✅ OK |
| SectionsUpdateView | IsAuthenticated | ✅ get_sezioni_filter | ✅ OK |
| SectionsOwnView | IsAuthenticated | ✅ RDL email | ✅ OK |
| SectionsAssignedView | IsAuthenticated | ✅ get_sezioni_filter | ✅ OK |
| SectionsSaveView | IsAuthenticated | ✅ can_enter_section_data | ✅ OK |
| ScrutinioInfoView | IsAuthenticated | N/A (metadata) | ✅ OK |
| ScrutinioSezioniView | IsAuthenticated | ✅ get_sezioni_filter + RDL | ✅ OK |
| ScrutinioSaveView | IsAuthenticated | ✅ can_enter_section_data | ✅ OK |
| RdlRegistrationListView | IsAuthenticated | ✅ _has_permission | ✅ OK |
| RdlRegistrationEditView | IsAuthenticated | ✅ _has_permission | ✅ OK |
| RdlRegistrationApproveView | IsAuthenticated | ✅ _has_permission | ✅ OK |
| RdlRegistrationImportView | IsAuthenticated | ✅ _has_permission batch | ✅ OK |
| RdlRegistrationRetryView | IsAuthenticated | ✅ _has_permission | ✅ OK |
| MappaturaSezioniView | IsAuthenticated | ✅ get_sezioni_filter | ✅ OK |
| MappaturaRdlView | IsAuthenticated | ✅ Territorio check | ✅ OK |
| MappaturaAssegnaView | IsAuthenticated | ✅ Territorio check | ✅ OK |

---

### 3.4 ELECTIONS ⚠️

| View | Auth | Territorio | Status |
|------|------|------------|--------|
| ConsultazioniListView | IsAuthenticated | ❌ NESSUNO | 🔴 CRITICO |
| ConsultazioneAttivaView | IsAuthenticated | ❌ NESSUNO | 🔴 CRITICO |
| ConsultazioneDetailView | IsAuthenticated | ❌ NESSUNO | 🔴 CRITICO |
| SchedaElettoraleDetailView (GET) | IsAuthenticated | ❌ NESSUNO | 🔴 CRITICO |
| SchedaElettoraleDetailView (PATCH) | IsAuthenticated | ⚠️ Ruolo check, no territorio | 🟡 MEDIO |
| ElectionListsView | IsAuthenticated | ❌ NESSUNO | 🔴 CRITICO |
| ElectionCandidatesView | IsAuthenticated | ❌ NESSUNO | 🔴 CRITICO |

**Problema**: Tutti gli utenti autenticati vedono TUTTE le consultazioni elettorali, anche fuori dal loro territorio.

**Esempio**: Un RDL di Milano vede consultazioni comunali di Palermo.

---

### 3.5 TERRITORY ⚠️

| View | Auth | Territorio | Status |
|------|------|------------|--------|
| RegioneViewSet (GET) | IsAuthenticated | ❌ NESSUNO | 🔴 CRITICO |
| ProvinciaViewSet (GET) | IsAuthenticated | ❌ NESSUNO | 🔴 CRITICO |
| ComuneViewSet (GET) | IsAuthenticated | ❌ NESSUNO | 🔴 CRITICO |
| MunicipioViewSet (GET) | IsAuthenticated | ❌ NESSUNO | 🔴 CRITICO |
| SezioneElettoraleViewSet (GET) | IsAuthenticated | ❌ NESSUNO | 🔴 ALTISSIMO |
| RegioneViewSet (WRITE) | IsAdminUser | Admin only | ✅ OK |
| ProvinciaViewSet (WRITE) | IsAdminUser | Admin only | ✅ OK |
| ComuneViewSet (WRITE) | IsAdminUser | Admin only | ✅ OK |
| MunicipioViewSet (WRITE) | IsAdminUser | Admin only | ✅ OK |
| SezioneElettoraleViewSet (WRITE) | IsAdminUser | Admin only | ✅ OK |

**Problema**: Qualsiasi utente autenticato può listare TUTTE le regioni, province, comuni, municipi, sezioni dell'Italia.

**Impatto**:
- Enumeration attack facile
- Leak informazioni su struttura territorio completo
- Un RDL può vedere sezioni di altri territori

---

### 3.6 KPI ❌

| View | Auth | Territorio | Status |
|------|------|------------|--------|
| KPIDatiView | IsAuthenticated | ❌ NESSUNO | 🔴 ALTISSIMO |
| KPISezioniView | IsAuthenticated | ❌ NESSUNO | 🔴 ALTISSIMO |

**Problema CRITICO**:
- KPI mostrano dati aggregati di TUTTA ITALIA
- Un RDL/SubDelegato vede performance di territori non suoi
- Possibile leak di dati sensibili su affluenza/scrutinio

**Esempio**: SubDelegato di Roma vede affluenza di Milano, Palermo, ecc.

---

### 3.7 RESOURCES ⚠️

| View | Auth | Territorio | Status |
|------|------|------------|--------|
| RisorseView (GET) | AllowAny | N/A | ⚠️ MEDIO |
| DocumentoViewSet (GET) | AllowAny | N/A | ⚠️ MEDIO |
| FAQViewSet (GET) | AllowAny | N/A | ⚠️ MEDIO |
| PDFProxyView | AllowAny | Whitelist domains | ⚠️ ALTO |

**Problema**:
- `is_pubblico` flag determina visibilità
- Se mal configurato, documenti interni potrebbero essere pubblici
- PDFProxyView potenziale vettore SSRF

---

### 3.8 DOCUMENTS ⚠️

| View | Auth | Territorio | Status |
|------|------|------------|--------|
| TemplateTypeViewSet | IsAuthenticated | N/A | ✅ OK |
| TemplateViewSet (GET) | IsAuthenticated | N/A | ✅ OK |
| TemplateViewSet (WRITE) | IsAdminUser | Admin only | ✅ OK |
| GeneratedDocumentViewSet | IsAuthenticated | ✅ User owns OR staff | ✅ OK |
| ConfirmPDFView | AllowAny | Token-based | ✅ OK |
| ServeMediaView | AllowAny | Path validation | ⚠️ ALTO |

**Nota**: ServeMediaView ha path traversal prevention, ma da testare con penetration testing.

---

### 3.9 INCIDENTS ✅

| View | Auth | Territorio | Status |
|------|------|------------|--------|
| IncidentReportViewSet | IsAuthenticated | ✅ User/assigned filtering | ✅ OK |
| IncidentCommentViewSet | IsAuthenticated | ✅ is_internal check | ✅ OK |
| IncidentAttachmentViewSet | IsAuthenticated | ✅ Ownership | ✅ OK |

---

### 3.10 AI_ASSISTANT ✅

| View | Auth | Territorio | Status |
|------|------|------------|--------|
| ChatView | IsAuthenticated | Feature flag | ✅ OK |
| ChatSessionsView | IsAuthenticated | ✅ User filtering | ✅ OK |
| KnowledgeSourcesView | IsAuthenticated | is_staff | ✅ OK |

---

## 4. Raccomandazioni per Fixing

### 🔴 PRIORITÀ ALTA (Da fixare immediatamente)

#### 4.1 KPI Endpoints - Implementare filtro territorio

**File**: `backend_django/kpi/views.py`

```python
# PRIMA (vulnerabile)
class KPIDatiView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Ritorna dati globali
        ...

# DOPO (sicuro)
class KPIDatiView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        consultazione_id = request.GET.get('consultazione_id')

        # Solo superuser vede tutto
        if request.user.is_superuser:
            sezioni_filter = Q()
        else:
            # Applica filtro territorio
            from delegations.permissions import get_sezioni_filter_for_user, has_kpi_permission

            if not has_kpi_permission(request.user, consultazione_id):
                return Response({'error': 'Non autorizzato'}, status=403)

            sezioni_filter = get_sezioni_filter_for_user(request.user, consultazione_id)
            if sezioni_filter is None:
                return Response({'error': 'Nessun territorio di competenza'}, status=403)

        # Calcola KPI solo per sezioni visibili
        sezioni = SezioneElettorale.objects.filter(sezioni_filter)
        ...
```

#### 4.2 Territory Endpoints - Filtrare per territorio utente

**File**: `backend_django/territory/views.py`

**Opzione 1: Filtrare QuerySet**
```python
class SezioneElettoraleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminForWriteOperations]

    def get_queryset(self):
        # Admin vede tutto
        if self.request.user.is_superuser:
            return SezioneElettorale.objects.all()

        # Altri vedono solo il loro territorio
        from delegations.permissions import get_sezioni_filter_for_user

        consultazione_id = self.request.GET.get('consultazione_id')
        sezioni_filter = get_sezioni_filter_for_user(self.request.user, consultazione_id)

        if sezioni_filter is None:
            return SezioneElettorale.objects.none()

        return SezioneElettorale.objects.filter(sezioni_filter)
```

**Opzione 2: Limitare visualizzazione solo per necessità** (meno restrittivo)
```python
# Se necessario per funzionalità (es. selezione comuni in form)
# mantenere lettura aperta ma:
# 1. Rimuovere dati sensibili (es. contatti, note interne)
# 2. Rate limiting
# 3. Logging accessi
```

#### 4.3 Elections Endpoints - Filtrare per territorio

**File**: `backend_django/elections/views.py`

```python
class ConsultazioniListView(ListAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Admin vede tutto
        if self.request.user.is_superuser:
            return ConsultazioneElettorale.objects.all()

        # Altri vedono solo consultazioni del loro territorio
        from delegations.permissions import get_user_delegation_roles

        roles = get_user_delegation_roles(self.request.user)

        # Filtra consultazioni per regioni/province/comuni di competenza
        if roles['is_delegato']:
            # Logica per vedere consultazioni nel territorio del delegato
            ...
        elif roles['is_sub_delegato']:
            # Logica per vedere consultazioni nel territorio del sub-delegato
            ...
        else:
            # RDL: nessuna visibilità lista consultazioni
            return ConsultazioneElettorale.objects.none()
```

---

### 🟡 PRIORITÀ MEDIA

#### 4.4 Resources - Audit is_pubblico flag

**Azione**:
1. Audit di tutti i documenti con `is_pubblico=True`
2. Verificare che nessun documento sensibile sia pubblico
3. Implementare logging accessi a documenti pubblici

#### 4.5 PDFProxyView - Hardening

**File**: `backend_django/resources/views.py`

```python
class PDFProxyView(APIView):
    permission_classes = [AllowAny]

    WHITELIST = [
        'interno.gov.it',
        'prefettura.interno.gov.it',
        # ...
    ]

    def get(self, request):
        url = request.GET.get('url')

        # Validazione URL più stretta
        parsed = urllib.parse.urlparse(url)

        # 1. Solo HTTPS
        if parsed.scheme != 'https':
            return Response({'error': 'Solo HTTPS permesso'}, status=400)

        # 2. Whitelist strict
        if not any(parsed.netloc.endswith(domain) for domain in self.WHITELIST):
            return Response({'error': 'Dominio non autorizzato'}, status=403)

        # 3. No redirect follow (anti-SSRF)
        response = requests.get(url, allow_redirects=False, timeout=10)
        ...
```

#### 4.6 ServeMediaView - Path Traversal Testing

**Azione**:
1. Penetration testing con payloads:
   - `../../../etc/passwd`
   - `%2e%2e%2f%2e%2e%2f`
   - URL encoding variants
2. Verificare path sanitization

---

### 🟢 PRIORITÀ BASSA

#### 4.7 Campagne - Valutare filtro territorio

**Azione**: Valutare se campagne devono essere filtrate per territorio o sono globali per design.

#### 4.8 Rate Limiting

**Azione**: Implementare rate limiting su:
- `/api/auth/magic-link/request/` (anti-spam)
- `/api/risorse/pdf-proxy/` (anti-SSRF abuse)
- `/api/territory/*` (anti-enumeration)

#### 4.9 Audit Logging

**Azione**: Implementare audit log per:
- Accessi a dati fuori territorio (se mantenuti pubblici)
- Impersonation
- Modifiche bulk (import CSV)
- Generazione documenti PDF

---

## 5. Matrice Rischio per Endpoint

| Endpoint | Rischio | Motivo | Fix Priority |
|----------|---------|--------|--------------|
| `/api/kpi/*` | 🔴 ALTISSIMO | Leak dati scrutinio/affluenza globali | 1 |
| `/api/territory/sezioni/` | 🔴 ALTISSIMO | Enumeration sezioni Italia | 1 |
| `/api/territory/*` | 🔴 ALTO | Enumeration territorio completo | 1 |
| `/api/elections/*` | 🔴 ALTO | Visibilità consultazioni fuori territorio | 1 |
| `/api/documents/media/` | 🟠 MEDIO-ALTO | Potenziale path traversal | 2 |
| `/api/risorse/pdf-proxy/` | 🟠 MEDIO-ALTO | Potenziale SSRF | 2 |
| `/api/risorse/*` | 🟡 MEDIO | is_pubblico flag da auditare | 3 |
| Altri endpoint | 🟢 BASSO | Controlli territorio presenti | - |

---

## 6. Checklist Implementazione Fix

### Phase 1: Immediate (Settimana 1)
- [ ] KPI: Implementare `get_sezioni_filter_for_user()`
- [ ] Territory: Filtrare GET per territorio utente
- [ ] Elections: Filtrare consultazioni per territorio

### Phase 2: Short-term (Settimana 2-3)
- [ ] PDFProxyView: Hardening SSRF prevention
- [ ] ServeMediaView: Penetration testing
- [ ] Resources: Audit `is_pubblico` flag
- [ ] Rate limiting su endpoint critici

### Phase 3: Medium-term (Mese 1)
- [ ] Audit logging implementazione
- [ ] Campagne: Valutare filtro territorio
- [ ] Security headers (CSP, HSTS, etc.)
- [ ] CORS policy review

### Phase 4: Long-term (Mese 2-3)
- [ ] Penetration testing completo
- [ ] Security review periodica
- [ ] Vulnerability scanning automatico
- [ ] Bug bounty program (se applicabile)

---

## 7. Testing dei Fix

### Test Cases da Implementare

```python
# Test: RDL non vede KPI fuori territorio
def test_rdl_cannot_see_global_kpi(self):
    rdl_user = User.objects.create(email='rdl@test.it')
    # Assegna RDL a sezione Roma
    ...

    response = self.client.get('/api/kpi/dati')
    data = response.json()

    # Verifica che KPI contengano solo dati Roma
    assert all(s.comune.nome == 'Roma' for s in data['sezioni'])

# Test: SubDelegato non vede sezioni fuori territorio
def test_subdelegate_cannot_list_all_sections(self):
    sd_user = User.objects.create(email='sd@test.it')
    # Assegna SubDelega su Milano
    ...

    response = self.client.get('/api/territory/sezioni/')
    data = response.json()

    # Verifica che sezioni siano solo Milano
    assert all(s['comune']['nome'] == 'Milano' for s in data['results'])

# Test: RDL non vede consultazioni fuori territorio
def test_rdl_cannot_see_all_elections(self):
    rdl_user = User.objects.create(email='rdl@test.it')
    # RDL non dovrebbe vedere lista consultazioni

    response = self.client.get('/api/elections/')
    assert response.status_code == 403
```

---

## Conclusioni

### Stato Attuale
Il sistema ha **buoni controlli su operazioni di scrittura** e alcune letture critiche (sezioni assegnate, scrutinio), ma **manca di filtri territoriali su molte operazioni di lettura** (KPI, territory, elections).

### Rischio Complessivo
🔴 **ALTO** - Un utente con ruolo limitato (RDL, SubDelegato) può accedere a dati sensibili fuori dal suo territorio.

### Next Steps
1. **Immediate**: Fix KPI, Territory, Elections endpoints (Priorità 1)
2. **Short-term**: Hardening SSRF/Path Traversal (Priorità 2)
3. **Medium-term**: Audit logging e rate limiting (Priorità 3)
4. **Long-term**: Security continuous monitoring

---

**Fine Report**
