import React, {useState} from "react";

function SectionForm({lists, candidates, section, updateSection, cancel}) {
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
                        </div>
                    ))}
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
