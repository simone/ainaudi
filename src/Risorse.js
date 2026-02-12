import React, { useState, useEffect } from 'react';
import PDFViewer from './PDFViewer';
import ReactMarkdown from 'react-markdown';
import MarkdownModal from './MarkdownModal';

/**
 * Pagina Risorse: Documenti e FAQ
 * I contenuti sono filtrati in base alla consultazione attiva e al suo tipo (referendum, comunali, etc.)
 */

// CSS per le card documenti e FAQ markdown
const docCardStyles = `
    /* Markdown FAQ styling */
    .faq-risposta {
        color: #333;
        line-height: 1.6;
    }
    .faq-risposta p {
        margin-bottom: 0.75rem;
    }
    .faq-risposta strong {
        color: #1a1a1a;
        font-weight: 600;
    }
    .faq-risposta ul,
    .faq-risposta ol {
        margin: 0.5rem 0;
        padding-left: 1.5rem;
    }
    .faq-risposta li {
        margin-bottom: 0.5rem;
    }
    .faq-risposta h1,
    .faq-risposta h2,
    .faq-risposta h3,
    .faq-risposta h4 {
        margin-top: 1rem;
        margin-bottom: 0.5rem;
        color: #1a1a1a;
        font-weight: 600;
    }
    .faq-risposta h1 { font-size: 1.5rem; }
    .faq-risposta h2 { font-size: 1.3rem; }
    .faq-risposta h3 { font-size: 1.15rem; }
    .faq-risposta h4 { font-size: 1rem; }
    .faq-risposta code {
        background: #f5f5f5;
        padding: 0.2rem 0.4rem;
        border-radius: 3px;
        font-size: 0.9em;
    }
    .faq-risposta pre {
        background: #f5f5f5;
        padding: 1rem;
        border-radius: 4px;
        overflow-x: auto;
    }
    .faq-risposta blockquote {
        border-left: 4px solid #ddd;
        padding-left: 1rem;
        margin: 1rem 0;
        color: #666;
    }

    /* Document cards */
    .doc-card {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 14px 12px;
        text-decoration: none;
        color: inherit;
        border-bottom: 1px solid #f0f0f0;
        transition: background 0.15s ease;
        cursor: pointer;
    }
    .doc-card:last-child {
        border-bottom: none;
    }
    .doc-card:hover {
        background: #f8f9fa;
    }
    .doc-card:active {
        background: #e9ecef;
    }
    .doc-card-icon {
        width: 46px;
        height: 46px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }
    .doc-card-content {
        flex: 1;
        min-width: 0;
    }
    .doc-card-title {
        font-weight: 600;
        font-size: 0.95rem;
        color: #1a1a1a;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .doc-card-desc {
        margin: 0;
        font-size: 0.8rem;
        color: #666;
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        line-height: 1.4;
    }
    .doc-card-arrow {
        color: #ccc;
        font-size: 0.85rem;
        flex-shrink: 0;
    }
    .doc-card-star {
        color: #ffc107;
        font-size: 0.7rem;
        margin-right: 4px;
    }
`;

function Risorse({ client, consultazione, setError }) {
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('documenti'); // 'documenti' | 'faq'
    const [data, setData] = useState({ documenti: null, faqs: null });
    const [pdfViewer, setPdfViewer] = useState(null); // { url, titolo } quando aperto
    const [showManuale, setShowManuale] = useState(false); // Manuale utente RDL

    // RDL designations state
    const [mieDesignazioni, setMieDesignazioni] = useState(null);
    const [loadingNomina, setLoadingNomina] = useState(false);

    // FAQ state
    const [expandedFaq, setExpandedFaq] = useState(null);
    const [searchFaq, setSearchFaq] = useState('');
    const [votedFaqs, setVotedFaqs] = useState(() => {
        const saved = localStorage.getItem('votedFaqs');
        return saved ? JSON.parse(saved) : {};
    });

    useEffect(() => {
        loadRisorse();
    }, [consultazione]);

    const loadRisorse = async () => {
        setLoading(true);
        try {
            // Load risorse (documenti + FAQ)
            const result = await client.risorse.list(consultazione?.id);
            if (result?.error) {
                // API non disponibile, mostra dati mock
                setData(getMockData());
            } else {
                setData(result);
            }

            // Load RDL's own designations (if any)
            if (consultazione?.id) {
                try {
                    const designazioni = await client.deleghe.processi.mieDesignazioni(consultazione.id);
                    if (designazioni?.has_designazioni) {
                        setMieDesignazioni(designazioni);
                    } else {
                        setMieDesignazioni(null);
                    }
                } catch (err) {
                    console.log('Non è possibile caricare le designazioni:', err);
                    setMieDesignazioni(null);
                }
            }
        } catch (err) {
            console.log('API risorse non disponibile, uso dati mock');
            setData(getMockData());
        }
        setLoading(false);
    };

    const getMockData = () => ({
        documenti: {
            categorie: [
                {
                    id: 1,
                    nome: 'Modulistica',
                    icona: 'fa-file-alt',
                    documenti: [
                        { id: 1, titolo: 'Modulo designazione RDL', tipo_file: 'PDF', dimensione_formattata: '245 KB', in_evidenza: true },
                        { id: 2, titolo: 'Modulo sub-delega', tipo_file: 'PDF', dimensione_formattata: '180 KB', in_evidenza: false },
                    ]
                },
                {
                    id: 2,
                    nome: 'Guide Operative',
                    icona: 'fa-book',
                    documenti: [
                        { id: 3, titolo: 'Guida completa RDL', tipo_file: 'PDF', dimensione_formattata: '2.1 MB', in_evidenza: true },
                        { id: 4, titolo: 'Slide formazione', tipo_file: 'PowerPoint', dimensione_formattata: '5.4 MB', in_evidenza: false },
                    ]
                },
                {
                    id: 3,
                    nome: 'Normativa',
                    icona: 'fa-gavel',
                    documenti: [
                        { id: 5, titolo: 'DPR 361/1957 - Rappresentanti di Lista', tipo_file: 'PDF', dimensione_formattata: '890 KB', in_evidenza: false },
                    ]
                }
            ],
            totale: 5
        },
        faqs: {
            categorie: [
                {
                    id: 1,
                    nome: 'Operazioni di voto',
                    icona: 'fa-vote-yea',
                    faqs: [
                        { id: 1, domanda: 'Cosa devo fare quando arrivo al seggio?', risposta: 'Presentati al presidente di seggio con il documento di designazione e un documento di identità. Verifica che il tuo nome sia nell\'elenco dei rappresentanti di lista.', in_evidenza: true, visualizzazioni: 234 },
                        { id: 2, domanda: 'Posso allontanarmi dal seggio durante le votazioni?', risposta: 'Sì, puoi allontanarti brevemente, ma è importante essere presenti durante le operazioni di scrutinio. Avvisa sempre il presidente prima di allontanarti.', in_evidenza: false, visualizzazioni: 156 },
                    ]
                },
                {
                    id: 2,
                    nome: 'Scrutinio',
                    icona: 'fa-calculator',
                    faqs: [
                        { id: 3, domanda: 'Come si contano i voti?', risposta: 'Le schede vengono estratte una alla volta dall\'urna. Per ogni scheda, il presidente legge ad alta voce il voto espresso e uno scrutatore lo annota nel registro.', in_evidenza: true, visualizzazioni: 312 },
                        { id: 4, domanda: 'Cosa faccio se noto un\'irregolarità?', risposta: 'Segnala immediatamente l\'irregolarità al presidente di seggio. Se non viene risolta, hai diritto di far verbalizzare la tua osservazione nel verbale delle operazioni.', in_evidenza: false, visualizzazioni: 198 },
                    ]
                },
                {
                    id: 3,
                    nome: 'App e Tecnologia',
                    icona: 'fa-mobile-alt',
                    faqs: [
                        { id: 5, domanda: 'Come inserisco i dati nell\'app?', risposta: 'Dalla sezione "Scrutinio", seleziona la tua sezione e compila i campi richiesti. I dati vengono salvati automaticamente e puoi modificarli fino alla chiusura dello scrutinio.', in_evidenza: false, visualizzazioni: 87 },
                    ]
                }
            ],
            totale: 5
        }
    });

    const handleVoteFaq = async (faqId, utile) => {
        if (votedFaqs[faqId]) return; // Già votato

        try {
            await client.risorse.faqs.vota(faqId, utile);
        } catch (err) {
            // Ignora errori API, salva comunque il voto locale
        }

        const newVotedFaqs = { ...votedFaqs, [faqId]: utile ? 'si' : 'no' };
        setVotedFaqs(newVotedFaqs);
        localStorage.setItem('votedFaqs', JSON.stringify(newVotedFaqs));
    };

    /**
     * Trasforma URL in URL completi gestendo URL relativi e proxy per domini esterni
     */
    const getProxiedUrl = (url) => {
        if (!url) return url;

        // Se è un URL relativo (inizia con /)
        if (url.startsWith('/')) {
            // URL che puntano a file del frontend (public/) → lascia relativo
            const frontendPaths = ['/documenti/', '/assets/', '/images/', '/static/'];
            if (frontendPaths.some(path => url.startsWith(path))) {
                return url; // Servito da Nginx/frontend direttamente
            }

            // Altri URL relativi (API backend) → aggiungi backend URL
            const apiUrl = client.server || process.env.REACT_APP_API_URL || window.location.origin.replace(':3000', ':3001');
            return `${apiUrl}${url}`;
        }

        // Lista domini che richiedono proxy (governo, prefetture, etc.)
        const externalDomains = [
            'prefettura.interno.gov.it',
            'www.interno.gov.it',
            'interno.gov.it',
            'dait.interno.gov.it',
            'elezioni.interno.gov.it',
            'referendum.interno.gov.it',
        ];

        try {
            const parsedUrl = new URL(url);
            if (externalDomains.some(d => parsedUrl.hostname === d || parsedUrl.hostname.endsWith('.' + d))) {
                // Usa il proxy Django
                const apiUrl = '';  // Use Vite proxy
                return `${apiUrl}/api/risorse/pdf-proxy/?url=${encodeURIComponent(url)}`;
            }
        } catch (e) {
            // URL non valido, restituisci come è
        }

        return url;
    };

    const handleDocumentClick = (doc, e) => {
        const originalUrl = doc.download_url || doc.file_url || doc.url_esterno;

        // Se è un PDF, apri nel viewer
        if (doc.tipo_file === 'PDF' && originalUrl) {
            e.preventDefault();
            const url = getProxiedUrl(originalUrl);
            setPdfViewer({ url, titolo: doc.titolo, originalUrl });
        }
        // Altrimenti lascia che il link apra in nuova scheda
    };

    const handleDownloadNomina = async () => {
        if (!consultazione?.id) {
            setError('Nessuna consultazione attiva');
            return;
        }

        setLoadingNomina(true);

        try {
            const apiUrl = client.server || process.env.REACT_APP_API_URL || window.location.origin.replace(':3000', ':3001');
            const url = `${apiUrl}/api/deleghe/processi/download-mia-nomina/?consultazione_id=${consultazione.id}`;

            // Open PDF in viewer
            setPdfViewer({
                url,
                titolo: 'La Tua Designazione RDL',
                originalUrl: url
            });

        } catch (err) {
            console.error('Errore download nomina:', err);
            setError(
                err.response?.data?.error ||
                'Errore durante il caricamento del PDF. Verifica di avere una designazione confermata.'
            );
        } finally {
            setLoadingNomina(false);
        }
    };

    const filteredFaqs = data.faqs?.categorie?.map(cat => ({
        ...cat,
        faqs: cat.faqs.filter(faq =>
            !searchFaq ||
            faq.domanda.toLowerCase().includes(searchFaq.toLowerCase()) ||
            faq.risposta.toLowerCase().includes(searchFaq.toLowerCase())
        )
    })).filter(cat => cat.faqs.length > 0);

    if (loading) {
        return (
            <div className="loading-container" role="status" aria-live="polite">
                <div className="spinner-border text-primary">
                    <span className="visually-hidden">Caricamento in corso...</span>
                </div>
                <p className="loading-text">Caricamento risorse...</p>
            </div>
        );
    }

    return (
        <>
            <style>{docCardStyles}</style>

            {/* Page Header */}
            <div className="page-header risorse">
                <div className="page-header-title">
                    <i className="fas fa-folder-open"></i>
                    Risorse
                </div>
                <div className="page-header-subtitle">
                    Documenti, guide, FAQ e supporto per i Rappresentanti di Lista
                </div>
            </div>

            {/* RDL Designations Section (if user is RDL) */}
            {mieDesignazioni?.has_designazioni && (
                <div className="card mb-4" style={{ borderLeft: '4px solid #1F4E5F' }}>
                    <div className="card-header" style={{ background: 'linear-gradient(135deg, #1F4E5F 0%, #2C5F6F 100%)', color: '#fff' }}>
                        <div className="d-flex justify-content-between align-items-center">
                            <div>
                                <i className="fas fa-id-badge me-2"></i>
                                <strong>Le Tue Designazioni RDL</strong>
                            </div>
                            <span className="badge bg-warning text-dark">
                                {mieDesignazioni.totale_sezioni} {mieDesignazioni.totale_sezioni === 1 ? 'sezione' : 'sezioni'}
                            </span>
                        </div>
                    </div>
                    <div className="card-body">
                        <p className="card-text mb-3">
                            Sei stato designato come Rappresentante di Lista per {mieDesignazioni.totale_sezioni === 1 ? 'la seguente sezione' : 'le seguenti sezioni'}:
                        </p>

                        <div className="list-group">
                            {mieDesignazioni.designazioni.map((des, idx) => (
                                <div key={idx} className="list-group-item list-group-item-action">
                                    <div className="d-flex w-100 justify-content-between align-items-start">
                                        <div className="flex-grow-1">
                                            <h6 className="mb-1">
                                                <i className="fas fa-map-marker-alt me-2" style={{ color: '#1F4E5F' }}></i>
                                                Sezione {des.sezione.numero}
                                            </h6>
                                            <p className="mb-1 text-muted" style={{ fontSize: '0.9rem' }}>
                                                {des.sezione.indirizzo}
                                            </p>
                                            <p className="mb-0 text-muted" style={{ fontSize: '0.85rem' }}>
                                                {des.sezione.comune_nome}
                                            </p>
                                        </div>
                                        <div className="ms-3">
                                            {des.tipo === 'EFFETTIVO' && (
                                                <span className="badge" style={{ backgroundColor: '#28a745' }}>
                                                    🟢 Effettivo
                                                </span>
                                            )}
                                            {des.tipo === 'SUPPLENTE' && (
                                                <span className="badge" style={{ backgroundColor: '#FFC800', color: '#1F4E5F' }}>
                                                    🟡 Supplente
                                                </span>
                                            )}
                                            {des.tipo === 'EFFETTIVO+SUPPLENTE' && (
                                                <div className="d-flex flex-column gap-1">
                                                    <span className="badge" style={{ backgroundColor: '#28a745', fontSize: '0.7rem' }}>
                                                        🟢 Effettivo
                                                    </span>
                                                    <span className="badge" style={{ backgroundColor: '#FFC800', color: '#1F4E5F', fontSize: '0.7rem' }}>
                                                        🟡 Supplente
                                                    </span>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>

                        <div className="mt-3 d-flex justify-content-end">
                            <button
                                className="btn btn-sm"
                                style={{
                                    backgroundColor: '#FFC800',
                                    color: '#1F4E5F',
                                    fontWeight: '600',
                                    border: 'none'
                                }}
                                onClick={handleDownloadNomina}
                                disabled={loadingNomina}
                            >
                                {loadingNomina ? (
                                    <>
                                        <span className="spinner-border spinner-border-sm me-2"></span>
                                        Caricamento...
                                    </>
                                ) : (
                                    <>
                                        <i className="fas fa-file-pdf me-2"></i>
                                        Visualizza Nomina Ufficiale
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Tabs */}
            <ul className="nav nav-tabs mb-3">
                <li className="nav-item">
                    <button
                        className={`nav-link ${activeTab === 'documenti' ? 'active' : ''}`}
                        onClick={() => setActiveTab('documenti')}
                    >
                        <i className="fas fa-file-download me-1"></i>
                        Documenti
                        {data.documenti?.totale > 0 && (
                            <span className="badge bg-primary ms-1">{data.documenti.totale}</span>
                        )}
                    </button>
                </li>
                <li className="nav-item">
                    <button
                        className={`nav-link ${activeTab === 'faq' ? 'active' : ''}`}
                        onClick={() => setActiveTab('faq')}
                    >
                        <i className="fas fa-question-circle me-1"></i>
                        FAQ
                        {data.faqs?.totale > 0 && (
                            <span className="badge bg-info ms-1">{data.faqs.totale}</span>
                        )}
                    </button>
                </li>
            </ul>

            {/* Tab Documenti */}
            {activeTab === 'documenti' && (
                <>
                    {/* Manuale Utente RDL - sempre in primo */}
                    <div className="card mb-3">
                        <div className="card-header bg-primary text-white">
                            <i className="fas fa-book-open me-2"></i>
                            <strong>Manuale Utente AInaudi</strong>
                            <span className="badge bg-light text-primary ms-2">1</span>
                        </div>
                        <div>
                            <a
                                href="#"
                                onClick={(e) => {
                                    e.preventDefault();
                                    setShowManuale(true);
                                }}
                                className="doc-card"
                            >
                                <div className="doc-card-icon" style={{ background: '#0d6efd12' }}>
                                    <i className="fas fa-book-open" style={{ fontSize: '1.25rem', color: '#0d6efd' }}></i>
                                </div>
                                <div className="doc-card-content">
                                    <div className="doc-card-title">
                                        <i className="fas fa-star doc-card-star"></i>
                                        Manuale Utente Completo
                                    </div>
                                    <p className="doc-card-desc">
                                        Guida completa all'utilizzo dell'applicazione AInaudi per RDL: scrutinio, risorse, assistente IA e funzionalità avanzate.
                                    </p>
                                </div>
                                <i className="fas fa-chevron-right doc-card-arrow"></i>
                            </a>
                        </div>
                    </div>

                    {data.documenti?.categorie?.length === 0 ? (
                        <div className="text-center text-muted py-5">
                            <div style={{ fontSize: '3rem' }}>📂</div>
                            <p>Nessun altro documento disponibile</p>
                        </div>
                    ) : (
                        data.documenti?.categorie?.map(categoria => (
                            <div key={categoria.id} className="card mb-3">
                                <div className="card-header bg-light">
                                    <i className={`fas ${categoria.icona} me-2`}></i>
                                    <strong>{categoria.nome}</strong>
                                    <span className="badge bg-secondary ms-2">{categoria.documenti.length}</span>
                                </div>
                                <div>
                                    {categoria.documenti.map(doc => (
                                        <DocumentCard
                                            key={doc.id}
                                            doc={doc}
                                            onClick={(e) => handleDocumentClick(doc, e)}
                                        />
                                    ))}
                                </div>
                            </div>
                        ))
                    )}
                </>
            )}

            {/* Tab FAQ */}
            {activeTab === 'faq' && (
                <>
                    {/* Barra di ricerca */}
                    <div className="mb-3">
                        <div className="input-group">
                            <span className="input-group-text">
                                <i className="fas fa-search"></i>
                            </span>
                            <input
                                type="text"
                                className="form-control"
                                placeholder="Cerca nelle FAQ..."
                                value={searchFaq}
                                onChange={(e) => setSearchFaq(e.target.value)}
                            />
                            {searchFaq && (
                                <button
                                    className="btn btn-outline-secondary"
                                    onClick={() => setSearchFaq('')}
                                >
                                    <i className="fas fa-times"></i>
                                </button>
                            )}
                        </div>
                    </div>

                    {filteredFaqs?.length === 0 ? (
                        <div className="text-center text-muted py-5">
                            <div style={{ fontSize: '3rem' }}>❓</div>
                            <p>{searchFaq ? 'Nessuna FAQ trovata per la ricerca' : 'Nessuna FAQ disponibile'}</p>
                        </div>
                    ) : (
                        filteredFaqs?.map(categoria => (
                            <div key={categoria.id} className="card mb-3">
                                <div className="card-header bg-light">
                                    <i className={`fas ${categoria.icona} me-2`}></i>
                                    <strong>{categoria.nome}</strong>
                                    <span className="badge bg-secondary ms-2">{categoria.faqs.length}</span>
                                </div>
                                <div className="accordion accordion-flush">
                                    {categoria.faqs.map(faq => (
                                        <div key={faq.id} className="accordion-item">
                                            <h2 className="accordion-header">
                                                <button
                                                    className={`accordion-button ${expandedFaq === faq.id ? '' : 'collapsed'}`}
                                                    type="button"
                                                    onClick={() => setExpandedFaq(expandedFaq === faq.id ? null : faq.id)}
                                                >
                                                    <span className="me-2">
                                                        {faq.in_evidenza && <span className="badge bg-warning text-dark me-1">⭐</span>}
                                                        {faq.domanda}
                                                    </span>
                                                </button>
                                            </h2>
                                            <div className={`accordion-collapse collapse ${expandedFaq === faq.id ? 'show' : ''}`}>
                                                <div className="accordion-body">
                                                    <div className="faq-risposta">
                                                        <ReactMarkdown>{faq.risposta}</ReactMarkdown>
                                                    </div>

                                                    <hr />

                                                    <div className="d-flex justify-content-between align-items-center">
                                                        <small className="text-muted">
                                                            <i className="fas fa-eye me-1"></i>
                                                            {faq.visualizzazioni || 0} visualizzazioni
                                                        </small>

                                                        {votedFaqs[faq.id] ? (
                                                            <small className="text-success">
                                                                <i className="fas fa-check me-1"></i>
                                                                Grazie per il feedback!
                                                            </small>
                                                        ) : (
                                                            <div>
                                                                <span className="text-muted me-2 small">Ti è stata utile?</span>
                                                                <button
                                                                    className="btn btn-sm btn-outline-success me-1"
                                                                    onClick={() => handleVoteFaq(faq.id, true)}
                                                                >
                                                                    <i className="fas fa-thumbs-up"></i> Sì
                                                                </button>
                                                                <button
                                                                    className="btn btn-sm btn-outline-danger"
                                                                    onClick={() => handleVoteFaq(faq.id, false)}
                                                                >
                                                                    <i className="fas fa-thumbs-down"></i> No
                                                                </button>
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))
                    )}
                </>
            )}

            {/* PDF Viewer Modal */}
            {pdfViewer && (
                <PDFViewer
                    url={pdfViewer.url}
                    originalUrl={pdfViewer.originalUrl}
                    titolo={pdfViewer.titolo}
                    onClose={() => setPdfViewer(null)}
                />
            )}

            {/* Manuale Utente Modal */}
            <MarkdownModal
                isOpen={showManuale}
                onClose={() => setShowManuale(false)}
                markdownUrl="/MANUALE_RDL.md"
                title="Manuale Utente AInaudi"
            />
        </>
    );
}

/**
 * Configurazione tipi documento
 */
const DOC_TYPES = {
    'PDF': { icon: 'fa-file-pdf', color: '#dc3545', label: 'PDF' },
    'Word': { icon: 'fa-file-word', color: '#0d6efd', label: 'Word' },
    'Excel': { icon: 'fa-file-excel', color: '#198754', label: 'Excel' },
    'PowerPoint': { icon: 'fa-file-powerpoint', color: '#fd7e14', label: 'PPT' },
    'ZIP': { icon: 'fa-file-archive', color: '#6c757d', label: 'ZIP' },
    'LINK': { icon: 'fa-external-link-alt', color: '#0d6efd', label: 'Link' },
};

/**
 * Card documento - design mobile-first
 */
function DocumentCard({ doc, onClick }) {
    const url = doc.download_url || doc.file_url || doc.url_esterno;
    const isExternal = url?.startsWith('http') && !doc.file_url;
    const docType = isExternal ? 'LINK' : doc.tipo_file;
    const config = DOC_TYPES[docType] || DOC_TYPES['LINK'];

    return (
        <a
            href={url || '#'}
            target="_blank"
            rel="noopener noreferrer"
            onClick={onClick}
            className="doc-card"
        >
            {/* Icona tipo con colore */}
            <div
                className="doc-card-icon"
                style={{ background: `${config.color}12` }}
            >
                <i
                    className={`fas ${config.icon}`}
                    style={{ fontSize: '1.25rem', color: config.color }}
                ></i>
            </div>

            {/* Contenuto */}
            <div className="doc-card-content">
                <div className="doc-card-title">
                    {doc.in_evidenza && (
                        <i className="fas fa-star doc-card-star"></i>
                    )}
                    {doc.titolo}
                </div>
                {doc.descrizione && (
                    <p className="doc-card-desc">{doc.descrizione}</p>
                )}
            </div>

            {/* Freccia / indicatore azione */}
            <i className={`fas ${isExternal ? 'fa-external-link-alt' : 'fa-chevron-right'} doc-card-arrow`}></i>
        </a>
    );
}

export default Risorse;
