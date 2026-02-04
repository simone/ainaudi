import React, { useState, useEffect } from 'react';
import './TemplateEditor.css';

/**
 * Template Editor - Admin only
 * Allows visual configuration of PDF templates without code changes
 *
 * STATUS: Basic implementation - needs PDF.js for visual editing
 */
function TemplateEditor({ templateId: initialTemplateId, client }) {
    const [templates, setTemplates] = useState([]);
    const [selectedTemplateId, setSelectedTemplateId] = useState(initialTemplateId || null);
    const [template, setTemplate] = useState(null);
    const [fieldMappings, setFieldMappings] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);
    const [showNewTemplateForm, setShowNewTemplateForm] = useState(false);
    const [newTemplate, setNewTemplate] = useState({
        name: '',
        template_type: 'DELEGATION',
        description: '',
        file: null
    });
    const [showNewFieldForm, setShowNewFieldForm] = useState(false);
    const [newField, setNewField] = useState({
        jsonpath: '',
        type: 'text',
        x: 100,
        y: 100,
        width: 200,
        height: 20,
        page: 0
    });

    // Load available templates on mount
    useEffect(() => {
        loadTemplates();
    }, []);

    // Load specific template when selected
    useEffect(() => {
        if (selectedTemplateId) {
            loadTemplate(selectedTemplateId);
        }
    }, [selectedTemplateId]);

    const loadTemplates = async () => {
        try {
            const data = await client.get('/api/documents/templates/');
            setTemplates(data || []);
            // Auto-select first template if none selected
            if (!selectedTemplateId && data && data.length > 0) {
                setSelectedTemplateId(data[0].id);
            }
        } catch (err) {
            setError(`Errore caricamento lista template: ${err.message}`);
            console.error('Templates list error:', err);
        }
    };

    const loadTemplate = async (id) => {
        try {
            setLoading(true);
            setError(null);
            const data = await client.get(`/api/documents/templates/${id}/editor/`);
            setTemplate(data);
            setFieldMappings(data.field_mappings || []);
        } catch (err) {
            setError(`Errore caricamento template: ${err.message}`);
            console.error('Template load error:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleAddField = () => {
        setShowNewFieldForm(true);
    };

    const handleSaveNewField = (e) => {
        e.preventDefault();

        if (!newField.jsonpath) {
            setError('JSONPath è obbligatorio');
            return;
        }

        const newMapping = {
            area: {
                x: parseInt(newField.x),
                y: parseInt(newField.y),
                width: parseInt(newField.width),
                height: parseInt(newField.height)
            },
            jsonpath: newField.jsonpath,
            type: newField.type,
            page: parseInt(newField.page)
        };

        setFieldMappings([...fieldMappings, newMapping]);
        setShowNewFieldForm(false);
        setNewField({
            jsonpath: '',
            type: 'text',
            x: 100,
            y: 100,
            width: 200,
            height: 20,
            page: 0
        });
        setSuccess('Campo aggiunto!');
        setTimeout(() => setSuccess(null), 2000);
    };

    const handleRemoveField = (index) => {
        setFieldMappings(fieldMappings.filter((_, i) => i !== index));
    };

    const handleSave = async () => {
        if (!selectedTemplateId) {
            setError('Seleziona un template prima di salvare');
            return;
        }

        try {
            setLoading(true);
            setError(null);

            await client.put(`/api/documents/templates/${selectedTemplateId}/editor/`, {
                field_mappings: fieldMappings,
                loop_config: template.loop_config,
                merge_mode: template.merge_mode
            });

            setSuccess('Template salvato con successo!');
            setTimeout(() => setSuccess(null), 3000);
        } catch (err) {
            setError(`Errore salvataggio: ${err.message}`);
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

        try {
            setLoading(true);
            setError(null);

            // Upload file using FormData
            const formData = new FormData();
            formData.append('name', newTemplate.name);
            formData.append('template_type', newTemplate.template_type);
            formData.append('description', newTemplate.description);
            formData.append('template_file', newTemplate.file);
            formData.append('is_active', 'true');

            const created = await client.upload('/api/documents/templates/', formData);

            setSuccess('Template creato con successo!');
            setShowNewTemplateForm(false);
            setNewTemplate({ name: '', template_type: 'DELEGATION', description: '', file: null });

            // Reload templates and select new one
            await loadTemplates();
            setSelectedTemplateId(created.id);

        } catch (err) {
            setError(`Errore creazione template: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteTemplate = async () => {
        if (!selectedTemplateId) return;

        if (!window.confirm(`Sei sicuro di voler eliminare il template "${template?.name}"?`)) {
            return;
        }

        try {
            setLoading(true);
            setError(null);

            await client.delete(`/api/documents/templates/${selectedTemplateId}/`);

            setSuccess('Template eliminato!');
            setTimeout(() => setSuccess(null), 3000);

            // Reload templates
            setSelectedTemplateId(null);
            setTemplate(null);
            await loadTemplates();

        } catch (err) {
            setError(`Errore eliminazione: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    if (loading && !template && templates.length === 0) {
        return <div className="template-editor-loading">Caricamento template...</div>;
    }

    if (templates.length === 0 && !loading) {
        return (
            <div className="template-editor">
                <div className="alert alert-warning">
                    <h4>Nessun Template Disponibile</h4>
                    <p>Non ci sono template configurati nel sistema.</p>
                    <p>Crea prima un template dal pannello admin Django oppure tramite API.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="template-editor">
            <div className="template-editor-header">
                <div>
                    <h2>Editor Template PDF</h2>
                    {templates.length > 0 && (
                        <div className="template-selector">
                            <label htmlFor="template-select">Seleziona Template: </label>
                            <select
                                id="template-select"
                                value={selectedTemplateId || ''}
                                onChange={(e) => setSelectedTemplateId(parseInt(e.target.value))}
                                className="form-control"
                                style={{ display: 'inline-block', width: 'auto', marginLeft: '10px' }}
                            >
                                {templates.map(t => (
                                    <option key={t.id} value={t.id}>
                                        {t.name} ({t.template_type})
                                    </option>
                                ))}
                            </select>
                        </div>
                    )}
                </div>
                <div style={{ display: 'flex', gap: '10px' }}>
                    <button
                        onClick={() => setShowNewTemplateForm(true)}
                        className="btn btn-primary"
                    >
                        + Nuovo Template
                    </button>
                    {selectedTemplateId && (
                        <>
                            <button
                                onClick={handleSave}
                                disabled={loading}
                                className="btn btn-success"
                            >
                                {loading ? 'Salvataggio...' : 'Salva Configurazione'}
                            </button>
                            <button
                                onClick={handleDeleteTemplate}
                                disabled={loading}
                                className="btn btn-danger"
                            >
                                Elimina
                            </button>
                        </>
                    )}
                </div>
            </div>

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
                                        placeholder="es: individuale"
                                        required
                                    />
                                </div>

                                <div className="form-group">
                                    <label>Tipo Template *</label>
                                    <select
                                        className="form-control"
                                        value={newTemplate.template_type}
                                        onChange={(e) => setNewTemplate({...newTemplate, template_type: e.target.value})}
                                    >
                                        <option value="DELEGATION">Delega Sub-Delegato</option>
                                        <option value="DESIGNATION">Designazione RDL</option>
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
                                            setNewTemplate({ name: '', template_type: 'DELEGATION', description: '', file: null });
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

            {/* Form Nuovo Campo */}
            {showNewFieldForm && (
                <div className="new-template-form">
                    <div className="card">
                        <div className="card-header">
                            <h3>Aggiungi Campo</h3>
                        </div>
                        <div className="card-body">
                            <form onSubmit={handleSaveNewField}>
                                <div className="form-group">
                                    <label>JSONPath *</label>
                                    <input
                                        type="text"
                                        className="form-control"
                                        value={newField.jsonpath}
                                        onChange={(e) => setNewField({...newField, jsonpath: e.target.value})}
                                        placeholder="es: $.delegato.cognome"
                                        required
                                    />
                                    <small className="text-muted">
                                        Percorso del dato (inizia con $.)
                                    </small>
                                </div>

                                <div className="form-group">
                                    <label>Tipo Campo *</label>
                                    <select
                                        className="form-control"
                                        value={newField.type}
                                        onChange={(e) => setNewField({...newField, type: e.target.value})}
                                    >
                                        <option value="text">Text (campo singolo)</option>
                                        <option value="loop">Loop (lista elementi)</option>
                                    </select>
                                </div>

                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                                    <div className="form-group">
                                        <label>X (coordinate orizzontale)</label>
                                        <input
                                            type="number"
                                            className="form-control"
                                            value={newField.x}
                                            onChange={(e) => setNewField({...newField, x: e.target.value})}
                                            min="0"
                                            required
                                        />
                                    </div>

                                    <div className="form-group">
                                        <label>Y (coordinate verticale)</label>
                                        <input
                                            type="number"
                                            className="form-control"
                                            value={newField.y}
                                            onChange={(e) => setNewField({...newField, y: e.target.value})}
                                            min="0"
                                            required
                                        />
                                    </div>

                                    <div className="form-group">
                                        <label>Larghezza (Width)</label>
                                        <input
                                            type="number"
                                            className="form-control"
                                            value={newField.width}
                                            onChange={(e) => setNewField({...newField, width: e.target.value})}
                                            min="1"
                                            required
                                        />
                                    </div>

                                    <div className="form-group">
                                        <label>Altezza (Height)</label>
                                        <input
                                            type="number"
                                            className="form-control"
                                            value={newField.height}
                                            onChange={(e) => setNewField({...newField, height: e.target.value})}
                                            min="1"
                                            required
                                        />
                                    </div>
                                </div>

                                <div className="form-group">
                                    <label>Pagina</label>
                                    <input
                                        type="number"
                                        className="form-control"
                                        value={newField.page}
                                        onChange={(e) => setNewField({...newField, page: e.target.value})}
                                        min="0"
                                    />
                                    <small className="text-muted">
                                        Numero pagina (0 = prima pagina)
                                    </small>
                                </div>

                                <div className="form-actions">
                                    <button type="submit" className="btn btn-success">
                                        Aggiungi Campo
                                    </button>
                                    <button
                                        type="button"
                                        className="btn btn-secondary"
                                        onClick={() => {
                                            setShowNewFieldForm(false);
                                            setNewField({
                                                jsonpath: '',
                                                type: 'text',
                                                x: 100,
                                                y: 100,
                                                width: 200,
                                                height: 20,
                                                page: 0
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

            {error && (
                <div className="alert alert-danger">{error}</div>
            )}

            {success && (
                <div className="alert alert-success">{success}</div>
            )}

            <div className="template-editor-content">
                {/* PDF Preview Section - Requires PDF.js integration */}
                <div className="pdf-preview-section">
                    <h3>Preview PDF</h3>
                    <div className="pdf-placeholder">
                        <p>📄 Template: {template?.template_file_url || 'Nessun file caricato'}</p>
                        <p className="text-muted">
                            <strong>Nota:</strong> Per l'editing visuale completo, serve integrazione con PDF.js
                        </p>
                        <p className="text-muted">
                            Al momento puoi configurare i campi manualmente usando i pulsanti sotto.
                        </p>
                    </div>
                </div>

                {/* Field Mappings List */}
                <div className="field-mappings-section">
                    <div className="field-mappings-header">
                        <h3>Campi Configurati ({fieldMappings.length})</h3>
                        <button
                            onClick={handleAddField}
                            className="btn btn-primary btn-sm"
                        >
                            + Aggiungi Campo
                        </button>
                    </div>

                    {fieldMappings.length === 0 ? (
                        <div className="no-fields">
                            <p>Nessun campo configurato.</p>
                            <p className="text-muted">
                                Clicca "Aggiungi Campo" per iniziare.
                            </p>
                        </div>
                    ) : (
                        <table className="table table-striped">
                            <thead>
                                <tr>
                                    <th>JSONPath</th>
                                    <th>Tipo</th>
                                    <th>Posizione</th>
                                    <th>Dimensioni</th>
                                    <th>Azioni</th>
                                </tr>
                            </thead>
                            <tbody>
                                {fieldMappings.map((mapping, index) => (
                                    <tr key={index}>
                                        <td><code>{mapping.jsonpath}</code></td>
                                        <td>
                                            <span className={`badge ${mapping.type === 'loop' ? 'bg-warning' : 'bg-info'}`}>
                                                {mapping.type}
                                            </span>
                                        </td>
                                        <td>x:{mapping.area.x}, y:{mapping.area.y}</td>
                                        <td>{mapping.area.width}×{mapping.area.height}</td>
                                        <td>
                                            <button
                                                onClick={() => handleRemoveField(index)}
                                                className="btn btn-danger btn-sm"
                                            >
                                                Rimuovi
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>

                {/* Configuration Section */}
                <div className="template-config-section">
                    <h3>Configurazione Template</h3>

                    <div className="form-group">
                        <label>Modalità Unione:</label>
                        <select
                            value={template?.merge_mode || 'SINGLE_DOC_PER_RECORD'}
                            onChange={(e) => setTemplate({...template, merge_mode: e.target.value})}
                            className="form-control"
                        >
                            <option value="SINGLE_DOC_PER_RECORD">
                                Un documento per record (es. un PDF per ogni Delegato)
                            </option>
                            <option value="MULTI_PAGE_LOOP">
                                Documento multi-pagina con loop (es. un PDF con tutti i Delegati)
                            </option>
                        </select>
                    </div>

                    {template?.merge_mode === 'MULTI_PAGE_LOOP' && (
                        <div className="loop-config">
                            <h4>Configurazione Loop</h4>
                            <div className="form-group">
                                <label>Righe prima pagina:</label>
                                <input
                                    type="number"
                                    className="form-control"
                                    value={template?.loop_config?.rows_first_page || 6}
                                    onChange={(e) => setTemplate({
                                        ...template,
                                        loop_config: {
                                            ...template.loop_config,
                                            rows_first_page: parseInt(e.target.value)
                                        }
                                    })}
                                />
                            </div>
                            <div className="form-group">
                                <label>Righe per pagina successiva:</label>
                                <input
                                    type="number"
                                    className="form-control"
                                    value={template?.loop_config?.rows_per_page || 13}
                                    onChange={(e) => setTemplate({
                                        ...template,
                                        loop_config: {
                                            ...template.loop_config,
                                            rows_per_page: parseInt(e.target.value)
                                        }
                                    })}
                                />
                            </div>
                        </div>
                    )}
                </div>
            </div>

            <div className="template-editor-footer">
                <button
                    onClick={handleSave}
                    disabled={loading}
                    className="btn btn-success btn-lg"
                >
                    {loading ? 'Salvataggio...' : 'Salva Configurazione'}
                </button>
            </div>

            <div className="template-editor-help">
                <h4>💡 Come funziona</h4>
                <ul>
                    <li><strong>JSONPath:</strong> Specifica da dove prendere i dati (es: <code>$.delegato.cognome</code>)</li>
                    <li><strong>Tipo text:</strong> Campo semplice, una riga di testo</li>
                    <li><strong>Tipo loop:</strong> Lista di elementi ripetuti (es: lista designazioni)</li>
                    <li><strong>Posizione:</strong> Coordinate x,y sulla pagina PDF</li>
                    <li><strong>Dimensioni:</strong> Larghezza e altezza dell'area</li>
                </ul>

                <div className="alert alert-info mt-3">
                    <strong>⚠️ Versione Semplificata</strong>
                    <p>Questa è una versione base dell'editor che richiede input manuale delle coordinate.</p>
                    <p>Per l'editing visuale completo (click sul PDF per posizionare i campi),
                       è necessario integrare la libreria PDF.js come descritto in
                       <code>IMPLEMENTATION_SUMMARY.md</code>.</p>
                </div>
            </div>
        </div>
    );
}

export default TemplateEditor;
