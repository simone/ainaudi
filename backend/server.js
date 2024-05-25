const express = require('express');
const cors = require('cors');
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

app.use(express.static(join(__dirname, '..', 'build')));
app.get('*', (req, res) => {
    res.sendFile(join(__dirname, '..', 'build', 'index.html'));
});

app.listen(port, () => {
    console.log(`Server running at ${port}`);
});
