/**
 * Play a vintage SLR camera shutter sound using Web Audio API.
 */
function playCameraSound() {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const mirrorDur = 0.08;
        const mirrorBuf = ctx.createBuffer(1, ctx.sampleRate * mirrorDur, ctx.sampleRate);
        const d1 = mirrorBuf.getChannelData(0);
        for (let i = 0; i < d1.length; i++) {
            const t = i / ctx.sampleRate;
            d1[i] = Math.sin(t * 200 * Math.PI) * Math.exp(-t * 40) * 0.8
                + (Math.random() * 2 - 1) * Math.exp(-t * 30) * 0.3;
        }
        const curtainDur = 0.12;
        const curtainBuf = ctx.createBuffer(1, ctx.sampleRate * curtainDur, ctx.sampleRate);
        const d2 = curtainBuf.getChannelData(0);
        for (let i = 0; i < d2.length; i++) {
            const t = i / ctx.sampleRate;
            d2[i] = (Math.random() * 2 - 1) * Math.exp(-t * 25) * 0.5
                + Math.sin(t * 800 * Math.PI) * Math.exp(-t * 35) * 0.3;
        }
        const m = ctx.createBufferSource(); m.buffer = mirrorBuf;
        const mg = ctx.createGain(); mg.gain.value = 0.4;
        m.connect(mg); mg.connect(ctx.destination); m.start(ctx.currentTime);
        const c = ctx.createBufferSource(); c.buffer = curtainBuf;
        const cg = ctx.createGain(); cg.gain.value = 0.35;
        c.connect(cg); cg.connect(ctx.destination); c.start(ctx.currentTime + 0.1);
        setTimeout(() => ctx.close(), 800);
    } catch { /* audio not available */ }
}

function flashScreen() {
    const flash = document.createElement('div');
    flash.style.cssText =
        'position:fixed;top:0;left:0;width:100vw;height:100vh;z-index:999999;' +
        'background:#fff;opacity:0.9;pointer-events:none;';
    document.body.appendChild(flash);
    return flash;
}

/**
 * Export email preview HTML as PNG.
 *
 * @param {string} html - Full HTML document string
 * @param {object} options - { width: number } (default 700, use 375 for mobile)
 */
export async function exportPreviewPng(html, options = {}) {
    const width = options.width || 700;
    const htmlEl = document.documentElement;
    const savedTheme = htmlEl.getAttribute('data-theme');

    playCameraSound();
    const flash = flashScreen();

    // Remove night theme under the flash overlay
    if (savedTheme) {
        await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
        htmlEl.removeAttribute('data-theme');
    }

    try {
        // Parse the email HTML and rebuild it in a container in the current document.
        // We need to force all text colors via inline styles because html2canvas
        // computes styles from the parent document which may override them.
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');

        const container = document.createElement('div');
        container.style.cssText =
            `position:fixed;left:0;top:0;width:${width}px;z-index:999998;` +
            'background:#f5f5f5;margin:0;padding:0;overflow:visible;' +
            'font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;' +
            'color:#333333;';

        // Copy body styles and content
        const bodyStyle = doc.body.getAttribute('style') || '';
        if (bodyStyle) container.style.cssText += ';' + bodyStyle;
        while (doc.body.firstChild) {
            container.appendChild(doc.body.firstChild);
        }

        // Force white color on elements that need it (html2canvas loses computed
        // colors from inline styles on elements inside colored backgrounds).
        container.querySelectorAll('h1, h2, h3, p, span, div, a, td').forEach(el => {
            const style = el.getAttribute('style') || '';
            // If the element has explicit color:#FFFFFF or color:#fff or color:white, reinforce it
            if (/color\s*:\s*(#fff|#FFF|#ffffff|#FFFFFF|white|rgba\(255)/i.test(style)) {
                el.style.setProperty('color', el.style.color, 'important');
            }
        });

        document.body.appendChild(container);
        await new Promise(r => setTimeout(r, 400));

        const html2canvas = (await import('html2canvas')).default;
        const canvas = await html2canvas(container, {
            scale: 2,
            backgroundColor: '#f5f5f5',
            width: width,
            scrollX: 0,
            scrollY: 0,
            useCORS: true,
            logging: false,
        });

        document.body.removeChild(container);

        const link = document.createElement('a');
        link.download = `email-preview${width <= 400 ? '-mobile' : ''}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
    } catch (e) {
        console.error('Export PNG failed:', e);
        // Fallback: open in new tab
        const blob = new Blob([html], { type: 'text/html' });
        window.open(URL.createObjectURL(blob), '_blank');
    } finally {
        if (savedTheme) htmlEl.setAttribute('data-theme', savedTheme);
        flash.style.transition = 'opacity 0.4s ease-out';
        requestAnimationFrame(() => { flash.style.opacity = '0'; });
        setTimeout(() => flash.remove(), 500);
    }
}
