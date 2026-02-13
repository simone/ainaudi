import React, { useState, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import './PDFViewer.css';

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
    const [pageWidth, setPageWidth] = useState(null);
    const [isLandscape, setIsLandscape] = useState(false);
    const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);

    // Block body scroll when PDF viewer is open
    useEffect(() => {
        // Save current scroll position
        const scrollY = window.scrollY;
        document.body.style.position = 'fixed';
        document.body.style.top = `-${scrollY}px`;
        document.body.style.left = '0';
        document.body.style.right = '0';
        document.body.style.overflow = 'hidden';

        return () => {
            // Restore scroll position
            document.body.style.position = '';
            document.body.style.top = '';
            document.body.style.left = '';
            document.body.style.right = '';
            document.body.style.overflow = '';
            window.scrollTo(0, scrollY);
        };
    }, []);

    // Detect mobile/desktop on resize
    useEffect(() => {
        const handleResize = () => {
            setIsMobile(window.innerWidth <= 768);
        };
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    const onDocumentLoadSuccess = ({ numPages }) => {
        setNumPages(numPages);
        setLoading(false);
    };

    const onPageLoadSuccess = (page) => {
        const viewport = page.getViewport({ scale: 1 });
        const isPageLandscape = viewport.width > viewport.height;
        setIsLandscape(isPageLandscape);

        // Calcola larghezza ottimale in base al container e all'orientamento
        // Container max-width è 1000px per portrait, 1400px per landscape
        const containerWidth = isPageLandscape ?
            Math.min(window.innerWidth * 0.9, 1400) :
            Math.min(window.innerWidth * 0.9, 1000);

        // Sottrai padding (40px totale)
        const availableWidth = containerWidth - 40;
        setPageWidth(availableWidth);
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
        if (pageWidth) {
            setPageWidth(prev => Math.min(prev * 1.25, 3000));
        } else {
            setScale(prev => Math.min(prev + 0.25, 3));
        }
    };

    const zoomOut = () => {
        if (pageWidth) {
            setPageWidth(prev => Math.max(prev * 0.8, 300));
        } else {
            setScale(prev => Math.max(prev - 0.25, 0.5));
        }
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

                {/* Toolbar - only show navigation on desktop */}
                {!isMobile && (
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
                                title="Riduci"
                            >
                                <i className="fas fa-minus"></i>
                            </button>
                            <span className="pdf-toolbar-label">
                                Zoom
                            </span>
                            <button
                                className="pdf-toolbar-btn"
                                onClick={zoomIn}
                                title="Ingrandisci"
                            >
                                <i className="fas fa-plus"></i>
                            </button>
                        </div>
                    </div>
                )}

                {/* Mobile: Show page count */}
                {isMobile && numPages && (
                    <div className="pdf-viewer-toolbar pdf-mobile-info">
                        <span className="pdf-toolbar-label">
                            {numPages} {numPages === 1 ? 'pagina' : 'pagine'}
                        </span>
                    </div>
                )}

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
                            {isMobile ? (
                                // Mobile: Render all pages for continuous scroll
                                Array.from(new Array(numPages), (el, index) => (
                                    <Page
                                        key={`page_${index + 1}`}
                                        pageNumber={index + 1}
                                        width={pageWidth || window.innerWidth - 40}
                                        onLoadSuccess={index === 0 ? onPageLoadSuccess : undefined}
                                        renderTextLayer={false}
                                        renderAnnotationLayer={false}
                                        className="pdf-page-mobile"
                                    />
                                ))
                            ) : (
                                // Desktop: Single page with navigation
                                <Page
                                    pageNumber={pageNumber}
                                    width={pageWidth}
                                    scale={pageWidth ? undefined : scale}
                                    onLoadSuccess={onPageLoadSuccess}
                                    renderTextLayer={false}
                                    renderAnnotationLayer={false}
                                />
                            )}
                        </Document>
                    )}
                </div>
            </div>
        </div>
    );
}

export default PDFViewer;
