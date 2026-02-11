# 🧪 Night Theme - Visual Testing Log

**Date:** 11 Febbraio 2026
**Branch:** night-theme-testing
**Goal:** Fix night theme basato su testing visuale reale

---

## 🚀 Quick Start - How to Test

1. **Start the app:**
   ```bash
   # Make sure frontend is running
   npm run frontend
   # Navigate to http://localhost:3000
   ```

2. **Activate Night Mode:**
   - Look for 🌙 button (bottom-right corner)
   - Click to toggle Night theme
   - Verify `[data-theme="night"]` is set on `<html>` element (DevTools)

3. **Systematic Testing:**
   - Go through each page in checklist below
   - For EACH page, check backgrounds, text, buttons, contrast
   - Document issues in "Issues Found" section
   - Take screenshots if helpful

4. **After Testing:**
   - Prioritize issues (Critical → High → Medium → Low)
   - Fix one issue at a time
   - Re-test after each fix
   - Commit incrementally

---

## Testing Plan

### Pre-Testing Cleanup
- [x] Remove obvious hacks (filter, opacity) - ✅ DONE: Removed opacity/filter from page-header and dashboard-card-header
- [ ] Reduce !important usage (54 → <10) - TODO after visual testing
- [ ] Remove fragile inline selectors - TODO after visual testing
- [ ] Simplify CSS structure - TODO after visual testing

### Visual Testing Checklist

**Environment:**
- URL: http://localhost:3000
- Browser: Chrome/Firefox
- Screen: Desktop 1920x1080

**Pages to Test:**
1. [ ] Login page
2. [ ] Dashboard (home)
3. [ ] GestioneRdl
4. [ ] GestioneDeleghe
5. [ ] GestioneSezioni
6. [ ] MappaturaGerarchica
7. [ ] Modals (all types)
8. [ ] Forms (all inputs)
9. [ ] Tables
10. [ ] Alerts
11. [ ] Badges
12. [ ] Dropdowns

**For Each Page Test:**
- [ ] Background colors (not white!)
- [ ] Text visibility (readable?)
- [ ] Button visibility (red visible?)
- [ ] Contrast (WCAG AA?)
- [ ] Hover states
- [ ] Active states
- [ ] Focus states

---

## Known Problem Areas (Check These First!)

Based on v3 radical changes, these are most likely to have issues:

1. **Dashboard Cards** - Check if colored headers (violet, blue, green) are visible
2. **White Cards** - Any cards with white backgrounds should now be dark
3. **Text Colors** - Black text on dark backgrounds will be invisible
4. **Red Buttons** - Primary buttons should use bright red (#ff6b6b) not dark red
5. **Tables** - Row backgrounds and borders
6. **Forms** - Input fields should have dark backgrounds
7. **Modals** - Modal backgrounds should be dark
8. **Dropdowns** - Already fixed, but verify navbar dropdowns are visible
9. **Badges** - Check visibility of colored badges
10. **Alerts** - Check visibility of info/warning/success/danger alerts

---

## Issues Found

### How to Report Issues
For each issue, document:
- **Page/Component:** Where the issue occurs
- **Problem:** What doesn't work (be specific: "text invisible", "button too dark", etc.)
- **Expected:** What it should look like
- **Screenshot:** (optional but helpful)

### Critical (Bloccanti)

#### Issue #2: Tables - white background
**Page:** All pages with tables
**Problem:**
- Bootstrap table variables use `--bs-body-bg: #fff`
- Tables render with white background in night mode
- Previous selectors lacked !important to override Bootstrap variables
**Status:** ✅ FIXED

**Fix Applied:**
- Forced table backgrounds with `!important`
- Override Bootstrap CSS variables: `--bs-table-bg`, `--bs-body-bg`, `--bs-table-color`
- Added striped rows support (subtle transparency)
- Added hover state override
- Added bordered table support

**Test Result:** Ricarica e verifica tabelle ora scure

#### Issue #3: Consultazione switcher - blue/white alert
**Page:** All pages with consultazione switcher header
**Element:**
```html
<div class="alert alert-primary d-flex align-items-center...">
  <h5 class="mb-0">Referendum Costituzionale Giustizia 2026</h5>
</div>
```
**Problem:** `alert-primary` has light blue background, not dark - missing from CSS!
**Status:** ✅ FIXED

**Fix Applied:**
```css
[data-theme="night"] .alert-primary {
  background: var(--bg-dark-tertiary) !important;
  border-color: var(--color-accent-red) !important;
  color: var(--text-primary) !important;
}
```

**Test Result:** Ricarica e verifica header consultazione ora scuro

#### Issue #4: Code elements in tables - light background
**Element:** `.table code`, `code`, `pre`
**Problem:**
```css
.table code {
    background: #f8f9fa;  /* Light gray */
    color: #d63384;       /* Pink */
}
```
**Status:** ✅ FIXED

**Fix Applied:**
```css
[data-theme="night"] code,
[data-theme="night"] .table code {
  background: var(--bg-dark-tertiary) !important;
  color: var(--color-accent-red) !important;
  border: 1px solid var(--border-medium);
}
```
Also fixed `pre` elements for code blocks.

**Test Result:** Ricarica e verifica elementi code ora scuri

#### Issue #5: Nav tabs active state - white background
**Element:** `.nav-tabs .nav-link.active`
**Problem:** Uses Bootstrap variables pointing to white:
- `--bs-nav-tabs-link-active-bg` → white
- `--bs-nav-tabs-link-active-color` → dark text
**Status:** ✅ FIXED

**Fix Applied:**
```css
[data-theme="night"] .nav-tabs .nav-link.active {
  background: var(--bg-dark-tertiary) !important;
  color: var(--text-primary) !important;
  --bs-nav-tabs-link-active-bg: var(--bg-dark-tertiary) !important;
  --bs-nav-tabs-link-active-color: var(--text-primary) !important;
}
```
Also styled inactive tabs, hover states, and tab-content area.

**Test Result:** Ricarica e verifica tabs attive ora scure

#### Issue #6: Alert-light - white/light background
**Element:** `.alert-light`
**Problem:** Uses Bootstrap light variables:
```css
--bs-alert-bg: var(--bs-light-bg-subtle);  /* Very light gray/white */
--bs-alert-color: var(--bs-light-text-emphasis);  /* Dark text */
```
**Status:** ✅ FIXED

**Fix Applied:**
```css
[data-theme="night"] .alert-light {
  background: var(--bg-dark-tertiary) !important;
  border-color: var(--border-medium) !important;
  color: var(--text-secondary) !important;
  --bs-alert-bg: var(--bg-dark-tertiary) !important;
  --bs-alert-color: var(--text-secondary) !important;
  --bs-alert-border-color: var(--border-medium) !important;
}
```
Override all Bootstrap alert-light variables.

**Test Result:** Ricarica e verifica .alert-light ora scuro

#### Issue #7: Bootstrap utility classes - light backgrounds and text
**Element:** `.bg-white`, `.bg-light`, `.text-dark`, etc.
**Problem:**
```css
.bg-white { background-color: white; }  /* Hardcoded */
.bg-light { background-color: #f8f9fa; }
.text-dark { color: #212529; }  /* Black text */
```
Bootstrap utilities used throughout app - major source of light backgrounds.
**Status:** ✅ FIXED

**Fix Applied:**
Created comprehensive utility class overrides:
```css
/* Backgrounds */
.bg-white → var(--bg-dark-secondary)
.bg-light → var(--bg-dark-tertiary)

/* Text colors */
.text-dark → var(--text-primary)
.text-muted → var(--text-muted)
.text-black → var(--text-primary)

/* Borders */
.border → var(--border-medium)
.border-light → var(--border-dark)
```

All overrides use !important to beat Bootstrap specificity.

**Test Result:** Ricarica e verifica elementi con .bg-white ora scuri

#### Issue #8: GestioneRdl component - multiple white backgrounds
**File:** `src/GestioneRdl.css`
**Problem:** 4 classes with hardcoded white backgrounds:
- `.rdl-stats` (line 243)
- `.rdl-card` (line 74)
- `.rdl-card-compact` (line 90)
- `.rdl-filters` (line 18)

Plus many elements using `--color-gray-100` (light gray)
**Status:** ✅ FIXED

**Fix Applied:**
Comprehensive GestioneRdl component overrides (15+ rules):
```css
/* Main containers */
.rdl-card, .rdl-card-compact → --bg-dark-secondary
.rdl-filters, .rdl-stats → dark backgrounds
.rdl-stat-box, .rdl-territory-filters → --bg-dark-tertiary

/* Text colors */
.rdl-data-label, .rdl-section-header → --text-secondary
.rdl-data-value, .rdl-form-label → --text-primary

/* Badges */
.rdl-badge-info → --color-info-bg + --color-info
.rdl-badge-primary → red accent colors
.rdl-badge-muted → dark elevated
```

**Test Result:** Ricarica GestioneRdl page e verifica tutti elementi scuri

#### Issue #9: Inline styles - background: white (keyword + hex)
**Element:** Registration lists, various containers
**Problem:**
- Inline `style="background: white"` not caught (keyword, not rgb)
- Inline `style="background: #fff"` and `#ffffff` not caught
- Inline `color: rgb(73, 80, 87)` gray text invisible
- Inline `border-bottom: 1px solid rgb(233, 236, 239)` light borders
**Status:** ✅ FIXED

**Fix Applied:**
Extended inline style selectors to catch ALL variations:
```css
/* Backgrounds - now catches white keyword + hex */
div[style*="background: white"],
div[style*="background: #fff"],
div[style*="background: #ffffff"] → --bg-dark-secondary

/* Text - now catches rgb(73, 80, 87) gray */
div[style*="color: rgb(73, 80, 87)"] → --text-primary

/* Borders - now catches rgb(233, 236, 239) */
div[style*="border-bottom: 1px solid rgb(233, 236, 239)"] → --border-dark
```

**Test Result:** Ricarica liste registrazioni e verifica backgrounds scuri

#### Issue #10: Progress bars - light background
**Element:** `.progress`, `.progress-stacked`
**Problem:** Uses Bootstrap `--bs-progress-bg: var(--bs-secondary-bg)` → light gray
**Status:** ✅ FIXED

**Fix Applied:**
```css
[data-theme="night"] .progress {
  background-color: var(--bg-dark-tertiary) !important;
  --bs-progress-bg: var(--bg-dark-tertiary) !important;
  --bs-progress-bar-bg: var(--color-accent-red) !important;
}

[data-theme="night"] .progress-bar {
  background-color: var(--color-accent-red) !important;
}

[data-theme="night"] .progress-bar-striped {
  /* Dark-aware stripes with subtle transparency */
}
```

Override Bootstrap variables + direct properties.
Progress bars now dark with bright red fill.

**Test Result:** Ricarica e verifica progress bars scuri con fill rosso

#### Issue #11: Mappatura page - massive inline rgb() styles
**Page:** MappaturaGerarchica
**Problem:** Entire page built with inline rgb() colors:
- `rgb(245, 245, 245)` body background
- `rgb(255, 255, 255)` white cards/headers/footer
- `rgb(233, 236, 239)` light gray badges
- `rgb(108, 117, 125)` gray text
- `rgb(33, 37, 41)` almost black text
- `rgb(222, 226, 230)` borders
**Status:** ✅ FIXED

**Fix Applied:**
Extended inline style selectors to catch ALL rgb() variations used in Mappatura page:

```css
/* Backgrounds - added rgb() variations */
background-color: rgb(255, 255, 255) → --bg-dark-secondary
background-color: rgb(245, 245, 245) → --bg-dark-secondary
background-color: rgb(233, 236, 239) → --bg-dark-secondary
background-color: rgb(248, 249, 250) → --bg-dark-secondary

/* Text - added new rgb() grays */
color: rgb(108, 117, 125) → --text-primary (medium gray)
color: rgb(33, 37, 41) → --text-primary (almost black)

/* Borders - added rgb() variations */
border: 1px solid rgb(222, 226, 230) → --border-dark
border-top/border-bottom variants
```

Extended to div, span, p, i, input elements.

**Test Result:** Ricarica MappaturaGerarchica e verifica tutto scuro

#### Issue #12: Alert-secondary + semantic subtle backgrounds
**Element:** `.alert-secondary`, inline subtle colors
**Problem:**
- `.alert-secondary` uses `--bs-secondary-bg-subtle` → light gray
- Inline `rgb(209, 231, 221)` light green (success subtle)
- Inline `rgb(248, 215, 218)` light pink (danger subtle)
**Status:** ✅ FIXED

**Fix Applied:**
```css
/* Alert-secondary */
[data-theme="night"] .alert-secondary {
  background: var(--bg-dark-tertiary) !important;
  /* Override all Bootstrap variables */
}

/* Success subtle background - light green */
div[style*="background: rgb(209, 231, 221)"] {
  background: var(--color-success-bg) !important;
  border-color: var(--color-success) !important;
}

/* Danger subtle background - light pink */
div[style*="background: rgb(248, 215, 218)"] {
  background: var(--color-danger-bg) !important;
  border-color: var(--color-danger) !important;
}
```

**Test Result:** Ricarica e verifica alerts e boxes semantici scuri

#### Issue #13: .doc-card states - light backgrounds
**Element:** `.doc-card` (Risorse page)
**Problem:**
- Base: likely light background
- `:hover`: light gray
- `:active`: `#e9ecef` light gray
**Status:** ✅ FIXED

**Fix Applied:**
```css
[data-theme="night"] .doc-card {
  background: var(--bg-dark-secondary) !important;
  border-color: var(--border-medium) !important;
}

[data-theme="night"] .doc-card:hover {
  background: var(--bg-dark-tertiary) !important;
  box-shadow: var(--shadow-md);
}

[data-theme="night"] .doc-card:active {
  background: var(--bg-dark-elevated) !important;
}
```

All interaction states now dark with proper visual feedback.

**Test Result:** Ricarica Risorse page, verifica doc cards scure e hover/active states

---

### Critical (Bloccanti) - FIXED

#### Issue #1: Dashboard info boxes - white background + black text
**Page:** Dashboard (home)
**Problem:**
- `<div style="background: rgb(248, 249, 250);">` → Light gray background (not overridden)
- `<div style="color: rgb(51, 51, 51);">` → Dark gray/black text
- Result: Light box with dark text in dark mode = breaks theme

**Element:**
```html
<div class="mb-3 p-3" style="background: rgb(248, 249, 250); border-radius: 10px; border-left: 4px solid rgb(111, 66, 193);">
  <div class="small text-muted mb-1"><i class="fas fa-lightbulb me-1"></i> A cosa serve</div>
  <div style="font-size: 0.85rem; color: rgb(51, 51, 51);">Configurazione della base territoriale...</div>
</div>
```

**Root Cause:** Inline styles use `rgb()` notation, but CSS selectors only match `#hex` notation
**Status:** ✅ FIXED

**Fix Applied:**
Added RGB notation selectors to catch inline styles:
```css
/* Background: rgb(248, 249, 250) → dark gray */
[data-theme="night"] div[style*="background: rgb(248, 249, 250)"] {
  background: var(--bg-dark-tertiary) !important;
}

/* Color: rgb(51, 51, 51) → light text */
[data-theme="night"] div[style*="color: rgb(51, 51, 51)"] {
  color: var(--text-primary) !important;
}
```

**Test Result:** Ricarica pagina (Cmd+Shift+R) e verifica box "A cosa serve"

### High Priority
<!-- Major visual problems that affect usability -->

### Medium Priority
<!-- Minor visual issues that should be fixed -->

### Low Priority
<!-- Polish and nice-to-haves -->

---

## Fixes Applied

### Fix 1: [Title]
**Problem:**
**Solution:**
**Test Result:**

---

## Testing Results

### Before (v3 untested)
- Screenshot: N/A
- Issues: Unknown

### After Each Fix
- Fix #1: [result]
- Fix #2: [result]
...

---

## Final Validation

### WCAG Contrast Check
- [ ] Text on backgrounds: __:1
- [ ] Links on backgrounds: __:1
- [ ] Buttons on backgrounds: __:1

### Cross-Browser
- [ ] Chrome
- [ ] Firefox
- [ ] Safari
- [ ] Edge

### Responsive
- [ ] Desktop (1920x1080)
- [ ] Laptop (1366x768)
- [ ] Tablet (768x1024)
- [ ] Mobile (375x667)

---

## Sign-Off

- [ ] All critical issues fixed
- [ ] All high priority fixed
- [ ] Contrast ratios validated
- [ ] Cross-browser tested
- [ ] User approval obtained

**Status:** 🟡 In Progress
**Next Steps:** Visual testing + iterative fixes
