import React, {useEffect, useState} from 'react';

function ReferentiComponent({client}) {
    const [assignedSezioni, setAssignedSezioni] = useState([]);
    const [filterAssigned, setFilterAssigned] = useState([]);
    const [unassignedSezioni, setUnassignedSezioni] = useState([]);
    const [filterUnassigned, setFilterUnassigned] = useState([]);
    const [datiData, setDatiData] = useState([]);
    const [referentiData, setReferentiData] = useState([]);
    const [sezioniData, setSezioniData] = useState([]);
    const [selectedSezione, setSelectedSezione] = useState(null);
    const [emailRDL, setEmailRDL] = useState("");
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadDatiData();
        loadSezioniData();
        loadReferentiData()
    }, []);

    useEffect(() => {
        let sezioni = sezioniData.filter(row => {
            return referentiData.some(referente =>
                referente[1] === row[1] // Comune
                && referente[2] === row[2]); // Municipio
        });
        const filtered = sezioni.map(sezione => {
            const found = datiData.find(row => row[0] === sezione[1] && row[1] === sezione[0]);
            return {...sezione, emailRDL: found ? found[2] : ""};
        }).sort((a, b) => a[1].localeCompare(b[1])); // Ordina alfabeticamente per il secondo elemento (nome sezione)

        const assigned = filtered.filter(sezione => sezione.emailRDL);
        const unassigned = filtered.filter(sezione => !sezione.emailRDL);
        setAssignedSezioni(assigned);
        setUnassignedSezioni(unassigned);

    }, [loading, referentiData, sezioniData, datiData]);

    useEffect(() => {
        setFilterUnassigned(unassignedSezioni);
    }, [unassignedSezioni]);

    useEffect(() => {
        setFilterAssigned(assignedSezioni);
    }, [assignedSezioni]);

    const loadDatiData = () => {
        client.get({ range: 'Dati!A2:C' })
            .then(data => {
                if (data.values && data.values.length > 0) {
                    setDatiData(data.values);
                }
                setLoading(false);
            }).catch(error => {
            console.error("Error fetching dati data:", error);
        });
    };

    const loadSezioniData = () => {
        client.get({
            range: "Sezioni!A2:C",
        }).then((response) => {
            const rows = response.values;
            if (rows && rows.length > 0) {
                setSezioniData(rows);
            }
        }).catch(error => {
            console.error("Error fetching sezioni data:", error);
        });
    };

    const loadReferentiData = () => {
        client.get({
            range: "Referenti!A2:C",
        }).then((response) => {
            const rows = response.values;
            if (rows && rows.length > 0) {
                const referentiSections = rows.filter(row => row[0] === client.email);
                setReferentiData(referentiSections);
            }
        }).catch(error => {
            console.error("Error fetching referenti data:", error);
        });
    };

    const handleSezioneClick = (sezione) => {
        setSelectedSezione(sezione);
        const found = datiData.find(row => row[0] === sezione[1] && row[1] === sezione[0]);
        setEmailRDL(found ? found[2] : "");
    };

    const handleEmailChange = (e) => {
        setEmailRDL(e.target.value);
    };

    const handleSave = (sezione, remove) => {
        const existingRecordIndex = datiData.findIndex(
            row => row[0] === sezione[1] && row[1] === sezione[0]
        );

        if (existingRecordIndex !== -1) {
            // Record exists, update the email
            const range = `Dati!C${existingRecordIndex + 2}`;
            client.update({
                    range: range,
                    valueInputOption: "RAW",
                    values: [[remove ? '' : emailRDL]] })
                .then(data => {
                    console.log("Updated sheets data:", data);
                    loadDatiData(); // Refresh the data
                    setSelectedSezione(null);
                }).catch(error => {
                console.error("Error updating sheets data:", error);
            });
        } else {
            // Record does not exist, append a new row
            client.append({
                    range: "Dati!A:C",
                    valueInputOption: "RAW",
                    values: [[sezione[1], sezione[0], remove ? '' : emailRDL]],
                })
                .then(data => {
                    console.log("Appended sheets data:", data);
                    loadDatiData(); // Refresh the data
                    setSelectedSezione(null);
                }).catch(error => {
                console.error("Error appending sheets data:", error);
            });
        }
    };

    const changeUnassignedFilter = (e) => {
        const value = e.target.value;
        setFilterUnassigned(unassignedSezioni.filter(sezione => {
            return sezione[0].toLowerCase().includes(value.toLowerCase());
        }));
    }

    const changeAssignedFilter = (e) => {
        const value = e.target.value;
        setFilterAssigned(assignedSezioni.filter(sezione => {
            return sezione[0].toLowerCase().includes(value.toLowerCase())
                || sezione.emailRDL.toLowerCase().includes(value.toLowerCase());
        }));
    }

    const getUniqueEmails = () => {
        let sezioni = sezioniData.filter(row => {
            return referentiData.some(referente =>
                referente[1] === row[1] // Comune
                && referente[2] === row[2]); // Municipio
        }).map(sezione => sezione[0]);
        const emails = new Set(datiData
            .filter(row => sezioni.includes(row[1]))
            .map(row => row[2]));
        emails.add(client.email);
        return [...emails];
    };

    if (loading) {
        return <div className="card-body d-flex align-items-center justify-content-center"
                    style={{minHeight: '50vh'}}>
            <div className="spinner-border text-primary" role="status">
                <span className="visually-hidden">Loading...</span>
            </div>
        </div>;
    }

    return (
        <>
            <div className="card">
                <div className="card-header bg-info">
                    Assegna un RDL a ciascuna sezione inserendo l'email del responsabile. Assicurati
                    che
                    ogni sezione abbia un RDL e aggiorna le assegnazioni se necessario.
                </div>
            </div>
            {unassignedSezioni.length > 0 && (
                <div className="card">
                    <div className="card-header bg-secondary">
                        Sezioni Non Assegnate
                    </div>
                    <input type="search"
                           className="form-control"
                           placeholder="Filtra tramite sezione..."
                           onChange={changeUnassignedFilter}
                    />
                    <div className="list-group">
                        {filterUnassigned.map((sezione, index) => (
                            <div key={index}>
                                {selectedSezione === sezione && (
                                    <div className="card">
                                        <div className="card-header bg-success">
                                            {sezione[1]} {sezione[2]} - {sezione[0]}
                                        </div>
                                        <div className="card-body">
                                            <div className="form-group">
                                                <input
                                                    type="email"
                                                    className="form-control"
                                                    list="rdl-emails"
                                                    value={emailRDL}
                                                    onChange={handleEmailChange}
                                                    required
                                                    name="nope"
                                                    autoComplete="off"
                                                />
                                                <datalist id="rdl-emails">
                                                    {getUniqueEmails().map((email, index) => (
                                                        <option key={index} value={email}/>
                                                    ))}
                                                </datalist>
                                            </div>
                                        </div>
                                        <div className="card-footer">
                                            <div className="row mt-3">
                                                <div className="col-12">
                                                    <button type="button" className="btn btn-success w-100"
                                                            onClick={() => handleSave(selectedSezione, false)}>
                                                        Assegna
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                ) || (
                                    <div onClick={() => handleSezioneClick(sezione)}
                                         style={{
                                             cursor: "pointer"
                                         }}
                                         className="list-group-item list-group-item-action flex-column align-items-start">
                                        <h5 className="mb-1">
                                            {sezione[1]} {sezione[2]} - {sezione[0]}
                                        </h5>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}
            {assignedSezioni.length > 0 && (
                <div className="card">
                    <div className="card-header">
                        Sezioni Assegnate
                    </div>
                    <input type="search"
                           className="form-control"
                           placeholder="Filtra tramite sezione o RDL..."
                           onChange={changeAssignedFilter}
                    />
                    <div className="list-group">
                        {filterAssigned.map((sezione, index) => (
                            <div key={index}>
                                {selectedSezione === sezione && (
                                    <div className="card">
                                        <div className="card-header bg-success">
                                            {sezione[1]} {sezione[2]} - {sezione[0]}
                                        </div>
                                        <div className="card-body">
                                            <div className="form-group">
                                                <input
                                                    type="email"
                                                    className="form-control"
                                                    list="rdl-emails"
                                                    value={emailRDL}
                                                    onChange={handleEmailChange}
                                                    required
                                                    name="nope"
                                                    autoComplete="off"
                                                />
                                                <datalist id="rdl-emails">
                                                    {getUniqueEmails().map((email, index) => (
                                                        <option key={index} value={email}/>
                                                    ))}
                                                </datalist>
                                            </div>
                                        </div>
                                        <div className="card-footer">
                                            <div className="row mt-3">
                                                <div className="col-6">
                                                    <button type="button" className="btn btn-secondary w-100"
                                                            onClick={() => handleSave(selectedSezione, true)}>
                                                        Rimuovi
                                                    </button>
                                                </div>
                                                <div className="col-6">
                                                    <button type="button" className="btn btn-success w-100"
                                                            onClick={() => handleSave(selectedSezione, false)}>
                                                        Assegna
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                ) || (
                                    <div onClick={() => handleSezioneClick(sezione)}
                                         style={{
                                             cursor: "pointer"
                                         }}
                                         className="list-group-item list-group-item-action flex-column align-items-start">
                                        <h5 className="mb-1">
                                            {sezione[1]} {sezione[2]} - {sezione[0]}
                                        </h5>
                                        <div className="mb-1">
                                            {sezione.emailRDL}
                                        </div>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </>
    );

}

export default ReferentiComponent;
