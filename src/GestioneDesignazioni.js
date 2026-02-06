import React, { useState, useEffect } from 'react';

/**
 * Converte un numero in numeri romani
 */
const toRoman = (num) => {
    const romanNumerals = [
        { value: 1000, numeral: 'M' },
        { value: 900, numeral: 'CM' },
        { value: 500, numeral: 'D' },
        { value: 400, numeral: 'CD' },
        { value: 100, numeral: 'C' },
        { value: 90, numeral: 'XC' },
        { value: 50, numeral: 'L' },
        { value: 40, numeral: 'XL' },
        { value: 10, numeral: 'X' },
        { value: 9, numeral: 'IX' },
        { value: 5, numeral: 'V' },
        { value: 4, numeral: 'IV' },
        { value: 1, numeral: 'I' }
    ];
    let result = '';
    for (const { value, numeral } of romanNumerals) {
        while (num >= value) {
            result += numeral;
            num -= value;
        }
    }
    return result;
};

function GestioneDesignazioni({ client, setError }) {
    const [stats, setStats] = useState(null);
    const [designazioni, setDesignazioni] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        setLoading(true);
        try {
            // Get user's delegation chain
            const chain = await client.deleghe.miaCatena();

            if (chain.error) {
                setError(chain.error);
                return;
            }

            // Combine all designations (both made and received)
            const allDesignazioni = [
                ...chain.designazioni_fatte.map(d => ({ ...d, ruolo: 'designante' })),
                ...chain.designazioni_ricevute.map(d => ({ ...d, ruolo: 'designato' }))
            ];

            // Calculate stats
            const totale = allDesignazioni.length;
            const effettivo = allDesignazioni.filter(d => d.ruolo_rdl === 'EFFETTIVO').length;
            const supplente = allDesignazioni.filter(d => d.ruolo_rdl === 'SUPPLENTE').length;
            const confermate = allDesignazioni.filter(d => d.stato === 'CONFERMATA').length;
            const bozze = allDesignazioni.filter(d => d.stato === 'BOZZA').length;

            setStats({
                totale,
                effettivo,
                supplente,
                confermate,
                bozze,
                is_delegato: chain.is_delegato,
                is_sub_delegato: chain.is_sub_delegato,
                is_rdl: chain.is_rdl
            });

            setDesignazioni(allDesignazioni);
        } catch (err) {
            setError(`Errore nel caricamento designazioni: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    const calcPercentuale = (parte, totale) => {
        if (!totale) return 0;
        return Math.round((parte / totale) * 100);
    };

    const getStatoBadgeClass = (stato) => {
        switch (stato) {
            case 'CONFERMATA':
                return 'bg-success';
            case 'BOZZA':
                return 'bg-warning';
            case 'RIFIUTATA':
                return 'bg-danger';
            default:
                return 'bg-secondary';
        }
    };

    const getRuoloBadgeClass = (ruolo) => {
        return ruolo === 'EFFETTIVO' ? 'bg-primary' : 'bg-info';
    };

    if (loading) {
        return (
            <div className="loading-container" role="status" aria-live="polite">
                <div className="spinner-border text-primary">
                    <span className="visually-hidden">Caricamento in corso...</span>
                </div>
                <p className="loading-text">Caricamento designazioni...</p>
            </div>
        );
    }

    return (
        <>
            {/* Page Header */}
            <div className="page-header rdl">
                <div className="page-header-title">
                    <i className="fas fa-user-check"></i>
                    Designazioni RDL
                </div>
                <div className="page-header-subtitle">
                    Le tue designazioni come Rappresentante di Lista
                    {stats && (
                        <span className="page-header-badge">
                            {stats.is_delegato && 'Delegato'}
                            {stats.is_sub_delegato && 'Sub-Delegato'}
                            {stats.is_rdl && 'RDL'}
                        </span>
                    )}
                </div>
            </div>

            {stats && (
                <>
                    {/* Summary Cards */}
                    <div className="row g-3 mb-4">
                        {/* Card Totale Designazioni */}
                        <div className="col-6 col-lg-3">
                            <div className="card h-100 border-primary">
                                <div className="card-body text-center p-2 p-md-3">
                                    <div className="text-muted small">Totale</div>
                                    <div className="fs-3 fw-bold text-primary">
                                        {stats.totale}
                                    </div>
                                    <div className="text-muted small">designazioni</div>
                                </div>
                            </div>
                        </div>

                        {/* Card Effettivi */}
                        <div className="col-6 col-lg-3">
                            <div className="card h-100 border-info">
                                <div className="card-body text-center p-2 p-md-3">
                                    <div className="text-muted small">Effettivo</div>
                                    <div className="fs-3 fw-bold text-info">
                                        {stats.effettivo}
                                    </div>
                                    <div className="text-muted small">
                                        {calcPercentuale(stats.effettivo, stats.totale)}%
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Card Supplenti */}
                        <div className="col-6 col-lg-3">
                            <div className="card h-100 border-info">
                                <div className="card-body text-center p-2 p-md-3">
                                    <div className="text-muted small">Supplente</div>
                                    <div className="fs-3 fw-bold text-info">
                                        {stats.supplente}
                                    </div>
                                    <div className="text-muted small">
                                        {calcPercentuale(stats.supplente, stats.totale)}%
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Card Confermate */}
                        <div className="col-6 col-lg-3">
                            <div className="card h-100 border-success">
                                <div className="card-body text-center p-2 p-md-3">
                                    <div className="text-muted small">Confermate</div>
                                    <div className="fs-3 fw-bold text-success">
                                        {stats.confermate}
                                    </div>
                                    <div className="text-muted small">
                                        {calcPercentuale(stats.confermate, stats.totale)}%
                                    </div>
                                    {stats.bozze > 0 && (
                                        <div className="small text-warning mt-1">
                                            {stats.bozze} bozze
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="card mb-4">
                        <div className="card-body">
                            <h6 className="card-title">Stato designazioni</h6>
                            <div className="progress" style={{ height: '24px' }}>
                                <div
                                    className="progress-bar bg-success"
                                    style={{ width: `${calcPercentuale(stats.confermate, stats.totale)}%` }}
                                    role="progressbar"
                                    aria-valuenow={stats.confermate}
                                    aria-valuemin="0"
                                    aria-valuemax={stats.totale}
                                >
                                    {calcPercentuale(stats.confermate, stats.totale)}% confermate
                                </div>
                                {stats.bozze > 0 && (
                                    <div
                                        className="progress-bar bg-warning"
                                        style={{ width: `${calcPercentuale(stats.bozze, stats.totale)}%` }}
                                        role="progressbar"
                                        aria-valuenow={stats.bozze}
                                        aria-valuemin="0"
                                        aria-valuemax={stats.totale}
                                    >
                                        {calcPercentuale(stats.bozze, stats.totale)}% bozze
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </>
            )}

            {/* Designazioni List */}
            <div className="card">
                <div className="card-header">
                    <h5 className="mb-0">
                        <i className="fas fa-list me-2"></i>
                        Elenco Designazioni
                    </h5>
                </div>
                {designazioni.length === 0 ? (
                    <div className="card-body text-center text-muted py-4">
                        <i className="fas fa-inbox fa-3x mb-3"></i>
                        <p className="mb-0">Nessuna designazione presente</p>
                    </div>
                ) : (
                    <div className="table-responsive">
                        <table className="table table-hover mb-0">
                            <thead className="table-light">
                                <tr>
                                    <th>Comune</th>
                                    <th>Sezione</th>
                                    <th>Plesso</th>
                                    <th>Effettivo</th>
                                    <th>Supplente</th>
                                    <th>Ruolo</th>
                                    <th>Stato</th>
                                    <th>Tuo Ruolo</th>
                                </tr>
                            </thead>
                            <tbody>
                                {designazioni.map((des, index) => (
                                    <tr key={index}>
                                        <td className="fw-bold">
                                            {des.sezione?.comune?.nome || '-'}
                                            {des.sezione?.municipio && (
                                                <small className="text-muted ms-1">
                                                    (Mun. {toRoman(des.sezione.municipio.numero)})
                                                </small>
                                            )}
                                        </td>
                                        <td>
                                            {des.sezione?.numero || '-'}
                                        </td>
                                        <td className="small">
                                            {des.sezione?.denominazione || des.sezione?.indirizzo || '-'}
                                        </td>
                                        <td>
                                            {des.ruolo_rdl === 'EFFETTIVO' ? (
                                                <div>
                                                    <div className="fw-bold">{des.cognome} {des.nome}</div>
                                                    {des.email && <small className="text-muted">{des.email}</small>}
                                                </div>
                                            ) : (
                                                <span className="text-muted">-</span>
                                            )}
                                        </td>
                                        <td>
                                            {des.ruolo_rdl === 'SUPPLENTE' ? (
                                                <div>
                                                    <div className="fw-bold">{des.cognome} {des.nome}</div>
                                                    {des.email && <small className="text-muted">{des.email}</small>}
                                                </div>
                                            ) : (
                                                <span className="text-muted">-</span>
                                            )}
                                        </td>
                                        <td>
                                            <span className={`badge ${getRuoloBadgeClass(des.ruolo_rdl)}`}>
                                                {des.ruolo_rdl}
                                            </span>
                                        </td>
                                        <td>
                                            <span className={`badge ${getStatoBadgeClass(des.stato)}`}>
                                                {des.stato}
                                            </span>
                                        </td>
                                        <td>
                                            <span className={`badge ${des.ruolo === 'designante' ? 'bg-secondary' : 'bg-primary'}`}>
                                                {des.ruolo === 'designante' ? 'Designante' : 'Designato'}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Refresh Button */}
            <div className="text-center mt-3">
                <button
                    className="btn btn-outline-secondary"
                    onClick={loadData}
                    disabled={loading}
                >
                    <i className="fas fa-sync-alt me-2"></i>
                    Aggiorna dati
                </button>
            </div>
        </>
    );
}

export default GestioneDesignazioni;
