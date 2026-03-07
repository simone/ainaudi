import React, { useState, useEffect } from 'react';
import SegnalazioniForm from './SegnalazioniForm';
import SegnalazioniList from './SegnalazioniList';
import IncidentDetail from './IncidentDetail';
import './SegnalazioniStyles.css';

function SegnalazioniUI({
    client,
    consultazione,
    user,
    permissions,
    setError,
}) {
    // State Management
    const [incidents, setIncidents] = useState([]);
    const [userSezioni, setUserSezioni] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('mie');
    const [selectedIncident, setSelectedIncident] = useState(null);
    const [showForm, setShowForm] = useState(false);
    const [categoryFilter, setCategoryFilter] = useState('');
    const [statusFilter, setStatusFilter] = useState('');
    const [verbalizzatoFilter, setVerbalizzatoFilter] = useState('');

    // Load incidents and user sezioni
    useEffect(() => {
        loadIncidents();
        loadUserSezioni();
    }, [consultazione]);

    const loadIncidents = async () => {
        if (!consultazione) return;

        setIsLoading(true);
        try {
            const response = await client.incidents.list({
                consultazione: consultazione.id,
            });
            setIncidents(response.results || response || []);
        } catch (err) {
            console.error('Error loading incidents:', err);
            setError('Errore nel caricamento delle segnalazioni');
        } finally {
            setIsLoading(false);
        }
    };

    const loadUserSezioni = async () => {
        try {
            // Get sections accessible to this user (RDL or Delegato/SubDelegato)
            // For RDL: sections assigned via DesignazioneRDL
            // For Delegato/SubDelegato: all sections in their territory
            const response = await client.scrutinio.sezioni(1, 1000);

            let sezioni = [];
            if (response && response.sezioni && Array.isArray(response.sezioni)) {
                // Extract basic section info from scrutinio response
                sezioni = response.sezioni.map(sez => ({
                    id: sez.sezione,
                    numero: sez.sezione,
                    comune: sez.comune,
                    municipio: sez.municipio || '',
                    indirizzo: sez.indirizzo || '',
                }));
            }
            setUserSezioni(sezioni);
        } catch (err) {
            console.error('Error loading user sezioni:', err);
            setUserSezioni([]);
        }
    };

    const filterIncidents = (list) => {
        if (activeTab === 'mie') {
            return list.filter((incident) => incident.reporter === user?.id);
        } else if (activeTab === 'assegnate') {
            return list.filter((incident) => incident.assigned_to === user?.id);
        }
        return list;
    };

    const displayedIncidents = filterIncidents(incidents);

    const handleSelectIncident = (incident) => {
        setSelectedIncident(incident);
        setShowForm(false);
    };

    const handleBackToList = () => {
        setSelectedIncident(null);
    };

    const handleCreateIncidentSubmit = async (newIncident) => {
        // Add the new incident to the list
        setIncidents([newIncident, ...incidents]);
        setShowForm(false);
        setSelectedIncident(newIncident);
    };

    const handleShowForm = () => {
        setShowForm(true);
        setSelectedIncident(null);
    };

    const handleCancelForm = () => {
        setShowForm(false);
    };

    const handleRefresh = () => {
        loadIncidents();
    };

    // Render Content
    if (isLoading) {
        return (
            <div className="segnalazioni-container">
                <div className="loading">
                    <div className="loading-spinner"></div>
                    <span>Caricamento segnalazioni...</span>
                </div>
            </div>
        );
    }

    if (showForm) {
        return (
            <div className="segnalazioni-container">
                <button
                    className="segnalazioni-btn segnalazioni-btn-back mb-3"
                    onClick={handleCancelForm}
                >
                    <i className="fas fa-arrow-left"></i>
                    Torna alle segnalazioni
                </button>
                <SegnalazioniForm
                    client={client}
                    consultazione={consultazione}
                    userSezioni={userSezioni}
                    onSubmit={handleCreateIncidentSubmit}
                    onCancel={handleCancelForm}
                />
            </div>
        );
    }

    if (selectedIncident) {
        return (
            <div className="segnalazioni-container">
                <IncidentDetail
                    incident={selectedIncident}
                    client={client}
                    onBack={handleBackToList}
                />
            </div>
        );
    }

    return (
        <div className="segnalazioni-container">
            {/* Page Header */}
            <div className="page-header segnalazioni">
                <div className="page-header-title">
                    <i className="fas fa-exclamation-triangle"></i>
                    Segnalazioni
                </div>
                <div className="page-header-subtitle">
                    Segnala problemi e irregolarità durante le operazioni elettorali
                </div>
            </div>

            {/* Actions Bar */}
            <div className="segnalazioni-actions-bar mb-3">
                <button
                    className="segnalazioni-btn segnalazioni-btn-create"
                    onClick={handleShowForm}
                >
                    <i className="fas fa-plus"></i>
                    Nuova Segnalazione
                </button>
                <button
                    className="segnalazioni-btn segnalazioni-btn-outline-secondary"
                    onClick={handleRefresh}
                    title="Aggiorna"
                >
                    <i className="fas fa-sync-alt"></i>
                </button>
            </div>

            {/* Tabs */}
            <div className="segnalazioni-tabs">
                <button
                    className={`segnalazioni-tab ${activeTab === 'mie' ? 'active' : ''}`}
                    onClick={() => {
                        setActiveTab('mie');
                        setCategoryFilter('');
                        setStatusFilter('');
                        setVerbalizzatoFilter('');
                    }}
                >
                    <i className="fas fa-user me-1"></i>
                    Mie Segnalazioni
                    {filterIncidents(incidents.filter((i) => i.reporter === user?.id)).length > 0 && (
                        <span
                            className="badge bg-primary ms-2"
                            style={{ fontSize: '0.75rem' }}
                        >
                            {filterIncidents(incidents.filter((i) => i.reporter === user?.id)).length}
                        </span>
                    )}
                </button>

                {permissions.can_manage_delegations && (
                    <button
                        className={`segnalazioni-tab ${activeTab === 'assegnate' ? 'active' : ''}`}
                        onClick={() => {
                            setActiveTab('assegnate');
                            setCategoryFilter('');
                            setStatusFilter('');
                            setVerbalizzatoFilter('');
                        }}
                    >
                        <i className="fas fa-tasks me-1"></i>
                        Assegnate a Me
                        {filterIncidents(incidents.filter((i) => i.assigned_to === user?.id)).length > 0 && (
                            <span
                                className="badge bg-warning ms-2"
                                style={{ fontSize: '0.75rem' }}
                            >
                                {filterIncidents(incidents.filter((i) => i.assigned_to === user?.id)).length}
                            </span>
                        )}
                    </button>
                )}

                {permissions.can_manage_delegations && (
                    <button
                        className={`segnalazioni-tab ${activeTab === 'tutte' ? 'active' : ''}`}
                        onClick={() => {
                            setActiveTab('tutte');
                            setCategoryFilter('');
                            setStatusFilter('');
                            setVerbalizzatoFilter('');
                        }}
                    >
                        <i className="fas fa-list me-1"></i>
                        Tutte le Segnalazioni
                        {incidents.length > 0 && (
                            <span
                                className="badge bg-secondary ms-2"
                                style={{ fontSize: '0.75rem' }}
                            >
                                {incidents.length}
                            </span>
                        )}
                    </button>
                )}
            </div>

            {/* List */}
            <SegnalazioniList
                incidents={displayedIncidents}
                onSelectIncident={handleSelectIncident}
                categoryFilter={categoryFilter}
                statusFilter={statusFilter}
                verbalizzatoFilter={verbalizzatoFilter}
                onCategoryFilterChange={setCategoryFilter}
                onStatusFilterChange={setStatusFilter}
                onVerbalizzatoFilterChange={setVerbalizzatoFilter}
            />
        </div>
    );
}

export default SegnalazioniUI;
