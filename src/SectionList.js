// SectionList.js - Mobile-first redesign with wizard support
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

    .consultazione-info {
        background: linear-gradient(135deg, #0d6efd 0%, #0a58ca 100%);
        color: white;
        padding: 16px;
        margin: -1rem -1rem 16px -1rem;
        text-align: center;
    }

    .consultazione-nome {
        font-size: 1rem;
        font-weight: 600;
        margin-bottom: 4px;
    }

    .consultazione-schede {
        font-size: 0.8rem;
        opacity: 0.9;
    }
`;

function SectionList({client, user, setError, referenti}) {
    const [loading, setLoading] = useState(true);
    const [consultazione, setConsultazione] = useState(null);
    const [schede, setSchede] = useState([]);
    const [sections, setSections] = useState([]);
    const [selectedSection, setSelectedSection] = useState(null);
    const [searchText, setSearchText] = useState('');
    const [filteredSections, setFilteredSections] = useState([]);

    // Load scrutinio info (consultazione + schede)
    useEffect(() => {
        window.scrollTo(0, 0);
        loadScrutinioInfo();
    }, []);

    const loadScrutinioInfo = async () => {
        try {
            const info = await client.scrutinio.info();
            if (info?.error) {
                setError(info.error);
                setLoading(false);
                return;
            }
            setConsultazione(info.consultazione);
            setSchede(info.schede || []);

            // Now load sections
            await loadSections();
        } catch (err) {
            console.error('Error loading scrutinio info:', err);
            setError('Errore nel caricamento dati');
            setLoading(false);
        }
    };

    const loadSections = async () => {
        try {
            const result = await client.scrutinio.sezioni();
            if (result?.error) {
                setError(result.error);
            } else {
                setSections(result.sezioni || []);
            }
        } catch (err) {
            console.error('Error loading sections:', err);
        }
        setLoading(false);
    };

    const updateSection = async (payload) => {
        try {
            const result = await client.scrutinio.save(payload);
            if (result?.error) {
                setError(result.error);
            } else {
                // Reload sections and close form
                await loadSections();
                window.scrollTo(0, 0);
                setSelectedSection(null);
            }
        } catch (err) {
            console.error('Error saving section:', err);
            setError('Errore durante il salvataggio');
        }
    };

    // Calculate progress for a section
    const calculateProgress = (sectionData) => {
        if (!sectionData) return 0;

        let filled = 0;
        let total = 4; // elettori M/F, votanti M/F

        const seggio = sectionData.dati_seggio || {};
        if (seggio.elettori_maschi != null) filled++;
        if (seggio.elettori_femmine != null) filled++;
        if (seggio.votanti_maschi != null) filled++;
        if (seggio.votanti_femmine != null) filled++;

        // Add schede fields
        schede.forEach(scheda => {
            const schedaData = sectionData.schede?.[String(scheda.id)];
            total += 5; // ricevute, autenticate, bianche, nulle, contestate
            if (schedaData) {
                if (schedaData.schede_ricevute != null) filled++;
                if (schedaData.schede_autenticate != null) filled++;
                if (schedaData.schede_bianche != null) filled++;
                if (schedaData.schede_nulle != null) filled++;
                if (schedaData.schede_contestate != null) filled++;

                // Referendum votes
                if (scheda.schema?.tipo === 'si_no') {
                    total += 2;
                    if (schedaData.voti?.si != null) filled++;
                    if (schedaData.voti?.no != null) filled++;
                }
            }
        });

        return Math.round((filled / total) * 100);
    };

    const isComplete = (sectionData) => {
        return calculateProgress(sectionData) === 100;
    };

    // Filter sections
    function filterSection(section) {
        if (!searchText) return true;
        const q = searchText.toLowerCase();
        const comuneString = section.comune?.toString().toLowerCase() || '';
        const sezioneString = section.sezione?.toString().toLowerCase() || '';
        return comuneString.includes(q) || sezioneString.includes(q);
    }

    useEffect(() => {
        setFilteredSections(sections.filter(filterSection));
    }, [sections, searchText]);

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
        // Find section data
        const sectionData = sections.find(
            s => s.comune === selectedSection.comune && s.sezione === selectedSection.sezione
        );

        return (
            <SectionForm
                schede={schede}
                section={selectedSection}
                sectionData={sectionData}
                updateSection={updateSection}
                cancel={() => setSelectedSection(null)}
            />
        );
    }

    const renderSectionCard = (section, index) => {
        const prog = calculateProgress(section);
        const complete = isComplete(section);

        let statusClass = 'primary';
        if (complete) statusClass = 'complete';
        else if (prog > 50) statusClass = 'warning';

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
                    {complete ? (
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

    return (
        <>
            <style>{listStyles}</style>

            {/* Consultazione info */}
            {consultazione && (
                <div className="consultazione-info">
                    <div className="consultazione-nome">{consultazione.nome}</div>
                    <div className="consultazione-schede">
                        {schede.length} {schede.length === 1 ? 'scheda' : 'schede'} da compilare
                    </div>
                </div>
            )}

            {/* Search */}
            {sections.length > 3 && (
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

            {/* No sections assigned */}
            {filteredSections.length === 0 && (
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

            {/* Sections list */}
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
        </>
    );
}

export default SectionList;
