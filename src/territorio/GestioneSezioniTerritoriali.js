import React, { useState, useEffect } from 'react';
import ConfirmModal from '../components/ConfirmModal';

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
 * GestioneSezioniTerritoriali - CRUD for electoral sections.
 *
 * Features:
 * - Cascading filters: region -> province -> municipality -> district
 * - Table view with search
 * - Create/Edit form with conditional district widget
 * - CSV import
 * - Delete with confirmation
 */
function GestioneSezioniTerritoriali({ client, setError }) {
    const [sezioni, setSezioni] = useState([]);
    const [regioni, setRegioni] = useState([]);
    const [province, setProvince] = useState([]);
    const [comuni, setComuni] = useState([]);
    const [municipi, setMunicipi] = useState([]);
    const [loading, setLoading] = useState(false);
    const [loadingMore, setLoadingMore] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [filterRegione, setFilterRegione] = useState('');
    const [filterProvincia, setFilterProvincia] = useState('');
    const [filterComune, setFilterComune] = useState('');
    const [filterMunicipio, setFilterMunicipio] = useState('');
    const [currentPage, setCurrentPage] = useState(1);
    const [hasMore, setHasMore] = useState(false);
    const [totalCount, setTotalCount] = useState(0);

    // Form state
    const [showForm, setShowForm] = useState(false);
    const [editingId, setEditingId] = useState(null);
    const [formData, setFormData] = useState({
        comune: '',
        municipio: '',
        numero: '',
        indirizzo: '',
        denominazione: '',
        n_elettori: '',
        is_attiva: true
    });
    const [formRegione, setFormRegione] = useState('');
    const [formProvincia, setFormProvincia] = useState('');
    const [formProvince, setFormProvince] = useState([]);
    const [formComuni, setFormComuni] = useState([]);
    const [formMunicipi, setFormMunicipi] = useState([]);
    const [saving, setSaving] = useState(false);

    // Import state
    const [showImport, setShowImport] = useState(false);
    const [importFile, setImportFile] = useState(null);
    const [importing, setImporting] = useState(false);
    const [importResult, setImportResult] = useState(null);

    // Delete confirmation modal
    const [confirmModal, setConfirmModal] = useState({ show: false, title: '', message: '', onConfirm: null });

    useEffect(() => {
        loadRegioni();
    }, []);

    useEffect(() => {
        loadProvince();
    }, [filterRegione]);

    useEffect(() => {
        loadComuni();
    }, [filterProvincia]);

    useEffect(() => {
        loadMunicipi();
    }, [filterComune]);

    useEffect(() => {
        if (filterComune) {
            loadSezioni();
        } else {
            setSezioni([]);
        }
    }, [filterComune, filterMunicipio]);

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

    const loadComuni = async (provinciaId = filterProvincia) => {
        if (!provinciaId) {
            setComuni([]);
            return;
        }
        try {
            const data = await client.territorio.admin.comuni.list({ provincia: provinciaId });
            if (!data.error) {
                setComuni(Array.isArray(data) ? data : data.results || []);
            }
        } catch (err) {
            console.error('Errore caricamento comuni:', err);
        }
    };

    const loadMunicipi = async (comuneId = filterComune) => {
        if (!comuneId) {
            setMunicipi([]);
            return;
        }
        try {
            const data = await client.territorio.admin.municipi.list({ comune: comuneId });
            if (!data.error) {
                setMunicipi(Array.isArray(data) ? data : data.results || []);
            }
        } catch (err) {
            console.error('Errore caricamento municipi:', err);
        }
    };

    const loadSezioni = async (reset = true) => {
        if (!filterComune) return;
        if (reset) {
            setLoading(true);
            setCurrentPage(1);
        }
        try {
            const filters = { comune: filterComune, page_size: 200 };
            if (filterMunicipio) filters.municipio = filterMunicipio;
            const data = await client.territorio.admin.sezioni.list(filters);
            if (data.error) {
                setError(data.error);
            } else {
                const results = Array.isArray(data) ? data : data.results || [];
                setSezioni(results);
                setTotalCount(data.count || results.length);
                setHasMore(!!data.next);
            }
        } catch (err) {
            setError(`Errore caricamento sezioni: ${err.message}`);
        }
        setLoading(false);
    };

    const loadMoreSezioni = async () => {
        if (loadingMore || !hasMore || !filterComune) return;
        setLoadingMore(true);
        const nextPage = currentPage + 1;
        try {
            const filters = { comune: filterComune, page: nextPage, page_size: 50 };
            if (filterMunicipio) filters.municipio = filterMunicipio;
            const data = await client.territorio.admin.sezioni.list(filters);
            if (data.error) {
                setError(data.error);
            } else {
                const results = Array.isArray(data) ? data : data.results || [];
                setSezioni(prev => [...prev, ...results]);
                setCurrentPage(nextPage);
                setHasMore(!!data.next);
            }
        } catch (err) {
            setError(`Errore caricamento sezioni: ${err.message}`);
        }
        setLoadingMore(false);
    };

    const handleScroll = (e) => {
        const { scrollTop, scrollHeight, clientHeight } = e.target;
        if (scrollHeight - scrollTop - clientHeight < 100) {
            loadMoreSezioni();
        }
    };

    // Form-specific loaders
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

    const loadFormComuni = async (provinciaId) => {
        if (!provinciaId) {
            setFormComuni([]);
            return;
        }
        try {
            const data = await client.territorio.admin.comuni.list({ provincia: provinciaId });
            if (!data.error) {
                setFormComuni(Array.isArray(data) ? data : data.results || []);
            }
        } catch (err) {
            console.error('Errore caricamento comuni form:', err);
        }
    };

    const loadFormMunicipi = async (comuneId) => {
        if (!comuneId) {
            setFormMunicipi([]);
            return;
        }
        try {
            const data = await client.territorio.admin.municipi.list({ comune: comuneId });
            if (!data.error) {
                setFormMunicipi(Array.isArray(data) ? data : data.results || []);
            }
        } catch (err) {
            console.error('Errore caricamento municipi form:', err);
        }
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
        setFormProvincia('');
        setFormData(prev => ({ ...prev, comune: '', municipio: '' }));
        setFormComuni([]);
        setFormMunicipi([]);
        await loadFormProvince(regioneId);
    };

    const handleFormProvinciaChange = async (provinciaId) => {
        setFormProvincia(provinciaId);
        setFormData(prev => ({ ...prev, comune: '', municipio: '' }));
        setFormMunicipi([]);
        await loadFormComuni(provinciaId);
    };

    const handleFormComuneChange = async (comuneId) => {
        setFormData(prev => ({ ...prev, comune: comuneId, municipio: '' }));
        await loadFormMunicipi(comuneId);
    };

    const resetForm = () => {
        setEditingId(null);
        setFormData({
            comune: '',
            municipio: '',
            numero: '',
            indirizzo: '',
            denominazione: '',
            n_elettori: '',
            is_attiva: true
        });
        setFormRegione('');
        setFormProvincia('');
        setFormProvince([]);
        setFormComuni([]);
        setFormMunicipi([]);
        setShowForm(false);
    };

    const handleEdit = async (sezione) => {
        setEditingId(sezione.id);

        // We need to load the cascading dropdowns
        // Get the comune details to find regione and provincia
        try {
            const comuneData = await client.territorio.admin.comuni.get(sezione.comune);
            if (comuneData && !comuneData.error) {
                const provinciaId = comuneData.provincia?.id;
                if (provinciaId) {
                    const provinciaData = await client.territorio.admin.province.get(provinciaId);
                    if (provinciaData && !provinciaData.error) {
                        const regioneId = provinciaData.regione?.id;
                        if (regioneId) {
                            setFormRegione(regioneId);
                            await loadFormProvince(regioneId);
                            setFormProvincia(provinciaId);
                            await loadFormComuni(provinciaId);
                            await loadFormMunicipi(sezione.comune);
                        }
                    }
                }
            }
        } catch (err) {
            console.error('Errore caricamento dati sezione:', err);
        }

        setFormData({
            comune: sezione.comune || '',
            municipio: sezione.municipio || '',
            numero: sezione.numero || '',
            indirizzo: sezione.indirizzo || '',
            denominazione: sezione.denominazione || '',
            n_elettori: sezione.n_elettori || '',
            is_attiva: sezione.is_attiva !== false
        });
        setShowForm(true);
    };

    const handleSave = async (e) => {
        e.preventDefault();
        if (!formData.comune || !formData.numero) {
            setError('Comune e Numero sezione sono obbligatori');
            return;
        }

        // Check if municipio is required (if the comune has municipi)
        if (formMunicipi.length > 0 && !formData.municipio) {
            setError('Seleziona un municipio');
            return;
        }

        setSaving(true);
        try {
            const payload = {
                comune: parseInt(formData.comune),
                municipio: formData.municipio ? parseInt(formData.municipio) : null,
                numero: parseInt(formData.numero),
                indirizzo: formData.indirizzo || null,
                denominazione: formData.denominazione || null,
                n_elettori: formData.n_elettori ? parseInt(formData.n_elettori) : null,
                is_attiva: formData.is_attiva
            };

            let result;
            if (editingId) {
                result = await client.territorio.admin.sezioni.update(editingId, payload);
            } else {
                result = await client.territorio.admin.sezioni.create(payload);
            }

            if (result.error) {
                setError(result.error);
            } else {
                resetForm();
                loadSezioni();
            }
        } catch (err) {
            setError(`Errore salvataggio: ${err.message}`);
        }
        setSaving(false);
    };

    const handleDelete = (sezione) => {
        setConfirmModal({
            show: true,
            title: 'Elimina Sezione',
            message: `Sei sicuro di voler eliminare la sezione ${sezione.numero} di ${sezione.comune_nome}?`,
            onConfirm: async () => {
                try {
                    const result = await client.territorio.admin.sezioni.delete(sezione.id);
                    if (result.error) {
                        setError(result.error);
                    } else {
                        loadSezioni();
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
            const result = await client.territorio.admin.sezioni.import(importFile);
            if (result.error) {
                setError(result.error);
            } else {
                setImportResult(result);
                loadSezioni();
            }
        } catch (err) {
            setError(`Errore importazione: ${err.message}`);
        }
        setImporting(false);
    };

    // Filter sezioni based on search term
    const filteredSezioni = sezioni.filter(s =>
        s.numero?.toString().includes(searchTerm) ||
        s.indirizzo?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        s.denominazione?.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return (
        <>
            {/* Filters */}
            <div className="card mb-3">
                <div className="card-header">
                    <i className="fas fa-filter me-2"></i>
                    Filtra per Territorio
                </div>
                <div className="card-body">
                    <div className="row g-3">
                        <div className="col-md-3">
                            <label className="form-label small">Regione</label>
                            <select
                                className="form-select form-select-sm"
                                value={filterRegione}
                                onChange={(e) => {
                                    setFilterRegione(e.target.value);
                                    setFilterProvincia('');
                                    setFilterComune('');
                                    setFilterMunicipio('');
                                }}
                            >
                                <option value="">Seleziona regione...</option>
                                {regioni.map(r => (
                                    <option key={r.id} value={r.id}>{r.nome}</option>
                                ))}
                            </select>
                        </div>
                        <div className="col-md-3">
                            <label className="form-label small">Provincia</label>
                            <select
                                className="form-select form-select-sm"
                                value={filterProvincia}
                                onChange={(e) => {
                                    setFilterProvincia(e.target.value);
                                    setFilterComune('');
                                    setFilterMunicipio('');
                                }}
                                disabled={!filterRegione}
                            >
                                <option value="">Seleziona provincia...</option>
                                {province.map(p => (
                                    <option key={p.id} value={p.id}>{p.nome} ({p.sigla})</option>
                                ))}
                            </select>
                        </div>
                        <div className="col-md-3">
                            <label className="form-label small">Comune</label>
                            <select
                                className="form-select form-select-sm"
                                value={filterComune}
                                onChange={(e) => {
                                    setFilterComune(e.target.value);
                                    setFilterMunicipio('');
                                }}
                                disabled={!filterProvincia}
                            >
                                <option value="">Seleziona comune...</option>
                                {comuni.map(c => (
                                    <option key={c.id} value={c.id}>{c.nome}</option>
                                ))}
                            </select>
                        </div>
                        <div className="col-md-3">
                            <label className="form-label small">Municipio</label>
                            <select
                                className="form-select form-select-sm"
                                value={filterMunicipio}
                                onChange={(e) => setFilterMunicipio(e.target.value)}
                                disabled={!filterComune || municipi.length === 0}
                            >
                                <option value="">Tutti i municipi</option>
                                {municipi.map(m => (
                                    <option key={m.id} value={m.id}>
                                        {m.nome || `Municipio ${toRoman(m.numero)}`}
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>
                </div>
            </div>

            {/* Content - only show when comune is selected */}
            {filterComune ? (
                <>
                    {/* Toolbar */}
                    <div className="d-flex flex-wrap justify-content-between align-items-center mb-3 gap-2">
                        <div className="d-flex gap-2 flex-wrap">
                            <input
                                type="text"
                                className="form-control form-control-sm"
                                placeholder="Cerca sezione..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                style={{ width: '150px' }}
                            />
                            <span className="badge bg-secondary align-self-center">
                                {filteredSezioni.length} sezioni
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
                                        // Pre-fill the form with the current filter values
                                        setFormRegione(filterRegione);
                                        loadFormProvince(filterRegione).then(() => {
                                            setFormProvincia(filterProvincia);
                                            loadFormComuni(filterProvincia).then(() => {
                                                setFormData(prev => ({ ...prev, comune: filterComune }));
                                                loadFormMunicipi(filterComune);
                                            });
                                        });
                                        setShowForm(true);
                                    }
                                }}
                            >
                                {showForm ? 'Annulla' : '+ Nuova Sezione'}
                            </button>
                        </div>
                    </div>

                    {/* Import Section */}
                    {showImport && (
                        <div className="card mb-3 border-info">
                            <div className="card-header bg-info text-white">
                                <i className="fas fa-file-import me-2"></i>
                                Importa Sezioni da CSV
                            </div>
                            <div className="card-body">
                                <p className="small text-muted">
                                    Formato CSV: <code>comune_codice_istat,municipio_numero,numero,indirizzo,denominazione,n_elettori,is_attiva</code>
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
                                            Create: {importResult.created} | Aggiornate: {importResult.updated}
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
                                {editingId ? 'Modifica Sezione' : 'Nuova Sezione'}
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
                                                value={formProvincia}
                                                onChange={(e) => handleFormProvinciaChange(e.target.value)}
                                                required
                                                disabled={!formRegione}
                                            >
                                                <option value="">Seleziona...</option>
                                                {formProvince.map(p => (
                                                    <option key={p.id} value={p.id}>{p.nome} ({p.sigla})</option>
                                                ))}
                                            </select>
                                        </div>
                                        <div className="col-md-3">
                                            <label className="form-label">Comune *</label>
                                            <select
                                                className="form-select"
                                                name="comune"
                                                value={formData.comune}
                                                onChange={(e) => handleFormComuneChange(e.target.value)}
                                                required
                                                disabled={!formProvincia}
                                            >
                                                <option value="">Seleziona...</option>
                                                {formComuni.map(c => (
                                                    <option key={c.id} value={c.id}>{c.nome}</option>
                                                ))}
                                            </select>
                                        </div>
                                        <div className="col-md-3">
                                            <label className="form-label">
                                                Municipio {formMunicipi.length > 0 ? '*' : ''}
                                            </label>
                                            {formMunicipi.length > 0 ? (
                                                <select
                                                    className="form-select"
                                                    name="municipio"
                                                    value={formData.municipio}
                                                    onChange={handleFormChange}
                                                    required
                                                >
                                                    <option value="">Seleziona...</option>
                                                    {formMunicipi.map(m => (
                                                        <option key={m.id} value={m.id}>
                                                            {m.nome || `Municipio ${toRoman(m.numero)}`}
                                                        </option>
                                                    ))}
                                                </select>
                                            ) : (
                                                <input
                                                    type="text"
                                                    className="form-control"
                                                    disabled
                                                    placeholder="Comune senza municipi"
                                                />
                                            )}
                                        </div>
                                        <div className="col-md-2">
                                            <label className="form-label">Numero Sezione *</label>
                                            <input
                                                type="number"
                                                className="form-control"
                                                name="numero"
                                                value={formData.numero}
                                                onChange={handleFormChange}
                                                min={1}
                                                placeholder="1"
                                                required
                                            />
                                        </div>
                                        <div className="col-md-4">
                                            <label className="form-label">Denominazione</label>
                                            <input
                                                type="text"
                                                className="form-control"
                                                name="denominazione"
                                                value={formData.denominazione}
                                                onChange={handleFormChange}
                                                placeholder="es. Scuola Elementare Mazzini"
                                            />
                                        </div>
                                        <div className="col-md-4">
                                            <label className="form-label">Indirizzo</label>
                                            <input
                                                type="text"
                                                className="form-control"
                                                name="indirizzo"
                                                value={formData.indirizzo}
                                                onChange={handleFormChange}
                                                placeholder="Via Roma, 1"
                                            />
                                        </div>
                                        <div className="col-md-2">
                                            <label className="form-label">N. Elettori</label>
                                            <input
                                                type="number"
                                                className="form-control"
                                                name="n_elettori"
                                                value={formData.n_elettori}
                                                onChange={handleFormChange}
                                                min={0}
                                                placeholder="1000"
                                            />
                                        </div>
                                        <div className="col-md-2">
                                            <label className="form-label">Attiva</label>
                                            <div className="form-check mt-2">
                                                <input
                                                    type="checkbox"
                                                    className="form-check-input"
                                                    id="is_attiva"
                                                    name="is_attiva"
                                                    checked={formData.is_attiva}
                                                    onChange={handleFormChange}
                                                />
                                                <label className="form-check-label" htmlFor="is_attiva">
                                                    Si
                                                </label>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="mt-3 d-flex gap-2">
                                        <button type="submit" className="btn btn-success" disabled={saving}>
                                            {saving ? 'Salvataggio...' : (editingId ? 'Salva' : 'Crea')}
                                        </button>
                                        <button type="button" className="btn btn-secondary" onClick={resetForm}>
                                            Annulla
                                        </button>
                                    </div>
                                </form>
                            </div>
                        </div>
                    )}

                    {/* Table */}
                    {loading ? (
                        <div className="text-center py-4">
                            <div className="spinner-border text-primary" role="status">
                                <span className="visually-hidden">Caricamento...</span>
                            </div>
                        </div>
                    ) : (
                        <>
                            {/* Counter info */}
                            <div className="d-flex justify-content-between align-items-center mb-2">
                                <small className="text-muted">
                                    {sezioni.length} di {totalCount} sezioni caricate
                                </small>
                                {hasMore && (
                                    <small className="text-muted">
                                        Scorri per caricarne altre
                                    </small>
                                )}
                            </div>
                            <div
                                className="table-responsive"
                                style={{ maxHeight: '60vh', overflowY: 'auto' }}
                                onScroll={handleScroll}
                            >
                                <table className="table table-hover table-sm">
                                    <thead className="table-light" style={{ position: 'sticky', top: 0, zIndex: 1 }}>
                                        <tr>
                                            <th style={{ width: '80px' }}>Sezione</th>
                                            <th>Comune</th>
                                            <th>Municipio</th>
                                            <th>Denominazione</th>
                                            <th>Indirizzo</th>
                                            <th style={{ width: '90px' }}>Elettori</th>
                                            <th style={{ width: '70px' }}>Attiva</th>
                                            <th style={{ width: '100px' }}>Azioni</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {filteredSezioni.length === 0 ? (
                                            <tr>
                                                <td colSpan={8} className="text-center text-muted py-4">
                                                    Nessuna sezione trovata
                                                </td>
                                            </tr>
                                        ) : (
                                            filteredSezioni.map(sezione => (
                                                <tr key={sezione.id}>
                                                    <td><strong>{sezione.numero}</strong></td>
                                                    <td>{sezione.comune_nome}</td>
                                                    <td className="text-muted">
                                                        {sezione.municipio_numero ? `Mun. ${toRoman(sezione.municipio_numero)}` : '-'}
                                                    </td>
                                                    <td>{sezione.denominazione || '-'}</td>
                                                    <td className="small">{sezione.indirizzo || '-'}</td>
                                                    <td className="text-end">
                                                        {sezione.n_elettori?.toLocaleString() || '-'}
                                                    </td>
                                                    <td>
                                                        {sezione.is_attiva ? (
                                                            <span className="badge bg-success">Si</span>
                                                        ) : (
                                                            <span className="badge bg-secondary">No</span>
                                                        )}
                                                    </td>
                                                    <td>
                                                        <button
                                                            className="btn btn-outline-primary btn-sm me-1"
                                                            onClick={() => handleEdit(sezione)}
                                                            title="Modifica"
                                                        >
                                                            <i className="fas fa-edit"></i>
                                                        </button>
                                                        <button
                                                            className="btn btn-outline-danger btn-sm"
                                                            onClick={() => handleDelete(sezione)}
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
                                    <div className="text-center py-3">
                                        <div className="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
                                        <span className="text-muted">Caricamento...</span>
                                    </div>
                                )}
                            </div>
                        </>
                    )}
                </>
            ) : (
                <div className="text-center py-5 text-muted">
                    <div style={{ fontSize: '3rem' }}>🗳️</div>
                    <p>Seleziona una regione, provincia e comune per visualizzare le sezioni elettorali</p>
                </div>
            )}

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

export default GestioneSezioniTerritoriali;
