import React, { useState, useEffect, useRef } from 'react';

function EmailAutocomplete({
    value,
    onChange,
    emails = [],
    placeholder = "Cerca email...",
    className = "",
    disabled = false,
    required = false,
    maxSuggestions = 10
}) {
    const [inputValue, setInputValue] = useState(value || '');
    const [suggestions, setSuggestions] = useState([]);
    const [showSuggestions, setShowSuggestions] = useState(false);
    const [selectedIndex, setSelectedIndex] = useState(-1);
    const inputRef = useRef(null);
    const suggestionsRef = useRef(null);

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

        const filtered = emails
            .filter(email =>
                email.toLowerCase().includes(inputValue.toLowerCase())
            )
            .slice(0, maxSuggestions);

        setSuggestions(filtered);
        setSelectedIndex(-1);
    }, [inputValue, emails, maxSuggestions]);

    // Handle click outside to close suggestions
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
        setShowSuggestions(true);
        onChange(newValue);
    };

    const handleSuggestionClick = (email) => {
        setInputValue(email);
        setShowSuggestions(false);
        onChange(email);
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
            case 'Escape':
                setShowSuggestions(false);
                break;
            default:
                break;
        }
    };

    const highlightMatch = (text, query) => {
        if (!query) return text;
        const regex = new RegExp(`(${query})`, 'gi');
        const parts = text.split(regex);
        return parts.map((part, i) =>
            regex.test(part) ? <strong key={i} className="text-primary">{part}</strong> : part
        );
    };

    return (
        <div className="position-relative" style={{ width: '100%' }}>
            <input
                ref={inputRef}
                type="email"
                className={`form-control ${className}`}
                value={inputValue}
                onChange={handleInputChange}
                onFocus={() => inputValue.length >= 2 && setShowSuggestions(true)}
                onKeyDown={handleKeyDown}
                placeholder={placeholder}
                disabled={disabled}
                required={required}
                autoComplete="off"
            />
            {showSuggestions && suggestions.length > 0 && (
                <div
                    ref={suggestionsRef}
                    className="position-absolute w-100 bg-white border rounded shadow-sm"
                    style={{
                        zIndex: 1050,
                        maxHeight: '300px',
                        overflowY: 'auto',
                        top: '100%',
                        left: 0
                    }}
                >
                    {suggestions.map((email, index) => (
                        <div
                            key={email}
                            className={`px-3 py-2 cursor-pointer ${
                                index === selectedIndex ? 'bg-primary text-white' : 'hover-bg-light'
                            }`}
                            style={{ cursor: 'pointer' }}
                            onClick={() => handleSuggestionClick(email)}
                            onMouseEnter={() => setSelectedIndex(index)}
                        >
                            {highlightMatch(email, inputValue)}
                        </div>
                    ))}
                </div>
            )}
            {showSuggestions && inputValue.length >= 2 && suggestions.length === 0 && (
                <div
                    className="position-absolute w-100 bg-white border rounded shadow-sm px-3 py-2 text-muted"
                    style={{ zIndex: 1050, top: '100%', left: 0 }}
                >
                    Nessun risultato per "{inputValue}"
                </div>
            )}
        </div>
    );
}

export default EmailAutocomplete;
