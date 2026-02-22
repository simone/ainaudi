import React, { useState, useEffect, useCallback, useRef } from 'react';
import { exportPreviewPng } from './exportPng';
import { VariablePalette, DropField } from './TemplateEmailEditor';
import './TemplateEmailList.css';

// Email wrapper template (matches backend campaign/email/mass_email_wrapper.html)
const WRAPPER_HTML = `<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f5f5;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f5f5f5;padding:20px 0;">
<tr><td align="center" style="padding:0 12px;">
<table cellpadding="0" cellspacing="0" border="0" style="background:#fff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);overflow:hidden;width:100%;max-width:600px;">
<tr><td style="background:linear-gradient(135deg,#1B2A5B 0%,#0D1B3E 100%);padding:30px 40px;text-align:center;">
<h1 style="margin:0 0 8px 0;font-size:28px;color:#FFFFFF;font-weight:700;letter-spacing:-0.5px;"><span style="color:#F5A623;">AI</span>naudi</h1>
<p style="margin:0;color:rgba(255,255,255,0.9);font-size:14px;font-weight:500;text-transform:uppercase;letter-spacing:1px;">Gestione Elettorale</p>
</td></tr>
<tr><td style="padding:30px 40px;">BODY_CONTENT</td></tr>
<tr><td style="background:linear-gradient(to bottom,#f8f9fa 0%,#f8f9fa 10%,#FFC800 10%,#FFC800 100%);padding:25px 40px;text-align:center;border-top:1px solid #e9ecef;">
<p style="margin:0 0 8px 0;font-size:13px;color:#666;font-weight:600;">AInaudi - Piattaforma Gestione Elettorale</p>
<p style="margin:0 0 15px 0;font-size:12px;color:#999;">Movimento 5 Stelle</p>
<p style="margin:0;font-size:11px;color:#aaa;line-height:1.4;">Questa è una email automatica, si prega di non rispondere.</p>
</td></tr>
</table></td></tr></table></body></html>`;

/**
 * LivePreviewIframe
 */
function LivePreviewIframe({ html }) {
    const iframeRef = useRef(null);
    const timerRef = useRef(null);
    useEffect(() => {
        clearTimeout(timerRef.current);
        timerRef.current = setTimeout(() => {
            const iframe = iframeRef.current;
            if (!iframe) return;
            const fullHtml = WRAPPER_HTML.replace('BODY_CONTENT', html || '');
            const doc = iframe.contentDocument;
            doc.open();
            doc.write(fullHtml);
            doc.close();
        }, 300);
        return () => clearTimeout(timerRef.current);
    }, [html]);
    return (
        <iframe
            ref={iframeRef}
            style={{ width: '100%', height: '400px', border: '1px solid var(--tpl-border)', borderRadius: '0.375rem', background: '#f4f4f4' }}
            title="Live Preview"
        />
    );
}

/**
 * TemplateEmailList - CRUD per template email riutilizzabili.
 * Mobile-first card list, theme-aware.
 */
function TemplateEmailList({ client, consultazione }) {
    const [templates, setTemplates] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);

    const [editing, setEditing] = useState(null);
    const [form, setForm] = useState({ nome: '', oggetto: '', corpo: '' });
    const [saving, setSaving] = useState(false);

    const [variables, setVariables] = useState([]);

    const [preview, setPreview] = useState(null);
    const [previewLoading, setPreviewLoading] = useState(false);
    const [exporting, setExporting] = useState(false);
    const [previewDevice, setPreviewDevice] = useState('desktop');
    const [testSending, setTestSending] = useState(false);
    const [previewTemplateId, setPreviewTemplateId] = useState(null);

    useEffect(() => {
        loadTemplates();
        loadVariables();
    }, [client, consultazione]);

    const loadTemplates = async () => {
        setLoading(true);
        const data = await client.emailTemplates.list(consultazione?.id);
        if (!data.error && Array.isArray(data)) {
            setTemplates(data);
        } else if (data.error) {
            setError(data.error);
        }
        setLoading(false);
    };

    const loadVariables = async () => {
        const data = await client.emailTemplates.variables();
        if (!data.error && Array.isArray(data)) setVariables(data);
    };

    const handleNew = () => {
        setEditing('new');
        setForm({ nome: '', oggetto: '', corpo: '' });
        setError(null);
        setSuccess(null);
    };

    const handleEdit = (tpl) => {
        setEditing(tpl.id);
        setForm({ nome: tpl.nome, oggetto: tpl.oggetto, corpo: tpl.corpo });
        setError(null);
        setSuccess(null);
    };

    const handleCancel = () => {
        setEditing(null);
        setForm({ nome: '', oggetto: '', corpo: '' });
    };

    const handleSave = async () => {
        if (!form.nome.trim() || !form.oggetto.trim() || !form.corpo.trim()) {
            setError('Compila tutti i campi obbligatori');
            return;
        }
        setSaving(true);
        setError(null);
        const payload = { ...form, consultazione: consultazione?.id || null };
        const result = editing === 'new'
            ? await client.emailTemplates.create(payload)
            : await client.emailTemplates.update(editing, payload);
        if (result.error) {
            setError(result.error);
        } else {
            setSuccess(editing === 'new' ? 'Template creato' : 'Template aggiornato');
            setEditing(null);
            setForm({ nome: '', oggetto: '', corpo: '' });
            loadTemplates();
            setTimeout(() => setSuccess(null), 3000);
        }
        setSaving(false);
    };

    const handleDuplicate = async (tpl) => {
        const result = await client.emailTemplates.create({
            nome: `${tpl.nome} (copia)`,
            oggetto: tpl.oggetto,
            corpo: tpl.corpo,
            consultazione: tpl.consultazione,
        });
        if (result.error) {
            setError(result.error);
        } else {
            setSuccess('Template duplicato');
            loadTemplates();
            setTimeout(() => setSuccess(null), 3000);
        }
    };

    const handleDelete = async (tpl) => {
        if (!window.confirm(`Eliminare il template "${tpl.nome}"?`)) return;
        const result = await client.emailTemplates.delete(tpl.id);
        if (result.error) {
            setError(result.error);
        } else {
            setSuccess('Template eliminato');
            loadTemplates();
            setTimeout(() => setSuccess(null), 3000);
        }
    };

    const handlePreview = async (tpl) => {
        setPreviewLoading(true);
        const result = await client.emailTemplates.preview(tpl.id);
        if (result.error) setError(result.error);
        else { setPreview(result); setPreviewTemplateId(tpl.id); }
        setPreviewLoading(false);
    };

    const handlePreviewInline = async () => {
        if (!form.corpo.trim()) { setError('Inserisci il corpo del template'); return; }
        setPreviewLoading(true);
        const result = await client.emailTemplates.previewInline({ corpo: form.corpo, oggetto: form.oggetto });
        if (result.error) setError(result.error);
        else setPreview(result);
        setPreviewLoading(false);
    };

    const handleTestSend = async () => {
        if (!previewTemplateId) return;
        setTestSending(true);
        const result = await client.emailTemplates.testSend(previewTemplateId);
        if (result.error) {
            setError(result.error);
        } else {
            setSuccess(`Email di test inviata a ${result.sent_to}`);
            setTimeout(() => setSuccess(null), 5000);
        }
        setTestSending(false);
    };

    const handleExportPng = useCallback(async () => {
        if (!preview) return;
        setExporting(true);
        const width = previewDevice === 'mobile' ? 375 : 700;
        try { await exportPreviewPng(preview.html, { width }); }
        catch (e) { console.error('Export PNG failed:', e); setError('Esportazione PNG fallita'); }
        setExporting(false);
    }, [preview, previewDevice]);

    return (
        <div className="tpl-list">
            {/* Header */}
            <div className="tpl-list-header">
                <h5 className="tpl-list-title">
                    <i className="fas fa-envelope me-2"></i>Template Email
                </h5>
                {!editing && (
                    <button className="btn btn-primary btn-sm" onClick={handleNew}>
                        <i className="fas fa-plus me-1"></i> Nuovo
                    </button>
                )}
            </div>

            {error && (
                <div className="alert alert-danger d-flex justify-content-between align-items-center py-2">
                    <small>{error}</small>
                    <button type="button" className="btn-close btn-close-sm" onClick={() => setError(null)}></button>
                </div>
            )}
            {success && <div className="alert alert-success py-2"><small>{success}</small></div>}

            {/* Editor */}
            {editing && (
                <div className="tpl-editor">
                    <div className="tpl-editor-title">
                        {editing === 'new' ? 'Nuovo Template' : 'Modifica Template'}
                    </div>
                    <div className="tpl-editor-body">
                        <div className="row">
                            <div className="col-lg-8">
                                <div className="mb-3">
                                    <label className="form-label fw-bold small">Nome template *</label>
                                    <input
                                        type="text"
                                        className="form-control form-control-sm"
                                        value={form.nome}
                                        onChange={e => setForm({ ...form, nome: e.target.value })}
                                        placeholder="es. Benvenuto RDL"
                                    />
                                </div>
                                <div className="mb-3">
                                    <label className="form-label fw-bold small">Oggetto email *</label>
                                    <DropField
                                        value={form.oggetto}
                                        onChange={v => setForm({ ...form, oggetto: v })}
                                        placeholder="es. Ciao Nome, conferma la tua registrazione"
                                    />
                                </div>
                                <div className="mb-3">
                                    <label className="form-label fw-bold small">Corpo email (HTML) *</label>
                                    <DropField
                                        value={form.corpo}
                                        onChange={v => setForm({ ...form, corpo: v })}
                                        placeholder={'<p>Ciao Nome,</p>\n<p>Sei registrato come RDL a Comune.</p>'}
                                        multiline
                                    />
                                </div>
                                <div className="d-flex flex-wrap gap-2">
                                    <button className="btn btn-success btn-sm" onClick={handleSave} disabled={saving}>
                                        {saving
                                            ? <><span className="spinner-border spinner-border-sm me-1"></span> Salva...</>
                                            : <><i className="fas fa-save me-1"></i> Salva</>}
                                    </button>
                                    <button className="btn btn-outline-info btn-sm" onClick={handlePreviewInline} disabled={previewLoading || !form.corpo.trim()}>
                                        {previewLoading
                                            ? <span className="spinner-border spinner-border-sm"></span>
                                            : <><i className="fas fa-eye me-1"></i> Anteprima</>}
                                    </button>
                                    <button className="btn btn-secondary btn-sm" onClick={handleCancel}>Annulla</button>
                                </div>
                            </div>
                            <div className="col-lg-4 mt-3 mt-lg-0">
                                <VariablePalette variables={variables} />
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Card List */}
            {loading ? (
                <div className="text-center py-4"><span className="spinner-border"></span></div>
            ) : templates.length === 0 && !editing ? (
                <div className="tpl-empty">
                    <i className="fas fa-envelope-open fa-2x mb-2"></i>
                    <p>Nessun template. Crea il primo per iniziare.</p>
                </div>
            ) : (
                <div className="tpl-cards">
                    {templates.map(tpl => (
                        <div key={tpl.id} className="tpl-card">
                            <div className="tpl-card-body">
                                <div className="tpl-card-info">
                                    <div className="tpl-card-name">{tpl.nome}</div>
                                    <div className="tpl-card-subject">{tpl.oggetto}</div>
                                    <div className="tpl-card-meta">
                                        <span>
                                            <i className="fas fa-paper-plane me-1"></i>
                                            {tpl.n_invii} invii
                                        </span>
                                        <span>
                                            <i className="fas fa-calendar me-1"></i>
                                            {tpl.created_at ? new Date(tpl.created_at).toLocaleDateString('it-IT') : '-'}
                                        </span>
                                    </div>
                                </div>
                                <div className="tpl-card-actions">
                                    <button className="tpl-action-btn tpl-action-preview" onClick={() => handlePreview(tpl)} title="Anteprima">
                                        <i className="fas fa-eye"></i>
                                    </button>
                                    <button className="tpl-action-btn tpl-action-edit" onClick={() => handleEdit(tpl)} title="Modifica">
                                        <i className="fas fa-edit"></i>
                                    </button>
                                    <button className="tpl-action-btn tpl-action-copy" onClick={() => handleDuplicate(tpl)} title="Duplica">
                                        <i className="fas fa-copy"></i>
                                    </button>
                                    <button className="tpl-action-btn tpl-action-delete" onClick={() => handleDelete(tpl)} title="Elimina" disabled={tpl.has_been_sent}>
                                        <i className="fas fa-trash"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Preview Modal */}
            {preview && (
                <div className="modal d-block" tabIndex="-1" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
                    <div className="modal-dialog modal-lg modal-dialog-centered">
                        <div className="modal-content">
                            <div className="modal-header">
                                <h5 className="modal-title">
                                    <i className="fas fa-eye me-2"></i>
                                    Anteprima
                                </h5>
                                <div className="btn-group btn-group-sm ms-3">
                                    <button
                                        className={`btn ${previewDevice === 'desktop' ? 'btn-primary' : 'btn-outline-secondary'}`}
                                        onClick={() => setPreviewDevice('desktop')}
                                        title="Desktop"
                                    ><i className="fas fa-desktop"></i></button>
                                    <button
                                        className={`btn ${previewDevice === 'mobile' ? 'btn-primary' : 'btn-outline-secondary'}`}
                                        onClick={() => setPreviewDevice('mobile')}
                                        title="Mobile"
                                    ><i className="fas fa-mobile-alt"></i></button>
                                </div>
                                <button type="button" className="btn-close ms-auto" onClick={() => { setPreview(null); setPreviewDevice('desktop'); }}></button>
                            </div>
                            <div className="modal-body p-0" style={{ background: previewDevice === 'mobile' ? '#e9ecef' : 'transparent' }}>
                                {preview.subject && (
                                    <div className="p-3 bg-light border-bottom small">
                                        <strong>Oggetto:</strong> {preview.subject}
                                    </div>
                                )}
                                <div style={{ display: 'flex', justifyContent: 'center', padding: previewDevice === 'mobile' ? '16px 0' : 0 }}>
                                    <iframe
                                        srcDoc={preview.html}
                                        style={{
                                            width: previewDevice === 'mobile' ? '375px' : '100%',
                                            height: '500px',
                                            border: previewDevice === 'mobile' ? '1px solid #ccc' : 'none',
                                            borderRadius: previewDevice === 'mobile' ? '8px' : 0,
                                            boxShadow: previewDevice === 'mobile' ? '0 4px 20px rgba(0,0,0,0.15)' : 'none',
                                            transition: 'width 0.3s ease',
                                        }}
                                        title="Email Preview"
                                    />
                                </div>
                            </div>
                            <div className="modal-footer">
                                <small className="text-muted me-auto">
                                    <i className="fas fa-info-circle me-1"></i>
                                    Dati di esempio{previewDevice === 'mobile' && ' — 375px'}
                                </small>
                                <button className="btn btn-outline-success btn-sm" onClick={handleTestSend} disabled={testSending || !previewTemplateId}>
                                    {testSending
                                        ? <><span className="spinner-border spinner-border-sm me-1"></span> Invio...</>
                                        : <><i className="fas fa-paper-plane me-1"></i> Test Invio</>}
                                </button>
                                <button className="btn btn-outline-primary btn-sm" onClick={handleExportPng} disabled={exporting}>
                                    {exporting
                                        ? <><span className="spinner-border spinner-border-sm me-1"></span> Esporto...</>
                                        : <><i className="fas fa-image me-1"></i> PNG</>}
                                </button>
                                <button className="btn btn-secondary btn-sm" onClick={() => { setPreview(null); setPreviewDevice('desktop'); setPreviewTemplateId(null); }}>
                                    Chiudi
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default TemplateEmailList;
