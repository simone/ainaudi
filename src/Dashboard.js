import React from 'react';

/**
 * Dashboard Home - presenta le sezioni dell'app in modo chiaro e visuale
 * Ogni blocco è visibile solo se l'utente ha i permessi per accedervi
 */
function Dashboard({ user, permissions, consultazione, hasContributions, onNavigate }) {
    // Determina se è un referendum: dal tipo o dal nome della consultazione
    const isReferendum = consultazione?.tipo === 'REFERENDUM' ||
        consultazione?.nome?.toLowerCase().includes('referendum');

    // Determina il ruolo principale dell'utente per il messaggio di benvenuto
    const getUserRole = () => {
        if (user?.is_superuser) return { label: 'Amministratore', icon: '👑', color: '#ffc107' };
        if (permissions.referenti) return { label: 'Delegato/Sub-Delegato', icon: '🏛️', color: '#0d6efd' };
        if (permissions.sections) return { label: 'Rappresentante di Lista', icon: '📋', color: '#198754' };
        if (permissions.kpi) return { label: 'Osservatore KPI', icon: '📊', color: '#6f42c1' };
        return { label: 'Utente', icon: '👤', color: '#6c757d' };
    };

    const role = getUserRole();

    const sections = [
        // SEZIONI (area RDL - SubDelegato)
        {
            id: 'sezioni',
            title: 'Gestione Sezioni',
            icon: '🗺️',
            color: '#fd7e14',
            gradient: 'linear-gradient(135deg, #fd7e14 0%, #dc6a0c 100%)',
            description: 'Visualizza le sezioni elettorali del tuo territorio. Vedi l\'elenco completo, filtra per comune/municipio e verifica lo stato di copertura RDL.',
            features: [
                'Elenco sezioni del territorio',
                'Filtro per comune/municipio',
                'Stato copertura RDL',
            ],
            permission: permissions.referenti,
            action: () => onNavigate('sezioni'),
            cta: 'Gestione Sezioni'
        },
        // DESIGNAZIONE (area RDL - SubDelegato)
        {
            id: 'designazione',
            title: 'Designazione RDL',
            icon: '📝',
            color: '#20c997',
            gradient: 'linear-gradient(135deg, #20c997 0%, #1aa179 100%)',
            description: 'Designa i Rappresentanti di Lista per le sezioni del tuo territorio. Seleziona un RDL approvato per ogni sezione.',
            features: [
                'Seleziona sezione',
                'Scegli RDL approvato',
                'Crea designazione ufficiale',
            ],
            permission: permissions.referenti && consultazione,
            action: () => onNavigate('designazione'),
            cta: 'Nuova Designazione'
        },
        // CATENA DELEGHE (area Delegati)
        {
            id: 'deleghe',
            title: 'Catena Deleghe',
            icon: '🔗',
            color: '#6f42c1',
            gradient: 'linear-gradient(135deg, #6f42c1 0%, #5a32a3 100%)',
            description: isReferendum
                ? 'Visualizza la tua catena di autorizzazione dal Comitato Promotore fino a te.'
                : 'Visualizza la tua catena di autorizzazione dal Partito fino a te.',
            features: [
                'Catena completa delle deleghe',
                'Sub-deleghe ricevute/create',
                'Stato autorizzazioni',
            ],
            permission: permissions.referenti,
            action: () => onNavigate('deleghe'),
            cta: 'Vedi Catena'
        },
        // SCRUTINIO
        {
            id: 'sections',
            title: 'Scrutinio',
            icon: '🗳️',
            color: '#0d6efd',
            gradient: 'linear-gradient(135deg, #0d6efd 0%, #0a58ca 100%)',
            description: isReferendum
                ? 'Inserisci i risultati dello scrutinio per la tua sezione: voti SI, voti NO, schede bianche, nulle e contestate.'
                : 'Inserisci i risultati dello scrutinio per la tua sezione: voti per lista, preferenze, schede bianche e nulle.',
            features: [
                'Inserimento dati scrutinio',
                'Validazione automatica',
                'Salvataggio sicuro',
            ],
            permission: permissions.sections && consultazione,
            action: () => onNavigate('sections'),
            cta: 'Vai allo Scrutinio'
        },
        // KPI / DIRETTA
        {
            id: 'kpi',
            title: 'Diretta Risultati',
            icon: '📊',
            color: '#dc3545',
            gradient: 'linear-gradient(135deg, #dc3545 0%, #b02a37 100%)',
            description: 'Segui in tempo reale l\'andamento dello scrutinio. Visualizza grafici, percentuali e proiezioni basate sui dati inseriti dai RDL.',
            features: [
                'Aggiornamento in tempo reale',
                'Grafici interattivi',
                'Confronto tra territori',
            ],
            permission: permissions.kpi && consultazione && hasContributions,
            action: () => onNavigate('kpi'),
            cta: 'Segui la Diretta',
            badge: hasContributions ? 'LIVE' : null
        },
        // RISORSE
        {
            id: 'risorse',
            title: 'Risorse e FAQ',
            icon: '📚',
            color: '#17a2b8',
            gradient: 'linear-gradient(135deg, #20c997 0%, #17a2b8 100%)',
            description: 'Consulta documenti, guide operative e domande frequenti. Tutto quello che ti serve per svolgere al meglio il tuo ruolo di Rappresentante di Lista.',
            features: [
                'Modulistica ufficiale',
                'Guide e tutorial',
                'FAQ interattive',
            ],
            permission: true, // Sempre visibile
            action: () => onNavigate('risorse'),
            cta: 'Consulta Risorse'
        },
    ];

    // Sezioni admin/gestione
    const adminSections = [
        {
            id: 'gestione_rdl',
            title: 'Approva Candidature RDL',
            icon: '✅',
            color: '#198754',
            gradient: 'linear-gradient(135deg, #198754 0%, #146c43 100%)',
            description: 'Revisiona e approva le candidature spontanee di chi vuole diventare Rappresentante di Lista.',
            features: [
                'Lista candidature in attesa',
                'Approvazione/rifiuto',
                'Notifica automatica',
            ],
            permission: permissions.gestione_rdl,
            action: () => onNavigate('gestione_rdl'),
            cta: 'Approva RDL'
        },
        {
            id: 'pdf',
            title: 'Stampa Designazioni',
            icon: '🖨️',
            color: '#6c757d',
            gradient: 'linear-gradient(135deg, #6c757d 0%, #5a6268 100%)',
            description: 'Genera i PDF delle designazioni con gli allegati di delega per la stampa e la consegna ai seggi.',
            features: [
                'PDF designazioni',
                'Allegati delega inclusi',
                'Stampa batch',
            ],
            permission: user?.email === 's.federici@gmail.com' && consultazione,
            action: () => onNavigate('pdf'),
            cta: 'Stampa'
        },
    ];

    const visibleSections = sections.filter(s => s.permission);
    const visibleAdminSections = adminSections.filter(s => s.permission);

    return (
        <div className="dashboard">
            {/* Hero Welcome */}
            <div className="card mb-4" style={{
                background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
                border: 'none',
                borderRadius: '16px',
                overflow: 'hidden'
            }}>
                <div className="card-body text-white py-4">
                    <div className="row align-items-center">
                        <div className="col-md-8">
                            <div className="d-flex align-items-center mb-3">
                                <span style={{ fontSize: '2.5rem', marginRight: '16px' }}>{role.icon}</span>
                                <div>
                                    <h2 className="mb-0">Benvenuto, {user?.first_name || user?.display_name?.split(' ')[0] || 'Utente'}!</h2>
                                    <span className="badge" style={{
                                        backgroundColor: role.color,
                                        fontSize: '0.85rem',
                                        padding: '6px 12px',
                                        marginTop: '8px',
                                        display: 'inline-block'
                                    }}>
                                        {role.label}
                                    </span>
                                </div>
                            </div>
                            <p className="mb-0 opacity-75" style={{ fontSize: '1.1rem' }}>
                                {consultazione
                                    ? `Stai lavorando su: ${consultazione.nome}`
                                    : 'Nessuna consultazione attiva al momento'}
                            </p>
                        </div>
                        <div className="col-md-4 text-end d-none d-md-block">
                            <div style={{ fontSize: '5rem', opacity: 0.3 }}>
                                {isReferendum ? '🗳️' : '🏛️'}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Quick Stats (if available) */}
            {permissions.referenti && (
                <div className="row mb-4 g-3">
                    <div className="col-6 col-md-3">
                        <div className="card h-100 border-0 shadow-sm">
                            <div className="card-body text-center">
                                <div style={{ fontSize: '2rem', color: '#6f42c1' }}>🔗</div>
                                <div className="small text-muted">Il Tuo Ruolo</div>
                                <div className="fw-bold">{role.label}</div>
                            </div>
                        </div>
                    </div>
                    <div className="col-6 col-md-3">
                        <div className="card h-100 border-0 shadow-sm">
                            <div className="card-body text-center">
                                <div style={{ fontSize: '2rem', color: '#fd7e14' }}>{isReferendum ? '🗳️' : '🏛️'}</div>
                                <div className="small text-muted">Tipo</div>
                                <div className="fw-bold">{consultazione?.tipo_display || (isReferendum ? 'Referendum' : 'Elezioni')}</div>
                            </div>
                        </div>
                    </div>
                    <div className="col-6 col-md-3">
                        <div className="card h-100 border-0 shadow-sm">
                            <div className="card-body text-center">
                                <div style={{ fontSize: '2rem', color: '#198754' }}>📅</div>
                                <div className="small text-muted">Data</div>
                                <div className="fw-bold">
                                    {consultazione?.data_inizio
                                        ? new Date(consultazione.data_inizio).toLocaleDateString('it-IT', { day: 'numeric', month: 'short' })
                                        : '-'}
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="col-6 col-md-3">
                        <div className="card h-100 border-0 shadow-sm">
                            <div className="card-body text-center">
                                <div style={{ fontSize: '2rem', color: hasContributions ? '#dc3545' : '#6c757d' }}>
                                    {hasContributions ? '🔴' : '⚪'}
                                </div>
                                <div className="small text-muted">Stato</div>
                                <div className="fw-bold">{hasContributions ? 'In corso' : 'In attesa'}</div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Main Sections */}
            <h5 className="mb-3 text-muted">
                <i className="fas fa-th-large me-2"></i>
                Le tue funzionalità
            </h5>

            <div className="row g-4 mb-4">
                {visibleSections.map((section) => (
                    <div key={section.id} className="col-12 col-md-6 col-lg-4">
                        <div
                            className="card h-100 border-0 shadow-sm dashboard-card"
                            style={{
                                cursor: 'pointer',
                                transition: 'all 0.3s ease',
                                borderRadius: '12px',
                                overflow: 'hidden'
                            }}
                            onClick={section.action}
                        >
                            {/* Card Header with gradient */}
                            <div style={{
                                background: section.gradient,
                                padding: '20px',
                                color: 'white',
                                position: 'relative'
                            }}>
                                <div className="d-flex justify-content-between align-items-start">
                                    <span style={{ fontSize: '2.5rem' }}>{section.icon}</span>
                                    {section.badge && (
                                        <span className="badge bg-light text-danger" style={{
                                            animation: 'pulse 1.5s infinite'
                                        }}>
                                            <span style={{
                                                display: 'inline-block',
                                                width: '8px',
                                                height: '8px',
                                                backgroundColor: '#dc3545',
                                                borderRadius: '50%',
                                                marginRight: '4px'
                                            }}></span>
                                            {section.badge}
                                        </span>
                                    )}
                                </div>
                                <h5 className="mt-3 mb-0">{section.title}</h5>
                            </div>

                            {/* Card Body */}
                            <div className="card-body">
                                <p className="text-muted small mb-3">
                                    {section.description}
                                </p>

                                {/* Features list */}
                                <ul className="list-unstyled mb-0 small">
                                    {section.features.map((feature, idx) => (
                                        <li key={idx} className="mb-1">
                                            <i className="fas fa-check-circle me-2" style={{ color: section.color }}></i>
                                            {feature}
                                        </li>
                                    ))}
                                </ul>
                            </div>

                            {/* Card Footer */}
                            <div className="card-footer bg-transparent border-0 pt-0">
                                <button
                                    className="btn w-100"
                                    style={{
                                        backgroundColor: section.color,
                                        color: 'white',
                                        borderRadius: '8px'
                                    }}
                                >
                                    {section.cta}
                                    <i className="fas fa-arrow-right ms-2"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Admin Sections */}
            {visibleAdminSections.length > 0 && (
                <>
                    <h5 className="mb-3 text-muted">
                        <i className="fas fa-cog me-2"></i>
                        Amministrazione
                    </h5>

                    <div className="row g-4 mb-4">
                        {visibleAdminSections.map((section) => (
                            <div key={section.id} className="col-12 col-md-6">
                                <div
                                    className="card h-100 border-0 shadow-sm dashboard-card"
                                    style={{
                                        cursor: 'pointer',
                                        transition: 'all 0.3s ease',
                                        borderRadius: '12px',
                                        overflow: 'hidden'
                                    }}
                                    onClick={section.action}
                                >
                                    <div className="card-body d-flex align-items-center">
                                        <div style={{
                                            width: '60px',
                                            height: '60px',
                                            borderRadius: '12px',
                                            background: section.gradient,
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            marginRight: '16px',
                                            flexShrink: 0
                                        }}>
                                            <span style={{ fontSize: '1.8rem' }}>{section.icon}</span>
                                        </div>
                                        <div className="flex-grow-1">
                                            <h6 className="mb-1">{section.title}</h6>
                                            <p className="text-muted small mb-0">{section.description}</p>
                                        </div>
                                        <i className="fas fa-chevron-right text-muted ms-2"></i>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </>
            )}

            {/* Help Section */}
            <div className="card border-0 shadow-sm" style={{
                background: 'linear-gradient(135deg, #e9ecef 0%, #f8f9fa 100%)',
                borderRadius: '12px'
            }}>
                <div className="card-body">
                    <div className="row align-items-center">
                        <div className="col-md-8">
                            <h5 className="mb-2">
                                <i className="fas fa-question-circle me-2 text-info"></i>
                                Hai bisogno di aiuto?
                            </h5>
                            <p className="mb-0 text-muted">
                                Consulta le risorse e le FAQ per trovare tutte le informazioni di cui hai bisogno.
                                Troverai guide, modulistica e risposte alle domande più frequenti.
                            </p>
                        </div>
                        <div className="col-md-4 text-md-end mt-3 mt-md-0">
                            <button
                                className="btn btn-info"
                                onClick={() => onNavigate('risorse')}
                            >
                                <i className="fas fa-book me-2"></i>
                                Vai alle Risorse
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Inline Styles for hover effects */}
            <style>{`
                .dashboard-card:hover {
                    transform: translateY(-4px);
                    box-shadow: 0 8px 25px rgba(0,0,0,0.15) !important;
                }

                .dashboard-card:active {
                    transform: translateY(-2px);
                }

                @keyframes pulse {
                    0% { opacity: 1; }
                    50% { opacity: 0.5; }
                    100% { opacity: 1; }
                }
            `}</style>
        </div>
    );
}

export default Dashboard;
