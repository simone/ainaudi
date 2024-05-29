import React, {useEffect, useState} from 'react';

function RdlList({client, setError}) {
    const [assigned, setAssigned] = useState([]);
    const [unassigned, setUnassigned] = useState([]);
    const [assignedFilter, setAssignedFilter] = useState('');
    const [unassignedFilter, setUnassignedFilter] = useState('');
    const [filteredAssigned, setFilteredAssigned] = useState([]);
    const [filteredUnassigned, setFilteredUnassigned] = useState([]);
    const [emails, setEmails] = useState([]);
    const [selected, setSelected] = useState(null);
    const [emailRDL, setEmailRDL] = useState("");
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        window.scrollTo(0, 0);
        loadSezioniData();
        loadEmails();
    }, []);

    const loadSezioniData = () => {
        client.rdl.sections().then((response) => {
            setAssigned(response.assigned);
            setUnassigned(response.unassigned)
            setLoading(false)
        }).catch(error => {
            setError(error);
            console.error("Error fetching sezioni data:", error);
        });
    };

    const loadEmails = () => {
        client.rdl.emails().then((response) => {
            setEmails(response.emails)
        });
    }

    const handleSezioneClick = (sezione) => {
        setSelected(sezione);
        setEmailRDL(sezione[2] ? sezione[2] : "");
    };

    const handleEmailChange = (e) => {
        setEmailRDL(e.target.value);
    };

    const handleSave = (sezione, remove) => {
        const email = emailRDL;
        if (remove) {
            setAssigned(assigned.filter(s => s !== sezione));
            setUnassigned([...unassigned, [sezione[0], sezione[1], '']]);
        } else {
            setUnassigned(unassigned.filter(s => s !== sezione));
            if (assigned.find(s => s === sezione)) {
                setAssigned(assigned.map(s => s === sezione ? [sezione[0], sezione[1], email] : s));
            } else {
                setAssigned([...assigned, [sezione[0], sezione[1], email]]);
            }
        }
        setSelected(null);
        setEmailRDL("");
        (remove ? client.rdl.unassign({
            comune: sezione[0],
            sezione: sezione[1]
        }) : client.rdl.assign({
            comune: sezione[0],
            sezione: sezione[1],
            email: email
        })).then(() => {
            loadSezioniData();
        });
    };

    const changeUnassignedFilter = (e) => {
        setUnassignedFilter(e.target.value)
    }

    useEffect(() => {
        if (!unassignedFilter) {
            setFilteredUnassigned(unassigned);
            return;
        }
        setFilteredUnassigned(unassigned.filter(sezione => {
            return sezione[1].toLowerCase().includes(unassignedFilter.toLowerCase());
        }).sort((a, b) => a[1].localeCompare(b[1]) || a[2].localeCompare(b[2]) || a[0].localeCompare(b[0])));
    }, [unassignedFilter, unassigned]);

    const changeAssignedFilter = (e) => {
        setAssignedFilter(e.target.value)
    }

    useEffect(() => {
        if (!assignedFilter) {
            setFilteredAssigned(assigned);
            return;
        }
        setFilteredAssigned(assigned.filter(sezione => {
            return sezione[1].toLowerCase().includes(assignedFilter.toLowerCase()) || sezione[2].toLowerCase().includes(assignedFilter.toLowerCase());
        }).sort((a, b) => a[1].localeCompare(b[1]) || a[2].localeCompare(b[2]) || a[0].localeCompare(b[0])));
    }, [assignedFilter, assigned]);

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
                    che ogni sezione abbia un RDL e aggiorna le assegnazioni se necessario.
                </div>
            </div>
            {unassigned.length > 0 && (
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
                        {filteredUnassigned.map((sezione, index) => (
                            <div key={index}>
                                {selected === sezione && (
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
                                                    {emails.map((email, index) => (
                                                        <option key={index} value={email}/>
                                                    ))}
                                                </datalist>
                                            </div>
                                        </div>
                                        <div className="card-footer">
                                            <div className="row mt-3">
                                                <div className="col-12">
                                                    <button type="button" className="btn btn-success w-100"
                                                            onClick={() => handleSave(selected, false)}>
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
            {assigned.length > 0 && (
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
                        {filteredAssigned.map((sezione, index) => (
                            <div key={index}>
                                {selected === sezione && (
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
                                                    {emails.map((email, index) => (
                                                        <option key={index} value={email}/>
                                                    ))}
                                                </datalist>
                                            </div>
                                        </div>
                                        <div className="card-footer">
                                            <div className="row mt-3">
                                                <div className="col-6">
                                                    <button type="button" className="btn btn-secondary w-100"
                                                            onClick={() => handleSave(selected, true)}>
                                                        Rimuovi
                                                    </button>
                                                </div>
                                                <div className="col-6">
                                                    <button type="button" className="btn btn-success w-100"
                                                            onClick={() => handleSave(selected, false)}>
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

export default RdlList;
