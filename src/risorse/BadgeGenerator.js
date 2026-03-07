import React, { useState, useEffect, useRef } from 'react';
import './BadgeGenerator.css';

/**
 * Badge Generator - Mobile-first swipe interface per scegliere badge RDL
 * Stile Tinder/Instagram Stories con swipe gestures
 */
function BadgeGenerator({ client, onClose }) {
    const [variants, setVariants] = useState([]);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [downloading, setDownloading] = useState(false);
    const [imageBlobUrls, setImageBlobUrls] = useState({}); // Cache blob URLs per variant

    // Touch/drag state
    const [touchStart, setTouchStart] = useState(null);
    const [touchOffset, setTouchOffset] = useState(0);
    const [isDragging, setIsDragging] = useState(false);

    const containerRef = useRef(null);

    useEffect(() => {
        loadVariants();
        // Cleanup blob URLs on unmount
        return () => {
            Object.values(imageBlobUrls).forEach(url => URL.revokeObjectURL(url));
        };
    }, []);

    const loadVariants = async () => {
        setLoading(true);
        setError(null);

        try {
            const data = await client.risorse.badgeVariants();

            // Converti l'oggetto variants in array e ordina
            let variantsList = Object.values(data.variants).sort((a, b) => {
                // Prima cards, poi lockscreens
                if (a.type !== b.type) {
                    return a.type === 'card' ? -1 : 1;
                }
                return a.id.localeCompare(b.id);
            });

            // FILTRA: mostra lockscreen SOLO su mobile
            const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
            if (!isMobile) {
                // Rimuovi lockscreen se non è mobile
                variantsList = variantsList.filter(v => v.type === 'card');
            }

            setVariants(variantsList);
        } catch (err) {
            console.error('Errore caricamento varianti:', err);
            setError('Errore nel caricamento delle varianti badge');
        } finally {
            setLoading(false);
        }
    };

    const currentVariant = variants[currentIndex];

    // Load image with authentication and return blob URL
    const loadBadgeImage = async (variantId) => {
        // Check cache first
        if (imageBlobUrls[variantId]) {
            return imageBlobUrls[variantId];
        }

        const apiUrl = client.server || process.env.REACT_APP_API_URL || window.location.origin.replace(':3000', ':3001');
        const url = `${apiUrl}/api/risorse/generate-badge/?variant=${variantId}`;

        try {
            const response = await fetch(url, {
                headers: { 'Authorization': client.authHeader }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const blob = await response.blob();
            const blobUrl = URL.createObjectURL(blob);

            // Cache the blob URL
            setImageBlobUrls(prev => ({ ...prev, [variantId]: blobUrl }));

            return blobUrl;
        } catch (err) {
            console.error('Errore caricamento badge:', err);
            return null;
        }
    };

    // Load current image when variant changes
    useEffect(() => {
        if (currentVariant?.id) {
            loadBadgeImage(currentVariant.id);
        }
    }, [currentIndex, currentVariant]);

    const handlePrevious = () => {
        if (currentIndex > 0) {
            setCurrentIndex(currentIndex - 1);
        }
    };

    const handleNext = () => {
        if (currentIndex < variants.length - 1) {
            setCurrentIndex(currentIndex + 1);
        }
    };

    // Touch handlers for swipe gestures
    const handleTouchStart = (e) => {
        setTouchStart(e.touches[0].clientX);
        setIsDragging(true);
    };

    const handleTouchMove = (e) => {
        if (touchStart === null) return;

        const currentTouch = e.touches[0].clientX;
        const diff = currentTouch - touchStart;

        // Limita lo spostamento
        const maxOffset = 100;
        setTouchOffset(Math.max(-maxOffset, Math.min(maxOffset, diff)));
    };

    const handleTouchEnd = () => {
        if (Math.abs(touchOffset) > 50) {
            if (touchOffset > 0) {
                handlePrevious();
            } else {
                handleNext();
            }
        }

        setTouchStart(null);
        setTouchOffset(0);
        setIsDragging(false);
    };

    // Mouse handlers (for desktop)
    const handleMouseDown = (e) => {
        setTouchStart(e.clientX);
        setIsDragging(true);
    };

    const handleMouseMove = (e) => {
        if (touchStart === null || !isDragging) return;

        const diff = e.clientX - touchStart;
        const maxOffset = 100;
        setTouchOffset(Math.max(-maxOffset, Math.min(maxOffset, diff)));
    };

    const handleMouseUp = () => {
        if (Math.abs(touchOffset) > 50) {
            if (touchOffset > 0) {
                handlePrevious();
            } else {
                handleNext();
            }
        }

        setTouchStart(null);
        setTouchOffset(0);
        setIsDragging(false);
    };

    const handleDownload = async () => {
        if (!currentVariant) return;

        setDownloading(true);

        try {
            // Use cached blob URL if available, otherwise load it
            let blobUrl = imageBlobUrls[currentVariant.id];
            if (!blobUrl) {
                blobUrl = await loadBadgeImage(currentVariant.id);
            }

            if (!blobUrl) throw new Error('Errore caricamento badge');

            // Fetch blob from blob URL to download
            const response = await fetch(blobUrl);
            const blob = await response.blob();
            const downloadUrl = URL.createObjectURL(blob);

            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = `badge_rdl_${currentVariant.id}.png`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(downloadUrl);

        } catch (err) {
            console.error('Errore download:', err);
            setError('Errore durante il download del badge');
        } finally {
            setDownloading(false);
        }
    };

    const handlePrint = async () => {
        if (!currentVariant) return;

        try {
            // Use cached blob URL if available, otherwise load it
            let blobUrl = imageBlobUrls[currentVariant.id];
            if (!blobUrl) {
                blobUrl = await loadBadgeImage(currentVariant.id);
            }

            if (!blobUrl) throw new Error('Errore caricamento badge');

            // Crea HTML per stampa con dimensioni corrette
            const isCard = currentVariant.type === 'card';

            const printWindow = window.open('', '_blank');
            if (!printWindow) return;

            const doc = printWindow.document;

            // Crea struttura HTML con DOM
            doc.title = `Stampa Badge - ${currentVariant.name}`;

            // Aggiungi style
            const style = doc.createElement('style');
            style.textContent = `
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }

                body {
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    background: #f5f5f5;
                }

                img {
                    max-width: 100%;
                    height: auto;
                    display: block;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }

                @media print {
                    body {
                        background: white;
                    }

                    img {
                        box-shadow: none;
                        ${isCard ? `
                            width: 85mm !important;
                            height: 55mm !important;
                            max-width: 85mm !important;
                            max-height: 55mm !important;
                        ` : `
                            width: 100%;
                            height: auto;
                        `}
                    }

                    @page {
                        ${isCard ? `
                            size: 85mm 55mm;
                            margin: 0;
                        ` : `
                            size: A4 portrait;
                            margin: 10mm;
                        `}
                    }
                }
            `;
            doc.head.appendChild(style);

            // Aggiungi immagine
            const img = doc.createElement('img');
            img.src = blobUrl;
            img.alt = currentVariant.name;

            img.onload = () => {
                setTimeout(() => {
                    printWindow.print();
                }, 100);
            };

            doc.body.appendChild(img);

        } catch (err) {
            console.error('Errore stampa:', err);
            setError('Errore durante la stampa del badge');
        }
    };

    const handleSetAsWallpaper = async () => {
        if (!currentVariant) return;

        try {
            // Use cached blob URL if available, otherwise load it
            let blobUrl = imageBlobUrls[currentVariant.id];
            if (!blobUrl) {
                blobUrl = await loadBadgeImage(currentVariant.id);
            }

            if (!blobUrl) throw new Error('Errore caricamento badge');

            const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

            if (isMobile) {
                // Su mobile, apri l'immagine a schermo intero in una nuova tab
                // L'utente può fare tap lungo per salvare direttamente
                window.open(blobUrl, '_blank');
            } else {
                alert(
                    'Funzione disponibile solo su smartphone.\n\n' +
                    'Scarica l\'immagine e trasferiscila sul tuo telefono per impostarla come sfondo della schermata di blocco.'
                );
            }
        } catch (err) {
            console.error('Errore apertura immagine:', err);
            setError('Errore durante l\'apertura dell\'immagine');
        }
    };

    if (loading) {
        return (
            <div className="badge-generator-modal">
                <div className="badge-generator-overlay" onClick={onClose}></div>
                <div className="badge-generator-content">
                    <div className="loading-container">
                        <div className="spinner-border text-primary"></div>
                        <p>Caricamento varianti...</p>
                    </div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="badge-generator-modal">
                <div className="badge-generator-overlay" onClick={onClose}></div>
                <div className="badge-generator-content">
                    <div className="error-container">
                        <i className="fas fa-exclamation-circle text-danger"></i>
                        <p>{error}</p>
                        <button className="btn btn-primary" onClick={onClose}>
                            Chiudi
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    if (!variants.length) {
        return null;
    }

    return (
        <div className="badge-generator-modal">
            <div className="badge-generator-overlay" onClick={onClose}></div>

            <div className="badge-generator-content">
                {/* Header */}
                <div className="badge-generator-header">
                    <button className="close-btn" onClick={onClose}>
                        <i className="fas fa-times"></i>
                    </button>
                    <h2>Genera Badge RDL</h2>
                    <p className="subtitle">Scorri per scegliere il design</p>
                </div>

                {/* Progress indicators */}
                <div className="progress-indicators">
                    {variants.map((_, idx) => (
                        <div
                            key={idx}
                            className={`progress-dot ${idx === currentIndex ? 'active' : ''} ${idx < currentIndex ? 'completed' : ''}`}
                            onClick={() => setCurrentIndex(idx)}
                        />
                    ))}
                </div>

                {/* Card container with swipe */}
                <div
                    className="badge-card-container"
                    ref={containerRef}
                    onTouchStart={handleTouchStart}
                    onTouchMove={handleTouchMove}
                    onTouchEnd={handleTouchEnd}
                    onMouseDown={handleMouseDown}
                    onMouseMove={handleMouseMove}
                    onMouseUp={handleMouseUp}
                    onMouseLeave={() => {
                        if (isDragging) handleMouseUp();
                    }}
                    style={{
                        transform: `translateX(${touchOffset}px)`,
                        transition: isDragging ? 'none' : 'transform 0.3s ease',
                    }}
                >
                    <div className="badge-card">
                        <div className="badge-image-wrapper">
                            {imageBlobUrls[currentVariant.id] ? (
                                <img
                                    src={imageBlobUrls[currentVariant.id]}
                                    alt={currentVariant.name}
                                    className="badge-image"
                                    draggable={false}
                                />
                            ) : (
                                <div className="loading-container">
                                    <div className="spinner-border text-primary"></div>
                                    <p>Caricamento badge...</p>
                                </div>
                            )}
                        </div>

                        <div className="badge-info">
                            <div className="badge-type-badge">
                                {currentVariant.type === 'card' ? (
                                    <>
                                        <i className="fas fa-id-card me-1"></i>
                                        Badge RDL
                                    </>
                                ) : (
                                    <>
                                        <i className="fas fa-mobile-alt me-1"></i>
                                        Sfondo Lockscreen
                                    </>
                                )}
                            </div>
                            <h3>{currentVariant.name}</h3>
                            <p>{currentVariant.description}</p>
                        </div>
                    </div>
                </div>

                {/* Navigation arrows */}
                <button
                    className="nav-arrow nav-arrow-left"
                    onClick={handlePrevious}
                    disabled={currentIndex === 0}
                >
                    <i className="fas fa-chevron-left"></i>
                </button>
                <button
                    className="nav-arrow nav-arrow-right"
                    onClick={handleNext}
                    disabled={currentIndex === variants.length - 1}
                >
                    <i className="fas fa-chevron-right"></i>
                </button>

                {/* Counter */}
                <div className="badge-counter">
                    {currentIndex + 1} / {variants.length}
                </div>

                {/* Action buttons */}
                <div className="badge-actions">
                    <button
                        className="action-btn btn-download"
                        onClick={handleDownload}
                        disabled={downloading}
                    >
                        <i className="fas fa-download"></i>
                        {downloading ? 'Download...' : 'Scarica'}
                    </button>

                    <button
                        className="action-btn btn-print"
                        onClick={handlePrint}
                    >
                        <i className="fas fa-print"></i>
                        Stampa
                    </button>

                    {currentVariant.type === 'lockscreen' && (
                        <button
                            className="action-btn btn-wallpaper"
                            onClick={handleSetAsWallpaper}
                        >
                            <i className="fas fa-mobile-alt"></i>
                            {/iPhone|iPad|iPod|Android/i.test(navigator.userAgent) ? 'Visualizza a Schermo Intero' : 'Imposta Sfondo'}
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}

export default BadgeGenerator;
