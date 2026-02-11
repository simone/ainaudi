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
