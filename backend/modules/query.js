exports.visible_sections = async (sheets, spreadsheetId, email) => {
    const referenti = (await sheets.spreadsheets.values.get({
        spreadsheetId,
        range: "Referenti!A2:C",
    })).data.values.filter((row) => row[0] === email);
    return (await sheets.spreadsheets.values.get({
        spreadsheetId,
        range: "Sezioni!A2:C",
    })).data.values.filter((row) => referenti.some(
        // referente/sezioni[1] è il comune, referente/sezioni[2] è il municipio
        (referente) => referente[1] === row[1] && referente[2] === row[2])
    ).map(sezione => [sezione[1], sezione[0]]);
}