const express = require('express');
const cors = require('cors');
const NodeCache = require('node-cache');
const cache = new NodeCache({ stdTTL: 60 });
const {google} = require('googleapis');
const fs = require('fs');
const {OAuth2Client} = require('google-auth-library');
const {join} = require("path");
const app = express();
const port = process.env.PORT || 3000;
const corsOrigin = process.env.GAE_SERVICE ? `https://${process.env.GAE_SERVICE}.appspot.com` : 'http://localhost:3000';


// Carica le credenziali dell'account di servizio
const credentials = JSON.parse(fs.readFileSync(join(__dirname, 'rdl-europee-2024-dddc509900da.json')));
const SHEET_ID = "1ZbPPXzjIiSq-1J0MjQYYjxY-ZuTwR3tDmCvcYgORabY";

// Configura l'autenticazione JWT
const auth = new google.auth.GoogleAuth({
    credentials,
    scopes: ['https://www.googleapis.com/auth/spreadsheets'],
});

const sheets = google.sheets({version: 'v4', auth});

const CLIENT_ID = "GOOGLE_CLIENT_ID_PLACEHOLDER";
const client = new OAuth2Client(CLIENT_ID);

// Middleware per verificare il token di Google
const authenticateToken = async (req, res, next) => {
    const token = req.headers['authorization'];
    if (!token) {
        console.log("No token: 401");
        return res.sendStatus(401);
    }

    try {
        const ticket = await client.verifyIdToken({
            idToken: token,
            audience: CLIENT_ID,
        });
        req.user = ticket.getPayload();
        next();
    } catch (error) {
        res.sendStatus(403);
    }
};

app.use(cors({
    origin: corsOrigin
}));
app.use(express.json());

// API per ottenere valori da un foglio
app.get('/api/sheets/values', authenticateToken, async (req, res) => {
    const {range} = req.query;
    try {
        const response = await sheets.spreadsheets.values.get({
            spreadsheetId: SHEET_ID,
            range,
        });
        res.status(response.status).json(response.data);
        console.log(response.status, 'get', range);
    } catch (error) {
        res.status(500).json({error: error.message});
        console.log(error);
    }
});

app.get('/api/sections', authenticateToken, async (req, res) => {
    const {email} = req.user;
    const {sections} = await cachedPermissions(email);
    try {
        if (!sections) {
            res.status(403).json({error: "Forbidden"});
            return;
        }
        const response = await sheets.spreadsheets.values.get({
            spreadsheetId: SHEET_ID,
            range: `Dati!A2:AJ`,
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
    const {sections} = await cachedPermissions(email);
    try {
        if (!sections) {
            res.status(403).json({error: "Forbidden"});
            return;
        }
        const response = await sheets.spreadsheets.values.get({
            spreadsheetId: SHEET_ID,
            range: `Dati!A2:AJ`,
        });
        const {comune,sezione,values} = req.body;
        const rows = response.data.values;
        const index = rows.findIndex((row) => row[0] === comune && row[1] === sezione && row[2] === email);
        if (index === -1) {
            res.status(404).json({error: "Not found"});
            console.log(404, email, 'sections.update', comune, sezione);
        } else {
            const response = await sheets.spreadsheets.values.update({
                spreadsheetId: SHEET_ID,
                range: `Dati!D${index + 2}:AJ${index + 2}`,
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

// API per aggiornare valori in un foglio
app.post('/api/sheets/values/update', authenticateToken, async (req, res) => {
    const {range, valueInputOption, values} = req.body;
    try {
        const response = await sheets.spreadsheets.values.update({
            spreadsheetId: SHEET_ID,
            range,
            valueInputOption,
            resource: {values},
        });
        res.status(response.status).json(response.data);
        console.log(response.status, 'update', range);
    } catch (error) {
        res.status(500).json({error: error.message});
        console.log(error);
    }
});

// API per aggiungere valori a un foglio
app.post('/api/sheets/values/append', authenticateToken, async (req, res) => {
    const {range, valueInputOption, values} = req.body;
    console.log(range, valueInputOption, values);
    try {
        const response = await sheets.spreadsheets.values.append({
            spreadsheetId: SHEET_ID,
            range,
            valueInputOption,
            resource: {values},
        });
        res.status(response.status).json(response.data);
        console.log(response.status, 'append', range);
    } catch (error) {
        res.status(500).json({error: error.message});
        console.log(error);
    }
});

async function cachedPermissions(email) {
    const cached = cache.get(email);
    if (cached) {
        console.log('Cache hit', cached);
        return cached;
    }
    const kpi = (await sheets.spreadsheets.values.get({spreadsheetId: SHEET_ID, range: "KPI!A2:A"}))
        .data.values.filter((row) => row[0] === email).length > 0;
    const referenti = (await sheets.spreadsheets.values.get({
        spreadsheetId: SHEET_ID,
        range: "Referenti!A2:A"
    })).data.values.filter((row) => row[0] === email).length > 0;
    const sections = referenti || (await sheets.spreadsheets.values.get({
        spreadsheetId: SHEET_ID,
        range: "Dati!C2:C"
    })).data.values.filter((row) => row[0] === email).length > 0;
    const permissions = {sections, referenti, kpi};
    cache.set(email, permissions);
    return permissions;
}

app.get('/api/permissions', authenticateToken, async (req, res) => {
    const {email} = req.user;
    const permissions = await cachedPermissions(email);
    console.log(200, email, permissions);
    res.status(200).json(permissions);
});

app.use(express.static(join(__dirname, '..', 'build')));
app.get('*', (req, res) => {
    res.sendFile(join(__dirname, '..', 'build', 'index.html'));
});

app.listen(port, () => {
    console.log(`Server running at ${port}`);
});
