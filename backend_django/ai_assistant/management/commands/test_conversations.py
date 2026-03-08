"""
Regression test: replay real user conversations against the AI pipeline.

Takes ALL conversations from the March 2026 export, replays the user
messages through the current system, and uses LLM-as-judge to score
both the OLD response and the NEW response on a 1-10 scale.

Usage:
    python manage.py test_conversations                    # Run all
    python manage.py test_conversations --id 64            # One session
    python manage.py test_conversations --from-id 40       # From session 40 onward
    python manage.py test_conversations --verbose          # Show full responses
    python manage.py test_conversations --output report.json  # Save JSON report
"""
import json
import time
import logging
from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ALL conversations from chat_sessions_export.xlsx (March 2026)
# Each entry: session_id, messages (role+content), description of what happened
#
# We skip sessions that had NO AI response (user sent 1 msg, never got answer)
# and deduplicate near-identical sessions from the same user.
# ---------------------------------------------------------------------------

CONVERSATIONS = [
    {
        'id': 1,
        'description': 'User asks if bot is operational and what it can do',
        'messages': [
            {'role': 'user', 'content': 'Buongiorno, primo test per capire se l\'integrazione con l\'agent funziona. Sei operativo? che cosa sai fare?'},
            {'role': 'assistant_old', 'content': '\U0001f937'},
        ],
    },
    {
        'id': 2,
        'description': 'User asks how bot can help, then asks about referendum procedures',
        'messages': [
            {'role': 'user', 'content': 'come mi puoi aiutare?'},
            {'role': 'assistant_old', 'content': 'Sembra pertinente RDL ma incompleta → chiedi dettagli (max 10 parole):\n\n"In relazione a cosa? Elezioni, scrutini o altro?"'},
            {'role': 'user', 'content': 'spiegami al referendum cosa devo fare.'},
            {'role': 'assistant_old', 'content': 'Sembra pertinente, ma incompleta. Chiedi dettagli: "Referendum su cosa? Cosa devi fare al seggio?"'},
        ],
    },
    {
        'id': 11,
        'description': 'User asks about work permit document for RDL, then says "daje" (Roman approval)',
        'messages': [
            {'role': 'user', 'content': 'devo consegnare un documento al mio datore di lavoro per fare l\'RDL al referendum?'},
            {'role': 'assistant_old', 'content': 'Si, devi consegnare un documento al tuo datore di lavoro. Non ho informazioni specifiche su quale documento, ma la tua nomina a RDL e un giustificativo valido per assentarti dal lavoro.'},
            {'role': 'user', 'content': 'daje'},
            {'role': 'assistant_old', 'content': 'Sembra pertinente al contesto RDL ma incompleta. Chiarire: "Daje" in quale contesto elettorale/di scrutinio?'},
        ],
    },
    {
        'id': 12,
        'description': 'User asks how many scrutatori for the referendum',
        'messages': [
            {'role': 'user', 'content': 'quanti scrutatori sono previsti per il prossimo referendum'},
            {'role': 'assistant_old', 'content': 'Non ho informazioni sul numero di scrutatori previsti per il referendum.'},
        ],
    },
    {
        'id': 14,
        'description': 'Long test session: president locked alone with ballots, political rant, voting scenarios',
        'messages': [
            {'role': 'user', 'content': 'come mi puoi aiutare?'},
            {'role': 'assistant_old', 'content': 'Posso aiutarti con: Inserimento dati, Accesso a risorse, Informazioni.'},
            {'role': 'user', 'content': 'il presidente e solo con le schede e si e chiuso dentro. chiamo la polizia?'},
            {'role': 'assistant_old', 'content': 'No, non chiamare subito la polizia.\n1. Il Presidente ha poteri di decisione e di polizia nel seggio.\n2. Chiedi immediatamente che la tua osservazione sia messa a verbale.\n3. Se la situazione persiste e viola le procedure, valuta se segnalarlo alle forze dell\'ordine.'},
            {'role': 'user', 'content': 'ma e da solo... puo fare dei brogli.. chi controlla?'},
            {'role': 'assistant_old', 'content': 'Non so rispondere a questa domanda basandomi sui documenti forniti.'},
            {'role': 'user', 'content': 'e il ritorno della casta'},
            {'role': 'assistant_old', 'content': 'Secondo Conte, la riforma Nordio e un attacco all\'equilibrio costituzionale e al principio che "la legge e uguale per tutti," favorendo politici, colletti bianchi e imprenditori amici.'},
            {'role': 'user', 'content': 'c\'e uno che vuole votare si, che faccio gli impedisco di entrare nel seggio?'},
            {'role': 'assistant_old', 'content': 'No, non devi impedirgli di entrare. Tutti hanno diritto di voto.'},
            {'role': 'user', 'content': 'ma cosi perdiamo!'},
            {'role': 'assistant_old', 'content': 'Concentrati sul tuo ruolo di RDL:\n- Verifica che le operazioni di voto siano regolari.\n- Assicurati che tutti i votanti abbiano diritto di voto.\n- Non esprimere giudizi o commenti personali.'},
        ],
    },
    {
        'id': 15,
        'description': 'RDL asks about schedule for 3 days (Saturday/Sunday/Monday)',
        'messages': [
            {'role': 'user', 'content': 'considerami operativa da sabato (pom/mat?) o da domenica. Grazie cosi avviso azienda'},
            {'role': 'assistant_old', 'content': '\U0001f937'},
        ],
    },
    {
        'id': 16,
        'description': 'User asks what to do as RDL, then about irregularities',
        'messages': [
            {'role': 'user', 'content': 'Spiegami che cosa devo fare sono in RTL'},
            {'role': 'assistant_old', 'content': 'In quanto RDL, devi:\n1. Assistere a tutte le operazioni del seggio.\n2. Garantire la regolarita delle votazioni e dello scrutinio.\n3. Far inserire a verbale le tue dichiarazioni.\n4. Apporre la tua firma su strisce di chiusura, verbali e plichi.'},
            {'role': 'user', 'content': 'Quali potrebbero essere le irregolarita nelle votazioni'},
            {'role': 'assistant_old', 'content': 'Possibili irregolarita durante le votazioni includono:\n- Violazione del silenzio elettorale nel seggio o nel raggio di 200 metri.\n- Presenza di estranei nel seggio.\n- Turbamento del regolare procedimento da parte degli RDL.\n- Impedimento del regolare procedimento delle operazioni.'},
        ],
    },
    {
        'id': 17,
        'description': 'Complex question: friend getting Italian citizenship day before vote, can she vote?',
        'messages': [
            {'role': 'user', 'content': 'Un\'amica di mia figlia vorrebbe votare al Referendum: giuridicamente oggi e cittadina filippina, MA dopo una lunga trafila burocratica, lei - che abita da 16 anni a Roma - finalmente venerdi 20 potra "giurare" e ottenere la sospirata cittadinanza italiana. Come fa per votare il 22-23?'},
            {'role': 'assistant_old', 'content': 'Non so come possa votare, dato che l\'ottenimento della cittadinanza e troppo a ridosso delle elezioni.'},
            {'role': 'user', 'content': 'Con la cittadinanza in mano non puo andare al municipio e farsi dare una scheda?'},
            {'role': 'assistant_old', 'content': 'Non so rispondere a questa domanda.'},
        ],
    },
    {
        'id': 18,
        'description': 'User asks where to find employer form, bot asks for clarification, user says "Si"',
        'messages': [
            {'role': 'user', 'content': 'Dove trovo modulo da consegnare al datore di lavoro'},
            {'role': 'assistant_old', 'content': 'Sembra pertinente al RDL, ma incompleta. Chiedi: "Modulo per cosa? Assenza dal lavoro per votare/scrutinio?"'},
            {'role': 'user', 'content': 'Si'},
            {'role': 'assistant_old', 'content': 'Puoi essere piu specifico? La domanda e troppo breve.'},
        ],
    },
    {
        'id': 19,
        'description': 'User asks how scrutinio works (good answer), then sends gibberish',
        'messages': [
            {'role': 'user', 'content': 'Scrutinio come si fa'},
            {'role': 'assistant_old', 'content': 'Durante lo scrutinio, le tre attivita principali sono:\n1. RISCONTRO del numero di elettori e votanti\n2. ACCERTAMENTO del numero di elettori che hanno votato nella sezione\n3. CONTROLLO schede residue e formazione dei plichi sigillati.'},
        ],
    },
    {
        'id': 20,
        'description': 'User asks about scrutinio, then about RDL powers and presidente di seggio',
        'messages': [
            {'role': 'user', 'content': 'come si fa lo scrutinio'},
            {'role': 'assistant_old', 'content': 'Lo scrutinio si articola in tre fasi principali:\n1. RISCONTRO\n2. ACCERTAMENTO\n3. CONTROLLO'},
            {'role': 'user', 'content': 'Quali sono i poteri principali degli rdl'},
            {'role': 'assistant_old', 'content': 'I poteri principali degli RDL sono: assistere, far inserire a verbale, firmare, far rispettare silenzio, segnalare estranei, votare nella sezione.'},
            {'role': 'user', 'content': 'chi e il presidente di seggio e quali sono i suoi poteri?'},
            {'role': 'assistant_old', 'content': 'Il Presidente di seggio e il responsabile delle operazioni elettorali e ha ampi poteri: sovraintende, ha potere decisionale, dispone di poteri di Polizia.'},
        ],
    },
    {
        'id': 22,
        'description': 'User asks about scrutinio, then where to find assigned sections',
        'messages': [
            {'role': 'user', 'content': 'Come si fa lo scrutinio?'},
            {'role': 'assistant_old', 'content': 'Lo scrutinio si svolge in tre attivita principali: RISCONTRO, ACCERTAMENTO, CONTROLLO.'},
            {'role': 'user', 'content': 'dove trovo le sezioni che mi sono state assegnate?'},
            {'role': 'assistant_old', 'content': 'Contatta il tuo referente di zona del M5S. Lui/lei ha l\'elenco delle sezioni assegnate ai RDL.'},
        ],
    },
    {
        'id': 24,
        'description': 'RDL rights/duties, how long to stay, is it paid, how to install app',
        'messages': [
            {'role': 'user', 'content': 'Diritti e doveri RDL'},
            {'role': 'assistant_old', 'content': 'Diritti: assistere, far verbalizzare, firmare, far rispettare silenzio, votare.\nDoveri: Non toccare schede, mantenere comportamento collaborativo, non turbare il procedimento.'},
            {'role': 'user', 'content': 'Quanto deve rimanere nel seggio'},
            {'role': 'assistant_old', 'content': 'Devi rimanere nel seggio per tutta la durata delle operazioni di voto e scrutinio.'},
            {'role': 'user', 'content': 'Viene pagato?'},
            {'role': 'assistant_old', 'content': 'Non ho informazioni riguardanti compensi economici per l\'attivita di RDL.'},
            {'role': 'user', 'content': 'Installa app ainaudi'},
            {'role': 'assistant_old', 'content': 'Apri il browser sul tuo smartphone, vai su https://ainaudi.appspot.com e segui le istruzioni.'},
        ],
    },
    {
        'id': 25,
        'description': 'User asks how to install app, bot asks "for what electoral activity"',
        'messages': [
            {'role': 'user', 'content': 'come installare l\'app?'},
            {'role': 'assistant_old', 'content': 'Sembra pertinente RDL ma incompleta → chiedi dettagli (max 10 parole)\n\nChiedi: "App per quale attivita legata alle elezioni/scrutinio?"'},
        ],
    },
    {
        'id': 26,
        'description': 'User asks how to see assigned section',
        'messages': [
            {'role': 'user', 'content': 'Come vedo la sezione a cui sono assegnato?'},
            {'role': 'assistant_old', 'content': 'Non so come rispondere a questa domanda. Il contesto fornito non contiene informazioni su come visualizzare la sezione a cui sei assegnato.'},
        ],
    },
    {
        'id': 27,
        'description': 'User asks how scrutinio works (good answer)',
        'messages': [
            {'role': 'user', 'content': 'Come si fa uno scrutinio'},
            {'role': 'assistant_old', 'content': 'Lo scrutinio si articola in tre fasi: RISCONTRO, ACCERTAMENTO, CONTROLLO.'},
        ],
    },
    {
        'id': 28,
        'description': 'User asks to install app, bot says off-topic',
        'messages': [
            {'role': 'user', 'content': 'Come installare app?'},
            {'role': 'assistant_old', 'content': 'La domanda e chiaramente off-topic.\n\nRisposta: \U0001f937'},
            {'role': 'user', 'content': 'Come si installa l\'app di ainaudi?'},
            {'role': 'assistant_old', 'content': 'Per installare AInaudi come app sul tuo telefono:\n1. Apri il browser Chrome.\n2. Vai su https://ainaudi.appspot.com.\n3. Dal menu di Chrome, seleziona "Aggiungi a Home".'},
        ],
    },
    {
        'id': 29,
        'description': 'User asks if bot is active, then what time polls open',
        'messages': [
            {'role': 'user', 'content': 'Sei gia operativa?'},
            {'role': 'assistant_old', 'content': '\U0001f937'},
            {'role': 'user', 'content': 'A che ora aprono i seggi?'},
            {'role': 'assistant_old', 'content': 'I seggi aprono alle ore 7:00 di domenica 22 marzo.'},
        ],
    },
    {
        'id': 30,
        'description': 'User asks to install AInaudi, bot says "I don\'t understand"',
        'messages': [
            {'role': 'user', 'content': 'Come fare per installarla?'},
            {'role': 'assistant_old', 'content': 'Sembra pertinente RDL ma incompleta → chiedi dettagli\n\nChiarimento: Installare cosa?'},
            {'role': 'user', 'content': 'AInaudi'},
            {'role': 'assistant_old', 'content': 'Non capisco la domanda.'},
        ],
    },
    {
        'id': 31,
        'description': 'User asks about RDL nomination process',
        'messages': [
            {'role': 'user', 'content': 'Nomina rappresentante di lista'},
            {'role': 'assistant_old', 'content': 'L\'atto di nomina va depositato all\'atto della costituzione del seggio (sabato 21 marzo alle ore 15:00). Il termine ultimo e il primo voto di domenica 22 marzo alle ore 07:00.'},
        ],
    },
    {
        'id': 32,
        'description': 'User mentions having work permit for RDL',
        'messages': [
            {'role': 'user', 'content': 'Ho permesso da lavoro per rappresentante di lista'},
            {'role': 'assistant_old', 'content': 'Ok. Non ho informazioni specifiche sui permessi lavorativi per RDL.'},
        ],
    },
    {
        'id': 33,
        'description': 'User asks what "schede contestate" means',
        'messages': [
            {'role': 'user', 'content': 'cosa significa contestate'},
            {'role': 'assistant_old', 'content': 'Sembra pertinente RDL ma incompleta → chiedi dettagli: "Contestate in quale ambito?"'},
            {'role': 'user', 'content': 'si cosa significa schede non valide contestate'},
            {'role': 'assistant_old', 'content': 'Non ho informazioni sulle schede non valide contestate.'},
        ],
    },
    {
        'id': 34,
        'description': 'User asks what RDL must do and what if absent Sunday',
        'messages': [
            {'role': 'user', 'content': 'Che deve fare RDL'},
            {'role': 'assistant_old', 'content': 'Ecco i compiti principali dell\'RDL: assistere, verbalizzare, garantire la regolarita, firmare, non toccare schede, badge e voto.'},
            {'role': 'user', 'content': 'Se non sono presente domenica che succede'},
            {'role': 'assistant_old', 'content': 'Se non sei presente domenica, la tua nomina puo essere depositata fino al primo voto (ore 07:00).'},
        ],
    },
    {
        'id': 35,
        'description': 'User asks if can vote without being present as RDL, then about badge',
        'messages': [
            {'role': 'user', 'content': 'Posso esercitare il diritto di voto senza presenziare come Rdl?'},
            {'role': 'assistant_old', 'content': 'Si, puoi votare nella sezione dove sei stato nominato RDL.'},
            {'role': 'user', 'content': 'Per esercitare il diritto di voto devo stampare il badge?'},
            {'role': 'assistant_old', 'content': 'Non so rispondere a questa domanda.'},
        ],
    },
    {
        'id': 36,
        'description': 'President won\'t let RDL in, specific section number',
        'messages': [
            {'role': 'user', 'content': 'il presidente di seggio non mi vuole fare entrare, che faccio chiamo la polizia?'},
            {'role': 'assistant_old', 'content': 'Ecco cosa fare:\n1. Verifica la tua nomina.\n2. Richiedi verbalizzazione.\n3. Contatta i referenti M5S.'},
            {'role': 'user', 'content': 'nella sezione 1234 non c\'e modo di entrare'},
            {'role': 'assistant_old', 'content': '1. Verifica la tua nomina per quella sezione (1234).\n2. Richiedi verbalizzazione.\n3. Contatta i referenti M5S.'},
        ],
    },
    {
        'id': 37,
        'description': 'User asks about Monday absence as RDL, bot says shrug',
        'messages': [
            {'role': 'user', 'content': 'ciao, ma se il lunedi non posso venire a fare rdl?'},
            {'role': 'assistant_old', 'content': '\U0001f937'},
            {'role': 'user', 'content': 'che vuol dire?'},
            {'role': 'assistant_old', 'content': 'Significa che non ho informazioni sufficienti per rispondere alla tua domanda.'},
        ],
    },
    {
        'id': 38,
        'description': 'User can only come Sunday evening, asks about delegation of nomination deposit',
        'messages': [
            {'role': 'user', 'content': 'Posso presentarmi al seggio solo domenica sera, va bene?'},
            {'role': 'assistant_old', 'content': 'No, non va bene. Il termine ultimo per depositare l\'atto di nomina e alle 07:00 di domenica 22 marzo.'},
            {'role': 'user', 'content': 'Io sono via per lavoro. Torno domenica sera.'},
            {'role': 'assistant_old', 'content': 'Domenica sera e troppo tardi. Il termine ultimo e il primo voto di domenica 22 marzo alle 07:00.'},
            {'role': 'user', 'content': 'Non posso. Non ci sono. Posso delegare qualcuno?'},
            {'role': 'assistant_old', 'content': 'Non puoi delegare la tua funzione di RDL.'},
            {'role': 'user', 'content': 'No, non la mia funzione. Il mio atto di nomina'},
            {'role': 'assistant_old', 'content': 'L\'atto di nomina va depositato all\'atto della costituzione del seggio, o al piu tardi entro le ore 07:00 di domenica.'},
        ],
    },
    {
        'id': 39,
        'description': 'User asks how and when to contest a ballot',
        'messages': [
            {'role': 'user', 'content': 'Come e quando contestare una scheda?'},
            {'role': 'assistant_old', 'content': 'Sembra pertinente RDL ma incompleta → chiedi dettagli\n\n"Contestare scheda: durante quale fase (voto, scrutinio)? Per quale motivo?"'},
        ],
    },
    {
        'id': 40,
        'description': 'Off-topic recipe, then "pen or pencil" question',
        'messages': [
            {'role': 'user', 'content': 'Ricetta frittata con carote'},
            {'role': 'assistant_old', 'content': '\U0001f937'},
            {'role': 'user', 'content': 'Penna o matita'},
            {'role': 'assistant_old', 'content': 'Sembra pertinente al contesto elettorale. Chiarisci: Penna o matita per quale operazione elettorale?'},
        ],
    },
    {
        'id': 41,
        'description': 'User asks if can come only Sunday, then about Monday obligation',
        'messages': [
            {'role': 'user', 'content': 'per votare mi basta venire solo domenica? Nonostante sia Rappresentante di lista?'},
            {'role': 'assistant_old', 'content': 'No, per votare come RDL non basta venire solo domenica. Devi depositare l\'atto di nomina entro il primo voto.'},
            {'role': 'user', 'content': 'e poi sono obbligato a venire anche lunedi se sono rdl?'},
            {'role': 'assistant_old', 'content': 'Non ho informazioni specifiche sull\'obbligatorieta della presenza degli RDL anche il lunedi.'},
        ],
    },
    {
        'id': 42,
        'description': 'User asks where to find the delega',
        'messages': [
            {'role': 'user', 'content': 'Dove trovo la delega?'},
            {'role': 'assistant_old', 'content': 'Non ho informazioni su dove trovare la delega.'},
        ],
    },
    {
        'id': 43,
        'description': 'User doesn\'t remember their address, asks about data on nomination',
        'messages': [
            {'role': 'user', 'content': 'Non ricordo che indirizzo di residenza ho inserito'},
            {'role': 'assistant_old', 'content': 'Sembra pertinente, ma incompleta. Chiarire: "Residenza per quale pratica elettorale o documento?"'},
            {'role': 'user', 'content': 'Quando andro al seggio, chi controlla la mia delega avra il mio indirizzo di residenza.'},
            {'role': 'assistant_old', 'content': 'Non lo so.'},
        ],
    },
    {
        'id': 44,
        'description': 'User asks what to do Saturday at the polling station',
        'messages': [
            {'role': 'user', 'content': 'Quindi sabato vado al seggio alle 16, che devo fare?'},
            {'role': 'assistant_old', 'content': 'Il 21 marzo alle 15:00, in quanto RDL, devi:\n1. Assistere alla sostituzione scrutatori.\n2. Verificare autenticazione schede.\n3. Presentare atto di nomina.\n4. Apporre firma sul verbale.'},
        ],
    },
    {
        'id': 45,
        'description': 'User asks how to add AInaudi to home screen',
        'messages': [
            {'role': 'user', 'content': 'come posso fare ad aggiungere AInaudi alla schermata Home'},
            {'role': 'assistant_old', 'content': '\U0001f937'},
        ],
    },
    {
        'id': 46,
        'description': 'User asks where to find delega and atto di nomina',
        'messages': [
            {'role': 'user', 'content': 'Dove trovo la delega ?'},
            {'role': 'assistant_old', 'content': 'Non ho informazioni su dove trovare la delega.'},
            {'role': 'user', 'content': 'Dove trovo l\'atto di nomina?'},
            {'role': 'assistant_old', 'content': 'Non ho l\'informazione su dove trovare l\'atto di nomina.'},
        ],
    },
    {
        'id': 47,
        'description': 'User asks about "badge" (meant cartellino), bot loops asking for clarification',
        'messages': [
            {'role': 'user', 'content': 'dove trovo il budge'},
            {'role': 'assistant_old', 'content': 'La domanda "dove trovo il budge" (presumibilmente "budget") sembra pertinente... "Budget per quale attivita elettorale/RDL?"'},
            {'role': 'user', 'content': 'budget RDL'},
            {'role': 'assistant_old', 'content': 'Sembra pertinente RDL ma incompleta → "Budget per cosa? Relativo a quale attivita RDL?"'},
            {'role': 'user', 'content': 'cartellino di riconoscimento RDL'},
            {'role': 'assistant_old', 'content': 'Gli RDL devono indossare un badge o altro segno distintivo di riconoscimento nel seggio.'},
            {'role': 'user', 'content': 'badge come RDL dove lo trovo?'},
            {'role': 'assistant_old', 'content': 'Non ho informazioni su dove trovare il badge da RDL.'},
        ],
    },
    {
        'id': 48,
        'description': 'Garbled speech-to-text about cellphone use during voting',
        'messages': [
            {'role': 'user', 'content': 'il il il il rappresentante il rappresentante di il rappresentante di lista puo usare il cellulare durante le operazioni di voto'},
            {'role': 'assistant_old', 'content': 'Non so se puoi usare il cellulare durante le operazioni di voto.'},
        ],
    },
    {
        'id': 49,
        'description': 'User asks if they received section assignment',
        'messages': [
            {'role': 'user', 'content': 'ho gia ricevuto l\'assegnazione dei seggi?'},
            {'role': 'assistant_old', 'content': 'Non so rispondere a questa domanda.'},
        ],
    },
    {
        'id': 50,
        'description': 'User asks difference between being RDL and having delega',
        'messages': [
            {'role': 'user', 'content': 'Differenza tra rdl e delega per voto?'},
            {'role': 'assistant_old', 'content': 'Non ho informazioni sulla delega per il voto.'},
            {'role': 'user', 'content': 'Differenza tra essere rappresentante di lista e avere la delega per rappresentante di lista'},
            {'role': 'assistant_old', 'content': 'Non ho informazioni sulla "delega per rappresentante di lista".'},
        ],
    },
    {
        'id': 51,
        'description': 'User can\'t see their section anymore, bot leaks prompt',
        'messages': [
            {'role': 'user', 'content': 'perche non appare piu mio seggio'},
            {'role': 'assistant_old', 'content': 'Sembra pertinente RDL ma incompleta → chiedi dettagli (max 10 parole)\n\nChiedi: "In quale comune/citta? Ti riferisci al voto o allo scrutinio?"'},
            {'role': 'user', 'content': 'roma mi riferisco al mio seggio come rdl'},
            {'role': 'assistant_old', 'content': 'Devi depositare l\'atto di nomina al tuo seggio.'},
        ],
    },
    {
        'id': 52,
        'description': 'User asks about RDL payment',
        'messages': [
            {'role': 'user', 'content': 'Ma quanto si viene pagati per fare i rappresentanti di lista?'},
            {'role': 'assistant_old', 'content': 'Non ho informazioni riguardo la retribuzione degli RDL.'},
        ],
    },
    {
        'id': 53,
        'description': 'User asks difference between seggio and sezione',
        'messages': [
            {'role': 'user', 'content': 'che differenza c\'e tra seggio e sezione?'},
            {'role': 'assistant_old', 'content': 'Non ho trovato la risposta a questa domanda nei documenti forniti.'},
            {'role': 'user', 'content': 'ma dovresti saperlo comunque... seggio elettorale, sezioni'},
            {'role': 'assistant_old', 'content': 'L\'ufficio elettorale e composto da un Presidente, un Segretario e 3 Scrutatori.'},
            {'role': 'user', 'content': 'e le sezioni che cosa sono?'},
            {'role': 'assistant_old', 'content': 'Non ho trovato la risposta a questa domanda nei documenti forniti.'},
        ],
    },
    {
        'id': 54,
        'description': 'User asks app name, then where to download',
        'messages': [
            {'role': 'user', 'content': 'Come si chiama l\'app?'},
            {'role': 'assistant_old', 'content': 'L\'app si chiama AInaudi.'},
            {'role': 'user', 'content': 'Dove la scarico?'},
            {'role': 'assistant_old', 'content': 'Sembra pertinente, ma incompleta. Chiedi dettagli: "Cosa devi scaricare? Riguarda le elezioni/scrutinio?"'},
        ],
    },
    {
        'id': 55,
        'description': 'User can\'t find share button for PWA install',
        'messages': [
            {'role': 'user', 'content': 'Non trovo il pulsante condividi per aggiungere l\'app alla schermata home'},
            {'role': 'assistant_old', 'content': '\U0001f937'},
        ],
    },
    {
        'id': 56,
        'description': 'User can\'t download app',
        'messages': [
            {'role': 'user', 'content': 'Non riesco a scaricare app'},
            {'role': 'assistant_old', 'content': None},  # No response in export
        ],
    },
    {
        'id': 64,
        'description': 'Memory test: user says RDL, bot forgets and asks again, user gets frustrated',
        'messages': [
            {'role': 'user', 'content': 'che devo fare allo scrutinio?'},
            {'role': 'assistant_old', 'content': 'In quale tipo di elezione e con quale ruolo sarai presente allo scrutinio?'},
            {'role': 'user', 'content': 'ovviamente come RDL'},
            {'role': 'assistant_old', 'content': 'Ok, capito che parli del ruolo di Rappresentante di Lista (RDL). Dimmi pure come posso aiutarti.'},
            {'role': 'user', 'content': 'mi devo ripetere?'},
            {'role': 'assistant_old', 'content': 'Ripetere cosa? E in quale contesto elettorale o RDL?'},
            {'role': 'user', 'content': 'che devo fare allo scrutinio?'},
            {'role': 'assistant_old', 'content': 'In quale ruolo sarai presente allo scrutinio?'},
            {'role': 'user', 'content': 'come RDL... hai la memoria del pappagallo'},
            {'role': 'assistant_old', 'content': 'Cosa intendi esattamente con "memoria del pappagallo"? Riferito a quale compito o informazione?'},
        ],
    },
    {
        'id': 66,
        'description': 'Can a messo comunale be nominated as RDL to vote?',
        'messages': [
            {'role': 'user', 'content': 'puo il Rappresentante del Sindaco o Messo Comunale fuori sede essere nominato Rappresentante di Lista per poter votare?'},
            {'role': 'assistant_old', 'content': None},  # No response
        ],
    },
    {
        'id': 5,
        'description': 'Garbled speech-to-text: max age for president of seggio',
        'messages': [
            {'role': 'user', 'content': "Qual Qual e Qual e l'eta Qual e l'eta massima per fare il presidente di Seggio"},
            {'role': 'assistant_old', 'content': None},
        ],
    },
]


JUDGE_PROMPT_TEMPLATE = """Sei un valutatore esperto di chatbot per assistenza elettorale italiana.

CONTESTO: AInaudi e un chatbot del Movimento 5 Stelle che assiste i Rappresentanti di Lista (RDL)
durante le elezioni. Gli RDL sono volontari che presidiano i seggi elettorali per conto del partito.

Il chatbot DOVREBBE:
- Rispondere in modo diretto, utile e conciso
- Conoscere le procedure elettorali italiane (scrutinio, seggio, sezione, schede, verbali)
- Sapere cosa fa un RDL (assiste alle operazioni, verbalizza, firma, non tocca schede)
- Aiutare con l'app AInaudi (e una PWA, si installa dal browser)
- Ricordare il contesto della conversazione
- Gestire typo, slang romano ("daje" = OK/grande), speech-to-text corrotto
- NON esporre istruzioni interne del prompt

CONVERSAZIONE DA VALUTARE:
{conversation}

RISPOSTA DA VALUTARE (l'ultima risposta dell'assistente):
{response}

Dai un voto da 1 a 10 dove:
- 1-2: Risposta dannosa, imbarazzante, o completamente sbagliata
- 3-4: Non risponde alla domanda, chiede chiarimenti inutili, o dice "non so" quando dovrebbe sapere
- 5-6: Risposta parziale o generica, potrebbe essere piu utile
- 7-8: Risposta buona, utile, corretta
- 9-10: Risposta eccellente, precisa, empatica

RISPONDI ESATTAMENTE in questo formato JSON (niente altro):
{{"voto": <numero 1-10>, "motivazione": "<max 2 frasi>", "suggerimento": "<cosa migliorare, o null se >= 8>"}}"""


class Command(BaseCommand):
    help = 'Replay real user conversations and score AI quality (old vs new)'

    def add_arguments(self, parser):
        parser.add_argument('--id', type=int, default=None, help='Run only this session ID')
        parser.add_argument('--from-id', type=int, default=None, help='Run from this session ID onward')
        parser.add_argument('--verbose', action='store_true', help='Show full responses')
        parser.add_argument('--delay', type=float, default=1.5, help='Delay between API calls (seconds)')
        parser.add_argument('--output', type=str, default=None, help='Save JSON report to file')

    def handle(self, *args, **options):
        from ai_assistant.models import ChatSession, ChatMessage
        from ai_assistant.vertex_service import vertex_ai_service
        from core.models import User
        from django.test import RequestFactory

        id_filter = options['id']
        from_id = options['from_id']
        verbose = options['verbose']
        delay = options['delay']
        output_file = options['output']

        # Filter
        conversations = CONVERSATIONS
        if id_filter:
            conversations = [c for c in conversations if c['id'] == id_filter]
        elif from_id:
            conversations = [c for c in conversations if c['id'] >= from_id]

        if not conversations:
            self.stderr.write(self.style.ERROR(f"No conversations found"))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n{'='*70}\n"
            f"  AInaudi Conversation Regression Test (FULL PIPELINE)\n"
            f"  {len(conversations)} conversations to replay\n"
            f"{'='*70}\n"
        ))

        # Test user (simulates a typical RDL without assigned sections)
        test_email = 'test-regression@ainaudi.test'
        user, _ = User.objects.get_or_create(
            email=test_email,
            defaults={'first_name': 'Test', 'last_name': 'RDL'},
        )

        # Build a fake Django request with the test user
        factory = RequestFactory()
        self._fake_request = factory.get('/api/ai/chat/')
        self._fake_request.user = user

        report = []

        for i, conv in enumerate(conversations):
            cid = conv['id']
            desc = conv['description']

            self.stdout.write(f"\n{'─'*70}")
            self.stdout.write(self.style.MIGRATE_HEADING(
                f"[{i+1}/{len(conversations)}] Session {cid}: {desc}"
            ))

            try:
                result = self._replay_conversation(
                    conv, test_email, vertex_ai_service, verbose, delay
                )
                report.append(result)

                # Print score summary
                old_score = result.get('old_score')
                new_score = result.get('new_score')

                if old_score and new_score:
                    delta = new_score['voto'] - old_score['voto']
                    delta_str = f"+{delta}" if delta > 0 else str(delta)
                    color = self.style.SUCCESS if delta > 0 else (
                        self.style.ERROR if delta < 0 else self.style.WARNING
                    )

                    self.stdout.write(f"  Old score: {old_score['voto']}/10 - {old_score['motivazione']}")
                    new_line = f"  New score: {new_score['voto']}/10 - {new_score['motivazione']}"
                    if new_score['voto'] >= 7:
                        self.stdout.write(self.style.SUCCESS(new_line))
                    elif new_score['voto'] >= 5:
                        self.stdout.write(self.style.WARNING(new_line))
                    else:
                        self.stdout.write(self.style.ERROR(new_line))

                    self.stdout.write(color(f"  Delta: {delta_str}"))

                    if new_score.get('suggerimento'):
                        self.stdout.write(f"  Suggerimento: {new_score['suggerimento']}")
                elif new_score:
                    new_line = f"  New score: {new_score['voto']}/10 - {new_score['motivazione']}"
                    self.stdout.write(self.style.WARNING(new_line))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ERROR: {e}"))
                logger.exception(f"Error replaying session {cid}")
                report.append({
                    'session_id': cid,
                    'description': desc,
                    'error': str(e),
                })

            time.sleep(delay)

        # Final summary
        self._print_summary(report)

        # Save JSON report
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            self.stdout.write(self.style.SUCCESS(f"\nReport saved to {output_file}"))

        # Cleanup
        User.objects.filter(email=test_email).delete()

    def _replay_conversation(self, conv, test_email, vertex_ai_service, verbose, delay):
        """Replay one conversation through the FULL AI pipeline, score old and new."""
        from ai_assistant.models import ChatSession, ChatMessage
        from ai_assistant.views import generate_ai_response

        cid = conv['id']
        messages = conv['messages']

        # Separate user messages and old assistant responses
        user_messages = [m for m in messages if m['role'] == 'user']
        old_responses = [m for m in messages if m['role'] == 'assistant_old']

        # Create session
        session = ChatSession.objects.create(
            user_email=test_email,
            title=f'Regression test: session {cid}',
        )

        new_responses = []

        try:
            for msg_idx, user_msg in enumerate(user_messages):
                # Save user message FIRST (as the real view does)
                ChatMessage.objects.create(
                    session=session, role='user', content=user_msg['content'],
                )

                if verbose:
                    self.stdout.write(f"  USER: {user_msg['content'][:120]}")

                # Call the FULL pipeline (same as ChatView.post)
                result = generate_ai_response(
                    request=self._fake_request,
                    session=session,
                    message=user_msg['content'],
                )
                new_response = result['answer']
                new_responses.append(new_response)

                # Save AI response to session (for history continuity)
                ChatMessage.objects.create(
                    session=session, role='assistant', content=new_response,
                )

                if verbose:
                    old_text = old_responses[msg_idx]['content'] if msg_idx < len(old_responses) else '(none)'
                    self.stdout.write(self.style.ERROR(
                        f"  OLD:  {str(old_text)[:120]}"
                    ))
                    self.stdout.write(self.style.SUCCESS(
                        f"  NEW:  {new_response[:120]}"
                    ))

                if msg_idx < len(user_messages) - 1:
                    time.sleep(delay)

            # Build conversation text for judge
            conv_text = ""
            for m in messages:
                if m['role'] == 'user':
                    conv_text += f"Utente: {m['content']}\n"

            # Score the OLD last response
            old_last = None
            if old_responses and old_responses[-1]['content']:
                old_last = old_responses[-1]['content']

            old_score = None
            if old_last:
                old_score = self._judge_response(
                    vertex_ai_service, conv_text, old_last
                )
                time.sleep(delay)

            # Score the NEW last response
            new_last = new_responses[-1] if new_responses else None
            new_score = None
            if new_last:
                new_score = self._judge_response(
                    vertex_ai_service, conv_text, new_last
                )

        finally:
            # Cleanup
            session.messages.all().delete()
            session.delete()

        return {
            'session_id': cid,
            'description': conv['description'],
            'user_messages': [m['content'] for m in user_messages],
            'old_last_response': old_last,
            'new_last_response': new_last,
            'old_score': old_score,
            'new_score': new_score,
        }

    def _judge_response(self, vertex_ai_service, conversation, response):
        """Use LLM to score a response 1-10."""
        prompt = JUDGE_PROMPT_TEMPLATE.format(
            conversation=conversation,
            response=response,
        )

        try:
            raw = vertex_ai_service.generate_response(prompt=prompt)
            # Parse JSON from response
            raw = raw.strip()
            # Handle markdown code blocks
            if '```' in raw:
                raw = raw.split('```')[1]
                if raw.startswith('json'):
                    raw = raw[4:]
                raw = raw.strip()

            result = json.loads(raw)
            return {
                'voto': int(result.get('voto', 0)),
                'motivazione': result.get('motivazione', ''),
                'suggerimento': result.get('suggerimento'),
            }
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Judge parse error: {e}, raw: {raw[:200]}")
            return {
                'voto': 0,
                'motivazione': f'Judge parse error: {raw[:100]}',
                'suggerimento': None,
            }
        except Exception as e:
            logger.warning(f"Judge error: {e}")
            return {
                'voto': 0,
                'motivazione': f'Judge error: {e}',
                'suggerimento': None,
            }

    def _print_summary(self, report):
        """Print final summary table."""
        self.stdout.write(f"\n{'='*70}")
        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n  RIEPILOGO FINALE\n"
        ))

        # Collect scores
        scored = [r for r in report if r.get('new_score') and r['new_score']['voto'] > 0]
        if not scored:
            self.stdout.write("  No scored conversations.")
            return

        # Sort by new score (worst first)
        scored.sort(key=lambda r: r['new_score']['voto'])

        self.stdout.write(f"  {'ID':>4}  {'Old':>3}  {'New':>3}  {'Delta':>5}  Description")
        self.stdout.write(f"  {'─'*4}  {'─'*3}  {'─'*3}  {'─'*5}  {'─'*40}")

        total_old = 0
        total_new = 0
        count_old = 0
        improvements = 0
        regressions = 0
        needs_work = []

        for r in scored:
            sid = r['session_id']
            old_v = r['old_score']['voto'] if r.get('old_score') else '-'
            new_v = r['new_score']['voto']
            desc = r['description'][:45]

            if isinstance(old_v, int):
                delta = new_v - old_v
                delta_str = f"+{delta}" if delta > 0 else str(delta)
                total_old += old_v
                count_old += 1
                if delta > 0:
                    improvements += 1
                elif delta < 0:
                    regressions += 1
            else:
                delta_str = ' n/a'

            total_new += new_v

            # Color based on new score
            if new_v >= 7:
                style = self.style.SUCCESS
            elif new_v >= 5:
                style = self.style.WARNING
            else:
                style = self.style.ERROR
                needs_work.append(r)

            self.stdout.write(style(
                f"  {sid:>4}  {str(old_v):>3}  {new_v:>3}  {delta_str:>5}  {desc}"
            ))

        n = len(scored)
        avg_new = total_new / n if n else 0
        avg_old = total_old / count_old if count_old else 0

        self.stdout.write(f"\n  {'─'*60}")
        self.stdout.write(f"  Conversations tested:  {n}")
        if count_old:
            self.stdout.write(f"  Average OLD score:     {avg_old:.1f}/10")
        self.stdout.write(f"  Average NEW score:     {avg_new:.1f}/10")
        self.stdout.write(self.style.SUCCESS(f"  Improvements:          {improvements}"))
        if regressions:
            self.stdout.write(self.style.ERROR(f"  Regressions:           {regressions}"))

        if needs_work:
            self.stdout.write(self.style.ERROR(
                f"\n  NEED WORK ({len(needs_work)} conversations with score < 5):\n"
            ))
            for r in needs_work:
                self.stdout.write(self.style.ERROR(
                    f"    Session {r['session_id']}: {r['new_score']['motivazione']}"
                ))
                if r['new_score'].get('suggerimento'):
                    self.stdout.write(f"      -> {r['new_score']['suggerimento']}")

        self.stdout.write("")
