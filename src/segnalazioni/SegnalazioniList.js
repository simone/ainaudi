import React from 'react';
import './SegnalazioniStyles.css';

function SegnalazioniList({
    incidents,
    onSelectIncident,
    categoryFilter,
    statusFilter,
    verbalizzatoFilter,
    onCategoryFilterChange,
    onStatusFilterChange,
    onVerbalizzatoFilterChange,
}) {
    const categoryOptions = [
        { value: '', label: 'Tutte le categorie' },
        { value: 'PROCEDURAL', label: 'Procedurale' },
        { value: 'ACCESS', label: 'Accesso al seggio' },
        { value: 'MATERIALS', label: 'Materiali' },
        { value: 'INTIMIDATION', label: 'Intimidazione' },
        { value: 'IRREGULARITY', label: 'Irregolarità' },
        { value: 'TECHNICAL', label: 'Tecnico' },
        { value: 'OTHER', label: 'Altro' },
    ];

    const statusOptions = [
        { value: '', label: 'Tutti gli stati' },
        { value: 'OPEN', label: 'Aperta' },
        { value: 'IN_PROGRESS', label: 'In corso' },
        { value: 'RESOLVED', label: 'Risolta' },
        { value: 'CLOSED', label: 'Chiusa' },
        { value: 'ESCALATED', label: 'Escalata' },
    ];

    const verbalizzatoOptions = [
        { value: '', label: 'Tutte' },
        { value: 'true', label: 'Solo verbalizzate' },
        { value: 'false', label: 'Non verbalizzate' },
    ];

    // Filter incidents
    const filteredIncidents = incidents.filter((incident) => {
        if (categoryFilter && incident.category !== categoryFilter) return false;
        if (statusFilter && incident.status !== statusFilter) return false;
        if (verbalizzatoFilter === 'true' && !incident.is_verbalizzato) return false;
        if (verbalizzatoFilter === 'false' && incident.is_verbalizzato) return false;
        return true;
    });

    const getSeverityClass = (severity) => {
        if (severity === 'CRITICAL') return 'severity-critical';
        if (severity === 'HIGH') return 'severity-high';
        return '';
    };

    const getStatusClass = (status) => {
        return `status-${status.toLowerCase()}`;
    };

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

    return (
        <div className="segnalazioni-list-container">
            <div className="segnalazioni-filters">
                <div className="segnalazioni-filter-group">
                    <label htmlFor="category-filter">Categoria:</label>
                    <select
                        id="category-filter"
                        value={categoryFilter}
                        onChange={(e) => onCategoryFilterChange(e.target.value)}
                    >
                        {categoryOptions.map((option) => (
                            <option key={option.value} value={option.value}>
                                {option.label}
                            </option>
                        ))}
                    </select>
                </div>

                <div className="segnalazioni-filter-group">
                    <label htmlFor="status-filter">Stato:</label>
                    <select
                        id="status-filter"
                        value={statusFilter}
                        onChange={(e) => onStatusFilterChange(e.target.value)}
                    >
                        {statusOptions.map((option) => (
                            <option key={option.value} value={option.value}>
                                {option.label}
                            </option>
                        ))}
                    </select>
                </div>

                <div className="segnalazioni-filter-group">
                    <label htmlFor="verbalizzato-filter">Verbalizzazione:</label>
                    <select
                        id="verbalizzato-filter"
                        value={verbalizzatoFilter}
                        onChange={(e) => onVerbalizzatoFilterChange(e.target.value)}
                    >
                        {verbalizzatoOptions.map((option) => (
                            <option key={option.value} value={option.value}>
                                {option.label}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {filteredIncidents.length === 0 ? (
                <div className="segnalazioni-empty">
                    <i className="fas fa-inbox"></i>
                    <p>Nessuna segnalazione trovata</p>
                </div>
            ) : (
                <ul className="segnalazioni-list">
                    {filteredIncidents.map((incident) => (
                        <li
                            key={incident.id}
                            className="segnalazione-item"
                            onClick={() => onSelectIncident(incident)}
                        >
                            <div className="segnalazione-item-content">
                                <div className="segnalazione-item-header">
                                    <h3 className="segnalazione-item-title">
                                        #{incident.id} - {incident.title}
                                    </h3>
                                </div>
                                <div className="segnalazione-item-meta">
                                    <span className="segnalazione-meta-badge">
                                        <i className="fas fa-calendar"></i>
                                        {formatDate(incident.created_at)}
                                    </span>
                                    {incident.location_description && (
                                        <span className="segnalazione-meta-badge">
                                            <i className="fas fa-map-marker-alt"></i>
                                            {incident.location_description}
                                        </span>
                                    )}
                                    <span className="segnalazione-meta-badge">
                                        <i className="fas fa-user"></i>
                                        {incident.reporter_email}
                                    </span>
                                </div>
                                <p className="segnalazione-item-description">
                                    {incident.description}
                                </p>
                            </div>

                            <div className="segnalazione-badges">
                                <span className={`badge badge-category`}>
                                    {incident.category_display}
                                </span>
                                <span className={`badge badge-severity ${getSeverityClass(incident.severity)}`}>
                                    {incident.severity_display}
                                </span>
                                <span className={`badge badge-status ${getStatusClass(incident.status)}`}>
                                    {incident.status_display}
                                </span>
                                {incident.is_verbalizzato && (
                                    <span className="segnalazione-verbalizzato">
                                        <i className="fas fa-check-circle"></i>
                                        Verbalizzata
                                    </span>
                                )}
                            </div>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}

export default SegnalazioniList;
