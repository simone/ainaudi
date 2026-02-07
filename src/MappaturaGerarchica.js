import React, { useState, useEffect } from 'react';
import Mappatura from './Mappatura';

/**
 * Componente per mappatura gerarchica RDL alle sezioni.
 * MOBILE-FIRST design con navigazione touch-friendly.
 *
 * Navigazione drill-down: Regione → Provincia → Comune → Municipio → Sezione
 * Con skip automatico se c'è solo una entità a un livello.
 * Quando raggiungi il livello sezioni, mostra il componente Mappatura completo.
 *
 * Per Delegati/SubDelegati che gestiscono molte sezioni.
 */
function MappaturaGerarchica({ client, consultazione, setError }) {
    const [loading, setLoading] = useState(true);
    const [data, setData] = useState(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [path, setPath] = useState({
        regione_id: null,
        provincia_id: null,
        comune_id: null,
        municipio_id: null
    });

    useEffect(() => {
        if (client && consultazione) {
            loadData();
        }
    }, [client, consultazione, path.regione_id, path.provincia_id, path.comune_id, path.municipio_id]);

    const loadData = async () => {
        setLoading(true);
        try {
            const result = await client.mappatura.gerarchica({
                consultazione_id: consultazione.id,
                regione_id: path.regione_id,
                provincia_id: path.provincia_id,
                comune_id: path.comune_id,
                municipio_id: path.municipio_id
            });

            if (result.error) {
                throw new Error(result.error);
            }

            setData(result);

            // Auto-skip if only one choice
            if (result.auto_skip && result.items && result.items.length === 1) {
                // Skip this level and drill down automatically
                handleDrillDown(result.items[0]);
                return;
            }

            window.scrollTo(0, 0);
        } catch (err) {
            console.error('Error loading hierarchical mapping data:', err);
            setError?.('Errore caricamento dati: ' + err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleDrillDown = (item) => {
        const newPath = { ...path };

        switch (item.tipo) {
            case 'regione':
                newPath.regione_id = item.id;
                newPath.provincia_id = null;
                newPath.comune_id = null;
                newPath.municipio_id = null;
                break;
            case 'provincia':
                newPath.provincia_id = item.id;
                newPath.comune_id = null;
                newPath.municipio_id = null;
                break;
            case 'comune':
                newPath.comune_id = item.id;
                newPath.municipio_id = null;
                break;
            case 'municipio':
                newPath.municipio_id = item.id;
                break;
            default:
                return;
        }

        setPath(newPath);
        setSearchQuery(''); // Reset search on navigation
    };

    const handleBack = () => {
        const newPath = { ...path };

        if (path.municipio_id) {
            newPath.municipio_id = null;
        } else if (path.comune_id) {
            newPath.comune_id = null;
        } else if (path.provincia_id) {
            newPath.provincia_id = null;
        } else if (path.regione_id) {
            newPath.regione_id = null;
        }

        setPath(newPath);
        setSearchQuery('');
    };

    const canGoBack = path.regione_id || path.provincia_id || path.comune_id || path.municipio_id;

    const getLevelIcon = () => {
        switch (data?.level) {
            case 'regioni': return 'fa-map';
            case 'province': return 'fa-map-marked-alt';
            case 'comuni': return 'fa-city';
            case 'municipi': return 'fa-building';
            case 'sezioni': return 'fa-list';
            default: return 'fa-th-list';
        }
    };

    const getLevelTitle = () => {
        switch (data?.level) {
            case 'regioni': return 'Regioni';
            case 'province': return 'Province';
            case 'comuni': return 'Comuni';
            case 'municipi': return 'Municipi';
            case 'sezioni': return 'Sezioni';
            default: return 'Mappatura';
        }
    };

    const filteredItems = data?.items?.filter(item => {
        if (!searchQuery) return true;
        const query = searchQuery.toLowerCase();
        return item.nome?.toLowerCase().includes(query) ||
               item.numero?.toString().includes(query) ||
               item.denominazione?.toLowerCase().includes(query) ||
               item.indirizzo?.toLowerCase().includes(query);
    }) || [];

    if (loading) {
        return (
            <div style={styles.loadingContainer}>
                <div className="spinner-border text-primary" role="status">
                    <span className="visually-hidden">Caricamento...</span>
                </div>
                <div className="mt-3 text-muted">Caricamento dati...</div>
            </div>
        );
    }

    if (!data) {
        return (
            <div className="alert alert-warning m-3">
                Nessun dato disponibile
            </div>
        );
    }

    const isSezioniLevel = data.level === 'sezioni';

    // Se siamo al livello sezioni, mostra il componente Mappatura completo
    if (isSezioniLevel && data.filters) {
        return (
            <div>
                {/* Header */}
                <div className="mappatura-header">
                    <div className="mappatura-header-title">Mappatura RDL</div>
                    <div className="mappatura-header-subtitle">
                        Assegnazione operativa RDL alle sezioni
                    </div>
                </div>
                {/* Breadcrumb per tornare indietro */}
                {canGoBack && (
                    <div className="p-3 border-bottom bg-light">
                        <button
                            onClick={handleBack}
                            className="btn btn-link p-0 text-decoration-none"
                        >
                            <i className="fas fa-chevron-left me-2"></i>
                            Torna alla navigazione
                        </button>
                        {data.summary && (
                            <span className="ms-3 text-muted">
                                <i className="fas fa-map-marker-alt me-1"></i>
                                {data.summary.tipo} {data.summary.nome}
                            </span>
                        )}
                    </div>
                )}
                <Mappatura
                    client={client}
                    setError={setError}
                    initialComuneId={data.filters.comune_id}
                    initialMunicipioId={data.filters.municipio_id}
                />
            </div>
        );
    }

    return (
        <div style={styles.container}>
            {/* Header */}
            <div className="mappatura-header">
                <div className="mappatura-header-title">Mappatura RDL</div>
                <div className="mappatura-header-subtitle">
                    Assegnazione operativa RDL alle sezioni
                </div>
            </div>
            {/* Fixed Header */}
            <div style={styles.header}>
                <div style={styles.headerTop}>
                    {canGoBack && (
                        <button
                            onClick={handleBack}
                            style={styles.backButton}
                            className="btn btn-link p-0"
                        >
                            <i className="fas fa-chevron-left"></i>
                        </button>
                    )}
                    <div style={styles.headerTitle}>
                        <i className={`fas ${getLevelIcon()} me-2`}></i>
                        {getLevelTitle()}
                    </div>
                    <div style={styles.badge}>
                        {data.items?.length || 0}
                    </div>
                </div>

                {/* Breadcrumb Path */}
                {data.breadcrumbs && data.breadcrumbs.length > 1 && (
                    <div style={styles.breadcrumbCompact}>
                        {data.breadcrumbs.map((crumb, idx) => (
                            <React.Fragment key={idx}>
                                {idx > 0 && <span className="text-muted mx-1">›</span>}
                                <span className={idx === data.breadcrumbs.length - 1 ? 'fw-bold' : 'text-muted'}>
                                    {crumb.nome}
                                </span>
                            </React.Fragment>
                        ))}
                    </div>
                )}

                {/* Search Bar */}
                {data.items && data.items.length > 5 && (
                    <div style={styles.searchContainer}>
                        <i className="fas fa-search" style={styles.searchIcon}></i>
                        <input
                            type="text"
                            placeholder={`Cerca ${isSezioniLevel ? 'sezioni' : getLevelTitle().toLowerCase()}...`}
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            style={styles.searchInput}
                        />
                        {searchQuery && (
                            <button
                                onClick={() => setSearchQuery('')}
                                style={styles.searchClear}
                                className="btn btn-link p-0"
                            >
                                <i className="fas fa-times"></i>
                            </button>
                        )}
                    </div>
                )}
            </div>

            {/* Content Area */}
            <div style={styles.content}>
                {/* Summary Cards */}
                {data.summary && (
                    <div className="row g-3 mb-4">
                        <div className="col-6 col-lg-3">
                            <div className="card h-100 border-primary">
                                <div className="card-body text-center p-2 p-md-3">
                                    <div className="text-muted small">{data.summary.tipo} {data.summary.nome}</div>
                                    <div className="fs-3 fw-bold text-primary">{data.summary.totale_sezioni || 0}</div>
                                    <div className="text-muted small">sezioni totali</div>
                                </div>
                            </div>
                        </div>
                        <div className="col-6 col-lg-3">
                            <div className="card h-100 border-success">
                                <div className="card-body text-center p-2 p-md-3">
                                    <div className="text-muted small">Assegnate</div>
                                    <div className="fs-3 fw-bold text-success">{data.summary.sezioni_assegnate || 0}</div>
                                    <div className="text-muted small">{data.summary.percentuale_assegnazione?.toFixed(1) || '0.0'}%</div>
                                </div>
                            </div>
                        </div>
                        <div className="col-6 col-lg-3">
                            <div className="card h-100 border-warning">
                                <div className="card-body text-center p-2 p-md-3">
                                    <div className="text-muted small">Da assegnare</div>
                                    <div className="fs-3 fw-bold text-warning">{data.summary.sezioni_non_assegnate || 0}</div>
                                    <div className="text-muted small">{(100 - (data.summary.percentuale_assegnazione || 0)).toFixed(1)}%</div>
                                </div>
                            </div>
                        </div>
                        <div className="col-6 col-lg-3">
                            <div className="card h-100 border-info">
                                <div className="card-body text-center p-2 p-md-3">
                                    <div className="text-muted small">RDL liberi</div>
                                    <div className="fs-3 fw-bold text-info">{data.summary.rdl_disponibili || 0}</div>
                                    <div className="text-muted small">disponibili</div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Divider */}
                {data.summary && filteredItems.length > 0 && (
                    <div style={styles.divider}>
                        <span style={styles.dividerText}>
                            {filteredItems.length} {isSezioniLevel ? 'sezioni' : getLevelTitle().toLowerCase()}
                            {searchQuery && ` (filtrat${filteredItems.length === 1 ? 'a' : 'i/e'})`}
                        </span>
                    </div>
                )}

                {/* Items List */}
                {filteredItems.length === 0 ? (
                    <div className="text-center p-4 text-muted">
                        <i className="fas fa-inbox fa-3x mb-3 d-block"></i>
                        {searchQuery ? `Nessun risultato per "${searchQuery}"` : 'Nessun dato disponibile'}
                    </div>
                ) : (
                    filteredItems.map((item) => (
                        <div
                            key={item.id}
                            style={styles.card}
                            onClick={() => {
                                if (isSezioniLevel) {
                                    onSezioneSelect?.(item);
                                } else {
                                    handleDrillDown(item);
                                }
                            }}
                        >
                            {/* Card Header */}
                            <div style={styles.cardHeader}>
                                <div style={styles.cardTitle}>
                                    {item.tipo === 'sezione' && (
                                        <span className="badge bg-secondary me-2" style={{ fontSize: '0.75rem' }}>
                                            Sez. {item.numero}
                                        </span>
                                    )}
                                    <span style={styles.cardName}>{item.nome || item.denominazione}</span>
                                    {item.sigla && (
                                        <span style={styles.cardSigla}>({item.sigla})</span>
                                    )}
                                </div>
                                {item.tipo !== 'sezione' && (
                                    <i className="fas fa-chevron-right text-muted"></i>
                                )}
                            </div>

                            {item.indirizzo && (
                                <div style={styles.cardSubtitle}>
                                    <i className="fas fa-map-marker-alt me-1"></i>
                                    {item.indirizzo}
                                </div>
                            )}

                            {/* Stats Grid for aggregated items */}
                            {item.tipo !== 'sezione' && (
                                <div style={styles.statsGrid}>
                                    <div style={styles.statBox}>
                                        <div style={styles.statValue}>
                                            {item.totale_sezioni || 0}
                                        </div>
                                        <div style={styles.statLabel}>Sezioni</div>
                                    </div>

                                    <div style={styles.statBox}>
                                        <div style={styles.statValue}>
                                            {item.sezioni_assegnate || 0}
                                        </div>
                                        <div style={styles.statLabel}>Assegnate</div>
                                    </div>

                                    <div style={styles.statBox}>
                                        <div style={styles.statValue}>
                                            {item.sezioni_non_assegnate || 0}
                                        </div>
                                        <div style={styles.statLabel}>Vuote</div>
                                    </div>

                                    <div style={styles.statBox}>
                                        <div style={styles.statValue}>
                                            {item.rdl_disponibili || 0}
                                        </div>
                                        <div style={styles.statLabel}>RDL liberi</div>
                                    </div>
                                </div>
                            )}

                            {/* Sezione status */}
                            {item.tipo === 'sezione' && (
                                <div style={styles.sezioneInfo}>
                                    {item.rdl_effettivo ? (
                                        <div style={styles.assignmentBadge}>
                                            <span className="badge bg-success" style={{ fontSize: '0.75rem' }}>
                                                <i className="fas fa-user-check me-1"></i>
                                                {item.rdl_effettivo.nome} {item.rdl_effettivo.cognome}
                                            </span>
                                            {item.rdl_supplente && (
                                                <span className="badge bg-info ms-2" style={{ fontSize: '0.75rem' }}>
                                                    <i className="fas fa-user me-1"></i>
                                                    Supp: {item.rdl_supplente.nome} {item.rdl_supplente.cognome}
                                                </span>
                                            )}
                                        </div>
                                    ) : (
                                        <div style={styles.assignmentBadge}>
                                            <span className="badge bg-warning text-dark" style={{ fontSize: '0.75rem' }}>
                                                <i className="fas fa-exclamation-triangle me-1"></i>
                                                Non Assegnata
                                            </span>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    ))
                )}
            </div>

            {/* Info Footer */}
            <div style={styles.footer}>
                <i className="fas fa-info-circle me-2"></i>
                {isSezioniLevel
                    ? 'Tocca una sezione per assegnare RDL'
                    : 'Tocca una card per navigare'}
            </div>
        </div>
    );
}

// Mobile-first styles (simili a ScrutinioAggregato)
const styles = {
    container: {
        minHeight: '100vh',
        backgroundColor: '#f5f5f5',
        display: 'flex',
        flexDirection: 'column'
    },
    loadingContainer: {
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '60vh'
    },
    header: {
        position: 'sticky',
        top: 0,
        backgroundColor: '#fff',
        borderBottom: '1px solid #dee2e6',
        zIndex: 100,
        padding: '12px 16px',
        boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
    },
    headerTop: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '8px'
    },
    backButton: {
        fontSize: '1.25rem',
        color: '#0d6efd',
        textDecoration: 'none',
        width: '32px',
        height: '32px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
    },
    headerTitle: {
        fontSize: '1.1rem',
        fontWeight: 'bold',
        flex: 1,
        textAlign: 'center'
    },
    badge: {
        backgroundColor: '#e9ecef',
        borderRadius: '12px',
        padding: '4px 12px',
        fontSize: '0.875rem',
        fontWeight: 'bold',
        color: '#495057'
    },
    breadcrumbCompact: {
        fontSize: '0.75rem',
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        color: '#6c757d',
        marginBottom: '8px'
    },
    searchContainer: {
        position: 'relative',
        marginTop: '8px'
    },
    searchIcon: {
        position: 'absolute',
        left: '12px',
        top: '50%',
        transform: 'translateY(-50%)',
        color: '#6c757d',
        fontSize: '0.875rem'
    },
    searchInput: {
        width: '100%',
        padding: '8px 36px 8px 36px',
        border: '1px solid #dee2e6',
        borderRadius: '8px',
        fontSize: '0.875rem',
        outline: 'none'
    },
    searchClear: {
        position: 'absolute',
        right: '8px',
        top: '50%',
        transform: 'translateY(-50%)',
        color: '#6c757d',
        fontSize: '0.875rem',
        background: 'none',
        border: 'none',
        cursor: 'pointer',
        padding: '4px 8px'
    },
    content: {
        flex: 1,
        padding: '12px',
        paddingBottom: '70px'
    },
    card: {
        backgroundColor: '#fff',
        borderRadius: '12px',
        padding: '16px',
        marginBottom: '12px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
        cursor: 'pointer',
        transition: 'transform 0.2s, box-shadow 0.2s'
    },
    summaryCard: {
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        color: '#fff',
        cursor: 'default',
        boxShadow: '0 4px 12px rgba(102, 126, 234, 0.3)',
        marginBottom: '16px'
    },
    summaryHeader: {
        display: 'flex',
        alignItems: 'center',
        marginBottom: '12px',
        fontSize: '0.875rem',
        fontWeight: 'bold',
        opacity: 0.9
    },
    summaryTitle: {
        fontSize: '1rem'
    },
    divider: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        margin: '16px 0',
        position: 'relative'
    },
    dividerText: {
        backgroundColor: '#f5f5f5',
        padding: '4px 16px',
        borderRadius: '12px',
        fontSize: '0.75rem',
        fontWeight: 'bold',
        color: '#6c757d',
        textTransform: 'uppercase'
    },
    cardHeader: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '8px'
    },
    cardTitle: {
        display: 'flex',
        alignItems: 'center',
        flex: 1
    },
    cardName: {
        fontSize: '1rem',
        fontWeight: 'bold',
        color: '#212529'
    },
    cardSigla: {
        marginLeft: '6px',
        fontSize: '0.875rem',
        color: '#6c757d'
    },
    cardSubtitle: {
        fontSize: '0.875rem',
        color: '#6c757d',
        marginBottom: '8px'
    },
    statsGrid: {
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(80px, 1fr))',
        gap: '8px',
        marginTop: '12px'
    },
    statBox: {
        backgroundColor: '#f8f9fa',
        borderRadius: '8px',
        padding: '8px',
        textAlign: 'center'
    },
    statBoxLarge: {
        gridColumn: 'span 2'
    },
    statValue: {
        fontSize: '1.125rem',
        fontWeight: 'bold',
        color: '#212529'
    },
    statValueLarge: {
        fontSize: '1.75rem',
        fontWeight: 'bold',
        color: '#0d6efd'
    },
    statLabel: {
        fontSize: '0.7rem',
        color: '#6c757d',
        marginTop: '2px'
    },
    sezioneInfo: {
        marginTop: '8px'
    },
    assignmentBadge: {
        display: 'flex',
        flexWrap: 'wrap',
        gap: '4px'
    },
    footer: {
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        backgroundColor: '#fff',
        borderTop: '1px solid #dee2e6',
        padding: '12px 16px',
        fontSize: '0.875rem',
        color: '#6c757d',
        textAlign: 'center',
        zIndex: 100
    }
};

export default MappaturaGerarchica;
