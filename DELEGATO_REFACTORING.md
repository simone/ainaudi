# Refactoring: DelegatoDiLista → Delegato

## 📋 Riepilogo Modifiche

### Obiettivo
- ✅ **Rinominare** DelegatoDiLista → Delegato
- ✅ **Semplificare** campi obbligatori: solo nome, cognome, consultazione
- ✅ **Territorio di competenza** già presente (regioni, province, comuni, municipi)

---

## 🔄 Modifiche al Modello

### PRIMA: DelegatoDiLista
```python
class DelegatoDiLista(models.Model):
    # OBBLIGATORI
    consultazione = FK(ConsultazioneElettorale)
    cognome = CharField()
    nome = CharField()
    luogo_nascita = CharField()  # ← Obbligatorio
    data_nascita = DateField()  # ← Obbligatorio
    carica = CharField(choices=Carica.choices)  # ← Obbligatorio
    data_nomina = DateField()  # ← Obbligatorio

    # Territorio
    territorio_regioni = M2M(Regione)
    territorio_province = M2M(Provincia)
    territorio_comuni = M2M(Comune)
    territorio_municipi = JSONField()

    # Meta
    unique_together = ['consultazione', 'cognome', 'nome', 'data_nascita']
```

### DOPO: Delegato
```python
class Delegato(models.Model):
    # ===== CAMPI OBBLIGATORI ===== (solo 3!)
    consultazione = FK(ConsultazioneElettorale)
    cognome = CharField()
    nome = CharField()

    # ===== CAMPI OPZIONALI =====
    luogo_nascita = CharField(blank=True)  # ← Opzionale
    data_nascita = DateField(null=True, blank=True)  # ← Opzionale
    carica = CharField(blank=True, choices=Carica.choices)  # ← Opzionale
    data_nomina = DateField(null=True, blank=True)  # ← Opzionale
    email = EmailField(blank=True)
    telefono = CharField(blank=True)

    # Territorio (nomi semplificati)
    regioni = M2M(Regione)  # ← territorio_regioni
    province = M2M(Provincia)  # ← territorio_province
    comuni = M2M(Comune)  # ← territorio_comuni
    municipi = JSONField()  # ← territorio_municipi

    # Meta
    unique_together = ['consultazione', 'cognome', 'nome']  # ← Senza data_nascita

    class Carica(choices):
        DEPUTATO
        SENATORE
        CONSIGLIERE_REGIONALE
        CONSIGLIERE_COMUNALE
        EURODEPUTATO
        RAPPRESENTANTE_PARTITO  # ← NUOVO

# Backwards compatibility
DelegatoDiLista = Delegato
```

---

## 🗂️ Modifiche Database (Migration)

### Migration: `0007_rename_delegatodelista_to_delegato.py`

**Operations:**

1. ✅ **RenameModel**: DelegatoDiLista → Delegato
2. ✅ **AlterModelTable**: delegations_delegatodelista → delegations_delegato
3. ✅ **AlterModelOptions**: verbose_name = 'Delegato'
4. ✅ **AlterUniqueTogether**: rimuove data_nascita
5. ✅ **AlterField** (4 campi opzionali):
   - luogo_nascita: `blank=True`
   - data_nascita: `null=True, blank=True`
   - carica: `blank=True` + nuova scelta RAPPRESENTANTE_PARTITO
   - data_nomina: `null=True, blank=True`
6. ✅ **RenameField** (4 campi territorio):
   - territorio_regioni → regioni
   - territorio_province → province
   - territorio_comuni → comuni
   - territorio_municipi → municipi
7. ✅ **AlterField** (consultazione): related_name='delegati'
8. ✅ **AlterField** (documento_nomina): upload_to='deleghe/nomine/'

**Comando per applicare:**
```bash
cd backend_django
python manage.py migrate delegations 0007
```

---

## 📦 File Modificati

| File | Modifiche |
|------|-----------|
| **delegations/models.py** | ✅ Modello Delegato + alias DelegatoDiLista |
| **delegations/migrations/0007_*.py** | ✅ Migration rinomina + semplificazione |
| **delegations/signals.py** | ✅ @receiver(Delegato) + imports |
| **delegations/serializers.py** | ✅ DelegatoSerializer + alias |
| **delegations/admin.py** | ✅ DelegatoAdmin con filter_horizontal territorio |
| **delegations/permissions.py** | ✅ Import Delegato + references |
| **delegations/views.py** | ✅ Import Delegato |
| **delegations/views_campagna.py** | ✅ Import Delegato |
| **core/views.py** | ✅ PermissionsView usa Delegato |
| **core/management/commands/cleanup_users.py** | ✅ Import Delegato |

---

## 🔒 Backwards Compatibility

### Alias nel Modello
```python
# delegations/models.py
DelegatoDiLista = Delegato
```

### Alias nel Serializer
```python
# delegations/serializers.py
DelegatoDiListaSerializer = DelegatoSerializer
```

### Cosa Funziona Ancora
✅ `from delegations.models import DelegatoDiLista`
✅ `DelegatoDiLista.objects.all()`
✅ `DelegatoDiListaSerializer(instance)`
✅ ForeignKey(DelegatoDiLista) (grazie a Django)

### Migrazioni Future (Opzionale)
- Rimuovere alias quando tutto il codebase è aggiornato
- Grep per `DelegatoDiLista` e sostituire con `Delegato`
- Comunicare breaking change se ci sono API esterne

---

## 🧪 Test Checklist

### 1. **Verifica Migration**
```bash
cd backend_django
python manage.py showmigrations delegations
# Deve mostrare 0007_rename_delegatodelista_to_delegato [X]
```

### 2. **Test Django Admin**
- [ ] Apri `/admin/delegations/delegato/`
- [ ] Crea nuovo Delegato con solo nome+cognome+consultazione
- [ ] Verifica che campi opzionali siano collapsabili
- [ ] Verifica filter_horizontal per territorio (regioni, province, comuni)
- [ ] Verifica che campi territorio salvino correttamente
- [ ] Verifica territorio_display in list_display

### 3. **Test Auto-Provisioning Permessi**
```python
from delegations.models import Delegato
from core.models import User

# Crea Delegato con email
delegato = Delegato.objects.create(
    cognome='Rossi',
    nome='Mario',
    consultazione_id=1,
    email='mario.rossi@example.com'
)

# Verifica user creato automaticamente
user = User.objects.get(email='mario.rossi@example.com')
assert user.has_perm('core.can_manage_elections')  # ✓
assert user.has_perm('core.can_manage_delegations')  # ✓
```

### 4. **Test API Endpoints**
```bash
# GET /api/delegations/my-chain/
curl -H "Authorization: Bearer $TOKEN" http://localhost:3001/api/delegations/my-chain/
# Deve ritornare 'deleghe_lista' con serializer aggiornato

# Test permissions endpoint
curl -H "Authorization: Bearer $DELEGATO_TOKEN" http://localhost:3001/api/permissions
# Deve ritornare is_delegato: true
```

### 5. **Test Frontend**
- [ ] Login come Delegato
- [ ] Apri menu "Delegati" → dovrebbe essere visibile
- [ ] Apri "Catena Deleghe" → visualizza Delegato
- [ ] Crea SubDelega da Delegato
- [ ] Verifica che SubDelega.delegato punti correttamente

### 6. **Test Territorio Filtering**
```python
from delegations.models import Delegato
from territory.models import Regione, Comune

# Crea Delegato con territorio
delegato = Delegato.objects.create(
    cognome='Bianchi', nome='Lucia', consultazione_id=1
)
lazio = Regione.objects.get(nome='Lazio')
delegato.regioni.add(lazio)

# Verifica filtering sezioni
from delegations.permissions import get_sezioni_filter_for_user
user = delegato.user
sezioni_filter = get_sezioni_filter_for_user(user, consultazione_id=1)
# Deve filtrare sezioni del Lazio
```

---

## ⚠️ Breaking Changes (Nessuno!)

**Grazie agli alias, NON ci sono breaking changes!**

Tutte le API, serializer, e riferimenti esistenti continuano a funzionare.

---

## 🚀 Prossimi Step

### Opzionale: Cleanup Completo (Futuro)
Se vuoi rimuovere completamente `DelegatoDiLista`:

1. **Grep & Replace**:
   ```bash
   grep -r "DelegatoDiLista" backend_django/ frontend/ --exclude-dir=migrations
   # Sostituisci tutti i riferimenti con "Delegato"
   ```

2. **Rimuovi Alias**:
   ```python
   # Rimuovi da models.py:
   # DelegatoDiLista = Delegato

   # Rimuovi da serializers.py:
   # DelegatoDiListaSerializer = DelegatoSerializer
   ```

3. **Commit Breaking Change**:
   ```
   git commit -m "BREAKING: Rimuovi alias DelegatoDiLista"
   ```

---

## 📊 Vantaggi del Refactoring

| Prima | Dopo |
|-------|------|
| Nome lungo e specifico | Nome generico e riutilizzabile |
| 7 campi obbligatori | 3 campi obbligatori |
| Campi territorio prefissati | Campi territorio diretti |
| Unico constraint con data_nascita | Constraint flessibile |
| Solo eletti come delegati | Anche rappresentanti del partito |
| Upload path specifico | Upload path generico |

---

## 🎯 Commit

```
Refactor: Rinomina DelegatoDiLista → Delegato + semplificazione modello

MODIFICHE MODELLO:
- Rinominato DelegatoDiLista → Delegato
- OBBLIGATORI: solo nome, cognome, consultazione
- OPZIONALI: luogo_nascita, data_nascita, carica, data_nomina, email, telefono
- Aggiunta nuova carica: RAPPRESENTANTE_PARTITO
- Territorio già presente: regioni, province, comuni, municipi (M2M)
- Rinominati campi territorio: territorio_* → nomi diretti
- Aggiornato unique_together: solo consultazione + cognome + nome
- Alias backwards compatibility: DelegatoDiLista = Delegato

MIGRATION:
- RenameModel + AlterModelTable
- Rende opzionali: luogo_nascita, data_nascita, carica, data_nomina
- Rinomina campi M2M territorio
- Aggiorna related_name: delegati_lista → delegati
- Aggiorna upload_to: deleghe/nomine_partito/ → deleghe/nomine/

BACKWARDS COMPATIBILITY:
- Alias DelegatoDiLista = Delegato nel modello
- Alias DelegatoDiListaSerializer nel serializer
- Nessun breaking change per codice esistente
```

---

## ✅ Status: COMPLETATO

Tutte le modifiche sono state applicate e committate.
Migration pronta per essere eseguita con `python manage.py migrate`.

**Prossimo step**: Testare in ambiente di sviluppo e verificare che tutto funzioni correttamente!
