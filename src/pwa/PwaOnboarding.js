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
const ICON_VERSION = 2; // Bump this when icons change

/**
 * One-time banner for iOS standalone users to reinstall for new icon.
 * Android/Chrome updates icons automatically via manifest.
 */
function PwaIconUpdateBanner() {
    const [visible, setVisible] = useState(false);

    useEffect(() => {
        const key = `pwa_icon_v${ICON_VERSION}_dismissed`;
        const alreadySeen = localStorage.getItem(key) === 'true';
        // Show for standalone users who need to reinstall.
        // Android/Chrome updates icons automatically, but iOS and desktop need manual action.
        if (!alreadySeen && isStandalone() && !isAndroid()) {
            setVisible(true);
        }
    }, []);

    const dismiss = () => {
        localStorage.setItem(`pwa_icon_v${ICON_VERSION}_dismissed`, 'true');
        setVisible(false);
    };

    if (!visible) return null;

    return (
        <div className="alert alert-info alert-dismissible fade show mb-3" role="alert">
            <strong><i className="fas fa-paint-brush me-2"></i>Nuovo look!</strong>
            <p className="mb-2 mt-1">
                Abbiamo aggiornato il logo di AInaudi.
                Per vedere la nuova icona:
            </p>
            {isIOS() ? (
                <ol className="mb-2" style={{ paddingLeft: '1.2rem' }}>
                    <li>Tieni premuto sull'icona di AInaudi nella Home</li>
                    <li>Tocca <strong>"Rimuovi app"</strong> &rarr; <strong>"Rimuovi dalla schermata Home"</strong></li>
                    <li>Riapri questa pagina in Safari</li>
                    <li>Tocca <i className="fas fa-share-square"></i> &rarr; <strong>"Aggiungi a Home"</strong></li>
                </ol>
            ) : (
                <ol className="mb-2" style={{ paddingLeft: '1.2rem' }}>
                    <li>Apri il menu dell'app (tre puntini in alto a destra)</li>
                    <li>Seleziona <strong>"Disinstalla AInaudi"</strong></li>
                    <li>Riapri <strong>{window.location.origin}</strong> nel browser</li>
                    <li>Reinstalla l'app dal menu del browser</li>
                </ol>
            )}
            <button type="button" className="btn-close" aria-label="Chiudi" onClick={dismiss}></button>
        </div>
    );
}

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
            // Check if Notification API is available
            if (typeof Notification === 'undefined') {
                setPushStatus('not_configured');
                return;
            }

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
                if (typeof Notification !== 'undefined' && Notification.permission === 'denied') {
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
        <>
        <PwaIconUpdateBanner />
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
        </>
    );
}
