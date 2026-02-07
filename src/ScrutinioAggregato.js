import React, { useState, useEffect } from 'react';

/**
 * Componente per visualizzazione gerarchica aggregata dello scrutinio.
 * MOBILE-FIRST design con navigazione touch-friendly.
 *
 * Navigazione drill-down: Regione → Provincia → Comune → Municipio → Sezione
 * Con skip automatico se c'è solo una entità a un livello.
 *
 * Read-only per Delegati/SubDelegati che supervisionano territori.
 */
function ScrutinioAggregato({ client, consultazione, setError }) {
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
    }, [client, consultazione, path]);

    const loadData = async () => {
        setLoading(true);
        try {
            const result = await client.scrutinio.aggregato(
                consultazione.id,
                path.regione_id,
                path.provincia_id,
                path.comune_id,
                path.municipio_id
            );

            if (result.error) {
                throw new Error(result.error);
            }

            setData(result);
            // Scroll to top on navigation
            window.scrollTo(0, 0);
        } catch (err) {
            console.error('Error loading aggregated data:', err);
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
        setSearchQuery(''); // Reset search on drill-down
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
        setSearchQuery(''); // Reset search on back
    };

    const filteredItems = data?.items?.filter(item => {
        if (!searchQuery) return true;
        const query = searchQuery.toLowerCase();
        return item.nome?.toLowerCase().includes(query) ||
               item.sigla?.toLowerCase().includes(query) ||
               item.denominazione?.toLowerCase().includes(query);
    }) || [];

    const canGoBack = path.regione_id || path.provincia_id || path.comune_id || path.municipio_id;

    const getLevelIcon = () => {
        switch (data?.level) {
            case 'regioni': return 'fa-map';
            case 'province': return 'fa-map-marked-alt';
            case 'comuni': return 'fa-city';
            case 'municipi': return 'fa-building';
            case 'sezioni': return 'fa-poll-h';
            default: return 'fa-chart-bar';
        }
    };

    const getLevelTitle = () => {
        switch (data?.level) {
            case 'regioni': return 'Regioni';
            case 'province': return 'Province';
            case 'comuni': return 'Comuni';
            case 'municipi': return 'Municipi';
            case 'sezioni': return 'Sezioni';
            default: return 'Scrutinio';
        }
    };

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

    return (
        <div>
            {/* Page Header */}
            <div className="page-header scrutinio">
                <div className="page-header-title">
                    <i className="fas fa-chart-line"></i>
                    Risultati Live
                </div>
                <div className="page-header-subtitle">
                    Visualizzazione aggregata dei risultati elettorali
                </div>
            </div>

            <div style={styles.container}>
                {/* Summary Card */}
                {data.summary && (
                    <div style={{ ...styles.card, ...styles.summaryCard }}>
                        <div style={styles.summaryHeader}>
                            <i className="fas fa-chart-bar me-2"></i>
                            <span style={styles.summaryTitle}>Riepilogo {data.summary.nome}</span>
                        </div>

                        {/* Stats Grid */}
                        <div className="grid-auto-fit-sm" style={{ marginTop: '12px' }}>
                            {/* Affluenza - Grande e prominente */}
                            <div style={{ ...styles.statBox, ...styles.statBoxLarge, backgroundColor: 'rgba(255,255,255,0.25)' }}>
                                <div style={{ ...styles.statValueLarge, color: '#fff' }}>
                                    {data.summary.affluenza_percentuale?.toFixed(1) || '0.0'}%
                                </div>
                                <div style={{ ...styles.statLabel, color: 'rgba(255,255,255,0.8)' }}>Affluenza</div>
                            </div>

                            {/* Votanti */}
                            <div style={{ ...styles.statBox, backgroundColor: 'rgba(255,255,255,0.2)' }}>
                                <div style={{ ...styles.statValue, color: '#fff' }}>
                                    {data.summary.totale_votanti?.toLocaleString() || 0}
                                </div>
                                <div style={{ ...styles.statLabel, color: 'rgba(255,255,255,0.8)' }}>Votanti</div>
                            </div>

                            {/* Elettori */}
                            <div style={{ ...styles.statBox, backgroundColor: 'rgba(255,255,255,0.2)' }}>
                                <div style={{ ...styles.statValue, color: '#fff' }}>
                                    {data.summary.totale_elettori?.toLocaleString() || 0}
                                </div>
                                <div style={{ ...styles.statLabel, color: 'rgba(255,255,255,0.8)' }}>Elettori</div>
                            </div>

                            {/* Sezioni Complete */}
                            <div style={{ ...styles.statBox, backgroundColor: 'rgba(255,255,255,0.2)' }}>
                                <div style={{ ...styles.statValue, color: '#fff' }}>
                                    {data.summary.sezioni_complete || 0}/{data.summary.totale_sezioni}
                                </div>
                                <div style={{ ...styles.statLabel, color: 'rgba(255,255,255,0.8)' }}>Complete</div>
                            </div>
                        </div>

                        {/* Risultati Schede (compact) */}
                        {data.summary.schede && data.summary.schede.length > 0 && data.summary.schede.some(s => Object.keys(s.voti || {}).length > 0) && (
                            <div style={{ ...styles.resultsSection, borderTop: '1px solid rgba(255,255,255,0.2)' }}>
                                <div style={{ ...styles.resultsTitle, color: 'rgba(255,255,255,0.9)' }}>Risultati</div>
                                {data.summary.schede.map((scheda, idx) => (
                                    Object.keys(scheda.voti || {}).length > 0 && (
                                        <div key={idx} style={styles.schedaResults}>
                                            <div style={{ ...styles.schedaName, color: '#fff' }}>{scheda.scheda_nome}</div>
                                            <div className="grid-2-col gap-xs">
                                                {Object.entries(scheda.voti).map(([key, value]) => (
                                                    <div key={key} style={{ ...styles.votoRow, backgroundColor: 'rgba(255,255,255,0.2)' }}>
                                                        <span style={{ ...styles.votoLabel, color: 'rgba(255,255,255,0.8)' }}>{key.toUpperCase()}</span>
                                                        <span style={{ ...styles.votoValue, color: '#fff' }}>{value?.toLocaleString() || 0}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Level Navigation Header */}
                <div style={styles.header}>
                    <div style={styles.headerTop}>
                        {canGoBack ? (
                            <a
                                href="#"
                                onClick={(e) => { e.preventDefault(); handleBack(); }}
                                style={styles.backButton}
                            >
                                <i className="fas fa-arrow-left"></i>
                            </a>
                        ) : (
                            <div style={{ width: '32px' }}></div>
                        )}

                        <div style={styles.headerTitle}>
                            <i className={`fas ${getLevelIcon()} me-2`}></i>
                            {getLevelTitle()}
                        </div>

                        <div style={{ width: '32px' }}></div>
                    </div>

                    {/* Breadcrumb */}
                    {canGoBack && (
                        <div style={styles.breadcrumbCompact}>
                            {data.breadcrumb && data.breadcrumb.map((crumb, idx) => (
                                <span key={idx}>
                                    {idx > 0 && ' › '}
                                    {crumb.nome}
                                </span>
                            ))}
                        </div>
                    )}
                </div>

                {/* Search Bar */}
                {data.items && data.items.length > 5 && (
                    <div style={{ ...styles.searchContainer, marginBottom: '1rem' }}>
                        <i className="fas fa-search" style={styles.searchIcon}></i>
                        <input
                            type="text"
                            placeholder={`Cerca ${getLevelTitle().toLowerCase()}...`}
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

                {/* Divider */}
                {data.summary && filteredItems.length > 0 && (
                    <div style={styles.divider}>
                        <span style={styles.dividerText}>
                            {filteredItems.length} {getLevelTitle().toLowerCase()}
                            {searchQuery && ` (filtrat${filteredItems.length === 1 ? 'o' : 'i'})`}
                        </span>
                    </div>
                )}

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
                            onClick={() => item.tipo !== 'sezione' && handleDrillDown(item)}
                        >
                            {/* Card Header */}
                            <div style={styles.cardHeader}>
                                <div style={styles.cardTitle}>
                                    {item.tipo === 'sezione' && (
                                        <span className="badge bg-primary me-2" style={{ fontSize: '0.75rem' }}>
                                            Sez. {item.numero}
                                        </span>
                                    )}
                                    <span style={styles.cardName}>{item.nome}</span>
                                    {item.sigla && (
                                        <span style={styles.cardSigla}>({item.sigla})</span>
                                    )}
                                </div>
                                {item.tipo !== 'sezione' && (
                                    <i className="fas fa-chevron-right text-muted"></i>
                                )}
                            </div>

                            {item.denominazione && (
                                <div style={styles.cardSubtitle}>{item.denominazione}</div>
                            )}
                            {item.indirizzo && (
                                <div style={styles.cardSubtitle}>
                                    <i className="fas fa-map-marker-alt me-1"></i>
                                    {item.indirizzo}
                                </div>
                            )}

                            {/* Stats Grid */}
                            <div className="grid-auto-fit-sm" style={{ marginTop: '12px' }}>
                                {/* Affluenza - Grande e prominente */}
                                <div style={{ ...styles.statBox, ...styles.statBoxLarge }}>
                                    <div style={styles.statValueLarge}>
                                        {item.affluenza_percentuale?.toFixed(1) || '0.0'}%
                                    </div>
                                    <div style={styles.statLabel}>Affluenza</div>
                                </div>

                                {/* Votanti */}
                                <div style={styles.statBox}>
                                    <div style={styles.statValue}>
                                        {item.totale_votanti?.toLocaleString() || 0}
                                    </div>
                                    <div style={styles.statLabel}>Votanti</div>
                                </div>

                                {/* Elettori */}
                                <div style={styles.statBox}>
                                    <div style={styles.statValue}>
                                        {item.totale_elettori?.toLocaleString() || 0}
                                    </div>
                                    <div style={styles.statLabel}>Elettori</div>
                                </div>

                                {/* Sezioni Complete (solo per aggregati) */}
                                {item.totale_sezioni !== undefined && (
                                    <div style={styles.statBox}>
                                        <div style={styles.statValue}>
                                            {item.sezioni_complete || 0}/{item.totale_sezioni}
                                        </div>
                                        <div style={styles.statLabel}>Complete</div>
                                    </div>
                                )}
                            </div>

                            {/* Status Badge (solo per sezioni) */}
                            {item.is_complete !== undefined && (
                                <div style={styles.statusBadge}>
                                    {item.is_complete ? (
                                        <span className="badge bg-success" style={{ fontSize: '0.75rem' }}>
                                            <i className="fas fa-check me-1"></i>
                                            Completa
                                        </span>
                                    ) : (
                                        <span className="badge bg-warning" style={{ fontSize: '0.75rem' }}>
                                            <i className="fas fa-clock me-1"></i>
                                            In corso
                                        </span>
                                    )}
                                </div>
                            )}

                            {/* Risultati Schede (compact) */}
                            {item.schede && item.schede.length > 0 && item.schede.some(s => Object.keys(s.voti || {}).length > 0) && (
                                <div style={styles.resultsSection}>
                                    <div style={styles.resultsTitle}>Risultati</div>
                                    {item.schede.map((scheda, idx) => (
                                        Object.keys(scheda.voti || {}).length > 0 && (
                                            <div key={idx} style={styles.schedaResults}>
                                                <div style={styles.schedaName}>{scheda.scheda_nome}</div>
                                                <div className="grid-2-col gap-xs">
                                                    {Object.entries(scheda.voti).map(([key, value]) => (
                                                        <div key={key} style={styles.votoRow}>
                                                            <span style={styles.votoLabel}>{key.toUpperCase()}</span>
                                                            <span style={styles.votoValue}>{value?.toLocaleString() || 0}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )
                                    ))}
                                </div>
                            )}
                        </div>
                    ))
                )}
            </div>

            {/* Info Footer */}
            <div style={styles.footer}>
                <i className="fas fa-info-circle me-2"></i>
                Tocca una card per esplorare. Usa il pulsante indietro per tornare.
            </div>
        </div>
    );
}

// Mobile-first styles
const styles = {
    container: {
        minHeight: '100vh',
        backgroundColor: '#f5f5f5',
        padding: '12px',
        paddingBottom: '70px' // Space for footer
    },
    loadingContainer: {
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '60vh'
    },
    header: {
        backgroundColor: '#fff',
        borderBottom: '1px solid #dee2e6',
        padding: '12px 16px',
        marginBottom: '12px',
        borderRadius: '12px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
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
        outline: 'none',
        transition: 'border-color 0.2s'
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
        paddingBottom: '70px' // Space for footer
    },
    card: {
        backgroundColor: '#fff',
        borderRadius: '12px',
        padding: '16px',
        marginBottom: '12px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
        cursor: 'pointer',
        transition: 'transform 0.2s, box-shadow 0.2s',
        WebkitTapHighlightColor: 'rgba(0,0,0,0.05)'
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
        textTransform: 'uppercase',
        letterSpacing: '0.5px'
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
        marginBottom: '4px'
    },
    statBox: {
        backgroundColor: '#f8f9fa',
        borderRadius: '8px',
        padding: '8px',
        textAlign: 'center'
    },
    statBoxLarge: {
        gridColumn: 'span 2',
        backgroundColor: '#e7f3ff'
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
    statusBadge: {
        marginTop: '8px',
        display: 'flex',
        justifyContent: 'flex-end'
    },
    resultsSection: {
        marginTop: '12px',
        paddingTop: '12px',
        borderTop: '1px solid #e9ecef'
    },
    resultsTitle: {
        fontSize: '0.75rem',
        fontWeight: 'bold',
        color: '#6c757d',
        marginBottom: '8px',
        textTransform: 'uppercase'
    },
    schedaResults: {
        marginBottom: '8px'
    },
    schedaName: {
        fontSize: '0.875rem',
        fontWeight: 'bold',
        color: '#495057',
        marginBottom: '4px'
    },
    votoRow: {
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: '0.875rem',
        padding: '4px 8px',
        backgroundColor: '#f8f9fa',
        borderRadius: '4px'
    },
    votoLabel: {
        color: '#6c757d',
        fontWeight: '500'
    },
    votoValue: {
        fontWeight: 'bold',
        color: '#212529'
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

export default ScrutinioAggregato;
