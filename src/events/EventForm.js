import React, { useState } from 'react';

/**
 * Event create/edit form.
 *
 * Props:
 * - client: API client
 * - event: null for create, object for edit
 * - consultazione: current consultation (pre-fill)
 * - onSaved: callback on success
 * - onCancel: callback to go back
 */
export default function EventForm({ client, event, consultazione, onSaved, onCancel }) {
    const isEdit = !!event?.id;

    const [form, setForm] = useState({
        title: event?.title || '',
        description: event?.description || '',
        start_at: event?.start_at ? toLocalDatetime(event.start_at) : '',
        end_at: event?.end_at ? toLocalDatetime(event.end_at) : '',
        external_url: event?.external_url || '',
        consultazione: event?.consultazione || consultazione?.id || '',
        status: event?.status || 'ACTIVE',
    });
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);

    function toLocalDatetime(isoStr) {
        const dt = new Date(isoStr);
        const offset = dt.getTimezoneOffset();
        const local = new Date(dt.getTime() - offset * 60000);
        return local.toISOString().slice(0, 16);
    }

    const handleChange = (e) => {
        const { name, value } = e.target;
        setForm(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSaving(true);
        setError(null);

        // Convert local datetime to ISO
        const payload = {
            ...form,
            start_at: new Date(form.start_at).toISOString(),
            end_at: new Date(form.end_at).toISOString(),
            consultazione: form.consultazione || null,
        };

        try {
            let result;
            if (isEdit) {
                result = await client.me.updateEvent(event.id, payload);
            } else {
                result = await client.me.createEvent(payload);
            }

            if (result.error) {
                setError(typeof result.error === 'string' ? result.error : JSON.stringify(result.error));
            } else {
                onSaved();
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="card">
            <div className="card-header bg-dark text-white">
                <h5 className="mb-0">
                    <i className={`fas ${isEdit ? 'fa-edit' : 'fa-plus'} me-2`}></i>
                    {isEdit ? 'Modifica evento' : 'Nuovo evento'}
                </h5>
            </div>
            <div className="card-body">
                {error && (
                    <div className="alert alert-danger">{error}</div>
                )}

                <form onSubmit={handleSubmit}>
                    <div className="mb-3">
                        <label className="form-label fw-bold">Titolo *</label>
                        <input
                            type="text"
                            className="form-control"
                            name="title"
                            value={form.title}
                            onChange={handleChange}
                            required
                            placeholder="Es. Corso formazione RDL - Zoom"
                        />
                    </div>

                    <div className="mb-3">
                        <label className="form-label fw-bold">Descrizione</label>
                        <textarea
                            className="form-control"
                            name="description"
                            value={form.description}
                            onChange={handleChange}
                            rows={3}
                            placeholder="Descrizione dell'evento..."
                        />
                    </div>

                    <div className="row mb-3">
                        <div className="col-md-6">
                            <label className="form-label fw-bold">Inizio *</label>
                            <input
                                type="datetime-local"
                                className="form-control"
                                name="start_at"
                                value={form.start_at}
                                onChange={handleChange}
                                required
                            />
                        </div>
                        <div className="col-md-6">
                            <label className="form-label fw-bold">Fine *</label>
                            <input
                                type="datetime-local"
                                className="form-control"
                                name="end_at"
                                value={form.end_at}
                                onChange={handleChange}
                                required
                            />
                        </div>
                    </div>

                    <div className="mb-3">
                        <label className="form-label fw-bold">Link esterno (Zoom, Meet, ecc.)</label>
                        <input
                            type="url"
                            className="form-control"
                            name="external_url"
                            value={form.external_url}
                            onChange={handleChange}
                            placeholder="https://zoom.us/j/..."
                        />
                        <small className="text-muted">
                            Se presente, gli utenti vedranno un pulsante "Entra ora" durante l'evento.
                        </small>
                    </div>

                    {isEdit && (
                        <div className="mb-3">
                            <label className="form-label fw-bold">Stato</label>
                            <select className="form-select" name="status" value={form.status} onChange={handleChange}>
                                <option value="ACTIVE">Attivo</option>
                                <option value="CANCELLED">Annullato</option>
                            </select>
                        </div>
                    )}

                    <div className="d-flex gap-2">
                        <button type="submit" className="btn btn-primary" disabled={saving}>
                            {saving ? (
                                <>
                                    <span className="spinner-border spinner-border-sm me-1"></span>
                                    Salvataggio...
                                </>
                            ) : (
                                <>
                                    <i className="fas fa-save me-1"></i>
                                    {isEdit ? 'Salva modifiche' : 'Crea evento'}
                                </>
                            )}
                        </button>
                        <button type="button" className="btn btn-secondary" onClick={onCancel}>
                            Annulla
                        </button>
                    </div>
                </form>

                {!isEdit && (
                    <div className="alert alert-info mt-3 mb-0">
                        <i className="fas fa-info-circle me-2"></i>
                        Dopo il salvataggio, le notifiche verranno generate automaticamente
                        per tutti gli utenti della consultazione (24h, 2h e 10min prima).
                    </div>
                )}
            </div>
        </div>
    );
}
