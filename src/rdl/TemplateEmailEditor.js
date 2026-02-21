import React, { useRef, useCallback, useEffect, useState } from 'react';
import './TemplateEmailEditor.css';

/**
 * Label leggibile per ogni variabile (mostrato nel pill).
 */
const VAR_LABELS = {
    'rdl.nome': 'Nome',
    'rdl.cognome': 'Cognome',
    'rdl.full_name': 'Nome Completo',
    'rdl.email': 'Email',
    'rdl.telefono': 'Telefono',
    'rdl.comune': 'Comune',
    'rdl.municipio': 'Municipio',
    'rdl.comune_residenza': 'Comune Residenza',
    'rdl.indirizzo_residenza': 'Indirizzo Residenza',
    'rdl.seggio_preferenza': 'Seggio Preferenza',
    'rdl.status': 'Stato',
};

// Regex to match {{ var_name }}
const VAR_REGEX = /\{\{\s*([\w.]+)\s*\}\}/g;

/**
 * Pill HTML string for a variable (used in HTML mode).
 */
function pillHtml(varName) {
    const label = VAR_LABELS[varName] || varName;
    return `<span class="var-pill" data-var="${varName}" contenteditable="false">${label}</span>`;
}

/**
 * Create a DOM pill element for a variable.
 * The pill is draggable so it can be repositioned within the editor.
 */
function makePillElement(varName) {
    const label = VAR_LABELS[varName] || varName;
    const span = document.createElement('span');
    span.className = 'var-pill';
    span.setAttribute('data-var', varName);
    span.setAttribute('contenteditable', 'false');
    span.setAttribute('draggable', 'true');
    span.textContent = label;
    // When dragging an already-placed pill, set its var name and mark for removal
    span.addEventListener('dragstart', (e) => {
        e.dataTransfer.setData('application/x-var-name', varName);
        e.dataTransfer.setData('text/plain', `{{ ${varName} }}`);
        e.dataTransfer.effectAllowed = 'move';
        // Mark this pill for removal on successful drop
        span.setAttribute('data-dragging', 'true');
        // Slight delay so the drag image captures before we hide it
        setTimeout(() => { span.style.opacity = '0.3'; }, 0);
    });
    span.addEventListener('dragend', (e) => {
        span.removeAttribute('data-dragging');
        span.style.opacity = '';
        // If it was dropped inside a field, the drop handler removes the original
    });
    return span;
}

/**
 * Convert {{ var }} to pill spans in an HTML string.
 */
function templateHtmlToPillHtml(html) {
    return html.replace(VAR_REGEX, (_, varName) => pillHtml(varName));
}

/**
 * Convert pill spans back to {{ var }} in an HTML string.
 */
function pillHtmlToTemplateHtml(html) {
    return html.replace(
        /<span class="var-pill" data-var="([\w.]+)" contenteditable="false">[^<]*<\/span>/g,
        (_, varName) => `{{ ${varName} }}`
    );
}

/**
 * Populate a DOM element with text content, replacing {{ var }} with pill elements.
 * Used for plain-text mode (oggetto field).
 */
function populateWithPills(containerEl, text) {
    containerEl.textContent = '';
    const regex = /\{\{\s*([\w.]+)\s*\}\}/g;
    let lastIndex = 0;
    let match;
    while ((match = regex.exec(text)) !== null) {
        if (match.index > lastIndex) {
            containerEl.appendChild(
                document.createTextNode(text.slice(lastIndex, match.index))
            );
        }
        containerEl.appendChild(makePillElement(match[1]));
        lastIndex = regex.lastIndex;
    }
    if (lastIndex < text.length) {
        containerEl.appendChild(document.createTextNode(text.slice(lastIndex)));
    }
}

/**
 * Extract text with {{ var }} from an element with pill spans.
 * Used for plain-text mode (oggetto field).
 */
function pillsToTemplate(containerEl) {
    let result = '';
    containerEl.childNodes.forEach(node => {
        if (node.nodeType === Node.TEXT_NODE) {
            result += node.textContent;
        } else if (node.nodeType === Node.ELEMENT_NODE) {
            if (node.classList.contains('var-pill')) {
                result += `{{ ${node.getAttribute('data-var')} }}`;
            } else {
                result += node.textContent;
            }
        }
    });
    return result;
}

// ─────────────────────────────────────────────
// VariablePalette
// ─────────────────────────────────────────────

function VariablePalette({ variables }) {
    const handleDragStart = (e, varName) => {
        e.dataTransfer.setData('text/plain', `{{ ${varName} }}`);
        e.dataTransfer.setData('application/x-var-name', varName);
        e.dataTransfer.effectAllowed = 'copy';
    };

    return (
        <div className="var-palette">
            <div className="var-palette-header">
                <i className="fas fa-puzzle-piece me-1"></i>
                Variabili
            </div>
            <div className="var-palette-hint">
                Trascina nel testo
            </div>
            <div className="var-palette-list">
                {variables.map(v => (
                    <div
                        key={v.name}
                        className="var-draggable"
                        draggable="true"
                        onDragStart={e => handleDragStart(e, v.name)}
                        title={v.description}
                    >
                        <span className="var-pill-preview">
                            {VAR_LABELS[v.name] || v.name}
                        </span>
                        <span className="var-draggable-desc">{v.description}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

// ─────────────────────────────────────────────
// Formatting Toolbar (for html mode)
// ─────────────────────────────────────────────

function FormatToolbar({ editorRef }) {
    const exec = useCallback((cmd, val = null) => {
        editorRef.current?.focus();
        document.execCommand(cmd, false, val);
    }, [editorRef]);

    const handleLink = useCallback(() => {
        const url = prompt('URL del link:', 'https://');
        if (url) exec('createLink', url);
    }, [exec]);

    return (
        <div className="format-toolbar">
            <button type="button" title="Grassetto (Ctrl+B)" onMouseDown={e => { e.preventDefault(); exec('bold'); }}>
                <i className="fas fa-bold"></i>
            </button>
            <button type="button" title="Corsivo (Ctrl+I)" onMouseDown={e => { e.preventDefault(); exec('italic'); }}>
                <i className="fas fa-italic"></i>
            </button>
            <button type="button" title="Sottolineato (Ctrl+U)" onMouseDown={e => { e.preventDefault(); exec('underline'); }}>
                <i className="fas fa-underline"></i>
            </button>
            <span className="toolbar-sep" />
            <button type="button" title="Link" onMouseDown={e => { e.preventDefault(); handleLink(); }}>
                <i className="fas fa-link"></i>
            </button>
            <button type="button" title="Rimuovi link" onMouseDown={e => { e.preventDefault(); exec('unlink'); }}>
                <i className="fas fa-unlink"></i>
            </button>
            <span className="toolbar-sep" />
            <button type="button" title="Elenco puntato" onMouseDown={e => { e.preventDefault(); exec('insertUnorderedList'); }}>
                <i className="fas fa-list-ul"></i>
            </button>
            <button type="button" title="Elenco numerato" onMouseDown={e => { e.preventDefault(); exec('insertOrderedList'); }}>
                <i className="fas fa-list-ol"></i>
            </button>
            <span className="toolbar-sep" />
            <button type="button" title="Linea orizzontale" onMouseDown={e => { e.preventDefault(); exec('insertHorizontalRule'); }}>
                <i className="fas fa-minus"></i>
            </button>
        </div>
    );
}

// ─────────────────────────────────────────────
// DropField
// ─────────────────────────────────────────────

/**
 * DropField - campo contenteditable che accetta drop di variabili.
 *
 * Props:
 *   html     - se true, gestisce HTML formattato (con toolbar). Default: false (plain text).
 *   value    - il valore (template con {{ var }})
 *   onChange - callback con il nuovo valore
 */
function DropField({ value, onChange, placeholder, multiline, html: htmlMode, className }) {
    const ref = useRef(null);
    const isInternalChange = useRef(false);
    const [showSource, setShowSource] = useState(false);

    // Sync external value → DOM
    useEffect(() => {
        if (isInternalChange.current) {
            isInternalChange.current = false;
            return;
        }
        const el = ref.current;
        if (!el) return;

        if (htmlMode && !showSource) {
            // HTML mode: render formatted HTML with pills
            const currentHtml = pillHtmlToTemplateHtml(el.innerHTML);
            if (currentHtml !== (value || '')) {
                el.innerHTML = templateHtmlToPillHtml(value || ''); // eslint-disable-line
            }
        } else {
            // Plain text mode: use DOM API to populate with pills
            const currentTemplate = pillsToTemplate(el);
            if (currentTemplate !== (value || '')) {
                if (htmlMode && showSource) {
                    // Source view: show raw HTML as text
                    el.textContent = value || '';
                } else {
                    populateWithPills(el, value || '');
                }
            }
        }
    }, [value, htmlMode, showSource]);

    const emitChange = useCallback(() => {
        const el = ref.current;
        if (!el) return;
        isInternalChange.current = true;

        if (htmlMode && !showSource) {
            onChange(pillHtmlToTemplateHtml(el.innerHTML));
        } else if (htmlMode && showSource) {
            onChange(el.textContent);
        } else {
            onChange(pillsToTemplate(el));
        }
    }, [onChange, htmlMode, showSource]);

    const handleInput = useCallback(() => emitChange(), [emitChange]);

    const handleDragOver = useCallback((e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'copy';
    }, []);

    const handleDrop = useCallback((e) => {
        e.preventDefault();
        const varName = e.dataTransfer.getData('application/x-var-name');
        if (!varName) return;

        const el = ref.current;

        // Remove the original pill if this is a move (drag from within an editor)
        const dragging = el.querySelector('.var-pill[data-dragging="true"]');
        if (dragging) dragging.remove();

        const range = document.caretRangeFromPoint?.(e.clientX, e.clientY);
        if (range) {
            const sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
        }

        const pillEl = makePillElement(varName);

        const sel = window.getSelection();
        if (sel.rangeCount > 0) {
            const r = sel.getRangeAt(0);
            if (el.contains(r.startContainer)) {
                r.deleteContents();
                r.insertNode(pillEl);
                r.setStartAfter(pillEl);
                r.collapse(true);
                sel.removeAllRanges();
                sel.addRange(r);
            } else {
                el.appendChild(pillEl);
            }
        } else {
            el.appendChild(pillEl);
        }

        emitChange();
    }, [emitChange]);

    const handleKeyDown = useCallback((e) => {
        if (!multiline && e.key === 'Enter') e.preventDefault();
    }, [multiline]);

    const handlePaste = useCallback((e) => {
        if (!htmlMode || showSource) {
            // Plain text paste
            e.preventDefault();
            const text = e.clipboardData.getData('text/plain');
            const sel = window.getSelection();
            if (!sel.rangeCount) return;
            const range = sel.getRangeAt(0);
            range.deleteContents();
            range.insertNode(document.createTextNode(text));
            range.collapse(false);
            emitChange();
        }
        // In HTML visual mode: let browser handle rich paste
    }, [htmlMode, showSource, emitChange]);

    const toggleSource = useCallback(() => {
        const el = ref.current;
        if (!el) return;

        if (!showSource) {
            // Switching TO source view: save current HTML
            const html = pillHtmlToTemplateHtml(el.innerHTML);
            el.textContent = html;
        } else {
            // Switching FROM source view: render HTML
            const html = el.textContent;
            el.innerHTML = templateHtmlToPillHtml(html); // eslint-disable-line
        }
        setShowSource(!showSource);
    }, [showSource]);

    return (
        <div className="drop-field-wrapper">
            {htmlMode && multiline && (
                <div className="d-flex align-items-center">
                    <FormatToolbar editorRef={ref} />
                    <button
                        type="button"
                        className={`btn btn-sm ms-auto ${showSource ? 'btn-dark' : 'btn-outline-secondary'}`}
                        onClick={toggleSource}
                        title={showSource ? 'Vista formattata' : 'Codice HTML'}
                    >
                        <i className={`fas ${showSource ? 'fa-eye' : 'fa-code'}`}></i>
                    </button>
                </div>
            )}
            <div
                ref={ref}
                className={[
                    'drop-field',
                    multiline ? 'drop-field-multi' : 'drop-field-single',
                    htmlMode && !showSource ? 'drop-field-html' : '',
                    showSource ? 'drop-field-source' : '',
                    className || '',
                ].join(' ')}
                contentEditable
                onInput={handleInput}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                onKeyDown={handleKeyDown}
                onPaste={handlePaste}
                data-placeholder={placeholder}
                suppressContentEditableWarning
            />
        </div>
    );
}

export { VariablePalette, DropField };
