import React from 'react';

/**
 * Dashboard Home - presenta le sezioni principali dell'app
 * Struttura allineata al menu: Territorio, Consultazione, Delegati, RDL, Scrutinio, Diretta
 */
function Dashboard({ user, permissions, consultazione, onNavigate }) {

    const sections = [
        // 1. TERRITORIO (solo superuser)
        {
            id: 'territorio',
            title: 'Territorio',
            icon: 'fa-globe-europe',
            color: '#6f42c1',
            gradient: 'linear-gradient(135deg, #6f42c1 0%, #5a32a3 100%)',
            description: 'Gestisci i dati territoriali italiani: regioni, province, comuni, municipi e sezioni elettorali.',
            purpose: 'Configurazione della base territoriale su cui operano le consultazioni elettorali.',
            features: [
                'Anagrafica regioni e province',
                'Gestione comuni e municipi',
                'Sezioni elettorali',
                'Import massivo CSV'
            ],
            permission: user?.is_superuser,
            action: () => onNavigate('territorio_admin'),
            cta: 'Gestisci Territorio'
        },

        // 2. CONSULTAZIONE
        {
            id: 'consultazione',
            title: 'Consultazione',
            icon: 'fa-vote-yea',
            color: '#0d6efd',
            gradient: 'linear-gradient(135deg, #0d6efd 0%, #0a58ca 100%)',
            description: 'Visualizza i dettagli della consultazione elettorale attiva: schede, quesiti, liste e candidati.',
            purpose: 'Ogni consultazione contiene una o più schede elettorali con i relativi quesiti o liste.',
            features: [
                `${consultazione?.schede?.length || 0} schede elettorali`,
                'Dettaglio quesiti referendum',
                'Liste e candidati',
                'Colori e denominazioni'
            ],
            permission: permissions.can_manage_elections && consultazione?.schede?.length > 0,
            action: () => {
                // Apri la prima scheda
                if (consultazione?.schede?.[0]) {
                    onNavigate('scheda');
                }
            },
            cta: 'Vedi Schede',
            extraInfo: consultazione?.nome
        },

        // 3. DELEGATI
        {
            id: 'delegati',
            title: 'Delegati',
            icon: 'fa-user-tie',
            color: '#198754',
            gradient: 'linear-gradient(135deg, #198754 0%, #146c43 100%)',
            description: 'Gestisci la catena delle deleghe: dal partito/comitato promotore fino ai sub-delegati territoriali.',
            purpose: 'I delegati di lista nominano sub-delegati che a loro volta designano i Rappresentanti di Lista.',
            features: [
                'Catena autorizzazioni',
                'Sub-deleghe territoriali',
                'Generazione documenti PDF',
                'Firma autenticata'
            ],
            permission: permissions.can_manage_delegations,
            action: () => onNavigate('deleghe'),
            cta: 'Gestisci Deleghe'
        },

        // 4. RDL
        {
            id: 'rdl',
            title: 'RDL',
            icon: 'fa-users',
            color: '#fd7e14',
            gradient: 'linear-gradient(135deg, #fd7e14 0%, #dc6a0c 100%)',
            description: 'Recluta, approva e assegna i Rappresentanti di Lista alle sezioni elettorali del territorio.',
            purpose: 'Gli RDL presidiano i seggi durante le votazioni e lo scrutinio, garantendo la regolarità delle operazioni.',
            features: [
                'Campagne di reclutamento',
                'Approvazione candidature',
                'Gestione sezioni',
                'Mappatura RDL-Sezioni'
            ],
            permission: permissions.can_manage_campaign || permissions.can_manage_rdl,
            action: () => onNavigate(permissions.can_manage_rdl ? 'gestione_rdl' : 'campagne'),
            cta: 'Gestisci RDL'
        },

        // 5. SCRUTINIO
        {
            id: 'scrutinio',
            title: 'Scrutinio',
            icon: 'fa-clipboard-check',
            color: '#20c997',
            gradient: 'linear-gradient(135deg, #20c997 0%, #1aa179 100%)',
            description: 'Inserisci i dati dello scrutinio per le sezioni assegnate: elettori, votanti, voti per scheda.',
            purpose: 'I dati inseriti dagli RDL permettono di seguire in tempo reale l\'andamento della consultazione.',
            features: [
                'Dati seggio (elettori/votanti)',
                'Voti per ogni scheda',
                'Schede bianche/nulle',
                'Salvataggio automatico'
            ],
            permission: permissions.has_scrutinio_access && consultazione,
            action: () => onNavigate('sections'),
            cta: 'Inserisci Dati',
            highlight: true
        },

        // 6. DIRETTA (solo per elezioni con liste/candidati, non referendum)
        {
            id: 'diretta',
            title: 'Diretta',
            icon: 'fa-chart-line',
            color: '#dc3545',
            gradient: 'linear-gradient(135deg, #dc3545 0%, #b02a37 100%)',
            description: 'Segui in tempo reale i risultati dello scrutinio con grafici, percentuali e proiezioni.',
            purpose: 'Dashboard KPI che aggrega i dati inseriti dagli RDL per mostrare l\'andamento live.',
            features: [
                'Aggiornamento real-time',
                'Grafici interattivi',
                'Affluenza e percentuali',
                'Confronto territoriale'
            ],
            permission: permissions.can_view_kpi && consultazione && consultazione.has_subdelegations !== false,
            action: () => onNavigate('kpi'),
            cta: 'Segui Live',
            badge: 'LIVE',
            badgeColor: '#dc3545'
        },

        // 7. ASSISTENZA
        {
            id: 'assistenza',
            title: 'Assistenza',
            icon: 'fa-life-ring',
            color: '#17a2b8',
            gradient: 'linear-gradient(135deg, #17a2b8 0%, #138496 100%)',
            description: 'Trova risposte, guide e supporto per ogni domanda. L\'assistente IA è pronto ad aiutarti.',
            purpose: 'Centro di supporto unificato: risorse, FAQ, guide operative e assistenza intelligente.',
            features: [
                'Assistente IA',
                'FAQ interattive',
                'Guide e tutorial',
                'Segnala problemi'
            ],
            permission: true, // Sempre visibile per tutti
            action: () => onNavigate('risorse'),
            cta: 'Ottieni Aiuto'
        },
    ];

    const visibleSections = sections.filter(s => s.permission);

    // Se non ci sono sezioni visibili, mostra messaggio
    if (visibleSections.length === 0) {
        return (
            <div className="dashboard">
                <div className="alert alert-info">
                    <h5><i className="fas fa-info-circle me-2"></i>Benvenuto!</h5>
                    <p className="mb-0">
                        Non hai ancora accesso a funzionalità specifiche.
                        Attendi che un delegato ti assegni un ruolo.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="dashboard">
            {/* Grid delle sezioni principali */}
            <div className="row g-4">
                {visibleSections.map((section) => (
                    <div key={section.id} className="col-12 col-md-6 col-xl-4">
                        <div
                            className={`card h-100 border-0 shadow-sm dashboard-card ${section.highlight ? 'dashboard-card-highlight' : ''}`}
                            style={{
                                cursor: 'pointer',
                                borderRadius: '16px',
                                overflow: 'hidden'
                            }}
                            onClick={section.action}
                        >
                            {/* Header con gradiente */}
                            <div className={`dashboard-card-header dashboard-card-gradient-${section.id}`}>
                                <div className="d-flex justify-content-between align-items-start">
                                    <div className="dashboard-card-icon">
                                        <i className={`fas ${section.icon}`}></i>
                                    </div>
                                    {section.badge && (
                                        <span className="badge dashboard-card-badge" style={{
                                            color: section.badgeColor || section.color
                                        }}>
                                            <span className="dashboard-card-badge-pulse" style={{
                                                background: section.badgeColor || section.color
                                            }}></span>
                                            {section.badge}
                                        </span>
                                    )}
                                </div>
                                <h4 className="mt-3 mb-1 fw-bold">{section.title}</h4>
                                {section.extraInfo && (
                                    <div className="dashboard-card-extra">
                                        {section.extraInfo}
                                    </div>
                                )}
                            </div>

                            {/* Body */}
                            <div className="card-body d-flex flex-column" style={{ padding: '20px' }}>
                                {/* Descrizione */}
                                <p className="text-muted mb-3" style={{ fontSize: '0.9rem', lineHeight: 1.5 }}>
                                    {section.description}
                                </p>

                                {/* Scopo */}
                                <div className="mb-3 p-3" style={{
                                    background: '#f8f9fa',
                                    borderRadius: '10px',
                                    borderLeft: `4px solid ${section.color}`
                                }}>
                                    <div className="small text-muted mb-1">
                                        <i className="fas fa-lightbulb me-1"></i> A cosa serve
                                    </div>
                                    <div style={{ fontSize: '0.85rem', color: '#333' }}>
                                        {section.purpose}
                                    </div>
                                </div>

                                {/* Features */}
                                <div className="flex-grow-1">
                                    <div className="row g-2">
                                        {section.features.map((feature, idx) => (
                                            <div key={idx} className="col-6">
                                                <div className="d-flex align-items-center" style={{ fontSize: '0.8rem' }}>
                                                    <i className="fas fa-check me-2" style={{ color: section.color, fontSize: '0.65rem' }}></i>
                                                    <span className="text-muted">{feature}</span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {/* CTA Button */}
                                <button className={`btn w-100 mt-3 dashboard-card-button dashboard-card-gradient-${section.id}`}>
                                    {section.cta}
                                    <i className="fas fa-arrow-right ms-2"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Styles */}
            <style>{`
                .dashboard-card {
                    transition: all 0.3s ease;
                }

                .dashboard-card:hover {
                    transform: translateY(-6px);
                    box-shadow: 0 12px 30px rgba(0,0,0,0.15) !important;
                }

                .dashboard-card:active {
                    transform: translateY(-3px);
                }

                .dashboard-card-highlight {
                    box-shadow: 0 4px 20px rgba(32, 201, 151, 0.3) !important;
                }

                @keyframes pulse {
                    0% { opacity: 1; }
                    50% { opacity: 0.4; }
                    100% { opacity: 1; }
                }
            `}</style>
        </div>
    );
}

export default Dashboard;
