"""
Tool definitions for AI Assistant function calling.

Single function: create_incident_report
- The AI gathers info conversationally, shows a summary, asks for confirmation
- When user confirms, AI calls this function with all the data
- The function creates the incident in the database
"""
from vertexai.generative_models import Tool, FunctionDeclaration


incident_management_tool = Tool(
    function_declarations=[
        FunctionDeclaration(
            name="create_incident_report",
            description=(
                "Crea una segnalazione di incidente nel database. "
                "CHIAMA QUESTA FUNZIONE quando l'utente ha confermato di voler aprire la segnalazione "
                "(es. 'si', 'ok', 'confermo', 'apri', 'vai'). "
                "Passa TUTTI i dati raccolti dalla conversazione."
            ),
            parameters={
                "type": "object",
                "properties": {
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
                },
                "required": ["title", "description", "category", "severity"]
            }
        )
    ]
)

# Tools list for views.py
incident_management_tools = [incident_management_tool]
