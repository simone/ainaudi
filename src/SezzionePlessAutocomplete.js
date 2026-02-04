import React, { useState, useEffect, useRef } from 'react';

const SERVER_API = process.env.NODE_ENV === 'development' ? process.env.REACT_APP_API_URL : '';

function SezzionePlessAutocomplete({ value, onChange, disabled, placeholder, comuneId, municipio, onMunicipioChange }) {
    const [query, setQuery] = useState('');
    const [suggestions, setSuggestions] = useState([]);
    const [showSuggestions, setShowSuggestions] = useState(false);
    const [loading, setLoading] = useState(false);
    const [selectedIndex, setSelectedIndex] = useState(-1);
    const wrapperRef = useRef(null);
    const inputRef = useRef(null);

    // Display the selected sezione or allow typing
    const displayValue = value ? value.label : query;

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
                setShowSuggestions(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    useEffect(() => {
        const fetchSuggestions = async () => {
            if (!comuneId || query.length < 1) {
                setSuggestions([]);
                return;
            }

            setLoading(true);
            try {
                // Use public search endpoint for RDL registration
                const searchParams = new URLSearchParams({
                    comune_id: comuneId,
                    q: query
                });

                const response = await fetch(`${SERVER_API}/api/sections/search-public/?${searchParams}`);
                const data = await response.json();

                if (Array.isArray(data)) {
                    // Filter by municipio if one is selected
                    const filtered = municipio
                        ? data.filter(s => s.municipio && s.municipio.numero === municipio)
                        : data;
                    setSuggestions(filtered);
                } else {
                    setSuggestions([]);
                }
                setSelectedIndex(-1);
            } catch (error) {
                console.error('Error fetching sezioni:', error);
                setSuggestions([]);
            } finally {
                setLoading(false);
            }
        };

        const debounceTimer = setTimeout(fetchSuggestions, 300);
        return () => clearTimeout(debounceTimer);
    }, [query, comuneId, municipio]);

    const handleInputChange = (e) => {
        const newValue = e.target.value;
        setQuery(newValue);
        setShowSuggestions(true);
        // When user types manually without selecting, still allow free text
        // Only clear selection if they had selected a sezione before
        if (value && typeof value === 'object') {
            onChange(null);
        }
    };

    const handleSelect = (sezione) => {
        const label = `Sez. ${sezione.numero}${sezione.denominazione ? ` - ${sezione.denominazione}` : ''}${sezione.indirizzo ? `, ${sezione.indirizzo}` : ''}`;
        onChange({
            ...sezione,
            label
        });

        // Auto-select municipio if not already selected and sezione has one
        if (!municipio && sezione.municipio && onMunicipioChange) {
            onMunicipioChange(sezione.municipio.numero);
        }

        setQuery('');
        setShowSuggestions(false);
        setSelectedIndex(-1);
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Escape') {
            setShowSuggestions(false);
            setSelectedIndex(-1);
            return;
        }

        if (!showSuggestions || suggestions.length === 0) {
            // If Enter is pressed and no suggestions shown, treat as free text
            if (e.key === 'Enter' && query.trim()) {
                e.preventDefault();
                onChange({ freeText: true, text: query.trim() });
                setShowSuggestions(false);
            }
            return;
        }

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                setSelectedIndex(prev => Math.min(prev + 1, suggestions.length - 1));
                break;
            case 'ArrowUp':
                e.preventDefault();
                setSelectedIndex(prev => Math.max(prev - 1, 0));
                break;
            case 'Enter':
                e.preventDefault();
                if (selectedIndex >= 0 && suggestions[selectedIndex]) {
                    handleSelect(suggestions[selectedIndex]);
                } else if (query.trim()) {
                    // Enter without selection: treat as free text
                    onChange({ freeText: true, text: query.trim() });
                    setShowSuggestions(false);
                }
                break;
            default:
                break;
        }
    };

    const handleClear = () => {
        onChange(null);
        setQuery('');
        setSuggestions([]);
        inputRef.current?.focus();
    };

    const handleInputBlur = () => {
        // When input loses focus, if user typed something but didn't select from suggestions,
        // treat it as free text and pass it to parent
        if (query.trim() && !value) {
            // Pass free text as a string instead of sezione object
            onChange({ freeText: true, text: query.trim() });
        }
        setShowSuggestions(false);
    };

    const highlightMatch = (text, query) => {
        if (!query || !text) return text;
        const parts = text.split(new RegExp(`(${query})`, 'gi'));
        return parts.map((part, i) =>
            part.toLowerCase() === query.toLowerCase()
                ? <strong key={i}>{part}</strong>
                : part
        );
    };

    return (
        <div ref={wrapperRef} style={{ position: 'relative' }}>
            <div className="input-group">
                <input
                    ref={inputRef}
                    type="text"
                    className="form-control"
                    value={displayValue}
                    onChange={handleInputChange}
                    onFocus={() => !value && query.length >= 1 && setShowSuggestions(true)}
                    onBlur={handleInputBlur}
                    onKeyDown={handleKeyDown}
                    placeholder={placeholder || "Cerca sezione/plesso..."}
                    disabled={disabled || !comuneId}
                    autoComplete="off"
                />
                {value && !disabled && (
                    <button
                        type="button"
                        className="btn btn-outline-secondary"
                        onClick={handleClear}
                        title="Cancella"
                    >
                        &times;
                    </button>
                )}
            </div>

            {showSuggestions && (suggestions.length > 0 || loading) && (
                <ul
                    className="list-group"
                    onMouseDown={(e) => e.preventDefault()}
                    style={{
                        position: 'absolute',
                        top: '100%',
                        left: 0,
                        right: 0,
                        zIndex: 1050,
                        maxHeight: '300px',
                        overflowY: 'auto',
                        boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
                    }}
                >
                    {loading ? (
                        <li className="list-group-item text-muted">
                            <span className="spinner-border spinner-border-sm me-2"></span>
                            Caricamento sezioni...
                        </li>
                    ) : (
                        suggestions.map((sezione, index) => (
                            <li
                                key={sezione.id}
                                className={`list-group-item list-group-item-action ${index === selectedIndex ? 'active' : ''}`}
                                onMouseDown={(e) => {
                                    e.preventDefault();
                                    handleSelect(sezione);
                                }}
                                style={{ cursor: 'pointer' }}
                            >
                                <div>
                                    <strong>Sez. {highlightMatch(sezione.numero.toString(), query)}</strong>
                                    {sezione.denominazione && (
                                        <div className="small text-muted">
                                            {highlightMatch(sezione.denominazione, query)}
                                        </div>
                                    )}
                                    {sezione.indirizzo && (
                                        <div className="small text-muted">
                                            {highlightMatch(sezione.indirizzo, query)}
                                        </div>
                                    )}
                                </div>
                            </li>
                        ))
                    )}
                </ul>
            )}

            {showSuggestions && !loading && query.length >= 1 && suggestions.length === 0 && comuneId && (
                <ul
                    className="list-group"
                    style={{
                        position: 'absolute',
                        top: '100%',
                        left: 0,
                        right: 0,
                        zIndex: 1050,
                        boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
                    }}
                >
                    <li className="list-group-item text-muted">
                        Nessuna sezione trovata
                    </li>
                </ul>
            )}
        </div>
    );
}

export default SezzionePlessAutocomplete;
