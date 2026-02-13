import React, { useState, useEffect, useRef, useMemo } from 'react';

/**
 * JSONPath Autocomplete with dynamic schema extraction.
 *
 * Props:
 * - value: Current JSONPath expression
 * - onChange: Callback when value changes
 * - exampleData: Example JSON object to extract paths from
 * - placeholder: Input placeholder
 */
function JSONPathAutocomplete({
    value,
    onChange,
    exampleData = {},
    placeholder = 'es: $.delegato.cognome + " " + $.delegato.nome',
    className = "",
    disabled = false,
    required = false
}) {
    const [inputValue, setInputValue] = useState(value || '');
    const [suggestions, setSuggestions] = useState([]);
    const [showSuggestions, setShowSuggestions] = useState(false);
    const [selectedIndex, setSelectedIndex] = useState(-1);
    const [cursorPosition, setCursorPosition] = useState(0);

    const inputRef = useRef(null);
    const suggestionsRef = useRef(null);

    // Extract all JSONPath from example data (memoized)
    const availablePaths = useMemo(() => {
        return extractJSONPaths(exampleData);
    }, [exampleData]);

    // Sync with external value
    useEffect(() => {
        setInputValue(value || '');
    }, [value]);

    // Filter suggestions based on input
    useEffect(() => {
        if (!inputValue || inputValue.length < 2) {
            setSuggestions([]);
            return;
        }

        // Get current token at cursor
        const currentToken = getCurrentToken(inputValue, cursorPosition);

        // Don't suggest inside quoted strings
        if (isInsideQuotes(inputValue, cursorPosition)) {
            setSuggestions([]);
            return;
        }

        // Filter paths that match current token
        const filtered = availablePaths
            .filter(item => {
                if (!currentToken) return true;
                return item.path.toLowerCase().includes(currentToken.toLowerCase());
            })
            .slice(0, 15);

        setSuggestions(filtered);
        setSelectedIndex(-1);
    }, [inputValue, cursorPosition, availablePaths]);

    // Handle click outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (
                inputRef.current &&
                !inputRef.current.contains(event.target) &&
                suggestionsRef.current &&
                !suggestionsRef.current.contains(event.target)
            ) {
                setShowSuggestions(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleInputChange = (e) => {
        const newValue = e.target.value;
        setInputValue(newValue);
        setCursorPosition(e.target.selectionStart);
        setShowSuggestions(true);
        onChange(newValue);
    };

    const handleCursorMove = (e) => {
        setCursorPosition(e.target.selectionStart);
    };

    const handleSuggestionClick = (suggestion) => {
        const currentToken = getCurrentToken(inputValue, cursorPosition);

        if (currentToken) {
            // Replace current token with selected path
            const tokenStart = inputValue.lastIndexOf(currentToken, cursorPosition);
            const before = inputValue.substring(0, tokenStart);
            const after = inputValue.substring(tokenStart + currentToken.length);
            const newValue = before + suggestion.path + after;

            setInputValue(newValue);
            onChange(newValue);
        } else {
            // Append to current position or end
            const before = inputValue.substring(0, cursorPosition);
            const after = inputValue.substring(cursorPosition);
            const newValue = before + suggestion.path + after;

            setInputValue(newValue);
            onChange(newValue);
        }

        setShowSuggestions(false);
    };

    const handleKeyDown = (e) => {
        if (!showSuggestions || suggestions.length === 0) return;

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                setSelectedIndex(prev =>
                    prev < suggestions.length - 1 ? prev + 1 : prev
                );
                break;
            case 'ArrowUp':
                e.preventDefault();
                setSelectedIndex(prev => prev > 0 ? prev - 1 : -1);
                break;
            case 'Enter':
                e.preventDefault();
                if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
                    handleSuggestionClick(suggestions[selectedIndex]);
                }
                break;
            case 'Tab':
                e.preventDefault();
                if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
                    handleSuggestionClick(suggestions[selectedIndex]);
                } else if (suggestions.length === 1) {
                    // Auto-complete if there's only 1 suggestion
                    handleSuggestionClick(suggestions[0]);
                }
                break;
            case 'Escape':
                setShowSuggestions(false);
                break;
            default:
                break;
        }
    };

    return (
        <div className="position-relative" style={{ width: '100%' }}>
            <input
                ref={inputRef}
                type="text"
                className={`form-control font-monospace ${className}`}
                value={inputValue}
                onChange={handleInputChange}
                onSelect={handleCursorMove}
                onClick={handleCursorMove}
                onFocus={() => setShowSuggestions(true)}
                onKeyDown={handleKeyDown}
                placeholder={placeholder}
                disabled={disabled}
                required={required}
                autoComplete="off"
                style={{ fontSize: '0.9em' }}
            />

            {showSuggestions && suggestions.length > 0 && (
                <div
                    ref={suggestionsRef}
                    className="position-absolute w-100 bg-white border rounded shadow"
                    style={{
                        zIndex: 1050,
                        maxHeight: '300px',
                        overflowY: 'auto',
                        top: '100%',
                        left: 0,
                        marginTop: '2px'
                    }}
                >
                    {suggestions.map((item, index) => (
                        <div
                            key={item.path}
                            className={`px-3 py-2 ${
                                index === selectedIndex ? 'bg-primary text-white' : ''
                            }`}
                            style={{ cursor: 'pointer' }}
                            onClick={() => handleSuggestionClick(item)}
                            onMouseEnter={() => setSelectedIndex(index)}
                        >
                            <div className="d-flex justify-content-between align-items-center">
                                <code className={index === selectedIndex ? 'text-white' : 'text-primary'}>
                                    {item.path}
                                </code>
                                <span className="badge bg-secondary ms-2">
                                    {item.type}
                                </span>
                            </div>
                            <small className={index === selectedIndex ? 'text-white-50' : 'text-muted'}>
                                Esempio: {item.sample}
                            </small>
                        </div>
                    ))}
                </div>
            )}

            {showSuggestions && inputValue && suggestions.length === 0 && (
                <div
                    className="position-absolute w-100 bg-white border rounded shadow px-3 py-2 text-muted"
                    style={{ zIndex: 1050, top: '100%', left: 0, marginTop: '2px' }}
                >
                    Nessun campo trovato
                </div>
            )}
        </div>
    );
}

// Helper: Extract JSONPath from JSON
function extractJSONPaths(json, prefix = '$') {
    const paths = [];

    if (json === null || json === undefined) return paths;

    if (Array.isArray(json)) {
        paths.push({
            path: prefix,
            type: 'array',
            sample: `[${json.length} elementi]`
        });

        if (json.length > 0) {
            const itemPaths = extractJSONPaths(json[0], `${prefix}[]`);
            paths.push(...itemPaths);
        }

        return paths;
    }

    if (typeof json === 'object') {
        for (const [key, value] of Object.entries(json)) {
            const currentPath = `${prefix}.${key}`;

            if (value === null) {
                paths.push({ path: currentPath, type: 'null', sample: 'null' });
            } else if (Array.isArray(value)) {
                paths.push({
                    path: currentPath,
                    type: 'array',
                    sample: `[${value.length} elementi]`
                });

                if (value.length > 0) {
                    const itemPaths = extractJSONPaths(value[0], `${currentPath}[]`);
                    paths.push(...itemPaths);
                }
            } else if (typeof value === 'object') {
                const nestedPaths = extractJSONPaths(value, currentPath);
                paths.push(...nestedPaths);
            } else {
                paths.push({
                    path: currentPath,
                    type: typeof value,
                    sample: String(value).length > 50
                        ? String(value).substring(0, 50) + '...'
                        : String(value)
                });
            }
        }
    }

    return paths;
}

// Helper: Get current token at cursor
function getCurrentToken(text, cursorPos) {
    const before = text.substring(0, cursorPos);
    const tokens = before.split(/[\s+]/);
    const currentToken = tokens[tokens.length - 1].trim();
    return currentToken.startsWith('$') ? currentToken : '';
}

// Helper: Check if cursor is inside quotes
function isInsideQuotes(text, cursorPos) {
    const before = text.substring(0, cursorPos);
    let inSingle = false;
    let inDouble = false;

    for (let i = 0; i < before.length; i++) {
        const char = before[i];
        const prevChar = i > 0 ? before[i - 1] : null;

        if (prevChar === '\\') continue;

        if (char === "'" && !inDouble) {
            inSingle = !inSingle;
        } else if (char === '"' && !inSingle) {
            inDouble = !inDouble;
        }
    }

    return inSingle || inDouble;
}

export default JSONPathAutocomplete;
