import React, { useState, useEffect } from 'react';
import EventForm from './EventForm';

/**
 * Admin Event List - CRUD per gli eventi.
 *
 * Props:
 * - client: API client
 * - consultazione: current active consultation
 */
export default function EventList({ client, consultazione }) {
    const [events, setEvents] = useState([]);
    const [loading, setLoading] = useState(true);
    const [editingEvent, setEditingEvent] = useState(null); // null = list, {} = new, {id,...} = edit
    const [error, setError] = useState(null);

    const loadEvents = () => {
        setLoading(true);
        client.me.events(consultazione?.id)
            .then(data => {
                if (!data.error && Array.isArray(data)) {
                    setEvents(data);
                } else {
                    setError(data.error || 'Errore caricamento eventi');
                }
                setLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setLoading(false);
            });
    };

    useEffect(() => {
        if (client) loadEvents();
    }, [client, consultazione?.id]);

    const handleDelete = async (eventId) => {
        if (!window.confirm('Annullare questo evento? Le notifiche programmate verranno cancellate.')) return;

        const result = await client.me.deleteEvent(eventId);
        if (result.error) {
            setError(result.error);
        } else {
            loadEvents();
        }
    };

    const handleSaved = () => {
        setEditingEvent(null);
        loadEvents();
    };

    const formatDate = (dtStr) => {
        return new Date(dtStr).toLocaleDateString('it-IT', {
            day: '2-digit', month: '2-digit', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    };

    const statusBadge = (status) => {
        if (status === 'IN_CORSO') return <span className="badge bg-success">In corso</span>;
        if (status === 'FUTURO') return <span className="badge bg-info">Futuro</span>;
        return <span className="badge bg-secondary">Concluso</span>;
    };

    // Show form if editing/creating
    if (editingEvent !== null) {
        return (
            <div>
                <button className="btn btn-secondary mb-3" onClick={() => setEditingEvent(null)}>
                    <i className="fas fa-arrow-left me-1"></i> Torna alla lista
                </button>
                <EventForm
                    client={client}
                    event={editingEvent.id ? editingEvent : null}
                    consultazione={consultazione}
                    onSaved={handleSaved}
                    onCancel={() => setEditingEvent(null)}
                />
            </div>
        );
    }

    return (
        <div>
            <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
                <h4 className="mb-0"><i className="fas fa-calendar-alt me-2"></i>Gestione Eventi</h4>
                <div className="d-flex gap-2">
                    <TestNotificationButton client={client} />
                    <button className="btn btn-primary" onClick={() => setEditingEvent({})}>
                        <i className="fas fa-plus me-1"></i> Nuovo evento
                    </button>
                </div>
            </div>

            {error && (
                <div className="alert alert-danger alert-dismissible">
                    {error}
                    <button type="button" className="btn-close" onClick={() => setError(null)}></button>
                </div>
            )}

            {loading ? (
                <div className="text-center py-4">
                    <div className="spinner-border" role="status">
                        <span className="visually-hidden">Caricamento...</span>
                    </div>
                </div>
            ) : events.length === 0 ? (
                <div className="alert alert-info">
                    Nessun evento. Crea il primo evento per inviare notifiche ai tuoi RDL.
                </div>
            ) : (
                <div className="table-responsive">
                    <table className="table table-hover">
                        <thead>
                            <tr>
                                <th>Titolo</th>
                                <th>Data</th>
                                <th>Stato</th>
                                <th>Link</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
                            {events.map(ev => (
                                <tr key={ev.id}>
                                    <td>
                                        <strong>{ev.title}</strong>
                                    </td>
                                    <td>
                                        <small>
                                            {formatDate(ev.start_at)}
                                            <br/>
                                            <span className="text-muted">→ {formatDate(ev.end_at)}</span>
                                        </small>
                                    </td>
                                    <td>{statusBadge(ev.temporal_status)}</td>
                                    <td>
                                        {ev.external_url ? (
                                            <a href={ev.external_url} target="_blank" rel="noopener noreferrer"
                                               className="btn btn-outline-primary btn-sm">
                                                <i className="fas fa-external-link-alt"></i>
                                            </a>
                                        ) : (
                                            <span className="text-muted">-</span>
                                        )}
                                    </td>
                                    <td>
                                        <div className="btn-group btn-group-sm">
                                            <button className="btn btn-outline-secondary"
                                                    onClick={() => setEditingEvent(ev)}>
                                                <i className="fas fa-edit"></i>
                                            </button>
                                            {ev.status !== 'CANCELLED' && (
                                                <button className="btn btn-outline-danger"
                                                        onClick={() => handleDelete(ev.id)}>
                                                    <i className="fas fa-times"></i>
                                                </button>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}

/**
 * Test notification button - sends a push to all registered devices.
 * TTL 15 seconds: the notification auto-expires.
 */
function TestNotificationButton({ client }) {
    const [sending, setSending] = useState(false);
    const [result, setResult] = useState(null);

    const handleTest = async () => {
        setSending(true);
        setResult(null);
        try {
            const data = await client.me.testNotification();
            setResult(data);
        } catch (err) {
            setResult({ error: err.message });
        } finally {
            setSending(false);
            setTimeout(() => setResult(null), 5000);
        }
    };

    return (
        <div className="d-flex align-items-center gap-2">
            <button
                className="btn btn-outline-warning"
                onClick={handleTest}
                disabled={sending}
                title="Invia una notifica test a tutti i dispositivi registrati (scade dopo 15s)"
            >
                {sending ? (
                    <span className="spinner-border spinner-border-sm"></span>
                ) : (
                    <>
                        <i className="fas fa-bell me-1"></i> Test push
                    </>
                )}
            </button>
            {result && !result.error && (
                <small className="text-success">
                    <i className="fas fa-check me-1"></i>{result.message}
                </small>
            )}
            {result?.error && (
                <small className="text-danger">
                    <i className="fas fa-times me-1"></i>{result.error}
                </small>
            )}
        </div>
    );
}
