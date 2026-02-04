import React, { useState, useEffect } from 'react';
import ConfirmModal from './ConfirmModal';

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

    return (
        <>
            <div className="mb-3">
                <div className="d-flex flex-column flex-sm-row justify-content-between align-items-start align-items-sm-center gap-2">
                    <div>
                        <h5 className="mb-0">
                            <i className="fas fa-bullhorn me-2"></i>
                            Campagne di Reclutamento RDL
                        </h5>
                        <small className="text-muted">Crea link pubblici per raccogliere candidature</small>
                    </div>
                    <div className="d-flex gap-2 flex-shrink-0">
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
            </div>

            {/* Form nuova/modifica campagna */}
            {showCampagnaForm && (
                <div className="card mb-3">
                    <div className="card-header bg-info text-white">
                        <strong>{editingCampagna ? 'Modifica Campagna' : 'Nuova Campagna'}</strong>
                    </div>
                    <div className="card-body">
                        <p className="text-muted mb-3">
                            Crea un link pubblico per raccogliere candidature come Rappresentante di Lista per la consultazione: <strong>{consultazione?.nome}</strong>
                        </p>

                        {formError && (
                            <div className="alert alert-danger">{formError}</div>
                        )}

                        <form onSubmit={handleSaveCampagna}>
                            {/* Informazioni campagna */}
                            <h6 className="text-muted mb-3">Informazioni campagna</h6>
                            <div className="row g-3 mb-3">
                                <div className="col-md-6">
                                    <label htmlFor="nome" className="form-label">Nome *</label>
                                    <input
                                        id="nome"
                                        type="text"
                                        className="form-control"
                                        value={campagnaForm.nome}
                                        onChange={(e) => handleCampagnaFormChange('nome', e.target.value)}
                                        placeholder="Es: Referendum Giugno 2025 - Roma"
                                        required
                                        disabled={savingCampagna}
                                        aria-required="true"
                                        aria-describedby="nome-help"
                                    />
                                    <small id="nome-help" className="text-muted">Nome della campagna di reclutamento</small>
                                </div>
                                <div className="col-md-6">
                                    <label htmlFor="slug" className="form-label">Slug URL</label>
                                    <input
                                        id="slug"
                                        type="text"
                                        className="form-control"
                                        value={campagnaForm.slug}
                                        onChange={(e) => handleCampagnaFormChange('slug', e.target.value)}
                                        placeholder="auto-generato"
                                        disabled={savingCampagna}
                                        aria-describedby="slug-help"
                                    />
                                    <small id="slug-help" className="text-muted">/campagna/{campagnaForm.slug || '...'}</small>
                                </div>
                            </div>

                            <div className="row g-3 mb-3">
                                <div className="col-12">
                                    <label htmlFor="descrizione" className="form-label">Descrizione</label>
                                    <textarea
                                        id="descrizione"
                                        className="form-control"
                                        rows="2"
                                        value={campagnaForm.descrizione}
                                        onChange={(e) => handleCampagnaFormChange('descrizione', e.target.value)}
                                        placeholder="Descrizione opzionale della campagna"
                                        disabled={savingCampagna}
                                        aria-describedby="descrizione-help"
                                    />
                                    <small id="descrizione-help" className="text-muted">Mostrata sulla pagina di registrazione</small>
                                </div>
                            </div>

                            {/* Date */}
                            <h6 className="text-muted mb-3 mt-3">Periodo di disponibilità</h6>
                            <div className="row g-3 mb-3">
                                <div className="col-md-6">
                                    <label htmlFor="data_apertura" className="form-label">Data e ora apertura *</label>
                                    <input
                                        id="data_apertura"
                                        type="datetime-local"
                                        className="form-control"
                                        value={campagnaForm.data_apertura}
                                        onChange={(e) => handleCampagnaFormChange('data_apertura', e.target.value)}
                                        required
                                        disabled={savingCampagna}
                                        aria-required="true"
                                        aria-describedby="data_apertura-help"
                                    />
                                    <small id="data_apertura-help" className="text-muted">Da quando la campagna è accessibile</small>
                                </div>
                                <div className="col-md-6">
                                    <label htmlFor="data_chiusura" className="form-label">Data e ora chiusura *</label>
                                    <input
                                        id="data_chiusura"
                                        type="datetime-local"
                                        className="form-control"
                                        value={campagnaForm.data_chiusura}
                                        onChange={(e) => handleCampagnaFormChange('data_chiusura', e.target.value)}
                                        required
                                        disabled={savingCampagna}
                                        aria-required="true"
                                        aria-describedby="data_chiusura-help"
                                    />
                                    <small id="data_chiusura-help" className="text-muted">Quando la campagna si chiude</small>
                                </div>
                            </div>

                            {/* Territorio */}
                            <h6 className="text-muted mb-3 mt-3">Territorio (opzionale)</h6>
                            <div className="alert alert-light border small mb-3" role="note">
                                <strong>Scegli per territorio:</strong> Lascia vuoto per accettare registrazioni da tutti i comuni,
                                oppure seleziona regione, provincia e/o comune per limitare le candidature a specifiche aree.
                            </div>

                            <div className="row g-3 mb-3">
                                <div className="col-md-6">
                                    <label htmlFor="regione" className="form-label">Regione</label>
                                    <select
                                        id="regione"
                                        className="form-select"
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
                                        aria-describedby="regione-help"
                                    >
                                        <option value="">Tutte le regioni</option>
                                        {regioni && regioni.map(r => (
                                            <option key={r.id} value={String(r.id)}>{r.nome}</option>
                                        ))}
                                    </select>
                                    <small id="regione-help" className="text-muted">Accettare candidature da tutta l'Italia o da una regione specifica?</small>
                                </div>
                                <div className="col-md-6">
                                    <label htmlFor="provincia" className="form-label">Provincia</label>
                                    <select
                                        id="provincia"
                                        className="form-select"
                                        value={String(campagnaForm.province_ids[0] || '')}
                                        onChange={(e) => {
                                            const val = e.target.value;
                                            handleCampagnaFormChange('province_ids', val ? [parseInt(val)] : []);
                                            handleCampagnaFormChange('comuni_ids', []);
                                            setComuni([]);
                                            if (val) loadComuni(val);
                                        }}
                                        disabled={!campagnaForm.regioni_ids.length || savingCampagna}
                                        aria-describedby="provincia-help"
                                    >
                                        <option value="">Tutte le province</option>
                                        {province.map(p => (
                                            <option key={p.id} value={String(p.id)}>{p.nome}</option>
                                        ))}
                                    </select>
                                    <small id="provincia-help" className="text-muted">Disponibile dopo aver selezionato una regione</small>
                                </div>
                            </div>

                            <div className="row g-3 mb-3">
                                <div className="col-12">
                                    <label htmlFor="comune" className="form-label">Comune</label>
                                    <select
                                        id="comune"
                                        className="form-select"
                                        value={String(campagnaForm.comuni_ids[0] || '')}
                                        onChange={(e) => {
                                            const val = e.target.value;
                                            handleCampagnaFormChange('comuni_ids', val ? [parseInt(val)] : []);
                                        }}
                                        disabled={!campagnaForm.province_ids.length || savingCampagna}
                                        aria-describedby="comune-help"
                                    >
                                        <option value="">Tutti i comuni</option>
                                        {comuni.map(c => (
                                            <option key={c.id} value={String(c.id)}>{c.nome}</option>
                                        ))}
                                    </select>
                                    <small id="comune-help" className="text-muted">Disponibile dopo aver selezionato una provincia</small>
                                </div>
                            </div>

                            {/* Messaggio di conferma */}
                            <h6 className="text-muted mb-3 mt-3">Messaggio di conferma</h6>
                            <div className="row g-3 mb-3">
                                <div className="col-12">
                                    <label htmlFor="messaggio" className="form-label">Messaggio personalizzato</label>
                                    <textarea
                                        id="messaggio"
                                        className="form-control"
                                        rows="2"
                                        value={campagnaForm.messaggio_conferma}
                                        onChange={(e) => handleCampagnaFormChange('messaggio_conferma', e.target.value)}
                                        placeholder="Messaggio mostrato dopo la registrazione (opzionale)"
                                        disabled={savingCampagna}
                                        aria-describedby="messaggio-help"
                                    />
                                    <small id="messaggio-help" className="text-muted">Se vuoto, verrà mostrato il messaggio predefinito di completamento registrazione</small>
                                </div>
                            </div>

                            {/* Buttons */}
                            <div className="d-flex gap-2 mt-4 pt-3 border-top">
                                <button
                                    type="submit"
                                    className="btn btn-primary"
                                    disabled={savingCampagna || !campagnaForm.nome || !campagnaForm.data_apertura || !campagnaForm.data_chiusura}
                                >
                                    {savingCampagna ? (
                                        <>
                                            <span className="spinner-border spinner-border-sm me-2"></span>
                                            Salvataggio...
                                        </>
                                    ) : (editingCampagna ? 'Salva Modifiche' : 'Crea Campagna')}
                                </button>
                                <button
                                    type="button"
                                    className="btn btn-secondary"
                                    onClick={() => { setShowCampagnaForm(false); resetCampagnaForm(); }}
                                    disabled={savingCampagna}
                                >
                                    Annulla
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Success screen */}
            {successCampagna && (
                <div className="card mb-3 border-success">
                    <div className="card-header bg-success text-white">
                        <i className="fas fa-check-circle me-2"></i>
                        {editingCampagna ? 'Campagna modificata' : 'Campagna creata'}
                    </div>
                    <div className="card-body">
                        <p className="mb-2">
                            {editingCampagna
                                ? `La campagna "${successCampagna.nome}" è stata modificata con successo.`
                                : `La campagna "${successCampagna.nome}" è stata creata con successo!`}
                        </p>
                        <p className="text-muted small mb-3">
                            {successCampagna.stato === 'BOZZA'
                                ? 'La campagna è attualmente in bozza e non visibile pubblicamente. Potrai attivarla quando sarai pronto.'
                                : 'La campagna è attualmente attiva e visibile pubblicamente.'}
                        </p>
                        <button
                            className="btn btn-primary"
                            onClick={() => setSuccessCampagna(null)}
                        >
                            Continua
                        </button>
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
                                    {/* Header: titolo e stato */}
                                    <div className="d-flex justify-content-between align-items-start mb-2">
                                        <h6 className="mb-0">
                                            <i className="fas fa-bullhorn me-2 text-primary"></i>
                                            {campagna.nome}
                                        </h6>
                                        <span className={`badge flex-shrink-0 ${
                                            campagna.stato === 'ATTIVA' ? 'bg-success' :
                                            campagna.stato === 'CHIUSA' ? 'bg-secondary' :
                                            'bg-warning text-dark'
                                        }`}>
                                            {campagna.stato === 'ATTIVA' ? '● Attiva' :
                                             campagna.stato === 'CHIUSA' ? '○ Chiusa' :
                                             '○ Bozza'}
                                        </span>
                                    </div>

                                    {/* Info badges */}
                                    <div className="mb-2 d-flex flex-wrap gap-1">
                                        <span className="badge bg-light text-dark">
                                            {campagna.n_registrazioni || 0} registrazioni
                                        </span>
                                        {campagna.data_chiusura && (
                                            <span className="badge bg-light text-dark">
                                                Scade: {formatDate(campagna.data_chiusura)}
                                            </span>
                                        )}
                                    </div>

                                    {/* Link (solo se attiva) */}
                                    {campagna.stato === 'ATTIVA' && (
                                        <div className="small mb-2" style={{ wordBreak: 'break-all' }}>
                                            <i className="fas fa-link me-1 text-muted"></i>
                                            <a
                                                href={`/campagna/${campagna.slug}`}
                                                onClick={(e) => {
                                                    e.preventDefault();
                                                    if (onOpenCampagna) {
                                                        onOpenCampagna(campagna.slug);
                                                    }
                                                }}
                                                className="text-primary"
                                                title="Apri campagna"
                                            >
                                                {window.location.origin}/campagna/{campagna.slug}
                                            </a>
                                        </div>
                                    )}

                                    {/* Territorio */}
                                    {campagna.territorio_display && (
                                        <div className="small text-muted mb-2">
                                            <i className="fas fa-map-marker-alt me-1"></i>
                                            {campagna.territorio_display}
                                        </div>
                                    )}

                                    {/* Azioni */}
                                    <div className="d-flex flex-wrap gap-1 pt-2 border-top">
                                        {campagna.stato === 'ATTIVA' && (
                                            <>
                                                <button
                                                    className="btn btn-outline-success btn-sm"
                                                    onClick={() => onOpenCampagna && onOpenCampagna(campagna.slug)}
                                                    title="Apri campagna"
                                                >
                                                    <i className="fas fa-external-link-alt"></i>
                                                </button>
                                                <button
                                                    className="btn btn-outline-primary btn-sm"
                                                    onClick={() => handleCopiaLink(campagna)}
                                                    title="Copia link"
                                                >
                                                    <i className="fas fa-copy"></i>
                                                </button>
                                            </>
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
                                            className="btn btn-outline-danger btn-sm ms-auto"
                                            onClick={() => handleDeleteCampagna(campagna)}
                                            title="Elimina"
                                        >
                                            <i className="fas fa-trash"></i>
                                        </button>
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
