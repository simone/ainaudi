import React, { useState, useEffect } from 'react';
import ConfirmModal from '../ConfirmModal';

/**
 * GestioneProvince - CRUD for Italian provinces.
 *
 * Features:
 * - Table view with region filter and search
 * - Create/Edit form with cascading region dropdown
 * - CSV import
 * - Delete with confirmation
 */
function GestioneProvince({ client, setError }) {
    const [province, setProvince] = useState([]);
    const [regioni, setRegioni] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [filterRegione, setFilterRegione] = useState('');

    // Form state
    const [showForm, setShowForm] = useState(false);
    const [editingId, setEditingId] = useState(null);
    const [formData, setFormData] = useState({
        regione: '',
        codice_istat: '',
        sigla: '',
        nome: '',
        is_citta_metropolitana: false
    });
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

    const loadProvince = async () => {
        setLoading(true);
        try {
            const filters = {};
            if (filterRegione) filters.regione = filterRegione;
            const data = await client.territorio.admin.province.list(filters);
            if (data.error) {
                setError(data.error);
            } else {
                setProvince(Array.isArray(data) ? data : data.results || []);
            }
        } catch (err) {
            setError(`Errore caricamento province: ${err.message}`);
        }
        setLoading(false);
    };

    const handleFormChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
    };

    const resetForm = () => {
        setEditingId(null);
        setFormData({
            regione: '',
            codice_istat: '',
            sigla: '',
            nome: '',
            is_citta_metropolitana: false
        });
        setShowForm(false);
    };

    const handleEdit = (provincia) => {
        setEditingId(provincia.id);
        setFormData({
            regione: provincia.regione || '',
            codice_istat: provincia.codice_istat || '',
            sigla: provincia.sigla || '',
            nome: provincia.nome || '',
            is_citta_metropolitana: provincia.is_citta_metropolitana || false
        });
        setShowForm(true);
    };

    const handleSave = async (e) => {
        e.preventDefault();
        if (!formData.regione || !formData.codice_istat || !formData.sigla || !formData.nome) {
            setError('Tutti i campi sono obbligatori');
            return;
        }

        setSaving(true);
        try {
            let result;
            if (editingId) {
                result = await client.territorio.admin.province.update(editingId, formData);
            } else {
                result = await client.territorio.admin.province.create(formData);
            }

            if (result.error) {
                setError(result.error);
            } else {
                resetForm();
                loadProvince();
            }
        } catch (err) {
            setError(`Errore salvataggio: ${err.message}`);
        }
        setSaving(false);
    };

    const handleDelete = (provincia) => {
        setConfirmModal({
            show: true,
            title: 'Elimina Provincia',
            message: `Sei sicuro di voler eliminare la provincia "${provincia.nome}"? Questa azione eliminera anche tutti i comuni collegati.`,
            onConfirm: async () => {
                try {
                    const result = await client.territorio.admin.province.delete(provincia.id);
                    if (result.error) {
                        setError(result.error);
                    } else {
                        loadProvince();
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
            const result = await client.territorio.admin.province.import(importFile);
            if (result.error) {
                setError(result.error);
            } else {
                setImportResult(result);
                loadProvince();
            }
        } catch (err) {
            setError(`Errore importazione: ${err.message}`);
        }
        setImporting(false);
    };

    // Filter province based on search term
    const filteredProvince = province.filter(p =>
        p.nome?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        p.sigla?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        p.codice_istat?.includes(searchTerm)
    );

    if (loading && province.length === 0) {
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
                        onChange={(e) => setFilterRegione(e.target.value)}
                        style={{ width: '180px' }}
                    >
                        <option value="">Tutte le regioni</option>
                        {regioni.map(r => (
                            <option key={r.id} value={r.id}>{r.nome}</option>
                        ))}
                    </select>
                    <input
                        type="text"
                        className="form-control form-control-sm"
                        placeholder="Cerca provincia..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        style={{ width: '150px' }}
                    />
                    <span className="badge bg-secondary align-self-center">
                        {filteredProvince.length} province
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
                        {showForm ? 'Annulla' : '+ Nuova Provincia'}
                    </button>
                </div>
            </div>

            {/* Import Section */}
            {showImport && (
                <div className="card mb-3 border-info">
                    <div className="card-header bg-info text-white">
                        <i className="fas fa-file-import me-2"></i>
                        Importa Province da CSV
                    </div>
                    <div className="card-body">
                        <p className="small text-muted">
                            Formato CSV: <code>regione_codice,codice_istat,sigla,nome,is_citta_metropolitana</code>
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
                        {editingId ? 'Modifica Provincia' : 'Nuova Provincia'}
                    </div>
                    <div className="card-body">
                        <form onSubmit={handleSave}>
                            <div className="row g-3">
                                <div className="col-md-3">
                                    <label className="form-label">Regione *</label>
                                    <select
                                        className="form-select"
                                        name="regione"
                                        value={formData.regione}
                                        onChange={handleFormChange}
                                        required
                                    >
                                        <option value="">Seleziona...</option>
                                        {regioni.map(r => (
                                            <option key={r.id} value={r.id}>{r.nome}</option>
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
                                        maxLength={3}
                                        placeholder="001"
                                        required
                                    />
                                    <small className="text-muted">3 cifre</small>
                                </div>
                                <div className="col-md-2">
                                    <label className="form-label">Sigla *</label>
                                    <input
                                        type="text"
                                        className="form-control"
                                        name="sigla"
                                        value={formData.sigla}
                                        onChange={handleFormChange}
                                        maxLength={2}
                                        placeholder="TO"
                                        required
                                    />
                                </div>
                                <div className="col-md-3">
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
                                <div className="col-md-2">
                                    <label className="form-label">Citta Metr.</label>
                                    <div className="form-check mt-2">
                                        <input
                                            type="checkbox"
                                            className="form-check-input"
                                            id="is_citta_metropolitana"
                                            name="is_citta_metropolitana"
                                            checked={formData.is_citta_metropolitana}
                                            onChange={handleFormChange}
                                        />
                                        <label className="form-check-label" htmlFor="is_citta_metropolitana">
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
            <div className="table-responsive">
                <table className="table table-hover table-sm">
                    <thead className="table-light">
                        <tr>
                            <th style={{ width: '80px' }}>Codice</th>
                            <th style={{ width: '60px' }}>Sigla</th>
                            <th>Nome</th>
                            <th>Regione</th>
                            <th style={{ width: '100px' }}>Citta Metr.</th>
                            <th style={{ width: '100px' }}>Azioni</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredProvince.length === 0 ? (
                            <tr>
                                <td colSpan={6} className="text-center text-muted py-4">
                                    Nessuna provincia trovata
                                </td>
                            </tr>
                        ) : (
                            filteredProvince.map(provincia => (
                                <tr key={provincia.id}>
                                    <td><code>{provincia.codice_istat}</code></td>
                                    <td><strong>{provincia.sigla}</strong></td>
                                    <td>{provincia.nome}</td>
                                    <td className="text-muted">{provincia.regione_nome}</td>
                                    <td>
                                        {provincia.is_citta_metropolitana ? (
                                            <span className="badge bg-success">Si</span>
                                        ) : (
                                            <span className="badge bg-secondary">No</span>
                                        )}
                                    </td>
                                    <td>
                                        <button
                                            className="btn btn-outline-primary btn-sm me-1"
                                            onClick={() => handleEdit(provincia)}
                                            title="Modifica"
                                        >
                                            <i className="fas fa-edit"></i>
                                        </button>
                                        <button
                                            className="btn btn-outline-danger btn-sm"
                                            onClick={() => handleDelete(provincia)}
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

export default GestioneProvince;
