// GestioneDesignazioni.js - Process-driven interface for formal RDL designations
import React, { useState, useEffect } from 'react';
import './GestioneDesignazioni.css';
import WizardDesignazioni from './components/designazioni/WizardDesignazioni';
import ConfirmModal from './ConfirmModal';
import PDFViewer from './PDFViewer';

/**
 * Workflow process-driven per designazioni formali RDL.
 *
 * Step 1: Seleziona sezioni mappate (checkbox)
 * Step 2: Avvia Processo → fotografa + genera 2 PDF automaticamente
 * Step 3: Controlla PDF
 * Step 4: Conferma Processo → tutto CONFERMATO oppure Annulla → tutto eliminato
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

    // Loading states
    const [loadingData, setLoadingData] = useState(false);
    const [avviandoProcesso, setAvviandoProcesso] = useState(false);

    // Messages
    const [successMessage, setSuccessMessage] = useState(null);

    // Wizard state
    const [showWizard, setShowWizard] = useState(false);

    // Confirm modal state
    const [showAnnullaModal, setShowAnnullaModal] = useState(false);

    // PDF Viewer state
    const [pdfViewer, setPdfViewer] = useState(null); // { url, titolo, blobUrl } quando aperto
    const [loadingPdf, setLoadingPdf] = useState(false);

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

            // 1. Load mappature (sezioni mappate)
            const mappaturaResult = await client.mappatura.sezioni({
                comune_id: comuneId,
                municipio_id: municipioId
            });

            if (!mappaturaResult.error && mappaturaResult.plessi) {
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
                console.log('[GestioneDesignazioni] Sezioni mappate totali:', allSezioni.length);

                // Filtra sezioni già in processi (BOZZA o CONFERMATA)
                // Carica designazioni per sapere quali sezioni sono già processate
                const designazioniResult = await client.deleghe.designazioni.list(consultazione.id);
                console.log('[GestioneDesignazioni] Designazioni result:', designazioniResult);

                if (!designazioniResult.error && designazioniResult.results) {
                    // Carica anche i batch per verificare lo stato dei processi
                    const batchTempResult = await client.deleghe.batch.list(consultazione.id);
                    const allBatch = batchTempResult.error ? [] : batchTempResult.results;

                    // Crea mappa batch_id -> stato per lookup veloce
                    const batchStati = {};
                    allBatch.forEach(b => {
                        batchStati[b.id] = b.stato;
                    });

                    // Sezioni DA ESCLUDERE: solo quelle in processi ATTIVI o COMPLETATI
                    // NON escludere sezioni in processi ERRORE, ANNULLATI o con batch mancanti
                    const designazioniProcessate = designazioniResult.results.filter(d => {
                        // SEMPRE escludi designazioni CONFERMATE (indipendentemente da processo/batch)
                        if (d.stato === 'CONFERMATA') {
                            return true; // Escludi sezioni confermate
                        }

                        // Per designazioni BOZZA: controlla se sono in processi attivi
                        if (!d.processo || !d.batch_pdf) {
                            // Designazione BOZZA orfana (processo eliminato) → sezione disponibile
                            return false;
                        }

                        const batchStato = batchStati[d.batch_pdf];

                        // Escludi BOZZE con batch in stato BOZZA o GENERATO (processo in corso)
                        if (d.stato === 'BOZZA' && ['BOZZA', 'GENERATO'].includes(batchStato)) {
                            return true; // Escludi sezioni in processi attivi
                        }

                        // Altrimenti sezione disponibile (BOZZE in batch ERRORE, APPROVATO senza conferma, etc.)
                        return false;
                    });

                    const sezioniProcessate = new Set(designazioniProcessate.map(d => d.sezione));
                    console.log('[GestioneDesignazioni] Sezioni già processate (escluse):', sezioniProcessate.size, Array.from(sezioniProcessate));

                    // Debug: mostra quali designazioni sono state filtrate e perché
                    const confermate = designazioniResult.results.filter(d => d.stato === 'CONFERMATA');
                    console.log('[GestioneDesignazioni] Designazioni CONFERMATE totali:', confermate.length, confermate.map(d => `Sezione ${d.sezione}: ${d.effettivo_cognome}`));

                    const bozzeAttive = designazioniResult.results.filter(d => {
                        return d.stato === 'BOZZA' && d.processo && d.batch_pdf && ['BOZZA', 'GENERATO'].includes(batchStati[d.batch_pdf]);
                    });
                    console.log('[GestioneDesignazioni] BOZZE in processi attivi:', bozzeAttive.length);

                    // Filtra sezioni disponibili (solo differenze - non ancora processate)
                    const sezioniDisponibili = allSezioni.filter(sez => !sezioniProcessate.has(sez.id));
                    console.log('[GestioneDesignazioni] Sezioni disponibili (differenze):', sezioniDisponibili.length);
                    setMappature(sezioniDisponibili);
                } else {
                    // Se errore caricando designazioni, mostra tutto
                    setMappature(allSezioni);
                }
            }

            // 2. Check processo in corso (batch con stato BOZZA o GENERATO)
            const batchResult = await client.deleghe.batch.list(consultazione.id);
            console.log('[GestioneDesignazioni] Batch result:', batchResult);

            if (!batchResult.error && batchResult.results) {
                console.log('[GestioneDesignazioni] Total batch found:', batchResult.results.length);

                const batchInCorso = batchResult.results.filter(b =>
                    ['BOZZA', 'GENERATO'].includes(b.stato)
                );
                console.log('[GestioneDesignazioni] Batch in corso:', batchInCorso.length, batchInCorso);

                if (batchInCorso.length > 0) {
                    // Raggruppa batch individuale + riepilogativo dello stesso processo
                    // I batch hanno un campo processo_id che indica a quale processo appartengono
                    const individuale = batchInCorso.find(b => b.tipo === 'INDIVIDUALE');
                    const riepilogativo = batchInCorso.find(b => b.tipo === 'RIEPILOGATIVO');

                    console.log('[GestioneDesignazioni] Individuale:', individuale);
                    console.log('[GestioneDesignazioni] Riepilogativo:', riepilogativo);

                    if (individuale && riepilogativo) {
                        // Usa il processo_id dal batch (dovrebbero avere lo stesso)
                        const processoId = individuale.processo_id || riepilogativo.processo_id;

                        const processo = {
                            id: processoId,  // IMPORTANTE: Aggiungi processo_id
                            batch_individuale: individuale,
                            batch_riepilogativo: riepilogativo,
                            created_at: individuale.created_at
                        };
                        console.log('[GestioneDesignazioni] Setting processo in corso:', processo);
                        setProcessoInCorso(processo);
                    } else if (individuale || riepilogativo) {
                        console.warn('[GestioneDesignazioni] Batch incompleto - manca uno dei due tipi!');
                        const batch = individuale || riepilogativo;
                        const processoId = batch.processo_id;

                        // Mostra comunque quello che c'è
                        setProcessoInCorso({
                            id: processoId,  // IMPORTANTE: Aggiungi processo_id
                            batch_individuale: individuale || null,
                            batch_riepilogativo: riepilogativo || null,
                            created_at: batch.created_at
                        });
                    }
                }

                // OLD: Processi completati (APPROVATO, INVIATO) - sostituito con archivio
            }

            // 3. Carica archivio processi completati (APPROVATO)
            const archivioResult = await client.deleghe.processi.archivio(consultazione.id, comuneId, 'completati');
            console.log('[GestioneDesignazioni] Archivio result:', archivioResult);

            if (!archivioResult.error && Array.isArray(archivioResult)) {
                console.log('[GestioneDesignazioni] Processi archiviati:', archivioResult.length);
                archivioResult.forEach(p => {
                    console.log('[GestioneDesignazioni] Processo archivio:', {
                        id: p.id,
                        documento_individuale_url: p.documento_individuale_url,
                        documento_cumulativo_url: p.documento_cumulativo_url
                    });
                });
                setProcessiArchivio(archivioResult);
            }

            // 4. Carica storico processi (ANNULLATO, etc.) per audit
            const storicoResult = await client.deleghe.processi.archivio(consultazione.id, comuneId, 'storico');
            console.log('[GestioneDesignazioni] Storico result:', storicoResult);

            if (!storicoResult.error && Array.isArray(storicoResult)) {
                console.log('[GestioneDesignazioni] Processi storici:', storicoResult.length);
                setProcessiStorico(storicoResult);
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
            setError?.('Seleziona almeno una sezione per avviare il processo');
            return;
        }

        console.log('[GestioneDesignazioni] Apertura wizard per', selectedSezioni.size, 'sezioni');
        console.log('[GestioneDesignazioni] Chiamata setShowWizard(true)');
        setShowWizard(true);
        console.log('[GestioneDesignazioni] showWizard dopo:', showWizard);
    };

    const handleWizardSuccess = () => {
        console.log('[GestioneDesignazioni] Wizard completato con successo');
        setSuccessMessage('✓ Processo di designazione completato con successo!');
        setSelectedSezioni(new Set());
        loadComuneData(path.comune_id, path.municipio_id);
    };

    const handleConfermaProcesso = async () => {
        if (!processoInCorso) return;

        try {
            console.log('[GestioneDesignazioni] Conferma processo');

            // Approva entrambi i batch
            const approve1 = await client.deleghe.batch.approva(processoInCorso.batch_individuale.id);
            if (approve1.error) {
                throw new Error('Errore approvazione batch INDIVIDUALE: ' + approve1.error);
            }

            const approve2 = await client.deleghe.batch.approva(processoInCorso.batch_riepilogativo.id);
            if (approve2.error) {
                throw new Error('Errore approvazione batch RIEPILOGATIVO: ' + approve2.error);
            }

            setSuccessMessage(
                `✓ Processo confermato con successo!\n` +
                `Tutte le designazioni sono ora CONFERMATE`
            );

            await loadComuneData(path.comune_id, path.municipio_id);

        } catch (err) {
            console.error('[GestioneDesignazioni] Error conferma processo:', err);
            setError?.('Errore conferma processo: ' + err.message);
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

            // Raccogli gli ID unici dei batch da eliminare
            const batchIds = new Set();
            if (processoInCorso.batch_individuale) {
                batchIds.add(processoInCorso.batch_individuale.id);
            }
            if (processoInCorso.batch_riepilogativo) {
                batchIds.add(processoInCorso.batch_riepilogativo.id);
            }

            // Elimina ogni batch unico
            for (const batchId of batchIds) {
                console.log('[GestioneDesignazioni] Eliminazione batch #', batchId);
                const result = await client.deleghe.batch.delete(batchId);

                if (result.error && !result.deleted) {
                    throw new Error('Errore eliminazione batch #' + batchId + ': ' + result.error);
                }

                console.log('[GestioneDesignazioni] ✓ Batch #', batchId, 'eliminato');
            }

            setSuccessMessage('✓ Processo annullato con successo! Le sezioni sono di nuovo disponibili.');
            setProcessoInCorso(null);
            await loadComuneData(path.comune_id, path.municipio_id);

        } catch (err) {
            console.error('[GestioneDesignazioni] Error annulla processo:', err);
            setError?.('Errore annullamento processo: ' + err.message);
        }
    };

    const handlePreviewIndividuale = async (processoId) => {
        if (!processoId) {
            console.error('[GestioneDesignazioni] Processo ID mancante');
            setError?.('Impossibile visualizzare: processo non trovato');
            return;
        }

        setLoadingPdf(true);
        try {
            console.log('[GestioneDesignazioni] Caricamento PDF individuale, processo:', processoId);

            // Usa il metodo preview che restituisce blob URL con autenticazione
            const blobUrl = await client.deleghe.processi.previewIndividuale(processoId);

            console.log('[GestioneDesignazioni] Blob URL ottenuto:', blobUrl);

            // URL originale per apertura in nuova scheda (questo farà il download)
            const serverUrl = client.server || process.env.REACT_APP_API_URL || window.location.origin.replace(':3000', ':3001');
            const originalUrl = `${serverUrl}/api/deleghe/processi/${processoId}/download_individuale/`;

            const viewerData = {
                url: blobUrl,  // Blob URL per il viewer
                originalUrl,   // URL originale per download
                blobUrl,       // Mantieni riferimento per revoke
                titolo: `Designazioni Individuali - Processo #${processoId}`
            };

            console.log('[GestioneDesignazioni] Apertura PDFViewer con:', viewerData);
            setPdfViewer(viewerData);
        } catch (err) {
            console.error('[GestioneDesignazioni] Errore caricamento PDF:', err);
            setError?.('Errore caricamento PDF: ' + err.message);
        } finally {
            setLoadingPdf(false);
        }
    };

    const handlePreviewCumulativo = async (processoId) => {
        if (!processoId) {
            console.error('[GestioneDesignazioni] Processo ID mancante');
            setError?.('Impossibile visualizzare: processo non trovato');
            return;
        }

        setLoadingPdf(true);
        try {
            console.log('[GestioneDesignazioni] Caricamento PDF cumulativo, processo:', processoId);

            // Usa il metodo preview che restituisce blob URL con autenticazione
            const blobUrl = await client.deleghe.processi.previewCumulativo(processoId);

            console.log('[GestioneDesignazioni] Blob URL ottenuto:', blobUrl);

            // URL originale per apertura in nuova scheda
            const serverUrl = client.server || process.env.REACT_APP_API_URL || window.location.origin.replace(':3000', ':3001');
            const originalUrl = `${serverUrl}/api/deleghe/processi/${processoId}/download_cumulativo/`;

            setPdfViewer({
                url: blobUrl,
                originalUrl,
                blobUrl,
                titolo: `Designazioni Cumulative - Processo #${processoId}`
            });
        } catch (err) {
            console.error('[GestioneDesignazioni] Errore caricamento PDF:', err);
            setError?.('Errore caricamento PDF: ' + err.message);
        } finally {
            setLoadingPdf(false);
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
        if (!searchQuery) return true;
        return item.nome.toLowerCase().includes(searchQuery.toLowerCase());
    }) || [];

    const styles = {
        card: {
            backgroundColor: '#fff',
            borderRadius: '12px',
            padding: '16px',
            marginBottom: '12px',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
            cursor: 'pointer',
            transition: 'transform 0.2s, box-shadow 0.2s'
        },
        cardHeader: {
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '12px'
        }
    };

    if (loading) {
        return (
            <div className="container mt-4">
                <div className="text-center p-5">
                    <div className="spinner-border text-primary mb-3"></div>
                    <p>Caricamento...</p>
                </div>
            </div>
        );
    }

    // Vista Comune: Tab Mappature + Processo in Corso
    if (path.comune_id) {
        console.log('[GestioneDesignazioni] Render vista comune, showWizard:', showWizard);
        return (
            <div className="container-fluid mt-4">
                <div className="row">
                    <div className="col-12">
                        {/* Breadcrumb */}
                        <nav aria-label="breadcrumb">
                            <ol className="breadcrumb">
                                <li className="breadcrumb-item">
                                    <a href="#" onClick={(e) => { e.preventDefault(); handleBack(); }}>
                                        <i className="fas fa-arrow-left me-2"></i>
                                        Indietro
                                    </a>
                                </li>
                                <li className="breadcrumb-item active">
                                    {data?.summary?.nome || 'Comune'}
                                </li>
                            </ol>
                        </nav>

                        {/* Success message */}
                        {successMessage && (
                            <div className="alert alert-success alert-dismissible fade show" role="alert">
                                <i className="fas fa-check-circle me-2"></i>
                                <pre className="mb-0" style={{whiteSpace: 'pre-wrap'}}>{successMessage}</pre>
                                <button
                                    type="button"
                                    className="btn-close"
                                    onClick={() => setSuccessMessage(null)}
                                ></button>
                            </div>
                        )}

                        {/* PROCESSO IN CORSO */}
                        {processoInCorso && (
                            <div className="card border-primary mb-4">
                                <div className="card-header bg-primary text-white">
                                    <h5 className="mb-0">
                                        <i className="fas fa-cog fa-spin me-2"></i>
                                        Processo di Designazione in Corso
                                    </h5>
                                </div>
                                <div className="card-body">
                                    <div className="alert alert-info mb-3">
                                        <i className="fas fa-info-circle me-2"></i>
                                        <strong>Controlla i documenti generati</strong>
                                        <p className="mb-0 mt-2 small">
                                            Verifica che i PDF siano corretti, poi conferma il processo per rendere definitive le designazioni.
                                            Se trovi errori, puoi annullare il processo e riavviarne uno nuovo.
                                        </p>
                                    </div>

                                    {/* Documento INDIVIDUALE */}
                                    {processoInCorso.batch_individuale && (
                                        <div className="mb-3 p-3 border rounded">
                                            <div className="d-flex justify-content-between align-items-center">
                                                <div>
                                                    <h6 className="mb-1">
                                                        <i className="fas fa-file-pdf me-2 text-danger"></i>
                                                        Documento INDIVIDUALE
                                                    </h6>
                                                    <small className="text-muted">
                                                        Un PDF per ogni sezione • Batch #{processoInCorso.batch_individuale.id}
                                                    </small>
                                                    <div className="mt-1">
                                                        <span className={`badge ${processoInCorso.batch_individuale.stato === 'GENERATO' ? 'bg-success' : 'bg-warning'}`}>
                                                            {processoInCorso.batch_individuale.stato}
                                                        </span>
                                                    </div>
                                                </div>
                                                <div>
                                                    {processoInCorso.batch_individuale.stato === 'GENERATO' && (
                                                        <button
                                                            className="btn btn-primary btn-sm"
                                                            onClick={() => handlePreviewIndividuale(processoInCorso.id)}
                                                        >
                                                            <i className="fas fa-eye me-1"></i>
                                                            Visualizza PDF
                                                        </button>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    {/* Documento RIEPILOGATIVO */}
                                    {processoInCorso.batch_riepilogativo && (
                                        <div className="mb-3 p-3 border rounded">
                                            <div className="d-flex justify-content-between align-items-center">
                                                <div>
                                                    <h6 className="mb-1">
                                                        <i className="fas fa-file-pdf me-2 text-danger"></i>
                                                        Documento RIEPILOGATIVO
                                                    </h6>
                                                    <small className="text-muted">
                                                        Un PDF cumulativo • Batch #{processoInCorso.batch_riepilogativo.id}
                                                    </small>
                                                    <div className="mt-1">
                                                        <span className={`badge ${processoInCorso.batch_riepilogativo.stato === 'GENERATO' ? 'bg-success' : 'bg-warning'}`}>
                                                            {processoInCorso.batch_riepilogativo.stato}
                                                        </span>
                                                    </div>
                                                </div>
                                                <div>
                                                    {processoInCorso.batch_riepilogativo.stato === 'GENERATO' && (
                                                        <button
                                                            className="btn btn-primary btn-sm"
                                                            onClick={() => handlePreviewCumulativo(processoInCorso.id)}
                                                        >
                                                            <i className="fas fa-eye me-1"></i>
                                                            Visualizza PDF
                                                        </button>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    {/* Azioni finali */}
                                    <div className="d-flex gap-2 justify-content-end">
                                        <button
                                            className="btn btn-outline-danger"
                                            onClick={handleAnnullaProcesso}
                                        >
                                            <i className="fas fa-times me-1"></i>
                                            Annulla Processo
                                        </button>
                                        <button
                                            className="btn btn-success"
                                            onClick={handleConfermaProcesso}
                                            disabled={
                                                !processoInCorso.batch_individuale ||
                                                !processoInCorso.batch_riepilogativo ||
                                                processoInCorso.batch_individuale.stato !== 'GENERATO' ||
                                                processoInCorso.batch_riepilogativo.stato !== 'GENERATO'
                                            }
                                        >
                                            <i className="fas fa-check me-1"></i>
                                            Conferma Processo
                                        </button>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* SEZIONI MAPPATE */}
                        <div className="card">
                            <div style={styles.cardHeader}>
                                <h6 className="mb-0">
                                    <i className="fas fa-map-marked-alt me-2"></i>
                                    Sezioni Mappate ({mappature.length})
                                </h6>
                                {console.log('[GestioneDesignazioni] Rendering pulsante Avvia, processoInCorso:', processoInCorso, 'mappature.length:', mappature.length)}
                                {!processoInCorso && mappature.length > 0 && (
                                    <button
                                        className="btn btn-primary btn-sm"
                                        onClick={(e) => {
                                            console.log('[GestioneDesignazioni] Click sul pulsante Avvia Processo!');
                                            handleAvviaProcesso();
                                        }}
                                        disabled={selectedSezioni.size === 0 || avviandoProcesso}
                                    >
                                        {avviandoProcesso ? (
                                            <>
                                                <span className="spinner-border spinner-border-sm me-2"></span>
                                                Avvio processo...
                                            </>
                                        ) : (
                                            <>
                                                <i className="fas fa-play me-2"></i>
                                                Avvia Processo ({selectedSezioni.size})
                                            </>
                                        )}
                                    </button>
                                )}
                            </div>

                            {processoInCorso && (
                                <div className="alert alert-warning mb-0">
                                    <i className="fas fa-exclamation-triangle me-2"></i>
                                    <strong>Processo in corso</strong> - Completa o annulla il processo attivo prima di avviarne uno nuovo.
                                </div>
                            )}

                            {!processoInCorso && mappature.length === 0 && (
                                <div className="text-center p-4 text-muted">
                                    <i className="fas fa-inbox fa-3x mb-3 d-block"></i>
                                    <p className="mb-0">Nessuna sezione mappata in questo comune</p>
                                    <p className="small mt-2">
                                        Vai su "Mappatura" per assegnare RDL alle sezioni
                                    </p>
                                </div>
                            )}

                            {!processoInCorso && mappature.length > 0 && (
                                <>
                                    <div className="mb-3 p-2 bg-light rounded d-flex align-items-center gap-3">
                                        <label className="mb-0">
                                            <input
                                                type="checkbox"
                                                className="form-check-input me-2"
                                                checked={selectedSezioni.size === mappature.length}
                                                onChange={handleToggleAll}
                                            />
                                            Seleziona tutte
                                        </label>
                                        <span className="text-muted small">
                                            {selectedSezioni.size} di {mappature.length} selezionate
                                        </span>
                                    </div>

                                    {mappature.map(sez => (
                                        <div key={sez.id} className="d-flex align-items-center gap-2 py-1 px-2 border-bottom" style={{fontSize: '0.85rem'}}>
                                            <input
                                                type="checkbox"
                                                className="form-check-input"
                                                checked={selectedSezioni.has(sez.id)}
                                                onChange={() => handleToggleSezione(sez.id)}
                                            />
                                            <strong style={{minWidth: '60px'}}>Sez. {sez.sezione_numero}</strong>
                                            {sez.rdl_effettivo && (
                                                <span className="text-primary">
                                                    <strong>Eff:</strong> {sez.rdl_effettivo.cognome} {sez.rdl_effettivo.nome}
                                                </span>
                                            )}
                                            {sez.rdl_supplente && (
                                                <span className="text-secondary ms-2">
                                                    | <strong>Sup:</strong> {sez.rdl_supplente.cognome} {sez.rdl_supplente.nome}
                                                </span>
                                            )}
                                        </div>
                                    ))}
                                </>
                            )}
                        </div>

                        {/* ARCHIVIO PROCESSI COMPLETATI */}
                        {processiArchivio.length > 0 && (
                            <div className="card mt-4">
                                <div style={styles.cardHeader}>
                                    <h6 className="mb-0">
                                        <i className="fas fa-check-circle me-2 text-success"></i>
                                        Archivio Processi Completati ({processiArchivio.length})
                                    </h6>
                                </div>
                                <div className="card-body">
                                    {processiArchivio.map(processo => (
                                        <div key={processo.id} className="mb-3 border rounded">
                                            <div
                                                className="d-flex justify-content-between align-items-center p-3"
                                                style={{cursor: 'pointer', backgroundColor: '#f8f9fa'}}
                                                onClick={() => handleToggleProcesso(processo.id)}
                                            >
                                                <div className="d-flex align-items-center gap-2 flex-grow-1">
                                                    <i className={`fas fa-chevron-${expandedProcessi.has(processo.id) ? 'down' : 'right'}`}></i>
                                                    <div className="flex-grow-1">
                                                        <div>
                                                            <strong>Processo #{processo.id}</strong>
                                                            {processo.delegato && (
                                                                <span className="ms-2 text-primary">
                                                                    <i className="fas fa-user me-1"></i>
                                                                    {processo.delegato.nome_completo} ({processo.delegato.tipo})
                                                                </span>
                                                            )}
                                                        </div>
                                                        <small className="text-muted">
                                                            {processo.n_designazioni} sezioni • Completato {new Date(processo.approvata_at).toLocaleDateString()}
                                                        </small>
                                                    </div>
                                                </div>
                                                <span className="badge bg-success">APPROVATO</span>
                                            </div>

                                            {expandedProcessi.has(processo.id) && (
                                                <div className="p-3 border-top">
                                                    {/* Documenti PDF */}
                                                    <div className="mb-3">
                                                        <h6 className="small text-uppercase text-muted mb-2">Documenti</h6>
                                                        <div className="d-flex gap-2">
                                                            {processo.documento_individuale_url && (
                                                                <button
                                                                    onClick={(e) => {
                                                                        console.log('[Archivio] Click PDF Individuale, processo.id:', processo.id);
                                                                        e.stopPropagation();
                                                                        e.preventDefault();
                                                                        handlePreviewIndividuale(processo.id);
                                                                    }}
                                                                    className="btn btn-sm btn-outline-primary"
                                                                    type="button"
                                                                >
                                                                    <i className="fas fa-eye me-1"></i>
                                                                    PDF Individuale
                                                                </button>
                                                            )}
                                                            {processo.documento_cumulativo_url && (
                                                                <button
                                                                    onClick={(e) => {
                                                                        console.log('[Archivio] Click PDF Cumulativo, processo.id:', processo.id);
                                                                        e.stopPropagation();
                                                                        e.preventDefault();
                                                                        handlePreviewCumulativo(processo.id);
                                                                    }}
                                                                    className="btn btn-sm btn-outline-primary"
                                                                    type="button"
                                                                >
                                                                    <i className="fas fa-eye me-1"></i>
                                                                    PDF Cumulativo
                                                                </button>
                                                            )}
                                                        </div>
                                                    </div>

                                                    {/* Lista Sezioni */}
                                                    <div>
                                                        <h6 className="small text-uppercase text-muted mb-2">Sezioni ({processo.sezioni.length})</h6>
                                                        <div style={{maxHeight: '300px', overflowY: 'auto', fontSize: '0.85rem'}}>
                                                            {processo.sezioni.map(sez => (
                                                                <div key={sez.id} className="mb-1 p-1 bg-light">
                                                                    <strong style={{display: 'inline-block', minWidth: '65px'}}>Sez. {sez.numero}</strong>
                                                                    <span className="text-primary">
                                                                        <strong>Eff:</strong> {sez.effettivo_cognome} {sez.effettivo_nome}
                                                                        {sez.effettivo_data_nascita && <>, {sez.effettivo_data_nascita}</>}
                                                                        {sez.effettivo_luogo_nascita && <>, {sez.effettivo_luogo_nascita}</>}
                                                                        {sez.effettivo_domicilio && <> - {sez.effettivo_domicilio}</>}
                                                                    </span>
                                                                    {sez.supplente_cognome && (
                                                                        <span className="text-secondary ms-2">
                                                                            | <strong>Sup:</strong> {sez.supplente_cognome} {sez.supplente_nome}
                                                                            {sez.supplente_data_nascita && <>, {sez.supplente_data_nascita}</>}
                                                                            {sez.supplente_luogo_nascita && <>, {sez.supplente_luogo_nascita}</>}
                                                                            {sez.supplente_domicilio && <> - {sez.supplente_domicilio}</>}
                                                                        </span>
                                                                    )}
                                                                </div>
                                                            ))}
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
                            <div className="card mt-4">
                                <div style={styles.cardHeader}>
                                    <h6 className="mb-0">
                                        <i className="fas fa-history me-2 text-muted"></i>
                                        Archivio Storico ({processiStorico.length})
                                    </h6>
                                    <small className="text-muted">Processi non completati o annullati (audit)</small>
                                </div>
                                <div className="card-body">
                                    {processiStorico.map(processo => (
                                        <div key={processo.id} className="mb-3 border rounded">
                                            <div
                                                className="d-flex justify-content-between align-items-center p-3"
                                                style={{cursor: 'pointer', backgroundColor: '#f8f9fa'}}
                                                onClick={() => handleToggleProcesso(processo.id)}
                                            >
                                                <div className="d-flex align-items-center gap-2 flex-grow-1">
                                                    <i className={`fas fa-chevron-${expandedProcessi.has(processo.id) ? 'down' : 'right'}`}></i>
                                                    <div className="flex-grow-1">
                                                        <div>
                                                            <strong>Processo #{processo.id}</strong>
                                                            {processo.delegato && (
                                                                <span className="ms-2 text-primary">
                                                                    <i className="fas fa-user me-1"></i>
                                                                    {processo.delegato.nome_completo} ({processo.delegato.tipo})
                                                                </span>
                                                            )}
                                                        </div>
                                                        <small className="text-muted">
                                                            {processo.n_designazioni} sezioni • Creato {new Date(processo.created_at).toLocaleDateString()}
                                                        </small>
                                                    </div>
                                                </div>
                                                <span className={`badge ${processo.stato === 'ANNULLATO' ? 'bg-danger' : 'bg-secondary'}`}>
                                                    {processo.stato}
                                                </span>
                                            </div>

                                            {expandedProcessi.has(processo.id) && (
                                                <div className="p-3 border-top">
                                                    {/* Informazioni processo */}
                                                    <div className="mb-3">
                                                        <div className="small text-muted">
                                                            Creato da: {processo.created_by_email} • {new Date(processo.created_at).toLocaleString()}
                                                        </div>
                                                    </div>

                                                    {/* Lista Sezioni */}
                                                    <div>
                                                        <h6 className="small text-uppercase text-muted mb-2">Sezioni ({processo.sezioni.length})</h6>
                                                        <div style={{maxHeight: '300px', overflowY: 'auto', fontSize: '0.85rem'}}>
                                                            {processo.sezioni.map(sez => (
                                                                <div key={sez.id} className="mb-1 p-1 bg-light">
                                                                    <strong style={{display: 'inline-block', minWidth: '65px'}}>Sez. {sez.numero}</strong>
                                                                    <span className="text-primary">
                                                                        <strong>Eff:</strong> {sez.effettivo_cognome} {sez.effettivo_nome}
                                                                        {sez.effettivo_data_nascita && <>, {sez.effettivo_data_nascita}</>}
                                                                        {sez.effettivo_luogo_nascita && <>, {sez.effettivo_luogo_nascita}</>}
                                                                        {sez.effettivo_domicilio && <> - {sez.effettivo_domicilio}</>}
                                                                    </span>
                                                                    {sez.supplente_cognome && (
                                                                        <span className="text-secondary ms-2">
                                                                            | <strong>Sup:</strong> {sez.supplente_cognome} {sez.supplente_nome}
                                                                            {sez.supplente_data_nascita && <>, {sez.supplente_data_nascita}</>}
                                                                            {sez.supplente_luogo_nascita && <>, {sez.supplente_luogo_nascita}</>}
                                                                            {sez.supplente_domicilio && <> - {sez.supplente_domicilio}</>}
                                                                        </span>
                                                                    )}
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Wizard multi-step */}
                {console.log('[GestioneDesignazioni] Prima di WizardDesignazioni, showWizard:', showWizard)}
                <WizardDesignazioni
                    show={showWizard}
                    onClose={() => setShowWizard(false)}
                    client={client}
                    consultazione={consultazione}
                    sezioniSelezionate={selectedSezioni}
                    onSuccess={handleWizardSuccess}
                />

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
                            <strong>Vuoi davvero annullare il processo?</strong>
                        </p>
                        <p className="mb-2">
                            Questa azione eliminerà:
                        </p>
                        <ul className="mb-2">
                            <li>Tutti i documenti PDF generati</li>
                            <li>Tutte le designazioni associate</li>
                        </ul>
                        <p className="mb-0">
                            Le sezioni torneranno disponibili per un nuovo processo.
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
        <div className="container-fluid mt-4">
            <div className="row">
                <div className="col-12">
                    {/* Header */}
                    <div className="d-flex justify-content-between align-items-center mb-4">
                        <div>
                            <h4>
                                <i className={`fas ${getLevelIcon()} me-2`}></i>
                                {getLevelTitle()}
                            </h4>
                            {data?.summary && (
                                <small className="text-muted">
                                    {data.summary.tipo}: {data.summary.nome}
                                </small>
                            )}
                        </div>
                        {canGoBack && (
                            <button className="btn btn-outline-secondary" onClick={handleBack}>
                                <i className="fas fa-arrow-left me-2"></i>
                                Indietro
                            </button>
                        )}
                    </div>

                    {/* Search */}
                    {data?.items && data.items.length > 5 && (
                        <div className="mb-3">
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
                        <div className="text-center p-4 text-muted">
                            <i className="fas fa-search fa-3x mb-3 d-block"></i>
                            <p>Nessun risultato</p>
                        </div>
                    ) : (
                        filteredItems.map(item => (
                            <div
                                key={item.id}
                                style={styles.card}
                                onClick={() => handleDrillDown(item)}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.transform = 'translateY(-2px)';
                                    e.currentTarget.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.15)';
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.transform = 'translateY(0)';
                                    e.currentTarget.style.boxShadow = '0 1px 3px rgba(0, 0, 0, 0.1)';
                                }}
                            >
                                <div className="d-flex justify-content-between align-items-start">
                                    <div>
                                        <h6 className="mb-1">
                                            {item.nome}
                                            {item.sigla && <span className="text-muted small ms-2">({item.sigla})</span>}
                                        </h6>
                                        {item.totale_sezioni !== undefined && (
                                            <div className="small text-muted">
                                                {item.sezioni_assegnate} sezioni mappate
                                            </div>
                                        )}
                                    </div>
                                    <div className="text-end">
                                        {/* Badge per comuni */}
                                        {item.tipo === 'comune' && item.mappature_nuove !== undefined && (
                                            <div className="d-flex flex-column gap-1 align-items-end">
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
                                            </div>
                                        )}

                                        {/* Progress bar per altri livelli */}
                                        {item.tipo !== 'comune' && item.totale_sezioni !== undefined && (
                                            <div className="small">
                                                <strong>{item.sezioni_assegnate}</strong>/{item.totale_sezioni} sezioni
                                                <div className="progress mt-1" style={{width: '100px', height: '6px'}}>
                                                    <div
                                                        className="progress-bar bg-success"
                                                        style={{width: `${item.percentuale_assegnazione || 0}%`}}
                                                    ></div>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

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
                        <strong>Vuoi davvero annullare il processo?</strong>
                    </p>
                    <p className="mb-2">
                        Questa azione eliminerà:
                    </p>
                    <ul className="mb-2">
                        <li>Tutti i documenti PDF generati</li>
                        <li>Tutte le designazioni associate</li>
                    </ul>
                    <p className="mb-0">
                        Le sezioni torneranno disponibili per un nuovo processo.
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
