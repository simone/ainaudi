import React, { useState, useEffect, useRef } from 'react';
import ConfirmModal from './ConfirmModal';

function GestioneRdl({ client, setError }) {
    const [registrations, setRegistrations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [statusFilter, setStatusFilter] = useState('');
    const [searchFilter, setSearchFilter] = useState('');
    const [editingId, setEditingId] = useState(null);
    const [editData, setEditData] = useState({});
    const [showImport, setShowImport] = useState(false);
    const [importResult, setImportResult] = useState(null);
    const [expandedId, setExpandedId] = useState(null);
    const fileInputRef = useRef(null);

    // Territory filter states
    const [regioni, setRegioni] = useState([]);
    const [province, setProvince] = useState([]);
    const [comuni, setComuni] = useState([]);
    const [municipi, setMunicipi] = useState([]);
    const [regioneFilter, setRegioneFilter] = useState('');
    const [provinciaFilter, setProvinciaFilter] = useState('');
    const [comuneFilter, setComuneFilter] = useState('');
    const [municipioFilter, setMunicipioFilter] = useState('');
    const [showTerritoryFilters, setShowTerritoryFilters] = useState(false);

    // Modal states
    const [modal, setModal] = useState({
        show: false,
        type: null,
        targetId: null,
        targetName: ''
    });

    // Load regioni on mount
    useEffect(() => {
        loadRegioni();
    }, []);

    // Load province when regione changes
    useEffect(() => {
        if (regioneFilter) {
            loadProvince(regioneFilter);
        } else {
            setProvince([]);
            setProvinciaFilter('');
        }
    }, [regioneFilter]);

    // Load comuni when provincia changes
    useEffect(() => {
        if (provinciaFilter) {
            loadComuni(provinciaFilter);
        } else {
            setComuni([]);
            setComuneFilter('');
        }
    }, [provinciaFilter]);

    // Load municipi when comune changes
    useEffect(() => {
        if (comuneFilter) {
            loadMunicipi(comuneFilter);
        } else {
            setMunicipi([]);
            setMunicipioFilter('');
        }
    }, [comuneFilter]);

    // Reload registrations when filters change
    useEffect(() => {
        loadRegistrations();
    }, [statusFilter, regioneFilter, provinciaFilter, comuneFilter, municipioFilter]);

    const loadRegioni = async () => {
        const result = await client.territorio.regioni();
        if (!result.error && Array.isArray(result)) {
            setRegioni(result);
        }
    };

    const loadProvince = async (regioneId) => {
        const result = await client.territorio.province(regioneId);
        if (!result.error && Array.isArray(result)) {
            setProvince(result);
        }
    };

    const loadComuni = async (provinciaId) => {
        const result = await client.territorio.comuni(provinciaId);
        if (!result.error && Array.isArray(result)) {
            setComuni(result);
        }
    };

    const loadMunicipi = async (comuneId) => {
        const result = await client.territorio.municipi(comuneId);
        if (!result.error && result.municipi) {
            setMunicipi(result.municipi);
        } else {
            setMunicipi([]);
        }
    };

    const loadRegistrations = async () => {
        setLoading(true);
        const filters = {};
        if (statusFilter) filters.status = statusFilter;
        if (regioneFilter) filters.regione = regioneFilter;
        if (provinciaFilter) filters.provincia = provinciaFilter;
        if (comuneFilter) filters.comune = comuneFilter;
        if (municipioFilter) filters.municipio = municipioFilter;

        const result = await client.rdlRegistrations.list(filters);
        if (result.error) {
            setError(result.error);
        } else {
            setRegistrations(result.registrations || []);
        }
        setLoading(false);
    };

    const clearTerritoryFilters = () => {
        setRegioneFilter('');
        setProvinciaFilter('');
        setComuneFilter('');
        setMunicipioFilter('');
    };

    const openModal = (type, reg) => {
        setModal({
            show: true,
            type,
            targetId: reg.id,
            targetName: `${reg.cognome} ${reg.nome}`
        });
    };

    const closeModal = () => {
        setModal({ show: false, type: null, targetId: null, targetName: '' });
    };

    const handleModalConfirm = async (inputValue) => {
        const { type, targetId } = modal;
        closeModal();

        let result;
        switch (type) {
            case 'approve':
                result = await client.rdlRegistrations.approve(targetId);
                break;
            case 'reject':
                result = await client.rdlRegistrations.reject(targetId, inputValue || '');
                break;
            case 'delete':
                result = await client.rdlRegistrations.delete(targetId);
                break;
            default:
                return;
        }

        if (result.error) {
            setError(result.error);
        } else {
            loadRegistrations();
        }
    };

    const handleEdit = (reg) => {
        setEditingId(reg.id);
        setEditData({
            email: reg.email,
            nome: reg.nome,
            cognome: reg.cognome,
            telefono: reg.telefono || '',
            comune_nascita: reg.comune_nascita || '',
            data_nascita: reg.data_nascita || '',
            comune_residenza: reg.comune_residenza || '',
            indirizzo_residenza: reg.indirizzo_residenza || '',
            seggio_preferenza: reg.seggio_preferenza || '',
            municipio: reg.municipio ? parseInt(reg.municipio.replace('Municipio ', '')) : '',
            notes: reg.notes || ''
        });
    };

    const handleSaveEdit = async () => {
        const result = await client.rdlRegistrations.update(editingId, {
            ...editData,
            municipio: editData.municipio || null
        });

        if (result.error) {
            setError(result.error);
        } else {
            setEditingId(null);
            loadRegistrations();
        }
    };

    const handleCancelEdit = () => {
        setEditingId(null);
        setEditData({});
    };

    const handleImport = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        setImportResult(null);
        const result = await client.rdlRegistrations.import(file);

        if (result.error) {
            setError(result.error);
        } else {
            setImportResult(result);
            loadRegistrations();
        }

        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    const toggleExpand = (id) => {
        setExpandedId(expandedId === id ? null : id);
    };

    const filteredRegistrations = registrations.filter(reg => {
        if (!searchFilter) return true;
        const search = searchFilter.toLowerCase();
        return (
            reg.email.toLowerCase().includes(search) ||
            reg.nome.toLowerCase().includes(search) ||
            reg.cognome.toLowerCase().includes(search) ||
            reg.comune.toLowerCase().includes(search) ||
            (reg.telefono && reg.telefono.includes(search))
        );
    });

    const getStatusBadge = (status) => {
        const styles = {
            PENDING: { bg: '#ffc107', color: '#000', label: 'In attesa' },
            APPROVED: { bg: '#198754', color: '#fff', label: 'Approvato' },
            REJECTED: { bg: '#dc3545', color: '#fff', label: 'Rifiutato' }
        };
        const s = styles[status] || { bg: '#6c757d', color: '#fff', label: status };
        return (
            <span style={{
                display: 'inline-block',
                padding: '2px 8px',
                borderRadius: '4px',
                fontSize: '0.75rem',
                fontWeight: 500,
                backgroundColor: s.bg,
                color: s.color
            }}>
                {s.label}
            </span>
        );
    };

    const formatDate = (dateStr) => {
        if (!dateStr) return '';
        return new Date(dateStr).toLocaleDateString('it-IT');
    };

    const getModalConfig = () => {
        switch (modal.type) {
            case 'approve':
                return {
                    title: 'Conferma Approvazione',
                    confirmText: 'Approva',
                    confirmVariant: 'success',
                    showInput: false,
                    children: (
                        <div>
                            <p>Stai per approvare <strong>{modal.targetName}</strong> come RDL.</p>
                            <div style={{
                                background: '#e7f3ff',
                                border: '1px solid #b6d4fe',
                                borderRadius: '6px',
                                padding: '12px',
                                marginBottom: '12px',
                                fontSize: '0.9rem'
                            }}>
                                <strong>Prima di approvare, verifica di aver:</strong>
                                <ul style={{ margin: '8px 0 0', paddingLeft: '20px' }}>
                                    <li>Controllato che i dati anagrafici siano corretti</li>
                                    <li>Verificato il numero di telefono (chiamalo/messaggialo)</li>
                                    <li>Verificato che l'email sia valida e raggiungibile</li>
                                    <li>Confermato la sua disponibilità per il giorno delle elezioni</li>
                                    <li>Valutato le sue motivazioni e affidabilità</li>
                                </ul>
                            </div>
                            <p style={{ fontSize: '0.85rem', color: '#6c757d', marginBottom: 0 }}>
                                Una volta approvato, l'RDL potrà accedere all'app e ricevere le credenziali.
                            </p>
                        </div>
                    )
                };
            case 'reject':
                return {
                    title: 'Rifiuta Registrazione',
                    message: `Stai per rifiutare la registrazione di ${modal.targetName}.`,
                    confirmText: 'Rifiuta',
                    confirmVariant: 'danger',
                    showInput: true,
                    inputLabel: 'Motivo del rifiuto (opzionale):',
                    inputPlaceholder: 'Es: Dati incompleti, non idoneo...'
                };
            case 'delete':
                return {
                    title: 'Elimina Registrazione',
                    message: `Sei sicuro di voler eliminare definitivamente la registrazione di ${modal.targetName}?`,
                    confirmText: 'Elimina',
                    confirmVariant: 'danger',
                    showInput: false
                };
            default:
                return {};
        }
    };

    if (loading && registrations.length === 0) {
        return (
            <div className="loading-container" role="status" aria-live="polite">
                <div className="spinner-border text-primary">
                    <span className="visually-hidden">Caricamento in corso...</span>
                </div>
                <p className="loading-text">Caricamento registrazioni...</p>
            </div>
        );
    }

    const modalConfig = getModalConfig();
    const pendingCount = registrations.filter(r => r.status === 'PENDING').length;

    return (
        <>
            <ConfirmModal
                show={modal.show}
                onConfirm={handleModalConfirm}
                onCancel={closeModal}
                {...modalConfig}
            />

            {/* Page Header */}
            <div className="page-header rdl">
                <div className="page-header-title">
                    <i className="fas fa-users"></i>
                    Gestione RDL
                </div>
                <div className="page-header-subtitle">
                    Approva e gestisci le registrazioni dei Rappresentanti di Lista
                </div>
            </div>

            {/* Filtri compatti */}
            <div style={{
                background: 'white',
                borderRadius: '8px',
                padding: '12px',
                marginBottom: '12px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
            }}>
                <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                    <select
                        className="form-select form-select-sm"
                        value={statusFilter}
                        onChange={(e) => setStatusFilter(e.target.value)}
                        style={{ flex: '0 0 120px' }}
                    >
                        <option value="">Tutti</option>
                        <option value="PENDING">In attesa</option>
                        <option value="APPROVED">Approvati</option>
                        <option value="REJECTED">Rifiutati</option>
                    </select>
                    <input
                        type="search"
                        className="form-control form-control-sm"
                        placeholder="Cerca..."
                        value={searchFilter}
                        onChange={(e) => setSearchFilter(e.target.value)}
                    />
                </div>

                {/* Toggle filtri territorio */}
                <div style={{ marginBottom: '8px' }}>
                    <button
                        className={`btn btn-sm ${showTerritoryFilters ? 'btn-primary' : 'btn-outline-primary'}`}
                        onClick={() => setShowTerritoryFilters(!showTerritoryFilters)}
                        style={{ width: '100%' }}
                    >
                        <i className="fas fa-map-marker-alt me-1"></i>
                        Filtri Territorio {(regioneFilter || provinciaFilter || comuneFilter || municipioFilter) && '●'}
                    </button>
                </div>

                {/* Filtri territorio a cascata */}
                {showTerritoryFilters && (
                    <div style={{
                        background: '#f8f9fa',
                        borderRadius: '6px',
                        padding: '10px',
                        marginBottom: '8px'
                    }}>
                        <div style={{ display: 'grid', gap: '8px', gridTemplateColumns: '1fr 1fr' }}>
                            <select
                                className="form-select form-select-sm"
                                value={regioneFilter}
                                onChange={(e) => setRegioneFilter(e.target.value)}
                            >
                                <option value="">-- Regione --</option>
                                {regioni.map(r => (
                                    <option key={r.id} value={r.id}>{r.nome}</option>
                                ))}
                            </select>
                            <select
                                className="form-select form-select-sm"
                                value={provinciaFilter}
                                onChange={(e) => setProvinciaFilter(e.target.value)}
                                disabled={!regioneFilter}
                            >
                                <option value="">-- Provincia --</option>
                                {province.map(p => (
                                    <option key={p.id} value={p.id}>{p.nome} ({p.sigla})</option>
                                ))}
                            </select>
                            <select
                                className="form-select form-select-sm"
                                value={comuneFilter}
                                onChange={(e) => setComuneFilter(e.target.value)}
                                disabled={!provinciaFilter}
                            >
                                <option value="">-- Comune --</option>
                                {comuni.map(c => (
                                    <option key={c.id} value={c.id}>{c.nome}</option>
                                ))}
                            </select>
                            <select
                                className="form-select form-select-sm"
                                value={municipioFilter}
                                onChange={(e) => setMunicipioFilter(e.target.value)}
                                disabled={!comuneFilter || municipi.length === 0}
                            >
                                <option value="">-- Municipio --</option>
                                {municipi.map(m => (
                                    <option key={m.id} value={m.id}>Municipio {m.numero}</option>
                                ))}
                            </select>
                        </div>
                        {(regioneFilter || provinciaFilter || comuneFilter || municipioFilter) && (
                            <button
                                className="btn btn-sm btn-outline-secondary mt-2"
                                onClick={clearTerritoryFilters}
                                style={{ width: '100%' }}
                            >
                                Cancella filtri territorio
                            </button>
                        )}
                    </div>
                )}

                <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                        className="btn btn-sm btn-outline-primary"
                        onClick={() => setShowImport(!showImport)}
                        style={{ flex: 1 }}
                    >
                        {showImport ? 'Chiudi' : 'Import CSV'}
                    </button>
                    <button
                        className="btn btn-sm btn-outline-secondary"
                        onClick={loadRegistrations}
                    >
                        Aggiorna
                    </button>
                </div>
            </div>

            {/* Import Section */}
            {showImport && (
                <div style={{
                    background: '#e3f2fd',
                    borderRadius: '8px',
                    padding: '12px',
                    marginBottom: '12px',
                    fontSize: '0.85rem'
                }}>
                    <div style={{ fontWeight: 600, marginBottom: '8px' }}>Import CSV</div>
                    <div style={{ marginBottom: '8px', color: '#666' }}>
                        <strong>Colonne:</strong> EMAIL, NOME, COGNOME, TELEFONO, COMUNE_NASCITA, DATA_NASCITA, COMUNE_RESIDENZA, INDIRIZZO_RESIDENZA, COMUNE_SEGGIO
                    </div>
                    <input
                        ref={fileInputRef}
                        type="file"
                        className="form-control form-control-sm"
                        accept=".csv"
                        onChange={handleImport}
                    />
                    {importResult && (
                        <div style={{
                            marginTop: '8px',
                            padding: '8px',
                            background: importResult.errors?.length ? '#fff3cd' : '#d1e7dd',
                            borderRadius: '4px'
                        }}>
                            {importResult.created} creati, {importResult.updated} aggiornati
                            {importResult.errors?.length > 0 && (
                                <ul style={{ margin: '4px 0 0', paddingLeft: '20px' }}>
                                    {importResult.errors.slice(0, 3).map((err, i) => (
                                        <li key={i}>{err}</li>
                                    ))}
                                </ul>
                            )}
                        </div>
                    )}
                </div>
            )}

            {/* Alert pending */}
            {pendingCount > 0 && !statusFilter && (
                <div style={{
                    background: '#fff3cd',
                    border: '1px solid #ffc107',
                    borderRadius: '8px',
                    padding: '10px 12px',
                    marginBottom: '12px',
                    fontSize: '0.9rem'
                }}>
                    <strong>{pendingCount}</strong> in attesa di approvazione
                </div>
            )}

            {/* Lista registrazioni */}
            <div style={{
                background: 'white',
                borderRadius: '8px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                overflow: 'hidden'
            }}>
                <div style={{
                    padding: '10px 12px',
                    borderBottom: '1px solid #e9ecef',
                    fontWeight: 600,
                    fontSize: '0.9rem',
                    color: '#495057'
                }}>
                    Registrazioni ({filteredRegistrations.length})
                </div>

                {filteredRegistrations.length === 0 ? (
                    <div style={{ padding: '20px', textAlign: 'center', color: '#6c757d' }}>
                        Nessuna registrazione trovata
                    </div>
                ) : (
                    filteredRegistrations.map(reg => (
                        <div key={reg.id} style={{
                            borderBottom: '1px solid #e9ecef'
                        }}>
                            {editingId === reg.id ? (
                                /* Edit Mode - Compact */
                                <div style={{ padding: '12px', background: '#f8f9fa' }}>
                                    <div style={{ display: 'grid', gap: '8px', gridTemplateColumns: '1fr 1fr' }}>
                                        <input
                                            type="text"
                                            className="form-control form-control-sm"
                                            placeholder="Nome"
                                            value={editData.nome}
                                            onChange={(e) => setEditData({ ...editData, nome: e.target.value })}
                                        />
                                        <input
                                            type="text"
                                            className="form-control form-control-sm"
                                            placeholder="Cognome"
                                            value={editData.cognome}
                                            onChange={(e) => setEditData({ ...editData, cognome: e.target.value })}
                                        />
                                        <input
                                            type="email"
                                            className="form-control form-control-sm"
                                            placeholder="Email"
                                            value={editData.email}
                                            onChange={(e) => setEditData({ ...editData, email: e.target.value })}
                                            style={{ gridColumn: '1 / -1' }}
                                        />
                                        <input
                                            type="tel"
                                            className="form-control form-control-sm"
                                            placeholder="Telefono"
                                            value={editData.telefono}
                                            onChange={(e) => setEditData({ ...editData, telefono: e.target.value })}
                                        />
                                        <input
                                            type="number"
                                            className="form-control form-control-sm"
                                            placeholder="Municipio"
                                            value={editData.municipio}
                                            onChange={(e) => setEditData({ ...editData, municipio: e.target.value })}
                                            min="1"
                                            max="15"
                                        />
                                        <input
                                            type="text"
                                            className="form-control form-control-sm"
                                            placeholder="Seggio preferenza"
                                            value={editData.seggio_preferenza}
                                            onChange={(e) => setEditData({ ...editData, seggio_preferenza: e.target.value })}
                                            style={{ gridColumn: '1 / -1' }}
                                        />
                                        <input
                                            type="text"
                                            className="form-control form-control-sm"
                                            placeholder="Note"
                                            value={editData.notes}
                                            onChange={(e) => setEditData({ ...editData, notes: e.target.value })}
                                            style={{ gridColumn: '1 / -1' }}
                                        />
                                    </div>
                                    <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
                                        <button className="btn btn-success btn-sm" onClick={handleSaveEdit} style={{ flex: 1 }}>
                                            Salva
                                        </button>
                                        <button className="btn btn-secondary btn-sm" onClick={handleCancelEdit} style={{ flex: 1 }}>
                                            Annulla
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                /* View Mode */
                                <div
                                    onClick={() => toggleExpand(reg.id)}
                                    style={{
                                        padding: '12px',
                                        cursor: 'pointer',
                                        background: expandedId === reg.id ? '#f8f9fa' : 'transparent'
                                    }}
                                >
                                    {/* Riga principale */}
                                    <div style={{
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        alignItems: 'flex-start',
                                        marginBottom: '4px'
                                    }}>
                                        <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>
                                            {reg.cognome} {reg.nome}
                                        </div>
                                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                                            {getStatusBadge(reg.status)}
                                            {reg.fuorisede && (
                                                <span style={{
                                                    display: 'inline-block',
                                                    padding: '2px 8px',
                                                    borderRadius: '4px',
                                                    fontSize: '0.7rem',
                                                    fontWeight: 500,
                                                    backgroundColor: '#0dcaf0',
                                                    color: '#000'
                                                }}>
                                                    <i className="fas fa-suitcase me-1" style={{ fontSize: '0.65rem' }}></i>
                                                    Fuorisede
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    {/* Info secondarie */}
                                    <div style={{ fontSize: '0.8rem', color: '#6c757d' }}>
                                        <div>{reg.email}</div>
                                        <div style={{ display: 'flex', gap: '12px', marginTop: '2px' }}>
                                            <span><strong>{reg.comune}</strong></span>
                                            {reg.municipio && <span>{reg.municipio}</span>}
                                            {reg.telefono && <span>{reg.telefono}</span>}
                                        </div>
                                    </div>

                                    {reg.rejection_reason && (
                                        <div style={{
                                            marginTop: '6px',
                                            fontSize: '0.8rem',
                                            color: '#dc3545',
                                            fontStyle: 'italic'
                                        }}>
                                            Rifiuto: {reg.rejection_reason}
                                        </div>
                                    )}

                                    {/* Expanded Content */}
                                    {expandedId === reg.id && (
                                        <div style={{ marginTop: '12px' }} onClick={(e) => e.stopPropagation()}>
                                            {/* Dettagli extra */}
                                            <div style={{
                                                background: 'white',
                                                borderRadius: '6px',
                                                padding: '10px',
                                                marginBottom: '10px',
                                                fontSize: '0.8rem',
                                                border: '1px solid #dee2e6'
                                            }}>
                                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px' }}>
                                                    <div><span style={{ color: '#6c757d' }}>Nascita:</span> {reg.comune_nascita || '-'}</div>
                                                    <div><span style={{ color: '#6c757d' }}>Data:</span> {formatDate(reg.data_nascita) || '-'}</div>
                                                    <div style={{ gridColumn: '1 / -1' }}>
                                                        <span style={{ color: '#6c757d' }}>Residenza:</span> {reg.comune_residenza || '-'}, {reg.indirizzo_residenza || '-'}
                                                    </div>
                                                    {reg.fuorisede !== null && (
                                                        <div style={{ gridColumn: '1 / -1' }}>
                                                            <span style={{ color: '#6c757d' }}>Fuorisede:</span>{' '}
                                                            {reg.fuorisede ? (
                                                                <span style={{
                                                                    background: '#0dcaf0',
                                                                    color: '#000',
                                                                    padding: '1px 6px',
                                                                    borderRadius: '4px',
                                                                    fontSize: '0.75rem',
                                                                    fontWeight: 500
                                                                }}>SI</span>
                                                            ) : (
                                                                <span style={{ color: '#6c757d' }}>No</span>
                                                            )}
                                                        </div>
                                                    )}
                                                    {reg.fuorisede && reg.comune_domicilio && (
                                                        <div style={{ gridColumn: '1 / -1' }}>
                                                            <span style={{ color: '#6c757d' }}>Domicilio:</span> {reg.comune_domicilio}, {reg.indirizzo_domicilio || '-'}
                                                        </div>
                                                    )}
                                                    {reg.seggio_preferenza && (
                                                        <div style={{ gridColumn: '1 / -1' }}>
                                                            <span style={{ color: '#6c757d' }}>Preferenza:</span> {reg.seggio_preferenza}
                                                        </div>
                                                    )}
                                                    {reg.notes && (
                                                        <div style={{ gridColumn: '1 / -1' }}>
                                                            <span style={{ color: '#6c757d' }}>Note:</span> {reg.notes}
                                                        </div>
                                                    )}
                                                    {/* Origine registrazione */}
                                                    <div style={{ gridColumn: '1 / -1', marginTop: '4px', paddingTop: '4px', borderTop: '1px dashed #dee2e6' }}>
                                                        <span style={{ color: '#6c757d' }}>Origine:</span>{' '}
                                                        {reg.campagna_slug ? (
                                                            <a
                                                                href={`/campagna/${reg.campagna_slug}`}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                                style={{ color: '#0d6efd' }}
                                                            >
                                                                <i className="fas fa-bullhorn me-1"></i>
                                                                {reg.campagna_nome}
                                                            </a>
                                                        ) : (
                                                            <span style={{
                                                                background: reg.source === 'SELF' ? '#6c757d' : reg.source === 'IMPORT' ? '#0dcaf0' : '#ffc107',
                                                                color: reg.source === 'IMPORT' ? '#000' : '#fff',
                                                                padding: '1px 6px',
                                                                borderRadius: '4px',
                                                                fontSize: '0.75rem',
                                                                fontWeight: 500
                                                            }}>
                                                                {reg.source === 'SELF' ? 'Auto-registrazione' :
                                                                 reg.source === 'IMPORT' ? 'CSV Import' :
                                                                 reg.source === 'MANUAL' ? 'Manuale' : reg.source}
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Azioni */}
                                            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                                                {reg.status === 'PENDING' && (
                                                    <>
                                                        <button
                                                            className="btn btn-success btn-sm"
                                                            onClick={() => openModal('approve', reg)}
                                                            style={{ flex: '1 1 calc(50% - 3px)' }}
                                                        >
                                                            Approva
                                                        </button>
                                                        <button
                                                            className="btn btn-danger btn-sm"
                                                            onClick={() => openModal('reject', reg)}
                                                            style={{ flex: '1 1 calc(50% - 3px)' }}
                                                        >
                                                            Rifiuta
                                                        </button>
                                                    </>
                                                )}
                                                <button
                                                    className="btn btn-outline-primary btn-sm"
                                                    onClick={() => handleEdit(reg)}
                                                    style={{ flex: '1 1 calc(50% - 3px)' }}
                                                >
                                                    Modifica
                                                </button>
                                                <button
                                                    className="btn btn-outline-danger btn-sm"
                                                    onClick={() => openModal('delete', reg)}
                                                    style={{ flex: '1 1 calc(50% - 3px)' }}
                                                >
                                                    Elimina
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    ))
                )}
            </div>
        </>
    );
}

export default GestioneRdl;
