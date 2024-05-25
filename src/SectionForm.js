import React, {useState} from "react";

function SectionForm({section, updateSection, cancel}) {
    const [formData, setFormData] = useState(section);

    const handleChange = (e, field) => {
        const newFormData = {
            ...formData,
            [field]: e.target.value && parseInt(e.target.value, 10) >= 0 ? parseInt(e.target.value, 10) : ''
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
                    </div>
                    <div className="form-group mb-3">
                        <label>N. Elettori Donne:</label>
                        <input
                            type="number"
                            className="form-control"
                            value={formData.nElettoriDonne}
                            onChange={(e) => handleChange(e, "nElettoriDonne")}
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
                    </div>
                    <div className="form-group mb-3">
                        <label>Schede Autenticate:</label>
                        <input
                            type="number"
                            className="form-control"
                            value={formData.schedeAutenticate}
                            onChange={(e) => handleChange(e, "schedeAutenticate")}
                        />
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
                    </div>
                    <div className="form-group mb-3">
                        <label>Schede Nulle:</label>
                        <input
                            type="number"
                            className="form-control"
                            value={formData.schedeNulle}
                            onChange={(e) => handleChange(e, "schedeNulle")}
                        />
                    </div>
                    <div className="form-group mb-3">
                        <label>Schede Contestate e Verbalizzate:</label>
                        <input
                            type="number"
                            className="form-control"
                            value={formData.schedeContestate}
                            onChange={(e) => handleChange(e, "schedeContestate")}
                        />
                    </div>
                </div>
            </div>
            <div className="card mt-3">
                <div className="card-header">
                    Preferenze
                </div>
                <div className="card-body">
                    {[
                        "Morace Carolina",
                        "Tamburrano Dario",
                        "Ferrara Gianluca",
                        "Basile Giovanna",
                        "Esposito Giusy",
                        "Fazio Valentina",
                        "Lauretti Federica",
                        "Pacetti Giuliano",
                        "Volpi Stefania",
                        "Romagnoli Sergio",
                        "Emiliozzi Mirella",
                        "Pococacio Valentina",
                        "Ceccato Emanuele",
                        "Alloatti Luca",
                        "Cecere Stefano",
                    ].map((name) => (
                        <div className="form-group mb-3" key={name}>
                            <label>{name}:</label>
                            <input
                                type="number"
                                className="form-control"
                                value={formData[name]}
                                onChange={(e) => handleChange(e, name)}
                                min="0"
                            />
                        </div>
                    ))}
                </div>
            </div>
            <div className="card mt-3">
                <div className="card-header">
                    Voti di Lista
                </div>
                <div className="card-body">
                    {[
                        "MOVIMENTO 5 STELLE",
                        "FRATELLI D'ITALIA",
                        "FORZA ITALIA-NOI MODERATI",
                        "LEGA SALVINI PREMIER",
                        "PARTITO DEMOCRATICO",
                        "ALLEANZA VERDI E SINISTRA",
                        "ALTERNATIVA POPOLARE",
                        "STATI UNITI D'EUROPA",
                        "DEMOCRAZIA POPOLARE SOVRANA",
                        "PACE TERRA DIGNITA'",
                        "AZIONE-SIAMO EUROPEI",
                    ].map((lista) => (
                        <div className="form-group mb-3" key={lista}>
                            <label
                                style={{
                                    backgroundColor: listaColors[lista] || "white",
                                    color: listaColors[lista] ? "white" : "black",
                                    padding: "5px",
                                }}
                            >{lista}:</label>
                            <input
                                type="number"
                                className="form-control"
                                value={formData[lista]}
                                onChange={(e) => handleChange(e, lista)}
                            />
                        </div>
                    ))}
                </div>
            </div>
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
