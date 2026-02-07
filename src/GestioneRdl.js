import React, { useState, useEffect, useRef } from 'react';
import ConfirmModal from './ConfirmModal';

/**
 * Genera un link WhatsApp per un numero di telefono
 */
const getWhatsAppLink = (phone) => {
    if (!phone) return null;
    // Rimuovi spazi, trattini, parentesi
    const cleaned = phone.replace(/[\s\-\(\)]/g, '');
    // Se inizia con 3 (numero italiano mobile) aggiungi prefisso +39
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

    // Column mapping state
    const [mappingStep, setMappingStep] = useState(null); // null | 'mapping' | 'importing'
    const [csvFile, setCsvFile] = useState(null);
    const [csvColumns, setCsvColumns] = useState([]);
    const [requiredFields, setRequiredFields] = useState([]);
    const [optionalFields, setOptionalFields] = useState([]);
    const [columnMapping, setColumnMapping] = useState({});
    const [usingSavedMapping, setUsingSavedMapping] = useState(false);

    // Failed records correction modal
    const [showErrorModal, setShowErrorModal] = useState(false);
    const [failedRecords, setFailedRecords] = useState([]);
    const [editingRecords, setEditingRecords] = useState([]);
    const [comuniOptions, setComuniOptions] = useState({});
    const [userTerritory, setUserTerritory] = useState([]);

    // Territory filter states
    const [regioni, setRegioni] = useState([]);
    const [province, setProvince] = useState([]);
    const [comuni, setComuni] = useState([]);
    const [municipi, setMunicipi] = useState([]);
    const [regioneFilter, setRegioneFilter] = useState('');
    const [provinciaFilter, setProvinciaFilter] = useState('');
    const [comuneFilter, setComuneFilter] = useState('');
    const [municipioFilter, setMunicipioFilter] = useState('');
    const [showTerritoryFilters, setShowTerritoryFilters] = useState(true);

    // User territory from delegation chain
    const [territorioLabel, setTerritorioLabel] = useState('');

    // Modal states
    const [modal, setModal] = useState({
        show: false,
        type: null,
        targetId: null,
        targetName: ''
    });

    // Load territory filters and user info on mount
    useEffect(() => {
        loadUserTerritorio();
        loadTerritoryFilters();
    }, []);

    // Reload registrations when filters change or on mount
    useEffect(() => {
        loadRegistrations();
    }, [statusFilter, regioneFilter, provinciaFilter, comuneFilter, municipioFilter]);

    // Handle regione filter change
    useEffect(() => {
        if (regioneFilter) {
            loadProvince(regioneFilter);
        } else {
            setProvince([]);
            setProvinciaFilter('');
            setComuni([]);
            setComuneFilter('');
            setMunicipi([]);
            setMunicipioFilter('');
        }
    }, [regioneFilter]);

    // Handle provincia filter change
    useEffect(() => {
        if (provinciaFilter) {
            loadComuni(provinciaFilter);
        } else {
            setComuni([]);
            setComuneFilter('');
            setMunicipi([]);
            setMunicipioFilter('');
        }
    }, [provinciaFilter]);

    // Handle comune filter change
    useEffect(() => {
        if (comuneFilter) {
            loadMunicipi(comuneFilter);
        } else {
            setMunicipi([]);
            setMunicipioFilter('');
        }
    }, [comuneFilter]);

    const loadProvince = async (regioneId) => {
        // Load all data and filter by regione
        const result = await client.rdlRegistrations.list({});
        if (result.error) return;

        const allData = result.registrations || [];

        const provinceMap = new Map();
        allData.forEach(rdl => {
            if (rdl.regione_id === parseInt(regioneId) && rdl.provincia_id && rdl.provincia) {
                provinceMap.set(rdl.provincia_id, { id: rdl.provincia_id, nome: rdl.provincia });
            }
        });

        const provinceList = Array.from(provinceMap.values());
        setProvince(provinceList);

        // Auto-select if only one
        if (provinceList.length === 1 && !provinciaFilter) {
            setProvinciaFilter(provinceList[0].id);
        }
    };

    const loadComuni = async (provinciaId) => {
        // Load all data and filter by provincia
        const result = await client.rdlRegistrations.list({});
        if (result.error) return;

        const allData = result.registrations || [];

        const comuniMap = new Map();
        allData.forEach(rdl => {
            if (rdl.provincia_id === parseInt(provinciaId) && rdl.comune_id && rdl.comune) {
                comuniMap.set(rdl.comune_id, { id: rdl.comune_id, nome: rdl.comune });
            }
        });

        const comuniList = Array.from(comuniMap.values());
        setComuni(comuniList);

        // Auto-select if only one
        if (comuniList.length === 1 && !comuneFilter) {
            setComuneFilter(comuniList[0].id);
        }
    };

    const loadMunicipi = async (comuneId) => {
        // Load all data and filter by comune
        const result = await client.rdlRegistrations.list({});
        if (result.error) return;

        const allData = result.registrations || [];

        const municipiMap = new Map();
        allData.forEach(rdl => {
            if (rdl.comune_id === parseInt(comuneId) && rdl.municipio_id && rdl.municipio) {
                // Extract numero from "Municipio 15" format
                const match = rdl.municipio.match(/\d+/);
                if (match) {
                    const numero = parseInt(match[0]);
                    municipiMap.set(rdl.municipio_id, { id: rdl.municipio_id, numero });
                }
            }
        });

        const municipiList = Array.from(municipiMap.values());
        setMunicipi(municipiList);
        // Don't auto-select municipio - let user choose
    };

    const loadTerritoryFilters = async () => {
        // Load all registrations to extract unique territory values
        const result = await client.rdlRegistrations.list({});
        if (result.error) {
            setRegioni([]);
            return;
        }

        const allData = result.registrations || [];

        // Extract unique values using Maps to avoid duplicates
        const regioniMap = new Map(); // regione_id -> {id, nome}
        const provinceByRegione = new Map(); // regione_id -> Map(provincia_id -> {id, nome})
        const comuniByProvincia = new Map(); // provincia_id -> Map(comune_id -> {id, nome})
        const municipiByComune = new Map(); // comune_id -> Map(municipio_id -> {id, numero})

        allData.forEach(rdl => {
            // Build regioni map
            if (rdl.regione_id && rdl.regione) {
                regioniMap.set(rdl.regione_id, { id: rdl.regione_id, nome: rdl.regione });

                // Build province map
                if (rdl.provincia_id && rdl.provincia) {
                    if (!provinceByRegione.has(rdl.regione_id)) {
                        provinceByRegione.set(rdl.regione_id, new Map());
                    }
                    provinceByRegione.get(rdl.regione_id).set(rdl.provincia_id, {
                        id: rdl.provincia_id,
                        nome: rdl.provincia
                    });

                    // Build comuni map
                    if (rdl.comune_id && rdl.comune) {
                        if (!comuniByProvincia.has(rdl.provincia_id)) {
                            comuniByProvincia.set(rdl.provincia_id, new Map());
                        }
                        comuniByProvincia.get(rdl.provincia_id).set(rdl.comune_id, {
                            id: rdl.comune_id,
                            nome: rdl.comune
                        });

                        // Build municipi map
                        if (rdl.municipio_id && rdl.municipio) {
                            const match = rdl.municipio.match(/\d+/);
                            if (match) {
                                const numero = parseInt(match[0]);
                                if (!municipiByComune.has(rdl.comune_id)) {
                                    municipiByComune.set(rdl.comune_id, new Map());
                                }
                                municipiByComune.get(rdl.comune_id).set(rdl.municipio_id, {
                                    id: rdl.municipio_id,
                                    numero
                                });
                            }
                        }
                    }
                }
            }
        });

        // Convert to arrays
        const regioniList = Array.from(regioniMap.values());
        setRegioni(regioniList);

        // Auto-select if only one value at each level
        if (regioniList.length === 1) {
            const regione = regioniList[0];
            setRegioneFilter(regione.id);

            // Load province for this regione
            const provinceMap = provinceByRegione.get(regione.id);
            if (provinceMap) {
                const provinceList = Array.from(provinceMap.values());
                setProvince(provinceList);

                if (provinceList.length === 1) {
                    const provincia = provinceList[0];
                    setProvinciaFilter(provincia.id);

                    // Load comuni for this provincia
                    const comuniMap = comuniByProvincia.get(provincia.id);
                    if (comuniMap) {
                        const comuniList = Array.from(comuniMap.values());
                        setComuni(comuniList);

                        if (comuniList.length === 1) {
                            const comune = comuniList[0];
                            setComuneFilter(comune.id);

                            // Load municipi for this comune
                            const municipiMap = municipiByComune.get(comune.id);
                            if (municipiMap) {
                                const municipiList = Array.from(municipiMap.values());
                                setMunicipi(municipiList);
                                // Don't auto-select municipio - let user choose
                            }
                        }
                    }
                }
            }
        }
    };

    const loadUserTerritorio = async () => {
        try {
            const chain = await client.deleghe.miaCatena();
            if (chain.error) return;

            let label = '';

            // Extract territory from sub-delegations
            if (chain.sub_deleghe_ricevute && chain.sub_deleghe_ricevute.length > 0) {
                const subDelega = chain.sub_deleghe_ricevute[0];

                // Build territory label
                const parti = [];

                // Comuni
                if (subDelega.comuni && subDelega.comuni.length > 0) {
                    const comuniNames = subDelega.comuni.map(c => c.nome);
                    if (comuniNames.length <= 2) {
                        parti.push(comuniNames.join(', '));
                    } else {
                        parti.push(`${comuniNames[0]} (+${comuniNames.length - 1} comuni)`);
                    }
                }

                // Municipi
                if (subDelega.municipi && subDelega.municipi.length > 0) {
                    const municString = subDelega.municipi
                        .map(m => `Mun. ${toRoman(m)}`)
                        .join(', ');
                    if (parti.length > 0) {
                        parti[0] = `${parti[0]} - ${municString}`;
                    } else {
                        parti.push(municString);
                    }
                }

                label = parti.join(', ');
            } else if (chain.delega_ricevuta) {
                // Delegato di lista - show circoscrizione
                label = chain.delega_ricevuta.circoscrizione || 'Nazionale';
            }

            setTerritorioLabel(label);
        } catch (err) {
            console.error('Error loading user territory:', err);
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
            municipio: reg.municipio ? (typeof reg.municipio === 'string' ? parseInt(reg.municipio.replace('Municipio ', '')) : reg.municipio) : '',
            fuorisede: reg.fuorisede || false,
            comune_domicilio: reg.comune_domicilio || '',
            indirizzo_domicilio: reg.indirizzo_domicilio || '',
            seggio_preferenza: reg.seggio_preferenza || '',
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
        setMappingStep('analyzing');

        // Step 1: Analyze CSV
        const result = await client.rdlRegistrations.analyzeCSV(file);

        if (result.error) {
            setError(result.error);
            setMappingStep(null);
            if (fileInputRef.current) {
                fileInputRef.current.value = '';
            }
            return;
        }

        // Try to load saved mapping for this CSV structure
        const columns = result.columns || [];
        const savedMapping = getSavedMapping(columns);
        const mappingToUse = savedMapping || result.suggested_mapping || {};
        const hasSavedMapping = savedMapping !== null;

        // Show mapping interface
        setCsvFile(file);
        setCsvColumns(columns);
        setRequiredFields(result.required_fields || []);
        setOptionalFields(result.optional_fields || []);
        setColumnMapping(mappingToUse);
        setUsingSavedMapping(hasSavedMapping);
        setMappingStep('mapping');
    };

    const getSavedMapping = (columns) => {
        try {
            // Create a signature based on column names
            const signature = columns.slice().sort().join('|');
            const savedMappings = JSON.parse(localStorage.getItem('csvColumnMappings') || '{}');
            return savedMappings[signature] || null;
        } catch (err) {
            console.error('Error loading saved mapping:', err);
            return null;
        }
    };

    const saveMappingToLocalStorage = (columns, mapping) => {
        try {
            const signature = columns.slice().sort().join('|');
            const savedMappings = JSON.parse(localStorage.getItem('csvColumnMappings') || '{}');
            savedMappings[signature] = mapping;
            localStorage.setItem('csvColumnMappings', JSON.stringify(savedMappings));
        } catch (err) {
            console.error('Error saving mapping:', err);
        }
    };

    const handleConfirmMapping = async () => {
        if (!csvFile) return;

        setMappingStep('importing');

        const result = await client.rdlRegistrations.import(csvFile, columnMapping);

        if (result.error) {
            setError(result.error);
            setMappingStep(null);
        } else {
            // Save successful mapping to localStorage
            saveMappingToLocalStorage(csvColumns, columnMapping);

            setImportResult(result);
            loadRegistrations();

            // Show error modal if there are failed records
            if (result.failed_records && result.failed_records.length > 0) {
                setFailedRecords(result.failed_records);
                // Deep copy and convert dates to ISO format, add error to notes
                setEditingRecords(result.failed_records.map(r => ({
                    ...r,
                    data_nascita: convertDateToISO(r.data_nascita),
                    note_correzione: `Errore CSV: ${r.error_message}` +
                        (r.comune_seggio ? `\nValore originale: ${r.comune_seggio}` : '') +
                        (r.provincia_seggio ? ` (${r.provincia_seggio})` : '')
                })));
                setUserTerritory(result.user_territory || []);
                setShowErrorModal(true);
            }

            // Reset mapping
            setMappingStep(null);
            setCsvFile(null);
            setCsvColumns([]);
            setColumnMapping({});
            setUsingSavedMapping(false);

            if (fileInputRef.current) {
                fileInputRef.current.value = '';
            }
        }
    };

    const handleCancelMapping = () => {
        setMappingStep(null);
        setCsvFile(null);
        setCsvColumns([]);
        setColumnMapping({});
        setUsingSavedMapping(false);
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    const toggleExpand = (id) => {
        setExpandedId(expandedId === id ? null : id);
    };

    const convertDateToISO = (dateStr) => {
        if (!dateStr) return '';

        // Already in ISO format (YYYY-MM-DD)
        if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
            return dateStr;
        }

        // Italian format: DD/MM/YYYY or DD-MM-YYYY
        const match = dateStr.match(/^(\d{1,2})[-\/](\d{1,2})[-\/](\d{4})$/);
        if (match) {
            const [, day, month, year] = match;
            return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
        }

        return dateStr; // Return as-is if can't parse
    };

    const handleSearchComune = async (query, recordIndex) => {
        if (query.length < 2) return;

        const result = await client.rdlRegistrations.searchComuni(query);
        if (!result.error && result.comuni) {
            setComuniOptions({...comuniOptions, [recordIndex]: result.comuni});
        }
    };

    const handleUpdateRecord = (index, field, value) => {
        const updated = [...editingRecords];
        updated[index] = { ...updated[index], [field]: value };
        setEditingRecords(updated);
    };

    const handleSelectComune = (index, comune) => {
        const updated = [...editingRecords];
        const originalValue = failedRecords[index].comune_seggio;

        updated[index] = {
            ...updated[index],
            comune_seggio: comune.nome,
            comune_id: comune.id
        };

        // Add automatic note about the correction
        if (comune.nome !== originalValue) {
            const correctionNote = `\n→ Corretto in: ${comune.nome}`;
            // Append correction to existing note (which already has the error)
            if (!updated[index].note_correzione.includes('Corretto in:')) {
                updated[index].note_correzione = (updated[index].note_correzione || '') + correctionNote;
            }
        }

        setEditingRecords(updated);
        // Clear error for this field
        const errorFields = updated[index].error_fields || [];
        updated[index].error_fields = errorFields.filter(f => f !== 'comune_seggio');
    };

    const handleRetryRecords = async () => {
        const result = await client.rdlRegistrations.retry(editingRecords);

        if (result.error) {
            setError(result.error);
        } else {
            setImportResult({
                ...importResult,
                created: (importResult?.created || 0) + result.created,
                updated: (importResult?.updated || 0) + result.updated,
                errors: result.errors || []
            });
            loadRegistrations();
            setShowErrorModal(false);
            setFailedRecords([]);
            setEditingRecords([]);
        }
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
                    {territorioLabel && (
                        <span className="page-header-badge">
                            {territorioLabel}
                        </span>
                    )}
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
            {showImport && !mappingStep && (
                <div style={{
                    background: '#e3f2fd',
                    borderRadius: '8px',
                    padding: '12px',
                    marginBottom: '12px',
                    fontSize: '0.85rem'
                }}>
                    <div style={{ fontWeight: 600, marginBottom: '8px' }}>Import CSV</div>
                    <div style={{ marginBottom: '8px', color: '#666' }}>
                        Seleziona un file CSV da importare. Il sistema ti permetterà di mappare le colonne.
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
                            <div style={{ fontWeight: 500 }}>
                                {importResult.created} creati, {importResult.updated} aggiornati
                                {importResult.skipped > 0 && (
                                    <span style={{ color: '#6c757d', marginLeft: '8px' }}>
                                        ({importResult.skipped} skippati perché fuori dalla tua area)
                                    </span>
                                )}
                            </div>
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

            {/* Column Mapping Interface */}
            {mappingStep === 'mapping' && (
                <div className="card mb-3">
                    <div className="card-header bg-primary text-white">
                        <h5 className="mb-0">
                            <i className="fas fa-columns me-2"></i>
                            Mappa le colonne del CSV
                        </h5>
                    </div>
                    <div className="card-body">
                        {usingSavedMapping && (
                            <div className="alert alert-success mb-3" style={{ fontSize: '0.85rem' }}>
                                <i className="fas fa-check-circle me-2"></i>
                                <strong>Mapping salvato trovato!</strong> Le colonne sono state mappate automaticamente in base a un import precedente con la stessa struttura.
                            </div>
                        )}
                        <p className="text-muted mb-3">
                            Associa le colonne del tuo CSV ai campi richiesti. {usingSavedMapping ? 'Il mapping è stato caricato da un import precedente.' : 'Le mappature consigliate sono già selezionate.'}
                        </p>

                        {/* Required fields */}
                        <div className="mb-4">
                            <h6 className="text-danger">Campi obbligatori</h6>
                            <div style={{ display: 'grid', gap: '12px', gridTemplateColumns: '1fr 1fr' }}>
                                {requiredFields.map(field => (
                                    <div key={field.key}>
                                        <label className="form-label mb-1" style={{ fontSize: '0.85rem', fontWeight: 500 }}>
                                            {field.label} <span className="text-danger">*</span>
                                        </label>
                                        <select
                                            className="form-select form-select-sm"
                                            value={columnMapping[field.key] || ''}
                                            onChange={(e) => setColumnMapping({...columnMapping, [field.key]: e.target.value})}
                                        >
                                            <option value="">-- Seleziona colonna --</option>
                                            {csvColumns.map(col => (
                                                <option key={col} value={col}>{col}</option>
                                            ))}
                                        </select>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Optional fields */}
                        <div className="mb-3">
                            <h6 className="text-secondary">Campi opzionali</h6>
                            <div style={{ display: 'grid', gap: '12px', gridTemplateColumns: '1fr 1fr' }}>
                                {optionalFields.map(field => (
                                    <div key={field.key}>
                                        <label className="form-label mb-1" style={{ fontSize: '0.85rem', fontWeight: 500 }}>
                                            {field.label}
                                        </label>
                                        <select
                                            className="form-select form-select-sm"
                                            value={columnMapping[field.key] || ''}
                                            onChange={(e) => setColumnMapping({...columnMapping, [field.key]: e.target.value})}
                                        >
                                            <option value="">-- Non mappare --</option>
                                            {csvColumns.map(col => (
                                                <option key={col} value={col}>{col}</option>
                                            ))}
                                        </select>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="d-flex gap-2 mt-4">
                            <button
                                className="btn btn-success flex-grow-1"
                                onClick={handleConfirmMapping}
                                disabled={requiredFields.some(f => !columnMapping[f.key])}
                            >
                                <i className="fas fa-check me-2"></i>
                                Importa dati
                            </button>
                            <button
                                className="btn btn-secondary"
                                onClick={handleCancelMapping}
                            >
                                <i className="fas fa-times me-2"></i>
                                Annulla
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {mappingStep === 'analyzing' && (
                <div className="alert alert-info">
                    <i className="fas fa-spinner fa-spin me-2"></i>
                    Analisi CSV in corso...
                </div>
            )}

            {mappingStep === 'importing' && (
                <div className="alert alert-info">
                    <i className="fas fa-spinner fa-spin me-2"></i>
                    Importazione dati in corso...
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
                                /* Edit Mode - Complete with labels */
                                <div style={{ padding: '12px', background: '#f8f9fa' }}>
                                    <div style={{ display: 'grid', gap: '12px', gridTemplateColumns: '1fr 1fr' }}>
                                        {/* Dati anagrafici */}
                                        <div>
                                            <label className="form-label mb-1" style={{ fontSize: '0.8rem', fontWeight: 500 }}>Nome</label>
                                            <input
                                                type="text"
                                                className="form-control form-control-sm"
                                                value={editData.nome || ''}
                                                onChange={(e) => setEditData({ ...editData, nome: e.target.value })}
                                            />
                                        </div>
                                        <div>
                                            <label className="form-label mb-1" style={{ fontSize: '0.8rem', fontWeight: 500 }}>Cognome</label>
                                            <input
                                                type="text"
                                                className="form-control form-control-sm"
                                                value={editData.cognome || ''}
                                                onChange={(e) => setEditData({ ...editData, cognome: e.target.value })}
                                            />
                                        </div>
                                        <div style={{ gridColumn: '1 / -1' }}>
                                            <label className="form-label mb-1" style={{ fontSize: '0.8rem', fontWeight: 500 }}>Email</label>
                                            <input
                                                type="email"
                                                className="form-control form-control-sm"
                                                value={editData.email || ''}
                                                onChange={(e) => setEditData({ ...editData, email: e.target.value })}
                                            />
                                        </div>
                                        <div>
                                            <label className="form-label mb-1" style={{ fontSize: '0.8rem', fontWeight: 500 }}>Telefono</label>
                                            <input
                                                type="tel"
                                                className="form-control form-control-sm"
                                                value={editData.telefono || ''}
                                                onChange={(e) => setEditData({ ...editData, telefono: e.target.value })}
                                            />
                                        </div>
                                        <div>
                                            <label className="form-label mb-1" style={{ fontSize: '0.8rem', fontWeight: 500 }}>Data nascita</label>
                                            <input
                                                type="date"
                                                className="form-control form-control-sm"
                                                value={editData.data_nascita || ''}
                                                onChange={(e) => setEditData({ ...editData, data_nascita: e.target.value })}
                                            />
                                        </div>
                                        <div style={{ gridColumn: '1 / -1' }}>
                                            <label className="form-label mb-1" style={{ fontSize: '0.8rem', fontWeight: 500 }}>Comune nascita</label>
                                            <input
                                                type="text"
                                                className="form-control form-control-sm"
                                                value={editData.comune_nascita || ''}
                                                onChange={(e) => setEditData({ ...editData, comune_nascita: e.target.value })}
                                            />
                                        </div>

                                        {/* Residenza */}
                                        <div style={{ gridColumn: '1 / -1', marginTop: '4px', paddingTop: '8px', borderTop: '1px solid #dee2e6' }}>
                                            <strong style={{ fontSize: '0.85rem' }}>Residenza</strong>
                                        </div>
                                        <div style={{ gridColumn: '1 / -1' }}>
                                            <label className="form-label mb-1" style={{ fontSize: '0.8rem', fontWeight: 500 }}>Comune residenza</label>
                                            <input
                                                type="text"
                                                className="form-control form-control-sm"
                                                value={editData.comune_residenza || ''}
                                                onChange={(e) => setEditData({ ...editData, comune_residenza: e.target.value })}
                                            />
                                        </div>
                                        <div style={{ gridColumn: '1 / -1' }}>
                                            <label className="form-label mb-1" style={{ fontSize: '0.8rem', fontWeight: 500 }}>Indirizzo residenza</label>
                                            <input
                                                type="text"
                                                className="form-control form-control-sm"
                                                value={editData.indirizzo_residenza || ''}
                                                onChange={(e) => setEditData({ ...editData, indirizzo_residenza: e.target.value })}
                                            />
                                        </div>
                                        <div>
                                            <label className="form-label mb-1" style={{ fontSize: '0.8rem', fontWeight: 500 }}>Municipio</label>
                                            <input
                                                type="number"
                                                className="form-control form-control-sm"
                                                value={editData.municipio || ''}
                                                onChange={(e) => setEditData({ ...editData, municipio: e.target.value })}
                                                min="1"
                                                max="15"
                                            />
                                        </div>

                                        {/* Fuorisede */}
                                        <div style={{ gridColumn: '1 / -1', marginTop: '4px', paddingTop: '8px', borderTop: '1px solid #dee2e6' }}>
                                            <strong style={{ fontSize: '0.85rem' }}>Fuorisede</strong>
                                        </div>
                                        <div style={{ gridColumn: '1 / -1' }}>
                                            <div className="form-check">
                                                <input
                                                    type="checkbox"
                                                    className="form-check-input"
                                                    id="edit-fuorisede"
                                                    checked={editData.fuorisede || false}
                                                    onChange={(e) => setEditData({ ...editData, fuorisede: e.target.checked })}
                                                />
                                                <label className="form-check-label" htmlFor="edit-fuorisede" style={{ fontSize: '0.8rem' }}>
                                                    Lavora o studia in un comune diverso dalla residenza
                                                </label>
                                            </div>
                                        </div>
                                        {editData.fuorisede && (
                                            <>
                                                <div style={{ gridColumn: '1 / -1' }}>
                                                    <label className="form-label mb-1" style={{ fontSize: '0.8rem', fontWeight: 500 }}>Comune domicilio</label>
                                                    <input
                                                        type="text"
                                                        className="form-control form-control-sm"
                                                        value={editData.comune_domicilio || ''}
                                                        onChange={(e) => setEditData({ ...editData, comune_domicilio: e.target.value })}
                                                    />
                                                </div>
                                                <div style={{ gridColumn: '1 / -1' }}>
                                                    <label className="form-label mb-1" style={{ fontSize: '0.8rem', fontWeight: 500 }}>Indirizzo domicilio</label>
                                                    <input
                                                        type="text"
                                                        className="form-control form-control-sm"
                                                        value={editData.indirizzo_domicilio || ''}
                                                        onChange={(e) => setEditData({ ...editData, indirizzo_domicilio: e.target.value })}
                                                    />
                                                </div>
                                            </>
                                        )}

                                        {/* Preferenze */}
                                        <div style={{ gridColumn: '1 / -1', marginTop: '4px', paddingTop: '8px', borderTop: '1px solid #dee2e6' }}>
                                            <strong style={{ fontSize: '0.85rem' }}>Preferenze</strong>
                                        </div>
                                        <div style={{ gridColumn: '1 / -1' }}>
                                            <label className="form-label mb-1" style={{ fontSize: '0.8rem', fontWeight: 500 }}>Seggio preferenza</label>
                                            <input
                                                type="text"
                                                className="form-control form-control-sm"
                                                value={editData.seggio_preferenza || ''}
                                                onChange={(e) => setEditData({ ...editData, seggio_preferenza: e.target.value })}
                                            />
                                        </div>
                                        <div style={{ gridColumn: '1 / -1' }}>
                                            <label className="form-label mb-1" style={{ fontSize: '0.8rem', fontWeight: 500 }}>Note</label>
                                            <textarea
                                                className="form-control form-control-sm"
                                                rows="2"
                                                value={editData.notes || ''}
                                                onChange={(e) => setEditData({ ...editData, notes: e.target.value })}
                                            />
                                        </div>
                                    </div>
                                    <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
                                        <button className="btn btn-success btn-sm" onClick={handleSaveEdit} style={{ flex: 1 }}>
                                            <i className="fas fa-save me-1"></i>
                                            Salva
                                        </button>
                                        <button className="btn btn-secondary btn-sm" onClick={handleCancelEdit} style={{ flex: 1 }}>
                                            <i className="fas fa-times me-1"></i>
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
                                        <div style={{ marginBottom: '4px' }}>
                                            <i className="fas fa-envelope me-1"></i>
                                            {reg.email}
                                            {reg.telefono && (
                                                <span className="ms-3">
                                                    <i className="fas fa-phone me-1"></i>
                                                    <a
                                                        href={getWhatsAppLink(reg.telefono)}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        style={{ color: '#25D366', textDecoration: 'none' }}
                                                        title="Contatta su WhatsApp"
                                                    >
                                                        {reg.telefono}
                                                    </a>
                                                    <button
                                                        onClick={() => downloadVCard(`${reg.cognome} ${reg.nome}`, reg.telefono, reg.email)}
                                                        className="btn btn-link btn-sm p-0 ms-2"
                                                        style={{ fontSize: '0.8rem', color: '#6c757d' }}
                                                        title="Salva contatto"
                                                    >
                                                        <i className="fas fa-user-plus"></i>
                                                    </button>
                                                </span>
                                            )}
                                        </div>
                                        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                                            <span>
                                                <i className="fas fa-map-marker-alt me-1"></i>
                                                <strong>{reg.comune_residenza || reg.comune}</strong>
                                                {reg.municipio && ` - ${reg.municipio}`}
                                            </span>
                                            {reg.data_nascita && (
                                                <span>
                                                    <i className="fas fa-birthday-cake me-1"></i>
                                                    {formatDate(reg.data_nascita)}
                                                    {reg.comune_nascita && ` (${reg.comune_nascita})`}
                                                </span>
                                            )}
                                            {reg.seggio_preferenza && (
                                                <span>
                                                    <i className="fas fa-star me-1" style={{ color: '#ffc107' }}></i>
                                                    Sez. {reg.seggio_preferenza}
                                                </span>
                                            )}
                                        </div>
                                        {reg.fuorisede && reg.comune_domicilio && (
                                            <div style={{ marginTop: '4px', fontSize: '0.75rem' }}>
                                                <i className="fas fa-suitcase me-1"></i>
                                                <strong>Domicilio:</strong> {reg.comune_domicilio}
                                                {reg.indirizzo_domicilio && `, ${reg.indirizzo_domicilio}`}
                                            </div>
                                        )}
                                        {reg.notes && (
                                            <div style={{ marginTop: '4px', fontStyle: 'italic', fontSize: '0.75rem' }}>
                                                <i className="fas fa-sticky-note me-1"></i>
                                                {reg.notes}
                                            </div>
                                        )}
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
                                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
                                                    <div style={{ gridColumn: '1 / -1' }}>
                                                        <span style={{ color: '#6c757d' }}>Email:</span> {reg.email}
                                                    </div>
                                                    <div>
                                                        <span style={{ color: '#6c757d' }}>Telefono:</span>{' '}
                                                        {reg.telefono ? (
                                                            <>
                                                                <a
                                                                    href={getWhatsAppLink(reg.telefono)}
                                                                    target="_blank"
                                                                    rel="noopener noreferrer"
                                                                    style={{ color: '#25D366', textDecoration: 'none' }}
                                                                    title="Contatta su WhatsApp"
                                                                >
                                                                    {reg.telefono}
                                                                </a>
                                                                <button
                                                                    onClick={() => downloadVCard(`${reg.cognome} ${reg.nome}`, reg.telefono, reg.email)}
                                                                    className="btn btn-link btn-sm p-0 ms-1"
                                                                    style={{ fontSize: '0.7rem', color: '#6c757d' }}
                                                                    title="Salva contatto"
                                                                >
                                                                    <i className="fas fa-user-plus"></i>
                                                                </button>
                                                            </>
                                                        ) : '-'}
                                                    </div>
                                                    <div>
                                                        <span style={{ color: '#6c757d' }}>Municipio:</span> {reg.municipio || '-'}
                                                    </div>
                                                    <div><span style={{ color: '#6c757d' }}>Nato a:</span> {reg.comune_nascita || '-'}</div>
                                                    <div><span style={{ color: '#6c757d' }}>il:</span> {formatDate(reg.data_nascita) || '-'}</div>
                                                    <div style={{ gridColumn: '1 / -1', marginTop: '4px', paddingTop: '4px', borderTop: '1px solid #e9ecef' }}>
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

            {/* Error Correction Modal */}
            {showErrorModal && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: 'rgba(0,0,0,0.5)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 9999,
                    padding: '20px'
                }}>
                    <div style={{
                        background: 'white',
                        borderRadius: '8px',
                        maxWidth: '900px',
                        width: '100%',
                        maxHeight: '90vh',
                        display: 'flex',
                        flexDirection: 'column',
                        boxShadow: '0 4px 20px rgba(0,0,0,0.2)'
                    }}>
                        {/* Modal Header */}
                        <div style={{
                            padding: '16px 20px',
                            borderBottom: '1px solid #dee2e6',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            background: '#f8f9fa'
                        }}>
                            <h5 style={{ margin: 0, fontSize: '1.1rem' }}>
                                <i className="fas fa-exclamation-triangle text-warning me-2"></i>
                                Correggi Record in Errore ({failedRecords.length})
                            </h5>
                            <button
                                onClick={() => setShowErrorModal(false)}
                                style={{
                                    background: 'none',
                                    border: 'none',
                                    fontSize: '1.5rem',
                                    cursor: 'pointer',
                                    color: '#6c757d'
                                }}
                            >
                                &times;
                            </button>
                        </div>

                        {/* Modal Body */}
                        <div style={{
                            padding: '20px',
                            overflowY: 'auto',
                            flex: 1
                        }}>
                            <p style={{ marginBottom: '16px', color: '#6c757d', fontSize: '0.9rem' }}>
                                I seguenti record non sono stati importati a causa di errori. Correggi i campi evidenziati in rosso e riprova.
                            </p>

                            {/* User Territory Info */}
                            {userTerritory.length > 0 && (
                                <div style={{
                                    background: '#e7f3ff',
                                    border: '1px solid #b6d4fe',
                                    borderRadius: '6px',
                                    padding: '12px',
                                    marginBottom: '16px',
                                    fontSize: '0.85rem'
                                }}>
                                    <div style={{ fontWeight: 600, marginBottom: '6px' }}>
                                        <i className="fas fa-info-circle me-2"></i>
                                        La tua area di competenza:
                                    </div>
                                    <ul style={{ margin: 0, paddingLeft: '20px' }}>
                                        {userTerritory.map((territory, idx) => (
                                            <li key={idx}>{territory}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {editingRecords.map((record, index) => (
                                <div key={index} style={{
                                    border: '2px solid #ffc107',
                                    borderRadius: '8px',
                                    padding: '16px',
                                    marginBottom: '16px',
                                    background: '#fffbf0'
                                }}>
                                    {/* Record Header */}
                                    <div style={{
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        marginBottom: '12px',
                                        paddingBottom: '8px',
                                        borderBottom: '1px solid #ffc107'
                                    }}>
                                        <strong style={{ fontSize: '0.95rem' }}>
                                            Riga {record.row_number}: {record.nome} {record.cognome}
                                        </strong>
                                        <span style={{
                                            background: '#dc3545',
                                            color: 'white',
                                            padding: '2px 8px',
                                            borderRadius: '4px',
                                            fontSize: '0.75rem'
                                        }}>
                                            {record.error_message}
                                        </span>
                                    </div>

                                    {/* Record Fields */}
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                                        <div>
                                            <label style={{ fontSize: '0.8rem', fontWeight: 500, display: 'block', marginBottom: '4px' }}>
                                                Email *
                                            </label>
                                            <input
                                                type="email"
                                                className="form-control form-control-sm"
                                                value={record.email || ''}
                                                onChange={(e) => handleUpdateRecord(index, 'email', e.target.value)}
                                                style={{
                                                    borderColor: record.error_fields?.includes('email') ? '#dc3545' : undefined,
                                                    borderWidth: record.error_fields?.includes('email') ? '2px' : undefined
                                                }}
                                            />
                                        </div>

                                        <div>
                                            <label style={{ fontSize: '0.8rem', fontWeight: 500, display: 'block', marginBottom: '4px' }}>
                                                Telefono *
                                            </label>
                                            <input
                                                type="tel"
                                                className="form-control form-control-sm"
                                                value={record.telefono || ''}
                                                onChange={(e) => handleUpdateRecord(index, 'telefono', e.target.value)}
                                                style={{
                                                    borderColor: record.error_fields?.includes('telefono') ? '#dc3545' : undefined,
                                                    borderWidth: record.error_fields?.includes('telefono') ? '2px' : undefined
                                                }}
                                            />
                                        </div>

                                        <div>
                                            <label style={{ fontSize: '0.8rem', fontWeight: 500, display: 'block', marginBottom: '4px' }}>
                                                Nome *
                                            </label>
                                            <input
                                                type="text"
                                                className="form-control form-control-sm"
                                                value={record.nome || ''}
                                                onChange={(e) => handleUpdateRecord(index, 'nome', e.target.value)}
                                                style={{
                                                    borderColor: record.error_fields?.includes('nome') ? '#dc3545' : undefined,
                                                    borderWidth: record.error_fields?.includes('nome') ? '2px' : undefined
                                                }}
                                            />
                                        </div>

                                        <div>
                                            <label style={{ fontSize: '0.8rem', fontWeight: 500, display: 'block', marginBottom: '4px' }}>
                                                Cognome *
                                            </label>
                                            <input
                                                type="text"
                                                className="form-control form-control-sm"
                                                value={record.cognome || ''}
                                                onChange={(e) => handleUpdateRecord(index, 'cognome', e.target.value)}
                                                style={{
                                                    borderColor: record.error_fields?.includes('cognome') ? '#dc3545' : undefined,
                                                    borderWidth: record.error_fields?.includes('cognome') ? '2px' : undefined
                                                }}
                                            />
                                        </div>

                                        <div style={{ gridColumn: '1 / -1' }}>
                                            <label style={{ fontSize: '0.8rem', fontWeight: 500, display: 'block', marginBottom: '4px' }}>
                                                Comune Seggio *
                                                {record.error_fields?.includes('comune_seggio') && (
                                                    <span style={{ color: '#dc3545', fontSize: '0.75rem', marginLeft: '8px' }}>
                                                        ← {record.error_message}
                                                    </span>
                                                )}
                                            </label>
                                            {failedRecords[index] && failedRecords[index].comune_seggio && (
                                                <div style={{
                                                    background: '#fff3cd',
                                                    border: '1px solid #ffc107',
                                                    borderRadius: '4px',
                                                    padding: '6px 8px',
                                                    marginBottom: '6px',
                                                    fontSize: '0.75rem',
                                                    fontFamily: 'monospace'
                                                }}>
                                                    <strong>Valore CSV originale:</strong> <span style={{ color: '#dc3545' }}>{failedRecords[index].comune_seggio}</span>
                                                    {failedRecords[index].provincia_seggio && (
                                                        <span style={{ marginLeft: '8px' }}>
                                                            Provincia: <span style={{ color: '#0d6efd' }}>{failedRecords[index].provincia_seggio}</span>
                                                        </span>
                                                    )}
                                                </div>
                                            )}
                                            <div style={{ position: 'relative' }}>
                                                <input
                                                    type="text"
                                                    className="form-control form-control-sm"
                                                    value={record.comune_seggio || ''}
                                                    onChange={(e) => {
                                                        handleUpdateRecord(index, 'comune_seggio', e.target.value);
                                                        handleSearchComune(e.target.value, index);
                                                    }}
                                                    placeholder="Scrivi per cercare..."
                                                    style={{
                                                        borderColor: record.error_fields?.includes('comune_seggio') ? '#dc3545' : undefined,
                                                        borderWidth: record.error_fields?.includes('comune_seggio') ? '2px' : undefined
                                                    }}
                                                />
                                                {comuniOptions[index] && comuniOptions[index].length > 0 && (
                                                    <div style={{
                                                        position: 'absolute',
                                                        top: '100%',
                                                        left: 0,
                                                        right: 0,
                                                        background: 'white',
                                                        border: '1px solid #dee2e6',
                                                        borderRadius: '4px',
                                                        marginTop: '2px',
                                                        maxHeight: '200px',
                                                        overflowY: 'auto',
                                                        zIndex: 1000,
                                                        boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                                                    }}>
                                                        {comuniOptions[index].map((comune) => (
                                                            <div
                                                                key={comune.id}
                                                                onClick={() => {
                                                                    handleSelectComune(index, comune);
                                                                    setComuniOptions({...comuniOptions, [index]: []});
                                                                }}
                                                                style={{
                                                                    padding: '8px 12px',
                                                                    cursor: 'pointer',
                                                                    fontSize: '0.85rem',
                                                                    borderBottom: '1px solid #f0f0f0'
                                                                }}
                                                                onMouseEnter={(e) => e.target.style.background = '#f8f9fa'}
                                                                onMouseLeave={(e) => e.target.style.background = 'white'}
                                                            >
                                                                {comune.nome} ({comune.provincia})
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        </div>

                                        <div>
                                            <label style={{ fontSize: '0.8rem', fontWeight: 500, display: 'block', marginBottom: '4px' }}>
                                                Data Nascita *
                                                {record.error_fields?.includes('data_nascita') && (
                                                    <span style={{ color: '#dc3545', fontSize: '0.75rem', marginLeft: '8px' }}>
                                                        Formato errato
                                                    </span>
                                                )}
                                            </label>
                                            <input
                                                type="date"
                                                className="form-control form-control-sm"
                                                value={record.data_nascita || ''}
                                                onChange={(e) => handleUpdateRecord(index, 'data_nascita', e.target.value)}
                                                style={{
                                                    borderColor: record.error_fields?.includes('data_nascita') ? '#dc3545' : undefined,
                                                    borderWidth: record.error_fields?.includes('data_nascita') ? '2px' : undefined
                                                }}
                                            />
                                            {record.data_nascita && (
                                                <small style={{ color: '#6c757d', fontSize: '0.7rem', display: 'block', marginTop: '2px' }}>
                                                    {new Date(record.data_nascita).toLocaleDateString('it-IT')}
                                                </small>
                                            )}
                                        </div>

                                        <div>
                                            <label style={{ fontSize: '0.8rem', fontWeight: 500, display: 'block', marginBottom: '4px' }}>
                                                Comune Nascita *
                                            </label>
                                            <input
                                                type="text"
                                                className="form-control form-control-sm"
                                                value={record.comune_nascita || ''}
                                                onChange={(e) => handleUpdateRecord(index, 'comune_nascita', e.target.value)}
                                                style={{
                                                    borderColor: record.error_fields?.includes('comune_nascita') ? '#dc3545' : undefined,
                                                    borderWidth: record.error_fields?.includes('comune_nascita') ? '2px' : undefined
                                                }}
                                            />
                                        </div>
                                    </div>

                                    {/* Note di correzione */}
                                    <div style={{
                                        marginTop: '12px',
                                        paddingTop: '12px',
                                        borderTop: '1px solid #ffc107'
                                    }}>
                                        <label style={{ fontSize: '0.8rem', fontWeight: 500, display: 'block', marginBottom: '4px' }}>
                                            <i className="fas fa-comment me-2"></i>
                                            Note di Correzione
                                        </label>
                                        <textarea
                                            className="form-control form-control-sm"
                                            rows="3"
                                            value={record.note_correzione || ''}
                                            onChange={(e) => handleUpdateRecord(index, 'note_correzione', e.target.value)}
                                            placeholder="Es: aveva scritto CERRRRON-e con 4 R, ho corretto in Serrone"
                                            style={{
                                                fontSize: '0.85rem',
                                                fontFamily: 'monospace'
                                            }}
                                        />
                                        <small style={{ color: '#6c757d', fontSize: '0.75rem', display: 'block', marginTop: '4px' }}>
                                            <i className="fas fa-info-circle me-1"></i>
                                            Queste note verranno salvate nel campo "Note" della registrazione per riferimento futuro.
                                        </small>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Modal Footer */}
                        <div style={{
                            padding: '16px 20px',
                            borderTop: '1px solid #dee2e6',
                            display: 'flex',
                            justifyContent: 'flex-end',
                            gap: '8px',
                            background: '#f8f9fa'
                        }}>
                            <button
                                className="btn btn-secondary"
                                onClick={() => setShowErrorModal(false)}
                            >
                                Annulla
                            </button>
                            <button
                                className="btn btn-success"
                                onClick={handleRetryRecords}
                            >
                                <i className="fas fa-check me-2"></i>
                                Salva e Riprova ({editingRecords.length} record)
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}

export default GestioneRdl;
