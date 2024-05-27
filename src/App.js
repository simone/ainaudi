// App.js
import React, {useState, useEffect} from "react";
import {gapi} from "gapi-script";
import RdlList from "./RdlList";
import Kpi from "./Kpi";
import Client from "./Client";
import SectionList from "./SectionList";
import logo from './assets/logo-m5s.png';

const CLIENT_ID = "GOOGLE_CLIENT_ID_PLACEHOLDER";
const API_KEY = "GOOGLE_API_KEY_PLACEHOLDER";
const SCOPES = "https://www.googleapis.com/auth/userinfo.email";
const SERVER = process.env.NODE_ENV === 'development' ? process.env.REACT_APP_API_URL : '';

function App() {
    const [client, setClient] = useState(null);
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [activeTab, setActiveTab] = useState(null);
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const [permissions, setPermissions] = useState({
        sections: false,
        referenti: false,
        kpi: false
    });

    useEffect(() => {
        gapi.load("client:auth2", initClient);
    }, []);

    const initClient = () => {
        console.log("Initializing Google API client");
        gapi.client
            .init({
                apiKey: API_KEY,
                clientId: CLIENT_ID,
                scope: SCOPES,
            })
            .then(() => {
                console.log("Google API client initialized");
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
            console.log("User is signed in");
            const authInstance = gapi.auth2.getAuthInstance();
            const user = authInstance.currentUser.get();
            const response = user.getAuthResponse();
            const client = Client(SERVER, response.id_token);
            client.permissions().then((permissions) => {
                setPermissions(permissions);
                if (!permissions.sections && !permissions.referenti && !permissions.kpi) {
                    setError("Non hai i permessi per accedere a nessuna sezione");
                    setTimeout(() => {
                        setClient(null);
                        setUser(null);
                        gapi.auth2.getAuthInstance().signOut();
                        setError(null);
                        setLoading(false)
                    }, 1000);
                } else {
                    if (permissions.sections) {
                        setActiveTab('sections');
                    } else if (permissions.referenti) {
                        setActiveTab('referenti');
                    } else if (permissions.kpi) {
                        setActiveTab('kpi');
                    }
                    setClient(client);
                    setUser(user.getBasicProfile());
                    setLoading(false)
                    console.log("Token expires in", Math.floor(response.expires_in / 60), "minutes");
                    setInterval(async () => {
                        console.log("Reloading auth response");
                        const newAuthResponse = await user.reloadAuthResponse();
                        setClient(Client(SERVER, newAuthResponse.id_token));
                    }, (response.expires_in - 60) * 1000);
                }
            });
        } else {
            console.log("User is not signed in");
            setClient(null);
            setLoading(false)
        }
        return isSignedIn;
    };

    const handleAuthClick = () => {
        setIsMenuOpen(false);
        setLoading(true)
        gapi.auth2.getAuthInstance().signIn().catch(error => {
            console.error("Error during sign-in:", error);
            setError("Errore durante il login con Google: " + error.result.message);
            setLoading(false)
        });
    };

    const handleSignoutClick = () => {
        setLoading(false)
        gapi.auth2.getAuthInstance().signOut().catch(error => {
            console.error("Error during sign-out:", error);
            setError("Errore durante il logout da Google: " + error.result.message);
        });
    };

    const toggleMenu = () => {
        setIsMenuOpen(!isMenuOpen);
    };

    const activate = (tab) => {
        setActiveTab(tab);
        setIsMenuOpen(false);
    }

    return (
        <div id="root">
            <div className="main-content">
                <nav className="navbar navbar-expand-lg navbar-dark bg-dark fixed-top">
                    <div className="container-fluid">
                        <a className="navbar-brand" href="#">ELEZIONI EUROPEE 2024</a>
                        {client && (
                            <>
                                <button className={`navbar-toggler ${isMenuOpen ? 'collapsed' : ''}`}
                                        type="button"
                                        onClick={toggleMenu}
                                        aria-controls="navbarNav"
                                        aria-expanded={isMenuOpen}
                                        aria-label="Toggle navigation">
                                    <span className="navbar-toggler-icon"></span>
                                </button>
                                <div className={`collapse navbar-collapse ${isMenuOpen ? 'show' : ''}`} id="navbarNav">
                                    <ul className="navbar-nav me-auto mb-2 mb-lg-0">
                                        {permissions.sections && (
                                            <li className="nav-item">
                                                <a className={`nav-link ${activeTab === 'sections' ? 'active' : ''}`}
                                                   onClick={() => activate('sections')} href="#">Sezioni</a>
                                            </li>
                                        )}
                                        {permissions.referenti && (
                                            <li className="nav-item">
                                                <a className={`nav-link ${activeTab === 'referenti' ? 'active' : ''}`}
                                                   onClick={() => activate('referenti')} href="#">Assegna RDL</a>
                                            </li>
                                        )}
                                        {permissions.kpi && (
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
                <h3 className="alert alert-primary">CIRCOSCRIZIONE ITALIA CENTRALE<br/>ROMA</h3>
                {error && <div className="alert alert-danger mt-3">{error}</div>}
                {client ? (
                    <div>
                        <div className="tab-content">
                            {activeTab === 'sections' && permissions.sections && (
                                <div className="tab-pane active">
                                    <SectionList
                                        user={user}
                                        client={client}
                                        setError={setError}
                                    />
                                </div>
                            )}
                            {activeTab === 'referenti' && permissions.referenti && (
                                <div className="tab-pane active">
                                    <RdlList
                                        client={client}
                                        setError={setError}
                                    />
                                </div>
                            )}
                            {activeTab === 'kpi' && permissions.kpi && (
                                <div className="tab-pane active">
                                    <Kpi
                                        client={client}
                                        setError={setError}
                                    />
                                </div>
                            )}
                        </div>
                    </div>
                ) : (
                    <div className="card">
                        {loading && (
                            <div className="card-body d-flex align-items-center justify-content-center"
                                 style={{minHeight: '50vh'}}>
                                <div className="spinner-border text-primary" role="status">
                                    <span className="visually-hidden">Loading...</span>
                                </div>
                            </div>
                        )}
                        {!loading && (
                            <>
                                <div className="card-header bg-warning">
                                    Autenticarsi utilizzando l'email fornita come RDL.
                                </div>

                                <div className="card-footer d-flex align-items-center justify-content-center"
                                     style={{minHeight: '50vh'}}>
                                    <div className="row w-100">
                                        <div className="col-12">
                                            <button className="btn btn-primary btn-lg w-100" onClick={handleAuthClick}>
                                                Login con Google
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </>
                        )}
                    </div>
                )}
            </div>
            <footer className="custom-footer">
                <div className="footer-logo">
                    <img src={logo} alt="Movimento 5 Stelle" style={{
                        width: '100%',
                    }} />
                </div>
                <div className="footer-text">
                    <p>
                        Proprietà del MOVIMENTO 5 STELLE<br/>Realizzato dal Gruppo Territoriale ROMA XV
                    </p>
                </div>
            </footer>
        </div>
    );
}

export default App;
