const NodeCache = require("node-cache");
const cache = new NodeCache({stdTTL: 60});

// Import and export modules
exports.kpiModule = ({app, authenticateToken, perms, sheets, SHEET_ID}) => {
    app.get('/api/kpi/dati', authenticateToken, async (req, res) => {
        const {kpi} = await perms(req.user.email);
        if (!kpi) {
            res.status(403).json({error: "Forbidden"});
            return;
        }
        if (cache.has('kpi')) {
            console.log('Cache hit', 'kpi');
            res.status(200).json({values: cache.get('kpi')});
            return;
        }
        try {
            const response = await sheets.spreadsheets.values.get({
                spreadsheetId: SHEET_ID,
                range: 'Dati!A2:BZ',
            });
            const kpi = response.data.values.map((row) => ({
                comune: row[0],
                sezione: row[1],
                values: row.slice(3)
            }));
            cache.set('kpi', kpi);
            res.status(response.status).json({values: kpi});
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
        if (cache.has('sezioni')) {
            console.log('Cache hit', 'sezioni');
            res.status(200).json({values: cache.get('sezioni')});
            return;
        }
        try {
            const response = await sheets.spreadsheets.values.get({
                spreadsheetId: SHEET_ID,
                range: 'Sezioni!A2:C',
            });
            const values = response.data.values.map((row) => ({
                comune: row[1],
                sezione: row[0],
                municipio: row[2]
            }));
            cache.set('sezioni', values);
            res.status(response.status).json({values: values});
            console.log(response.status, 'kpi.values');
        } catch (error) {
            res.status(500).json({error: error.message});
            console.log(error);
        }
    });
}