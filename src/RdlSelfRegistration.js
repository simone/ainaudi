import React, { useState, useEffect } from 'react';
import ComuneAutocomplete from './ComuneAutocomplete';
import SezzionePlessAutocomplete from './SezzionePlessAutocomplete';

const SERVER_API = process.env.NODE_ENV === 'development' ? process.env.REACT_APP_API_URL : '';

// Eligibility requirements by election type
const REQUISITI_ELETTORE = {
    COMUNALI: {
        label: 'Comunali',
        requisito: 'Elettore dello stesso Comune',
        descrizione: 'Il RDL deve essere iscritto nelle liste elettorali del comune dove intende operare.'
    },
    REGIONALI: {
        label: 'Regionali',
        requisito: 'Elettore della stessa Regione',
        descrizione: 'Il RDL deve essere elettore di un qualsiasi comune della stessa regione.'
    },
    POLITICHE_CAMERA: {
        label: 'Politiche Camera',
        requisito: 'Elettore della stessa Circoscrizione',
        descrizione: 'Il RDL deve essere elettore di un comune della stessa circoscrizione elettorale (26 circoscrizioni).'
    },
    POLITICHE_SENATO: {
        label: 'Politiche Senato',
        requisito: 'Elettore della stessa Regione',
        descrizione: 'Il RDL deve essere elettore di un comune della stessa circoscrizione regionale (20 circoscrizioni = regioni).'
    },
    EUROPEE: {
        label: 'Europee',
        requisito: 'Elettore della stessa Circoscrizione Europea',
        descrizione: 'Il RDL deve essere elettore di un comune della stessa circoscrizione europea (5 circoscrizioni: Nord-Ovest, Nord-Est, Centro, Sud, Isole).'
    },
    REFERENDUM: {
        label: 'Referendum',
        requisito: 'Elettore di qualsiasi Comune italiano',
        descrizione: 'Il RDL può essere un elettore di qualsiasi comune italiano.'
    }
};

function RdlSelfRegistration({ onClose }) {
    const [formData, setFormData] = useState({
        email: '',
        cognome: '',
        nome: '',
        comune_nascita: '',
        data_nascita: '',
        comune_residenza: '',
        indirizzo_residenza: '',
        seggio_preferenza: '',
        municipio: '',
        telefono: '',
        fuorisede: null,
        comune_domicilio: '',
        indirizzo_domicilio: ''
    });
    const [selectedComune, setSelectedComune] = useState(null);
    const [selectedSezione, setSelectedSezione] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(false);
    const [registrationStatus, setRegistrationStatus] = useState(null);
    const [checkingStatus, setCheckingStatus] = useState(true);
    const [gdprAccepted, setGdprAccepted] = useState(false);

    useEffect(() => {
        checkRegistrationStatus();
    }, []);

    const checkRegistrationStatus = async () => {
        try {
            const response = await fetch(`${SERVER_API}/api/rdl/register/status`);
            const data = await response.json();
            setRegistrationStatus(data);

            // Auto-select comune if only one is available
            if (data.available && data.comuni && data.comuni.length === 1) {
                setSelectedComune(data.comuni[0]);
            }
        } catch (err) {
            setRegistrationStatus({ available: false, message: 'Errore verifica stato' });
        } finally {
            setCheckingStatus(false);
        }
    };

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleComuneChange = (comune) => {
        setSelectedComune(comune);
        // Reset municipio when comune changes
        setFormData(prev => ({ ...prev, municipio: '' }));
        // Reset sezione when comune changes
        setSelectedSezione(null);
    };

    const handleSezioneChange = (sezione) => {
        if (!sezione) {
            // Cleared selection
            setSelectedSezione(null);
            setFormData(prev => ({ ...prev, seggio_preferenza: '' }));
        } else if (sezione.freeText) {
            // Free text input (user typed something without selecting from suggestions)
            setSelectedSezione(null);
            setFormData(prev => ({ ...prev, seggio_preferenza: sezione.text }));
        } else {
            // Selected from autocomplete suggestions
            setSelectedSezione(sezione);
            const parts = [`Sez. ${sezione.numero}`];
            if (sezione.denominazione) parts.push(sezione.denominazione);
            if (sezione.indirizzo) parts.push(sezione.indirizzo);
            setFormData(prev => ({ ...prev, seggio_preferenza: parts.join(' - ') }));
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        if (!selectedComune) {
            setError('Seleziona il comune del seggio');
            setLoading(false);
            return;
        }

        // Municipio is required if the comune has municipalities
        if (selectedComune.has_municipi && selectedComune.municipi?.length > 0 && !formData.municipio) {
            setError('Seleziona un municipio');
            setLoading(false);
            return;
        }

        // Fuorisede selection is required
        if (formData.fuorisede === null) {
            setError('Devi indicare se sei un fuorisede');
            setLoading(false);
            return;
        }

        // If fuorisede is true, domicilio fields are required
        if (formData.fuorisede === true) {
            if (!formData.comune_domicilio) {
                setError('Inserisci il comune di domicilio');
                setLoading(false);
                return;
            }
            if (!formData.indirizzo_domicilio) {
                setError('Inserisci l\'indirizzo di domicilio');
                setLoading(false);
                return;
            }
        }

        // GDPR acceptance is required
        if (!gdprAccepted) {
            setError('Devi accettare il trattamento dei dati personali per continuare');
            setLoading(false);
            return;
        }

        try {
            const response = await fetch(`${SERVER_API}/api/rdl/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ...formData,
                    comune_id: selectedComune.id,
                    municipio: formData.municipio ? parseInt(formData.municipio) : null
                })
            });

            const data = await response.json();

            if (!response.ok || data.error) {
                throw new Error(data.error || 'Errore durante la registrazione');
            }

            setSuccess(true);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    if (checkingStatus) {
        return (
            <div className="loading-container" role="status" aria-live="polite">
                <div className="spinner-border text-primary">
                    <span className="visually-hidden">Verifica in corso...</span>
                </div>
                <p className="loading-text">Verifica disponibilità registrazioni...</p>
            </div>
        );
    }

    if (!registrationStatus?.available) {
        return (
            <div className="card">
                <div className="card-header bg-secondary text-white">
                    Registrazione non disponibile
                </div>
                <div className="card-body">
                    <p className="text-muted">
                        {registrationStatus?.message || 'La registrazione come Rappresentante di Lista non è attualmente disponibile.'}
                    </p>
                    <p className="text-muted">
                        Le registrazioni verranno aperte quando sarà indetta una nuova consultazione elettorale.
                    </p>
                    <button className="btn btn-primary" onClick={onClose}>
                        Torna al Login
                    </button>
                </div>
            </div>
        );
    }

    if (success) {
        return (
            <div className="card">
                <div className="card-header bg-success text-white">
                    Richiesta Inviata
                </div>
                <div className="card-body">
                    <p>La tua richiesta di registrazione come Rappresentante di Lista è stata inviata.</p>
                    <p>
                        <strong>Consultazione:</strong> {registrationStatus.consultation?.nome}
                    </p>
                    <p>Riceverai una notifica via email quando sarà approvata dal delegato del tuo comune.</p>
                    <button className="btn btn-primary" onClick={onClose}>
                        Torna al Login
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="card">
            <div className="card-header bg-info text-white">
                Registrazione Rappresentante di Lista
            </div>
            <div className="card-body">
                <p className="text-muted mb-3">
                    Compila il form per richiedere di diventare Rappresentante di Lista per la consultazione: <strong>{registrationStatus.consultation?.nome}</strong>
                </p>

                {/* Eligibility info based on election type */}
                {registrationStatus.consultation?.tipi_elezione?.length > 0 && (
                    <div className="alert alert-info small mb-3">
                        <strong>Requisiti per essere RDL in questa consultazione:</strong>
                        <ul className="mb-0 mt-1">
                            {[...new Set(registrationStatus.consultation.tipi_elezione)].map(tipo => (
                                REQUISITI_ELETTORE[tipo] && (
                                    <li key={tipo}>
                                        <strong>{REQUISITI_ELETTORE[tipo].label}:</strong> {REQUISITI_ELETTORE[tipo].requisito}
                                    </li>
                                )
                            ))}
                        </ul>
                        <hr className="my-2" />
                        <small className="text-muted">
                            <strong>Incompatibilità:</strong> Non possono svolgere funzioni di RDL gli appartenenti alle Forze di Polizia.
                        </small>
                    </div>
                )}

                <p className="text-muted small mb-3">
                    La tua richiesta sarà valutata dal delegato del comune selezionato.
                </p>

                {error && (
                    <div className="alert alert-danger">{error}</div>
                )}

                <form onSubmit={handleSubmit}>
                    {/* Dati personali */}
                    <h6 className="text-muted mb-3">Dati personali</h6>
                    <div className="row">
                        <div className="col-md-6 mb-3">
                            <label htmlFor="cognome" className="form-label">Cognome *</label>
                            <input
                                id="cognome"
                                type="text"
                                className="form-control"
                                name="cognome"
                                value={formData.cognome}
                                onChange={handleChange}
                                required
                                disabled={loading}
                                aria-required="true"
                            />
                        </div>
                        <div className="col-md-6 mb-3">
                            <label htmlFor="nome" className="form-label">Nome *</label>
                            <input
                                id="nome"
                                type="text"
                                className="form-control"
                                name="nome"
                                value={formData.nome}
                                onChange={handleChange}
                                required
                                disabled={loading}
                                aria-required="true"
                            />
                        </div>
                    </div>

                    <div className="row">
                        <div className="col-md-6 mb-3">
                            <label htmlFor="comune_nascita" className="form-label">Comune di nascita *</label>
                            <input
                                id="comune_nascita"
                                type="text"
                                className="form-control"
                                name="comune_nascita"
                                value={formData.comune_nascita}
                                onChange={handleChange}
                                required
                                disabled={loading}
                                aria-required="true"
                            />
                        </div>
                        <div className="col-md-6 mb-3">
                            <label htmlFor="data_nascita" className="form-label">Data di nascita *</label>
                            <input
                                id="data_nascita"
                                type="date"
                                className="form-control"
                                name="data_nascita"
                                value={formData.data_nascita}
                                onChange={handleChange}
                                required
                                disabled={loading}
                                aria-required="true"
                            />
                        </div>
                    </div>

                    {/* Contatti */}
                    <h6 className="text-muted mb-3 mt-3">Contatti</h6>
                    <div className="row">
                        <div className="col-md-6 mb-3">
                            <label htmlFor="email" className="form-label">Indirizzo email *</label>
                            <input
                                id="email"
                                type="email"
                                className="form-control"
                                name="email"
                                value={formData.email}
                                onChange={handleChange}
                                required
                                disabled={loading}
                                aria-required="true"
                                aria-describedby="email-help"
                            />
                        </div>
                        <div className="col-md-6 mb-3">
                            <label htmlFor="telefono" className="form-label">Recapito telefonico *</label>
                            <input
                                id="telefono"
                                type="tel"
                                className="form-control"
                                name="telefono"
                                value={formData.telefono}
                                onChange={handleChange}
                                required
                                disabled={loading}
                                aria-required="true"
                            />
                        </div>
                    </div>

                    {/* Residenza */}
                    <h6 className="text-muted mb-3 mt-3">Residenza</h6>
                    <div className="row">
                        <div className="col-md-6 mb-3">
                            <label htmlFor="comune_residenza" className="form-label">Residente nel Comune di *</label>
                            <input
                                id="comune_residenza"
                                type="text"
                                className="form-control"
                                name="comune_residenza"
                                value={formData.comune_residenza}
                                onChange={handleChange}
                                required
                                disabled={loading}
                                aria-required="true"
                            />
                        </div>
                        <div className="col-md-6 mb-3">
                            <label htmlFor="indirizzo_residenza" className="form-label">Indirizzo di residenza *</label>
                            <input
                                id="indirizzo_residenza"
                                type="text"
                                className="form-control"
                                name="indirizzo_residenza"
                                value={formData.indirizzo_residenza}
                                onChange={handleChange}
                                required
                                disabled={loading}
                                aria-required="true"
                            />
                        </div>
                    </div>

                    {/* Fuorisede */}
                    <h6 className="text-muted mb-3 mt-3">Situazione abitativa</h6>
                    <div className="row">
                        <div className="col-12 mb-3">
                            <label className="form-label">
                                Sei un "fuorisede": lavori o studi in un comune italiano, diverso da quello della tua residenza anagrafica? *
                            </label>
                            <div className="btn-group w-100" role="group" aria-required="true">
                                <input
                                    type="radio"
                                    className="btn-check"
                                    name="fuorisede"
                                    id="fuorisede_si"
                                    value="true"
                                    checked={formData.fuorisede === true}
                                    onChange={() => setFormData(prev => ({ ...prev, fuorisede: true }))}
                                    disabled={loading}
                                />
                                <label className="btn btn-outline-primary" htmlFor="fuorisede_si">
                                    <i className="fas fa-check me-2"></i>SI
                                </label>

                                <input
                                    type="radio"
                                    className="btn-check"
                                    name="fuorisede"
                                    id="fuorisede_no"
                                    value="false"
                                    checked={formData.fuorisede === false}
                                    onChange={() => setFormData(prev => ({ ...prev, fuorisede: false }))}
                                    disabled={loading}
                                />
                                <label className="btn btn-outline-primary" htmlFor="fuorisede_no">
                                    <i className="fas fa-times me-2"></i>NO
                                </label>
                            </div>
                        </div>
                    </div>

                    {/* Domicilio (shown only if fuorisede === true) */}
                    {formData.fuorisede === true && (
                        <>
                            <h6 className="text-muted mb-3 mt-3">Domicilio</h6>
                            <div className="row">
                                <div className="col-md-6 mb-3">
                                    <label htmlFor="comune_domicilio" className="form-label">Comune di domicilio *</label>
                                    <input
                                        id="comune_domicilio"
                                        type="text"
                                        className="form-control"
                                        name="comune_domicilio"
                                        value={formData.comune_domicilio}
                                        onChange={handleChange}
                                        required
                                        disabled={loading}
                                        aria-required="true"
                                    />
                                </div>
                                <div className="col-md-6 mb-3">
                                    <label htmlFor="indirizzo_domicilio" className="form-label">Indirizzo di domicilio *</label>
                                    <input
                                        id="indirizzo_domicilio"
                                        type="text"
                                        className="form-control"
                                        name="indirizzo_domicilio"
                                        value={formData.indirizzo_domicilio}
                                        onChange={handleChange}
                                        required
                                        disabled={loading}
                                        aria-required="true"
                                    />
                                </div>
                            </div>
                        </>
                    )}

                    {/* Dove vuoi fare il RDL */}
                    <h6 className="text-muted mb-3 mt-3">Dove vuoi fare il Rappresentante di Lista?</h6>
                    <div className="alert alert-light border small mb-3" role="note">
                        <strong>Scegli in base alle tue preferenze:</strong> puoi indicare un seggio vicino a dove abiti,
                        dove lavori, o semplicemente dove ti è più comodo recarti il giorno delle elezioni.
                    </div>

                    <div className="row">
                        <div className="col-md-6 mb-3">
                            <label htmlFor="comune_seggio" className="form-label">Comune del seggio *</label>
                            {registrationStatus?.comuni?.length === 1 ? (
                                // Single comune: show as read-only
                                <input
                                    id="comune_seggio"
                                    type="text"
                                    className="form-control"
                                    value={selectedComune?.label || ''}
                                    disabled
                                    readOnly
                                    aria-describedby="comune-seggio-help"
                                />
                            ) : (
                                // Multiple comuni: show autocomplete
                                <ComuneAutocomplete
                                    value={selectedComune}
                                    onChange={handleComuneChange}
                                    disabled={loading}
                                    placeholder="Cerca comune..."
                                    aria-describedby="comune-seggio-help"
                                />
                            )}
                            <small id="comune-seggio-help" className="text-muted">
                                {registrationStatus?.comuni?.length === 1
                                    ? 'Comune pre-selezionato per questa consultazione'
                                    : 'In quale comune vuoi operare come RDL?'}
                            </small>
                        </div>
                        <div className="col-md-6 mb-3">
                            <label htmlFor="municipio" className="form-label">
                                Municipio del seggio {selectedComune?.has_municipi && selectedComune?.municipi?.length > 0 ? '*' : ''}
                            </label>
                            {selectedComune?.has_municipi && selectedComune?.municipi?.length > 0 ? (
                                <select
                                    id="municipio"
                                    className="form-select"
                                    name="municipio"
                                    value={formData.municipio}
                                    onChange={handleChange}
                                    required
                                    disabled={loading}
                                    aria-required="true"
                                    aria-describedby="municipio-help"
                                >
                                    <option value="">-- Seleziona municipio --</option>
                                    {selectedComune.municipi.map((m) => (
                                        <option key={m.numero} value={m.numero}>
                                            {m.nome}
                                        </option>
                                    ))}
                                </select>
                            ) : (
                                <input
                                    id="municipio"
                                    type="text"
                                    className="form-control"
                                    disabled
                                    placeholder={selectedComune ? "Questo comune non ha municipi" : "Seleziona prima un comune"}
                                    aria-describedby="municipio-help"
                                />
                            )}
                            <small id="municipio-help" className="text-muted">
                                {selectedComune?.has_municipi ? 'In quale municipio vuoi operare?' : 'Solo per grandi città (Roma, Milano, Napoli, ecc.)'}
                            </small>
                        </div>
                    </div>

                    <div className="row">
                        <div className="col-md-12 mb-3">
                            <label htmlFor="seggio_preferenza" className="form-label">Seggio o plesso di preferenza</label>
                            {selectedComune ? (
                                <SezzionePlessAutocomplete
                                    value={selectedSezione}
                                    onChange={handleSezioneChange}
                                    disabled={loading}
                                    placeholder="Cerca sezione, plesso o indirizzo..."
                                    comuneId={selectedComune.id}
                                />
                            ) : (
                                <input
                                    id="seggio_preferenza"
                                    type="text"
                                    className="form-control"
                                    disabled
                                    placeholder="Seleziona prima un comune"
                                />
                            )}
                            <small id="seggio-help" className="text-muted">
                                Opzionale: digita per cercare una sezione, plesso, scuola o indirizzo dove preferiresti essere assegnato
                            </small>
                        </div>
                    </div>

                    {/* Privacy GDPR Acceptance */}
                    <div className="form-check mt-4 pt-3 border-top">
                        <input
                            id="gdprAccepted"
                            type="checkbox"
                            className="form-check-input"
                            checked={gdprAccepted}
                            onChange={(e) => setGdprAccepted(e.target.checked)}
                            disabled={loading}
                            aria-required="true"
                        />
                        <label htmlFor="gdprAccepted" className="form-check-label">
                            <strong>Autorizzo il trattamento dei miei dati personali</strong> inseriti in questo modulo.
                            I dati saranno usati solo ai sensi del Decreto Legislativo 30 giugno 2003, n. 196 e del GDPR
                            (Regolamento UE 2016/679) esclusivamente ai fini del coordinamento delle attività degli RDL *
                        </label>
                    </div>

                    <div className="d-flex gap-2 mt-3">
                        <button
                            type="submit"
                            className="btn btn-primary"
                            disabled={loading || !gdprAccepted}
                        >
                            {loading ? 'Invio in corso...' : 'ACCETTO'}
                        </button>
                        <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={onClose}
                            disabled={loading}
                        >
                            Annulla
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

export default RdlSelfRegistration;
