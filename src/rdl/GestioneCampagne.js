import React, { useState, useEffect } from 'react';
import ConfirmModal from '../components/ConfirmModal';

/**
 * GestioneCampagne - Gestione campagne di reclutamento RDL
 *
 * Permette ai delegati e sub-delegati di creare link pubblici
 * per raccogliere candidature RDL.
 */
function GestioneCampagne({ client, consultazione, setError, onOpenCampagna }) {
    // Campagne di reclutamento
    const [campagne, setCampagne] = useState([]);
    const [loadingCampagne, setLoadingCampagne] = useState(false);
    const [showCampagnaForm, setShowCampagnaForm] = useState(false);
    const [editingCampagna, setEditingCampagna] = useState(null);
    const [campagnaForm, setCampagnaForm] = useState({
        nome: '', slug: '', descrizione: '',
        data_apertura: '', data_chiusura: '',
        regioni_ids: [], province_ids: [], comuni_ids: [],
        messaggio_conferma: ''
    });
    const [savingCampagna, setSavingCampagna] = useState(false);
    const [successCampagna, setSuccessCampagna] = useState(null);
    const [formError, setFormError] = useState(null);

    // Territorio per campagna
    const [regioni, setRegioni] = useState([]);
    const [province, setProvince] = useState([]);
    const [comuni, setComuni] = useState([]);

    // Modal conferma
    const [confirmModal, setConfirmModal] = useState({ show: false, title: '', message: '', onConfirm: null });

    useEffect(() => {
        if (client) {
            loadCampagne();
        }
    }, [client, consultazione]);

    // Carica regioni quando il form viene aperto o al mount
    useEffect(() => {
        if (client && (showCampagnaForm || regioni.length === 0)) {
            loadRegioni();
        }
    }, [showCampagnaForm, client]);

    // Carica territorio per form campagna
    const loadRegioni = async () => {
        try {
            const result = await client.territorio.regioni();
            if (!result?.error) {
                // L'API ritorna {count, results, ...} oppure array direttamente
                const data = Array.isArray(result) ? result : result?.results || [];
                setRegioni(data);
            } else {
                console.error('Errore API:', result.error);
                setRegioni([]);
            }
        } catch (err) {
            console.error('Errore caricamento regioni:', err);
            setRegioni([]);
        }
    };

    const loadProvince = async (regioneId) => {
        try {
            const result = await client.territorio.province(regioneId);
            if (!result?.error) {
                // L'API ritorna {count, results, ...} oppure array direttamente
                const data = Array.isArray(result) ? result : result?.results || [];
                setProvince(data);
            }
        } catch (err) {
            console.error('Errore caricamento province:', err);
            setProvince([]);
        }
    };

    const loadComuni = async (provinciaId) => {
        try {
            const result = await client.territorio.comuni(provinciaId);
            if (!result?.error) {
                // L'API ritorna {count, results, ...} oppure array direttamente
                const data = Array.isArray(result) ? result : result?.results || [];
                setComuni(data);
            }
        } catch (err) {
            console.error('Errore caricamento comuni:', err);
            setComuni([]);
        }
    };

    // Campagne
    const loadCampagne = async () => {
        setLoadingCampagne(true);
        try {
            const result = await client.deleghe.campagne.list(consultazione?.id);
            if (result?.error) {
                setCampagne([]);
            } else {
                setCampagne(Array.isArray(result) ? result : result?.results || []);
            }
        } catch (err) {
            console.error('Errore caricamento campagne:', err);
            setCampagne([]);
        }
        setLoadingCampagne(false);
    };

    const generateSlug = (nome) => {
        return nome
            .toLowerCase()
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '') // rimuove accenti
            .replace(/[^a-z0-9\s-]/g, '')    // rimuove caratteri speciali
            .replace(/\s+/g, '-')             // spazi -> trattini
            .replace(/-+/g, '-')              // rimuove trattini doppi
            .substring(0, 100);
    };

    const handleCampagnaFormChange = (field, value) => {
        setCampagnaForm(prev => {
            const newForm = { ...prev, [field]: value };
            // Auto-genera slug dal nome
            if (field === 'nome' && !editingCampagna) {
                newForm.slug = generateSlug(value);
            }
            return newForm;
        });
    };

    const resetCampagnaForm = () => {
        setEditingCampagna(null);
        setCampagnaForm({
            nome: '', slug: '', descrizione: '',
            data_apertura: '', data_chiusura: '',
            regioni_ids: [], province_ids: [], comuni_ids: [],
            messaggio_conferma: ''
        });
        setProvince([]);
        setComuni([]);
        setFormError(null);
    };

    const handleEditCampagna = async (campagna) => {
        const regioneIds = campagna.territorio_regioni?.map(r => r.id) || [];
        const provinceIds = campagna.territorio_province?.map(p => p.id) || [];
        const comuniIds = campagna.territorio_comuni?.map(c => c.id) || [];

        setEditingCampagna(campagna.id);
        setCampagnaForm({
            nome: campagna.nome || '',
            slug: campagna.slug || '',
            descrizione: campagna.descrizione || '',
            data_apertura: campagna.data_apertura ? campagna.data_apertura.substring(0, 16) : '',
            data_chiusura: campagna.data_chiusura ? campagna.data_chiusura.substring(0, 16) : '',
            regioni_ids: regioneIds,
            province_ids: provinceIds,
            comuni_ids: comuniIds,
            messaggio_conferma: campagna.messaggio_conferma || ''
        });

        // Carica province se c'è una regione
        if (regioneIds.length > 0) {
            await loadProvince(regioneIds[0]);
        }

        // Carica comuni se c'è una provincia
        if (provinceIds.length > 0) {
            await loadComuni(provinceIds[0]);
        }

        setShowCampagnaForm(true);
    };

    const handleSaveCampagna = async (e) => {
        e.preventDefault();
        setFormError(null);

        if (!consultazione?.id) {
            setFormError('Consultazione attiva non trovata');
            return;
        }
        if (!campagnaForm.nome || !campagnaForm.data_apertura || !campagnaForm.data_chiusura) {
            setFormError('Compila tutti i campi obbligatori');
            return;
        }

        setSavingCampagna(true);
        try {
            const payload = {
                nome: campagnaForm.nome,
                slug: campagnaForm.slug || generateSlug(campagnaForm.nome),
                descrizione: campagnaForm.descrizione,
                data_apertura: campagnaForm.data_apertura,
                data_chiusura: campagnaForm.data_chiusura,
                territorio_regioni: campagnaForm.regioni_ids,
                territorio_province: campagnaForm.province_ids,
                territorio_comuni: campagnaForm.comuni_ids,
                messaggio_conferma: campagnaForm.messaggio_conferma,
                consultazione: consultazione?.id
            };

            let result;
            if (editingCampagna) {
                result = await client.deleghe.campagne.update(editingCampagna, payload);
            } else {
                result = await client.deleghe.campagne.create(payload);
            }

            if (result?.error) {
                setFormError(result.error);
            } else {
                // Show success screen
                setSuccessCampagna(result);
                setShowCampagnaForm(false);
                setFormError(null);
                loadCampagne();
            }
        } catch (err) {
            setFormError(editingCampagna ? 'Errore nella modifica della campagna' : 'Errore nella creazione della campagna');
        }
        setSavingCampagna(false);
    };

    const handleAttivaCampagna = (campagna) => {
        setConfirmModal({
            show: true,
            title: 'Attiva Campagna',
            message: `Sei sicuro di voler attivare la campagna "${campagna.nome}"? Una volta attiva, sara accessibile pubblicamente.`,
            onConfirm: async () => {
                try {
                    const result = await client.deleghe.campagne.attiva(campagna.id);
                    if (result?.error) {
                        setError(result.error);
                    } else {
                        loadCampagne();
                    }
                } catch (err) {
                    setError('Errore nell\'attivazione della campagna');
                }
                setConfirmModal({ show: false });
            }
        });
    };

    const handleChiudiCampagna = (campagna) => {
        setConfirmModal({
            show: true,
            title: 'Chiudi Campagna',
            message: `Sei sicuro di voler chiudere la campagna "${campagna.nome}"? Il link non sara piu accessibile.`,
            onConfirm: async () => {
                try {
                    const result = await client.deleghe.campagne.chiudi(campagna.id);
                    if (result?.error) {
                        setError(result.error);
                    } else {
                        loadCampagne();
                    }
                } catch (err) {
                    setError('Errore nella chiusura della campagna');
                }
                setConfirmModal({ show: false });
            }
        });
    };

    const handleDeleteCampagna = (campagna) => {
        setConfirmModal({
            show: true,
            title: 'Elimina Campagna',
            message: `Sei sicuro di voler eliminare la campagna "${campagna.nome}"?`,
            onConfirm: async () => {
                try {
                    const result = await client.deleghe.campagne.delete(campagna.id);
                    if (result?.error) {
                        setError(result.error);
                    } else {
                        loadCampagne();
                    }
                } catch (err) {
                    setError('Errore nell\'eliminazione della campagna');
                }
                setConfirmModal({ show: false });
            }
        });
    };

    const handleCopiaLink = (campagna) => {
        const link = `${window.location.origin}/campagna/${campagna.slug}`;
        navigator.clipboard.writeText(link).then(() => {
            setError(null);
            // Show success message briefly
            alert('Link copiato negli appunti!');
        }).catch(() => {
            setError('Errore nella copia del link');
        });
    };

    const formatDate = (dateStr) => {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return date.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric' });
    };

    // Render del form campagna (riusabile)
    const renderCampagnaForm = () => (
        <div className="card">
            <div className="card-header bg-info text-white d-flex justify-content-between align-items-center">
                <strong>{editingCampagna ? 'Modifica Campagna' : 'Nuova Campagna'}</strong>
                <button
                    type="button"
                    className="btn-close btn-close-white"
                    onClick={() => { setShowCampagnaForm(false); resetCampagnaForm(); }}
                    aria-label="Chiudi"
                />
            </div>
            <div className="card-body">
                <p className="text-muted mb-3 small">
                    Crea un link pubblico per raccogliere candidature RDL per: <strong>{consultazione?.nome}</strong>
                </p>

                {formError && (
                    <div className="alert alert-danger py-2">{formError}</div>
                )}

                <form onSubmit={handleSaveCampagna}>
                    <div className="row g-2 mb-2">
                        <div className="col-12">
                            <label htmlFor="nome" className="form-label small mb-1">Nome *</label>
                            <input
                                id="nome"
                                type="text"
                                className="form-control form-control-sm"
                                value={campagnaForm.nome}
                                onChange={(e) => handleCampagnaFormChange('nome', e.target.value)}
                                placeholder="Es: Referendum Giugno 2025 - Roma"
                                required
                                disabled={savingCampagna}
                            />
                        </div>
                        <div className="col-12">
                            <label htmlFor="slug" className="form-label small mb-1">Slug URL</label>
                            <input
                                id="slug"
                                type="text"
                                className="form-control form-control-sm"
                                value={campagnaForm.slug}
                                onChange={(e) => handleCampagnaFormChange('slug', e.target.value)}
                                placeholder="auto-generato"
                                disabled={savingCampagna}
                            />
                            <small className="text-muted">/campagna/{campagnaForm.slug || '...'}</small>
                        </div>
                    </div>

                    <div className="mb-2">
                        <label htmlFor="descrizione" className="form-label small mb-1">Descrizione</label>
                        <textarea
                            id="descrizione"
                            className="form-control form-control-sm"
                            rows="2"
                            value={campagnaForm.descrizione}
                            onChange={(e) => handleCampagnaFormChange('descrizione', e.target.value)}
                            placeholder="Descrizione opzionale"
                            disabled={savingCampagna}
                        />
                    </div>

                    <div className="row g-2 mb-2">
                        <div className="col-6">
                            <label htmlFor="data_apertura" className="form-label small mb-1">Apertura *</label>
                            <input
                                id="data_apertura"
                                type="datetime-local"
                                className="form-control form-control-sm"
                                value={campagnaForm.data_apertura}
                                onChange={(e) => handleCampagnaFormChange('data_apertura', e.target.value)}
                                required
                                disabled={savingCampagna}
                            />
                        </div>
                        <div className="col-6">
                            <label htmlFor="data_chiusura" className="form-label small mb-1">Chiusura *</label>
                            <input
                                id="data_chiusura"
                                type="datetime-local"
                                className="form-control form-control-sm"
                                value={campagnaForm.data_chiusura}
                                onChange={(e) => handleCampagnaFormChange('data_chiusura', e.target.value)}
                                required
                                disabled={savingCampagna}
                            />
                        </div>
                    </div>

                    <div className="row g-2 mb-2">
                        <div className="col-6">
                            <label htmlFor="regione" className="form-label small mb-1">Regione</label>
                            <select
                                id="regione"
                                className="form-select form-select-sm"
                                value={String(campagnaForm.regioni_ids[0] || '')}
                                onChange={(e) => {
                                    const val = e.target.value;
                                    if (val) {
                                        handleCampagnaFormChange('regioni_ids', [parseInt(val)]);
                                        handleCampagnaFormChange('province_ids', []);
                                        handleCampagnaFormChange('comuni_ids', []);
                                        setProvince([]);
                                        setComuni([]);
                                        loadProvince(val);
                                    } else {
                                        handleCampagnaFormChange('regioni_ids', []);
                                        handleCampagnaFormChange('province_ids', []);
                                        handleCampagnaFormChange('comuni_ids', []);
                                        setProvince([]);
                                        setComuni([]);
                                    }
                                }}
                                disabled={savingCampagna}
                            >
                                <option value="">Tutte</option>
                                {regioni && regioni.map(r => (
                                    <option key={r.id} value={String(r.id)}>{r.nome}</option>
                                ))}
                            </select>
                        </div>
                        <div className="col-6">
                            <label htmlFor="provincia" className="form-label small mb-1">Provincia</label>
                            <select
                                id="provincia"
                                className="form-select form-select-sm"
                                value={String(campagnaForm.province_ids[0] || '')}
                                onChange={(e) => {
                                    const val = e.target.value;
                                    handleCampagnaFormChange('province_ids', val ? [parseInt(val)] : []);
                                    handleCampagnaFormChange('comuni_ids', []);
                                    setComuni([]);
                                    if (val) loadComuni(val);
                                }}
                                disabled={!campagnaForm.regioni_ids.length || savingCampagna}
                            >
                                <option value="">Tutte</option>
                                {province.map(p => (
                                    <option key={p.id} value={String(p.id)}>{p.nome}</option>
                                ))}
                            </select>
                        </div>
                    </div>

                    <div className="mb-2">
                        <label htmlFor="comune" className="form-label small mb-1">Comune</label>
                        <select
                            id="comune"
                            className="form-select form-select-sm"
                            value={String(campagnaForm.comuni_ids[0] || '')}
                            onChange={(e) => {
                                const val = e.target.value;
                                handleCampagnaFormChange('comuni_ids', val ? [parseInt(val)] : []);
                            }}
                            disabled={!campagnaForm.province_ids.length || savingCampagna}
                        >
                            <option value="">Tutti</option>
                            {comuni.map(c => (
                                <option key={c.id} value={String(c.id)}>{c.nome}</option>
                            ))}
                        </select>
                    </div>

                    <div className="mb-3">
                        <label htmlFor="messaggio" className="form-label small mb-1">Messaggio conferma</label>
                        <textarea
                            id="messaggio"
                            className="form-control form-control-sm"
                            rows="2"
                            value={campagnaForm.messaggio_conferma}
                            onChange={(e) => handleCampagnaFormChange('messaggio_conferma', e.target.value)}
                            placeholder="Opzionale"
                            disabled={savingCampagna}
                        />
                    </div>

                    <div className="d-flex gap-2">
                        <button
                            type="submit"
                            className="btn btn-primary btn-sm flex-grow-1"
                            disabled={savingCampagna || !campagnaForm.nome || !campagnaForm.data_apertura || !campagnaForm.data_chiusura}
                        >
                            {savingCampagna ? (
                                <><span className="spinner-border spinner-border-sm me-1"></span>Salvataggio...</>
                            ) : (editingCampagna ? 'Salva' : 'Crea')}
                        </button>
                        <button
                            type="button"
                            className="btn btn-outline-secondary btn-sm"
                            onClick={() => { setShowCampagnaForm(false); resetCampagnaForm(); }}
                            disabled={savingCampagna}
                        >
                            Annulla
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );

    // Render della lista campagne
    const renderCampagneList = () => (
        <>
            {loadingCampagne ? (
                <div className="text-center py-4">
                    <div className="spinner-border text-primary" role="status">
                        <span className="visually-hidden">Caricamento...</span>
                    </div>
                </div>
            ) : campagne.length === 0 && !showCampagnaForm ? (
                <div className="text-center text-muted py-5">
                    <div style={{ fontSize: '3rem' }}>📢</div>
                    <p>Non hai ancora creato campagne di reclutamento</p>
                    <p className="small">Le campagne ti permettono di creare link pubblici per raccogliere candidature RDL.</p>
                </div>
            ) : (
                <div className="d-flex flex-column gap-2">
                    {campagne.map((campagna) => (
                        <div key={campagna.id} className={`card ${
                            campagna.stato === 'ATTIVA' ? 'border-success' :
                            campagna.stato === 'CHIUSA' ? 'border-secondary' :
                            'border-warning'
                        }`}>
                            <div className="card-body py-2 px-3">
                                <div className="d-flex justify-content-between align-items-start mb-1">
                                    <h6 className="mb-0 small">
                                        <i className="fas fa-bullhorn me-1 text-primary"></i>
                                        {campagna.nome}
                                    </h6>
                                    <span className={`badge ${
                                        campagna.stato === 'ATTIVA' ? 'bg-success' :
                                        campagna.stato === 'CHIUSA' ? 'bg-secondary' :
                                        'bg-warning text-dark'
                                    }`} style={{ fontSize: '0.65rem' }}>
                                        {campagna.stato}
                                    </span>
                                </div>

                                <div className="mb-1 d-flex flex-wrap gap-1">
                                    <span className="badge bg-light text-dark" style={{ fontSize: '0.65rem' }}>
                                        {campagna.n_registrazioni || 0} registrazioni
                                    </span>
                                    {campagna.data_chiusura && (
                                        <span className="badge bg-light text-dark" style={{ fontSize: '0.65rem' }}>
                                            Scade: {formatDate(campagna.data_chiusura)}
                                        </span>
                                    )}
                                </div>

                                {campagna.stato === 'ATTIVA' && (
                                    <div className="small mb-1" style={{ wordBreak: 'break-all', fontSize: '0.75rem' }}>
                                        <a
                                            href={`/campagna/${campagna.slug}`}
                                            onClick={(e) => { e.preventDefault(); onOpenCampagna?.(campagna.slug); }}
                                            className="text-primary"
                                        >
                                            /campagna/{campagna.slug}
                                        </a>
                                    </div>
                                )}

                                <div className="d-flex flex-wrap gap-1 pt-1 border-top">
                                    {campagna.stato === 'ATTIVA' && (
                                        <>
                                            <button className="btn btn-outline-success btn-sm py-0 px-1" onClick={() => onOpenCampagna?.(campagna.slug)} title="Apri">
                                                <i className="fas fa-external-link-alt"></i>
                                            </button>
                                            <button className="btn btn-outline-primary btn-sm py-0 px-1" onClick={() => handleCopiaLink(campagna)} title="Copia">
                                                <i className="fas fa-copy"></i>
                                            </button>
                                        </>
                                    )}
                                    <button className="btn btn-outline-secondary btn-sm py-0 px-1" onClick={() => handleEditCampagna(campagna)} title="Modifica">
                                        <i className="fas fa-edit"></i>
                                    </button>
                                    {campagna.stato === 'BOZZA' && (
                                        <button className="btn btn-success btn-sm py-0 px-2" onClick={() => handleAttivaCampagna(campagna)} title="Attiva">
                                            <i className="fas fa-play"></i>
                                        </button>
                                    )}
                                    {campagna.stato === 'ATTIVA' && (
                                        <button className="btn btn-outline-warning btn-sm py-0 px-2" onClick={() => handleChiudiCampagna(campagna)} title="Chiudi">
                                            <i className="fas fa-pause"></i>
                                        </button>
                                    )}
                                    <button className="btn btn-outline-danger btn-sm py-0 px-1 ms-auto" onClick={() => handleDeleteCampagna(campagna)} title="Elimina">
                                        <i className="fas fa-trash"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </>
    );

    return (
        <>
            {/* Page Header */}
            <div className="page-header campagne">
                <div className="page-header-title">
                    <i className="fas fa-bullhorn"></i>
                    Campagne di Reclutamento
                </div>
                <div className="page-header-subtitle">
                    Crea link pubblici per raccogliere candidature RDL
                </div>
            </div>

            {/* Actions */}
            <div className="d-flex justify-content-end gap-2 mb-3">
                <button
                    className="btn btn-outline-secondary btn-sm"
                    onClick={loadCampagne}
                    disabled={loadingCampagne}
                >
                    <i className="fas fa-sync-alt me-1"></i>
                    Aggiorna
                </button>
                <button
                    className="btn btn-primary btn-sm"
                    onClick={() => {
                        if (showCampagnaForm) {
                            setShowCampagnaForm(false);
                            resetCampagnaForm();
                        } else {
                            setShowCampagnaForm(true);
                        }
                    }}
                >
                    {showCampagnaForm ? 'Torna alla Lista' : '+ Nuova Campagna'}
                </button>
            </div>

            {/* Success screen */}
            {successCampagna && (
                <div className="alert alert-success d-flex align-items-center mb-3">
                    <i className="fas fa-check-circle me-2"></i>
                    <div className="flex-grow-1">
                        Campagna "{successCampagna.nome}" {editingCampagna ? 'modificata' : 'creata'} con successo!
                    </div>
                    <button className="btn btn-sm btn-success" onClick={() => setSuccessCampagna(null)}>OK</button>
                </div>
            )}

            {/* Form OPPURE Lista (mai entrambi) */}
            {showCampagnaForm ? (
                renderCampagnaForm()
            ) : (
                renderCampagneList()
            )}

            {/* Info box */}
            {!showCampagnaForm && campagne.length > 0 && (
                <div className="alert alert-info mt-3 small">
                    <i className="fas fa-info-circle me-1"></i>
                    <strong>Bozza</strong> = non visibile | <strong>Attiva</strong> = link funzionante | <strong>Chiusa</strong> = link disattivato
                </div>
            )}

            {/* Confirm Modal */}
            <ConfirmModal
                show={confirmModal.show}
                title={confirmModal.title}
                message={confirmModal.message}
                onConfirm={confirmModal.onConfirm}
                onCancel={() => setConfirmModal({ show: false })}
            />
        </>
    );
}

export default GestioneCampagne;
