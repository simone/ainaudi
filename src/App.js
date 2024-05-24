// App.js
import React, {useState, useEffect} from "react";
import {gapi} from "gapi-script";
import SectionForm from "./SectionForm";
import ReferentiComponent from "./ReferentiComponent";
import KpiComponent from "./KpiComponent";

const CLIENT_ID =
    "GOOGLE_CLIENT_ID_PLACEHOLDER";
const API_KEY = "GOOGLE_API_KEY_PLACEHOLDER";
const SHEET_ID = "1ZbPPXzjIiSq-1J0MjQYYjxY-ZuTwR3tDmCvcYgORabY";
const DISCOVERY_DOCS = ["https://sheets.googleapis.com/$discovery/rest?version=v4"];
const SCOPES = "https://www.googleapis.com/auth/spreadsheets";

function App() {
    const [sections, setSections] = useState([]);
    const [user, setUser] = useState(null);
    const [selectedSection, setSelectedSection] = useState(null);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(true);
    const [referentiData, setReferentiData] = useState([]);
    const [sezioniData, setSezioniData] = useState([]);
    const [activeTab, setActiveTab] = useState('sections');
    const [isKpiAuthorized, setIsKpiAuthorized] = useState(false);
    const [isMenuOpen, setIsMenuOpen] = useState(false);

    useEffect(() => {
        gapi.load("client:auth2", initClient);
    }, []);

    useEffect(() => {
        if (!user) return;
        listSections(user.getEmail());
    }, [user, activeTab]);

    useEffect(() => {
        if (!loading || !user) {
            return;
        }
        // Check if the user is authorized to view KPI data
        if (!isKpiAuthorized && sections.length === 0 && referentiData.length === 0) {
            setError(
                "La tua mail non è autorizzata a utilizzare questa applicazione."
            );
            setTimeout(() => {
                gapi.auth2.getAuthInstance().signOut();
            }, 5000);
        } else {
            setError(null);
        }
    }, [loading, user, sections, referentiData, sezioniData, isKpiAuthorized]);

    const initClient = () => {
        gapi.client
            .init({
                apiKey: API_KEY,
                clientId: CLIENT_ID,
                discoveryDocs: DISCOVERY_DOCS,
                scope: SCOPES,
            })
            .then(() => {
                const authInstance = gapi.auth2.getAuthInstance();
                authInstance.isSignedIn.listen(updateSigninStatus);
                if (updateSigninStatus(authInstance.isSignedIn.get())) {
                    setLoading(true);
                }
            })
            .catch((error) => {
                console.error("Error initializing Google API client:", error);
                setError("Errore durante l'inizializzazione del client Google: " + error.result.message);
                setLoading(false);
            });
    };

    const updateSigninStatus = (isSignedIn) => {
        if (isSignedIn) {
            const user = gapi.auth2.getAuthInstance().currentUser.get();
            setUser(user.getBasicProfile());
            loadReferentiData(user.getBasicProfile().getEmail());
            loadSezioniData();
            checkKpiAuthorization(user.getBasicProfile().getEmail());
            setLoading(false);
        } else {
            setUser(null);
            setLoading(false);
        }
        return isSignedIn;
    };

    const handleAuthClick = () => {
        setIsMenuOpen(false);
        gapi.auth2.getAuthInstance().signIn().catch(error => {
            console.error("Error during sign-in:", error);
            setError("Errore durante il login con Google: " + error.result.message);
        });
    };

    const handleSignoutClick = () => {
        gapi.auth2.getAuthInstance().signOut().catch(error => {
            console.error("Error during sign-out:", error);
            setError("Errore durante il logout da Google: " + error.result.message);
        });
    };

    const checkKpiAuthorization = (email) => {
        gapi.client.sheets.spreadsheets.values.get({
            spreadsheetId: SHEET_ID,
            range: 'KPI!A2:A', // Intervallo della colonna KPI con le email
        }).then(response => {
            const rows = response.result.values;
            if (rows && rows.length > 0) {
                const authorizedEmails = rows.flat();
                setIsKpiAuthorized(authorizedEmails.includes(email));
            }
        }).catch(error => {
            console.error("Error fetching KPI authorization data:", error);
        });
    };

    const listSections = (email) => {
        gapi.client.sheets.spreadsheets.values
            .get({
                spreadsheetId: SHEET_ID,
                range: "Dati!A2:AJ",
            })
            .then((response) => {
                const rows = response.result.values;
                if (rows && rows.length > 0) {
                    const userSections = rows.filter((row) => row[2] === email);
                    setSections(
                        userSections.map((row) => ({
                            comune: row[0],
                            sezione: row[1],
                            email: row[2],
                            nElettoriMaschi: row[3],
                            nElettoriDonne: row[4],
                            schedeRicevute: row[5],
                            schedeAutenticate: row[6],
                            schedeBianche: row[7],
                            schedeNulle: row[8],
                            schedeContestate: row[9],
                            "Morace Carolina": row[10],
                            "Tamburrano Dario": row[11],
                            "Ferrara Gianluca": row[12],
                            "Basile Giovanna": row[13],
                            "Esposito Giusy": row[14],
                            "Fazio Valentina": row[15],
                            "Lauretti Federica": row[16],
                            "Pacetti Giuliano": row[17],
                            "Volpi Stefania": row[18],
                            "Romagnoli Sergio": row[19],
                            "Emiliozzi Mirella": row[20],
                            "Pococacio Valentina": row[21],
                            "Ceccato Emanuele": row[22],
                            "Alloatti Luca": row[23],
                            "Cecere Stefano": row[24],
                            "MOVIMENTO 5 STELLE": row[25],
                            "FRATELLI D'ITALIA": row[26],
                            "FORZA ITALIA-NOI MODERATI": row[27],
                            "LEGA SALVINI PREMIER": row[28],
                            "PARTITO DEMOCRATICO": row[29],
                            "ALLEANZA VERDI E SINISTRA": row[30],
                            "ALTERNATIVA POPOLARE": row[31],
                            "STATI UNITI D'EUROPA": row[32],
                            "DEMOCRAZIA POPOLARE SOVRANA": row[33],
                            "PACE TERRA DIGNITA'": row[34],
                            "AZIONE-SIAMO EUROPEI": row[35],
                        }))
                    );
                }
            })
            .catch((error) => {
                console.error("Error reading Sheet:", error);
                setError("Errore durante la lettura del foglio di calcolo: " + error.result.message);
            });
    };

    const loadReferentiData = (email) => {
        gapi.client.sheets.spreadsheets.values.get({
            spreadsheetId: SHEET_ID,
            range: "Referenti!A2:C",
        }).then((response) => {
            const rows = response.result.values;
            if (rows && rows.length > 0) {
                const referentiSections = rows.filter(row => row[0] === email);
                setReferentiData(referentiSections);
            }
        }).catch(error => {
            console.error("Error fetching referenti data:", error);
        });
    };

    const loadSezioniData = () => {
        gapi.client.sheets.spreadsheets.values.get({
            spreadsheetId: SHEET_ID,
            range: "Sezioni!A2:C",
        }).then((response) => {
            const rows = response.result.values;
            if (rows && rows.length > 0) {
                setSezioniData(rows);
            }
        }).catch(error => {
            console.error("Error fetching sezioni data:", error);
        });
    };

    const findIndexByComuneSezione = (comune, sezione, data) => {
        return data.findIndex(row => row[0] === comune && row[1] === sezione);
    };


    const updateSection = (newData) => {
        gapi.client.sheets.spreadsheets.values
            .get({
                spreadsheetId: SHEET_ID,
                range: "Dati!A2:C", // Supponiamo che le colonne A, B e C siano comune, sezione ed email
            })
            .then((response) => {
                const data = response.result.values;
                const correctIndex = findIndexByComuneSezione(newData.comune, newData.sezione, data);
                if (correctIndex !== -1) {
                    const range = `Dati!A${correctIndex + 2}:AJ${correctIndex + 2}`; // Supponendo che l'indice inizi da 0 e il foglio abbia intestazioni
                    gapi.client.sheets.spreadsheets.values
                        .update({
                            spreadsheetId: SHEET_ID,
                            range: range,
                            valueInputOption: "RAW",
                            resource: {
                                values: [
                                    [
                                        newData.comune,
                                        newData.sezione,
                                        newData.email,
                                        newData.nElettoriMaschi,
                                        newData.nElettoriDonne,
                                        newData.schedeRicevute,
                                        newData.schedeAutenticate,
                                        newData.schedeBianche,
                                        newData.schedeNulle,
                                        newData.schedeContestate,
                                        newData["Morace Carolina"],
                                        newData["Tamburrano Dario"],
                                        newData["Ferrara Gianluca"],
                                        newData["Basile Giovanna"],
                                        newData["Esposito Giusy"],
                                        newData["Fazio Valentina"],
                                        newData["Lauretti Federica"],
                                        newData["Pacetti Giuliano"],
                                        newData["Volpi Stefania"],
                                        newData["Romagnoli Sergio"],
                                        newData["Emiliozzi Mirella"],
                                        newData["Pococacio Valentina"],
                                        newData["Ceccato Emanuele"],
                                        newData["Alloatti Luca"],
                                        newData["Cecere Stefano"],
                                        newData["MOVIMENTO 5 STELLE"],
                                        newData["FRATELLI D'ITALIA"],
                                        newData["FORZA ITALIA-NOI MODERATI"],
                                        newData["LEGA SALVINI PREMIER"],
                                        newData["PARTITO DEMOCRATICO"],
                                        newData["ALLEANZA VERDI E SINISTRA"],
                                        newData["ALTERNATIVA POPOLARE"],
                                        newData["STATI UNITI D'EUROPA"],
                                        newData["DEMOCRAZIA POPOLARE SOVRANA"],
                                        newData["PACE TERRA DIGNITA'"],
                                        newData["AZIONE-SIAMO EUROPEI"],
                                    ],
                                ],
                            },
                        })
                        .then((response) => {
                            listSections(user.getEmail());
                            setSelectedSection(null);
                        })
                        .catch((error) => {
                            console.error("Error updating Sheet:", error);
                            setError("Errore durante l'aggiornamento del foglio di calcolo: " + error.result.message);
                        });
                } else {
                    console.error("Record not found for update");
                    setError("Errore: record non trovato per l'aggiornamento");
                }
            })
            .catch((error) => {
                console.error("Error reading Sheet:", error);
                setError("Errore durante la lettura del foglio di calcolo: " + error.result.message);
            });
    };

    const toggleMenu = () => {
        setIsMenuOpen(!isMenuOpen);
    };

    const activate = (tab) => {
        setActiveTab(tab);
        setIsMenuOpen(false);
    }

    const isComplete = (section) => {
        // Verifica che tutti i valori della section sono valorizzati
        for (let key in section) {
            if (section[key] === null || section[key] === undefined || section[key] === '') {
                return false;
            }
        }
        return true;
    };

    const progress = (section) => {
        // Numero totale di proprietà nell'oggetto section
        const totalProperties = Object.keys(section).length;
        // Numero di proprietà valorizzate
        let filledProperties = 0;

        // Itera su tutte le proprietà dell'oggetto section
        for (let key in section) {
            if (section[key] !== null && section[key] !== undefined && section[key] !== '') {
                filledProperties++;
            }
        }

        // Calcola la percentuale di completamento
        const progressPercentage = (filledProperties / totalProperties) * 100;

        return Math.round(progressPercentage);
    };


    if (loading || (!user && !sections)) {
        return <div className="alert alert-info mt-3">Loading</div>;
    }

    return (
        <>
            <nav className="navbar navbar-expand-lg navbar-dark bg-dark fixed-top">
                <div className="container-fluid">
                    <a className="navbar-brand" href="#">ELEZIONI EUROPEE 2024</a>
                    {user && (
                        <>
                            <button className={`navbar-toggler ${isMenuOpen ? 'collapsed' : ''}`} type="button" onClick={toggleMenu} aria-controls="navbarNav" aria-expanded={isMenuOpen} aria-label="Toggle navigation">
                                <span className="navbar-toggler-icon"></span>
                            </button>
                            <div className={`collapse navbar-collapse ${isMenuOpen ? 'show' : ''}`} id="navbarNav">
                                <ul className="navbar-nav me-auto mb-2 mb-lg-0">
                                    <li className="nav-item">
                                        <a className={`nav-link ${activeTab === 'sections' ? 'active' : ''}`}
                                           onClick={() => activate('sections')} href="#">Sezioni</a>
                                    </li>
                                    {referentiData.length > 0 && (
                                        <li className="nav-item">
                                            <a className={`nav-link ${activeTab === 'referenti' ? 'active' : ''}`}
                                               onClick={() => activate('referenti')} href="#">Assegna RDL</a>
                                        </li>
                                    )}
                                    {isKpiAuthorized && (
                                        <li className="nav-item">
                                            <a className={`nav-link ${activeTab === 'kpi' ? 'active' : ''}`}
                                               onClick={() => activate('kpi')} href="#">KPI</a>
                                        </li>
                                    )}
                                </ul>
                                <div className="d-flex align-items-center">
                                    <p className="text-light me-3 mb-0">{user.getName()}</p>
                                    <button className="btn btn-danger" onClick={handleSignoutClick}>Esci</button>
                                </div>
                            </div>

                        </>
                    )}
                </div>
            </nav>
            <h3 className="alert alert-primary">CIRCOSCRIZIONE ITALIA CENTRALE<br/>ROMA e PROVINCIA</h3>
            {error && <div className="alert alert-danger mt-3">{error}</div>}
            {user ? (
                <div>
                    <div className="tab-content">
                        {activeTab === 'sections' && (
                            <div className="tab-pane active">
                                {!selectedSection ? (
                                    <div className="card">
                                        <div className="card-header bg-info">
                                            Questa applicazione è destinata agli RDL del Movimento 5 Stelle e
                                            serve per inviare al movimento i dati raccolti nelle sezioni. Si
                                            prega di scegliere una delle sezioni assegnate e di compilare
                                            tutti i campi richiesti con i numeri corretti.
                                        </div>
                                        {sections.length>0 ? (
                                            <div className="card-body">
                                                <h2>Scegli una sezione assegnata a te</h2>
                                                <ul className="list-group">
                                                    {sections.map((section, index) => (
                                                        <li
                                                            className="list-group-item d-flex justify-content-between align-items-center"
                                                            key={index}
                                                        >
                                                            {section.comune} - {section.sezione}
                                                            {isComplete(section) ? (
                                                                <button
                                                                    className="btn btn-success"
                                                                    onClick={() => {
                                                                        setSelectedSection(section);
                                                                    }}
                                                                >
                                                                    Completo
                                                                </button>
                                                            ) : (
                                                                <button
                                                                    className="btn btn-primary"
                                                                    onClick={() => {
                                                                        setSelectedSection(section);
                                                                    }}
                                                                >
                                                                    Apri {progress(section)}%
                                                                </button>
                                                            )}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                            ) : (
                                        <div className="card-footer">
                                            <h2>Non vedi la tua sezione?</h2>
                                            <p className="bg-warning">
                                                Se non vedi la tua sezione, contatta il Referente RDL della tua Zona.
                                            </p>
                                        </div>
                                            )}
                                    </div>
                                ) : (
                                    <>
                                        <div className="card">
                                            <div className="card-header bg-info">
                                                Compila tutti i campi richiesti con i dati corretti e salva. Verifica che i
                                                numeri inseriti siano accurati prima di inviare.
                                            </div>
                                        </div>
                                        <SectionForm
                                            section={selectedSection}
                                            updateSection={updateSection}
                                            cancel={()=>setSelectedSection(null)}
                                        />
                                    </>
                                )}
                            </div>
                        )}
                        {activeTab === 'referenti' && (
                            <div className="tab-pane active">
                                <div className="card">
                                    <div className="card-header bg-info">
                                        Assegna un RDL a ciascuna sezione inserendo l'email del responsabile. Assicurati che
                                        ogni sezione abbia un RDL e aggiorna le assegnazioni se necessario.
                                    </div>
                                </div>
                                <ReferentiComponent
                                    email={user.getEmail()}
                                    referentiData={referentiData}
                                    sezioniData={sezioniData}
                                    sheet={SHEET_ID}
                                />
                            </div>
                        )}
                        {activeTab === 'kpi' && (
                            <div className="tab-pane active">
                                <div className="card">
                                    <div className="card-header bg-info">
                                        Visualizza i grafici delle performance elettorali nella sezione KPI. Analizza i dati
                                        per le preferenze dei candidati e i voti di lista per valutare l'andamento
                                        elettorale.
                                    </div>
                                </div>
                                <KpiComponent
                                    sheet={SHEET_ID}
                                />
                            </div>
                        )}
                    </div>
                </div>
            ) : (
                <div className="card">
                    <div className="card-header bg-warning">
                        Autenticarsi utilizzando l'email fornita come RDL.
                    </div>
                      <div className="card-footer d-flex align-items-center justify-content-center" style={{ minHeight: '50vh' }}>
                        <div className="row w-100">
                            <div className="col-12">
                                <button className="btn btn-primary btn-lg w-100" onClick={handleAuthClick}>
                                    Login con Google
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}

export default App;
