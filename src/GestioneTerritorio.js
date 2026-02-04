import React, { useState, useEffect } from 'react';
import GestioneRegioni from './territorio/GestioneRegioni';
import GestioneProvince from './territorio/GestioneProvince';
import GestioneComuni from './territorio/GestioneComuni';
import GestioneSezioniTerritoriali from './territorio/GestioneSezioniTerritoriali';

/**
 * GestioneTerritorio - Main component for territory administration.
 *
 * Provides tab navigation for managing:
 * - Regioni (20 Italian regions)
 * - Province (107 provinces)
 * - Comuni (7896 municipalities) + their Municipi
 * - Sezioni Elettorali (electoral sections)
 */
function GestioneTerritorio({ client, setError }) {
    const [activeTab, setActiveTab] = useState('regioni');
    const [counts, setCounts] = useState({
        regioni: null,
        province: null,
        comuni: null,
        sezioni: null
    });

    useEffect(() => {
        loadCounts();
    }, []);

    const loadCounts = async () => {
        try {
            const [regioni, province, comuni, sezioni] = await Promise.all([
                client.territorio.admin.regioni.list(),
                client.territorio.admin.province.list(),
                client.territorio.admin.comuni.list(),
                client.territorio.admin.sezioni.list()
            ]);
            setCounts({
                regioni: regioni?.count ?? (Array.isArray(regioni) ? regioni.length : regioni?.results?.length ?? 0),
                province: province?.count ?? (Array.isArray(province) ? province.length : province?.results?.length ?? 0),
                comuni: comuni?.count ?? (Array.isArray(comuni) ? comuni.length : comuni?.results?.length ?? 0),
                sezioni: sezioni?.count ?? (Array.isArray(sezioni) ? sezioni.length : sezioni?.results?.length ?? 0)
            });
        } catch (err) {
            console.error('Errore caricamento conteggi:', err);
        }
    };

    return (
        <>
            {/* Page Header */}
            <div className="page-header territorio">
                <div className="page-header-title">
                    <i className="fas fa-globe-europe"></i>
                    Territorio
                </div>
                <div className="page-header-subtitle">
                    Amministrazione dati territoriali italiani
                </div>
            </div>

            {/* Stats Boxes */}
            <div className="row g-3 mb-3">
                <div className="col-6 col-md-3">
                    <div className="card border-0 bg-primary bg-opacity-10 h-100">
                        <div className="card-body text-center py-3">
                            <i className="fas fa-map text-primary mb-2" style={{ fontSize: '1.5rem' }}></i>
                            <h3 className="mb-0 text-primary">{counts.regioni ?? '-'}</h3>
                            <small className="text-muted">Regioni</small>
                        </div>
                    </div>
                </div>
                <div className="col-6 col-md-3">
                    <div className="card border-0 bg-success bg-opacity-10 h-100">
                        <div className="card-body text-center py-3">
                            <i className="fas fa-map-marked text-success mb-2" style={{ fontSize: '1.5rem' }}></i>
                            <h3 className="mb-0 text-success">{counts.province ?? '-'}</h3>
                            <small className="text-muted">Province</small>
                        </div>
                    </div>
                </div>
                <div className="col-6 col-md-3">
                    <div className="card border-0 bg-warning bg-opacity-10 h-100">
                        <div className="card-body text-center py-3">
                            <i className="fas fa-city text-warning mb-2" style={{ fontSize: '1.5rem' }}></i>
                            <h3 className="mb-0 text-warning">{counts.comuni ?? '-'}</h3>
                            <small className="text-muted">Comuni</small>
                        </div>
                    </div>
                </div>
                <div className="col-6 col-md-3">
                    <div className="card border-0 bg-info bg-opacity-10 h-100">
                        <div className="card-body text-center py-3">
                            <i className="fas fa-vote-yea text-info mb-2" style={{ fontSize: '1.5rem' }}></i>
                            <h3 className="mb-0 text-info">{counts.sezioni ?? '-'}</h3>
                            <small className="text-muted">Sezioni</small>
                        </div>
                    </div>
                </div>
            </div>

            {/* Tab Navigation */}
            <ul className="nav nav-tabs mb-3">
                <li className="nav-item">
                    <button
                        className={`nav-link ${activeTab === 'regioni' ? 'active' : ''}`}
                        onClick={() => setActiveTab('regioni')}
                    >
                        <i className="fas fa-map me-1"></i>
                        Regioni
                    </button>
                </li>
                <li className="nav-item">
                    <button
                        className={`nav-link ${activeTab === 'province' ? 'active' : ''}`}
                        onClick={() => setActiveTab('province')}
                    >
                        <i className="fas fa-map-marked me-1"></i>
                        Province
                    </button>
                </li>
                <li className="nav-item">
                    <button
                        className={`nav-link ${activeTab === 'comuni' ? 'active' : ''}`}
                        onClick={() => setActiveTab('comuni')}
                    >
                        <i className="fas fa-city me-1"></i>
                        Comuni
                    </button>
                </li>
                <li className="nav-item">
                    <button
                        className={`nav-link ${activeTab === 'sezioni' ? 'active' : ''}`}
                        onClick={() => setActiveTab('sezioni')}
                    >
                        <i className="fas fa-vote-yea me-1"></i>
                        Sezioni
                    </button>
                </li>
            </ul>

            {/* Tab Content */}
            {activeTab === 'regioni' && (
                <GestioneRegioni client={client} setError={setError} />
            )}
            {activeTab === 'province' && (
                <GestioneProvince client={client} setError={setError} />
            )}
            {activeTab === 'comuni' && (
                <GestioneComuni client={client} setError={setError} />
            )}
            {activeTab === 'sezioni' && (
                <GestioneSezioniTerritoriali client={client} setError={setError} />
            )}
        </>
    );
}

export default GestioneTerritorio;
