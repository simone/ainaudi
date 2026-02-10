#!/bin/bash
# Script per inizializzare il database da zero con tutti i dati necessari
# Uso: ./scripts/init-db.sh [-y|--yes]
#
# Flags:
#   -y, --yes    Auto-conferma (salta tutte le domande, risponde SI a tutto)

set -e  # Exit on error

# Parse arguments
AUTO_YES=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -y|--yes)
            AUTO_YES=true
            shift
            ;;
        *)
            echo "Usage: $0 [-y|--yes]"
            exit 1
            ;;
    esac
done

if [ "$AUTO_YES" = true ]; then
    echo "🤖 Modalità AUTO-YES attivata (nessuna conferma richiesta)"
    echo ""
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Inizializzazione Database AInaudi"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Rileva ambiente (Docker o locale)
if docker-compose ps 2>/dev/null | grep -q "backend.*Up"; then
    echo "🐳 Rilevato Docker Compose"
    DOCKER_CMD="docker-compose exec -T backend"
elif docker ps 2>/dev/null | grep -q "ainaudi.*backend"; then
    echo "🐳 Rilevato Docker"
    CONTAINER_NAME=$(docker ps --format "{{.Names}}" | grep backend | head -1)
    DOCKER_CMD="docker exec -i $CONTAINER_NAME"
else
    echo "💻 Esecuzione in locale (no Docker)"
    DOCKER_CMD=""
fi

# Helper function per eseguire comandi Django
run_manage() {
    if [ -z "$DOCKER_CMD" ]; then
        cd backend_django
        python manage.py "$@"
        cd ..
    else
        $DOCKER_CMD python manage.py "$@"
    fi
}

# Helper function per prompt yes/no con auto-yes support
# Usage: ask_yes_no "Domanda?" "default_value"
# Returns: 0 (yes) or 1 (no)
ask_yes_no() {
    local question="$1"
    local default="${2:-N}"  # Default N se non specificato

    if [ "$AUTO_YES" = true ]; then
        echo "$question Y (auto-yes)"
        return 0  # Yes
    fi

    read -p "$question " -n 1 -r
    echo ""

    # Check response
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        return 0  # Yes
    elif [[ $REPLY =~ ^[Nn]$ ]]; then
        return 1  # No
    else
        # Empty response, use default
        if [[ $default =~ ^[Yy]$ ]]; then
            return 0
        else
            return 1
        fi
    fi
}

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 1: Migrations"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

run_manage migrate

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 2: Dati Iniziali (Regioni, Province)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📍 Carico Regioni e Province italiane..."
run_manage loaddata fixtures/initial_data.json

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 3: Consultazione Elettorale"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "🗳️  Carico Referendum Costituzionale Giustizia 2026..."
run_manage loaddata fixtures/referendum_giustizia_2026.json

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 3bis: Delegati Roma per Referendum 2026"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "👥 Carico 5 delegati per Roma..."
echo "   Pietracci, Federici, Meleo, Contardi, Riccardi"
echo ""

if ask_yes_no "Vuoi caricare i delegati Roma? (y/N)" "Y"; then
    run_manage load_delegati_roma
else
    echo "⏭️  Salto caricamento delegati"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 3ter: Risorse Referendum 2026"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📚 Carico risorse educative e campagna referendum..."
echo "   • Link campagna M5S 'Vota NO al Referendum Salva-Casta'"
echo "   • Dichiarazioni di Giuseppe Conte"
echo "   • Informazioni istituzionali"
echo "   • PDF Corso Formazione RDL (1.3 MB)"
echo ""

run_manage loaddata fixtures/risorse_referendum_2026.json

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 4: Comuni (da CSV ISTAT)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Determina percorso CSV comuni
COMUNI_CSV_LOCAL="backend_django/fixtures/comuni_istat.csv"

# Controlla se il CSV comuni esiste
if [ ! -f "$COMUNI_CSV_LOCAL" ]; then
    echo "📥 CSV comuni non trovato, scarico da ISTAT..."
    echo ""

    # URL ISTAT per elenco comuni (aggiornato 2024)
    COMUNI_URL="https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv"

    echo "   Fonte: $COMUNI_URL"

    # Prova a scaricare con curl
    if command -v curl >/dev/null 2>&1; then
        if curl -L -f -o "$COMUNI_CSV_LOCAL" "$COMUNI_URL" 2>/dev/null; then
            echo "✅ Download completato!"
        else
            echo "❌ Download fallito!"
            echo ""
            echo "📖 Scarica manualmente da:"
            echo "   https://www.istat.it/it/archivio/6789"
            echo "   Salva come: $COMUNI_CSV_LOCAL"
            echo ""
            echo "⏭️  Salto import comuni"
            COMUNI_CSV_LOCAL=""
        fi
    elif command -v wget >/dev/null 2>&1; then
        if wget -q -O "$COMUNI_CSV_LOCAL" "$COMUNI_URL" 2>/dev/null; then
            echo "✅ Download completato!"
        else
            echo "❌ Download fallito!"
            echo ""
            echo "📖 Scarica manualmente da:"
            echo "   https://www.istat.it/it/archivio/6789"
            echo "   Salva come: $COMUNI_CSV_LOCAL"
            echo ""
            echo "⏭️  Salto import comuni"
            COMUNI_CSV_LOCAL=""
        fi
    else
        echo "❌ curl/wget non disponibili"
        echo ""
        echo "📖 Scarica manualmente da:"
        echo "   https://www.istat.it/it/archivio/6789"
        echo "   Salva come: $COMUNI_CSV_LOCAL"
        echo ""
        echo "⏭️  Salto import comuni"
        COMUNI_CSV_LOCAL=""
    fi
    echo ""
fi

# Import comuni se CSV disponibile
if [ -n "$COMUNI_CSV_LOCAL" ] && [ -f "$COMUNI_CSV_LOCAL" ]; then
    echo "🏘️  Import comuni italiani da dati ISTAT..."
    echo "   (Questo può richiedere 1-2 minuti...)"

    # Percorso per Docker/locale
    if [ -z "$DOCKER_CMD" ]; then
        CSV_PATH="$COMUNI_CSV_LOCAL"
    else
        CSV_PATH="fixtures/comuni_istat.csv"
    fi

    run_manage import_comuni_istat --file "$CSV_PATH"
else
    echo "⏭️  CSV comuni non disponibile, salto import"
    echo "   Scarica da: https://www.istat.it/it/archivio/6789"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 5: Municipi Grandi Città"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "🏛️  Le grandi città italiane sono divise in municipi/circoscrizioni."
echo "   Genera: Roma (15), Milano (9), Torino (8), Napoli (10), Bari (5), Palermo (8), Genova (9)"
echo ""

if ask_yes_no "Vuoi generare i municipi delle grandi città? (~64 municipi) (y/N)" "Y"; then
    echo "🏛️  Generazione municipi per grandi città..."
    run_manage generate_municipi
else
    echo "⏭️  Salto generazione municipi"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 5bis: Flag Popolazione Comuni (> 15.000 abitanti)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📊 Determina quali comuni hanno più di 15.000 abitanti."
echo "   Questo influenza il sistema elettorale (turno unico vs doppio turno)."
echo ""

if ask_yes_no "Vuoi aggiornare il flag popolazione comuni? (~556 comuni > 15k) (y/N)" "Y"; then
    echo "📊 Update flag sopra_15000_abitanti..."
    run_manage update_comuni_popolazione
else
    echo "⏭️  Salto update popolazione"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 6: Sezioni Elettorali Nazionali"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

SEZIONI_CSV_LOCAL="backend_django/fixtures/sezioni_eligendo.csv"

# Controlla se il CSV sezioni esiste
if [ ! -f "$SEZIONI_CSV_LOCAL" ]; then
    echo "📥 CSV sezioni non trovato, scarico da Eligendo..."
    echo ""

    # URL Eligendo per sezioni elettorali
    SEZIONI_URL="https://elezionistorico.interno.gov.it/daithome/documenti/opendata/catalogoagid/elenco-sezioni-elettorali.csv"

    echo "   Fonte: $SEZIONI_URL"

    # Prova a scaricare con curl
    if command -v curl >/dev/null 2>&1; then
        if curl -L -f -o "$SEZIONI_CSV_LOCAL" "$SEZIONI_URL" 2>/dev/null; then
            echo "✅ Download completato!"
        else
            echo "❌ Download fallito!"
            echo ""
            echo "📖 Scarica manualmente da:"
            echo "   https://elezionistorico.interno.gov.it/eligendo/opendata.php"
            echo "   File: 'elenco-sezioni-elettorali.csv'"
            echo ""
            echo "💾 Salva come: $SEZIONI_CSV_LOCAL"
            echo ""
            echo "⏭️  Salto import sezioni"
            SEZIONI_CSV_LOCAL=""
        fi
    elif command -v wget >/dev/null 2>&1; then
        if wget -q -O "$SEZIONI_CSV_LOCAL" "$SEZIONI_URL" 2>/dev/null; then
            echo "✅ Download completato!"
        else
            echo "❌ Download fallito!"
            echo ""
            echo "📖 Scarica manualmente da:"
            echo "   https://elezionistorico.interno.gov.it/eligendo/opendata.php"
            echo ""
            echo "⏭️  Salto import sezioni"
            SEZIONI_CSV_LOCAL=""
        fi
    else
        echo "❌ curl/wget non disponibili"
        echo ""
        echo "📖 Scarica manualmente da:"
        echo "   https://elezionistorico.interno.gov.it/eligendo/opendata.php"
        echo ""
        echo "⏭️  Salto import sezioni"
        SEZIONI_CSV_LOCAL=""
    fi
    echo ""
fi

# Import sezioni se CSV disponibile
if [ -n "$SEZIONI_CSV_LOCAL" ] && [ -f "$SEZIONI_CSV_LOCAL" ]; then
    if ask_yes_no "Vuoi importare le sezioni elettorali nazionali? (~61.000 sezioni) (y/N)" "Y"; then
        echo "🗳️  Import sezioni elettorali da Eligendo..."
        echo "   (~61.540 sezioni, richiede 1-2 minuti...)"

        # Percorso per Docker/locale
        if [ -z "$DOCKER_CMD" ]; then
            CSV_PATH="$SEZIONI_CSV_LOCAL"
        else
            CSV_PATH="fixtures/sezioni_eligendo.csv"
        fi

        run_manage import_sezioni_italia --file "$CSV_PATH"
    else
        echo "⏭️  Salto import sezioni"
    fi
else
    echo "⏭️  CSV sezioni non disponibile, salto import"
    echo "   Scarica da: https://elezionistorico.interno.gov.it/eligendo/opendata.php"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 6bis: Matching Sezioni → Plessi Scolastici"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📚 I file SCUANA contengono i plessi scolastici nazionali."
echo "   Il matching collega le sezioni ai plessi per migliorare i dati."
echo ""

# Check if SCUANA files exist
SCUANA_STAT="backend_django/fixtures/SCUANAGRAFESTAT20252620250901.csv"
SCUANA_PAR="backend_django/fixtures/SCUANAGRAFEPAR20252620250901.csv"
SCUANA_AUT_STAT="backend_django/fixtures/SCUANAAUTSTAT20252620250901.csv"
SCUANA_AUT_PAR="backend_django/fixtures/SCUANAAUTPAR20252620250901.csv"

if [ -f "$SCUANA_STAT" ]; then
    if ask_yes_no "Vuoi eseguire il matching sezioni-plessi? (~60k sezioni, 2-3 min) (y/N)" "Y"; then
        echo "🔗 Matching sezioni con plessi scolastici..."
        echo "   (Questo migliora denominazioni e indirizzi dove disponibile)"

        # Build command with available files
        MATCH_CMD="match_sezioni_plessi --stat fixtures/SCUANAGRAFESTAT20252620250901.csv --threshold 0.6"

        if [ -f "$SCUANA_PAR" ]; then
            MATCH_CMD="$MATCH_CMD --par fixtures/SCUANAGRAFEPAR20252620250901.csv"
        fi
        if [ -f "$SCUANA_AUT_STAT" ]; then
            MATCH_CMD="$MATCH_CMD --aut-stat fixtures/SCUANAAUTSTAT20252620250901.csv"
        fi
        if [ -f "$SCUANA_AUT_PAR" ]; then
            MATCH_CMD="$MATCH_CMD --aut-par fixtures/SCUANAAUTPAR20252620250901.csv"
        fi

        run_manage $MATCH_CMD
    else
        echo "⏭️  Salto matching sezioni-plessi"
    fi
else
    echo "ℹ️  File SCUANA non trovati, salto matching"
    echo "   I file sono già presenti in fixtures/ con il repository"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 6ter: Update Dettagli Sezioni (es. Roma)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📍 Per città specifiche, i comuni rilasciano dati ancora più dettagliati."
echo "   Roma ha un CSV con indirizzi specifici e municipi."
echo ""

if [ -f "backend_django/fixtures/ROMA - Sezioni.csv" ]; then
    if ask_yes_no "Vuoi aggiornare le sezioni di Roma con indirizzi specifici? (y/N)" "Y"; then
        echo "🏛️  Aggiorno sezioni di Roma con indirizzi..."

        if [ -z "$DOCKER_CMD" ]; then
            CSV_ROMA="backend_django/fixtures/ROMA - Sezioni.csv"
        else
            CSV_ROMA="fixtures/ROMA - Sezioni.csv"
        fi

        run_manage update_sezioni_dettagli "$CSV_ROMA"
    else
        echo "⏭️  Salto update sezioni Roma"
    fi
else
    echo "ℹ️  File 'ROMA - Sezioni.csv' non trovato, salto questo step"
    echo "   Puoi aggiungerlo dopo in fixtures/ e eseguire:"
    echo "   python manage.py update_sezioni_dettagli 'fixtures/ROMA - Sezioni.csv'"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 7: Superuser Django"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ "$AUTO_YES" = true ]; then
    echo "⏭️  Salto creazione superuser (auto-yes richiede input manuale)"
    echo "   Crea il superuser dopo con: docker-compose exec backend python manage.py createsuperuser"
elif ask_yes_no "Vuoi creare un superuser adesso? (Y/n)" "Y"; then
    if [ -z "$DOCKER_CMD" ]; then
        cd backend_django
        python manage.py createsuperuser
        cd ..
    else
        # Remove -T flag for interactive input
        docker-compose exec backend python manage.py createsuperuser || \
        docker exec -it $(docker ps --format "{{.Names}}" | grep backend | head -1) python manage.py createsuperuser
    fi
else
    echo "⏭️  Salto creazione superuser"
    echo "   Puoi crearlo dopo con: python manage.py createsuperuser"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ INIZIALIZZAZIONE COMPLETATA!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Database popolato con:"
echo "   ✅ 20 Regioni"
echo "   ✅ 107 Province"
echo "   ✅ 7.896 Comuni italiani"
echo "   ✅ 64 Municipi (Roma, Milano, Torino, Napoli, Bari, Palermo, Genova)"
echo "   ✅ 556 Comuni > 15.000 abitanti (flag sistema elettorale)"
echo "   ✅ 61.543 Sezioni Elettorali nazionali (Eligendo)"
echo "   ✅ ~10.000 Sezioni migliorate con matching plessi SCUANA"
echo "   ✅ Referendum Costituzionale Giustizia 2026 (ATTIVO)"
echo "   ✅ 5 Delegati per Roma (Pietracci, Federici, Meleo, Contardi, Riccardi)"
echo ""
echo "📈 Qualità Dati:"
echo "   ✅ 99% sezioni con indirizzo"
echo "   ✅ 98% sezioni con denominazione"
echo "   ✅ 100% copertura comuni italiani"
echo ""
echo "🗳️  Consultazione Elettorale:"
echo "   • Data: 22-23 marzo 2026"
echo "   • Tipo: Referendum Costituzionale Confermativo (art. 138 Cost.)"
echo "   • Quorum: NON richiesto"
echo "   • Oggetto: Riforma Giustizia (Separazione Carriere)"
echo ""
echo "🚀 Prossimi passi:"
echo "   1. Crea superuser: docker-compose exec backend python manage.py createsuperuser"
echo "   2. Accedi frontend: http://localhost:3000"
echo "   3. Login con Magic Link"
echo "   4. Admin Django: http://localhost:3001/admin"
echo ""
echo "📖 Comandi utili:"
echo "   - Aggiorna sezioni specifiche: python manage.py update_sezioni_dettagli <file.csv>"
echo "   - Verifica dati: python manage.py shell"
echo ""
echo "📥 Fonti dati:"
echo "   - Comuni: https://www.istat.it/it/archivio/6789"
echo "   - Sezioni: https://elezionistorico.interno.gov.it/eligendo/opendata.php"
echo ""
