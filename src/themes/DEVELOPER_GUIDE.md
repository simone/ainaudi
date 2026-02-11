# 🛠️ Developer Guide - Night Theme

## Come scrivere codice theme-aware

### ❌ Da evitare: Inline Styles Hardcoded

```jsx
// ❌ BAD: Hardcoded colors
<div style={{ background: '#e7f3ff', color: '#084298' }}>
  Info message
</div>

// ❌ BAD: Non risponde al theme
<span style={{ backgroundColor: '#ffc107', color: '#000' }}>
  Pending
</span>
```

**Problema:** Questi colori NON cambiano in night mode!

### ✅ Soluzione 1: Utility Classes (RACCOMANDATO)

```jsx
// ✅ GOOD: Theme-aware utilities
<div className="bg-info-subtle border-info-subtle">
  Info message
</div>

// ✅ GOOD: Status badge con classe
<span className="badge badge-status-pending">
  Pending
</span>
```

**Utilities disponibili:**

| Class | Day Mode | Night Mode |
|-------|----------|------------|
| `.bg-info-subtle` | Azzurro chiaro | Ciano trasparente |
| `.bg-warning-subtle` | Giallo chiaro | Giallo trasparente |
| `.bg-success-subtle` | Verde chiaro | Verde trasparente |
| `.bg-danger-subtle` | Rosso chiaro | Rosso trasparente |
| `.bg-surface-subtle` | Grigio chiaro | Bianco 5% |
| `.bg-surface-hover` | Grigio medio | Bianco 8% |
| `.bg-surface-active` | Grigio | Bianco 12% |

**Border utilities:**
- `.border-subtle` - Bordi sottili
- `.border-medium` - Bordi medi
- `.border-strong` - Bordi forti

**Text utilities:**
- `.text-info-night` - Testo info (ciano in night)
- `.text-warning-night` - Testo warning (giallo in night)
- `.text-muted-night` - Testo muted
- `.text-subtle-night` - Testo subtle

### ✅ Soluzione 2: CSS Variables

Per logica condizionale:

```jsx
// ✅ GOOD: CSS variables in inline styles
<div style={{
  background: expanded
    ? 'var(--color-surface-hover)'
    : 'transparent',
  borderColor: 'var(--color-border-subtle)'
}}>
  Expandable content
</div>
```

**CSS Variables disponibili:**

```css
/* Info colors */
--color-info-bg
--color-info-border
--color-info-text

/* Warning colors */
--color-warning-bg
--color-warning-border
--color-warning-text

/* Success colors */
--color-success-bg
--color-success-border
--color-success-text

/* Danger colors */
--color-danger-bg
--color-danger-border
--color-danger-text

/* Surface colors */
--color-surface-subtle
--color-surface-hover
--color-surface-active

/* Border colors */
--color-border-subtle
--color-border-medium
--color-border-strong
```

### ✅ Soluzione 3: Bootstrap Classes

Bootstrap classes sono già theme-aware:

```jsx
// ✅ GOOD: Bootstrap alert
<div className="alert alert-info">
  Info message - funziona già in night mode!
</div>

// ✅ GOOD: Bootstrap badge
<span className="badge bg-warning">
  Warning - funziona già!
</span>
```

## Esempi Pratici

### Info Box

```jsx
// ❌ BEFORE
<div style={{
  background: '#e7f3ff',
  border: '1px solid #b6d4fe',
  borderRadius: '6px',
  padding: '12px'
}}>
  <strong>Info:</strong> Message here
</div>

// ✅ AFTER
<div className="bg-info-subtle border-info-subtle rounded p-3">
  <strong>Info:</strong> Message here
</div>
```

### Status Badge

```jsx
// ❌ BEFORE
const getStatusBadge = (status) => {
  const styles = {
    PENDING: { bg: '#ffc107', color: '#000' },
    APPROVED: { bg: '#198754', color: '#fff' }
  };
  const s = styles[status];
  return <span style={{ backgroundColor: s.bg, color: s.color }}>...</span>;
}

// ✅ AFTER
const getStatusBadge = (status) => {
  const classes = {
    PENDING: 'badge-status-pending',
    APPROVED: 'badge-status-approved'
  };
  return <span className={`badge ${classes[status]}`}>...</span>;
}
```

### Expandable Row

```jsx
// ❌ BEFORE
<div style={{
  background: expanded ? '#f8f9fa' : 'transparent'
}}>
  Content
</div>

// ✅ AFTER - Option 1: CSS Variable
<div style={{
  background: expanded
    ? 'var(--color-surface-hover)'
    : 'transparent'
}}>
  Content
</div>

// ✅ AFTER - Option 2: Class
<div className={expanded ? 'bg-surface-hover' : ''}>
  Content
</div>
```

### Warning Box with Logic

```jsx
// ❌ BEFORE
<div style={{
  background: hasError ? '#fff3cd' : '#e7f3ff',
  border: `1px solid ${hasError ? '#ffecb5' : '#b6d4fe'}`
}}>
  Message
</div>

// ✅ AFTER
<div className={hasError ? 'bg-warning-subtle' : 'bg-info-subtle'}>
  Message
</div>
```

## Migration Checklist

Per convertire componenti esistenti:

### 1. Identifica inline styles

```bash
# Trova inline styles con colori
grep -r "style=.*background: '#" src/YourComponent.js
```

### 2. Sostituisci con utilities

| Inline Style | Utility Class |
|--------------|---------------|
| `background: '#e7f3ff'` | `className="bg-info-subtle"` |
| `background: '#fff3cd'` | `className="bg-warning-subtle"` |
| `background: '#f8f9fa'` | `className="bg-surface-subtle"` |
| `border: '1px solid #dee2e6'` | `className="border-subtle"` |

### 3. Testa in entrambi i temi

- [ ] Component ok in Day mode
- [ ] Component ok in Night mode
- [ ] Transizione smooth tra temi
- [ ] Contrasto leggibile
- [ ] No hardcoded colors residui

## Best Practices

### DO ✅

1. **Usa Bootstrap quando possibile**
   ```jsx
   <div className="alert alert-info">...</div>
   ```

2. **Usa utility classes per custom styling**
   ```jsx
   <div className="bg-info-subtle border-info-subtle">...</div>
   ```

3. **Usa CSS variables per logica complessa**
   ```jsx
   <div style={{ background: active ? 'var(--color-surface-active)' : 'transparent' }}>
   ```

4. **Commenta scelte specifiche**
   ```jsx
   // Using CSS variable for conditional background
   <div style={{ background: 'var(--color-surface-hover)' }}>
   ```

### DON'T ❌

1. **Non usare hex colors hardcoded**
   ```jsx
   ❌ <div style={{ background: '#e7f3ff' }}>
   ```

2. **Non assumere sempre background bianco**
   ```jsx
   ❌ <div style={{ color: '#212529' }}>  // Illeggibile su navy!
   ```

3. **Non ignorare contrast ratios**
   - Sempre testare in night mode
   - Usare colori semantic che auto-adjustano

4. **Non creare inline logic per colors**
   ```jsx
   ❌ const bgColor = status === 'pending' ? '#ffc107' : '#198754';
   ✅ const bgClass = status === 'pending' ? 'badge-status-pending' : 'badge-status-approved';
   ```

## Testing

### Manual Test

1. Apri component in Day mode
2. Verifica leggibilità
3. Switch a Night mode (bottone 🌙)
4. Verifica leggibilità e contrasto
5. Controlla transizioni smooth

### Visual Regression

```bash
# Capture screenshots in both modes
npm run test:visual -- --theme=day
npm run test:visual -- --theme=night
```

## Troubleshooting

### Problema: Colors non cambiano

**Causa:** Inline styles con priorità
```jsx
❌ <div style={{ background: '#fff3cd' }}>
```

**Fix:** Usa utility class
```jsx
✅ <div className="bg-warning-subtle">
```

### Problema: Text illeggibile

**Causa:** Color assumptions (nero su bianco)
```jsx
❌ <span style={{ color: '#212529' }}>
```

**Fix:** Usa semantic classes o lascia ereditare
```jsx
✅ <span className="text-muted-night">
✅ <span>  <!-- Eredita da parent -->
```

### Problema: Border invisibile

**Causa:** Border colors chiari su navy
```jsx
❌ <div style={{ border: '1px solid #dee2e6' }}>
```

**Fix:** Usa border utility
```jsx
✅ <div className="border border-subtle">
```

## FAQ

**Q: Posso ancora usare inline styles?**
A: Sì, ma SOLO con CSS variables: `style={{ background: 'var(--color-info-bg)' }}`

**Q: Devo convertire tutti i componenti?**
A: Priorità: 1) User-facing, 2) Frequently used, 3) Nice to have

**Q: Come testo rapidamente?**
A: Usa DevTools, modifica `<html data-theme="night">` manualmente

**Q: Posso mixare utility classes?**
A: Sì! `className="bg-info-subtle border-info-subtle rounded p-3"`

**Q: Come contribuisco nuove utilities?**
A: Aggiungi a `night-theme.css` nella sezione Utility Classes

## Resources

- `night-theme.css` - Theme implementation
- `NIGHT_THEME_ISSUES.md` - Known issues and fixes
- `UX_AUDIT.md` - UX considerations
- Bootstrap docs - https://getbootstrap.com/docs/5.0/

---

**Ricorda:** Un tema è solo il 50% del lavoro. L'altro 50% è scrivere codice theme-aware! 🌓
