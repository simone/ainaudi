// App.js
import React, {useEffect, useState} from "react";
import SectionForm from "./SectionForm";

function SectionList({client, user, setError, referenti}) {
    const [loading, setLoading] = useState(true);
    const [sections, setSections] = useState([]);
    const [assignedSections, setAssignedSections] = useState([]);
    const [selectedSection, setSelectedSection] = useState(null);
    const [lists, setLists] = useState([]);
    const [candidates, setCandidates] = useState([]);
    const [searchText, setSearchText] = useState('');
    const [selectedError, setSelectedError] = useState('');
    const [filteredSections, setFilteredSections] = useState([]);
    const [filteredAssignedSections, setFilteredAssignedSections] = useState([]);

    useEffect(() => {
        window.scrollTo(0, 0);
        console.log("Loading data");
        loadLists();
        loadCandidates();
    }, []);

    const loadCandidates = () => {
        client.election.candidates()
            .then(data => {
                setCandidates(data.values);
            }).catch(error => {
            console.error('Error fetching Candidates data:', error);
            setError(error.error || error.message || error.toString());
        });
    }

    const loadLists = () => {
        client.election.lists()
            .then(data => {
                setLists(data.values.map(row => row[0]));
            }).catch(error => {
            console.error('Error fetching Lists data:', error);
            setError(error.error || error.message || error.toString());
        });
    }

    useEffect(() => {
        if (lists.length > 0 && candidates.length > 0) {
            listSections();
        }
    }, [lists, candidates]);

    function adaptToSections(rows) {
        return rows.map(({comune, sezione, email, values}) => {
            const section = {
                comune,
                sezione,
                email: email,
                nElettoriMaschi: values[0] || '',
                nElettoriDonne: values[1] || '',
                schedeRicevute: values[2] || '',
                schedeAutenticate: values[3] || '',
                nVotantiMaschi: values[4] || '',
                nVotantiDonne: values[5] || '',
                schedeBianche: values[6] || '',
                schedeNulle: values[7] || '',
                schedeContestate: values[8] || ''
            };

            // indici delle colonne preferenze e liste
            const fP = 9;
            const fL = fP + candidates.length;
            const lL = fL + lists.length;

            candidates.forEach((name, index) => {
                section[name] = values[fP + index] || '';
            });

            lists.forEach((name, index) => {
                section[name] = values[fL + index] || '';
            });

            section.incongruenze = values[lL] || '';

            return section;
        });
    }

    const listSections = () => {
        client.sections.get({assigned: false}).then((response) => {
            const rows = response.rows;
            if (rows) {
                setLoading(false);
                setSections(adaptToSections(rows));
            }
        }).catch((error) => {
            console.error("Error reading Sheet:", error);
            setError("Errore durante la lettura del foglio di calcolo: " + error.result.message);
        });
        if (referenti) {
            client.sections.get({assigned: true}).then((response) => {
                const rows = response.rows;
                if (rows) {
                    setLoading(false);
                    setAssignedSections(adaptToSections(rows));
                }
            }).catch((error) => {
                console.error("Error reading Sheet:", error);
                setError("Errore durante la lettura del foglio di calcolo: " + error.result.message);
            });
        }
    };

    const updateSection = (newData, errors) => {
        const values = [
            newData.nElettoriMaschi,
            newData.nElettoriDonne,
            newData.schedeRicevute,
            newData.schedeAutenticate,
            newData.nVotantiMaschi,
            newData.nVotantiDonne,
            newData.schedeBianche,
            newData.schedeNulle,
            newData.schedeContestate,
            ...candidates.map(name => newData[name] || ''),
            ...lists.map(name => newData[name] || ''),
            errors.join(', ')
        ];
        client.sections.save({
            comune: newData.comune,
            sezione: newData.sezione,
            values: values,
        })
            .then((response) => {
                listSections();
                window.scrollTo(0, 0);
                setSelectedSection(null);
            })
            .catch((error) => {
                console.error("Error updating Sheet:", error);
                setError("Errore durante l'aggiornamento del foglio di calcolo: " + error.result.message);
            });
    };

    const isComplete = (section) => {
        // Verifica che tutti i valori della section sono valorizzati
        for (let key in section) {
            if (section[key] === null || section[key] === undefined || section[key] === '') {
                return false;
            }
        }
        return true;
    };

    const hasErrors = (section) => {
        return section.incongruenze !== '';
    }

    const progress = (section) => {
        // Numero totale di proprietà nell'oggetto section
        const totalProperties = Object.keys(section).length - 4;
        // Numero di proprietà valorizzate
        let filledProperties = 0;

        // Itera su tutte le proprietà dell'oggetto section
        for (let key in section) {
            if (key === 'comune' || key === 'sezione' || key === 'email' || key === 'incongruenze') {
                continue;
            }
            if (section[key] !== null && section[key] !== undefined && section[key] !== '') {
                filledProperties++;
            }
        }

        // Calcola la percentuale di completamento
        const progressPercentage = (filledProperties / totalProperties) * 100;

        return Math.round(progressPercentage);
    };

    function filterSection(section) {
        let q = searchText.toLowerCase();
        // Convert all fields to string before calling .toLowerCase()
        const comuneString = section.comune.toString().toLowerCase();
        const sezioneString = section.sezione.toString().toLowerCase();
        const emailString = section.email.toString().toLowerCase();
        const incongruenzeString = section.incongruenze.toString().toLowerCase();
        const matchesSearchText = comuneString.includes(q)
            || sezioneString.includes(q)
            || emailString.includes(q);
        const matchesError = selectedError === '' || incongruenzeString.includes(selectedError.toLowerCase());
        return matchesSearchText && matchesError;
    }


    useEffect(() => {
        setFilteredSections(sections.filter(filterSection));
    }, [sections, searchText, selectedError]);

    useEffect(() => {
        setFilteredAssignedSections(assignedSections.filter(filterSection));
    }, [assignedSections, searchText, selectedError]);

    if (loading) {
        return <div className="card-body d-flex align-items-center justify-content-center"
                    style={{minHeight: '50vh'}}>
            <div className="spinner-border text-primary" role="status">
                <span className="visually-hidden">Loading...</span>
            </div>
        </div>;
    }

    if (selectedSection) {
        return (
            <SectionForm
                lists={lists}
                candidates={candidates}
                section={selectedSection}
                updateSection={updateSection}
                cancel={() => setSelectedSection(null)}
            />
        );
    }

    return (
        <>
            <div className="card mb-3">
                <div className="card-body">
                    <input
                        type="text"
                        className="form-control mb-2"
                        placeholder="Cerca per comune, sezione o email"
                        value={searchText}
                        onChange={(e) => setSearchText(e.target.value)}
                    />
                    <select
                        className="form-control"
                        value={selectedError}
                        onChange={(e) => setSelectedError(e.target.value)}
                    >
                        <option value=""></option>
                        <option value="Il presidente deve fare la richiesta per avere le schede sufficienti a tutti gli elettori">Richiesta schede per elettori</option>
                        <option value="Impossibile autenticare più schede di quelle ricevute">Autenticazione schede limitata</option>
                        <option value="Il presidente non deve autenticare più schede del numero di elettori ">Limite schede autenticabili</option>
                        <option value="Il totale delle schede scrutinate (Bianche, Nulle, Contestate e totale voti di lista) NON DEVE ESSERE maggiore al numero dei votanti">Schede scrutinate ≤ votanti</option>
                        <option value="Probabilmente mancano dei voti di lista o delle schede perché il totale delle schede scrutinate (Bianche, Nulle, Contestate e totale voti di lista) non è uguale al numero dei votanti">Verifica voti mancanti</option>
                        <option value="Il totale dei voti di lista non può essere maggiore del numero dei votanti">Voti lista ≤ votanti</option>
                        <option value="Visto che un elettore può votare fino a 3 candidati, il totale dei voti di preferenza non può essere maggiore del triplo del numero dei votanti">Preferenze ≤ 3x votanti</option>
                        <option value="Il totale dei votanti non può essere maggiore del numero degli elettori">Votanti ≤ elettori</option>
                    </select>
                </div>
            </div>
            {filteredSections.length === 0 && (
                <div className="card">
                    <div className="card-header alert alert-warning mt-3">
                        Non hai sezioni assegnate. Contatta il Referente RDL della tua Zona.
                    </div>
                </div>)
            }
            {filteredSections.length > 0 && (
                <div className="card">
                <div className="card-header bg-info">
                    Questa applicazione è destinata agli RDL del Movimento 5 Stelle e
                    serve per inviare al movimento i dati raccolti nelle sezioni. Si
                    prega di scegliere una delle sezioni assegnate e di compilare
                    tutti i campi richiesti con i numeri corretti.
                </div>
                <div className="card-body">
                    <h2>Scegli una sezione assegnata a te</h2>
                    <ul className="list-group">
                        {sections.map((section, index) => (
                            <li
                                className="list-group-item d-flex justify-content-between align-items-center"
                                key={index}
                            >
                                <span className="col-6 col-md-4 col-lg-3">{section.comune} - {section.sezione}</span>
                                {hasErrors(section) ? (
                                    <button
                                        className="btn btn-warning col-6 col-md-4 col-lg-3"
                                        onClick={() => {
                                            setSelectedSection(section);
                                        }}
                                    >
                                        Apri {progress(section)}%
                                    </button>
                                ) : isComplete(section) ? (
                                    <button
                                        className="btn btn-success col-6 col-md-4 col-lg-3"
                                        onClick={() => {
                                            setSelectedSection(section);
                                        }}
                                    >
                                        Completo
                                    </button>
                                ) : (
                                    <button
                                        className="btn btn-primary col-6 col-md-4 col-lg-3"
                                        onClick={() => {
                                            setSelectedSection(section);
                                        }}
                                    >
                                        Apri {progress(section)}%
                                    </button>
                                )}
                            </li>
                        ))}
                    </ul>
                </div>
            </div>
            )}
            {referenti && (<div className="card">
                <div className="card-header bg-secondary">
                    Questa sezione è per i subdelegati che possono accedere ai dati raccolti dai propri RDL.
                </div>
                <div className="card-body">
                    <h2>Apri una sezione che hai assegnato</h2>
                    <ul className="list-group">
                        {filteredAssignedSections.map((section, index) => (
                            <li
                                className="list-group-item d-flex justify-content-between align-items-center"
                                key={index}
                            >
                                <div className="col-6 col-md-8 col-lg-9 row">
                                    <span className="col-12 col-md-4 col-lg-3">{section.comune} - {section.sezione}</span>
                                    <span className="col-12 col-md-8 col-lg-9">
                                        <span className="email">{section.email.split('@')[0]}</span>
                                        <span className="email domain">@{section.email.split('@')[1]}</span>
                                    </span>
                                </div>
                                {hasErrors(section) ? (
                                    <button
                                        className="btn btn-warning col-6 col-md-4 col-lg-3"
                                        onClick={() => {
                                            setSelectedSection(section);
                                        }}
                                    >
                                        Apri {progress(section)}%
                                    </button>
                                ) : isComplete(section) ? (
                                    <button
                                        className="btn btn-success col-6 col-md-4 col-lg-3"
                                        onClick={() => {
                                            setSelectedSection(section);
                                        }}
                                    >
                                        Completo
                                    </button>
                                ) : (
                                    <button
                                        className="btn btn-primary col-6 col-md-4 col-lg-3"
                                        onClick={() => {
                                            setSelectedSection(section);
                                        }}
                                    >
                                        Apri {progress(section)}%
                                    </button>
                                )}
                            </li>
                        ))}
                    </ul>
                </div>
            </div>)}
        </>
    );
}

export default SectionList;
