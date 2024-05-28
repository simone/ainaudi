const {visible_sections} = require("./query");

exports.sectionModule = ({app, authenticateToken, perms, sheets, SHEET_ID}) =>
{
    const eq = (s1, s2) => s1.localeCompare(s2, undefined, { sensitivity: 'base' }) === 0;
    app.get('/api/sections/:type', authenticateToken, async (req, res) => {
        const sectionType = req.params.type;
        const {email} = req.user;
        const {sections, referenti} = await perms(email);
        try {
            switch (sectionType) {
                case 'own':
                    if (!sections) {
                        res.status(403).json({error: "Forbidden"});
                        return;
                    }
                    break;
                case 'assigned':
                    if (!referenti) {
                        res.status(403).json({error: "Forbidden"});
                        return;
                    }
                    break;
                default:
                    res.status(404).json({error: "Not found"});
                    return;
            }
            const sezioni = referenti ? await visible_sections(sheets, SHEET_ID, email) : [];
            const filter = () => {
                if (sectionType === 'own') {
                    return (row) => eq(row[2], email);
                } else {
                    return (row) => !eq(row[2], email) && sezioni.some(
                        // dati[0]/sezione[1] è il comune, dati[1]/sezione[0] è la sezione
                        (sezione) => sezione[0] === row[0] && sezione[1] === row[1]);
                }
            }
            const response = await sheets.spreadsheets.values.get({
                spreadsheetId: SHEET_ID,
                range: `Dati!A2:ZZ`,
            });
            const values = response.data.values.filter(filter());
            res.status(response.status).json({
                rows: values.map((row) => ({
                    comune: row[0],
                    sezione: row[1],
                    email: row[2].toLowerCase(),
                    values: row.slice(3)
                }))
            });
            console.log(response.status, email, 'sections');
        } catch (error) {
            res.status(500).json({error: error.message});
            console.log(error);
        }
    });
    app.post('/api/sections', authenticateToken, async (req, res) => {
        const {email} = req.user;
        const {sections} = await perms(email);
        try {
            if (!sections) {
                res.status(403).json({error: "Forbidden"});
                return;
            }
            const response = await sheets.spreadsheets.values.get({
                spreadsheetId: SHEET_ID,
                range: `Dati!A2:C`,
            });
            const {comune, sezione, values} = req.body;
            const rows = response.data.values;
            const index = rows.findIndex((row) => row[0] === comune && row[1] === sezione && eq(row[2], email));
            if (index === -1) {
                res.status(404).json({error: "Not found"});
                console.log(404, email, 'sections.update', comune, sezione);
            } else {
                const response = await sheets.spreadsheets.values.update({
                    spreadsheetId: SHEET_ID,
                    range: `Dati!D${index + 2}:${index + 2}`,
                    valueInputOption: "RAW",
                    resource: {values: [values]},
                });
                res.status(response.status).json({});
                console.log(response.status, email, 'sections.update', comune, sezione);
            }
        } catch (error) {
            console.log(error);
            res.status(500).json({error: error.message});
        }
    });
}
