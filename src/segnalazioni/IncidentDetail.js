import React, { useState } from 'react';
import './SegnalazioniStyles.css';

function IncidentDetail({
    incident,
    client,
    onBack,
}) {
    const [newComment, setNewComment] = useState('');
    const [isSubmittingComment, setIsSubmittingComment] = useState(false);
    const [comments, setComments] = useState(incident.comments || []);
    const [error, setError] = useState(null);

    const formatDate = (dateString) => {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleDateString('it-IT', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    const getSeverityIcon = (severity) => {
        switch (severity) {
            case 'CRITICAL':
                return 'fa-exclamation-circle text-danger';
            case 'HIGH':
                return 'fa-exclamation-triangle text-warning';
            case 'MEDIUM':
                return 'fa-exclamation text-info';
            default:
                return 'fa-info-circle text-muted';
        }
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case 'OPEN':
                return 'fa-circle text-secondary';
            case 'IN_PROGRESS':
                return 'fa-spinner text-primary';
            case 'RESOLVED':
                return 'fa-check-circle text-success';
            case 'CLOSED':
                return 'fa-times-circle text-secondary';
            case 'ESCALATED':
                return 'fa-arrow-up text-danger';
            default:
                return 'fa-question-circle';
        }
    };

    const handleAddComment = async (e) => {
        e.preventDefault();
        if (!newComment.trim()) return;

        setError(null);
        setIsSubmittingComment(true);

        try {
            const comment = await client.incidents.createComment({
                incident: incident.id,
                content: newComment,
                is_internal: false,
            });

            setComments([...comments, comment]);
            setNewComment('');
        } catch (err) {
            console.error('Error adding comment:', err);
            setError(err.message || 'Errore nell\'aggiunta del commento');
        } finally {
            setIsSubmittingComment(false);
        }
    };

    return (
        <div className="incident-detail-container">
            <button className="segnalazioni-btn segnalazioni-btn-back" onClick={onBack}>
                <i className="fas fa-arrow-left"></i>
                Torna alla lista
            </button>

            {error && (
                <div className="alert alert-danger" role="alert">
                    <i className="fas fa-exclamation-circle me-2"></i>
                    {error}
                </div>
            )}

            {/* Header */}
            <div className="incident-detail-header">
                <div className="incident-detail-title">
                    <i className={`fas ${getSeverityIcon(incident.severity)} me-2`}></i>
                    #{incident.id} - {incident.title}
                </div>

                <div className="incident-detail-meta">
                    <div className="incident-detail-meta-item">
                        <div className="incident-detail-meta-label">Categoria</div>
                        <div className="incident-detail-meta-value">
                            {incident.category_display}
                        </div>
                    </div>

                    <div className="incident-detail-meta-item">
                        <div className="incident-detail-meta-label">Gravità</div>
                        <div className="incident-detail-meta-value">
                            <i className={`fas ${getSeverityIcon(incident.severity)} me-1`}></i>
                            {incident.severity_display}
                        </div>
                    </div>

                    <div className="incident-detail-meta-item">
                        <div className="incident-detail-meta-label">Stato</div>
                        <div className="incident-detail-meta-value">
                            <i className={`fas ${getStatusIcon(incident.status)} me-1`}></i>
                            {incident.status_display}
                        </div>
                    </div>

                    <div className="incident-detail-meta-item">
                        <div className="incident-detail-meta-label">Sezione</div>
                        <div className="incident-detail-meta-value">
                            {incident.location_description}
                        </div>
                    </div>

                    <div className="incident-detail-meta-item">
                        <div className="incident-detail-meta-label">Segnalante</div>
                        <div className="incident-detail-meta-value">
                            {incident.reporter_name || incident.reporter_email}
                        </div>
                    </div>

                    <div className="incident-detail-meta-item">
                        <div className="incident-detail-meta-label">Data Creazione</div>
                        <div className="incident-detail-meta-value">
                            {formatDate(incident.created_at)}
                        </div>
                    </div>

                    {incident.is_verbalizzato && (
                        <div className="incident-detail-meta-item">
                            <div className="incident-detail-meta-label">Verbalizzazione</div>
                            <div className="incident-detail-meta-value">
                                <i className="fas fa-check-circle text-success me-1"></i>
                                Verbalizzata
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Description */}
            <div className="incident-detail-section">
                <h3 className="incident-detail-section-title">
                    <i className="fas fa-align-left me-2"></i>
                    Descrizione
                </h3>
                <div className="incident-detail-description">
                    {incident.description}
                </div>
            </div>

            {/* Occurred At */}
            {incident.occurred_at && (
                <div className="incident-detail-section">
                    <h3 className="incident-detail-section-title">
                        <i className="fas fa-clock me-2"></i>
                        Data/Ora dell'Incidente
                    </h3>
                    <div className="incident-detail-description">
                        {formatDate(incident.occurred_at)}
                    </div>
                </div>
            )}

            {/* Attachments */}
            {incident.attachments && incident.attachments.length > 0 && (
                <div className="incident-detail-section">
                    <h3 className="incident-detail-section-title">
                        <i className="fas fa-paperclip me-2"></i>
                        Allegati ({incident.attachments.length})
                    </h3>
                    <ul className="file-list">
                        {incident.attachments.map((attachment) => (
                            <li key={attachment.id} className="file-item">
                                <div className="file-item-info">
                                    <div className="file-item-icon">
                                        {attachment.file_type === 'IMAGE' ? (
                                            <i className="fas fa-image"></i>
                                        ) : attachment.file_type === 'DOCUMENT' ? (
                                            <i className="fas fa-file-pdf"></i>
                                        ) : attachment.file_type === 'VIDEO' ? (
                                            <i className="fas fa-video"></i>
                                        ) : (
                                            <i className="fas fa-file"></i>
                                        )}
                                    </div>
                                    <div className="file-item-details">
                                        <div className="file-item-name">
                                            {attachment.filename}
                                        </div>
                                        <div className="file-item-size">
                                            {attachment.file_type_display} • {formatBytes(attachment.file_size)}
                                        </div>
                                    </div>
                                </div>
                                <a
                                    href={attachment.file}
                                    className="segnalazioni-btn segnalazioni-btn-sm segnalazioni-btn-outline-primary"
                                    download
                                    style={{ whiteSpace: 'nowrap' }}
                                >
                                    <i className="fas fa-download me-1"></i>
                                    Scarica
                                </a>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Comments */}
            <div className="incident-detail-section comments-section">
                <h3 className="incident-detail-section-title">
                    <i className="fas fa-comments me-2"></i>
                    Commenti ({comments.length})
                </h3>

                {comments.length > 0 ? (
                    <ul className="comments-list">
                        {comments.map((comment) => (
                            <li key={comment.id} className="comment-item">
                                <div className="comment-header">
                                    <span className="comment-author">
                                        {comment.author_name || comment.author_email}
                                    </span>
                                    {comment.is_internal && (
                                        <span className="comment-internal-badge">
                                            <i className="fas fa-lock me-1"></i>
                                            Interno
                                        </span>
                                    )}
                                    <span className="comment-date">
                                        {formatDate(comment.created_at)}
                                    </span>
                                </div>
                                <div className="comment-content">
                                    {comment.content}
                                </div>
                            </li>
                        ))}
                    </ul>
                ) : (
                    <p style={{ color: '#999', marginTop: '10px' }}>
                        Nessun commento per il momento.
                    </p>
                )}

                {/* Add Comment Form */}
                <form className="add-comment-form" onSubmit={handleAddComment}>
                    <textarea
                        value={newComment}
                        onChange={(e) => setNewComment(e.target.value)}
                        placeholder="Aggiungi un commento..."
                        disabled={isSubmittingComment}
                    />
                    <div className="add-comment-form-buttons">
                        <button
                            type="submit"
                            className="segnalazioni-btn segnalazioni-btn-primary"
                            disabled={!newComment.trim() || isSubmittingComment}
                        >
                            {isSubmittingComment ? (
                                <>
                                    <span className="loading-spinner me-2"></span>
                                    Invio in corso...
                                </>
                            ) : (
                                <>
                                    <i className="fas fa-paper-plane me-1"></i>
                                    Aggiungi Commento
                                </>
                            )}
                        </button>
                    </div>
                </form>
            </div>

            {/* Resolution Info */}
            {incident.resolution && (
                <div className="incident-detail-section">
                    <h3 className="incident-detail-section-title">
                        <i className="fas fa-check-circle me-2"></i>
                        Risoluzione
                    </h3>
                    <div className="incident-detail-description">
                        {incident.resolution}
                    </div>
                    {incident.resolved_by_email && (
                        <p style={{ marginTop: '10px', color: '#999', fontSize: '0.9rem' }}>
                            Risolto da: {incident.resolved_by_email} il {formatDate(incident.resolved_at)}
                        </p>
                    )}
                </div>
            )}
        </div>
    );
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

export default IncidentDetail;
