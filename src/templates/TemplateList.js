import React, { useState, useEffect } from 'react';
import ConfirmModal from '../components/ConfirmModal';
import './TemplateEditor.css';

const TEMPLATE_TYPES = [
    { code: 'DESIGNATION_SINGLE', name: 'Designazione RDL Singola' },
    { code: 'DESIGNATION_MULTI', name: 'Designazione RDL Riepilogativa' },
    { code: 'DELEGATION', name: 'Delega Sub-Delegato' },
];

/**
 * Template List - Lista template per consultazione attiva
 * Permette di creare nuovi template o aprire l'editor
 */
function TemplateList({ client, onEditTemplate }) {
    const [templates, setTemplates] = useState([]);
    const [visibleDelegates, setVisibleDelegates] = useState([]);
    const [consultazione, setConsultazione] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);
    const [deleteTarget, setDeleteTarget] = useState(null);
    const [showNewTemplateForm, setShowNewTemplateForm] = useState(false);
    const [newTemplate, setNewTemplate] = useState({
        name: '',
        template_type: '',
        description: '',
        owner_email: '',
        file: null
    });

    useEffect(() => {
        loadConsultazioneAndTemplates();
    }, []);

    const loadConsultazioneAndTemplates = async () => {
        try {
            setLoading(true);
            setError(null);

            // Get active consultazione
            const electionData = await client.election.active();
            if (!electionData || electionData.error) {
                setError('Nessuna consultazione elettorale attiva');
                setLoading(false);
                return;
            }

            setConsultazione(electionData);

            // Load templates for this consultazione
            const templatesData = await client.get(
                `/api/documents/templates/?consultazione=${electionData.id}`
            );

            // Handle both paginated response {results: [...]} and direct array
            if (Array.isArray(templatesData)) {
                setTemplates(templatesData);
            } else if (templatesData && Array.isArray(templatesData.results)) {
                setTemplates(templatesData.results);
            } else {
                setTemplates([]);
            }

            // Load visible delegates for owner selection
            const delegatesData = await client.templates.visibleDelegates(electionData.id);
            if (Array.isArray(delegatesData)) {
                setVisibleDelegates(delegatesData);
            } else {
                setVisibleDelegates([]);
            }

        } catch (err) {
            setError(`Errore caricamento: ${err.message}`);
            console.error('Load error:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleCreateTemplate = async (e) => {
        e.preventDefault();

        if (!newTemplate.name || !newTemplate.file) {
            setError('Nome e file PDF sono obbligatori');
            return;
        }

        if (!consultazione) {
            setError('Consultazione elettorale non disponibile');
            return;
        }

        try {
            setLoading(true);
            setError(null);

            // Upload file using FormData
            const formData = new FormData();
            formData.append('consultazione', consultazione.id);
            formData.append('name', newTemplate.name);
            formData.append('template_type', newTemplate.template_type);
            formData.append('description', newTemplate.description);
            if (newTemplate.owner_email) {
                formData.append('owner_email', newTemplate.owner_email);
            }
            formData.append('template_file', newTemplate.file);
            formData.append('is_active', 'true');

            const created = await client.upload('/api/documents/templates/', formData);

            setSuccess(`Template "${created.name}" creato con successo!`);
            setTimeout(() => setSuccess(null), 3000);
            setShowNewTemplateForm(false);
            setNewTemplate({
                name: '',
                template_type: '',
                description: '',
                owner_email: '',
                file: null
            });

            // Reload templates
            await loadConsultazioneAndTemplates();

        } catch (err) {
            setError(`Errore creazione template: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteTemplate = (template) => {
        setDeleteTarget(template);
    };

    const confirmDeleteTemplate = async () => {
        const template = deleteTarget;
        setDeleteTarget(null);

        try {
            setLoading(true);
            setError(null);

            await client.delete(`/api/documents/templates/${template.id}/`);

            setSuccess('Template eliminato!');
            setTimeout(() => setSuccess(null), 3000);

            // Reload templates
            await loadConsultazioneAndTemplates();

        } catch (err) {
            setError(`Errore eliminazione: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    if (loading && !consultazione) {
        return <div className="template-editor-loading">Caricamento consultazione...</div>;
    }

    if (error && !consultazione) {
        return (
            <div className="template-editor">
                <div className="alert alert-danger">
                    <h4>Errore</h4>
                    <p>{error}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="template-editor">
            {/* Page Header */}
            <div className="page-header templates">
                <div className="page-header-title">
                    <i className="fas fa-file-pdf"></i>
                    Template PDF
                </div>
                <div className="page-header-subtitle">
                    Gestisci i template per la generazione dei documenti di designazione
                    {consultazione && (
                        <span className="page-header-badge">{consultazione.nome}</span>
                    )}
                </div>
            </div>

            {/* Actions */}
            <div className="d-flex justify-content-end mb-3">
                <button
                    onClick={() => setShowNewTemplateForm(true)}
                    className="btn btn-primary"
                    disabled={loading}
                >
                    <i className="fas fa-plus me-2"></i>
                    Nuovo Template
                </button>
            </div>

            {error && (
                <div className="alert alert-danger">{error}</div>
            )}

            {success && (
                <div className="alert alert-success">{success}</div>
            )}

            {/* Form Nuovo Template */}
            {showNewTemplateForm && (
                <div className="new-template-form">
                    <div className="card">
                        <div className="card-header">
                            <h3>Nuovo Template PDF</h3>
                        </div>
                        <div className="card-body">
                            <form onSubmit={handleCreateTemplate}>
                                <div className="form-group">
                                    <label>Nome Template *</label>
                                    <input
                                        type="text"
                                        className="form-control"
                                        value={newTemplate.name}
                                        onChange={(e) => setNewTemplate({...newTemplate, name: e.target.value})}
                                        placeholder="es: individuale, riepilogativo"
                                        required
                                    />
                                </div>

                                <div className="form-group">
                                    <label>Tipo Template *</label>
                                    <select
                                        className="form-control"
                                        value={newTemplate.template_type}
                                        onChange={(e) => setNewTemplate({...newTemplate, template_type: e.target.value})}
                                        required
                                    >
                                        <option value="">-- Seleziona tipo --</option>
                                        {TEMPLATE_TYPES.map(tt => (
                                            <option key={tt.code} value={tt.code}>
                                                {tt.name}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                <div className="form-group">
                                    <label>Descrizione</label>
                                    <textarea
                                        className="form-control"
                                        value={newTemplate.description}
                                        onChange={(e) => setNewTemplate({...newTemplate, description: e.target.value})}
                                        placeholder="Descrizione template..."
                                        rows="3"
                                    />
                                </div>

                                <div className="form-group">
                                    <label>Proprietario</label>
                                    <select
                                        className="form-control"
                                        value={newTemplate.owner_email}
                                        onChange={(e) => setNewTemplate({...newTemplate, owner_email: e.target.value})}
                                    >
                                        <option value="">Template Generico (visibile a tutti)</option>
                                        {visibleDelegates.map((delegate, idx) => (
                                            <option key={idx} value={delegate.email}>
                                                {delegate.nome_completo} ({delegate.tipo}) - {delegate.ambito}
                                            </option>
                                        ))}
                                    </select>
                                    <small className="text-muted">
                                        Seleziona un proprietario per rendere il template personale (visibile solo a lui).
                                        Lascia "Template Generico" per renderlo visibile a tutti.
                                    </small>
                                </div>

                                <div className="form-group">
                                    <label>File PDF Template *</label>
                                    <input
                                        type="file"
                                        className="form-control"
                                        accept=".pdf"
                                        onChange={(e) => setNewTemplate({...newTemplate, file: e.target.files[0]})}
                                        required
                                    />
                                    <small className="text-muted">
                                        Carica il file PDF base su cui configurare i campi
                                    </small>
                                </div>

                                <div className="form-actions">
                                    <button type="submit" className="btn btn-success" disabled={loading}>
                                        Crea Template
                                    </button>
                                    <button
                                        type="button"
                                        className="btn btn-secondary"
                                        onClick={() => {
                                            setShowNewTemplateForm(false);
                                            setNewTemplate({
                                                name: '',
                                                template_type: templateTypes.length > 0 ? templateTypes[0].id : '',
                                                description: '',
                                                owner_email: '',
                                                file: null
                                            });
                                        }}
                                    >
                                        Annulla
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            )}

            {/* Lista Template */}
            <div className="template-config-section">
                <h3>Template Disponibili ({Array.isArray(templates) ? templates.length : 0})</h3>

                {!Array.isArray(templates) || templates.length === 0 ? (
                    <div className="no-fields">
                        <p>Nessun template configurato per questa consultazione.</p>
                        <p className="text-muted">
                            Clicca "+ Nuovo Template" per caricare un PDF e configurarlo.
                        </p>
                    </div>
                ) : (
                    <div className="template-list-cards">
                        {templates.map((template) => (
                            <div key={template.id} className="template-list-card">
                                <div className="template-list-card-header">
                                    <strong>{template.name}</strong>
                                    <span className="badge bg-info">
                                        {template.template_type_display || template.template_type || 'N/A'}
                                    </span>
                                </div>
                                {template.description && template.description !== '-' && (
                                    <div className="template-list-card-desc">{template.description}</div>
                                )}
                                <div className="template-list-card-meta">
                                    <span>v{template.version}</span>
                                    <span>{template.field_mappings?.length || 0} campi</span>
                                </div>
                                <div className="template-list-card-actions">
                                    <button
                                        onClick={() => onEditTemplate(template.id)}
                                        className="btn btn-primary btn-sm"
                                    >
                                        <i className="fas fa-cog me-1"></i>Configura
                                    </button>
                                    <button
                                        onClick={() => handleDeleteTemplate(template)}
                                        className="btn btn-danger btn-sm"
                                        disabled={loading}
                                    >
                                        <i className="fas fa-trash me-1"></i>Elimina
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <div className="template-editor-help">
                <h4>💡 Come funziona</h4>
                <ul>
                    <li><strong>Crea Template:</strong> Carica un file PDF base che verrà usato per generare i documenti</li>
                    <li><strong>Configura:</strong> Dopo aver creato un template, clicca "Configura" per definire i campi dinamici</li>
                    <li><strong>Field Mappings:</strong> Specifica dove posizionare i dati nel PDF (coordinate X, Y)</li>
                    <li><strong>JSONPath:</strong> Indica da dove prendere i dati (es: $.delegato.cognome)</li>
                </ul>
            </div>

            <ConfirmModal
                show={!!deleteTarget}
                onConfirm={confirmDeleteTemplate}
                onCancel={() => setDeleteTarget(null)}
                title="Elimina Template"
                message={`Sei sicuro di voler eliminare il template "${deleteTarget?.name}"?`}
                confirmText="Elimina"
                confirmVariant="danger"
            />
        </div>
    );
}

export default TemplateList;
