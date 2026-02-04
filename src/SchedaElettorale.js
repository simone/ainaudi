import React, { useState, useEffect } from 'react';

/**
 * Componente per visualizzare e modificare i dettagli di una scheda elettorale.
 * Mostra informazioni diverse in base al tipo di elezione.
 */
function SchedaElettorale({ scheda, client, onClose, onUpdate }) {
    const [isEditing, setIsEditing] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);
    const [formData, setFormData] = useState({
        nome: '',
        colore: '',
        ordine: 0,
        turno: 1,
        data_inizio_turno: '',
        testo_quesito: '',
        schema_voti: '',
    });

    useEffect(() => {
        if (scheda) {
            setFormData({
                nome: scheda.nome || '',
                colore: scheda.colore || '',
                ordine: scheda.ordine || 0,
                turno: scheda.turno || 1,
                data_inizio_turno: scheda.data_inizio_turno || '',
                testo_quesito: scheda.testo_quesito || '',
                schema_voti: typeof scheda.schema_voti === 'object'
                    ? JSON.stringify(scheda.schema_voti, null, 2)
                    : (scheda.schema_voti || ''),
            });
        }
    }, [scheda]);

    if (!scheda) return null;

    const getTipoLabel = (tipo) => {
        const tipi = {
            'REFERENDUM': 'Referendum',
            'EUROPEE': 'Elezioni Europee',
            'POLITICHE_CAMERA': 'Elezioni Politiche - Camera',
            'POLITICHE_SENATO': 'Elezioni Politiche - Senato',
            'REGIONALI': 'Elezioni Regionali',
            'COMUNALI': 'Elezioni Comunali',
            'MUNICIPALI': 'Elezioni Municipali',
        };
        return tipi[tipo] || tipo;
    };

    const isReferendum = scheda.tipo === 'REFERENDUM';
    // Il turno/ballottaggio è previsto solo per elezioni comunali con comuni > 15.000 abitanti
    const supportsBallottaggio = scheda.tipo === 'COMUNALI' || scheda.tipo === 'MUNICIPALI';

    const handleChange = (field, value) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    const handleSave = async () => {
        setSaving(true);
        setError(null);

        try {
            // Prepara i dati per il salvataggio
            const dataToSave = {
                nome: formData.nome,
                colore: formData.colore,
                ordine: parseInt(formData.ordine) || 0,
                turno: parseInt(formData.turno) || 1,
                data_inizio_turno: formData.data_inizio_turno || null,
            };

            if (isReferendum) {
                dataToSave.testo_quesito = formData.testo_quesito;
            } else if (formData.schema_voti) {
                try {
                    dataToSave.schema_voti = JSON.parse(formData.schema_voti);
                } catch (e) {
                    // Se non è JSON valido, salva come stringa
                    dataToSave.schema_voti = formData.schema_voti;
                }
            }

            const result = await client.election.updateBallot(scheda.id, dataToSave);

            if (result.error) {
                setError(result.error);
            } else {
                setIsEditing(false);
                // Notifica il parent che la scheda è stata aggiornata
                if (onUpdate) {
                    onUpdate({ ...scheda, ...result });
                }
            }
        } catch (err) {
            setError('Errore nel salvataggio');
        }

        setSaving(false);
    };

    const handleCancel = () => {
        // Reset form data
        setFormData({
            nome: scheda.nome || '',
            colore: scheda.colore || '',
            ordine: scheda.ordine || 0,
            turno: scheda.turno || 1,
            data_inizio_turno: scheda.data_inizio_turno || '',
            testo_quesito: scheda.testo_quesito || '',
            schema_voti: typeof scheda.schema_voti === 'object'
                ? JSON.stringify(scheda.schema_voti, null, 2)
                : (scheda.schema_voti || ''),
        });
        setIsEditing(false);
        setError(null);
    };

    // Colori predefiniti per le schede
    const coloriPredefiniti = [
        { nome: 'Verde chiaro', valore: '#90EE90' },
        { nome: 'Rosa', valore: '#FFB6C1' },
        { nome: 'Giallo', valore: '#FFFF99' },
        { nome: 'Azzurro', valore: '#87CEEB' },
        { nome: 'Arancione', valore: '#FFA500' },
        { nome: 'Lilla', valore: '#DDA0DD' },
        { nome: 'Grigio', valore: '#D3D3D3' },
    ];

    return (
        <div className="scheda-elettorale">
            {/* Page Header */}
            <div className="page-header consultazione">
                <div className="page-header-title">
                    <i className="fas fa-vote-yea"></i>
                    Consultazione
                </div>
                <div className="page-header-subtitle">
                    Dettaglio scheda elettorale: {scheda.nome || 'Scheda'}
                </div>
            </div>

            {error && (
                <div className="alert alert-danger alert-dismissible">
                    {error}
                    <button type="button" className="btn-close" onClick={() => setError(null)}></button>
                </div>
            )}

            {/* Header con colore della scheda */}
            <div
                className="card mb-4"
                style={{ borderTop: `4px solid ${formData.colore || scheda.colore || '#007bff'}` }}
            >
                <div className="card-header d-flex justify-content-between align-items-center">
                    <div className="d-flex align-items-center">
                        <span
                            className="me-3"
                            style={{
                                display: 'inline-block',
                                width: '24px',
                                height: '24px',
                                backgroundColor: formData.colore || scheda.colore || '#007bff',
                                borderRadius: '4px'
                            }}
                        ></span>
                        <div>
                            {isEditing ? (
                                <input
                                    type="text"
                                    className="form-control form-control-lg"
                                    value={formData.nome}
                                    onChange={(e) => handleChange('nome', e.target.value)}
                                    placeholder="Nome scheda"
                                />
                            ) : (
                                <h4 className="mb-0">{scheda.nome}</h4>
                            )}
                            <small className="text-muted">{getTipoLabel(scheda.tipo)}</small>
                        </div>
                    </div>
                    <div className="d-flex gap-2">
                        {isEditing ? (
                            <>
                                <button
                                    className="btn btn-success btn-sm"
                                    onClick={handleSave}
                                    disabled={saving}
                                >
                                    {saving ? (
                                        <><span className="spinner-border spinner-border-sm me-1"></span>Salvataggio...</>
                                    ) : (
                                        <><i className="fas fa-save me-1"></i>Salva</>
                                    )}
                                </button>
                                <button
                                    className="btn btn-secondary btn-sm"
                                    onClick={handleCancel}
                                    disabled={saving}
                                >
                                    <i className="fas fa-times me-1"></i>Annulla
                                </button>
                            </>
                        ) : (
                            <>
                                <button
                                    className="btn btn-primary btn-sm"
                                    onClick={() => setIsEditing(true)}
                                >
                                    <i className="fas fa-edit me-1"></i>Modifica
                                </button>
                                <button
                                    className="btn btn-outline-secondary btn-sm"
                                    onClick={onClose}
                                >
                                    <i className="fas fa-arrow-left me-1"></i>Indietro
                                </button>
                            </>
                        )}
                    </div>
                </div>

                <div className="card-body">
                    {/* Colore scheda (in modifica) */}
                    {isEditing && (
                        <div className="mb-4">
                            <label className="form-label">
                                <i className="fas fa-palette me-2"></i>
                                Colore Scheda
                            </label>
                            <div className="d-flex flex-wrap gap-2 mb-2">
                                {coloriPredefiniti.map((c) => (
                                    <button
                                        key={c.valore}
                                        type="button"
                                        className={`btn btn-sm ${formData.colore === c.valore ? 'border-dark border-2' : ''}`}
                                        style={{ backgroundColor: c.valore, minWidth: '80px' }}
                                        onClick={() => handleChange('colore', c.valore)}
                                        title={c.nome}
                                    >
                                        {c.nome}
                                    </button>
                                ))}
                            </div>
                            <input
                                type="color"
                                className="form-control form-control-color"
                                value={formData.colore || '#007bff'}
                                onChange={(e) => handleChange('colore', e.target.value)}
                                title="Scegli colore personalizzato"
                            />
                        </div>
                    )}

                    {/* Referendum: mostra/modifica il quesito */}
                    {isReferendum && (
                        <div className="referendum-quesito">
                            <h5 className="text-muted mb-3">
                                <i className="fas fa-question-circle me-2"></i>
                                Quesito Referendario
                            </h5>
                            {isEditing ? (
                                <textarea
                                    className="form-control"
                                    rows="6"
                                    value={formData.testo_quesito}
                                    onChange={(e) => handleChange('testo_quesito', e.target.value)}
                                    placeholder="Inserisci il testo del quesito referendario..."
                                />
                            ) : (
                                <>
                                    {scheda.testo_quesito ? (
                                        <div className="alert alert-light border" style={{ fontSize: '1.1em' }}>
                                            <p className="mb-0" style={{ whiteSpace: 'pre-wrap' }}>
                                                {scheda.testo_quesito}
                                            </p>
                                        </div>
                                    ) : (
                                        <div className="alert alert-warning">
                                            <i className="fas fa-exclamation-triangle me-2"></i>
                                            Quesito non ancora inserito. Clicca "Modifica" per aggiungerlo.
                                        </div>
                                    )}
                                </>
                            )}
                            <div className="mt-3">
                                <span className="badge bg-success me-2 p-2">SI</span>
                                <span className="badge bg-danger p-2">NO</span>
                            </div>
                        </div>
                    )}

                    {/* Altre elezioni: mostra/modifica schema voti */}
                    {!isReferendum && (
                        <div className="elezione-info">
                            <h5 className="text-muted mb-3">
                                <i className="fas fa-info-circle me-2"></i>
                                Configurazione Scheda
                            </h5>

                            {isEditing ? (
                                <div className="mb-4">
                                    <label className="form-label">Schema di Voto (JSON)</label>
                                    <textarea
                                        className="form-control font-monospace"
                                        rows="8"
                                        value={formData.schema_voti}
                                        onChange={(e) => handleChange('schema_voti', e.target.value)}
                                        placeholder='{"tipo": "lista_candidati", ...}'
                                    />
                                    <small className="text-muted">
                                        Inserisci lo schema in formato JSON per definire come raccogliere i voti
                                    </small>
                                </div>
                            ) : (
                                <>
                                    {scheda.schema_voti ? (
                                        <div className="mb-4">
                                            <h6>Schema di Voto</h6>
                                            <div className="alert alert-light border">
                                                <pre className="mb-0" style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                                                    {typeof scheda.schema_voti === 'object'
                                                        ? JSON.stringify(scheda.schema_voti, null, 2)
                                                        : scheda.schema_voti}
                                                </pre>
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="alert alert-warning">
                                            <i className="fas fa-exclamation-triangle me-2"></i>
                                            Schema voti non configurato. Clicca "Modifica" per aggiungerlo.
                                        </div>
                                    )}
                                </>
                            )}

                            {/* Placeholder per liste e candidati */}
                            {!isEditing && (
                                <div className="row mt-4">
                                    <div className="col-md-6">
                                        <div className="card bg-light">
                                            <div className="card-body text-center text-muted">
                                                <i className="fas fa-list fa-2x mb-2"></i>
                                                <p className="mb-0">Liste elettorali</p>
                                                <small>Gestione da Admin Django</small>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="col-md-6">
                                        <div className="card bg-light">
                                            <div className="card-body text-center text-muted">
                                                <i className="fas fa-user-tie fa-2x mb-2"></i>
                                                <p className="mb-0">Candidati</p>
                                                <small>Gestione da Admin Django</small>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Ordine e Turno (in modifica) */}
                    {isEditing && (
                        <div className="mt-4">
                            <div className="row">
                                <div className={supportsBallottaggio ? "col-md-6" : "col-md-12"}>
                                    <label className="form-label">
                                        <i className="fas fa-sort-numeric-up me-2"></i>
                                        Ordine di Visualizzazione
                                    </label>
                                    <input
                                        type="number"
                                        className="form-control"
                                        style={{ maxWidth: '120px' }}
                                        value={formData.ordine}
                                        onChange={(e) => handleChange('ordine', e.target.value)}
                                        min="0"
                                    />
                                </div>
                                {/* Turno/Ballottaggio solo per elezioni comunali (> 15.000 abitanti) */}
                                {supportsBallottaggio && (
                                    <>
                                        <div className="col-md-3">
                                            <label className="form-label">
                                                <i className="fas fa-redo me-2"></i>
                                                Turno
                                            </label>
                                            <select
                                                className="form-select"
                                                value={formData.turno}
                                                onChange={(e) => handleChange('turno', e.target.value)}
                                            >
                                                <option value={1}>1 - Primo turno</option>
                                                <option value={2}>2 - Ballottaggio</option>
                                            </select>
                                        </div>
                                        {parseInt(formData.turno) === 2 && (
                                            <div className="col-md-3">
                                                <label className="form-label">
                                                    <i className="fas fa-calendar me-2"></i>
                                                    Data Ballottaggio
                                                </label>
                                                <input
                                                    type="date"
                                                    className="form-control"
                                                    value={formData.data_inizio_turno}
                                                    onChange={(e) => handleChange('data_inizio_turno', e.target.value)}
                                                />
                                                <small className="text-muted">
                                                    Data a partire dalla quale gli RDL vedono questo turno
                                                </small>
                                            </div>
                                        )}
                                    </>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Dettagli tecnici */}
            <div className="card">
                <div className="card-header">
                    <h6 className="mb-0">
                        <i className="fas fa-cog me-2"></i>
                        Dettagli Tecnici
                    </h6>
                </div>
                <div className="card-body">
                    <div className="row">
                        <div className="col-md-2">
                            <strong>ID Scheda:</strong> {scheda.id}
                        </div>
                        <div className="col-md-2">
                            <strong>Tipo:</strong> {scheda.tipo}
                        </div>
                        {supportsBallottaggio && (
                            <div className="col-md-2">
                                <strong>Turno:</strong> {formData.turno === 2 ? 'Ballottaggio' : 'Primo turno'}
                            </div>
                        )}
                        <div className="col-md-2">
                            <strong>Ordine:</strong> {formData.ordine}
                        </div>
                        <div className="col-md-4">
                            <strong>Colore:</strong>
                            <span
                                className="ms-2 px-2 py-1 rounded"
                                style={{ backgroundColor: formData.colore || scheda.colore || '#ccc', color: '#000' }}
                            >
                                {formData.colore || scheda.colore || 'N/D'}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default SchedaElettorale;
