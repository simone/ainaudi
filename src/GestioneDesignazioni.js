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
            setError?.('Seleziona almeno una sezione per avviare l\'atto di designazione');
            return;
        }

        console.log('[GestioneDesignazioni] Apertura wizard per', selectedSezioni.size, 'sezioni');
        console.log('[GestioneDesignazioni] Chiamata setShowWizard(true)');
        setShowWizard(true);
        console.log('[GestioneDesignazioni] showWizard dopo:', showWizard);
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

            setSuccessMessage('✓ Atto di designazione annullato con successo! Le sezioni sono di nuovo disponibili.');
            setProcessoInCorso(null);
            await loadComuneData(path.comune_id, path.municipio_id);

        } catch (err) {
            console.error('[GestioneDesignazioni] Error annulla processo:', err);
            setError?.('Errore annullamento atto: ' + err.message);
        }
    };

    const handlePreviewIndividuale = async (processoId) => {
        if (!processoId) {
            console.error('[GestioneDesignazioni] Processo ID mancante');
            setError?.('Impossibile visualizzare: atto non trovato');
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
            setError?.('Impossibile visualizzare: atto non trovato');
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
                {/* Breadcrumb */}
                <nav aria-label="breadcrumb" className="gd-breadcrumb">
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
                            {processoInCorso.batch_individuale && (
                                <div className="gd-pdf-document">
                                    <div className="gd-pdf-document-header">
                                        <div className="gd-pdf-document-info">
                                            <div className="gd-pdf-document-title">
                                                <i className="fas fa-file-pdf text-danger"></i>
                                                <span>Documento INDIVIDUALE</span>
                                            </div>
                                            <span className="gd-pdf-document-subtitle">
                                                Un PDF per ogni sezione • Batch #{processoInCorso.batch_individuale.id}
                                            </span>
                                            <span className={`badge ${processoInCorso.batch_individuale.stato === 'GENERATO' ? 'bg-success' : 'bg-warning'}`}>
                                                {processoInCorso.batch_individuale.stato}
                                            </span>
                                        </div>
                                        <div className="gd-pdf-document-actions">
                                            {processoInCorso.batch_individuale.stato === 'GENERATO' && (
                                                <button
                                                    className="btn btn-primary gd-btn-preview"
                                                    onClick={() => handlePreviewIndividuale(processoInCorso.id)}
                                                >
                                                    <i className="fas fa-eye"></i>
                                                    <span>Visualizza PDF</span>
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Documento RIEPILOGATIVO */}
                            {processoInCorso.batch_riepilogativo && (
                                <div className="gd-pdf-document">
                                    <div className="gd-pdf-document-header">
                                        <div className="gd-pdf-document-info">
                                            <div className="gd-pdf-document-title">
                                                <i className="fas fa-file-pdf text-danger"></i>
                                                <span>Documento RIEPILOGATIVO</span>
                                            </div>
                                            <span className="gd-pdf-document-subtitle">
                                                Un PDF cumulativo • Batch #{processoInCorso.batch_riepilogativo.id}
                                            </span>
                                            <span className={`badge ${processoInCorso.batch_riepilogativo.stato === 'GENERATO' ? 'bg-success' : 'bg-warning'}`}>
                                                {processoInCorso.batch_riepilogativo.stato}
                                            </span>
                                        </div>
                                        <div className="gd-pdf-document-actions">
                                            {processoInCorso.batch_riepilogativo.stato === 'GENERATO' && (
                                                <button
                                                    className="btn btn-primary gd-btn-preview"
                                                    onClick={() => handlePreviewCumulativo(processoInCorso.id)}
                                                >
                                                    <i className="fas fa-eye"></i>
                                                    <span>Visualizza PDF</span>
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )}

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
                                                                handlePreviewIndividuale(processo.id);
                                                            }}
                                                            className="btn btn-outline-primary"
                                                            type="button"
                                                        >
                                                            <i className="fas fa-eye me-1"></i>
                                                            <span>PDF Individuale</span>
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
                                                            className="btn btn-outline-primary"
                                                            type="button"
                                                        >
                                                            <i className="fas fa-eye me-1"></i>
                                                            <span>PDF Cumulativo</span>
                                                        </button>
                                                    )}
                                                </div>
                                            </div>

                                            {/* Lista Sezioni */}
                                            <div className="gd-archivio-section">
                                                <h6 className="gd-archivio-section-title">Sezioni ({processo.sezioni.length})</h6>
                                                <div className="gd-sezioni-archive-list">
                                                    {processo.sezioni.map(sez => (
                                                        <div key={sez.id} className="gd-sezione-item">
                                                            <div className="gd-sezione-content">
                                                                <div className="gd-sezione-numero">Sez. {sez.numero}</div>
                                                                <div className="gd-sezione-rdl">
                                                                    <div className="gd-rdl-effettivo">
                                                                        <span className="gd-rdl-label">Eff:</span> {sez.effettivo_cognome} {sez.effettivo_nome}
                                                                    </div>
                                                                    {sez.supplente_cognome && (
                                                                        <div className="gd-rdl-supplente">
                                                                            <span className="gd-rdl-label">Sup:</span> {sez.supplente_cognome} {sez.supplente_nome}
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            </div>
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

                                            {/* Lista Sezioni */}
                                            <div className="gd-archivio-section">
                                                <h6 className="gd-archivio-section-title">Sezioni ({processo.sezioni.length})</h6>
                                                <div className="gd-sezioni-archive-list">
                                                    {processo.sezioni.map(sez => (
                                                        <div key={sez.id} className="gd-sezione-item">
                                                            <div className="gd-sezione-content">
                                                                <div className="gd-sezione-numero">Sez. {sez.numero}</div>
                                                                <div className="gd-sezione-rdl">
                                                                    <div className="gd-rdl-effettivo">
                                                                        <span className="gd-rdl-label">Eff:</span> {sez.effettivo_cognome} {sez.effettivo_nome}
                                                                    </div>
                                                                    {sez.supplente_cognome && (
                                                                        <div className="gd-rdl-supplente">
                                                                            <span className="gd-rdl-label">Sup:</span> {sez.supplente_cognome} {sez.supplente_nome}
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            </div>
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
            {/* Header */}
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
