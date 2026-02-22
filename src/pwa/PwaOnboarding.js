import React, { useState, useEffect } from 'react';
import { requestPushToken } from '../firebase';

/**
 * Detect if running in standalone (installed) mode
 */
function isStandalone() {
    return (
        window.matchMedia('(display-mode: standalone)').matches ||
        window.navigator.standalone === true
    );
}

/**
 * Detect iOS
 */
function isIOS() {
    return /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
}

/**
 * Detect Android
 */
function isAndroid() {
    return /Android/.test(navigator.userAgent);
}

/**
 * Check if push notifications are supported
 */
function isPushSupported() {
    return 'Notification' in window && 'serviceWorker' in navigator;
}

/**
 * PWA Onboarding Wizard
 *
 * Step 1: Guide user to install PWA (add to home screen)
 * Step 2: Request notification permission and register FCM token
 *
 * Props:
 * - onComplete: callback when wizard finishes (token registered or skipped)
 * - client: API client for device token registration
 */
export default function PwaOnboarding({ onComplete, client }) {
    const [step, setStep] = useState(() => {
        if (isStandalone()) return 2; // Already installed, go to notifications
        return 1;
    });
    const [pushStatus, setPushStatus] = useState('idle'); // idle | requesting | granted | denied | error
    const [dismissed, setDismissed] = useState(false);

    // Check if already completed
    useEffect(() => {
        const done = localStorage.getItem('pwa_onboarding_done');
        if (done === 'true') {
            setDismissed(true);
        }
    }, []);

    const handleInstallDone = () => {
        // User says they installed, move to step 2
        setStep(2);
    };

    const handleSkipInstall = () => {
        // Skip install, still show notification prompt if supported
        if (isPushSupported()) {
            setStep(2);
        } else {
            handleDismiss();
        }
    };

    const handleEnableNotifications = async () => {
        setPushStatus('requesting');

        try {
            // Check if browser permission is already denied
            if (Notification.permission === 'denied') {
                setPushStatus('denied');
                return;
            }

            const token = await requestPushToken();

            if (token) {
                setPushStatus('granted');
                // Register token on backend
                if (client) {
                    try {
                        await client.me.registerDeviceToken(token, 'WEB');
                    } catch (err) {
                        console.error('Failed to register device token:', err);
                    }
                }
                // Auto-dismiss after success
                setTimeout(() => handleDismiss(), 2000);
            } else {
                // Token is null: could be config issue or permission denied
                if (Notification.permission === 'denied') {
                    setPushStatus('denied');
                } else {
                    // Firebase not configured or other setup issue
                    setPushStatus('not_configured');
                }
            }
        } catch (err) {
            console.error('Push notification error:', err);
            setPushStatus('error');
        }
    };

    const handleDismiss = () => {
        localStorage.setItem('pwa_onboarding_done', 'true');
        setDismissed(true);
        if (onComplete) onComplete();
    };

    if (dismissed) return null;

    // Don't show if push not supported at all
    if (!isPushSupported() && isStandalone()) return null;

    return (
        <div className="card mb-3 border-primary">
            <div className="card-body">
                {step === 1 && (
                    <div>
                        <h5 className="card-title">
                            <i className="fas fa-mobile-alt me-2"></i>
                            Installa l'app
                        </h5>
                        <p className="card-text">
                            Aggiungi AInaudi alla schermata Home per un accesso rapido
                            e ricevere notifiche importanti.
                        </p>

                        {isIOS() ? (
                            <div className="alert alert-light border">
                                <ol className="mb-0">
                                    <li>
                                        Tocca il pulsante <strong>Condividi</strong>{' '}
                                        <i className="fas fa-share-square"></i> in basso
                                    </li>
                                    <li>
                                        Scorri e tocca <strong>"Aggiungi a Home"</strong>{' '}
                                        <i className="fas fa-plus-square"></i>
                                    </li>
                                    <li>Tocca <strong>"Aggiungi"</strong> in alto a destra</li>
                                </ol>
                            </div>
                        ) : isAndroid() ? (
                            <div className="alert alert-light border">
                                <ol className="mb-0">
                                    <li>
                                        Tocca il menu <i className="fas fa-ellipsis-v"></i> in alto a destra
                                    </li>
                                    <li>
                                        Tocca <strong>"Installa app"</strong> o <strong>"Aggiungi a Home"</strong>
                                    </li>
                                    <li>Conferma l'installazione</li>
                                </ol>
                            </div>
                        ) : (
                            <div className="alert alert-light border">
                                <p className="mb-0">
                                    Cerca l'icona di installazione{' '}
                                    <i className="fas fa-download"></i>{' '}
                                    nella barra degli indirizzi del browser.
                                </p>
                            </div>
                        )}

                        <div className="d-flex gap-2 mt-3">
                            <button className="btn btn-primary" onClick={handleInstallDone}>
                                <i className="fas fa-check me-1"></i>
                                Ho installato
                            </button>
                            <button className="btn btn-outline-secondary" onClick={handleSkipInstall}>
                                Salta
                            </button>
                        </div>
                    </div>
                )}

                {step === 2 && (
                    <div>
                        <h5 className="card-title">
                            <i className="fas fa-bell me-2"></i>
                            Attiva le notifiche
                        </h5>
                        <p className="card-text">
                            Ricevi promemoria per i tuoi incarichi elettorali,
                            corsi di formazione e aggiornamenti importanti.
                        </p>

                        {pushStatus === 'idle' && (
                            <div className="d-flex gap-2">
                                <button className="btn btn-primary" onClick={handleEnableNotifications}>
                                    <i className="fas fa-bell me-1"></i>
                                    Attiva notifiche
                                </button>
                                <button className="btn btn-outline-secondary" onClick={handleDismiss}>
                                    Salta per ora
                                </button>
                            </div>
                        )}

                        {pushStatus === 'requesting' && (
                            <div className="d-flex align-items-center">
                                <div className="spinner-border spinner-border-sm me-2" role="status">
                                    <span className="visually-hidden">Caricamento...</span>
                                </div>
                                <span>Richiesta permesso...</span>
                            </div>
                        )}

                        {pushStatus === 'granted' && (
                            <div className="alert alert-success mb-0">
                                <i className="fas fa-check-circle me-2"></i>
                                Notifiche attivate con successo!
                            </div>
                        )}

                        {pushStatus === 'denied' && (
                            <div>
                                <div className="alert alert-warning">
                                    <i className="fas fa-exclamation-triangle me-2"></i>
                                    Permesso negato. Puoi attivare le notifiche in seguito
                                    dalle impostazioni del browser.
                                </div>
                                <button className="btn btn-outline-secondary" onClick={handleDismiss}>
                                    Chiudi
                                </button>
                            </div>
                        )}

                        {pushStatus === 'not_configured' && (
                            <div>
                                <div className="alert alert-info">
                                    <i className="fas fa-info-circle me-2"></i>
                                    Le notifiche push non sono ancora disponibili.
                                    Verranno attivate a breve.
                                </div>
                                <button className="btn btn-outline-secondary" onClick={handleDismiss}>
                                    Chiudi
                                </button>
                            </div>
                        )}

                        {pushStatus === 'error' && (
                            <div>
                                <div className="alert alert-danger">
                                    <i className="fas fa-times-circle me-2"></i>
                                    Errore nell'attivazione delle notifiche.
                                </div>
                                <button className="btn btn-outline-secondary" onClick={handleDismiss}>
                                    Chiudi
                                </button>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
