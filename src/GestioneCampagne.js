import React, { useState, useEffect } from 'react';
import ConfirmModal from './ConfirmModal';

/**
 * GestioneCampagne - Gestione campagne di reclutamento RDL
 *
 * Permette ai delegati e sub-delegati di creare link pubblici
 * per raccogliere candidature RDL.
 */
function GestioneCampagne({ client, consultazione, setError }) {
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

    // Debug: log campagnaForm changes
    useEffect(() => {
        console.log('campagnaForm updated:', campagnaForm);
    }, [campagnaForm]);

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
        const newForm = { ...campagnaForm, [field]: value };
        // Auto-genera slug dal nome
        if (field === 'nome' && !editingCampagna) {
            newForm.slug = generateSlug(value);
        }
        console.log('handleCampagnaFormChange:', field, '=', value, 'newForm:', newForm);
        setCampagnaForm(newForm);
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
        if (!campagnaForm.nome || !campagnaForm.data_apertura || !campagnaForm.data_chiusura) {
            setError('Compila tutti i campi obbligatori');
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
                territorio_regioni_ids: campagnaForm.regioni_ids,
                territorio_province_ids: campagnaForm.province_ids,
                territorio_comuni_ids: campagnaForm.comuni_ids,
                messaggio_conferma: campagnaForm.messaggio_conferma,
                consultazione_id: consultazione?.id
            };

            let result;
            if (editingCampagna) {
                result = await client.deleghe.campagne.update(editingCampagna, payload);
            } else {
                result = await client.deleghe.campagne.create(payload);
            }

            if (result?.error) {
                setError(result.error);
            } else {
                setShowCampagnaForm(false);
                resetCampagnaForm();
                loadCampagne();
            }
        } catch (err) {
            setError(editingCampagna ? 'Errore nella modifica della campagna' : 'Errore nella creazione della campagna');
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

    return (
        <>
            <div className="d-flex justify-content-between align-items-center mb-3">
                <div>
                    <h5 className="mb-0">
                        <i className="fas fa-bullhorn me-2"></i>
                        Campagne di Reclutamento RDL
                    </h5>
                    <small className="text-muted">Crea link pubblici per raccogliere candidature</small>
                </div>
                <div className="d-flex gap-2">
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
                        {showCampagnaForm ? 'Annulla' : '+ Nuova Campagna'}
                    </button>
                </div>
            </div>

            {/* Form nuova/modifica campagna */}
            {showCampagnaForm && (
                <div className="card mb-3 border-primary">
                    <div className="card-header bg-primary text-white">
                        <strong>{editingCampagna ? 'Modifica Campagna' : 'Nuova Campagna'}</strong>
                    </div>
                    <div className="card-body">
                        <form onSubmit={handleSaveCampagna}>
                            <div className="row g-3">
                                <div className="col-md-8">
                                    <label className="form-label">Nome *</label>
                                    <input
                                        type="text"
                                        className="form-control"
                                        value={campagnaForm.nome}
                                        onChange={(e) => handleCampagnaFormChange('nome', e.target.value)}
                                        placeholder="Es: Referendum Giugno 2025 - Roma"
                                        required
                                    />
                                </div>
                                <div className="col-md-4">
                                    <label className="form-label">Slug URL</label>
                                    <input
                                        type="text"
                                        className="form-control"
                                        value={campagnaForm.slug}
                                        onChange={(e) => handleCampagnaFormChange('slug', e.target.value)}
                                        placeholder="auto-generato"
                                    />
                                    <small className="text-muted">/campagna/{campagnaForm.slug || '...'}</small>
                                </div>
                                <div className="col-12">
                                    <label className="form-label">Descrizione</label>
                                    <textarea
                                        className="form-control"
                                        rows="2"
                                        value={campagnaForm.descrizione}
                                        onChange={(e) => handleCampagnaFormChange('descrizione', e.target.value)}
                                        placeholder="Descrizione opzionale della campagna"
                                    />
                                </div>
                                <div className="col-md-6">
                                    <label className="form-label">Data e ora apertura *</label>
                                    <input
                                        type="datetime-local"
                                        className="form-control"
                                        value={campagnaForm.data_apertura}
                                        onChange={(e) => handleCampagnaFormChange('data_apertura', e.target.value)}
                                        required
                                    />
                                </div>
                                <div className="col-md-6">
                                    <label className="form-label">Data e ora chiusura *</label>
                                    <input
                                        type="datetime-local"
                                        className="form-control"
                                        value={campagnaForm.data_chiusura}
                                        onChange={(e) => handleCampagnaFormChange('data_chiusura', e.target.value)}
                                        required
                                    />
                                </div>

                                {/* Territorio */}
                                <div className="col-12">
                                    <label className="form-label">Territorio (opzionale)</label>
                                    <small className="text-muted d-block mb-2">
                                        Lascia vuoto per accettare registrazioni da tutti i comuni.
                                    </small>
                                </div>
                                <div className="col-md-4">
                                    <label className="form-label small">Regione</label>
                                    <select
                                        className="form-select form-select-sm"
                                        value={campagnaForm.regioni_ids[0] ? String(campagnaForm.regioni_ids[0]) : ''}
                                        onChange={(e) => {
                                            console.log('Regione onChange:', e.target.value);
                                            const val = e.target.value;
                                            console.log('campagnaForm before:', campagnaForm);
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
                                            setTimeout(() => console.log('campagnaForm after:', campagnaForm), 0);
                                        }}
                                    >
                                        <option value="">Tutte le regioni</option>
                                        {regioni && regioni.map(r => (
                                            <option key={r.id} value={r.id}>{r.nome}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="col-md-4">
                                    <label className="form-label small">Provincia</label>
                                    <select
                                        className="form-select form-select-sm"
                                        value={String(campagnaForm.province_ids[0] || '')}
                                        onChange={(e) => {
                                            const val = e.target.value;
                                            handleCampagnaFormChange('province_ids', val ? [parseInt(val)] : []);
                                            handleCampagnaFormChange('comuni_ids', []);
                                            setComuni([]);
                                            if (val) loadComuni(val);
                                        }}
                                        disabled={!campagnaForm.regioni_ids.length}
                                    >
                                        <option value="">Tutte le province</option>
                                        {province.map(p => (
                                            <option key={p.id} value={String(p.id)}>{p.nome}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="col-md-4">
                                    <label className="form-label small">Comune</label>
                                    <select
                                        className="form-select form-select-sm"
                                        value={String(campagnaForm.comuni_ids[0] || '')}
                                        onChange={(e) => {
                                            const val = e.target.value;
                                            handleCampagnaFormChange('comuni_ids', val ? [parseInt(val)] : []);
                                        }}
                                        disabled={!campagnaForm.province_ids.length}
                                    >
                                        <option value="">Tutti i comuni</option>
                                        {comuni.map(c => (
                                            <option key={c.id} value={String(c.id)}>{c.nome}</option>
                                        ))}
                                    </select>
                                </div>

                                <div className="col-12">
                                    <label className="form-label">Messaggio di conferma</label>
                                    <textarea
                                        className="form-control"
                                        rows="2"
                                        value={campagnaForm.messaggio_conferma}
                                        onChange={(e) => handleCampagnaFormChange('messaggio_conferma', e.target.value)}
                                        placeholder="Messaggio mostrato dopo la registrazione (opzionale)"
                                    />
                                </div>
                            </div>
                            <div className="mt-3 d-flex gap-2">
                                <button type="submit" className="btn btn-success" disabled={savingCampagna}>
                                    {savingCampagna ? 'Salvataggio...' : (editingCampagna ? 'Salva Modifiche' : 'Crea Campagna')}
                                </button>
                                <button type="button" className="btn btn-secondary" onClick={() => { setShowCampagnaForm(false); resetCampagnaForm(); }}>
                                    Annulla
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Lista campagne */}
            {loadingCampagne ? (
                <div className="text-center py-4">
                    <div className="spinner-border text-primary" role="status">
                        <span className="visually-hidden">Caricamento...</span>
                    </div>
                </div>
            ) : campagne.length === 0 ? (
                <div className="text-center text-muted py-5">
                    <div style={{ fontSize: '3rem' }}>📢</div>
                    <p>Non hai ancora creato campagne di reclutamento</p>
                    <p className="small">
                        Le campagne ti permettono di creare link pubblici per raccogliere candidature RDL.
                    </p>
                </div>
            ) : (
                <div className="row g-3">
                    {campagne.map((campagna) => (
                        <div key={campagna.id} className="col-12">
                            <div className={`card ${
                                campagna.stato === 'ATTIVA' ? 'border-success' :
                                campagna.stato === 'CHIUSA' ? 'border-secondary' :
                                'border-warning'
                            }`}>
                                <div className="card-body">
                                    <div className="d-flex justify-content-between align-items-start">
                                        <div className="flex-grow-1">
                                            <h6 className="mb-1">
                                                <i className="fas fa-bullhorn me-2 text-primary"></i>
                                                {campagna.nome}
                                            </h6>
                                            <div className="mb-2">
                                                <span className={`badge me-2 ${
                                                    campagna.stato === 'ATTIVA' ? 'bg-success' :
                                                    campagna.stato === 'CHIUSA' ? 'bg-secondary' :
                                                    'bg-warning text-dark'
                                                }`}>
                                                    {campagna.stato === 'ATTIVA' ? '● Attiva' :
                                                     campagna.stato === 'CHIUSA' ? '○ Chiusa' :
                                                     '○ Bozza'}
                                                </span>
                                                <span className="badge bg-light text-dark me-2">
                                                    {campagna.n_registrazioni || 0} registrazioni
                                                </span>
                                                {campagna.data_chiusura && (
                                                    <span className="badge bg-light text-dark">
                                                        Scade: {formatDate(campagna.data_chiusura)}
                                                    </span>
                                                )}
                                            </div>
                                            {campagna.stato === 'ATTIVA' && (
                                                <div className="small text-muted">
                                                    <i className="fas fa-link me-1"></i>
                                                    {window.location.origin}/campagna/{campagna.slug}
                                                </div>
                                            )}
                                            {campagna.territorio_display && (
                                                <div className="small text-muted mt-1">
                                                    <i className="fas fa-map-marker-alt me-1"></i>
                                                    {campagna.territorio_display}
                                                </div>
                                            )}
                                        </div>
                                        <div className="d-flex flex-wrap gap-1 justify-content-end" style={{ minWidth: '200px' }}>
                                            {campagna.stato === 'ATTIVA' && (
                                                <button
                                                    className="btn btn-outline-primary btn-sm"
                                                    onClick={() => handleCopiaLink(campagna)}
                                                    title="Copia link"
                                                >
                                                    <i className="fas fa-copy"></i>
                                                </button>
                                            )}
                                            <button
                                                className="btn btn-outline-secondary btn-sm"
                                                onClick={() => handleEditCampagna(campagna)}
                                                title="Modifica"
                                            >
                                                <i className="fas fa-edit"></i>
                                            </button>
                                            {campagna.stato === 'BOZZA' && (
                                                <button
                                                    className="btn btn-success btn-sm"
                                                    onClick={() => handleAttivaCampagna(campagna)}
                                                    title="Attiva"
                                                >
                                                    <i className="fas fa-play me-1"></i>Attiva
                                                </button>
                                            )}
                                            {campagna.stato === 'ATTIVA' && (
                                                <button
                                                    className="btn btn-outline-warning btn-sm"
                                                    onClick={() => handleChiudiCampagna(campagna)}
                                                    title="Chiudi"
                                                >
                                                    <i className="fas fa-pause me-1"></i>Chiudi
                                                </button>
                                            )}
                                            <button
                                                className="btn btn-outline-danger btn-sm"
                                                onClick={() => handleDeleteCampagna(campagna)}
                                                title="Elimina"
                                            >
                                                <i className="fas fa-trash"></i>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Info box */}
            <div className="alert alert-info mt-3 small">
                <i className="fas fa-info-circle me-1"></i>
                <strong>Come funzionano le campagne:</strong>
                <ul className="mb-0 mt-1">
                    <li><strong>Bozza</strong>: La campagna non e visibile pubblicamente</li>
                    <li><strong>Attiva</strong>: Il link e accessibile e le persone possono registrarsi</li>
                    <li><strong>Chiusa</strong>: Il link non funziona piu</li>
                </ul>
            </div>

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
