import React, {useEffect, useState} from 'react';
import EmailAutocomplete from '../components/EmailAutocomplete';

const HighlightedText = ({ text, filter }) => {
    const regex = new RegExp(filter, 'gi');
    const parts = text.split(regex);
    const matches = text.match(regex);
    return (
        <span>
      {parts.map((part, index) => (
          <React.Fragment key={index}>
              {part}
              {index < parts.length - 1 && matches[index] && (
                  <span className="yellow">{matches[index]}</span>
              )}
          </React.Fragment>
      ))}
    </span>
    );
};

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
    const [emailError, setEmailError] = useState("");
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

    useEffect(() => {
        if (emailRDL) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(emailRDL)) {
                setEmailError("indirizzo email non valido");
            } else {
                setEmailError("");
            }
        } else {
            setEmailError("");
        }
    }, [emailRDL]);

    const loadEmails = () => {
        client.rdl.emails().then((response) => {
            setEmails(response.emails)
        });
    }

    const handleSezioneClick = (sezione) => {
        setSelected(sezione);
        setEmailRDL(sezione[3] ? sezione[3] : "");
    };

    const handleSave = (sezione, remove) => {
        const email = emailRDL;
        if (remove) {
            setAssigned(assigned.filter(s => s !== sezione));
            setUnassigned([...unassigned, [sezione[0], sezione[1], sezione[2], '']]);
        } else {
            setUnassigned(unassigned.filter(s => s !== sezione));
            if (assigned.find(s => s === sezione)) {
                setAssigned(assigned.map(s => s === sezione ? [sezione[0], sezione[1], sezione[2], email] : s));
            } else {
                setAssigned([...assigned, [sezione[0], sezione[1], sezione[2], email]]);
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
            return sezione[1].toLowerCase().includes(unassignedFilter.toLowerCase()) || sezione[2].toLowerCase().includes(unassignedFilter.toLowerCase());
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
            return sezione[1].toLowerCase().includes(assignedFilter.toLowerCase())
                || sezione[2].toLowerCase().includes(assignedFilter.toLowerCase())
                || sezione[3].toLowerCase().includes(assignedFilter.toLowerCase());
        }).sort((a, b) => a[1].localeCompare(b[1]) || a[2].localeCompare(b[2]) || a[0].localeCompare(b[0])));
    }, [assignedFilter, assigned]);

    if (loading) {
        return (
            <div className="loading-container" role="status" aria-live="polite">
                <div className="spinner-border text-primary">
                    <span className="visually-hidden">Caricamento in corso...</span>
                </div>
                <p className="loading-text">Caricamento assegnazioni RDL...</p>
            </div>
        );
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
                    <input
                           type="search"
                           className="form-control"
                           placeholder="Filtra tramite sezione..."
                           onChange={changeUnassignedFilter}
                           aria-label="Filtra sezioni non assegnate"
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
                                                <EmailAutocomplete
                                                    value={emailRDL}
                                                    onChange={setEmailRDL}
                                                    emails={emails}
                                                    placeholder="Cerca email RDL..."
                                                    className={emailError ? "is-invalid" : ""}
                                                    required
                                                />
                                                {emailError && (
                                                    <div className="alert alert-danger mt-2" role="alert">
                                                        {emailError}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                        <div className="card-footer">
                                            <div className="row mt-3">
                                                <div className="col-12">
                                                    <button type="button" className="btn btn-success w-100"
                                                            onClick={() => handleSave(selected, false)}
                                                            disabled={!!emailError || !emailRDL}>
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
                                            <HighlightedText text={`${sezione[1]} ${sezione[2]} - ${sezione[0]}`} filter={unassignedFilter}/>
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
                    <input
                           type="search"
                           className="form-control"
                           placeholder="Filtra tramite sezione o RDL..."
                           onChange={changeAssignedFilter}
                           aria-label="Filtra sezioni assegnate"
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
                                                <EmailAutocomplete
                                                    value={emailRDL}
                                                    onChange={setEmailRDL}
                                                    emails={emails}
                                                    placeholder="Cerca email RDL..."
                                                    className={emailError ? "is-invalid" : ""}
                                                    required
                                                />
                                                {emailError && (
                                                    <div className="alert alert-danger mt-2" role="alert">
                                                        {emailError}
                                                    </div>
                                                )}
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
                                                            onClick={() => handleSave(selected, false)}
                                                            disabled={!!emailError || !emailRDL}>
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
                                            <HighlightedText text={`${sezione[1]} ${sezione[2]} - ${sezione[0]}`} filter={assignedFilter}/>
                                        </h5>
                                        <div className="mb-1">
                                            <HighlightedText text={sezione[3]} filter={assignedFilter}/>
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
