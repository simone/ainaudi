// SectionList.js - Mobile-first redesign
import React, {useEffect, useState} from "react";
import SectionForm from "./SectionForm";

// Stili mobile-first per la lista sezioni
const listStyles = `
    .sezioni-search {
        position: sticky;
        top: 0;
        z-index: 50;
        background: white;
        padding: 12px;
        margin: -1rem -1rem 0 -1rem;
        border-bottom: 1px solid #eee;
    }

    .sezioni-search-input {
        width: 100%;
        padding: 12px 16px;
        font-size: 1rem;
        border: 2px solid #e0e0e0;
        border-radius: 10px;
        transition: border-color 0.2s;
    }

    .sezioni-search-input:focus {
        outline: none;
        border-color: #0d6efd;
    }

    .sezioni-header {
        padding: 16px;
        text-align: center;
    }

    .sezioni-header-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #333;
        margin-bottom: 4px;
    }

    .sezioni-header-subtitle {
        font-size: 0.85rem;
        color: #666;
    }

    .sezioni-list {
        list-style: none;
        padding: 0;
        margin: 0;
    }

    .sezione-card {
        display: flex;
        align-items: center;
        padding: 14px 16px;
        background: white;
        border-bottom: 1px solid #f0f0f0;
        cursor: pointer;
        transition: background 0.15s;
    }

    .sezione-card:hover {
        background: #f8f9fa;
    }

    .sezione-card:active {
        background: #e9ecef;
    }

    .sezione-info {
        flex: 1;
        min-width: 0;
    }

    .sezione-title {
        font-weight: 600;
        font-size: 1rem;
        color: #1a1a1a;
        margin-bottom: 2px;
    }

    .sezione-subtitle {
        font-size: 0.8rem;
        color: #666;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .sezione-status {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-shrink: 0;
    }

    .sezione-progress {
        width: 50px;
        height: 6px;
        background: #e9ecef;
        border-radius: 3px;
        overflow: hidden;
    }

    .sezione-progress-bar {
        height: 100%;
        border-radius: 3px;
        transition: width 0.3s;
    }

    .sezione-progress-bar.complete { background: #198754; }
    .sezione-progress-bar.warning { background: #ffc107; }
    .sezione-progress-bar.primary { background: #0d6efd; }

    .sezione-badge {
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .sezione-badge.complete {
        background: #d1e7dd;
        color: #0f5132;
    }

    .sezione-badge.warning {
        background: #fff3cd;
        color: #856404;
    }

    .sezione-badge.primary {
        background: #cfe2ff;
        color: #084298;
    }

    .sezione-arrow {
        color: #ccc;
        font-size: 0.9rem;
        margin-left: 8px;
    }

    .sezioni-empty {
        text-align: center;
        padding: 40px 20px;
        color: #666;
    }

    .sezioni-empty-icon {
        font-size: 3rem;
        margin-bottom: 16px;
        opacity: 0.5;
    }

    .sezioni-empty-title {
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 8px;
    }

    .sezioni-empty-text {
        font-size: 0.9rem;
    }

    .sezioni-section-header {
        padding: 12px 16px;
        background: #f8f9fa;
        border-bottom: 1px solid #eee;
        font-size: 0.85rem;
        font-weight: 600;
        color: #666;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .ballottaggio-alert {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
        background: linear-gradient(135deg, #ffc107 0%, #ffca2c 100%);
        color: #000;
        margin: 0 -1rem;
    }

    .ballottaggio-alert i {
        font-size: 1.25rem;
    }

    .ballottaggio-alert-text {
        font-size: 0.9rem;
    }

    .ballottaggio-alert-title {
        font-weight: 700;
    }
`;

function SectionList({client, user, setError, referenti}) {
    const [loading, setLoading] = useState(true);
    const [sections, setSections] = useState([]);
    const [assignedSections, setAssignedSections] = useState([]);
    const [selectedSection, setSelectedSection] = useState(null);
    const [lists, setLists] = useState([]);
    const [candidates, setCandidates] = useState([]);
    const [dataLoaded, setDataLoaded] = useState(false);
    const [searchText, setSearchText] = useState('');
    const [filteredSections, setFilteredSections] = useState([]);
    const [filteredAssignedSections, setFilteredAssignedSections] = useState([]);
    const [turnoInfo, setTurnoInfo] = useState(null);

    useEffect(() => {
        window.scrollTo(0, 0);
        Promise.all([loadLists(), loadCandidates()])
            .then(() => setDataLoaded(true));
    }, []);

    const loadCandidates = () => {
        return client.election.candidates()
            .then(data => setCandidates(Array.isArray(data.values) ? data.values : []))
            .catch(() => setCandidates([]));
    }

    const loadLists = () => {
        return client.election.lists()
            .then(data => {
                const values = Array.isArray(data.values) ? data.values : [];
                setLists(values.map(row => row[0]));
            })
            .catch(() => setLists([]));
    }

    useEffect(() => {
        if (dataLoaded) listSections();
    }, [dataLoaded]);

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
            if (response.turno) setTurnoInfo(response.turno);
        }).catch((error) => {
            console.error("Error reading Sheet:", error);
            setError("Errore durante la lettura: " + error.result?.message);
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
            .then(() => {
                listSections();
                window.scrollTo(0, 0);
                setSelectedSection(null);
            })
            .catch((error) => {
                console.error("Error updating Sheet:", error);
                setError("Errore durante l'aggiornamento: " + error.result?.message);
            });
    };

    const isComplete = (section) => {
        for (let key in section) {
            if (section[key] === null || section[key] === undefined || section[key] === '') {
                return false;
            }
        }
        return true;
    };

    const hasErrors = (section) => section.incongruenze !== '';

    const progress = (section) => {
        const totalProperties = Object.keys(section).length - 4;
        let filledProperties = 0;
        for (let key in section) {
            if (key === 'comune' || key === 'sezione' || key === 'email' || key === 'incongruenze') continue;
            if (section[key] !== null && section[key] !== undefined && section[key] !== '') {
                filledProperties++;
            }
        }
        return Math.round((filledProperties / totalProperties) * 100);
    };

    function filterSection(section) {
        let q = searchText.toLowerCase();
        const comuneString = section.comune.toString().toLowerCase();
        const sezioneString = section.sezione.toString().toLowerCase();
        const emailString = section.email.toString().toLowerCase();
        return comuneString.includes(q) || sezioneString.includes(q) || emailString.includes(q);
    }

    useEffect(() => {
        setFilteredSections(sections.filter(filterSection));
    }, [sections, searchText]);

    useEffect(() => {
        setFilteredAssignedSections(assignedSections.filter(filterSection));
    }, [assignedSections, searchText]);

    if (loading) {
        return (
            <div className="loading-container" role="status" aria-live="polite">
                <div className="spinner-border text-primary">
                    <span className="visually-hidden">Caricamento in corso...</span>
                </div>
                <p className="loading-text">Caricamento sezioni...</p>
            </div>
        );
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

    const renderSectionCard = (section, index) => {
        const prog = progress(section);
        const complete = isComplete(section);
        const errors = hasErrors(section);

        let statusClass = 'primary';
        if (complete && !errors) statusClass = 'complete';
        else if (errors) statusClass = 'warning';

        return (
            <li
                key={index}
                className="sezione-card"
                onClick={() => setSelectedSection(section)}
            >
                <div className="sezione-info">
                    <div className="sezione-title">
                        Sezione {section.sezione}
                    </div>
                    <div className="sezione-subtitle">
                        {section.comune}
                    </div>
                </div>
                <div className="sezione-status">
                    {complete && !errors ? (
                        <span className="sezione-badge complete">
                            <i className="fas fa-check me-1"></i>
                            Completo
                        </span>
                    ) : (
                        <>
                            <div className="sezione-progress">
                                <div
                                    className={`sezione-progress-bar ${statusClass}`}
                                    style={{ width: `${prog}%` }}
                                />
                            </div>
                            <span className={`sezione-badge ${statusClass}`}>
                                {prog}%
                            </span>
                        </>
                    )}
                    <i className="fas fa-chevron-right sezione-arrow"></i>
                </div>
            </li>
        );
    };

    const renderAssignedSectionCard = (section, index) => {
        const prog = progress(section);
        const complete = isComplete(section);
        const errors = hasErrors(section);

        let statusClass = 'primary';
        if (complete && !errors) statusClass = 'complete';
        else if (errors) statusClass = 'warning';

        return (
            <li
                key={index}
                className="sezione-card"
                onClick={() => setSelectedSection(section)}
            >
                <div className="sezione-info">
                    <div className="sezione-title">
                        {section.comune} - Sez. {section.sezione}
                    </div>
                    <div className="sezione-subtitle">
                        {section.email}
                    </div>
                </div>
                <div className="sezione-status">
                    {complete && !errors ? (
                        <span className="sezione-badge complete">
                            <i className="fas fa-check me-1"></i>
                            OK
                        </span>
                    ) : (
                        <span className={`sezione-badge ${statusClass}`}>
                            {errors && <i className="fas fa-exclamation-triangle me-1"></i>}
                            {prog}%
                        </span>
                    )}
                    <i className="fas fa-chevron-right sezione-arrow"></i>
                </div>
            </li>
        );
    };

    return (
        <>
            <style>{listStyles}</style>

            {/* Search */}
            {(sections.length > 3 || assignedSections.length > 3) && (
                <div className="sezioni-search">
                    <input
                        type="search"
                        className="sezioni-search-input"
                        placeholder="Cerca sezione..."
                        value={searchText}
                        onChange={(e) => setSearchText(e.target.value)}
                    />
                </div>
            )}

            {/* Ballottaggio Alert */}
            {turnoInfo?.is_ballottaggio && (
                <div className="ballottaggio-alert">
                    <i className="fas fa-redo"></i>
                    <div className="ballottaggio-alert-text">
                        <span className="ballottaggio-alert-title">BALLOTTAGGIO</span>
                        <span> - {turnoInfo.scheda_nome}</span>
                    </div>
                </div>
            )}

            {/* No sections assigned */}
            {filteredSections.length === 0 && !referenti && (
                <div className="sezioni-empty">
                    <div className="sezioni-empty-icon">
                        <i className="fas fa-inbox"></i>
                    </div>
                    <div className="sezioni-empty-title">
                        Nessuna sezione assegnata
                    </div>
                    <div className="sezioni-empty-text">
                        Contatta il Referente RDL della tua zona per ricevere l'assegnazione.
                    </div>
                </div>
            )}

            {/* My sections */}
            {filteredSections.length > 0 && (
                <>
                    <div className="sezioni-section-header">
                        <i className="fas fa-user"></i>
                        Le mie sezioni
                        <span style={{ marginLeft: 'auto', fontWeight: 400 }}>
                            {filteredSections.length}
                        </span>
                    </div>
                    <ul className="sezioni-list">
                        {filteredSections.map(renderSectionCard)}
                    </ul>
                </>
            )}

            {/* Assigned sections (for referenti) */}
            {referenti && filteredAssignedSections.length > 0 && (
                <>
                    <div className="sezioni-section-header" style={{ marginTop: 16 }}>
                        <i className="fas fa-users"></i>
                        Sezioni dei miei RDL
                        <span style={{ marginLeft: 'auto', fontWeight: 400 }}>
                            {filteredAssignedSections.length}
                        </span>
                    </div>
                    <ul className="sezioni-list">
                        {filteredAssignedSections.map(renderAssignedSectionCard)}
                    </ul>
                </>
            )}
        </>
    );
}

export default SectionList;
