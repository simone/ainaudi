import React, { useState, useEffect, useRef, useCallback } from 'react';
import { exportPreviewPng } from './exportPng';
import TemplateEmailList from './TemplateEmailList';

/**
 * MassEmail - Pagina unificata per gestione template email e invio massivo.
 *
 * Solo admin (can_manage_mass_email).
 *
 * Layout:
 * - Sezione filtri destinatari (territorio + stato)
 * - Conteggio destinatari
 * - Selezione template
 * - Preview + invio con progress bar
 *
 * Tab: "Invia Email" | "Gestione Template"
 */
function MassEmail({ client, consultazione }) {
    const [activeSection, setActiveSection] = useState('send'); // 'send' | 'templates'

    // Territory filters
    const [regioni, setRegioni] = useState([]);
    const [province, setProvince] = useState([]);
    const [comuni, setComuni] = useState([]);
    const [municipi, setMunicipi] = useState([]);
    const [regioneFilter, setRegioneFilter] = useState('');
    const [provinciaFilter, setProvinciaFilter] = useState('');
    const [comuneFilter, setComuneFilter] = useState('');
    const [municipioFilter, setMunicipioFilter] = useState('');

    // Status filter
    const [statusFilter, setStatusFilter] = useState('');

    // Template selection
    const [templates, setTemplates] = useState([]);
    const [selectedTemplateId, setSelectedTemplateId] = useState('');

    // Recipients info
    const [recipientsInfo, setRecipientsInfo] = useState(null);
    const [loadingInfo, setLoadingInfo] = useState(false);

    // Preview
    const [preview, setPreview] = useState(null);
    const [previewLoading, setPreviewLoading] = useState(false);

    // Send
    const [sending, setSending] = useState(false);
    const [taskId, setTaskId] = useState(null);
    const [progress, setProgress] = useState(null);
    const pollingRef = useRef(null);

    // PNG export
    const [exporting, setExporting] = useState(false);

    // Error / success
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);

    // Load initial data
    useEffect(() => {
        loadRegioni();
        loadTemplates();
    }, [client]);

    useEffect(() => {
        return () => { if (pollingRef.current) clearTimeout(pollingRef.current); };
    }, []);

    // Cascading territory filters
    useEffect(() => {
        if (regioneFilter) {
            loadProvince(regioneFilter);
        } else {
            setProvince([]);
            setProvinciaFilter('');
            setComuni([]);
            setComuneFilter('');
            setMunicipi([]);
            setMunicipioFilter('');
        }
    }, [regioneFilter]);

    useEffect(() => {
        if (provinciaFilter) {
            loadComuni(provinciaFilter);
        } else {
            setComuni([]);
            setComuneFilter('');
            setMunicipi([]);
            setMunicipioFilter('');
        }
    }, [provinciaFilter]);

    useEffect(() => {
        if (comuneFilter) {
            loadMunicipi(comuneFilter);
        } else {
            setMunicipi([]);
            setMunicipioFilter('');
        }
    }, [comuneFilter]);

    // Reload recipients info when filters or template change
    useEffect(() => {
        if (selectedTemplateId) {
            loadRecipientsInfo();
        } else {
            setRecipientsInfo(null);
        }
    }, [selectedTemplateId, regioneFilter, provinciaFilter, comuneFilter, municipioFilter, statusFilter]);

    const loadRegioni = async () => {
        const data = await client.territorio.regioni();
        const items = data?.results || (Array.isArray(data) ? data : null);
        if (items) setRegioni(items);
    };

    const loadProvince = async (regioneId) => {
        const data = await client.territorio.province(regioneId);
        const items = data?.results || (Array.isArray(data) ? data : null);
        if (items) setProvince(items);
    };

    const loadComuni = async (provinciaId) => {
        const data = await client.territorio.comuni(provinciaId);
        const items = data?.results || (Array.isArray(data) ? data : null);
        if (items) setComuni(items);
    };

    const loadMunicipi = async (comuneId) => {
        const data = await client.territorio.municipi(comuneId);
        if (!data.error && data.municipi && Array.isArray(data.municipi)) {
            setMunicipi(data.municipi);
        } else {
            setMunicipi([]);
        }
    };

    const loadTemplates = async () => {
        const data = await client.emailTemplates.list(consultazione?.id);
        if (!data.error && Array.isArray(data)) {
            setTemplates(data);
        }
    };

    const buildFilters = () => {
        const filters = {};
        if (comuneFilter) filters.comune = comuneFilter;
        if (municipioFilter) filters.municipio = municipioFilter;
        if (regioneFilter) filters.regione = regioneFilter;
        if (provinciaFilter) filters.provincia = provinciaFilter;
        if (statusFilter) filters.status = statusFilter;
        return filters;
    };

    const loadRecipientsInfo = async () => {
        setLoadingInfo(true);
        const info = await client.massEmail.recipientsInfo({
            template_id: parseInt(selectedTemplateId),
            filters: buildFilters(),
            consultazione_id: consultazione?.id,
        });
        if (!info.error) {
            setRecipientsInfo(info);
        } else {
            setError(info.error);
        }
        setLoadingInfo(false);
    };

    const handlePreview = async () => {
        if (!selectedTemplateId) return;
        setPreviewLoading(true);
        const result = await client.emailTemplates.preview(parseInt(selectedTemplateId));
        if (result.error) {
            setError(result.error);
        } else {
            setPreview(result);
        }
        setPreviewLoading(false);
    };

    const handleSend = async () => {
        if (!selectedTemplateId || !recipientsInfo || recipientsInfo.new_recipients === 0) return;

        setSending(true);
        setError(null);
        setSuccess(null);

        const result = await client.massEmail.send({
            template_id: parseInt(selectedTemplateId),
            filters: buildFilters(),
            consultazione_id: consultazione?.id,
        });

        if (result.error) {
            setError(result.error);
            setSending(false);
            return;
        }

        setTaskId(result.task_id);
        pollProgress(result.task_id);
    };

    const pollProgress = (tid) => {
        const poll = async () => {
            const prog = await client.massEmail.progress(tid);
            if (prog.error) {
                setError(prog.error);
                setSending(false);
                return;
            }

            setProgress(prog);

            if (prog.status === 'SUCCESS') {
                setSending(false);
                setSuccess(`Invio completato: ${prog.sent} email inviate${prog.failed > 0 ? `, ${prog.failed} fallite` : ''}`);
                // Refresh recipients info to show updated dedup counts
                loadRecipientsInfo();
                return;
            }
            if (prog.status === 'FAILURE') {
                setSending(false);
                setError(`Invio fallito: ${prog.error || 'errore sconosciuto'}`);
                return;
            }

            pollingRef.current = setTimeout(poll, 2000);
        };
        poll();
    };

    const handleReset = () => {
        setTaskId(null);
        setProgress(null);
        setSending(false);
        setSuccess(null);
    };

    const clearFilters = () => {
        setRegioneFilter('');
        setProvinciaFilter('');
        setComuneFilter('');
        setMunicipioFilter('');
        setStatusFilter('');
    };

    const percentage = progress && progress.total > 0
        ? Math.round((progress.current / progress.total) * 100)
        : 0;

    const handleExportPng = useCallback(async () => {
        if (!preview) return;
        setExporting(true);
        try {
            await exportPreviewPng(preview.html);
        } catch (e) {
            console.error('Export PNG failed:', e);
            setError('Esportazione PNG fallita');
        }
        setExporting(false);
    }, [preview]);

    const hasFilters = regioneFilter || provinciaFilter || comuneFilter || municipioFilter || statusFilter;

    return (
        <div>
            {/* Page Header */}
            <div className="page-header mass-email">
                <div className="page-header-title">
                    <i className="fas fa-paper-plane"></i>
                    Mass Mail
                </div>
                <div className="page-header-subtitle">
                    Invio email massive agli RDL con template personalizzabili
                </div>
            </div>

            {/* Tab navigation */}
            <ul className="nav nav-tabs mb-4">
                <li className="nav-item">
                    <button
                        className={`nav-link ${activeSection === 'send' ? 'active' : ''}`}
                        onClick={() => setActiveSection('send')}
                    >
                        <i className="fas fa-paper-plane me-1"></i>
                        Invia Email
                    </button>
                </li>
                <li className="nav-item">
                    <button
                        className={`nav-link ${activeSection === 'templates' ? 'active' : ''}`}
                        onClick={() => { setActiveSection('templates'); loadTemplates(); }}
                    >
                        <i className="fas fa-file-alt me-1"></i>
                        Gestione Template
                    </button>
                </li>
            </ul>

            {/* Error / Success alerts */}
            {error && (
                <div className="alert alert-danger d-flex justify-content-between align-items-center">
                    <span>{error}</span>
                    <button type="button" className="btn-close" onClick={() => setError(null)}></button>
                </div>
            )}
            {success && (
                <div className="alert alert-success d-flex justify-content-between align-items-center">
                    <span>{success}</span>
                    <button type="button" className="btn-close" onClick={() => setSuccess(null)}></button>
                </div>
            )}

            {/* TAB: Gestione Template */}
            {activeSection === 'templates' && (
                <TemplateEmailList client={client} consultazione={consultazione} />
            )}

            {/* TAB: Invia Email */}
            {activeSection === 'send' && (
                <div className="row">
                    {/* Left column: Filters */}
                    <div className="col-lg-5 mb-4">
                        <div className="card">
                            <div className="card-header d-flex justify-content-between align-items-center">
                                <strong>
                                    <i className="fas fa-filter me-1"></i>
                                    Destinatari
                                </strong>
                                {hasFilters && (
                                    <button className="btn btn-sm btn-outline-secondary" onClick={clearFilters}>
                                        <i className="fas fa-times me-1"></i>Pulisci
                                    </button>
                                )}
                            </div>
                            <div className="card-body">
                                {/* Territory filters */}
                                <div className="mb-3">
                                    <label className="form-label small fw-bold">Regione</label>
                                    <select
                                        className="form-select form-select-sm"
                                        value={regioneFilter}
                                        onChange={e => setRegioneFilter(e.target.value)}
                                    >
                                        <option value="">Tutte le regioni</option>
                                        {regioni.map(r => (
                                            <option key={r.id} value={r.id}>{r.nome}</option>
                                        ))}
                                    </select>
                                </div>

                                <div className="mb-3">
                                    <label className="form-label small fw-bold">Provincia</label>
                                    <select
                                        className="form-select form-select-sm"
                                        value={provinciaFilter}
                                        onChange={e => setProvinciaFilter(e.target.value)}
                                        disabled={!regioneFilter}
                                    >
                                        <option value="">Tutte le province</option>
                                        {province.map(p => (
                                            <option key={p.id} value={p.id}>{p.nome}</option>
                                        ))}
                                    </select>
                                </div>

                                <div className="mb-3">
                                    <label className="form-label small fw-bold">Comune</label>
                                    <select
                                        className="form-select form-select-sm"
                                        value={comuneFilter}
                                        onChange={e => setComuneFilter(e.target.value)}
                                        disabled={!provinciaFilter}
                                    >
                                        <option value="">Tutti i comuni</option>
                                        {comuni.map(c => (
                                            <option key={c.id} value={c.id}>{c.nome}</option>
                                        ))}
                                    </select>
                                </div>

                                {municipi.length > 0 && (
                                    <div className="mb-3">
                                        <label className="form-label small fw-bold">Municipio</label>
                                        <select
                                            className="form-select form-select-sm"
                                            value={municipioFilter}
                                            onChange={e => setMunicipioFilter(e.target.value)}
                                        >
                                            <option value="">Tutti i municipi</option>
                                            {municipi.map(m => (
                                                <option key={m.id} value={m.id}>
                                                    Municipio {m.numero || m.nome || m.id}
                                                </option>
                                            ))}
                                        </select>
                                    </div>
                                )}

                                <hr />

                                {/* Status filter */}
                                <div className="mb-3">
                                    <label className="form-label small fw-bold">Stato RDL</label>
                                    <select
                                        className="form-select form-select-sm"
                                        value={statusFilter}
                                        onChange={e => setStatusFilter(e.target.value)}
                                    >
                                        <option value="">Tutti</option>
                                        <option value="APPROVED">Approvati</option>
                                        <option value="PENDING">Da approvare</option>
                                        <option value="REJECTED">Rifiutati</option>
                                    </select>
                                </div>

                                <hr />

                                {/* Template selection */}
                                <div className="mb-3">
                                    <label className="form-label small fw-bold">Template Email</label>
                                    {templates.length === 0 ? (
                                        <div className="alert alert-warning small py-2 mb-0">
                                            Nessun template. Crea un template nella sezione "Gestione Template".
                                        </div>
                                    ) : (
                                        <select
                                            className="form-select form-select-sm"
                                            value={selectedTemplateId}
                                            onChange={e => setSelectedTemplateId(e.target.value)}
                                        >
                                            <option value="">-- Seleziona template --</option>
                                            {templates.map(t => (
                                                <option key={t.id} value={t.id}>
                                                    {t.nome} ({t.n_invii} invii)
                                                </option>
                                            ))}
                                        </select>
                                    )}
                                </div>

                                {/* Recipients info */}
                                {loadingInfo && (
                                    <div className="text-center py-2">
                                        <span className="spinner-border spinner-border-sm me-1"></span>
                                        <small>Calcolo destinatari...</small>
                                    </div>
                                )}
                                {recipientsInfo && !loadingInfo && (
                                    <div className={`alert ${recipientsInfo.new_recipients > 0 ? 'alert-info' : 'alert-warning'} py-2 mb-0`}>
                                        <div className="row text-center small">
                                            <div className="col-4">
                                                <div className="fw-bold fs-6">{recipientsInfo.total}</div>
                                                <div>Totale</div>
                                            </div>
                                            <div className="col-4">
                                                <div className="fw-bold fs-6 text-success">{recipientsInfo.new_recipients}</div>
                                                <div>Nuovi</div>
                                            </div>
                                            <div className="col-4">
                                                <div className="fw-bold fs-6 text-warning">{recipientsInfo.already_sent}</div>
                                                <div>Gi&agrave; inviato</div>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Right column: Preview + Send */}
                    <div className="col-lg-7 mb-4">
                        <div className="card">
                            <div className="card-header d-flex justify-content-between align-items-center">
                                <strong>
                                    <i className="fas fa-eye me-1"></i>
                                    Anteprima e Invio
                                </strong>
                                {selectedTemplateId && !taskId && (
                                    <button
                                        className="btn btn-sm btn-outline-info"
                                        onClick={handlePreview}
                                        disabled={previewLoading}
                                    >
                                        {previewLoading ? (
                                            <span className="spinner-border spinner-border-sm"></span>
                                        ) : (
                                            <><i className="fas fa-eye me-1"></i> Aggiorna Preview</>
                                        )}
                                    </button>
                                )}
                            </div>
                            <div className="card-body">
                                {!selectedTemplateId ? (
                                    <div className="text-center text-muted py-5">
                                        <i className="fas fa-envelope-open fa-3x mb-3 d-block opacity-25"></i>
                                        <p>Seleziona i filtri e un template per vedere l'anteprima</p>
                                    </div>
                                ) : !taskId ? (
                                    <>
                                        {/* Preview */}
                                        {preview ? (
                                            <div className="mb-3">
                                                <div className="bg-light p-2 rounded mb-2 small">
                                                    <strong>Oggetto:</strong> {preview.subject}
                                                </div>
                                                <div className="border rounded" style={{ overflow: 'hidden' }}>
                                                    <iframe
                                                        srcDoc={preview.html}
                                                        style={{ width: '100%', height: '400px', border: 'none' }}
                                                        title="Email Preview"
                                                    />
                                                </div>
                                                <div className="d-flex justify-content-between align-items-center mt-2">
                                                    <small className="text-muted">
                                                        <i className="fas fa-info-circle me-1"></i>
                                                        Dati di esempio (Mario Rossi, Roma)
                                                    </small>
                                                    <button
                                                        className="btn btn-sm btn-outline-primary"
                                                        onClick={handleExportPng}
                                                        disabled={exporting}
                                                    >
                                                        {exporting ? (
                                                            <><span className="spinner-border spinner-border-sm me-1"></span> Esporto...</>
                                                        ) : (
                                                            <><i className="fas fa-image me-1"></i> Esporta PNG</>
                                                        )}
                                                    </button>
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="text-center text-muted py-4">
                                                <p className="mb-0">Clicca "Aggiorna Preview" per visualizzare l'anteprima</p>
                                            </div>
                                        )}

                                        {/* Send button */}
                                        <div className="d-grid mt-3">
                                            <button
                                                className="btn btn-success btn-lg"
                                                onClick={handleSend}
                                                disabled={sending || !recipientsInfo || recipientsInfo.new_recipients === 0}
                                            >
                                                {sending ? (
                                                    <><span className="spinner-border spinner-border-sm me-2"></span> Invio in corso...</>
                                                ) : recipientsInfo && recipientsInfo.new_recipients === 0 ? (
                                                    <><i className="fas fa-ban me-2"></i> Nessun nuovo destinatario</>
                                                ) : (
                                                    <><i className="fas fa-paper-plane me-2"></i>
                                                        Invia a {recipientsInfo?.new_recipients || '...'} destinatari
                                                    </>
                                                )}
                                            </button>
                                        </div>
                                    </>
                                ) : (
                                    /* Progress */
                                    <div>
                                        <h6 className="mb-3">
                                            {progress?.status === 'SUCCESS' ? (
                                                <><i className="fas fa-check-circle text-success me-2"></i> Invio completato</>
                                            ) : progress?.status === 'FAILURE' ? (
                                                <><i className="fas fa-times-circle text-danger me-2"></i> Invio fallito</>
                                            ) : (
                                                <><span className="spinner-border spinner-border-sm me-2"></span> Invio in corso...</>
                                            )}
                                        </h6>

                                        {progress && (
                                            <>
                                                <div className="d-flex justify-content-between mb-1 small">
                                                    <span>{progress.current}/{progress.total}</span>
                                                    <span className="fw-bold">{percentage}%</span>
                                                </div>
                                                <div className="progress mb-3" style={{ height: '24px' }}>
                                                    <div
                                                        className={`progress-bar ${
                                                            progress.status === 'SUCCESS' ? 'bg-success' :
                                                            progress.status === 'FAILURE' ? 'bg-danger' :
                                                            'progress-bar-striped progress-bar-animated'
                                                        }`}
                                                        style={{ width: `${percentage}%` }}
                                                    >
                                                        {percentage}%
                                                    </div>
                                                </div>
                                                <div className="row text-center mb-3">
                                                    <div className="col-4">
                                                        <div className="h5 mb-0 text-success">{progress.sent}</div>
                                                        <small>Inviate</small>
                                                    </div>
                                                    <div className="col-4">
                                                        <div className="h5 mb-0 text-danger">{progress.failed}</div>
                                                        <small>Fallite</small>
                                                    </div>
                                                    <div className="col-4">
                                                        <div className="h5 mb-0">{progress.total}</div>
                                                        <small>Totale</small>
                                                    </div>
                                                </div>

                                                {(progress.status === 'SUCCESS' || progress.status === 'FAILURE') && (
                                                    <button className="btn btn-outline-primary w-100" onClick={handleReset}>
                                                        <i className="fas fa-redo me-1"></i> Nuovo invio
                                                    </button>
                                                )}
                                            </>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default MassEmail;
