import React, { useState, useEffect } from 'react';
import ConfirmModal from './ConfirmModal';

/**
 * Gerarchia delle deleghe per la designazione dei Rappresentanti di Lista.
 *
 * PER ELEZIONI (Art. 25 DPR 361/1957):
 * PARTITO (M5S)
 *     ↓ nomina
 * DELEGATO DI LISTA (deputati, senatori, consiglieri)
 *     ↓ sub-delega (firma autenticata)
 * SUB-DELEGATO (per territorio specifico)
 *     ↓ designa
 * RDL (Effettivo + Supplente) per sezione
 *
 * PER REFERENDUM:
 * COMITATO PROMOTORE / PARTITO
 *     ↓ mandato autenticato da notaio
 * DELEGATO (del comitato o del partito)
 *     ↓ designa (può anche sub-delegare)
 * RAPPRESENTANTE DI LISTA (Effettivo + Supplente) per sezione
 *
 * Nei referendum, i promotori o il presidente/segretario del partito
 * possono anche designare direttamente i rappresentanti.
 */

function GestioneDeleghe({ client, user, consultazione, setError, initialTab }) {
    const [loading, setLoading] = useState(true);
    const [catena, setCatena] = useState(null);
    const [activeTab, setActiveTab] = useState(initialTab || 'catena'); // 'catena' | 'sub-deleghe' | 'conferma' | 'campagne'

    // Bozze da confermare
    const [bozze, setBozze] = useState([]);
    const [loadingBozze, setLoadingBozze] = useState(false);

    // Form sub-delega
    const [showSubDelegaForm, setShowSubDelegaForm] = useState(false);
    const [editingSubDelega, setEditingSubDelega] = useState(null); // ID della sub-delega in modifica
    const [subDelegaForm, setSubDelegaForm] = useState({
        cognome: '', nome: '', luogo_nascita: '', data_nascita: '',
        domicilio: '', tipo_documento: '', numero_documento: '',
        email: '', telefono: '', comuni_ids: [], municipi: []
    });
    const [saving, setSaving] = useState(false);

    // Modal conferma
    const [confirmModal, setConfirmModal] = useState({ show: false, title: '', message: '', onConfirm: null });

    // Campagne di reclutamento
    const [campagne, setCampagne] = useState([]);
    const [loadingCampagne, setLoadingCampagne] = useState(false);
    const [showCampagnaForm, setShowCampagnaForm] = useState(false);
    const [editingCampagna, setEditingCampagna] = useState(null);
    const [campagnaForm, setCampagnaForm] = useState({
        nome: '', slug: '', descrizione: '',
        data_apertura: '', data_chiusura: '',
        regioni_ids: [], province_ids: [], comuni_ids: [],
        richiedi_approvazione: true, max_registrazioni: '',
        messaggio_conferma: ''
    });
    const [savingCampagna, setSavingCampagna] = useState(false);

    // Territorio per campagna
    const [regioni, setRegioni] = useState([]);
    const [province, setProvince] = useState([]);
    const [comuni, setComuni] = useState([]);

    useEffect(() => {
        loadCatena();
        loadRegioni();
    }, [consultazione]);

    // Aggiorna il tab attivo quando cambia initialTab (navigazione dal menu)
    useEffect(() => {
        if (initialTab) {
            setActiveTab(initialTab);
        }
    }, [initialTab]);

    // Carica bozze quando si apre il tab conferma
    useEffect(() => {
        if (activeTab === 'conferma') {
            loadBozze();
        }
        if (activeTab === 'campagne') {
            loadCampagne();
        }
    }, [activeTab]);

    // Carica territorio per form campagna
    const loadRegioni = async () => {
        try {
            const result = await client.territorio.regioni();
            if (!result?.error && Array.isArray(result)) {
                setRegioni(result);
            }
        } catch (err) {
            console.error('Errore caricamento regioni:', err);
        }
    };

    const loadProvince = async (regioneId) => {
        try {
            const result = await client.territorio.province(regioneId);
            if (!result?.error && Array.isArray(result)) {
                setProvince(result);
            }
        } catch (err) {
            console.error('Errore caricamento province:', err);
        }
    };

    const loadComuni = async (provinciaId) => {
        try {
            const result = await client.territorio.comuni(provinciaId);
            if (!result?.error && Array.isArray(result)) {
                setComuni(result);
            }
        } catch (err) {
            console.error('Errore caricamento comuni:', err);
        }
    };

    // Campagne
    const loadCampagne = async () => {
        setLoadingCampagne(true);
        try {
            const result = await client.deleghe.campagne.list(consultazione?.id);
            if (result?.error) {
                setCampagne([]);
            } else {
                setCampagne(Array.isArray(result) ? result : result?.results || []);
            }
        } catch (err) {
            console.error('Errore caricamento campagne:', err);
            setCampagne([]);
        }
        setLoadingCampagne(false);
    };

    const generateSlug = (nome) => {
        return nome
            .toLowerCase()
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '') // rimuove accenti
            .replace(/[^a-z0-9\s-]/g, '')    // rimuove caratteri speciali
            .replace(/\s+/g, '-')             // spazi -> trattini
            .replace(/-+/g, '-')              // rimuove trattini doppi
            .substring(0, 100);
    };

    const handleCampagnaFormChange = (field, value) => {
        const newForm = { ...campagnaForm, [field]: value };
        // Auto-genera slug dal nome
        if (field === 'nome' && !editingCampagna) {
            newForm.slug = generateSlug(value);
        }
        setCampagnaForm(newForm);
    };

    const resetCampagnaForm = () => {
        setEditingCampagna(null);
        setCampagnaForm({
            nome: '', slug: '', descrizione: '',
            data_apertura: '', data_chiusura: '',
            regioni_ids: [], province_ids: [], comuni_ids: [],
            richiedi_approvazione: true, max_registrazioni: '',
            messaggio_conferma: ''
        });
        setProvince([]);
        setComuni([]);
    };

    const handleEditCampagna = (campagna) => {
        setEditingCampagna(campagna.id);
        setCampagnaForm({
            nome: campagna.nome || '',
            slug: campagna.slug || '',
            descrizione: campagna.descrizione || '',
            data_apertura: campagna.data_apertura ? campagna.data_apertura.substring(0, 16) : '',
            data_chiusura: campagna.data_chiusura ? campagna.data_chiusura.substring(0, 16) : '',
            regioni_ids: campagna.territorio_regioni?.map(r => r.id) || [],
            province_ids: campagna.territorio_province?.map(p => p.id) || [],
            comuni_ids: campagna.territorio_comuni?.map(c => c.id) || [],
            richiedi_approvazione: campagna.richiedi_approvazione ?? true,
            max_registrazioni: campagna.max_registrazioni || '',
            messaggio_conferma: campagna.messaggio_conferma || ''
        });
        setShowCampagnaForm(true);
    };

    const handleSaveCampagna = async (e) => {
        e.preventDefault();
        if (!campagnaForm.nome || !campagnaForm.data_apertura || !campagnaForm.data_chiusura) {
            setError('Compila tutti i campi obbligatori');
            return;
        }

        setSavingCampagna(true);
        try {
            const payload = {
                nome: campagnaForm.nome,
                slug: campagnaForm.slug || generateSlug(campagnaForm.nome),
                descrizione: campagnaForm.descrizione,
                data_apertura: campagnaForm.data_apertura,
                data_chiusura: campagnaForm.data_chiusura,
                territorio_regioni_ids: campagnaForm.regioni_ids,
                territorio_province_ids: campagnaForm.province_ids,
                territorio_comuni_ids: campagnaForm.comuni_ids,
                richiedi_approvazione: campagnaForm.richiedi_approvazione,
                max_registrazioni: campagnaForm.max_registrazioni ? parseInt(campagnaForm.max_registrazioni) : null,
                messaggio_conferma: campagnaForm.messaggio_conferma,
                consultazione_id: consultazione?.id
            };

            let result;
            if (editingCampagna) {
                result = await client.deleghe.campagne.update(editingCampagna, payload);
            } else {
                result = await client.deleghe.campagne.create(payload);
            }

            if (result?.error) {
                setError(result.error);
            } else {
                setShowCampagnaForm(false);
                resetCampagnaForm();
                loadCampagne();
            }
        } catch (err) {
            setError(editingCampagna ? 'Errore nella modifica della campagna' : 'Errore nella creazione della campagna');
        }
        setSavingCampagna(false);
    };

    const handleAttivaCampagna = (campagna) => {
        setConfirmModal({
            show: true,
            title: 'Attiva Campagna',
            message: `Sei sicuro di voler attivare la campagna "${campagna.nome}"? Una volta attiva, sarà accessibile pubblicamente.`,
            onConfirm: async () => {
                try {
                    const result = await client.deleghe.campagne.attiva(campagna.id);
                    if (result?.error) {
                        setError(result.error);
                    } else {
                        loadCampagne();
                    }
                } catch (err) {
                    setError('Errore nell\'attivazione della campagna');
                }
                setConfirmModal({ show: false });
            }
        });
    };

    const handleChiudiCampagna = (campagna) => {
        setConfirmModal({
            show: true,
            title: 'Chiudi Campagna',
            message: `Sei sicuro di voler chiudere la campagna "${campagna.nome}"? Il link non sarà più accessibile.`,
            onConfirm: async () => {
                try {
                    const result = await client.deleghe.campagne.chiudi(campagna.id);
                    if (result?.error) {
                        setError(result.error);
                    } else {
                        loadCampagne();
                    }
                } catch (err) {
                    setError('Errore nella chiusura della campagna');
                }
                setConfirmModal({ show: false });
            }
        });
    };

    const handleDeleteCampagna = (campagna) => {
        setConfirmModal({
            show: true,
            title: 'Elimina Campagna',
            message: `Sei sicuro di voler eliminare la campagna "${campagna.nome}"? Questa azione non può essere annullata.`,
            onConfirm: async () => {
                try {
                    const result = await client.deleghe.campagne.delete(campagna.id);
                    if (result?.error) {
                        setError(result.error);
                    } else {
                        loadCampagne();
                    }
                } catch (err) {
                    setError('Errore nell\'eliminazione della campagna');
                }
                setConfirmModal({ show: false });
            }
        });
    };

    const handleCopiaLink = (campagna) => {
        const url = `${window.location.origin}/campagna/${campagna.slug}`;
        navigator.clipboard.writeText(url).then(() => {
            // Feedback visivo opzionale
            alert(`Link copiato: ${url}`);
        }).catch(() => {
            setError('Errore nella copia del link');
        });
    };

    const loadBozze = async () => {
        setLoadingBozze(true);
        try {
            const result = await client.deleghe.designazioni.bozzeDaConfermare();
            if (result?.error) {
                setBozze([]);
            } else {
                setBozze(result || []);
            }
        } catch (err) {
            console.log('Errore caricamento bozze:', err);
            setBozze([]);
        }
        setLoadingBozze(false);
    };

    const handleConfermaBozza = async (bozza) => {
        setConfirmModal({
            show: true,
            title: 'Conferma Designazione',
            message: `Stai per confermare la designazione di ${bozza.cognome} ${bozza.nome} come ${bozza.ruolo_display} nella sezione ${bozza.sezione_numero} (${bozza.sezione_comune}).`,
            onConfirm: async () => {
                try {
                    const result = await client.deleghe.designazioni.conferma(bozza.id);
                    if (result?.error) {
                        setError(result.error);
                    } else {
                        loadBozze();
                        loadCatena();
                    }
                } catch (err) {
                    setError('Errore nella conferma');
                }
                setConfirmModal({ show: false });
            }
        });
    };

    const handleRifiutaBozza = async (bozza) => {
        setConfirmModal({
            show: true,
            title: 'Rifiuta Designazione',
            message: `Sei sicuro di voler rifiutare la designazione di ${bozza.cognome} ${bozza.nome}?`,
            onConfirm: async () => {
                try {
                    const result = await client.deleghe.designazioni.rifiuta(bozza.id, 'Rifiutata dal delegato');
                    if (result?.error) {
                        setError(result.error);
                    } else {
                        loadBozze();
                    }
                } catch (err) {
                    setError('Errore nel rifiuto');
                }
                setConfirmModal({ show: false });
            }
        });
    };

    const loadCatena = async () => {
        setLoading(true);
        try {
            const result = await client.deleghe.miaCatena(consultazione?.id);
            if (result?.error) {
                // API non disponibile, mostra stato vuoto
                setCatena({
                    is_delegato: false,
                    is_sub_delegato: false,
                    deleghe_lista: [],
                    sub_deleghe_ricevute: [],
                    sub_deleghe_fatte: [],
                    designazioni_fatte: []
                });
            } else {
                setCatena(result);
            }
        } catch (err) {
            console.log('API deleghe non disponibile, uso dati mock');
            // Mock per sviluppo
            setCatena({
                is_delegato: false,
                is_sub_delegato: false,
                deleghe_lista: [],
                sub_deleghe_ricevute: [],
                sub_deleghe_fatte: [],
                designazioni_fatte: []
            });
        }
        setLoading(false);
    };

    const handleSaveSubDelega = async (e) => {
        e.preventDefault();
        if (!subDelegaForm.cognome || !subDelegaForm.nome || !subDelegaForm.email) {
            setError('Compila tutti i campi obbligatori');
            return;
        }

        setSaving(true);
        try {
            let result;
            if (editingSubDelega) {
                // Modifica sub-delega esistente
                result = await client.deleghe.subDeleghe.update(editingSubDelega, subDelegaForm);
            } else {
                // Crea nuova sub-delega
                result = await client.deleghe.subDeleghe.create(subDelegaForm);
            }

            if (result?.error) {
                setError(result.error);
            } else {
                setShowSubDelegaForm(false);
                resetSubDelegaForm();
                loadCatena();
            }
        } catch (err) {
            setError(editingSubDelega ? 'Errore nella modifica della sub-delega' : 'Errore nella creazione della sub-delega');
        }
        setSaving(false);
    };

    const handleEditSubDelega = (subDelega) => {
        setEditingSubDelega(subDelega.id);
        setSubDelegaForm({
            cognome: subDelega.cognome || '',
            nome: subDelega.nome || '',
            luogo_nascita: subDelega.luogo_nascita || '',
            data_nascita: subDelega.data_nascita || '',
            domicilio: subDelega.domicilio || '',
            tipo_documento: subDelega.tipo_documento || '',
            numero_documento: subDelega.numero_documento || '',
            email: subDelega.email || '',
            telefono: subDelega.telefono || '',
            comuni_ids: subDelega.comuni_ids || [],
            municipi: subDelega.municipi || []
        });
        setShowSubDelegaForm(true);
    };

    const handleRevokeSubDelega = (subDelega) => {
        setConfirmModal({
            show: true,
            title: 'Revoca Sub-Delega',
            message: `Sei sicuro di voler revocare la sub-delega a ${subDelega.cognome} ${subDelega.nome}?`,
            onConfirm: async () => {
                try {
                    await client.deleghe.subDeleghe.revoke(subDelega.id);
                    loadCatena();
                } catch (err) {
                    setError('Errore nella revoca');
                }
                setConfirmModal({ show: false });
            }
        });
    };

    const resetSubDelegaForm = () => {
        setEditingSubDelega(null);
        setSubDelegaForm({
            cognome: '', nome: '', luogo_nascita: '', data_nascita: '',
            domicilio: '', tipo_documento: '', numero_documento: '',
            email: '', telefono: '', comuni_ids: [], municipi: []
        });
    };

    const formatDate = (dateStr) => {
        if (!dateStr) return '-';
        return new Date(dateStr).toLocaleDateString('it-IT');
    };

    if (loading) {
        return (
            <div className="loading-container" role="status" aria-live="polite">
                <div className="spinner-border text-primary">
                    <span className="visually-hidden">Caricamento in corso...</span>
                </div>
                <p className="loading-text">Caricamento deleghe...</p>
            </div>
        );
    }

    const isDelegato = catena?.is_delegato;
    const isSubDelegato = catena?.is_sub_delegato;

    // Determina se è un referendum: dal tipo o dal nome della consultazione
    const isReferendum = consultazione?.tipo === 'REFERENDUM' ||
        consultazione?.nome?.toLowerCase().includes('referendum');

    return (
        <>
            {/* Header */}
            <div className="card mb-3" style={{ background: 'linear-gradient(135deg, #6f42c1 0%, #5a32a3 100%)' }}>
                <div className="card-body text-white py-3">
                    <h5 className="mb-1">Gestione Deleghe</h5>
                    <small className="opacity-75">
                        Sistema di autorizzazione per la designazione dei Rappresentanti di Lista
                    </small>
                </div>
            </div>

            {/* Tabs */}
            <ul className="nav nav-tabs mb-3">
                <li className="nav-item">
                    <button
                        className={`nav-link ${activeTab === 'catena' ? 'active' : ''}`}
                        onClick={() => setActiveTab('catena')}
                    >
                        <i className="fas fa-link me-1"></i>
                        Catena Deleghe
                    </button>
                </li>
                {/* Sub-Deleghe: solo Delegati possono creare sub-deleghe */}
                {isDelegato && (
                    <li className="nav-item">
                        <button
                            className={`nav-link ${activeTab === 'sub-deleghe' ? 'active' : ''}`}
                            onClick={() => setActiveTab('sub-deleghe')}
                        >
                            <i className="fas fa-users me-1"></i>
                            Sub-Deleghe
                            {catena?.sub_deleghe_fatte?.length > 0 && (
                                <span className="badge bg-primary ms-1">{catena.sub_deleghe_fatte.length}</span>
                            )}
                        </button>
                    </li>
                )}
                {/* Conferma Bozze: Delegati e Sub-Delegati con firma possono confermare */}
                {(isDelegato || isSubDelegato) && (
                    <li className="nav-item">
                        <button
                            className={`nav-link ${activeTab === 'conferma' ? 'active' : ''}`}
                            onClick={() => setActiveTab('conferma')}
                        >
                            <i className="fas fa-check-double me-1"></i>
                            Conferma Bozze
                            {bozze.length > 0 && (
                                <span className="badge bg-warning text-dark ms-1">{bozze.length}</span>
                            )}
                        </button>
                    </li>
                )}
                {/* Campagne: Delegati e Sub-Delegati possono creare campagne di reclutamento */}
                {(isDelegato || isSubDelegato) && (
                    <li className="nav-item">
                        <button
                            className={`nav-link ${activeTab === 'campagne' ? 'active' : ''}`}
                            onClick={() => setActiveTab('campagne')}
                        >
                            <i className="fas fa-bullhorn me-1"></i>
                            Campagne
                            {campagne.length > 0 && (
                                <span className="badge bg-info ms-1">{campagne.length}</span>
                            )}
                        </button>
                    </li>
                )}
            </ul>

            {/* Tab: Catena Deleghe */}
            {activeTab === 'catena' && (
                <>
                    {/* Info sul ruolo */}
                    <div className={`alert ${isDelegato ? 'alert-primary' : isSubDelegato ? 'alert-success' : 'alert-secondary'} mb-3`}>
                        <div className="d-flex align-items-center">
                            <div className="me-3" style={{ fontSize: '2rem' }}>
                                {isDelegato ? '🏛️' : isSubDelegato ? '📋' : '👤'}
                            </div>
                            <div>
                                <strong>
                                    {isDelegato ? `Sei un Delegato${isReferendum ? '' : ' di Lista'}` :
                                     isSubDelegato ? 'Sei un Sub-Delegato autorizzato' :
                                     'Nessuna delega attiva'}
                                </strong>
                                <div className="small">
                                    {isDelegato ? 'Puoi creare sub-deleghe per il tuo territorio' :
                                     isSubDelegato ? 'Puoi designare RDL nelle sezioni del tuo territorio' :
                                     `Contatta un Delegato${isReferendum ? '' : ' di Lista'} per ricevere l'autorizzazione`}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Visualizzazione catena */}
                    <div className="card">
                        <div className="card-header bg-light">
                            <strong>Catena delle Deleghe</strong>
                            <small className="text-muted d-block">Dal Partito fino a te</small>
                        </div>
                        <div className="card-body">
                            <div className="delegation-chain">
                                {/* Livello 1: Partito/Comitato */}
                                {isReferendum ? (
                                    <ChainNode
                                        icon="📣"
                                        iconBg="#198754"
                                        title="COMITATO PROMOTORE / M5S"
                                        subtitle="Promotore referendum o partito in Parlamento"
                                        bgColor="#d1e7dd"
                                        borderColor="#198754"
                                    />
                                ) : (
                                    <ChainNode
                                        icon="⭐"
                                        iconBg="#ffc107"
                                        title="MOVIMENTO 5 STELLE"
                                        subtitle="Deposito lista candidati"
                                        bgColor="#fff3cd"
                                        borderColor="#ffc107"
                                    />
                                )}
                                <ChainConnector />

                                {/* Livello 2: Delegato di Lista */}
                                {isDelegato && catena.deleghe_lista.length > 0 ? (
                                    catena.deleghe_lista.map((dl, idx) => (
                                        <React.Fragment key={dl.id || idx}>
                                            <ChainNode
                                                icon="🏛️"
                                                iconBg="#0d6efd"
                                                title={`${dl.carica_display || dl.carica}: ${dl.cognome} ${dl.nome}`}
                                                subtitle={`${dl.territorio || dl.circoscrizione || 'Territorio non specificato'} • Nomina: ${formatDate(dl.data_nomina)}`}
                                                bgColor="#cfe2ff"
                                                borderColor="#0d6efd"
                                                highlight={true}
                                                highlightText="TU"
                                            />
                                            {idx < catena.deleghe_lista.length - 1 && <ChainConnector />}
                                        </React.Fragment>
                                    ))
                                ) : isSubDelegato && catena.sub_deleghe_ricevute.length > 0 ? (
                                    catena.sub_deleghe_ricevute.map((sd, idx) => (
                                        <React.Fragment key={sd.id || idx}>
                                            <ChainNode
                                                icon="🏛️"
                                                iconBg="#0d6efd"
                                                title={`${sd.delegato_carica}: ${sd.delegato_nome}`}
                                                subtitle={isReferendum ? "Delegato" : "Delegato di Lista"}
                                                bgColor="#e9ecef"
                                                borderColor="#6c757d"
                                            />
                                            <ChainConnector />
                                            <ChainNode
                                                icon="📋"
                                                iconBg="#198754"
                                                title={`${sd.cognome} ${sd.nome}`}
                                                subtitle={`Sub-Delegato (${sd.tipo_delega_display || (sd.puo_designare_direttamente ? 'Designa' : 'Solo Mappatura')}) • ${sd.territorio || 'Territorio non specificato'}`}
                                                bgColor="#d1e7dd"
                                                borderColor="#198754"
                                                highlight={true}
                                                highlightText="TU"
                                            />
                                        </React.Fragment>
                                    ))
                                ) : (
                                    <>
                                        <ChainNode
                                            icon="🏛️"
                                            iconBg="#6c757d"
                                            title={isReferendum ? "Delegato" : "Delegato di Lista"}
                                            subtitle="(Non assegnato)"
                                            bgColor="#f8f9fa"
                                            borderColor="#dee2e6"
                                        />
                                        <ChainConnector />
                                        <ChainNode
                                            icon="👤"
                                            iconBg="#dc3545"
                                            title={user?.display_name || user?.email || 'Tu'}
                                            subtitle="In attesa di autorizzazione"
                                            bgColor="#f8d7da"
                                            borderColor="#dc3545"
                                        />
                                    </>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Note legali */}
                    <div className="alert alert-warning mt-3 small">
                        <strong><i className="fas fa-info-circle me-1"></i> Note normative:</strong>
                        {isReferendum ? (
                            <ul className="mb-0 mt-1">
                                <li>Il delegato deve avere <strong>mandato autenticato da notaio</strong> conferito da un promotore o dal presidente/segretario del partito</li>
                                <li>I promotori o il presidente del partito possono anche designare <strong>direttamente</strong> i rappresentanti</li>
                                <li>Presso ogni seggio: 2 rappresentanti (1 effettivo + 1 supplente)</li>
                                <li>Riferimento: L. 352/1970 e DPR 361/1957</li>
                            </ul>
                        ) : (
                            <ul className="mb-0 mt-1">
                                <li>Le sub-deleghe richiedono <strong>firma autenticata</strong> (notaio, segretario comunale)</li>
                                <li>Il sub-delegato deve allegare copia della delega quando designa un RDL</li>
                                <li>Riferimento: Art. 25 DPR 361/1957</li>
                            </ul>
                        )}
                    </div>
                </>
            )}

            {/* Tab: Sub-Deleghe - solo per Delegati */}
            {activeTab === 'sub-deleghe' && isDelegato && (
                <>
                    <div className="d-flex justify-content-between align-items-center mb-3">
                        <div>
                            <h6 className="mb-0">Sub-deleghe che hai creato</h6>
                            <small className="text-muted">Persone autorizzate a designare RDL</small>
                        </div>
                        {isDelegato && (
                            <button
                                className="btn btn-primary btn-sm"
                                onClick={() => {
                                    if (showSubDelegaForm) {
                                        setShowSubDelegaForm(false);
                                        resetSubDelegaForm();
                                    } else {
                                        setShowSubDelegaForm(true);
                                    }
                                }}
                            >
                                {showSubDelegaForm ? 'Annulla' : '+ Nuova Sub-Delega'}
                            </button>
                        )}
                    </div>

                    {/* Form nuova sub-delega */}
                    {showSubDelegaForm && isDelegato && (
                        <div className="card mb-3 border-primary">
                            <div className="card-header bg-primary text-white">
                                <strong>{editingSubDelega ? 'Modifica Sub-Delega' : 'Nuova Sub-Delega'}</strong>
                            </div>
                            <div className="card-body">
                                <form onSubmit={handleSaveSubDelega}>
                                    <div className="row g-3">
                                        <div className="col-md-6">
                                            <label className="form-label">Cognome *</label>
                                            <input
                                                type="text"
                                                className="form-control"
                                                value={subDelegaForm.cognome}
                                                onChange={(e) => setSubDelegaForm({...subDelegaForm, cognome: e.target.value})}
                                                required
                                            />
                                        </div>
                                        <div className="col-md-6">
                                            <label className="form-label">Nome *</label>
                                            <input
                                                type="text"
                                                className="form-control"
                                                value={subDelegaForm.nome}
                                                onChange={(e) => setSubDelegaForm({...subDelegaForm, nome: e.target.value})}
                                                required
                                            />
                                        </div>
                                        <div className="col-md-6">
                                            <label className="form-label">Luogo di nascita *</label>
                                            <input
                                                type="text"
                                                className="form-control"
                                                value={subDelegaForm.luogo_nascita}
                                                onChange={(e) => setSubDelegaForm({...subDelegaForm, luogo_nascita: e.target.value})}
                                                required
                                            />
                                        </div>
                                        <div className="col-md-6">
                                            <label className="form-label">Data di nascita *</label>
                                            <input
                                                type="date"
                                                className="form-control"
                                                value={subDelegaForm.data_nascita}
                                                onChange={(e) => setSubDelegaForm({...subDelegaForm, data_nascita: e.target.value})}
                                                required
                                            />
                                        </div>
                                        <div className="col-12">
                                            <label className="form-label">Domicilio *</label>
                                            <input
                                                type="text"
                                                className="form-control"
                                                value={subDelegaForm.domicilio}
                                                onChange={(e) => setSubDelegaForm({...subDelegaForm, domicilio: e.target.value})}
                                                placeholder="Via, n. civico, CAP, Città"
                                                required
                                            />
                                        </div>
                                        <div className="col-md-6">
                                            <label className="form-label">Tipo documento *</label>
                                            <select
                                                className="form-select"
                                                value={subDelegaForm.tipo_documento}
                                                onChange={(e) => setSubDelegaForm({...subDelegaForm, tipo_documento: e.target.value})}
                                                required
                                            >
                                                <option value="">Seleziona...</option>
                                                <option value="Carta d'identità">Carta d'identità</option>
                                                <option value="Patente">Patente</option>
                                                <option value="Passaporto">Passaporto</option>
                                            </select>
                                        </div>
                                        <div className="col-md-6">
                                            <label className="form-label">Numero documento *</label>
                                            <input
                                                type="text"
                                                className="form-control"
                                                value={subDelegaForm.numero_documento}
                                                onChange={(e) => setSubDelegaForm({...subDelegaForm, numero_documento: e.target.value})}
                                                required
                                            />
                                        </div>
                                        <div className="col-md-6">
                                            <label className="form-label">Email *</label>
                                            <input
                                                type="email"
                                                className="form-control"
                                                value={subDelegaForm.email}
                                                onChange={(e) => setSubDelegaForm({...subDelegaForm, email: e.target.value})}
                                                required
                                            />
                                        </div>
                                        <div className="col-md-6">
                                            <label className="form-label">Telefono</label>
                                            <input
                                                type="tel"
                                                className="form-control"
                                                value={subDelegaForm.telefono}
                                                onChange={(e) => setSubDelegaForm({...subDelegaForm, telefono: e.target.value})}
                                            />
                                        </div>
                                        <div className="col-12">
                                            <label className="form-label">Territori autorizzati *</label>
                                            <input
                                                type="text"
                                                className="form-control"
                                                placeholder="Es: ROMA Municipio I, II, III oppure MENTANA, MONTEROTONDO"
                                                onChange={(e) => {
                                                    // TODO: parsing più intelligente quando avremo l'autocomplete
                                                    setSubDelegaForm({...subDelegaForm, comuni_ids: e.target.value.split(',').map(s => s.trim())});
                                                }}
                                                required
                                            />
                                            <small className="text-muted">
                                                Specifica i comuni o i municipi per cui questa persona potrà designare RDL
                                            </small>
                                        </div>
                                    </div>
                                    <div className="mt-3 d-flex gap-2">
                                        <button type="submit" className="btn btn-success" disabled={saving}>
                                            {saving ? 'Salvataggio...' : (editingSubDelega ? 'Salva Modifiche' : 'Crea Sub-Delega')}
                                        </button>
                                        <button type="button" className="btn btn-secondary" onClick={() => { setShowSubDelegaForm(false); resetSubDelegaForm(); }}>
                                            Annulla
                                        </button>
                                    </div>
                                </form>
                            </div>
                        </div>
                    )}

                    {/* Lista sub-deleghe */}
                    {(isDelegato ? catena.sub_deleghe_fatte : catena.sub_deleghe_ricevute)?.length === 0 ? (
                        <div className="text-center text-muted py-5">
                            <div style={{ fontSize: '3rem' }}>👥</div>
                            <p>{isDelegato ? 'Non hai ancora creato sub-deleghe' : 'Non hai sub-deleghe attive'}</p>
                        </div>
                    ) : (
                        <div className="row g-3">
                            {(isDelegato ? catena.sub_deleghe_fatte : catena.sub_deleghe_ricevute)?.map((sd, idx) => (
                                <div key={sd.id || idx} className="col-12">
                                    <div className="card">
                                        <div className="card-body">
                                            <div className="d-flex justify-content-between align-items-start">
                                                <div>
                                                    <h6 className="mb-1">{sd.cognome} {sd.nome}</h6>
                                                    <div className="small text-muted">
                                                        {sd.email} {sd.telefono && `• ${sd.telefono}`}
                                                    </div>
                                                    <div className="mt-2">
                                                        <span className="badge bg-info me-1">
                                                            {sd.territorio || 'Territorio non specificato'}
                                                        </span>
                                                        {sd.firma_autenticata ? (
                                                            <span className="badge bg-success">✓ Firma autenticata</span>
                                                        ) : (
                                                            <span className="badge bg-warning text-dark">⚠ Firma da autenticare</span>
                                                        )}
                                                    </div>
                                                    <div className="small text-muted mt-1">
                                                        {sd.n_designazioni || 0} RDL designati • Delega del {formatDate(sd.data_delega)}
                                                    </div>
                                                </div>
                                                {isDelegato && (
                                                    <div className="d-flex gap-2">
                                                        <button
                                                            className="btn btn-outline-primary btn-sm"
                                                            onClick={() => handleEditSubDelega(sd)}
                                                        >
                                                            <i className="fas fa-edit me-1"></i>Modifica
                                                        </button>
                                                        <button
                                                            className="btn btn-outline-danger btn-sm"
                                                            onClick={() => handleRevokeSubDelega(sd)}
                                                        >
                                                            Revoca
                                                        </button>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </>
            )}

            {/* Tab: Conferma Bozze */}
            {activeTab === 'conferma' && (isDelegato || isSubDelegato) && (
                <>
                    <div className="d-flex justify-content-between align-items-center mb-3">
                        <div>
                            <h6 className="mb-0">Designazioni da confermare</h6>
                            <small className="text-muted">Bozze create dai sub-delegati che richiedono la tua approvazione</small>
                        </div>
                        <button
                            className="btn btn-outline-secondary btn-sm"
                            onClick={loadBozze}
                            disabled={loadingBozze}
                        >
                            <i className="fas fa-sync-alt me-1"></i>
                            Aggiorna
                        </button>
                    </div>

                    {loadingBozze ? (
                        <div className="text-center py-4">
                            <div className="spinner-border text-primary" role="status">
                                <span className="visually-hidden">Caricamento...</span>
                            </div>
                        </div>
                    ) : bozze.length === 0 ? (
                        <div className="text-center text-muted py-5">
                            <div style={{ fontSize: '3rem' }}>✓</div>
                            <p>Nessuna bozza in attesa di conferma</p>
                        </div>
                    ) : (
                        <div className="row g-3">
                            {bozze.map((bozza) => (
                                <div key={bozza.id} className="col-12">
                                    <div className="card border-warning">
                                        <div className="card-body">
                                            <div className="d-flex justify-content-between align-items-start">
                                                <div>
                                                    <h6 className="mb-1">
                                                        {bozza.cognome} {bozza.nome}
                                                        <span className={`badge ms-2 ${bozza.ruolo === 'EFFETTIVO' ? 'bg-success' : 'bg-info'}`}>
                                                            {bozza.ruolo_display}
                                                        </span>
                                                    </h6>
                                                    <div className="small text-muted">
                                                        <i className="fas fa-envelope me-1"></i>{bozza.email}
                                                    </div>
                                                    <div className="mt-2">
                                                        <span className="badge bg-secondary me-1">
                                                            <i className="fas fa-map-marker-alt me-1"></i>
                                                            Sezione {bozza.sezione_numero}
                                                        </span>
                                                        <span className="badge bg-light text-dark">
                                                            {bozza.sezione_comune}
                                                            {bozza.sezione_municipio && ` - Mun. ${bozza.sezione_municipio}`}
                                                        </span>
                                                    </div>
                                                    <div className="small text-muted mt-1">
                                                        Creata da: {bozza.designante_nome || 'Sub-delegato'}
                                                    </div>
                                                </div>
                                                <div className="d-flex flex-column gap-2">
                                                    <button
                                                        className="btn btn-success btn-sm"
                                                        onClick={() => handleConfermaBozza(bozza)}
                                                    >
                                                        <i className="fas fa-check me-1"></i>
                                                        Conferma
                                                    </button>
                                                    <button
                                                        className="btn btn-outline-danger btn-sm"
                                                        onClick={() => handleRifiutaBozza(bozza)}
                                                    >
                                                        <i className="fas fa-times me-1"></i>
                                                        Rifiuta
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Info box */}
                    <div className="alert alert-info mt-3 small">
                        <i className="fas fa-info-circle me-1"></i>
                        Le designazioni in stato <strong>BOZZA</strong> sono state create dai sub-delegati senza firma autenticata.
                        Come delegato o sub-delegato con firma, puoi confermarle per renderle ufficiali.
                    </div>
                </>
            )}

            {/* Tab: Campagne di Reclutamento */}
            {activeTab === 'campagne' && (isDelegato || isSubDelegato) && (
                <>
                    <div className="d-flex justify-content-between align-items-center mb-3">
                        <div>
                            <h6 className="mb-0">Campagne di Reclutamento RDL</h6>
                            <small className="text-muted">Crea link pubblici per raccogliere candidature</small>
                        </div>
                        <button
                            className="btn btn-primary btn-sm"
                            onClick={() => {
                                if (showCampagnaForm) {
                                    setShowCampagnaForm(false);
                                    resetCampagnaForm();
                                } else {
                                    setShowCampagnaForm(true);
                                }
                            }}
                        >
                            {showCampagnaForm ? 'Annulla' : '+ Nuova Campagna'}
                        </button>
                    </div>

                    {/* Form nuova/modifica campagna */}
                    {showCampagnaForm && (
                        <div className="card mb-3 border-primary">
                            <div className="card-header bg-primary text-white">
                                <strong>{editingCampagna ? 'Modifica Campagna' : 'Nuova Campagna'}</strong>
                            </div>
                            <div className="card-body">
                                <form onSubmit={handleSaveCampagna}>
                                    <div className="row g-3">
                                        <div className="col-md-8">
                                            <label className="form-label">Nome *</label>
                                            <input
                                                type="text"
                                                className="form-control"
                                                value={campagnaForm.nome}
                                                onChange={(e) => handleCampagnaFormChange('nome', e.target.value)}
                                                placeholder="Es: Referendum Giugno 2025 - Roma"
                                                required
                                            />
                                        </div>
                                        <div className="col-md-4">
                                            <label className="form-label">Slug URL</label>
                                            <input
                                                type="text"
                                                className="form-control"
                                                value={campagnaForm.slug}
                                                onChange={(e) => handleCampagnaFormChange('slug', e.target.value)}
                                                placeholder="auto-generato"
                                            />
                                            <small className="text-muted">/campagna/{campagnaForm.slug || '...'}</small>
                                        </div>
                                        <div className="col-12">
                                            <label className="form-label">Descrizione</label>
                                            <textarea
                                                className="form-control"
                                                rows="2"
                                                value={campagnaForm.descrizione}
                                                onChange={(e) => handleCampagnaFormChange('descrizione', e.target.value)}
                                                placeholder="Descrizione opzionale della campagna"
                                            />
                                        </div>
                                        <div className="col-md-6">
                                            <label className="form-label">Data e ora apertura *</label>
                                            <input
                                                type="datetime-local"
                                                className="form-control"
                                                value={campagnaForm.data_apertura}
                                                onChange={(e) => handleCampagnaFormChange('data_apertura', e.target.value)}
                                                required
                                            />
                                        </div>
                                        <div className="col-md-6">
                                            <label className="form-label">Data e ora chiusura *</label>
                                            <input
                                                type="datetime-local"
                                                className="form-control"
                                                value={campagnaForm.data_chiusura}
                                                onChange={(e) => handleCampagnaFormChange('data_chiusura', e.target.value)}
                                                required
                                            />
                                        </div>

                                        {/* Territorio */}
                                        <div className="col-12">
                                            <label className="form-label">Territorio (opzionale)</label>
                                            <small className="text-muted d-block mb-2">
                                                Lascia vuoto per accettare registrazioni da tutti i comuni.
                                            </small>
                                        </div>
                                        <div className="col-md-4">
                                            <label className="form-label small">Regione</label>
                                            <select
                                                className="form-select form-select-sm"
                                                value={campagnaForm.regioni_ids[0] || ''}
                                                onChange={(e) => {
                                                    const val = e.target.value;
                                                    handleCampagnaFormChange('regioni_ids', val ? [parseInt(val)] : []);
                                                    handleCampagnaFormChange('province_ids', []);
                                                    handleCampagnaFormChange('comuni_ids', []);
                                                    setProvince([]);
                                                    setComuni([]);
                                                    if (val) loadProvince(val);
                                                }}
                                            >
                                                <option value="">Tutte le regioni</option>
                                                {regioni.map(r => (
                                                    <option key={r.id} value={r.id}>{r.nome}</option>
                                                ))}
                                            </select>
                                        </div>
                                        <div className="col-md-4">
                                            <label className="form-label small">Provincia</label>
                                            <select
                                                className="form-select form-select-sm"
                                                value={campagnaForm.province_ids[0] || ''}
                                                onChange={(e) => {
                                                    const val = e.target.value;
                                                    handleCampagnaFormChange('province_ids', val ? [parseInt(val)] : []);
                                                    handleCampagnaFormChange('comuni_ids', []);
                                                    setComuni([]);
                                                    if (val) loadComuni(val);
                                                }}
                                                disabled={!campagnaForm.regioni_ids.length}
                                            >
                                                <option value="">Tutte le province</option>
                                                {province.map(p => (
                                                    <option key={p.id} value={p.id}>{p.nome}</option>
                                                ))}
                                            </select>
                                        </div>
                                        <div className="col-md-4">
                                            <label className="form-label small">Comune</label>
                                            <select
                                                className="form-select form-select-sm"
                                                value={campagnaForm.comuni_ids[0] || ''}
                                                onChange={(e) => {
                                                    const val = e.target.value;
                                                    handleCampagnaFormChange('comuni_ids', val ? [parseInt(val)] : []);
                                                }}
                                                disabled={!campagnaForm.province_ids.length}
                                            >
                                                <option value="">Tutti i comuni</option>
                                                {comuni.map(c => (
                                                    <option key={c.id} value={c.id}>{c.nome}</option>
                                                ))}
                                            </select>
                                        </div>

                                        {/* Opzioni */}
                                        <div className="col-md-6">
                                            <div className="form-check">
                                                <input
                                                    type="checkbox"
                                                    className="form-check-input"
                                                    id="richiedi_approvazione"
                                                    checked={campagnaForm.richiedi_approvazione}
                                                    onChange={(e) => handleCampagnaFormChange('richiedi_approvazione', e.target.checked)}
                                                />
                                                <label className="form-check-label" htmlFor="richiedi_approvazione">
                                                    Richiedi approvazione manuale
                                                </label>
                                            </div>
                                            <small className="text-muted">
                                                Se attivo, le registrazioni dovranno essere approvate da un delegato
                                            </small>
                                        </div>
                                        <div className="col-md-6">
                                            <label className="form-label">Max registrazioni</label>
                                            <input
                                                type="number"
                                                className="form-control"
                                                value={campagnaForm.max_registrazioni}
                                                onChange={(e) => handleCampagnaFormChange('max_registrazioni', e.target.value)}
                                                placeholder="Illimitato"
                                                min="1"
                                            />
                                        </div>
                                        <div className="col-12">
                                            <label className="form-label">Messaggio di conferma</label>
                                            <textarea
                                                className="form-control"
                                                rows="2"
                                                value={campagnaForm.messaggio_conferma}
                                                onChange={(e) => handleCampagnaFormChange('messaggio_conferma', e.target.value)}
                                                placeholder="Messaggio mostrato dopo la registrazione (opzionale)"
                                            />
                                        </div>
                                    </div>
                                    <div className="mt-3 d-flex gap-2">
                                        <button type="submit" className="btn btn-success" disabled={savingCampagna}>
                                            {savingCampagna ? 'Salvataggio...' : (editingCampagna ? 'Salva Modifiche' : 'Crea Campagna')}
                                        </button>
                                        <button type="button" className="btn btn-secondary" onClick={() => { setShowCampagnaForm(false); resetCampagnaForm(); }}>
                                            Annulla
                                        </button>
                                    </div>
                                </form>
                            </div>
                        </div>
                    )}

                    {/* Lista campagne */}
                    {loadingCampagne ? (
                        <div className="text-center py-4">
                            <div className="spinner-border text-primary" role="status">
                                <span className="visually-hidden">Caricamento...</span>
                            </div>
                        </div>
                    ) : campagne.length === 0 ? (
                        <div className="text-center text-muted py-5">
                            <div style={{ fontSize: '3rem' }}>📢</div>
                            <p>Non hai ancora creato campagne di reclutamento</p>
                            <p className="small">
                                Le campagne ti permettono di creare link pubblici per raccogliere candidature RDL.
                            </p>
                        </div>
                    ) : (
                        <div className="row g-3">
                            {campagne.map((campagna) => (
                                <div key={campagna.id} className="col-12">
                                    <div className={`card ${
                                        campagna.stato === 'ATTIVA' ? 'border-success' :
                                        campagna.stato === 'CHIUSA' ? 'border-secondary' :
                                        'border-warning'
                                    }`}>
                                        <div className="card-body">
                                            <div className="d-flex justify-content-between align-items-start">
                                                <div className="flex-grow-1">
                                                    <h6 className="mb-1">
                                                        <i className="fas fa-bullhorn me-2 text-primary"></i>
                                                        {campagna.nome}
                                                    </h6>
                                                    <div className="mb-2">
                                                        <span className={`badge me-2 ${
                                                            campagna.stato === 'ATTIVA' ? 'bg-success' :
                                                            campagna.stato === 'CHIUSA' ? 'bg-secondary' :
                                                            'bg-warning text-dark'
                                                        }`}>
                                                            {campagna.stato === 'ATTIVA' ? '● Attiva' :
                                                             campagna.stato === 'CHIUSA' ? '○ Chiusa' :
                                                             '○ Bozza'}
                                                        </span>
                                                        <span className="badge bg-light text-dark me-2">
                                                            {campagna.n_registrazioni || 0} registrazioni
                                                        </span>
                                                        {campagna.data_chiusura && (
                                                            <span className="badge bg-light text-dark">
                                                                Scade: {formatDate(campagna.data_chiusura)}
                                                            </span>
                                                        )}
                                                    </div>
                                                    {campagna.stato === 'ATTIVA' && (
                                                        <div className="small text-muted">
                                                            <i className="fas fa-link me-1"></i>
                                                            {window.location.origin}/campagna/{campagna.slug}
                                                        </div>
                                                    )}
                                                    {campagna.territorio_display && (
                                                        <div className="small text-muted mt-1">
                                                            <i className="fas fa-map-marker-alt me-1"></i>
                                                            {campagna.territorio_display}
                                                        </div>
                                                    )}
                                                </div>
                                                <div className="d-flex flex-wrap gap-1 justify-content-end" style={{ minWidth: '200px' }}>
                                                    {campagna.stato === 'ATTIVA' && (
                                                        <button
                                                            className="btn btn-outline-primary btn-sm"
                                                            onClick={() => handleCopiaLink(campagna)}
                                                            title="Copia link"
                                                        >
                                                            <i className="fas fa-copy"></i>
                                                        </button>
                                                    )}
                                                    <button
                                                        className="btn btn-outline-secondary btn-sm"
                                                        onClick={() => handleEditCampagna(campagna)}
                                                        title="Modifica"
                                                    >
                                                        <i className="fas fa-edit"></i>
                                                    </button>
                                                    {campagna.stato === 'BOZZA' && (
                                                        <button
                                                            className="btn btn-success btn-sm"
                                                            onClick={() => handleAttivaCampagna(campagna)}
                                                            title="Attiva"
                                                        >
                                                            <i className="fas fa-play me-1"></i>Attiva
                                                        </button>
                                                    )}
                                                    {campagna.stato === 'ATTIVA' && (
                                                        <button
                                                            className="btn btn-outline-warning btn-sm"
                                                            onClick={() => handleChiudiCampagna(campagna)}
                                                            title="Chiudi"
                                                        >
                                                            <i className="fas fa-pause me-1"></i>Chiudi
                                                        </button>
                                                    )}
                                                    <button
                                                        className="btn btn-outline-danger btn-sm"
                                                        onClick={() => handleDeleteCampagna(campagna)}
                                                        title="Elimina"
                                                    >
                                                        <i className="fas fa-trash"></i>
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Info box */}
                    <div className="alert alert-info mt-3 small">
                        <i className="fas fa-info-circle me-1"></i>
                        <strong>Come funzionano le campagne:</strong>
                        <ul className="mb-0 mt-1">
                            <li><strong>Bozza</strong>: La campagna non è visibile pubblicamente</li>
                            <li><strong>Attiva</strong>: Il link è accessibile e le persone possono registrarsi</li>
                            <li><strong>Chiusa</strong>: Il link non funziona più</li>
                        </ul>
                    </div>
                </>
            )}

            {/* Confirm Modal */}
            <ConfirmModal
                show={confirmModal.show}
                title={confirmModal.title}
                message={confirmModal.message}
                onConfirm={confirmModal.onConfirm}
                onCancel={() => setConfirmModal({ show: false })}
            />
        </>
    );
}

/**
 * Componente per un nodo della catena deleghe
 */
function ChainNode({ icon, iconBg, title, subtitle, bgColor, borderColor, highlight, highlightText }) {
    return (
        <div className="d-flex align-items-center mb-2">
            <div
                style={{
                    width: '44px',
                    height: '44px',
                    borderRadius: '50%',
                    background: iconBg,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '1.2rem',
                    marginRight: '12px',
                    flexShrink: 0
                }}
            >
                {icon}
            </div>
            <div
                style={{
                    flex: 1,
                    padding: '12px 16px',
                    background: bgColor,
                    borderRadius: '8px',
                    border: `2px solid ${borderColor}`,
                    position: 'relative'
                }}
            >
                <div style={{ fontWeight: 600 }}>{title}</div>
                <div style={{ fontSize: '0.85rem', color: '#6c757d' }}>{subtitle}</div>
                {highlight && (
                    <span
                        style={{
                            position: 'absolute',
                            top: '-8px',
                            right: '12px',
                            background: borderColor,
                            color: 'white',
                            padding: '2px 8px',
                            borderRadius: '10px',
                            fontSize: '0.7rem',
                            fontWeight: 600
                        }}
                    >
                        {highlightText}
                    </span>
                )}
            </div>
        </div>
    );
}

/**
 * Connettore verticale tra nodi
 */
function ChainConnector() {
    return (
        <div style={{ marginLeft: '21px', width: '2px', height: '20px', background: '#dee2e6' }}></div>
    );
}

export default GestioneDeleghe;
