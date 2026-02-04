import React, {useEffect, useState} from "react";
import '@fortawesome/fontawesome-free/css/all.min.css';

// Stili per il wizard mobile-first
const wizardStyles = `
    .wizard-container {
        min-height: 100vh;
        padding-bottom: 100px;
        background: #f5f5f5;
    }

    .wizard-header {
        position: sticky;
        top: 0;
        z-index: 100;
        background: linear-gradient(135deg, #0d6efd 0%, #0a58ca 100%);
        color: white;
        padding: 12px 16px;
        margin: -1rem -1rem 0 -1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }

    .wizard-header-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
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

    /* Step indicator */
    .wizard-steps {
        display: flex;
        justify-content: center;
        gap: 8px;
        padding: 8px 0;
    }

    .wizard-step {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: rgba(255,255,255,0.3);
        transition: all 0.3s;
    }

    .wizard-step.active {
        background: white;
        transform: scale(1.2);
    }

    .wizard-step.completed {
        background: rgba(255,255,255,0.8);
    }

    .wizard-step-label {
        font-size: 0.75rem;
        opacity: 0.9;
        text-align: center;
        margin-top: 4px;
    }

    /* Content area */
    .wizard-content {
        padding: 16px;
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

    .wizard-input.error {
        border-color: #dc3545;
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

    /* Bottom navigation */
    .wizard-nav {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: white;
        padding: 12px 16px;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
        display: flex;
        gap: 12px;
        z-index: 100;
    }

    .wizard-nav-btn {
        flex: 1;
        padding: 14px 20px;
        border-radius: 12px;
        font-size: 1rem;
        font-weight: 600;
        border: none;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        transition: all 0.2s;
    }

    .wizard-nav-btn.secondary {
        background: #f0f0f0;
        color: #333;
    }

    .wizard-nav-btn.primary {
        background: #0d6efd;
        color: white;
    }

    .wizard-nav-btn.success {
        background: #198754;
        color: white;
    }

    .wizard-nav-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    /* Summary */
    .summary-section {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
    }

    .summary-section-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: #666;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .summary-row {
        display: flex;
        justify-content: space-between;
        padding: 6px 0;
        border-bottom: 1px solid #e9ecef;
    }

    .summary-row:last-child {
        border-bottom: none;
    }

    .summary-label {
        color: #666;
        font-size: 0.9rem;
    }

    .summary-value {
        font-weight: 600;
        color: #333;
    }

    .summary-value.si { color: #198754; }
    .summary-value.no { color: #dc3545; }

    /* Error message */
    .wizard-error {
        background: #f8d7da;
        color: #721c24;
        padding: 10px 14px;
        border-radius: 8px;
        font-size: 0.85rem;
        margin-bottom: 12px;
    }
`;

function SectionForm({schede, section, sectionData, updateSection, cancel}) {
    // Steps: 0 = Dati Seggio, 1..N = Schede, N+1 = Riepilogo
    const totalSteps = schede.length + 2; // seggio + N schede + riepilogo
    const [currentStep, setCurrentStep] = useState(0);
    const [isSaving, setIsSaving] = useState(false);

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

    useEffect(() => {
        window.scrollTo(0, 0);
    }, [currentStep]);

    // Handle back button
    useEffect(() => {
        window.history.pushState(null, null, window.location.pathname);
        const onPopState = () => {
            if (currentStep > 0) {
                setCurrentStep(currentStep - 1);
                window.history.pushState(null, null, window.location.pathname);
            } else {
                cancel();
            }
        };
        window.addEventListener('popstate', onPopState);
        return () => window.removeEventListener('popstate', onPopState);
    }, [currentStep, cancel]);

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

    // Calculate totals
    const totalElettori = (+datiSeggio.elettori_maschi || 0) + (+datiSeggio.elettori_femmine || 0);
    const totalVotanti = (+datiSeggio.votanti_maschi || 0) + (+datiSeggio.votanti_femmine || 0);
    const affluenza = totalElettori > 0 ? ((totalVotanti / totalElettori) * 100).toFixed(1) : 0;

    const handleSeggioChange = (field, value) => {
        const numValue = value === '' ? '' : Math.max(0, parseInt(value) || 0);
        setDatiSeggio(prev => ({ ...prev, [field]: numValue }));
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
    };

    const goNext = () => {
        if (currentStep < totalSteps - 1) {
            setCurrentStep(currentStep + 1);
        }
    };

    const goPrev = () => {
        if (currentStep > 0) {
            setCurrentStep(currentStep - 1);
        } else {
            cancel();
        }
    };

    const handleSave = async () => {
        if (isSaving) return;
        setIsSaving(true);

        // Build payload
        const payload = {
            comune: section.comune,
            sezione: section.sezione,
            dati_seggio: {
                elettori_maschi: datiSeggio.elettori_maschi === '' ? null : datiSeggio.elettori_maschi,
                elettori_femmine: datiSeggio.elettori_femmine === '' ? null : datiSeggio.elettori_femmine,
                votanti_maschi: datiSeggio.votanti_maschi === '' ? null : datiSeggio.votanti_maschi,
                votanti_femmine: datiSeggio.votanti_femmine === '' ? null : datiSeggio.votanti_femmine,
            },
            schede: {},
        };

        // Add each scheda
        schede.forEach(scheda => {
            const data = schedeData[scheda.id];
            payload.schede[scheda.id] = {
                schede_ricevute: data.schede_ricevute === '' ? null : data.schede_ricevute,
                schede_autenticate: data.schede_autenticate === '' ? null : data.schede_autenticate,
                schede_bianche: data.schede_bianche === '' ? null : data.schede_bianche,
                schede_nulle: data.schede_nulle === '' ? null : data.schede_nulle,
                schede_contestate: data.schede_contestate === '' ? null : data.schede_contestate,
                voti: data.voti,
            };
        });

        await updateSection(payload);
        setIsSaving(false);
    };

    // Get step name for indicator
    const getStepName = (index) => {
        if (index === 0) return 'Seggio';
        if (index === totalSteps - 1) return 'Invio';
        return `Scheda ${index}`;
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
                        Inserisci i dati relativi agli elettori e ai votanti
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
                        <div className="wizard-total" style={{ marginTop: 8 }}>
                            <span className="wizard-total-label">Affluenza</span>
                            <span className="wizard-total-value highlight">{affluenza}%</span>
                        </div>
                    </div>
                </div>
            );
        }

        // Last step: Riepilogo
        if (currentStep === totalSteps - 1) {
            return (
                <div className="wizard-card">
                    <div className="wizard-card-title">
                        <i className="fas fa-clipboard-check"></i>
                        Riepilogo Dati
                    </div>
                    <div className="wizard-card-subtitle">
                        Verifica i dati prima dell'invio
                    </div>

                    {/* Dati Seggio Summary */}
                    <div className="summary-section">
                        <div className="summary-section-title">
                            <i className="fas fa-users"></i>
                            Dati Seggio
                        </div>
                        <div className="summary-row">
                            <span className="summary-label">Elettori</span>
                            <span className="summary-value">
                                {datiSeggio.elettori_maschi || 0} M + {datiSeggio.elettori_femmine || 0} F = {totalElettori}
                            </span>
                        </div>
                        <div className="summary-row">
                            <span className="summary-label">Votanti</span>
                            <span className="summary-value">
                                {datiSeggio.votanti_maschi || 0} M + {datiSeggio.votanti_femmine || 0} F = {totalVotanti}
                            </span>
                        </div>
                        <div className="summary-row">
                            <span className="summary-label">Affluenza</span>
                            <span className="summary-value">{affluenza}%</span>
                        </div>
                    </div>

                    {/* Schede Summary */}
                    {schede.map(scheda => {
                        const data = schedeData[scheda.id];
                        const isReferendum = scheda.schema?.tipo === 'si_no';
                        const votiSi = data.voti?.si || 0;
                        const votiNo = data.voti?.no || 0;

                        return (
                            <div key={scheda.id} className="summary-section">
                                <div className="summary-section-title">
                                    <span
                                        style={{
                                            width: 12,
                                            height: 12,
                                            borderRadius: 3,
                                            background: scheda.colore || '#ccc',
                                            display: 'inline-block'
                                        }}
                                    ></span>
                                    {scheda.nome}
                                </div>
                                <div className="summary-row">
                                    <span className="summary-label">Schede ricevute</span>
                                    <span className="summary-value">{data.schede_ricevute || '-'}</span>
                                </div>
                                <div className="summary-row">
                                    <span className="summary-label">Schede autenticate</span>
                                    <span className="summary-value">{data.schede_autenticate || '-'}</span>
                                </div>
                                {isReferendum && (
                                    <>
                                        <div className="summary-row">
                                            <span className="summary-label">Voti SI</span>
                                            <span className="summary-value si">{votiSi || '-'}</span>
                                        </div>
                                        <div className="summary-row">
                                            <span className="summary-label">Voti NO</span>
                                            <span className="summary-value no">{votiNo || '-'}</span>
                                        </div>
                                    </>
                                )}
                                <div className="summary-row">
                                    <span className="summary-label">Bianche / Nulle / Contestate</span>
                                    <span className="summary-value">
                                        {data.schede_bianche || 0} / {data.schede_nulle || 0} / {data.schede_contestate || 0}
                                    </span>
                                </div>
                            </div>
                        );
                    })}
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
                        {scheda.testo_quesito.length > 150
                            ? scheda.testo_quesito.substring(0, 150) + '...'
                            : scheda.testo_quesito}
                    </div>
                )}

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

                {/* Voti Referendum */}
                {isReferendum && (
                    <div className="wizard-field-group">
                        <span className="wizard-field-label">Voti Espressi</span>
                        <div className="referendum-votes">
                            <div className="referendum-vote-card si">
                                <div className="referendum-vote-label si">SI</div>
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
                        <div className="wizard-total" style={{ marginTop: 12 }}>
                            <span className="wizard-total-label">Totale Voti Validi</span>
                            <span className="wizard-total-value">
                                {(+data.voti?.si || 0) + (+data.voti?.no || 0)}
                            </span>
                        </div>
                    </div>
                )}

                {/* Schede speciali */}
                <div className="wizard-field-group">
                    <span className="wizard-field-label">Schede Speciali</span>
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
            </div>
        );
    };

    return (
        <>
            <style>{wizardStyles}</style>
            <div className="wizard-container">
                {/* Header */}
                <div className="wizard-header">
                    <div className="wizard-header-top">
                        <button className="wizard-header-back" onClick={goPrev}>
                            <i className="fas fa-arrow-left"></i>
                        </button>
                        <div className="wizard-header-title">
                            <div className="wizard-header-sezione">Sezione {section.sezione}</div>
                            <div className="wizard-header-comune">{section.comune}</div>
                        </div>
                        <div style={{ width: 40 }}></div>
                    </div>

                    {/* Step indicators */}
                    <div className="wizard-steps">
                        {Array.from({ length: totalSteps }).map((_, index) => (
                            <div
                                key={index}
                                className={`wizard-step ${
                                    index === currentStep ? 'active' :
                                    index < currentStep ? 'completed' : ''
                                }`}
                            ></div>
                        ))}
                    </div>
                    <div className="wizard-step-label">
                        {getStepName(currentStep)} ({currentStep + 1}/{totalSteps})
                    </div>
                </div>

                {/* Content */}
                <div className="wizard-content">
                    {renderStepContent()}
                </div>

                {/* Bottom navigation */}
                <div className="wizard-nav">
                    <button
                        className="wizard-nav-btn secondary"
                        onClick={goPrev}
                    >
                        <i className="fas fa-chevron-left"></i>
                        {currentStep === 0 ? 'Esci' : 'Indietro'}
                    </button>

                    {currentStep === totalSteps - 1 ? (
                        <button
                            className="wizard-nav-btn success"
                            onClick={handleSave}
                            disabled={isSaving}
                        >
                            {isSaving ? (
                                <>
                                    <span className="spinner-border spinner-border-sm"></span>
                                    Invio...
                                </>
                            ) : (
                                <>
                                    <i className="fas fa-paper-plane"></i>
                                    Invia Dati
                                </>
                            )}
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
        </>
    );
}

export default SectionForm;
