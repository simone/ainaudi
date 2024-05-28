const {visible_sections} = require("./query");

exports.rdlModule = ({app, authenticateToken, perms, sheets, SHEET_ID}) =>
{
    app.get('/api/rdl/emails', authenticateToken, async (req, res) => {
        try {
            const email = req.user.email;
            const {referenti} = await perms(email);
            if (!referenti) {
                res.status(403).json({error: "Forbidden"});
                return;
            }
            const sezioni = await visible_sections(sheets, SHEET_ID, email); // comune, sezione
            const assigned = (await sheets.spreadsheets.values.get({
                spreadsheetId: SHEET_ID,
                range: "Dati!A2:C",
            })).data.values.filter((row) => sezioni.some(
                // dati[0]/sezione[1] è il comune, dati[1]/sezione[0] è la sezione
                (sezione) => sezione[0] === row[0] && sezione[1] === row[1] && row[2])
            );
            const emails = new Set(assigned.map((row) => row[2]));
            emails.add(email);
            res.status(200).json({emails: [...emails]});
        } catch (error) {
            res.status(500).json({error: error.message});
            console.log(error);
        }
    });

    app.get('/api/rdl/sections', authenticateToken, async (req, res) => {
        try {
            const email = req.user.email;
            const {referenti} = await perms(email);
            if (!referenti) {
                res.status(403).json({error: "Forbidden"});
                return;
            }
            const sezioni = await visible_sections(sheets, SHEET_ID, email); // comune, sezione
            const assigned = (await sheets.spreadsheets.values.get({
                spreadsheetId: SHEET_ID,
                range: "Dati!A2:C",
            })).data.values.filter((row) => sezioni.some(
                // dati[0]/sezione[1] è il comune, dati[1]/sezione[0] è la sezione
                (sezione) => sezione[0] === row[0] && sezione[1] === row[1] && row[2])
            ).sort((a, b) => a[0] === b[0] ? a[1] - b[1] : a[0].localeCompare(b[0]));
            const unassigned = sezioni.filter((sezione) => !assigned.some(
                // dati[0]/sezione[1] è il comune, dati[1]/sezione[0] è la sezione
                (row) => sezione[0] === row[0] && sezione[1] === row[1])
            ).sort((a, b) => a[0] === b[0] ? a[1] - b[1] : a[0].localeCompare(b[0]));
            res.status(200).json({
                assigned,
                unassigned
            });
        } catch (error) {
            res.status(500).json({error: error.message});
            console.log(error);
        }
    });

    app.post('/api/rdl/assign', authenticateToken, async (req, res) => {
        try {
            let emailRef = req.user.email;
            const {referenti} = await perms(emailRef);
            if (!referenti) {
                res.status(403).json({error: "Forbidden"});
                return;
            }
            const sezioni = await visible_sections(sheets, SHEET_ID, emailRef); // comune, sezione
            const {comune, sezione, email} = req.body;
            if (!sezioni.some((row) => row[0] === comune && row[1] === sezione)) {
                res.status(403).json({error: "Forbidden"});
                return
            }
            const response = await sheets.spreadsheets.values.get({
                spreadsheetId: SHEET_ID,
                range: `Dati!A2:AJ`,
            });
            const rows = response.data.values;
            const index = rows.findIndex((row) => row[0] === comune && row[1] === sezione);
            if (index === -1) {
                // append
                const response = await sheets.spreadsheets.values.append({
                    spreadsheetId: SHEET_ID,
                    range: `Dati!A2`,
                    valueInputOption: "RAW",
                    resource: {values: [[comune, sezione, email]]},
                });
            } else {
                const response = await sheets.spreadsheets.values.update({
                    spreadsheetId: SHEET_ID,
                    range: `Dati!C${index + 2}`,
                    valueInputOption: "RAW",
                    resource: {values: [[email]]},
                });
                res.status(response.status).json({});
                console.log(response.status, 'rdl.assign', comune, sezione, email);
            }
        } catch (error) {
            res.status(500).json({error: error.message});
            console.log(error);
        }
    });

    app.post('/api/rdl/unassign', authenticateToken, async (req, res) => {
        try {
            let emailRef = req.user.email;
            const {referenti} = await perms(emailRef);
            if (!referenti) {
                res.status(403).json({error: "Forbidden"});
                return;
            }
            const sezioni = await visible_sections(sheets, SHEET_ID, emailRef); // comune, sezione
            const {comune, sezione} = req.body;
            if (!sezioni.some((row) => row[0] === comune && row[1] === sezione)) {
                res.status(403).json({error: "Forbidden"});
                return
            }
            const response = await sheets.spreadsheets.values.get({
                spreadsheetId: SHEET_ID,
                range: `Dati!A2:AJ`,
            });
            const rows = response.data.values;
            const index = rows.findIndex((row) => row[0] === comune && row[1] === sezione);
            if (index === -1) {
                res.status(404).json({error: "Not found"});
                console.log(404, 'rdl.unassign', comune, sezione);
            } else {
                const response = await sheets.spreadsheets.values.update({
                    spreadsheetId: SHEET_ID,
                    range: `Dati!C${index + 2}`,
                    valueInputOption: "RAW",
                    resource: {values: [['']]},
                });
                res.status(response.status).json({});
                console.log(response.status, 'rdl.unassign', comune, sezione);
            }
        } catch (error) {
            res.status(500).json({error: error.message});
            console.log(error);
        }
    });

}