exports.sectionModule = ({app, authenticateToken, perms, sheets, SHEET_ID}) =>
{
    app.get('/api/sections', authenticateToken, async (req, res) => {
        const {email} = req.user;
        const {sections} = await perms(email);
        try {
            if (!sections) {
                res.status(403).json({error: "Forbidden"});
                return;
            }
            const response = await sheets.spreadsheets.values.get({
                spreadsheetId: SHEET_ID,
                range: `Dati!A2:ZZ`,
            });
            const values = response.data.values
                .filter((row) => row[2] === email);
            res.status(response.status).json({
                rows: values.map((row) => ({
                    comune: row[0],
                    sezione: row[1],
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
            const index = rows.findIndex((row) => row[0] === comune && row[1] === sezione && row[2] === email);
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