"""
Tool definitions for AI Assistant function calling.

Tools:
- incident_management_tool: Create/update incident reports
- scrutinio_data_tool: Read/save scrutinio section data
"""
from vertexai.generative_models import Tool, FunctionDeclaration


# =============================================================================
# INCIDENT MANAGEMENT TOOLS
# =============================================================================

_incident_fields = {
    "title": {
        "type": "string",
        "description": "Titolo breve della segnalazione (max 200 caratteri)"
    },
    "description": {
        "type": "string",
        "description": "Descrizione dettagliata dell'incidente, raccolta dalla conversazione"
    },
    "category": {
        "type": "string",
        "enum": ["PROCEDURAL", "ACCESS", "MATERIALS", "INTIMIDATION", "IRREGULARITY", "TECHNICAL", "OTHER"],
        "description": "Categoria: PROCEDURAL (procedure), ACCESS (accesso seggio), MATERIALS (materiali), INTIMIDATION (intimidazioni), IRREGULARITY (irregolarita), TECHNICAL (tecnico piattaforma), OTHER (altro)"
    },
    "severity": {
        "type": "string",
        "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        "description": "Gravita: LOW (bassa), MEDIUM (media), HIGH (alta), CRITICAL (critica)"
    },
    "sezione_numero": {
        "type": "string",
        "description": "Numero della sezione elettorale (es. '42', '12345'). Vuoto se problema generico non legato a sezione."
    },
    "is_verbalizzato": {
        "type": "boolean",
        "description": "Se l'utente ha gia verbalizzato l'incidente nel registro di sezione"
    }
}

_incident_declarations = [
    FunctionDeclaration(
        name="create_incident_report",
        description=(
            "Crea una NUOVA segnalazione di incidente nel database. "
            "CHIAMA QUESTA FUNZIONE quando l'utente ha confermato di voler aprire la segnalazione "
            "(es. 'si', 'ok', 'confermo', 'apri', 'vai'). "
            "Passa TUTTI i dati raccolti dalla conversazione."
        ),
        parameters={
            "type": "object",
            "properties": _incident_fields,
            "required": ["title", "description", "category", "severity"]
        }
    ),
    FunctionDeclaration(
        name="update_incident_report",
        description=(
            "Aggiorna una segnalazione GIA ESISTENTE in questa sessione. "
            "Usa questa funzione quando l'utente chiede di MODIFICARE, AGGIORNARE o CORREGGERE "
            "una segnalazione gia creata (es. 'aggiorna la segnalazione', 'modifica la descrizione', "
            "'cambia la gravita'). Passa SOLO i campi da aggiornare."
        ),
        parameters={
            "type": "object",
            "properties": _incident_fields,
            "required": []
        }
    ),
]


# =============================================================================
# SCRUTINIO DATA TOOLS
# =============================================================================

_scrutinio_save_fields = {
    "sezione_numero": {
        "type": "string",
        "description": "Numero della sezione elettorale (es. '42')"
    },
    # DatiSezione (turnout - common to all ballots)
    "elettori_maschi": {
        "type": "number",
        "description": "Numero elettori iscritti maschi"
    },
    "elettori_femmine": {
        "type": "number",
        "description": "Numero elettori iscritti femmine"
    },
    "votanti_maschi": {
        "type": "number",
        "description": "Numero votanti maschi"
    },
    "votanti_femmine": {
        "type": "number",
        "description": "Numero votanti femmine"
    },
    # DatiScheda (ballot-specific)
    "scheda_nome": {
        "type": "string",
        "description": (
            "Nome della scheda da aggiornare (es. 'Referendum abrogativo n.1', 'Referendum 3'). "
            "OBBLIGATORIO se si aggiornano dati di una scheda. "
            "Se l'utente non specifica e c'e una sola scheda, usala."
        )
    },
    "schede_ricevute": {
        "type": "number",
        "description": "Numero schede ricevute dal seggio"
    },
    "schede_autenticate": {
        "type": "number",
        "description": "Numero schede firmate/timbrate/autenticate dal presidente"
    },
    "schede_bianche": {
        "type": "number",
        "description": "Numero schede bianche"
    },
    "schede_nulle": {
        "type": "number",
        "description": "Numero schede nulle"
    },
    "schede_contestate": {
        "type": "number",
        "description": "Numero schede contestate"
    },
    "voti_si": {
        "type": "number",
        "description": "Voti SI (solo per schede referendum)"
    },
    "voti_no": {
        "type": "number",
        "description": "Voti NO (solo per schede referendum)"
    },
    "osservazioni": {
        "type": "string",
        "description": (
            "Testo delle osservazioni e contestazioni dal verbale di scrutinio. "
            "Se presenti, verranno automaticamente inserite come segnalazione. "
            "Trascrivi il testo esattamente come scritto nel modulo."
        )
    },
}

_scrutinio_declarations = [
    FunctionDeclaration(
        name="get_scrutinio_status",
        description=(
            "Recupera lo stato attuale dei dati di scrutinio per una sezione. "
            "Usa questa funzione quando l'utente chiede di vedere i dati inseriti, "
            "oppure quando un DELEGATO vuole ispezionare una sezione specifica. "
            "Per gli RDL i dati sono gia nel contesto, quindi usa questa funzione "
            "solo se i dati non sono presenti."
        ),
        parameters={
            "type": "object",
            "properties": {
                "sezione_numero": {
                    "type": "string",
                    "description": "Numero della sezione elettorale"
                }
            },
            "required": ["sezione_numero"]
        }
    ),
    FunctionDeclaration(
        name="save_scrutinio_data",
        description=(
            "Salva dati di scrutinio per una sezione. "
            "CHIAMA SOLO dopo che l'utente ha CONFERMATO esplicitamente (es. 'si', 'ok', 'confermo', 'salva'). "
            "Passa SOLO i campi forniti dall'utente. "
            "I campi seggio (elettori, votanti) sono comuni a tutte le schede. "
            "I campi scheda (schede_ricevute, voti, ecc.) richiedono scheda_nome per identificare quale scheda. "
            "Per aggiornare piu schede, chiama questa funzione piu volte."
        ),
        parameters={
            "type": "object",
            "properties": _scrutinio_save_fields,
            "required": ["sezione_numero"]
        }
    ),
]


# =============================================================================
# SINGLE COMBINED TOOL (Gemini requires all declarations in one Tool object)
# =============================================================================

all_ai_tools = [Tool(
    function_declarations=_incident_declarations + _scrutinio_declarations
)]
