import React, { useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';

// Configura il worker PDF.js
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

/**
 * Modal per visualizzare PDF
 * @param {string} url - URL del PDF (può essere proxied)
 * @param {string} originalUrl - URL originale del PDF (per aprire in nuova scheda)
 * @param {string} titolo - Titolo del documento
 * @param {function} onClose - Callback per chiudere il viewer
 */
function PDFViewer({ url, originalUrl, titolo, onClose }) {
    const [numPages, setNumPages] = useState(null);
    const [pageNumber, setPageNumber] = useState(1);
    const [scale, setScale] = useState(1.0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const onDocumentLoadSuccess = ({ numPages }) => {
        setNumPages(numPages);
        setLoading(false);
    };

    const onDocumentLoadError = (error) => {
        console.error('Error loading PDF:', error);
        setError('Impossibile caricare il PDF. Prova ad aprirlo in una nuova scheda.');
        setLoading(false);
    };

    const goToPrevPage = () => {
        setPageNumber(prev => Math.max(prev - 1, 1));
    };

    const goToNextPage = () => {
        setPageNumber(prev => Math.min(prev + 1, numPages || 1));
    };

    const zoomIn = () => {
        setScale(prev => Math.min(prev + 0.25, 3));
    };

    const zoomOut = () => {
        setScale(prev => Math.max(prev - 0.25, 0.5));
    };

    const openInNewTab = () => {
        // Usa URL originale per aprire in nuova scheda (non il proxy)
        window.open(originalUrl || url, '_blank');
    };

    return (
        <div className="pdf-viewer-overlay" onClick={onClose}>
            <div className="pdf-viewer-container" onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div className="pdf-viewer-header">
                    <div className="pdf-title">
                        <i className="fas fa-file-pdf me-2 text-danger"></i>
                        <span className="text-truncate">{titolo}</span>
                    </div>
                    <div className="pdf-actions">
                        <button
                            className="btn btn-sm btn-outline-light me-2"
                            onClick={openInNewTab}
                            title="Apri in nuova scheda"
                        >
                            <i className="fas fa-external-link-alt"></i>
                        </button>
                        <button
                            className="btn btn-sm btn-outline-light"
                            onClick={onClose}
                            title="Chiudi"
                        >
                            <i className="fas fa-times"></i>
                        </button>
                    </div>
                </div>

                {/* Toolbar */}
                <div className="pdf-viewer-toolbar">
                    <div className="pdf-toolbar-group">
                        <button
                            className="pdf-toolbar-btn"
                            onClick={goToPrevPage}
                            disabled={pageNumber <= 1}
                        >
                            <i className="fas fa-chevron-left"></i>
                        </button>
                        <span className="pdf-toolbar-label">
                            {pageNumber} / {numPages || '?'}
                        </span>
                        <button
                            className="pdf-toolbar-btn"
                            onClick={goToNextPage}
                            disabled={pageNumber >= (numPages || 1)}
                        >
                            <i className="fas fa-chevron-right"></i>
                        </button>
                    </div>

                    <div className="pdf-toolbar-group">
                        <button
                            className="pdf-toolbar-btn"
                            onClick={zoomOut}
                            disabled={scale <= 0.5}
                            title="Riduci"
                        >
                            <i className="fas fa-minus"></i>
                        </button>
                        <span className="pdf-toolbar-label">
                            {Math.round(scale * 100)}%
                        </span>
                        <button
                            className="pdf-toolbar-btn"
                            onClick={zoomIn}
                            disabled={scale >= 3}
                            title="Ingrandisci"
                        >
                            <i className="fas fa-plus"></i>
                        </button>
                    </div>
                </div>

                {/* PDF Content */}
                <div className="pdf-viewer-content">
                    {loading && (
                        <div className="pdf-loading">
                            <div className="spinner-border text-primary" role="status">
                                <span className="visually-hidden">Caricamento...</span>
                            </div>
                            <p className="mt-2">Caricamento PDF...</p>
                        </div>
                    )}

                    {error ? (
                        <div className="pdf-error">
                            <i className="fas fa-exclamation-triangle fa-3x text-warning mb-3"></i>
                            <p>{error}</p>
                            <button className="btn btn-primary" onClick={openInNewTab}>
                                <i className="fas fa-external-link-alt me-2"></i>
                                Apri in nuova scheda
                            </button>
                        </div>
                    ) : (
                        <Document
                            file={url}
                            onLoadSuccess={onDocumentLoadSuccess}
                            onLoadError={onDocumentLoadError}
                            loading={null}
                        >
                            <Page
                                pageNumber={pageNumber}
                                scale={scale}
                                renderTextLayer={true}
                                renderAnnotationLayer={true}
                            />
                        </Document>
                    )}
                </div>
            </div>

            <style>{`
                .pdf-viewer-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0, 0, 0, 0.85);
                    z-index: 1050;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }

                .pdf-viewer-container {
                    width: 95%;
                    max-width: 1000px;
                    height: 95vh;
                    background: #1a1a1a;
                    border-radius: 8px;
                    display: flex;
                    flex-direction: column;
                    overflow: hidden;
                }

                .pdf-viewer-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 12px 16px;
                    background: #2d2d2d;
                    border-bottom: 1px solid #444;
                }

                .pdf-title {
                    display: flex;
                    align-items: center;
                    color: white;
                    font-weight: 500;
                    overflow: hidden;
                    max-width: calc(100% - 100px);
                }

                .pdf-actions {
                    display: flex;
                    gap: 8px;
                }

                .pdf-viewer-toolbar {
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    gap: 16px;
                    padding: 8px 16px;
                    background: #252525;
                    border-bottom: 1px solid #444;
                }

                .pdf-toolbar-group {
                    display: inline-flex;
                    align-items: center;
                    background: #3a3a3a;
                    border-radius: 6px;
                    overflow: hidden;
                }

                .pdf-toolbar-btn {
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    width: 36px;
                    height: 32px;
                    border: none;
                    background: #4a4a4a;
                    color: white;
                    cursor: pointer;
                    transition: background 0.2s;
                }

                .pdf-toolbar-btn:hover:not(:disabled) {
                    background: #5a5a5a;
                }

                .pdf-toolbar-btn:disabled {
                    opacity: 0.4;
                    cursor: not-allowed;
                }

                .pdf-toolbar-label {
                    padding: 0 12px;
                    color: white;
                    font-size: 0.85rem;
                    white-space: nowrap;
                }

                .pdf-viewer-content {
                    flex: 1;
                    overflow: auto;
                    display: flex;
                    justify-content: center;
                    padding: 20px;
                    background: #333;
                }

                .pdf-viewer-content .react-pdf__Document {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                }

                .pdf-viewer-content .react-pdf__Page {
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
                    margin-bottom: 20px;
                }

                .pdf-loading, .pdf-error {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    text-align: center;
                    padding: 40px;
                }

                @media (max-width: 768px) {
                    .pdf-viewer-container {
                        width: 100%;
                        height: 100vh;
                        border-radius: 0;
                    }

                    .pdf-viewer-toolbar {
                        gap: 8px;
                        padding: 6px 10px;
                    }

                    .pdf-toolbar-btn {
                        width: 32px;
                        height: 28px;
                        font-size: 0.8rem;
                    }

                    .pdf-toolbar-label {
                        padding: 0 8px;
                        font-size: 0.75rem;
                    }

                    .pdf-viewer-header {
                        padding: 8px 12px;
                    }

                    .pdf-title {
                        font-size: 0.85rem;
                    }

                    .pdf-viewer-content {
                        padding: 10px;
                    }
                }
            `}</style>
        </div>
    );
}

export default PDFViewer;
