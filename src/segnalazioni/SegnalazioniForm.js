import React, { useState, useEffect, useRef } from 'react';
import './SegnalazioniStyles.css';

function SegnalazioniForm({
    client,
    consultazione,
    userSezioni,
    initialData = null,
    onSubmit,
    onCancel,
}) {
    const [formData, setFormData] = useState({
        title: initialData?.title || '',
        description: initialData?.description || '',
        category: initialData?.category || 'TECHNICAL',
        severity: initialData?.severity || 'MEDIUM',
        sezione: initialData?.sezione || (userSezioni?.length === 1 ? userSezioni[0].id : ''),
        occurred_at: initialData?.occurred_at ? initialData.occurred_at.split('T')[0] : '',
        is_verbalizzato: initialData?.is_verbalizzato || false,
    });

    const [files, setFiles] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [dragOver, setDragOver] = useState(false);
    const fileInputRef = useRef(null);

    const categoryOptions = [
        { value: 'PROCEDURAL', label: 'Procedurale' },
        { value: 'ACCESS', label: 'Accesso al seggio' },
        { value: 'MATERIALS', label: 'Materiali' },
        { value: 'INTIMIDATION', label: 'Intimidazione' },
        { value: 'IRREGULARITY', label: 'Irregolarità' },
        { value: 'TECHNICAL', label: 'Tecnico' },
        { value: 'OTHER', label: 'Altro' },
    ];

    const severityOptions = [
        { value: 'LOW', label: 'Bassa' },
        { value: 'MEDIUM', label: 'Media' },
        { value: 'HIGH', label: 'Alta' },
        { value: 'CRITICAL', label: 'Critica' },
    ];

    // Get sezioni for RDL user
    const sezioniArray = Array.isArray(userSezioni) ? userSezioni : (userSezioni?.results || []);
    const sezioniOptions = sezioniArray || [];
    const isSingolaSezione = sezioniOptions.length === 1;

    const verbalizzazioneTemplates = {
        PROCEDURAL: 'Procedura irregolare segnalata presso la sezione. È necessario verificare il protocollo d\'apertura dei seggi.',
        ACCESS: 'Accesso al seggio irregolare. Persone non autorizzate hanno accesso all\'area di voto.',
        MATERIALS: 'Materiali di voto insufficienti o mancanti. Le schede/materiali necessari non sono disponibili.',
        IRREGULARITY: 'Irregolarità rilevata durante le operazioni di voto. Consultare il verbale ufficiale per i dettagli.',
        TECHNICAL: 'Problema tecnico con la piattaforma AInaudi segnalato. Verificare la connessione e riprovare.',
        OTHER: 'Altra segnalazione riguardante lo svolgimento delle operazioni elettorali.',
    };

    const handleFormChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData({
            ...formData,
            [name]: type === 'checkbox' ? checked : value,
        });
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        setDragOver(true);
    };

    const handleDragLeave = () => {
        setDragOver(false);
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setDragOver(false);
        const droppedFiles = Array.from(e.dataTransfer.files);
        addFiles(droppedFiles);
    };

    const handleFileInputChange = (e) => {
        const selectedFiles = Array.from(e.target.files);
        addFiles(selectedFiles);
    };

    const addFiles = (newFiles) => {
        setFiles([...files, ...newFiles]);
    };

    const removeFile = (index) => {
        setFiles(files.filter((_, i) => i !== index));
    };

    const copyTemplateToDescription = (template) => {
        setFormData({
            ...formData,
            description: formData.description ? `${formData.description}\n\n${template}` : template,
        });
    };

    const formatFileSize = (bytes) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);
        setIsLoading(true);

        try {
            // Create incident
            const incidentData = {
                consultazione: consultazione.id,
                sezione: formData.sezione || null,
                title: formData.title,
                description: formData.description,
                category: formData.category,
                severity: formData.severity,
                occurred_at: formData.occurred_at || null,
                is_verbalizzato: formData.is_verbalizzato,
            };

            const response = await client.incidents.create(incidentData);
            const incidentId = response.id;

            // Upload files
            if (files.length > 0) {
                for (const file of files) {
                    const fileFormData = new FormData();
                    fileFormData.append('incident', incidentId);
                    fileFormData.append('file', file);
                    fileFormData.append('description', file.name);

                    await client.incidents.uploadAttachment(fileFormData);
                }
            }

            // Callback
            if (onSubmit) {
                onSubmit(response);
            }
        } catch (err) {
            console.error('Error creating incident:', err);
            setError(err.message || 'Errore nella creazione della segnalazione');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <form className="segnalazioni-form-container" onSubmit={handleSubmit}>
            {error && (
                <div className="alert alert-danger" role="alert">
                    <i className="fas fa-exclamation-circle me-2"></i>
                    {error}
                </div>
            )}

            {/* Informazioni Base */}
            <div className="form-section">
                <div className="form-section-title">
                    <i className="fas fa-info-circle"></i>
                    Informazioni di base
                </div>

                <div className="form-group">
                    <label htmlFor="title">Titolo *</label>
                    <input
                        type="text"
                        id="title"
                        name="title"
                        value={formData.title}
                        onChange={handleFormChange}
                        required
                        maxLength="200"
                        placeholder="Breve descrizione della segnalazione"
                    />
                    <div className="form-helper">
                        Titolo della segnalazione (max 200 caratteri)
                    </div>
                </div>

                <div className="form-group">
                    <label htmlFor="description">Descrizione dettagliata *</label>
                    <textarea
                        id="description"
                        name="description"
                        value={formData.description}
                        onChange={handleFormChange}
                        required
                        placeholder="Descrivi nel dettaglio cosa è accaduto..."
                    />
                    <div className="form-helper">
                        Fornisci una descrizione dettagliata dell'incidente
                    </div>
                </div>

                <div className="form-group-row">
                    <div className="form-group">
                        <label htmlFor="category">Categoria *</label>
                        <select
                            id="category"
                            name="category"
                            value={formData.category}
                            onChange={handleFormChange}
                            required
                        >
                            {categoryOptions.map((opt) => (
                                <option key={opt.value} value={opt.value}>
                                    {opt.label}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="form-group">
                        <label htmlFor="severity">Gravità *</label>
                        <select
                            id="severity"
                            name="severity"
                            value={formData.severity}
                            onChange={handleFormChange}
                            required
                        >
                            {severityOptions.map((opt) => (
                                <option key={opt.value} value={opt.value}>
                                    {opt.label}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>

                <div className="form-group-row">
                    <div className="form-group">
                        <label htmlFor="occurred_at">Data/Ora dell'incidente</label>
                        <input
                            type="datetime-local"
                            id="occurred_at"
                            name="occurred_at"
                            value={formData.occurred_at}
                            onChange={handleFormChange}
                        />
                        <div className="form-helper">
                            Quando è avvenuto l'incidente
                        </div>
                    </div>

                    <div className="form-group">
                        <label htmlFor="sezione">Sezione Elettorale</label>
                        <select
                            id="sezione"
                            name="sezione"
                            value={formData.sezione}
                            onChange={handleFormChange}
                            disabled={isSingolaSezione}
                            className={isSingolaSezione ? 'read-only' : ''}
                        >
                            <option value="">Generale (non specifico a sezione)</option>
                            {sezioniOptions.map((sezione) => (
                                <option key={sezione.id} value={sezione.id}>
                                    Sezione {sezione.numero} - {sezione.comune}
                                </option>
                            ))}
                        </select>
                        {isSingolaSezione && (
                            <div className="form-helper">
                                Sei assegnato a una sola sezione. Il valore è fisso.
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Verbalizzazione Panel - Only if sezione is selected */}
            {formData.sezione && (
                <div className="form-section">
                    <div className="verbalizzazione-panel">
                        <div className="verbalizzazione-panel-title">
                            <i className="fas fa-pen-fancy"></i>
                            Come segnalare efficacemente nel registro
                        </div>
                        <div className="verbalizzazione-template">
                            {verbalizzazioneTemplates[formData.category] ||
                                verbalizzazioneTemplates.OTHER}
                        </div>
                        <button
                            type="button"
                            className="verbalizzazione-copy-btn"
                            onClick={() =>
                                copyTemplateToDescription(
                                    verbalizzazioneTemplates[formData.category] ||
                                    verbalizzazioneTemplates.OTHER
                                )
                            }
                        >
                            <i className="fas fa-copy me-1"></i>
                            Copia nella descrizione
                        </button>

                        <div className="verbalizzazione-checkbox">
                            <input
                                type="checkbox"
                                id="is_verbalizzato"
                                name="is_verbalizzato"
                                checked={formData.is_verbalizzato}
                                onChange={handleFormChange}
                            />
                            <label htmlFor="is_verbalizzato">
                                <i className="fas fa-check-circle me-1"></i>
                                Questa segnalazione è stata verbalizzata nel registro di sezione
                            </label>
                        </div>
                    </div>
                </div>
            )}

            {/* Allegati */}
            <div className="form-section">
                <div className="form-section-title">
                    <i className="fas fa-paperclip"></i>
                    Allegati (foto, documenti)
                </div>

                <div
                    className={`file-upload-area ${dragOver ? 'drag-over' : ''}`}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                >
                    <i className="fas fa-cloud-upload-alt"></i>
                    <p>
                        Trascina i file qui oppure{' '}
                        <span className="file-upload-area-highlight">clicca per selezionare</span>
                    </p>
                    <input
                        ref={fileInputRef}
                        type="file"
                        multiple
                        className="file-upload-input"
                        onChange={handleFileInputChange}
                        accept="image/*,.pdf,.doc,.docx,.txt,.mp4,.webm"
                    />
                </div>

                {files.length > 0 && (
                    <ul className="file-list">
                        {files.map((file, index) => (
                            <li key={index} className="file-item">
                                <div className="file-item-info">
                                    <div className="file-item-icon">
                                        {file.type.startsWith('image/') ? (
                                            <i className="fas fa-image"></i>
                                        ) : (
                                            <i className="fas fa-file"></i>
                                        )}
                                    </div>
                                    <div className="file-item-details">
                                        <div className="file-item-name">{file.name}</div>
                                        <div className="file-item-size">
                                            {formatFileSize(file.size)}
                                        </div>
                                    </div>
                                </div>
                                <button
                                    type="button"
                                    className="file-item-remove"
                                    onClick={() => removeFile(index)}
                                >
                                    <i className="fas fa-trash me-1"></i>
                                    Rimuovi
                                </button>
                            </li>
                        ))}
                    </ul>
                )}
            </div>

            {/* Submit Buttons */}
            <div className="form-section" style={{ borderBottom: 'none', paddingBottom: 0 }}>
                <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                    <button
                        type="button"
                        className="segnalazioni-btn segnalazioni-btn-secondary"
                        onClick={onCancel}
                        disabled={isLoading}
                    >
                        Annulla
                    </button>
                    <button
                        type="submit"
                        className="segnalazioni-btn segnalazioni-btn-primary"
                        disabled={isLoading || !formData.title || !formData.description}
                    >
                        {isLoading ? (
                            <>
                                <span className="loading-spinner" style={{ marginRight: '8px' }}></span>
                                Invio in corso...
                            </>
                        ) : (
                            <>
                                <i className="fas fa-paper-plane me-1"></i>
                                Crea Segnalazione
                            </>
                        )}
                    </button>
                </div>
            </div>
        </form>
    );
}

export default SegnalazioniForm;
