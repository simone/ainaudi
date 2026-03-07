"""
Tool definitions for AI Assistant function calling.

Two functions:
- create_incident_report: Creates a new incident report
- update_incident_report: Updates an existing incident report in the current session
"""
from vertexai.generative_models import Tool, FunctionDeclaration


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

incident_management_tool = Tool(
    function_declarations=[
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
)

# Tools list for views.py
incident_management_tools = [incident_management_tool]
