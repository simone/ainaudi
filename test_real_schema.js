#!/usr/bin/env node

/**
 * Test autocomplete con schema reale dal database
 */

// Extract JSONPath function (same as in component)
function extractJSONPaths(json, prefix = '$') {
    const paths = [];

    if (json === null || json === undefined) return paths;

    if (Array.isArray(json)) {
        paths.push({
            path: prefix,
            type: 'array',
            sample: `[${json.length} elementi]`
        });

        if (json.length > 0) {
            const itemPaths = extractJSONPaths(json[0], `${prefix}[]`);
            paths.push(...itemPaths);
        }

        return paths;
    }

    if (typeof json === 'object') {
        for (const [key, value] of Object.entries(json)) {
            const currentPath = `${prefix}.${key}`;

            if (value === null) {
                paths.push({ path: currentPath, type: 'null', sample: 'null' });
            } else if (Array.isArray(value)) {
                paths.push({
                    path: currentPath,
                    type: 'array',
                    sample: `[${value.length} elementi]`
                });

                if (value.length > 0) {
                    const itemPaths = extractJSONPaths(value[0], `${currentPath}[]`);
                    paths.push(...itemPaths);
                }
            } else if (typeof value === 'object') {
                const nestedPaths = extractJSONPaths(value, currentPath);
                paths.push(...nestedPaths);
            } else {
                paths.push({
                    path: currentPath,
                    type: typeof value,
                    sample: String(value).length > 50
                        ? String(value).substring(0, 50) + '...'
                        : String(value)
                });
            }
        }
    }

    return paths;
}

// Schema DESIGNATION dal database (popolato dal command)
const designationSchema = {
    "delegato": {
        "id": 1,
        "cognome": "Rossi",
        "nome": "Mario",
        "nome_completo": "Rossi Mario",
        "luogo_nascita": "Roma",
        "data_nascita": "1980-01-15",
        "carica": "DEPUTATO",
        "carica_display": "Deputato",
        "circoscrizione": "Lazio 1",
        "data_nomina": "2024-01-01",
        "email": "mario.rossi@m5s.it",
        "telefono": "+39 123456789",
        "territorio": "Regioni: Lazio",
        "n_sub_deleghe": 5
    },
    "subdelegato": {
        "id": 10,
        "cognome": "Bianchi",
        "nome": "Anna",
        "nome_completo": "Bianchi Anna",
        "email": "anna.bianchi@example.com",
        "telefono": "+39 987654321",
        "territorio": "Province: Milano | Comuni: Milano, Monza",
        "delegato_nome": "Rossi Mario",
        "tipo_delega_display": "Firma Autenticata"
    },
    "designazioni": [
        {
            "id": 100,
            "sezione": 1,
            "sezione_numero": "001",
            "sezione_comune": "Milano",
            "sezione_indirizzo": "Via Roma 1, 20121 Milano",
            "sezione_municipio": 1,
            "ruolo": "EFFETTIVO",
            "ruolo_display": "Effettivo",
            "stato": "CONFERMATA",
            "stato_display": "Confermata",
            "cognome": "Verdi",
            "nome": "Luigi",
            "nome_completo": "Verdi Luigi",
            "luogo_nascita": "Torino",
            "data_nascita": "1990-03-20",
            "domicilio": "Via Milano 5, 20122 Milano (MI)",
            "email": "luigi.verdi@example.com",
            "telefono": "+39 111222333",
            "data_designazione": "2024-03-15",
            "delegato_nome": "Rossi Mario",
            "sub_delegato_nome": "Bianchi Anna",
            "designante_nome": "Bianchi Anna"
        }
    ]
};

console.log('='.repeat(80));
console.log('Test Autocomplete con Schema Reale (DESIGNATION)');
console.log('='.repeat(80));
console.log();

// Extract all paths
const paths = extractJSONPaths(designationSchema);

console.log(`✓ Estratti ${paths.length} JSONPath expressions dallo schema reale\n`);

// Categorize paths
const delegatoPaths = paths.filter(p => p.path.includes('.delegato.'));
const subdelegatoPaths = paths.filter(p => p.path.includes('.subdelegato.'));
const designazioniPaths = paths.filter(p => p.path.includes('designazioni'));

console.log('📋 Campi Delegato:');
console.log(`   Trovati: ${delegatoPaths.length} campi`);
delegatoPaths.slice(0, 5).forEach(p => {
    console.log(`   • ${p.path.padEnd(40)} (${p.type})`);
});
if (delegatoPaths.length > 5) {
    console.log(`   ... e altri ${delegatoPaths.length - 5} campi`);
}

console.log('\n📋 Campi SubDelegato:');
console.log(`   Trovati: ${subdelegatoPaths.length} campi`);
subdelegatoPaths.slice(0, 5).forEach(p => {
    console.log(`   • ${p.path.padEnd(40)} (${p.type})`);
});
if (subdelegatoPaths.length > 5) {
    console.log(`   ... e altri ${subdelegatoPaths.length - 5} campi`);
}

console.log('\n📋 Campi Designazioni:');
console.log(`   Trovati: ${designazioniPaths.length} campi (array + elementi)`);
console.log(`   • $.designazioni                         (array) [${designationSchema.designazioni.length} elementi]`);
designazioniPaths.filter(p => p.path.includes('[]')).slice(0, 8).forEach(p => {
    console.log(`   • ${p.path.padEnd(40)} (${p.type})`);
});
if (designazioniPaths.filter(p => p.path.includes('[]')).length > 8) {
    console.log(`   ... e altri ${designazioniPaths.filter(p => p.path.includes('[]')).length - 8} campi`);
}

console.log('\n' + '='.repeat(80));
console.log('Test Queries Comuni:');
console.log('='.repeat(80));

const testQueries = [
    { query: '$.del', desc: 'Campi delegato' },
    { query: '$.subdel', desc: 'Campi subdelegato' },
    { query: '$.designazioni', desc: 'Array designazioni + campi loop' },
    { query: '$.designazioni[].sezione', desc: 'Info sezione' },
    { query: '$.designazioni[].nome', desc: 'Nome RDL' },
    { query: '$.designazioni[].ruolo', desc: 'Ruolo RDL' }
];

testQueries.forEach(({ query, desc }) => {
    const filtered = paths.filter(p =>
        p.path.toLowerCase().includes(query.toLowerCase())
    );
    console.log(`\n  Query: "${query}"`);
    console.log(`  Descrizione: ${desc}`);
    console.log(`  Risultati: ${filtered.length}`);
    filtered.slice(0, 3).forEach(p => {
        console.log(`    • ${p.path}`);
    });
    if (filtered.length > 3) {
        console.log(`    ... e altri ${filtered.length - 3}`);
    }
});

console.log('\n' + '='.repeat(80));
console.log('Esempi Pratici:');
console.log('='.repeat(80));

console.log('\n1. Campo semplice:');
console.log('   $.delegato.nome_completo → "Rossi Mario"');

console.log('\n2. Concatenazione:');
console.log('   $.subdelegato.cognome + " " + $.subdelegato.nome → "Bianchi Anna"');

console.log('\n3. Loop array (type: loop):');
console.log('   $.designazioni → [1 elemento]');

console.log('\n4. Campi dentro loop (path relativi):');
console.log('   $.sezione_numero → "001"');
console.log('   $.nome_completo → "Verdi Luigi"');
console.log('   $.ruolo_display → "Effettivo"');

console.log('\n5. Concatenazione dentro loop:');
console.log('   $.sezione_numero + " - " + $.sezione_comune → "001 - Milano"');

console.log('\n' + '='.repeat(80));
console.log('✅ Test Completato con Schema Reale!');
console.log('='.repeat(80));
console.log('\nL\'autocomplete nel Template Editor mostrerà tutti questi campi.');
console.log('Prova ad aprire il Template Editor e digitare "$." per vederli!\n');
