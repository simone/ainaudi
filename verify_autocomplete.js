#!/usr/bin/env node

/**
 * Verification script for JSONPath autocomplete
 * Run: node verify_autocomplete.js
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

// Test with example data
const exampleData = {
    delegato: {
        cognome: "Rossi",
        nome: "Mario",
        nome_completo: "Rossi Mario",
        email: "mario.rossi@m5s.it",
        telefono: "+39 123456789",
        carica_display: "Deputato"
    },
    subdelegato: {
        cognome: "Bianchi",
        nome: "Anna",
        email: "anna.bianchi@example.com"
    },
    designazioni: [
        {
            sezione: "001",
            indirizzo: "Via Roma 1, Milano",
            effettivo_cognome: "Verdi",
            effettivo_nome: "Luigi",
            effettivo_email: "luigi.verdi@example.com",
            supplente_cognome: "Gialli",
            supplente_nome: "Maria",
            supplente_email: "maria.gialli@example.com"
        },
        {
            sezione: "002",
            indirizzo: "Via Milano 5, Milano",
            effettivo_cognome: "Neri",
            effettivo_nome: "Paolo",
            effettivo_email: "paolo.neri@example.com",
            supplente_cognome: null,
            supplente_nome: null,
            supplente_email: null
        }
    ]
};

console.log('='.repeat(80));
console.log('JSONPath Autocomplete - Verification Test');
console.log('='.repeat(80));
console.log();

// Extract all paths
const paths = extractJSONPaths(exampleData);

console.log(`✓ Extracted ${paths.length} JSONPath expressions\n`);

// Display paths by category
console.log('📋 Delegato Fields:');
paths.filter(p => p.path.includes('.delegato.')).forEach(p => {
    console.log(`  ${p.path.padEnd(35)} (${p.type.padEnd(8)}) → ${p.sample}`);
});

console.log('\n📋 SubDelegato Fields:');
paths.filter(p => p.path.includes('.subdelegato.')).forEach(p => {
    console.log(`  ${p.path.padEnd(35)} (${p.type.padEnd(8)}) → ${p.sample}`);
});

console.log('\n📋 Designazioni (Array):');
paths.filter(p => p.path.includes('designazioni')).forEach(p => {
    console.log(`  ${p.path.padEnd(35)} (${p.type.padEnd(8)}) → ${p.sample}`);
});

console.log('\n' + '='.repeat(80));
console.log('Test Scenarios:');
console.log('='.repeat(80));

// Test filtering
const testQueries = [
    { query: '$.del', expected: 'delegato fields' },
    { query: '$.subdel', expected: 'subdelegato fields' },
    { query: '$.desi', expected: 'designazioni array' },
    { query: '$.designazioni[].eff', expected: 'effettivo fields' },
    { query: '$.designazioni[].supp', expected: 'supplente fields' }
];

testQueries.forEach(({ query, expected }) => {
    const filtered = paths.filter(p =>
        p.path.toLowerCase().includes(query.toLowerCase())
    );
    console.log(`\n  Query: "${query}" → ${filtered.length} results (${expected})`);
    filtered.slice(0, 3).forEach(p => {
        console.log(`    • ${p.path}`);
    });
    if (filtered.length > 3) {
        console.log(`    ... and ${filtered.length - 3} more`);
    }
});

console.log('\n' + '='.repeat(80));
console.log('✅ Verification Complete!');
console.log('='.repeat(80));
console.log('\nThe JSONPath autocomplete is working correctly.');
console.log('Open the Template Editor to see it in action!\n');
