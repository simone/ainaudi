import React, {useEffect, useState} from "react";
import '@fortawesome/fontawesome-free/css/all.min.css';

function SectionForm({lists, candidates, section, updateSection, cancel}) {
    const [formData, setFormData] = useState(section);
    const [errors, setErrors] = useState(
        Object.keys(section).reduce((acc, key) => {
            acc[key] = '';
            return acc;
        }, {})
    );

    const validation = (field, value) => {
        let error = '';
        const nElettoriMaschi = parseInt(formData.nElettoriMaschi) || 0;
        const nElettoriDonne = parseInt(formData.nElettoriDonne) || 0;
        const totalElettori = nElettoriMaschi + nElettoriDonne;
        const votiDiLista = lists.reduce((sum, name) => sum + (parseInt(formData[name]) || 0), 0);
        const votiDiPreferenza = candidates.reduce((sum, name) => sum + (parseInt(formData[name]) || 0), 0);

        switch (field) {
            case "schedeRicevute":
                if (value < totalElettori) {
                    error = 'Il presidente deve fare la richiesta per avere le schede sufficienti a tutti gli elettori (' + value + ' < ' + totalElettori + ')';
                }
                break;
            case "schedeAutenticate":
                if (value > formData.schedeRicevute) {
                    error = 'Impossibile autenticare più schede di quelle ricevute (' + value + ' > ' + formData.schedeRicevute + ')';
                }
                if (value > totalElettori) {
                    error = 'Il presidente non deve autenticare più schede del numero di elettori (' + value + ' > ' + totalElettori + ')';
                }
                break;
            case "schedeContestate":
                const schedeBianche = parseInt(formData.schedeBianche) || 0;
                const schedeNulle = parseInt(formData.schedeNulle) || 0;
                const schedeContestate = parseInt(formData.schedeContestate) || 0;
                const totalSchede = schedeBianche + schedeNulle + schedeContestate + votiDiLista;
                if (totalSchede > totalElettori) {
                    error = 'Il totale delle schede scrutinate (Bianche, Nulle, Contestate e totale voti di lista) NON DEVE ESSERE maggiore al numero dei votanti. (' + totalSchede + ' > ' + totalElettori + ')';
                }
                if (totalSchede < totalElettori) {
                    error = 'Probabilmente mancano dei voti di lista o delle schede perché il totale delle schede scrutinate (Bianche, Nulle, Contestate e totale voti di lista) non è uguale al numero dei votanti. (' + totalSchede + ' < ' + totalElettori + ')';
                }
                break;
            case "AZIONE-SIAMO EUROPEI":
                // TODO: spostare totto il campo TOTALE VOTI DI LISTA
                if (votiDiLista > totalElettori) {
                    error = 'Il totale dei voti di lista non può essere maggiore del numero dei votanti (' + votiDiLista + ' > ' + totalElettori + ')';
                }
                break;
            case "Cecere Stefano":
                // TODO: spostare totto il campo TOTALE VOTI DI PREFERENZA
                if (votiDiPreferenza > totalElettori * 3) {
                    error = 'Visto che un elettore può votare fino a 3 candidati, il totale dei voti di preferenza non può essere maggiore del triplo del numero dei votanti (' + votiDiPreferenza + ' > ' + totalElettori * 3 + ')';
                }
            default:
                break;
        }

        return error;
    };

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
        setFormData(newFormData);
    };

    const handleSave = () => {
        updateSection(formData);
    };

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
                            value={+formData.nElettoriMaschi + +formData.nElettoriDonne}
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
                            value={formData.nElettoriMaschi}
                            onChange={(e) => handleChange(e, "nElettoriMaschi")}
                        />
                        {errors['nElettoriMaschi'] && <div className="text-danger">{errors['nElettoriMaschi']}</div>}
                    </div>
                    <div className="form-group mb-3">
                        <label>N. VOTANTI Donne:</label>
                        <input
                            type="number"
                            className="form-control"
                            value={formData.nElettoriDonne}
                            onChange={(e) => handleChange(e, "nElettoriDonne")}
                        />
                        {errors['nElettoriDonne'] && <div className="text-danger">{errors['nElettoriDonne']}</div>}
                    </div>
                    <div className="form-group mb-3">
                        <label>N. VOTANTI Totali:</label>
                        <input
                            type="number"
                            className="form-control"
                            value={+formData.nElettoriMaschi + +formData.nElettoriDonne}
                            readOnly
                            style={{backgroundColor: 'lightgray'}}
                        />
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
                            value={candidates.reduce((sum, name) => {
                                return sum + (parseInt(formData[name]) || 0);
                            }, 0)}
                            readOnly
                            style={{backgroundColor: 'lightgray'}}
                        />
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
                            value={lists.reduce((sum, name) => {
                                return sum + (parseInt(formData[name]) || 0);
                            }, 0)}
                            readOnly
                            style={{backgroundColor: 'lightgray'}}
                        />
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
                            required
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
                </div>
            </div>
        </form>
    );
}

export default SectionForm;
