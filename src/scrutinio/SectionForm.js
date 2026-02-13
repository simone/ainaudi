import React, {useEffect, useState, useRef, useCallback} from "react";
import '@fortawesome/fontawesome-free/css/all.min.css';

// Stili per il wizard mobile-first
const wizardStyles = `
    /* Overlay backdrop */
    .wizard-overlay {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.5);
        z-index: 998;
        opacity: 0;
        animation: fadeIn 0.3s ease forwards;
    }

    .wizard-overlay.closing {
        animation: fadeOut 0.3s ease forwards;
    }

    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    @keyframes fadeOut {
        from { opacity: 1; }
        to { opacity: 0; }
    }

    /* Sheet container */
    .wizard-sheet {
        position: fixed;
        inset: 0;
        top: 40px;
        z-index: 999;
        transform: translateY(100%);
        animation: slideUp 0.35s cubic-bezier(0.32, 0.72, 0, 1) forwards;
        will-change: transform;
    }

    .wizard-sheet.closing {
        animation: slideDown 0.3s cubic-bezier(0.32, 0.72, 0, 1) forwards;
    }

    .wizard-sheet.dragging {
        animation: none;
        transition: none;
    }

    @keyframes slideUp {
        from { transform: translateY(100%); }
        to { transform: translateY(0); }
    }

    @keyframes slideDown {
        from { transform: translateY(0); }
        to { transform: translateY(100%); }
    }

    .wizard-container {
        height: 100%;
        display: flex;
        flex-direction: column;
        background: #f5f5f5;
        border-radius: 20px 20px 0 0;
        overflow: hidden;
    }

    /* Drag handle */
    .wizard-drag-handle {
        flex-shrink: 0;
        padding: 12px 0 8px 0;
        display: flex;
        justify-content: center;
        cursor: grab;
        touch-action: none;
    }

    .wizard-drag-handle:active {
        cursor: grabbing;
    }

    .wizard-drag-bar {
        width: 36px;
        height: 5px;
        background: #ccc;
        border-radius: 3px;
    }

    .wizard-header {
        flex-shrink: 0;
        background: linear-gradient(135deg, #0d6efd 0%, #0a58ca 100%);
        color: white;
        padding: 8px 16px 12px 16px;
    }

    .wizard-header-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 8px;
    }

    .wizard-header-back {
        background: rgba(255,255,255,0.2);
        border: none;
        color: white;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: background 0.2s;
    }

    .wizard-header-back:hover {
        background: rgba(255,255,255,0.3);
    }

    .wizard-header-title {
        text-align: center;
        flex: 1;
    }

    .wizard-header-sezione {
        font-size: 1.1rem;
        font-weight: 700;
    }

    .wizard-header-comune {
        font-size: 0.8rem;
        opacity: 0.9;
    }

    /* Step tabs - Touch optimized */
    .wizard-tabs {
        display: flex;
        gap: 8px;
        padding: 10px 0 6px 0;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: none;
    }

    .wizard-tabs::-webkit-scrollbar {
        display: none;
    }

    .wizard-tab {
        flex: 0 0 auto;
        min-height: 36px;
        padding: 8px 14px;
        border-radius: 18px;
        font-size: 0.8rem;
        font-weight: 600;
        background: rgba(255,255,255,0.2);
        color: white;
        border: none;
        cursor: pointer;
        white-space: nowrap;
        transition: all 0.15s;
        -webkit-tap-highlight-color: transparent;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .wizard-tab:active {
        transform: scale(0.95);
    }

    .wizard-tab.active {
        background: white;
        color: #0d6efd;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }

    .wizard-tab.complete:not(.active) {
        background: rgba(255,255,255,0.5);
    }

    .wizard-tab-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        flex-shrink: 0;
    }

    .wizard-tab-check {
        color: #198754;
        font-size: 0.7rem;
    }

    /* Scrollable content area */
    .wizard-scroll {
        flex: 1;
        overflow-y: auto;
        -webkit-overflow-scrolling: touch;
        overscroll-behavior: contain;
    }

    .wizard-content {
        padding: 16px;
        padding-bottom: 100px;
    }

    .wizard-card {
        background: white;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }

    .wizard-card-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #333;
        margin-bottom: 4px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .wizard-card-subtitle {
        font-size: 0.85rem;
        color: #666;
        margin-bottom: 16px;
    }

    /* Form fields */
    .wizard-field-group {
        margin-bottom: 16px;
    }

    .wizard-field-label {
        font-size: 0.85rem;
        font-weight: 600;
        color: #555;
        margin-bottom: 6px;
        display: block;
    }

    .wizard-field-row {
        display: flex;
        gap: 12px;
    }

    .wizard-field-col {
        flex: 1;
    }

    .wizard-field-col label {
        font-size: 0.75rem;
        color: #888;
        display: block;
        margin-bottom: 4px;
    }

    .wizard-input {
        width: 100%;
        padding: 12px 16px;
        font-size: 1.1rem;
        font-weight: 600;
        border: 2px solid #e0e0e0;
        border-radius: 12px;
        text-align: center;
        transition: border-color 0.2s;
    }

    .wizard-input:focus {
        outline: none;
        border-color: #0d6efd;
    }

    /* Totals */
    .wizard-total {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 16px;
        background: #f8f9fa;
        border-radius: 12px;
        margin-top: 12px;
    }

    .wizard-total-label {
        font-size: 0.9rem;
        color: #666;
    }

    .wizard-total-value {
        font-size: 1.25rem;
        font-weight: 700;
        color: #333;
    }

    .wizard-total-value.highlight {
        color: #0d6efd;
    }

    /* Referendum vote buttons */
    .referendum-votes {
        display: flex;
        gap: 16px;
        margin-top: 8px;
    }

    .referendum-vote-card {
        flex: 1;
        background: #f8f9fa;
        border-radius: 16px;
        padding: 16px;
        text-align: center;
    }

    .referendum-vote-card.si {
        border: 2px solid #198754;
    }

    .referendum-vote-card.no {
        border: 2px solid #dc3545;
    }

    .referendum-vote-label {
        font-size: 1.5rem;
        font-weight: 800;
        margin-bottom: 8px;
    }

    .referendum-vote-label.si { color: #198754; }
    .referendum-vote-label.no { color: #dc3545; }

    .referendum-vote-input {
        width: 100%;
        padding: 12px;
        font-size: 1.5rem;
        font-weight: 700;
        border: none;
        border-radius: 10px;
        text-align: center;
        background: white;
    }

    .referendum-vote-input:focus {
        outline: none;
        box-shadow: 0 0 0 2px rgba(13, 110, 253, 0.25);
    }

    /* Scheda header with color */
    .scheda-color-bar {
        height: 6px;
        border-radius: 3px;
        margin-bottom: 12px;
    }

    /* Bottom navigation - Mobile optimized */
    .wizard-nav {
        flex-shrink: 0;
        background: white;
        padding: 12px 16px;
        padding-bottom: max(12px, env(safe-area-inset-bottom));
        box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
        display: flex;
        gap: 12px;
        position: relative;
    }

    .wizard-nav-btn {
        flex: 1;
        min-height: 52px;
        padding: 14px 16px;
        border-radius: 14px;
        font-size: 1rem;
        font-weight: 600;
        border: none;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        transition: all 0.15s;
        -webkit-tap-highlight-color: transparent;
    }

    .wizard-nav-btn:active {
        transform: scale(0.97);
    }

    .wizard-nav-btn.secondary {
        background: #f0f0f0;
        color: #495057;
        flex: 0.8;
    }

    .wizard-nav-btn.primary {
        background: linear-gradient(135deg, #0d6efd 0%, #0a58ca 100%);
        color: white;
        flex: 1.2;
    }

    .wizard-nav-btn.success {
        background: linear-gradient(135deg, #198754 0%, #157347 100%);
        color: white;
        flex: 1.2;
    }

    .wizard-nav-btn:disabled {
        opacity: 0.4;
        cursor: not-allowed;
        transform: none;
    }

    .wizard-nav-btn i {
        font-size: 0.9rem;
    }

    /* Step indicator in nav */
    .wizard-nav-indicator {
        position: absolute;
        top: -24px;
        left: 50%;
        transform: translateX(-50%);
        background: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        color: #666;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    /* Saving indicator */
    .saving-indicator {
        position: fixed;
        top: 80px;
        left: 50%;
        transform: translateX(-50%);
        background: #198754;
        color: white;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        z-index: 200;
        animation: fadeInOut 1.5s ease-in-out;
    }

    @keyframes fadeInOut {
        0% { opacity: 0; transform: translateX(-50%) translateY(-10px); }
        20% { opacity: 1; transform: translateX(-50%) translateY(0); }
        80% { opacity: 1; transform: translateX(-50%) translateY(0); }
        100% { opacity: 0; transform: translateX(-50%) translateY(-10px); }
    }
`;

function SectionForm({schede, section, sectionData, saveSection, saveAndClose}) {
    // Steps: 0 = Dati Seggio, 1..N = Schede
    const totalSteps = schede.length + 1;
    const [currentStep, setCurrentStep] = useState(0);
    const [showSaved, setShowSaved] = useState(false);
    const hasChangesRef = useRef(false);

    // Bottom sheet animation state
    const [isClosing, setIsClosing] = useState(false);
    const [dragOffset, setDragOffset] = useState(0);
    const [isDragging, setIsDragging] = useState(false);
    const sheetRef = useRef(null);
    const dragStartY = useRef(0);
    const dragStartOffset = useRef(0);

    // Initialize form data from sectionData
    const [datiSeggio, setDatiSeggio] = useState({
        elettori_maschi: sectionData?.dati_seggio?.elettori_maschi ?? '',
        elettori_femmine: sectionData?.dati_seggio?.elettori_femmine ?? '',
        votanti_maschi: sectionData?.dati_seggio?.votanti_maschi ?? '',
        votanti_femmine: sectionData?.dati_seggio?.votanti_femmine ?? '',
    });

    // Initialize schede data
    const [schedeData, setSchedeData] = useState(() => {
        const initial = {};
        schede.forEach(scheda => {
            const existing = sectionData?.schede?.[String(scheda.id)];
            initial[scheda.id] = {
                schede_ricevute: existing?.schede_ricevute ?? '',
                schede_autenticate: existing?.schede_autenticate ?? '',
                schede_bianche: existing?.schede_bianche ?? '',
                schede_nulle: existing?.schede_nulle ?? '',
                schede_contestate: existing?.schede_contestate ?? '',
                voti: existing?.voti ?? {},
            };
        });
        return initial;
    });

    // Calculate first incomplete step
    const getFirstIncompleteStep = useCallback(() => {
        // Check seggio
        const seggio = sectionData?.dati_seggio || {};
        const seggioComplete = seggio.elettori_maschi != null &&
                              seggio.elettori_femmine != null &&
                              seggio.votanti_maschi != null &&
                              seggio.votanti_femmine != null;
        if (!seggioComplete) return 0;

        // Check each scheda
        for (let i = 0; i < schede.length; i++) {
            const schedaData = sectionData?.schede?.[String(schede[i].id)];
            if (!schedaData) return i + 1;

            const isReferendum = schede[i].schema?.tipo === 'si_no';
            const hasVotes = !isReferendum || (schedaData.voti?.si != null && schedaData.voti?.no != null);
            const complete = schedaData.schede_ricevute != null && hasVotes;
            if (!complete) return i + 1;
        }

        return 0; // All complete, go to first
    }, [schede, sectionData]);

    // Start at first incomplete step
    useEffect(() => {
        const startStep = getFirstIncompleteStep();
        setCurrentStep(startStep);
    }, []);

    useEffect(() => {
        window.scrollTo(0, 0);
    }, [currentStep]);

    // Handle browser back button
    useEffect(() => {
        window.history.pushState(null, null, window.location.pathname);
        const onPopState = () => {
            handleExit();
        };
        window.addEventListener('popstate', onPopState);
        return () => window.removeEventListener('popstate', onPopState);
    }, []);

    // Prevent scroll on number input wheel
    useEffect(() => {
        const handleWheel = (e) => {
            if (document.activeElement.type === "number") {
                e.preventDefault();
            }
        };
        window.addEventListener('wheel', handleWheel, { passive: false });
        return () => window.removeEventListener('wheel', handleWheel);
    }, []);

    // Build payload for saving
    const buildPayload = useCallback(() => {
        return {
            comune: section.comune,
            sezione: section.sezione,
            dati_seggio: {
                elettori_maschi: datiSeggio.elettori_maschi === '' ? null : +datiSeggio.elettori_maschi,
                elettori_femmine: datiSeggio.elettori_femmine === '' ? null : +datiSeggio.elettori_femmine,
                votanti_maschi: datiSeggio.votanti_maschi === '' ? null : +datiSeggio.votanti_maschi,
                votanti_femmine: datiSeggio.votanti_femmine === '' ? null : +datiSeggio.votanti_femmine,
            },
            schede: Object.fromEntries(
                schede.map(scheda => {
                    const data = schedeData[scheda.id];
                    return [scheda.id, {
                        schede_ricevute: data.schede_ricevute === '' ? null : +data.schede_ricevute,
                        schede_autenticate: data.schede_autenticate === '' ? null : +data.schede_autenticate,
                        schede_bianche: data.schede_bianche === '' ? null : +data.schede_bianche,
                        schede_nulle: data.schede_nulle === '' ? null : +data.schede_nulle,
                        schede_contestate: data.schede_contestate === '' ? null : +data.schede_contestate,
                        voti: {
                            si: data.voti?.si === '' ? null : (data.voti?.si != null ? +data.voti.si : null),
                            no: data.voti?.no === '' ? null : (data.voti?.no != null ? +data.voti.no : null),
                        },
                    }];
                })
            ),
        };
    }, [section, datiSeggio, schede, schedeData]);

    // Auto-save function (doesn't close the form)
    const doSave = useCallback(async (showIndicator = true) => {
        if (!hasChangesRef.current) return;

        const payload = buildPayload();
        const success = await saveSection(payload);

        if (success) {
            hasChangesRef.current = false;
            if (showIndicator) {
                setShowSaved(true);
                setTimeout(() => setShowSaved(false), 1500);
            }
        }
    }, [buildPayload, saveSection]);

    // No auto-save on data change - save only on step change or exit
    // This prevents hammering the server

    // Calculate totals
    const totalElettori = (+datiSeggio.elettori_maschi || 0) + (+datiSeggio.elettori_femmine || 0);
    const totalVotanti = (+datiSeggio.votanti_maschi || 0) + (+datiSeggio.votanti_femmine || 0);
    const affluenza = totalElettori > 0 ? ((totalVotanti / totalElettori) * 100).toFixed(1) : 0;

    const handleSeggioChange = (field, value) => {
        const numValue = value === '' ? '' : Math.max(0, parseInt(value) || 0);
        setDatiSeggio(prev => ({ ...prev, [field]: numValue }));
        hasChangesRef.current = true;
    };

    const handleSchedaChange = (schedaId, field, value) => {
        const numValue = value === '' ? '' : Math.max(0, parseInt(value) || 0);
        setSchedeData(prev => ({
            ...prev,
            [schedaId]: {
                ...prev[schedaId],
                [field]: numValue,
            }
        }));
        hasChangesRef.current = true;
    };

    const handleVotiChange = (schedaId, votoKey, value) => {
        const numValue = value === '' ? '' : Math.max(0, parseInt(value) || 0);
        setSchedeData(prev => ({
            ...prev,
            [schedaId]: {
                ...prev[schedaId],
                voti: {
                    ...prev[schedaId].voti,
                    [votoKey]: numValue,
                }
            }
        }));
        hasChangesRef.current = true;
    };

    const goToStep = async (step) => {
        if (step >= 0 && step < totalSteps && step !== currentStep) {
            // Save before changing step
            await doSave(false);
            setCurrentStep(step);
        }
    };

    const goNext = () => goToStep(currentStep + 1);
    const goPrev = () => goToStep(currentStep - 1);

    const handleExit = async () => {
        // Start closing animation, then save and close
        setIsClosing(true);
        const payload = buildPayload();
        // Wait for animation then close
        setTimeout(async () => {
            await saveAndClose(payload);
        }, 280);
    };

    // Refs for drag handling
    const dragHandleRef = useRef(null);
    const isDraggingRef = useRef(false);
    const dragOffsetRef = useRef(0);

    // Touch handlers for swipe-to-dismiss (native events for passive: false)
    useEffect(() => {
        const dragHandle = dragHandleRef.current;
        if (!dragHandle) return;

        const handleTouchStart = (e) => {
            e.preventDefault();
            dragStartY.current = e.touches[0].clientY;
            dragStartOffset.current = dragOffsetRef.current;
            isDraggingRef.current = true;
            setIsDragging(true);
        };

        const handleTouchMove = (e) => {
            if (!isDraggingRef.current) return;
            e.preventDefault();
            const currentY = e.touches[0].clientY;
            const diff = currentY - dragStartY.current;
            const newOffset = Math.max(0, dragStartOffset.current + diff);
            dragOffsetRef.current = newOffset;
            setDragOffset(newOffset);
        };

        const handleTouchEnd = () => {
            if (!isDraggingRef.current) return;
            isDraggingRef.current = false;
            setIsDragging(false);

            if (dragOffsetRef.current > 150) {
                handleExit();
            } else {
                dragOffsetRef.current = 0;
                setDragOffset(0);
            }
        };

        dragHandle.addEventListener('touchstart', handleTouchStart, { passive: false });
        document.addEventListener('touchmove', handleTouchMove, { passive: false });
        document.addEventListener('touchend', handleTouchEnd);

        return () => {
            dragHandle.removeEventListener('touchstart', handleTouchStart);
            document.removeEventListener('touchmove', handleTouchMove);
            document.removeEventListener('touchend', handleTouchEnd);
        };
    }, []);

    // Check if a step is complete
    const isStepComplete = (stepIndex) => {
        if (stepIndex === 0) {
            return datiSeggio.elettori_maschi !== '' &&
                   datiSeggio.elettori_femmine !== '' &&
                   datiSeggio.votanti_maschi !== '' &&
                   datiSeggio.votanti_femmine !== '';
        }
        const scheda = schede[stepIndex - 1];
        const data = schedeData[scheda.id];
        const isReferendum = scheda.schema?.tipo === 'si_no';
        const hasVotes = !isReferendum || (data.voti?.si !== '' && data.voti?.no !== '');
        return data.schede_ricevute !== '' && hasVotes;
    };

    // Render step content
    const renderStepContent = () => {
        // Step 0: Dati Seggio
        if (currentStep === 0) {
            return (
                <div className="wizard-card">
                    <div className="wizard-card-title">
                        <i className="fas fa-users"></i>
                        Dati del Seggio
                    </div>
                    <div className="wizard-card-subtitle">
                        Elettori iscritti e votanti
                    </div>

                    {/* Elettori */}
                    <div className="wizard-field-group">
                        <span className="wizard-field-label">Elettori Iscritti</span>
                        <div className="wizard-field-row">
                            <div className="wizard-field-col">
                                <label>Maschi</label>
                                <input
                                    type="number"
                                    inputMode="numeric"
                                    className="wizard-input"
                                    value={datiSeggio.elettori_maschi}
                                    onChange={(e) => handleSeggioChange('elettori_maschi', e.target.value)}
                                    placeholder="0"
                                />
                            </div>
                            <div className="wizard-field-col">
                                <label>Femmine</label>
                                <input
                                    type="number"
                                    inputMode="numeric"
                                    className="wizard-input"
                                    value={datiSeggio.elettori_femmine}
                                    onChange={(e) => handleSeggioChange('elettori_femmine', e.target.value)}
                                    placeholder="0"
                                />
                            </div>
                        </div>
                        <div className="wizard-total">
                            <span className="wizard-total-label">Totale Elettori</span>
                            <span className="wizard-total-value">{totalElettori}</span>
                        </div>
                    </div>

                    {/* Votanti */}
                    <div className="wizard-field-group">
                        <span className="wizard-field-label">Votanti</span>
                        <div className="wizard-field-row">
                            <div className="wizard-field-col">
                                <label>Maschi</label>
                                <input
                                    type="number"
                                    inputMode="numeric"
                                    className="wizard-input"
                                    value={datiSeggio.votanti_maschi}
                                    onChange={(e) => handleSeggioChange('votanti_maschi', e.target.value)}
                                    placeholder="0"
                                />
                            </div>
                            <div className="wizard-field-col">
                                <label>Femmine</label>
                                <input
                                    type="number"
                                    inputMode="numeric"
                                    className="wizard-input"
                                    value={datiSeggio.votanti_femmine}
                                    onChange={(e) => handleSeggioChange('votanti_femmine', e.target.value)}
                                    placeholder="0"
                                />
                            </div>
                        </div>
                        <div className="wizard-total">
                            <span className="wizard-total-label">Totale Votanti</span>
                            <span className="wizard-total-value">{totalVotanti}</span>
                        </div>
                        {totalElettori > 0 && (
                            <div className="wizard-total" style={{ marginTop: 8 }}>
                                <span className="wizard-total-label">Affluenza</span>
                                <span className="wizard-total-value highlight">{affluenza}%</span>
                            </div>
                        )}
                    </div>
                </div>
            );
        }

        // Steps 1..N: Schede
        const schedaIndex = currentStep - 1;
        const scheda = schede[schedaIndex];
        const data = schedeData[scheda.id];
        const isReferendum = scheda.schema?.tipo === 'si_no';

        return (
            <div className="wizard-card">
                {/* Color bar */}
                {scheda.colore && (
                    <div
                        className="scheda-color-bar"
                        style={{ background: scheda.colore }}
                    ></div>
                )}

                <div className="wizard-card-title">
                    <i className="fas fa-file-alt"></i>
                    {scheda.nome}
                </div>
                {scheda.testo_quesito && (
                    <div className="wizard-card-subtitle" style={{ fontStyle: 'italic' }}>
                        {scheda.testo_quesito.length > 120
                            ? scheda.testo_quesito.substring(0, 120) + '...'
                            : scheda.testo_quesito}
                    </div>
                )}

                {/* Voti Referendum - mostrati prima */}
                {isReferendum && (
                    <div className="wizard-field-group">
                        <span className="wizard-field-label">Voti Espressi</span>
                        <div className="referendum-votes">
                            <div className="referendum-vote-card si">
                                <div className="referendum-vote-label si">SÌ</div>
                                <input
                                    type="number"
                                    inputMode="numeric"
                                    className="referendum-vote-input"
                                    value={data.voti?.si ?? ''}
                                    onChange={(e) => handleVotiChange(scheda.id, 'si', e.target.value)}
                                    placeholder="0"
                                />
                            </div>
                            <div className="referendum-vote-card no">
                                <div className="referendum-vote-label no">NO</div>
                                <input
                                    type="number"
                                    inputMode="numeric"
                                    className="referendum-vote-input"
                                    value={data.voti?.no ?? ''}
                                    onChange={(e) => handleVotiChange(scheda.id, 'no', e.target.value)}
                                    placeholder="0"
                                />
                            </div>
                        </div>
                    </div>
                )}

                {/* Schede speciali */}
                <div className="wizard-field-group">
                    <span className="wizard-field-label">Schede non valide</span>
                    <div className="wizard-field-row">
                        <div className="wizard-field-col">
                            <label>Bianche</label>
                            <input
                                type="number"
                                inputMode="numeric"
                                className="wizard-input"
                                value={data.schede_bianche}
                                onChange={(e) => handleSchedaChange(scheda.id, 'schede_bianche', e.target.value)}
                                placeholder="0"
                            />
                        </div>
                        <div className="wizard-field-col">
                            <label>Nulle</label>
                            <input
                                type="number"
                                inputMode="numeric"
                                className="wizard-input"
                                value={data.schede_nulle}
                                onChange={(e) => handleSchedaChange(scheda.id, 'schede_nulle', e.target.value)}
                                placeholder="0"
                            />
                        </div>
                        <div className="wizard-field-col">
                            <label>Contestate</label>
                            <input
                                type="number"
                                inputMode="numeric"
                                className="wizard-input"
                                value={data.schede_contestate}
                                onChange={(e) => handleSchedaChange(scheda.id, 'schede_contestate', e.target.value)}
                                placeholder="0"
                            />
                        </div>
                    </div>
                </div>

                {/* Schede consegnate */}
                <div className="wizard-field-group">
                    <span className="wizard-field-label">Schede</span>
                    <div className="wizard-field-row">
                        <div className="wizard-field-col">
                            <label>Ricevute</label>
                            <input
                                type="number"
                                inputMode="numeric"
                                className="wizard-input"
                                value={data.schede_ricevute}
                                onChange={(e) => handleSchedaChange(scheda.id, 'schede_ricevute', e.target.value)}
                                placeholder="0"
                            />
                        </div>
                        <div className="wizard-field-col">
                            <label>Autenticate</label>
                            <input
                                type="number"
                                inputMode="numeric"
                                className="wizard-input"
                                value={data.schede_autenticate}
                                onChange={(e) => handleSchedaChange(scheda.id, 'schede_autenticate', e.target.value)}
                                placeholder="0"
                            />
                        </div>
                    </div>
                </div>
            </div>
        );
    };

    // Calculate sheet transform
    const sheetTransform = isDragging ? `translateY(${dragOffset}px)` : undefined;

    return (
        <>
            <style>{wizardStyles}</style>

            {/* Overlay backdrop - click to close */}
            <div
                className={`wizard-overlay ${isClosing ? 'closing' : ''}`}
                onClick={handleExit}
            />

            {/* Sheet container */}
            <div
                ref={sheetRef}
                className={`wizard-sheet ${isClosing ? 'closing' : ''} ${isDragging ? 'dragging' : ''}`}
                style={isDragging ? { transform: sheetTransform } : undefined}
            >
                <div className="wizard-container">
                    {/* Drag handle for swipe-to-dismiss */}
                    <div className="wizard-drag-handle" ref={dragHandleRef}>
                        <div className="wizard-drag-bar"></div>
                    </div>

                    {/* Saving indicator */}
                    {showSaved && (
                        <div className="saving-indicator">
                            <i className="fas fa-check me-2"></i>
                            Salvato
                        </div>
                    )}

                    {/* Header */}
                    <div className="wizard-header">
                        <div className="wizard-header-top">
                            <button className="wizard-header-back" onClick={handleExit}>
                                <i className="fas fa-arrow-left"></i>
                            </button>
                            <div className="wizard-header-title">
                                <div className="wizard-header-sezione">Sezione {section.sezione}</div>
                                <div className="wizard-header-comune">{section.comune}</div>
                            </div>
                            <div style={{ width: 40 }}></div>
                        </div>

                        {/* Step tabs */}
                        <div className="wizard-tabs">
                            <button
                                className={`wizard-tab ${currentStep === 0 ? 'active' : ''} ${isStepComplete(0) ? 'complete' : ''}`}
                                onClick={() => goToStep(0)}
                            >
                                {isStepComplete(0) && <i className="fas fa-check wizard-tab-check"></i>}
                                Seggio
                            </button>
                            {schede.map((scheda, index) => (
                                <button
                                    key={scheda.id}
                                    className={`wizard-tab ${currentStep === index + 1 ? 'active' : ''} ${isStepComplete(index + 1) ? 'complete' : ''}`}
                                    onClick={() => goToStep(index + 1)}
                                >
                                    {isStepComplete(index + 1) ? (
                                        <i className="fas fa-check wizard-tab-check"></i>
                                    ) : scheda.colore ? (
                                        <span className="wizard-tab-dot" style={{ background: scheda.colore }}></span>
                                    ) : null}
                                    {scheda.nome?.length > 12 ? scheda.nome.substring(0, 12) + '…' : scheda.nome}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Scrollable content */}
                    <div className="wizard-scroll">
                        <div className="wizard-content">
                            {renderStepContent()}
                        </div>
                    </div>

                    {/* Bottom navigation - Mobile optimized */}
                    <div className="wizard-nav">
                        {/* Step indicator pill */}
                        <div className="wizard-nav-indicator">
                            {currentStep + 1} / {totalSteps}
                        </div>

                        {/* Back button */}
                        <button
                            className="wizard-nav-btn secondary"
                            onClick={currentStep === 0 ? handleExit : goPrev}
                        >
                            <i className="fas fa-chevron-left"></i>
                            {currentStep === 0 ? 'Esci' : 'Indietro'}
                        </button>

                        {/* Forward button - changes based on position */}
                        {currentStep === totalSteps - 1 ? (
                            <button
                                className="wizard-nav-btn success"
                                onClick={handleExit}
                            >
                                <i className="fas fa-check"></i>
                                Fatto
                            </button>
                        ) : (
                            <button
                                className="wizard-nav-btn primary"
                                onClick={goNext}
                            >
                                Avanti
                                <i className="fas fa-chevron-right"></i>
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </>
    );
}

export default SectionForm;
