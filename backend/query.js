const NodeCache = require("node-cache");
const {eq} = require("./tools");
const cache = new NodeCache({ stdTTL: 60 });

// Exports functions to query the Google Sheets
exports.visible_sections = async (sheets, spreadsheetId, email) => {
    if (cache.has(email)) {
        console.log('Cache hit', email, "visible_sections");
        return cache.get(email);
    }
    const referenti = (await sheets.spreadsheets.values.get({
        spreadsheetId,
        range: "Referenti!A2:C",
    })).data.values.filter((row) => eq(row[0], email));
    let results = (await sheets.spreadsheets.values.get({
        spreadsheetId,
        range: "Sezioni!A2:C",
    })).data.values.filter((row) => referenti.some(
        // referente/sezioni[1] è il comune, referente/sezioni[2] è il municipio
        (referente) => referente[1] === row[1] && referente[2] === row[2])
    ).map(sezione => [sezione[1], sezione[0]]);
    cache.set(email, results);
    return results;

}