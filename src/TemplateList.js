import React, { useState, useEffect } from 'react';
import './TemplateEditor.css';

/**
 * Template List - Lista template per consultazione attiva
 * Permette di creare nuovi template o aprire l'editor
 */
function TemplateList({ client, onEditTemplate }) {
    const [templates, setTemplates] = useState([]);
    const [templateTypes, setTemplateTypes] = useState([]);
    const [consultazione, setConsultazione] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);
    const [showNewTemplateForm, setShowNewTemplateForm] = useState(false);
    const [newTemplate, setNewTemplate] = useState({
        name: '',
        template_type: '',
        description: '',
        file: null
    });

    useEffect(() => {
        loadConsultazioneAndTemplates();
        loadTemplateTypes();
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

        } catch (err) {
            setError(`Errore caricamento: ${err.message}`);
            console.error('Load error:', err);
        } finally {
            setLoading(false);
        }
    };

    const loadTemplateTypes = async () => {
        try {
            const data = await client.get('/api/documents/template-types/');
            setTemplateTypes(data || []);
            // Set default template_type if available
            if (data && data.length > 0 && !newTemplate.template_type) {
                setNewTemplate(prev => ({ ...prev, template_type: data[0].id }));
            }
        } catch (err) {
            console.error('Template types load error:', err);
            setError(`Errore caricamento tipi template: ${err.message}`);
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
            formData.append('template_file', newTemplate.file);
            formData.append('is_active', 'true');

            const created = await client.upload('/api/documents/templates/', formData);

            setSuccess(`Template "${created.name}" creato con successo!`);
            setTimeout(() => setSuccess(null), 3000);
            setShowNewTemplateForm(false);
            setNewTemplate({
                name: '',
                template_type: templateTypes.length > 0 ? templateTypes[0].id : '',
                description: '',
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

    const handleDeleteTemplate = async (template) => {
        if (!window.confirm(`Sei sicuro di voler eliminare il template "${template.name}"?`)) {
            return;
        }

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
            <div className="template-editor-header">
                <div>
                    <h2>Template PDF</h2>
                    {consultazione && (
                        <p className="text-muted">
                            Consultazione: <strong>{consultazione.nome}</strong>
                        </p>
                    )}
                </div>
                <div>
                    <button
                        onClick={() => setShowNewTemplateForm(true)}
                        className="btn btn-primary"
                        disabled={loading}
                    >
                        + Nuovo Template
                    </button>
                </div>
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
                                        onChange={(e) => setNewTemplate({...newTemplate, template_type: parseInt(e.target.value)})}
                                        required
                                    >
                                        <option value="">-- Seleziona tipo --</option>
                                        {templateTypes.map(tt => (
                                            <option key={tt.id} value={tt.id}>
                                                {tt.name}
                                            </option>
                                        ))}
                                    </select>
                                    {newTemplate.template_type && templateTypes.length > 0 && (
                                        <small className="text-muted d-block mt-1">
                                            {templateTypes.find(tt => tt.id === newTemplate.template_type)?.description}
                                        </small>
                                    )}
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
                    <table className="table table-striped">
                        <thead>
                            <tr>
                                <th>Nome</th>
                                <th>Tipo</th>
                                <th>Descrizione</th>
                                <th>Versione</th>
                                <th>Campi</th>
                                <th>Azioni</th>
                            </tr>
                        </thead>
                        <tbody>
                            {templates.map((template) => (
                                <tr key={template.id}>
                                    <td><strong>{template.name}</strong></td>
                                    <td>
                                        <span className="badge bg-info">
                                            {template.template_type_details?.name || template.template_type || 'N/A'}
                                        </span>
                                    </td>
                                    <td>{template.description || '-'}</td>
                                    <td>v{template.version}</td>
                                    <td>{template.field_mappings?.length || 0}</td>
                                    <td>
                                        <button
                                            onClick={() => onEditTemplate(template.id)}
                                            className="btn btn-primary btn-sm"
                                            style={{ marginRight: '5px' }}
                                        >
                                            Configura
                                        </button>
                                        <button
                                            onClick={() => handleDeleteTemplate(template)}
                                            className="btn btn-danger btn-sm"
                                            disabled={loading}
                                        >
                                            Elimina
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
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
        </div>
    );
}

export default TemplateList;
