import React, { useState, useEffect, useLayoutEffect, useRef } from 'react';
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
    const [sessionTitle, setSessionTitle] = useState('');
    const [editingMessageId, setEditingMessageId] = useState(null);
    const [editText, setEditText] = useState('');
    const [showSessionsList, setShowSessionsList] = useState(false);
    const [sessions, setSessions] = useState([]);
    const [isLoadingSessions, setIsLoadingSessions] = useState(false);
    const [speakingMessageId, setSpeakingMessageId] = useState(null);
    const [fontSize, setFontSize] = useState(() => {
        const saved = localStorage.getItem('ai_chat_font_size');
        return saved ? parseInt(saved) : 100; // 100 = default (100%)
    });

    const messagesEndRef = useRef(null);
    const messagesContainerRef = useRef(null);
    const recognitionRef = useRef(null);
    const speechSynthesisRef = useRef(null);

    // Scroll to bottom helper
    const scrollToBottom = (behavior = 'auto') => {
        if (messagesContainerRef.current) {
            messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
        }
    };

    // Scroll to bottom when chat is opened
    useEffect(() => {
        if (show && messages.length > 0) {
            // Use timeout to ensure DOM is ready
            setTimeout(() => scrollToBottom(), 100);
        }
    }, [show]);

    // Load saved session on mount
    useEffect(() => {
        const loadSavedSession = async () => {
            if (sessionId && show && messages.length === 0) {
                setIsLoadingHistory(true);
                try {
                    const result = await client.ai.getSession(sessionId);
                    if (result.messages) {
                        console.log('Session loaded:', sessionId, 'messages:', result.messages.length, 'first msg has id:', result.messages[0]?.id);
                        setMessages(result.messages);
                        setSessionTitle(result.title || '');
                        // Scroll to bottom after messages are loaded
                        setTimeout(() => scrollToBottom(), 200);
                    } else if (result.error === 'Session not found') {
                        // Session doesn't exist anymore, clear it
                        localStorage.removeItem('ai_chat_session_id');
                        setSessionId(null);
                        setSessionTitle('');
                    }
                } catch (error) {
                    console.error('Error loading session:', error);
                    // Clear invalid session
                    localStorage.removeItem('ai_chat_session_id');
                    setSessionId(null);
                    setSessionTitle('');
                } finally {
                    setIsLoadingHistory(false);
                }
            }
        };

        loadSavedSession();
    }, [sessionId, show, client]);

    // Auto-scroll to latest message when new messages arrive
    useLayoutEffect(() => {
        if (messages.length > 0 && !isLoadingHistory) {
            // Use requestAnimationFrame to ensure DOM is updated
            requestAnimationFrame(() => scrollToBottom());
        }
    }, [messages, isLoadingHistory]);

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

        // Add user message to UI (optimistic, without ID yet)
        setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
        setIsLoading(true);

        try {
            // Call AI chat API
            const response = await client.ai.chat({
                session_id: sessionId,
                message: userMessage,
            });

            // Save session ID and title for continuity (both in state and localStorage)
            if (!sessionId && response.session_id) {
                setSessionId(response.session_id);
                localStorage.setItem('ai_chat_session_id', response.session_id);
            }

            // Update title if returned (after first message)
            if (response.title && !sessionTitle) {
                setSessionTitle(response.title);
            }

            // Replace optimistic user message with real one (with ID) + add assistant message
            setMessages(prev => {
                // Remove the last message (optimistic user message without ID)
                const messagesWithoutOptimistic = prev.slice(0, -1);
                // Add both user message (with ID) and assistant message
                return [
                    ...messagesWithoutOptimistic,
                    response.user_message,
                    {
                        id: response.message.id,
                        role: 'assistant',
                        content: response.message.content,
                        sources: response.message.sources,
                    }
                ];
            });

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
        setSessionTitle('');
        setInputText('');
        localStorage.removeItem('ai_chat_session_id');
    };

    const handleEditMessage = (messageId, content) => {
        setEditingMessageId(messageId);
        setEditText(content);
    };

    const handleCancelEdit = () => {
        setEditingMessageId(null);
        setEditText('');
    };

    const handleSendEdit = async (messageId) => {
        if (!editText.trim() || isLoading) return;

        setIsLoading(true);
        setEditingMessageId(null);

        try {
            // Create branch with edited message
            const response = await client.ai.branch({
                session_id: sessionId,
                message_id: messageId,
                new_message: editText.trim(),
            });

            if (response.error) {
                throw new Error(response.error);
            }

            // Switch to new branch
            setSessionId(response.session_id);
            setSessionTitle(response.title);
            localStorage.setItem('ai_chat_session_id', response.session_id);

            // Reload messages from new branch
            const result = await client.ai.getSession(response.session_id);
            if (result.messages) {
                console.log('Branch messages loaded:', result.messages.map(m => ({ id: m.id, role: m.role })));
                setMessages(result.messages);
                // Scroll to bottom after branch messages are loaded
                setTimeout(() => scrollToBottom(), 200);
            }

        } catch (error) {
            console.error('Edit error:', error);
            alert('Errore durante la modifica del messaggio. Riprova.');
            setEditingMessageId(messageId);
        } finally {
            setIsLoading(false);
            setEditText('');
        }
    };

    const handleLoadSessions = async () => {
        setIsLoadingSessions(true);
        setShowSessionsList(true);
        try {
            const result = await client.ai.sessions();
            if (Array.isArray(result)) {
                setSessions(result);
            }
        } catch (error) {
            console.error('Failed to load sessions:', error);
        } finally {
            setIsLoadingSessions(false);
        }
    };

    const handleSwitchSession = async (newSessionId) => {
        setIsLoadingHistory(true);
        setShowSessionsList(false);
        try {
            const result = await client.ai.getSession(newSessionId);
            if (result.messages) {
                setMessages(result.messages);
                setSessionId(newSessionId);
                setSessionTitle(result.title || '');
                localStorage.setItem('ai_chat_session_id', newSessionId);
                // Scroll to bottom after switching session
                setTimeout(() => scrollToBottom(), 200);
            }
        } catch (error) {
            console.error('Failed to switch session:', error);
        } finally {
            setIsLoadingHistory(false);
        }
    };

    const handleSpeak = (messageId, text) => {
        // Stop any ongoing speech
        if (window.speechSynthesis.speaking) {
            window.speechSynthesis.cancel();
            if (speakingMessageId === messageId) {
                // Toggle off if clicking the same message
                setSpeakingMessageId(null);
                return;
            }
        }

        // Check if Speech Synthesis is supported
        if (!('speechSynthesis' in window)) {
            alert('Il tuo browser non supporta la sintesi vocale. Usa Chrome, Safari o Edge.');
            return;
        }

        // Create utterance
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'it-IT';
        utterance.rate = 0.9; // Slightly slower for better comprehension
        utterance.pitch = 1.0;

        // Find Italian voice (prefer quality voices)
        const voices = window.speechSynthesis.getVoices();
        const italianVoice = voices.find(voice =>
            voice.lang.startsWith('it') && (voice.name.includes('Google') || voice.name.includes('Microsoft'))
        ) || voices.find(voice => voice.lang.startsWith('it'));

        if (italianVoice) {
            utterance.voice = italianVoice;
        }

        // Event handlers
        utterance.onstart = () => {
            setSpeakingMessageId(messageId);
        };

        utterance.onend = () => {
            setSpeakingMessageId(null);
        };

        utterance.onerror = (event) => {
            console.error('Speech synthesis error:', event);
            setSpeakingMessageId(null);
        };

        // Speak
        speechSynthesisRef.current = utterance;
        window.speechSynthesis.speak(utterance);
    };

    const handleStopSpeaking = () => {
        if (window.speechSynthesis.speaking) {
            window.speechSynthesis.cancel();
            setSpeakingMessageId(null);
        }
    };

    const handleZoomIn = () => {
        const newSize = Math.min(fontSize + 10, 200); // Max 200%
        setFontSize(newSize);
        localStorage.setItem('ai_chat_font_size', newSize);
    };

    const handleZoomOut = () => {
        const newSize = Math.max(fontSize - 10, 70); // Min 70%
        setFontSize(newSize);
        localStorage.setItem('ai_chat_font_size', newSize);
    };

    const handleZoomReset = () => {
        setFontSize(100);
        localStorage.setItem('ai_chat_font_size', 100);
    };

    // Cleanup speech on unmount
    useEffect(() => {
        return () => {
            if (window.speechSynthesis.speaking) {
                window.speechSynthesis.cancel();
            }
        };
    }, []);

    // Load voices on mount (needed for some browsers)
    useEffect(() => {
        if ('speechSynthesis' in window) {
            const loadVoices = () => {
                window.speechSynthesis.getVoices();
            };
            loadVoices();
            if (window.speechSynthesis.onvoiceschanged !== undefined) {
                window.speechSynthesis.onvoiceschanged = loadVoices;
            }
        }
    }, []);

    // Block body scroll when chat is open (mobile)
    useEffect(() => {
        if (show) {
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
        }
    }, [show]);

    if (!show) return null;

    return (
        <div className="chat-overlay" onClick={onClose}>
            <div className="chat-container" onClick={(e) => e.stopPropagation()}>
                {/* Header */}
                <div className="chat-header">
                    <div>
                        <i className="fas fa-robot me-2"></i>
                        <div>
                            <strong>AI RDL</strong>
                            {sessionTitle && <div className="chat-title-subtitle">{sessionTitle}</div>}
                        </div>
                    </div>
                    <div>
                        {/* Zoom controls */}
                        <div className="zoom-controls">
                            <button
                                className="btn-zoom btn-zoom-small"
                                onClick={handleZoomOut}
                                disabled={fontSize <= 70}
                                title="Riduci dimensione testo"
                            >
                                <span className="zoom-icon-small">A</span>
                            </button>
                            <button
                                className="btn-zoom btn-zoom-large"
                                onClick={handleZoomIn}
                                disabled={fontSize >= 200}
                                title="Aumenta dimensione testo"
                            >
                                <span className="zoom-icon-large">A</span>
                            </button>
                        </div>

                        <button
                            className="btn btn-outline-light"
                            onClick={handleLoadSessions}
                            title="Conversazioni precedenti"
                        >
                            <i className="fas fa-history"></i>
                        </button>
                        {messages.length > 0 && (
                            <button
                                className="btn btn-outline-light"
                                onClick={handleNewConversation}
                                title="Nuova conversazione"
                            >
                                <i className="fas fa-plus"></i>
                            </button>
                        )}
                        <button className="btn-close btn-close-white" onClick={onClose}></button>
                    </div>
                </div>

                {/* Messages */}
                <div
                    ref={messagesContainerRef}
                    className="chat-messages"
                    style={{ fontSize: `${(fontSize / 100) * 16}px` }}
                >
                    {isLoadingHistory ? (
                        <div className="chat-welcome">
                            <span className="spinner-border spinner-border-lg mb-3"></span>
                            <p>Caricamento conversazione...</p>
                        </div>
                    ) : messages.length === 0 ? (
                        <div className="chat-welcome">
                            <i className="fas fa-gavel" style={{ fontSize: '2.5rem', color: '#1F4E5F', marginBottom: '12px' }}></i>
                            <h5 style={{ marginBottom: '16px', fontWeight: '600' }}>Assistente AI per Rappresentanti di Lista</h5>
                            <p style={{ marginBottom: '20px', lineHeight: '1.6' }}>
                                Ti aiuto a rispondere a domande operative durante le elezioni e i referendum.
                            </p>
                            <div style={{ textAlign: 'left', maxWidth: '320px', margin: '0 auto' }}>
                                <p className="text-muted" style={{ fontSize: '0.9rem', marginBottom: '8px' }}>
                                    <strong>Cosa posso fare:</strong>
                                </p>
                                <ul className="text-muted" style={{ fontSize: '0.85rem', paddingLeft: '20px', marginBottom: '0' }}>
                                    <li>Spiegare procedure di scrutinio e spoglio</li>
                                    <li>Chiarire diritti e doveri degli RDL</li>
                                    <li>Gestione irregolarità e contestazioni</li>
                                    <li>Interpretare normative elettorali</li>
                                    <li>Fornire moduli e documentazione</li>
                                </ul>
                            </div>
                            <p className="text-muted" style={{ fontSize: '0.85rem', marginTop: '20px', fontStyle: 'italic' }}>
                                💬 Scrivi o usa il microfono per iniziare
                            </p>
                        </div>
                    ) : null}

                    {messages.map((msg, idx) => (
                        <div key={msg.id || `msg-${idx}`} className={`chat-message ${msg.role}`}>
                            <div className="message-bubble">
                                {editingMessageId === msg.id && msg.role === 'user' ? (
                                    /* Edit mode for user message */
                                    <div className="message-edit-container">
                                        <textarea
                                            className="form-control message-edit-textarea"
                                            value={editText}
                                            onChange={(e) => setEditText(e.target.value)}
                                            rows={3}
                                            autoFocus
                                        />
                                        <div className="message-edit-actions">
                                            <button
                                                className="btn btn-sm btn-primary"
                                                onClick={() => handleSendEdit(msg.id)}
                                                disabled={!editText.trim() || isLoading}
                                            >
                                                <i className="fas fa-paper-plane me-1"></i>
                                                Invia modificato
                                            </button>
                                            <button
                                                className="btn btn-sm btn-secondary"
                                                onClick={handleCancelEdit}
                                                disabled={isLoading}
                                            >
                                                <i className="fas fa-times me-1"></i>
                                                Annulla
                                            </button>
                                        </div>
                                    </div>
                                ) : (
                                    /* Normal message display */
                                    <>
                                        <div className="message-content">
                                            <ReactMarkdown>{msg.content}</ReactMarkdown>
                                        </div>
                                        {msg.sources && msg.sources.length > 0 && (
                                            <div className="message-sources">
                                                <div className="mb-2">
                                                    <small className="text-muted">
                                                        <i className="fas fa-book me-1"></i>
                                                        <strong>Fonti:</strong>
                                                    </small>
                                                </div>
                                                {msg.sources.map((source, sidx) => (
                                                    <div key={sidx} className="source-item">
                                                        <small className="text-muted">
                                                            {source.title}
                                                            {source.url && (
                                                                <a
                                                                    href={source.url}
                                                                    target="_blank"
                                                                    rel="noopener noreferrer"
                                                                    className="ms-2 source-link"
                                                                    title="Apri documento"
                                                                >
                                                                    <i className="fas fa-external-link-alt me-1"></i>
                                                                    Apri PDF
                                                                </a>
                                                            )}
                                                        </small>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                        {/* Actions row */}
                                        {msg.id && !isLoading && (
                                            <div className="message-actions">
                                                {msg.role === 'assistant' && (
                                                    <button
                                                        className={`btn-speak ${speakingMessageId === msg.id ? 'speaking' : ''}`}
                                                        onClick={() => handleSpeak(msg.id, msg.content)}
                                                        title={speakingMessageId === msg.id ? "Interrompi lettura" : "Leggi ad alta voce"}
                                                    >
                                                        <i className={`fas ${speakingMessageId === msg.id ? 'fa-stop-circle' : 'fa-volume-up'} me-2`}></i>
                                                        {speakingMessageId === msg.id ? 'Interrompi' : 'Leggi ad alta voce'}
                                                    </button>
                                                )}
                                                {msg.role === 'user' && (
                                                    <button
                                                        className="btn-message-action"
                                                        onClick={() => handleEditMessage(msg.id, msg.content)}
                                                        title="Modifica messaggio"
                                                    >
                                                        <i className="fas fa-edit me-1"></i>
                                                        Modifica
                                                    </button>
                                                )}
                                            </div>
                                        )}
                                    </>
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

                {/* Sessions List Modal */}
                {showSessionsList && (
                    <div className="sessions-overlay" onClick={() => setShowSessionsList(false)}>
                        <div className="sessions-panel" onClick={(e) => e.stopPropagation()}>
                            <div className="sessions-header">
                                <h5>
                                    <i className="fas fa-history me-2"></i>
                                    Conversazioni
                                </h5>
                                <button className="btn-close" onClick={() => setShowSessionsList(false)}></button>
                            </div>
                            <div className="sessions-list">
                                {isLoadingSessions ? (
                                    <div className="text-center p-4">
                                        <span className="spinner-border spinner-border-sm"></span>
                                        <p className="mt-2 mb-0">Caricamento...</p>
                                    </div>
                                ) : sessions.length === 0 ? (
                                    <div className="text-center p-4 text-muted">
                                        <i className="fas fa-comments mb-2" style={{ fontSize: '2rem' }}></i>
                                        <p>Nessuna conversazione salvata</p>
                                    </div>
                                ) : (
                                    sessions.map((session) => (
                                        <div
                                            key={session.id}
                                            className={`session-item ${session.id === sessionId ? 'active' : ''}`}
                                            onClick={() => handleSwitchSession(session.id)}
                                        >
                                            <div className="session-title">
                                                <i className="fas fa-comment me-2"></i>
                                                {session.title}
                                            </div>
                                            <div className="session-meta">
                                                <small className="text-muted">
                                                    {session.message_count} {session.message_count === 1 ? 'messaggio' : 'messaggi'}
                                                    {' · '}
                                                    {new Date(session.updated_at).toLocaleDateString('it-IT', {
                                                        day: 'numeric',
                                                        month: 'short',
                                                        year: 'numeric'
                                                    })}
                                                </small>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

export default ChatInterface;
