import React, { useState, useEffect } from 'react';
import PDFViewer from './PDFViewer';

/**
 * Pagina Risorse: Documenti e FAQ
 * I contenuti sono filtrati in base alla consultazione attiva e al suo tipo (referendum, comunali, etc.)
 */

// CSS per le card documenti
const docCardStyles = `
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
            const result = await client.risorse.list(consultazione?.id);
            if (result?.error) {
                // API non disponibile, mostra dati mock
                setData(getMockData());
            } else {
                setData(result);
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
     * Trasforma URL esterni in URL proxy per evitare CORS
     */
    const getProxiedUrl = (url) => {
        if (!url) return url;

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
                const apiUrl = import.meta.env.VITE_API_URL || '';
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
            <div className="page-header assistenza">
                <div className="page-header-title">
                    <i className="fas fa-life-ring"></i>
                    Assistenza
                </div>
                <div className="page-header-subtitle">
                    Documenti, guide, FAQ e supporto per i Rappresentanti di Lista
                </div>
            </div>

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
                    {data.documenti?.categorie?.length === 0 ? (
                        <div className="text-center text-muted py-5">
                            <div style={{ fontSize: '3rem' }}>📂</div>
                            <p>Nessun documento disponibile</p>
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
                                                    <p style={{ whiteSpace: 'pre-line' }}>{faq.risposta}</p>

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
