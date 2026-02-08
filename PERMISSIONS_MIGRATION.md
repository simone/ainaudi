# Migrazione Sistema Permessi: Da Assegnazione Diretta a Gruppi Django

## Cosa è cambiato

### Prima (sistema vecchio):
- I permessi venivano assegnati **direttamente agli utenti** tramite signals
- Quando un Delegato/SubDelegato/RDL veniva creato, il sistema assegnava automaticamente i permessi al loro user
- Gestione complessa e difficile da manutenere

### Dopo (sistema nuovo):
- I permessi vengono assegnati ai **Gruppi Django**
- Gli utenti vengono aggiunti al gruppo appropriato
- I permessi vengono ereditati dal gruppo
- Gestione centralizzata e semplice

## Gruppi Creati

| Gruppo | Permessi Assegnati |
|--------|-------------------|
| **Delegato** | `can_manage_delegations`, `can_manage_rdl`, `can_view_resources`, `can_generate_documents`, `can_view_kpi` |
| **Subdelegato** | `can_manage_rdl`, `can_view_resources`, `can_view_kpi` |
| **RDL** | `has_scrutinio_access`, `can_view_resources` |
| **Diretta** | `can_view_kpi`, `can_view_resources` |

## Come Applicare le Modifiche

### Step 1: Applica le migration

```bash
cd backend_django
python manage.py migrate
```

Questo creerà i 4 gruppi e assegnerà i permessi appropriati a ciascun gruppo.

### Step 2: Migra gli utenti esistenti (IMPORTANTE!)

```bash
# Prima fai un dry-run per vedere cosa succederà
python manage.py migrate_permissions_to_groups --dry-run

# Se tutto ok, applica la migrazione
python manage.py migrate_permissions_to_groups
```

Questo comando:
1. Trova tutti gli utenti con RoleAssignment attivo
2. Li aggiunge al gruppo appropriato basato sul loro ruolo
3. Rimuove i permessi diretti (ora ereditati dal gruppo)
4. Mostra un report delle modifiche

### Step 3: Verifica nel Django Admin

1. Vai su http://localhost:3001/admin/
2. Controlla la sezione "Authentication and Authorization" → "Groups"
3. Verifica che i 4 gruppi esistano con i permessi corretti
4. Controlla alcuni utenti per verificare che siano nei gruppi giusti

## Modifiche al Codice

### File modificati:

1. **`core/migrations/0008_create_permission_groups.py`** (NEW)
   - Crea i 4 gruppi Django
   - Assegna i permessi ai gruppi

2. **`delegations/signals.py`**
   - `assign_permissions_for_role()` → `assign_group_for_role()`
   - Ora assegna gruppi invece di permessi diretti

3. **`core/management/commands/migrate_permissions_to_groups.py`** (NEW)
   - Management command per migrare utenti esistenti

## Vantaggi del Nuovo Sistema

✅ **Centralizzazione**: I permessi sono definiti una volta nel gruppo, non ripetuti per ogni utente

✅ **Manutenibilità**: Modificare i permessi di un ruolo significa modificare un solo gruppo

✅ **Visibilità**: Nel Django Admin puoi vedere chiaramente quali permessi ha ogni gruppo

✅ **Standard Django**: Usa il sistema nativo di Django invece di logica custom

✅ **Performance**: Query più efficienti (Django ottimizza l'accesso ai permessi di gruppo)

## Comportamento dei Signals (Automatico)

Quando viene creato un nuovo:
- **Delegato** → utente aggiunto al gruppo "Delegato"
- **SubDelega** → utente aggiunto al gruppo "Subdelegato"
- **DesignazioneRDL** → utenti (effettivo/supplente) aggiunti al gruppo "RDL"

I permessi vengono ereditati automaticamente dal gruppo, non serve fare nulla.

## Gestione Manuale Gruppi (Admin)

Se un amministratore vuole dare accesso "Diretta" (KPI viewer) a qualcuno:

1. Vai su Django Admin → Users
2. Seleziona l'utente
3. In "Groups", aggiungi "Diretta"
4. Salva

L'utente avrà automaticamente accesso a KPI e Risorse.

## Troubleshooting

### Gli utenti non hanno più accesso dopo la migrazione

```bash
# Ri-esegui il command di migrazione
python manage.py migrate_permissions_to_groups

# Verifica i gruppi
python manage.py shell
>>> from django.contrib.auth.models import Group
>>> Group.objects.all().values('name', 'permissions__codename')
```

### Un gruppo non ha i permessi corretti

```bash
# Re-run migration
python manage.py migrate core 0007  # rollback
python manage.py migrate core 0008  # re-apply
```

## Note Importanti

⚠️ **NON rimuovere i RoleAssignment**: Il sistema li usa ancora per determinare il ruolo dell'utente nella catena deleghe

⚠️ **Superuser**: I superuser non vengono modificati, hanno accesso completo indipendentemente dai gruppi

⚠️ **Backward compatibility**: Il sistema continua a funzionare anche se non migri subito gli utenti esistenti, ma è consigliato farlo
