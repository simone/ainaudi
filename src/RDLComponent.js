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
        client.get({
                range: "Dati!A2:AJ",
        })
        .then((response) => {
            const rows = response.values;
            if (rows && rows.length > 0) {
                const userSections = rows.filter((row) => row[2] === client.email);
                setSections(
                    userSections.map((row) => ({
                        comune: row[0],
                        sezione: row[1],
                        email: row[2],
                        nElettoriMaschi: row[3],
                        nElettoriDonne: row[4],
                        schedeRicevute: row[5],
                        schedeAutenticate: row[6],
                        schedeBianche: row[7],
                        schedeNulle: row[8],
                        schedeContestate: row[9],
                        "Morace Carolina": row[10],
                        "Tamburrano Dario": row[11],
                        "Ferrara Gianluca": row[12],
                        "Basile Giovanna": row[13],
                        "Esposito Giusy": row[14],
                        "Fazio Valentina": row[15],
                        "Lauretti Federica": row[16],
                        "Pacetti Giuliano": row[17],
                        "Volpi Stefania": row[18],
                        "Romagnoli Sergio": row[19],
                        "Emiliozzi Mirella": row[20],
                        "Pococacio Valentina": row[21],
                        "Ceccato Emanuele": row[22],
                        "Alloatti Luca": row[23],
                        "Cecere Stefano": row[24],
                        "MOVIMENTO 5 STELLE": row[25],
                        "FRATELLI D'ITALIA": row[26],
                        "FORZA ITALIA-NOI MODERATI": row[27],
                        "LEGA SALVINI PREMIER": row[28],
                        "PARTITO DEMOCRATICO": row[29],
                        "ALLEANZA VERDI E SINISTRA": row[30],
                        "ALTERNATIVA POPOLARE": row[31],
                        "STATI UNITI D'EUROPA": row[32],
                        "DEMOCRAZIA POPOLARE SOVRANA": row[33],
                        "PACE TERRA DIGNITA'": row[34],
                        "AZIONE-SIAMO EUROPEI": row[35],
                    }))
                );
            }
        })
        .catch((error) => {
            console.error("Error reading Sheet:", error);
            setError("Errore durante la lettura del foglio di calcolo: " + error.result.message);
        });
    };

    const findIndexByComuneSezione = (comune, sezione, data) => {
        return data.findIndex(row => row[0] === comune && row[1] === sezione);
    };


    const updateSection = (newData) => {
        client.get({
            range: "Dati!A2:C", // Supponiamo che le colonne A, B e C siano comune, sezione ed email
        })
        .then((response) => {
            const data = response.values;
            const correctIndex = findIndexByComuneSezione(newData.comune, newData.sezione, data);
            if (correctIndex !== -1) {
                const range = `Dati!A${correctIndex + 2}:AJ${correctIndex + 2}`; // Supponendo che l'indice inizi da 0 e il foglio abbia intestazioni
                client.update({
                    range: range,
                    valueInputOption: "RAW",
                    values: [
                        [
                            newData.comune,
                            newData.sezione,
                            newData.email,
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
                    ],
                })
                .then((response) => {
                    listSections();
                    setSelectedSection(null);
                })
                .catch((error) => {
                    console.error("Error updating Sheet:", error);
                    setError("Errore durante l'aggiornamento del foglio di calcolo: " + error.result.message);
                });
            } else {
                console.error("Record not found for update");
                setError("Errore: record non trovato per l'aggiornamento");
            }
        })
        .catch((error) => {
            console.error("Error reading Sheet:", error);
            setError("Errore durante la lettura del foglio di calcolo: " + error.result.message);
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
                cancel={()=>setSelectedSection(null)}
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
                            {section.comune} - {section.sezione}
                            {isComplete(section) ? (
                                <button
                                    className="btn btn-success"
                                    onClick={() => {
                                        setSelectedSection(section);
                                    }}
                                >
                                    Completo
                                </button>
                            ) : (
                                <button
                                    className="btn btn-primary"
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
