import React, { useState, useEffect } from 'react';
import SezzionePlessAutocomplete from './SezzionePlessAutocomplete';

// Use empty string to leverage Vite proxy in development (vite.config.js)
// In production, use empty string for same-origin requests
const SERVER_API = '';

// Eligibility requirements by election type
const REQUISITI_ELETTORE = {
    COMUNALI: {
        label: 'Comunali',
        requisito: 'Elettore dello stesso Comune',
        descrizione: 'Il RDL deve essere iscritto nelle liste elettorali del comune dove intende operare.'
    },
    REGIONALI: {
        label: 'Regionali',
        requisito: 'Elettore della stessa Regione',
        descrizione: 'Il RDL deve essere elettore di un qualsiasi comune della stessa regione.'
    },
    POLITICHE_CAMERA: {
        label: 'Politiche Camera',
        requisito: 'Elettore della stessa Circoscrizione',
        descrizione: 'Il RDL deve essere elettore di un comune della stessa circoscrizione elettorale (26 circoscrizioni).'
    },
    POLITICHE_SENATO: {
        label: 'Politiche Senato',
        requisito: 'Elettore della stessa Regione',
        descrizione: 'Il RDL deve essere elettore di un comune della stessa circoscrizione regionale (20 circoscrizioni = regioni).'
    },
    EUROPEE: {
        label: 'Europee',
        requisito: 'Elettore della stessa Circoscrizione Europea',
        descrizione: 'Il RDL deve essere elettore di un comune della stessa circoscrizione europea (5 circoscrizioni: Nord-Ovest, Nord-Est, Centro, Sud, Isole).'
    },
    REFERENDUM: {
        label: 'Referendum',
        requisito: 'Elettore di qualsiasi Comune italiano',
        descrizione: 'Il RDL può essere un elettore di qualsiasi comune italiano.'
    }
};

function CampagnaRegistration({ slug, onClose, isAuthenticated, isSuperuser }) {
    const [formData, setFormData] = useState({
        email: '',
        cognome: '',
        nome: '',
        comune_nascita: '',
        data_nascita: '',
        comune_residenza: '',
        indirizzo_residenza: '',
        seggio_preferenza: '',
        municipio: '',
        telefono: '',
        fuorisede: null,
        comune_domicilio: '',
        indirizzo_domicilio: ''
    });
    const [selectedComune, setSelectedComune] = useState(null);
    const [selectedSezione, setSelectedSezione] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(false);
    const [campagna, setCampagna] = useState(null);
    const [checkingStatus, setCheckingStatus] = useState(true);
    const [comuneSearch, setComuneSearch] = useState('');
    const [gdprAccepted, setGdprAccepted] = useState(false);

    // Test data for superadmin auto-fill
    const COLORI_ITALIANI = [
        'Rosso', 'Blu', 'Verde', 'Giallo', 'Arancione', 'Viola', 'Rosa',
        'Marrone', 'Grigio', 'Nero', 'Bianco', 'Azzurro', 'Indaco', 'Turchese',
        'Magenta', 'Ciano', 'Beige', 'Cremisi', 'Corallo', 'Smeraldo'
    ];

    const fillTestData = () => {
        // Random color names for cognome and nome
        const cognome = COLORI_ITALIANI[Math.floor(Math.random() * COLORI_ITALIANI.length)];
        let nome = COLORI_ITALIANI[Math.floor(Math.random() * COLORI_ITALIANI.length)];
        // Make sure nome is different from cognome
        while (nome === cognome) {
            nome = COLORI_ITALIANI[Math.floor(Math.random() * COLORI_ITALIANI.length)];
        }

        // Today's date in YYYY-MM-DD format
        const today = new Date();
        const birthYear = 1970 + Math.floor(Math.random() * 35); // 1970-2005
        const birthDate = `${birthYear}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

        // Random phone
        const phone = `3${Math.floor(Math.random() * 10)}${Math.floor(Math.random() * 10000000).toString().padStart(7, '0')}`;

        // Random email using color name
        const email = `${nome.toLowerCase()}.${cognome.toLowerCase()}${Math.floor(Math.random() * 100)}@test.it`;

        // Find Rome in available comuni
        const romaComune = campagna?.comuni_disponibili?.find(c =>
            c.nome?.toLowerCase() === 'roma' ||
            c.label?.toLowerCase().includes('roma') ||
            c.codice_istat === '058091'
        );

        // 30% chance of being fuorisede
        const isFuorisede = Math.random() > 0.7;

        // Set form data
        setFormData({
            email: email,
            cognome: cognome,
            nome: nome,
            comune_nascita: 'Roma',
            data_nascita: birthDate,
            comune_residenza: isFuorisede ? 'Napoli' : 'Roma', // If fuorisede, residence is elsewhere
            indirizzo_residenza: `Via ${COLORI_ITALIANI[Math.floor(Math.random() * COLORI_ITALIANI.length)]} ${Math.floor(Math.random() * 200) + 1}`,
            seggio_preferenza: '',
            municipio: romaComune?.has_municipi ? String(Math.floor(Math.random() * 15) + 1) : '',
            telefono: phone,
            fuorisede: isFuorisede,
            comune_domicilio: isFuorisede ? 'Roma' : '',
            indirizzo_domicilio: isFuorisede ? `Via ${COLORI_ITALIANI[Math.floor(Math.random() * COLORI_ITALIANI.length)]} ${Math.floor(Math.random() * 200) + 1}` : ''
        });

        // If Rome is available, select it
        if (romaComune) {
            setSelectedComune(romaComune);
            setComuneSearch(romaComune.label || romaComune.nome);
        }

        // Accept GDPR
        setGdprAccepted(true);
    };

    useEffect(() => {
        loadCampagna();
    }, [slug]);

    // Auto-select comune if only one is available
    useEffect(() => {
        if (campagna?.comuni_disponibili?.length === 1 && !selectedComune) {
            setSelectedComune(campagna.comuni_disponibili[0]);
            setComuneSearch(campagna.comuni_disponibili[0].label || campagna.comuni_disponibili[0].nome);
        }
    }, [campagna, selectedComune]);

    const loadCampagna = async () => {
        try {
            const response = await fetch(`${SERVER_API}/api/campagna/${slug}/`);
            if (!response.ok) {
                if (response.status === 404) {
                    setCampagna({ error: 'Campagna non trovata' });
                } else {
                    throw new Error('Errore caricamento campagna');
                }
            } else {
                const data = await response.json();
                setCampagna(data);
            }
        } catch (err) {
            setCampagna({ error: 'Errore caricamento campagna' });
        } finally {
            setCheckingStatus(false);
        }
    };

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleComuneSelect = (comune) => {
        setSelectedComune(comune);
        setComuneSearch(comune.label || comune.nome);
        // Reset municipio and sezione when comune changes
        setFormData(prev => ({ ...prev, municipio: '', seggio_preferenza: '' }));
        setSelectedSezione(null);
    };

    // Monitor municipio changes and clear sezione if incoherent
    useEffect(() => {
        if (selectedSezione && selectedSezione.municipio && formData.municipio) {
            // If sezione has a municipio and user selected a different one, clear the sezione
            if (parseInt(formData.municipio) !== selectedSezione.municipio.numero) {
                setSelectedSezione(null);
                setFormData(prev => ({ ...prev, seggio_preferenza: '' }));
            }
        }
    }, [formData.municipio, selectedSezione]);

    const handleSezioneChange = (sezione) => {
        if (!sezione) {
            // Cleared selection
            setSelectedSezione(null);
            setFormData(prev => ({ ...prev, seggio_preferenza: '' }));
        } else if (sezione.freeText) {
            // Free text input (user typed something without selecting from suggestions)
            setSelectedSezione(null);
            setFormData(prev => ({ ...prev, seggio_preferenza: sezione.text }));
        } else {
            // Selected from autocomplete suggestions
            setSelectedSezione(sezione);
            const parts = [`Sez. ${sezione.numero}`];
            if (sezione.denominazione) parts.push(sezione.denominazione);
            if (sezione.indirizzo) parts.push(sezione.indirizzo);
            setFormData(prev => ({ ...prev, seggio_preferenza: parts.join(' - ') }));
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        if (!selectedComune) {
            setError('Seleziona il comune del seggio');
            setLoading(false);
            return;
        }

        // Municipio is required if the comune has municipalities
        if (selectedComune.has_municipi && selectedComune.municipi?.length > 0 && !formData.municipio) {
            setError('Seleziona un municipio');
            setLoading(false);
            return;
        }

        // Fuorisede selection is required
        if (formData.fuorisede === null) {
            setError('Devi indicare se sei un fuorisede');
            setLoading(false);
            return;
        }

        // If fuorisede is true, domicilio fields are required
        if (formData.fuorisede === true) {
            if (!formData.comune_domicilio) {
                setError('Inserisci il comune di domicilio');
                setLoading(false);
                return;
            }
            if (!formData.indirizzo_domicilio) {
                setError('Inserisci l\'indirizzo di domicilio');
                setLoading(false);
                return;
            }
        }

        // GDPR acceptance is required
        if (!gdprAccepted) {
            setError('Devi accettare il trattamento dei dati personali per continuare');
            setLoading(false);
            return;
        }

        try {
            const response = await fetch(`${SERVER_API}/api/campagna/${slug}/registra/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ...formData,
                    comune_id: selectedComune.id,
                    municipio: formData.municipio ? parseInt(formData.municipio) : null
                })
            });

            const data = await response.json();

            if (!response.ok || data.error) {
                throw new Error(data.error || JSON.stringify(data) || 'Errore durante la registrazione');
            }

            setSuccess(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    // Filter comuni based on search
    const filteredComuni = campagna?.comuni_disponibili?.filter(c =>
        c.label?.toLowerCase().includes(comuneSearch.toLowerCase()) ||
        c.nome?.toLowerCase().includes(comuneSearch.toLowerCase())
    ) || [];

    if (checkingStatus) {
        return (
            <div className="loading-container" role="status" aria-live="polite">
                <div className="spinner-border text-primary">
                    <span className="visually-hidden">Caricamento...</span>
                </div>
                <p className="loading-text">Caricamento campagna...</p>
            </div>
        );
    }

    if (campagna?.error) {
        return (
            <div className="card">
                <div className="card-header bg-danger text-white">
                    Campagna non trovata
                </div>
                <div className="card-body">
                    <p className="text-muted">{campagna.error}</p>
                </div>
            </div>
        );
    }

    if (!campagna?.is_aperta) {
        return (
            <div className="card">
                <div className="card-header bg-secondary text-white">
                    Campagna chiusa
                </div>
                <div className="card-body">
                    <h5>{campagna.nome}</h5>
                    <p className="text-muted">
                        Questa campagna di reclutamento non è attualmente aperta.
                    </p>
                    {campagna.data_apertura && (
                        <p className="text-muted">
                            <strong>Periodo:</strong> {new Date(campagna.data_apertura).toLocaleDateString('it-IT')} - {new Date(campagna.data_chiusura).toLocaleDateString('it-IT')}
                        </p>
                    )}
                </div>
            </div>
        );
    }

    if (campagna.posti_disponibili !== null && campagna.posti_disponibili <= 0) {
        return (
            <div className="card">
                <div className="card-header bg-warning text-dark">
                    Posti esauriti
                </div>
                <div className="card-body">
                    <h5>{campagna.nome}</h5>
                    <p className="text-muted">
                        I posti per questa campagna sono esauriti.
                    </p>
                </div>
            </div>
        );
    }

    if (success) {
        return (
            <div className="card border-0 shadow-sm">
                {/* Hero Section - Success gradient */}
                <div
                    className="text-white text-center py-5 px-4"
                    style={{
                        background: 'linear-gradient(135deg, #198754 0%, #157347 50%, #0f5132 100%)',
                        borderRadius: '0.375rem 0.375rem 0 0'
                    }}
                >
                    <div className="mb-3">
                        <i className="fas fa-check-circle" style={{ fontSize: '4rem', opacity: 0.9 }}></i>
                    </div>
                    <h1 className="display-5 fw-bold mb-2">
                        Grazie!
                    </h1>
                    <p className="lead mb-0" style={{ opacity: 0.95 }}>
                        La tua candidatura è stata registrata
                    </p>
                </div>

                <div className="card-body px-4 py-4">
                    {/* Personal thank you message */}
                    <div className="text-center mb-4">
                        <div
                            className="d-inline-block p-4 rounded-3 shadow-sm"
                            style={{
                                backgroundColor: '#e7f1ff',
                                border: '2px solid #0d6efd',
                                maxWidth: '500px'
                            }}
                        >
                            <i className="fas fa-heart text-danger mb-2" style={{ fontSize: '2rem' }}></i>
                            <p className="fs-5 mb-0 fw-medium" style={{ lineHeight: '1.6' }}>
                                {success.message || 'Grazie per aver dato la tua disponibilità!'}
                            </p>
                        </div>
                    </div>

                    {/* What happens next */}
                    <div className="mb-4">
                        <h5 className="text-center mb-3">
                            <i className="fas fa-route me-2 text-primary"></i>
                            Cosa succede ora?
                        </h5>
                        <div className="row g-3 justify-content-center">
                            <div className="col-md-4">
                                <div className="text-center p-3 bg-light rounded-3 h-100">
                                    <div className="rounded-circle bg-primary text-white d-inline-flex align-items-center justify-content-center mb-2" style={{ width: '40px', height: '40px' }}>
                                        <strong>1</strong>
                                    </div>
                                    <h6 className="fw-bold">Verifica</h6>
                                    <p className="small text-muted mb-0">
                                        {success.richiede_approvazione
                                            ? 'Il delegato verificherà la tua candidatura'
                                            : 'La tua candidatura è già stata approvata!'
                                        }
                                    </p>
                                </div>
                            </div>
                            <div className="col-md-4">
                                <div className="text-center p-3 bg-light rounded-3 h-100">
                                    <div className="rounded-circle bg-primary text-white d-inline-flex align-items-center justify-content-center mb-2" style={{ width: '40px', height: '40px' }}>
                                        <strong>2</strong>
                                    </div>
                                    <h6 className="fw-bold">Notifica</h6>
                                    <p className="small text-muted mb-0">
                                        Riceverai un'email con le istruzioni per accedere
                                    </p>
                                </div>
                            </div>
                            <div className="col-md-4">
                                <div className="text-center p-3 bg-light rounded-3 h-100">
                                    <div className="rounded-circle bg-primary text-white d-inline-flex align-items-center justify-content-center mb-2" style={{ width: '40px', height: '40px' }}>
                                        <strong>3</strong>
                                    </div>
                                    <h6 className="fw-bold">Formazione</h6>
                                    <p className="small text-muted mb-0">
                                        Ti invieremo materiale formativo per prepararti
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Consultation info */}
                    <div className="alert alert-info text-center mb-4">
                        <i className="fas fa-calendar-alt me-2"></i>
                        <strong>Consultazione:</strong> {campagna.consultazione_nome}
                    </div>

                    {/* Spread the word - Share section */}
                    <div
                        className="text-center p-4 rounded-3 mb-4"
                        style={{ backgroundColor: '#fff3cd', border: '1px solid #ffca2c' }}
                    >
                        <h5 className="mb-3">
                            <i className="fas fa-bullhorn me-2"></i>
                            Passa parola!
                        </h5>
                        <p className="mb-3">
                            Conosci altre persone che potrebbero voler diventare RDL?<br />
                            <strong>Ogni sezione ha bisogno di rappresentanti!</strong>
                        </p>
                        <div className="d-flex justify-content-center flex-wrap gap-2">
                            <a
                                href={`https://wa.me/?text=${encodeURIComponent(`Ho appena dato la mia disponibilità come Rappresentante di Lista per ${campagna.consultazione_nome}!\n\nVuoi partecipare anche tu? Registrati qui:\n${window.location.href}`)}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="btn btn-success"
                                title="Condividi su WhatsApp"
                            >
                                <i className="fab fa-whatsapp me-1"></i>
                                WhatsApp
                            </a>
                            <a
                                href={`https://www.facebook.com/sharer.php?u=${encodeURIComponent(window.location.href)}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="btn btn-primary"
                                title="Condividi su Facebook"
                                onClick={(e) => {
                                    e.preventDefault();
                                    window.open(
                                        `https://www.facebook.com/sharer.php?u=${encodeURIComponent(window.location.href)}`,
                                        'facebook-share',
                                        'width=580,height=400'
                                    );
                                }}
                            >
                                <i className="fab fa-facebook-f me-1"></i>
                                Facebook
                            </a>
                            <a
                                href={`https://t.me/share/url?url=${encodeURIComponent(window.location.href)}&text=${encodeURIComponent(`Diventa anche tu Rappresentante di Lista per ${campagna.consultazione_nome}!`)}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="btn btn-info text-white"
                                title="Condividi su Telegram"
                            >
                                <i className="fab fa-telegram-plane me-1"></i>
                                Telegram
                            </a>
                            <a
                                href={`mailto:?subject=${encodeURIComponent(`Diventa Rappresentante di Lista - ${campagna.consultazione_nome}`)}&body=${encodeURIComponent(`Ciao!\n\nHo appena dato la mia disponibilità come Rappresentante di Lista.\n\nTi segnalo questa iniziativa: ${campagna.nome}\n\nSe vuoi partecipare anche tu, registrati qui:\n${window.location.href}\n\nGrazie!`)}`}
                                className="btn btn-secondary"
                                title="Condividi via Email"
                            >
                                <i className="fas fa-envelope me-1"></i>
                                Email
                            </a>
                            <button
                                type="button"
                                className="btn btn-outline-dark"
                                onClick={() => {
                                    navigator.clipboard.writeText(window.location.href);
                                    alert('Link copiato! Condividilo con chi vuoi.');
                                }}
                                title="Copia link"
                            >
                                <i className="fas fa-copy me-1"></i>
                                Copia link
                            </button>
                        </div>
                    </div>

                    {/* Final message */}
                    <div className="text-center">
                        <p className="text-muted mb-3">
                            <i className="fas fa-shield-alt me-1"></i>
                            Insieme possiamo garantire elezioni trasparenti e regolari.
                        </p>
                        {isAuthenticated ? (
                            <button
                                type="button"
                                className="btn btn-outline-primary"
                                onClick={onClose}
                            >
                                <i className="fas fa-arrow-left me-1"></i>
                                Torna alla Dashboard
                            </button>
                        ) : (
                            <p className="small text-muted">
                                <i className="fas fa-check-circle text-success me-1"></i>
                                Puoi chiudere questa pagina. Ti contatteremo via email.
                            </p>
                        )}
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="card border-0 shadow-sm">
            {/* Hero Section - Full width gradient header */}
            <div
                className="text-white text-center py-5 px-4"
                style={{
                    background: 'linear-gradient(135deg, #0d6efd 0%, #0a58ca 50%, #084298 100%)',
                    borderRadius: '0.375rem 0.375rem 0 0'
                }}
            >
                <div className="mb-3">
                    <i className="fas fa-vote-yea" style={{ fontSize: '3rem', opacity: 0.9 }}></i>
                </div>
                <h1 className="display-5 fw-bold mb-2">
                    {campagna.nome}
                </h1>
                <p className="lead mb-0" style={{ opacity: 0.9 }}>
                    {campagna.consultazione_nome}
                </p>
            </div>

            <div className="card-body px-4 py-4">
                {/* Campaign description - prominent box */}
                {campagna.descrizione && (
                    <div
                        className="mb-4 p-4 rounded-3 shadow-sm"
                        style={{
                            backgroundColor: '#e7f1ff',
                            border: '2px solid #0d6efd'
                        }}
                    >
                        <div className="d-flex align-items-start">
                            <i className="fas fa-quote-left text-primary me-3 mt-1" style={{ fontSize: '1.5rem', opacity: 0.6 }}></i>
                            <p className="mb-0 fs-5" style={{ whiteSpace: 'pre-line', lineHeight: '1.8' }}>
                                {campagna.descrizione}
                            </p>
                        </div>
                    </div>
                )}

                {/* Value proposition */}
                <div className="text-center mb-4">
                    <h4 className="text-dark mb-4">
                        <strong>Perché diventare Rappresentante di Lista?</strong>
                    </h4>
                    <div className="row g-4 justify-content-center">
                        <div className="col-sm-6 col-lg-3">
                            <div className="p-3 h-100 rounded-3" style={{ backgroundColor: '#f8f9fa' }}>
                                <div className="text-primary mb-2">
                                    <i className="fas fa-shield-alt fa-2x"></i>
                                </div>
                                <h6 className="fw-bold">Tuteli la democrazia</h6>
                                <p className="small text-muted mb-0">Garantisci la regolarità del voto</p>
                            </div>
                        </div>
                        <div className="col-sm-6 col-lg-3">
                            <div className="p-3 h-100 rounded-3" style={{ backgroundColor: '#f8f9fa' }}>
                                <div className="text-primary mb-2">
                                    <i className="fas fa-users fa-2x"></i>
                                </div>
                                <h6 className="fw-bold">Partecipi attivamente</h6>
                                <p className="small text-muted mb-0">Diventi protagonista</p>
                            </div>
                        </div>
                        <div className="col-sm-6 col-lg-3">
                            <div className="p-3 h-100 rounded-3" style={{ backgroundColor: '#f8f9fa' }}>
                                <div className="text-primary mb-2">
                                    <i className="fas fa-graduation-cap fa-2x"></i>
                                </div>
                                <h6 className="fw-bold">Impari sul campo</h6>
                                <p className="small text-muted mb-0">Scopri come funziona</p>
                            </div>
                        </div>
                        <div className="col-sm-6 col-lg-3">
                            <div className="p-3 h-100 rounded-3" style={{ backgroundColor: '#f8f9fa' }}>
                                <div className="text-primary mb-2">
                                    <i className="fas fa-map-marker-alt fa-2x"></i>
                                </div>
                                <h6 className="fw-bold">Scegli dove</h6>
                                <p className="small text-muted mb-0">Vicino a te</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Reassurance banner */}
                <div className="alert alert-success text-center mb-4" role="alert">
                    <div className="d-flex align-items-center justify-content-center flex-wrap gap-3">
                        <span>
                            <i className="fas fa-clock me-1"></i>
                            Registrazione in <strong>2 minuti</strong>
                        </span>
                        <span className="text-muted">|</span>
                        <span>
                            <i className="fas fa-chalkboard-teacher me-1"></i>
                            <strong>Ti formiamo noi</strong>
                        </span>
                    </div>
                </div>

                {/* Share buttons */}
                <div className="text-center mb-4">
                    <p className="small text-muted mb-2">
                        <i className="fas fa-share-alt me-1"></i>
                        Condividi con amici e conoscenti
                    </p>
                    <div className="d-flex justify-content-center flex-wrap gap-2">
                        <a
                            href={`https://wa.me/?text=${encodeURIComponent(`${campagna.nome} - Diventa Rappresentante di Lista!\n${window.location.href}`)}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="btn btn-success btn-sm"
                            title="Condividi su WhatsApp"
                        >
                            <i className="fab fa-whatsapp me-1"></i>
                            WhatsApp
                        </a>
                        <a
                            href={`https://www.facebook.com/sharer.php?u=${encodeURIComponent(window.location.href)}&quote=${encodeURIComponent(campagna.nome + ' - Diventa Rappresentante di Lista!')}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="btn btn-primary btn-sm"
                            title="Condividi su Facebook"
                            onClick={(e) => {
                                e.preventDefault();
                                window.open(
                                    `https://www.facebook.com/sharer.php?u=${encodeURIComponent(window.location.href)}`,
                                    'facebook-share',
                                    'width=580,height=400'
                                );
                            }}
                        >
                            <i className="fab fa-facebook-f me-1"></i>
                            Facebook
                        </a>
                        <a
                            href={`https://t.me/share/url?url=${encodeURIComponent(window.location.href)}&text=${encodeURIComponent(campagna.nome)}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="btn btn-info btn-sm text-white"
                            title="Condividi su Telegram"
                        >
                            <i className="fab fa-telegram-plane me-1"></i>
                            Telegram
                        </a>
                        <a
                            href={`mailto:?subject=${encodeURIComponent(`${campagna.nome} - Diventa RDL`)}&body=${encodeURIComponent(`Ciao,\n\nti segnalo questa iniziativa: ${campagna.nome}\n\nRegistrati come Rappresentante di Lista:\n${window.location.href}\n\nGrazie!`)}`}
                            className="btn btn-secondary btn-sm"
                            title="Condividi via Email"
                        >
                            <i className="fas fa-envelope me-1"></i>
                            Email
                        </a>
                        <button
                            type="button"
                            className="btn btn-outline-dark btn-sm"
                            onClick={() => {
                                navigator.clipboard.writeText(window.location.href);
                                alert('Link copiato! Puoi incollarlo su Instagram, TikTok o altre app.');
                            }}
                            title="Copia link per Instagram/TikTok"
                        >
                            <i className="fas fa-copy me-1"></i>
                            Copia link
                        </button>
                    </div>
                </div>

                {/* Eligibility info based on election type */}
                {campagna.consultazione_tipi_elezione?.length > 0 && (
                    <div className="alert alert-info small mb-3">
                        <strong>Requisiti per essere RDL in questa consultazione:</strong>
                        <ul className="mb-0 mt-1">
                            {[...new Set(campagna.consultazione_tipi_elezione)].map(tipo => (
                                REQUISITI_ELETTORE[tipo] && (
                                    <li key={tipo}>
                                        <strong>{REQUISITI_ELETTORE[tipo].label}:</strong> {REQUISITI_ELETTORE[tipo].requisito}
                                    </li>
                                )
                            ))}
                        </ul>
                        <hr className="my-2" />
                        <small className="text-muted">
                            <strong>Incompatibilità:</strong> Non possono svolgere funzioni di RDL gli appartenenti alle Forze di Polizia.
                        </small>
                    </div>
                )}

                {campagna.posti_disponibili !== null && (
                    <div className="alert alert-warning small mb-3">
                        <strong>Posti disponibili:</strong> {campagna.posti_disponibili}
                    </div>
                )}

                {error && (
                    <div className="alert alert-danger">{error}</div>
                )}

                <form onSubmit={handleSubmit}>
                    {/* Superadmin test data button */}
                    {isSuperuser && (
                        <div className="alert alert-warning mb-4 d-flex align-items-center justify-content-between">
                            <span>
                                <i className="fas fa-flask me-2"></i>
                                <strong>Superadmin:</strong> Compila con dati di test
                            </span>
                            <button
                                type="button"
                                className="btn btn-warning btn-sm"
                                onClick={fillTestData}
                                disabled={loading}
                            >
                                <i className="fas fa-magic me-1"></i>
                                Auto-fill test
                            </button>
                        </div>
                    )}

                    {/* Dati personali */}
                    <h6 className="text-muted mb-3">Dati personali</h6>
                    <div className="row">
                        <div className="col-md-6 mb-3">
                            <label htmlFor="cognome" className="form-label">Cognome *</label>
                            <input
                                id="cognome"
                                type="text"
                                className="form-control"
                                name="cognome"
                                value={formData.cognome}
                                onChange={handleChange}
                                required
                                disabled={loading}
                                aria-required="true"
                            />
                        </div>
                        <div className="col-md-6 mb-3">
                            <label htmlFor="nome" className="form-label">Nome *</label>
                            <input
                                id="nome"
                                type="text"
                                className="form-control"
                                name="nome"
                                value={formData.nome}
                                onChange={handleChange}
                                required
                                disabled={loading}
                                aria-required="true"
                            />
                        </div>
                    </div>

                    <div className="row">
                        <div className="col-md-6 mb-3">
                            <label htmlFor="comune_nascita" className="form-label">Comune di nascita *</label>
                            <input
                                id="comune_nascita"
                                type="text"
                                className="form-control"
                                name="comune_nascita"
                                value={formData.comune_nascita}
                                onChange={handleChange}
                                required
                                disabled={loading}
                                aria-required="true"
                            />
                        </div>
                        <div className="col-md-6 mb-3">
                            <label htmlFor="data_nascita" className="form-label">Data di nascita *</label>
                            <input
                                id="data_nascita"
                                type="date"
                                className="form-control"
                                name="data_nascita"
                                value={formData.data_nascita}
                                onChange={handleChange}
                                required
                                disabled={loading}
                                aria-required="true"
                            />
                        </div>
                    </div>

                    {/* Contatti */}
                    <h6 className="text-muted mb-3 mt-3">Contatti</h6>
                    <div className="row">
                        <div className="col-md-6 mb-3">
                            <label htmlFor="email" className="form-label">Indirizzo email *</label>
                            <input
                                id="email"
                                type="email"
                                className="form-control"
                                name="email"
                                value={formData.email}
                                onChange={handleChange}
                                required
                                disabled={loading}
                                aria-required="true"
                                aria-describedby="email-help"
                            />
                        </div>
                        <div className="col-md-6 mb-3">
                            <label htmlFor="telefono" className="form-label">Recapito telefonico *</label>
                            <input
                                id="telefono"
                                type="tel"
                                className="form-control"
                                name="telefono"
                                value={formData.telefono}
                                onChange={handleChange}
                                required
                                disabled={loading}
                                aria-required="true"
                            />
                        </div>
                    </div>

                    {/* Residenza */}
                    <h6 className="text-muted mb-3 mt-3">Residenza</h6>
                    <div className="row">
                        <div className="col-md-6 mb-3">
                            <label htmlFor="comune_residenza" className="form-label">Residente nel Comune di *</label>
                            <input
                                id="comune_residenza"
                                type="text"
                                className="form-control"
                                name="comune_residenza"
                                value={formData.comune_residenza}
                                onChange={handleChange}
                                required
                                disabled={loading}
                                aria-required="true"
                            />
                        </div>
                        <div className="col-md-6 mb-3">
                            <label htmlFor="indirizzo_residenza" className="form-label">Indirizzo di residenza *</label>
                            <input
                                id="indirizzo_residenza"
                                type="text"
                                className="form-control"
                                name="indirizzo_residenza"
                                value={formData.indirizzo_residenza}
                                onChange={handleChange}
                                required
                                disabled={loading}
                                aria-required="true"
                            />
                        </div>
                    </div>

                    {/* Fuorisede */}
                    <h6 className="text-muted mb-3 mt-3">Situazione abitativa</h6>
                    <div className="row">
                        <div className="col-12 mb-3">
                            <label className="form-label">
                                Sei un "fuorisede": lavori o studi in un comune italiano, diverso da quello della tua residenza anagrafica? *
                            </label>
                            <div className="btn-group w-100" role="group" aria-required="true">
                                <input
                                    type="radio"
                                    className="btn-check"
                                    name="fuorisede"
                                    id="fuorisede_si"
                                    value="true"
                                    checked={formData.fuorisede === true}
                                    onChange={() => setFormData(prev => ({ ...prev, fuorisede: true }))}
                                    disabled={loading}
                                />
                                <label className="btn btn-outline-primary" htmlFor="fuorisede_si">
                                    <i className="fas fa-check me-2"></i>SI
                                </label>

                                <input
                                    type="radio"
                                    className="btn-check"
                                    name="fuorisede"
                                    id="fuorisede_no"
                                    value="false"
                                    checked={formData.fuorisede === false}
                                    onChange={() => setFormData(prev => ({ ...prev, fuorisede: false }))}
                                    disabled={loading}
                                />
                                <label className="btn btn-outline-primary" htmlFor="fuorisede_no">
                                    <i className="fas fa-times me-2"></i>NO
                                </label>
                            </div>
                        </div>
                    </div>

                    {/* Domicilio (shown only if fuorisede === true) */}
                    {formData.fuorisede === true && (
                        <>
                            <h6 className="text-muted mb-3 mt-3">Domicilio</h6>
                            <div className="row">
                                <div className="col-md-6 mb-3">
                                    <label htmlFor="comune_domicilio" className="form-label">Comune di domicilio *</label>
                                    <input
                                        id="comune_domicilio"
                                        type="text"
                                        className="form-control"
                                        name="comune_domicilio"
                                        value={formData.comune_domicilio}
                                        onChange={handleChange}
                                        required
                                        disabled={loading}
                                        aria-required="true"
                                    />
                                </div>
                                <div className="col-md-6 mb-3">
                                    <label htmlFor="indirizzo_domicilio" className="form-label">Indirizzo di domicilio *</label>
                                    <input
                                        id="indirizzo_domicilio"
                                        type="text"
                                        className="form-control"
                                        name="indirizzo_domicilio"
                                        value={formData.indirizzo_domicilio}
                                        onChange={handleChange}
                                        required
                                        disabled={loading}
                                        aria-required="true"
                                    />
                                </div>
                            </div>
                        </>
                    )}

                    {/* Dove vuoi fare il RDL */}
                    <h6 className="text-muted mb-3 mt-3">Dove vuoi fare il Rappresentante di Lista?</h6>
                    <div className="alert alert-light border small mb-3" role="note">
                        <strong>Scegli in base alle tue preferenze:</strong> puoi indicare un seggio vicino a dove abiti,
                        dove lavori, o semplicemente dove ti è più comodo recarti il giorno delle elezioni.
                    </div>

                    <div className="row">
                        <div className="col-md-6 mb-3">
                            <label htmlFor="comune_seggio" className="form-label">Comune del seggio *</label>
                            {campagna.comuni_disponibili?.length === 1 ? (
                                // Single comune: show as read-only (auto-selected via useEffect)
                                <input
                                    id="comune_seggio"
                                    type="text"
                                    className="form-control"
                                    value={campagna.comuni_disponibili[0].label || campagna.comuni_disponibili[0].nome}
                                    disabled
                                    readOnly
                                    aria-describedby="comune-seggio-help"
                                />
                            ) : (
                                // Multiple comuni: show search/select
                                <div className="position-relative">
                                    <input
                                        id="comune_seggio"
                                        type="text"
                                        className="form-control"
                                        value={comuneSearch}
                                        onChange={(e) => {
                                            setComuneSearch(e.target.value);
                                            if (selectedComune && e.target.value !== (selectedComune.label || selectedComune.nome)) {
                                                setSelectedComune(null);
                                            }
                                        }}
                                        placeholder="Cerca comune..."
                                        disabled={loading}
                                        autoComplete="off"
                                        aria-required="true"
                                        aria-describedby="comune-seggio-help"
                                    />
                                    {comuneSearch && !selectedComune && filteredComuni.length > 0 && (
                                        <div className="position-absolute w-100 bg-white border rounded shadow-sm" style={{ zIndex: 1000, maxHeight: '200px', overflowY: 'auto' }}>
                                            {filteredComuni.slice(0, 20).map(comune => (
                                                <div
                                                    key={comune.id}
                                                    className="p-2 cursor-pointer"
                                                    style={{ cursor: 'pointer' }}
                                                    onClick={() => handleComuneSelect(comune)}
                                                    onMouseEnter={(e) => e.target.style.backgroundColor = '#f0f0f0'}
                                                    onMouseLeave={(e) => e.target.style.backgroundColor = 'white'}
                                                >
                                                    {comune.label || comune.nome}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}
                            <small id="comune-seggio-help" className="text-muted">
                                {campagna.comuni_disponibili?.length === 1
                                    ? 'Comune pre-selezionato per questa campagna'
                                    : 'In quale comune vuoi operare come RDL?'}
                            </small>
                        </div>
                        <div className="col-md-6 mb-3">
                            <label htmlFor="municipio" className="form-label">
                                Municipio del seggio {selectedComune?.has_municipi && selectedComune?.municipi?.length > 0 ? '*' : ''}
                            </label>
                            {selectedComune?.has_municipi && selectedComune?.municipi?.length > 0 ? (
                                <select
                                    id="municipio"
                                    className="form-select"
                                    name="municipio"
                                    value={formData.municipio}
                                    onChange={handleChange}
                                    required
                                    disabled={loading}
                                    aria-required="true"
                                    aria-describedby="municipio-help"
                                >
                                    <option value="">-- Seleziona municipio --</option>
                                    {selectedComune.municipi.map((m) => (
                                        <option key={m.numero} value={m.numero}>
                                            {m.nome}
                                        </option>
                                    ))}
                                </select>
                            ) : (
                                <input
                                    id="municipio"
                                    type="text"
                                    className="form-control"
                                    disabled
                                    placeholder={selectedComune ? "Questo comune non ha municipi" : "Seleziona prima un comune"}
                                    aria-describedby="municipio-help"
                                />
                            )}
                            <small id="municipio-help" className="text-muted">
                                {selectedComune?.has_municipi ? 'In quale municipio vuoi operare?' : 'Solo per grandi città (Roma, Milano, Napoli, ecc.)'}
                            </small>
                        </div>
                    </div>

                    <div className="row">
                        <div className="col-md-12 mb-3">
                            <label htmlFor="seggio_preferenza" className="form-label">Seggio o plesso di preferenza</label>
                            {selectedComune ? (
                                <SezzionePlessAutocomplete
                                    value={selectedSezione}
                                    onChange={handleSezioneChange}
                                    disabled={loading}
                                    placeholder="Cerca sezione, plesso o indirizzo..."
                                    comuneId={selectedComune.id}
                                    municipio={formData.municipio ? parseInt(formData.municipio) : null}
                                    onMunicipioChange={(mun) => setFormData(prev => ({ ...prev, municipio: String(mun) }))}
                                />
                            ) : (
                                <input
                                    id="seggio_preferenza"
                                    type="text"
                                    className="form-control"
                                    disabled
                                    placeholder="Seleziona prima un comune"
                                />
                            )}
                            <small id="seggio-help" className="text-muted">
                                Opzionale: digita per cercare una sezione, plesso, scuola o indirizzo dove preferiresti essere assegnato
                            </small>
                        </div>
                    </div>

                    {/* Privacy GDPR Acceptance */}
                    <div className="form-check mt-4 pt-3 border-top">
                        <input
                            id="gdprAccepted"
                            type="checkbox"
                            className="form-check-input"
                            checked={gdprAccepted}
                            onChange={(e) => setGdprAccepted(e.target.checked)}
                            disabled={loading}
                            aria-required="true"
                        />
                        <label htmlFor="gdprAccepted" className="form-check-label">
                            <strong>Autorizzo il trattamento dei miei dati personali</strong> inseriti in questo modulo.
                            I dati saranno usati solo ai sensi del Decreto Legislativo 30 giugno 2003, n. 196 e del GDPR
                            (Regolamento UE 2016/679) esclusivamente ai fini del coordinamento delle attività degli RDL *
                        </label>
                    </div>

                    <div className="d-flex gap-2 mt-3">
                        <button
                            type="submit"
                            className="btn btn-primary"
                            disabled={loading || !gdprAccepted}
                        >
                            {loading ? (
                                <>
                                    <span className="spinner-border spinner-border-sm me-2"></span>
                                    Invio in corso...
                                </>
                            ) : 'ACCETTO'}
                        </button>
                        {isAuthenticated && (
                            <button
                                type="button"
                                className="btn btn-secondary"
                                onClick={onClose}
                                disabled={loading}
                            >
                                Torna alla Dashboard
                            </button>
                        )}
                    </div>
                </form>
            </div>
        </div>
    );
}

export default CampagnaRegistration;
