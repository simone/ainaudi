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

function GestioneSezioni({ client, setError }) {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [activeView, setActiveView] = useState('panoramica'); // 'panoramica' | 'aggiungi' | 'carica'

    // Upload state
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [result, setResult] = useState(null);

    // Add/Edit section state
    const [formData, setFormData] = useState({
        sezione: '',
        comune: '',
        municipio: '',
        indirizzo: ''
    });
    const [saving, setSaving] = useState(false);
    const [saveResult, setSaveResult] = useState(null);

    // Expanded sections for drill-down
    const [expandedComune, setExpandedComune] = useState(null);

    useEffect(() => {
        loadStats();
    }, []);

    const loadStats = async () => {
        setLoading(true);
        try {
            const data = await client.sections.stats();
            if (data.error) {
                setError(data.error);
            } else {
                setStats(data);
            }
        } catch (err) {
            setError(`Errore nel caricamento statistiche: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    // Helper to describe user's territory scope
    const getTerritorioLabel = () => {
        if (!stats) return '';
        // If perComune has only one comune
        const comuni = Object.keys(stats.perComune || {});
        if (comuni.length === 1) {
            const comune = comuni[0];
            // Check if there are specific municipi
            const municipi = Object.keys(stats.perMunicipio || {}).filter(
                m => stats.perMunicipio[m].visibili > 0
            );
            if (municipi.length > 0 && municipi.length < 15) {
                const municipiRoman = municipi.map(m => `Mun. ${toRoman(+m)}`).join(', ');
                return `${comune} - ${municipiRoman}`;
            }
            return comune;
        }
        return `${comuni.length} comuni`;
    };

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile) {
            if (!selectedFile.name.endsWith('.csv')) {
                setError('Seleziona un file CSV');
                return;
            }
            setFile(selectedFile);
            setResult(null);
        }
    };

    const handleUpload = async () => {
        if (!file) {
            setError('Seleziona un file prima di caricare');
            return;
        }

        setUploading(true);
        setError(null);
        setResult(null);

        try {
            const res = await client.sections.upload(file);
            if (res.error) {
                setError(res.error);
            } else {
                setResult(res);
                // Ricarica le statistiche dopo l'upload
                loadStats();
            }
        } catch (err) {
            setError(`Errore durante il caricamento: ${err.message}`);
        } finally {
            setUploading(false);
        }
    };

    const handleFormChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value
        }));
    };

    const handleAddSection = async (e) => {
        e.preventDefault();

        if (!formData.sezione || !formData.comune) {
            setError('Sezione e Comune sono obbligatori');
            return;
        }

        setSaving(true);
        setSaveResult(null);
        setError(null);

        try {
            // Per ora usiamo l'upload con un singolo record
            // In futuro si può creare un endpoint dedicato
            const csvContent = `SEZIONE,COMUNE,MUNICIPIO,INDIRIZZO\n${formData.sezione},${formData.comune},${formData.municipio || ''},"${formData.indirizzo || ''}"`;
            const blob = new Blob([csvContent], { type: 'text/csv' });
            const file = new File([blob], 'sezione.csv', { type: 'text/csv' });

            const res = await client.sections.upload(file);
            if (res.error) {
                setError(res.error);
            } else {
                setSaveResult({
                    success: true,
                    message: `Sezione ${formData.sezione} di ${formData.comune} aggiunta con successo`
                });
                // Reset form
                setFormData({
                    sezione: '',
                    comune: '',
                    municipio: '',
                    indirizzo: ''
                });
                // Ricarica statistiche
                loadStats();
            }
        } catch (err) {
            setError(`Errore durante il salvataggio: ${err.message}`);
        } finally {
            setSaving(false);
        }
    };

    const handleAddMultiple = async (e) => {
        e.preventDefault();

        const startSection = parseInt(formData.sezioneInizio);
        const endSection = parseInt(formData.sezioneFine);

        if (!startSection || !endSection || !formData.comune) {
            setError('Sezione inizio, fine e Comune sono obbligatori');
            return;
        }

        if (startSection > endSection) {
            setError('La sezione di inizio deve essere minore o uguale alla sezione di fine');
            return;
        }

        if (endSection - startSection > 100) {
            setError('Puoi aggiungere massimo 100 sezioni alla volta');
            return;
        }

        setSaving(true);
        setSaveResult(null);
        setError(null);

        try {
            let csvContent = 'SEZIONE,COMUNE,MUNICIPIO,INDIRIZZO\n';
            for (let i = startSection; i <= endSection; i++) {
                csvContent += `${i},${formData.comune},${formData.municipio || ''},"${formData.indirizzo || ''}"\n`;
            }

            const blob = new Blob([csvContent], { type: 'text/csv' });
            const file = new File([blob], 'sezioni.csv', { type: 'text/csv' });

            const res = await client.sections.upload(file);
            if (res.error) {
                setError(res.error);
            } else {
                setSaveResult({
                    success: true,
                    message: `Aggiunte ${endSection - startSection + 1} sezioni (${startSection}-${endSection}) per ${formData.comune}`
                });
                // Reset form
                setFormData({
                    sezione: '',
                    sezioneInizio: '',
                    sezioneFine: '',
                    comune: '',
                    municipio: '',
                    indirizzo: ''
                });
                // Ricarica statistiche
                loadStats();
            }
        } catch (err) {
            setError(`Errore durante il salvataggio: ${err.message}`);
        } finally {
            setSaving(false);
        }
    };

    const calcPercentuale = (parte, totale) => {
        if (!totale) return 0;
        return Math.round((parte / totale) * 100);
    };

    if (loading) {
        return (
            <div className="loading-container" role="status" aria-live="polite">
                <div className="spinner-border text-primary">
                    <span className="visually-hidden">Caricamento in corso...</span>
                </div>
                <p className="loading-text">Caricamento panoramica sezioni...</p>
            </div>
        );
    }

    return (
        <>
            {/* Tab Navigation */}
            <ul className="nav nav-tabs mb-3">
                <li className="nav-item">
                    <button
                        className={`nav-link ${activeView === 'panoramica' ? 'active' : ''}`}
                        onClick={() => setActiveView('panoramica')}
                        aria-selected={activeView === 'panoramica'}
                    >
                        <i className="fas fa-chart-pie me-2"></i>
                        Panoramica
                    </button>
                </li>
                <li className="nav-item">
                    <button
                        className={`nav-link ${activeView === 'aggiungi' ? 'active' : ''}`}
                        onClick={() => setActiveView('aggiungi')}
                        aria-selected={activeView === 'aggiungi'}
                    >
                        <i className="fas fa-plus me-2"></i>
                        Aggiungi
                    </button>
                </li>
                <li className="nav-item">
                    <button
                        className={`nav-link ${activeView === 'carica' ? 'active' : ''}`}
                        onClick={() => setActiveView('carica')}
                        aria-selected={activeView === 'carica'}
                    >
                        <i className="fas fa-file-import me-2"></i>
                        Importa CSV
                    </button>
                </li>
            </ul>

            {/* Panoramica View */}
            {activeView === 'panoramica' && stats && (
                <>
                    {/* Summary Cards */}
                    <div className="row g-3 mb-4">
                        {/* Card Totale Italia */}
                        <div className="col-6 col-lg-3">
                            <div className="card h-100 border-primary">
                                <div className="card-body text-center p-2 p-md-3">
                                    <div className="text-muted small">Italia</div>
                                    <div className="fs-3 fw-bold text-primary">
                                        {stats.totale?.sezioni?.toLocaleString() || 0}
                                    </div>
                                    <div className="text-muted small">sezioni totali</div>
                                    <div className="small text-secondary">
                                        {stats.totale?.comuni || 0} comuni
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Card Tue Sezioni */}
                        <div className="col-6 col-lg-3">
                            <div className="card h-100 border-info">
                                <div className="card-body text-center p-2 p-md-3">
                                    <div className="text-muted small" title={getTerritorioLabel()}>
                                        {getTerritorioLabel() || 'Tuo territorio'}
                                    </div>
                                    <div className="fs-3 fw-bold text-info">
                                        {stats.visibili?.sezioni?.toLocaleString() || 0}
                                    </div>
                                    <div className="text-muted small">sezioni visibili</div>
                                </div>
                            </div>
                        </div>

                        {/* Card Assegnate */}
                        <div className="col-6 col-lg-3">
                            <div className="card h-100 border-success">
                                <div className="card-body text-center p-2 p-md-3">
                                    <div className="text-muted small">RDL Assegnati</div>
                                    <div className="fs-3 fw-bold text-success">
                                        {stats.visibili?.assegnate?.toLocaleString() || 0}
                                    </div>
                                    <div className="text-muted small">
                                        {calcPercentuale(stats.visibili?.assegnate, stats.visibili?.sezioni)}%
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Card Non Assegnate */}
                        <div className="col-6 col-lg-3">
                            <div className="card h-100 border-warning">
                                <div className="card-body text-center p-2 p-md-3">
                                    <div className="text-muted small">Da assegnare</div>
                                    <div className="fs-3 fw-bold text-warning">
                                        {stats.visibili?.nonAssegnate?.toLocaleString() || 0}
                                    </div>
                                    <div className="text-muted small">
                                        {calcPercentuale(stats.visibili?.nonAssegnate, stats.visibili?.sezioni)}%
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Progress Bar Globale */}
                    <div className="card mb-4">
                        <div className="card-body">
                            <h6 className="card-title">Copertura RDL nel tuo territorio</h6>
                            <div className="progress" style={{ height: '24px' }}>
                                <div
                                    className="progress-bar bg-success"
                                    style={{ width: `${calcPercentuale(stats.visibili?.assegnate, stats.visibili?.sezioni)}%` }}
                                    role="progressbar"
                                    aria-valuenow={stats.visibili?.assegnate || 0}
                                    aria-valuemin="0"
                                    aria-valuemax={stats.visibili?.sezioni || 0}
                                >
                                    {calcPercentuale(stats.visibili?.assegnate, stats.visibili?.sezioni)}% assegnate
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Dettaglio per Comune */}
                    {stats.perComune && Object.keys(stats.perComune).length > 0 && (
                        <div className="card mb-4">
                            <div className="card-header">
                                <h5 className="mb-0">
                                    <i className="fas fa-city me-2"></i>
                                    Dettaglio per Comune
                                </h5>
                            </div>
                            <div className="list-group list-group-flush">
                                {Object.entries(stats.perComune)
                                    .sort((a, b) => b[1].totale - a[1].totale)
                                    .map(([comune, data]) => {
                                        // Build display name with municipi if limited visibility
                                        let displayName = comune;
                                        const municipi = Object.keys(stats.perMunicipio || {}).filter(
                                            m => stats.perMunicipio[m].visibili > 0
                                        );
                                        if (comune.toUpperCase() === 'ROMA' && municipi.length > 0 && municipi.length < 15) {
                                            const municipiRoman = municipi.map(m => `Mun. ${toRoman(+m)}`).join(', ');
                                            displayName = `${comune} - ${municipiRoman}`;
                                        }
                                        return (
                                        <div key={comune}>
                                            <button
                                                className="list-group-item list-group-item-action d-flex justify-content-between align-items-center"
                                                onClick={() => setExpandedComune(expandedComune === comune ? null : comune)}
                                                aria-expanded={expandedComune === comune}
                                            >
                                                <div>
                                                    <strong>{displayName}</strong>
                                                    <div className="small text-muted">
                                                        {data.totale} sezioni
                                                    </div>
                                                </div>
                                                <div className="d-flex align-items-center gap-2 gap-md-3">
                                                    <div className="text-end d-none d-sm-block">
                                                        <span className="badge bg-success me-1">
                                                            {data.assegnate}
                                                        </span>
                                                        <span className="badge bg-warning">
                                                            {data.totale - data.assegnate}
                                                        </span>
                                                    </div>
                                                    <div style={{ width: '60px' }} className="d-none d-sm-block">
                                                        <div className="progress" style={{ height: '8px' }}>
                                                            <div
                                                                className="progress-bar bg-success"
                                                                style={{ width: `${calcPercentuale(data.assegnate, data.totale)}%` }}
                                                            ></div>
                                                        </div>
                                                    </div>
                                                    <span className="badge bg-primary d-sm-none">
                                                        {calcPercentuale(data.assegnate, data.totale)}%
                                                    </span>
                                                    <i className={`fas fa-chevron-${expandedComune === comune ? 'up' : 'down'}`}></i>
                                                </div>
                                            </button>

                                            {/* Expanded: Municipio details for ROMA */}
                                            {expandedComune === comune && comune === 'ROMA' && stats.perMunicipio && (
                                                <div className="bg-light p-3">
                                                    <h6 className="text-muted mb-2">Dettaglio Municipi</h6>
                                                    <div className="row g-2">
                                                        {Object.entries(stats.perMunicipio)
                                                            .filter(([_, mdata]) => mdata.visibili > 0)
                                                            .sort((a, b) => +a[0] - +b[0])
                                                            .map(([municipio, mdata]) => (
                                                                <div key={municipio} className="col-6 col-md-4 col-lg-3">
                                                                    <div className="card">
                                                                        <div className="card-body p-2 text-center">
                                                                            <div className="fw-bold small">
                                                                                Mun. {toRoman(+municipio)}
                                                                            </div>
                                                                            <div className="small">
                                                                                <span className="text-success">{mdata.assegnate || 0}</span>
                                                                                {' / '}
                                                                                <span>{mdata.visibili || 0}</span>
                                                                            </div>
                                                                            <div className="progress mt-1" style={{ height: '4px' }}>
                                                                                <div
                                                                                    className="progress-bar bg-success"
                                                                                    style={{ width: `${calcPercentuale(mdata.assegnate, mdata.visibili)}%` }}
                                                                                ></div>
                                                                            </div>
                                                                        </div>
                                                                    </div>
                                                                </div>
                                                            ))}
                                                    </div>
                                                </div>
                                            )}

                                            {/* Expanded: Summary for non-ROMA comuni */}
                                            {expandedComune === comune && comune !== 'ROMA' && (
                                                <div className="bg-light p-3">
                                                    <div className="row">
                                                        <div className="col-6">
                                                            <div className="text-success">
                                                                <i className="fas fa-check-circle me-1"></i>
                                                                {data.assegnate} assegnate
                                                            </div>
                                                        </div>
                                                        <div className="col-6">
                                                            <div className="text-warning">
                                                                <i className="fas fa-exclamation-circle me-1"></i>
                                                                {data.totale - data.assegnate} da assegnare
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    );
                                    })}
                            </div>
                        </div>
                    )}

                    {/* Refresh Button */}
                    <div className="text-center">
                        <button
                            className="btn btn-outline-secondary"
                            onClick={loadStats}
                            disabled={loading}
                        >
                            <i className="fas fa-sync-alt me-2"></i>
                            Aggiorna dati
                        </button>
                    </div>
                </>
            )}

            {/* Aggiungi View */}
            {activeView === 'aggiungi' && (
                <>
                    {/* Aggiungi singola sezione */}
                    <div className="card mb-4">
                        <div className="card-header">
                            <h5 className="mb-0">
                                <i className="fas fa-plus-circle me-2"></i>
                                Aggiungi Sezione Singola
                            </h5>
                        </div>
                        <div className="card-body">
                            <form onSubmit={handleAddSection}>
                                <div className="row g-3">
                                    <div className="col-6 col-md-3">
                                        <label htmlFor="sezione" className="form-label">Numero Sezione *</label>
                                        <input
                                            type="number"
                                            className="form-control"
                                            id="sezione"
                                            name="sezione"
                                            value={formData.sezione}
                                            onChange={handleFormChange}
                                            min="1"
                                            required
                                            placeholder="1"
                                        />
                                    </div>
                                    <div className="col-6 col-md-3">
                                        <label htmlFor="comune" className="form-label">Comune *</label>
                                        <input
                                            type="text"
                                            className="form-control"
                                            id="comune"
                                            name="comune"
                                            value={formData.comune}
                                            onChange={handleFormChange}
                                            required
                                            placeholder="ROMA"
                                            style={{ textTransform: 'uppercase' }}
                                        />
                                    </div>
                                    <div className="col-6 col-md-3">
                                        <label htmlFor="municipio" className="form-label">Municipio</label>
                                        <input
                                            type="number"
                                            className="form-control"
                                            id="municipio"
                                            name="municipio"
                                            value={formData.municipio}
                                            onChange={handleFormChange}
                                            min="1"
                                            max="15"
                                            placeholder="1-15"
                                        />
                                        <div className="form-text small">Solo per Roma</div>
                                    </div>
                                    <div className="col-12 col-md-6">
                                        <label htmlFor="indirizzo" className="form-label">Indirizzo seggio</label>
                                        <input
                                            type="text"
                                            className="form-control"
                                            id="indirizzo"
                                            name="indirizzo"
                                            value={formData.indirizzo}
                                            onChange={handleFormChange}
                                            placeholder="Via Roma, 1"
                                        />
                                    </div>
                                    <div className="col-12 col-md-6 d-flex align-items-end">
                                        <button
                                            type="submit"
                                            className="btn btn-primary w-100"
                                            disabled={saving}
                                        >
                                            {saving ? (
                                                <>
                                                    <span className="spinner-border spinner-border-sm me-2"></span>
                                                    Salvataggio...
                                                </>
                                            ) : (
                                                <>
                                                    <i className="fas fa-save me-2"></i>
                                                    Aggiungi Sezione
                                                </>
                                            )}
                                        </button>
                                    </div>
                                </div>
                            </form>
                        </div>
                    </div>

                    {/* Aggiungi range di sezioni */}
                    <div className="card mb-4">
                        <div className="card-header">
                            <h5 className="mb-0">
                                <i className="fas fa-layer-group me-2"></i>
                                Aggiungi Range di Sezioni
                            </h5>
                        </div>
                        <div className="card-body">
                            <p className="text-muted small">
                                Per piccoli comuni con poche sezioni: inserisci il range (es. da 1 a 5)
                                e verranno create tutte le sezioni intermedie.
                            </p>
                            <form onSubmit={handleAddMultiple}>
                                <div className="row g-3">
                                    <div className="col-6 col-md-2">
                                        <label htmlFor="sezioneInizio" className="form-label">Da sezione *</label>
                                        <input
                                            type="number"
                                            className="form-control"
                                            id="sezioneInizio"
                                            name="sezioneInizio"
                                            value={formData.sezioneInizio || ''}
                                            onChange={handleFormChange}
                                            min="1"
                                            required
                                            placeholder="1"
                                        />
                                    </div>
                                    <div className="col-6 col-md-2">
                                        <label htmlFor="sezioneFine" className="form-label">A sezione *</label>
                                        <input
                                            type="number"
                                            className="form-control"
                                            id="sezioneFine"
                                            name="sezioneFine"
                                            value={formData.sezioneFine || ''}
                                            onChange={handleFormChange}
                                            min="1"
                                            required
                                            placeholder="10"
                                        />
                                    </div>
                                    <div className="col-12 col-md-3">
                                        <label htmlFor="comuneRange" className="form-label">Comune *</label>
                                        <input
                                            type="text"
                                            className="form-control"
                                            id="comuneRange"
                                            name="comune"
                                            value={formData.comune}
                                            onChange={handleFormChange}
                                            required
                                            placeholder="MENTANA"
                                            style={{ textTransform: 'uppercase' }}
                                        />
                                    </div>
                                    <div className="col-6 col-md-2">
                                        <label htmlFor="municipioRange" className="form-label">Municipio</label>
                                        <input
                                            type="number"
                                            className="form-control"
                                            id="municipioRange"
                                            name="municipio"
                                            value={formData.municipio}
                                            onChange={handleFormChange}
                                            min="1"
                                            max="15"
                                        />
                                    </div>
                                    <div className="col-12 col-md-3 d-flex align-items-end">
                                        <button
                                            type="submit"
                                            className="btn btn-success w-100"
                                            disabled={saving}
                                        >
                                            {saving ? (
                                                <>
                                                    <span className="spinner-border spinner-border-sm me-2"></span>
                                                    Creazione...
                                                </>
                                            ) : (
                                                <>
                                                    <i className="fas fa-plus me-2"></i>
                                                    Crea Sezioni
                                                </>
                                            )}
                                        </button>
                                    </div>
                                </div>
                            </form>
                        </div>
                    </div>

                    {/* Risultato salvataggio */}
                    {saveResult && (
                        <div className={`alert ${saveResult.success ? 'alert-success' : 'alert-danger'}`}>
                            <i className={`fas ${saveResult.success ? 'fa-check-circle' : 'fa-exclamation-circle'} me-2`}></i>
                            {saveResult.message}
                        </div>
                    )}
                </>
            )}

            {/* Upload View */}
            {activeView === 'carica' && (
                <>
                    <div className="card">
                        <div className="card-header bg-info text-white">
                            <i className="fas fa-file-import me-2"></i>
                            Importa Sezioni da CSV
                        </div>
                        <div className="card-body">
                            <p className="alert alert-secondary">
                                <i className="fas fa-info-circle me-2"></i>
                                L'import CSV è utile per le grandi città con molte sezioni.
                                Per piccoli comuni con poche sezioni, usa la tab "Aggiungi".
                            </p>

                            <p className="text-muted">
                                Il file CSV deve avere le seguenti colonne:
                            </p>
                            <ul className="text-muted">
                                <li><strong>SEZIONE</strong>: Numero della sezione</li>
                                <li><strong>COMUNE</strong>: Nome del comune (es. ROMA)</li>
                                <li><strong>MUNICIPIO</strong>: Numero del municipio (opzionale)</li>
                                <li><strong>INDIRIZZO</strong>: Indirizzo del seggio</li>
                            </ul>

                            <div className="mb-3">
                                <label htmlFor="csvFile" className="form-label">Seleziona file CSV</label>
                                <input
                                    type="file"
                                    className="form-control"
                                    id="csvFile"
                                    accept=".csv"
                                    onChange={handleFileChange}
                                    disabled={uploading}
                                    aria-describedby="csvHelp"
                                />
                                <div id="csvHelp" className="form-text">
                                    Formati supportati: .csv (separatore virgola)
                                </div>
                            </div>

                            {file && (
                                <div className="alert alert-info d-flex align-items-center">
                                    <i className="fas fa-file-csv me-2"></i>
                                    <div>
                                        <strong>{file.name}</strong>
                                        <span className="text-muted ms-2">({(file.size / 1024).toFixed(1)} KB)</span>
                                    </div>
                                </div>
                            )}

                            <button
                                className="btn btn-primary"
                                onClick={handleUpload}
                                disabled={!file || uploading}
                            >
                                {uploading ? (
                                    <>
                                        <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                                        Caricamento in corso...
                                    </>
                                ) : (
                                    <>
                                        <i className="fas fa-cloud-upload-alt me-2"></i>
                                        Importa Sezioni
                                    </>
                                )}
                            </button>
                        </div>
                    </div>

                    {result && (
                        <div className={`alert ${result.errors?.length ? 'alert-warning' : 'alert-success'} mt-3`}>
                            <h5>
                                <i className={`fas ${result.errors?.length ? 'fa-exclamation-triangle' : 'fa-check-circle'} me-2`}></i>
                                Importazione completata
                            </h5>
                            <ul className="mb-0">
                                <li>Sezioni create: <strong>{result.created}</strong></li>
                                <li>Sezioni aggiornate: <strong>{result.updated}</strong></li>
                                <li>Totale elaborato: <strong>{result.total}</strong></li>
                            </ul>
                            {result.errors?.length > 0 && (
                                <div className="mt-2">
                                    <strong>Errori:</strong>
                                    <ul className="mb-0">
                                        {result.errors.map((err, i) => (
                                            <li key={i} className="text-danger">{err}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}

                    <div className="card mt-3">
                        <div className="card-header">
                            <i className="fas fa-code me-2"></i>
                            Esempio formato CSV
                        </div>
                        <div className="card-body">
                            <pre className="mb-0 bg-light p-3 rounded" style={{ fontSize: '0.85em' }}>
{`SEZIONE,COMUNE,MUNICIPIO,INDIRIZZO
1,ROMA,3,"VIA DI SETTEBAGNI, 231"
2,ROMA,1,"VIA DANIELE MANIN, 72"
3,ROMA,1,"VIA DANIELE MANIN, 72"
1,MENTANA,,"VIA ROMA, 1"
2,MENTANA,,"VIA ROMA, 1"
...`}
                            </pre>
                        </div>
                    </div>
                </>
            )}
        </>
    );
}

export default GestioneSezioni;
