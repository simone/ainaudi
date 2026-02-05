import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './MarkdownModal.css';

/**
 * Modal component for displaying markdown documentation
 *
 * Usage:
 * <MarkdownModal
 *   isOpen={showModal}
 *   onClose={() => setShowModal(false)}
 *   markdownUrl="/LOOP_GUIDE.md"
 *   title="Loop Guide"
 * />
 */
function MarkdownModal({ isOpen, onClose, markdownUrl, title }) {
    const [content, setContent] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (isOpen && markdownUrl) {
            loadMarkdown();
        }
    }, [isOpen, markdownUrl]);

    const loadMarkdown = async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await fetch(markdownUrl);
            if (!response.ok) {
                throw new Error(`Failed to load: ${response.statusText}`);
            }
            const text = await response.text();
            setContent(text);
        } catch (err) {
            setError(`Errore caricamento documento: ${err.message}`);
            console.error('Markdown load error:', err);
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="markdown-modal-overlay" onClick={onClose}>
            <div className="markdown-modal-content" onClick={(e) => e.stopPropagation()}>
                <div className="markdown-modal-header">
                    <h2>{title || 'Documentazione'}</h2>
                    <button
                        className="markdown-modal-close"
                        onClick={onClose}
                        aria-label="Chiudi"
                    >
                        ×
                    </button>
                </div>

                <div className="markdown-modal-body">
                    {loading && (
                        <div className="markdown-loading">
                            <p>Caricamento...</p>
                        </div>
                    )}

                    {error && (
                        <div className="alert alert-danger">
                            {error}
                        </div>
                    )}

                    {!loading && !error && content && (
                        <div className="markdown-content">
                            <ReactMarkdown
                                remarkPlugins={[remarkGfm]}
                                components={{
                                    // Custom code block styling
                                    code({node, inline, className, children, ...props}) {
                                        return inline ? (
                                            <code className="inline-code" {...props}>
                                                {children}
                                            </code>
                                        ) : (
                                            <pre className="code-block">
                                                <code className={className} {...props}>
                                                    {children}
                                                </code>
                                            </pre>
                                        );
                                    },
                                    // Custom table styling
                                    table({node, ...props}) {
                                        return (
                                            <div className="table-wrapper">
                                                <table className="markdown-table" {...props} />
                                            </div>
                                        );
                                    }
                                }}
                            >
                                {content}
                            </ReactMarkdown>
                        </div>
                    )}
                </div>

                <div className="markdown-modal-footer">
                    <button
                        className="btn btn-secondary"
                        onClick={onClose}
                    >
                        Chiudi
                    </button>
                </div>
            </div>
        </div>
    );
}

export default MarkdownModal;
