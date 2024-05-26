import React, {useEffect, useState} from "react";

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

        switch (field) {
            case "schedeAutenticate":
                if (value > formData.schedeRicevute) {
                    error = 'Impossibile autenticare più schede di quelle ricevute (' + value + ' > ' + formData.schedeRicevute + ')';
                }
                break;
            case "schedeContestate":
                const schedeBianche = parseInt(formData.schedeBianche) || 0;
                const schedeNulle = parseInt(formData.schedeNulle) || 0;
                const schedeContestate = parseInt(formData.schedeContestate) || 0;
                const totalSchede = schedeBianche + schedeNulle + schedeContestate + lists.reduce((sum, name) => sum + (parseInt(formData[name]) || 0), 0);
                if (totalSchede > totalElettori) {
                    error = 'Bianche+nulle+contestate + voti di lista > elettori M e F (' + totalSchede + ' > ' + totalElettori + ')';
                }
                if (totalSchede < totalElettori) {
                    error = 'Bianche+nulle+contestate + voti di lista < elettori M e F (' + totalSchede + ' < ' + totalElettori + ')';
                }
                break;
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

    const listaColors = {
        'MOVIMENTO 5 STELLE': '#FF0000',
    };

    const errorsList = Object.values(errors).filter(value => value !== '');

    return (
        <form>
            <div className="card">
                <div className="card-header bg-info">
                    Compilare tutti i campi richiesti con i numeri presi nel seggio.
                </div>
            </div>
            <div className="card">
                <div className="card-header">
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
                <div className="card-header">
                    Elettori
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
                </div>
            </div>
            <div className="card mt-3">
                <div className="card-header">
                    Schede
                </div>
                <div className="card-body">
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
                            <label
                                style={{
                                    backgroundColor: listaColors[l] || "white",
                                    color: listaColors[l] ? "white" : "black",
                                    padding: "5px",
                                }}
                            >{l}:</label>
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
