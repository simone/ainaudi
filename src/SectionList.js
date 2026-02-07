// SectionList.js - Mobile-first redesign with wizard support
import React, {useEffect, useState, useRef, useCallback} from "react";
import SectionForm from "./SectionForm";
import './SectionList.css';


function SectionList({client, user, setError, referenti}) {
    const [loading, setLoading] = useState(true);
    const [loadingMore, setLoadingMore] = useState(false);
    const [consultazione, setConsultazione] = useState(null);
    const [schede, setSchede] = useState([]);
    const [sections, setSections] = useState([]);
    const [selectedSection, setSelectedSection] = useState(null);
    const [searchText, setSearchText] = useState('');
    const [filteredSections, setFilteredSections] = useState([]);

    // Pagination state
    const [currentPage, setCurrentPage] = useState(1);
    const [totalSections, setTotalSections] = useState(0);
    const [totalMie, setTotalMie] = useState(0);
    const [totalTerritorio, setTotalTerritorio] = useState(0);
    const [hasMore, setHasMore] = useState(false);

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
            await loadSections(1, true);
        } catch (err) {
            console.error('Error loading scrutinio info:', err);
            setError('Errore nel caricamento dati');
            setLoading(false);
        }
    };

    const loadSections = async (page = 1, reset = false) => {
        if (reset) {
            setLoading(true);
        } else {
            setLoadingMore(true);
        }

        try {
            const result = await client.scrutinio.sezioni(page, 50);
            if (result?.error) {
                setError(result.error);
            } else {
                if (reset) {
                    setSections(result.sezioni || []);
                } else {
                    setSections(prev => [...prev, ...(result.sezioni || [])]);
                }
                setCurrentPage(result.page || page);
                setTotalSections(result.total || 0);
                setTotalMie(result.total_mie || 0);
                setTotalTerritorio(result.total_territorio || 0);
                setHasMore(result.has_more || false);
            }
        } catch (err) {
            console.error('Error loading sections:', err);
        }
        setLoading(false);
        setLoadingMore(false);
    };

    const loadMore = useCallback(() => {
        if (!loadingMore && hasMore) {
            loadSections(currentPage + 1, false);
        }
    }, [loadingMore, hasMore, currentPage]);

    // Infinite scroll with IntersectionObserver
    const sentinelRef = useRef(null);

    useEffect(() => {
        if (!sentinelRef.current || searchText) return;

        const observer = new IntersectionObserver(
            (entries) => {
                if (entries[0].isIntersecting && hasMore && !loadingMore) {
                    loadMore();
                }
            },
            { threshold: 0.1, rootMargin: '100px' }
        );

        observer.observe(sentinelRef.current);
        return () => observer.disconnect();
    }, [hasMore, loadingMore, loadMore, searchText]);

    // Save without closing the form (for auto-save)
    const saveSection = async (payload) => {
        try {
            // Use new optimized endpoint with optimistic locking if available
            if (client.scrutinio.saveSezione && selectedSection?.id) {
                // Extract version from section data (if we add it later)
                const version = sectionsData[selectedSection.id]?.version || 0;

                const data = {
                    consultazione_id: consultazione?.id,
                    version: version,
                    dati_seggio: {
                        elettori_maschi: payload.dati_seggio?.elettori_maschi,
                        elettori_femmine: payload.dati_seggio?.elettori_femmine,
                        votanti_maschi: payload.dati_seggio?.votanti_maschi,
                        votanti_femmine: payload.dati_seggio?.votanti_femmine,
                    },
                    schede: Object.entries(payload.schede || {}).map(([schedaId, schedaData]) => ({
                        scheda_id: parseInt(schedaId),
                        schede_ricevute: schedaData.schede_ricevute,
                        schede_autenticate: schedaData.schede_autenticate,
                        schede_bianche: schedaData.schede_bianche,
                        schede_nulle: schedaData.schede_nulle,
                        schede_contestate: schedaData.schede_contestate,
                        voti: schedaData.voti
                    }))
                };

                const result = await client.scrutinio.saveSezione(selectedSection.id, data);
                if (result?.error) {
                    setError(result.error);
                    return false;
                }

                // Update local version on success
                if (result.new_version) {
                    sectionsData[selectedSection.id] = {
                        ...sectionsData[selectedSection.id],
                        version: result.new_version
                    };
                }
                return true;
            }

            // Fallback to old endpoint
            const result = await client.scrutinio.save(payload);
            if (result?.error) {
                setError(result.error);
                return false;
            }
            return true;
        } catch (err) {
            console.error('Error saving section:', err);

            // Handle optimistic locking conflict (409)
            if (err.isConflict) {
                const conflictData = err.conflictData || {};
                const updatedBy = conflictData.updated_by || 'un altro utente';
                const message = `I dati sono stati modificati da ${updatedBy}.\n\nClicca OK per ricaricare (perderai le modifiche locali) o Annulla per continuare a modificare.`;

                if (window.confirm(message)) {
                    // Reload section data
                    await loadSections(currentPage, true);
                    window.location.reload(); // Force full reload to reset form
                }
                return false;
            }

            setError('Errore durante il salvataggio: ' + (err.message || 'errore sconosciuto'));
            return false;
        }
    };

    // Save and close the form (for explicit exit)
    const saveAndClose = async (payload) => {
        const success = await saveSection(payload);
        if (success) {
            await loadSections(1, true);
            window.scrollTo(0, 0);
            setSelectedSection(null);
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

    // Filter sections by numero, comune, indirizzo, denominazione
    function filterSection(section) {
        if (!searchText) return true;
        const q = searchText.toLowerCase().trim();
        const numero = String(section.sezione || '');
        const comune = (section.comune || '').toLowerCase();
        const indirizzo = (section.indirizzo || '').toLowerCase();
        const denominazione = (section.denominazione || '').toLowerCase();

        return numero.includes(q) ||
               comune.includes(q) ||
               indirizzo.includes(q) ||
               denominazione.includes(q);
    }

    // Get plesso key for grouping
    function getPlessoKey(section) {
        return section.denominazione || section.indirizzo || 'Altro';
    }

    // Group sections by plesso
    function groupByPlesso(sections) {
        const groups = {};
        sections.forEach(section => {
            const key = getPlessoKey(section);
            if (!groups[key]) {
                groups[key] = {
                    name: section.denominazione || '',
                    address: section.indirizzo || '',
                    sections: []
                };
            }
            groups[key].sections.push(section);
        });
        return groups;
    }

    useEffect(() => {
        setFilteredSections(sections.filter(filterSection));
    }, [sections, searchText]);

    // Split into my sections vs other sections, then group by plesso
    const mySections = filteredSections.filter(s => s.is_mia);
    const otherSections = filteredSections.filter(s => !s.is_mia);
    const myGrouped = groupByPlesso(mySections);
    const otherGrouped = groupByPlesso(otherSections);

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
                saveSection={saveSection}
                saveAndClose={saveAndClose}
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
            {/* Page Header */}
            <div className="page-header scrutinio">
                <div className="page-header-title">
                    <i className="fas fa-clipboard-check"></i>
                    Scrutinio
                </div>
                <div className="page-header-subtitle">
                    Inserimento dati votazioni per le tue sezioni
                </div>
            </div>

            {/* Search */}
            {sections.length > 3 && (
                <div className="sezioni-search">
                    <input
                        type="search"
                        className="sezioni-search-input"
                        placeholder="Cerca numero, città, indirizzo..."
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

            {/* My sections (assigned to me as RDL) */}
            {(mySections.length > 0 || totalMie > 0) && (
                <>
                    <div className="sezioni-section-header">
                        <i className="fas fa-user"></i>
                        Le mie sezioni
                        <span style={{ marginLeft: 'auto', fontWeight: 400 }}>
                            {searchText ? mySections.length : totalMie}
                        </span>
                    </div>

                    {Object.entries(myGrouped).map(([key, group]) => (
                        <div key={`my-${key}`}>
                            <div className="plesso-header">
                                <i className="fas fa-school"></i>
                                <div>
                                    <div>{group.name || group.address || 'Senza plesso'}</div>
                                    {group.name && group.address && (
                                        <div className="plesso-address">{group.address}</div>
                                    )}
                                </div>
                                <span className="plesso-count">{group.sections.length} sez.</span>
                            </div>
                            <ul className="sezioni-list">
                                {group.sections.map(renderSectionCard)}
                            </ul>
                        </div>
                    ))}
                </>
            )}

            {/* Other sections in my territory (as delegato/sub-delegato) */}
            {(otherSections.length > 0 || totalTerritorio > 0) && (
                <>
                    <div className="sezioni-section-header" style={{ background: '#fff3cd', color: '#856404' }}>
                        <i className="fas fa-users"></i>
                        Sezioni del territorio
                        <span style={{ marginLeft: 'auto', fontWeight: 400 }}>
                            {searchText ? otherSections.length : totalTerritorio}
                        </span>
                    </div>

                    {Object.entries(otherGrouped).map(([key, group]) => (
                        <div key={`other-${key}`}>
                            <div className="plesso-header">
                                <i className="fas fa-school"></i>
                                <div>
                                    <div>{group.name || group.address || 'Senza plesso'}</div>
                                    {group.name && group.address && (
                                        <div className="plesso-address">{group.address}</div>
                                    )}
                                </div>
                                <span className="plesso-count">{group.sections.length} sez.</span>
                            </div>
                            <ul className="sezioni-list">
                                {group.sections.map(renderSectionCard)}
                            </ul>
                        </div>
                    ))}
                </>
            )}

            {/* Infinite scroll sentinel and load more indicator */}
            {filteredSections.length > 0 && !searchText && (
                <div ref={sentinelRef} style={{ padding: '16px', textAlign: 'center', minHeight: '60px' }}>
                    {loadingMore ? (
                        <div className="spinner-border spinner-border-sm text-primary" role="status">
                            <span className="visually-hidden">Caricamento...</span>
                        </div>
                    ) : hasMore ? (
                        <button
                            className="btn btn-outline-primary btn-sm"
                            onClick={loadMore}
                        >
                            Carica altre sezioni ({totalSections - sections.length} rimanenti)
                        </button>
                    ) : totalSections > 0 ? (
                        <small className="text-muted">
                            Tutte le {totalSections} sezioni caricate
                        </small>
                    ) : null}
                </div>
            )}
        </>
    );
}

export default SectionList;
