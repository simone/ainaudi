#!/bin/bash
# Script per scaricare i CSV corretti ISTAT per comuni e sezioni
# Uso: ./scripts/download-csv-istat.sh

set -e

FIXTURES_DIR="backend_django/fixtures"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Download CSV ISTAT per Comuni e Sezioni"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📥 Fonte: ISTAT Open Data + Ministero Interno"
echo ""

# Crea directory fixtures se non esiste
mkdir -p "$FIXTURES_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  NOTA IMPORTANTE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⚠️  I CSV ISTAT per comuni cambiano frequentemente URL."
echo "    Se il download fallisce, segui questa procedura:"
echo ""
echo "1️⃣  Vai su: https://www.istat.it/it/archivio/6789"
echo "   Scarica: 'Elenco comuni italiani' (formato CSV)"
echo ""
echo "2️⃣  Vai su: https://dait.interno.gov.it/territorio-e-autonomie-locali"
echo "   Scarica: 'Sezioni elettorali' (formato CSV o XLS→CSV)"
echo ""
echo "3️⃣  Rinomina e salva in $FIXTURES_DIR/:"
echo "   - comuni_istat.csv"
echo "   - sezioni_italia.csv"
echo ""

read -p "Vuoi continuare con download automatico? (Y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo "⏭️  Download annullato"
    echo "   Scarica manualmente e salva in $FIXTURES_DIR/"
    exit 0
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  File 1: Comuni Italiani"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

COMUNI_URL="https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv"
COMUNI_FILE="$FIXTURES_DIR/comuni_istat.csv"

echo "📥 Download comuni da ISTAT..."
echo "   URL: $COMUNI_URL"

if curl -L -f -o "$COMUNI_FILE" "$COMUNI_URL" 2>/dev/null; then
    SIZE=$(du -h "$COMUNI_FILE" | cut -f1)
    echo "✅ Download completato: $COMUNI_FILE ($SIZE)"
else
    echo "❌ Download fallito!"
    echo ""
    echo "📖 Scarica manualmente da:"
    echo "   https://www.istat.it/it/archivio/6789"
    echo ""
    echo "💾 Salva come: $COMUNI_FILE"
    echo ""
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  File 2: Sezioni Elettorali"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "⚠️  Le sezioni elettorali NON sono scaricabili automaticamente."
echo "   Devi scaricarle manualmente dal Ministero Interno."
echo ""
echo "📖 Procedura:"
echo "   1. Vai su: https://dait.interno.gov.it/"
echo "   2. Sezione: 'Territorio e Autonomie Locali'"
echo "   3. Scarica: 'Anagrafe Sezioni Elettorali'"
echo "   4. Se in formato XLS, converti in CSV"
echo "   5. Salva come: $FIXTURES_DIR/sezioni_italia.csv"
echo ""

read -p "Hai già il file sezioni_italia.csv? (y/N) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -f "$FIXTURES_DIR/sezioni_italia.csv" ]; then
        SIZE=$(du -h "$FIXTURES_DIR/sezioni_italia.csv" | cut -f1)
        echo "✅ Trovato: sezioni_italia.csv ($SIZE)"
    else
        echo "❌ File non trovato: $FIXTURES_DIR/sezioni_italia.csv"
    fi
else
    echo "⏭️  Scarica quando necessario"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📊 RIEPILOGO FILE NECESSARI"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Controlla questi file in $FIXTURES_DIR/:"
echo ""

if [ -f "$FIXTURES_DIR/comuni_istat.csv" ]; then
    SIZE=$(du -h "$FIXTURES_DIR/comuni_istat.csv" | cut -f1)
    echo "✅ comuni_istat.csv ($SIZE)"
else
    echo "❌ comuni_istat.csv (mancante)"
fi

if [ -f "$FIXTURES_DIR/sezioni_italia.csv" ]; then
    SIZE=$(du -h "$FIXTURES_DIR/sezioni_italia.csv" | cut -f1)
    echo "✅ sezioni_italia.csv ($SIZE)"
else
    echo "❌ sezioni_italia.csv (mancante)"
fi

if [ -f "$FIXTURES_DIR/ROMA - Sezioni.csv" ]; then
    SIZE=$(du -h "$FIXTURES_DIR/ROMA - Sezioni.csv" | cut -f1)
    echo "✅ ROMA - Sezioni.csv ($SIZE)"
else
    echo "ℹ️  ROMA - Sezioni.csv (opzionale)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🚀 PROSSIMI PASSI"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ -f "$FIXTURES_DIR/comuni_istat.csv" ]; then
    echo "1️⃣  Import comuni:"
    echo "   docker-compose exec backend python manage.py import_comuni_istat --file fixtures/comuni_istat.csv"
    echo ""
fi

if [ -f "$FIXTURES_DIR/sezioni_italia.csv" ]; then
    echo "2️⃣  Import sezioni:"
    echo "   docker-compose exec backend python manage.py import_sezioni_italia --file fixtures/sezioni_italia.csv"
    echo ""
fi

echo "📖 Documentazione completa: SEZIONI_IMPORT.md"
echo ""
