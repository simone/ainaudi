// App.js
import React, {useState, useEffect} from "react";
import SectionForm from "./SectionForm";

function RDLComponent({client, setError}) {
    const [loading, setLoading] = useState(true);
    const [sections, setSections] = useState([]);
    const [selectedSection, setSelectedSection] = useState(null);

    useEffect(() => {
        console.log("Loading data");
        listSections();
        setLoading(false);
    }, []);

    const listSections = () => {
        client.sections.get().then((response) => {
            const rows = response.rows;
            if (rows && rows.length > 0) {
                setSections(
                    rows.map(({comune, sezione, values}) => ({
                        comune,
                        sezione,
                        email: client.email,
                        nElettoriMaschi: values[0],
                        nElettoriDonne: values[1],
                        schedeRicevute: values[2],
                        schedeAutenticate: values[3],
                        schedeBianche: values[4],
                        schedeNulle: values[5],
                        schedeContestate: values[6],
                        "Morace Carolina": values[7],
                        "Tamburrano Dario": values[8],
                        "Ferrara Gianluca": values[9],
                        "Basile Giovanna": values[10],
                        "Esposito Giusy": values[11],
                        "Fazio Valentina": values[12],
                        "Lauretti Federica": values[13],
                        "Pacetti Giuliano": values[14],
                        "Volpi Stefania": values[15],
                        "Romagnoli Sergio": values[16],
                        "Emiliozzi Mirella": values[17],
                        "Pococacio Valentina": values[18],
                        "Ceccato Emanuele": values[19],
                        "Alloatti Luca": values[20],
                        "Cecere Stefano": values[21],
                        "MOVIMENTO 5 STELLE": values[22],
                        "FRATELLI D'ITALIA": values[23],
                        "FORZA ITALIA-NOI MODERATI": values[24],
                        "LEGA SALVINI PREMIER": values[25],
                        "PARTITO DEMOCRATICO": values[26],
                        "ALLEANZA VERDI E SINISTRA": values[27],
                        "ALTERNATIVA POPOLARE": values[28],
                        "STATI UNITI D'EUROPA": values[29],
                        "DEMOCRAZIA POPOLARE SOVRANA": values[30],
                        "PACE TERRA DIGNITA'": values[31],
                        "AZIONE-SIAMO EUROPEI": values[32],
                    }))
                );
            }
        })
            .catch((error) => {
                console.error("Error reading Sheet:", error);
                setError("Errore durante la lettura del foglio di calcolo: " + error.result.message);
            });
    };

    const updateSection = (newData) => {
        client.sections.save({
            comune: newData.comune,
            sezione: newData.sezione,
            values: [
                newData.nElettoriMaschi,
                newData.nElettoriDonne,
                newData.schedeRicevute,
                newData.schedeAutenticate,
                newData.schedeBianche,
                newData.schedeNulle,
                newData.schedeContestate,
                newData["Morace Carolina"],
                newData["Tamburrano Dario"],
                newData["Ferrara Gianluca"],
                newData["Basile Giovanna"],
                newData["Esposito Giusy"],
                newData["Fazio Valentina"],
                newData["Lauretti Federica"],
                newData["Pacetti Giuliano"],
                newData["Volpi Stefania"],
                newData["Romagnoli Sergio"],
                newData["Emiliozzi Mirella"],
                newData["Pococacio Valentina"],
                newData["Ceccato Emanuele"],
                newData["Alloatti Luca"],
                newData["Cecere Stefano"],
                newData["MOVIMENTO 5 STELLE"],
                newData["FRATELLI D'ITALIA"],
                newData["FORZA ITALIA-NOI MODERATI"],
                newData["LEGA SALVINI PREMIER"],
                newData["PARTITO DEMOCRATICO"],
                newData["ALLEANZA VERDI E SINISTRA"],
                newData["ALTERNATIVA POPOLARE"],
                newData["STATI UNITI D'EUROPA"],
                newData["DEMOCRAZIA POPOLARE SOVRANA"],
                newData["PACE TERRA DIGNITA'"],
                newData["AZIONE-SIAMO EUROPEI"],
            ],
        }).then((response) => {
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

    const progress = (section) => {
        // Numero totale di proprietà nell'oggetto section
        const totalProperties = Object.keys(section).length;
        // Numero di proprietà valorizzate
        let filledProperties = 0;

        // Itera su tutte le proprietà dell'oggetto section
        for (let key in section) {
            if (section[key] !== null && section[key] !== undefined && section[key] !== '') {
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
                            {isComplete(section) ? (
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
    );
}

export default RDLComponent;
