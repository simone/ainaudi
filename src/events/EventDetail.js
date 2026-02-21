import React, { useState, useEffect } from 'react';

/**
 * Event Detail Page
 *
 * Shows event info with temporal status:
 * - FUTURO: countdown + date/time + info
 * - IN_CORSO: "Entra ora" button (opens external_url)
 * - CONCLUSO: "Evento concluso"
 *
 * Props:
 * - eventId: UUID of the event
 * - client: API client
 */
export default function EventDetail({ eventId, client }) {
    const [event, setEvent] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!client || !eventId) return;

        setLoading(true);
        client.me.event(eventId)
            .then(data => {
                if (data.error) {
                    setError(data.error);
                } else {
                    setEvent(data);
                }
                setLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setLoading(false);
            });
    }, [client, eventId]);

    // Refresh temporal status every 30 seconds
    const [now, setNow] = useState(new Date());
    useEffect(() => {
        const interval = setInterval(() => setNow(new Date()), 30000);
        return () => clearInterval(interval);
    }, []);

    if (loading) {
        return (
            <div className="text-center py-5">
                <div className="spinner-border" role="status">
                    <span className="visually-hidden">Caricamento...</span>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="alert alert-danger">
                <i className="fas fa-exclamation-triangle me-2"></i>
                {error}
            </div>
        );
    }

    if (!event) return null;

    const startAt = new Date(event.start_at);
    const endAt = new Date(event.end_at);

    // Compute temporal status client-side for real-time updates
    let temporalStatus;
    if (now < startAt) {
        temporalStatus = 'FUTURO';
    } else if (now <= endAt) {
        temporalStatus = 'IN_CORSO';
    } else {
        temporalStatus = 'CONCLUSO';
    }

    const formatDate = (dt) => {
        return dt.toLocaleDateString('it-IT', {
            weekday: 'long',
            day: 'numeric',
            month: 'long',
            year: 'numeric',
        });
    };

    const formatTime = (dt) => {
        return dt.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
    };

    // Countdown for future events
    const getCountdown = () => {
        const diff = startAt - now;
        if (diff <= 0) return null;

        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

        const parts = [];
        if (days > 0) parts.push(`${days}g`);
        if (hours > 0) parts.push(`${hours}h`);
        parts.push(`${minutes}m`);
        return parts.join(' ');
    };

    return (
        <div className="card">
            <div className="card-header bg-dark text-white">
                <h5 className="mb-0">
                    <i className="fas fa-calendar-alt me-2"></i>
                    {event.title}
                </h5>
            </div>
            <div className="card-body">
                {/* Status Badge */}
                <div className="mb-3">
                    {temporalStatus === 'FUTURO' && (
                        <span className="badge bg-info fs-6">
                            <i className="fas fa-clock me-1"></i>
                            In programma - tra {getCountdown()}
                        </span>
                    )}
                    {temporalStatus === 'IN_CORSO' && (
                        <span className="badge bg-success fs-6">
                            <i className="fas fa-broadcast-tower me-1"></i>
                            In corso
                        </span>
                    )}
                    {temporalStatus === 'CONCLUSO' && (
                        <span className="badge bg-secondary fs-6">
                            <i className="fas fa-check me-1"></i>
                            Concluso
                        </span>
                    )}
                </div>

                {/* Date/Time */}
                <div className="mb-3">
                    <div className="d-flex align-items-center mb-1">
                        <i className="fas fa-calendar me-2 text-muted"></i>
                        <strong>{formatDate(startAt)}</strong>
                    </div>
                    <div className="d-flex align-items-center">
                        <i className="fas fa-clock me-2 text-muted"></i>
                        <span>{formatTime(startAt)} - {formatTime(endAt)}</span>
                    </div>
                </div>

                {/* Description */}
                {event.description && (
                    <div className="mb-3">
                        <p className="mb-0">{event.description}</p>
                    </div>
                )}

                {/* Consultation */}
                {event.consultazione_nome && (
                    <div className="mb-3">
                        <small className="text-muted">
                            <i className="fas fa-vote-yea me-1"></i>
                            {event.consultazione_nome}
                        </small>
                    </div>
                )}

                {/* CTA: Entra ora (only when IN_CORSO and has URL) */}
                {temporalStatus === 'IN_CORSO' && event.external_url && (
                    <div className="mt-4">
                        <a
                            href={event.external_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="btn btn-success btn-lg w-100"
                        >
                            <i className="fas fa-video me-2"></i>
                            Entra ora
                        </a>
                    </div>
                )}

                {/* Future event with URL: show link info */}
                {temporalStatus === 'FUTURO' && event.external_url && (
                    <div className="alert alert-info mt-3 mb-0">
                        <i className="fas fa-info-circle me-2"></i>
                        Il pulsante per entrare apparirà quando l'evento inizierà.
                    </div>
                )}
            </div>
        </div>
    );
}
