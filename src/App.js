// App.js
import React, {useState, useEffect, useMemo} from "react";
import RdlList from "./RdlList";
import Mappatura from "./Mappatura";
import Kpi from "./Kpi";
import Client, {clearCache} from "./Client";
import SectionList from "./SectionList";
import logo from './assets/logo-m5s.png';
import GeneraModuli from "./GeneraModuli";
import GestioneSezioni from "./GestioneSezioni";
import EmailAutocomplete from "./EmailAutocomplete";
import RdlSelfRegistration from "./RdlSelfRegistration";
import GestioneRdl from "./GestioneRdl";
import GestioneDeleghe from "./GestioneDeleghe";
import Risorse from "./Risorse";
import Dashboard from "./Dashboard";
import {AuthProvider, useAuth} from "./AuthContext";

const SERVER_API = process.env.NODE_ENV === 'development' ? process.env.REACT_APP_API_URL : '';
const SERVER_PDF = process.env.NODE_ENV === 'development' ? process.env.REACT_APP_PDF_URL : '';

function AppContent() {
    const {user, accessToken, isAuthenticated, requestMagicLink, verifyMagicLink, logout, loading: authLoading, error: authError, impersonate, isImpersonating, originalUser, stopImpersonating} = useAuth();

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [activeTab, setActiveTab] = useState(null);
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const [permissions, setPermissions] = useState({
        sections: false,
        referenti: false,
        kpi: false,
        gestione_rdl: false
    });
    const [showRdlRegistration, setShowRdlRegistration] = useState(false);
    const [pdf, setPdf] = useState(false);
    const [isGestioneDropdownOpen, setIsGestioneDropdownOpen] = useState(false);
    const [isDelegheDropdownOpen, setIsDelegheDropdownOpen] = useState(false);
    const [magicLinkEmail, setMagicLinkEmail] = useState(() => {
        return localStorage.getItem('rdl_magic_link_email') || '';
    });
    const [magicLinkSent, setMagicLinkSent] = useState(false);
    const [consultazione, setConsultazione] = useState(null);
    const [consultazioneLoaded, setConsultazioneLoaded] = useState(false);
    const [hasContributions, setHasContributions] = useState(false);
    const [impersonateEmail, setImpersonateEmail] = useState('');
    const [showImpersonate, setShowImpersonate] = useState(false);
    const [impersonateEmails, setImpersonateEmails] = useState([]);

    // Create client when we have a token
    const client = useMemo(() => {
        if (accessToken) {
            return Client(SERVER_API, SERVER_PDF, accessToken);
        }
        return null;
    }, [accessToken]);

    // Check for magic link token in URL
    useEffect(() => {
        const urlParams = new URLSearchParams(window.location.search);
        const token = urlParams.get('token');

        if (token && !isAuthenticated) {
            console.log("Magic link token found, verifying...");
            setLoading(true);
            verifyMagicLink(token)
                .then(() => {
                    // Clear the URL parameter
                    window.history.replaceState({}, document.title, window.location.pathname);
                    setLoading(false);
                })
                .catch((err) => {
                    setError(`Errore verifica magic link: ${err.message}`);
                    window.history.replaceState({}, document.title, window.location.pathname);
                    setLoading(false);
                });
        }
    }, [isAuthenticated, verifyMagicLink]);

    // Load permissions when authenticated
    useEffect(() => {
        if (client && isAuthenticated) {
            client.permissions().then((perms) => {
                if (perms.error) {
                    setError(`Errore nel caricamento permessi: ${perms.error}`);
                    return;
                }
                setPermissions(perms);
                if (!perms.sections && !perms.referenti && !perms.kpi) {
                    setError(`La mail ${user.email} non ha permessi per accedere ad alcuna sezione`);
                    setTimeout(() => {
                        handleSignoutClick();
                    }, 2000);
                } else {
                    // Show dashboard by default
                    setActiveTab('dashboard');
                }
            });
        }
    }, [client, isAuthenticated, user]);

    // Check PDF permission
    useEffect(() => {
        if (user) {
            setPdf(user.email === 's.federici@gmail.com')
        }
    }, [user])

    // Load active consultazione
    useEffect(() => {
        if (client && isAuthenticated) {
            client.election.consultazioneAttiva().then(data => {
                if (!data.error && data.id) {
                    setConsultazione(data);
                }
                setConsultazioneLoaded(true);
            }).catch(() => {
                setConsultazioneLoaded(true);
            });
        }
    }, [client, isAuthenticated]);

    // Show auth errors
    useEffect(() => {
        if (authError) {
            setError(authError);
        }
    }, [authError]);

    // Check for contributions (to enable "Diretta")
    useEffect(() => {
        if (client && isAuthenticated && permissions.kpi && consultazione) {
            const checkContributions = () => {
                client.kpi.hasContributions?.().then(data => {
                    if (data && !data.error) {
                        setHasContributions(data.has_contributions || false);
                    }
                }).catch(() => {
                    // API not available, check via dati
                    client.kpi.dati?.().then(data => {
                        if (data?.values && Array.isArray(data.values)) {
                            // Has contributions if any row has data
                            const hasData = data.values.some(row =>
                                row.values && row.values.some(v => v !== '' && v !== null && v !== undefined)
                            );
                            setHasContributions(hasData);
                        }
                    }).catch(() => {});
                });
            };

            checkContributions();
            // Check every 60 seconds
            const interval = setInterval(checkContributions, 60000);
            return () => clearInterval(interval);
        }
    }, [client, isAuthenticated, permissions.kpi, consultazione]);

    const handleImpersonate = async (e) => {
        e.preventDefault();
        if (!impersonateEmail) return;

        try {
            await impersonate(impersonateEmail);
            setShowImpersonate(false);
            setImpersonateEmail('');
            // Reset state to reload with new user
            setConsultazione(null);
            setConsultazioneLoaded(false);
            setPermissions({sections: false, referenti: false, kpi: false, gestione_rdl: false});
            setActiveTab(null);
            clearCache();
        } catch (err) {
            setError(`Errore impersonation: ${err.message}`);
        }
    };

    const handleStopImpersonating = () => {
        stopImpersonating();
        // Reset state to reload with original user
        setConsultazione(null);
        setConsultazioneLoaded(false);
        setPermissions({sections: false, referenti: false, kpi: false, upload_sezioni: false, gestione_rdl: false});
        setActiveTab(null);
        clearCache();
    };

    // Search users for impersonate autocomplete
    const handleImpersonateEmailChange = async (value) => {
        setImpersonateEmail(value);
        if (client && value && value.length >= 2) {
            const result = await client.users.search(value);
            setImpersonateEmails(result.emails || []);
        } else {
            setImpersonateEmails([]);
        }
    };

    const handleSignoutClick = () => {
        setLoading(false);
        clearCache();
        logout();
        setPermissions({sections: false, referenti: false, kpi: false, upload_sezioni: false, gestione_rdl: false});
        setActiveTab(null);
        setShowRdlRegistration(false);
        setConsultazione(null);
        setConsultazioneLoaded(false);
    };

    const toggleMenu = () => {
        setIsMenuOpen(!isMenuOpen);
        if (isMenuOpen) {
            setIsGestioneDropdownOpen(false);
        }
    };

    // Close dropdowns when clicking outside
    useEffect(() => {
        const handleClickOutside = (e) => {
            if (!e.target.closest('.dropdown')) {
                setIsGestioneDropdownOpen(false);
                setIsDelegheDropdownOpen(false);
            }
        };
        document.addEventListener('click', handleClickOutside);
        return () => document.removeEventListener('click', handleClickOutside);
    }, [isGestioneDropdownOpen, isDelegheDropdownOpen]);

    const activate = (tab) => {
        setActiveTab(tab);
        setIsMenuOpen(false);
    };

    const handleMagicLinkSubmit = async (e) => {
        e.preventDefault();
        if (!magicLinkEmail) return;

        setLoading(true);
        setError(null);

        try {
            await requestMagicLink(magicLinkEmail);
            localStorage.setItem('rdl_magic_link_email', magicLinkEmail);
            setMagicLinkSent(true);
            setLoading(false);
        } catch (err) {
            setError(`Errore invio magic link: ${err.message}`);
            setLoading(false);
        }
    };

    const isLoading = loading || authLoading;
    const displayName = user?.display_name || user?.email || '';

    return (
        <>
            <div className="main-content">
                <nav className="navbar navbar-expand-lg navbar-dark bg-dark fixed-top">
                    <div className="container-fluid">
                        <a className="navbar-brand" href="#" onClick={(e) => { e.preventDefault(); activate('dashboard'); }}>
                            RDL 5 Stelle <span style={{color: '#e9d483'}}>★★★★★</span>
                        </a>
                        {isAuthenticated && client && (
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
                                        {/* 0. Home/Dashboard */}
                                        <li className="nav-item">
                                            <a className={`nav-link ${activeTab === 'dashboard' ? 'active' : ''}`}
                                               onClick={() => activate('dashboard')} href="#">
                                                <i className="fas fa-home me-1"></i>
                                                Home
                                            </a>
                                        </li>
                                        {/* 1. Dropdown RDL (area SubDelegato) */}
                                        {(permissions.referenti || permissions.gestione_rdl) && (
                                            <li className="nav-item dropdown">
                                                <a className={`nav-link dropdown-toggle ${['sezioni', 'gestione_rdl', 'designazione'].includes(activeTab) ? 'active' : ''}`}
                                                   href="#"
                                                   role="button"
                                                   onClick={(e) => { e.preventDefault(); setIsGestioneDropdownOpen(!isGestioneDropdownOpen); setIsDelegheDropdownOpen(false); }}
                                                   aria-expanded={isGestioneDropdownOpen}>
                                                    RDL
                                                </a>
                                                <ul className={`dropdown-menu dropdown-menu-dark ${isGestioneDropdownOpen ? 'show' : ''}`}>
                                                    {permissions.referenti && (
                                                        <li>
                                                            <a className={`dropdown-item ${activeTab === 'sezioni' ? 'active' : ''}`}
                                                               onClick={() => { activate('sezioni'); setIsGestioneDropdownOpen(false); }} href="#">
                                                                <i className="fas fa-map-marker-alt me-2"></i>
                                                                Gestione Sezioni
                                                            </a>
                                                        </li>
                                                    )}
                                                    {permissions.gestione_rdl && (
                                                        <li>
                                                            <a className={`dropdown-item ${activeTab === 'gestione_rdl' ? 'active' : ''}`}
                                                               onClick={() => { activate('gestione_rdl'); setIsGestioneDropdownOpen(false); }} href="#">
                                                                <i className="fas fa-user-check me-2"></i>
                                                                Gestione RDL
                                                            </a>
                                                        </li>
                                                    )}
                                                    {consultazione && permissions.referenti && (
                                                        <li>
                                                            <a className={`dropdown-item ${activeTab === 'designazione' ? 'active' : ''}`}
                                                               onClick={() => { activate('designazione'); setIsGestioneDropdownOpen(false); }} href="#">
                                                                <i className="fas fa-map-marker-alt me-2"></i>
                                                                Mappatura
                                                            </a>
                                                        </li>
                                                    )}
                                                </ul>
                                            </li>
                                        )}
                                        {/* 2. Dropdown Delegati (area Delegato) */}
                                        {(permissions.referenti || pdf) && (
                                            <li className="nav-item dropdown">
                                                <a className={`nav-link dropdown-toggle ${['deleghe', 'pdf'].includes(activeTab) ? 'active' : ''}`}
                                                   href="#"
                                                   role="button"
                                                   onClick={(e) => { e.preventDefault(); setIsDelegheDropdownOpen(!isDelegheDropdownOpen); setIsGestioneDropdownOpen(false); }}
                                                   aria-expanded={isDelegheDropdownOpen}>
                                                    Delegati
                                                </a>
                                                <ul className={`dropdown-menu dropdown-menu-dark ${isDelegheDropdownOpen ? 'show' : ''}`}>
                                                    {permissions.referenti && (
                                                        <li>
                                                            <a className={`dropdown-item ${activeTab === 'deleghe' ? 'active' : ''}`}
                                                               onClick={() => { activate('deleghe'); setIsDelegheDropdownOpen(false); }} href="#">
                                                                <i className="fas fa-link me-2"></i>
                                                                Catena Deleghe
                                                            </a>
                                                        </li>
                                                    )}
                                                    {consultazione && pdf && (
                                                        <li>
                                                            <a className={`dropdown-item ${activeTab === 'pdf' ? 'active' : ''}`}
                                                               onClick={() => { activate('pdf'); setIsDelegheDropdownOpen(false); }} href="#">
                                                                <i className="fas fa-print me-2"></i>
                                                                Stampa Designazioni
                                                            </a>
                                                        </li>
                                                    )}
                                                </ul>
                                            </li>
                                        )}
                                        {/* 3. Scrutinio */}
                                        {consultazione && permissions.sections && (
                                            <li className="nav-item">
                                                <a className={`nav-link ${activeTab === 'sections' ? 'active' : ''}`}
                                                   onClick={() => activate('sections')} href="#">Scrutinio</a>
                                            </li>
                                        )}
                                        {/* 4. Diretta (KPI) - visibile solo quando ci sono contributi */}
                                        {consultazione && permissions.kpi && hasContributions && (
                                            <li className="nav-item">
                                                <a className={`nav-link ${activeTab === 'kpi' ? 'active' : ''}`}
                                                   onClick={() => activate('kpi')} href="#">
                                                    Diretta <span style={{
                                                        display: 'inline-block',
                                                        width: '8px',
                                                        height: '8px',
                                                        backgroundColor: '#dc3545',
                                                        borderRadius: '50%',
                                                        marginLeft: '4px',
                                                        animation: 'pulse 1.5s infinite'
                                                    }}></span>
                                                </a>
                                            </li>
                                        )}
                                        {/* 5. Risorse - visibile a tutti gli utenti autenticati */}
                                        <li className="nav-item">
                                            <a className={`nav-link ${activeTab === 'risorse' ? 'active' : ''}`}
                                               onClick={() => activate('risorse')} href="#">
                                                <i className="fas fa-folder-open me-1"></i>
                                                Risorse
                                            </a>
                                        </li>
                                    </ul>
                                    <div className="d-flex align-items-center">
                                        {user?.is_superuser && !isImpersonating && (
                                            <button
                                                className="btn btn-outline-warning btn-sm me-2"
                                                onClick={() => setShowImpersonate(!showImpersonate)}
                                                title="Impersona utente"
                                            >
                                                Impersona
                                            </button>
                                        )}
                                        <p className="text-light me-3 mb-0">{displayName}</p>
                                        <button className="btn btn-danger" onClick={handleSignoutClick}>Esci</button>
                                    </div>
                                </div>
                            </>
                        )}
                    </div>
                </nav>
                {isImpersonating && (
                    <div className="alert alert-danger mt-3 d-flex align-items-center justify-content-between">
                        <span>
                            <strong>Stai impersonando:</strong> {user?.email}
                            {originalUser && <span className="ms-2">(tu sei: {originalUser.email})</span>}
                        </span>
                        <button
                            className="btn btn-light btn-sm"
                            onClick={handleStopImpersonating}
                        >
                            Torna al tuo account
                        </button>
                    </div>
                )}
                {showImpersonate && user?.is_superuser && !isImpersonating && (
                    <div className="alert alert-warning mt-3">
                        <form onSubmit={handleImpersonate} className="d-flex align-items-center">
                            <label className="me-2 mb-0">Impersona utente:</label>
                            <div style={{maxWidth: '300px', flex: 1}} className="me-2">
                                <EmailAutocomplete
                                    value={impersonateEmail}
                                    onChange={handleImpersonateEmailChange}
                                    emails={impersonateEmails}
                                    placeholder="Cerca email..."
                                    className="form-control-sm"
                                    required
                                />
                            </div>
                            <button type="submit" className="btn btn-warning btn-sm me-2">Impersona</button>
                            <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowImpersonate(false)}>Annulla</button>
                        </form>
                    </div>
                )}
                {consultazione && activeTab !== 'dashboard' && (
                    <h3 className="alert alert-primary">{consultazione.nome}</h3>
                )}
                {consultazioneLoaded && !consultazione && isAuthenticated && (
                    <div className="alert alert-info">Nessuna consultazione elettorale attiva</div>
                )}
                {error && <div className="alert alert-danger mt-3">{error}</div>}
                {isAuthenticated && client && consultazione ? (
                    <div>
                        <div className="tab-content">
                            {activeTab === 'dashboard' && (
                                <div className="tab-pane active">
                                    <Dashboard
                                        user={user}
                                        permissions={permissions}
                                        consultazione={consultazione}
                                        hasContributions={hasContributions}
                                        onNavigate={activate}
                                    />
                                </div>
                            )}
                            {activeTab === 'sections' && permissions.sections && (
                                <div className="tab-pane active">
                                    <SectionList
                                        user={user}
                                        client={client}
                                        setError={setError}
                                        referenti={permissions.referenti}
                                    />
                                </div>
                            )}
                            {activeTab === 'designazione' && permissions.referenti && (
                                <div className="tab-pane active">
                                    <Mappatura
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
                                        consultazione={consultazione}
                                    />
                                </div>
                            )}
                            {activeTab === 'pdf' && pdf && (
                                <div className="tab-pane active">
                                    <GeneraModuli
                                        client={client}
                                        setError={setError}
                                    />
                                </div>
                            )}
                            {activeTab === 'sezioni' && permissions.referenti && (
                                <div className="tab-pane active">
                                    <GestioneSezioni
                                        client={client}
                                        setError={setError}
                                    />
                                </div>
                            )}
                            {activeTab === 'gestione_rdl' && permissions.gestione_rdl && (
                                <div className="tab-pane active">
                                    <GestioneRdl
                                        client={client}
                                        setError={setError}
                                    />
                                </div>
                            )}
                            {activeTab === 'deleghe' && permissions.referenti && (
                                <div className="tab-pane active">
                                    <GestioneDeleghe
                                        client={client}
                                        user={user}
                                        consultazione={consultazione}
                                        setError={setError}
                                    />
                                </div>
                            )}
                            {activeTab === 'risorse' && (
                                <div className="tab-pane active">
                                    <Risorse
                                        client={client}
                                        consultazione={consultazione}
                                        setError={setError}
                                    />
                                </div>
                            )}
                        </div>
                    </div>
                ) : showRdlRegistration ? (
                    <RdlSelfRegistration onClose={() => setShowRdlRegistration(false)} />
                ) : (
                    <div className="card">
                        <div className="card-header bg-primary text-white">
                            <h5 className="mb-0">Accedi all'app RDL</h5>
                        </div>
                        <div className="card-body">
                            {magicLinkSent ? (
                                /* STEP 2: Email inviata - istruzioni chiare */
                                <div className="text-center">
                                    <div className="alert alert-success">
                                        <h4 className="alert-heading">Email inviata con successo!</h4>
                                    </div>

                                    <div className="my-4 p-4 bg-light rounded">
                                        <h5>Cosa fare ora:</h5>
                                        <ol className="text-start mb-0" style={{fontSize: '1.1em'}}>
                                            <li className="mb-2">
                                                <strong>Apri la tua casella email</strong><br/>
                                                <span className="text-muted">Controlla la posta di: <strong>{magicLinkEmail}</strong></span>
                                            </li>
                                            <li className="mb-2">
                                                <strong>Cerca l'email da "RDL 5 Stelle"</strong><br/>
                                                <span className="text-muted">Oggetto: "Il tuo link di accesso"</span>
                                            </li>
                                            <li className="mb-2">
                                                <strong>Clicca sul pulsante "Accedi"</strong><br/>
                                                <span className="text-muted">Si aprirà automaticamente questa pagina e sarai dentro!</span>
                                            </li>
                                        </ol>
                                    </div>

                                    <div className="alert alert-warning">
                                        <strong>Non trovi l'email?</strong><br/>
                                        <small>
                                            Controlla nella cartella <strong>SPAM</strong> o <strong>Posta indesiderata</strong>.<br/>
                                            Il link è valido per 60 minuti.
                                        </small>
                                    </div>

                                    <button
                                        className="btn btn-outline-primary"
                                        onClick={() => setMagicLinkSent(false)}
                                    >
                                        ← Torna indietro per reinviare
                                    </button>
                                </div>
                            ) : (
                                /* STEP 1: Inserisci email */
                                <>
                                    <div className="alert alert-info mb-4">
                                        <h6 className="alert-heading">Come funziona?</h6>
                                        <ol className="mb-0 ps-3">
                                            <li>Inserisci la tua email qui sotto</li>
                                            <li>Riceverai un'email con un link di accesso</li>
                                            <li>Clicca il link e sei dentro! Niente password da ricordare.</li>
                                        </ol>
                                    </div>

                                    <form onSubmit={handleMagicLinkSubmit}>
                                        <div className="mb-3">
                                            <label htmlFor="email" className="form-label fw-bold">
                                                Inserisci la tua email:
                                            </label>
                                            <input
                                                type="email"
                                                className="form-control form-control-lg"
                                                id="email"
                                                placeholder="tu@esempio.com"
                                                value={magicLinkEmail}
                                                onChange={(e) => setMagicLinkEmail(e.target.value)}
                                                required
                                                disabled={isLoading}
                                                autoFocus
                                            />
                                            <small className="text-muted">
                                                Usa l'email con cui sei registrato come RDL
                                            </small>
                                        </div>
                                        <button
                                            type="submit"
                                            className="btn btn-primary btn-lg w-100"
                                            disabled={isLoading || !magicLinkEmail}
                                        >
                                            {isLoading ? (
                                                <>
                                                    <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                                                    Invio in corso...
                                                </>
                                            ) : (
                                                'Inviami il link di accesso'
                                            )}
                                        </button>
                                    </form>

                                    <hr className="my-4" />

                                    {/* Sezione Persuasiva - Diventa RDL */}
                                    <div className="bg-success bg-opacity-10 border border-success rounded p-4">
                                        <div className="text-center mb-3">
                                            <span style={{fontSize: '2.5rem'}}>&#9733;</span>
                                        </div>
                                        <h4 className="text-success text-center mb-3">
                                            Vuoi fare la differenza?
                                        </h4>
                                        <p className="text-center mb-4" style={{fontSize: '1.1em'}}>
                                            <strong>Diventa Rappresentante di Lista</strong> e proteggi il voto dei cittadini
                                        </p>

                                        <div className="row mb-4">
                                            <div className="col-md-6 mb-3 mb-md-0">
                                                <div className="d-flex align-items-start">
                                                    <span className="text-success me-2" style={{fontSize: '1.3em'}}>&#10003;</span>
                                                    <div>
                                                        <strong>Tuteli la democrazia</strong><br/>
                                                        <small className="text-muted">Garantisci la regolarità delle operazioni di voto nel tuo seggio</small>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="col-md-6">
                                                <div className="d-flex align-items-start">
                                                    <span className="text-success me-2" style={{fontSize: '1.3em'}}>&#10003;</span>
                                                    <div>
                                                        <strong>Partecipi attivamente</strong><br/>
                                                        <small className="text-muted">Non solo votante: diventi protagonista del processo elettorale</small>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="row mb-4">
                                            <div className="col-md-6 mb-3 mb-md-0">
                                                <div className="d-flex align-items-start">
                                                    <span className="text-success me-2" style={{fontSize: '1.3em'}}>&#10003;</span>
                                                    <div>
                                                        <strong>Impari come funziona</strong><br/>
                                                        <small className="text-muted">Scopri dall'interno il meccanismo elettorale italiano</small>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="col-md-6">
                                                <div className="d-flex align-items-start">
                                                    <span className="text-success me-2" style={{fontSize: '1.3em'}}>&#10003;</span>
                                                    <div>
                                                        <strong>Scegli dove operare</strong><br/>
                                                        <small className="text-muted">Vicino a casa, al lavoro, o dove preferisci</small>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="alert alert-light border-success mb-4 text-center">
                                            <small>
                                                <strong>Nessun requisito particolare richiesto.</strong><br/>
                                                Basta essere elettori. Ti formeremo noi su tutto quello che c'è da sapere!
                                            </small>
                                        </div>

                                        <button
                                            className="btn btn-success btn-lg w-100"
                                            onClick={() => setShowRdlRegistration(true)}
                                        >
                                            Candidati come Rappresentante di Lista
                                        </button>
                                        <p className="text-center text-muted mt-2 mb-0">
                                            <small>La registrazione richiede solo 2 minuti</small>
                                        </p>
                                    </div>
                                </>
                            )}
                        </div>
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
                        RDL 5 Stelle<br/>
                        Donata al MOVIMENTO 5 STELLE<br/>
                        da Simone Federici GT Roma XV
                    </p>
                </div>
            </footer>
        </>
    );
}

function App() {
    return (
        <AuthProvider>
            <AppContent />
        </AuthProvider>
    );
}

export default App;
