// WizardDesignazioni.js - Multi-step wizard for designation process
import React, { useState, useEffect } from 'react';
import './WizardDesignazioni.css';
import PDFViewer from '../components/PDFViewer';
import ConfirmModal from '../components/ConfirmModal';

/**
 * Wizard multi-step per processo designazione con template.
 *
 * Steps:
 * 1. Selezione Delegato/SubDelegato (pre-selezionato utente loggato, modificabile)
 * 2. Selezione Template (individuale + cumulativo)
 * 3. Form dinamica dati delegato
 * 4. Generazione PDF Individuale
 * 5. Generazione PDF Cumulativo
 * 6. Conferma finale
 */
function WizardDesignazioni({
    show,
    onClose,
    client,
    consultazione,
    sezioniSelezionate,
    onSuccess
}) {
    const [currentStep, setCurrentStep] = useState(1);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // Processo ID (ritornato da backend al primo step)
    const [processoId, setProcessoId] = useState(null);

    // Step 1: Delegato/SubDelegato (pre-selezionato utente loggato)
    const [delegati, setDelegati] = useState([]);
    const [subdelegati, setSubdelegati] = useState([]);
    const [useDelegato, setUseDelegato] = useState(true);
    const [selectedDelegato, setSelectedDelegato] = useState(null);
    const [selectedSubDelegato, setSelectedSubDelegato] = useState(null);
    const [isSuperuser, setIsSuperuser] = useState(false);

    // Step 2: Templates
    const [templatesIndividuali, setTemplatesIndividuali] = useState([]);
    const [templatesCumulativi, setTemplatesCumulativi] = useState([]);
    const [selectedTemplateInd, setSelectedTemplateInd] = useState(null);
    const [selectedTemplateCum, setSelectedTemplateCum] = useState(null);

    // Step 3: Form dinamica
    const [campiRichiesti, setCampiRichiesti] = useState([]);
    const [formData, setFormData] = useState({});

    // Step 4-5: PDF generati
    const [pdfIndividualeGenerato, setPdfIndividualeGenerato] = useState(false);
    const [pdfCumulativoGenerato, setPdfCumulativoGenerato] = useState(false);

    // PDF Viewer state
    const [pdfViewer, setPdfViewer] = useState(null); // { url, titolo, blobUrl } quando aperto
    const [loadingPdf, setLoadingPdf] = useState(false);

    // Confirm modal state
    const [showAnnullaModal, setShowAnnullaModal] = useState(false);

    useEffect(() => {
        console.log('[Wizard] useEffect triggered, show:', show);
        if (show) {
            console.log('[Wizard] Chiamata initWizard()');
            initWizard();
        }
    }, [show]);

    const initWizard = async () => {
        setLoading(true);
        setError(null);
        try {
            console.log('[Wizard] Inizializzazione con', sezioniSelezionate.length, 'sezioni');
            console.log('[Wizard] client.deleghe.processi:', client.deleghe.processi);
            console.log('[Wizard] consultazione.id:', consultazione?.id);

            // Avvia processo backend - fotografa mappatura
            const avviaResult = await client.deleghe.processi.avvia({
                consultazione_id: consultazione.id,
                sezione_ids: Array.from(sezioniSelezionate)
            });
            console.log('[Wizard] avviaResult ricevuto:', avviaResult);

            if (avviaResult.error) {
                throw new Error(avviaResult.error);
            }

            console.log('[Wizard] Processo avviato:', avviaResult);

            setProcessoId(avviaResult.processo_id);
            setDelegati(avviaResult.delegati_disponibili || []);
            setSubdelegati(avviaResult.subdelegati_disponibili || []);
            setIsSuperuser(avviaResult.is_superuser || false);

            const templatesInd = avviaResult.template_choices?.individuali || [];
            const templatesCum = avviaResult.template_choices?.cumulativi || [];
            setTemplatesIndividuali(templatesInd);
            setTemplatesCumulativi(templatesCum);

            // PRE-SELEZIONA template se ce n'è solo uno
            if (templatesInd.length === 1) {
                console.log('[Wizard] Pre-selezionato template individuale (unico):', templatesInd[0]);
                setSelectedTemplateInd(templatesInd[0].id);
            }
            if (templatesCum.length === 1) {
                console.log('[Wizard] Pre-selezionato template cumulativo (unico):', templatesCum[0]);
                setSelectedTemplateCum(templatesCum[0].id);
            }

            // AUTO-SELEZIONA utente corrente
            const currentUserDelegato = avviaResult.delegati_disponibili?.find(d => d.is_current_user);
            const currentUserSubDelegato = avviaResult.subdelegati_disponibili?.find(sd => sd.is_current_user);

            if (currentUserDelegato) {
                console.log('[Wizard] Auto-selezionato delegato corrente:', currentUserDelegato);
                setSelectedDelegato(currentUserDelegato.id);
                setUseDelegato(true);
            } else if (currentUserSubDelegato) {
                console.log('[Wizard] Auto-selezionato subdelegato corrente:', currentUserSubDelegato);
                setSelectedSubDelegato(currentUserSubDelegato.id);
                setUseDelegato(false);
            }

        } catch (err) {
            console.error('[Wizard] Errore inizializzazione:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleStep1Next = async () => {
        // Step 1: Validazione selezione delegato/subdelegato
        if (useDelegato && !selectedDelegato) {
            setError('Seleziona un delegato');
            return;
        }
        if (!useDelegato && !selectedSubDelegato) {
            setError('Seleziona un subdelegato');
            return;
        }

        setCurrentStep(2);
        setError(null);
    };

    const handleStep2Next = async () => {
        // Step 2: Selezione template
        if (!selectedTemplateInd || !selectedTemplateCum) {
            setError('Seleziona entrambi i template');
            return;
        }

        setLoading(true);
        try {
            // Richiedi campi richiesti per i template selezionati
            const campiResult = await client.deleghe.processi.getCampiRichiesti(
                processoId,
                selectedTemplateInd,
                selectedTemplateCum,
                useDelegato ? selectedDelegato : null,
                !useDelegato ? selectedSubDelegato : null
            );

            if (campiResult.error) {
                throw new Error(campiResult.error);
            }

            console.log('[Wizard] Campi richiesti:', campiResult);
            setCampiRichiesti(campiResult.campi || []);

            // Pre-compila form con valori attuali
            const initialFormData = {};
            campiResult.campi.forEach(campo => {
                initialFormData[campo.field_name] = campo.current_value || '';
            });
            setFormData(initialFormData);

            setCurrentStep(3);
            setError(null);
        } catch (err) {
            console.error('[Wizard] Errore step 2:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleStep3Next = async () => {
        // Step 3: Validazione form dati delegato
        const campiMancanti = campiRichiesti.filter(campo =>
            campo.required && !formData[campo.field_name]
        );

        if (campiMancanti.length > 0) {
            setError(`Compila tutti i campi obbligatori: ${campiMancanti.map(c => c.label).join(', ')}`);
            return;
        }

        setLoading(true);
        try {
            // Configura processo con template e dati
            const configResult = await client.deleghe.processi.configura(processoId, {
                template_individuale_id: selectedTemplateInd,
                template_cumulativo_id: selectedTemplateCum,
                delegato_id: useDelegato ? selectedDelegato : null,
                subdelegato_id: !useDelegato ? selectedSubDelegato : null,
                dati_delegato: formData
            });

            if (configResult.error) {
                throw new Error(configResult.error);
            }

            console.log('[Wizard] Processo configurato:', configResult);

            setCurrentStep(4);
            setError(null);
        } catch (err) {
            console.error('[Wizard] Errore step 3:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleGeneraPdfIndividuale = async () => {
        setLoading(true);
        try {
            const result = await client.deleghe.processi.generaIndividuale(processoId);

            if (result.error) {
                throw new Error(result.error);
            }

            console.log('[Wizard] PDF individuale generato');
            setPdfIndividualeGenerato(true);
            setError(null);
        } catch (err) {
            console.error('[Wizard] Errore generazione PDF individuale:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleGeneraPdfCumulativo = async () => {
        setLoading(true);
        try {
            const result = await client.deleghe.processi.generaCumulativo(processoId);

            if (result.error) {
                throw new Error(result.error);
            }

            console.log('[Wizard] PDF cumulativo generato');
            setPdfCumulativoGenerato(true);
            setError(null);
        } catch (err) {
            console.error('[Wizard] Errore generazione PDF cumulativo:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handlePreviewIndividuale = async () => {
        if (!processoId) {
            console.error('[Wizard] Processo ID mancante');
            return;
        }

        setLoadingPdf(true);
        try {
            console.log('[Wizard] Caricamento PDF individuale, processo:', processoId);

            // Usa il metodo preview che restituisce blob URL con autenticazione
            const blobUrl = await client.deleghe.processi.previewIndividuale(processoId);

            console.log('[Wizard] Blob URL ottenuto:', blobUrl);

            // URL originale per apertura in nuova scheda
            const serverUrl = client.server || process.env.REACT_APP_API_URL || window.location.origin.replace(':3000', ':3001');
            const originalUrl = `${serverUrl}/api/deleghe/processi/${processoId}/download_individuale/`;

            setPdfViewer({
                url: blobUrl,
                originalUrl,
                blobUrl,
                titolo: `Designazioni Individuali - Processo #${processoId}`
            });
        } catch (err) {
            console.error('[Wizard] Errore caricamento PDF:', err);
            setError('Errore caricamento PDF: ' + err.message);
        } finally {
            setLoadingPdf(false);
        }
    };

    const handlePreviewCumulativo = async () => {
        if (!processoId) {
            console.error('[Wizard] Processo ID mancante');
            return;
        }

        setLoadingPdf(true);
        try {
            console.log('[Wizard] Caricamento PDF cumulativo, processo:', processoId);

            // Usa il metodo preview che restituisce blob URL con autenticazione
            const blobUrl = await client.deleghe.processi.previewCumulativo(processoId);

            console.log('[Wizard] Blob URL ottenuto:', blobUrl);

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
            console.error('[Wizard] Errore caricamento PDF:', err);
            setError('Errore caricamento PDF: ' + err.message);
        } finally {
            setLoadingPdf(false);
        }
    };

    // Cleanup blob URL quando chiudi il viewer
    const handleClosePdfViewer = () => {
        if (pdfViewer?.blobUrl) {
            console.log('[Wizard] Revoke blob URL:', pdfViewer.blobUrl);
            window.URL.revokeObjectURL(pdfViewer.blobUrl);
        }
        setPdfViewer(null);
    };

    const handleConferma = async () => {
        setLoading(true);
        try {
            const result = await client.deleghe.processi.conferma(processoId);

            if (result.error) {
                throw new Error(result.error);
            }

            console.log('[Wizard] Processo confermato');
            onSuccess?.();
            handleClose();
        } catch (err) {
            console.error('[Wizard] Errore conferma:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleAnnulla = () => {
        // Apri modale di conferma
        setShowAnnullaModal(true);
    };

    const confirmAnnulla = async () => {
        setShowAnnullaModal(false);

        if (processoId) {
            try {
                await client.deleghe.processi.annulla(processoId);
            } catch (err) {
                console.error('[Wizard] Errore annullamento:', err);
            }
        }

        handleClose();
    };

    const handleClose = () => {
        // Reset stato
        setCurrentStep(1);
        setProcessoId(null);
        setDelegati([]);
        setSubdelegati([]);
        setSelectedDelegato(null);
        setSelectedSubDelegato(null);
        setIsSuperuser(false);
        setSelectedTemplateInd(null);
        setSelectedTemplateCum(null);
        setCampiRichiesti([]);
        setFormData({});
        setPdfIndividualeGenerato(false);
        setPdfCumulativoGenerato(false);
        setError(null);
        onClose?.();
    };

    const handleBack = () => {
        if (currentStep > 1) {
            setCurrentStep(currentStep - 1);
            setError(null);
        }
    };

    console.log('[Wizard] Render chiamato, show:', show, 'loading:', loading);
    if (!show) {
        console.log('[Wizard] Non mostro wizard (show=false)');
        return null;
    }

    const steps = [
        { number: 1, label: 'Delegato' },
        { number: 2, label: 'Template' },
        { number: 3, label: 'Dati' },
        { number: 4, label: 'PDF Individuale' },
        { number: 5, label: 'PDF Cumulativo' },
        { number: 6, label: 'Conferma' }
    ];

    return (
        <div className="wizard-overlay">
            <div className="wizard-modal">
                {/* Header */}
                <div className="wizard-header">
                    <h4>
                        <i className="fas fa-magic me-2"></i>
                        Processo di Designazione
                    </h4>
                    <button className="btn-close" onClick={handleAnnulla}></button>
                </div>

                {/* Progress */}
                <div className="wizard-progress">
                    {steps.map(step => (
                        <div
                            key={step.number}
                            className={`wizard-step ${currentStep === step.number ? 'active' : ''} ${currentStep > step.number ? 'completed' : ''}`}
                        >
                            <div className="step-number">
                                {currentStep > step.number ? <i className="fas fa-check"></i> : step.number}
                            </div>
                            <div className="step-label">{step.label}</div>
                        </div>
                    ))}
                </div>

                {/* Error */}
                {error && (
                    <div className="alert alert-danger">
                        <i className="fas fa-exclamation-triangle me-2"></i>
                        {error}
                    </div>
                )}

                {/* Content */}
                <div className="wizard-content">
                    {loading && (
                        <div className="text-center p-5">
                            <div className="spinner-border text-primary mb-3"></div>
                            <p>Caricamento...</p>
                        </div>
                    )}

                    {!loading && currentStep === 1 && (
                        <StepDelegato
                            delegati={delegati}
                            subdelegati={subdelegati}
                            useDelegato={useDelegato}
                            setUseDelegato={setUseDelegato}
                            selectedDelegato={selectedDelegato}
                            setSelectedDelegato={setSelectedDelegato}
                            selectedSubDelegato={selectedSubDelegato}
                            setSelectedSubDelegato={setSelectedSubDelegato}
                            isSuperuser={isSuperuser}
                        />
                    )}

                    {!loading && currentStep === 2 && (
                        <StepTemplate
                            templatesIndividuali={templatesIndividuali}
                            templatesCumulativi={templatesCumulativi}
                            selectedTemplateInd={selectedTemplateInd}
                            setSelectedTemplateInd={setSelectedTemplateInd}
                            selectedTemplateCum={selectedTemplateCum}
                            setSelectedTemplateCum={setSelectedTemplateCum}
                        />
                    )}

                    {!loading && currentStep === 3 && (
                        <StepFormDati
                            campiRichiesti={campiRichiesti}
                            formData={formData}
                            setFormData={setFormData}
                        />
                    )}

                    {!loading && currentStep === 4 && (
                        <StepPdfIndividuale
                            processoId={processoId}
                            generato={pdfIndividualeGenerato}
                            onGenera={handleGeneraPdfIndividuale}
                            onPreview={handlePreviewIndividuale}
                        />
                    )}

                    {!loading && currentStep === 5 && (
                        <StepPdfCumulativo
                            processoId={processoId}
                            generato={pdfCumulativoGenerato}
                            onGenera={handleGeneraPdfCumulativo}
                            onPreview={handlePreviewCumulativo}
                        />
                    )}

                    {!loading && currentStep === 6 && (
                        <StepConferma
                            sezioniCount={sezioniSelezionate.length}
                        />
                    )}
                </div>

                {/* Footer */}
                <div className="wizard-footer">
                    <button
                        className="btn btn-outline-secondary"
                        onClick={currentStep === 1 ? handleAnnulla : handleBack}
                        disabled={loading}
                    >
                        {currentStep === 1 ? 'Annulla' : 'Indietro'}
                    </button>

                    <div className="ms-auto d-flex gap-2">
                        {currentStep < 6 && (
                            <button
                                className="btn btn-primary"
                                onClick={() => {
                                    if (currentStep === 1) handleStep1Next();
                                    else if (currentStep === 2) handleStep2Next();
                                    else if (currentStep === 3) handleStep3Next();
                                    else if (currentStep === 4) {
                                        if (pdfIndividualeGenerato) setCurrentStep(5);
                                        else setError('Genera prima il PDF individuale');
                                    }
                                    else if (currentStep === 5) {
                                        if (pdfCumulativoGenerato) setCurrentStep(6);
                                        else setError('Genera prima il PDF cumulativo');
                                    }
                                }}
                                disabled={loading}
                            >
                                Avanti <i className="fas fa-arrow-right ms-2"></i>
                            </button>
                        )}

                        {currentStep === 6 && (
                            <button
                                className="btn btn-success"
                                onClick={handleConferma}
                                disabled={loading}
                            >
                                <i className="fas fa-check me-2"></i>
                                Conferma Processo
                            </button>
                        )}
                    </div>
                </div>
            </div>

            {/* PDF Viewer Modal */}
            {pdfViewer && (
                <PDFViewer
                    url={pdfViewer.url}
                    originalUrl={pdfViewer.originalUrl}
                    titolo={pdfViewer.titolo}
                    onClose={handleClosePdfViewer}
                />
            )}

            {/* Confirm Annulla Modal */}
            <ConfirmModal
                show={showAnnullaModal}
                onConfirm={confirmAnnulla}
                onCancel={() => setShowAnnullaModal(false)}
                title="⚠️ Annulla Processo"
                confirmText="Sì, annulla"
                cancelText="No, continua"
                confirmVariant="danger"
            >
                <div className="alert alert-warning mb-0">
                    <p className="mb-2">
                        <strong>Vuoi davvero annullare il processo?</strong>
                    </p>
                    <p className="mb-0">
                        Tutti i dati inseriti andranno persi e il processo verrà eliminato.
                    </p>
                </div>
            </ConfirmModal>
        </div>
    );
}

// Step components

function StepDelegato({ delegati, subdelegati, useDelegato, setUseDelegato, selectedDelegato, setSelectedDelegato, selectedSubDelegato, setSelectedSubDelegato, isSuperuser }) {
    // Per utenti normali: mostra solo se stessi
    const myDelegati = isSuperuser ? delegati : delegati.filter(d => d.is_current_user);
    const mySubdelegati = isSuperuser ? subdelegati : subdelegati.filter(sd => sd.is_current_user);
    const hasDelegato = myDelegati.length > 0;
    const hasSubdelegato = mySubdelegati.length > 0;

    // Trova il nome selezionato per la visualizzazione read-only
    const selectedDelegatoObj = delegati.find(d => d.id === selectedDelegato);
    const selectedSubDelegatoObj = subdelegati.find(sd => sd.id === selectedSubDelegato);

    return (
        <div className="step-container">
            <h5 className="mb-4">Chi effettua la designazione?</h5>
            {isSuperuser ? (
                <p className="text-muted mb-4">
                    Come amministratore puoi selezionare qualsiasi delegato o subdelegato.
                </p>
            ) : (
                <p className="text-muted mb-4">
                    La designazione verrà effettuata a tuo nome.
                </p>
            )}

            {hasDelegato && (
                <div className="mb-4">
                    <div className="form-check mb-3">
                        <input
                            className="form-check-input"
                            type="radio"
                            id="radio-delegato"
                            checked={useDelegato}
                            onChange={() => setUseDelegato(true)}
                            disabled={!hasDelegato || (!hasSubdelegato && hasDelegato)}
                        />
                        <label className="form-check-label" htmlFor="radio-delegato">
                            <strong>Delegato di Lista</strong>
                        </label>
                    </div>

                    {useDelegato && (
                        isSuperuser ? (
                            <select
                                className="form-select"
                                value={selectedDelegato || ''}
                                onChange={(e) => setSelectedDelegato(parseInt(e.target.value))}
                            >
                                <option value="">Seleziona delegato...</option>
                                {myDelegati.map(d => (
                                    <option key={d.id} value={d.id}>
                                        {d.nome_completo} {d.carica && `(${d.carica})`} {d.is_current_user && '(Tu)'}
                                    </option>
                                ))}
                            </select>
                        ) : (
                            <div className="form-control bg-light">
                                {selectedDelegatoObj?.nome_completo || 'Non selezionato'}
                                {selectedDelegatoObj?.carica && ` (${selectedDelegatoObj.carica})`}
                            </div>
                        )
                    )}
                </div>
            )}

            {hasSubdelegato && (
                <div>
                    <div className="form-check mb-3">
                        <input
                            className="form-check-input"
                            type="radio"
                            id="radio-subdelegato"
                            checked={!useDelegato}
                            onChange={() => setUseDelegato(false)}
                            disabled={(!hasDelegato && hasSubdelegato) || !hasSubdelegato}
                        />
                        <label className="form-check-label" htmlFor="radio-subdelegato">
                            <strong>Sub-Delegato</strong>
                        </label>
                    </div>

                    {!useDelegato && (
                        isSuperuser ? (
                            <select
                                className="form-select"
                                value={selectedSubDelegato || ''}
                                onChange={(e) => setSelectedSubDelegato(parseInt(e.target.value))}
                            >
                                <option value="">Seleziona sub-delegato...</option>
                                {mySubdelegati.map(sd => (
                                    <option key={sd.id} value={sd.id}>
                                        {sd.nome_completo} {sd.is_current_user && '(Tu)'}
                                    </option>
                                ))}
                            </select>
                        ) : (
                            <div className="form-control bg-light">
                                {selectedSubDelegatoObj?.nome_completo || 'Non selezionato'}
                            </div>
                        )
                    )}
                </div>
            )}

            {!hasDelegato && !hasSubdelegato && (
                <div className="alert alert-warning">
                    <i className="fas fa-exclamation-triangle me-2"></i>
                    Non risulti come delegato o subdelegato per questa consultazione.
                </div>
            )}
        </div>
    );
}

function StepTemplate({ templatesIndividuali, templatesCumulativi, selectedTemplateInd, setSelectedTemplateInd, selectedTemplateCum, setSelectedTemplateCum }) {
    return (
        <div className="step-container">
            <h5 className="mb-4">Seleziona i template da utilizzare</h5>

            <div className="mb-4">
                <label className="form-label">
                    <strong>Template Individuale</strong>
                    <small className="text-muted ms-2">(un PDF per ogni sezione)</small>
                </label>
                <select
                    className="form-select"
                    value={selectedTemplateInd || ''}
                    onChange={(e) => setSelectedTemplateInd(parseInt(e.target.value))}
                >
                    <option value="">Seleziona template...</option>
                    {templatesIndividuali.map(t => (
                        <option key={t.id} value={t.id}>
                            {t.nome}
                        </option>
                    ))}
                </select>
            </div>

            <div>
                <label className="form-label">
                    <strong>Template Cumulativo</strong>
                    <small className="text-muted ms-2">(un PDF con tutte le sezioni)</small>
                </label>
                <select
                    className="form-select"
                    value={selectedTemplateCum || ''}
                    onChange={(e) => setSelectedTemplateCum(parseInt(e.target.value))}
                >
                    <option value="">Seleziona template...</option>
                    {templatesCumulativi.map(t => (
                        <option key={t.id} value={t.id}>
                            {t.nome}
                        </option>
                    ))}
                </select>
            </div>
        </div>
    );
}

function StepFormDati({ campiRichiesti, formData, setFormData }) {
    const handleChange = (fieldName, value) => {
        setFormData(prev => ({
            ...prev,
            [fieldName]: value
        }));
    };

    return (
        <div className="step-container">
            <h5 className="mb-4">Compila i dati necessari per i documenti</h5>

            {campiRichiesti.map(campo => (
                <div key={campo.field_name} className="mb-3">
                    <label className="form-label">
                        {campo.label}
                        {campo.required && <span className="text-danger">*</span>}
                    </label>
                    {campo.field_type === 'textarea' ? (
                        <textarea
                            className="form-control"
                            value={formData[campo.field_name] || ''}
                            onChange={(e) => handleChange(campo.field_name, e.target.value)}
                            required={campo.required}
                            rows={3}
                        />
                    ) : campo.field_type === 'date' ? (
                        <input
                            type="date"
                            className="form-control"
                            value={formData[campo.field_name] || ''}
                            onChange={(e) => handleChange(campo.field_name, e.target.value)}
                            required={campo.required}
                        />
                    ) : (
                        <input
                            type="text"
                            className="form-control"
                            value={formData[campo.field_name] || ''}
                            onChange={(e) => handleChange(campo.field_name, e.target.value)}
                            required={campo.required}
                        />
                    )}
                    {campo.description && (
                        <small className="form-text text-muted">{campo.description}</small>
                    )}
                </div>
            ))}
        </div>
    );
}

function StepPdfIndividuale({ processoId, generato, onGenera, onPreview }) {
    return (
        <div className="step-container text-center">
            <h5 className="mb-4">Genera e controlla il PDF Individuale</h5>

            {!generato ? (
                <div>
                    <p className="text-muted mb-4">
                        Clicca sul pulsante per generare i documenti PDF individuali (uno per ogni sezione).
                    </p>
                    <button
                        className="btn btn-primary btn-lg"
                        onClick={onGenera}
                    >
                        <i className="fas fa-file-pdf me-2"></i>
                        Genera PDF Individuale
                    </button>
                </div>
            ) : (
                <div>
                    <div className="alert alert-success">
                        <i className="fas fa-check-circle me-2"></i>
                        PDF Individuale generato con successo!
                    </div>
                    <button
                        className="btn btn-outline-primary"
                        onClick={onPreview}
                    >
                        <i className="fas fa-eye me-2"></i>
                        Visualizza e Controlla
                    </button>
                </div>
            )}
        </div>
    );
}

function StepPdfCumulativo({ processoId, generato, onGenera, onPreview }) {
    return (
        <div className="step-container text-center">
            <h5 className="mb-4">Genera e controlla il PDF Cumulativo</h5>

            {!generato ? (
                <div>
                    <p className="text-muted mb-4">
                        Clicca sul pulsante per generare il documento PDF cumulativo (tutte le sezioni in un unico file).
                    </p>
                    <button
                        className="btn btn-primary btn-lg"
                        onClick={onGenera}
                    >
                        <i className="fas fa-file-pdf me-2"></i>
                        Genera PDF Cumulativo
                    </button>
                </div>
            ) : (
                <div>
                    <div className="alert alert-success">
                        <i className="fas fa-check-circle me-2"></i>
                        PDF Cumulativo generato con successo!
                    </div>
                    <button
                        className="btn btn-outline-primary"
                        onClick={onPreview}
                    >
                        <i className="fas fa-eye me-2"></i>
                        Visualizza e Controlla
                    </button>
                </div>
            )}
        </div>
    );
}

function StepConferma({ sezioniCount }) {
    return (
        <div className="step-container text-center">
            <div className="mb-4">
                <i className="fas fa-check-circle text-success" style={{fontSize: '64px'}}></i>
            </div>
            <h5 className="mb-4">Tutto Pronto!</h5>
            <p className="text-muted mb-4">
                Hai completato tutti i passaggi. Clicca "Conferma Processo" per rendere definitive
                le {sezioniCount} designazioni create.
            </p>
            <div className="alert alert-info">
                <i className="fas fa-info-circle me-2"></i>
                Dopo la conferma, le designazioni saranno nello stato CONFERMATA e non potranno più essere modificate.
            </div>
        </div>
    );
}

export default WizardDesignazioni;
