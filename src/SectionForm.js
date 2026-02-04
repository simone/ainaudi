import React, {useEffect, useState} from "react";
import '@fortawesome/fontawesome-free/css/all.min.css';

// Stili per il form mobile-first
const formStyles = `
    .scrutinio-container {
        padding-bottom: 80px; /* Spazio per bottom bar */
    }

    .scrutinio-header {
        position: sticky;
        top: 0;
        z-index: 100;
        background: linear-gradient(135deg, #0d6efd 0%, #0a58ca 100%);
        color: white;
        padding: 12px 16px;
        margin: -1rem -1rem 16px -1rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }

    .scrutinio-header-info {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .scrutinio-header-sezione {
        font-size: 1.25rem;
        font-weight: 700;
    }

    .scrutinio-header-comune {
        font-size: 0.85rem;
        opacity: 0.9;
    }

    .scrutinio-header-back {
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

    .scrutinio-header-back:hover {
        background: rgba(255,255,255,0.3);
    }

    .scrutinio-section {
        background: white;
        border-radius: 12px;
        margin-bottom: 12px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }

    .scrutinio-section-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 16px;
        background: #f8f9fa;
        cursor: pointer;
        user-select: none;
        border-bottom: 1px solid #eee;
    }

    .scrutinio-section-header:hover {
        background: #f0f1f2;
    }

    .scrutinio-section-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 600;
        font-size: 0.9rem;
        color: #333;
    }

    .scrutinio-section-badge {
        background: #e9ecef;
        color: #495057;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 500;
    }

    .scrutinio-section-badge.complete {
        background: #d1e7dd;
        color: #0f5132;
    }

    .scrutinio-section-content {
        padding: 16px;
    }

    .scrutinio-row {
        display: flex;
        gap: 12px;
        margin-bottom: 12px;
    }

    .scrutinio-field {
        flex: 1;
    }

    .scrutinio-field.full {
        flex: none;
        width: 100%;
    }

    .scrutinio-label {
        font-size: 0.8rem;
        color: #666;
        margin-bottom: 4px;
        display: block;
    }

    .scrutinio-input {
        width: 100%;
        padding: 10px 12px;
        font-size: 1.1rem;
        font-weight: 500;
        border: 2px solid #e0e0e0;
        border-radius: 8px;
        text-align: center;
        transition: border-color 0.2s, box-shadow 0.2s;
    }

    .scrutinio-input:focus {
        outline: none;
        border-color: #0d6efd;
        box-shadow: 0 0 0 3px rgba(13, 110, 253, 0.15);
    }

    .scrutinio-input.has-error {
        border-color: #dc3545;
    }

    .scrutinio-input:read-only {
        background: #f8f9fa;
        border-color: transparent;
        color: #495057;
    }

    .scrutinio-total {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: #f8f9fa;
        padding: 8px 12px;
        border-radius: 8px;
        margin-top: 8px;
    }

    .scrutinio-total-label {
        font-size: 0.8rem;
        color: #666;
    }

    .scrutinio-total-value {
        font-size: 1.1rem;
        font-weight: 700;
        color: #0d6efd;
    }

    .scrutinio-error {
        font-size: 0.75rem;
        color: #dc3545;
        margin-top: 4px;
        padding: 4px 8px;
        background: #fff5f5;
        border-radius: 4px;
    }

    .scrutinio-list-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 0;
        border-bottom: 1px solid #f0f0f0;
    }

    .scrutinio-list-item:last-child {
        border-bottom: none;
    }

    .scrutinio-list-label {
        flex: 1;
        font-size: 0.85rem;
        color: #333;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .scrutinio-list-label.highlight {
        color: #0d6efd;
        font-weight: 600;
    }

    .scrutinio-list-input {
        width: 80px;
        padding: 8px;
        font-size: 1rem;
        font-weight: 600;
        border: 2px solid #e0e0e0;
        border-radius: 8px;
        text-align: center;
    }

    .scrutinio-list-input:focus {
        outline: none;
        border-color: #0d6efd;
    }

    .scrutinio-bottom-bar {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: white;
        padding: 12px 16px;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
        z-index: 200;
        display: flex;
        gap: 12px;
    }

    .scrutinio-btn {
        flex: 1;
        padding: 14px 20px;
        border: none;
        border-radius: 10px;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        transition: transform 0.1s, opacity 0.2s;
    }

    .scrutinio-btn:active {
        transform: scale(0.98);
    }

    .scrutinio-btn:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }

    .scrutinio-btn-secondary {
        background: #f0f0f0;
        color: #333;
    }

    .scrutinio-btn-primary {
        background: #198754;
        color: white;
    }

    .scrutinio-warnings {
        background: #fff3cd;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
    }

    .scrutinio-warnings-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: #856404;
        margin-bottom: 8px;
    }

    .scrutinio-warnings-list {
        font-size: 0.8rem;
        color: #856404;
        margin: 0;
        padding-left: 16px;
    }

    .scrutinio-warnings-list li {
        margin-bottom: 4px;
    }

    /* Referendum specific */
    .referendum-btn {
        flex: 1;
        padding: 20px;
        border: 3px solid #e0e0e0;
        border-radius: 12px;
        background: white;
        cursor: pointer;
        transition: all 0.2s;
    }

    .referendum-btn.active {
        border-color: #0d6efd;
        background: #f0f7ff;
    }

    .referendum-btn-label {
        font-size: 1.5rem;
        font-weight: 700;
        display: block;
        margin-bottom: 4px;
    }

    .referendum-btn-label.si { color: #198754; }
    .referendum-btn-label.no { color: #dc3545; }

    .referendum-input {
        width: 100%;
        padding: 8px;
        font-size: 1.25rem;
        font-weight: 700;
        border: none;
        background: transparent;
        text-align: center;
    }

    .referendum-input:focus {
        outline: none;
    }
`;

function SectionForm({lists, candidates, section, updateSection, cancel}) {
    const initialState = {...section, ...
            {
                totalElettori: +section.nElettoriMaschi + +section.nElettoriDonne,
                totalVotanti: +section.nVotantiMaschi + +section.nVotantiDonne,
                totalVotiDiLista: lists.reduce((sum, name) => sum + (parseInt(section[name]) || 0), 0),
                totalVotiDiPreferenza: candidates.reduce((sum, name) => sum + (parseInt(section[name]) || 0), 0),
            }
    };
    const [formData, setFormData] = useState(initialState);
    const [errors, setErrors] = useState({});
    const [isSaving, setIsSaving] = useState(false);
    const [expandedSections, setExpandedSections] = useState({
        preparazione: true,
        votanti: false,
        referendum: false,
        preferenze: false,
        liste: false,
        schede: false,
    });

    const validation = (field, value) => {
        let error = '';
        switch (field) {
            case "schedeRicevute":
                if (value && +value < +formData.totalElettori) {
                    error = 'Schede ricevute < elettori';
                }
                break;
            case "schedeAutenticate":
                if (value && +value > +formData.schedeRicevute) {
                    error = 'Autenticate > ricevute';
                }
                if (value && +value > +formData.totalElettori) {
                    error = 'Autenticate > elettori';
                }
                break;
            case "schedeContestate":
                const schedeBianche = parseInt(formData.schedeBianche) || 0;
                const schedeNulle = parseInt(formData.schedeNulle) || 0;
                const schedeContestate = parseInt(formData.schedeContestate) || 0;
                const totalSchede = schedeBianche + schedeNulle + schedeContestate + formData.totalVotiDiLista;
                if (totalSchede > +formData.totalVotanti) {
                    error = 'Totale schede > votanti';
                }
                if (totalSchede < +formData.totalVotanti && formData.totalVotanti > 0) {
                    error = 'Totale schede < votanti';
                }
                break;
            case "totalVotiDiLista":
                if (value > 0 && +value > +formData.totalVotanti) {
                    error = 'Voti lista > votanti';
                }
                break;
            case "totalVotiDiPreferenza":
                if (value > 0 && +value > +formData.totalVotanti * 3) {
                    error = 'Preferenze > 3x votanti';
                }
                break;
            case "totalVotanti":
                if (value > 0 && +value > +formData.totalElettori) {
                    error = 'Votanti > elettori';
                }
                break;
            default:
                break;
        }
        return error;
    };

    useEffect(() => {
        window.scrollTo(0, 0);
        const handleWheel = (e) => {
            if (document.activeElement.type === "number" && document.activeElement === e.target) {
                e.preventDefault();
            }
        };
        window.addEventListener('wheel', handleWheel, { passive: false });
        return () => window.removeEventListener('wheel', handleWheel);
    }, []);

    useEffect(() => {
        const newErrors = {};
        for (const key in formData) {
            newErrors[key] = validation(key, formData[key]);
        }
        setErrors(newErrors);
    }, [formData]);

    const handleChange = (e, field) => {
        let value = e.target.value;
        if (value !== "") {
            if (value < 0) value = 0;
            value = parseInt(value, 10);
        }
        const newFormData = {
            ...formData,
            [field]: value && parseInt(value, 10) >= 0 ? parseInt(value, 10) : ''
        };

        newFormData.totalElettori = +newFormData.nElettoriMaschi + +newFormData.nElettoriDonne;
        newFormData.totalVotanti = +newFormData.nVotantiMaschi + +newFormData.nVotantiDonne;
        newFormData.totalVotiDiLista = lists.reduce((sum, name) => sum + (parseInt(newFormData[name]) || 0), 0);
        newFormData.totalVotiDiPreferenza = candidates.reduce((sum, name) => sum + (parseInt(newFormData[name]) || 0), 0);

        setFormData(newFormData);
    };

    const handleSave = () => {
        if (isSaving) return;
        setIsSaving(true);
        if (Object.values(formData).every(value => value === '')) {
            cancel();
            return;
        }
        updateSection(formData, errorsList);
    };

    useEffect(() => {
        window.history.pushState(null, null, window.location.pathname);
        const onPopState = () => cancel();
        window.addEventListener('popstate', onPopState);
        return () => window.removeEventListener('popstate', onPopState);
    }, []);

    const toggleSection = (sectionName) => {
        setExpandedSections(prev => ({
            ...prev,
            [sectionName]: !prev[sectionName]
        }));
    };

    const errorsList = Object.values(errors).filter(value => value !== '');

    // Check section completion
    const isPreparazioneComplete = formData.nElettoriMaschi !== '' && formData.nElettoriDonne !== ''
        && formData.schedeRicevute !== '' && formData.schedeAutenticate !== '';
    const isVotantiComplete = formData.nVotantiMaschi !== '' && formData.nVotantiDonne !== '';
    const isSchedeComplete = formData.schedeBianche !== '' && formData.schedeNulle !== ''
        && formData.schedeContestate !== '';

    const isReferendum = lists.length === 0 && candidates.length === 0;

    return (
        <>
            <style>{formStyles}</style>
            <div className="scrutinio-container">
                {/* Sticky Header */}
                <div className="scrutinio-header">
                    <button className="scrutinio-header-back" onClick={cancel}>
                        <i className="fas fa-arrow-left"></i>
                    </button>
                    <div className="scrutinio-header-info">
                        <div>
                            <div className="scrutinio-header-sezione">Sezione {formData.sezione}</div>
                            <div className="scrutinio-header-comune">{formData.comune}</div>
                        </div>
                    </div>
                    <div style={{ width: 40 }}></div> {/* Spacer for centering */}
                </div>

                {/* Warnings */}
                {errorsList.length > 0 && (
                    <div className="scrutinio-warnings">
                        <div className="scrutinio-warnings-title">
                            <i className="fas fa-exclamation-triangle me-1"></i>
                            Verificare i dati
                        </div>
                        <ul className="scrutinio-warnings-list">
                            {errorsList.map((error, i) => <li key={i}>{error}</li>)}
                        </ul>
                    </div>
                )}

                {/* 1. Preparazione Seggio */}
                <div className="scrutinio-section">
                    <div
                        className="scrutinio-section-header"
                        onClick={() => toggleSection('preparazione')}
                    >
                        <div className="scrutinio-section-title">
                            <i className="fas fa-clipboard-list"></i>
                            Preparazione Seggio
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            {isPreparazioneComplete && (
                                <span className="scrutinio-section-badge complete">
                                    <i className="fas fa-check me-1"></i>OK
                                </span>
                            )}
                            <i className={`fas fa-chevron-${expandedSections.preparazione ? 'up' : 'down'}`}></i>
                        </div>
                    </div>
                    {expandedSections.preparazione && (
                        <div className="scrutinio-section-content">
                            <div className="scrutinio-row">
                                <div className="scrutinio-field">
                                    <label className="scrutinio-label">Elettori M</label>
                                    <input
                                        type="number"
                                        className={`scrutinio-input ${errors.nElettoriMaschi ? 'has-error' : ''}`}
                                        value={formData.nElettoriMaschi}
                                        onChange={(e) => handleChange(e, "nElettoriMaschi")}
                                        inputMode="numeric"
                                    />
                                </div>
                                <div className="scrutinio-field">
                                    <label className="scrutinio-label">Elettori F</label>
                                    <input
                                        type="number"
                                        className={`scrutinio-input ${errors.nElettoriDonne ? 'has-error' : ''}`}
                                        value={formData.nElettoriDonne}
                                        onChange={(e) => handleChange(e, "nElettoriDonne")}
                                        inputMode="numeric"
                                    />
                                </div>
                            </div>
                            <div className="scrutinio-total">
                                <span className="scrutinio-total-label">Totale Elettori</span>
                                <span className="scrutinio-total-value">{formData.totalElettori || 0}</span>
                            </div>

                            <div className="scrutinio-row" style={{ marginTop: 16 }}>
                                <div className="scrutinio-field">
                                    <label className="scrutinio-label">Schede Ricevute</label>
                                    <input
                                        type="number"
                                        className={`scrutinio-input ${errors.schedeRicevute ? 'has-error' : ''}`}
                                        value={formData.schedeRicevute}
                                        onChange={(e) => handleChange(e, "schedeRicevute")}
                                        inputMode="numeric"
                                    />
                                    {errors.schedeRicevute && (
                                        <div className="scrutinio-error">{errors.schedeRicevute}</div>
                                    )}
                                </div>
                                <div className="scrutinio-field">
                                    <label className="scrutinio-label">Schede Autenticate</label>
                                    <input
                                        type="number"
                                        className={`scrutinio-input ${errors.schedeAutenticate ? 'has-error' : ''}`}
                                        value={formData.schedeAutenticate}
                                        onChange={(e) => handleChange(e, "schedeAutenticate")}
                                        inputMode="numeric"
                                    />
                                    {errors.schedeAutenticate && (
                                        <div className="scrutinio-error">{errors.schedeAutenticate}</div>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* 2. Votanti */}
                <div className="scrutinio-section">
                    <div
                        className="scrutinio-section-header"
                        onClick={() => toggleSection('votanti')}
                    >
                        <div className="scrutinio-section-title">
                            <i className="fas fa-users"></i>
                            Affluenza
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            {isVotantiComplete && (
                                <span className="scrutinio-section-badge complete">
                                    <i className="fas fa-check me-1"></i>OK
                                </span>
                            )}
                            <i className={`fas fa-chevron-${expandedSections.votanti ? 'up' : 'down'}`}></i>
                        </div>
                    </div>
                    {expandedSections.votanti && (
                        <div className="scrutinio-section-content">
                            <div className="scrutinio-row">
                                <div className="scrutinio-field">
                                    <label className="scrutinio-label">Votanti M</label>
                                    <input
                                        type="number"
                                        className={`scrutinio-input ${errors.nVotantiMaschi ? 'has-error' : ''}`}
                                        value={formData.nVotantiMaschi}
                                        onChange={(e) => handleChange(e, "nVotantiMaschi")}
                                        inputMode="numeric"
                                    />
                                </div>
                                <div className="scrutinio-field">
                                    <label className="scrutinio-label">Votanti F</label>
                                    <input
                                        type="number"
                                        className={`scrutinio-input ${errors.nVotantiDonne ? 'has-error' : ''}`}
                                        value={formData.nVotantiDonne}
                                        onChange={(e) => handleChange(e, "nVotantiDonne")}
                                        inputMode="numeric"
                                    />
                                </div>
                            </div>
                            <div className="scrutinio-total">
                                <span className="scrutinio-total-label">Totale Votanti</span>
                                <span className="scrutinio-total-value">
                                    {formData.totalVotanti || 0}
                                    {formData.totalElettori > 0 && (
                                        <span style={{ fontSize: '0.8rem', fontWeight: 400, marginLeft: 8, color: '#666' }}>
                                            ({Math.round((formData.totalVotanti / formData.totalElettori) * 100)}%)
                                        </span>
                                    )}
                                </span>
                            </div>
                            {errors.totalVotanti && (
                                <div className="scrutinio-error">{errors.totalVotanti}</div>
                            )}
                        </div>
                    )}
                </div>

                {/* 3. Voti Referendum (if applicable) */}
                {isReferendum && (
                    <div className="scrutinio-section">
                        <div
                            className="scrutinio-section-header"
                            onClick={() => toggleSection('referendum')}
                        >
                            <div className="scrutinio-section-title">
                                <i className="fas fa-vote-yea"></i>
                                Voti Referendum
                            </div>
                            <i className={`fas fa-chevron-${expandedSections.referendum ? 'up' : 'down'}`}></i>
                        </div>
                        {expandedSections.referendum && (
                            <div className="scrutinio-section-content">
                                <div className="scrutinio-row">
                                    <div className="referendum-btn">
                                        <span className="referendum-btn-label si">SÌ</span>
                                        <input
                                            type="number"
                                            className="referendum-input"
                                            value={formData.votiSi || ''}
                                            onChange={(e) => handleChange(e, "votiSi")}
                                            inputMode="numeric"
                                            placeholder="0"
                                        />
                                    </div>
                                    <div className="referendum-btn">
                                        <span className="referendum-btn-label no">NO</span>
                                        <input
                                            type="number"
                                            className="referendum-input"
                                            value={formData.votiNo || ''}
                                            onChange={(e) => handleChange(e, "votiNo")}
                                            inputMode="numeric"
                                            placeholder="0"
                                        />
                                    </div>
                                </div>
                                <div className="scrutinio-total">
                                    <span className="scrutinio-total-label">Totale Voti Validi</span>
                                    <span className="scrutinio-total-value">
                                        {(parseInt(formData.votiSi) || 0) + (parseInt(formData.votiNo) || 0)}
                                    </span>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* 4. Preferenze (if applicable) */}
                {candidates.length > 0 && (
                    <div className="scrutinio-section">
                        <div
                            className="scrutinio-section-header"
                            onClick={() => toggleSection('preferenze')}
                        >
                            <div className="scrutinio-section-title">
                                <i className="fas fa-user-check"></i>
                                Preferenze
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <span className="scrutinio-section-badge">
                                    Tot: {formData.totalVotiDiPreferenza || 0}
                                </span>
                                <i className={`fas fa-chevron-${expandedSections.preferenze ? 'up' : 'down'}`}></i>
                            </div>
                        </div>
                        {expandedSections.preferenze && (
                            <div className="scrutinio-section-content">
                                {candidates.map((name) => (
                                    <div className="scrutinio-list-item" key={name}>
                                        <span className="scrutinio-list-label">{name}</span>
                                        <input
                                            type="number"
                                            className="scrutinio-list-input"
                                            value={formData[name]}
                                            onChange={(e) => handleChange(e, name)}
                                            inputMode="numeric"
                                            min="0"
                                        />
                                    </div>
                                ))}
                                <div className="scrutinio-total">
                                    <span className="scrutinio-total-label">Totale Preferenze</span>
                                    <span className="scrutinio-total-value">{formData.totalVotiDiPreferenza || 0}</span>
                                </div>
                                {errors.totalVotiDiPreferenza && (
                                    <div className="scrutinio-error">{errors.totalVotiDiPreferenza}</div>
                                )}
                            </div>
                        )}
                    </div>
                )}

                {/* 5. Voti di Lista (if applicable) */}
                {lists.length > 0 && (
                    <div className="scrutinio-section">
                        <div
                            className="scrutinio-section-header"
                            onClick={() => toggleSection('liste')}
                        >
                            <div className="scrutinio-section-title">
                                <i className="fas fa-list-ol"></i>
                                Voti di Lista
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <span className="scrutinio-section-badge">
                                    Tot: {formData.totalVotiDiLista || 0}
                                </span>
                                <i className={`fas fa-chevron-${expandedSections.liste ? 'up' : 'down'}`}></i>
                            </div>
                        </div>
                        {expandedSections.liste && (
                            <div className="scrutinio-section-content">
                                {lists.map((name) => (
                                    <div className="scrutinio-list-item" key={name}>
                                        <span className={`scrutinio-list-label ${name === "MOVIMENTO 5 STELLE" ? 'highlight' : ''}`}>
                                            {name === "MOVIMENTO 5 STELLE" && (
                                                <i className="fas fa-star me-1" style={{ color: '#ffc107' }}></i>
                                            )}
                                            {name}
                                        </span>
                                        <input
                                            type="number"
                                            className="scrutinio-list-input"
                                            value={formData[name]}
                                            onChange={(e) => handleChange(e, name)}
                                            inputMode="numeric"
                                            min="0"
                                        />
                                    </div>
                                ))}
                                <div className="scrutinio-total">
                                    <span className="scrutinio-total-label">Totale Voti Lista</span>
                                    <span className="scrutinio-total-value">{formData.totalVotiDiLista || 0}</span>
                                </div>
                                {errors.totalVotiDiLista && (
                                    <div className="scrutinio-error">{errors.totalVotiDiLista}</div>
                                )}
                            </div>
                        )}
                    </div>
                )}

                {/* 6. Schede */}
                <div className="scrutinio-section">
                    <div
                        className="scrutinio-section-header"
                        onClick={() => toggleSection('schede')}
                    >
                        <div className="scrutinio-section-title">
                            <i className="fas fa-file-alt"></i>
                            Schede Speciali
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            {isSchedeComplete && (
                                <span className="scrutinio-section-badge complete">
                                    <i className="fas fa-check me-1"></i>OK
                                </span>
                            )}
                            <i className={`fas fa-chevron-${expandedSections.schede ? 'up' : 'down'}`}></i>
                        </div>
                    </div>
                    {expandedSections.schede && (
                        <div className="scrutinio-section-content">
                            <div className="scrutinio-list-item">
                                <span className="scrutinio-list-label">Schede Bianche</span>
                                <input
                                    type="number"
                                    className="scrutinio-list-input"
                                    value={formData.schedeBianche}
                                    onChange={(e) => handleChange(e, "schedeBianche")}
                                    inputMode="numeric"
                                    min="0"
                                />
                            </div>
                            <div className="scrutinio-list-item">
                                <span className="scrutinio-list-label">Schede Nulle</span>
                                <input
                                    type="number"
                                    className="scrutinio-list-input"
                                    value={formData.schedeNulle}
                                    onChange={(e) => handleChange(e, "schedeNulle")}
                                    inputMode="numeric"
                                    min="0"
                                />
                            </div>
                            <div className="scrutinio-list-item">
                                <span className="scrutinio-list-label">Schede Contestate</span>
                                <input
                                    type="number"
                                    className="scrutinio-list-input"
                                    value={formData.schedeContestate}
                                    onChange={(e) => handleChange(e, "schedeContestate")}
                                    inputMode="numeric"
                                    min="0"
                                />
                            </div>
                            {errors.schedeContestate && (
                                <div className="scrutinio-error">{errors.schedeContestate}</div>
                            )}
                        </div>
                    )}
                </div>

                {/* Bottom Bar */}
                <div className="scrutinio-bottom-bar">
                    <button
                        className="scrutinio-btn scrutinio-btn-primary"
                        onClick={handleSave}
                        disabled={isSaving}
                    >
                        {isSaving ? (
                            <>
                                <i className="fas fa-spinner fa-spin me-2"></i>
                                Invio...
                            </>
                        ) : (
                            <>
                                <i className="fas fa-paper-plane me-2"></i>
                                Invia Dati
                            </>
                        )}
                    </button>
                </div>
            </div>
        </>
    );
}

export default SectionForm;
