import React, { useState, useEffect, useRef } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import MarkdownModal from './MarkdownModal';
import JSONPathAutocomplete from './JSONPathAutocomplete';
import './TemplateEditor.css';

// Configure PDF.js worker (use local worker from /public folder)
pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.js';

/**
 * Template Editor - Admin only
 * Visual PDF editor with click-to-place field mappings
 *
 * STATUS: Full visual editing with PDF.js
 */
function TemplateEditor({ templateId: initialTemplateId, client }) {
    const [templates, setTemplates] = useState([]);
    const [templateTypes, setTemplateTypes] = useState([]);
    const [selectedTemplateId, setSelectedTemplateId] = useState(initialTemplateId || null);
    const [template, setTemplate] = useState(null);
    const [fieldMappings, setFieldMappings] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);
    const [showNewTemplateForm, setShowNewTemplateForm] = useState(false);
    const [newTemplate, setNewTemplate] = useState({
        name: '',
        template_type: '',
        description: '',
        file: null
    });
    const [showNewFieldForm, setShowNewFieldForm] = useState(false);
    const [showLoopGuide, setShowLoopGuide] = useState(false);
    const [showLoopFieldsModal, setShowLoopFieldsModal] = useState(false);
    const [currentLoopIndex, setCurrentLoopIndex] = useState(null);
    const [isAddingLoopField, setIsAddingLoopField] = useState(false); // Modalità aggiunta campo loop
    const [isAddingLoopPage, setIsAddingLoopPage] = useState(false); // Modalità aggiunta pagina loop
    const [newLoopField, setNewLoopField] = useState({ jsonpath: '', x: 0, y: 0, width: 100, height: 20 });
    const [newField, setNewField] = useState({
        jsonpath: '',
        type: 'text',
        x: 100,
        y: 100,
        width: 200,
        height: 20,
        page: 0
    });

    // PDF rendering state
    const [pdfDoc, setPdfDoc] = useState(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [numPages, setNumPages] = useState(0);
    const [scale, setScale] = useState(1.0);
    const canvasRef = useRef(null);

    // Interactive selection state
    const [isSelecting, setIsSelecting] = useState(false);
    const [selectionStart, setSelectionStart] = useState(null);
    const [currentSelection, setCurrentSelection] = useState(null);
    const renderTaskRef = useRef(null);
    const canvasSnapshotRef = useRef(null);
    const isRenderingRef = useRef(false);

    // Field manipulation state (resize/drag)
    const [hoveredField, setHoveredField] = useState(null); // { index, isLoopField, loopIndex, handle }
    const [draggingField, setDraggingField] = useState(null); // { index, isLoopField, loopIndex, startX, startY, mode: 'move'|'resize', handle }
    const [cursorStyle, setCursorStyle] = useState('pointer');

    // Load available templates and template types on mount
    useEffect(() => {
        loadTemplates();
        loadTemplateTypes();
    }, []);

    // Load specific template when selected
    useEffect(() => {
        if (selectedTemplateId) {
            loadTemplate(selectedTemplateId);
        }
    }, [selectedTemplateId]);

    // Load and render PDF when template is loaded
    useEffect(() => {
        if (template?.template_file_url) {
            loadPDF(template.template_file_url);
        }
    }, [template]);

    // Re-render PDF when page or scale changes
    useEffect(() => {
        if (pdfDoc) {
            renderPage(currentPage);
        }
    }, [pdfDoc, currentPage, scale, fieldMappings]);

    // Draw selection overlay on canvas without re-rendering PDF
    useEffect(() => {
        if (!isSelecting || !currentSelection || !canvasRef.current || !canvasSnapshotRef.current) return;

        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');

        // Restore the saved canvas state
        ctx.putImageData(canvasSnapshotRef.current, 0, 0);

        // Draw selection on top
        const scaledSelection = {
            x: currentSelection.x * scale,
            y: currentSelection.y * scale,
            width: currentSelection.width * scale,
            height: currentSelection.height * scale
        };
        drawSelection(ctx, scaledSelection);
    }, [currentSelection, isSelecting, scale]);

    // Re-render when hoveredField changes (to show/hide resize handles)
    useEffect(() => {
        if (pdfDoc) {
            renderPage(currentPage);
        }
    }, [hoveredField]);

    const loadTemplates = async () => {
        try {
            const data = await client.get('/api/documents/templates/');
            setTemplates(data || []);
            // Auto-select first template if none selected
            if (!selectedTemplateId && data && data.length > 0) {
                setSelectedTemplateId(data[0].id);
            }
        } catch (err) {
            setError(`Errore caricamento lista template: ${err.message}`);
            console.error('Templates list error:', err);
        }
    };

    const loadTemplateTypes = async () => {
        console.log('🔍 Loading template types...');
        try {
            const data = await client.get('/api/documents/template-types/');
            console.log('✅ Template types loaded:', data);
            setTemplateTypes(data || []);
            // Set default template_type if available
            if (data && data.length > 0 && !newTemplate.template_type) {
                setNewTemplate(prev => ({ ...prev, template_type: data[0].id }));
            }
        } catch (err) {
            console.error('❌ Template types load error:', err);
            setError(`Errore caricamento tipi template: ${err.message}`);
        }
    };

    const loadTemplate = async (id) => {
        try {
            setLoading(true);
            setError(null);
            const data = await client.get(`/api/documents/templates/${id}/editor/`);
            setTemplate(data);
            setFieldMappings(data.field_mappings || []);
        } catch (err) {
            setError(`Errore caricamento template: ${err.message}`);
            console.error('Template load error:', err);
        } finally {
            setLoading(false);
        }
    };

    const loadPDF = async (url) => {
        try {
            const loadingTask = pdfjsLib.getDocument(url);
            const pdf = await loadingTask.promise;
            setPdfDoc(pdf);
            setNumPages(pdf.numPages);
            setCurrentPage(1);
        } catch (err) {
            setError(`Errore caricamento PDF: ${err.message}`);
            console.error('PDF load error:', err);
        }
    };

    const renderPage = async (pageNum) => {
        if (!pdfDoc || !canvasRef.current) return;

        // Skip if already rendering
        if (isRenderingRef.current) {
            console.log('Render already in progress, skipping');
            return;
        }

        // Cancel previous render if in progress
        if (renderTaskRef.current) {
            renderTaskRef.current.cancel();
        }

        try {
            isRenderingRef.current = true;

            const page = await pdfDoc.getPage(pageNum);
            const canvas = canvasRef.current;
            const ctx = canvas.getContext('2d');
            const viewport = page.getViewport({ scale });

            canvas.width = viewport.width;
            canvas.height = viewport.height;

            // Render PDF page and store the task
            const renderTask = page.render({ canvasContext: ctx, viewport });
            renderTaskRef.current = renderTask;

            await renderTask.promise;
            renderTaskRef.current = null;

            // Draw existing field mappings as overlays
            drawFieldMappingsOverlay(ctx, pageNum - 1);

            // Save canvas snapshot for selection drawing
            canvasSnapshotRef.current = ctx.getImageData(0, 0, canvas.width, canvas.height);
        } catch (err) {
            if (err.name === 'RenderingCancelledException') {
                console.log('Render cancelled');
            } else {
                console.error('Page render error:', err);
            }
        } finally {
            isRenderingRef.current = false;
        }
    };

    const drawFieldMappingsOverlay = (ctx, pageIndex) => {
        const pageMappings = fieldMappings.filter(m => m.page === pageIndex);

        // Also include loop_pages that match this page
        const loopPageMappings = fieldMappings
            .filter(m => m.type === 'loop' && m.loop_pages && m.loop_pages.length > 0)
            .flatMap(m => m.loop_pages
                .filter(lp => lp.page === pageIndex)
                .map(lp => ({ ...m, area: lp.area, isLoopPage: true }))
            );

        const allMappings = [...pageMappings, ...loopPageMappings];

        allMappings.forEach((mapping, index) => {
            const { x, y, width, height } = mapping.area;
            const scaledX = x * scale;
            const scaledY = y * scale;
            const scaledWidth = width * scale;
            const scaledHeight = height * scale;

            // Determine if this is a loop
            const isLoop = mapping.type === 'loop';
            const originalIndex = fieldMappings.findIndex(m => m === mapping);

            // Check if this field is hovered
            const isHovered = hoveredField && hoveredField.type === 'field' && hoveredField.index === originalIndex;

            // Draw rectangle
            ctx.strokeStyle = isLoop ? '#ffc107' : '#0dcaf0';
            ctx.lineWidth = isHovered ? 4 : (isLoop ? 3 : 2);
            ctx.strokeRect(scaledX, scaledY, scaledWidth, scaledHeight);

            // Fill with semi-transparent color
            ctx.fillStyle = isLoop ? 'rgba(255, 193, 7, 0.2)' : 'rgba(13, 202, 240, 0.2)';
            ctx.fillRect(scaledX, scaledY, scaledWidth, scaledHeight);

            // Draw label
            ctx.fillStyle = '#000';
            ctx.font = 'bold 12px Arial';
            const label = isLoop ? `🔁 LOOP: ${mapping.jsonpath}` : `${index + 1}. ${mapping.jsonpath}`;
            ctx.fillText(label, scaledX + 5, scaledY + 15);

            // If loop, draw arrow down indicator and loop fields
            if (isLoop) {
                ctx.fillStyle = '#ffc107';
                ctx.font = '20px Arial';
                ctx.fillText('↓', scaledX + scaledWidth - 25, scaledY + scaledHeight - 5);

                // Draw loop fields (if any)
                if (mapping.loop_fields && mapping.loop_fields.length > 0) {
                    mapping.loop_fields.forEach((field, fieldIndex) => {
                        // Convert relative coordinates to absolute
                        const fieldAbsX = (x + field.x) * scale;
                        const fieldAbsY = (y + field.y) * scale;
                        const fieldW = field.width * scale;
                        const fieldH = field.height * scale;

                        // Check if this loop field is hovered
                        const isLoopFieldHovered = hoveredField && hoveredField.type === 'loop_field'
                            && hoveredField.index === originalIndex && hoveredField.fieldIndex === fieldIndex;

                        // Draw field rectangle (green for loop fields)
                        ctx.strokeStyle = '#28a745';
                        ctx.lineWidth = isLoopFieldHovered ? 3 : 2;
                        ctx.setLineDash([5, 3]);
                        ctx.strokeRect(fieldAbsX, fieldAbsY, fieldW, fieldH);
                        ctx.setLineDash([]);

                        // Fill with semi-transparent green
                        ctx.fillStyle = 'rgba(40, 167, 69, 0.15)';
                        ctx.fillRect(fieldAbsX, fieldAbsY, fieldW, fieldH);

                        // Draw label
                        ctx.fillStyle = '#155724';
                        ctx.font = '10px Arial';
                        const fieldLabel = field.jsonpath || `field ${fieldIndex + 1}`;
                        ctx.fillText(fieldLabel, fieldAbsX + 3, fieldAbsY + 12);

                        // Draw resize handles if hovered
                        if (isLoopFieldHovered) {
                            drawResizeHandles(ctx, x + field.x, y + field.y, field.width, field.height);
                        }
                    });
                }
            }

            // Draw resize handles if this field is hovered
            if (isHovered) {
                drawResizeHandles(ctx, x, y, width, height);
            }
        });
    };

    const drawSelection = (ctx, selection) => {
        ctx.strokeStyle = '#28a745';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.strokeRect(selection.x, selection.y, selection.width, selection.height);
        ctx.setLineDash([]);

        ctx.fillStyle = 'rgba(40, 167, 69, 0.1)';
        ctx.fillRect(selection.x, selection.y, selection.width, selection.height);
    };

    // Helper: Get resize handle at position (8 handles: 4 corners + 4 edges)
    const getResizeHandle = (x, y, fieldX, fieldY, fieldW, fieldH, handleSize = 8) => {
        const corners = [
            { name: 'nw', x: fieldX, y: fieldY, cursor: 'nw-resize' },
            { name: 'ne', x: fieldX + fieldW, y: fieldY, cursor: 'ne-resize' },
            { name: 'sw', x: fieldX, y: fieldY + fieldH, cursor: 'sw-resize' },
            { name: 'se', x: fieldX + fieldW, y: fieldY + fieldH, cursor: 'se-resize' },
            { name: 'n', x: fieldX + fieldW / 2, y: fieldY, cursor: 'n-resize' },
            { name: 's', x: fieldX + fieldW / 2, y: fieldY + fieldH, cursor: 's-resize' },
            { name: 'w', x: fieldX, y: fieldY + fieldH / 2, cursor: 'w-resize' },
            { name: 'e', x: fieldX + fieldW, y: fieldY + fieldH / 2, cursor: 'e-resize' }
        ];

        for (const corner of corners) {
            const dx = x - corner.x;
            const dy = y - corner.y;
            if (Math.abs(dx) <= handleSize && Math.abs(dy) <= handleSize) {
                return { handle: corner.name, cursor: corner.cursor };
            }
        }

        return null;
    };

    // Helper: Check if point is inside field
    const isPointInField = (x, y, fieldX, fieldY, fieldW, fieldH) => {
        return x >= fieldX && x <= fieldX + fieldW && y >= fieldY && y <= fieldY + fieldH;
    };

    // Helper: Find field at position (returns { type, index, loopIndex, handle })
    const findFieldAtPosition = (x, y, pageIndex) => {
        // Check loop fields first (they're rendered on top)
        for (let i = 0; i < fieldMappings.length; i++) {
            const mapping = fieldMappings[i];

            if (mapping.type === 'loop') {
                // Check main page
                if (mapping.page === pageIndex && mapping.loop_fields && mapping.loop_fields.length > 0) {
                    const loopArea = mapping.area;

                    for (let j = 0; j < mapping.loop_fields.length; j++) {
                        const field = mapping.loop_fields[j];
                        const fieldX = loopArea.x + field.x;
                        const fieldY = loopArea.y + field.y;
                        const fieldW = field.width;
                        const fieldH = field.height;

                        // Check resize handles first
                        const handle = getResizeHandle(x, y, fieldX, fieldY, fieldW, fieldH);
                        if (handle) {
                            return { type: 'loop_field', index: i, fieldIndex: j, ...handle };
                        }

                        // Check if inside field
                        if (isPointInField(x, y, fieldX, fieldY, fieldW, fieldH)) {
                            return { type: 'loop_field', index: i, fieldIndex: j, cursor: 'grab' };
                        }
                    }
                }

                // Check loop pages
                if (mapping.loop_pages) {
                    for (const lp of mapping.loop_pages) {
                        if (lp.page === pageIndex && mapping.loop_fields && mapping.loop_fields.length > 0) {
                            for (let j = 0; j < mapping.loop_fields.length; j++) {
                                const field = mapping.loop_fields[j];
                                const fieldX = lp.area.x + field.x;
                                const fieldY = lp.area.y + field.y;
                                const fieldW = field.width;
                                const fieldH = field.height;

                                const handle = getResizeHandle(x, y, fieldX, fieldY, fieldW, fieldH);
                                if (handle) {
                                    return { type: 'loop_field', index: i, fieldIndex: j, ...handle };
                                }

                                if (isPointInField(x, y, fieldX, fieldY, fieldW, fieldH)) {
                                    return { type: 'loop_field', index: i, fieldIndex: j, cursor: 'grab' };
                                }
                            }
                        }
                    }
                }
            }
        }

        // Check regular fields and loop containers
        const pageMappings = fieldMappings.filter(m => m.page === pageIndex);
        const loopPageMappings = fieldMappings
            .filter(m => m.type === 'loop' && m.loop_pages && m.loop_pages.length > 0)
            .flatMap(m => m.loop_pages
                .filter(lp => lp.page === pageIndex)
                .map(lp => ({ ...m, area: lp.area, isLoopPage: true }))
            );

        const allMappings = [...pageMappings, ...loopPageMappings];

        for (let i = allMappings.length - 1; i >= 0; i--) {
            const mapping = allMappings[i];
            const { x: fieldX, y: fieldY, width: fieldW, height: fieldH } = mapping.area;

            // Check resize handles
            const handle = getResizeHandle(x, y, fieldX, fieldY, fieldW, fieldH);
            if (handle) {
                const originalIndex = fieldMappings.findIndex(m => m === mapping);
                return { type: 'field', index: originalIndex, ...handle };
            }

            // Check if inside field
            if (isPointInField(x, y, fieldX, fieldY, fieldW, fieldH)) {
                const originalIndex = fieldMappings.findIndex(m => m === mapping);
                return { type: 'field', index: originalIndex, cursor: 'grab' };
            }
        }

        return null;
    };

    // Draw resize handles on field
    const drawResizeHandles = (ctx, x, y, width, height) => {
        const handleSize = 6;
        const handles = [
            { x: x, y: y }, // nw
            { x: x + width, y: y }, // ne
            { x: x, y: y + height }, // sw
            { x: x + width, y: y + height }, // se
            { x: x + width / 2, y: y }, // n
            { x: x + width / 2, y: y + height }, // s
            { x: x, y: y + height / 2 }, // w
            { x: x + width, y: y + height / 2 } // e
        ];

        handles.forEach(handle => {
            ctx.fillStyle = '#fff';
            ctx.strokeStyle = '#0dcaf0';
            ctx.lineWidth = 2;
            ctx.fillRect(
                handle.x * scale - handleSize / 2,
                handle.y * scale - handleSize / 2,
                handleSize,
                handleSize
            );
            ctx.strokeRect(
                handle.x * scale - handleSize / 2,
                handle.y * scale - handleSize / 2,
                handleSize,
                handleSize
            );
        });
    };

    const handleCanvasMouseDown = (e) => {
        const canvas = canvasRef.current;
        const rect = canvas.getBoundingClientRect();

        // Convert mouse coordinates to canvas coordinates
        // Account for both canvas internal scale and CSS scaling
        const canvasX = (e.clientX - rect.left) * (canvas.width / rect.width);
        const canvasY = (e.clientY - rect.top) * (canvas.height / rect.height);

        // Convert to PDF coordinates (unscaled)
        const x = canvasX / scale;
        const y = canvasY / scale;

        const pageIndex = currentPage - 1;

        // Check if clicking on an existing field
        const fieldAtPos = findFieldAtPosition(x, y, pageIndex);

        if (fieldAtPos) {
            // Start dragging or resizing
            if (fieldAtPos.handle) {
                // Resize mode
                setDraggingField({
                    ...fieldAtPos,
                    startX: x,
                    startY: y,
                    mode: 'resize'
                });
            } else {
                // Move mode
                setDraggingField({
                    ...fieldAtPos,
                    startX: x,
                    startY: y,
                    mode: 'move'
                });
                setCursorStyle('grabbing');
            }
        } else {
            // Start new selection
            setSelectionStart({ x, y });
            setCurrentSelection({ x, y, width: 0, height: 0 });
            setIsSelecting(true);
        }
    };

    const handleCanvasMouseMove = (e) => {
        const canvas = canvasRef.current;
        const rect = canvas.getBoundingClientRect();

        // Convert mouse coordinates to canvas coordinates
        const canvasX = (e.clientX - rect.left) * (canvas.width / rect.width);
        const canvasY = (e.clientY - rect.top) * (canvas.height / rect.height);

        // Convert to PDF coordinates (unscaled)
        const currentX = canvasX / scale;
        const currentY = canvasY / scale;

        const pageIndex = currentPage - 1;

        // Handle dragging/resizing
        if (draggingField) {
            const dx = currentX - draggingField.startX;
            const dy = currentY - draggingField.startY;

            const updatedMappings = [...fieldMappings];

            if (draggingField.type === 'field') {
                // Drag/resize regular field or loop container
                const field = updatedMappings[draggingField.index];

                if (draggingField.mode === 'move') {
                    // Move field (rounded to integers)
                    field.area = {
                        ...field.area,
                        x: Math.round(Math.max(0, field.area.x + dx)),
                        y: Math.round(Math.max(0, field.area.y + dy))
                    };
                    draggingField.startX = currentX;
                    draggingField.startY = currentY;
                } else if (draggingField.mode === 'resize') {
                    // Resize field based on handle (rounded to integers)
                    const handle = draggingField.handle;
                    const area = { ...field.area };

                    if (handle.includes('n')) {
                        const newY = Math.round(area.y + dy);
                        const newHeight = Math.round(area.height - dy);
                        if (newHeight > 10) {
                            area.y = newY;
                            area.height = newHeight;
                            draggingField.startY = currentY;
                        }
                    }
                    if (handle.includes('s')) {
                        area.height = Math.round(Math.max(10, area.height + dy));
                        draggingField.startY = currentY;
                    }
                    if (handle.includes('w')) {
                        const newX = Math.round(area.x + dx);
                        const newWidth = Math.round(area.width - dx);
                        if (newWidth > 10) {
                            area.x = newX;
                            area.width = newWidth;
                            draggingField.startX = currentX;
                        }
                    }
                    if (handle.includes('e')) {
                        area.width = Math.round(Math.max(10, area.width + dx));
                        draggingField.startX = currentX;
                    }

                    field.area = area;
                }

                setFieldMappings(updatedMappings);
            } else if (draggingField.type === 'loop_field') {
                // Drag/resize loop field
                const loopMapping = updatedMappings[draggingField.index];
                const field = loopMapping.loop_fields[draggingField.fieldIndex];

                if (draggingField.mode === 'move') {
                    // Move loop field (relative coordinates, rounded to integers)
                    field.x = Math.round(Math.max(0, field.x + dx));
                    field.y = Math.round(Math.max(0, field.y + dy));
                    draggingField.startX = currentX;
                    draggingField.startY = currentY;
                } else if (draggingField.mode === 'resize') {
                    // Resize loop field (rounded to integers)
                    const handle = draggingField.handle;

                    if (handle.includes('n')) {
                        const newY = Math.round(field.y + dy);
                        const newHeight = Math.round(field.height - dy);
                        if (newHeight > 10) {
                            field.y = newY;
                            field.height = newHeight;
                            draggingField.startY = currentY;
                        }
                    }
                    if (handle.includes('s')) {
                        field.height = Math.round(Math.max(10, field.height + dy));
                        draggingField.startY = currentY;
                    }
                    if (handle.includes('w')) {
                        const newX = Math.round(field.x + dx);
                        const newWidth = Math.round(field.width - dx);
                        if (newWidth > 10) {
                            field.x = newX;
                            field.width = newWidth;
                            draggingField.startX = currentX;
                        }
                    }
                    if (handle.includes('e')) {
                        field.width = Math.round(Math.max(10, field.width + dx));
                        draggingField.startX = currentX;
                    }
                }

                setFieldMappings(updatedMappings);
            }

            return;
        }

        // Handle new selection drawing
        if (isSelecting && selectionStart) {
            const width = currentX - selectionStart.x;
            const height = currentY - selectionStart.y;

            setCurrentSelection({
                x: width >= 0 ? selectionStart.x : currentX,
                y: height >= 0 ? selectionStart.y : currentY,
                width: Math.abs(width),
                height: Math.abs(height)
            });

            return;
        }

        // Handle hover detection (when not dragging or selecting)
        const fieldAtPos = findFieldAtPosition(currentX, currentY, pageIndex);

        if (fieldAtPos) {
            setHoveredField(fieldAtPos);
            setCursorStyle(fieldAtPos.cursor);
        } else {
            setHoveredField(null);
            setCursorStyle(isAddingLoopField || isAddingLoopPage ? 'crosshair' : 'pointer');
        }
    };

    const handleCanvasMouseUp = () => {
        // Handle end of drag/resize
        if (draggingField) {
            setDraggingField(null);
            setCursorStyle('pointer');
            setSuccess(draggingField.mode === 'move' ? 'Campo spostato!' : 'Campo ridimensionato!');
            setTimeout(() => setSuccess(null), 1500);
            return;
        }

        if (!isSelecting || !currentSelection) return;

        // If selection is too small, ignore it
        if (currentSelection.width < 10 || currentSelection.height < 10) {
            setIsSelecting(false);
            setCurrentSelection(null);
            setSelectionStart(null);
            // Restore canvas without selection
            if (canvasRef.current && canvasSnapshotRef.current) {
                const ctx = canvasRef.current.getContext('2d');
                ctx.putImageData(canvasSnapshotRef.current, 0, 0);
            }
            return;
        }

        // Check if we're adding a loop page
        if (isAddingLoopPage && currentLoopIndex !== null) {
            const selX = Math.round(currentSelection.x);
            const selY = Math.round(currentSelection.y);
            const selW = Math.round(currentSelection.width);
            const selH = Math.round(currentSelection.height);

            // Ask for number of rows in this page
            const rowsInput = window.prompt(
                `Quante righe del loop ci sono in questa pagina (pagina ${currentPage})?\n\n` +
                `Suggerimento: Calcola in base all'altezza disponibile.\n` +
                `- Altezza area selezionata: ${selH}px\n` +
                `- Altezza singola riga: ${fieldMappings[currentLoopIndex].area.height}px\n` +
                `- Righe stimate: ${Math.floor(selH / fieldMappings[currentLoopIndex].area.height)}`,
                Math.floor(selH / fieldMappings[currentLoopIndex].area.height).toString()
            );

            if (!rowsInput) {
                // User cancelled
                setIsSelecting(false);
                setSelectionStart(null);
                setCurrentSelection(null);
                setIsAddingLoopPage(false);
                setError('Aggiunta pagina annullata');
                setTimeout(() => setError(null), 2000);
                return;
            }

            const rows = parseInt(rowsInput);
            if (isNaN(rows) || rows < 1) {
                setIsSelecting(false);
                setSelectionStart(null);
                setCurrentSelection(null);
                setIsAddingLoopPage(false);
                setError('Numero di righe non valido');
                setTimeout(() => setError(null), 2000);
                return;
            }

            const updatedMappings = [...fieldMappings];
            const loopMapping = updatedMappings[currentLoopIndex];

            if (!loopMapping.loop_pages) {
                loopMapping.loop_pages = [];
            }

            loopMapping.loop_pages.push({
                page: currentPage - 1,
                area: { x: selX, y: selY, width: selW, height: selH },
                rows: rows
            });

            setFieldMappings(updatedMappings);
            setIsSelecting(false);
            setSelectionStart(null);
            setCurrentSelection(null);
            setIsAddingLoopPage(false);
            setSuccess(`Pagina ${currentPage} aggiunta al loop con ${rows} righe!`);
            setTimeout(() => setSuccess(null), 2000);
            return;
        }

        // Check if we're adding a loop field
        if (isAddingLoopField && currentLoopIndex !== null) {
            const loopMapping = fieldMappings[currentLoopIndex];

            // Get loop area (could be from main page or loop_pages)
            let loopArea = loopMapping.area;
            if (loopMapping.page !== currentPage - 1 && loopMapping.loop_pages) {
                const loopPage = loopMapping.loop_pages.find(lp => lp.page === currentPage - 1);
                if (loopPage) {
                    loopArea = loopPage.area;
                }
            }

            // Verify selection is inside loop area
            const selX = Math.round(currentSelection.x);
            const selY = Math.round(currentSelection.y);
            const selW = Math.round(currentSelection.width);
            const selH = Math.round(currentSelection.height);

            if (selX < loopArea.x || selY < loopArea.y ||
                selX + selW > loopArea.x + loopArea.width ||
                selY + selH > loopArea.y + loopArea.height) {
                setError('Il campo deve essere dentro l\'area del loop! Area loop: x=' + loopArea.x + ', y=' + loopArea.y + ', w=' + loopArea.width + ', h=' + loopArea.height);
                setIsSelecting(false);
                setSelectionStart(null);
                setCurrentSelection(null);
                setTimeout(() => setError(null), 3000);
                return;
            }

            // Convert to relative coordinates
            setNewLoopField({
                jsonpath: '',
                x: selX - loopArea.x,
                y: selY - loopArea.y,
                width: selW,
                height: selH
            });

            setIsSelecting(false);
            setSelectionStart(null);
            // Keep currentSelection visible to show where field was drawn
            // (will be cleared when modal is closed)

            setSuccess('Campo disegnato! Ora inserisci il JSONPath.');
            setTimeout(() => setSuccess(null), 2000);
        } else {
            // Normal field selection
            setNewField({
                ...newField,
                x: Math.round(currentSelection.x),
                y: Math.round(currentSelection.y),
                width: Math.round(currentSelection.width),
                height: Math.round(currentSelection.height),
                page: currentPage - 1
            });
            setShowNewFieldForm(true);

            // Keep selection visible until form is submitted/cancelled
            setIsSelecting(false);
            setSelectionStart(null);
        }
    };

    const handleAddField = () => {
        setShowNewFieldForm(true);
    };

    const handleSaveNewField = (e) => {
        e.preventDefault();

        if (!newField.jsonpath) {
            setError('JSONPath è obbligatorio');
            return;
        }

        const newMapping = {
            area: {
                x: parseInt(newField.x),
                y: parseInt(newField.y),
                width: parseInt(newField.width),
                height: parseInt(newField.height)
            },
            jsonpath: newField.jsonpath,
            type: newField.type,
            page: parseInt(newField.page)
        };

        setFieldMappings([...fieldMappings, newMapping]);
        setShowNewFieldForm(false);
        setCurrentSelection(null);
        setNewField({
            jsonpath: '',
            type: 'text',
            x: 100,
            y: 100,
            width: 200,
            height: 20,
            page: 0
        });
        setSuccess('Campo aggiunto!');
        setTimeout(() => setSuccess(null), 2000);

        // PDF will re-render automatically via effect when fieldMappings changes
    };

    const handleCancelNewField = () => {
        setShowNewFieldForm(false);
        setCurrentSelection(null);
        setNewField({
            jsonpath: '',
            type: 'text',
            x: 100,
            y: 100,
            width: 200,
            height: 20,
            page: 0
        });

        // Restore canvas without selection
        if (canvasRef.current && canvasSnapshotRef.current) {
            const ctx = canvasRef.current.getContext('2d');
            ctx.putImageData(canvasSnapshotRef.current, 0, 0);
        }
    };

    const handleRemoveField = (index) => {
        setFieldMappings(fieldMappings.filter((_, i) => i !== index));
    };

    // Loop fields management
    const openLoopFieldsModal = (mapping, index) => {
        setCurrentLoopIndex(index);
        setIsAddingLoopField(true);
        setShowLoopFieldsModal(true);
        // Navigate to the page where the loop is
        setCurrentPage(mapping.page + 1);
    };

    const getLoopItemExample = (loopMapping) => {
        if (!loopMapping || !template?.variables_schema) {
            return {};
        }

        // Extract array from schema
        const arrayPath = loopMapping.jsonpath; // es: "$.designazioni"
        const keys = arrayPath.replace('$.', '').split('.');

        let current = template.variables_schema;
        for (const key of keys) {
            current = current?.[key];
        }

        // Return first item of array (or empty object)
        if (Array.isArray(current) && current.length > 0) {
            return current[0];
        }

        return {};
    };

    const handleAddLoopField = () => {
        if (!newLoopField.jsonpath) {
            setError('JSONPath è obbligatorio');
            return;
        }

        const updatedMappings = [...fieldMappings];
        const loopMapping = updatedMappings[currentLoopIndex];

        if (!loopMapping.loop_fields) {
            loopMapping.loop_fields = [];
        }

        loopMapping.loop_fields.push({
            jsonpath: newLoopField.jsonpath,
            x: parseInt(newLoopField.x) || 0,
            y: parseInt(newLoopField.y) || 0,
            width: parseInt(newLoopField.width) || 100,
            height: parseInt(newLoopField.height) || 20
        });

        setFieldMappings(updatedMappings);
        setNewLoopField({ jsonpath: '', x: 0, y: 0, width: 100, height: 20 });
        setCurrentSelection(null);
        setError(null);
        setSuccess('Campo loop aggiunto!');
        setTimeout(() => setSuccess(null), 2000);
    };

    const handleRemoveLoopField = (fieldIndex) => {
        const updatedMappings = [...fieldMappings];
        const loopMapping = updatedMappings[currentLoopIndex];

        if (loopMapping.loop_fields) {
            loopMapping.loop_fields = loopMapping.loop_fields.filter((_, i) => i !== fieldIndex);
        }

        setFieldMappings(updatedMappings);
    };

    const handleSave = async () => {
        if (!selectedTemplateId) {
            setError('Seleziona un template prima di salvare');
            return;
        }

        try {
            setLoading(true);
            setError(null);

            await client.put(`/api/documents/templates/${selectedTemplateId}/editor/`, {
                field_mappings: fieldMappings
            });

            setSuccess('Template salvato con successo!');
            setTimeout(() => setSuccess(null), 3000);
        } catch (err) {
            setError(`Errore salvataggio: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    const handleCreateTemplate = async (e) => {
        e.preventDefault();

        if (!newTemplate.name || !newTemplate.file) {
            setError('Nome e file PDF sono obbligatori');
            return;
        }

        try {
            setLoading(true);
            setError(null);

            // Upload file using FormData
            const formData = new FormData();
            formData.append('name', newTemplate.name);
            formData.append('template_type', newTemplate.template_type);
            formData.append('description', newTemplate.description);
            formData.append('template_file', newTemplate.file);
            formData.append('is_active', 'true');

            const created = await client.upload('/api/documents/templates/', formData);

            setSuccess('Template creato con successo!');
            setShowNewTemplateForm(false);
            setNewTemplate({
                name: '',
                template_type: templateTypes.length > 0 ? templateTypes[0].id : '',
                description: '',
                file: null
            });

            // Reload templates and select new one
            await loadTemplates();
            setSelectedTemplateId(created.id);

        } catch (err) {
            setError(`Errore creazione template: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteTemplate = async () => {
        if (!selectedTemplateId) return;

        if (!window.confirm(`Sei sicuro di voler eliminare il template "${template?.name}"?`)) {
            return;
        }

        try {
            setLoading(true);
            setError(null);

            await client.delete(`/api/documents/templates/${selectedTemplateId}/`);

            setSuccess('Template eliminato!');
            setTimeout(() => setSuccess(null), 3000);

            // Reload templates
            setSelectedTemplateId(null);
            setTemplate(null);
            await loadTemplates();

        } catch (err) {
            setError(`Errore eliminazione: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    if (loading && !template && templates.length === 0) {
        return <div className="template-editor-loading">Caricamento template...</div>;
    }

    if (templates.length === 0 && !loading) {
        return (
            <div className="template-editor">
                <div className="alert alert-warning">
                    <h4>Nessun Template Disponibile</h4>
                    <p>Non ci sono template configurati nel sistema.</p>
                    <p>Crea prima un template dal pannello admin Django oppure tramite API.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="template-editor">
            <div className="template-editor-header">
                <div>
                    <h2>Editor Template PDF</h2>
                    {templates.length > 0 && (
                        <div className="template-selector">
                            <label htmlFor="template-select">Seleziona Template: </label>
                            <select
                                id="template-select"
                                value={selectedTemplateId || ''}
                                onChange={(e) => setSelectedTemplateId(parseInt(e.target.value))}
                                className="form-control"
                                style={{ display: 'inline-block', width: 'auto', marginLeft: '10px' }}
                            >
                                {templates.map(t => (
                                    <option key={t.id} value={t.id}>
                                        {t.name} ({t.template_type_details?.name || 'N/A'})
                                    </option>
                                ))}
                            </select>
                        </div>
                    )}
                </div>
                <div style={{ display: 'flex', gap: '10px' }}>
                    <button
                        onClick={() => setShowNewTemplateForm(true)}
                        className="btn btn-primary"
                    >
                        + Nuovo Template
                    </button>
                    {selectedTemplateId && (
                        <>
                            <button
                                onClick={handleSave}
                                disabled={loading}
                                className="btn btn-success"
                            >
                                {loading ? 'Salvataggio...' : 'Salva Configurazione'}
                            </button>
                            <button
                                onClick={handleDeleteTemplate}
                                disabled={loading}
                                className="btn btn-danger"
                            >
                                Elimina
                            </button>
                        </>
                    )}
                </div>
            </div>

            {/* Form Nuovo Template */}
            {showNewTemplateForm && (
                <div className="new-template-form">
                    <div className="card">
                        <div className="card-header">
                            <h3>Nuovo Template PDF</h3>
                        </div>
                        <div className="card-body">
                            <form onSubmit={handleCreateTemplate}>
                                <div className="form-group">
                                    <label>Nome Template *</label>
                                    <input
                                        type="text"
                                        className="form-control"
                                        value={newTemplate.name}
                                        onChange={(e) => setNewTemplate({...newTemplate, name: e.target.value})}
                                        placeholder="es: individuale"
                                        required
                                    />
                                </div>

                                <div className="form-group">
                                    <label>Tipo Template *</label>
                                    <select
                                        className="form-control"
                                        value={newTemplate.template_type}
                                        onChange={(e) => setNewTemplate({...newTemplate, template_type: parseInt(e.target.value)})}
                                        required
                                    >
                                        <option value="">-- Seleziona tipo --</option>
                                        {templateTypes.map(tt => (
                                            <option key={tt.id} value={tt.id}>
                                                {tt.name}
                                            </option>
                                        ))}
                                    </select>
                                    {newTemplate.template_type && templateTypes.length > 0 && (
                                        <small className="text-muted d-block mt-1">
                                            {templateTypes.find(tt => tt.id === newTemplate.template_type)?.description}
                                        </small>
                                    )}
                                </div>

                                <div className="form-group">
                                    <label>Descrizione</label>
                                    <textarea
                                        className="form-control"
                                        value={newTemplate.description}
                                        onChange={(e) => setNewTemplate({...newTemplate, description: e.target.value})}
                                        placeholder="Descrizione template..."
                                        rows="3"
                                    />
                                </div>

                                <div className="form-group">
                                    <label>File PDF Template *</label>
                                    <input
                                        type="file"
                                        className="form-control"
                                        accept=".pdf"
                                        onChange={(e) => setNewTemplate({...newTemplate, file: e.target.files[0]})}
                                        required
                                    />
                                    <small className="text-muted">
                                        Carica il file PDF base su cui configurare i campi
                                    </small>
                                </div>

                                <div className="form-actions">
                                    <button type="submit" className="btn btn-success" disabled={loading}>
                                        Crea Template
                                    </button>
                                    <button
                                        type="button"
                                        className="btn btn-secondary"
                                        onClick={() => {
                                            setShowNewTemplateForm(false);
                                            setNewTemplate({
                                                name: '',
                                                template_type: templateTypes.length > 0 ? templateTypes[0].id : '',
                                                description: '',
                                                file: null
                                            });
                                        }}
                                    >
                                        Annulla
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            )}

            {/* Form Nuovo Campo */}
            {showNewFieldForm && (
                <div className="new-template-form">
                    <div className="card">
                        <div className="card-header">
                            <h3>Aggiungi Campo</h3>
                        </div>
                        <div className="card-body">
                            <form onSubmit={handleSaveNewField}>
                                <div className="form-group">
                                    <label>
                                        JSONPath *
                                        <button
                                            type="button"
                                            onClick={() => setShowLoopGuide(true)}
                                            style={{
                                                marginLeft: '10px',
                                                fontSize: '0.9em',
                                                background: 'none',
                                                border: 'none',
                                                color: '#0d6efd',
                                                cursor: 'pointer',
                                                textDecoration: 'underline'
                                            }}
                                        >
                                            📖 Guida Loop & JSONPath
                                        </button>
                                    </label>
                                    <JSONPathAutocomplete
                                        value={newField.jsonpath}
                                        onChange={(value) => setNewField({...newField, jsonpath: value})}
                                        exampleData={template?.variables_schema || {}}
                                        placeholder='es: $.delegato.cognome + " " + $.delegato.nome'
                                        required
                                    />
                                    <small className="text-muted">
                                        <strong>Semplice:</strong> <code>$.delegato.cognome</code><br/>
                                        <strong>Concatenato:</strong> <code>$.cognome + " " + $.nome</code><br/>
                                        <strong>Loop:</strong> <code>$.designazioni</code> (array)
                                    </small>
                                </div>

                                <div className="form-group">
                                    <label>Tipo Campo *</label>
                                    <select
                                        className="form-control"
                                        value={newField.type}
                                        onChange={(e) => setNewField({...newField, type: e.target.value})}
                                    >
                                        <option value="text">Text (campo singolo)</option>
                                        <option value="loop">Loop (lista elementi)</option>
                                    </select>
                                </div>

                                {newField.type === 'loop' && (
                                    <div className="alert alert-info mt-3">
                                        <h6 className="alert-heading">
                                            📋 Come funziona il Loop
                                        </h6>
                                        <ol className="mb-0 ps-3">
                                            <li>
                                                <strong>Seleziona solo la PRIMA riga</strong> della tabella sul PDF
                                            </li>
                                            <li>
                                                Le righe successive verranno generate <strong>automaticamente</strong>
                                            </li>
                                            <li>
                                                Ogni riga avrà la <strong>stessa altezza</strong> della prima
                                            </li>
                                            <li>
                                                Il sistema trasla automaticamente ogni riga verso il basso
                                            </li>
                                            <li>
                                                Dopo aver creato il loop, usa il pulsante <strong>"📝 Campi"</strong> per definire le colonne
                                            </li>
                                            <li>
                                                Se il loop continua su più pagine, usa <strong>"📄 +Pagina"</strong> per aggiungerle
                                            </li>
                                        </ol>
                                        <hr className="my-2" />
                                        <p className="mb-0 small">
                                            <strong>Esempio:</strong> Se la prima riga è a Y=150 con altezza 20px,
                                            la seconda sarà a Y=170, la terza a Y=190, ecc.
                                        </p>
                                    </div>
                                )}

                                <div className="grid-2-col" style={{ gap: '15px' }}>
                                    <div className="form-group">
                                        <label>X (coordinate orizzontale)</label>
                                        <input
                                            type="number"
                                            className="form-control"
                                            value={newField.x}
                                            onChange={(e) => setNewField({...newField, x: e.target.value})}
                                            min="0"
                                            required
                                        />
                                    </div>

                                    <div className="form-group">
                                        <label>Y (coordinate verticale)</label>
                                        <input
                                            type="number"
                                            className="form-control"
                                            value={newField.y}
                                            onChange={(e) => setNewField({...newField, y: e.target.value})}
                                            min="0"
                                            required
                                        />
                                    </div>

                                    <div className="form-group">
                                        <label>Larghezza (Width)</label>
                                        <input
                                            type="number"
                                            className="form-control"
                                            value={newField.width}
                                            onChange={(e) => setNewField({...newField, width: e.target.value})}
                                            min="1"
                                            required
                                        />
                                    </div>

                                    <div className="form-group">
                                        <label>Altezza (Height)</label>
                                        <input
                                            type="number"
                                            className="form-control"
                                            value={newField.height}
                                            onChange={(e) => setNewField({...newField, height: e.target.value})}
                                            min="1"
                                            required
                                        />
                                    </div>
                                </div>

                                <div className="form-group">
                                    <label>Pagina</label>
                                    <input
                                        type="number"
                                        className="form-control"
                                        value={newField.page}
                                        onChange={(e) => setNewField({...newField, page: parseInt(e.target.value) || 0})}
                                        min="0"
                                        max={numPages - 1}
                                        disabled
                                    />
                                    <small className="text-muted">
                                        Pagina corrente: {currentPage}. Il campo verrà creato sulla pagina visualizzata.
                                    </small>
                                </div>

                                <div className="form-actions">
                                    <button type="submit" className="btn btn-success">
                                        Aggiungi Campo
                                    </button>
                                    <button
                                        type="button"
                                        className="btn btn-secondary"
                                        onClick={handleCancelNewField}
                                    >
                                        Annulla
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            )}

            {error && (
                <div className="alert alert-danger">{error}</div>
            )}

            {success && (
                <div className="alert alert-success">{success}</div>
            )}

            <div className="template-editor-content">
                {/* PDF Interactive Canvas */}
                <div className="pdf-preview-section">
                    <div className="pdf-controls">
                        <h3>Editor Visuale PDF</h3>
                        {pdfDoc && (
                            <div className="pdf-navigation">
                                <button
                                    className="btn btn-secondary btn-sm"
                                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                                    disabled={currentPage === 1}
                                >
                                    ← Pagina precedente
                                </button>
                                <span className="page-indicator">
                                    Pagina {currentPage} di {numPages}
                                </span>
                                <button
                                    className="btn btn-secondary btn-sm"
                                    onClick={() => setCurrentPage(Math.min(numPages, currentPage + 1))}
                                    disabled={currentPage === numPages}
                                >
                                    Pagina successiva →
                                </button>
                                <div className="zoom-controls">
                                    <button
                                        className="btn btn-secondary btn-sm"
                                        onClick={() => setScale(Math.max(0.5, scale - 0.1))}
                                    >
                                        −
                                    </button>
                                    <span className="zoom-level">{Math.round(scale * 100)}%</span>
                                    <button
                                        className="btn btn-secondary btn-sm"
                                        onClick={() => setScale(Math.min(2.0, scale + 0.1))}
                                    >
                                        +
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>

                    {pdfDoc ? (
                        <div className="pdf-canvas-container">
                            <canvas
                                ref={canvasRef}
                                onMouseDown={handleCanvasMouseDown}
                                onMouseMove={handleCanvasMouseMove}
                                onMouseUp={handleCanvasMouseUp}
                                style={{
                                    border: '1px solid #dee2e6',
                                    cursor: isSelecting ? 'crosshair' : draggingField?.mode === 'move' ? 'grabbing' : cursorStyle,
                                    display: 'block'
                                }}
                            />
                            <div className="pdf-instructions">
                                {isAddingLoopPage ? (
                                    <div className="alert alert-success">
                                        <strong>📄 Modalità: Aggiungi Pagina Loop</strong>
                                        <p className="mb-1">Disegna il rettangolo dove il loop continua in questa pagina. Le colonne saranno le stesse della prima pagina.</p>
                                        <p className="mb-0 small">Dopo aver disegnato l'area, ti verrà chiesto <strong>quante righe</strong> del loop ci sono in questa pagina.</p>
                                        <button
                                            className="btn btn-sm btn-secondary mt-2"
                                            onClick={() => {
                                                setIsAddingLoopPage(false);
                                                setCurrentLoopIndex(null);
                                            }}
                                        >
                                            Annulla
                                        </button>
                                    </div>
                                ) : isAddingLoopField ? (
                                    <div className="alert alert-info">
                                        <strong>🖱️ Modalità: Disegna Campo Loop</strong>
                                        <p className="mb-0">Disegna un rettangolo dentro l'area gialla del loop per aggiungere un campo.</p>
                                    </div>
                                ) : (
                                    <>
                                        <p><strong>💡 Istruzioni:</strong></p>
                                        <ul>
                                            <li>Clicca e trascina sul PDF per selezionare un'area</li>
                                            <li>Le aree blu sono campi di tipo "text"</li>
                                            <li>Le aree gialle sono campi di tipo "loop"</li>
                                            <li>Dopo la selezione, compila il form per definire il campo</li>
                                        </ul>
                                    </>
                                )}
                            </div>
                        </div>
                    ) : (
                        <div className="pdf-placeholder">
                            <p>📄 {template?.template_file_url ? 'Caricamento PDF...' : 'Nessun template selezionato'}</p>
                            {template?.template_file_url && (
                                <p className="text-muted">
                                    Se il caricamento non parte, verifica che il file PDF sia accessibile
                                </p>
                            )}
                        </div>
                    )}
                </div>

                {/* Field Mappings List */}
                <div className="field-mappings-section">
                    <div className="field-mappings-header">
                        <h3>Campi Configurati ({fieldMappings.length})</h3>
                        <button
                            onClick={handleAddField}
                            className="btn btn-primary btn-sm"
                        >
                            + Aggiungi Campo
                        </button>
                    </div>

                    {fieldMappings.length === 0 ? (
                        <div className="no-fields">
                            <p>Nessun campo configurato.</p>
                            <p className="text-muted">
                                Clicca "Aggiungi Campo" per iniziare.
                            </p>
                        </div>
                    ) : (
                        <table className="table table-striped">
                            <thead>
                                <tr>
                                    <th>JSONPath</th>
                                    <th>Tipo</th>
                                    <th>Posizione</th>
                                    <th>Dimensioni</th>
                                    <th>Azioni</th>
                                </tr>
                            </thead>
                            <tbody>
                                {fieldMappings.map((mapping, index) => (
                                    <tr key={index}>
                                        <td><code>{mapping.jsonpath}</code></td>
                                        <td>
                                            <span className={`badge ${mapping.type === 'loop' ? 'bg-warning' : 'bg-info'}`}>
                                                {mapping.type}
                                            </span>
                                            {mapping.type === 'loop' && (
                                                <>
                                                    <button
                                                        className="btn btn-sm btn-primary ms-2"
                                                        onClick={() => openLoopFieldsModal(mapping, index)}
                                                        title="Gestisci campi del loop"
                                                    >
                                                        📝 Campi ({mapping.loop_fields?.length || 0})
                                                    </button>
                                                    <button
                                                        className="btn btn-sm btn-success ms-1"
                                                        onClick={() => {
                                                            setCurrentLoopIndex(index);
                                                            setIsAddingLoopPage(true);
                                                            setSuccess('Vai alla pagina dove vuoi continuare il loop e disegna l\'area');
                                                        }}
                                                        title="Aggiungi il loop su un'altra pagina"
                                                    >
                                                        📄 +Pagina
                                                    </button>
                                                </>
                                            )}
                                        </td>
                                        <td>
                                            p:{mapping.page}, x:{mapping.area.x}, y:{mapping.area.y}
                                            {mapping.type === 'loop' && (
                                                <div className="badge bg-info ms-2" title="Righe in questa pagina">
                                                    {mapping.rows || 6}r
                                                </div>
                                            )}
                                            {mapping.loop_pages && mapping.loop_pages.length > 0 && (
                                                <div className="badge bg-success ms-2" title={`+${mapping.loop_pages.length} pagine aggiuntive (${mapping.loop_pages.map(lp => lp.rows || '?').join(', ')} righe)`}>
                                                    +{mapping.loop_pages.length}pag
                                                </div>
                                            )}
                                        </td>
                                        <td>{mapping.area.width}×{mapping.area.height}</td>
                                        <td>
                                            <button
                                                onClick={() => handleRemoveField(index)}
                                                className="btn btn-danger btn-sm"
                                            >
                                                Rimuovi
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>

            </div>

            <div className="template-editor-footer">
                <button
                    onClick={handleSave}
                    disabled={loading}
                    className="btn btn-success btn-lg"
                >
                    {loading ? 'Salvataggio...' : 'Salva Configurazione'}
                </button>
            </div>

            <div className="template-editor-help">
                <h4>💡 Come funziona l'Editor Visuale</h4>
                <ul>
                    <li><strong>Selezione Visuale:</strong> Clicca e trascina sul PDF per definire un'area campo</li>
                    <li><strong>JSONPath:</strong> Specifica da dove prendere i dati (es: <code>$.delegato.cognome</code>)</li>
                    <li><strong>Autocomplete:</strong> Digita <code>$.</code> per vedere i campi disponibili dal template</li>
                    <li><strong>Tipo text:</strong> Campo semplice, una riga di testo (overlay blu)</li>
                    <li><strong>Tipo loop:</strong> Lista di elementi ripetuti (overlay giallo)</li>
                    <li><strong>Navigazione:</strong> Usa i controlli per cambiare pagina e zoom</li>
                    <li><strong>Modifica:</strong> Rimuovi campi dalla tabella e ricrea con nuova selezione</li>
                </ul>

                <div className="alert alert-warning mt-3">
                    <h5 className="alert-heading">🔁 Loop: Come Configurare</h5>
                    <p className="mb-2">
                        Per i campi di tipo <strong>loop</strong> (tabelle con più righe):
                    </p>
                    <ol className="mb-2 ps-3">
                        <li>Seleziona <strong>solo la prima riga</strong> della tabella sul PDF</li>
                        <li>L'altezza selezionata definisce l'altezza di <strong>ogni</strong> riga</li>
                        <li>Le righe successive saranno automaticamente generate traslando verticalmente</li>
                        <li>Click su <strong>"📝 Campi"</strong> per definire le colonne (JSONPath di ogni campo)</li>
                        <li>Configura il numero di righe per la prima pagina nella tabella del modal</li>
                    </ol>
                    <hr className="my-2" />
                    <p className="mb-1"><strong>Loop Multi-Pagina (se il loop continua su più pagine):</strong></p>
                    <ol className="mb-0 ps-3">
                        <li>Click su <strong>"📄 +Pagina"</strong> accanto al loop</li>
                        <li>Vai alla pagina successiva e disegna l'area dove continua il loop</li>
                        <li>Inserisci quante righe ci sono in quella pagina</li>
                        <li>Ripeti per ogni pagina aggiuntiva</li>
                        <li>Ogni pagina può avere un <strong>numero di righe diverso</strong> (es: prima 6, altre 13, ultima 10)</li>
                    </ol>
                </div>

                <div className="alert alert-success mt-3">
                    <strong>✅ Editor Visuale Attivo</strong>
                    <p>Questo editor usa PDF.js per rendering interattivo. Puoi cliccare direttamente sul PDF per posizionare i campi!</p>
                    <p><strong>Workflow:</strong> Seleziona area → Compila form → Salva configurazione → Testa generazione PDF</p>
                </div>
            </div>

            {/* Markdown Guide Modal */}
            <MarkdownModal
                isOpen={showLoopGuide}
                onClose={() => setShowLoopGuide(false)}
                markdownUrl="/LOOP_GUIDE.md"
                title="📚 Guida Loop & JSONPath"
            />

            {/* Loop Fields Management Modal */}
            {showLoopFieldsModal && currentLoopIndex !== null && (
                <div className="modal show d-block" tabIndex="-1" style={{backgroundColor: 'rgba(0,0,0,0.5)'}}>
                    <div className="modal-dialog modal-lg">
                        <div className="modal-content">
                            <div className="modal-header">
                                <h5 className="modal-title">
                                    Gestisci Colonne Loop: <code>{fieldMappings[currentLoopIndex]?.jsonpath}</code>
                                </h5>
                                <button
                                    type="button"
                                    className="btn-close"
                                    onClick={() => {
                                        setShowLoopFieldsModal(false);
                                        setIsAddingLoopField(false);
                                        setCurrentLoopIndex(null);
                                        setNewLoopField({ jsonpath: '', x: 0, y: 0, width: 100, height: 20 });
                                        setCurrentSelection(null);
                                        setError(null);
                                    }}
                                ></button>
                            </div>

                            <div className="modal-body">
                                {/* Info box */}
                                <div className="alert alert-primary">
                                    <strong>🖱️ Disegna i campi sul PDF:</strong>
                                    <ol className="mb-0 mt-2">
                                        <li><strong>Disegna</strong> un rettangolo dentro l'area del loop evidenziata in giallo</li>
                                        <li>Le coordinate saranno <strong>relative</strong> al loop</li>
                                        <li>Dopo aver disegnato, inserisci il <strong>JSONPath</strong> del campo</li>
                                        <li>Ripeti per ogni campo (i campi possono essere su più righe)</li>
                                    </ol>
                                </div>

                                {/* Pagine Loop */}
                                {fieldMappings[currentLoopIndex]?.loop_pages && fieldMappings[currentLoopIndex].loop_pages.length > 0 && (
                                    <>
                                        <h6>📄 Pagine Aggiuntive ({fieldMappings[currentLoopIndex].loop_pages.length})</h6>
                                        <div className="alert alert-info mb-3">
                                            <strong>Loop Multi-Pagina:</strong> Il loop continua su più pagine con le stesse colonne ma posizioni e numero di righe diverse.
                                            <br/>
                                            <small>Modifica il numero di righe per ogni pagina nella colonna "Righe".</small>
                                        </div>
                                        <table className="table table-sm table-bordered">
                                            <thead>
                                                <tr>
                                                    <th>Pagina</th>
                                                    <th>Posizione</th>
                                                    <th>Dimensioni</th>
                                                    <th>Righe</th>
                                                    <th>Azioni</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <tr className="table-light">
                                                    <td><strong>Pagina {fieldMappings[currentLoopIndex].page + 1}</strong> (principale)</td>
                                                    <td>({fieldMappings[currentLoopIndex].area.x}, {fieldMappings[currentLoopIndex].area.y})</td>
                                                    <td>{fieldMappings[currentLoopIndex].area.width}×{fieldMappings[currentLoopIndex].area.height}</td>
                                                    <td>
                                                        <input
                                                            type="number"
                                                            className="form-control form-control-sm"
                                                            style={{ width: '80px' }}
                                                            value={fieldMappings[currentLoopIndex].rows || 6}
                                                            min="1"
                                                            onChange={(e) => {
                                                                const updatedMappings = [...fieldMappings];
                                                                updatedMappings[currentLoopIndex].rows = parseInt(e.target.value) || 1;
                                                                setFieldMappings(updatedMappings);
                                                            }}
                                                        />
                                                    </td>
                                                    <td>-</td>
                                                </tr>
                                                {fieldMappings[currentLoopIndex].loop_pages.map((lp, lpIndex) => (
                                                    <tr key={lpIndex}>
                                                        <td>Pagina {lp.page + 1}</td>
                                                        <td>({lp.area.x}, {lp.area.y})</td>
                                                        <td>{lp.area.width}×{lp.area.height}</td>
                                                        <td>
                                                            <input
                                                                type="number"
                                                                className="form-control form-control-sm"
                                                                style={{ width: '80px' }}
                                                                value={lp.rows || 1}
                                                                min="1"
                                                                onChange={(e) => {
                                                                    const updatedMappings = [...fieldMappings];
                                                                    const loopMapping = updatedMappings[currentLoopIndex];
                                                                    loopMapping.loop_pages[lpIndex].rows = parseInt(e.target.value) || 1;
                                                                    setFieldMappings(updatedMappings);
                                                                }}
                                                            />
                                                        </td>
                                                        <td>
                                                            <button
                                                                className="btn btn-sm btn-danger"
                                                                onClick={() => {
                                                                    const updatedMappings = [...fieldMappings];
                                                                    const loopMapping = updatedMappings[currentLoopIndex];
                                                                    loopMapping.loop_pages = loopMapping.loop_pages.filter((_, i) => i !== lpIndex);
                                                                    setFieldMappings(updatedMappings);
                                                                }}
                                                            >
                                                                Rimuovi
                                                            </button>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                        <hr />
                                    </>
                                )}

                                {/* Lista colonne esistenti */}
                                <h6>Campi Configurati ({fieldMappings[currentLoopIndex]?.loop_fields?.length || 0})</h6>
                                {!fieldMappings[currentLoopIndex]?.loop_fields || fieldMappings[currentLoopIndex].loop_fields.length === 0 ? (
                                    <div className="alert alert-warning">
                                        Nessun campo configurato. Disegna il primo campo sul PDF.
                                    </div>
                                ) : (
                                    <table className="table table-sm table-bordered">
                                        <thead>
                                            <tr>
                                                <th>JSONPath Relativo</th>
                                                <th>Posizione (x, y)</th>
                                                <th>Dimensioni</th>
                                                <th>Azioni</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {fieldMappings[currentLoopIndex].loop_fields.map((field, i) => (
                                                <tr key={i}>
                                                    <td><code>{field.jsonpath}</code></td>
                                                    <td>({field.x}, {field.y})</td>
                                                    <td>{field.width}×{field.height}</td>
                                                    <td>
                                                        <button
                                                            className="btn btn-sm btn-danger"
                                                            onClick={() => handleRemoveLoopField(i)}
                                                        >
                                                            Rimuovi
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                )}

                                {/* Form aggiungi campo */}
                                <hr />
                                <h6>Aggiungi Nuovo Campo</h6>
                                {newLoopField.width > 0 ? (
                                    <>
                                        <div className="alert alert-success">
                                            <strong>✅ Campo disegnato!</strong>
                                            <p className="mb-0">Posizione relativa: ({newLoopField.x}, {newLoopField.y}), Dimensioni: {newLoopField.width}×{newLoopField.height}</p>
                                        </div>
                                        <div className="mb-3">
                                            <label className="form-label">JSONPath Relativo *</label>
                                            <JSONPathAutocomplete
                                                value={newLoopField.jsonpath}
                                                onChange={(val) => setNewLoopField({...newLoopField, jsonpath: val})}
                                                exampleData={getLoopItemExample(fieldMappings[currentLoopIndex])}
                                                placeholder="es: $.sezione, $.effettivo_nome, ..."
                                            />
                                            <small className="text-muted d-block mt-1">
                                                Path relativo all'elemento dell'array (es: <code>$.sezione</code>, NON <code>$.designazioni[].sezione</code>)
                                            </small>
                                        </div>
                                        <div className="d-flex gap-2">
                                            <button
                                                className="btn btn-success"
                                                onClick={handleAddLoopField}
                                                disabled={!newLoopField.jsonpath}
                                            >
                                                ✓ Salva Campo
                                            </button>
                                            <button
                                                className="btn btn-secondary"
                                                onClick={() => {
                                                    setNewLoopField({ jsonpath: '', x: 0, y: 0, width: 100, height: 20 });
                                                    setCurrentSelection(null);
                                                }}
                                            >
                                                Annulla
                                            </button>
                                        </div>
                                    </>
                                ) : (
                                    <div className="alert alert-info">
                                        <strong>👉 Disegna un rettangolo sul PDF</strong>
                                        <p className="mb-0">Clicca e trascina sul PDF dentro l'area del loop (evidenziata in giallo) per definire la posizione del campo.</p>
                                    </div>
                                )}

                                {error && (
                                    <div className="alert alert-danger mt-3">
                                        {error}
                                    </div>
                                )}

                                {success && (
                                    <div className="alert alert-success mt-3">
                                        {success}
                                    </div>
                                )}
                            </div>

                            <div className="modal-footer">
                                <button
                                    type="button"
                                    className="btn btn-secondary"
                                    onClick={() => {
                                        setShowLoopFieldsModal(false);
                                        setIsAddingLoopField(false);
                                        setCurrentLoopIndex(null);
                                        setNewLoopField({ jsonpath: '', x: 0, y: 0, width: 100, height: 20 });
                                        setCurrentSelection(null);
                                        setError(null);
                                        setSuccess(null);
                                    }}
                                >
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

export default TemplateEditor;
