import React, { useState, useEffect } from 'react';

/**
 * Assignment Detail Page
 *
 * Shows section assignment details with location info.
 * Derived from SectionAssignment + Consultazione + SezioneElettorale.
 *
 * Props:
 * - assignmentId: ID of the SectionAssignment
 * - client: API client
 */
export default function AssignmentDetail({ assignmentId, client }) {
    const [assignment, setAssignment] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!client || !assignmentId) return;

        setLoading(true);
        client.me.assignment(assignmentId)
            .then(data => {
                if (data.error) {
                    setError(data.error);
                } else {
                    setAssignment(data);
                }
                setLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setLoading(false);
            });
    }, [client, assignmentId]);

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

    if (!assignment) return null;

    const formatDate = (dateStr) => {
        if (!dateStr) return '';
        return new Date(dateStr).toLocaleDateString('it-IT', {
            weekday: 'long',
            day: 'numeric',
            month: 'long',
            year: 'numeric',
        });
    };

    const mapsUrl = assignment.lat && assignment.lng
        ? `https://maps.google.com/?q=${assignment.lat},${assignment.lng}`
        : assignment.address
            ? `https://maps.google.com/?q=${encodeURIComponent(assignment.address + ' ' + assignment.comune_nome)}`
            : null;

    return (
        <div className="card">
            <div className="card-header bg-dark text-white">
                <h5 className="mb-0">
                    <i className="fas fa-map-marker-alt me-2"></i>
                    Sezione {assignment.sezione_numero} - {assignment.comune_nome}
                </h5>
            </div>
            <div className="card-body">
                {/* Role Badge */}
                <div className="mb-3">
                    <span className={`badge fs-6 ${assignment.role === 'RDL' ? 'bg-primary' : 'bg-warning text-dark'}`}>
                        <i className="fas fa-user-check me-1"></i>
                        {assignment.role_display}
                    </span>
                    {assignment.temporal_status === 'FUTURO' && (
                        <span className="badge bg-info ms-2 fs-6">In programma</span>
                    )}
                    {assignment.temporal_status === 'IN_CORSO' && (
                        <span className="badge bg-success ms-2 fs-6">In corso</span>
                    )}
                    {assignment.temporal_status === 'CONCLUSO' && (
                        <span className="badge bg-secondary ms-2 fs-6">Concluso</span>
                    )}
                </div>

                {/* Location Info */}
                <div className="mb-3">
                    {assignment.location_name && (
                        <div className="d-flex align-items-start mb-2">
                            <i className="fas fa-school me-2 text-muted mt-1"></i>
                            <div>
                                <strong>{assignment.location_name}</strong>
                            </div>
                        </div>
                    )}
                    {assignment.address && (
                        <div className="d-flex align-items-start mb-2">
                            <i className="fas fa-map-marker-alt me-2 text-muted mt-1"></i>
                            <div>{assignment.address}</div>
                        </div>
                    )}
                    <div className="d-flex align-items-start mb-2">
                        <i className="fas fa-city me-2 text-muted mt-1"></i>
                        <div>
                            {assignment.comune_nome}
                            {assignment.municipio_nome && ` - ${assignment.municipio_nome}`}
                        </div>
                    </div>
                </div>

                {/* Date */}
                <div className="mb-3">
                    <div className="d-flex align-items-center mb-1">
                        <i className="fas fa-calendar me-2 text-muted"></i>
                        <span>
                            {formatDate(assignment.start_at)}
                            {assignment.end_at !== assignment.start_at && (
                                <> - {formatDate(assignment.end_at)}</>
                            )}
                        </span>
                    </div>
                </div>

                {/* Consultation */}
                {assignment.consultazione_nome && (
                    <div className="mb-3">
                        <small className="text-muted">
                            <i className="fas fa-vote-yea me-1"></i>
                            {assignment.consultazione_nome}
                        </small>
                    </div>
                )}

                {/* Notes */}
                {assignment.notes && (
                    <div className="alert alert-light mb-3">
                        <i className="fas fa-sticky-note me-2"></i>
                        {assignment.notes}
                    </div>
                )}

                {/* Maps CTA */}
                {mapsUrl && (
                    <div className="mt-4">
                        <a
                            href={mapsUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="btn btn-primary btn-lg w-100"
                        >
                            <i className="fas fa-directions me-2"></i>
                            Apri in Google Maps
                        </a>
                    </div>
                )}
            </div>
        </div>
    );
}
