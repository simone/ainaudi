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

    useEffect(() => {
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
                console.log(key, section[key]);
                filledProperties++;
            }
        }

        // Calcola la percentuale di completamento
        const progressPercentage = (filledProperties / totalProperties) * 100;

        return Math.round(progressPercentage);
    };


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

    if (sections.length === 0) {
        return (
            <div className="card">
                <div className="card-header alert alert-warning mt-3">
                    Non hai sezioni assegnate. Contatta il Referente RDL della tua Zona.
                </div>
            </div>
        );
    }

    return (
        <>
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
            {referenti && (<div className="card">
                <div className="card-header bg-secondary">
                    Questa sezione è per i subdelegati che possono accedere ai dati raccolti dai propri RDL.
                </div>
                <div className="card-body">
                    <h2>Apri una sezione che hai assegnato</h2>
                    <ul className="list-group">
                        {assignedSections.map((section, index) => (
                            <li
                                className="list-group-item d-flex justify-content-between align-items-center"
                                key={index}
                            >
                                <span className="col-6 col-md-4 col-lg-3">{section.comune} - {section.sezione} - {section.email}</span>
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
