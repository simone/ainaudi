"""
Registry dei tipi di template con serializzazione definita nel codice.

Unica fonte di verita' per:
- serialize(): come trasformare processo + designazioni in dict per il PDF generator
- example_schema: dict di esempio visibile nell'autocomplete dell'editor
- variables_doc: markdown con guida all'uso dei JSONPath
"""


def _serialize_delegato(processo):
    """Serializza il delegato (o subdelegato se selezionato).

    processo.dati_delegato e' gia' un dict con cognome, nome, etc.
    compilato dall'utente nello step di configurazione.
    """
    return processo.dati_delegato or {}


def _serialize_designazione(designazione):
    """Serializza una singola designazione con oggetti nested puliti."""
    return {
        'sezione': designazione.sezione.numero,
        'comune': designazione.sezione.comune.nome if designazione.sezione.comune else '',
        'indirizzo': designazione.sezione.indirizzo or '',
        'effettivo': {
            'cognome': designazione.effettivo_cognome or '',
            'nome': designazione.effettivo_nome or '',
            'data_nascita': designazione.effettivo_data_nascita,
            'luogo_nascita': designazione.effettivo_luogo_nascita or '',
            'domicilio': designazione.effettivo_domicilio or '',
        },
        'supplente': {
            'cognome': designazione.supplente_cognome or '',
            'nome': designazione.supplente_nome or '',
            'data_nascita': designazione.supplente_data_nascita,
            'luogo_nascita': designazione.supplente_luogo_nascita or '',
            'domicilio': designazione.supplente_domicilio or '',
        },
    }


def _serialize_designazione_flat(designazione):
    """Serializza una designazione come lista flat: prima effettivo, poi supplente.

    Restituisce 1 o 2 record per sezione, ordinati effettivo poi supplente.
    Se il supplente non esiste (cognome vuoto), viene saltato.
    """
    sezione = designazione.sezione.numero
    comune = designazione.sezione.comune.nome if designazione.sezione.comune else ''
    indirizzo = designazione.sezione.indirizzo or ''

    records = []

    # Effettivo (sempre presente)
    if designazione.effettivo_cognome:
        records.append({
            'sezione': sezione,
            'comune': comune,
            'indirizzo': indirizzo,
            'tipo_rdl': 'EFFETTIVO',
            'cognome': designazione.effettivo_cognome or '',
            'nome': designazione.effettivo_nome or '',
            'data_nascita': designazione.effettivo_data_nascita,
            'luogo_nascita': designazione.effettivo_luogo_nascita or '',
            'domicilio': designazione.effettivo_domicilio or '',
        })

    # Supplente (solo se presente)
    if designazione.supplente_cognome:
        records.append({
            'sezione': sezione,
            'comune': comune,
            'indirizzo': indirizzo,
            'tipo_rdl': 'SUPPLENTE',
            'cognome': designazione.supplente_cognome or '',
            'nome': designazione.supplente_nome or '',
            'data_nascita': designazione.supplente_data_nascita,
            'luogo_nascita': designazione.supplente_luogo_nascita or '',
            'domicilio': designazione.supplente_domicilio or '',
        })

    return records


class DesignationSingleType:
    """Template per designazione singola: una pagina per sezione, NO loop."""

    code = 'DESIGNATION_SINGLE'
    name = 'Designazione RDL Singola'
    description = 'Un documento per sezione elettorale. Dati spalmati al top level.'

    example_schema = {
        'delegato': {
            'cognome': 'Rossi',
            'nome': 'Mario',
            'luogo_nascita': 'Roma',
            'data_nascita': '1980-01-15',
            'carica': 'Deputato',
            'documento': 'CI AB123456',
            'domicilio': 'Via Roma 1, Roma',
        },
        'sezione': 2359,
        'comune': 'Roma',
        'indirizzo': 'VIA VALLOMBROSA, 31',
        'effettivo': {
            'cognome': 'Verdi',
            'nome': 'Luigi',
            'data_nascita': '1990-03-20',
            'luogo_nascita': 'Torino',
            'domicilio': 'Via Milano 5, Milano',
        },
        'supplente': {
            'cognome': 'Gialli',
            'nome': 'Maria',
            'data_nascita': '1988-07-10',
            'luogo_nascita': 'Bologna',
            'domicilio': 'Via Torino 8, Milano',
        },
    }

    variables_doc = """\
## Designazione Singola (DESIGNATION_SINGLE)

Una pagina per sezione. I dati della designazione sono al top level.

### Campi delegato
- `$.delegato.cognome`
- `$.delegato.nome`
- `$.delegato.luogo_nascita`
- `$.delegato.data_nascita`
- `$.delegato.carica`
- `$.delegato.documento`
- `$.delegato.domicilio`

### Campi sezione
- `$.sezione` (numero)
- `$.comune`
- `$.indirizzo`

### Campi effettivo
- `$.effettivo.cognome`
- `$.effettivo.nome`
- `$.effettivo.data_nascita`
- `$.effettivo.luogo_nascita`
- `$.effettivo.domicilio`

### Campi supplente
- `$.supplente.cognome`
- `$.supplente.nome`
- `$.supplente.data_nascita`
- `$.supplente.luogo_nascita`
- `$.supplente.domicilio`

### Concatenazioni
- `$.effettivo.cognome + " " + $.effettivo.nome`
- `$.delegato.cognome + " " + $.delegato.nome`
"""

    @staticmethod
    def serialize(processo, designazione):
        """Piatto: delegato + designazione spalmata al top level."""
        d = _serialize_designazione(designazione)
        return {
            'delegato': _serialize_delegato(processo),
            **d,  # sezione, comune, indirizzo, effettivo, supplente
        }


class DesignationMultiType:
    """Template cumulativo: delegato + array designazioni per loop."""

    code = 'DESIGNATION_MULTI'
    name = 'Designazione RDL Riepilogativa'
    description = 'Documento multi-pagina con loop sulle designazioni.'

    example_schema = {
        'delegato': {
            'cognome': 'Rossi',
            'nome': 'Mario',
            'luogo_nascita': 'Roma',
            'data_nascita': '1980-01-15',
            'carica': 'Deputato',
            'documento': 'CI AB123456',
            'domicilio': 'Via Roma 1, Roma',
        },
        'comune': 'Roma',
        'designazioni': [
            {
                'sezione': 2359,
                'indirizzo': 'VIA VALLOMBROSA, 31',
                'effettivo': {
                    'cognome': 'Verdi',
                    'nome': 'Luigi',
                    'data_nascita': '1990-03-20',
                    'luogo_nascita': 'Torino',
                    'domicilio': 'Via Milano 5, Milano',
                },
                'supplente': {
                    'cognome': 'Gialli',
                    'nome': 'Maria',
                    'data_nascita': '1988-07-10',
                    'luogo_nascita': 'Bologna',
                    'domicilio': 'Via Torino 8, Milano',
                },
            },
            {
                'sezione': 2360,
                'indirizzo': 'VIA CASSIA, 472',
                'effettivo': {
                    'cognome': 'Neri',
                    'nome': 'Paolo',
                    'data_nascita': '1992-11-05',
                    'luogo_nascita': 'Napoli',
                    'domicilio': 'Via Napoli 12, Roma',
                },
                'supplente': {
                    'cognome': 'Blu',
                    'nome': 'Carla',
                    'data_nascita': '1995-02-28',
                    'luogo_nascita': 'Firenze',
                    'domicilio': 'Via Firenze 3, Roma',
                },
            },
        ],
        'designazioni_flat': [
            {
                'sezione': 2359,
                'comune': 'Roma',
                'indirizzo': 'VIA VALLOMBROSA, 31',
                'tipo_rdl': 'EFFETTIVO',
                'cognome': 'Verdi',
                'nome': 'Luigi',
                'data_nascita': '1990-03-20',
                'luogo_nascita': 'Torino',
                'domicilio': 'Via Milano 5, Milano',
            },
            {
                'sezione': 2359,
                'comune': 'Roma',
                'indirizzo': 'VIA VALLOMBROSA, 31',
                'tipo_rdl': 'SUPPLENTE',
                'cognome': 'Gialli',
                'nome': 'Maria',
                'data_nascita': '1988-07-10',
                'luogo_nascita': 'Bologna',
                'domicilio': 'Via Torino 8, Milano',
            },
            {
                'sezione': 2360,
                'comune': 'Roma',
                'indirizzo': 'VIA CASSIA, 472',
                'tipo_rdl': 'EFFETTIVO',
                'cognome': 'Neri',
                'nome': 'Paolo',
                'data_nascita': '1992-11-05',
                'luogo_nascita': 'Napoli',
                'domicilio': 'Via Napoli 12, Roma',
            },
            {
                'sezione': 2360,
                'comune': 'Roma',
                'indirizzo': 'VIA CASSIA, 472',
                'tipo_rdl': 'SUPPLENTE',
                'cognome': 'Blu',
                'nome': 'Carla',
                'data_nascita': '1995-02-28',
                'luogo_nascita': 'Firenze',
                'domicilio': 'Via Firenze 3, Roma',
            },
        ],
    }

    variables_doc = """\
## Designazione Riepilogativa (DESIGNATION_MULTI)

Delegato e comune al top level, designazioni in array per loop.

### Campi delegato (testo, assoluti)
- `$.delegato.cognome`
- `$.delegato.nome`
- `$.delegato.luogo_nascita`
- `$.delegato.data_nascita`
- `$.delegato.carica`
- `$.delegato.documento`
- `$.delegato.domicilio`

### Comune (testo, assoluto)
- `$.comune`

### Loop jsonpath (nested: effettivo/supplente come oggetti)
- `$.designazioni`

### Campi nel loop designazioni (relativi ad ogni item)
- `$.sezione` (numero)
- `$.indirizzo`
- `$.effettivo.cognome`
- `$.effettivo.nome`
- `$.effettivo.data_nascita`
- `$.effettivo.luogo_nascita`
- `$.effettivo.domicilio`
- `$.supplente.cognome`
- `$.supplente.nome`
- `$.supplente.data_nascita`
- `$.supplente.luogo_nascita`
- `$.supplente.domicilio`

### Loop jsonpath alternativo (flat: un record per persona)
- `$.designazioni_flat`

Ordinato per sezione, prima effettivo poi supplente.
Il supplente viene saltato se assente.

### Campi nel loop designazioni_flat (relativi ad ogni item)
- `$.sezione` (numero)
- `$.comune`
- `$.indirizzo`
- `$.tipo_rdl` (EFFETTIVO o SUPPLENTE)
- `$.cognome`
- `$.nome`
- `$.data_nascita`
- `$.luogo_nascita`
- `$.domicilio`
"""

    @staticmethod
    def serialize(processo, designazioni):
        """Delegato + comune al top level + array designazioni per loop.

        Include sia `designazioni` (nested effettivo/supplente) che
        `designazioni_flat` (un record per persona, ordinato per sezione).
        """
        # Il comune e' lo stesso per tutte le designazioni (no cross-comune)
        comune = ''
        if designazioni:
            first = designazioni[0] if hasattr(designazioni, '__getitem__') else designazioni.first()
            if first and first.sezione and first.sezione.comune:
                comune = first.sezione.comune.nome

        # Flat: un record per persona, ordinato per sezione, effettivo prima di supplente
        flat = []
        for d in designazioni:
            flat.extend(_serialize_designazione_flat(d))

        return {
            'delegato': _serialize_delegato(processo),
            'comune': comune,
            'designazioni': [_serialize_designazione(d) for d in designazioni],
            'designazioni_flat': flat,
        }


TEMPLATE_TYPE_REGISTRY = {
    'DESIGNATION_SINGLE': DesignationSingleType,
    'DESIGNATION_MULTI': DesignationMultiType,
}


def get_template_type_class(code):
    """Ritorna la classe template type per codice, o None."""
    return TEMPLATE_TYPE_REGISTRY.get(code)
