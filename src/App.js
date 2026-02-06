// App.js
import React, {useState, useEffect, useMemo} from "react";
import RdlList from "./RdlList";
import Mappatura from "./Mappatura";
import Kpi from "./Kpi";
import Client, {clearCache} from "./Client";
import SectionList from "./SectionList";
import logo from './assets/ainaudi_logo.png';
import GeneraModuli from "./GeneraModuli";
import GestioneSezioni from "./GestioneSezioni";
import EmailAutocomplete from "./EmailAutocomplete";
import RdlSelfRegistration from "./RdlSelfRegistration";
import CampagnaRegistration from "./CampagnaRegistration";
import GestioneRdl from "./GestioneRdl";
import GestioneDeleghe from "./GestioneDeleghe";
import GestioneCampagne from "./GestioneCampagne";
import Risorse from "./Risorse";
import Dashboard from "./Dashboard";
import SchedaElettorale from "./SchedaElettorale";
import GestioneTerritorio from "./GestioneTerritorio";
import PDFConfirmPage from "./PDFConfirmPage";
import TemplateEditor from "./TemplateEditor";
import TemplateList from "./TemplateList";
import {AuthProvider, useAuth} from "./AuthContext";

// In development, use empty string to leverage Vite proxy (vite.config.js)
// In production, use empty string for same-origin requests
const SERVER_API = '';
const SERVER_PDF = '';

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
    const [campagnaSlug, setCampagnaSlug] = useState(null);
    const [showPdfConfirm, setShowPdfConfirm] = useState(false);
    const [pdf, setPdf] = useState(false);
    const [isTerritorioDropdownOpen, setIsTerritorioDropdownOpen] = useState(false);
    const [isRdlDropdownOpen, setIsRdlDropdownOpen] = useState(false);
    const [isDelegheDropdownOpen, setIsDelegheDropdownOpen] = useState(false);
    const [isConsultazioneDropdownOpen, setIsConsultazioneDropdownOpen] = useState(false);
    const [magicLinkEmail, setMagicLinkEmail] = useState(() => {
        return localStorage.getItem('rdl_magic_link_email') || '';
    });
    const [magicLinkSent, setMagicLinkSent] = useState(false);
    const [consultazione, setConsultazione] = useState(null);
    const [consultazioni, setConsultazioni] = useState([]);
    const [consultazioneLoaded, setConsultazioneLoaded] = useState(false);
    const [showConsultazioniDropdown, setShowConsultazioniDropdown] = useState(false);
    const [selectedScheda, setSelectedScheda] = useState(null);
    const [hasContributions, setHasContributions] = useState(false);
    const [impersonateEmail, setImpersonateEmail] = useState('');
    const [showImpersonate, setShowImpersonate] = useState(false);
    const [impersonateEmails, setImpersonateEmails] = useState([]);
    const [templateIdToEdit, setTemplateIdToEdit] = useState(null);

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

    // Check for campagna URL: /campagna/:slug
    useEffect(() => {
        const path = window.location.pathname;
        const campagnaMatch = path.match(/^\/campagna\/([^/]+)\/?$/);
        if (campagnaMatch) {
            setCampagnaSlug(campagnaMatch[1]);
        }

        // Check for PDF confirm URL: /pdf/confirm
        const pdfConfirmMatch = path.match(/^\/pdf\/confirm\/?$/);
        if (pdfConfirmMatch) {
            setShowPdfConfirm(true);
        }
    }, []);

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
                } else if (perms.referenti || perms.kpi) {
                    // Delegati/Sub-delegati/Admin vedono la dashboard
                    setActiveTab('dashboard');
                } else if (perms.sections) {
                    // RDL semplici vanno direttamente a Scrutinio
                    setActiveTab('sections');
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

    // Load consultazioni and set the active one
    useEffect(() => {
        if (client && isAuthenticated) {
            // Carica la lista delle consultazioni
            client.election.list().then(data => {
                if (!data.error && Array.isArray(data)) {
                    setConsultazioni(data);
                }
            }).catch(() => {});

            // Carica la consultazione attiva (prima nel futuro o in corso)
            client.election.active().then(data => {
                if (!data.error && data.id) {
                    setConsultazione(data);
                }
                setConsultazioneLoaded(true);
            }).catch(() => {
                setConsultazioneLoaded(true);
            });
        }
    }, [client, isAuthenticated]);

    // Handle consultazione switch
    const handleConsultazioneChange = async (id) => {
        if (!client || id === consultazione?.id) {
            setShowConsultazioniDropdown(false);
            return;
        }

        try {
            const data = await client.election.get(id);
            if (!data.error && data.id) {
                setConsultazione(data);
                clearCache(); // Invalida la cache per ricaricare i dati
            }
        } catch (err) {
            setError('Errore nel cambio consultazione');
        }
        setShowConsultazioniDropdown(false);
    };

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
        setCampagnaSlug(null);
        setConsultazione(null);
        setConsultazioneLoaded(false);
    };

    const handleCloseCampagna = () => {
        setCampagnaSlug(null);
        // Update URL back to home
        window.history.replaceState({}, document.title, '/');
    };

    const toggleMenu = () => {
        setIsMenuOpen(!isMenuOpen);
    };

    // Close dropdowns when clicking outside
    useEffect(() => {
        const handleClickOutside = (e) => {
            if (!e.target.closest('.dropdown')) {
                setIsTerritorioDropdownOpen(false);
                setIsRdlDropdownOpen(false);
                setIsDelegheDropdownOpen(false);
                setIsConsultazioneDropdownOpen(false);
            }
            if (!e.target.closest('.consultazione-switcher')) {
                setShowConsultazioniDropdown(false);
            }
        };
        document.addEventListener('click', handleClickOutside);
        return () => document.removeEventListener('click', handleClickOutside);
    }, [isTerritorioDropdownOpen, isRdlDropdownOpen, isDelegheDropdownOpen, isConsultazioneDropdownOpen, showConsultazioniDropdown]);

    const closeAllDropdowns = () => {
        setIsTerritorioDropdownOpen(false);
        setIsRdlDropdownOpen(false);
        setIsDelegheDropdownOpen(false);
        setIsConsultazioneDropdownOpen(false);
    };

    const activate = (tab) => {
        // Close campaign registration if open
        if (campagnaSlug) {
            setCampagnaSlug(null);
            window.history.replaceState({}, document.title, '/');
        }
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
                        <a
                            className="navbar-brand"
                            href="#"
                            onClick={(e) => {
                                e.preventDefault();
                                if (isAuthenticated) {
                                    activate('dashboard');
                                }
                            }}
                            style={{ cursor: isAuthenticated ? 'pointer' : 'default' }}
                        >
                            AInaudi
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
                                        {/* 1. HOME - solo per delegati/sub-delegati/admin, non per RDL semplici */}
                                        {(permissions.referenti || permissions.kpi) && (
                                            <li className="nav-item">
                                                <a className={`nav-link ${activeTab === 'dashboard' ? 'active' : ''}`}
                                                   onClick={() => activate('dashboard')} href="#">
                                                    <i className="fas fa-home me-1"></i>
                                                    Home
                                                </a>
                                            </li>
                                        )}

                                        {/* 2. TERRITORIO - solo superuser */}
                                        {user?.is_superuser && (
                                            <li className="nav-item">
                                                <a className={`nav-link ${activeTab === 'territorio_admin' ? 'active' : ''}`}
                                                   onClick={() => activate('territorio_admin')} href="#">
                                                    <i className="fas fa-globe-europe me-1"></i>
                                                    Territorio
                                                </a>
                                            </li>
                                        )}

                                        {/* 3. CONSULTAZIONE - Menu dinamico con tipologie elezione */}
                                        {consultazione && permissions.referenti && consultazione.schede && consultazione.schede.length > 0 && (
                                            <li className="nav-item dropdown">
                                                <a className={`nav-link dropdown-toggle ${activeTab === 'scheda' ? 'active' : ''}`}
                                                   href="#"
                                                   role="button"
                                                   onClick={(e) => { e.preventDefault(); closeAllDropdowns(); setIsConsultazioneDropdownOpen(!isConsultazioneDropdownOpen); }}
                                                   aria-expanded={isConsultazioneDropdownOpen}>
                                                    <i className="fas fa-vote-yea me-1"></i>
                                                    Consultazione
                                                </a>
                                                <ul className={`dropdown-menu dropdown-menu-dark ${isConsultazioneDropdownOpen ? 'show' : ''}`}>
                                                    {consultazione.schede.map((scheda, idx) => (
                                                        <li key={scheda.id || idx}>
                                                            <a className={`dropdown-item ${selectedScheda?.id === scheda.id && activeTab === 'scheda' ? 'active' : ''}`}
                                                               onClick={() => { setSelectedScheda(scheda); activate('scheda'); closeAllDropdowns(); }} href="#">
                                                                <span className="me-2" style={{
                                                                    display: 'inline-block',
                                                                    width: '12px',
                                                                    height: '12px',
                                                                    backgroundColor: scheda.colore || '#ccc',
                                                                    borderRadius: '2px'
                                                                }}></span>
                                                                {scheda.nome}
                                                            </a>
                                                        </li>
                                                    ))}
                                                </ul>
                                            </li>
                                        )}

                                        {/* 4. DELEGATI - Catena deleghe e designazioni */}
                                        {(permissions.referenti || pdf) && (
                                            <li className="nav-item dropdown">
                                                <a className={`nav-link dropdown-toggle ${['deleghe', 'pdf', 'template_list', 'template_editor'].includes(activeTab) ? 'active' : ''}`}
                                                   href="#"
                                                   role="button"
                                                   onClick={(e) => { e.preventDefault(); closeAllDropdowns(); setIsDelegheDropdownOpen(!isDelegheDropdownOpen); }}
                                                   aria-expanded={isDelegheDropdownOpen}>
                                                    <i className="fas fa-user-tie me-1"></i>
                                                    Delegati
                                                </a>
                                                <ul className={`dropdown-menu dropdown-menu-dark ${isDelegheDropdownOpen ? 'show' : ''}`}>
                                                    {permissions.referenti && (
                                                        <li>
                                                            <a className={`dropdown-item ${activeTab === 'deleghe' ? 'active' : ''}`}
                                                               onClick={() => { activate('deleghe'); closeAllDropdowns(); }} href="#">
                                                                <i className="fas fa-sitemap me-2"></i>
                                                                Catena Deleghe
                                                            </a>
                                                        </li>
                                                    )}
                                                    {consultazione && permissions.referenti && (
                                                        <li>
                                                            <a className={`dropdown-item ${activeTab === 'template_list' ? 'active' : ''}`}
                                                               onClick={() => { activate('template_list'); setTemplateIdToEdit(null); closeAllDropdowns(); }} href="#">
                                                                <i className="fas fa-file-pdf me-2"></i>
                                                                Template Designazioni
                                                            </a>
                                                        </li>
                                                    )}
                                                    {consultazione && pdf && (
                                                        <li>
                                                            <a className={`dropdown-item ${activeTab === 'pdf' ? 'active' : ''}`}
                                                               onClick={() => { activate('pdf'); closeAllDropdowns(); }} href="#">
                                                                <i className="fas fa-file-signature me-2"></i>
                                                                Genera Moduli
                                                            </a>
                                                        </li>
                                                    )}
                                                </ul>
                                            </li>
                                        )}

                                        {/* 5. RDL - Gestione RDL */}
                                        {(permissions.referenti || permissions.gestione_rdl) && (
                                            <li className="nav-item dropdown">
                                                <a className={`nav-link dropdown-toggle ${['campagne', 'gestione_rdl', 'designazione', 'sezioni'].includes(activeTab) ? 'active' : ''}`}
                                                   href="#"
                                                   role="button"
                                                   onClick={(e) => { e.preventDefault(); closeAllDropdowns(); setIsRdlDropdownOpen(!isRdlDropdownOpen); }}
                                                   aria-expanded={isRdlDropdownOpen}>
                                                    <i className="fas fa-users me-1"></i>
                                                    RDL
                                                </a>
                                                <ul className={`dropdown-menu dropdown-menu-dark ${isRdlDropdownOpen ? 'show' : ''}`}>
                                                    {permissions.referenti && (
                                                        <li>
                                                            <a className={`dropdown-item ${activeTab === 'campagne' ? 'active' : ''}`}
                                                               onClick={() => { activate('campagne'); closeAllDropdowns(); }} href="#">
                                                                <i className="fas fa-bullhorn me-2"></i>
                                                                Campagne
                                                            </a>
                                                        </li>
                                                    )}
                                                    {permissions.gestione_rdl && (
                                                        <li>
                                                            <a className={`dropdown-item ${activeTab === 'gestione_rdl' ? 'active' : ''}`}
                                                               onClick={() => { activate('gestione_rdl'); closeAllDropdowns(); }} href="#">
                                                                <i className="fas fa-user-check me-2"></i>
                                                                Gestione RDL
                                                            </a>
                                                        </li>
                                                    )}
                                                    {permissions.referenti && (
                                                        <li>
                                                            <a className={`dropdown-item ${activeTab === 'sezioni' ? 'active' : ''}`}
                                                               onClick={() => { activate('sezioni'); closeAllDropdowns(); }} href="#">
                                                                <i className="fas fa-map-marker-alt me-2"></i>
                                                                Gestione Sezioni
                                                            </a>
                                                        </li>
                                                    )}
                                                    {consultazione && permissions.referenti && (
                                                        <li>
                                                            <a className={`dropdown-item ${activeTab === 'designazione' ? 'active' : ''}`}
                                                               onClick={() => { activate('designazione'); closeAllDropdowns(); }} href="#">
                                                                <i className="fas fa-th me-2"></i>
                                                                Mappatura
                                                            </a>
                                                        </li>
                                                    )}
                                                </ul>
                                            </li>
                                        )}

                                        {/* 6. SCRUTINIO */}
                                        {consultazione && permissions.sections && (
                                            <li className="nav-item">
                                                <a className={`nav-link ${activeTab === 'sections' ? 'active' : ''}`}
                                                   onClick={() => activate('sections')} href="#">
                                                    <i className="fas fa-clipboard-check me-1"></i>
                                                    Scrutinio
                                                </a>
                                            </li>
                                        )}

                                        {/* 7. DIRETTA (KPI) - visibile solo quando ci sono contributi */}
                                        {consultazione && permissions.kpi && hasContributions && (
                                            <li className="nav-item">
                                                <a className={`nav-link ${activeTab === 'kpi' ? 'active' : ''}`}
                                                   onClick={() => activate('kpi')} href="#">
                                                    <i className="fas fa-chart-line me-1"></i>
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

                                        {/* 8. RISORSE - visibile a tutti gli utenti autenticati */}
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
                {consultazione && (
                    <div className="consultazione-switcher position-relative">
                        {/* Solo delegati/sub-delegati/admin possono switchare consultazione */}
                        {permissions.referenti ? (
                            <>
                                <div
                                    className="alert alert-primary d-flex align-items-center justify-content-between mb-3"
                                    style={{ cursor: consultazioni.length > 1 ? 'pointer' : 'default' }}
                                    onClick={() => consultazioni.length > 1 && setShowConsultazioniDropdown(!showConsultazioniDropdown)}
                                >
                                    <h5 className="mb-0">
                                        {consultazione.nome}
                                        {!consultazione.is_attiva && (
                                            <span className="badge bg-secondary ms-2">Non attiva</span>
                                        )}
                                    </h5>
                                    {consultazioni.length > 1 && (
                                        <span className="ms-2">
                                            <i className={`fas fa-chevron-${showConsultazioniDropdown ? 'up' : 'down'}`}></i>
                                        </span>
                                    )}
                                </div>
                                {showConsultazioniDropdown && consultazioni.length > 1 && (
                                    <div
                                        className="position-absolute bg-white border rounded shadow-lg p-2"
                                        style={{ top: '100%', left: 0, right: 0, zIndex: 1000, maxHeight: '300px', overflowY: 'auto' }}
                                    >
                                        <div className="small text-muted mb-2 px-2">Seleziona consultazione:</div>
                                        {consultazioni.map(c => (
                                            <div
                                                key={c.id}
                                                className={`p-2 rounded ${c.id === consultazione.id ? 'bg-primary text-white' : 'hover-bg-light'}`}
                                                style={{ cursor: 'pointer' }}
                                                onClick={() => handleConsultazioneChange(c.id)}
                                            >
                                                <div className="d-flex justify-content-between align-items-center">
                                                    <div>
                                                        <strong>{c.nome}</strong>
                                                        <div className="small">
                                                            {new Date(c.data_inizio).toLocaleDateString('it-IT')}
                                                            {c.data_fine !== c.data_inizio && ` - ${new Date(c.data_fine).toLocaleDateString('it-IT')}`}
                                                        </div>
                                                    </div>
                                                    <div>
                                                        {c.is_current && <span className="badge bg-success">In corso</span>}
                                                        {c.is_future && !c.is_current && <span className="badge bg-info">Futura</span>}
                                                        {!c.is_future && !c.is_current && <span className="badge bg-secondary">Passata</span>}
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </>
                        ) : (
                            /* RDL semplici vedono solo il nome, senza switch */
                            <h5 className="alert alert-primary mb-3">{consultazione.nome}</h5>
                        )}
                    </div>
                )}
                {consultazioneLoaded && !consultazione && isAuthenticated && (
                    <div className="alert alert-info">Nessuna consultazione elettorale attiva</div>
                )}
                {error && <div className="alert alert-danger mt-3">{error}</div>}
                {showPdfConfirm ? (
                    <PDFConfirmPage serverApi={SERVER_API} />
                ) : campagnaSlug ? (
                    <CampagnaRegistration slug={campagnaSlug} onClose={handleCloseCampagna} isAuthenticated={isAuthenticated} isSuperuser={user?.is_superuser} />
                ) : isAuthenticated && client && consultazione ? (
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
                            {activeTab === 'scheda' && selectedScheda && permissions.referenti && (
                                <div className="tab-pane active">
                                    <SchedaElettorale
                                        scheda={selectedScheda}
                                        client={client}
                                        onClose={() => activate('dashboard')}
                                        onUpdate={(updatedScheda) => {
                                            setSelectedScheda(updatedScheda);
                                            // Aggiorna anche la scheda nella consultazione
                                            if (consultazione) {
                                                setConsultazione({
                                                    ...consultazione,
                                                    schede: consultazione.schede.map(s =>
                                                        s.id === updatedScheda.id ? { ...s, ...updatedScheda } : s
                                                    )
                                                });
                                            }
                                        }}
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
                            {activeTab === 'campagne' && permissions.referenti && (
                                <div className="tab-pane active">
                                    <GestioneCampagne
                                        client={client}
                                        consultazione={consultazione}
                                        setError={setError}
                                        onOpenCampagna={(slug) => {
                                            setCampagnaSlug(slug);
                                            window.history.replaceState({}, document.title, `/campagna/${slug}`);
                                        }}
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
                            {activeTab === 'territorio_admin' && user?.is_superuser && (
                                <div className="tab-pane active">
                                    <GestioneTerritorio
                                        client={client}
                                        setError={setError}
                                    />
                                </div>
                            )}
                            {activeTab === 'template_list' && consultazione && permissions.referenti && (
                                <div className="tab-pane active">
                                    <TemplateList
                                        client={client}
                                        onEditTemplate={(id) => {
                                            setTemplateIdToEdit(id);
                                            setActiveTab('template_editor');
                                        }}
                                    />
                                </div>
                            )}
                            {activeTab === 'template_editor' && consultazione && permissions.referenti && templateIdToEdit && (
                                <div className="tab-pane active">
                                    <div style={{ marginBottom: '15px' }}>
                                        <button
                                            className="btn btn-secondary"
                                            onClick={() => {
                                                setActiveTab('template_list');
                                                setTemplateIdToEdit(null);
                                            }}
                                        >
                                            ← Torna alla lista template
                                        </button>
                                    </div>
                                    <TemplateEditor
                                        templateId={templateIdToEdit}
                                        client={client}
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
                                                <strong>Cerca l'email da "AInaudi"</strong><br/>
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
                    <img src={logo} alt="AInaudi" style={{
                        width: '100%',
                    }} />
                </div>
                <div className="footer-text">
                    <p>
                        <strong>AInaudi</strong><br/>
                        © Simone Federici
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
