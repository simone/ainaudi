import React, { useState, useEffect } from 'react';

/**
 * Converte un numero in numeri romani
 */
const toRoman = (num) => {
    const romanNumerals = [
        { value: 1000, numeral: 'M' },
        { value: 900, numeral: 'CM' },
        { value: 500, numeral: 'D' },
        { value: 400, numeral: 'CD' },
        { value: 100, numeral: 'C' },
        { value: 90, numeral: 'XC' },
        { value: 50, numeral: 'L' },
        { value: 40, numeral: 'XL' },
        { value: 10, numeral: 'X' },
        { value: 9, numeral: 'IX' },
        { value: 5, numeral: 'V' },
        { value: 4, numeral: 'IV' },
        { value: 1, numeral: 'I' }
    ];
    let result = '';
    for (const { value, numeral } of romanNumerals) {
        while (num >= value) {
            result += numeral;
            num -= value;
        }
    }
    return result;
};

function GestioneDesignazioni({ client, setError, consultazione }) {
    const [stats, setStats] = useState(null);
    const [designazioni, setDesignazioni] = useState([]);
    const [loading, setLoading] = useState(true);
    const [activeView, setActiveView] = useState('panoramica'); // 'panoramica' | 'importa'

    // Upload state
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [uploadResult, setUploadResult] = useState(null);

    // Carica mappatura state
    const [loadingMappatura, setLoadingMappatura] = useState(false);
    const [mappaturaResult, setMappaturaResult] = useState(null);
    const [showMappaturaModal, setShowMappaturaModal] = useState(false);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        setLoading(true);
        try {
            // Get user's delegation chain
            const chain = await client.deleghe.miaCatena();

            if (chain.error) {
                setError(chain.error);
                return;
            }

            // Combine all designations (both made and received)
            const allDesignazioni = [
                ...chain.designazioni_fatte.map(d => ({ ...d, ruolo: 'designante', tipo: 'designazione' })),
                ...chain.designazioni_ricevute.map(d => ({ ...d, ruolo: 'designato', tipo: 'designazione' }))
            ];

            // Get section stats to check for unmapped assignments
            const statsData = await client.sections.stats();
            const sezioniAssegnate = statsData?.visibili?.assegnate || 0;
            const sezioniVisibili = statsData?.visibili?.sezioni || 0;

            // Calculate stats
            const totale = allDesignazioni.length;
            // Nel nuovo modello, ogni designazione può avere effettivo E supplente
            const effettivo = allDesignazioni.filter(d => d.effettivo).length;
            const supplente = allDesignazioni.filter(d => d.supplente).length;
            const confermate = allDesignazioni.filter(d => d.stato === 'CONFERMATA').length;
            const bozze = allDesignazioni.filter(d => d.stato === 'BOZZA').length;

            // Extract territory from sub-delegations
            let territorioLabel = '';
            if (chain.sub_deleghe_ricevute && chain.sub_deleghe_ricevute.length > 0) {
                const subDelega = chain.sub_deleghe_ricevute[0];

                // Build territory label
                const parti = [];

                // Comuni
                if (subDelega.comuni && subDelega.comuni.length > 0) {
                    const comuniNames = subDelega.comuni.map(c => c.nome);
                    if (comuniNames.length <= 2) {
                        parti.push(comuniNames.join(', '));
                    } else {
                        parti.push(`${comuniNames[0]} (+${comuniNames.length - 1} comuni)`);
                    }
                }

                // Municipi
                if (subDelega.municipi && subDelega.municipi.length > 0) {
                    const municString = subDelega.municipi
                        .map(m => `Mun. ${toRoman(m)}`)
                        .join(', ');
                    if (parti.length > 0) {
                        parti[0] = `${parti[0]} - ${municString}`;
                    } else {
                        parti.push(municString);
                    }
                }

                territorioLabel = parti.join(', ');
            } else if (chain.delega_ricevuta) {
                // Delegato di lista - show circoscrizione
                territorioLabel = chain.delega_ricevuta.circoscrizione || 'Nazionale';
            }

            setStats({
                totale,
                effettivo,
                supplente,
                confermate,
                bozze,
                is_delegato: chain.is_delegato,
                is_sub_delegato: chain.is_sub_delegato,
                is_rdl: chain.is_rdl,
                sezioni_assegnate: sezioniAssegnate,
                sezioni_visibili: sezioniVisibili,
                assegnazioni_non_convertite: Math.max(0, sezioniAssegnate - totale),
                territorio: territorioLabel
            });

            setDesignazioni(allDesignazioni);
        } catch (err) {
            setError(`Errore nel caricamento designazioni: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    const calcPercentuale = (parte, totale) => {
        if (!totale) return 0;
        return Math.round((parte / totale) * 100);
    };

    const getStatoBadgeClass = (stato) => {
        switch (stato) {
            case 'CONFERMATA':
                return 'bg-success';
            case 'BOZZA':
                return 'bg-warning';
            case 'RIFIUTATA':
                return 'bg-danger';
            default:
                return 'bg-secondary';
        }
    };

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile) {
            if (!selectedFile.name.endsWith('.csv')) {
                setError('Seleziona un file CSV');
                return;
            }
            setFile(selectedFile);
            setUploadResult(null);
        }
    };

    const handleUpload = async () => {
        if (!file) {
            setError('Seleziona un file prima di caricare');
            return;
        }

        setUploading(true);
        setError(null);
        setUploadResult(null);

        try {
            const res = await client.deleghe.designazioni.uploadCsv(file);
            if (res.error) {
                setError(res.error);
            } else {
                setUploadResult(res);
                // Ricarica i dati dopo l'upload
                loadData();
            }
        } catch (err) {
            setError(`Errore durante il caricamento: ${err.message}`);
        } finally {
            setUploading(false);
        }
    };

    const handleCaricaMappatura = async () => {
        if (!consultazione || !consultazione.id) {
            setError('Nessuna consultazione attiva selezionata');
            return;
        }

        setLoadingMappatura(true);
        setError(null);
        setMappaturaResult(null);
        setShowMappaturaModal(false);

        try {
            const res = await client.deleghe.designazioni.caricaMappatura(consultazione.id);
            if (res.error) {
                setError(res.error);
            } else {
                setMappaturaResult(res);
                // Ricarica i dati dopo il caricamento
                loadData();
            }
        } catch (err) {
            setError(`Errore durante il caricamento mappatura: ${err.message}`);
        } finally {
            setLoadingMappatura(false);
        }
    };

    if (loading) {
        return (
            <div className="loading-container" role="status" aria-live="polite">
                <div className="spinner-border text-primary">
                    <span className="visually-hidden">Caricamento in corso...</span>
                </div>
                <p className="loading-text">Caricamento designazioni...</p>
            </div>
        );
    }

    return (
        <>
            {/* Page Header */}
            <div className="page-header rdl">
                <div className="page-header-title">
                    <i className="fas fa-clipboard-list"></i>
                    Designazioni RDL
                </div>
                <div className="page-header-subtitle">
                    Gestione e monitoraggio designazioni Rappresentanti di Lista
                    {stats && stats.territorio && (
                        <span className="page-header-badge">
                            {stats.territorio}
                        </span>
                    )}
                </div>
            </div>

            {/* Tab Navigation */}
            <ul className="nav nav-tabs mb-3">
                <li className="nav-item">
                    <button
                        className={`nav-link ${activeView === 'panoramica' ? 'active' : ''}`}
                        onClick={() => setActiveView('panoramica')}
                        aria-selected={activeView === 'panoramica'}
                    >
                        <i className="fas fa-chart-pie me-2"></i>
                        Panoramica
                    </button>
                </li>
                <li className="nav-item">
                    <button
                        className={`nav-link ${activeView === 'importa' ? 'active' : ''}`}
                        onClick={() => setActiveView('importa')}
                        aria-selected={activeView === 'importa'}
                    >
                        <i className="fas fa-file-import me-2"></i>
                        Importa CSV
                    </button>
                </li>
            </ul>

            {/* Panoramica View */}
            {activeView === 'panoramica' && stats && (
                <>
                    {/* Alert: Assegnazioni da convertire */}
                    {stats.assegnazioni_non_convertite > 0 && (
                        <div className="alert alert-warning mb-4">
                            <div className="d-flex align-items-center">
                                <i className="fas fa-exclamation-triangle fa-2x me-3"></i>
                                <div className="flex-grow-1">
                                    <strong>Hai {stats.assegnazioni_non_convertite} assegnazioni RDL non ancora convertite in designazioni formali</strong>
                                    <p className="mb-0 small mt-1">
                                        Le assegnazioni sono state fatte tramite app mobile, ma non sono ancora state
                                        convertite in designazioni formali. Clicca su "Carica Mappatura" qui sotto per convertirle.
                                    </p>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Carica Mappatura Button */}
                    <div className="alert alert-primary mb-4">
                        <div className="d-flex align-items-center justify-content-between flex-wrap gap-3">
                            <div className="d-flex align-items-center">
                                <i className="fas fa-map-marked-alt fa-2x me-3"></i>
                                <div>
                                    <strong>Carica Mappatura dal Territorio</strong>
                                    <p className="mb-0 small">
                                        Converte le assegnazioni RDL-Sezione fatte tramite app in designazioni formali
                                    </p>
                                </div>
                            </div>
                            <button
                                className="btn btn-primary"
                                onClick={() => setShowMappaturaModal(true)}
                                disabled={loadingMappatura || !consultazione}
                            >
                                <i className="fas fa-download me-2"></i>
                                Carica Mappatura
                            </button>
                        </div>
                    </div>

                    {/* Mappatura Result */}
                    {mappaturaResult && (
                        <div className={`alert ${mappaturaResult.errors?.length ? 'alert-warning' : 'alert-success'} mb-4`}>
                            <h5>
                                <i className={`fas ${mappaturaResult.errors?.length ? 'fa-exclamation-triangle' : 'fa-check-circle'} me-2`}></i>
                                Mappatura caricata
                            </h5>
                            <ul className="mb-0">
                                <li>Designazioni create: <strong>{mappaturaResult.created}</strong></li>
                                <li>Già esistenti (saltate): <strong>{mappaturaResult.skipped}</strong></li>
                                <li>Totale elaborato: <strong>{mappaturaResult.total}</strong></li>
                            </ul>
                            {mappaturaResult.errors?.length > 0 && (
                                <div className="mt-2">
                                    <strong>Errori:</strong>
                                    <ul className="mb-0">
                                        {mappaturaResult.errors.slice(0, 10).map((err, i) => (
                                            <li key={i} className="text-danger small">{err}</li>
                                        ))}
                                        {mappaturaResult.errors.length > 10 && (
                                            <li className="text-muted small">... e altri {mappaturaResult.errors.length - 10} errori</li>
                                        )}
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Summary Cards */}
                    <div className="row g-3 mb-4">
                        {/* Card Assegnazioni Territorio */}
                        <div className="col-6 col-lg-3">
                            <div className="card h-100 border-info">
                                <div className="card-body text-center p-2 p-md-3">
                                    <div className="text-muted small">Assegnazioni Territorio</div>
                                    <div className="fs-3 fw-bold text-info">
                                        {stats.sezioni_assegnate}
                                    </div>
                                    <div className="text-muted small">
                                        su {stats.sezioni_visibili} sezioni
                                    </div>
                                    {stats.assegnazioni_non_convertite > 0 && (
                                        <div className="small text-warning mt-1">
                                            {stats.assegnazioni_non_convertite} da convertire
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Card Totale Designazioni */}
                        <div className="col-6 col-lg-3">
                            <div className="card h-100 border-primary">
                                <div className="card-body text-center p-2 p-md-3">
                                    <div className="text-muted small">Designazioni Formali</div>
                                    <div className="fs-3 fw-bold text-primary">
                                        {stats.totale}
                                    </div>
                                    <div className="text-muted small">create</div>
                                </div>
                            </div>
                        </div>

                        {/* Card Effettivi e Supplenti */}
                        <div className="col-6 col-lg-3">
                            <div className="card h-100 border-secondary">
                                <div className="card-body p-2 p-md-3">
                                    <div className="row g-2">
                                        <div className="col-6">
                                            <div className="text-center">
                                                <div className="text-muted small">Effettivi</div>
                                                <div className="fs-3 fw-bold text-primary">
                                                    {stats.effettivo}
                                                </div>
                                                <div className="text-muted small">
                                                    {calcPercentuale(stats.effettivo, stats.totale)}%
                                                </div>
                                            </div>
                                        </div>
                                        <div className="col-6">
                                            <div className="text-center">
                                                <div className="text-muted small">Supplenti</div>
                                                <div className="fs-3 fw-bold text-info">
                                                    {stats.supplente}
                                                </div>
                                                <div className="text-muted small">
                                                    {calcPercentuale(stats.supplente, stats.totale)}%
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Card Confermate */}
                        <div className="col-6 col-lg-3">
                            <div className="card h-100 border-success">
                                <div className="card-body text-center p-2 p-md-3">
                                    <div className="text-muted small">Confermate</div>
                                    <div className="fs-3 fw-bold text-success">
                                        {stats.confermate}
                                    </div>
                                    <div className="text-muted small">
                                        {calcPercentuale(stats.confermate, stats.totale)}%
                                    </div>
                                    {stats.bozze > 0 && (
                                        <div className="small text-warning mt-1">
                                            {stats.bozze} bozze
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="card mb-4">
                        <div className="card-body">
                            <h6 className="card-title">Stato designazioni</h6>
                            <div className="progress" style={{ height: '24px' }}>
                                <div
                                    className="progress-bar bg-success"
                                    style={{ width: `${calcPercentuale(stats.confermate, stats.totale)}%` }}
                                    role="progressbar"
                                    aria-valuenow={stats.confermate}
                                    aria-valuemin="0"
                                    aria-valuemax={stats.totale}
                                >
                                    {calcPercentuale(stats.confermate, stats.totale)}% confermate
                                </div>
                                {stats.bozze > 0 && (
                                    <div
                                        className="progress-bar bg-warning"
                                        style={{ width: `${calcPercentuale(stats.bozze, stats.totale)}%` }}
                                        role="progressbar"
                                        aria-valuenow={stats.bozze}
                                        aria-valuemin="0"
                                        aria-valuemax={stats.totale}
                                    >
                                        {calcPercentuale(stats.bozze, stats.totale)}% bozze
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Refresh Button */}
                    <div className="text-center mt-3">
                        <button
                            className="btn btn-outline-secondary"
                            onClick={loadData}
                            disabled={loading}
                        >
                            <i className="fas fa-sync-alt me-2"></i>
                            Aggiorna dati
                        </button>
                    </div>
                </>
            )}

            {/* Import CSV View */}
            {activeView === 'importa' && (
                <>
                    <div className="alert alert-warning mb-3">
                        <h6 className="alert-heading">
                            <i className="fas fa-lightbulb me-2"></i>
                            Due modi per caricare le designazioni
                        </h6>
                        <p className="mb-2">
                            <strong>1. Carica Mappatura (consigliato):</strong> Usa il pulsante nella tab "Panoramica" per caricare
                            automaticamente tutte le assegnazioni fatte tramite app mobile nel tuo territorio.
                        </p>
                        <p className="mb-0">
                            <strong>2. Import CSV (manuale):</strong> Usa questa tab se hai un CSV preparato manualmente
                            o se vuoi integrare designazioni da altre fonti.
                        </p>
                    </div>

                    <div className="card">
                        <div className="card-header bg-info text-white">
                            <i className="fas fa-file-import me-2"></i>
                            Importa Designazioni da CSV
                        </div>
                        <div className="card-body">
                            <p className="alert alert-info">
                                <i className="fas fa-info-circle me-2"></i>
                                <strong>Import manuale:</strong> Carica un file CSV con le designazioni RDL.
                                <br/>
                                Il sistema creerà automaticamente le designazioni per ogni sezione specificata.
                            </p>

                            <p className="text-muted">
                                Il file CSV deve avere le seguenti colonne:
                            </p>
                            <ul className="text-muted">
                                <li><strong>SEZIONE</strong> *: Numero della sezione</li>
                                <li><strong>COMUNE</strong> *: Nome del comune (es. ROMA)</li>
                                <li><strong>MUNICIPIO</strong>: Numero del municipio (opzionale, per città con municipi)</li>
                                <li><strong>EFFETTIVO_EMAIL</strong>: Email del RDL effettivo (opzionale se c'è supplente)</li>
                                <li><strong>SUPPLENTE_EMAIL</strong>: Email del RDL supplente (opzionale se c'è effettivo)</li>
                            </ul>

                            <div className="mb-3">
                                <label htmlFor="csvFile" className="form-label">Seleziona file CSV</label>
                                <input
                                    type="file"
                                    className="form-control"
                                    id="csvFile"
                                    accept=".csv"
                                    onChange={handleFileChange}
                                    disabled={uploading}
                                    aria-describedby="csvHelp"
                                />
                                <div id="csvHelp" className="form-text">
                                    Formati supportati: .csv (separatore virgola)
                                </div>
                            </div>

                            {file && (
                                <div className="alert alert-info d-flex align-items-center">
                                    <i className="fas fa-file-csv me-2"></i>
                                    <div>
                                        <strong>{file.name}</strong>
                                        <span className="text-muted ms-2">({(file.size / 1024).toFixed(1)} KB)</span>
                                    </div>
                                </div>
                            )}

                            <button
                                className="btn btn-primary"
                                onClick={handleUpload}
                                disabled={!file || uploading}
                            >
                                {uploading ? (
                                    <>
                                        <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                                        Caricamento in corso...
                                    </>
                                ) : (
                                    <>
                                        <i className="fas fa-cloud-upload-alt me-2"></i>
                                        Importa Designazioni
                                    </>
                                )}
                            </button>
                        </div>
                    </div>

                    {uploadResult && (
                        <div className={`alert ${uploadResult.errors?.length ? 'alert-warning' : 'alert-success'} mt-3`}>
                            <h5>
                                <i className={`fas ${uploadResult.errors?.length ? 'fa-exclamation-triangle' : 'fa-check-circle'} me-2`}></i>
                                Importazione completata
                            </h5>
                            <ul className="mb-0">
                                <li>Designazioni create: <strong>{uploadResult.created}</strong></li>
                                <li>Designazioni aggiornate: <strong>{uploadResult.updated}</strong></li>
                                <li>Totale elaborato: <strong>{uploadResult.total}</strong></li>
                            </ul>
                            {uploadResult.errors?.length > 0 && (
                                <div className="mt-2">
                                    <strong>Errori:</strong>
                                    <ul className="mb-0">
                                        {uploadResult.errors.slice(0, 10).map((err, i) => (
                                            <li key={i} className="text-danger small">{err}</li>
                                        ))}
                                        {uploadResult.errors.length > 10 && (
                                            <li className="text-muted small">... e altri {uploadResult.errors.length - 10} errori</li>
                                        )}
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}

                    <div className="card mt-3">
                        <div className="card-header">
                            <i className="fas fa-code me-2"></i>
                            Esempio formato CSV
                        </div>
                        <div className="card-body">
                            <pre className="mb-0 bg-light p-3 rounded" style={{ fontSize: '0.85em' }}>
{`SEZIONE,COMUNE,MUNICIPIO,EFFETTIVO_EMAIL,SUPPLENTE_EMAIL
1,ROMA,3,mario.rossi@example.com,anna.bianchi@example.com
2,ROMA,1,luigi.verdi@example.com,
3,ROMA,1,,maria.gialli@example.com
1,MENTANA,,paolo.neri@example.com,carla.blu@example.com
...`}
                            </pre>
                            <p className="text-muted small mt-2 mb-0">
                                <i className="fas fa-lightbulb me-1"></i>
                                <strong>Note:</strong>
                            </p>
                            <ul className="text-muted small">
                                <li>Almeno una email (effettivo o supplente) deve essere presente</li>
                                <li>Se il comune non ha municipi, lascia vuota la colonna MUNICIPIO</li>
                                <li>Gli RDL devono essere già registrati nel sistema e approvati</li>
                                <li>Se la designazione esiste già, verrà aggiornata</li>
                            </ul>
                        </div>
                    </div>
                </>
            )}

            {/* Modale Conferma Carica Mappatura */}
            {showMappaturaModal && (
                <div className="modal show d-block" tabIndex="-1" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
                    <div className="modal-dialog modal-dialog-centered">
                        <div className="modal-content">
                            <div className="modal-header">
                                <h5 className="modal-title">
                                    <i className="fas fa-download me-2"></i>
                                    Conferma Caricamento Mappatura
                                </h5>
                                <button
                                    type="button"
                                    className="btn-close"
                                    onClick={() => setShowMappaturaModal(false)}
                                    disabled={loadingMappatura}
                                ></button>
                            </div>
                            <div className="modal-body">
                                <p className="mb-3">
                                    <strong>Questa operazione creerà le designazioni formali per tutte le assegnazioni RDL presenti nel tuo territorio.</strong>
                                </p>
                                <ul className="mb-3">
                                    <li>Verranno convertite tutte le assegnazioni (SectionAssignment) in designazioni (DesignazioneRDL)</li>
                                    <li>Le assegnazioni già convertite in designazioni verranno automaticamente saltate</li>
                                    <li>Le designazioni con firma autenticata saranno subito CONFERMATE</li>
                                    <li>Le altre designazioni saranno in stato BOZZA fino ad approvazione</li>
                                </ul>
                                <div className="alert alert-info mb-0">
                                    <i className="fas fa-info-circle me-2"></i>
                                    <small>
                                        Questa operazione è sicura e può essere ripetuta più volte.
                                        Non verranno create designazioni duplicate.
                                    </small>
                                </div>
                            </div>
                            <div className="modal-footer">
                                <button
                                    type="button"
                                    className="btn btn-secondary"
                                    onClick={() => setShowMappaturaModal(false)}
                                    disabled={loadingMappatura}
                                >
                                    Annulla
                                </button>
                                <button
                                    type="button"
                                    className="btn btn-primary"
                                    onClick={handleCaricaMappatura}
                                    disabled={loadingMappatura}
                                >
                                    {loadingMappatura ? (
                                        <>
                                            <span className="spinner-border spinner-border-sm me-2"></span>
                                            Caricamento in corso...
                                        </>
                                    ) : (
                                        <>
                                            <i className="fas fa-check me-2"></i>
                                            Conferma e Carica
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Designazioni List (sempre visibile) */}
            <div className="card mt-4">
                <div className="card-header">
                    <h5 className="mb-0">
                        <i className="fas fa-list me-2"></i>
                        Elenco Designazioni
                    </h5>
                </div>
                {designazioni.length === 0 ? (
                    <div className="card-body text-center text-muted py-4">
                        <i className="fas fa-inbox fa-3x mb-3"></i>
                        <p className="mb-0">Nessuna designazione presente</p>
                    </div>
                ) : (
                    <div className="table-responsive">
                        <table className="table table-hover mb-0">
                            <thead className="table-light">
                                <tr>
                                    <th>Comune</th>
                                    <th>Sezione</th>
                                    <th>Plesso</th>
                                    <th>Effettivo</th>
                                    <th>Supplente</th>
                                    <th>Stato</th>
                                    <th>Tuo Ruolo</th>
                                </tr>
                            </thead>
                            <tbody>
                                {designazioni.map((des, index) => (
                                    <tr key={index}>
                                        <td className="fw-bold">
                                            {des.sezione_comune || '-'}
                                            {des.sezione_municipio && (
                                                <small className="text-muted ms-1">
                                                    (Mun. {toRoman(des.sezione_municipio)})
                                                </small>
                                            )}
                                        </td>
                                        <td>
                                            {des.sezione_numero || '-'}
                                        </td>
                                        <td className="small">
                                            {des.sezione_indirizzo || '-'}
                                        </td>
                                        <td>
                                            {des.effettivo ? (
                                                <div>
                                                    <div className="fw-bold">{des.effettivo.cognome} {des.effettivo.nome}</div>
                                                    {des.effettivo.email && <small className="text-muted">{des.effettivo.email}</small>}
                                                </div>
                                            ) : (
                                                <span className="text-muted">-</span>
                                            )}
                                        </td>
                                        <td>
                                            {des.supplente ? (
                                                <div>
                                                    <div className="fw-bold">{des.supplente.cognome} {des.supplente.nome}</div>
                                                    {des.supplente.email && <small className="text-muted">{des.supplente.email}</small>}
                                                </div>
                                            ) : (
                                                <span className="text-muted">-</span>
                                            )}
                                        </td>
                                        <td>
                                            <span className={`badge ${getStatoBadgeClass(des.stato)}`}>
                                                {des.stato_display || des.stato}
                                            </span>
                                        </td>
                                        <td>
                                            <span className={`badge ${des.ruolo === 'designante' ? 'bg-secondary' : 'bg-primary'}`}>
                                                {des.ruolo === 'designante' ? 'Designante' : 'Designato'}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </>
    );
}

export default GestioneDesignazioni;
