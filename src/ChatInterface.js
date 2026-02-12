import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import './ChatInterface.css';

function ChatInterface({ client, show, onClose }) {
    const [messages, setMessages] = useState([]);
    const [inputText, setInputText] = useState('');
    const [isRecording, setIsRecording] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [sessionId, setSessionId] = useState(() => {
        // Recupera sessionId salvato in localStorage
        const saved = localStorage.getItem('ai_chat_session_id');
        return saved ? parseInt(saved) : null;
    });
    const [isLoadingHistory, setIsLoadingHistory] = useState(false);

    const messagesEndRef = useRef(null);
    const recognitionRef = useRef(null);

    // Load saved session on mount
    useEffect(() => {
        const loadSavedSession = async () => {
            if (sessionId && show && messages.length === 0) {
                setIsLoadingHistory(true);
                try {
                    const result = await client.ai.getSession(sessionId);
                    if (result.messages) {
                        setMessages(result.messages);
                    } else if (result.error === 'Session not found') {
                        // Session doesn't exist anymore, clear it
                        localStorage.removeItem('ai_chat_session_id');
                        setSessionId(null);
                    }
                } catch (error) {
                    console.error('Error loading session:', error);
                    // Clear invalid session
                    localStorage.removeItem('ai_chat_session_id');
                    setSessionId(null);
                } finally {
                    setIsLoadingHistory(false);
                }
            }
        };

        loadSavedSession();
    }, [sessionId, show, client]);

    // Auto-scroll to latest message
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Initialize Web Speech API
    useEffect(() => {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognitionRef.current = new SpeechRecognition();
            recognitionRef.current.lang = 'it-IT';
            recognitionRef.current.continuous = true;  // Continua ad ascoltare
            recognitionRef.current.interimResults = true;  // Mostra risultati parziali

            recognitionRef.current.onresult = (event) => {
                // Accumula tutti i risultati finali
                let transcript = '';

                for (let i = 0; i < event.results.length; i++) {
                    transcript += event.results[i][0].transcript;
                    if (i < event.results.length - 1) {
                        transcript += ' ';
                    }
                }

                // Aggiorna il campo di testo con tutto il trascritto
                setInputText(transcript.trim());
            };

            recognitionRef.current.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                // Non fermare per 'no-speech', può essere una pausa naturale
                if (event.error !== 'no-speech' && event.error !== 'aborted') {
                    setIsRecording(false);
                }
            };

            recognitionRef.current.onend = () => {
                // Solo se non stiamo registrando (stop manuale)
                setIsRecording(false);
            };
        }
    }, []);

    // Keyboard ESC handler
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === 'Escape' && show) {
                onClose();
            }
        };
        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [show, onClose]);

    const handleMicrophoneClick = () => {
        if (!recognitionRef.current) {
            alert('Il tuo browser non supporta il riconoscimento vocale. Usa Chrome o Edge.');
            return;
        }

        if (isRecording) {
            recognitionRef.current.stop();
        } else {
            recognitionRef.current.start();
            setIsRecording(true);
        }
    };

    const handleSendMessage = async () => {
        if (!inputText.trim() || isLoading) return;

        const userMessage = inputText.trim();
        setInputText('');

        // Add user message to UI
        setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
        setIsLoading(true);

        try {
            // Call AI chat API
            const response = await client.ai.chat({
                session_id: sessionId,
                message: userMessage,
            });

            // Save session ID for continuity (both in state and localStorage)
            if (!sessionId && response.session_id) {
                setSessionId(response.session_id);
                localStorage.setItem('ai_chat_session_id', response.session_id);
            }

            // Add assistant message to UI
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: response.message.content,
                sources: response.message.sources,
            }]);

        } catch (error) {
            console.error('Chat error:', error);
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: 'Mi dispiace, si è verificato un errore. Riprova.',
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    const handleNewConversation = () => {
        // Clear current conversation
        setMessages([]);
        setSessionId(null);
        setInputText('');
        localStorage.removeItem('ai_chat_session_id');
    };

    if (!show) return null;

    return (
        <div className="chat-overlay" onClick={onClose}>
            <div className="chat-container" onClick={(e) => e.stopPropagation()}>
                {/* Header */}
                <div className="chat-header">
                    <div>
                        <i className="fas fa-robot me-2"></i>
                        <strong>Assistente AI</strong>
                    </div>
                    <div className="d-flex align-items-center gap-2">
                        {messages.length > 0 && (
                            <button
                                className="btn btn-sm btn-outline-light"
                                onClick={handleNewConversation}
                                title="Inizia una nuova conversazione"
                            >
                                <i className="fas fa-plus"></i>
                            </button>
                        )}
                        <button className="btn-close btn-close-white" onClick={onClose}></button>
                    </div>
                </div>

                {/* Messages */}
                <div className="chat-messages">
                    {isLoadingHistory ? (
                        <div className="chat-welcome">
                            <span className="spinner-border spinner-border-lg mb-3"></span>
                            <p>Caricamento conversazione...</p>
                        </div>
                    ) : messages.length === 0 ? (
                        <div className="chat-welcome">
                            <i className="fas fa-comments" style={{ fontSize: '3rem', color: '#1F4E5F' }}></i>
                            <p>Ciao! Sono l'assistente AI per RDL.</p>
                            <p className="text-muted">Chiedimi qualsiasi cosa su procedure, scrutinio, normative...</p>
                        </div>
                    ) : null}

                    {messages.map((msg, idx) => (
                        <div key={idx} className={`chat-message ${msg.role}`}>
                            <div className="message-bubble">
                                <div className="message-content">
                                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                                </div>
                                {msg.sources && msg.sources.length > 0 && (
                                    <div className="message-sources">
                                        <small className="text-muted">
                                            <i className="fas fa-book me-1"></i>
                                            Fonti: {msg.sources.map(s => s.title).join(', ')}
                                        </small>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}

                    {isLoading && (
                        <div className="chat-message assistant">
                            <div className="message-bubble">
                                <span className="spinner-border spinner-border-sm me-2"></span>
                                Sto pensando...
                            </div>
                        </div>
                    )}

                    <div ref={messagesEndRef} />
                </div>

                {/* Input */}
                <div className="chat-input-container">
                    <button
                        className={`btn btn-microphone ${isRecording ? 'recording' : ''}`}
                        onClick={handleMicrophoneClick}
                        disabled={isLoading}
                        title={isRecording ? 'Clicca per fermare' : 'Clicca e parla (clicca di nuovo per fermare)'}
                    >
                        <i className={`fas ${isRecording ? 'fa-stop' : 'fa-microphone'}`}></i>
                    </button>

                    <input
                        type="text"
                        className="form-control chat-input"
                        placeholder={isRecording ? 'Sto ascoltando... (clicca STOP per fermare)' : 'Scrivi o usa il microfono...'}
                        value={inputText}
                        onChange={(e) => setInputText(e.target.value)}
                        onKeyPress={handleKeyPress}
                        disabled={isLoading}
                    />

                    <button
                        className="btn btn-primary btn-send"
                        onClick={handleSendMessage}
                        disabled={!inputText.trim() || isLoading}
                    >
                        <i className="fas fa-paper-plane"></i>
                    </button>
                </div>
            </div>
        </div>
    );
}

export default ChatInterface;
