import React, { useState, useEffect } from 'react';
import ComuneAutocomplete from './ComuneAutocomplete';

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
        municipio: '',
        indirizzo: '',
        // Range fields
        sezioneInizio: '',
        sezioneFine: ''
    });
    const [selectedComune, setSelectedComune] = useState(null);
    const [saving, setSaving] = useState(false);
    const [saveResult, setSaveResult] = useState(null);

    // Expanded sections for drill-down
    const [expandedComune, setExpandedComune] = useState(null);
    const [expandedComuneId, setExpandedComuneId] = useState(null);
    const [comuneSezioni, setComuneSezioni] = useState([]);
    const [loadingSezioni, setLoadingSezioni] = useState(false);
    const [loadingMore, setLoadingMore] = useState(false);
    const [sezioniPage, setSezioniPage] = useState(1);
    const [sezioniHasMore, setSezioniHasMore] = useState(false);
    const [sezioniTotal, setSezioniTotal] = useState(0);
    const [editingSezione, setEditingSezione] = useState(null);
    const [editForm, setEditForm] = useState({ indirizzo: '', denominazione: '' });
    const [savingEdit, setSavingEdit] = useState(false);

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
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleComuneChange = (comune) => {
        setSelectedComune(comune);
        // Reset municipio when comune changes
        setFormData(prev => ({ ...prev, municipio: '' }));
    };

    const handleAddSection = async (e) => {
        e.preventDefault();

        if (!formData.sezione || !selectedComune) {
            setError('Sezione e Comune sono obbligatori');
            return;
        }

        // Municipio required if comune has municipi
        if (selectedComune.municipi?.length > 0 && !formData.municipio) {
            setError('Seleziona un municipio');
            return;
        }

        setSaving(true);
        setSaveResult(null);
        setError(null);

        try {
            // Per ora usiamo l'upload con un singolo record
            // In futuro si può creare un endpoint dedicato
            const csvContent = `SEZIONE,COMUNE,MUNICIPIO,INDIRIZZO\n${formData.sezione},${selectedComune.nome},${formData.municipio || ''},"${formData.indirizzo || ''}"`;
            const blob = new Blob([csvContent], { type: 'text/csv' });
            const file = new File([blob], 'sezione.csv', { type: 'text/csv' });

            const res = await client.sections.upload(file);
            if (res.error) {
                setError(res.error);
            } else {
                setSaveResult({
                    success: true,
                    message: `Sezione ${formData.sezione} di ${selectedComune.nome} aggiunta con successo`
                });
                // Reset form
                setFormData({
                    sezione: '',
                    municipio: '',
                    indirizzo: '',
                    sezioneInizio: '',
                    sezioneFine: ''
                });
                setSelectedComune(null);
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

        if (!startSection || !endSection || !selectedComune) {
            setError('Sezione inizio, fine e Comune sono obbligatori');
            return;
        }

        // Municipio required if comune has municipi
        if (selectedComune.municipi?.length > 0 && !formData.municipio) {
            setError('Seleziona un municipio');
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
                csvContent += `${i},${selectedComune.nome},${formData.municipio || ''},"${formData.indirizzo || ''}"\n`;
            }

            const blob = new Blob([csvContent], { type: 'text/csv' });
            const file = new File([blob], 'sezioni.csv', { type: 'text/csv' });

            const res = await client.sections.upload(file);
            if (res.error) {
                setError(res.error);
            } else {
                setSaveResult({
                    success: true,
                    message: `Aggiunte ${endSection - startSection + 1} sezioni (${startSection}-${endSection}) per ${selectedComune.nome}`
                });
                // Reset form
                setFormData({
                    sezione: '',
                    municipio: '',
                    indirizzo: '',
                    sezioneInizio: '',
                    sezioneFine: ''
                });
                setSelectedComune(null);
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

    // Load sezioni for a comune when expanded (first page)
    const loadComuneSezioni = async (comuneId) => {
        setLoadingSezioni(true);
        setComuneSezioni([]);
        setSezioniPage(1);
        setSezioniHasMore(false);
        setSezioniTotal(0);
        try {
            const data = await client.sections.list(comuneId, 1, 200);
            if (data.error) {
                setError(data.error);
            } else {
                const sezioni = data.results || [];
                setComuneSezioni(sezioni);
                setSezioniHasMore(data.has_next || false);
                setSezioniTotal(data.count || sezioni.length);
            }
        } catch (err) {
            setError(`Errore nel caricamento sezioni: ${err.message}`);
        } finally {
            setLoadingSezioni(false);
        }
    };

    // Load more sezioni (next pages)
    const loadMoreSezioni = async () => {
        if (loadingMore || !sezioniHasMore || !expandedComuneId) return;

        setLoadingMore(true);
        const nextPage = sezioniPage + 1;
        try {
            const data = await client.sections.list(expandedComuneId, nextPage, 50);
            if (data.error) {
                setError(data.error);
            } else {
                const newSezioni = data.results || [];
                setComuneSezioni(prev => [...prev, ...newSezioni]);
                setSezioniPage(nextPage);
                setSezioniHasMore(data.has_next || false);
            }
        } catch (err) {
            setError(`Errore nel caricamento sezioni: ${err.message}`);
        } finally {
            setLoadingMore(false);
        }
    };

    // Handle scroll in sezioni table
    const handleSezioniScroll = (e) => {
        const { scrollTop, scrollHeight, clientHeight } = e.target;
        // Load more when scrolled near bottom (within 100px)
        if (scrollHeight - scrollTop - clientHeight < 100) {
            loadMoreSezioni();
        }
    };

    // Handle comune expansion
    const handleExpandComune = (comune, comuneId) => {
        if (expandedComune === comune) {
            setExpandedComune(null);
            setExpandedComuneId(null);
            setComuneSezioni([]);
            setEditingSezione(null);
        } else {
            setExpandedComune(comune);
            setExpandedComuneId(comuneId);
            setEditingSezione(null);
            if (comuneId) {
                loadComuneSezioni(comuneId);
            }
        }
    };

    // Start editing a sezione
    const handleEditSezione = (sezione) => {
        setEditingSezione(sezione.id);
        setEditForm({
            indirizzo: sezione.indirizzo || '',
            denominazione: sezione.denominazione || ''
        });
    };

    // Cancel editing
    const handleCancelEdit = () => {
        setEditingSezione(null);
        setEditForm({ indirizzo: '', denominazione: '' });
    };

    // Save sezione edit
    const handleSaveEdit = async (sezioneId) => {
        setSavingEdit(true);
        try {
            const result = await client.sections.update(sezioneId, editForm);
            if (result.error) {
                setError(result.error);
            } else {
                // Update local state
                setComuneSezioni(prev => prev.map(s =>
                    s.id === sezioneId ? { ...s, ...editForm } : s
                ));
                setEditingSezione(null);
                setEditForm({ indirizzo: '', denominazione: '' });
            }
        } catch (err) {
            setError(`Errore nel salvataggio: ${err.message}`);
        } finally {
            setSavingEdit(false);
        }
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
            {/* Page Header */}
            <div className="page-header rdl">
                <div className="page-header-title">
                    <i className="fas fa-map-marker-alt"></i>
                    Gestione Sezioni
                </div>
                <div className="page-header-subtitle">
                    Panoramica e arricchimento dati sezioni elettorali
                    {getTerritorioLabel() && (
                        <span className="page-header-badge">{getTerritorioLabel()}</span>
                    )}
                </div>
            </div>

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
                    {stats.comuni && stats.comuni.length > 0 && (
                        <div className="card mb-4">
                            <div className="card-header">
                                <h5 className="mb-0">
                                    <i className="fas fa-city me-2"></i>
                                    Dettaglio per Comune
                                </h5>
                            </div>
                            <div className="list-group list-group-flush">
                                {stats.comuni
                                    .sort((a, b) => b.totale - a.totale)
                                    .map((comuneData) => {
                                        const comuneNome = comuneData.nome;
                                        const comuneId = comuneData.id;
                                        // Build display name with municipi if limited visibility
                                        let displayName = comuneNome;
                                        if (comuneData.municipi && comuneData.municipi.length > 0) {
                                            const municipiRoman = comuneData.municipi.map(m => `Mun. ${toRoman(m.numero)}`).join(', ');
                                            displayName = `${comuneNome} - ${municipiRoman}`;
                                        }
                                        const isExpanded = expandedComune === comuneNome;
                                        return (
                                        <div key={comuneId}>
                                            <button
                                                className="list-group-item list-group-item-action d-flex justify-content-between align-items-center"
                                                onClick={() => handleExpandComune(comuneNome, comuneId)}
                                                aria-expanded={isExpanded}
                                            >
                                                <div>
                                                    <strong>{displayName}</strong>
                                                    <div className="small text-muted">
                                                        {comuneData.totale} sezioni
                                                    </div>
                                                </div>
                                                <div className="d-flex align-items-center gap-2 gap-md-3">
                                                    <div className="text-end d-none d-sm-block">
                                                        <span className="badge bg-success me-1">
                                                            {comuneData.assegnate}
                                                        </span>
                                                        <span className="badge bg-warning">
                                                            {comuneData.totale - comuneData.assegnate}
                                                        </span>
                                                    </div>
                                                    <div style={{ width: '60px' }} className="d-none d-sm-block">
                                                        <div className="progress" style={{ height: '8px' }}>
                                                            <div
                                                                className="progress-bar bg-success"
                                                                style={{ width: `${calcPercentuale(comuneData.assegnate, comuneData.totale)}%` }}
                                                            ></div>
                                                        </div>
                                                    </div>
                                                    <span className="badge bg-primary d-sm-none">
                                                        {calcPercentuale(comuneData.assegnate, comuneData.totale)}%
                                                    </span>
                                                    <i className={`fas fa-chevron-${isExpanded ? 'up' : 'down'}`}></i>
                                                </div>
                                            </button>

                                            {/* Expanded: Sezioni list with edit capability */}
                                            {isExpanded && (
                                                <div className="bg-light p-3">
                                                    {/* Municipio summary for cities with municipi */}
                                                    {comuneData.municipi && comuneData.municipi.length > 0 && (
                                                        <>
                                                            <h6 className="text-muted mb-2">Riepilogo Municipi</h6>
                                                            <div className="row g-2 mb-3">
                                                                {comuneData.municipi.map((mun) => (
                                                                    <div key={mun.numero} className="col-6 col-md-4 col-lg-3">
                                                                        <div className="card">
                                                                            <div className="card-body p-2 text-center">
                                                                                <div className="fw-bold small">
                                                                                    Mun. {toRoman(mun.numero)}
                                                                                </div>
                                                                                <div className="small">
                                                                                    <span className="text-success">{mun.assegnate || 0}</span>
                                                                                    {' / '}
                                                                                    <span>{mun.visibili || 0}</span>
                                                                                </div>
                                                                            </div>
                                                                        </div>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        </>
                                                    )}

                                                    {/* Sezioni list */}
                                                    <div className="d-flex justify-content-between align-items-center mb-2">
                                                        <h6 className="text-muted mb-0">
                                                            <i className="fas fa-list me-1"></i>
                                                            Elenco Sezioni
                                                        </h6>
                                                        {sezioniTotal > 0 && (
                                                            <small className="text-muted">
                                                                {comuneSezioni.length} di {sezioniTotal} caricate
                                                            </small>
                                                        )}
                                                    </div>
                                                    {loadingSezioni ? (
                                                        <div className="text-center py-3">
                                                            <div className="spinner-border spinner-border-sm text-primary me-2"></div>
                                                            Caricamento sezioni...
                                                        </div>
                                                    ) : comuneSezioni.length === 0 ? (
                                                        <div className="text-muted text-center py-2">
                                                            Nessuna sezione trovata
                                                        </div>
                                                    ) : (
                                                        <div
                                                            className="table-responsive"
                                                            style={{ maxHeight: '400px', overflowY: 'auto' }}
                                                            onScroll={handleSezioniScroll}
                                                        >
                                                            <table className="table table-sm table-hover mb-0">
                                                                <thead className="table-light sticky-top">
                                                                    <tr>
                                                                        <th style={{ width: '60px' }}>Sez.</th>
                                                                        {comuneData.municipi?.length > 0 && (
                                                                            <th style={{ width: '60px' }}>Mun.</th>
                                                                        )}
                                                                        <th>Indirizzo</th>
                                                                        <th>Denominazione</th>
                                                                        <th style={{ width: '80px' }}>Azioni</th>
                                                                    </tr>
                                                                </thead>
                                                                <tbody>
                                                                    {comuneSezioni.map((sez) => (
                                                                        <tr key={sez.id}>
                                                                            <td className="fw-bold">{sez.numero}</td>
                                                                            {comuneData.municipi?.length > 0 && (
                                                                                <td>
                                                                                    {sez.municipio ? toRoman(sez.municipio.numero || sez.municipio) : '-'}
                                                                                </td>
                                                                            )}
                                                                            {editingSezione === sez.id ? (
                                                                                <>
                                                                                    <td>
                                                                                        <input
                                                                                            type="text"
                                                                                            className="form-control form-control-sm"
                                                                                            value={editForm.indirizzo}
                                                                                            onChange={(e) => setEditForm(prev => ({ ...prev, indirizzo: e.target.value }))}
                                                                                            placeholder="Indirizzo..."
                                                                                        />
                                                                                    </td>
                                                                                    <td>
                                                                                        <input
                                                                                            type="text"
                                                                                            className="form-control form-control-sm"
                                                                                            value={editForm.denominazione}
                                                                                            onChange={(e) => setEditForm(prev => ({ ...prev, denominazione: e.target.value }))}
                                                                                            placeholder="Denominazione..."
                                                                                        />
                                                                                    </td>
                                                                                    <td>
                                                                                        <div className="btn-group btn-group-sm">
                                                                                            <button
                                                                                                className="btn btn-success"
                                                                                                onClick={() => handleSaveEdit(sez.id)}
                                                                                                disabled={savingEdit}
                                                                                                title="Salva"
                                                                                            >
                                                                                                {savingEdit ? (
                                                                                                    <span className="spinner-border spinner-border-sm"></span>
                                                                                                ) : (
                                                                                                    <i className="fas fa-check"></i>
                                                                                                )}
                                                                                            </button>
                                                                                            <button
                                                                                                className="btn btn-secondary"
                                                                                                onClick={handleCancelEdit}
                                                                                                disabled={savingEdit}
                                                                                                title="Annulla"
                                                                                            >
                                                                                                <i className="fas fa-times"></i>
                                                                                            </button>
                                                                                        </div>
                                                                                    </td>
                                                                                </>
                                                                            ) : (
                                                                                <>
                                                                                    <td className={!sez.indirizzo ? 'text-muted' : ''}>
                                                                                        {sez.indirizzo || '-'}
                                                                                    </td>
                                                                                    <td className={!sez.denominazione ? 'text-muted' : ''}>
                                                                                        {sez.denominazione || '-'}
                                                                                    </td>
                                                                                    <td>
                                                                                        <button
                                                                                            className="btn btn-outline-primary btn-sm"
                                                                                            onClick={() => handleEditSezione(sez)}
                                                                                            title="Modifica"
                                                                                        >
                                                                                            <i className="fas fa-edit"></i>
                                                                                        </button>
                                                                                    </td>
                                                                                </>
                                                                            )}
                                                                        </tr>
                                                                    ))}
                                                                </tbody>
                                                            </table>
                                                            {/* Loading more indicator */}
                                                            {loadingMore && (
                                                                <div className="text-center py-2 bg-light">
                                                                    <div className="spinner-border spinner-border-sm text-primary me-2"></div>
                                                                    <small>Caricamento altre sezioni...</small>
                                                                </div>
                                                            )}
                                                            {sezioniHasMore && !loadingMore && (
                                                                <div className="text-center py-2 bg-light">
                                                                    <small className="text-muted">
                                                                        Scorri per caricare altre sezioni
                                                                    </small>
                                                                </div>
                                                            )}
                                                        </div>
                                                    )}
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

            {/* Upload View */}
            {activeView === 'carica' && (
                <>
                    {/* Territory Scope Alert */}
                    <div className="alert alert-primary mb-3">
                        <div className="d-flex align-items-center">
                            <i className="fas fa-map-marked-alt fa-2x me-3"></i>
                            <div>
                                <strong>Il tuo ambito territoriale:</strong>
                                <div className="fs-5 fw-bold">{getTerritorioLabel() || 'Tutto il territorio'}</div>
                            </div>
                        </div>
                    </div>

                    <div className="card">
                        <div className="card-header bg-info text-white">
                            <i className="fas fa-file-import me-2"></i>
                            Aggiorna Denominazioni e Indirizzi
                        </div>
                        <div className="card-body">
                            <p className="alert alert-warning">
                                <i className="fas fa-exclamation-triangle me-2"></i>
                                <strong>Attenzione:</strong> L'import elabora solo le sezioni <strong>già presenti a sistema</strong> e
                                <strong> all'interno del tuo territorio</strong> ({getTerritorioLabel() || 'intero territorio'}).
                                <br/>
                                Le righe con sezioni fuori dal tuo ambito verranno <strong>scartate automaticamente</strong>.
                            </p>

                            <p className="alert alert-success mb-3">
                                <i className="fas fa-lightbulb me-2"></i>
                                <strong>A cosa serve:</strong> Questo strumento è pensato per arricchire le sezioni esistenti
                                aggiungendo o modificando <strong>denominazioni</strong> (es. "Scuola Mazzini") e
                                <strong> indirizzi</strong> (es. "Via Roma, 1").
                                <br/>
                                I campi vuoti nel CSV non sovrascriveranno i dati esistenti.
                            </p>

                            <p className="text-muted">
                                Il file CSV deve avere le seguenti colonne (solo SEZIONE e COMUNE sono obbligatorie):
                            </p>
                            <ul className="text-muted">
                                <li><strong>SEZIONE</strong> *: Numero della sezione</li>
                                <li><strong>COMUNE</strong> *: Nome del comune (es. ROMA)</li>
                                <li><strong>MUNICIPIO</strong>: Numero del municipio (opzionale)</li>
                                <li><strong>INDIRIZZO</strong>: Indirizzo del seggio (opzionale)</li>
                                <li><strong>DENOMINAZIONE</strong>: Nome del seggio, es. "Scuola Mazzini" (opzionale)</li>
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
                                {result.skipped > 0 && (
                                    <li>Sezioni invariate/fuori territorio: <strong>{result.skipped}</strong></li>
                                )}
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
{`SEZIONE,COMUNE,MUNICIPIO,INDIRIZZO,DENOMINAZIONE
1,ROMA,3,"VIA DI SETTEBAGNI, 231","Scuola Elementare Mazzini"
2,ROMA,1,"VIA DANIELE MANIN, 72","IC Via Manin"
3,ROMA,1,"VIA DANIELE MANIN, 72","IC Via Manin"
1,MENTANA,,"VIA ROMA, 1","Scuola Media Garibaldi"
2,MENTANA,,"VIA ROMA, 1","Scuola Media Garibaldi"
...`}
                            </pre>
                            <p className="text-muted small mt-2 mb-0">
                                <i className="fas fa-lightbulb me-1"></i>
                                <strong>Tip:</strong> Puoi importare solo le colonne che ti servono.
                                Ad esempio, per aggiungere solo le denominazioni:
                            </p>
                            <pre className="mb-0 bg-light p-3 rounded mt-2" style={{ fontSize: '0.85em' }}>
{`SEZIONE,COMUNE,DENOMINAZIONE
1,ROMA,"Scuola Elementare Mazzini"
2,ROMA,"IC Via Manin"
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
