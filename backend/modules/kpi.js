exports.kpiModule = ({app, authenticateToken, perms, sheets, SHEET_ID}) =>
{
    app.get('/api/kpi/dati', authenticateToken, async (req, res) => {
        const {kpi} = await perms(req.user.email);
        if (!kpi) {
            res.status(403).json({error: "Forbidden"});
            return;
        }
        try {
            const response = await sheets.spreadsheets.values.get({
                spreadsheetId: SHEET_ID,
                range: 'Dati!A2:AJ',
            });
            res.status(response.status).json({ values: response.data.values.map((row) => ({
                comune: row[0],
                sezione: row[1],
                values: row.slice(3)
            }))});
            console.log(response.status, 'kpi.values');
        } catch (error) {
            res.status(500).json({error: error.message});
            console.log(error);
        }
    });

    app.get('/api/kpi/sezioni', authenticateToken, async (req, res) => {
        const {kpi} = await perms(req.user.email);
        if (!kpi) {
            res.status(403).json({error: "Forbidden"});
            return;
        }
        try {
            const response = await sheets.spreadsheets.values.get({
                spreadsheetId: SHEET_ID,
                range: 'Sezioni!A2:C',
            });
            res.status(response.status).json({values: response.data.values.map((row) => ({
                comune: row[1],
                sezione: row[0],
                municipio: row[2]
            }))});
            console.log(response.status, 'kpi.values');
        } catch (error) {
            res.status(500).json({error: error.message});
            console.log(error);
        }
    });
}