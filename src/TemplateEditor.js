import React, { useState, useEffect, useRef } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import MarkdownModal from './MarkdownModal';
import './TemplateEditor.css';

// Configure PDF.js worker (use local worker from /public folder)
pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.js';

/**
 * Template Editor - Admin only
 * Visual PDF editor with click-to-place field mappings
 *
 * STATUS: Full visual editing with PDF.js
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
    const [showLoopGuide, setShowLoopGuide] = useState(false);
    const [newField, setNewField] = useState({
        jsonpath: '',
        type: 'text',
        x: 100,
        y: 100,
        width: 200,
        height: 20,
        page: 0
    });

    // PDF rendering state
    const [pdfDoc, setPdfDoc] = useState(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [numPages, setNumPages] = useState(0);
    const [scale, setScale] = useState(1.0);
    const canvasRef = useRef(null);

    // Interactive selection state
    const [isSelecting, setIsSelecting] = useState(false);
    const [selectionStart, setSelectionStart] = useState(null);
    const [currentSelection, setCurrentSelection] = useState(null);
    const renderTaskRef = useRef(null);
    const animationFrameRef = useRef(null);
    const canvasSnapshotRef = useRef(null);

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

    // Load and render PDF when template is loaded
    useEffect(() => {
        if (template?.template_file_url) {
            loadPDF(template.template_file_url);
        }
    }, [template]);

    // Re-render PDF when page or scale changes
    useEffect(() => {
        if (pdfDoc) {
            renderPage(currentPage);
        }
    }, [pdfDoc, currentPage, scale, fieldMappings]);

    // Draw selection overlay on canvas without re-rendering PDF
    useEffect(() => {
        if (!isSelecting || !currentSelection || !canvasRef.current || !canvasSnapshotRef.current) return;

        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');

        // Restore the saved canvas state
        ctx.putImageData(canvasSnapshotRef.current, 0, 0);

        // Draw selection on top
        const scaledSelection = {
            x: currentSelection.x * scale,
            y: currentSelection.y * scale,
            width: currentSelection.width * scale,
            height: currentSelection.height * scale
        };
        drawSelection(ctx, scaledSelection);
    }, [currentSelection, isSelecting]);

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

    const loadPDF = async (url) => {
        try {
            const loadingTask = pdfjsLib.getDocument(url);
            const pdf = await loadingTask.promise;
            setPdfDoc(pdf);
            setNumPages(pdf.numPages);
            setCurrentPage(1);
        } catch (err) {
            setError(`Errore caricamento PDF: ${err.message}`);
            console.error('PDF load error:', err);
        }
    };

    const renderPage = async (pageNum) => {
        if (!pdfDoc || !canvasRef.current) return;

        // Cancel previous render if in progress
        if (renderTaskRef.current) {
            renderTaskRef.current.cancel();
        }

        try {
            const page = await pdfDoc.getPage(pageNum);
            const canvas = canvasRef.current;
            const ctx = canvas.getContext('2d');
            const viewport = page.getViewport({ scale });

            canvas.width = viewport.width;
            canvas.height = viewport.height;

            // Render PDF page and store the task
            const renderTask = page.render({ canvasContext: ctx, viewport });
            renderTaskRef.current = renderTask;

            await renderTask.promise;
            renderTaskRef.current = null;

            // Draw existing field mappings as overlays
            drawFieldMappingsOverlay(ctx, pageNum - 1);

            // Save canvas snapshot for selection drawing
            canvasSnapshotRef.current = ctx.getImageData(0, 0, canvas.width, canvas.height);
        } catch (err) {
            if (err.name === 'RenderingCancelledException') {
                console.log('Render cancelled');
            } else {
                console.error('Page render error:', err);
            }
        }
    };

    const drawFieldMappingsOverlay = (ctx, pageIndex) => {
        const pageMappings = fieldMappings.filter(m => m.page === pageIndex);

        pageMappings.forEach((mapping, index) => {
            const { x, y, width, height } = mapping.area;
            const scaledX = x * scale;
            const scaledY = y * scale;
            const scaledWidth = width * scale;
            const scaledHeight = height * scale;

            // Draw rectangle
            ctx.strokeStyle = mapping.type === 'loop' ? '#ffc107' : '#0dcaf0';
            ctx.lineWidth = 2;
            ctx.strokeRect(scaledX, scaledY, scaledWidth, scaledHeight);

            // Fill with semi-transparent color
            ctx.fillStyle = mapping.type === 'loop' ? 'rgba(255, 193, 7, 0.2)' : 'rgba(13, 202, 240, 0.2)';
            ctx.fillRect(scaledX, scaledY, scaledWidth, scaledHeight);

            // Draw label
            ctx.fillStyle = '#000';
            ctx.font = '12px Arial';
            ctx.fillText(`${index + 1}. ${mapping.jsonpath}`, scaledX + 5, scaledY + 15);
        });
    };

    const drawSelection = (ctx, selection) => {
        ctx.strokeStyle = '#28a745';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.strokeRect(selection.x, selection.y, selection.width, selection.height);
        ctx.setLineDash([]);

        ctx.fillStyle = 'rgba(40, 167, 69, 0.1)';
        ctx.fillRect(selection.x, selection.y, selection.width, selection.height);
    };

    const handleCanvasMouseDown = (e) => {
        const canvas = canvasRef.current;
        const rect = canvas.getBoundingClientRect();

        // Convert mouse coordinates to canvas coordinates
        // Account for both canvas internal scale and CSS scaling
        const canvasX = (e.clientX - rect.left) * (canvas.width / rect.width);
        const canvasY = (e.clientY - rect.top) * (canvas.height / rect.height);

        // Convert to PDF coordinates (unscaled)
        const x = canvasX / scale;
        const y = canvasY / scale;

        setSelectionStart({ x, y });
        setCurrentSelection({ x, y, width: 0, height: 0 });
        setIsSelecting(true);
    };

    const handleCanvasMouseMove = (e) => {
        if (!isSelecting || !selectionStart) return;

        const canvas = canvasRef.current;
        const rect = canvas.getBoundingClientRect();

        // Convert mouse coordinates to canvas coordinates
        const canvasX = (e.clientX - rect.left) * (canvas.width / rect.width);
        const canvasY = (e.clientY - rect.top) * (canvas.height / rect.height);

        // Convert to PDF coordinates (unscaled)
        const currentX = canvasX / scale;
        const currentY = canvasY / scale;

        const width = currentX - selectionStart.x;
        const height = currentY - selectionStart.y;

        setCurrentSelection({
            x: width >= 0 ? selectionStart.x : currentX,
            y: height >= 0 ? selectionStart.y : currentY,
            width: Math.abs(width),
            height: Math.abs(height)
        });

        // Selection overlay will be drawn by effect
    };

    const handleCanvasMouseUp = () => {
        if (!isSelecting || !currentSelection) return;

        // If selection is too small, ignore it
        if (currentSelection.width < 10 || currentSelection.height < 10) {
            setIsSelecting(false);
            setCurrentSelection(null);
            setSelectionStart(null);
            // Restore canvas without selection
            if (canvasRef.current && canvasSnapshotRef.current) {
                const ctx = canvasRef.current.getContext('2d');
                ctx.putImageData(canvasSnapshotRef.current, 0, 0);
            }
            return;
        }

        // Open form with selection coordinates
        setNewField({
            ...newField,
            x: Math.round(currentSelection.x),
            y: Math.round(currentSelection.y),
            width: Math.round(currentSelection.width),
            height: Math.round(currentSelection.height),
            page: currentPage - 1
        });
        setShowNewFieldForm(true);

        // Keep selection visible until form is submitted/cancelled
        setIsSelecting(false);
        setSelectionStart(null);
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
        setCurrentSelection(null);
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

        // Re-render PDF to show new field overlay
        if (pdfDoc) {
            setTimeout(() => renderPage(currentPage), 100);
        }
    };

    const handleCancelNewField = () => {
        setShowNewFieldForm(false);
        setCurrentSelection(null);
        setNewField({
            jsonpath: '',
            type: 'text',
            x: 100,
            y: 100,
            width: 200,
            height: 20,
            page: 0
        });

        // Restore canvas without selection
        if (canvasRef.current && canvasSnapshotRef.current) {
            const ctx = canvasRef.current.getContext('2d');
            ctx.putImageData(canvasSnapshotRef.current, 0, 0);
        }
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
                                    <label>
                                        JSONPath *
                                        <button
                                            type="button"
                                            onClick={() => setShowLoopGuide(true)}
                                            style={{
                                                marginLeft: '10px',
                                                fontSize: '0.9em',
                                                background: 'none',
                                                border: 'none',
                                                color: '#0d6efd',
                                                cursor: 'pointer',
                                                textDecoration: 'underline'
                                            }}
                                        >
                                            📖 Guida Loop & JSONPath
                                        </button>
                                    </label>
                                    <input
                                        type="text"
                                        className="form-control"
                                        value={newField.jsonpath}
                                        onChange={(e) => setNewField({...newField, jsonpath: e.target.value})}
                                        placeholder='es: $.delegato.cognome + " " + $.delegato.nome'
                                        required
                                    />
                                    <small className="text-muted">
                                        <strong>Semplice:</strong> <code>$.delegato.cognome</code><br/>
                                        <strong>Concatenato:</strong> <code>$.cognome + " " + $.nome</code><br/>
                                        <strong>Loop:</strong> <code>$.designazioni</code> (array)
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
                                        onClick={handleCancelNewField}
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
                {/* PDF Interactive Canvas */}
                <div className="pdf-preview-section">
                    <div className="pdf-controls">
                        <h3>Editor Visuale PDF</h3>
                        {pdfDoc && (
                            <div className="pdf-navigation">
                                <button
                                    className="btn btn-secondary btn-sm"
                                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                                    disabled={currentPage === 1}
                                >
                                    ← Pagina precedente
                                </button>
                                <span className="page-indicator">
                                    Pagina {currentPage} di {numPages}
                                </span>
                                <button
                                    className="btn btn-secondary btn-sm"
                                    onClick={() => setCurrentPage(Math.min(numPages, currentPage + 1))}
                                    disabled={currentPage === numPages}
                                >
                                    Pagina successiva →
                                </button>
                                <div className="zoom-controls">
                                    <button
                                        className="btn btn-secondary btn-sm"
                                        onClick={() => setScale(Math.max(0.5, scale - 0.1))}
                                    >
                                        −
                                    </button>
                                    <span className="zoom-level">{Math.round(scale * 100)}%</span>
                                    <button
                                        className="btn btn-secondary btn-sm"
                                        onClick={() => setScale(Math.min(2.0, scale + 0.1))}
                                    >
                                        +
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>

                    {pdfDoc ? (
                        <div className="pdf-canvas-container">
                            <canvas
                                ref={canvasRef}
                                onMouseDown={handleCanvasMouseDown}
                                onMouseMove={handleCanvasMouseMove}
                                onMouseUp={handleCanvasMouseUp}
                                style={{
                                    border: '1px solid #dee2e6',
                                    cursor: isSelecting ? 'crosshair' : 'pointer',
                                    display: 'block'
                                }}
                            />
                            <div className="pdf-instructions">
                                <p><strong>💡 Istruzioni:</strong></p>
                                <ul>
                                    <li>Clicca e trascina sul PDF per selezionare un'area</li>
                                    <li>Le aree blu sono campi di tipo "text"</li>
                                    <li>Le aree gialle sono campi di tipo "loop"</li>
                                    <li>Dopo la selezione, compila il form per definire il campo</li>
                                </ul>
                            </div>
                        </div>
                    ) : (
                        <div className="pdf-placeholder">
                            <p>📄 {template?.template_file_url ? 'Caricamento PDF...' : 'Nessun template selezionato'}</p>
                            {template?.template_file_url && (
                                <p className="text-muted">
                                    Se il caricamento non parte, verifica che il file PDF sia accessibile
                                </p>
                            )}
                        </div>
                    )}
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
                <h4>💡 Come funziona l'Editor Visuale</h4>
                <ul>
                    <li><strong>Selezione Visuale:</strong> Clicca e trascina sul PDF per definire un'area campo</li>
                    <li><strong>JSONPath:</strong> Specifica da dove prendere i dati (es: <code>$.delegato.cognome</code>)</li>
                    <li><strong>Tipo text:</strong> Campo semplice, una riga di testo (overlay blu)</li>
                    <li><strong>Tipo loop:</strong> Lista di elementi ripetuti (overlay giallo)</li>
                    <li><strong>Navigazione:</strong> Usa i controlli per cambiare pagina e zoom</li>
                    <li><strong>Modifica:</strong> Rimuovi campi dalla tabella e ricrea con nuova selezione</li>
                </ul>

                <div className="alert alert-success mt-3">
                    <strong>✅ Editor Visuale Attivo</strong>
                    <p>Questo editor usa PDF.js per rendering interattivo. Puoi cliccare direttamente sul PDF per posizionare i campi!</p>
                    <p><strong>Workflow:</strong> Seleziona area → Compila form → Salva configurazione → Testa generazione PDF</p>
                </div>
            </div>

            {/* Markdown Guide Modal */}
            <MarkdownModal
                isOpen={showLoopGuide}
                onClose={() => setShowLoopGuide(false)}
                markdownUrl="/LOOP_GUIDE.md"
                title="📚 Guida Loop & JSONPath"
            />
        </div>
    );
}

export default TemplateEditor;
