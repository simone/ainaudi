import React, { useState, useEffect, useCallback } from 'react';
import ConfirmModal from '../ConfirmModal';

/**
 * Custom hook for debouncing a value
 */
function useDebounce(value, delay) {
    const [debouncedValue, setDebouncedValue] = useState(value);

    useEffect(() => {
        const handler = setTimeout(() => {
            setDebouncedValue(value);
        }, delay);

        return () => {
            clearTimeout(handler);
        };
    }, [value, delay]);

    return debouncedValue;
}

/**
 * Converte un numero in numeri romani
 */
const toRoman = (num) => {
    const romanNumerals = [
        { value: 1000, numeral: 'M' },
        { value: 900, numeral: 'CM' },
        { value: 500, numeral: 'D' },
        { value: 400, numeral: 'CD' },
        { value: 100, numeral: 'C' },
        { value: 90, numeral: 'XC' },
        { value: 50, numeral: 'L' },
        { value: 40, numeral: 'XL' },
        { value: 10, numeral: 'X' },
        { value: 9, numeral: 'IX' },
        { value: 5, numeral: 'V' },
        { value: 4, numeral: 'IV' },
        { value: 1, numeral: 'I' }
    ];
    let result = '';
    for (const { value, numeral } of romanNumerals) {
        while (num >= value) {
            result += numeral;
            num -= value;
        }
    }
    return result;
};

/**
 * GestioneComuni - CRUD for Italian municipalities.
 *
 * Features:
 * - Table view with cascading filters (region -> province) and search
 * - Create/Edit form with cascading dropdowns
 * - Municipi management when editing a comune
 * - CSV import
 * - Delete with confirmation
 */
function GestioneComuni({ client, setError }) {
    const [comuni, setComuni] = useState([]);
    const [regioni, setRegioni] = useState([]);
    const [province, setProvince] = useState([]);
    const [loading, setLoading] = useState(true);
    const [loadingMore, setLoadingMore] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [filterRegione, setFilterRegione] = useState('');
    const [filterProvincia, setFilterProvincia] = useState('');
    const [currentPage, setCurrentPage] = useState(1);
    const [hasMore, setHasMore] = useState(false);
    const [totalCount, setTotalCount] = useState(0);

    // Form state
    const [showForm, setShowForm] = useState(false);
    const [editingId, setEditingId] = useState(null);
    const [formData, setFormData] = useState({
        provincia: '',
        codice_istat: '',
        codice_catastale: '',
        nome: '',
        sopra_15000_abitanti: false
    });
    const [formProvince, setFormProvince] = useState([]);
    const [formRegione, setFormRegione] = useState('');
    const [saving, setSaving] = useState(false);

    // Municipi state (for editing comune)
    const [municipi, setMunicipi] = useState([]);
    const [loadingMunicipi, setLoadingMunicipi] = useState(false);
    const [newMunicipio, setNewMunicipio] = useState({ numero: '', nome: '' });
    const [savingMunicipio, setSavingMunicipio] = useState(false);

    // Import state
    const [showImport, setShowImport] = useState(false);
    const [importFile, setImportFile] = useState(null);
    const [importing, setImporting] = useState(false);
    const [importResult, setImportResult] = useState(null);

    // Delete confirmation modal
    const [confirmModal, setConfirmModal] = useState({ show: false, title: '', message: '', onConfirm: null });

    // Debounce search term for backend queries
    const debouncedSearchTerm = useDebounce(searchTerm, 300);

    const loadRegioni = async () => {
        try {
            const data = await client.territorio.admin.regioni.list();
            if (!data.error) {
                setRegioni(Array.isArray(data) ? data : data.results || []);
            }
        } catch (err) {
            console.error('Errore caricamento regioni:', err);
        }
    };

    const loadProvince = async (regioneId = filterRegione) => {
        if (!regioneId) {
            setProvince([]);
            return;
        }
        try {
            const data = await client.territorio.admin.province.list({ regione: regioneId });
            if (!data.error) {
                setProvince(Array.isArray(data) ? data : data.results || []);
            }
        } catch (err) {
            console.error('Errore caricamento province:', err);
        }
    };

    const loadFormProvince = async (regioneId) => {
        if (!regioneId) {
            setFormProvince([]);
            return;
        }
        try {
            const data = await client.territorio.admin.province.list({ regione: regioneId });
            if (!data.error) {
                setFormProvince(Array.isArray(data) ? data : data.results || []);
            }
        } catch (err) {
            console.error('Errore caricamento province form:', err);
        }
    };

    const loadComuni = useCallback(async (reset = true) => {
        if (reset) {
            setLoading(true);
            setCurrentPage(1);
        }
        try {
            const filters = { page_size: 200 };
            if (filterProvincia) filters.provincia = filterProvincia;
            else if (filterRegione) filters.provincia__regione = filterRegione;
            if (debouncedSearchTerm) filters.search = debouncedSearchTerm;
            const data = await client.territorio.admin.comuni.list(filters);
            if (data.error) {
                setError(data.error);
            } else {
                const results = Array.isArray(data) ? data : data.results || [];
                setComuni(results);
                setTotalCount(data.count || results.length);
                setHasMore(!!data.next);
            }
        } catch (err) {
            setError(`Errore caricamento comuni: ${err.message}`);
        }
        setLoading(false);
    }, [client, filterProvincia, filterRegione, debouncedSearchTerm, setError]);

    const loadMoreComuni = useCallback(async () => {
        if (loadingMore || !hasMore) return;
        setLoadingMore(true);
        const nextPage = currentPage + 1;
        try {
            const filters = { page: nextPage, page_size: 50 };
            if (filterProvincia) filters.provincia = filterProvincia;
            else if (filterRegione) filters.provincia__regione = filterRegione;
            if (debouncedSearchTerm) filters.search = debouncedSearchTerm;
            const data = await client.territorio.admin.comuni.list(filters);
            if (data.error) {
                setError(data.error);
            } else {
                const results = Array.isArray(data) ? data : data.results || [];
                setComuni(prev => [...prev, ...results]);
                setCurrentPage(nextPage);
                setHasMore(!!data.next);
            }
        } catch (err) {
            setError(`Errore caricamento comuni: ${err.message}`);
        }
        setLoadingMore(false);
    }, [client, filterProvincia, filterRegione, debouncedSearchTerm, currentPage, hasMore, loadingMore, setError]);

    const handleScroll = useCallback((e) => {
        const { scrollTop, scrollHeight, clientHeight } = e.target;
        if (scrollHeight - scrollTop - clientHeight < 100) {
            loadMoreComuni();
        }
    }, [loadMoreComuni]);

    useEffect(() => {
        loadRegioni();
    }, []);

    useEffect(() => {
        loadProvince();
    }, [filterRegione]);

    useEffect(() => {
        loadComuni();
    }, [loadComuni]);

    const loadMunicipi = async (comuneId) => {
        if (!comuneId) {
            setMunicipi([]);
            return;
        }
        setLoadingMunicipi(true);
        try {
            const data = await client.territorio.admin.municipi.list({ comune: comuneId });
            if (!data.error) {
                setMunicipi(Array.isArray(data) ? data : data.results || []);
            }
        } catch (err) {
            console.error('Errore caricamento municipi:', err);
        }
        setLoadingMunicipi(false);
    };

    const handleFormChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
    };

    const handleFormRegioneChange = async (regioneId) => {
        setFormRegione(regioneId);
        setFormData(prev => ({ ...prev, provincia: '' }));
        await loadFormProvince(regioneId);
    };

    const resetForm = () => {
        setEditingId(null);
        setFormData({
            provincia: '',
            codice_istat: '',
            codice_catastale: '',
            nome: '',
            sopra_15000_abitanti: false
        });
        setFormRegione('');
        setFormProvince([]);
        setMunicipi([]);
        setNewMunicipio({ numero: '', nome: '' });
        setShowForm(false);
    };

    const handleEdit = async (comune) => {
        setEditingId(comune.id);
        // Find the regione from the provincia
        const provinceData = await client.territorio.admin.province.get(comune.provincia);
        if (provinceData && !provinceData.error) {
            const regioneId = provinceData.regione?.id;
            if (regioneId) {
                setFormRegione(regioneId);
                await loadFormProvince(regioneId);
            }
        }
        setFormData({
            provincia: comune.provincia || '',
            codice_istat: comune.codice_istat || '',
            codice_catastale: comune.codice_catastale || '',
            nome: comune.nome || '',
            sopra_15000_abitanti: comune.sopra_15000_abitanti || false
        });
        // Load municipi for this comune
        await loadMunicipi(comune.id);
        setShowForm(true);
    };

    const handleSave = async (e) => {
        e.preventDefault();
        if (!formData.provincia || !formData.codice_istat || !formData.codice_catastale || !formData.nome) {
            setError('Provincia, Codice ISTAT, Codice Catastale e Nome sono obbligatori');
            return;
        }

        setSaving(true);
        try {
            let result;
            if (editingId) {
                result = await client.territorio.admin.comuni.update(editingId, formData);
            } else {
                result = await client.territorio.admin.comuni.create(formData);
            }

            if (result.error) {
                setError(result.error);
            } else {
                resetForm();
                loadComuni();
            }
        } catch (err) {
            setError(`Errore salvataggio: ${err.message}`);
        }
        setSaving(false);
    };

    const handleDelete = (comune) => {
        setConfirmModal({
            show: true,
            title: 'Elimina Comune',
            message: `Sei sicuro di voler eliminare il comune "${comune.nome}"? Questa azione eliminera anche tutti i municipi e le sezioni elettorali collegate.`,
            onConfirm: async () => {
                try {
                    const result = await client.territorio.admin.comuni.delete(comune.id);
                    if (result.error) {
                        setError(result.error);
                    } else {
                        loadComuni();
                    }
                } catch (err) {
                    setError(`Errore eliminazione: ${err.message}`);
                }
                setConfirmModal({ show: false });
            }
        });
    };

    // Municipi management
    const handleAddMunicipio = async () => {
        if (!newMunicipio.numero || !editingId) {
            setError('Numero municipio obbligatorio');
            return;
        }

        setSavingMunicipio(true);
        try {
            const payload = {
                comune: editingId,
                numero: parseInt(newMunicipio.numero),
                nome: newMunicipio.nome || `Municipio ${toRoman(parseInt(newMunicipio.numero))}`
            };
            const result = await client.territorio.admin.municipi.create(payload);
            if (result.error) {
                setError(result.error);
            } else {
                setNewMunicipio({ numero: '', nome: '' });
                await loadMunicipi(editingId);
                loadComuni(); // Refresh to update n_municipi count
            }
        } catch (err) {
            setError(`Errore creazione municipio: ${err.message}`);
        }
        setSavingMunicipio(false);
    };

    const handleDeleteMunicipio = (municipio) => {
        setConfirmModal({
            show: true,
            title: 'Elimina Municipio',
            message: `Sei sicuro di voler eliminare "${municipio.nome || `Municipio ${toRoman(municipio.numero)}`}"?`,
            onConfirm: async () => {
                try {
                    const result = await client.territorio.admin.municipi.delete(municipio.id);
                    if (result.error) {
                        setError(result.error);
                    } else {
                        await loadMunicipi(editingId);
                        loadComuni(); // Refresh to update n_municipi count
                    }
                } catch (err) {
                    setError(`Errore eliminazione: ${err.message}`);
                }
                setConfirmModal({ show: false });
            }
        });
    };

    const handleImport = async () => {
        if (!importFile) {
            setError('Seleziona un file CSV');
            return;
        }

        setImporting(true);
        setImportResult(null);
        try {
            const result = await client.territorio.admin.comuni.import(importFile);
            if (result.error) {
                setError(result.error);
            } else {
                setImportResult(result);
                loadComuni();
            }
        } catch (err) {
            setError(`Errore importazione: ${err.message}`);
        }
        setImporting(false);
    };

    if (loading && comuni.length === 0) {
        return (
            <div className="text-center py-4">
                <div className="spinner-border text-primary" role="status">
                    <span className="visually-hidden">Caricamento...</span>
                </div>
            </div>
        );
    }

    return (
        <>
            {/* Toolbar */}
            <div className="d-flex flex-wrap justify-content-between align-items-center mb-3 gap-2">
                <div className="d-flex gap-2 flex-wrap">
                    <select
                        className="form-select form-select-sm"
                        value={filterRegione}
                        onChange={(e) => {
                            setFilterRegione(e.target.value);
                            setFilterProvincia('');
                        }}
                        style={{ width: '160px' }}
                    >
                        <option value="">Tutte le regioni</option>
                        {regioni.map(r => (
                            <option key={r.id} value={r.id}>{r.nome}</option>
                        ))}
                    </select>
                    <select
                        className="form-select form-select-sm"
                        value={filterProvincia}
                        onChange={(e) => setFilterProvincia(e.target.value)}
                        style={{ width: '160px' }}
                        disabled={!filterRegione}
                    >
                        <option value="">Tutte le province</option>
                        {province.map(p => (
                            <option key={p.id} value={p.id}>{p.nome} ({p.sigla})</option>
                        ))}
                    </select>
                    <input
                        type="text"
                        className="form-control form-control-sm"
                        placeholder="Cerca comune..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        style={{ width: '150px' }}
                    />
                    <span className="badge bg-secondary align-self-center">
                        {comuni.length}{totalCount > comuni.length ? ` / ${totalCount}` : ''} comuni
                    </span>
                </div>
                <div className="d-flex gap-2">
                    <button
                        className="btn btn-outline-secondary btn-sm"
                        onClick={() => setShowImport(!showImport)}
                    >
                        <i className="fas fa-file-import me-1"></i>
                        Importa CSV
                    </button>
                    <button
                        className="btn btn-primary btn-sm"
                        onClick={() => {
                            if (showForm) {
                                resetForm();
                            } else {
                                setShowForm(true);
                            }
                        }}
                    >
                        {showForm ? 'Annulla' : '+ Nuovo Comune'}
                    </button>
                </div>
            </div>

            {/* Info alert if no filter selected */}
            {!filterRegione && !filterProvincia && !searchTerm && comuni.length >= 50 && (
                <div className="alert alert-info small py-2">
                    <i className="fas fa-info-circle me-1"></i>
                    Usa la ricerca o seleziona una regione/provincia per filtrare. Visualizzati i primi {comuni.length} comuni.
                </div>
            )}

            {/* Import Section */}
            {showImport && (
                <div className="card mb-3 border-info">
                    <div className="card-header bg-info text-white">
                        <i className="fas fa-file-import me-2"></i>
                        Importa Comuni da CSV
                    </div>
                    <div className="card-body">
                        <p className="small text-muted">
                            Formato CSV: <code>provincia_sigla,codice_istat,codice_catastale,nome,sopra_15000_abitanti</code>
                        </p>
                        <div className="row g-2">
                            <div className="col-auto">
                                <input
                                    type="file"
                                    className="form-control form-control-sm"
                                    accept=".csv"
                                    onChange={(e) => {
                                        setImportFile(e.target.files[0]);
                                        setImportResult(null);
                                    }}
                                />
                            </div>
                            <div className="col-auto">
                                <button
                                    className="btn btn-info btn-sm"
                                    onClick={handleImport}
                                    disabled={!importFile || importing}
                                >
                                    {importing ? 'Importazione...' : 'Importa'}
                                </button>
                            </div>
                        </div>
                        {importResult && (
                            <div className={`alert ${importResult.errors?.length ? 'alert-warning' : 'alert-success'} mt-2 mb-0`}>
                                <small>
                                    Creati: {importResult.created} | Aggiornati: {importResult.updated}
                                    {importResult.errors?.length > 0 && (
                                        <ul className="mb-0 mt-1">
                                            {importResult.errors.slice(0, 5).map((err, i) => (
                                                <li key={i} className="text-danger">{err}</li>
                                            ))}
                                            {importResult.errors.length > 5 && (
                                                <li>...e altri {importResult.errors.length - 5} errori</li>
                                            )}
                                        </ul>
                                    )}
                                </small>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Form */}
            {showForm && (
                <div className="card mb-3 border-primary">
                    <div className="card-header bg-primary text-white">
                        {editingId ? 'Modifica Comune' : 'Nuovo Comune'}
                    </div>
                    <div className="card-body">
                        <form onSubmit={handleSave}>
                            <div className="row g-3">
                                <div className="col-md-3">
                                    <label className="form-label">Regione *</label>
                                    <select
                                        className="form-select"
                                        value={formRegione}
                                        onChange={(e) => handleFormRegioneChange(e.target.value)}
                                        required
                                    >
                                        <option value="">Seleziona...</option>
                                        {regioni.map(r => (
                                            <option key={r.id} value={r.id}>{r.nome}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="col-md-3">
                                    <label className="form-label">Provincia *</label>
                                    <select
                                        className="form-select"
                                        name="provincia"
                                        value={formData.provincia}
                                        onChange={handleFormChange}
                                        required
                                        disabled={!formRegione}
                                    >
                                        <option value="">Seleziona...</option>
                                        {formProvince.map(p => (
                                            <option key={p.id} value={p.id}>{p.nome} ({p.sigla})</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="col-md-2">
                                    <label className="form-label">Codice ISTAT *</label>
                                    <input
                                        type="text"
                                        className="form-control"
                                        name="codice_istat"
                                        value={formData.codice_istat}
                                        onChange={handleFormChange}
                                        maxLength={6}
                                        placeholder="001272"
                                        required
                                    />
                                </div>
                                <div className="col-md-2">
                                    <label className="form-label">Cod. Catastale *</label>
                                    <input
                                        type="text"
                                        className="form-control"
                                        name="codice_catastale"
                                        value={formData.codice_catastale}
                                        onChange={handleFormChange}
                                        maxLength={4}
                                        placeholder="L219"
                                        required
                                    />
                                </div>
                                <div className="col-md-2">
                                    <label className="form-label">Nome *</label>
                                    <input
                                        type="text"
                                        className="form-control"
                                        name="nome"
                                        value={formData.nome}
                                        onChange={handleFormChange}
                                        placeholder="Torino"
                                        required
                                    />
                                </div>
                                <div className="col-md-3">
                                    <label className="form-label">&gt; 15.000 abitanti</label>
                                    <div className="form-check mt-2">
                                        <input
                                            type="checkbox"
                                            className="form-check-input"
                                            id="sopra_15000_abitanti"
                                            name="sopra_15000_abitanti"
                                            checked={formData.sopra_15000_abitanti}
                                            onChange={handleFormChange}
                                        />
                                        <label className="form-check-label" htmlFor="sopra_15000_abitanti">
                                            Si (doppio turno)
                                        </label>
                                    </div>
                                </div>
                            </div>
                            <div className="mt-3 d-flex gap-2">
                                <button type="submit" className="btn btn-success" disabled={saving}>
                                    {saving ? 'Salvataggio...' : (editingId ? 'Salva Comune' : 'Crea')}
                                </button>
                                <button type="button" className="btn btn-secondary" onClick={resetForm}>
                                    Annulla
                                </button>
                            </div>
                        </form>

                        {/* Municipi Section - only for editing existing comune */}
                        {editingId && (
                            <div className="mt-4 pt-4 border-top">
                                <h6>
                                    <i className="fas fa-building me-2"></i>
                                    Municipi di {formData.nome}
                                </h6>

                                {loadingMunicipi ? (
                                    <div className="text-center py-3">
                                        <div className="spinner-border spinner-border-sm text-primary" role="status">
                                            <span className="visually-hidden">Caricamento...</span>
                                        </div>
                                    </div>
                                ) : (
                                    <>
                                        {/* Add new municipio */}
                                        <div className="row g-2 mb-3">
                                            <div className="col-auto">
                                                <input
                                                    type="number"
                                                    className="form-control form-control-sm"
                                                    placeholder="Numero"
                                                    value={newMunicipio.numero}
                                                    onChange={(e) => setNewMunicipio(prev => ({ ...prev, numero: e.target.value }))}
                                                    min={1}
                                                    style={{ width: '80px' }}
                                                />
                                            </div>
                                            <div className="col">
                                                <input
                                                    type="text"
                                                    className="form-control form-control-sm"
                                                    placeholder="Nome (opzionale)"
                                                    value={newMunicipio.nome}
                                                    onChange={(e) => setNewMunicipio(prev => ({ ...prev, nome: e.target.value }))}
                                                />
                                            </div>
                                            <div className="col-auto">
                                                <button
                                                    type="button"
                                                    className="btn btn-outline-primary btn-sm"
                                                    onClick={handleAddMunicipio}
                                                    disabled={!newMunicipio.numero || savingMunicipio}
                                                >
                                                    {savingMunicipio ? '...' : '+ Aggiungi'}
                                                </button>
                                            </div>
                                        </div>

                                        {/* List of municipi */}
                                        {municipi.length === 0 ? (
                                            <p className="text-muted small">Nessun municipio configurato</p>
                                        ) : (
                                            <div className="d-flex flex-wrap gap-2">
                                                {municipi
                                                    .sort((a, b) => a.numero - b.numero)
                                                    .map(m => (
                                                        <span
                                                            key={m.id}
                                                            className="badge bg-light text-dark border d-inline-flex align-items-center"
                                                        >
                                                            <strong className="me-1">{toRoman(m.numero)}</strong>
                                                            {m.nome && <span className="me-2">- {m.nome}</span>}
                                                            <button
                                                                type="button"
                                                                className="btn-close btn-close-sm ms-1"
                                                                style={{ fontSize: '0.6rem' }}
                                                                onClick={() => handleDeleteMunicipio(m)}
                                                                title="Elimina"
                                                            ></button>
                                                        </span>
                                                    ))
                                                }
                                            </div>
                                        )}
                                    </>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Table */}
            <div
                className="table-responsive"
                style={{ maxHeight: '60vh', overflowY: 'auto' }}
                onScroll={handleScroll}
            >
                <table className="table table-hover table-sm">
                    <thead className="table-light">
                        <tr>
                            <th style={{ width: '90px' }}>ISTAT</th>
                            <th style={{ width: '70px' }}>Catast.</th>
                            <th>Nome</th>
                            <th>Provincia</th>
                            <th style={{ width: '100px' }}>&gt; 15.000 ab.</th>
                            <th style={{ width: '80px' }}>Municipi</th>
                            <th style={{ width: '100px' }}>Azioni</th>
                        </tr>
                    </thead>
                    <tbody>
                        {comuni.length === 0 ? (
                            <tr>
                                <td colSpan={7} className="text-center text-muted py-4">
                                    Nessun comune trovato
                                </td>
                            </tr>
                        ) : (
                            comuni.map(comune => (
                                <tr key={comune.id}>
                                    <td><code>{comune.codice_istat}</code></td>
                                    <td><code>{comune.codice_catastale}</code></td>
                                    <td><strong>{comune.nome}</strong></td>
                                    <td className="text-muted">
                                        {comune.provincia_nome} ({comune.provincia_sigla})
                                    </td>
                                    <td>
                                        {comune.sopra_15000_abitanti ? (
                                            <span className="badge bg-primary">Si</span>
                                        ) : (
                                            <span className="badge bg-secondary">No</span>
                                        )}
                                    </td>
                                    <td className="text-center">
                                        {comune.n_municipi > 0 ? (
                                            <span className="badge bg-info">{comune.n_municipi}</span>
                                        ) : (
                                            <span className="text-muted">-</span>
                                        )}
                                    </td>
                                    <td>
                                        <button
                                            className="btn btn-outline-primary btn-sm me-1"
                                            onClick={() => handleEdit(comune)}
                                            title="Modifica"
                                        >
                                            <i className="fas fa-edit"></i>
                                        </button>
                                        <button
                                            className="btn btn-outline-danger btn-sm"
                                            onClick={() => handleDelete(comune)}
                                            title="Elimina"
                                        >
                                            <i className="fas fa-trash"></i>
                                        </button>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
                {/* Loading more indicator */}
                {loadingMore && (
                    <div className="text-center py-2 bg-light">
                        <div className="spinner-border spinner-border-sm text-primary me-2"></div>
                        <small>Caricamento altri comuni...</small>
                    </div>
                )}
                {hasMore && !loadingMore && (
                    <div className="text-center py-2 bg-light">
                        <small className="text-muted">Scorri per caricare altri comuni</small>
                    </div>
                )}
            </div>

            {/* Confirm Modal */}
            <ConfirmModal
                show={confirmModal.show}
                title={confirmModal.title}
                message={confirmModal.message}
                onConfirm={confirmModal.onConfirm}
                onCancel={() => setConfirmModal({ show: false })}
                confirmVariant="danger"
                confirmText="Elimina"
            />
        </>
    );
}

export default GestioneComuni;
