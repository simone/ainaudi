import React, { useState, useEffect, useRef } from 'react';

const SERVER_API = process.env.NODE_ENV === 'development' ? process.env.REACT_APP_API_URL : '';

function ComuneAutocomplete({ value, onChange, disabled, placeholder, searchEndpoint, authenticated }) {
    // Default endpoint for public RDL registration, can be overridden
    const endpoint = searchEndpoint || '/api/rdl/comuni/search';
    // If authenticated, include JWT token in request
    const needsAuth = authenticated || (searchEndpoint && searchEndpoint !== '/api/rdl/comuni/search');
    const [query, setQuery] = useState('');
    const [suggestions, setSuggestions] = useState([]);
    const [showSuggestions, setShowSuggestions] = useState(false);
    const [loading, setLoading] = useState(false);
    const [selectedIndex, setSelectedIndex] = useState(-1);
    const wrapperRef = useRef(null);
    const inputRef = useRef(null);

    // Display the selected comune or allow typing
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
            if (query.length < 2) {
                setSuggestions([]);
                return;
            }

            setLoading(true);
            try {
                const fetchOptions = {};
                if (needsAuth) {
                    const token = localStorage.getItem('rdl_access_token');
                    if (token) {
                        fetchOptions.headers = {
                            'Authorization': `Bearer ${token}`
                        };
                    }
                }
                const response = await fetch(`${SERVER_API}${endpoint}?q=${encodeURIComponent(query)}`, fetchOptions);
                const data = await response.json();
                setSuggestions(data.comuni || []);
                setSelectedIndex(-1);
            } catch (error) {
                console.error('Error fetching comuni:', error);
                setSuggestions([]);
            } finally {
                setLoading(false);
            }
        };

        const debounceTimer = setTimeout(fetchSuggestions, 300);
        return () => clearTimeout(debounceTimer);
    }, [query, endpoint, needsAuth]);

    const handleInputChange = (e) => {
        const newValue = e.target.value;
        setQuery(newValue);
        setShowSuggestions(true);
        // Clear selection when user types
        if (value) {
            onChange(null);
        }
    };

    const handleSelect = (comune) => {
        onChange(comune);
        setQuery('');
        setShowSuggestions(false);
        setSelectedIndex(-1);
    };

    const handleKeyDown = (e) => {
        if (!showSuggestions || suggestions.length === 0) return;

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
                }
                break;
            case 'Escape':
                setShowSuggestions(false);
                setSelectedIndex(-1);
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

    const highlightMatch = (text, query) => {
        if (!query) return text;
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
                    onFocus={() => !value && query.length >= 2 && setShowSuggestions(true)}
                    onKeyDown={handleKeyDown}
                    placeholder={placeholder || "Cerca comune..."}
                    disabled={disabled}
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
                            Caricamento...
                        </li>
                    ) : (
                        suggestions.map((comune, index) => (
                            <li
                                key={comune.id}
                                className={`list-group-item list-group-item-action ${index === selectedIndex ? 'active' : ''}`}
                                onClick={() => handleSelect(comune)}
                                style={{ cursor: 'pointer' }}
                            >
                                <div>
                                    {highlightMatch(comune.label, query)}
                                </div>
                                {comune.has_municipi && (
                                    <small className="text-muted">
                                        (con municipi)
                                    </small>
                                )}
                            </li>
                        ))
                    )}
                </ul>
            )}

            {showSuggestions && !loading && query.length >= 2 && suggestions.length === 0 && (
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
                        Nessun comune trovato
                    </li>
                </ul>
            )}
        </div>
    );
}

export default ComuneAutocomplete;
