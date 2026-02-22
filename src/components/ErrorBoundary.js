import React from 'react';

/**
 * Report error to backend → Cloud Logging → Error Reporting.
 * Fire-and-forget: never blocks the UI.
 */
function reportError(error, errorInfo) {
    try {
        fetch('/api/client-errors/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: error ? error.toString() : 'Unknown error',
                stack: error && error.stack ? error.stack : '',
                componentStack: errorInfo && errorInfo.componentStack ? errorInfo.componentStack : '',
                url: window.location.href,
            }),
        }).catch(function() {
            // Ignore network errors - we're already in error state
        });
    } catch (e) {
        // Never crash the error handler
    }
}

/**
 * Catch unhandled promise rejections and global errors too.
 * Called once on module load.
 */
if (typeof window !== 'undefined') {
    window.addEventListener('error', function(event) {
        reportError(event.error || new Error(event.message), null);
    });
    window.addEventListener('unhandledrejection', function(event) {
        reportError(event.reason || new Error('Unhandled promise rejection'), null);
    });
}

/**
 * React Error Boundary - catches rendering errors and shows them
 * instead of white screen. Also reports to backend for Cloud Error Reporting.
 */
export default class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error: error };
    }

    componentDidCatch(error, errorInfo) {
        this.setState({ errorInfo: errorInfo });
        console.error('ErrorBoundary caught:', error, errorInfo);
        // Report to backend
        reportError(error, errorInfo);
    }

    render() {
        if (this.state.hasError) {
            var error = this.state.error;
            var errorInfo = this.state.errorInfo;
            var errorMessage = error ? error.toString() : 'Errore sconosciuto';
            var componentStack = errorInfo ? errorInfo.componentStack : '';

            return (
                <div style={{
                    padding: '20px',
                    margin: '20px',
                    fontFamily: '-apple-system, BlinkMacSystemFont, sans-serif',
                }}>
                    <div style={{
                        background: '#fff3cd',
                        border: '1px solid #ffc107',
                        borderRadius: '8px',
                        padding: '20px',
                        marginBottom: '16px',
                    }}>
                        <h3 style={{ color: '#856404', margin: '0 0 12px 0' }}>
                            Si e' verificato un errore
                        </h3>
                        <p style={{ color: '#856404', margin: '0 0 12px 0' }}>
                            L'app ha riscontrato un problema.
                            L'errore e' stato segnalato automaticamente.
                        </p>
                        <button
                            onClick={function() { window.location.reload(); }}
                            style={{
                                background: '#ffc107',
                                color: '#856404',
                                border: 'none',
                                padding: '10px 20px',
                                borderRadius: '6px',
                                fontWeight: 'bold',
                                cursor: 'pointer',
                            }}
                        >
                            Ricarica pagina
                        </button>
                    </div>

                    <details style={{
                        background: '#f8f9fa',
                        border: '1px solid #dee2e6',
                        borderRadius: '8px',
                        padding: '16px',
                    }}>
                        <summary style={{ cursor: 'pointer', fontWeight: 'bold', color: '#333' }}>
                            Dettagli errore
                        </summary>
                        <pre style={{
                            marginTop: '12px',
                            padding: '12px',
                            background: '#1a1a2e',
                            color: '#e94560',
                            borderRadius: '6px',
                            overflow: 'auto',
                            fontSize: '12px',
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-word',
                        }}>
                            {errorMessage}
                            {'\n\n'}
                            {componentStack}
                        </pre>
                    </details>
                </div>
            );
        }

        return this.props.children;
    }
}
