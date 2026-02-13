import React, { useState, useEffect } from 'react';
import ConfirmModal from '../components/ConfirmModal';

/**
 * GestioneRegioni - CRUD for Italian regions.
 *
 * Features:
 * - Table view with search filter
 * - Create/Edit inline form
 * - CSV import
 * - Delete with confirmation
 */
function GestioneRegioni({ client, setError }) {
    const [regioni, setRegioni] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');

    // Form state
    const [showForm, setShowForm] = useState(false);
    const [editingId, setEditingId] = useState(null);
    const [formData, setFormData] = useState({
        codice_istat: '',
        nome: '',
        statuto_speciale: false
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

    const loadRegioni = async () => {
        setLoading(true);
        try {
            const data = await client.territorio.admin.regioni.list();
            if (data.error) {
                setError(data.error);
            } else {
                setRegioni(Array.isArray(data) ? data : data.results || []);
            }
        } catch (err) {
            setError(`Errore caricamento regioni: ${err.message}`);
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
            codice_istat: '',
            nome: '',
            statuto_speciale: false
        });
        setShowForm(false);
    };

    const handleEdit = (regione) => {
        setEditingId(regione.id);
        setFormData({
            codice_istat: regione.codice_istat || '',
            nome: regione.nome || '',
            statuto_speciale: regione.statuto_speciale || false
        });
        setShowForm(true);
    };

    const handleSave = async (e) => {
        e.preventDefault();
        if (!formData.codice_istat || !formData.nome) {
            setError('Codice ISTAT e Nome sono obbligatori');
            return;
        }

        setSaving(true);
        try {
            let result;
            if (editingId) {
                result = await client.territorio.admin.regioni.update(editingId, formData);
            } else {
                result = await client.territorio.admin.regioni.create(formData);
            }

            if (result.error) {
                setError(result.error);
            } else {
                resetForm();
                loadRegioni();
            }
        } catch (err) {
            setError(`Errore salvataggio: ${err.message}`);
        }
        setSaving(false);
    };

    const handleDelete = (regione) => {
        setConfirmModal({
            show: true,
            title: 'Elimina Regione',
            message: `Sei sicuro di voler eliminare la regione "${regione.nome}"? Questa azione eliminera anche tutte le province e i comuni collegati.`,
            onConfirm: async () => {
                try {
                    const result = await client.territorio.admin.regioni.delete(regione.id);
                    if (result.error) {
                        setError(result.error);
                    } else {
                        loadRegioni();
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
            const result = await client.territorio.admin.regioni.import(importFile);
            if (result.error) {
                setError(result.error);
            } else {
                setImportResult(result);
                loadRegioni();
            }
        } catch (err) {
            setError(`Errore importazione: ${err.message}`);
        }
        setImporting(false);
    };

    // Filter regioni based on search term
    const filteredRegioni = regioni.filter(r =>
        r.nome?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        r.codice_istat?.includes(searchTerm)
    );

    if (loading) {
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
                <div className="d-flex gap-2">
                    <input
                        type="text"
                        className="form-control"
                        placeholder="Cerca regione..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        style={{ width: '200px' }}
                    />
                    <span className="badge bg-secondary align-self-center">
                        {filteredRegioni.length} regioni
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
                        {showForm ? 'Annulla' : '+ Nuova Regione'}
                    </button>
                </div>
            </div>

            {/* Import Section */}
            {showImport && (
                <div className="card mb-3 border-info">
                    <div className="card-header bg-info text-white">
                        <i className="fas fa-file-import me-2"></i>
                        Importa Regioni da CSV
                    </div>
                    <div className="card-body">
                        <p className="small text-muted">
                            Formato CSV: <code>codice_istat,nome,statuto_speciale</code>
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
                        {editingId ? 'Modifica Regione' : 'Nuova Regione'}
                    </div>
                    <div className="card-body">
                        <form onSubmit={handleSave}>
                            <div className="row g-3">
                                <div className="col-md-3">
                                    <label className="form-label">Codice ISTAT *</label>
                                    <input
                                        type="text"
                                        className="form-control"
                                        name="codice_istat"
                                        value={formData.codice_istat}
                                        onChange={handleFormChange}
                                        maxLength={2}
                                        placeholder="01"
                                        required
                                    />
                                    <small className="text-muted">2 cifre</small>
                                </div>
                                <div className="col-md-6">
                                    <label className="form-label">Nome *</label>
                                    <input
                                        type="text"
                                        className="form-control"
                                        name="nome"
                                        value={formData.nome}
                                        onChange={handleFormChange}
                                        placeholder="Piemonte"
                                        required
                                    />
                                </div>
                                <div className="col-md-3">
                                    <label className="form-label">Statuto Speciale</label>
                                    <div className="form-check mt-2">
                                        <input
                                            type="checkbox"
                                            className="form-check-input"
                                            id="statuto_speciale"
                                            name="statuto_speciale"
                                            checked={formData.statuto_speciale}
                                            onChange={handleFormChange}
                                        />
                                        <label className="form-check-label" htmlFor="statuto_speciale">
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
                            <th style={{ width: '100px' }}>Codice</th>
                            <th>Nome</th>
                            <th style={{ width: '150px' }}>Statuto Speciale</th>
                            <th style={{ width: '120px' }}>Azioni</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredRegioni.length === 0 ? (
                            <tr>
                                <td colSpan={4} className="text-center text-muted py-4">
                                    Nessuna regione trovata
                                </td>
                            </tr>
                        ) : (
                            filteredRegioni.map(regione => (
                                <tr key={regione.id}>
                                    <td><code>{regione.codice_istat}</code></td>
                                    <td>{regione.nome}</td>
                                    <td>
                                        {regione.statuto_speciale ? (
                                            <span className="badge bg-info">Si</span>
                                        ) : (
                                            <span className="badge bg-secondary">No</span>
                                        )}
                                    </td>
                                    <td>
                                        <button
                                            className="btn btn-outline-primary btn-sm me-1"
                                            onClick={() => handleEdit(regione)}
                                            title="Modifica"
                                        >
                                            <i className="fas fa-edit"></i>
                                        </button>
                                        <button
                                            className="btn btn-outline-danger btn-sm"
                                            onClick={() => handleDelete(regione)}
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

export default GestioneRegioni;
