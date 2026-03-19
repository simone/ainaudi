// GestioneDesignazioni.js - Process-driven interface for formal RDL designations
import React, { useState, useEffect } from 'react';
import './GestioneDesignazioni.css';
import WizardDesignazioni from './WizardDesignazioni';
import ConfirmModal from '../components/ConfirmModal';
import PDFViewer from '../components/PDFViewer';

/**
 * Workflow process-driven per designazioni formali RDL.
 *
 * Step 1: Seleziona sezioni mappate (checkbox)
 * Step 2: Avvia Atto di Designazione → fotografa + genera 2 PDF automaticamente
 * Step 3: Controlla PDF
 * Step 4: Conferma Atto → tutto CONFERMATO oppure Annulla → tutto eliminato
 */
function GestioneDesignazioni({ client, consultazione, setError }) {
    const [loading, setLoading] = useState(true);
    const [data, setData] = useState(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [path, setPath] = useState({
        regione_id: null,
        provincia_id: null,
        comune_id: null,
        municipio_id: null
    });

    // Data states
    const [mappature, setMappature] = useState([]); // Sezioni mappate disponibili
    const [processiArchivio, setProcessiArchivio] = useState([]); // Processi completati (APPROVATO)
    const [processiStorico, setProcessiStorico] = useState([]); // Processi annullati/non completati per audit
    const [expandedProcessi, setExpandedProcessi] = useState(new Set()); // ID processi espansi
    const [selectedSezioni, setSelectedSezioni] = useState(new Set()); // Sezioni selezionate per processo
    const [processoInCorso, setProcessoInCorso] = useState(null); // Processo attivo {batch_ind, batch_riep, designazioni}
    const [processiCompletati, setProcessiCompletati] = useState([]); // Archivio processi confermati

    // Export XLSX modal
    const [showExportModal, setShowExportModal] = useState(false);
    const [exportMode, setExportMode] = useState('all'); // 'selected' | 'all'
    const [exportIncludiConfermati, setExportIncludiConfermati] = useState(true);
    const [exporting, setExporting] = useState(false);

    // Loading states
    const [loadingData, setLoadingData] = useState(false);
    const [avviandoProcesso, setAvviandoProcesso] = useState(false);

    // Messages
    const [successMessage, setSuccessMessage] = useState(null);

    // Wizard state
    const [showWizard, setShowWizard] = useState(false);
    const [wizardProcessoId, setWizardProcessoId] = useState(null); // For resuming existing process

    // Confirm modal state
    const [showAnnullaModal, setShowAnnullaModal] = useState(false);
    const [showEmailModal, setShowEmailModal] = useState(false);
    const [emailProcessoId, setEmailProcessoId] = useState(null);
    const [allegaDesignazione, setAllegaDesignazione] = useState(false);

    // PDF Viewer state
    const [pdfViewer, setPdfViewer] = useState(null); // { url, titolo, blobUrl } quando aperto
    const [loadingPdf, setLoadingPdf] = useState(false);

    // Email sending state
    const [inviandoEmail, setInviandoEmail] = useState({}); // { processoId: boolean }
    const [emailProgress, setEmailProgress] = useState({}); // { processoId: { percentage, status, current, total, sent, failed } }

    useEffect(() => {
        if (client && consultazione) {
            loadData();
        }
    }, [client, consultazione, path.regione_id, path.provincia_id, path.comune_id, path.municipio_id]);

    // Debug: Log pdfViewer state changes
    useEffect(() => {
        console.log('[GestioneDesignazioni] pdfViewer state changed:', pdfViewer);
    }, [pdfViewer]);

    const loadData = async () => {
        setLoading(true);
        try {
            const result = await client.mappatura.gerarchica({
                consultazione_id: consultazione.id,
                regione_id: path.regione_id,
                provincia_id: path.provincia_id,
                comune_id: path.comune_id,
                municipio_id: path.municipio_id
            });

            if (result.error) {
                throw new Error(result.error);
            }

            setData(result);

            // Auto-skip if only one choice
            if (result.auto_skip && result.items && result.items.length === 1) {
                handleDrillDown(result.items[0]);
                return;
            }

            // If we reached comune level, load designazioni data
            if (path.comune_id) {
                await loadComuneData(path.comune_id, path.municipio_id);
            }

            window.scrollTo(0, 0);
        } catch (err) {
            console.error('[GestioneDesignazioni] Error loading data:', err);
            setError?.('Errore caricamento dati: ' + err.message);
        } finally {
            setLoading(false);
        }
    };

    const loadComuneData = async (comuneId, municipioId) => {
        if (!comuneId || !consultazione) return;

        setLoadingData(true);
        try {
            console.log('[GestioneDesignazioni] Loading data for comune:', comuneId);

            // 1. Load nuove mappature (sezioni senza designazioni confermate - già filtrate dal backend)
            const mappaturaResult = await client.mappatura.sezioni({
                comune_id: comuneId,
                municipio_id: municipioId,
                filter_status: 'nuove_mappature'
            });

            console.log('[GestioneDesignazioni] Mappatura result:', mappaturaResult);

            if (!mappaturaResult.error && mappaturaResult.plessi) {
                console.log('[GestioneDesignazioni] Plessi trovati:', mappaturaResult.plessi.length);
                const allSezioni = [];
                mappaturaResult.plessi.forEach(plesso => {
                    if (plesso.sezioni) {
                        plesso.sezioni.forEach(sez => {
                            // SOLO sezioni con effettivo o supplente
                            if (sez.effettivo || sez.supplente) {
                                allSezioni.push({
                                    ...sez,
                                    plesso_denominazione: plesso.denominazione,
                                    sezione_numero: sez.numero,
                                    rdl_effettivo: sez.effettivo,
                                    rdl_supplente: sez.supplente
                                });
                            }
                        });
                    }
                });
                console.log('[GestioneDesignazioni] Nuove mappature disponibili:', allSezioni.length);
                setMappature(allSezioni);
            }

            // 2. Carica tutti i processi per questo comune/consultazione
            const processiResult = await client.deleghe.processi.list(consultazione.id);
            console.log('[GestioneDesignazioni] Processi result:', processiResult);

            if (!processiResult.error && processiResult.results) {
                const tuttiProcessi = processiResult.results;
                console.log('[GestioneDesignazioni] Total processi found:', tuttiProcessi.length);

                // Processi attivi: BOZZA, IN_GENERAZIONE, GENERATO
                const statiAttivi = ['BOZZA', 'IN_GENERAZIONE', 'GENERATO'];
                const processiAttivi = tuttiProcessi.filter(p => statiAttivi.includes(p.stato));

                if (processiAttivi.length > 0) {
                    // Prendi il processo attivo più recente
                    const processoAttivo = processiAttivi[0];
                    console.log('[GestioneDesignazioni] Processo attivo:', processoAttivo);
                    setProcessoInCorso(processoAttivo);
                } else {
                    setProcessoInCorso(null);
                }

                // Processi completati: APPROVATO, INVIATO
                const processiCompletati = tuttiProcessi.filter(p => ['APPROVATO', 'INVIATO'].includes(p.stato));
                console.log('[GestioneDesignazioni] Processi completati:', processiCompletati.length);
                setProcessiArchivio(processiCompletati);

                // Processi annullati/test per storico
                const processiStorici = tuttiProcessi.filter(p => ['ANNULLATO', 'TEST'].includes(p.stato));
                console.log('[GestioneDesignazioni] Processi storici:', processiStorici.length);
                setProcessiStorico(processiStorici);
            } else {
                setProcessoInCorso(null);
                setProcessiArchivio([]);
                setProcessiStorico([]);
            }

        } catch (err) {
            console.error('[GestioneDesignazioni] Error loading comune data:', err);
            setError?.('Errore caricamento dati comune: ' + err.message);
        } finally {
            setLoadingData(false);
        }
    };

    const handleDrillDown = (item) => {
        const newPath = { ...path };

        switch (item.tipo) {
            case 'regione':
                newPath.regione_id = item.id;
                newPath.provincia_id = null;
                newPath.comune_id = null;
                newPath.municipio_id = null;
                break;
            case 'provincia':
                newPath.provincia_id = item.id;
                newPath.comune_id = null;
                newPath.municipio_id = null;
                break;
            case 'comune':
                newPath.comune_id = item.id;
                newPath.municipio_id = null;
                break;
            case 'municipio':
                newPath.municipio_id = item.id;
                break;
            default:
                return;
        }

        setPath(newPath);
        setSearchQuery('');
    };

    const handleBack = () => {
        const newPath = { ...path };

        if (path.municipio_id) {
            newPath.municipio_id = null;
        } else if (path.comune_id) {
            newPath.comune_id = null;
        } else if (path.provincia_id) {
            newPath.provincia_id = null;
        } else if (path.regione_id) {
            newPath.regione_id = null;
        }

        setPath(newPath);
        setSearchQuery('');
        setSelectedSezioni(new Set());
    };

    const handleToggleProcesso = (processoId) => {
        const newExpanded = new Set(expandedProcessi);
        if (newExpanded.has(processoId)) {
            newExpanded.delete(processoId);
        } else {
            newExpanded.add(processoId);
        }
        setExpandedProcessi(newExpanded);
    };

    const handleToggleSezione = (sezioneId) => {
        const newSelected = new Set(selectedSezioni);
        if (newSelected.has(sezioneId)) {
            newSelected.delete(sezioneId);
        } else {
            newSelected.add(sezioneId);
        }
        setSelectedSezioni(newSelected);
    };

    const handleToggleAll = () => {
        if (selectedSezioni.size === mappature.length) {
            setSelectedSezioni(new Set());
        } else {
            setSelectedSezioni(new Set(mappature.map(m => m.id)));
        }
    };

    const handleAvviaProcesso = () => {
        console.log('[GestioneDesignazioni] handleAvviaProcesso chiamato!');
        console.log('[GestioneDesignazioni] selectedSezioni.size:', selectedSezioni.size);
        console.log('[GestioneDesignazioni] showWizard prima:', showWizard);

        if (selectedSezioni.size === 0) {
            console.log('[GestioneDesignazioni] ERRORE: nessuna sezione selezionata');
            setError?.('Seleziona almeno una sezione per avviare l\'atto di designazione');
            return;
        }

        console.log('[GestioneDesignazioni] Apertura wizard per', selectedSezioni.size, 'sezioni');
        setWizardProcessoId(null); // New process
        setShowWizard(true);
    };

    const handleRiprendiProcesso = () => {
        if (!processoInCorso?.id) return;
        console.log('[GestioneDesignazioni] Riprendi processo:', processoInCorso.id);
        setWizardProcessoId(processoInCorso.id);
        setShowWizard(true);
    };

    const handleExportXlsx = async () => {
        setExporting(true);
        try {
            const opts = {
                includiConfermati: exportIncludiConfermati,
            };
            if (exportMode === 'selected' && selectedSezioni.size > 0) {
                opts.sezioneIds = Array.from(selectedSezioni);
            }
            const blob = await client.mappatura.reportXlsx(path.comune_id, opts);
            const blobUrl = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = blobUrl;
            const comune = (data?.summary?.nome || 'comune').replace(/\s+/g, '_').toLowerCase();
            link.download = `mappatura_rdl_${comune}.xlsx`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(blobUrl);
            setShowExportModal(false);
        } catch (err) {
            setError?.('Errore download XLSX: ' + err.message);
        } finally {
            setExporting(false);
        }
    };

    const handleWizardSuccess = () => {
        console.log('[GestioneDesignazioni] Wizard completato con successo');
        setSuccessMessage('✓ Atto di designazione completato con successo!');
        setSelectedSezioni(new Set());
        loadComuneData(path.comune_id, path.municipio_id);
    };

    const handleConfermaProcesso = async () => {
        if (!processoInCorso) return;

        try {
            console.log('[GestioneDesignazioni] Conferma processo');

            // Conferma il processo
            const result = await client.deleghe.processi.conferma(processoInCorso.id);
            if (result.error) {
                throw new Error('Errore conferma processo: ' + result.error);
            }

            setSuccessMessage(
                `✓ Atto di designazione confermato con successo!\n` +
                `Tutte le designazioni sono ora CONFERMATE`
            );

            await loadComuneData(path.comune_id, path.municipio_id);

        } catch (err) {
            console.error('[GestioneDesignazioni] Error conferma processo:', err);
            setError?.('Errore conferma atto: ' + err.message);
        }
    };

    const handleAnnullaProcesso = () => {
        if (!processoInCorso) return;
        setShowAnnullaModal(true);
    };

    const confirmAnnullaProcesso = async () => {
        setShowAnnullaModal(false);

        try {
            console.log('[GestioneDesignazioni] Annullamento processo');

            // Annulla il processo
            const result = await client.deleghe.processi.annulla(processoInCorso.id);
            if (result.error) {
                throw new Error('Errore annullamento processo: ' + result.error);
            }

            setSuccessMessage('✓ Atto di designazione annullato con successo! Le sezioni sono di nuovo disponibili.');
            setProcessoInCorso(null);
            await loadComuneData(path.comune_id, path.municipio_id);

        } catch (err) {
            console.error('[GestioneDesignazioni] Error annulla processo:', err);
            setError?.('Errore annullamento atto: ' + err.message);
        }
    };

    const handleDownloadIndividuale = async (processoId) => {
        if (!processoId) {
            setError?.('Impossibile scaricare: atto non trovato');
            return;
        }
        try {
            await client.deleghe.processi.downloadIndividuale(processoId);
        } catch (err) {
            console.error('[GestioneDesignazioni] Errore download PDF individuale:', err);
            setError?.('Errore download PDF: ' + err.message);
        }
    };

    const handleDownloadCumulativo = async (processoId) => {
        if (!processoId) {
            setError?.('Impossibile scaricare: atto non trovato');
            return;
        }
        try {
            await client.deleghe.processi.downloadCumulativo(processoId);
        } catch (err) {
            console.error('[GestioneDesignazioni] Errore download PDF cumulativo:', err);
            setError?.('Errore download PDF: ' + err.message);
        }
    };

    // Cleanup blob URL quando chiudi il viewer
    const handleClosePdfViewer = () => {
        if (pdfViewer?.blobUrl) {
            console.log('[GestioneDesignazioni] Revoke blob URL:', pdfViewer.blobUrl);
            window.URL.revokeObjectURL(pdfViewer.blobUrl);
        }
        setPdfViewer(null);
    };

    // Handler invio email agli RDL
    const handleInviaEmail = (processoId) => {
        setEmailProcessoId(processoId);
        setShowEmailModal(true);
    };

    const confirmInviaEmail = async () => {
        setShowEmailModal(false);
        const processoId = emailProcessoId;
        const allegaPdf = allegaDesignazione;
        setEmailProcessoId(null);
        setAllegaDesignazione(false);

        setInviandoEmail(prev => ({ ...prev, [processoId]: true }));
        setEmailProgress(prev => ({ ...prev, [processoId]: { percentage: 0, status: 'STARTED' } }));

        try {
            // Avvia invio asincrono
            const serverUrl = client.server || process.env.REACT_APP_API_URL || window.location.origin.replace(':3000', ':3001');
            const response = await fetch(`${serverUrl}/api/deleghe/processi/${processoId}/invia-email/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ allega_designazione: allegaPdf })
            });

            const data = await response.json();

            if (data.success) {
                const taskId = data.task_id;
                // Avvia polling per progress
                pollEmailProgress(processoId, taskId);
            } else {
                throw new Error(data.error || 'Errore sconosciuto');
            }
        } catch (error) {
            console.error('Errore invio email:', error);
            setError?.(`Errore durante l'avvio dell'invio email: ${error.message || error}`);
            setInviandoEmail(prev => ({ ...prev, [processoId]: false }));
            setEmailProgress(prev => ({ ...prev, [processoId]: null }));
        }
    };

    // Polling progress invio email
    const pollEmailProgress = async (processoId, taskId) => {
        try {
            const serverUrl = client.server || process.env.REACT_APP_API_URL || window.location.origin.replace(':3000', ':3001');
            const response = await fetch(`${serverUrl}/api/deleghe/processi/${processoId}/email-progress/`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                }
            });

            const data = await response.json();

            if (data.status === 'PROGRESS' || data.status === 'STARTED') {
                // Aggiorna progress bar
                setEmailProgress(prev => ({
                    ...prev,
                    [processoId]: {
                        percentage: data.percentage || 0,
                        status: data.status,
                        current: data.current,
                        total: data.total,
                        sent: data.sent,
                        failed: data.failed
                    }
                }));

                // Poll ogni 2 secondi
                setTimeout(() => pollEmailProgress(processoId, taskId), 2000);

            } else if (data.status === 'SUCCESS') {
                // Completato
                setInviandoEmail(prev => ({ ...prev, [processoId]: false }));
                setEmailProgress(prev => ({ ...prev, [processoId]: null }));

                const successMsg = `✅ Email inviate con successo!\n\n` +
                    `📧 Inviate: ${data.sent}` +
                    (data.failed > 0 ? `\n❌ Fallite: ${data.failed}` : '');

                setSuccessMessage(successMsg);

                // Ricarica lista processi
                if (path.comune_id) {
                    await loadComuneData(path.comune_id, path.municipio_id);
                }

                // Auto-clear success message dopo 5 secondi
                setTimeout(() => setSuccessMessage(null), 5000);

            } else if (data.status === 'FAILURE') {
                // Errore
                setInviandoEmail(prev => ({ ...prev, [processoId]: false }));
                setEmailProgress(prev => ({ ...prev, [processoId]: null }));

                setError?.(`Errore durante l'invio: ${data.error || 'Errore sconosciuto'}`);
            }

        } catch (error) {
            console.error('Errore polling progress:', error);
            // Riprova dopo 5 secondi in caso di errore di rete
            setTimeout(() => pollEmailProgress(processoId, taskId), 5000);
        }
    };

    // Rendering helpers
    const canGoBack = path.regione_id || path.provincia_id || path.comune_id || path.municipio_id;

    const getLevelIcon = () => {
        switch (data?.level) {
            case 'regioni': return 'fa-map';
            case 'province': return 'fa-map-marked-alt';
            case 'comuni': return 'fa-city';
            case 'municipi': return 'fa-building';
            default: return 'fa-th-list';
        }
    };

    const getLevelTitle = () => {
        switch (data?.level) {
            case 'regioni': return 'Regioni';
            case 'province': return 'Province';
            case 'comuni': return 'Comuni';
            case 'municipi': return 'Municipi';
            default: return 'Designazioni';
        }
    };

    const filteredItems = data?.items?.filter(item => {
        // Nascondi territori senza sezioni mappate
        if (item.sezioni_assegnate !== undefined && item.sezioni_assegnate === 0) return false;
        if (!searchQuery) return true;
        return item.nome.toLowerCase().includes(searchQuery.toLowerCase());
    }) || [];

    if (loading) {
        return (
            <div className="gd-container">
                <div className="gd-loading">
                    <div className="spinner-border text-primary"></div>
                    <p>Caricamento...</p>
                </div>
            </div>
        );
    }

    // Vista Comune: Tab Mappature + Processo in Corso
    if (path.comune_id) {
        console.log('[GestioneDesignazioni] Render vista comune, showWizard:', showWizard);
        return (
            <div className="gd-container">
                {/* Breadcrumb + Actions */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <nav aria-label="breadcrumb" className="gd-breadcrumb" style={{ marginBottom: 0 }}>
                        <ol className="breadcrumb mb-0">
                            <li className="breadcrumb-item">
                                <a
                                    href="#"
                                    onClick={(e) => { e.preventDefault(); handleBack(); }}
                                    className="gd-breadcrumb-link"
                                >
                                    <i className="fas fa-arrow-left"></i>
                                    <span>Indietro</span>
                                </a>
                            </li>
                            <li className="breadcrumb-item active gd-breadcrumb-current">
                                {data?.summary?.nome || 'Comune'}
                            </li>
                        </ol>
                    </nav>
                    <button
                        className="btn btn-sm btn-outline-success"
                        onClick={() => {
                            setExportMode(selectedSezioni.size > 0 ? 'selected' : 'all');
                            setShowExportModal(true);
                        }}
                    >
                        <i className="fas fa-file-excel me-1"></i>
                        Scarica XLSX
                    </button>
                </div>

                {/* Success message */}
                {successMessage && (
                    <div className="alert alert-success alert-dismissible fade show gd-alert" role="alert">
                        <i className="fas fa-check-circle me-2"></i>
                        <pre className="mb-0" style={{whiteSpace: 'pre-wrap'}}>{successMessage}</pre>
                        <button
                            type="button"
                            className="btn-close"
                            onClick={() => setSuccessMessage(null)}
                            aria-label="Chiudi"
                        ></button>
                    </div>
                )}

                {/* PROCESSO IN CORSO */}
                {processoInCorso && (
                    <div className="gd-card border-primary">
                        <div className="gd-card-header bg-primary text-white">
                            <h5 className="gd-card-title mb-0">
                                <i className="fas fa-cog fa-spin"></i>
                                <span>Atto di Designazione RDL in Corso</span>
                            </h5>
                        </div>
                        <div className="gd-card-body">
                            <div className="gd-processo-alert">
                                <i className="fas fa-info-circle me-2"></i>
                                <strong>Controlla i documenti generati</strong>
                                <p className="mb-0 mt-2">
                                    Verifica che i PDF siano corretti, poi conferma l'atto per rendere definitive le designazioni.
                                    Se trovi errori, puoi annullare l'atto e riavviarne uno nuovo.
                                </p>
                            </div>

                            {/* Documento INDIVIDUALE */}
                            <div className="gd-pdf-document">
                                <div className="gd-pdf-document-header">
                                    <div className="gd-pdf-document-info">
                                        <div className="gd-pdf-document-title">
                                            <i className="fas fa-file-pdf text-danger"></i>
                                            <span>Documento INDIVIDUALE</span>
                                        </div>
                                        <span className="gd-pdf-document-subtitle">
                                            Un PDF per ogni sezione • Processo #{processoInCorso.id}
                                        </span>
                                        <span className={`badge ${processoInCorso.documento_individuale ? 'bg-success' : 'bg-warning'}`}>
                                            {processoInCorso.documento_individuale ? 'GENERATO' : processoInCorso.stato}
                                        </span>
                                    </div>
                                    <div className="gd-pdf-document-actions">
                                        {processoInCorso.documento_individuale && (
                                            <button
                                                className="btn btn-primary gd-btn-preview"
                                                onClick={() => handleDownloadIndividuale(processoInCorso.id)}
                                            >
                                                <i className="fas fa-download"></i>
                                                <span>Scarica PDF</span>
                                            </button>
                                        )}
                                    </div>
                                </div>
                            </div>

                            {/* Documento RIEPILOGATIVO */}
                            <div className="gd-pdf-document">
                                <div className="gd-pdf-document-header">
                                    <div className="gd-pdf-document-info">
                                        <div className="gd-pdf-document-title">
                                            <i className="fas fa-file-pdf text-danger"></i>
                                            <span>Documento RIEPILOGATIVO</span>
                                        </div>
                                        <span className="gd-pdf-document-subtitle">
                                            Un PDF cumulativo • Processo #{processoInCorso.id}
                                        </span>
                                        <span className={`badge ${processoInCorso.documento_cumulativo ? 'bg-success' : 'bg-warning'}`}>
                                            {processoInCorso.documento_cumulativo ? 'GENERATO' : processoInCorso.stato}
                                        </span>
                                    </div>
                                    <div className="gd-pdf-document-actions">
                                        {processoInCorso.documento_cumulativo && (
                                            <button
                                                className="btn btn-primary gd-btn-preview"
                                                onClick={() => handleDownloadCumulativo(processoInCorso.id)}
                                            >
                                                <i className="fas fa-download"></i>
                                                <span>Scarica PDF</span>
                                            </button>
                                        )}
                                    </div>
                                </div>
                            </div>

                            {/* Azioni finali */}
                            <div className="gd-processo-actions">
                                <button
                                    className="btn btn-outline-danger"
                                    onClick={handleAnnullaProcesso}
                                >
                                    <i className="fas fa-times me-1"></i>
                                    <span>Annulla Atto</span>
                                </button>
                                <button
                                    className="btn btn-primary"
                                    onClick={handleRiprendiProcesso}
                                >
                                    <i className="fas fa-redo me-1"></i>
                                    <span>Continua</span>
                                </button>
                                <button
                                    className="btn btn-success"
                                    onClick={handleConfermaProcesso}
                                    disabled={
                                        !processoInCorso.documento_individuale ||
                                        !processoInCorso.documento_cumulativo
                                    }
                                >
                                    <i className="fas fa-check me-1"></i>
                                    <span>Conferma Atto</span>
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* SEZIONI MAPPATE */}
                <div className="gd-card">
                    <div className="gd-card-header">
                        <div className="gd-card-header-content">
                            <h6 className="gd-card-title mb-0">
                                <i className="fas fa-map-marked-alt"></i>
                                <span>Sezioni Mappate ({mappature.length})</span>
                            </h6>
                            {console.log('[GestioneDesignazioni] Rendering pulsante Avvia, processoInCorso:', processoInCorso, 'mappature.length:', mappature.length)}
                            {!processoInCorso && mappature.length > 0 && (
                                <button
                                    className="btn btn-primary"
                                    onClick={(e) => {
                                        console.log('[GestioneDesignazioni] Click sul pulsante Avvia Processo!');
                                        handleAvviaProcesso();
                                    }}
                                    disabled={selectedSezioni.size === 0 || avviandoProcesso}
                                    style={{minHeight: '44px'}}
                                >
                                    {avviandoProcesso ? (
                                        <>
                                            <span className="spinner-border spinner-border-sm me-2"></span>
                                            <span>Avvio atto...</span>
                                        </>
                                    ) : (
                                        <>
                                            <i className="fas fa-play me-2"></i>
                                            <span>Avvia Atto ({selectedSezioni.size})</span>
                                        </>
                                    )}
                                </button>
                            )}
                        </div>
                    </div>

                    <div className="gd-card-body">
                        {processoInCorso && (
                            <div className="alert alert-warning mb-0">
                                <i className="fas fa-exclamation-triangle me-2"></i>
                                <strong>Atto in corso</strong> - Completa o annulla l'atto attivo prima di avviarne uno nuovo.
                            </div>
                        )}

                        {!processoInCorso && mappature.length === 0 && (
                            <div className="gd-empty-state">
                                <i className="fas fa-inbox gd-empty-icon"></i>
                                <div className="gd-empty-title">Nessuna sezione mappata in questo comune</div>
                                <div className="gd-empty-subtitle">
                                    Vai su "Mappatura" per assegnare RDL alle sezioni
                                </div>
                            </div>
                        )}

                        {!processoInCorso && mappature.length > 0 && (
                            <>
                                <div className="gd-select-all-bar">
                                    <label className="gd-select-all-label">
                                        <input
                                            type="checkbox"
                                            checked={selectedSezioni.size === mappature.length}
                                            onChange={handleToggleAll}
                                        />
                                        <span>Seleziona tutte</span>
                                    </label>
                                    <span className="gd-select-counter">
                                        {selectedSezioni.size} di {mappature.length} selezionate
                                    </span>
                                </div>

                                {mappature.map(sez => (
                                    <div key={sez.id} className="gd-sezione-item">
                                        <div className="gd-sezione-checkbox">
                                            <input
                                                type="checkbox"
                                                checked={selectedSezioni.has(sez.id)}
                                                onChange={() => handleToggleSezione(sez.id)}
                                                aria-label={`Seleziona sezione ${sez.sezione_numero}`}
                                            />
                                        </div>
                                        <div className="gd-sezione-content">
                                            <div className="gd-sezione-numero">Sez. {sez.sezione_numero}</div>
                                            <div className="gd-sezione-rdl">
                                                {sez.rdl_effettivo && (
                                                    <div className="gd-rdl-effettivo">
                                                        <span className="gd-rdl-label">Eff:</span> {sez.rdl_effettivo.cognome} {sez.rdl_effettivo.nome}
                                                    </div>
                                                )}
                                                {sez.rdl_supplente && (
                                                    <div className="gd-rdl-supplente">
                                                        <span className="gd-rdl-label">Sup:</span> {sez.rdl_supplente.cognome} {sez.rdl_supplente.nome}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </>
                        )}
                    </div>
                </div>

                {/* ARCHIVIO PROCESSI COMPLETATI */}
                {processiArchivio.length > 0 && (
                    <div className="gd-card">
                        <div className="gd-card-header">
                            <h6 className="gd-card-title mb-0">
                                <i className="fas fa-check-circle text-success"></i>
                                <span>Archivio Atti di Designazione Completati ({processiArchivio.length})</span>
                            </h6>
                        </div>
                        <div className="gd-card-body">
                            {processiArchivio.map(processo => (
                                <div key={processo.id} className="gd-archivio-item">
                                    <div
                                        className="gd-archivio-header"
                                        onClick={() => handleToggleProcesso(processo.id)}
                                    >
                                        <div className="gd-archivio-chevron">
                                            <i className={`fas fa-chevron-${expandedProcessi.has(processo.id) ? 'down' : 'right'}`}></i>
                                        </div>
                                        <div className="gd-archivio-info">
                                            <div>
                                                <div className="gd-archivio-title">
                                                    Atto designazione RDL di {data?.summary?.nome || 'Comune'} #{processo.id}
                                                </div>
                                                {processo.delegato && (
                                                    <div className="gd-archivio-delegato">
                                                        <i className="fas fa-user"></i>
                                                        <span>{processo.delegato.nome_completo} ({processo.delegato.tipo})</span>
                                                    </div>
                                                )}
                                                <div className="gd-archivio-meta">
                                                    {processo.n_designazioni} sezioni • Completato il {new Date(processo.approvata_at).toLocaleDateString('it-IT')} alle {new Date(processo.approvata_at).toLocaleTimeString('it-IT', {hour: '2-digit', minute: '2-digit'})}
                                                </div>
                                            </div>
                                            <div className="gd-archivio-badge">
                                                <span className="badge bg-success">APPROVATO</span>
                                            </div>
                                        </div>
                                    </div>

                                    {expandedProcessi.has(processo.id) && (
                                        <div className="gd-archivio-body">
                                            {/* Documenti PDF */}
                                            <div className="gd-archivio-section">
                                                <h6 className="gd-archivio-section-title">Documenti</h6>
                                                <div className="gd-archivio-pdf-buttons">
                                                    {processo.documento_individuale_url && (
                                                        <button
                                                            onClick={(e) => {
                                                                console.log('[Archivio] Click PDF Individuale, processo.id:', processo.id);
                                                                e.stopPropagation();
                                                                e.preventDefault();
                                                                handleDownloadIndividuale(processo.id);
                                                            }}
                                                            className="btn btn-outline-primary"
                                                            type="button"
                                                        >
                                                            <i className="fas fa-download me-1"></i>
                                                            <span>PDF Individuale</span>
                                                        </button>
                                                    )}
                                                    {processo.documento_cumulativo_url && (
                                                        <button
                                                            onClick={(e) => {
                                                                console.log('[Archivio] Click PDF Cumulativo, processo.id:', processo.id);
                                                                e.stopPropagation();
                                                                e.preventDefault();
                                                                handleDownloadCumulativo(processo.id);
                                                            }}
                                                            className="btn btn-outline-primary"
                                                            type="button"
                                                        >
                                                            <i className="fas fa-download me-1"></i>
                                                            <span>PDF Cumulativo</span>
                                                        </button>
                                                    )}
                                                </div>

                                                {/* Invio Email RDL */}
                                                <div className="gd-archivio-email mt-3">
                                                    {!processo.email_gia_inviate ? (
                                                        <>
                                                            <button
                                                                className="btn btn-success btn-sm"
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    e.preventDefault();
                                                                    handleInviaEmail(processo.id);
                                                                }}
                                                                disabled={inviandoEmail[processo.id]}
                                                                title="Invia email agli RDL designati"
                                                            >
                                                                {inviandoEmail[processo.id] ? (
                                                                    <>
                                                                        <span className="spinner-border spinner-border-sm me-1"></span>
                                                                        {emailProgress[processo.id] ? (
                                                                            `Invio ${emailProgress[processo.id].current || 0}/${emailProgress[processo.id].total || 0}...`
                                                                        ) : (
                                                                            'Avvio invio...'
                                                                        )}
                                                                    </>
                                                                ) : (
                                                                    <>
                                                                        <i className="fas fa-envelope me-1"></i>
                                                                        Invia Email agli RDL
                                                                    </>
                                                                )}
                                                            </button>

                                                            {/* Progress bar sotto il bottone */}
                                                            {emailProgress[processo.id] && (
                                                                <div className="progress mt-2" style={{height: '20px'}}>
                                                                    <div
                                                                        className="progress-bar progress-bar-striped progress-bar-animated"
                                                                        role="progressbar"
                                                                        style={{width: `${emailProgress[processo.id].percentage}%`}}
                                                                    >
                                                                        {emailProgress[processo.id].percentage}%
                                                                    </div>
                                                                </div>
                                                            )}
                                                        </>
                                                    ) : (
                                                        <div className="alert alert-info mb-0" style={{fontSize: '0.875rem', padding: '0.5rem'}}>
                                                            <i className="fas fa-check-circle me-1"></i>
                                                            Email inviate il {new Date(processo.email_inviate_at).toLocaleDateString('it-IT')} alle {new Date(processo.email_inviate_at).toLocaleTimeString('it-IT', {hour: '2-digit', minute: '2-digit'})}
                                                            <br />
                                                            <small>
                                                                {processo.n_email_inviate} inviate
                                                                {processo.n_email_fallite > 0 && `, ${processo.n_email_fallite} fallite`}
                                                            </small>
                                                        </div>
                                                    )}
                                                </div>
                                            </div>

                                            {/* Riepilogo Designazioni */}
                                            <div className="gd-archivio-section">
                                                <div className="alert alert-info mb-0">
                                                    <i className="fas fa-users me-2"></i>
                                                    <strong>{processo.n_designazioni || 0} designazioni confermate</strong>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* ARCHIVIO STORICO (Annullati / Non Completati) */}
                {processiStorico.length > 0 && (
                    <div className="gd-card">
                        <div className="gd-card-header">
                            <div className="gd-card-header-content">
                                <h6 className="gd-card-title mb-0">
                                    <i className="fas fa-history text-muted"></i>
                                    <span>Archivio Storico ({processiStorico.length})</span>
                                </h6>
                                <small className="text-muted">Atti non completati o annullati (audit)</small>
                            </div>
                        </div>
                        <div className="gd-card-body">
                            {processiStorico.map(processo => (
                                <div key={processo.id} className="gd-archivio-item">
                                    <div
                                        className="gd-archivio-header"
                                        onClick={() => handleToggleProcesso(processo.id)}
                                    >
                                        <div className="gd-archivio-chevron">
                                            <i className={`fas fa-chevron-${expandedProcessi.has(processo.id) ? 'down' : 'right'}`}></i>
                                        </div>
                                        <div className="gd-archivio-info">
                                            <div>
                                                <div className="gd-archivio-title">
                                                    Atto designazione RDL di {data?.summary?.nome || 'Comune'} #{processo.id}
                                                </div>
                                                {processo.delegato && (
                                                    <div className="gd-archivio-delegato">
                                                        <i className="fas fa-user"></i>
                                                        <span>{processo.delegato.nome_completo} ({processo.delegato.tipo})</span>
                                                    </div>
                                                )}
                                                <div className="gd-archivio-meta">
                                                    {processo.n_designazioni} sezioni • Creato il {new Date(processo.created_at).toLocaleDateString('it-IT')} alle {new Date(processo.created_at).toLocaleTimeString('it-IT', {hour: '2-digit', minute: '2-digit'})}
                                                </div>
                                            </div>
                                            <div className="gd-archivio-badge">
                                                <span className={`badge ${processo.stato === 'ANNULLATO' ? 'bg-danger' : 'bg-secondary'}`}>
                                                    {processo.stato}
                                                </span>
                                            </div>
                                        </div>
                                    </div>

                                    {expandedProcessi.has(processo.id) && (
                                        <div className="gd-archivio-body">
                                            {/* Informazioni processo */}
                                            <div className="gd-archivio-section">
                                                <div className="gd-archivio-meta">
                                                    Creato da: {processo.created_by_email} • il {new Date(processo.created_at).toLocaleDateString('it-IT')} alle {new Date(processo.created_at).toLocaleTimeString('it-IT', {hour: '2-digit', minute: '2-digit'})}
                                                </div>
                                            </div>

                                            {/* Riepilogo Designazioni */}
                                            <div className="gd-archivio-section">
                                                <div className="alert alert-info mb-0">
                                                    <i className="fas fa-users me-2"></i>
                                                    <strong>{processo.n_designazioni || 0} designazioni confermate</strong>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Wizard multi-step */}
                {console.log('[GestioneDesignazioni] Prima di WizardDesignazioni, showWizard:', showWizard)}
                <WizardDesignazioni
                    show={showWizard}
                    onClose={() => { setShowWizard(false); setWizardProcessoId(null); }}
                    client={client}
                    consultazione={consultazione}
                    sezioniSelezionate={selectedSezioni}
                    onSuccess={handleWizardSuccess}
                    existingProcessoId={wizardProcessoId}
                />

                {/* Modal conferma annullamento processo */}
                <ConfirmModal
                    show={showAnnullaModal}
                    onConfirm={confirmAnnullaProcesso}
                    onCancel={() => setShowAnnullaModal(false)}
                    title="⚠️ Annulla Atto di Designazione"
                    confirmText="Sì, annulla tutto"
                    cancelText="No, mantieni"
                    confirmVariant="danger"
                >
                    <div className="alert alert-warning mb-0">
                        <p className="mb-2">
                            <strong>Vuoi davvero annullare l'atto di designazione?</strong>
                        </p>
                        <p className="mb-2">
                            Questa azione eliminerà:
                        </p>
                        <ul className="mb-2">
                            <li>Tutti i documenti PDF generati</li>
                            <li>Tutte le designazioni associate</li>
                        </ul>
                        <p className="mb-0">
                            Le sezioni torneranno disponibili per un nuovo atto.
                        </p>
                    </div>
                </ConfirmModal>

                {/* Modal conferma invio email */}
                <ConfirmModal
                    show={showEmailModal}
                    onConfirm={confirmInviaEmail}
                    onCancel={() => { setShowEmailModal(false); setEmailProcessoId(null); }}
                    title="Invio Email RDL"
                    confirmText="Invia Email"
                    confirmVariant="primary"
                >
                    <div>
                        <p>Sei sicuro di voler inviare le email a tutti gli RDL di questo processo?</p>
                        <p className="text-muted mb-0">
                            Questa operazione puo' richiedere alcuni minuti per comuni grandi.
                            Riceverai una notifica al completamento.
                        </p>
                    </div>
                </ConfirmModal>

                {/* Export XLSX Modal */}
                <ConfirmModal
                    show={showExportModal}
                    onConfirm={handleExportXlsx}
                    onCancel={() => setShowExportModal(false)}
                    title="Esporta Report XLSX"
                    confirmText={exporting ? 'Download...' : 'Scarica XLSX'}
                    confirmVariant="success"
                    confirmDisabled={exporting}
                >
                    <div>
                        <p style={{ marginBottom: '12px' }}><strong>Cosa vuoi esportare?</strong></p>
                        {selectedSezioni.size > 0 && (
                            <label style={{ display: 'block', marginBottom: '8px', cursor: 'pointer' }}>
                                <input
                                    type="radio"
                                    name="exportMode"
                                    checked={exportMode === 'selected'}
                                    onChange={() => setExportMode('selected')}
                                    style={{ marginRight: '8px' }}
                                />
                                Solo le {selectedSezioni.size} sezioni selezionate
                            </label>
                        )}
                        <label style={{ display: 'block', marginBottom: '16px', cursor: 'pointer' }}>
                            <input
                                type="radio"
                                name="exportMode"
                                checked={exportMode === 'all'}
                                onChange={() => setExportMode('all')}
                                style={{ marginRight: '8px' }}
                            />
                            Tutte le sezioni del comune di {data?.summary?.nome || 'questo comune'}
                        </label>

                        <hr style={{ margin: '12px 0' }} />

                        <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                            <input
                                type="checkbox"
                                checked={exportIncludiConfermati}
                                onChange={(e) => setExportIncludiConfermati(e.target.checked)}
                                style={{ marginRight: '8px' }}
                            />
                            Includi atti confermati
                        </label>
                        <p className="text-muted" style={{ fontSize: '0.8rem', marginTop: '4px', marginBottom: 0 }}>
                            Le righe mostreranno lo stato CONFERMATO o MAPPATO
                        </p>
                    </div>
                </ConfirmModal>

                {/* PDF Viewer Modal */}
                {pdfViewer && (
                    <PDFViewer
                        url={pdfViewer.url}
                        originalUrl={pdfViewer.originalUrl}
                        titolo={pdfViewer.titolo}
                        onClose={handleClosePdfViewer}
                    />
                )}
            </div>
        );
    }

    // Vista navigazione territoriale
    return (
        <div className="gd-container">
            {/* Page Header */}
            <div className="page-header designazioni">
                <div className="page-header-title">
                    <i className="fas fa-file-signature"></i>
                    Designazioni
                </div>
                <div className="page-header-subtitle">
                    Gestione designazioni formali RDL: fotografa mappatura, genera documenti ufficiali e conferma atti
                </div>
            </div>

            {/* Territorial Navigation Header */}
            <div className="gd-territory-header">
                <div>
                    <h4 className="gd-territory-title">
                        <i className={`fas ${getLevelIcon()}`}></i>
                        <span>{getLevelTitle()}</span>
                    </h4>
                    {data?.summary && (
                        <div className="gd-territory-subtitle">
                            {data.summary.tipo}: {data.summary.nome}
                        </div>
                    )}
                </div>
                {canGoBack && (
                    <button
                        className="btn btn-outline-secondary"
                        onClick={handleBack}
                        style={{minHeight: '44px'}}
                    >
                        <i className="fas fa-arrow-left me-2"></i>
                        <span>Indietro</span>
                    </button>
                )}
            </div>

            {/* Search */}
            {data?.items && data.items.length > 5 && (
                <div className="gd-territory-search">
                    <input
                        type="text"
                        className="form-control"
                        placeholder="Cerca..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                </div>
            )}

            {/* Items list */}
            {filteredItems.length === 0 ? (
                <div className="gd-empty-state">
                    <i className="fas fa-search gd-empty-icon"></i>
                    <div className="gd-empty-title">Nessun risultato</div>
                </div>
            ) : (
                filteredItems.map(item => (
                    <div
                        key={item.id}
                        className="gd-territory-card"
                        onClick={() => handleDrillDown(item)}
                    >
                        <div className="gd-territory-card-content">
                            <div className="gd-territory-card-name">
                                {item.nome}
                                {item.sigla && <span className="sigla">({item.sigla})</span>}
                            </div>
                            {item.totale_sezioni !== undefined && (
                                <div className="gd-territory-card-stats">
                                    {item.sezioni_assegnate} sezioni mappate
                                </div>
                            )}
                        </div>
                        <div className="gd-territory-card-badges">
                            {/* Badge per comuni */}
                            {item.tipo === 'comune' && item.mappature_nuove !== undefined && (
                                <>
                                    {item.mappature_nuove > 0 ? (
                                        <>
                                            <span className="badge bg-warning text-dark">
                                                <i className="fas fa-exclamation-circle me-1"></i>
                                                {item.mappature_nuove} da designare
                                            </span>
                                            {item.designazioni_confermate > 0 && (
                                                <span className="badge bg-success">
                                                    {item.designazioni_confermate} confermate
                                                </span>
                                            )}
                                        </>
                                    ) : (
                                        <span className="badge bg-success">
                                            <i className="fas fa-check me-1"></i>
                                            Tutto confermato
                                        </span>
                                    )}
                                </>
                            )}

                            {/* Progress bar per altri livelli */}
                            {item.tipo !== 'comune' && item.totale_sezioni !== undefined && (
                                <div className="gd-territory-progress">
                                    <div className="gd-territory-progress-text">
                                        <strong>{item.sezioni_assegnate}</strong>/{item.totale_sezioni} sezioni
                                    </div>
                                    <div className="gd-territory-progress-bar">
                                        <div
                                            className="gd-territory-progress-fill"
                                            style={{width: `${item.percentuale_assegnazione || 0}%`}}
                                        ></div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                ))
            )}

            {/* Modal conferma annullamento processo */}
            <ConfirmModal
                show={showAnnullaModal}
                onConfirm={confirmAnnullaProcesso}
                onCancel={() => setShowAnnullaModal(false)}
                title="⚠️ Annulla Processo"
                confirmText="Sì, annulla tutto"
                cancelText="No, mantieni"
                confirmVariant="danger"
            >
                <div className="alert alert-warning mb-0">
                    <p className="mb-2">
                        <strong>Vuoi davvero annullare l'atto di designazione?</strong>
                    </p>
                    <p className="mb-2">
                        Questa azione eliminerà:
                    </p>
                    <ul className="mb-2">
                        <li>Tutti i documenti PDF generati</li>
                        <li>Tutte le designazioni associate</li>
                    </ul>
                    <p className="mb-0">
                        Le sezioni torneranno disponibili per un nuovo atto.
                    </p>
                </div>
            </ConfirmModal>

            {/* Modal conferma invio email */}
            <ConfirmModal
                show={showEmailModal}
                onConfirm={confirmInviaEmail}
                onCancel={() => { setShowEmailModal(false); setEmailProcessoId(null); }}
                title="Invio Email RDL"
                confirmText="Invia Email"
                confirmVariant="primary"
            >
                <div>
                    <p>Sei sicuro di voler inviare le email a tutti gli RDL di questo processo?</p>
                    <div className="form-check mb-3">
                        <input
                            className="form-check-input"
                            type="checkbox"
                            id="allegaDesignazione"
                            checked={allegaDesignazione}
                            onChange={(e) => setAllegaDesignazione(e.target.checked)}
                        />
                        <label className="form-check-label" htmlFor="allegaDesignazione">
                            <i className="fas fa-paperclip me-1"></i>
                            Allega PDF designazione personalizzato
                        </label>
                        <div className="form-text">
                            Ogni RDL riceverà in allegato il PDF con le proprie sezioni e la nomina del delegato.
                        </div>
                    </div>
                    <p className="text-muted mb-0">
                        Questa operazione puo' richiedere alcuni minuti per comuni grandi.
                        Riceverai una notifica al completamento.
                    </p>
                </div>
            </ConfirmModal>

            {/* PDF Viewer Modal */}
            {pdfViewer && (
                <PDFViewer
                    url={pdfViewer.url}
                    originalUrl={pdfViewer.originalUrl}
                    titolo={pdfViewer.titolo}
                    onClose={handleClosePdfViewer}
                />
            )}
        </div>
    );
}

export default GestioneDesignazioni;
