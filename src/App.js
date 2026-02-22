// App.js
import React, {useState, useEffect, useMemo, useRef} from "react";
import RdlList from "./rdl/RdlList";
import MappaturaGerarchica from "./rdl/MappaturaGerarchica";
import Kpi from "./kpi/Kpi";
import Client, {clearCache} from "./auth/Client";
import SectionList from "./scrutinio/SectionList";
import logo from './assets/logo-m5s.png';
import GestioneSezioni from "./rdl/GestioneSezioni";
import EmailAutocomplete from "./components/EmailAutocomplete";
import RdlSelfRegistration from "./rdl/RdlSelfRegistration";
import CampagnaRegistration from "./rdl/CampagnaRegistration";
import GestioneRdl from "./rdl/GestioneRdl";
import MassEmail from "./rdl/MassEmail";
import GestioneDeleghe from "./deleghe/GestioneDeleghe";
import GestioneDesignazioni from "./deleghe/GestioneDesignazioni";
import GestioneCampagne from "./rdl/GestioneCampagne";
import Risorse from "./risorse/Risorse";
import Dashboard from "./dashboard/Dashboard";
import SchedaElettorale from "./elezioni/SchedaElettorale";
import GestioneTerritorio from "./territorio/GestioneTerritorio";
import PDFConfirmPage from "./components/PDFConfirmPage";
import TemplateEditor from "./templates/TemplateEditor";
import TemplateList from "./templates/TemplateList";
import ScrutinioAggregato from "./scrutinio/ScrutinioAggregato";
import {AuthProvider, useAuth} from "./auth/AuthContext";
import ChatInterface from "./chat/ChatInterface";
import PwaOnboarding from "./pwa/PwaOnboarding";
import EventDetail from "./events/EventDetail";
import AssignmentDetail from "./events/AssignmentDetail";
import EventList from "./events/EventList";
import { onForegroundMessage } from "./firebase";

// In development, use empty string to leverage Vite proxy (vite.config.js)
// In production, use empty string for same-origin requests
const SERVER_API = '';
const SERVER_PDF = '';

function AppContent() {
    const {user, accessToken, isAuthenticated, requestMagicLink, verifyMagicLink, logout, refreshAccessToken, loading: authLoading, error: authError, impersonate, isImpersonating, originalUser, stopImpersonating} = useAuth();

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [apiToast, setApiToast] = useState(null);
    const [activeTab, setActiveTab] = useState(null);
    const activeTabRef = useRef(null);
    useEffect(() => { activeTabRef.current = activeTab; }, [activeTab]);
    // Global API error toast
    useEffect(() => {
        const handler = (e) => {
            setApiToast(e.detail);
            setTimeout(() => setApiToast(null), 5000);
        };
        window.addEventListener('api-error', handler);
        return () => window.removeEventListener('api-error', handler);
    }, []);

    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const [permissions, setPermissions] = useState({
        // Permessi granulari (uno per voce menu)
        is_superuser: false,
        can_view_dashboard: false,           // Dashboard
        can_manage_territory: false,         // Territorio
        can_manage_elections: false,         // Consultazione
        can_manage_campaign: false,          // Campagne
        can_manage_rdl: false,               // Gestione RDL
        can_manage_sections: false,          // Gestione Sezioni
        can_manage_mappatura: false,         // Mappatura
        can_manage_delegations: false,       // Catena Deleghe
        can_manage_designazioni: false,      // Designazioni
        can_manage_templates: false,         // Template PDF
        can_generate_documents: false,       // Genera Moduli
        has_scrutinio_access: false,         // Scrutinio
        can_view_resources: false,           // Risorse
        can_view_live_results: false,        // Risultati Live
        can_view_kpi: false,                 // Diretta (KPI)

        // Admin-only
        can_manage_mass_email: false,
        can_manage_events: false,

        // Future features
        can_ask_to_ai_assistant: false,
        can_manage_incidents: false,

        // Info catena deleghe
        is_delegato: false,
        is_sub_delegato: false,
        is_rdl: false,

        // Backwards compatibility (deprecati)
        sections: false,
        referenti: false,
        kpi: false,
        gestione_rdl: false,
        upload_sezioni: false
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
    const [impersonateEmail, setImpersonateEmail] = useState('');
    const [showImpersonate, setShowImpersonate] = useState(false);
    const [impersonateEmails, setImpersonateEmails] = useState([]);
    const [templateIdToEdit, setTemplateIdToEdit] = useState(null);
    const [showChat, setShowChat] = useState(false);
    const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
    const [deepLinkEventId, setDeepLinkEventId] = useState(null);
    const [deepLinkAssignmentId, setDeepLinkAssignmentId] = useState(null);
    const [theme, setTheme] = useState(() => {
        const savedTheme = localStorage.getItem('app-theme');
        if (savedTheme) return savedTheme;
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'night';
        }
        return 'daily';
    });

    // Create client when we have a token
    const client = useMemo(() => {
        if (accessToken) {
            return Client(SERVER_API, SERVER_PDF, accessToken, refreshAccessToken, logout);
        }
        return null;
    }, [accessToken, refreshAccessToken, logout]);

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

    // Theme effect
    useEffect(() => {
        if (theme === 'night') {
            document.documentElement.setAttribute('data-theme', 'night');
        } else {
            document.documentElement.removeAttribute('data-theme');
        }
        localStorage.setItem('app-theme', theme);
    }, [theme]);

    // Close user menu when clicking outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (isUserMenuOpen && !event.target.closest('.dropdown')) {
                setIsUserMenuOpen(false);
            }
        };
        document.addEventListener('click', handleClickOutside);
        return () => document.removeEventListener('click', handleClickOutside);
    }, [isUserMenuOpen]);

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

        // Check for deep link: /events/:id
        const eventMatch = path.match(/^\/events\/([a-f0-9-]+)\/?$/);
        if (eventMatch) {
            setDeepLinkEventId(eventMatch[1]);
            setActiveTab('event-detail');
        }

        // Check for deep link: /assignments/:id
        const assignmentMatch = path.match(/^\/assignments\/(\d+)\/?$/);
        if (assignmentMatch) {
            setDeepLinkAssignmentId(assignmentMatch[1]);
            setActiveTab('assignment-detail');
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
                console.log(perms);

                // Verifica se l'utente ha almeno un permesso significativo
                const hasAnyPermission = (
                    perms.is_superuser ||
                    perms.can_view_dashboard ||
                    perms.can_manage_territory ||
                    perms.can_view_kpi ||
                    perms.can_manage_elections ||
                    perms.can_manage_campaign ||
                    perms.can_manage_delegations ||
                    perms.can_manage_rdl ||
                    perms.can_manage_sections ||
                    perms.can_manage_mappatura ||
                    perms.can_manage_designazioni ||
                    perms.can_manage_templates ||
                    perms.has_scrutinio_access ||
                    perms.can_generate_documents ||
                    perms.can_view_live_results ||
                    perms.can_view_resources
                );

                if (!hasAnyPermission) {
                    setError(`La mail ${user.email} non ha permessi per accedere ad alcuna sezione`);
                    setTimeout(() => {
                        handleSignoutClick();
                    }, 2000);
                } else if (perms.can_view_dashboard || perms.is_superuser) {
                    // Delegati/Sub-delegati/Admin vedono la dashboard
                    // pushState (non replaceState) crea una entry "guardia" sotto,
                    // così il popstate handler può intercettare il Back e impedire l'uscita dall'app
                    window.history.pushState({ tab: 'dashboard' }, '');
                    setActiveTab('dashboard');
                } else if (perms.has_scrutinio_access) {
                    // RDL semplici vanno direttamente a Scrutinio
                    window.history.pushState({ tab: 'sections' }, '');
                    setActiveTab('sections');

                    // Preload seggi in background per UX ottimizzato
                    client.scrutinio.mieiSeggiLight().then(data => {
                        if (data && !data.error) {
                            console.log(`Preload seggi completato: ${data.total} seggi caricati`);
                        }
                    }).catch(err => {
                        console.warn('Preload seggi fallito (non critico):', err);
                    });
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
            // Carica la lista delle consultazioni (solo per chi può gestire elezioni o delegazioni)
            if (permissions.can_manage_elections || permissions.can_manage_delegations || permissions.is_superuser) {
                client.election.list().then(data => {
                    if (!data.error && Array.isArray(data)) {
                        setConsultazioni(data);
                    }
                }).catch(() => {});
            }

            // Carica la consultazione attiva (accessibile a tutti gli autenticati)
            client.election.active().then(data => {
                if (!data.error && data.id) {
                    setConsultazione(data);
                }
                setConsultazioneLoaded(true);
            }).catch(() => {
                setConsultazioneLoaded(true);
            });
        }
    }, [client, isAuthenticated, permissions.can_manage_elections, permissions.can_manage_delegations, permissions.is_superuser]);

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

    // Auto-register FCM token on every app start (best practice: tokens can change)
    useEffect(() => {
        if (!isAuthenticated || !client) return;
        if (Notification.permission !== 'granted') return;

        (async () => {
            try {
                const { requestPushToken } = await import('./firebase');
                const token = await requestPushToken();
                if (token) {
                    await client.me.registerDeviceToken(token, 'WEB');
                    console.log('FCM token registered');
                }
            } catch (err) {
                console.warn('FCM token registration failed:', err);
            }
        })();
    }, [isAuthenticated, client]);

    // Firebase foreground message handler
    useEffect(() => {
        if (!isAuthenticated) return;

        const unsubscribe = onForegroundMessage((msg) => {
            // Show OS notification even when app is in foreground
            if (Notification.permission === 'granted' && navigator.serviceWorker?.controller) {
                navigator.serviceWorker.ready.then(reg => {
                    reg.showNotification(msg.title, {
                        body: msg.body,
                        icon: '/icon-192.png',
                        data: msg.data,
                        tag: msg.data?.notification_id || 'foreground',
                    });
                });
            }
            // Also show in-app toast
            setApiToast(null);
            setTimeout(() => {
                setApiToast(`${msg.title}: ${msg.body}`);
                setTimeout(() => setApiToast(null), 5000);
            }, 50);
        });

        return unsubscribe;
    }, [isAuthenticated]);

    // Handle deep link messages from service worker
    useEffect(() => {
        const handler = (event) => {
            if (event.data?.type === 'NOTIFICATION_CLICK') {
                const link = event.data.deep_link;
                const eventMatch = link?.match(/^\/events\/([a-f0-9-]+)/);
                const assignmentMatch = link?.match(/^\/assignments\/(\d+)/);

                if (eventMatch) {
                    setDeepLinkEventId(eventMatch[1]);
                    activate('event-detail');
                } else if (assignmentMatch) {
                    setDeepLinkAssignmentId(assignmentMatch[1]);
                    activate('assignment-detail');
                }
            }
        };

        navigator.serviceWorker?.addEventListener('message', handler);
        return () => navigator.serviceWorker?.removeEventListener('message', handler);
    }, []);

    // Service worker is registered by firebase.js when requesting push token

    // Handle deep link navigation from dashboard widget
    useEffect(() => {
        const handler = (e) => {
            const { type, id } = e.detail;
            if (type === 'event') {
                setDeepLinkEventId(id);
            } else if (type === 'assignment') {
                setDeepLinkAssignmentId(id);
            }
        };
        window.addEventListener('navigate-deep-link', handler);
        return () => window.removeEventListener('navigate-deep-link', handler);
    }, []);

    // Check for contributions (to enable "Diretta")
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

    const toggleTheme = () => {
        setTheme(prevTheme => prevTheme === 'daily' ? 'night' : 'daily');
    };

    const handleCloseCampagna = () => {
        setCampagnaSlug(null);
        // Update URL back to home
        window.history.replaceState({}, document.title, '/');
    };

    const toggleMenu = () => {
        setIsMenuOpen(prev => !prev);
    };

    // Lock body scroll when mobile menu is open
    useEffect(() => {
        document.body.style.overflow = isMenuOpen ? 'hidden' : '';
        return () => { document.body.style.overflow = ''; };
    }, [isMenuOpen]);

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

    // Browser back/forward button support
    useEffect(() => {
        const onPopState = (event) => {
            if (event.state && event.state.tab) {
                setActiveTab(event.state.tab);
                setIsMenuOpen(false);
                setError(null);
            } else {
                // Prevent exiting the app - stay on current tab
                const tab = activeTabRef.current || 'dashboard';
                window.history.pushState({ tab }, '');
            }
        };

        // Prevent href="#" from adding extra history entries
        const preventHashNav = (e) => {
            if (e.target.closest('a[href="#"]')) {
                e.preventDefault();
            }
        };

        window.addEventListener('popstate', onPopState);
        document.addEventListener('click', preventHashNav);
        return () => {
            window.removeEventListener('popstate', onPopState);
            document.removeEventListener('click', preventHashNav);
        };
    }, []);

    const activate = (tab) => {
        // Close campaign registration if open
        if (campagnaSlug) {
            setCampagnaSlug(null);
            window.history.replaceState({}, document.title, '/');
        }
        window.history.pushState({ tab }, '');
        setActiveTab(tab);
        setIsMenuOpen(false);
        setError(null);

        // Scroll to top quando si cambia pagina (importante per mobile)
        window.scrollTo({ top: 0, behavior: 'smooth' });
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
                                        {/* 1. DASHBOARD - solo per chi può vederla */}
                                        {permissions.can_view_dashboard && (
                                            <li className="nav-item">
                                                <a className={`nav-link ${activeTab === 'dashboard' ? 'active' : ''}`}
                                                   onClick={() => activate('dashboard')} href="#">
                                                    <i className="fas fa-home me-1"></i>
                                                    Home
                                                </a>
                                            </li>
                                        )}

                                        {/* 2. TERRITORIO - gestione territorio (admin) */}
                                        {permissions.can_manage_territory && (
                                            <li className="nav-item">
                                                <a className={`nav-link ${activeTab === 'territorio_admin' ? 'active' : ''}`}
                                                   onClick={() => activate('territorio_admin')} href="#">
                                                    <i className="fas fa-globe-europe me-1"></i>
                                                    Territorio
                                                </a>
                                            </li>
                                        )}

                                        {/* 3. CONSULTAZIONE - Menu dinamico con tipologie elezione (solo per chi gestisce elezioni) */}
                                        {consultazione && permissions.can_manage_elections && consultazione.schede && consultazione.schede.length > 0 && (
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
                                                                <span className="me-2 scheda-color-indicator" style={{
                                                                    backgroundColor: scheda.colore || 'var(--color-gray-300)'
                                                                }}></span>
                                                                {scheda.nome}
                                                            </a>
                                                        </li>
                                                    ))}
                                                </ul>
                                            </li>
                                        )}

                                        {/* 4. RDL - Menu gestione RDL */}
                                        {(permissions.can_manage_campaign || permissions.can_manage_rdl || permissions.can_manage_mass_email || permissions.can_manage_sections || permissions.can_manage_mappatura || permissions.can_manage_events) && (
                                            <li className="nav-item dropdown">
                                                <a className={`nav-link dropdown-toggle ${['campagne', 'gestione_rdl', 'mass_email', 'sezioni', 'mappatura-gerarchica', 'eventi'].includes(activeTab) ? 'active' : ''}`}
                                                   href="#"
                                                   role="button"
                                                   onClick={(e) => { e.preventDefault(); closeAllDropdowns(); setIsRdlDropdownOpen(!isRdlDropdownOpen); }}
                                                   aria-expanded={isRdlDropdownOpen}>
                                                    <i className="fas fa-users me-1"></i>
                                                    RDL
                                                </a>
                                                <ul className={`dropdown-menu dropdown-menu-dark ${isRdlDropdownOpen ? 'show' : ''}`}>
                                                    {permissions.can_manage_campaign && (
                                                        <li>
                                                            <a className={`dropdown-item ${activeTab === 'campagne' ? 'active' : ''}`}
                                                               onClick={() => { activate('campagne'); closeAllDropdowns(); }} href="#">
                                                                <i className="fas fa-bullhorn me-2"></i>
                                                                Campagne
                                                            </a>
                                                        </li>
                                                    )}
                                                    {permissions.can_manage_rdl && (
                                                        <li>
                                                            <a className={`dropdown-item ${activeTab === 'gestione_rdl' ? 'active' : ''}`}
                                                               onClick={() => { activate('gestione_rdl'); closeAllDropdowns(); }} href="#">
                                                                <i className="fas fa-user-check me-2"></i>
                                                                Gestione RDL
                                                            </a>
                                                        </li>
                                                    )}
                                                    {permissions.can_manage_mass_email && (
                                                        <li>
                                                            <a className={`dropdown-item ${activeTab === 'mass_email' ? 'active' : ''}`}
                                                               onClick={() => { activate('mass_email'); closeAllDropdowns(); }} href="#">
                                                                <i className="fas fa-paper-plane me-2"></i>
                                                                Mass Mail
                                                            </a>
                                                        </li>
                                                    )}
                                                    {permissions.can_manage_events && (
                                                        <li>
                                                            <a className={`dropdown-item ${activeTab === 'eventi' ? 'active' : ''}`}
                                                               onClick={() => { activate('eventi'); closeAllDropdowns(); }} href="#">
                                                                <i className="fas fa-calendar-alt me-2"></i>
                                                                Eventi
                                                            </a>
                                                        </li>
                                                    )}
                                                    {permissions.can_manage_sections && (
                                                        <li>
                                                            <a className={`dropdown-item ${activeTab === 'sezioni' ? 'active' : ''}`}
                                                               onClick={() => { activate('sezioni'); closeAllDropdowns(); }} href="#">
                                                                <i className="fas fa-map-marker-alt me-2"></i>
                                                                Gestione Sezioni
                                                            </a>
                                                        </li>
                                                    )}
                                                    {consultazione && permissions.can_manage_mappatura && (
                                                        <li>
                                                            <a className={`dropdown-item ${activeTab === 'mappatura-gerarchica' ? 'active' : ''}`}
                                                               onClick={() => { activate('mappatura-gerarchica'); closeAllDropdowns(); }} href="#">
                                                                <i className="fas fa-sitemap me-2"></i>
                                                                Mappatura
                                                            </a>
                                                        </li>
                                                    )}
                                                </ul>
                                            </li>
                                        )}

                                        {/* 5. DELEGATI - Catena deleghe e designazioni */}
                                        {(permissions.can_manage_delegations || permissions.can_manage_designazioni || permissions.can_manage_templates) && (
                                            <li className="nav-item dropdown">
                                                <a className={`nav-link dropdown-toggle ${['deleghe', 'designazioni', 'template_list', 'template_editor'].includes(activeTab) ? 'active' : ''}`}
                                                   href="#"
                                                   role="button"
                                                   onClick={(e) => { e.preventDefault(); closeAllDropdowns(); setIsDelegheDropdownOpen(!isDelegheDropdownOpen); }}
                                                   aria-expanded={isDelegheDropdownOpen}>
                                                    <i className="fas fa-user-tie me-1"></i>
                                                    Delegati
                                                </a>
                                                <ul className={`dropdown-menu dropdown-menu-dark ${isDelegheDropdownOpen ? 'show' : ''}`}>
                                                    {permissions.can_manage_delegations && (
                                                        <li>
                                                            <a className={`dropdown-item ${activeTab === 'deleghe' ? 'active' : ''}`}
                                                               onClick={() => { activate('deleghe'); closeAllDropdowns(); }} href="#">
                                                                <i className="fas fa-sitemap me-2"></i>
                                                                Catena Deleghe
                                                            </a>
                                                        </li>
                                                    )}
                                                    {permissions.can_manage_designazioni && (
                                                        <li>
                                                            <a className={`dropdown-item ${activeTab === 'designazioni' ? 'active' : ''}`}
                                                               onClick={() => { activate('designazioni'); closeAllDropdowns(); }} href="#">
                                                                <i className="fas fa-user-check me-2"></i>
                                                                Designazioni
                                                            </a>
                                                        </li>
                                                    )}
                                                    {consultazione && permissions.can_manage_templates && (
                                                        <li>
                                                            <a className={`dropdown-item ${activeTab === 'template_list' ? 'active' : ''}`}
                                                               onClick={() => { activate('template_list'); setTemplateIdToEdit(null); closeAllDropdowns(); }} href="#">
                                                                <i className="fas fa-file-pdf me-2"></i>
                                                                Template PDF
                                                            </a>
                                                        </li>
                                                    )}
                                                </ul>
                                            </li>
                                        )}

                                        {/* 6. SCRUTINIO */}
                                        {consultazione && permissions.has_scrutinio_access && (
                                            <li className="nav-item">
                                                <a className={`nav-link ${activeTab === 'sections' ? 'active' : ''}`}
                                                   onClick={() => activate('sections')} href="#">
                                                    <i className="fas fa-clipboard-check me-1"></i>
                                                    Scrutinio
                                                </a>
                                            </li>
                                        )}

                                        {/* 8. RISORSE - documenti e materiali */}
                                        {permissions.can_view_resources && (
                                            <li className="nav-item">
                                                <a className={`nav-link ${activeTab === 'risorse' ? 'active' : ''}`}
                                                   onClick={() => activate('risorse')} href="#">
                                                    <i className="fas fa-folder-open me-1"></i>
                                                    Risorse
                                                </a>
                                            </li>
                                        )}

                                        {/* 9. RISULTATI LIVE - scrutinio aggregato */}
                                        {consultazione && permissions.can_view_live_results && (
                                            <li className="nav-item">
                                                <a className={`nav-link ${activeTab === 'scrutinio-aggregato' ? 'active' : ''}`}
                                                   onClick={() => activate('scrutinio-aggregato')} href="#">
                                                    <i className="fas fa-chart-line me-1"></i>
                                                    Live <span className="pulse-indicator pulse-indicator-success"></span>
                                                </a>
                                            </li>
                                        )}

                                        {/* 7. DIRETTA (KPI) - visibile solo per elezioni (non referendum) */}
                                        {consultazione && permissions.can_view_kpi && consultazione.has_subdelegations !== false && (
                                            <li className="nav-item">
                                                <a className={`nav-link ${activeTab === 'kpi' ? 'active' : ''}`}
                                                   onClick={() => activate('kpi')} href="#">
                                                    <i className="fas fa-chart-line me-1"></i>
                                                    Diretta <span className="pulse-indicator pulse-indicator-danger"></span>
                                                </a>
                                            </li>
                                        )}
                                    </ul>

                                    {/* User Menu - Separato per allineamento destro su desktop */}
                                    <ul className="navbar-nav ms-auto">
                                        <li className="nav-item dropdown">
                                            <a className="nav-link dropdown-toggle d-flex align-items-center"
                                               href="#"
                                               role="button"
                                               onClick={(e) => { e.preventDefault(); closeAllDropdowns(); setIsUserMenuOpen(!isUserMenuOpen); }}
                                               aria-expanded={isUserMenuOpen}
                                               title={displayName}>
                                                <i className="fas fa-user-circle me-2" style={{ fontSize: '1.2rem' }}></i>
                                                <span className="d-lg-none">{displayName}</span>
                                            </a>
                                            <ul className={`dropdown-menu dropdown-menu-dark user-menu-dropdown ${isUserMenuOpen ? 'show' : ''}`}>
                                            {/* User Info Header */}
                                            <li>
                                                {isImpersonating ? (
                                                    <div className="dropdown-header">
                                                        <div className="d-flex align-items-center mb-1">
                                                            <i className="fas fa-user-secret me-2 text-warning"></i>
                                                            <small className="text-warning fw-bold">Impersonando</small>
                                                        </div>
                                                        <div className="text-white">{user?.email}</div>
                                                        {originalUser && (
                                                            <div className="mt-1">
                                                                <small className="text-white-50">
                                                                    <i className="fas fa-user me-1"></i>
                                                                    Tu sei: {originalUser.email}
                                                                </small>
                                                            </div>
                                                        )}
                                                    </div>
                                                ) : (
                                                    <h6 className="dropdown-header d-flex align-items-center">
                                                        <i className="fas fa-user me-2"></i>
                                                        {displayName}
                                                    </h6>
                                                )}
                                            </li>
                                            <li><hr className="dropdown-divider" /></li>

                                            {/* Theme Toggle */}
                                            <li>
                                                <a className="dropdown-item d-flex align-items-center justify-content-between"
                                                   href="#"
                                                   onClick={(e) => {
                                                       e.preventDefault();
                                                       toggleTheme();
                                                       closeAllDropdowns();
                                                       setIsMenuOpen(false);
                                                   }}>
                                                    <span>
                                                        <i className={`fas ${theme === 'night' ? 'fa-sun' : 'fa-moon'} me-2`}></i>
                                                        {theme === 'night' ? 'Tema Daily' : 'Tema Night'}
                                                    </span>
                                                    <span>{theme === 'night' ? '☀️' : '🌙'}</span>
                                                </a>
                                            </li>

                                            {/* Impersonate (admin only) */}
                                            {user?.is_superuser && !isImpersonating && (
                                                <>
                                                    <li><hr className="dropdown-divider" /></li>
                                                    <li>
                                                        <a className="dropdown-item d-flex align-items-center"
                                                           href="#"
                                                           onClick={(e) => {
                                                               e.preventDefault();
                                                               setShowImpersonate(!showImpersonate);
                                                               closeAllDropdowns();
                                                               setIsMenuOpen(false);
                                                           }}>
                                                            <i className="fas fa-user-secret me-2 text-warning"></i>
                                                            Impersona utente
                                                        </a>
                                                    </li>
                                                </>
                                            )}

                                            {/* Logout / Stop Impersonating */}
                                            <li><hr className="dropdown-divider" /></li>
                                            <li>
                                                {isImpersonating ? (
                                                    <a className="dropdown-item d-flex align-items-center text-warning"
                                                       href="#"
                                                       onClick={(e) => {
                                                           e.preventDefault();
                                                           handleStopImpersonating();
                                                           closeAllDropdowns();
                                                           setIsMenuOpen(false);
                                                       }}>
                                                        <i className="fas fa-user-check me-2"></i>
                                                        Torna al tuo account
                                                    </a>
                                                ) : (
                                                    <a className="dropdown-item d-flex align-items-center text-danger"
                                                       href="#"
                                                       onClick={(e) => {
                                                           e.preventDefault();
                                                           handleSignoutClick();
                                                           closeAllDropdowns();
                                                           setIsMenuOpen(false);
                                                       }}>
                                                        <i className="fas fa-sign-out-alt me-2"></i>
                                                        Esci
                                                    </a>
                                                )}
                                            </li>
                                        </ul>
                                    </li>
                                </ul>
                            </div>
                            </>
                        )}
                    </div>
                </nav>
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
                        {/* Solo chi può gestire elezioni o delegazioni può switchare consultazione */}
                        {(permissions.can_manage_elections || permissions.can_manage_delegations || permissions.is_superuser) ? (
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
                {error && (
                    <div className="alert alert-danger mt-3 d-flex align-items-center justify-content-between">
                        <span>{error}</span>
                        <button type="button" className="btn-close" aria-label="Chiudi" onClick={() => setError(null)}></button>
                    </div>
                )}
                {showPdfConfirm ? (
                    <PDFConfirmPage serverApi={SERVER_API} />
                ) : campagnaSlug ? (
                    <CampagnaRegistration slug={campagnaSlug} onClose={handleCloseCampagna} isAuthenticated={isAuthenticated} isSuperuser={user?.is_superuser} />
                ) : isAuthenticated && client && consultazione ? (
                    <div>
                        <div className="tab-content">
                            {activeTab === 'dashboard' && (
                                <div className="tab-pane active">
                                    <PwaOnboarding client={client} />
                                    <Dashboard
                                        user={user}
                                        permissions={permissions}
                                        consultazione={consultazione}
                                        onNavigate={activate}
                                        client={client}
                                    />
                                </div>
                            )}
                            {activeTab === 'scheda' && selectedScheda && permissions.can_manage_elections && (
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
                            {activeTab === 'sections' && permissions.has_scrutinio_access && (
                                <div className="tab-pane active">
                                    <SectionList
                                        user={user}
                                        client={client}
                                        setError={setError}
                                        referenti={permissions.can_manage_elections}
                                    />
                                </div>
                            )}
                            {activeTab === 'scrutinio-aggregato' && permissions.can_view_live_results && (
                                <div className="tab-pane active">
                                    <ScrutinioAggregato
                                        client={client}
                                        consultazione={consultazione}
                                        setError={setError}
                                    />
                                </div>
                            )}
                            {activeTab === 'mappatura-gerarchica' && permissions.can_manage_mappatura && (
                                <div className="tab-pane active">
                                    <MappaturaGerarchica
                                        client={client}
                                        setError={setError}
                                        consultazione={consultazione}
                                    />
                                </div>
                            )}
                            {activeTab === 'kpi' && permissions.can_view_kpi && (
                                <div className="tab-pane active">
                                    <Kpi
                                        client={client}
                                        setError={setError}
                                        consultazione={consultazione}
                                    />
                                </div>
                            )}
                            {activeTab === 'sezioni' && permissions.can_manage_sections && (
                                <div className="tab-pane active">
                                    <GestioneSezioni
                                        client={client}
                                        setError={setError}
                                    />
                                </div>
                            )}
                            {activeTab === 'gestione_rdl' && permissions.can_manage_rdl && (
                                <div className="tab-pane active">
                                    <GestioneRdl
                                        client={client}
                                        setError={setError}
                                    />
                                </div>
                            )}
                            {activeTab === 'mass_email' && permissions.can_manage_mass_email && (
                                <div className="tab-pane active">
                                    <MassEmail
                                        client={client}
                                        consultazione={consultazione}
                                    />
                                </div>
                            )}
                            {activeTab === 'deleghe' && permissions.can_manage_delegations && (
                                <div className="tab-pane active">
                                    <GestioneDeleghe
                                        client={client}
                                        user={user}
                                        consultazione={consultazione}
                                        setError={setError}
                                    />
                                </div>
                            )}
                            {activeTab === 'designazioni' && permissions.can_manage_designazioni && (
                                <div className="tab-pane active">
                                    <GestioneDesignazioni
                                        client={client}
                                        consultazione={consultazione}
                                        setError={setError}
                                    />
                                </div>
                            )}
                            {activeTab === 'campagne' && permissions.can_manage_campaign && (
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
                            {activeTab === 'risorse' && permissions.can_view_resources && (
                                <div className="tab-pane active">
                                    <Risorse
                                        client={client}
                                        consultazione={consultazione}
                                        setError={setError}
                                    />
                                </div>
                            )}
                            {activeTab === 'eventi' && permissions.can_manage_events && (
                                <div className="tab-pane active">
                                    <EventList
                                        client={client}
                                        consultazione={consultazione}
                                    />
                                </div>
                            )}
                            {activeTab === 'event-detail' && deepLinkEventId && (
                                <div className="tab-pane active">
                                    <button className="btn btn-secondary mb-3" onClick={() => activate('dashboard')}>
                                        <i className="fas fa-arrow-left me-1"></i> Torna alla dashboard
                                    </button>
                                    <EventDetail
                                        eventId={deepLinkEventId}
                                        client={client}
                                    />
                                </div>
                            )}
                            {activeTab === 'assignment-detail' && deepLinkAssignmentId && (
                                <div className="tab-pane active">
                                    <button className="btn btn-secondary mb-3" onClick={() => activate('dashboard')}>
                                        <i className="fas fa-arrow-left me-1"></i> Torna alla dashboard
                                    </button>
                                    <AssignmentDetail
                                        assignmentId={deepLinkAssignmentId}
                                        client={client}
                                    />
                                </div>
                            )}
                            {activeTab === 'territorio_admin' && permissions.can_manage_territory && (
                                <div className="tab-pane active">
                                    <GestioneTerritorio
                                        client={client}
                                        setError={setError}
                                    />
                                </div>
                            )}
                            {activeTab === 'template_list' && consultazione && permissions.can_manage_templates && (
                                <div className="tab-pane active">
                                    <TemplateList
                                        client={client}
                                        onEditTemplate={(id) => {
                                            setTemplateIdToEdit(id);
                                            window.history.pushState({ tab: 'template_editor' }, '');
                                            setActiveTab('template_editor');
                                        }}
                                    />
                                </div>
                            )}
                            {activeTab === 'template_editor' && consultazione && permissions.can_manage_templates && templateIdToEdit && (
                                <div className="tab-pane active">
                                    <div style={{ marginBottom: '15px' }}>
                                        <button
                                            className="btn btn-secondary"
                                            onClick={() => {
                                                window.history.back();
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
                        <div className="card-header bg-referendum text-white">
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
                                            className="btn btn-referendum btn-lg w-100"
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
                                            onClick={() => {
                                                const registrationUrl = import.meta.env.VITE_RDL_REGISTRATION_URL || 'https://forms.gle/sLzS7fABZNXeUUnC9';
                                                window.open(registrationUrl, '_blank');
                                            }}
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
                        © Simone Federici (GT XV ROMA)
                    </p>
                </div>
            </footer>

            {/* FAB: Floating Action Button for AI Chat */}
            {isAuthenticated && permissions.can_ask_to_ai_assistant && (
                <button
                    className="chat-fab"
                    onClick={() => setShowChat(true)}
                    title="Assistente AI"
                >
                    <i className="fas fa-robot"></i>
                </button>
            )}

            {/* Chat Interface Modal */}
            {client && (
                <ChatInterface
                    client={client}
                    show={showChat}
                    onClose={() => setShowChat(false)}
                />
            )}

            {/* Global API error toast */}
            {apiToast && (
                <div style={{
                    position: 'fixed', bottom: 20, left: '50%', transform: 'translateX(-50%)',
                    background: '#dc3545', color: '#fff', padding: '10px 24px',
                    borderRadius: 8, fontSize: '0.9rem', zIndex: 9999,
                    boxShadow: '0 4px 12px rgba(0,0,0,0.3)', cursor: 'pointer',
                    maxWidth: '90vw', textAlign: 'center'
                }} onClick={() => setApiToast(null)}>
                    {apiToast}
                </div>
            )}
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
