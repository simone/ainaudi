import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import './ChatInterface.css';

function ChatInterface({ client, show, onClose }) {
    const [messages, setMessages] = useState([]);
    const [inputText, setInputText] = useState('');
    const [isRecording, setIsRecording] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [sessionId, setSessionId] = useState(null);

    const messagesEndRef = useRef(null);
    const recognitionRef = useRef(null);

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
            recognitionRef.current.continuous = false;
            recognitionRef.current.interimResults = false;

            recognitionRef.current.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                setInputText(transcript);
                setIsRecording(false);
            };

            recognitionRef.current.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                setIsRecording(false);
            };

            recognitionRef.current.onend = () => {
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

            // Save session ID for continuity
            if (!sessionId) {
                setSessionId(response.session_id);
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
                    <button className="btn-close btn-close-white" onClick={onClose}></button>
                </div>

                {/* Messages */}
                <div className="chat-messages">
                    {messages.length === 0 && (
                        <div className="chat-welcome">
                            <i className="fas fa-comments" style={{ fontSize: '3rem', color: '#1F4E5F' }}></i>
                            <p>Ciao! Sono l'assistente AI per RDL.</p>
                            <p className="text-muted">Chiedimi qualsiasi cosa su procedure, scrutinio, normative...</p>
                        </div>
                    )}

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
                        title="Registra messaggio vocale"
                    >
                        <i className={`fas ${isRecording ? 'fa-stop' : 'fa-microphone'}`}></i>
                    </button>

                    <input
                        type="text"
                        className="form-control chat-input"
                        placeholder="Scrivi o usa il microfono..."
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
