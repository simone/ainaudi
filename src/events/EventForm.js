import React, { useState, useEffect } from 'react';

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
        regioni: event?.regioni || [],
        province: event?.province || [],
        comuni: event?.comuni || [],
    });
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);

    // Territory options
    const [regioniOptions, setRegioniOptions] = useState([]);
    const [provinceOptions, setProvinceOptions] = useState([]);
    const [comuniOptions, setComuniOptions] = useState([]);
    const [loadingTerritory, setLoadingTerritory] = useState(false);

    // Selected filters for cascading
    const [selectedRegione, setSelectedRegione] = useState('');
    const [selectedProvincia, setSelectedProvincia] = useState('');

    function toLocalDatetime(isoStr) {
        const dt = new Date(isoStr);
        const offset = dt.getTimezoneOffset();
        const local = new Date(dt.getTime() - offset * 60000);
        return local.toISOString().slice(0, 16);
    }

    // Load regioni on mount
    useEffect(() => {
        if (!client?.territory?.regioni) return;
        client.territory.regioni()
            .then(data => {
                if (Array.isArray(data)) {
                    setRegioniOptions(data);
                }
            });
    }, [client]);

    // Load province when a regione is selected for filtering
    useEffect(() => {
        if (!selectedRegione || !client?.territory?.province) {
            setProvinceOptions([]);
            return;
        }
        client.territory.province(selectedRegione)
            .then(data => {
                if (Array.isArray(data)) {
                    setProvinceOptions(data);
                }
            });
    }, [client, selectedRegione]);

    // Load comuni when a provincia is selected for filtering
    useEffect(() => {
        if (!selectedProvincia || !client?.territory?.comuni) {
            setComuniOptions([]);
            return;
        }
        client.territory.comuni(selectedProvincia)
            .then(data => {
                if (Array.isArray(data)) {
                    setComuniOptions(data);
                }
            });
    }, [client, selectedProvincia]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setForm(prev => ({ ...prev, [name]: value }));
    };

    // Add/remove from M2M arrays
    const addToList = (field, id, label) => {
        if (!id) return;
        const numId = Number(id);
        setForm(prev => {
            if (prev[field].includes(numId)) return prev;
            return { ...prev, [field]: [...prev[field], numId] };
        });
    };

    const removeFromList = (field, id) => {
        setForm(prev => ({
            ...prev,
            [field]: prev[field].filter(v => v !== id),
        }));
    };

    const getLabel = (options, id) => {
        const opt = options.find(o => o.id === id);
        return opt?.nome || opt?.name || `#${id}`;
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

                    {/* Territory filters */}
                    <div className="mb-3 p-3" style={{ background: '#f8f9fa', borderRadius: '8px', border: '1px solid #dee2e6' }}>
                        <label className="form-label fw-bold">
                            <i className="fas fa-globe-europe me-1"></i>
                            Visibilita' territoriale
                        </label>
                        <small className="d-block text-muted mb-3">
                            Se non selezioni nessun territorio, l'evento sara' visibile a tutti.
                            Se ne selezioni almeno uno, solo gli utenti con sezioni in quei territori lo vedranno.
                        </small>

                        {/* Regioni */}
                        <div className="mb-2">
                            <label className="form-label small fw-bold mb-1">Regioni</label>
                            <div className="input-group input-group-sm">
                                <select
                                    className="form-select form-select-sm"
                                    value={selectedRegione}
                                    onChange={e => setSelectedRegione(e.target.value)}
                                >
                                    <option value="">-- Seleziona regione --</option>
                                    {regioniOptions.map(r => (
                                        <option key={r.id} value={r.id}>{r.nome}</option>
                                    ))}
                                </select>
                                <button
                                    type="button"
                                    className="btn btn-outline-primary btn-sm"
                                    onClick={() => {
                                        addToList('regioni', selectedRegione);
                                        // Don't reset selectedRegione - it's useful for province cascade
                                    }}
                                    disabled={!selectedRegione}
                                >
                                    <i className="fas fa-plus"></i> Aggiungi
                                </button>
                            </div>
                            {form.regioni.length > 0 && (
                                <div className="mt-1">
                                    {form.regioni.map(id => (
                                        <span key={id} className="badge bg-primary me-1 mb-1">
                                            {getLabel(regioniOptions, id)}
                                            <button
                                                type="button"
                                                className="btn-close btn-close-white ms-1"
                                                style={{ fontSize: '0.5em' }}
                                                onClick={() => removeFromList('regioni', id)}
                                            ></button>
                                        </span>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Province */}
                        <div className="mb-2">
                            <label className="form-label small fw-bold mb-1">Province</label>
                            <div className="input-group input-group-sm">
                                <select
                                    className="form-select form-select-sm"
                                    value={selectedProvincia}
                                    onChange={e => setSelectedProvincia(e.target.value)}
                                    disabled={!selectedRegione}
                                >
                                    <option value="">
                                        {selectedRegione ? '-- Seleziona provincia --' : '-- Seleziona prima una regione --'}
                                    </option>
                                    {provinceOptions.map(p => (
                                        <option key={p.id} value={p.id}>{p.nome}</option>
                                    ))}
                                </select>
                                <button
                                    type="button"
                                    className="btn btn-outline-primary btn-sm"
                                    onClick={() => addToList('province', selectedProvincia)}
                                    disabled={!selectedProvincia}
                                >
                                    <i className="fas fa-plus"></i> Aggiungi
                                </button>
                            </div>
                            {form.province.length > 0 && (
                                <div className="mt-1">
                                    {form.province.map(id => (
                                        <span key={id} className="badge bg-info me-1 mb-1">
                                            {getLabel(provinceOptions, id)}
                                            <button
                                                type="button"
                                                className="btn-close btn-close-white ms-1"
                                                style={{ fontSize: '0.5em' }}
                                                onClick={() => removeFromList('province', id)}
                                            ></button>
                                        </span>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Comuni */}
                        <div className="mb-0">
                            <label className="form-label small fw-bold mb-1">Comuni</label>
                            <div className="input-group input-group-sm">
                                <select
                                    className="form-select form-select-sm"
                                    id="comuni-select"
                                    disabled={!selectedProvincia}
                                >
                                    <option value="">
                                        {selectedProvincia ? '-- Seleziona comune --' : '-- Seleziona prima una provincia --'}
                                    </option>
                                    {comuniOptions.map(c => (
                                        <option key={c.id} value={c.id}>{c.nome}</option>
                                    ))}
                                </select>
                                <button
                                    type="button"
                                    className="btn btn-outline-primary btn-sm"
                                    onClick={() => {
                                        const sel = document.getElementById('comuni-select');
                                        addToList('comuni', sel?.value);
                                    }}
                                    disabled={!selectedProvincia}
                                >
                                    <i className="fas fa-plus"></i> Aggiungi
                                </button>
                            </div>
                            {form.comuni.length > 0 && (
                                <div className="mt-1">
                                    {form.comuni.map(id => (
                                        <span key={id} className="badge bg-success me-1 mb-1">
                                            {getLabel(comuniOptions, id)}
                                            <button
                                                type="button"
                                                className="btn-close btn-close-white ms-1"
                                                style={{ fontSize: '0.5em' }}
                                                onClick={() => removeFromList('comuni', id)}
                                            ></button>
                                        </span>
                                    ))}
                                </div>
                            )}
                        </div>
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
