"""
Fase 2: Seed/update FAQ entries to improve RAG knowledge base.

Enriches existing terse FAQs and adds new ones for topics
that caused poor chatbot responses in real conversations.

Usage:
    python manage.py seed_faq_fase2
    python manage.py seed_faq_fase2 --dry-run   # Preview without saving
"""
from django.core.management.base import BaseCommand
from resources.models import FAQ


# FAQ updates: enrich existing terse answers
FAQ_UPDATES = [
    {
        'id': 1001,
        'domanda': 'Dove trovo AInaudi? Come si installa?',
        'risposta': (
            "AInaudi è una Progressive Web App (PWA) disponibile su https://ainaudi.it\n"
            "Non si scarica dagli store (App Store / Play Store): si usa dal browser.\n\n"
            "COME INSTALLARE SU iPHONE / iPAD (Safari):\n"
            "1. Apri Safari e vai su https://ainaudi.it\n"
            "2. Tocca l'icona di condivisione (quadrato con freccia verso l'alto) in basso\n"
            "3. Scorri e tocca \"Aggiungi alla schermata Home\"\n"
            "4. Conferma toccando \"Aggiungi\" in alto a destra\n"
            "5. L'icona AInaudi apparirà nella Home come una normale app\n"
            "IMPORTANTE: Su iPhone bisogna usare Safari. Chrome/Firefox su iOS non supportano l'installazione PWA.\n\n"
            "COME INSTALLARE SU ANDROID (Chrome):\n"
            "1. Apri Chrome e vai su https://ainaudi.it\n"
            "2. Dovrebbe apparire un banner \"Aggiungi alla schermata Home\" — tocca \"Installa\"\n"
            "3. Se il banner non appare: tocca i tre puntini in alto a destra → \"Installa app\" o \"Aggiungi a schermata Home\"\n"
            "4. L'icona apparirà nella Home\n\n"
            "DA COMPUTER (Chrome/Edge):\n"
            "1. Vai su https://ainaudi.it\n"
            "2. Nella barra degli indirizzi, clicca sull'icona di installazione (monitor con freccia)\n"
            "3. Oppure: menu (tre puntini) → \"Installa AInaudi\"\n\n"
            "Una volta installata, AInaudi si apre a schermo intero come un'app nativa."
        ),
    },
    {
        'id': 1002,
        'domanda': 'Non riesco a "scaricare" AInaudi dallo store, è normale?',
        'risposta': (
            "Sì, è assolutamente normale! AInaudi NON è un'app da App Store o Play Store.\n"
            "È una Progressive Web App (PWA): si apre dal browser andando su https://ainaudi.it\n\n"
            "Per averla come icona nella Home del telefono:\n"
            "- iPhone/iPad: apri con Safari → icona condivisione → \"Aggiungi alla schermata Home\"\n"
            "- Android: apri con Chrome → banner \"Installa\" oppure menu tre puntini → \"Installa app\"\n\n"
            "Non serve cercarla negli store: gli store non c'entrano."
        ),
    },
    {
        'id': 1003,
        'domanda': 'Si può usare sia da telefono che da PC/browser?',
        'risposta': (
            "Sì! AInaudi funziona su qualsiasi dispositivo con un browser moderno:\n"
            "- Smartphone (iPhone, Android)\n"
            "- Tablet (iPad, Android)\n"
            "- Computer (Windows, Mac, Linux)\n\n"
            "Su telefono puoi anche installarla come app sulla Home. "
            "Su computer puoi installarla come app desktop da Chrome/Edge.\n"
            "I dati sono sincronizzati: puoi iniziare dal telefono e continuare dal PC."
        ),
    },
    {
        'id': 1021,
        'domanda': 'Dove vedo a che seggio/scuola sono assegnato?',
        'risposta': (
            "La sezione a cui sei assegnato come RDL è visibile in AInaudi:\n"
            "- Nella schermata Home, sotto il tuo nome, troverai il numero di sezione e l'indirizzo del seggio\n"
            "- Se non vedi ancora nessuna sezione, significa che l'assegnazione non è ancora stata fatta\n\n"
            "L'assegnazione viene fatta dal tuo sub-delegato o delegato nei giorni precedenti il voto. "
            "Riceverai anche una notifica quando la sezione ti verrà assegnata.\n"
            "La sezione sarà inoltre indicata nell'atto di nomina ufficiale."
        ),
    },
    {
        'id': 1095,
        'domanda': 'Permessi e riposi compensativi: come funzionano?',
        'risposta': (
            "I rappresentanti di lista hanno diritto a permessi retribuiti e riposi compensativi "
            "per le giornate dedicate alle operazioni elettorali.\n\n"
            "REGOLE GENERALI:\n"
            "- Per le giornate lavorative coincidenti con operazioni elettorali: permesso retribuito\n"
            "- Per le giornate festive (domenica): riposo compensativo da fruire nei giorni successivi\n"
            "- Il permesso copre l'intera giornata, indipendentemente dalle ore effettive al seggio\n\n"
            "COME OTTENERE L'ATTESTAZIONE:\n"
            "- Il presidente di sezione firma un'attestazione di presenza\n"
            "- Questa attestazione va presentata al datore di lavoro\n"
            "- Il datore di lavoro è obbligato a riconoscere il permesso (art. 119 DPR 361/1957)\n\n"
            "ATTENZIONE: le specifiche (numero giorni di riposo, modalità) possono variare "
            "in base al tuo contratto collettivo. Consulta il tuo ufficio HR per i dettagli."
        ),
    },
]

# New FAQs: topics completely missing from knowledge base
FAQ_NEW = [
    {
        'domanda': "L'RDL è retribuito? C'è un compenso?",
        'risposta': (
            "No, il ruolo di Rappresentante di Lista (RDL) è volontario e NON retribuito.\n"
            "Non è previsto alcun compenso economico.\n\n"
            "Tuttavia, l'RDL ha diritto a:\n"
            "- Permesso retribuito dal lavoro per le giornate elettorali "
            "(il datore di lavoro deve concederlo per legge, art. 119 DPR 361/1957)\n"
            "- Riposo compensativo per le giornate festive trascorse al seggio (es. la domenica)\n"
            "- Attestazione di presenza rilasciata dal presidente di sezione\n\n"
            "In sintesi: non ricevi un pagamento, ma non perdi la retribuzione lavorativa "
            "perché il permesso è obbligatorio e retribuito."
        ),
        'scope': 'TUTTI',
        'in_evidenza': True,
    },
    {
        'domanda': 'Qual è la differenza tra seggio e sezione elettorale?',
        'risposta': (
            "Spesso usati come sinonimi nel linguaggio comune, ma tecnicamente:\n\n"
            "SEZIONE ELETTORALE:\n"
            "- È l'unità amministrativa: un gruppo di elettori assegnati a un numero (es. Sezione 42)\n"
            "- Ogni comune è diviso in sezioni numerate\n"
            "- In AInaudi, quando parliamo di \"sezione\" intendiamo questo\n\n"
            "SEGGIO ELETTORALE:\n"
            "- È il luogo fisico (la scuola, il tavolo) dove si vota\n"
            "- Un seggio corrisponde a una sezione: il seggio della Sezione 42 è il tavolo/aula dove votano gli elettori della Sezione 42\n"
            "- Il \"presidente di seggio\" è il presidente della sezione elettorale\n\n"
            "In pratica: \"Sono assegnato alla sezione 42\" e \"vado al seggio 42\" indicano la stessa cosa.\n\n"
            "ALTRI TERMINI UTILI:\n"
            "- Scheda contestata: scheda il cui voto è oggetto di contestazione da parte di un componente del seggio o di un RDL\n"
            "- Scheda nulla: scheda che non esprime un voto valido (segni di riconoscimento, voto non chiaro, etc.)\n"
            "- Scheda bianca: scheda riconsegnata senza alcun segno\n"
            "- Scrutinio: la fase di conteggio dei voti dopo la chiusura delle urne"
        ),
        'scope': 'TUTTI',
        'in_evidenza': False,
    },
    {
        'domanda': 'Cos\'è AInaudi? Cosa fa questo chatbot?',
        'risposta': (
            "AInaudi è l'assistente digitale del Movimento 5 Stelle per le elezioni.\n\n"
            "COSA PUO' FARE:\n"
            "- Rispondere alle tue domande su procedure elettorali, regole dello scrutinio, "
            "ruolo dell'RDL e funzionamento dell'app\n"
            "- Aiutarti a capire cosa fare prima, durante e dopo il voto\n"
            "- Fornirti informazioni su permessi lavorativi, documenti necessari, orari\n"
            "- Guidarti nell'inserimento dei dati di scrutinio il giorno del voto\n"
            "- Aiutarti a segnalare incidenti o irregolarità al seggio\n\n"
            "COSA NON PUO' FARE:\n"
            "- Non può modificare la tua assegnazione di sezione\n"
            "- Non può contattare il tuo delegato al posto tuo\n"
            "- Non è un sostituto della formazione: leggi sempre il materiale formativo\n\n"
            "Puoi scrivermi in qualsiasi momento, anche settimane prima del voto. "
            "Sono qui per aiutarti!"
        ),
        'scope': 'TUTTI',
        'in_evidenza': True,
    },
]


class Command(BaseCommand):
    help = 'Fase 2: Seed/update FAQ entries to improve RAG knowledge base'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without saving',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        updated = 0
        created = 0

        # Update existing FAQs with richer content
        self.stdout.write('\n--- Updating existing FAQs ---')
        for item in FAQ_UPDATES:
            try:
                faq = FAQ.objects.get(id=item['id'])
                old_q = faq.domanda
                old_a = faq.risposta[:60]
                faq.domanda = item['domanda']
                faq.risposta = item['risposta']
                if not dry_run:
                    faq.save()  # triggers post_save signal → embedding + KnowledgeSource
                updated += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  Updated FAQ {item["id"]}: {old_q[:60]}')
                )
                if dry_run:
                    self.stdout.write(f'    OLD answer: {old_a}...')
                    self.stdout.write(f'    NEW answer: {item["risposta"][:80]}...')
            except FAQ.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'  FAQ {item["id"]} not found, skipping')
                )

        # Create new FAQs
        self.stdout.write('\n--- Creating new FAQs ---')
        for item in FAQ_NEW:
            # Check if similar FAQ already exists
            exists = FAQ.objects.filter(domanda__icontains=item['domanda'][:40]).exists()
            if exists:
                self.stdout.write(
                    self.style.WARNING(f'  Similar FAQ already exists: {item["domanda"][:60]}')
                )
                continue

            faq = FAQ(
                domanda=item['domanda'],
                risposta=item['risposta'],
                scope=item.get('scope', 'TUTTI'),
                in_evidenza=item.get('in_evidenza', False),
                is_attivo=True,
            )
            if not dry_run:
                faq.save()  # triggers post_save signal → embedding + KnowledgeSource
            created += 1
            self.stdout.write(
                self.style.SUCCESS(f'  Created FAQ: {item["domanda"][:60]}')
            )

        # Summary
        prefix = '[DRY RUN] ' if dry_run else ''
        self.stdout.write(
            self.style.SUCCESS(
                f'\n{prefix}Done! Updated: {updated}, Created: {created}'
            )
        )

        if not dry_run:
            from ai_assistant.models import KnowledgeSource
            total = KnowledgeSource.objects.filter(source_type='FAQ').count()
            self.stdout.write(f'Total FAQ KnowledgeSource entries: {total}')
