const express = require('express');
const rateLimit = require('express-rate-limit');
const cors = require('cors');
const NodeCache = require('node-cache');
const cache = new NodeCache({stdTTL: 60});
const {google} = require('googleapis');
const fs = require('fs');
const {OAuth2Client} = require('google-auth-library');
const {join} = require("path");
const app = express();
const port = process.env.PORT || 3000;
const corsOrigin = process.env.GAE_SERVICE ? `https://${process.env.GAE_SERVICE}.appspot.com` : 'http://localhost:3000';

const {sectionModule} = require('./modules/section');
const {rdlModule} = require('./modules/rdl');
const {kpiModule} = require('./modules/kpi');
const {reactModule} = require("./modules/react");
const {electionModule} = require("./modules/election");
const {eq} = require("./tools");

// Carica le credenziali dell'account di servizio
const credentials = JSON.parse(fs.readFileSync(join(__dirname, 'rdl-europee-2024-dddc509900da.json')));
const SHEET_ID = "1ZbPPXzjIiSq-1J0MjQYYjxY-ZuTwR3tDmCvcYgORabY";

// Configura il rate limiting
const limiter = rateLimit({
    windowMs: 60 * 1000,
    max: 60,
    message: 'Troppe richieste, riprova tra un minuto.'
});

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
        console.log("Invalid token: 403", error);
        res.sendStatus(403);
    }
};

app.use(cors({
    origin: corsOrigin
}));
app.use('/api/', limiter);
app.use(express.json());
app.use(express.urlencoded({extended: false}));

async function perms(email) {
    const cached = cache.get(email);
    if (cached) {
        console.log('Cache hit', email, cached);
        return cached;
    }
    const kpi = (await sheets.spreadsheets.values.get({spreadsheetId: SHEET_ID, range: "KPI!A2:A"}))
        .data.values.filter((row) => eq(row[0], email)).length > 0;
    const referenti = (await sheets.spreadsheets.values.get({
        spreadsheetId: SHEET_ID,
        range: "Referenti!A2:A"
    })).data.values.filter((row) => eq(row[0], email)).length > 0;
    const sections = referenti || (await sheets.spreadsheets.values.get({
        spreadsheetId: SHEET_ID,
        range: "Dati!C2:C"
    })).data.values.filter((row) => eq(row[0], email)).length > 0;
    const permissions = {sections, referenti, kpi};
    cache.set(email, permissions);
    return permissions;
}

app.get('/api/permissions', authenticateToken, async (req, res) => {
    const {email} = req.user;
    const permissions = await perms(email);
    console.log(200, email, permissions);
    res.status(200).json(permissions);
});

electionModule({
    app, authenticateToken, perms, sheets, SHEET_ID
});

// api for manage sections
sectionModule({
    app, authenticateToken, perms, sheets, SHEET_ID
});

// api to manage RDL
rdlModule({
    app, authenticateToken, perms, sheets, SHEET_ID
});

// api to see KPI
kpiModule({
    app, authenticateToken, perms, sheets, SHEET_ID
});

reactModule({
    app
});

app.listen(port, () => {
    console.log(`Server running at ${port}`);
});
