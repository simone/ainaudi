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
    const [activeView, setActiveView] = useState('panoramica'); // 'panoramica' | 'importa' | 'lista'

    // Upload state
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [uploadResult, setUploadResult] = useState(null);

    // Carica mappatura state
    const [loadingMappatura, setLoadingMappatura] = useState(false);
    const [mappaturaResult, setMappaturaResult] = useState(null);
    const [showMappaturaModal, setShowMappaturaModal] = useState(false);

    // Multi-select for PDF generation
    const [selectedDesignazioni, setSelectedDesignazioni] = useState(new Set());

    // PDF generation modal
    const [showPdfModal, setShowPdfModal] = useState(false);
    const [pdfStep, setPdfStep] = useState('template'); // 'template' | 'form' | 'preview'
    const [selectedTemplate, setSelectedTemplate] = useState(null);
    const [templates, setTemplates] = useState([]);
    const [delegatoData, setDelegatoData] = useState(null);
    const [formData, setFormData] = useState({});
    const [pdfPreview, setPdfPreview] = useState(null);
    const [generatingPdf, setGeneratingPdf] = useState(false);

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

    // Format date for display
    const formatDate = (dateStr) => {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        const day = String(date.getDate()).padStart(2, '0');
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const year = date.getFullYear();
        return `${day}/${month}/${year}`;
    };

    // Format RDL data: "Cognome Nome nato a Luogo il DD/MM/YYYY, domiciliato in Indirizzo"
    const formatRdlData = (rdl) => {
        if (!rdl.cognome || !rdl.nome) return 'Non assegnato';

        let text = `${rdl.cognome} ${rdl.nome}`;

        if (rdl.luogo_nascita) {
            text += ` nato a ${rdl.luogo_nascita}`;
        }

        if (rdl.data_nascita) {
            text += ` il ${formatDate(rdl.data_nascita)}`;
        }

        if (rdl.domicilio) {
            text += `, domiciliato in ${rdl.domicilio}`;
        }

        return text;
    };

    // Multi-select functions
    const toggleSelectAll = () => {
        const bozze = designazioni.filter(d => d.stato === 'BOZZA');
        if (selectedDesignazioni.size === bozze.length && bozze.length > 0) {
            setSelectedDesignazioni(new Set());
        } else {
            setSelectedDesignazioni(new Set(bozze.map(d => d.id)));
        }
    };

    const toggleSelect = (id) => {
        const newSelected = new Set(selectedDesignazioni);
        if (newSelected.has(id)) {
            newSelected.delete(id);
        } else {
            newSelected.add(id);
        }
        setSelectedDesignazioni(newSelected);
    };

    const openPdfModal = async () => {
        if (selectedDesignazioni.size === 0) return;
        setShowPdfModal(true);
        setPdfStep('template');

        // Load templates and delegato data
        await Promise.all([
            loadTemplates(),
            loadDelegatoData()
        ]);
    };

    const loadTemplates = async () => {
        try {
            const result = await client.templates.list(consultazione.id);
            if (result.error) {
                setError(result.error);
            } else {
                setTemplates(result.templates || []);
            }
        } catch (err) {
            setError(`Errore caricamento templates: ${err.message}`);
        }
    };

    const loadDelegatoData = async () => {
        try {
            const chain = await client.deleghe.miaCatena();
            if (chain.error) {
                setError(chain.error);
                return;
            }

            let data = {};

            // Se subdelegato, prendi i dati dalla subdelega
            if (chain.sub_deleghe_ricevute && chain.sub_deleghe_ricevute.length > 0) {
                const subDelega = chain.sub_deleghe_ricevute[0];
                data = {
                    tipo_firmatario: 'subdelegato',
                    cognome: subDelega.cognome || '',
                    nome: subDelega.nome || '',
                    luogo_nascita: subDelega.luogo_nascita || '',
                    data_nascita: subDelega.data_nascita || '',
                    domicilio: subDelega.domicilio || '',
                    tipo_documento: subDelega.tipo_documento || '',
                    numero_documento: subDelega.numero_documento || '',
                    // Info delegato (per catena)
                    delegato_cognome: subDelega.delegato?.cognome || '',
                    delegato_nome: subDelega.delegato?.nome || '',
                    delegato_carica: subDelega.delegato?.carica || ''
                };
            }
            // Se delegato diretto
            else if (chain.delega_ricevuta) {
                const delega = chain.delega_ricevuta;
                data = {
                    tipo_firmatario: 'delegato',
                    cognome: delega.cognome || '',
                    nome: delega.nome || '',
                    luogo_nascita: delega.luogo_nascita || '',
                    data_nascita: delega.data_nascita || '',
                    carica: delega.carica || '',
                    circoscrizione: delega.circoscrizione || ''
                };
            }

            setDelegatoData(data);
            setFormData(data);
        } catch (err) {
            setError(`Errore caricamento dati delegato: ${err.message}`);
        }
    };

    const closePdfModal = () => {
        setShowPdfModal(false);
        setPdfStep('template');
        setSelectedTemplate(null);
        setFormData({});
        setPdfPreview(null);
    };

    const goToStep = (step) => {
        setPdfStep(step);
    };

    const handleTemplateSelect = (template) => {
        setSelectedTemplate(template);
    };

    const handleFormChange = (field, value) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    const validateForm = () => {
        const required = ['cognome', 'nome', 'luogo_nascita', 'data_nascita'];

        if (formData.tipo_firmatario === 'subdelegato') {
            required.push('domicilio', 'tipo_documento', 'numero_documento');
        }

        const missing = required.filter(field => !formData[field]);
        return missing;
    };

    const generatePreview = async () => {
        setGeneratingPdf(true);
        try {
            // Prepara dati per preview
            const previewData = {
                delegato: formData,
                designazioni: Array.from(selectedDesignazioni).map(id =>
                    designazioni.find(d => d.id === id)
                ),
                consultazione_id: consultazione.id
            };

            const blob = await client.templates.preview(selectedTemplate.id, previewData);
            if (blob) {
                setPdfPreview(URL.createObjectURL(blob));
                goToStep('preview');
            } else {
                setError('Errore generazione preview PDF');
            }
        } catch (err) {
            setError(`Errore preview: ${err.message}`);
        } finally {
            setGeneratingPdf(false);
        }
    };

    const generateBatch = async () => {
        setGeneratingPdf(true);
        try {
            // Step 1: Crea batch
            const batchResult = await client.batch.create({
                consultazione_id: consultazione.id,
                tipo: 'INDIVIDUALE',
                solo_sezioni: Array.from(selectedDesignazioni).map(id => {
                    const des = designazioni.find(d => d.id === id);
                    return des?.sezione_id;
                }).filter(Boolean),
                delegato_data: formData,
                template_id: selectedTemplate.id
            });

            if (batchResult.error) {
                setError(batchResult.error);
                return;
            }

            // Step 2: Genera PDF
            const generaResult = await client.batch.genera(batchResult.id);
            if (generaResult.error) {
                setError(generaResult.error);
                return;
            }

            // Step 3: Approva batch (questo conferma le designazioni BOZZA → CONFERMATA)
            const approvaResult = await client.batch.approva(batchResult.id);
            if (approvaResult.error) {
                setError(approvaResult.error);
                return;
            }

            // Step 4: Download PDF automatico
            await client.batch.downloadPdf(batchResult.id);

            // Success!
            const numDesignazioni = selectedDesignazioni.size;
            alert(
                `✅ PDF generato con successo!\n\n` +
                `• Batch ID: ${batchResult.id}\n` +
                `• ${numDesignazioni} designazioni confermate (BOZZA → CONFERMATA)\n` +
                `• Documento scaricato`
            );

            // Chiudi modale e ricarica dati
            closePdfModal();
            setSelectedDesignazioni(new Set());
            loadData();
        } catch (err) {
            setError(`Errore generazione batch: ${err.message}`);
        } finally {
            setGeneratingPdf(false);
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
                        className={`nav-link ${activeView === 'lista' ? 'active' : ''}`}
                        onClick={() => setActiveView('lista')}
                        aria-selected={activeView === 'lista'}
                    >
                        <i className="fas fa-list me-2"></i>
                        Lista Designazioni
                        {stats && stats.bozze > 0 && (
                            <span className="badge bg-warning text-dark ms-2">{stats.bozze}</span>
                        )}
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

            {/* Lista Designazioni View */}
            {activeView === 'lista' && (
                <>
                    {/* Bulk Actions */}
                    {stats && stats.bozze > 0 && (
                        <div style={{
                            background: 'white',
                            borderRadius: '8px',
                            padding: '12px',
                            marginBottom: '12px',
                            boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', margin: 0, cursor: 'pointer' }}>
                                    <input
                                        type="checkbox"
                                        checked={selectedDesignazioni.size > 0 && selectedDesignazioni.size === designazioni.filter(d => d.stato === 'BOZZA').length}
                                        onChange={toggleSelectAll}
                                        style={{ cursor: 'pointer', width: '18px', height: '18px' }}
                                    />
                                    <span style={{ fontSize: '0.9rem', fontWeight: 500 }}>
                                        Seleziona tutte le bozze ({designazioni.filter(d => d.stato === 'BOZZA').length})
                                    </span>
                                </label>
                                {selectedDesignazioni.size > 0 && (
                                    <>
                                        <span style={{ fontSize: '0.9rem', color: '#6c757d' }}>
                                            {selectedDesignazioni.size} selezionate
                                        </span>
                                        <button
                                            className="btn btn-primary btn-sm"
                                            onClick={openPdfModal}
                                            style={{ marginLeft: 'auto' }}
                                        >
                                            <i className="fas fa-file-pdf me-2"></i>
                                            Genera PDF
                                        </button>
                                    </>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Lista Designazioni */}
                    <div style={{
                        background: 'white',
                        borderRadius: '8px',
                        boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                        marginBottom: '12px'
                    }}>
                        <div style={{
                            padding: '12px 16px',
                            borderBottom: '2px solid #e9ecef',
                            fontWeight: 600,
                            fontSize: '0.95rem',
                            color: '#495057'
                        }}>
                            Designazioni ({designazioni.length})
                        </div>

                        {designazioni.length === 0 ? (
                            <div style={{ padding: '40px', textAlign: 'center', color: '#6c757d' }}>
                                <i className="fas fa-inbox fa-3x mb-3" style={{ opacity: 0.3 }}></i>
                                <p>Nessuna designazione trovata</p>
                                <p className="small">Usa "Carica Mappatura" o "Importa CSV" per creare designazioni</p>
                            </div>
                        ) : (
                            designazioni.map(des => {
                                const effettivoData = {
                                    cognome: des.effettivo_cognome,
                                    nome: des.effettivo_nome,
                                    luogo_nascita: des.effettivo_luogo_nascita,
                                    data_nascita: des.effettivo_data_nascita,
                                    domicilio: des.effettivo_domicilio
                                };

                                const suppleenteData = {
                                    cognome: des.supplente_cognome,
                                    nome: des.supplente_nome,
                                    luogo_nascita: des.supplente_luogo_nascita,
                                    data_nascita: des.supplente_data_nascita,
                                    domicilio: des.supplente_domicilio
                                };

                                return (
                                    <div key={des.id} style={{
                                        borderBottom: '1px solid #e9ecef',
                                        padding: '16px',
                                        cursor: des.stato === 'BOZZA' ? 'pointer' : 'default'
                                    }}>
                                        <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                                            {/* Checkbox per bozze */}
                                            {des.stato === 'BOZZA' && (
                                                <input
                                                    type="checkbox"
                                                    checked={selectedDesignazioni.has(des.id)}
                                                    onChange={(e) => {
                                                        e.stopPropagation();
                                                        toggleSelect(des.id);
                                                    }}
                                                    style={{ cursor: 'pointer', width: '20px', height: '20px', marginTop: '4px' }}
                                                />
                                            )}

                                            <div style={{ flex: 1 }}>
                                                {/* Header con sezione e stato */}
                                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                                        <span style={{ fontSize: '1.1rem', fontWeight: 600, color: '#212529' }}>
                                                            <i className="fas fa-map-marker-alt me-2" style={{ color: '#6c757d' }}></i>
                                                            Sezione {des.sezione_numero}
                                                        </span>
                                                        <span style={{ fontSize: '0.9rem', color: '#6c757d' }}>
                                                            {des.comune}
                                                            {des.municipio && ` - Municipio ${toRoman(des.municipio)}`}
                                                        </span>
                                                    </div>
                                                    <span className={`badge ${getStatoBadgeClass(des.stato)}`}>
                                                        {des.stato}
                                                    </span>
                                                </div>

                                                {/* Effettivo */}
                                                <div style={{ marginBottom: '8px' }}>
                                                    <div style={{ fontSize: '0.85rem', color: '#6c757d', fontWeight: 500, marginBottom: '4px' }}>
                                                        <i className="fas fa-user me-1"></i>
                                                        EFFETTIVO
                                                    </div>
                                                    <div style={{ fontSize: '0.95rem', color: '#212529', paddingLeft: '20px' }}>
                                                        {formatRdlData(effettivoData)}
                                                    </div>
                                                    {des.effettivo_email && (
                                                        <div style={{ fontSize: '0.85rem', color: '#6c757d', paddingLeft: '20px', marginTop: '2px' }}>
                                                            <i className="fas fa-envelope me-1"></i>
                                                            {des.effettivo_email}
                                                        </div>
                                                    )}
                                                </div>

                                                {/* Supplente */}
                                                <div>
                                                    <div style={{ fontSize: '0.85rem', color: '#6c757d', fontWeight: 500, marginBottom: '4px' }}>
                                                        <i className="fas fa-user-plus me-1"></i>
                                                        SUPPLENTE
                                                    </div>
                                                    <div style={{ fontSize: '0.95rem', color: '#212529', paddingLeft: '20px' }}>
                                                        {formatRdlData(suppleenteData)}
                                                    </div>
                                                    {des.supplente_email && (
                                                        <div style={{ fontSize: '0.85rem', color: '#6c757d', paddingLeft: '20px', marginTop: '2px' }}>
                                                            <i className="fas fa-envelope me-1"></i>
                                                            {des.supplente_email}
                                                        </div>
                                                    )}
                                                </div>

                                                {/* Data designazione */}
                                                {des.data_designazione && (
                                                    <div style={{ fontSize: '0.8rem', color: '#6c757d', marginTop: '8px' }}>
                                                        <i className="fas fa-calendar me-1"></i>
                                                        Designato il {formatDate(des.data_designazione)}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })
                        )}
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

            {/* Modale Generazione PDF */}
            {showPdfModal && (
                <div className="modal show d-block" tabIndex="-1" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
                    <div className="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
                        <div className="modal-content">
                            <div className="modal-header">
                                <div>
                                    <h5 className="modal-title">
                                        <i className="fas fa-file-pdf me-2"></i>
                                        Generazione PDF Designazioni
                                    </h5>
                                    {/* Step indicator */}
                                    <div className="mt-2">
                                        <small className="text-muted">
                                            Step {pdfStep === 'template' ? '1' : pdfStep === 'form' ? '2' : '3'} di 3:
                                            {' '}
                                            {pdfStep === 'template' && 'Selezione Template'}
                                            {pdfStep === 'form' && 'Dati Firmatario'}
                                            {pdfStep === 'preview' && 'Preview e Generazione'}
                                        </small>
                                    </div>
                                </div>
                                <button
                                    type="button"
                                    className="btn-close"
                                    onClick={closePdfModal}
                                    disabled={generatingPdf}
                                ></button>
                            </div>
                            <div className="modal-body" style={{ maxHeight: '70vh' }}>
                                {/* Info header */}
                                <div className="alert alert-info mb-3">
                                    <i className="fas fa-info-circle me-2"></i>
                                    <strong>{selectedDesignazioni.size} designazioni selezionate</strong>
                                </div>

                                {/* STEP 1: Selezione Template */}
                                {pdfStep === 'template' && (
                                    <div>
                                        <h6 className="mb-3">Seleziona il template del documento</h6>

                                        {templates.length === 0 ? (
                                            <div className="alert alert-warning">
                                                <i className="fas fa-exclamation-triangle me-2"></i>
                                                Nessun template disponibile per questa consultazione.
                                            </div>
                                        ) : (
                                            <div className="list-group">
                                                {templates.map(template => (
                                                    <label
                                                        key={template.id}
                                                        className={`list-group-item list-group-item-action ${selectedTemplate?.id === template.id ? 'active' : ''}`}
                                                        style={{ cursor: 'pointer' }}
                                                    >
                                                        <div className="d-flex align-items-start">
                                                            <input
                                                                type="radio"
                                                                name="template"
                                                                className="me-3 mt-1"
                                                                checked={selectedTemplate?.id === template.id}
                                                                onChange={() => handleTemplateSelect(template)}
                                                                style={{ cursor: 'pointer' }}
                                                            />
                                                            <div>
                                                                <h6 className="mb-1">{template.nome}</h6>
                                                                {template.descrizione && (
                                                                    <p className="mb-1 small">{template.descrizione}</p>
                                                                )}
                                                                {template.tipo && (
                                                                    <span className="badge bg-secondary">{template.tipo}</span>
                                                                )}
                                                            </div>
                                                        </div>
                                                    </label>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* STEP 2: Form Dati Firmatario */}
                                {pdfStep === 'form' && (
                                    <div>
                                        <h6 className="mb-3">Verifica e completa i dati del firmatario</h6>

                                        <div className="row g-3">
                                            <div className="col-md-6">
                                                <label className="form-label">Cognome *</label>
                                                <input
                                                    type="text"
                                                    className="form-control"
                                                    value={formData.cognome || ''}
                                                    onChange={(e) => handleFormChange('cognome', e.target.value)}
                                                    required
                                                />
                                            </div>
                                            <div className="col-md-6">
                                                <label className="form-label">Nome *</label>
                                                <input
                                                    type="text"
                                                    className="form-control"
                                                    value={formData.nome || ''}
                                                    onChange={(e) => handleFormChange('nome', e.target.value)}
                                                    required
                                                />
                                            </div>
                                            <div className="col-md-6">
                                                <label className="form-label">Luogo di nascita *</label>
                                                <input
                                                    type="text"
                                                    className="form-control"
                                                    value={formData.luogo_nascita || ''}
                                                    onChange={(e) => handleFormChange('luogo_nascita', e.target.value)}
                                                    placeholder="es. Roma"
                                                    required
                                                />
                                            </div>
                                            <div className="col-md-6">
                                                <label className="form-label">Data di nascita *</label>
                                                <input
                                                    type="date"
                                                    className="form-control"
                                                    value={formData.data_nascita || ''}
                                                    onChange={(e) => handleFormChange('data_nascita', e.target.value)}
                                                    required
                                                />
                                            </div>

                                            {formData.tipo_firmatario === 'subdelegato' && (
                                                <>
                                                    <div className="col-12">
                                                        <label className="form-label">Domicilio *</label>
                                                        <input
                                                            type="text"
                                                            className="form-control"
                                                            value={formData.domicilio || ''}
                                                            onChange={(e) => handleFormChange('domicilio', e.target.value)}
                                                            placeholder="es. Via Roma, 123 - 00100 Roma"
                                                            required
                                                        />
                                                    </div>
                                                    <div className="col-md-6">
                                                        <label className="form-label">Tipo documento *</label>
                                                        <select
                                                            className="form-select"
                                                            value={formData.tipo_documento || ''}
                                                            onChange={(e) => handleFormChange('tipo_documento', e.target.value)}
                                                            required
                                                        >
                                                            <option value="">-- Seleziona --</option>
                                                            <option value="Carta d'Identità">Carta d'Identità</option>
                                                            <option value="Patente">Patente</option>
                                                            <option value="Passaporto">Passaporto</option>
                                                        </select>
                                                    </div>
                                                    <div className="col-md-6">
                                                        <label className="form-label">Numero documento *</label>
                                                        <input
                                                            type="text"
                                                            className="form-control"
                                                            value={formData.numero_documento || ''}
                                                            onChange={(e) => handleFormChange('numero_documento', e.target.value)}
                                                            placeholder="es. CA12345XX"
                                                            required
                                                        />
                                                    </div>
                                                </>
                                            )}

                                            {formData.tipo_firmatario === 'delegato' && (
                                                <>
                                                    <div className="col-md-6">
                                                        <label className="form-label">Carica</label>
                                                        <input
                                                            type="text"
                                                            className="form-control"
                                                            value={formData.carica || ''}
                                                            onChange={(e) => handleFormChange('carica', e.target.value)}
                                                            placeholder="es. Deputato"
                                                        />
                                                    </div>
                                                    <div className="col-md-6">
                                                        <label className="form-label">Circoscrizione</label>
                                                        <input
                                                            type="text"
                                                            className="form-control"
                                                            value={formData.circoscrizione || ''}
                                                            onChange={(e) => handleFormChange('circoscrizione', e.target.value)}
                                                            placeholder="es. Lazio 1"
                                                        />
                                                    </div>
                                                </>
                                            )}
                                        </div>

                                        {validateForm().length > 0 && (
                                            <div className="alert alert-warning mt-3">
                                                <i className="fas fa-exclamation-triangle me-2"></i>
                                                <strong>Campi mancanti:</strong> {validateForm().join(', ')}
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* STEP 3: Preview PDF */}
                                {pdfStep === 'preview' && (
                                    <div>
                                        <h6 className="mb-3">Anteprima documento</h6>

                                        {pdfPreview ? (
                                            <div style={{ height: '500px', border: '1px solid #dee2e6', borderRadius: '4px' }}>
                                                <object
                                                    data={pdfPreview}
                                                    type="application/pdf"
                                                    width="100%"
                                                    height="100%"
                                                >
                                                    <p className="p-3">
                                                        Il tuo browser non supporta la visualizzazione PDF.
                                                        <a href={pdfPreview} download className="ms-2">Scarica il PDF</a>
                                                    </p>
                                                </object>
                                            </div>
                                        ) : (
                                            <div className="alert alert-info">
                                                <div className="spinner-border spinner-border-sm me-2"></div>
                                                Generazione anteprima in corso...
                                            </div>
                                        )}

                                        <div className="alert alert-warning mt-3">
                                            <i className="fas fa-info-circle me-2"></i>
                                            Verifica attentamente i dati prima di generare il documento finale.
                                        </div>
                                    </div>
                                )}
                            </div>
                            <div className="modal-footer">
                                <button
                                    type="button"
                                    className="btn btn-secondary"
                                    onClick={closePdfModal}
                                    disabled={generatingPdf}
                                >
                                    Annulla
                                </button>

                                {pdfStep !== 'template' && (
                                    <button
                                        type="button"
                                        className="btn btn-outline-secondary"
                                        onClick={() => goToStep(pdfStep === 'form' ? 'template' : 'form')}
                                        disabled={generatingPdf}
                                    >
                                        <i className="fas fa-arrow-left me-2"></i>
                                        Indietro
                                    </button>
                                )}

                                {pdfStep === 'template' && (
                                    <button
                                        type="button"
                                        className="btn btn-primary"
                                        onClick={() => goToStep('form')}
                                        disabled={!selectedTemplate}
                                    >
                                        Avanti
                                        <i className="fas fa-arrow-right ms-2"></i>
                                    </button>
                                )}

                                {pdfStep === 'form' && (
                                    <button
                                        type="button"
                                        className="btn btn-primary"
                                        onClick={generatePreview}
                                        disabled={validateForm().length > 0 || generatingPdf}
                                    >
                                        {generatingPdf ? (
                                            <>
                                                <span className="spinner-border spinner-border-sm me-2"></span>
                                                Generazione...
                                            </>
                                        ) : (
                                            <>
                                                Genera Anteprima
                                                <i className="fas fa-arrow-right ms-2"></i>
                                            </>
                                        )}
                                    </button>
                                )}

                                {pdfStep === 'preview' && (
                                    <button
                                        type="button"
                                        className="btn btn-success"
                                        onClick={generateBatch}
                                        disabled={generatingPdf}
                                    >
                                        {generatingPdf ? (
                                            <>
                                                <span className="spinner-border spinner-border-sm me-2"></span>
                                                Generazione PDF...
                                            </>
                                        ) : (
                                            <>
                                                <i className="fas fa-check me-2"></i>
                                                Genera PDF Finale
                                            </>
                                        )}
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}

export default GestioneDesignazioni;
