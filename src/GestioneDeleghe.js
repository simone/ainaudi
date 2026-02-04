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
    const [activeTab, setActiveTab] = useState(initialTab || 'catena'); // 'catena' | 'sub-deleghe'

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

    useEffect(() => {
        loadCatena();
    }, [consultazione]);

    // Aggiorna il tab attivo quando cambia initialTab (navigazione dal menu)
    useEffect(() => {
        if (initialTab) {
            setActiveTab(initialTab);
        }
    }, [initialTab]);

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
