exports.electionModule = ({app, authenticateToken, perms, sheets, SHEET_ID}) => {
    app.get('/api/election/lists', authenticateToken, async (req, res) => {
        const {email} = req.user;
        const {sections, kpi} = await perms(email);
        if (!sections && !kpi) {
            res.status(403).json({error: "Forbidden"});
            return;
        }
        try {
            const lists = (await sheets.spreadsheets.values.get({
                spreadsheetId: SHEET_ID,
                range: "Liste!A2:B"
            })).data.values;
            res.status(200).json({values: lists});
            console.log(200, 'election.lists');
        } catch (error) {
            res.status(500).json({error: error.message});
            console.log(error);
        }
    });

    app.get('/api/election/candidates', authenticateToken, async (req, res) => {
        const {email} = req.user;
        const {sections, kpi} = await perms(email);
        if (!sections && !kpi) {
            res.status(403).json({error: "Forbidden"});
            return;
        }
        try {
            const candidates = (await sheets.spreadsheets.values.get({
                spreadsheetId: SHEET_ID,
                range: "Candidati!A2:A"
            })).data.values;
            res.status(200).json({values: candidates});
            console.log(200, 'election.candidates');
        } catch (error) {
            res.status(500).json({error: error.message});
            console.log(error);
        }
    });
}