"""
Tool definitions for AI Assistant function calling.
"""
from vertexai.generative_models import Tool, FunctionDeclaration


# Single tool with both incident management functions
# NOTE: Vertex AI requires all tools to be in a single Tool object when using function calling
incident_management_tool = Tool(
    function_declarations=[
        FunctionDeclaration(
            name="suggest_incident_report",
            description="⚠️ CHIAMAMI ADESSO se hai raccolto TUTTE queste informazioni: "
                        "(1) Sezione identificata (o NULL se generico), "
                        "(2) Descrizione dettagliata del problema (min 20 parole), "
                        "(3) Conferma verbalizzazione ricevuta (se sezione). "
                        "⚠️ NON dire 'preparo il preview' senza chiamarmi - SE dici che prepari il preview, DEVI chiamarmi nello stesso turno! "
                        "Questa funzione genera il preview formattato della segnalazione da mostrare all'utente per conferma.",
            parameters={
                "type": "object",
                "properties": {
                    "ready_to_create": {
                        "type": "boolean",
                        "description": "Conferma che hai tutti i dati necessari (true)"
                    }
                },
                "required": ["ready_to_create"]
            }
        ),
        FunctionDeclaration(
            name="create_incident_report",
            description="Crea effettivamente la segnalazione nel database dopo conferma dell'utente. "
                        "Usa questa funzione SOLO dopo aver chiamato suggest_incident_report "
                        "E dopo aver ricevuto conferma esplicita dall'utente (es. 'sì', 'ok', 'vai', 'conferma').",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]
)


# Tools list for views.py
incident_management_tools = [incident_management_tool]
