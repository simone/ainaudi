import React, { useState, useEffect } from 'react';

/**
 * Modal di conferma riutilizzabile per sostituire window.confirm e window.prompt
 */
function ConfirmModal({
    show,
    onConfirm,
    onCancel,
    title = 'Conferma',
    message,
    confirmText = 'Conferma',
    cancelText = 'Annulla',
    confirmVariant = 'primary',
    confirmDisabled = false,
    showInput = false,
    inputLabel = '',
    inputPlaceholder = '',
    inputRequired = false,
    children
}) {
    const [inputValue, setInputValue] = useState('');

    // Reset input when modal opens
    useEffect(() => {
        if (show) {
            setInputValue('');
        }
    }, [show]);

    // Handle keyboard escape
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (show && e.key === 'Escape') {
                onCancel();
            }
        };
        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [show, onCancel]);

    if (!show) return null;

    const handleConfirm = () => {
        if (showInput && inputRequired && !inputValue.trim()) {
            return; // Don't close if input is required but empty
        }
        onConfirm(showInput ? inputValue : true);
    };

    const handleBackdropClick = (e) => {
        if (e.target === e.currentTarget) {
            onCancel();
        }
    };

    return (
        <div
            className="modal-backdrop-custom"
            onClick={handleBackdropClick}
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-title"
        >
            <div className="modal-custom" role="document">
                <div className="modal-custom-header">
                    <h5 id="modal-title" className="mb-0">{title}</h5>
                    <button
                        type="button"
                        className="btn-close"
                        onClick={onCancel}
                        aria-label="Chiudi"
                    ></button>
                </div>
                <div className="modal-custom-body">
                    {message && <p>{message}</p>}
                    {children}
                    {showInput && (
                        <div className="mt-3">
                            {inputLabel && (
                                <label className="form-label">{inputLabel}</label>
                            )}
                            <input
                                type="text"
                                className="form-control"
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                placeholder={inputPlaceholder}
                                autoFocus
                            />
                        </div>
                    )}
                </div>
                <div className="modal-custom-footer">
                    <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={onCancel}
                    >
                        {cancelText}
                    </button>
                    <button
                        type="button"
                        className={`btn btn-${confirmVariant}`}
                        onClick={handleConfirm}
                        disabled={confirmDisabled || (showInput && inputRequired && !inputValue.trim())}
                    >
                        {confirmText}
                    </button>
                </div>
            </div>
        </div>
    );
}

export default ConfirmModal;
