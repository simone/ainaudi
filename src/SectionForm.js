import React, {useEffect, useState} from "react";
import '@fortawesome/fontawesome-free/css/all.min.css';

function SectionForm({lists, candidates, section, updateSection, cancel}) {
    const initialState = {...section, ...
            {
                totalElettori: +section.nElettoriMaschi + +section.nElettoriDonne,
                totalVotanti: +section.nVotantiMaschi + +section.nVotantiDonne,
                totalVotiDiLista: lists.reduce((sum, name) => sum + (parseInt(section[name]) || 0), 0),
                totalVotiDiPreferenza: candidates.reduce((sum, name) => sum + (parseInt(section[name]) || 0), 0),
            }
    };
    const [formData, setFormData] = useState(initialState);
    const [errors, setErrors] = useState({});
    const [isSaving, setIsSaving] = useState(false);
    const validation = (field, value) => {
        let error = '';
        switch (field) {
            case "schedeRicevute":
                if (value && +value < +formData.totalElettori) {
                    error = 'Il presidente deve fare la richiesta per avere le schede sufficienti a tutti gli elettori (' + value + ' < ' + formData.totalElettori + ')';
                }
                break;
            case "schedeAutenticate":
                if (value && +value > +formData.schedeRicevute) {
                    error = 'Impossibile autenticare più schede di quelle ricevute (' + value + ' > ' + formData.schedeRicevute + ')';
                }
                if (value && +value > +formData.totalElettori) {
                    error = 'Il presidente non deve autenticare più schede del numero di elettori (' + value + ' > ' + formData.totalElettori + ')';
                }
                break;
            case "schedeContestate":
                const schedeBianche = parseInt(formData.schedeBianche) || 0;
                const schedeNulle = parseInt(formData.schedeNulle) || 0;
                const schedeContestate = parseInt(formData.schedeContestate) || 0;
                const totalSchede = schedeBianche + schedeNulle + schedeContestate + formData.totalVotiDiLista;
                if (totalSchede > +formData.totalVotanti) {
                    error = 'Il totale delle schede scrutinate (Bianche, Nulle, Contestate e totale voti di lista) NON DEVE ESSERE maggiore al numero dei votanti. (' + totalSchede + ' > ' + formData.totalVotanti + ')';
                }
                if (totalSchede < +formData.totalVotanti) {
                    error = 'Probabilmente mancano dei voti di lista o delle schede perché il totale delle schede scrutinate (Bianche, Nulle, Contestate e totale voti di lista) non è uguale al numero dei votanti. (' + totalSchede + ' < ' + formData.totalVotanti + ')';
                }
                break;
            case "totalVotiDiLista":
                if (value > 0 && +value > +formData.totalVotanti) {
                    error = 'Il totale dei voti di lista non può essere maggiore del numero dei votanti (' + value + ' > ' + formData.totalVotanti + ')';
                }
                break;
            case "totalVotiDiPreferenza":
                if (value > 0 && +value > +formData.totalVotanti * 3) {
                    error = 'Visto che un elettore può votare fino a 3 candidati, il totale dei voti di preferenza non può essere maggiore del triplo del numero dei votanti (' + value + ' > ' + formData.totalVotanti * 3 + ')';
                }
                case "totalVotanti":
                if (value > 0 && +value > +formData.totalElettori) {
                    error = 'Il totale dei votanti non può essere maggiore del numero degli elettori (' + value + ' > ' + formData.totalElettori + ')';
                }
            default:
                break;
        }

        return error;
    };

    useEffect(() => {
        window.scrollTo(0, 0);

        const handleWheel = (e) => {
            if (document.activeElement.type === "number" && document.activeElement === e.target) {
                e.preventDefault();
            }
        };

        // Aggiungi l'evento wheel al window
        window.addEventListener('wheel', handleWheel, { passive: false });

        // Rimuovi l'evento wheel quando il componente viene smontato
        return () => {
            window.removeEventListener('wheel', handleWheel);
        };
    }, []);

    useEffect(() => {
        const newErrors = {};
        for (const key in formData) {
            newErrors[key] = validation(key, formData[key]);
        }
        setErrors(newErrors);
    }, [formData]);

    const handleChange = (e, field) => {
        let value = e.target.value;
        if (value !== "") {
            if (value < 0) {
                value = 0;
            }
            value = parseInt(value, 10);
        }
        const newFormData = {
            ...formData,
            [field]: value && parseInt(value, 10) >= 0 ? parseInt(value, 10) : ''
        };

        newFormData.totalElettori = +newFormData.nElettoriMaschi + +newFormData.nElettoriDonne;
        newFormData.totalVotanti = +newFormData.nVotantiMaschi + +newFormData.nVotantiDonne;
        newFormData.totalVotiDiLista = lists.reduce((sum, name) => sum + (parseInt(newFormData[name]) || 0), 0);
        newFormData.totalVotiDiPreferenza = candidates.reduce((sum, name) => sum + (parseInt(newFormData[name]) || 0), 0);

        setFormData(newFormData);
    };

    const handleSave = () => {
        if (isSaving) {
            // Blocca ulteriori salvataggi
            console.log('Salvataggio in corso...');
            return;
        }
        setIsSaving(true); // Imposta il flag di salvataggio
        if (Object.values(formData).every(value => value === '')) {
            console.log('Tutti i campi sono vuoti, forse è stato un errore');
            cancel();
            return;
        }
        updateSection(formData, errorsList);
    };

    useEffect(() => {
        // Funzione che verrà chiamata quando l'evento popstate viene attivato
        window.history.pushState(null, null, window.location.pathname);
        const onPopState = (event) => {
            handleBack();
        };

        // Aggiungi il listener per l'evento popstate
        window.addEventListener('popstate', onPopState);
        return () => {
            // Rimuovi il listener quando il componente viene smontato
            window.removeEventListener('popstate', onPopState);
        };
    }, []);

    const handleBack = () => {
        cancel();
    }

    const errorsList = Object.values(errors).filter(value => value !== '');

    return (
        <form>
            <div className="card">
                <div className="card-header bg-info">
                    Compilare tutti i campi richiesti con i numeri presi nel seggio.
                </div>
            </div>
            <div className="card">
                <div className="card-header bg-secondary">
                    Informazioni Generali
                </div>
                <div className="card-body">
                    <div className="form-group mb-3">
                        <label>Comune:</label>
                        <input
                            type="text"
                            className="form-control"
                            value={formData.comune}
                            readOnly
                            style={{backgroundColor: 'lightgray'}}
                        />
                    </div>
                    <div className="form-group mb-3">
                        <label>Sezione:</label>
                        <input
                            type="text"
                            className="form-control"
                            value={formData.sezione}
                            readOnly
                            style={{backgroundColor: 'lightgray'}}
                        />
                    </div>
                    <div className="form-group mb-3">
                        <label>Email RDL:</label>
                        <input
                            type="text"
                            className="form-control"
                            value={formData.email}
                            readOnly
                            style={{backgroundColor: 'lightgray'}}
                        />
                    </div>
                </div>
            </div>
            <div className="card mt-3">
                <div className="card-header bg-success">
                    Raccolta Dati preparazione Seggio
                </div>
                <div className="card-body">
                    <div className="form-group mb-3">
                        <label>N. Elettori Maschi:</label>
                        <input
                            type="number"
                            className="form-control"
                            value={formData.nElettoriMaschi}
                            onChange={(e) => handleChange(e, "nElettoriMaschi")}
                        />
                        {errors['nElettoriMaschi'] && <div className="text-danger">{errors['nElettoriMaschi']}</div>}
                    </div>
                    <div className="form-group mb-3">
                        <label>N. Elettori Donne:</label>
                        <input
                            type="number"
                            className="form-control"
                            value={formData.nElettoriDonne}
                            onChange={(e) => handleChange(e, "nElettoriDonne")}
                        />
                        {errors['nElettoriDonne'] && <div className="text-danger">{errors['nElettoriDonne']}</div>}
                    </div>
                    <div className="form-group mb-3">
                        <label>N. Elettori Totali:</label>
                        <input
                            type="number"
                            className="form-control"
                            value={formData.totalElettori}
                            readOnly
                            style={{backgroundColor: 'lightgray'}}
                        />
                    </div>
                    <div className="form-group mb-3">
                        <label>Schede Ricevute:</label>
                        <input
                            type="number"
                            className="form-control"
                            value={formData.schedeRicevute}
                            onChange={(e) => handleChange(e, "schedeRicevute")}
                        />
                        {errors['schedeRicevute'] && <div className="text-danger">{errors['schedeRicevute']}</div>}
                    </div>
                    <div className="form-group mb-3">
                        <label>Schede Autenticate:</label>
                        <input
                            type="number"
                            className="form-control"
                            value={formData.schedeAutenticate}
                            onChange={(e) => handleChange(e, "schedeAutenticate")}
                        />
                        {errors['schedeAutenticate'] && <div className="text-danger">{errors['schedeAutenticate']}</div>}
                    </div>
                </div>
            </div>
            <div className="card mt-3">
                <div className="card-header">
                    Raccolta Dati Scrutinio
                </div>
                <div className="card-body">
                    <div className="form-group mb-3">
                        <label>N. VOTANTI Maschi:</label>
                        <input
                            type="number"
                            className="form-control"
                            value={formData.nVotantiMaschi}
                            onChange={(e) => handleChange(e, "nVotantiMaschi")}
                        />
                        {errors['nVotantiMaschi'] && <div className="text-danger">{errors['nVotantiMaschi']}</div>}
                    </div>
                    <div className="form-group mb-3">
                        <label>N. VOTANTI Donne:</label>
                        <input
                            type="number"
                            className="form-control"
                            value={formData.nVotantiDonne}
                            onChange={(e) => handleChange(e, "nVotantiDonne")}
                        />
                        {errors['nVotantiDonne'] && <div className="text-danger">{errors['nVotantiDonne']}</div>}
                    </div>
                    <div className="form-group mb-3">
                        <label>N. VOTANTI Totali:</label>
                        <input
                            type="number"
                            className="form-control"
                            value={+formData.totalVotanti}
                            readOnly
                            style={{backgroundColor: 'lightgray'}}
                        />
                        {errors['totalVotanti'] && <div className="text-danger">{errors['totalVotanti']}</div>}
                    </div>
                </div>
            </div>
            <div className="card mt-3">
                <div className="card-header">
                    Preferenze
                </div>
                <div className="card-body">
                    {candidates.map((name) => (
                        <div className="form-group mb-3" key={name}>
                            <label>{name}:</label>
                            <input
                                type="number"
                                className="form-control"
                                value={formData[name]}
                                onChange={(e) => handleChange(e, name)}
                                min="0"
                            />
                            {errors[name] && <div className="text-danger">{errors[name]}</div>}
                        </div>
                    ))}
                    <div className="form-group mb-3">
                        <label>TOTALE VOTI DI PREFERENZA</label>
                        <input
                            type="number"
                            className="form-control"
                            value={formData.totalVotiDiPreferenza}
                            readOnly
                            style={{backgroundColor: 'lightgray'}}
                        />
                        {errors['totalVotiDiPreferenza'] && <div className="text-danger">{errors['totalVotiDiPreferenza']}</div>}
                    </div>
                </div>
            </div>
            <div className="card mt-3">
                <div className="card-header">
                    Voti di Lista
                </div>
                <div className="card-body">
                    {lists.map((l) => (
                        <div className="form-group mb-3" key={l}>
                            <label>{l}:</label>
                            {l === "MOVIMENTO 5 STELLE" && (
                                <small className="text-muted" style={{
                                    paddingLeft: '.5em',
                                }}>
                                    <i className="fas fa-star yellow-star"></i>
                                    <i className="fas fa-star yellow-star"></i>
                                    <i className="fas fa-star yellow-star"></i>
                                    <i className="fas fa-star yellow-star"></i>
                                    <i className="fas fa-star yellow-star"></i>
                                </small>
                            )}
                            <input
                                type="number"
                                className="form-control"
                                value={formData[l]}
                                onChange={(e) => handleChange(e, l)}
                            />
                            {errors[l] && <div className="text-danger">{errors[l]}</div>}
                        </div>
                    ))}
                    <div className="form-group mb-3">
                        <label>TOTALE VOTI DI LISTA</label>
                        <input
                            type="number"
                            className="form-control"
                            value={formData.totalVotiDiLista}
                            readOnly
                            style={{backgroundColor: 'lightgray'}}
                        />
                        {errors['totalVotiDiLista'] && <div className="text-danger">{errors['totalVotiDiLista']}</div>}
                    </div>
                </div>
            </div>
            <div className="card mt-3">
                <div className="card-header">
                    Schede
                </div>
                <div className="card-body">
                    <div className="form-group mb-3">
                        <label>Schede Bianche:</label>
                        <input
                            type="number"
                            className="form-control"
                            value={formData.schedeBianche}
                            onChange={(e) => handleChange(e, "schedeBianche")}
                        />
                        {errors['schedeBianche'] && <div className="text-danger">{errors['schedeBianche']}</div>}
                    </div>
                    <div className="form-group mb-3">
                        <label>Schede Nulle:</label>
                        <input
                            type="number"
                            className="form-control"
                            value={formData.schedeNulle}
                            onChange={(e) => handleChange(e, "schedeNulle")}
                        />
                        {errors['schedeNulle'] && <div className="text-danger">{errors['schedeNulle']}</div>}
                    </div>
                    <div className="form-group mb-3">
                        <label>Schede Contestate e Verbalizzate:</label>
                        <input
                            type="number"
                            className="form-control"
                            value={formData.schedeContestate}
                            onChange={(e) => handleChange(e, "schedeContestate")}
                        />
                        {errors['schedeContestate'] && <div className="text-danger">{errors['schedeContestate']}</div>}
                    </div>
                </div>
            </div>
            {errorsList.length > 0 && (
                <div className="alert alert-warning mt-3" role="alert">
                    Incongruenze o non completezza dei dati inseriti:
                    <ul>
                    {errorsList.map((error, index) => (
                        <li key={index}>{error}</li>
                    ))}
                    </ul>
                    E' comunque possibile INVIARE i dati.
                </div>
            )}
            <div className="card">
                <div className="card-body">
                    {!isSaving && (
                        <div className="row mt-3">
                            <div className="col-6">
                                <button type="button" className="btn btn-secondary w-100" onClick={handleBack}>
                                    Indietro
                                </button>
                            </div>
                            <div className="col-6">
                                <button type="button" className="btn btn-success w-100" onClick={handleSave}>
                                    Invia dati
                                </button>
                            </div>
                        </div>
                    )}
                    {isSaving && (
                        <div className="row mt-3">
                            <div className="col-6">
                                <button type="button" className="btn btn-secondary w-100" disabled={true}>
                                    Indietro
                                </button>
                            </div>
                            <div className="col-6">
                                <button type="button" className="btn btn-success w-100" disabled={true}>
                                    Invia dati
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </form>
    );
}

export default SectionForm;
