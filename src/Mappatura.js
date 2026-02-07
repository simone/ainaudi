import React, { useState, useEffect, useCallback } from 'react';
import ConfirmModal from './ConfirmModal';

/**
 * Genera un link WhatsApp per un numero di telefono
 */
const getWhatsAppLink = (phone) => {
    if (!phone) return null;
    const cleaned = phone.replace(/[\s\-\(\)]/g, '');
    const international = cleaned.startsWith('3') && cleaned.length === 10
        ? `39${cleaned}`
        : cleaned.startsWith('+') ? cleaned.substring(1) : cleaned;
    return `https://wa.me/${international}`;
};

/**
 * Genera e scarica un file vCard per salvare il contatto
 */
const downloadVCard = (name, phone, email) => {
    if (!phone) return;
    const cleaned = phone.replace(/[\s\-\(\)]/g, '');
    const international = cleaned.startsWith('3') && cleaned.length === 10
        ? `+39${cleaned}`
        : cleaned.startsWith('+') ? cleaned : `+${cleaned}`;

    const vcard = `BEGIN:VCARD
VERSION:3.0
FN:${name}
TEL;TYPE=CELL:${international}
${email ? `EMAIL:${email}` : ''}
END:VCARD`;

    const blob = new Blob([vcard], { type: 'text/vcard' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${name.replace(/\s+/g, '_')}_-_RDL.vcf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
};

function Mappatura({ client, setError, initialComuneId, initialMunicipioId }) {
    // View state
    const [activeTab, setActiveTab] = useState('sezioni'); // 'sezioni' or 'rdl'

    // Data states
    const [plessi, setPlessi] = useState([]);
    const [rdlList, setRdlList] = useState([]);
    const [loading, setLoading] = useState(true);

    // Filter states
    const [comuneFilter, setComuneFilter] = useState(initialComuneId || '');
    const [municipioFilter, setMunicipioFilter] = useState(initialMunicipioId || '');
    const [searchFilter, setSearchFilter] = useState('');
    const [sezioneSearchFilter, setSezioneSearchFilter] = useState('');
    const [filterStatus, setFilterStatus] = useState('all'); // 'all' | 'assigned' | 'unassigned'

    // Totals for stats bar
    const [totals, setTotals] = useState({ sezioni: 0, assigned: 0, unassigned: 0 });

    // View mode: 'grouped' (by plesso) or 'flat' (list)
    const [viewMode, setViewMode] = useState('grouped');

    // Multi-selection state
    const [selectedSezioni, setSelectedSezioni] = useState(new Set());

    // Bulk assign modal
    const [bulkModal, setBulkModal] = useState({
        show: false,
        ruolo: null,
        rdlList: [],
        selectedRdl: null,
        loading: false
    });

    // Expanded plessi (accordion)
    const [expandedPlessi, setExpandedPlessi] = useState(new Set());

    // Assignment modal
    const [modal, setModal] = useState({
        show: false,
        sezione: null,
        ruolo: null,
        rdlList: [],
        selectedRdl: null
    });

    // Removal modal
    const [removeModal, setRemoveModal] = useState({
        show: false,
        assignment: null,
        sezione: null
    });

    // Add sections modal (from RDL view)
    const [addSezioniModal, setAddSezioniModal] = useState({
        show: false,
        rdl: null,
        sezioni: [],
        selectedSezioni: new Set(),
        ruolo: 'RDL',
        loading: false
    });

    // Assegna preferenze modal
    const [assegnaPreferenzeModal, setAssegnaPreferenzeModal] = useState({
        show: false,
        rdl: null,
        preferenza: '',
        sezioniTrovate: [],
        selectedSezioni: new Set(),
        ruolo: 'RDL',
        loading: false
    });

    // Load data when filters change (or on mount)
    useEffect(() => {
        loadData();
    }, [comuneFilter, municipioFilter, filterStatus, activeTab]);

    // Clear selection when filters change or tab changes
    useEffect(() => {
        setSelectedSezioni(new Set());
    }, [comuneFilter, municipioFilter, filterStatus, activeTab]);

    // Clear search filters when tab changes
    useEffect(() => {
        setSearchFilter('');
        setSezioneSearchFilter('');
    }, [activeTab]);

    const loadData = useCallback(async () => {
        setLoading(true);

        const filters = {};
        if (comuneFilter) filters.comune_id = comuneFilter;
        if (municipioFilter) filters.municipio_id = municipioFilter;
        if (filterStatus !== 'all') filters.filter_status = filterStatus;

        try {
            if (activeTab === 'sezioni') {
                const result = await client.mappatura.sezioni(filters);
                if (result.error) {
                    setError(result.error);
                } else {
                    setPlessi(result.plessi || []);
                    // Set totals from response
                    if (result.totals) {
                        setTotals(result.totals);
                    }
                    // Start with all plessi collapsed
                    setExpandedPlessi(new Set());
                }
            } else {
                filters.search = searchFilter;
                const result = await client.mappatura.rdl(filters);
                if (result.error) {
                    setError(result.error);
                } else {
                    setRdlList(result.rdl || []);
                }
            }
        } catch (err) {
            setError(err.message);
        }

        setLoading(false);
    }, [comuneFilter, municipioFilter, filterStatus, activeTab, searchFilter, client, setError]);

    // Toggle plesso expansion
    const togglePlesso = (denominazione) => {
        setExpandedPlessi(prev => {
            const next = new Set(prev);
            if (next.has(denominazione)) {
                next.delete(denominazione);
            } else {
                next.add(denominazione);
            }
            return next;
        });
    };

    // Open assignment modal for a slot
    const openAssignModal = async (sezione, ruolo) => {
        setModal({
            show: true,
            sezione,
            ruolo,
            rdlList: [],
            selectedRdl: null,
            loading: true
        });

        // Load available RDL - filter by sezione's municipio if present
        const filters = {};
        if (comuneFilter) filters.comune_id = comuneFilter;
        // Se la sezione ha un municipio, filtra gli RDL per quel municipio
        if (sezione.municipio) {
            filters.municipio = sezione.municipio;  // Usa il numero del municipio
        } else if (municipioFilter) {
            filters.municipio_id = municipioFilter;
        }

        const result = await client.mappatura.rdl(filters);
        if (result.error) {
            setError(result.error);
            closeModal();
        } else {
            setModal(prev => ({
                ...prev,
                rdlList: result.rdl || [],
                loading: false
            }));
        }
    };

    const closeModal = () => {
        setModal({
            show: false,
            sezione: null,
            ruolo: null,
            rdlList: [],
            selectedRdl: null
        });
    };

    const handleAssign = async () => {
        const { sezione, ruolo, selectedRdl } = modal;
        if (!sezione || !selectedRdl) return;

        closeModal();

        const result = await client.mappatura.assegna(
            sezione.id,
            selectedRdl.rdl_registration_id,
            ruolo
        );

        if (result.error) {
            setError(result.error);
        } else {
            // Invalidate and reload
            client.mappatura.invalidateCache();
            loadData();
        }
    };

    // Open removal confirmation modal
    const openRemoveModal = (assignment, sezione) => {
        setRemoveModal({
            show: true,
            assignment,
            sezione
        });
    };

    const closeRemoveModal = () => {
        setRemoveModal({
            show: false,
            assignment: null,
            sezione: null
        });
    };

    const handleRemove = async () => {
        const { assignment } = removeModal;
        if (!assignment) return;

        closeRemoveModal();

        const result = await client.mappatura.rimuovi(assignment.assignment_id);

        if (result.error) {
            setError(result.error);
        } else {
            client.mappatura.invalidateCache();
            loadData();
        }
    };

    // Multi-selection helpers
    const toggleSelection = (sezId) => {
        setSelectedSezioni(prev => {
            const next = new Set(prev);
            if (next.has(sezId)) {
                next.delete(sezId);
            } else {
                next.add(sezId);
            }
            return next;
        });
    };

    const selectAllInPlesso = (plesso, checked) => {
        setSelectedSezioni(prev => {
            const next = new Set(prev);
            for (const sez of plesso.sezioni) {
                if (checked) {
                    next.add(sez.id);
                } else {
                    next.delete(sez.id);
                }
            }
            return next;
        });
    };

    const isPlessoFullySelected = (plesso) => {
        if (plesso.sezioni.length === 0) return false;
        return plesso.sezioni.every(s => selectedSezioni.has(s.id));
    };

    const isPlessoPartiallySelected = (plesso) => {
        if (plesso.sezioni.length === 0) return false;
        const selected = plesso.sezioni.filter(s => selectedSezioni.has(s.id));
        return selected.length > 0 && selected.length < plesso.sezioni.length;
    };

    // Bulk modal handlers
    const openBulkModal = async (ruolo) => {
        setBulkModal({
            show: true,
            ruolo,
            rdlList: [],
            selectedRdl: null,
            loading: true
        });

        // Load available RDL
        const filters = {};
        if (comuneFilter) filters.comune_id = comuneFilter;
        if (municipioFilter) filters.municipio_id = municipioFilter;

        const result = await client.mappatura.rdl(filters);
        if (result.error) {
            setError(result.error);
            closeBulkModal();
        } else {
            setBulkModal(prev => ({
                ...prev,
                rdlList: result.rdl || [],
                loading: false
            }));
        }
    };

    const closeBulkModal = () => {
        setBulkModal({
            show: false,
            ruolo: null,
            rdlList: [],
            selectedRdl: null,
            loading: false
        });
    };

    const handleBulkAssign = async () => {
        const { ruolo, selectedRdl } = bulkModal;
        if (!selectedRdl || selectedSezioni.size === 0) return;

        closeBulkModal();

        const result = await client.mappatura.assegnaBulk(
            selectedRdl.rdl_registration_id,
            Array.from(selectedSezioni),
            ruolo
        );

        if (result.error) {
            setError(result.error);
        } else {
            setSelectedSezioni(new Set());
            client.mappatura.invalidateCache();
            loadData();
        }
    };

    // Filter plessi and sezioni based on search
    const filterPlessiBySearch = (plessiList) => {
        if (!sezioneSearchFilter) return plessiList;

        const searchLower = sezioneSearchFilter.toLowerCase();

        return plessiList.map(plesso => {
            // Check if plesso matches
            const plessoMatches =
                plesso.denominazione?.toLowerCase().includes(searchLower) ||
                plesso.indirizzo?.toLowerCase().includes(searchLower);

            // Filter sezioni by numero
            const filteredSezioni = plesso.sezioni.filter(sez =>
                sez.numero?.toString().includes(searchLower) ||
                plessoMatches // Include all sezioni if plesso matches
            );

            // Return plesso only if it has matching sezioni
            if (filteredSezioni.length > 0) {
                return {
                    ...plesso,
                    sezioni: filteredSezioni
                };
            }
            return null;
        }).filter(p => p !== null);
    };

    const filteredPlessi = filterPlessiBySearch(plessi);

    // Get all sections flat for flat view
    const allSezioniFlat = filteredPlessi.flatMap(p =>
        p.sezioni.map(s => ({ ...s, plesso: p.denominazione, plessoIndirizzo: p.indirizzo }))
    );

    // Add sections from RDL view
    const openAddSezioniModal = async (rdl) => {
        setAddSezioniModal({
            show: true,
            rdl,
            sezioni: [],
            selectedSezioni: new Set(),
            ruolo: 'RDL',
            loading: true
        });

        // Load unassigned sections for RDL's territory
        const filters = {
            filter_status: 'unassigned'
        };
        if (rdl.comune_id) filters.comune_id = rdl.comune_id;
        if (rdl.municipio_id) filters.municipio_id = rdl.municipio_id;

        const result = await client.mappatura.sezioni(filters);
        if (result.error) {
            setError(result.error);
            closeAddSezioniModal();
        } else {
            // Flatten all sections from plessi
            const allSezioni = (result.plessi || []).flatMap(p =>
                p.sezioni.map(s => ({ ...s, plesso: p.denominazione }))
            );
            setAddSezioniModal(prev => ({
                ...prev,
                sezioni: allSezioni,
                loading: false
            }));
        }
    };

    const closeAddSezioniModal = () => {
        setAddSezioniModal({
            show: false,
            rdl: null,
            sezioni: [],
            selectedSezioni: new Set(),
            ruolo: 'RDL',
            loading: false
        });
    };

    const toggleAddSezioneSelection = (sezId) => {
        setAddSezioniModal(prev => {
            const next = new Set(prev.selectedSezioni);
            if (next.has(sezId)) {
                next.delete(sezId);
            } else {
                next.add(sezId);
            }
            return { ...prev, selectedSezioni: next };
        });
    };

    const handleAddSezioni = async () => {
        const { rdl, selectedSezioni, ruolo } = addSezioniModal;
        if (!rdl || selectedSezioni.size === 0) return;

        closeAddSezioniModal();

        const result = await client.mappatura.assegnaBulk(
            rdl.rdl_registration_id,
            Array.from(selectedSezioni),
            ruolo
        );

        if (result.error) {
            setError(result.error);
        } else {
            client.mappatura.invalidateCache();
            loadData();
        }
    };

    // Assegna preferenze handlers
    const openAssegnaPreferenzeModal = async (rdl) => {
        setAssegnaPreferenzeModal({
            show: true,
            rdl,
            preferenza: rdl.seggio_preferenza || '',
            sezioniTrovate: [],
            selectedSezioni: new Set(),
            ruolo: 'RDL',
            loading: true
        });

        // Analizza preferenze
        const result = await client.mappatura.analizzaPreferenze(
            rdl.rdl_registration_id,
            rdl.seggio_preferenza
        );

        if (result.error) {
            setError(result.error);
            closeAssegnaPreferenzeModal();
        } else {
            // Pre-seleziona solo le sezioni disponibili (non assegnate)
            const disponibili = (result.all_sezioni || []).filter(s => !s.is_assigned);
            const preselected = new Set(disponibili.map(s => s.id));

            setAssegnaPreferenzeModal(prev => ({
                ...prev,
                sezioniTrovate: result.all_sezioni || [],
                selectedSezioni: preselected,
                loading: false
            }));
        }
    };

    const closeAssegnaPreferenzeModal = () => {
        setAssegnaPreferenzeModal({
            show: false,
            rdl: null,
            preferenza: '',
            sezioniTrovate: [],
            selectedSezioni: new Set(),
            ruolo: 'RDL',
            loading: false
        });
    };

    const toggleAssegnaPreferenzeSelection = (sezId) => {
        setAssegnaPreferenzeModal(prev => {
            const next = new Set(prev.selectedSezioni);
            if (next.has(sezId)) {
                next.delete(sezId);
            } else {
                next.add(sezId);
            }
            return { ...prev, selectedSezioni: next };
        });
    };

    const handleAssegnaPreferenze = async () => {
        const { rdl, selectedSezioni, ruolo } = assegnaPreferenzeModal;
        if (!rdl || selectedSezioni.size === 0) return;

        closeAssegnaPreferenzeModal();

        const result = await client.mappatura.assegnaBulk(
            rdl.rdl_registration_id,
            Array.from(selectedSezioni),
            ruolo
        );

        if (result.error) {
            setError(result.error);
        } else {
            client.mappatura.invalidateCache();
            loadData();
        }
    };

    // Search filter and sort for RDL tab
    // Sort: fewer sections first, then alphabetically by cognome/nome
    const filteredRdl = rdlList
        .filter(rdl => {
            if (!searchFilter) return true;
            const search = searchFilter.toLowerCase();
            return (
                rdl.email.toLowerCase().includes(search) ||
                rdl.nome.toLowerCase().includes(search) ||
                rdl.cognome.toLowerCase().includes(search)
            );
        })
        .sort((a, b) => {
            // First by number of sections (fewer first)
            if (a.totale_sezioni !== b.totale_sezioni) {
                return a.totale_sezioni - b.totale_sezioni;
            }
            // Then alphabetically by cognome, then nome
            const cognomeCompare = a.cognome.localeCompare(b.cognome);
            if (cognomeCompare !== 0) return cognomeCompare;
            return a.nome.localeCompare(b.nome);
        });

    if (loading && plessi.length === 0 && rdlList.length === 0) {
        return (
            <div className="loading-container" role="status" aria-live="polite">
                <div className="spinner-border text-primary">
                    <span className="visually-hidden">Caricamento in corso...</span>
                </div>
                <p className="loading-text">Caricamento dati...</p>
            </div>
        );
    }

    return (
        <>
            {/* Assignment Modal */}
            <ConfirmModal
                show={modal.show}
                onConfirm={handleAssign}
                onCancel={closeModal}
                title={`Assegna ${modal.ruolo === 'RDL' ? 'Effettivo' : 'Supplente'}`}
                confirmText="Assegna"
                confirmVariant="primary"
                confirmDisabled={!modal.selectedRdl}
            >
                <div>
                    <div className="mappatura-modal-info">
                        <strong>Sezione:</strong> {modal.sezione?.numero}
                        {modal.sezione?.comune && ` - ${modal.sezione.comune}`}
                        {modal.sezione?.municipio && ` (Mun. ${modal.sezione.municipio})`}
                    </div>
                    <div className="mappatura-modal-info">
                        <strong>Ruolo:</strong> {modal.ruolo === 'RDL' ? 'Effettivo' : 'Supplente'}
                    </div>
                    <div className="mappatura-modal-territorio-hint">
                        Mostra solo RDL di {modal.sezione?.comune || 'questo comune'}
                        {modal.sezione?.municipio && ` - Municipio ${modal.sezione.municipio}`}
                    </div>

                    {modal.loading ? (
                        <div style={{ padding: '20px', textAlign: 'center' }}>
                            <div className="spinner-border spinner-border-sm text-primary"></div>
                            <span style={{ marginLeft: '8px' }}>Caricamento RDL...</span>
                        </div>
                    ) : (
                        <>
                            <input
                                type="search"
                                className="form-control form-control-sm mt-2 mb-2"
                                placeholder="Cerca RDL..."
                                onChange={(e) => {
                                    const search = e.target.value.toLowerCase();
                                    setModal(prev => ({
                                        ...prev,
                                        filteredRdl: prev.rdlList.filter(r =>
                                            r.email.toLowerCase().includes(search) ||
                                            r.nome.toLowerCase().includes(search) ||
                                            r.cognome.toLowerCase().includes(search)
                                        )
                                    }));
                                }}
                            />
                            <div className="mappatura-rdl-select">
                                {(modal.filteredRdl || modal.rdlList).map(rdl => (
                                    <div
                                        key={rdl.rdl_registration_id}
                                        className={`mappatura-rdl-option ${modal.selectedRdl?.rdl_registration_id === rdl.rdl_registration_id ? 'selected' : ''}`}
                                        onClick={() => setModal(prev => ({ ...prev, selectedRdl: rdl }))}
                                    >
                                        <div className="mappatura-rdl-option-name">
                                            {rdl.cognome} {rdl.nome}
                                        </div>
                                        <div className="mappatura-rdl-option-email">
                                            {rdl.email}
                                        </div>
                                        {rdl.seggio_preferenza && (
                                            <div className="mappatura-rdl-option-pref">
                                                <i className="fas fa-map-pin me-1"></i>
                                                <strong>Preferenza:</strong> {rdl.seggio_preferenza}
                                            </div>
                                        )}
                                        {rdl.notes && (
                                            <div className="mappatura-rdl-option-notes">
                                                <i className="fas fa-sticky-note me-1"></i>
                                                <strong>Note:</strong> {rdl.notes}
                                            </div>
                                        )}
                                        {rdl.totale_sezioni > 0 && (
                                            <div className="mappatura-rdl-option-count">
                                                <i className="fas fa-list me-1"></i>
                                                {rdl.totale_sezioni} sezioni assegnate
                                            </div>
                                        )}
                                    </div>
                                ))}
                                {(modal.filteredRdl || modal.rdlList).length === 0 && (
                                    <div style={{ padding: '12px', textAlign: 'center', color: '#6c757d' }}>
                                        Nessun RDL disponibile
                                    </div>
                                )}
                            </div>
                        </>
                    )}
                </div>
            </ConfirmModal>

            {/* Remove Confirmation Modal */}
            <ConfirmModal
                show={removeModal.show}
                onConfirm={handleRemove}
                onCancel={closeRemoveModal}
                title="Rimuovi Assegnazione"
                confirmText="Rimuovi"
                confirmVariant="danger"
            >
                <div>
                    <p>Vuoi rimuovere questa assegnazione?</p>
                    <div className="mappatura-modal-info">
                        <strong>RDL:</strong> {removeModal.assignment?.user_nome}
                    </div>
                    <div className="mappatura-modal-info">
                        <strong>Email:</strong> {removeModal.assignment?.user_email}
                    </div>
                    <div className="mappatura-modal-info">
                        <strong>Sezione:</strong> {removeModal.sezione?.numero}
                    </div>
                </div>
            </ConfirmModal>

            {/* Tabs */}
            <div className="mappatura-tabs">
                <button
                    className={`mappatura-tab ${activeTab === 'sezioni' ? 'active' : ''}`}
                    onClick={() => setActiveTab('sezioni')}
                >
                    Per Sezione
                </button>
                <button
                    className={`mappatura-tab ${activeTab === 'rdl' ? 'active' : ''}`}
                    onClick={() => setActiveTab('rdl')}
                >
                    Per RDL
                </button>
            </div>

            {/* Filtri */}
            <div className="mappatura-filters">
                {activeTab === 'sezioni' && (
                    <>
                        <div className="mappatura-filters-row">
                            <select
                                className="form-select form-select-sm"
                                value={filterStatus}
                                onChange={(e) => setFilterStatus(e.target.value)}
                            >
                                <option value="all">Tutte le sezioni</option>
                                <option value="unassigned">Non assegnate</option>
                                <option value="assigned">Assegnate</option>
                            </select>
                            <div className="mappatura-view-toggle">
                                <button
                                    className={viewMode === 'grouped' ? 'active' : ''}
                                    onClick={() => setViewMode('grouped')}
                                    title="Vista per plesso"
                                >
                                    Per Plesso
                                </button>
                                <button
                                    className={viewMode === 'flat' ? 'active' : ''}
                                    onClick={() => setViewMode('flat')}
                                    title="Vista lista"
                                >
                                    Lista
                                </button>
                            </div>
                        </div>
                        <input
                            type="search"
                            className="form-control form-control-sm mt-2"
                            placeholder="Cerca per numero sezione, indirizzo o plesso..."
                            value={sezioneSearchFilter}
                            onChange={(e) => setSezioneSearchFilter(e.target.value)}
                        />
                    </>
                )}
                {activeTab === 'rdl' && (
                    <input
                        type="search"
                        className="form-control form-control-sm"
                        placeholder="Cerca RDL..."
                        value={searchFilter}
                        onChange={(e) => setSearchFilter(e.target.value)}
                    />
                )}
            </div>

            {/* Stats bar - only for sezioni tab */}
            {activeTab === 'sezioni' && totals.sezioni > 0 && (
                <div className="mappatura-stats">
                    <span><strong>{totals.sezioni}</strong> sezioni</span>
                    <span className="assigned"><strong>{totals.assigned}</strong> assegnate</span>
                    <span className="unassigned"><strong>{totals.unassigned}</strong> da assegnare</span>
                </div>
            )}

            {/* Content */}
            {activeTab === 'sezioni' ? (
                <div className="mappatura-plessi">
                    {loading && (
                        <div className="mappatura-loading">
                            <div className="spinner-border spinner-border-sm text-primary"></div>
                            <span>Caricamento...</span>
                        </div>
                    )}

                    {!loading && filteredPlessi.length === 0 && (
                        <div className="mappatura-empty">
                            {sezioneSearchFilter ? `Nessuna sezione trovata per "${sezioneSearchFilter}"` : 'Nessuna sezione trovata'}
                        </div>
                    )}

                    {viewMode === 'grouped' ? (
                        /* Vista raggruppata per plesso */
                        filteredPlessi.map(plesso => (
                            <div key={plesso.denominazione} className="mappatura-plesso">
                                <div className="mappatura-plesso-header">
                                    {/* Checkbox select all in plesso */}
                                    <input
                                        type="checkbox"
                                        className="mappatura-plesso-checkbox"
                                        checked={isPlessoFullySelected(plesso)}
                                        ref={el => el && (el.indeterminate = isPlessoPartiallySelected(plesso))}
                                        onChange={(e) => {
                                            e.stopPropagation();
                                            selectAllInPlesso(plesso, e.target.checked);
                                        }}
                                        title="Seleziona tutte le sezioni del plesso"
                                    />
                                    <div
                                        className="mappatura-plesso-toggle"
                                        onClick={() => togglePlesso(plesso.denominazione)}
                                    >
                                        {expandedPlessi.has(plesso.denominazione) ? '▼' : '►'}
                                    </div>
                                    <div
                                        className="mappatura-plesso-info"
                                        onClick={() => togglePlesso(plesso.denominazione)}
                                    >
                                        <div className="mappatura-plesso-name">
                                            {plesso.denominazione}
                                            {plesso.municipio && (
                                                <span className="mappatura-plesso-municipio">Mun. {plesso.municipio}</span>
                                            )}
                                        </div>
                                        {plesso.indirizzo && (
                                            <div className="mappatura-plesso-address">{plesso.indirizzo}</div>
                                        )}
                                    </div>
                                    <div className="mappatura-plesso-stats">
                                        {/* Warning: supplente senza effettivo */}
                                        {plesso.warning > 0 && (
                                            <span className="mappatura-plesso-warning" title={`${plesso.warning} sezioni con supplente ma senza effettivo`}>
                                                ⚠️ {plesso.warning}
                                            </span>
                                        )}
                                        {/* Effettivi count */}
                                        <span className={`mappatura-plesso-count ${plesso.complete === plesso.totale ? 'complete' : ''}`} title="Effettivi assegnati">
                                            E: {plesso.complete}/{plesso.totale}
                                        </span>
                                        {/* Supplenti count */}
                                        {plesso.supplenti > 0 && (
                                            <span className="mappatura-plesso-supplenti" title="Supplenti assegnati">
                                                S: {plesso.supplenti}
                                            </span>
                                        )}
                                    </div>
                                </div>

                                {expandedPlessi.has(plesso.denominazione) && (
                                    <div className="mappatura-plesso-sezioni">
                                        {plesso.sezioni.map(sez => (
                                            <div key={sez.id} className={`mappatura-sezione ${sez.warning ? 'has-warning' : ''}`}>
                                                {/* Warning indicator */}
                                                {sez.warning && (
                                                    <span className="mappatura-sezione-warning" title="Supplente senza effettivo">⚠️</span>
                                                )}
                                                {/* Checkbox for selection */}
                                                <input
                                                    type="checkbox"
                                                    className="mappatura-sezione-checkbox"
                                                    checked={selectedSezioni.has(sez.id)}
                                                    onChange={() => toggleSelection(sez.id)}
                                                />
                                                <div className="mappatura-sezione-numero">
                                                    Sez. {sez.numero}
                                                    {sez.municipio && (
                                                        <span className="mappatura-sezione-municipio">
                                                            Mun. {sez.municipio}
                                                        </span>
                                                    )}
                                                </div>
                                                <div className="mappatura-sezione-slots">
                                                    {/* Effettivo slot */}
                                                    <div className={`mappatura-slot ${sez.effettivo ? 'assigned' : 'empty'}`}>
                                                        <span className="mappatura-slot-label">E:</span>
                                                        {sez.effettivo ? (
                                                            <>
                                                                {sez.effettivo.multi_plesso && (
                                                                    <span className="mappatura-slot-warning" title="RDL assegnato a più plessi">⚠️</span>
                                                                )}
                                                                {sez.effettivo.territorio_mismatch && (
                                                                    <span className="mappatura-slot-warning territorio" title="RDL registrato in altro territorio">❗</span>
                                                                )}
                                                                <span className="mappatura-slot-name">{sez.effettivo.user_nome}</span>
                                                                <button
                                                                    className="mappatura-slot-action remove"
                                                                    onClick={() => openRemoveModal(sez.effettivo, sez)}
                                                                    title="Rimuovi"
                                                                >
                                                                    ✕
                                                                </button>
                                                            </>
                                                        ) : (
                                                            <button
                                                                className="mappatura-slot-action add"
                                                                onClick={() => openAssignModal(sez, 'RDL')}
                                                                title="Assegna Effettivo"
                                                            >
                                                                +
                                                            </button>
                                                        )}
                                                    </div>
                                                    {/* Supplente slot */}
                                                    <div className={`mappatura-slot ${sez.supplente ? 'assigned' : 'empty'}`}>
                                                        <span className="mappatura-slot-label">S:</span>
                                                        {sez.supplente ? (
                                                            <>
                                                                {sez.supplente.multi_plesso && (
                                                                    <span className="mappatura-slot-warning" title="RDL assegnato a più plessi">⚠️</span>
                                                                )}
                                                                {sez.supplente.territorio_mismatch && (
                                                                    <span className="mappatura-slot-warning territorio" title="RDL registrato in altro territorio">❗</span>
                                                                )}
                                                                <span className="mappatura-slot-name">{sez.supplente.user_nome}</span>
                                                                <button
                                                                    className="mappatura-slot-action remove"
                                                                    onClick={() => openRemoveModal(sez.supplente, sez)}
                                                                    title="Rimuovi"
                                                                >
                                                                    ✕
                                                                </button>
                                                            </>
                                                        ) : (
                                                            <button
                                                                className="mappatura-slot-action add"
                                                                onClick={() => openAssignModal(sez, 'SUPPLENTE')}
                                                                title="Assegna Supplente"
                                                            >
                                                                +
                                                            </button>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        ))
                    ) : (
                        /* Vista lista piatta */
                        <div className="mappatura-flat-list">
                            {allSezioniFlat.map(sez => (
                                <div key={sez.id} className="mappatura-flat-item">
                                    <input
                                        type="checkbox"
                                        className="mappatura-sezione-checkbox"
                                        checked={selectedSezioni.has(sez.id)}
                                                                                onChange={() => toggleSelection(sez.id)}
                                    />
                                    <div className="mappatura-sezione-numero">
                                        Sez. {sez.numero}
                                        {sez.municipio && (
                                            <span className="mappatura-sezione-municipio">
                                                Mun. {sez.municipio}
                                            </span>
                                        )}
                                    </div>
                                    <span className="plesso-tag">{sez.plesso}</span>
                                    <div className="mappatura-sezione-slots">
                                        <div className={`mappatura-slot ${sez.effettivo ? 'assigned' : 'empty'}`}>
                                            <span className="mappatura-slot-label">E:</span>
                                            {sez.effettivo ? (
                                                <>
                                                    {sez.effettivo.multi_plesso && (
                                                        <span className="mappatura-slot-warning" title="RDL assegnato a più plessi">⚠️</span>
                                                    )}
                                                    {sez.effettivo.territorio_mismatch && (
                                                        <span className="mappatura-slot-warning territorio" title="RDL registrato in altro territorio">❗</span>
                                                    )}
                                                    <span className="mappatura-slot-name">{sez.effettivo.user_nome}</span>
                                                    <button
                                                        className="mappatura-slot-action remove"
                                                        onClick={() => openRemoveModal(sez.effettivo, sez)}
                                                        title="Rimuovi"
                                                    >
                                                        ✕
                                                    </button>
                                                </>
                                            ) : (
                                                <button
                                                    className="mappatura-slot-action add"
                                                    onClick={() => openAssignModal(sez, 'RDL')}
                                                    title="Assegna Effettivo"
                                                >
                                                    +
                                                </button>
                                            )}
                                        </div>
                                        <div className={`mappatura-slot ${sez.supplente ? 'assigned' : 'empty'}`}>
                                            <span className="mappatura-slot-label">S:</span>
                                            {sez.supplente ? (
                                                <>
                                                    {sez.supplente.multi_plesso && (
                                                        <span className="mappatura-slot-warning" title="RDL assegnato a più plessi">⚠️</span>
                                                    )}
                                                    {sez.supplente.territorio_mismatch && (
                                                        <span className="mappatura-slot-warning territorio" title="RDL registrato in altro territorio">❗</span>
                                                    )}
                                                    <span className="mappatura-slot-name">{sez.supplente.user_nome}</span>
                                                    <button
                                                        className="mappatura-slot-action remove"
                                                        onClick={() => openRemoveModal(sez.supplente, sez)}
                                                        title="Rimuovi"
                                                    >
                                                        ✕
                                                    </button>
                                                </>
                                            ) : (
                                                <button
                                                    className="mappatura-slot-action add"
                                                    onClick={() => openAssignModal(sez, 'SUPPLENTE')}
                                                    title="Assegna Supplente"
                                                >
                                                    +
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            ) : (
                /* Tab Per RDL */
                <div className="mappatura-rdl-list">
                    {loading && (
                        <div className="mappatura-loading">
                            <div className="spinner-border spinner-border-sm text-primary"></div>
                            <span>Caricamento...</span>
                        </div>
                    )}

                    {!loading && filteredRdl.length === 0 && (
                        <div className="mappatura-empty">
                            Nessun RDL trovato
                        </div>
                    )}

                    {filteredRdl.map(rdl => {
                        // Count unique plessi for this RDL
                        const allSezioni = [...(rdl.sezioni_effettivo || []), ...(rdl.sezioni_supplente || [])];
                        const uniquePlessi = new Set(allSezioni.map(s => s.plesso));
                        const isOnMultiplePlessi = uniquePlessi.size > 1;

                        // Check if preference is already assigned
                        // Extract numbers from preference text
                        const parseNumeriPreferenza = (testo) => {
                            if (!testo) return [];
                            const numeri = new Set();
                            const patterns = testo.match(/(\d+)(?:\s*[-–]\s*(\d+))?/g) || [];
                            patterns.forEach(pattern => {
                                const match = pattern.match(/(\d+)(?:\s*[-–]\s*(\d+))?/);
                                if (match) {
                                    const start = parseInt(match[1]);
                                    const end = match[2] ? parseInt(match[2]) : start;
                                    for (let n = start; n <= end; n++) {
                                        numeri.add(n);
                                    }
                                }
                            });
                            return Array.from(numeri);
                        };

                        const numeriPreferenza = parseNumeriPreferenza(rdl.seggio_preferenza);
                        const numeriAssegnati = new Set(allSezioni.map(s => parseInt(s.numero)));

                        // Show button only if:
                        // 1. Has preference AND
                        // 2. (No numbers in preference OR at least one number is not yet assigned)
                        const hasPrefenzaNonAssegnata = numeriPreferenza.length === 0 ||
                            numeriPreferenza.some(num => !numeriAssegnati.has(num));

                        return (
                        <div key={rdl.rdl_registration_id} className={`mappatura-rdl-card ${isOnMultiplePlessi ? 'multi-plesso' : ''}`}>
                            <div className="mappatura-rdl-header">
                                <div className="mappatura-rdl-name">
                                    {isOnMultiplePlessi && (
                                        <span className="mappatura-rdl-multi-warning" title={`Assegnato a ${uniquePlessi.size} plessi diversi`}>⚠️</span>
                                    )}
                                    {rdl.cognome} {rdl.nome}
                                </div>
                                <div className="mappatura-rdl-badge">
                                    {rdl.totale_sezioni > 0 ? (
                                        <span className="assigned">{rdl.totale_sezioni} sez.</span>
                                    ) : (
                                        <span className="available">Disponibile</span>
                                    )}
                                </div>
                            </div>
                            {/* Territorio dell'RDL */}
                            <div className="mappatura-rdl-territorio">
                                {rdl.comune}
                                {rdl.municipio && ` - ${rdl.municipio}`}
                            </div>
                            <div className="mappatura-rdl-details">
                                <div className="mappatura-rdl-email">{rdl.email}</div>
                                <div className="mappatura-rdl-phone">
                                    {rdl.telefono ? (
                                        <>
                                            <a
                                                href={getWhatsAppLink(rdl.telefono)}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                style={{ color: '#25D366', textDecoration: 'none' }}
                                                title="Contatta su WhatsApp"
                                            >
                                                {rdl.telefono}
                                            </a>
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    downloadVCard(`${rdl.cognome} ${rdl.nome}`, rdl.telefono, rdl.email);
                                                }}
                                                className="btn btn-link btn-sm p-0 ms-1"
                                                style={{ fontSize: '0.7rem', color: '#6c757d' }}
                                                title="Salva contatto"
                                            >
                                                <i className="fas fa-user-plus"></i>
                                            </button>
                                        </>
                                    ) : '-'}
                                </div>
                                {rdl.seggio_preferenza && (
                                    <div className="mappatura-rdl-pref">
                                        <i className="fas fa-map-pin me-1"></i>
                                        <strong>Pref:</strong> {rdl.seggio_preferenza}
                                    </div>
                                )}
                                {rdl.notes && (
                                    <div className="mappatura-rdl-notes">
                                        <i className="fas fa-sticky-note me-1"></i>
                                        <strong>Note:</strong> {rdl.notes}
                                    </div>
                                )}
                            </div>

                            {/* Add sections button */}
                            <div className="mappatura-rdl-actions">
                                <button
                                    className="btn btn-sm btn-outline-primary"
                                    onClick={() => openAddSezioniModal(rdl)}
                                >
                                    + Aggiungi Sezione
                                </button>
                                {rdl.seggio_preferenza && hasPrefenzaNonAssegnata && (
                                    <button
                                        className="btn btn-sm btn-outline-success ms-2"
                                        onClick={() => openAssegnaPreferenzeModal(rdl)}
                                        title="Analizza la preferenza e assegna automaticamente"
                                    >
                                        <i className="fas fa-magic me-1"></i>
                                        Assegna Preferita
                                    </button>
                                )}
                            </div>

                            {/* Sezioni assegnate */}
                            {(rdl.sezioni_effettivo.length > 0 || rdl.sezioni_supplente.length > 0) && (
                                <div className="mappatura-rdl-sezioni">
                                    {rdl.sezioni_effettivo.map(sez => (
                                        <div key={sez.sezione_id} className={`mappatura-rdl-sezione effettivo ${sez.territorio_mismatch ? 'mismatch' : ''}`}>
                                            {sez.territorio_mismatch && (
                                                <span className="mappatura-rdl-sezione-warning" title="Sezione in altro territorio">❗</span>
                                            )}
                                            <span className="mappatura-rdl-sezione-num">Sez. {sez.numero}</span>
                                            {sez.municipio && <span className="mappatura-rdl-sezione-mun">Mun. {sez.municipio}</span>}
                                            <span className="mappatura-rdl-sezione-ruolo">Effettivo</span>
                                            <span className="mappatura-rdl-sezione-plesso">{sez.plesso}</span>
                                            <button
                                                className="mappatura-rdl-sezione-remove"
                                                onClick={() => openRemoveModal({
                                                    assignment_id: sez.assignment_id,
                                                    user_nome: `${rdl.cognome} ${rdl.nome}`,
                                                    user_email: rdl.email
                                                }, { numero: sez.numero })}
                                            >
                                                ✕
                                            </button>
                                        </div>
                                    ))}
                                    {rdl.sezioni_supplente.map(sez => (
                                        <div key={sez.sezione_id} className={`mappatura-rdl-sezione supplente ${sez.territorio_mismatch ? 'mismatch' : ''}`}>
                                            {sez.territorio_mismatch && (
                                                <span className="mappatura-rdl-sezione-warning" title="Sezione in altro territorio">❗</span>
                                            )}
                                            <span className="mappatura-rdl-sezione-num">Sez. {sez.numero}</span>
                                            {sez.municipio && <span className="mappatura-rdl-sezione-mun">Mun. {sez.municipio}</span>}
                                            <span className="mappatura-rdl-sezione-ruolo">Supplente</span>
                                            <span className="mappatura-rdl-sezione-plesso">{sez.plesso}</span>
                                            <button
                                                className="mappatura-rdl-sezione-remove"
                                                onClick={() => openRemoveModal({
                                                    assignment_id: sez.assignment_id,
                                                    user_nome: `${rdl.cognome} ${rdl.nome}`,
                                                    user_email: rdl.email
                                                }, { numero: sez.numero })}
                                            >
                                                ✕
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    );
                    })}
                </div>
            )}

            {/* Legend */}
            <div className="mappatura-legend">
                <strong>Legenda:</strong>
                <span className="mappatura-legend-item">
                    <span className="effettivo"></span> Effettivo
                </span>
                <span className="mappatura-legend-item">
                    <span className="supplente"></span> Supplente
                </span>
                <span className="mappatura-legend-item">
                    <span className="empty"></span> Non assegnato
                </span>
                <span className="mappatura-legend-item">
                    ⚠️ Più plessi
                </span>
                <span className="mappatura-legend-item">
                    ❗ Altro territorio
                </span>
            </div>

            {/* Bulk Actions Bar */}
            {selectedSezioni.size > 0 && (
                <div className="mappatura-bulk-actions">
                    <span className="mappatura-bulk-count">
                        <strong>{selectedSezioni.size}</strong> sezioni selezionate
                    </span>
                    <div className="mappatura-bulk-buttons">
                        <button
                            className="btn btn-sm btn-success"
                            onClick={() => openBulkModal('RDL')}
                        >
                            Assegna Effettivo
                        </button>
                        <button
                            className="btn btn-sm btn-info"
                            onClick={() => openBulkModal('SUPPLENTE')}
                        >
                            Assegna Supplente
                        </button>
                        <button
                            className="btn btn-sm btn-outline-secondary"
                            onClick={() => setSelectedSezioni(new Set())}
                        >
                            Deseleziona
                        </button>
                    </div>
                </div>
            )}

            {/* Bulk Assign Modal */}
            <ConfirmModal
                show={bulkModal.show}
                onConfirm={handleBulkAssign}
                onCancel={closeBulkModal}
                title={`Assegna ${bulkModal.ruolo === 'RDL' ? 'Effettivo' : 'Supplente'} a ${selectedSezioni.size} sezioni`}
                confirmText="Assegna a tutte"
                confirmVariant="primary"
                confirmDisabled={!bulkModal.selectedRdl}
            >
                <div>
                    <div className="mappatura-modal-info">
                        <strong>Sezioni selezionate:</strong> {selectedSezioni.size}
                    </div>
                    <div className="mappatura-modal-info">
                        <strong>Ruolo:</strong> {bulkModal.ruolo === 'RDL' ? 'Effettivo' : 'Supplente'}
                    </div>

                    {bulkModal.loading ? (
                        <div style={{ padding: '20px', textAlign: 'center' }}>
                            <div className="spinner-border spinner-border-sm text-primary"></div>
                            <span style={{ marginLeft: '8px' }}>Caricamento RDL...</span>
                        </div>
                    ) : (
                        <>
                            <input
                                type="search"
                                className="form-control form-control-sm mt-2 mb-2"
                                placeholder="Cerca RDL..."
                                onChange={(e) => {
                                    const search = e.target.value.toLowerCase();
                                    setBulkModal(prev => ({
                                        ...prev,
                                        filteredRdl: prev.rdlList.filter(r =>
                                            r.email.toLowerCase().includes(search) ||
                                            r.nome.toLowerCase().includes(search) ||
                                            r.cognome.toLowerCase().includes(search)
                                        )
                                    }));
                                }}
                            />
                            <div className="mappatura-rdl-select">
                                {(bulkModal.filteredRdl || bulkModal.rdlList).map(rdl => (
                                    <div
                                        key={rdl.rdl_registration_id}
                                        className={`mappatura-rdl-option ${bulkModal.selectedRdl?.rdl_registration_id === rdl.rdl_registration_id ? 'selected' : ''}`}
                                        onClick={() => setBulkModal(prev => ({ ...prev, selectedRdl: rdl }))}
                                    >
                                        <div className="mappatura-rdl-option-name">
                                            {rdl.cognome} {rdl.nome}
                                        </div>
                                        <div className="mappatura-rdl-option-email">
                                            {rdl.email}
                                        </div>
                                        {rdl.seggio_preferenza && (
                                            <div className="mappatura-rdl-option-pref">
                                                <i className="fas fa-map-pin me-1"></i>
                                                <strong>Preferenza:</strong> {rdl.seggio_preferenza}
                                            </div>
                                        )}
                                        {rdl.notes && (
                                            <div className="mappatura-rdl-option-notes">
                                                <i className="fas fa-sticky-note me-1"></i>
                                                <strong>Note:</strong> {rdl.notes}
                                            </div>
                                        )}
                                        {rdl.totale_sezioni > 0 && (
                                            <div className="mappatura-rdl-option-count">
                                                <i className="fas fa-list me-1"></i>
                                                {rdl.totale_sezioni} sezioni assegnate
                                            </div>
                                        )}
                                    </div>
                                ))}
                                {(bulkModal.filteredRdl || bulkModal.rdlList).length === 0 && (
                                    <div style={{ padding: '12px', textAlign: 'center', color: '#6c757d' }}>
                                        Nessun RDL disponibile
                                    </div>
                                )}
                            </div>
                        </>
                    )}
                </div>
            </ConfirmModal>

            {/* Add Sections Modal (from RDL view) */}
            <ConfirmModal
                show={addSezioniModal.show}
                onConfirm={handleAddSezioni}
                onCancel={closeAddSezioniModal}
                title={`Aggiungi Sezioni a ${addSezioniModal.rdl?.cognome} ${addSezioniModal.rdl?.nome}`}
                confirmText={`Assegna ${addSezioniModal.selectedSezioni.size} sezioni`}
                confirmVariant="primary"
                confirmDisabled={addSezioniModal.selectedSezioni.size === 0}
            >
                <div>
                    <div className="mappatura-modal-info">
                        <strong>RDL:</strong> {addSezioniModal.rdl?.cognome} {addSezioniModal.rdl?.nome}
                    </div>
                    <div className="mappatura-modal-territorio-hint">
                        Territorio: {addSezioniModal.rdl?.comune}
                        {addSezioniModal.rdl?.municipio && ` - ${addSezioniModal.rdl.municipio}`}
                    </div>
                    <div className="mappatura-modal-info mb-2">
                        <label className="form-label mb-1">Ruolo:</label>
                        <select
                            className="form-select form-select-sm"
                            value={addSezioniModal.ruolo}
                            onChange={(e) => setAddSezioniModal(prev => ({ ...prev, ruolo: e.target.value }))}
                        >
                            <option value="RDL">Effettivo</option>
                            <option value="SUPPLENTE">Supplente</option>
                        </select>
                    </div>

                    {addSezioniModal.loading ? (
                        <div style={{ padding: '20px', textAlign: 'center' }}>
                            <div className="spinner-border spinner-border-sm text-primary"></div>
                            <span style={{ marginLeft: '8px' }}>Caricamento sezioni...</span>
                        </div>
                    ) : (
                        <>
                            <div className="mappatura-modal-info">
                                <strong>{addSezioniModal.sezioni.length}</strong> sezioni disponibili nel territorio
                                {addSezioniModal.selectedSezioni.size > 0 && (
                                    <span className="ms-2 text-primary">
                                        ({addSezioniModal.selectedSezioni.size} selezionate)
                                    </span>
                                )}
                            </div>
                            <div className="mappatura-add-sezioni-list">
                                {addSezioniModal.sezioni.map(sez => (
                                    <div
                                        key={sez.id}
                                        className={`mappatura-add-sezione-item ${addSezioniModal.selectedSezioni.has(sez.id) ? 'selected' : ''}`}
                                        onClick={() => toggleAddSezioneSelection(sez.id)}
                                    >
                                        <input
                                            type="checkbox"
                                            checked={addSezioniModal.selectedSezioni.has(sez.id)}
                                            onChange={() => {}}
                                        />
                                        <span className="mappatura-add-sezione-num">Sez. {sez.numero}</span>
                                        <span className="mappatura-add-sezione-plesso">{sez.plesso}</span>
                                    </div>
                                ))}
                                {addSezioniModal.sezioni.length === 0 && (
                                    <div style={{ padding: '12px', textAlign: 'center', color: '#6c757d' }}>
                                        Nessuna sezione disponibile
                                    </div>
                                )}
                            </div>
                        </>
                    )}
                </div>
            </ConfirmModal>

            {/* Assegna Preferenze Modal */}
            <ConfirmModal
                show={assegnaPreferenzeModal.show}
                onConfirm={handleAssegnaPreferenze}
                onCancel={closeAssegnaPreferenzeModal}
                title={`Assegna Preferenze: ${assegnaPreferenzeModal.rdl?.cognome} ${assegnaPreferenzeModal.rdl?.nome}`}
                confirmText={`Assegna ${assegnaPreferenzeModal.selectedSezioni.size} ${assegnaPreferenzeModal.selectedSezioni.size === 1 ? 'sezione' : 'sezioni'}`}
                confirmVariant="success"
                confirmDisabled={assegnaPreferenzeModal.selectedSezioni.size === 0}
            >
                <div>
                    <div className="mappatura-modal-info">
                        <strong>RDL:</strong> {assegnaPreferenzeModal.rdl?.cognome} {assegnaPreferenzeModal.rdl?.nome}
                    </div>
                    <div className="mappatura-modal-info">
                        <strong>Preferenza espressa:</strong> "{assegnaPreferenzeModal.preferenza}"
                    </div>
                    <div className="mappatura-modal-info mb-2">
                        <label className="form-label mb-1">Ruolo:</label>
                        <select
                            className="form-select form-select-sm"
                            value={assegnaPreferenzeModal.ruolo}
                            onChange={(e) => setAssegnaPreferenzeModal(prev => ({ ...prev, ruolo: e.target.value }))}
                        >
                            <option value="RDL">Effettivo</option>
                            <option value="SUPPLENTE">Supplente</option>
                        </select>
                    </div>

                    {assegnaPreferenzeModal.loading ? (
                        <div style={{ padding: '20px', textAlign: 'center' }}>
                            <div className="spinner-border spinner-border-sm text-primary"></div>
                            <span style={{ marginLeft: '8px' }}>Analisi preferenze in corso...</span>
                        </div>
                    ) : (
                        <>
                            {assegnaPreferenzeModal.sezioniTrovate.length === 0 ? (
                                <div className="alert alert-warning" style={{ marginTop: '12px' }}>
                                    <i className="fas fa-exclamation-triangle me-2"></i>
                                    Nessuna sezione trovata corrispondente alla preferenza.
                                </div>
                            ) : (
                                <>
                                    <div className="mappatura-modal-info">
                                        <strong>{assegnaPreferenzeModal.sezioniTrovate.length}</strong> sezioni trovate
                                        {assegnaPreferenzeModal.selectedSezioni.size > 0 && (
                                            <span className="ms-2 text-success">
                                                ({assegnaPreferenzeModal.selectedSezioni.size} selezionate per assegnazione)
                                            </span>
                                        )}
                                    </div>

                                    <div className="mappatura-add-sezioni-list" style={{ maxHeight: '400px', overflowY: 'auto', marginTop: '12px' }}>
                                        {assegnaPreferenzeModal.sezioniTrovate.map(sez => {
                                            const isDisabled = sez.is_assigned;
                                            return (
                                                <div
                                                    key={sez.id}
                                                    className={`mappatura-add-sezione-item ${assegnaPreferenzeModal.selectedSezioni.has(sez.id) ? 'selected' : ''} ${isDisabled ? 'disabled' : ''}`}
                                                    onClick={() => !isDisabled && toggleAssegnaPreferenzeSelection(sez.id)}
                                                    style={{ cursor: isDisabled ? 'not-allowed' : 'pointer', opacity: isDisabled ? 0.6 : 1 }}
                                                >
                                                    <input
                                                        type="checkbox"
                                                        checked={assegnaPreferenzeModal.selectedSezioni.has(sez.id)}
                                                        disabled={isDisabled}
                                                        onChange={() => {}}
                                                    />
                                                    <div style={{ flex: 1 }}>
                                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                            <span className="mappatura-add-sezione-num">Sez. {sez.numero}</span>
                                                            {sez.municipio && (
                                                                <span className="badge bg-secondary" style={{ fontSize: '0.7rem' }}>
                                                                    Mun. {sez.municipio}
                                                                </span>
                                                            )}
                                                            <span className="badge bg-info" style={{ fontSize: '0.65rem' }}>
                                                                {sez.match_type}
                                                            </span>
                                                        </div>
                                                        {sez.denominazione && (
                                                            <div className="mappatura-sezione-denominazione">{sez.denominazione}</div>
                                                        )}
                                                        {sez.indirizzo && (
                                                            <div className="mappatura-sezione-indirizzo">
                                                                <i className="fas fa-map-marker-alt me-1"></i>
                                                                {sez.indirizzo}
                                                            </div>
                                                        )}
                                                        {isDisabled && (
                                                            <div style={{ fontSize: '0.7rem', color: '#dc3545', marginTop: '4px' }}>
                                                                <i className="fas fa-exclamation-circle me-1"></i>
                                                                Già assegnata
                                                                {sez.effettivo && ` - Eff: ${sez.effettivo}`}
                                                                {sez.supplente && ` - Sup: ${sez.supplente}`}
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </>
                            )}
                        </>
                    )}
                </div>
            </ConfirmModal>
        </>
    );
}

export default Mappatura;
