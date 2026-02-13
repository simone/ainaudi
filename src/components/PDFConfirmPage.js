import React, { useEffect, useState } from 'react';
import './PDFConfirmPage.css';

function PDFConfirmPage({ serverApi }) {
    const [loading, setLoading] = useState(true);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        // Get token from URL query params
        const urlParams = new URLSearchParams(window.location.search);
        const token = urlParams.get('token');

        if (!token) {
            setError('Token mancante nell\'URL');
            setLoading(false);
            return;
        }

        // Call confirmation endpoint
        const apiUrl = serverApi || '';  // Use Vite proxy in dev, same-origin in prod
        fetch(`${apiUrl}/api/documents/confirm/?token=${token}`)
            .then(res => {
                if (!res.ok) {
                    return res.json().then(data => {
                        throw new Error(data.error || `HTTP ${res.status}`);
                    });
                }
                return res.json();
            })
            .then(data => {
                setResult(data);
            })
            .catch(err => {
                setError(err.message);
            })
            .finally(() => {
                setLoading(false);
            });
    }, [serverApi]);

    if (loading) {
        return (
            <div className="pdf-confirm-container">
                <div className="loading-spinner">
                    <div className="spinner"></div>
                    <p>Conferma in corso...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="pdf-confirm-container">
                <div className="alert alert-danger">
                    <h2>❌ Errore Conferma</h2>
                    <p className="error-message">{error}</p>
                    <div className="error-details">
                        {error.includes('expired') && (
                            <p>Il link di conferma è scaduto. Richiedi un nuovo documento preview.</p>
                        )}
                        {error.includes('Invalid') && (
                            <p>Il link non è valido. Controlla di aver copiato l'URL completo dall'email.</p>
                        )}
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="pdf-confirm-container">
            <div className="alert alert-success">
                <h2>✓ Documento Confermato!</h2>
                <p className="success-message">{result.message}</p>

                <div className="document-details">
                    <p><strong>ID Documento:</strong> {result.document_id}</p>
                    <p><strong>Stato:</strong> <span className="badge badge-success">{result.status}</span></p>
                    {result.confirmed_at && (
                        <p><strong>Confermato il:</strong> {new Date(result.confirmed_at).toLocaleString('it-IT')}</p>
                    )}
                </div>

                {result.pdf_url && (
                    <div className="download-section">
                        <a href={result.pdf_url} className="btn btn-primary" download>
                            📥 Scarica PDF Finale
                        </a>
                    </div>
                )}

                <div className="info-box">
                    <strong>ℹ️ Importante:</strong>
                    <p>Il documento è ora immutabile e non può essere modificato. Conserva questo PDF per i tuoi archivi.</p>
                </div>
            </div>
        </div>
    );
}

export default PDFConfirmPage;
